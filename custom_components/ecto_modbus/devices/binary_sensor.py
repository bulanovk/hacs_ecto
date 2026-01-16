import logging

from .base import EctoDevice
import modbus_tk.defines as cst
from ..transport.modBusRTU import ModBusRegisterSensor
from modbus_tk.modbus_rtu import RtuServer

_LOGGER = logging.getLogger(__name__)


class EctoCH10BinarySensor(EctoDevice):
    """10-канальный бинарный датчик"""
    DEVICE_TYPE = 0x5908
    CHANNEL_COUNT = 8

    def __init__(self, config, server: RtuServer):
        super().__init__(config, server)
        _LOGGER.debug("Initializing EctoCH10BinarySensor: addr=%s", self.addr)
        reg = ModBusRegisterSensor(self.slave, cst.READ_INPUT_REGISTERS, 0x10, 1, read_callback=self._on_register_read)
        self.registers[0x10] = reg
        self.switch = [0, 0, 0, 0, 0, 0, 0, 0]
        _LOGGER.info("EctoCH10BinarySensor initialized: addr=%s, channels=%s",
                    self.addr, self.CHANNEL_COUNT)

    def set_switch_state(self, num, state):
        # with self.lock:
        original_num = num
        num = 7 - num
        _LOGGER.debug("set_switch_state called: channel=%s (mapped=%s), state=%s, current_states=%s",
                     original_num, num, state, self.switch)
        if state != self.switch[num]:
            _LOGGER.debug("Toggle switch %s (channel %s) to %s", num + 1, original_num, state)
            value = 0
            state_value = 0
            if state:
                state_value = 1
            self.switch[num] = state_value
            for a in self.switch:
                value = (value << 1) + a
            final_value = value << 8
            _LOGGER.debug("Calculated register value: switches=%s, value=%s",
                         self.switch, hex(final_value))
            self.set_value(final_value)
        else:
            _LOGGER.debug("Switch %s (channel %s) already in state %s, skipping",
                         num + 1, original_num, state)

    def set_value(self, value):
        _LOGGER.debug("Setting register 0x10 value: addr=%s, value=%s", self.addr, hex(value))
        self.registers[0x10].set_raw_value([value])
        _LOGGER.debug("Register 0x10 value set successfully: addr=%s", self.addr)

    def _on_register_read(self, addr, values):
        """Callback when register is read"""
        if addr == 0x10:
            _LOGGER.debug("Register 0x10 read: addr=%s, value=%s", self.addr, values)
