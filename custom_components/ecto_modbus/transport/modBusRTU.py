import logging
from modbus_tk.modbus import Slave

_LOGGER = logging.getLogger(__name__)


class ModBusRegisterSensor:

    def __init__(self, slave: Slave, reg_type: int, addr: int, reg_size: int, read_callback=None):
        self.block_name = "val-x" + str(addr)
        self.addr = addr
        self.reg_type = reg_type
        self.reg_size = reg_size
        self.read_callback = read_callback
        slave.add_block(self.block_name, reg_type, addr, reg_size)
        self.slave = slave
        _LOGGER.debug("Created ModbusRegisterSensor: block=%s, type=%s, addr=%s, size=%s",
                     self.block_name, hex(reg_type), hex(addr), reg_size)

    def set_raw_value(self, raw_value):
        _LOGGER.debug("TX: Writing to register - block=%s, addr=%s (0x%s), value=%s, type=%s",
                     self.block_name, self.addr, hex(self.addr), raw_value,
                     "HOLDING" if self.reg_type == 0 else "INPUT")
        self.slave.set_values(self.block_name, self.addr, raw_value)
        _LOGGER.debug("TX: Register write completed - block=%s, addr=%s (0x%s)",
                     self.block_name, self.addr, hex(self.addr))

    def get_values(self):
        """Get values from the register with optional callback logging"""
        _LOGGER.debug("RT: Reading from register - block=%s, addr=%s (0x%s), size=%s, type=%s",
                     self.block_name, self.addr, hex(self.addr), self.reg_size,
                     "HOLDING" if self.reg_type == 0 else "INPUT")
        values = self.slave.get_values(self.block_name, self.addr, self.reg_size)
        _LOGGER.debug("RT: Register read completed - block=%s, addr=%s (0x%s), values=%s",
                     self.block_name, self.addr, hex(self.addr), values)
        if self.read_callback:
            self.read_callback(self.addr, values)
        return values
