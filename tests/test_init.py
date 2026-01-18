"""Tests for main integration setup."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import voluptuous as vol

from custom_components.ecto_modbus import (
    CONFIG_SCHEMA,
    async_setup,
    async_unload_entry,
    DEVICE_CLASSES,
    DOMAIN
)
from custom_components.ecto_modbus.const import (
    PORT_TYPE_RS485,
    PORT_TYPE_SERIAL,
    DEFAULT_BAUDRATE
)


class TestConfigSchema:
    """Test suite for configuration schema validation."""

    def test_valid_config_minimal(self):
        """Test valid minimal configuration."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'devices': [
                    {'type': 'binary_sensor_10ch', 'addr': 3}
                ]
            }
        }

        # Execute & Assert - Should not raise
        CONFIG_SCHEMA(config)

    def test_valid_config_full(self):
        """Test valid full configuration."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyACM0',
                'port_type': PORT_TYPE_RS485,
                'baudrate': 19200,
                'devices': [
                    {
                        'type': 'temperature_sensor',
                        'addr': 4,
                        'entity_id': 'sensor.test_temp'
                    },
                    {
                        'type': 'binary_sensor_10ch',
                        'addr': 3
                    },
                    {
                        'type': 'relay_8ch',
                        'addr': 5
                    }
                ]
            }
        }

        # Execute & Assert
        CONFIG_SCHEMA(config)

    def test_valid_config_serial_port(self):
        """Test configuration with serial port type."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'port_type': PORT_TYPE_SERIAL,
                'devices': [
                    {'type': 'binary_sensor_10ch', 'addr': 3}
                ]
            }
        }

        # Execute & Assert
        CONFIG_SCHEMA(config)

    def test_missing_port(self):
        """Test that missing port raises validation error."""
        # Setup
        config = {
            DOMAIN: {
                'devices': [
                    {'type': 'binary_sensor_10ch', 'addr': 3}
                ]
            }
        }

        # Execute & Assert - Should raise
        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)

    def test_missing_devices(self):
        """Test that missing devices raises validation error."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0'
            }
        }

        # Execute & Assert - Should raise
        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)

    def test_invalid_device_type(self):
        """Test that invalid device type raises validation error."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'devices': [
                    {'type': 'invalid_type', 'addr': 3}
                ]
            }
        }

        # Execute & Assert - Should raise
        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)

    def test_invalid_address_too_low(self):
        """Test that address below minimum raises validation error."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'devices': [
                    {'type': 'temperature_sensor', 'addr': 2, 'entity_id': 'sensor.test'}
                ]
            }
        }

        # Execute & Assert - Should raise
        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)

    def test_invalid_address_too_high(self):
        """Test that address above maximum raises validation error."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'devices': [
                    {'type': 'temperature_sensor', 'addr': 33, 'entity_id': 'sensor.test'}
                ]
            }
        }

        # Execute & Assert - Should raise
        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)

    def test_invalid_entity_id(self):
        """Test that invalid entity_id raises validation error."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'devices': [
                    {'type': 'temperature_sensor', 'addr': 4, 'entity_id': 'invalid_entity'}
                ]
            }
        }

        # Execute & Assert - Should raise
        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)

    def test_default_baudrate(self):
        """Test that default baudrate is applied."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'devices': [
                    {'type': 'binary_sensor_10ch', 'addr': 3}
                ]
            }
        }

        # Execute
        validated = CONFIG_SCHEMA(config)

        # Assert
        assert validated[DOMAIN]['baudrate'] == DEFAULT_BAUDRATE

    def test_custom_baudrate(self):
        """Test custom baudrate."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'baudrate': 9600,
                'devices': [
                    {'type': 'binary_sensor_10ch', 'addr': 3}
                ]
            }
        }

        # Execute
        validated = CONFIG_SCHEMA(config)

        # Assert
        assert validated[DOMAIN]['baudrate'] == 9600


class TestAsyncSetup:
    """Test suite for async_setup function."""

    @pytest.mark.asyncio
    async def test_setup_with_rs485(self, hass):
        """Test setup with RS485 port type."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'port_type': PORT_TYPE_RS485,
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
            assert DOMAIN in hass.data
            assert 'devices' in hass.data[DOMAIN]
            assert 'rtu' in hass.data[DOMAIN]
            mock_rs485.assert_called_once()
            mock_server.start.assert_called_once()
            mock_load_platform.assert_called_once_with(hass, 'switch', DOMAIN, {}, config)

    @pytest.mark.asyncio
    async def test_setup_with_serial(self, hass):
        """Test setup with standard Serial port type."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'port_type': PORT_TYPE_SERIAL,
                'baudrate': 19200,
                'devices': [
                    {'type': 'binary_sensor_10ch', 'addr': 3}
                ]
            }
        }

        with patch('serial.Serial') as mock_serial, \
             patch('custom_components.ecto_modbus.modbus_rtu.RtuServer') as mock_server_class, \
             patch('custom_components.ecto_modbus.load_platform') as mock_load_platform:

            mock_server = MagicMock()
            mock_server.start = MagicMock()
            mock_server_class.return_value = mock_server

            mock_serial_instance = MagicMock()
            mock_serial.return_value = mock_serial_instance

            # Execute
            result = await async_setup(hass, config)

            # Assert
            assert result is True
            mock_serial.assert_called_once()
            mock_load_platform.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_multiple_devices(self, hass):
        """Test setup with multiple devices."""
        # Setup
        config = {
            DOMAIN: {
                'port': '/dev/ttyUSB0',
                'devices': [
                    {'type': 'temperature_sensor', 'addr': 4, 'entity_id': 'sensor.test'},
                    {'type': 'binary_sensor_10ch', 'addr': 3},
                    {'type': 'relay_8ch', 'addr': 5}
                ]
            }
        }

        with patch('custom_components.ecto_modbus.rs485.RS485') as mock_rs485, \
             patch('custom_components.ecto_modbus.modbus_rtu.RtuServer') as mock_server_class, \
             patch('custom_components.ecto_modbus.load_platform') as mock_load_platform, \
             patch('custom_components.ecto_modbus.devices.temperature.async_track_state_change'):

            mock_server = MagicMock()
            mock_server.start = MagicMock()
            mock_server_class.return_value = mock_server
            mock_server.add_slave = MagicMock(return_value=MagicMock())

            mock_rs485_instance = MagicMock()
            mock_rs485.return_value = mock_rs485_instance

            # Execute
            result = await async_setup(hass, config)

            # Assert
            assert result is True
            devices = hass.data[DOMAIN]['devices']
            assert len(devices) == 3


class TestAsyncUnloadEntry:
    """Test suite for async_unload_entry function."""

    @pytest.mark.asyncio
    async def test_unload_entry(self, hass, config_entry):
        """Test unloading a config entry."""
        # Setup
        hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)

        # Execute
        result = await async_unload_entry(hass, config_entry)

        # Assert
        assert result is True


class TestDeviceClasses:
    """Test suite for device classes mapping."""

    def test_device_classes_mapping(self):
        """Test that all device types are mapped correctly."""
        # Assert
        assert 'binary_sensor_10ch' in DEVICE_CLASSES
        assert 'relay_8ch' in DEVICE_CLASSES
        assert 'temperature_sensor' in DEVICE_CLASSES

    def test_device_classes_importable(self):
        """Test that all device classes can be imported."""
        from custom_components.ecto_modbus.devices import (
            EctoCH10BinarySensor,
            EctoRelay8CH,
            EctoTemperatureSensor
        )

        assert DEVICE_CLASSES['binary_sensor_10ch'] == EctoCH10BinarySensor
        assert DEVICE_CLASSES['relay_8ch'] == EctoRelay8CH
        assert DEVICE_CLASSES['temperature_sensor'] == EctoTemperatureSensor
