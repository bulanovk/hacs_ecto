import logging

from .base import EctoDevice
import modbus_tk.defines as cst
from ..transport.modBusRTU import ModBusRegisterSensor
from modbus_tk.modbus_rtu import RtuServer

LOGGER = logging.getLogger(__name__)


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
        if state != self.switch[num]:
            LOGGER.warning("Toggle switch " + str(num + 1) + " to " + str(state))
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
