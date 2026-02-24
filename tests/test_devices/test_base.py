"""Tests for EctoDevice base class."""
import pytest
from unittest.mock import MagicMock, patch
import modbus_tk.defines as cst

from custom_components.ecto_modbus.devices.base import EctoDevice


class TestEctoDevice:
    """Test suite for EctoDevice base class."""

    def test_init_minimal(self, mock_modbus_server):
        """Test basic initialization of EctoDevice."""
        # Setup
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {'addr': 4}

        # Execute
        device = EctoDevice(config, mock_server)

        # Assert
        assert device.addr == 4
        assert device.config == config
        assert device.server == mock_server
        assert device.slave == mock_slave
        assert device.DEVICE_TYPE == 0x00
        mock_server.add_slave.assert_called_once_with(4)

    def test_uid_calculation(self, mock_modbus_server):
        """Test UID calculation for different addresses."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        test_cases = [
            (3, 0x800000),
            (4, 0x800001),
            (5, 0x800002),
            (10, 0x800007),
            (32, 0x80001D),
        ]

        for addr, expected_uid in test_cases:
            # Execute
            config = {'addr': addr}
            device = EctoDevice(config, mock_server)

            # Assert
            assert device.uid == expected_uid, \
                f"UID mismatch for addr {addr}: expected {hex(expected_uid)}, got {hex(device.uid)}"

    def test_register_initialization(self, mock_modbus_server):
        """Test that holding registers are initialized correctly."""
        # Setup
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {'addr': 4}

        # Execute
        device = EctoDevice(config, mock_server)

        # Assert
        assert 0 in device.registers
        assert 'registers' in dir(device)
        assert isinstance(device.registers, dict)

    def test_device_type_constant(self, mock_modbus_server):
        """Test that base class has correct DEVICE_TYPE."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 4}

        # Execute
        device = EctoDevice(config, mock_server)

        # Assert
        assert device.DEVICE_TYPE == 0x00

    def test_uid_base_constant(self, mock_modbus_server):
        """Test UID_BASE constant."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 3}

        # Execute
        device = EctoDevice(config, mock_server)

        # Assert
        assert device.UID_BASE == 0x800000

    def test_register_uid_values(self, mock_modbus_server):
        """Test that UID register is set with correct values."""
        # Setup
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        # Mock the set_raw_value method
        with patch('custom_components.ecto_modbus.devices.base.ModBusRegisterSensor') as mock_sensor:
            mock_instance = MagicMock()
            mock_sensor.return_value = mock_instance

            config = {'addr': 5}

            # Execute
            device = EctoDevice(config, mock_server)

            # Assert - verify register was created
            mock_sensor.assert_called_once()
            call_args = mock_sensor.call_args

            # Check that it's a HOLDING_REGISTER at address 0 with size 4
            assert call_args[0][1] == cst.HOLDING_REGISTERS
            assert call_args[0][2] == 0
            assert call_args[0][3] == 4

            # Check that set_raw_value was called with correct UID data
            # UID data format: [0x80, (addr - 3), addr, (device_type << 8) | channel_count]
            # For base class: type=0x00, channels=1 → (0x00 << 8) | 1 = 1
            expected_data = [0x80, 2, 5, 1]
            mock_instance.set_raw_value.assert_called_once_with(expected_data)

    def test_multiple_addresses(self, mock_modbus_server):
        """Test creating devices with different addresses."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        addresses = [3, 4, 10, 20, 32]

        # Execute
        devices = []
        for addr in addresses:
            config = {'addr': addr}
            device = EctoDevice(config, mock_server)
            devices.append(device)

        # Assert
        assert len(devices) == len(addresses)
        for i, device in enumerate(devices):
            assert device.addr == addresses[i]
            assert device.uid == 0x800000 + (addresses[i] - 3)

    def test_config_stored(self, mock_modbus_server):
        """Test that config is stored correctly."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {
            'addr': 4,
            'extra_param': 'test_value',
            'another_param': 123
        }

        # Execute
        device = EctoDevice(config, mock_server)

        # Assert
        assert device.config == config
        assert device.config['extra_param'] == 'test_value'
        assert device.config['another_param'] == 123

    def test_server_reference_stored(self, mock_modbus_server):
        """Test that server reference is stored."""
        # Setup
        mock_server = MagicMock()
        mock_server.add_slave.return_value = MagicMock()

        config = {'addr': 4}

        # Execute
        device = EctoDevice(config, mock_server)

        # Assert
        assert device.server is mock_server

    def test_slave_reference_stored(self, mock_modbus_server):
        """Test that slave reference is stored."""
        # Setup
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {'addr': 4}

        # Execute
        device = EctoDevice(config, mock_server)

        # Assert
        assert device.slave is mock_slave
