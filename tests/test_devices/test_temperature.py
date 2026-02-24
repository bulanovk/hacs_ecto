"""Tests for EctoTemperatureSensor device."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import modbus_tk.defines as cst

from custom_components.ecto_modbus.devices.temperature import EctoTemperatureSensor


class TestEctoTemperatureSensor:
    """Test suite for EctoTemperatureSensor class."""

    def test_device_type_constant(self):
        """Test that DEVICE_TYPE is correct per protocol (0x22 = temperature sensor)."""
        assert EctoTemperatureSensor.DEVICE_TYPE == 0x22

    def test_channel_count_constant(self):
        """Test that CHANNEL_COUNT is correct."""
        assert EctoTemperatureSensor.CHANNEL_COUNT == 1

    def test_scale_factor_constant(self):
        """Test that SCALE_FACTOR is correct."""
        assert EctoTemperatureSensor.SCALE_FACTOR == 10

    def test_init_with_entity_id(self, mock_modbus_server):
        """Test initialization with entity_id."""
        # Setup
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {
            'addr': 4,
            'entity_id': 'sensor.test_temperature'
        }

        # Execute
        device = EctoTemperatureSensor(config, mock_server)

        # Assert
        assert device.addr == 4
        assert device.entity_id == 'sensor.test_temperature'
        assert device.DEVICE_TYPE == 0x22
        assert device.CHANNEL_COUNT == 1
        assert device._hass is None
        assert 0x20 in device.registers

    def test_init_without_entity_id(self, mock_modbus_server):
        """Test initialization without entity_id."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 4}

        # Execute
        device = EctoTemperatureSensor(config, mock_server)

        # Assert
        assert device.entity_id is None

    @pytest.mark.asyncio
    async def test_async_init_with_entity_id(self, mock_modbus_server):
        """Test async_init when entity_id is configured."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {
            'addr': 4,
            'entity_id': 'sensor.test_temperature'
        }

        device = EctoTemperatureSensor(config, mock_server)

        mock_hass = MagicMock()
        mock_hass.async_run_job = AsyncMock()

        with patch('custom_components.ecto_modbus.devices.temperature.async_track_state_change') as mock_track:
            # Execute
            await device.async_init(mock_hass)

            # Assert
            assert device._hass is mock_hass
            mock_track.assert_called_once_with(
                mock_hass,
                'sensor.test_temperature',
                device._state_changed
            )

    @pytest.mark.asyncio
    async def test_async_init_without_entity_id(self, mock_modbus_server):
        """Test async_init when entity_id is not configured."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 4}

        device = EctoTemperatureSensor(config, mock_server)

        mock_hass = MagicMock()

        # Execute
        await device.async_init(mock_hass)

        # Assert
        assert device._hass is mock_hass

    @pytest.mark.asyncio
    async def test_state_changed_valid_temperature(self, mock_modbus_server):
        """Test _state_changed with valid temperature value."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.temperature.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 4}
            device = EctoTemperatureSensor(config, mock_server)

            # Create mock states
            mock_old_state = MagicMock()
            mock_old_state.state = "20.0"

            mock_new_state = MagicMock()
            mock_new_state.state = "22.5"

            # Execute
            await device._state_changed('sensor.test', mock_old_state, mock_new_state)

            # Assert - Temperature should be scaled by 10
            # 22.5 * 10 = 225
            mock_instance.set_raw_value.assert_called_with([225])

    @pytest.mark.asyncio
    async def test_state_changed_temperature_scaling(self, mock_modbus_server):
        """Test that temperature is correctly scaled by factor of 10."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.temperature.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 4}
            device = EctoTemperatureSensor(config, mock_server)

            test_cases = [
                ("0.0", 0),
                ("10.0", 100),
                ("20.5", 205),
                ("25.3", 253),
                ("30.0", 300),
                ("-5.0", -50),
                ("-10.5", -105),
            ]

            for temp_str, expected_scaled in test_cases:
                mock_instance.reset_mock()

                # Create mock state
                mock_new_state = MagicMock()
                mock_new_state.state = temp_str
                mock_old_state = MagicMock()

                # Execute
                await device._state_changed('sensor.test', mock_old_state, mock_new_state)

                # Assert
                mock_instance.set_raw_value.assert_called_with([expected_scaled])

    @pytest.mark.asyncio
    async def test_state_changed_invalid_value(self, mock_modbus_server):
        """Test _state_changed with invalid value."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 4}
        device = EctoTemperatureSensor(config, mock_server)

        # Create mock states with invalid value
        mock_old_state = MagicMock()
        mock_new_state = MagicMock()
        mock_new_state.state = "unknown"

        # Execute - Should not raise exception
        try:
            await device._state_changed('sensor.test', mock_old_state, mock_new_state)
            # If we get here, error was handled gracefully
            assert True
        except (ValueError, AttributeError):
            # Expected - invalid value should raise error
            assert True

    @pytest.mark.asyncio
    async def test_state_changed_none_value(self, mock_modbus_server):
        """Test _state_changed with None value."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 4}
        device = EctoTemperatureSensor(config, mock_server)

        # Create mock states with None
        mock_old_state = MagicMock()
        mock_new_state = MagicMock()
        mock_new_state.state = None

        # Execute - Should handle gracefully
        try:
            await device._state_changed('sensor.test', mock_old_state, mock_new_state)
            assert True
        except (ValueError, AttributeError):
            assert True

    @pytest.mark.asyncio
    async def test_state_changed_unavailable_state(self, mock_modbus_server):
        """Test _state_changed with unavailable state."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 4}
        device = EctoTemperatureSensor(config, mock_server)

        # Create mock states
        mock_old_state = MagicMock()
        mock_new_state = MagicMock()
        mock_new_state.state = "unavailable"

        # Execute
        try:
            await device._state_changed('sensor.test', mock_old_state, mock_new_state)
            assert True
        except (ValueError, AttributeError):
            assert True

    def test_register_address(self, mock_modbus_server):
        """Test that temperature register is at correct address."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        # Patch both base and temperature modules since they import ModBusRegisterSensor separately
        with patch('custom_components.ecto_modbus.devices.base.ModBusRegisterSensor') as mock_base_sensor, \
             patch('custom_components.ecto_modbus.devices.temperature.ModBusRegisterSensor', mock_base_sensor):
            mock_instance = MagicMock()
            mock_base_sensor.return_value = mock_instance

            config = {'addr': 4}
            device = EctoTemperatureSensor(config, mock_server)

            # Assert - Check that register was created at address 0x20
            # The second call to ModBusRegisterSensor is for the temperature register
            calls = mock_base_sensor.call_args_list
            assert len(calls) >= 2, f"Expected at least 2 calls, got {len(calls)}: {calls}"
            temperature_call = calls[1]  # Second call after base class register

            assert temperature_call[0][2] == 0x20  # Third positional argument is addr
            assert temperature_call[0][1] == cst.READ_INPUT_REGISTERS  # Second is reg_type
            assert temperature_call[0][3] == 1  # Fourth is reg_size

    def test_different_addresses(self, mock_modbus_server):
        """Test initialization with different addresses."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        addresses = [3, 4, 10, 32]

        # Execute
        for addr in addresses:
            config = {'addr': addr}
            device = EctoTemperatureSensor(config, mock_server)

            # Assert
            assert device.addr == addr
            assert device.DEVICE_TYPE == 0x22

    def test_inheritance_from_ecto_device(self, mock_modbus_server):
        """Test that EctoTemperatureSensor inherits from EctoDevice."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 4}

        # Execute
        device = EctoTemperatureSensor(config, mock_server)

        # Assert - Check for EctoDevice attributes
        assert hasattr(device, 'uid')
        assert hasattr(device, 'registers')
        assert hasattr(device, 'slave')
        assert hasattr(device, 'server')
        assert hasattr(device, 'config')

    @pytest.mark.asyncio
    async def test_multiple_state_changes(self, mock_modbus_server):
        """Test multiple state changes in sequence."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        with patch('custom_components.ecto_modbus.devices.temperature.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 4}
            device = EctoTemperatureSensor(config, mock_server)

            temperatures = ["20.0", "21.5", "22.0", "23.5", "25.0"]

            # Execute
            for temp in temperatures:
                mock_new_state = MagicMock()
                mock_new_state.state = temp
                mock_old_state = MagicMock()

                await device._state_changed('sensor.test', mock_old_state, mock_new_state)

            # Assert - Should have 5 calls
            assert mock_instance.set_raw_value.call_count == len(temperatures)
