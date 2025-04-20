#!/usr/bin/env python
import logging
import sys
import asyncio
import getopt
import struct
import sys
import threading
import traceback

from modbus_tk import modbus_rtu, utils, hooks
from modbus_tk.modbus_rtu import RtuServer
import modbus_tk.defines as cst

from modbus_tk.modbus import Slave
from serial import rs485

logger = utils.create_logger(name="console", level=logging.DEBUG, record_format="%(message)s")


class ModBusRegisterSensor:

    def __init__(self, slave: Slave, reg_type: int, addr: int, reg_size: int):
        self.block_name = "val-x" + str(addr)
        self.addr = addr
        slave.add_block(self.block_name, reg_type, addr, reg_size)
        self.slave = slave

    def set_raw_value(self, raw_value):
        logger.error("RAV=%s",raw_value)
        self.slave.set_values(self.block_name, self.addr, raw_value)


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


class EctoCH10BinarySensor(EctoDevice):
    """10-канальный бинарный датчик"""
    DEVICE_TYPE = 0x5908
    CHANNEL_COUNT = 8

    def __init__(self, config, server: RtuServer):
        super().__init__(config, server)
        reg = ModBusRegisterSensor(self.slave, cst.READ_INPUT_REGISTERS, 0x10, 1)
        self.registers[0x10] = reg
        self.switch = [0, 0, 0, 0, 0, 0, 0, 0]

    def set_switch_state(self, num, state):
        # with self.lock:
        num = 7 - num
        if state != self.switch[num]:
            value = 0
            state_value = 0
            if state:
                state_value = 1
            self.switch[num] = state_value
            for a in self.switch:
                value = (value << 1) + a
            self.set_value(value << 8)

    def set_value(self, value):
        self.registers[0x10].set_raw_value([value])


def on_error(data):
    _, ex, request_pdu = data
    print(''.join(traceback.TracebackException.from_exception(ex).format()))
    logger.error("pdu=%s", request_pdu)


def main() -> int | None:
    hooks.install_hook("modbus.Databank.on_error", on_error)
    port485_main = rs485.RS485("/dev/ttyACM0", baudrate=19200, inter_byte_timeout=0.002)
    server19200 = modbus_rtu.RtuServer(port485_main, interchar_multiplier=1, error_on_missing_slave=False)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        server19200.start()
        conf = {'addr': 4}
        EctoCH10BinarySensor(conf, server19200)
        loop.run_forever()
    finally:
        server19200.stop()

    return 0


if __name__ == '__main__':
    sys.exit(main())  # next section explains the use of sys.exit
