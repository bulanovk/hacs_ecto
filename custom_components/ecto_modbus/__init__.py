import logging
import struct

import modbus_tk
import voluptuous as vol
# from pymodbus.server import ModbusSerialServer
# from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
# from pymodbus.datastore import ModbusSequentialDataBlock
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .devices import EctoCH10BinarySensor, EctoRelay10CH, EctoTemperatureSensor
from .const import (
    DOMAIN,
    DEFAULT_BAUDRATE,
    DEVICE_TYPES,
    PORT_TYPE_SERIAL,
    PORT_TYPE_RS485
)
from homeassistant.helpers.discovery import load_platform
from modbus_tk import modbus_rtu, hooks
from serial import rs485
from modbus_tk import utils

_LOGGER = logging.getLogger(__name__)

# Global device registry for hook callback
_DEVICE_REGISTRY = {}


class LoggingSerialWrapper:
    """Wrapper around serial port to log all RT/TX bytes"""
    
    def __init__(self, serial_port, logger, port_name):
        self._serial = serial_port
        self._logger = logger
        self._port_name = port_name
        
    def read(self, size=1):
        """Read and log bytes from serial port"""
        data = self._serial.read(size)
        if data:
            hex_str = ' '.join(f'{b:02x}' for b in data)
            self._logger.debug("RT: %s RX (%d bytes): %s", self._port_name, len(data), hex_str)
        return data
    
    def write(self, data):
        """Write and log bytes to serial port"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        self._logger.debug("TX: %s TX (%d bytes): %s", self._port_name, len(data), hex_str)
        return self._serial.write(data)
    
    def __getattr__(self, name):
        """Proxy all other attributes to the wrapped serial port"""
        return getattr(self._serial, name)


def _log_modbus_error(data):
    """Hook to log Modbus errors"""
    try:
        # Handle different error hook signatures
        if len(data) >= 3:
            # Old format: (databank, exception, request_pdu)
            databank, ex, request_pdu = data[0], data[1], data[2]
        elif len(data) == 2:
            # Alternative format: (exception, request_pdu)
            ex, request_pdu = data[0], data[1]
        else:
            # Unknown format
            ex, request_pdu = "Unknown error", data
        _LOGGER.error("Modbus Error: exception=%s, request_pdu=%s", ex, request_pdu)
    except Exception as e:
        _LOGGER.error("Modbus Error: Failed to parse error data: %s, data=%s", e, data)


def _on_slave_handle_request(data):
    """Hook to intercept Modbus write requests and sync to device state.

    This hook is called after a slave processes a request. We parse write
    operations (function code 0x10 - Write Multiple Registers) and notify
    the corresponding device so it can update its internal state and trigger HA updates.

    Note: Ectocontrol protocol only supports 0x10, not 0x06 (Write Single Register).
    """
    try:
        # data is a tuple: (slave_id, request_pdu, response_pdu)
        if len(data) < 3:
            return

        slave_id = data[0]
        request_pdu = data[1]

        if not request_pdu or len(request_pdu) < 6:
            return

        function_code = request_pdu[0]

        # Function code 0x10 = Write Multiple Registers (only one supported by protocol)
        if function_code != 0x10:
            return

        # Look up device by slave_id
        device = _DEVICE_REGISTRY.get(slave_id)
        if not device or not hasattr(device, 'on_register_write'):
            return

        # Write Multiple Registers: FC(1) + StartAddr(2) + RegCount(2) + ByteCount(1) + Values(N*2)
        start_addr = struct.unpack(">H", request_pdu[1:3])[0]
        reg_count = struct.unpack(">H", request_pdu[3:5])[0]
        byte_count = request_pdu[5]

        if len(request_pdu) >= 6 + byte_count:
            values = []
            for i in range(reg_count):
                offset = 6 + i * 2
                val = struct.unpack(">H", request_pdu[offset:offset+2])[0]
                values.append(val)
            _LOGGER.debug("Detected write multiple registers: slave=%s, addr=0x%04X, count=%d, values=%s",
                         slave_id, start_addr, reg_count, [hex(v) for v in values])
            device.on_register_write(start_addr, values)

    except Exception as e:
        _LOGGER.error("Error in _on_slave_handle_request: %s", e)

DEVICE_CLASSES = {
    'binary_sensor_10ch': EctoCH10BinarySensor,
    'relay_10ch': EctoRelay10CH,
    'temperature_sensor': EctoTemperatureSensor

}

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("port"): str,
        vol.Optional("port_type", default=PORT_TYPE_RS485): vol.In({
            PORT_TYPE_SERIAL,
            PORT_TYPE_RS485
        }),
        vol.Optional("baudrate", default=DEFAULT_BAUDRATE): cv.positive_int,
        vol.Required("devices"): vol.All(
            cv.ensure_list,
            [
                vol.Any(
                    {
                        vol.Required("type"): 'temperature_sensor',
                        vol.Required("addr"): vol.All(
                            cv.positive_int,
                            vol.Range(min=3, max=32)
                        ),
                        vol.Required("entity_id"): cv.entity_id
                    },
                    {
                        vol.Required("type"): vol.In(
                            ['binary_sensor_10ch', 'relay_10ch']
                        ),
                        vol.Required("addr"): vol.All(
                            cv.positive_int,
                            vol.Range(min=3, max=32)
                        )
                    }
                )
            ]
        )
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    _LOGGER.info("Setting up Ecto Modbus integration")
    conf = config[DOMAIN]
    ecto_devices = []

    _LOGGER.debug("Creating dummy logger for modbus_tk")
    logger = utils.create_logger(name="dummy",level=logging.DEBUG, record_format="%(message)s")

    _LOGGER.debug("Installing Modbus error logging hook")
    hooks.install_hook("modbus.Databank.on_error", _log_modbus_error)

    _LOGGER.debug("Installing Modbus write detection hook for sync")
    hooks.install_hook("modbus.Slave.on_handle_request", _on_slave_handle_request)

    port = conf.get("port")
    port_type = conf.get("port_type", PORT_TYPE_RS485)
    baudrate = conf.get("baudrate", DEFAULT_BAUDRATE)

    _LOGGER.debug("Configuring %s port: %s", port_type, port)

    if port_type == PORT_TYPE_RS485:
        port485_main = rs485.RS485(port, baudrate=baudrate, inter_byte_timeout=0.002)
        _LOGGER.info("RS485 port configured: %s, baudrate=%d", port, baudrate)
    else:
        import serial
        port485_main = serial.Serial(port, baudrate=baudrate, timeout=0.002)
        _LOGGER.info("Serial port configured: %s, baudrate=%d", port, baudrate)

    # Wrap serial port with logging
    port485_main = LoggingSerialWrapper(port485_main, _LOGGER, port)
    _LOGGER.info("Serial packet logging enabled for port %s", port)

    _LOGGER.debug("Creating Modbus RTU server")
    server19200 = modbus_rtu.RtuServer(port485_main, interchar_multiplier=1, error_on_missing_slave=False)
    server19200.start()
    _LOGGER.info("Modbus RTU server started on port %s", port)

    device_count = len(conf["devices"])
    _LOGGER.info("Initializing %d device(s)", device_count)

    for idx, device_conf in enumerate(conf["devices"]):
        device_type = device_conf["type"]
        device_addr = device_conf["addr"]
        _LOGGER.debug("Creating device %d/%d: type=%s, addr=%s",
                     idx + 1, device_count, device_type, device_addr)
        device_class = DEVICE_CLASSES[device_type]
        device = device_class(device_conf, server19200)

        if hasattr(device, 'async_init'):
            _LOGGER.debug("Calling async_init for device: addr=%s", device_addr)
            await device.async_init(hass)

        ecto_devices.append(device)

        # Register device for Modbus write hook callback
        _DEVICE_REGISTRY[device_addr] = device
        _LOGGER.debug("Device registered for sync: addr=%s", device_addr)

    _LOGGER.info("All devices initialized: total=%d", len(ecto_devices))
    _LOGGER.debug("Storing devices and server in hass.data")

    hass.data[DOMAIN] = {
        "devices": ecto_devices,
        "rtu": server19200
    }

    _LOGGER.debug("Loading switch platform")
    load_platform(hass, "switch", DOMAIN, {}, config)
    _LOGGER.info("Ecto Modbus integration setup completed")
    return True

# async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
#     """Настройка через UI"""
#     config = entry.data
#     ecto_devices = []

#     # Инициализация устройств
#     for device_conf in config.get('devices', []):
#         device_type = device_conf['type']
#         if device_type not in DEVICE_CLASSES:
#             continue

#         device_class = DEVICE_CLASSES[device_type]
#         device = device_class(device_conf)

#         if hasattr(device, 'setup'):
#             await device.setup(hass)

#         ecto_devices.append(device)

#     # Запуск Modbus сервера
#     await setup_modbus_server(hass, config, ecto_devices)

#     # Регистрация платформ
#     await hass.config_entries.async_forward_entry_setups(entry, "switch")
#     return True

# async def setup_modbus_server(hass, config, ecto_devices):
#     """Настройка Modbus сервера"""
#     slaves = {}
#     for device in ecto_devices:
#         store = ModbusSlaveContext(
#             hr=ModbusSequentialDataBlock(0x00, device.holding_registers),
#             ir=ModbusSequentialDataBlock(0x10, device.input_registers)
#         )
#         slaves[device.addr] = store

#     context = ModbusServerContext(slaves=slaves, single=False)

#     try:
#         svr: ModbusSerialServer = ModbusSerialServer(
#             context,
#             port=config['port'],
#             baudrate=DEFAULT_BAUDRATE,
#             parity="N",
#             stopbits=1,
#             bytesize=8,
#             broadcast_enable=True
#         )
#         await svr.serve_forever(background=True)
#     except Exception as e:
#         _LOGGER.error("Failed to start Modbus server: %s", e)
#         return False

#     hass.data.setdefault(DOMAIN, {})[config['port']] = {
#         'context': context,
#         'devices': ecto_devices
#     }

async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Выгрузка конфигурации"""
    await hass.config_entries.async_forward_entry_unload(entry, "switch")
    return True


# async def add_device_service(call):
#     """Сервис для добавления устройств через UI"""
#     entry_id = call.data["entry_id"]
#     device_config = call.data["device"]
#
#     entry = hass.config_entries.async_get_entry(entry_id)
#     new_data = dict(entry.data)
#     new_data["devices"].append(device_config)
#
#     hass.config_entries.async_update_entry(entry, data=new_data)

