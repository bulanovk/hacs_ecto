"""Integration tests for Ectocontrol Modbus Integration.

These tests use socat PTY to emulate serial ports for real hardware testing.
"""
import pytest
import time
from unittest.mock import MagicMock

integration_marker = pytest.mark.integration


class TestIntegrationWithPTY:
    """Integration tests using pseudo-terminal pairs."""

    @pytest.mark.asyncio
    @integration_marker
    async def test_binary_sensor_with_pty(self, modbus_server_with_pty):
        """Test binary sensor device with emulated serial port."""
        from custom_components.ecto_modbus.devices.binary_sensor import EctoCH10BinarySensor

        # Setup
        server, slave_pty = modbus_server_with_pty

        # Create device
        config = {'addr': 3}
        device = EctoCH10BinarySensor(config, server)

        # Assert - Device initialized correctly
        assert device.addr == 3
        assert device.DEVICE_TYPE == 0x5908
        assert device.CHANNEL_COUNT == 8
        assert all(state == 0 for state in device.switch)

        # Test turning on channel 0
        device.set_switch_state(0, 1)
        assert device.switch[7] == 1  # Channel 0 maps to index 7

        # Test turning on multiple channels
        device.set_switch_state(1, 1)
        device.set_switch_state(2, 1)
        assert device.switch[6] == 1  # Channel 1 maps to index 6
        assert device.switch[5] == 1  # Channel 2 maps to index 5

        # Test turning off
        device.set_switch_state(0, 0)
        assert device.switch[7] == 0

    @pytest.mark.asyncio
    @integration_marker
    async def test_temperature_sensor_with_pty(self, modbus_server_with_pty):
        """Test temperature sensor with emulated serial port."""
        from custom_components.ecto_modbus.devices.temperature import EctoTemperatureSensor

        # Setup
        server, slave_pty = modbus_server_with_pty

        # Create device
        config = {'addr': 4, 'entity_id': 'sensor.test_temp'}
        device = EctoTemperatureSensor(config, server)

        # Assert - Device initialized correctly
        assert device.addr == 4
        assert device.DEVICE_TYPE == 0x2201
        assert device.entity_id == 'sensor.test_temp'
        assert 0x20 in device.registers

    @pytest.mark.asyncio
    @integration_marker
    async def test_relay_with_pty(self, modbus_server_with_pty):
        """Test relay device with emulated serial port."""
        from custom_components.ecto_modbus.devices.relay import EctoRelay8CH

        # Setup
        server, slave_pty = modbus_server_with_pty

        # Create device
        config = {'addr': 5}
        device = EctoRelay8CH(config, server)

        # Assert - Device initialized correctly
        assert device.addr == 5
        assert device.DEVICE_TYPE == 0xC108

    @pytest.mark.asyncio
    @integration_marker
    async def test_multiple_devices_same_server(self, modbus_server_with_pty):
        """Test multiple devices on the same Modbus server."""
        from custom_components.ecto_modbus.devices.binary_sensor import EctoCH10BinarySensor
        from custom_components.ecto_modbus.devices.temperature import EctoTemperatureSensor
        from custom_components.ecto_modbus.devices.relay import EctoRelay8CH

        # Setup
        server, slave_pty = modbus_server_with_pty

        # Create multiple devices
        binary_sensor = EctoCH10BinarySensor({'addr': 3}, server)
        temp_sensor = EctoTemperatureSensor({'addr': 4, 'entity_id': 'sensor.test'}, server)
        relay = EctoRelay8CH({'addr': 5}, server)

        # Assert - All devices initialized
        assert binary_sensor.addr == 3
        assert temp_sensor.addr == 4
        assert relay.addr == 5

        # Test that devices can operate independently
        binary_sensor.set_switch_state(0, 1)
        assert binary_sensor.switch[7] == 1

    @pytest.mark.asyncio
    @integration_marker
    async def test_device_address_range(self, modbus_server_with_pty):
        """Test devices across valid address range (3-32)."""
        from custom_components.ecto_modbus.devices.binary_sensor import EctoCH10BinarySensor

        # Setup
        server, slave_pty = modbus_server_with_pty

        # Test boundary addresses
        addresses_to_test = [3, 4, 10, 20, 31, 32]

        for addr in addresses_to_test:
            device = EctoCH10BinarySensor({'addr': addr}, server)
            assert device.addr == addr
            assert device.uid == 0x800000 + (addr - 3)

    @pytest.mark.asyncio
    @integration_marker
    async def test_switch_state_transitions(self, modbus_server_with_pty):
        """Test switch state transitions."""
        from custom_components.ecto_modbus.devices.binary_sensor import EctoCH10BinarySensor

        # Setup
        server, slave_pty = modbus_server_with_pty
        device = EctoCH10BinarySensor({'addr': 3}, server)

        # Test all channels
        for channel in range(8):
            # Turn on
            device.set_switch_state(channel, 1)
            expected_index = 7 - channel
            assert device.switch[expected_index] == 1, \
                f"Channel {channel} should set index {expected_index} to 1"

            # Turn off
            device.set_switch_state(channel, 0)
            assert device.switch[expected_index] == 0, \
                f"Channel {channel} should set index {expected_index} to 0"

    @pytest.mark.asyncio
    @integration_marker
    async def test_register_creation(self, modbus_server_with_pty):
        """Test that registers are created correctly."""
        from custom_components.ecto_modbus.devices.binary_sensor import EctoCH10BinarySensor
        from custom_components.ecto_modbus.devices.temperature import EctoTemperatureSensor

        # Setup
        server, slave_pty = modbus_server_with_pty

        # Test binary sensor registers
        binary_sensor = EctoCH10BinarySensor({'addr': 3}, server)
        assert 0 in binary_sensor.registers  # UID register from base class
        assert 0x10 in binary_sensor.registers  # Switch state register

        # Test temperature sensor registers
        temp_sensor = EctoTemperatureSensor({'addr': 4}, server)
        assert 0 in temp_sensor.registers  # UID register from base class
        assert 0x20 in temp_sensor.registers  # Temperature register


class TestIntegrationWithoutPTY:
    """Integration tests that work without PTY (mocked hardware)."""

    @pytest.mark.asyncio
    async def test_hass_integration_setup(self, hass):
        """Test Home Assistant integration setup."""
        from custom_components.ecto_modbus import async_setup
        from unittest.mock import patch, MagicMock

        config = {
            'ecto_modbus': {
                'port': '/dev/ttyUSB0',
                'port_type': 'rs485',
                'baudrate': 19200,
                'devices': [
                    {'type': 'binary_sensor_10ch', 'addr': 3}
                ]
            }
        }

        with patch('custom_components.ecto_modbus.rs485.RS485') as mock_rs485, \
             patch('custom_components.ecto_modbus.modbus_rtu.RtuServer') as mock_server_class, \
             patch('custom_components.ecto_modbus.load_platform') as mock_load_platform:

            mock_server = MagicMock()
            mock_server.start = MagicMock()
            mock_server_class.return_value = mock_server

            mock_rs485_instance = MagicMock()
            mock_rs485.return_value = mock_rs485_instance

            # Execute
            result = await async_setup(hass, config)

            # Assert
            assert result is True
            assert 'ecto_modbus' in hass.data
            assert 'devices' in hass.data['ecto_modbus']
            assert 'rtu' in hass.data['ecto_modbus']
            mock_load_platform.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_entity_integration(self, hass):
        """Test switch entity with mock device."""
        from custom_components.ecto_modbus.switch import EctoChannelSwitch

        # Setup
        mock_device = MagicMock()
        mock_device.addr = 3
        switch = EctoChannelSwitch(mock_device, channel=0)

        # Test properties
        assert switch.unique_id == "ecto_3_ch0"
        assert switch.name == "Device 3 Ch.1"
        assert switch.is_on is False

        # Test turning on
        await switch.async_turn_on()
        assert switch.is_on is True
        mock_device.set_switch_state.assert_called_with(0, 1)

        # Test turning off
        await switch.async_turn_off()
        assert switch.is_on is False
        mock_device.set_switch_state.assert_called_with(0, 0)
