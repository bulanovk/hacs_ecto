"""Tests for EctoRelay8CH device."""
import pytest
from unittest.mock import MagicMock

from custom_components.ecto_modbus.devices.relay import EctoRelay8CH


class TestEctoRelay8CH:
    """Test suite for EctoRelay8CH class."""

    def test_device_type_constant(self):
        """Test that DEVICE_TYPE is correct."""
        assert EctoRelay8CH.DEVICE_TYPE == 0xC108

    def test_init_basic(self, mock_modbus_server):
        """Test basic initialization."""
        # Setup
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {'addr': 5}

        # Execute
        device = EctoRelay8CH(config, mock_server)

        # Assert
        assert device.addr == 5
        assert device.DEVICE_TYPE == 0xC108

    def test_inheritance_from_ecto_device(self, mock_modbus_server):
        """Test that EctoRelay8CH inherits from EctoDevice."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 5}

        # Execute
        device = EctoRelay8CH(config, mock_server)

        # Assert - Check for EctoDevice attributes
        assert hasattr(device, 'uid')
        assert hasattr(device, 'registers')
        assert hasattr(device, 'slave')
        assert hasattr(device, 'server')
        assert hasattr(device, 'config')
        assert hasattr(device, 'DEVICE_TYPE')

    def test_different_addresses(self, mock_modbus_server):
        """Test initialization with different addresses."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        addresses = [3, 4, 10, 32]

        # Execute
        for addr in addresses:
            config = {'addr': addr}
            device = EctoRelay8CH(config, mock_server)

            # Assert
            assert device.addr == addr
            assert device.DEVICE_TYPE == 0xC108

    def test_config_stored(self, mock_modbus_server):
        """Test that config is stored correctly."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {
            'addr': 5,
            'extra_param': 'test_value'
        }

        # Execute
        device = EctoRelay8CH(config, mock_server)

        # Assert
        assert device.config == config
        assert device.config['extra_param'] == 'test_value'
