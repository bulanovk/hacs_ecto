import logging

from .base import EctoDevice
import modbus_tk.defines as cst
from ..transport.modBusRTU import ModBusRegisterSensor
from modbus_tk.modbus_rtu import RtuServer

_LOGGER = logging.getLogger(__name__)


class EctoRelay10CH(EctoDevice):
    """10-channel relay module with timer functionality."""
    DEVICE_TYPE = 0xC1
    CHANNEL_COUNT = 10

    def __init__(self, config, server: RtuServer):
        super().__init__(config, server)
        _LOGGER.debug("Initializing EctoRelay10CH: addr=%s", self.addr)

        # State register at 0x0010 (HOLDING, RW) - 16-bit bitfield
        self.registers[0x10] = ModBusRegisterSensor(
            self.slave, cst.HOLDING_REGISTERS, 0x10, 1
        )

        # Timer registers at 0x0020-0x0029 (HOLDING, RW)
        self.registers[0x20] = ModBusRegisterSensor(
            self.slave, cst.HOLDING_REGISTERS, 0x20, 10
        )

        # Track channel states (0-9)
        self.channels = [0] * 10

        # Track timer values (0-9)
        self.timers = [0] * 10

        # Callbacks for state changes (to notify HA entities) - one per channel
        self._state_change_callbacks = {}

        _LOGGER.info("EctoRelay10CH initialized: addr=%s, channels=%s",
                     self.addr, self.CHANNEL_COUNT)

    def set_switch_state(self, num, state):
        """Set relay channel state using same bit mapping as binary sensor.

        Bit mapping:
        - Channels 0-7 in MSB byte (bits 15-8)
        - Channels 8-9 in LSB byte (bits 7-0)
        """
        original_num = num
        num = 7 - num  # Same reversal as binary sensor

        _LOGGER.debug("set_switch_state called: channel=%s (mapped=%s), state=%s, "
                      "current_states=%s", original_num, num, state, self.channels)

        if state != self.channels[original_num]:
            _LOGGER.debug("Toggle relay channel %s (channel %s) to %s",
                          num + 1, original_num, state)
            state_value = 1 if state else 0
            self.channels[original_num] = state_value

            # Calculate bit pattern for channels 0-7 (in MSB)
            value = 0
            for i in range(8):
                value = (value << 1) + self.channels[7 - i]

            # Add channels 8-9 (in LSB)
            lsb = 0
            if self.channels[8]:
                lsb |= 0x01
            if self.channels[9]:
                lsb |= 0x02

            final_value = (value << 8) | lsb
            _LOGGER.debug("Calculated register value: channels=%s, value=%s",
                          self.channels, hex(final_value))
            self.registers[0x10].set_raw_value([final_value])
        else:
            _LOGGER.debug("Relay channel %s (channel %s) already in state %s, "
                          "skipping", num + 1, original_num, state)

    def set_timer(self, channel, initial_state, timeout_seconds):
        """Set timer for relay channel.

        Args:
            channel: Channel number (0-9)
            initial_state: True for ON, False for OFF
            timeout_seconds: Timeout in seconds (will be converted to 500ms units)

        Timer format:
            Bit 15 = initial state (1=ON, 0=OFF)
            Bits 14-0 = timeout in 500ms units
        """
        if not 0 <= channel < self.CHANNEL_COUNT:
            _LOGGER.error("Invalid channel %s for set_timer (must be 0-9)", channel)
            return

        # Convert timeout to 500ms units
        timeout_units = int(timeout_seconds * 2)

        # Bit 15 = initial state, bits 14-0 = timeout
        timer_value = (1 << 15) if initial_state else 0
        timer_value |= (timeout_units & 0x7FFF)

        self.timers[channel] = timer_value

        # Build the full 10-register array
        timer_values = [self.timers[i] for i in range(10)]
        self.registers[0x20].set_raw_value(timer_values)

        _LOGGER.debug("Set timer for channel %s: initial_state=%s, timeout=%ss, "
                      "value=%s", channel, initial_state, timeout_seconds,
                      hex(timer_value))

    def get_channel_state(self, channel):
        """Get current state of a channel.

        Args:
            channel: Channel number (0-9)

        Returns:
            int: 1 for ON, 0 for OFF, None if invalid channel
        """
        if 0 <= channel < self.CHANNEL_COUNT:
            return self.channels[channel]
        return None

    def get_timer(self, channel):
        """Get current timer value for a channel.

        Args:
            channel: Channel number (0-9)

        Returns:
            int: Timer register value, None if invalid channel
        """
        if 0 <= channel < self.CHANNEL_COUNT:
            return self.timers[channel]
        return None

    def set_state_change_callback(self, channel, callback):
        """Set callback to be called when a specific channel state changes via Modbus.

        Args:
            channel: Channel number (0-9)
            callback: Function taking (channel, state) arguments
        """
        if 0 <= channel < self.CHANNEL_COUNT:
            self._state_change_callbacks[channel] = callback
            _LOGGER.debug("State change callback set for relay addr=%s, channel=%s",
                         self.addr, channel)

    def on_register_write(self, reg_addr, values):
        """Handle external Modbus write to holding registers.

        This is called when an external Modbus master writes to our registers.
        We need to parse the value and update our internal state accordingly.

        Args:
            reg_addr: Register address that was written
            values: List of values written
        """
        if reg_addr != 0x10 or not values:
            _LOGGER.debug("Ignoring write to register 0x%s", hex(reg_addr))
            return

        value = values[0]
        _LOGGER.info("External Modbus write to register 0x10: addr=%s, value=%s",
                     self.addr, hex(value))

        # Parse MSB byte (channels 0-7, reversed bit order)
        msb = (value >> 8) & 0xFF
        for i in range(8):
            # Channel i corresponds to bit (7-i) in MSB
            bit_pos = 7 - i
            new_state = (msb >> bit_pos) & 1

            if self.channels[i] != new_state:
                self.channels[i] = new_state
                _LOGGER.debug("Channel %d changed to %d via Modbus write", i, new_state)
                if i in self._state_change_callbacks:
                    self._state_change_callbacks[i](i, new_state)

        # Parse LSB byte (channels 8-9)
        lsb = value & 0xFF
        for i in range(2):
            channel = 8 + i
            new_state = (lsb >> i) & 1

            if self.channels[channel] != new_state:
                self.channels[channel] = new_state
                _LOGGER.debug("Channel %d changed to %d via Modbus write", channel, new_state)
                if channel in self._state_change_callbacks:
                    self._state_change_callbacks[channel](channel, new_state)

        _LOGGER.debug("Channel states after Modbus write: %s", self.channels)
