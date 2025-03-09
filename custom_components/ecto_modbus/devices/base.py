import struct

class EctoDevice:
    """Базовый класс для всех устройств Ectocontrol"""
    STRUCT_FORMAT = ">BBBBBBBB"
    DEVICE_TYPE = 0x00
    CHANNEL_COUNT = 0
    UID_BASE = 0x800000

    def __init__(self, config):
        self.config = config
        self.addr = config['addr']
        self.uid = self.UID_BASE + (self.addr - 3)
        self._init_registers()
        self.input_registers = [0, 0, 0, 0]

    def _init_registers(self):
        # reg = ModBusRegisterSensor(self.slave, cst.HOLDING_REGISTERS, 0, 4)
        # reg.set_raw_value([0x80, slave_id - 3, slave_id, dev_type])
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

