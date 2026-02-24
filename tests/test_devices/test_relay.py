"""Tests for EctoRelay10CH device."""
import pytest
from unittest.mock import MagicMock

from custom_components.ecto_modbus.devices.relay import EctoRelay10CH


class TestEctoRelay10CHConstants:
    """Test suite for EctoRelay10CH class constants."""

    def test_device_type_is_0xC1(self):
        """Test that DEVICE_TYPE is 0xC1."""
        assert EctoRelay10CH.DEVICE_TYPE == 0xC1

    def test_channel_count_is_10(self):
        """Test that CHANNEL_COUNT is 10."""
        assert EctoRelay10CH.CHANNEL_COUNT == 10


class TestEctoRelay10CHInit:
    """Test suite for EctoRelay10CH initialization."""

    def test_init_basic(self, mock_modbus_server):
        """Test basic initialization."""
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {'addr': 5}

        device = EctoRelay10CH(config, mock_server)

        assert device.addr == 5
        assert 0x10 in device.registers  # State register
        assert 0x20 in device.registers  # Timer registers
        assert len(device.channels) == 10
        assert len(device.timers) == 10

    def test_init_all_channels_off(self, mock_modbus_server):
        """Test that all channels are initialized to OFF."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        assert all(ch == 0 for ch in device.channels)

    def test_init_all_timers_zero(self, mock_modbus_server):
        """Test that all timers are initialized to 0."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        assert all(timer == 0 for timer in device.timers)

    def test_inheritance_from_ecto_device(self, mock_modbus_server):
        """Test that EctoRelay10CH inherits from EctoDevice."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        # Check for EctoDevice attributes
        assert hasattr(device, 'uid')
        assert hasattr(device, 'registers')
        assert hasattr(device, 'slave')
        assert hasattr(device, 'server')
        assert hasattr(device, 'config')
        assert hasattr(device, 'DEVICE_TYPE')

    def test_different_addresses(self, mock_modbus_server):
        """Test initialization with different addresses."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        addresses = [3, 4, 10, 32]

        for addr in addresses:
            config = {'addr': addr}
            device = EctoRelay10CH(config, mock_server)

            assert device.addr == addr
            assert device.DEVICE_TYPE == 0xC1

    def test_config_stored(self, mock_modbus_server):
        """Test that config is stored correctly."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {
            'addr': 5,
            'extra_param': 'test_value'
        }

        device = EctoRelay10CH(config, mock_server)

        assert device.config == config
        assert device.config['extra_param'] == 'test_value'


class TestEctoRelay10CHSetSwitchState:
    """Test suite for EctoRelay10CH set_switch_state method."""

    def test_set_switch_state_channel_0_on(self, mock_modbus_server):
        """Test setting channel 0 ON."""
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_switch_state(0, 1)

        assert device.channels[0] == 1

    def test_set_switch_state_channel_9_on(self, mock_modbus_server):
        """Test setting channel 9 ON (LSB byte)."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_switch_state(9, 1)

        assert device.channels[9] == 1

    def test_set_switch_state_all_channels(self, mock_modbus_server):
        """Test setting all 10 channels ON."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        for ch in range(10):
            device.set_switch_state(ch, 1)

        assert all(device.channels[ch] == 1 for ch in range(10))

    def test_set_switch_state_preserves_other_channels(self, mock_modbus_server):
        """Verify changing one channel doesn't affect others."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        # Set channel 0 ON
        device.set_switch_state(0, 1)
        assert device.channels[0] == 1

        # Set channel 5 ON
        device.set_switch_state(5, 1)
        assert device.channels[0] == 1  # Still ON
        assert device.channels[5] == 1

        # Set channel 0 OFF
        device.set_switch_state(0, 0)
        assert device.channels[0] == 0
        assert device.channels[5] == 1  # Still ON

    def test_set_switch_state_off(self, mock_modbus_server):
        """Test setting channel OFF after ON."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_switch_state(0, 1)
        assert device.channels[0] == 1

        device.set_switch_state(0, 0)
        assert device.channels[0] == 0

    def test_set_switch_state_channel_8_on(self, mock_modbus_server):
        """Test setting channel 8 ON (LSB byte, bit 0)."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_switch_state(8, 1)

        assert device.channels[8] == 1
        assert device.channels[9] == 0  # Should not affect channel 9


class TestEctoRelay10CHTimer:
    """Test suite for EctoRelay10CH timer functionality."""

    def test_set_timer_basic(self, mock_modbus_server):
        """Test setting timer without initial state."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_timer(0, False, 10)  # 10 seconds, initial OFF

        # 10 seconds = 20 units of 500ms
        # Bit 15 = 0 (initial OFF), bits 14-0 = 20
        expected_value = 20
        assert device.timers[0] == expected_value

    def test_set_timer_with_initial_state(self, mock_modbus_server):
        """Test timer with initial_state=True (bit 15 set)."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_timer(0, True, 10)  # 10 seconds, initial ON

        # 10 seconds = 20 units of 500ms
        # Bit 15 = 1 (initial ON), bits 14-0 = 20
        expected_value = (1 << 15) | 20
        assert device.timers[0] == expected_value

    def test_timer_value_calculation(self, mock_modbus_server):
        """Verify 500ms unit conversion: 10 seconds = 20 units."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        # 5 seconds = 10 units of 500ms
        device.set_timer(0, False, 5)
        assert device.timers[0] == 10

        # 1 second = 2 units
        device.set_timer(1, False, 1)
        assert device.timers[1] == 2

        # 0.5 seconds = 1 unit
        device.set_timer(2, False, 0.5)
        assert device.timers[2] == 1

    def test_set_timer_multiple_channels(self, mock_modbus_server):
        """Test setting timers on multiple channels."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_timer(0, False, 10)
        device.set_timer(5, True, 20)
        device.set_timer(9, False, 30)

        assert device.timers[0] == 20  # 10s * 2
        assert device.timers[5] == (1 << 15) | 40  # 20s * 2 with initial ON
        assert device.timers[9] == 60  # 30s * 2

    def test_set_timer_invalid_channel(self, mock_modbus_server):
        """Test that invalid channel is handled gracefully."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        # These should not raise exceptions
        device.set_timer(-1, False, 10)
        device.set_timer(10, False, 10)
        device.set_timer(100, False, 10)

        # No timer should be set for invalid channels
        assert all(t == 0 for t in device.timers)


class TestEctoRelay10CHHelpers:
    """Test suite for EctoRelay10CH helper methods."""

    def test_get_channel_state_valid(self, mock_modbus_server):
        """Test get_channel_state with valid channel."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_switch_state(0, 1)
        device.set_switch_state(5, 1)

        assert device.get_channel_state(0) == 1
        assert device.get_channel_state(5) == 1
        assert device.get_channel_state(9) == 0  # Not set

    def test_get_channel_state_invalid(self, mock_modbus_server):
        """Test get_channel_state with invalid channel."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        assert device.get_channel_state(-1) is None
        assert device.get_channel_state(10) is None
        assert device.get_channel_state(100) is None

    def test_get_timer_valid(self, mock_modbus_server):
        """Test get_timer with valid channel."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        device.set_timer(0, True, 15)

        assert device.get_timer(0) == (1 << 15) | 30  # 15s * 2 with initial ON

    def test_get_timer_invalid(self, mock_modbus_server):
        """Test get_timer with invalid channel."""
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}
        device = EctoRelay10CH(config, mock_server)

        assert device.get_timer(-1) is None
        assert device.get_timer(10) is None
        assert device.get_timer(100) is None
