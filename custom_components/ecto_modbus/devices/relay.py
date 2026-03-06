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
        """Set relay channel state per Modbus protocol section 4.2.

        Register 0x10 format (16-bit):
        - MSB byte (bits 15-8): CHN 0-7, BIT_NO = CHN_NO % 8
        - LSB byte (bits 7-0): CHN 8-9, BIT_NO = CHN_NO % 8

        Direct bit mapping: Channel N → Bit (N % 8) in byte (N / 8)
        """
        _LOGGER.debug("set_switch_state called: channel=%s, state=%s, "
                      "current_states=%s", num, state, self.channels)

        if state != self.channels[num]:
            _LOGGER.debug("Toggle relay channel %s to %s", num, state)
            state_value = 1 if state else 0
            self.channels[num] = state_value

            # Calculate MSB byte (channels 0-7): direct bit mapping
            msb = 0
            for i in range(8):
                if self.channels[i]:
                    msb |= (1 << i)  # Channel i → Bit i

            # Calculate LSB byte (channels 8-9): direct bit mapping
            lsb = 0
            if self.channels[8]:
                lsb |= (1 << 0)  # Channel 8 → Bit 0
            if self.channels[9]:
                lsb |= (1 << 1)  # Channel 9 → Bit 1

            final_value = (msb << 8) | lsb
            _LOGGER.debug("Calculated register value: channels=%s, msb=0x%02X, lsb=0x%02X, value=0x%04X",
                          self.channels, msb, lsb, final_value)
            self.registers[0x10].set_raw_value([final_value])
        else:
            _LOGGER.debug("Relay channel %s already in state %s, skipping", num, state)

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

    def sync_channels_from_register(self):
        """Sync channel states from the actual Modbus register value.

        Reads the current value from register 0x10, parses channel states,
        and triggers callbacks for any changed channels.

        Returns:
            bool: True if any channel state changed
        """
        values = self.registers[0x10].get_values()
        _LOGGER.debug("sync_channels_from_register: addr=%s, values=%s, type=%s",
                     self.addr, values, type(values))
        if not values:
            _LOGGER.warning("sync_channels_from_register: No values returned for addr=%s", self.addr)
            return False

        value = values[0]
        _LOGGER.debug("sync_channels_from_register: addr=%s, register_value=%s (0x%04X), current_channels=%s",
                     self.addr, value, value, self.channels)
        changed = False

        # Parse MSB byte (channels 0-7): BIT_NO = CHN_NO % 8
        msb = (value >> 8) & 0xFF
        for i in range(8):
            new_state = (msb >> i) & 1  # Direct: Channel i → Bit i

            if self.channels[i] != new_state:
                self.channels[i] = new_state
                changed = True
                _LOGGER.info("Channel %d changed to %d (detected via sync)", i, new_state)
                if i in self._state_change_callbacks:
                    _LOGGER.debug("Calling callback for channel %d, callback=%s", i, self._state_change_callbacks[i])
                    self._state_change_callbacks[i](i, new_state)
                else:
                    _LOGGER.warning("No callback registered for channel %d, registered channels: %s",
                                   i, list(self._state_change_callbacks.keys()))

        # Parse LSB byte (channels 8-9)
        lsb = value & 0xFF
        for i in range(2):
            channel = 8 + i
            new_state = (lsb >> i) & 1

            if self.channels[channel] != new_state:
                self.channels[channel] = new_state
                changed = True
                _LOGGER.info("Channel %d changed to %d (detected via sync)", channel, new_state)
                if channel in self._state_change_callbacks:
                    _LOGGER.debug("Calling callback for channel %d, callback=%s", channel, self._state_change_callbacks[channel])
                    self._state_change_callbacks[channel](channel, new_state)
                else:
                    _LOGGER.warning("No callback registered for channel %d, registered channels: %s",
                                   channel, list(self._state_change_callbacks.keys()))

        _LOGGER.debug("sync_channels_from_register complete: addr=%s, changed=%s, channels=%s",
                     self.addr, changed, self.channels)
        return changed

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

        # Parse MSB byte (channels 0-7): BIT_NO = CHN_NO % 8
        msb = (value >> 8) & 0xFF
        for i in range(8):
            new_state = (msb >> i) & 1  # Direct: Channel i → Bit i

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
