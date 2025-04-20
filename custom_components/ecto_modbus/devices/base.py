from modbus_tk.modbus_rtu import RtuServer
import modbus_tk.defines as cst
from ..transport.modBusRTU import ModBusRegisterSensor


class EctoDevice:
    """Базовый класс для всех устройств Ectocontrol"""
    DEVICE_TYPE = 0x00
    UID_BASE = 0x800000

    def __init__(self, config, server: RtuServer):
        self.config = config
        self.addr = config['addr']
        self.server = server
        self.slave = server.add_slave(self.addr)
        self.uid = self.UID_BASE + (self.addr - 3)
        reg = ModBusRegisterSensor(self.slave, cst.HOLDING_REGISTERS, 0, 4)
        reg.set_raw_value([0x80, (self.addr - 3), self.addr, self.DEVICE_TYPE])
        self.registers = {0: reg}
