"""Tests for ModBusRegisterSensor transport layer."""
import pytest
from unittest.mock import MagicMock, call
import modbus_tk.defines as cst

from custom_components.ecto_modbus.transport.modBusRTU import ModBusRegisterSensor


class TestModBusRegisterSensor:
    """Test suite for ModBusRegisterSensor class."""

    def test_init_basic(self, mock_modbus_server):
        """Test basic initialization of ModBusRegisterSensor."""
        # Setup
        mock_slave = MagicMock()
        mock_slave.add_block = MagicMock()

        # Execute
        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.HOLDING_REGISTERS,
            addr=0x10,
            reg_size=1
        )

        # Assert
        assert sensor.addr == 0x10
        assert sensor.reg_type == cst.HOLDING_REGISTERS
        assert sensor.reg_size == 1
        assert sensor.slave == mock_slave
        assert sensor.read_callback is None
        assert sensor.block_name == "val-x16"
        mock_slave.add_block.assert_called_once_with(
            "val-x16",
            cst.HOLDING_REGISTERS,
            0x10,
            1
        )

    def test_init_with_callback(self, mock_modbus_server):
        """Test initialization with read callback."""
        # Setup
        mock_slave = MagicMock()
        callback = MagicMock()

        # Execute
        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.READ_INPUT_REGISTERS,
            addr=0x20,
            reg_size=2,
            read_callback=callback
        )

        # Assert
        assert sensor.read_callback == callback
        assert sensor.block_name == "val-x32"

    def test_set_raw_value_single(self, mock_modbus_server):
        """Test setting a single raw value."""
        # Setup
        mock_slave = MagicMock()
        mock_slave.add_block = MagicMock()
        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.HOLDING_REGISTERS,
            addr=0x00,
            reg_size=1
        )

        # Execute
        sensor.set_raw_value([0x1234])

        # Assert
        mock_slave.set_values.assert_called_once_with("val-x0", 0x00, [0x1234])

    def test_set_raw_value_multiple(self, mock_modbus_server):
        """Test setting multiple raw values."""
        # Setup
        mock_slave = MagicMock()
        mock_slave.add_block = MagicMock()
        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.HOLDING_REGISTERS,
            addr=0x10,
            reg_size=4
        )

        # Execute
        test_values = [0x8000, 0x0001, 0x0002, 0x5908]
        sensor.set_raw_value(test_values)

        # Assert
        mock_slave.set_values.assert_called_once_with("val-x16", 0x10, test_values)

    def test_set_raw_value_empty(self, mock_modbus_server):
        """Test setting empty value list."""
        # Setup
        mock_slave = MagicMock()
        mock_slave.add_block = MagicMock()
        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.HOLDING_REGISTERS,
            addr=0x00,
            reg_size=1
        )

        # Execute
        sensor.set_raw_value([])

        # Assert
        mock_slave.set_values.assert_called_once_with("val-x0", 0x00, [])

    def test_get_values_without_callback(self, mock_modbus_server):
        """Test getting values without callback."""
        # Setup
        mock_slave = MagicMock()
        mock_slave.add_block = MagicMock()
        expected_values = [0x8000, 0x0001]
        mock_slave.get_values = MagicMock(return_value=expected_values)

        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.READ_INPUT_REGISTERS,
            addr=0x10,
            reg_size=2
        )

        # Execute
        result = sensor.get_values()

        # Assert
        assert result == expected_values
        mock_slave.get_values.assert_called_once_with("val-x16", 0x10, 2)

    def test_get_values_with_callback(self, mock_modbus_server):
        """Test getting values with callback invocation."""
        # Setup
        mock_slave = MagicMock()
        mock_slave.add_block = MagicMock()
        expected_values = [0x1234]
        mock_slave.get_values = MagicMock(return_value=expected_values)

        callback = MagicMock()
        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.READ_INPUT_REGISTERS,
            addr=0x20,
            reg_size=1,
            read_callback=callback
        )

        # Execute
        result = sensor.get_values()

        # Assert
        assert result == expected_values
        mock_slave.get_values.assert_called_once_with("val-x32", 0x20, 1)
        callback.assert_called_once_with(0x20, expected_values)

    def test_get_values_callback_parameters(self, mock_modbus_server):
        """Test that callback receives correct parameters."""
        # Setup
        mock_slave = MagicMock()
        mock_slave.add_block = MagicMock()

        callback = MagicMock()
        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.READ_INPUT_REGISTERS,
            addr=0x30,
            reg_size=3,
            read_callback=callback
        )

        test_values = [0x1000, 0x2000, 0x3000]
        mock_slave.get_values = MagicMock(return_value=test_values)

        # Execute
        sensor.get_values()

        # Assert
        callback.assert_called_once_with(0x30, test_values)

    def test_different_register_types(self, mock_modbus_server):
        """Test initialization with different register types."""
        # Setup
        mock_slave = MagicMock()

        reg_types = [
            cst.HOLDING_REGISTERS,
            cst.READ_INPUT_REGISTERS,
            cst.READ_COILS,
            cst.READ_DISCRETE_INPUTS
        ]

        for reg_type in reg_types:
            # Execute
            sensor = ModBusRegisterSensor(
                slave=mock_slave,
                reg_type=reg_type,
                addr=0x00,
                reg_size=1
            )

            # Assert
            assert sensor.reg_type == reg_type

    def test_multiple_blocks_same_slave(self, mock_modbus_server):
        """Test creating multiple registers on the same slave."""
        # Setup
        mock_slave = MagicMock()

        # Execute
        sensor1 = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.HOLDING_REGISTERS,
            addr=0x00,
            reg_size=4
        )

        sensor2 = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.READ_INPUT_REGISTERS,
            addr=0x10,
            reg_size=1
        )

        sensor3 = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.READ_INPUT_REGISTERS,
            addr=0x20,
            reg_size=1
        )

        # Assert
        assert sensor1.block_name == "val-x0"
        assert sensor2.block_name == "val-x16"
        assert sensor3.block_name == "val-x32"
        assert mock_slave.add_block.call_count == 3

    def test_set_raw_value_updates_multiple_times(self, mock_modbus_server):
        """Test updating the same register multiple times."""
        # Setup
        mock_slave = MagicMock()
        mock_slave.add_block = MagicMock()
        sensor = ModBusRegisterSensor(
            slave=mock_slave,
            reg_type=cst.HOLDING_REGISTERS,
            addr=0x10,
            reg_size=1
        )

        # Execute
        sensor.set_raw_value([0x0000])
        sensor.set_raw_value([0x8000])
        sensor.set_raw_value([0xFFFF])

        # Assert
        assert mock_slave.set_values.call_count == 3
        calls = [
            call("val-x16", 0x10, [0x0000]),
            call("val-x16", 0x10, [0x8000]),
            call("val-x16", 0x10, [0xFFFF])
        ]
        mock_slave.set_values.assert_has_calls(calls)
