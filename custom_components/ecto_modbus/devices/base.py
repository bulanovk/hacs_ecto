import struct

class EctoDevice:
    """Базовый класс для всех устройств Ectocontrol"""
    STRUCT_FORMAT = ">B3BxB2B"
    DEVICE_TYPE = 0x00
    CHANNEL_COUNT = 0
    UID_BASE = 0x800000

    def __init__(self, config):
        self.config = config
        self.addr = config['addr']
        self.uid = self.UID_BASE + (self.addr - 3)
        self._init_registers()

    def _init_registers(self):
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
        self.input_registers = [0x0000] * self._register_count()

    @property
    def _register_count(self):
        return (self.CHANNEL_COUNT + 15) // 16