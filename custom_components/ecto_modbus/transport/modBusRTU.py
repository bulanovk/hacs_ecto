from modbus_tk.modbus import Slave


class ModBusRegisterSensor:

    def __init__(self, slave: Slave, reg_type: int, addr: int, reg_size: int):
        self.block_name = "val-x" + str(addr)
        self.addr = addr
        slave.add_block(self.block_name, reg_type, addr, reg_size)
        self.slave = slave

    def set_raw_value(self, raw_value):
        self.slave.set_values(self.block_name, self.addr, raw_value)
