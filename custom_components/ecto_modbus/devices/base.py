import logging
from modbus_tk.modbus_rtu import RtuServer
import modbus_tk.defines as cst
from ..transport.modBusRTU import ModBusRegisterSensor

_LOGGER = logging.getLogger(__name__)


class EctoDevice:
    """Базовый класс для всех устройств Ectocontrol"""
    DEVICE_TYPE = 0x00
    UID_BASE = 0x800000

    def __init__(self, config, server: RtuServer):
        self.config = config
        self.addr = config['addr']
        self.server = server
        _LOGGER.debug("Creating EctoDevice: addr=%s, type=%s", self.addr, hex(self.DEVICE_TYPE))
        self.slave = server.add_slave(self.addr)
        _LOGGER.debug("Slave added to server: slave_id=%s", self.addr)
        self.uid = self.UID_BASE + (self.addr - 3)
        reg = ModBusRegisterSensor(self.slave, cst.HOLDING_REGISTERS, 0, 4)
        uid_data = [0x80, (self.addr - 3), self.addr, self.DEVICE_TYPE]
        _LOGGER.debug("Setting UID registers: addr=%s, uid=%s, data=%s",
                     self.addr, hex(self.uid), uid_data)
        reg.set_raw_value(uid_data)
        self.registers = {0: reg}
        _LOGGER.info("EctoDevice initialized: addr=%s, uid=%s, device_type=%s",
                    self.addr, hex(self.uid), hex(self.DEVICE_TYPE))
