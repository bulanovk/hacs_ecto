# custom_components/ecto_modbus/__init__.py
import logging
import struct
import voluptuous as vol
from pymodbus.server.async_io import StartAsyncSerialServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

DOMAIN = "ecto_modbus"
_LOGGER = logging.getLogger(__name__)
BAUDRATE = 19200
UID_BASE = 0x800000

class EctoDevice:
    """Базовый класс устройств Ectocontrol"""
    STRUCT_FORMAT = ">B3BxB2B"

    def __init__(self, addr):
        self.addr = addr
        self.uid = UID_BASE + (self.addr - 3)
        self._setup_device_registers()

    def _setup_device_registers(self):
        """Инициализация структуры устройства"""
        device_bytes = struct.pack(
            self.STRUCT_FORMAT,
            0x00,
            (self.uid >> 16) & 0xFF,
            (self.uid >> 8) & 0xFF,
            self.uid & 0xFF,
            0x00,
            self.addr,
            self.DEVICE_TYPE,
            self.CHANNEL_COUNT
        )
        self.holding_registers = [
            (device_bytes[i] << 8) | device_bytes[i+1]
            for i in range(0, 8, 2)
        ]

class EctoCH10BinarySensor(EctoDevice):
    """10-канальный бинарный датчик"""
    DEVICE_TYPE = 0x59
    CHANNEL_COUNT = 10

    def __init__(self, addr):
        super().__init__(addr)
        self.input_registers = [0x0000]

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("port"): str,
        vol.Required("devices"): vol.All(
            cv.ensure_list,
            [
                {
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
        addr = device_conf["addr"]
        device = EctoCH10BinarySensor(addr)

        store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0x00, device.holding_registers),
            ir=ModbusSequentialDataBlock(0x10, device.input_registers),
            zero_mode=True
        )

        slaves[addr] = store
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