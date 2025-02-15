import logging
import voluptuous as vol
from pymodbus.server.async_io import StartAsyncSerialServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .devices import EctoCH10BinarySensor, EctoRelay8CH

DOMAIN = "ecto"
_LOGGER = logging.getLogger(__name__)
BAUDRATE = 19200

DEVICE_CLASSES = {
    'binary_sensor_10ch': EctoCH10BinarySensor,
    'relay_8ch': EctoRelay8CH
}

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("port"): str,
        vol.Required("devices"): vol.All(
            cv.ensure_list,
            [
                {
                    vol.Required("type"): vol.In(DEVICE_CLASSES.keys()),
                    vol.Required("addr"): vol.All(
                        cv.positive_int,
                        vol.Range(min=3, max=32)
                }
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

        store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0x00, device.holding_registers),
            ir=ModbusSequentialDataBlock(0x10, device.input_registers),
            zero_mode=True
        )

        slaves[device.addr] = store
        devices.append(device)

    context = ModbusServerContext(slaves=slaves, single=False)

    await StartAsyncSerialServer(
        context,
        port=conf["port"],
        baudrate=BAUDRATE,
        parity="N",
        stopbits=1,
        bytesize=8,
        broadcast_enable=True
    )

    hass.data[DOMAIN] = {
        "devices": devices,
        "context": context
    }

    hass.helpers.discovery.load_platform("switch", DOMAIN, {}, config)
    return True