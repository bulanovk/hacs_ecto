import logging
import voluptuous as vol
from pymodbus.server import StartAsyncSerialServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .devices import EctoCH10BinarySensor, EctoRelay8CH,EctoTemperatureSensor
from .const import DOMAIN, DEFAULT_BAUDRATE, DEVICE_TYPES
from homeassistant.helpers.discovery import load_platform



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
    slaves = {}
    devices = []

    for device_conf in conf["devices"]:
        device_class = DEVICE_CLASSES[device_conf["type"]]
        device = device_class(device_conf)

        if hasattr(device, 'async_init'):
            await device.async_init(hass)

        store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0x00, device.holding_registers),
            ir=ModbusSequentialDataBlock(0x10, device.input_registers)
        )

        slaves[device.addr] = store
        devices.append(device)

    context = ModbusServerContext(slaves=slaves, single=False)

    await StartAsyncSerialServer(
        context,
        port=conf["port"],
        baudrate=DEFAULT_BAUDRATE,
        parity="N",
        stopbits=1,
        bytesize=8,
        broadcast_enable=True
    )

    hass.data[DOMAIN] = {
        "devices": devices,
        "context": context
    }

    load_platform("switch", DOMAIN, {}, config)
    return True

async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Настройка через UI"""
    config = entry.data
    devices = []

    # Инициализация устройств
    for device_conf in config.get('devices', []):
        device_type = device_conf['type']
        if device_type not in DEVICE_CLASSES:
            continue

        device_class = DEVICE_CLASSES[device_type]
        device = device_class(device_conf)

        if hasattr(device, 'setup'):
            await device.setup(hass)

        devices.append(device)

    # Запуск Modbus сервера
    await setup_modbus_server(hass, config, devices)

    # Регистрация платформ
    await hass.config_entries.async_forward_entry_setups(entry, "switch")
    return True

async def setup_modbus_server(hass, config, devices):
    """Настройка Modbus сервера"""
    slaves = {}
    for device in devices:
        store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0x00, device.holding_registers),
            ir=ModbusSequentialDataBlock(0x10, device.input_registers)
        )
        slaves[device.addr] = store

    context = ModbusServerContext(slaves=slaves, single=False)

    try:
        await StartAsyncSerialServer(
            context,
            port=config['port'],
            baudrate=DEFAULT_BAUDRATE,
            parity="N",
            stopbits=1,
            bytesize=8,
            broadcast_enable=True
        )
    except Exception as e:
        _LOGGER.error("Failed to start Modbus server: %s", e)
        return False

    hass.data.setdefault(DOMAIN, {})[config['port']] = {
        'context': context,
        'devices': devices
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

