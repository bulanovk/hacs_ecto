import logging
import voluptuous as vol
from pymodbus.server import ModbusSerialServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .devices import EctoCH10BinarySensor, EctoRelay8CH,EctoTemperatureSensor
from .const import DOMAIN, DEFAULT_BAUDRATE, DEVICE_TYPES
from homeassistant.helpers.discovery import load_platform
from modbus_tk import modbus_rtu
from serial import rs485


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
    conf = config[DOMAIN]
    ecto_devices = []

    port485_main = rs485.RS485(config['port'], baudrate=19200, inter_byte_timeout=0.002)
    server19200 = modbus_rtu.RtuServer(port485_main, interchar_multiplier=1)
    server19200.start()

    for device_conf in conf["devices"]:
        device_class = DEVICE_CLASSES[device_conf["type"]]
        device = device_class(device_conf, server19200)

        if hasattr(device, 'async_init'):
            await device.async_init(hass)

        ecto_devices.append(device)

    _LOGGER.warning("Going to init Modbus")

    hass.data[DOMAIN] = {
        "devices": ecto_devices,
        "rtu": server19200
    }

    load_platform(hass, "switch", DOMAIN, {}, config)
    return True

async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Настройка через UI"""
    config = entry.data
    ecto_devices = []

    # Инициализация устройств
    for device_conf in config.get('devices', []):
        device_type = device_conf['type']
        if device_type not in DEVICE_CLASSES:
            continue

        device_class = DEVICE_CLASSES[device_type]
        device = device_class(device_conf)

        if hasattr(device, 'setup'):
            await device.setup(hass)

        ecto_devices.append(device)

    # Запуск Modbus сервера
    await setup_modbus_server(hass, config, ecto_devices)

    # Регистрация платформ
    await hass.config_entries.async_forward_entry_setups(entry, "switch")
    return True

async def setup_modbus_server(hass, config, ecto_devices):
    """Настройка Modbus сервера"""
    slaves = {}
    for device in ecto_devices:
        store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0x00, device.holding_registers),
            ir=ModbusSequentialDataBlock(0x10, device.input_registers)
        )
        slaves[device.addr] = store

    context = ModbusServerContext(slaves=slaves, single=False)

    try:
        svr: ModbusSerialServer = ModbusSerialServer(
            context,
            port=config['port'],
            baudrate=DEFAULT_BAUDRATE,
            parity="N",
            stopbits=1,
            bytesize=8,
            broadcast_enable=True
        )
        await svr.serve_forever(background=True)
    except Exception as e:
        _LOGGER.error("Failed to start Modbus server: %s", e)
        return False

    hass.data.setdefault(DOMAIN, {})[config['port']] = {
        'context': context,
        'devices': ecto_devices
    }

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

