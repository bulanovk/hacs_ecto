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
        _LOGGER.debug("Setting raw value: block=%s, addr=%s, value=%s",
                     self.block_name, hex(self.addr), raw_value)
        self.slave.set_values(self.block_name, self.addr, raw_value)
        _LOGGER.debug("Value set successfully: block=%s", self.block_name)

    def get_values(self):
        """Get values from the register with optional callback logging"""
        values = self.slave.get_values(self.block_name, self.addr, self.reg_size)
        if self.read_callback:
            self.read_callback(self.addr, values)
        return values
