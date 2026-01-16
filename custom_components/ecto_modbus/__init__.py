import logging

import modbus_tk
import voluptuous as vol
# from pymodbus.server import ModbusSerialServer
# from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
# from pymodbus.datastore import ModbusSequentialDataBlock
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .devices import EctoCH10BinarySensor, EctoRelay8CH,EctoTemperatureSensor
from .const import DOMAIN, DEFAULT_BAUDRATE, DEVICE_TYPES
from homeassistant.helpers.discovery import load_platform
from modbus_tk import modbus_rtu, hooks
from serial import rs485
from modbus_tk import utils

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASSES = {
    'binary_sensor_10ch': EctoCH10BinarySensor,
    'relay_8ch': EctoRelay8CH,
    'temperature_sensor': EctoTemperatureSensor

}

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("port"): str,
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
                            ['binary_sensor_10ch', 'relay_8ch']
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
    logger = utils.create_logger(name="dummy",level=logging.CRITICAL, record_format="%(message)s")

    port = conf.get("port")
    _LOGGER.debug("Configuring RS485 port: %s", port)
    port485_main = rs485.RS485(port, baudrate=19200, inter_byte_timeout=0.002)
    _LOGGER.info("RS485 port configured: %s, baudrate=19200", port)

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
        _LOGGER.debug("Device added to list: addr=%s", device_addr)

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

