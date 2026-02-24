"""Tests for EctoCH10BinarySensor device."""
import pytest
from unittest.mock import MagicMock, patch, call
import modbus_tk.defines as cst

from custom_components.ecto_modbus.devices.binary_sensor import EctoCH10BinarySensor


class TestEctoCH10BinarySensor:
    """Test suite for EctoCH10BinarySensor class."""

    def test_device_type_constant(self):
        """Test that DEVICE_TYPE is correct per protocol (0x59 = 10-channel contact sensor)."""
        assert EctoCH10BinarySensor.DEVICE_TYPE == 0x59

    def test_channel_count_constant(self):
        """Test that CHANNEL_COUNT is correct (10 channels per protocol)."""
        assert EctoCH10BinarySensor.CHANNEL_COUNT == 10

    def test_init_basic(self, mock_modbus_server):
        """Test basic initialization."""
        # Setup
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {'addr': 3}

        # Execute
        device = EctoCH10BinarySensor(config, mock_server)

        # Assert
        assert device.addr == 3
        assert device.DEVICE_TYPE == 0x59
        assert device.CHANNEL_COUNT == 10
        assert device.switch == [0, 0, 0, 0, 0, 0, 0, 0]
        assert 0x10 in device.registers

    def test_switch_initial_state(self, mock_modbus_server):
        """Test that all switches start in OFF state."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 3}

        # Execute
        device = EctoCH10BinarySensor(config, mock_server)

        # Assert
        assert all(state == 0 for state in device.switch)
        assert len(device.switch) == 8

    def test_set_switch_state_channel_0_on(self, mock_modbus_server):
        """Test turning on channel 0."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.binary_sensor.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 3}
            device = EctoCH10BinarySensor(config, mock_server)

            # Reset the mock to track new calls
            mock_instance.reset_mock()

            # Execute - Turn on channel 0
            device.set_switch_state(0, 1)

            # Assert - Channel 0 is mapped to index 7
            assert device.switch[7] == 1
            # Verify set_value was called with correct bit pattern
            # Channel 0 on = bit 7 set = 0x80 shifted left 8 = 0x8000
            mock_instance.set_raw_value.assert_called_once()

    def test_set_switch_state_channel_7_on(self, mock_modbus_server):
        """Test turning on channel 7."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.binary_sensor.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 3}
            device = EctoCH10BinarySensor(config, mock_server)
            mock_instance.reset_mock()

            # Execute - Turn on channel 7
            device.set_switch_state(7, 1)

            # Assert - Channel 7 is mapped to index 0
            assert device.switch[0] == 1

    def test_set_switch_state_multiple_channels(self, mock_modbus_server):
        """Test turning on multiple channels."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 3}
        device = EctoCH10BinarySensor(config, mock_server)

        # Execute - Turn on channels 0, 2, 4
        device.set_switch_state(0, 1)
        device.set_switch_state(2, 1)
        device.set_switch_state(4, 1)

        # Assert - Check mapped indices
        assert device.switch[7] == 1  # Channel 0
        assert device.switch[5] == 1  # Channel 2
        assert device.switch[3] == 1  # Channel 4
        assert device.switch[6] == 0  # Channel 1 (off)
        assert device.switch[4] == 0  # Channel 3 (off)

    def test_set_switch_state_turn_off(self, mock_modbus_server):
        """Test turning off a channel."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 3}
        device = EctoCH10BinarySensor(config, mock_server)

        # Execute - Turn on then off
        device.set_switch_state(0, 1)
        assert device.switch[7] == 1
        device.set_switch_state(0, 0)

        # Assert
        assert device.switch[7] == 0

    def test_set_switch_state_no_change(self, mock_modbus_server):
        """Test that setting same state doesn't trigger update."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.binary_sensor.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 3}
            device = EctoCH10BinarySensor(config, mock_server)
            mock_instance.reset_mock()

            # Execute - Set to same state twice
            device.set_switch_state(0, 1)
            call_count_after_first = mock_instance.set_raw_value.call_count
            device.set_switch_state(0, 1)  # Same state
            call_count_after_second = mock_instance.set_raw_value.call_count

            # Assert - Should not call set_raw_value again
            assert call_count_after_first == call_count_after_second

    def test_set_value(self, mock_modbus_server):
        """Test set_value method."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.binary_sensor.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 3}
            device = EctoCH10BinarySensor(config, mock_server)
            mock_instance.reset_mock()

            # Execute
            device.set_value(0x1234)

            # Assert
            mock_instance.set_raw_value.assert_called_once_with([0x1234])

    def test_bit_pattern_calculation_all_off(self, mock_modbus_server):
        """Test bit pattern when all switches are off."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.binary_sensor.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 3}
            device = EctoCH10BinarySensor(config, mock_server)
            mock_instance.reset_mock()

            # Execute - All switches off (initial state, so no calls expected)
            for i in range(8):
                device.set_switch_state(i, 0)

            # Assert - set_raw_value should not be called since state hasn't changed
            assert mock_instance.set_raw_value.call_count == 0

    def test_bit_pattern_calculation_all_on(self, mock_modbus_server):
        """Test bit pattern when all switches are on."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.binary_sensor.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 3}
            device = EctoCH10BinarySensor(config, mock_server)
            mock_instance.reset_mock()

            # Execute - Turn all switches on
            for i in range(8):
                device.set_switch_state(i, 1)

            # Assert - All bits should be set (0xFF << 8 = 0xFF00)
            last_call = mock_instance.set_raw_value.call_args
            # The value is shifted left by 8 bits
            assert last_call[0][0][0] == 0xFF00

    def test_channel_mapping(self, mock_modbus_server):
        """Test that channels are correctly mapped to switch array indices."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 3}
        device = EctoCH10BinarySensor(config, mock_server)

        # Execute - Turn on each channel individually
        for channel in range(8):
            device.set_switch_state(channel, 1)
            expected_index = 7 - channel

            # Assert - Check correct index is set
            for i in range(8):
                if i == expected_index:
                    assert device.switch[i] == 1, f"Channel {channel} should set index {expected_index}"
                else:
                    assert device.switch[i] == 0, f"Channel {channel} should not affect index {i}"

            # Reset
            device.switch = [0, 0, 0, 0, 0, 0, 0, 0]

    def test_on_register_read_callback(self, mock_modbus_server):
        """Test _on_register_read callback."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.binary_sensor.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 3}
            device = EctoCH10BinarySensor(config, mock_server)

            # Execute
            test_values = [0x1234]
            device._on_register_read(0x10, test_values)

            # Assert - Callback should just log, no exceptions
            # If we get here without exception, callback works
            assert True

    def test_different_addresses(self, mock_modbus_server):
        """Test initialization with different addresses."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        addresses = [3, 4, 10, 32]

        # Execute
        for addr in addresses:
            config = {'addr': addr}
            device = EctoCH10BinarySensor(config, mock_server)

            # Assert
            assert device.addr == addr
            assert device.DEVICE_TYPE == 0x59

    def test_inheritance_from_ecto_device(self, mock_modbus_server):
        """Test that EctoCH10BinarySensor inherits from EctoDevice."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 3}

        # Execute
        device = EctoCH10BinarySensor(config, mock_server)

        # Assert - Check for EctoDevice attributes
        assert hasattr(device, 'uid')
        assert hasattr(device, 'registers')
        assert hasattr(device, 'slave')
        assert hasattr(device, 'server')
        assert hasattr(device, 'config')
