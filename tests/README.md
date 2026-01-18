# Testing Guide for Ectocontrol Modbus Integration

This directory contains the test suite for the Ectocontrol Modbus Home Assistant integration.

## Prerequisites

### 1. Install Test Dependencies

```bash
# Activate virtual environment (IMPORTANT!)
source venv/bin/activate

# Install test dependencies
pip install -r requirements_test.txt
```

### 2. Install socat for Integration Tests (Optional but Recommended)

```bash
# Ubuntu/Debian
sudo apt-get install socat

# Fedora
sudo dnf install socat

# macOS
brew install socat
```

**Note**: If socat is not installed, integration tests will be automatically skipped.

## Running Tests

### Run All Tests

```bash
# From project root
./run_tests.sh

# Or directly with pytest
pytest --cov=custom_components/ecto_modbus --cov-report=html
```

### Run Specific Test Files

```bash
# Test transport layer
pytest tests/test_transport/test_modbus_rtu.py -v

# Test specific device
pytest tests/test_devices/test_binary_sensor.py -v

# Test switch entities
pytest tests/test_entities/test_switch.py -v
```

### Run Specific Test Cases

```bash
# Run specific test class
pytest tests/test_devices/test_binary_sensor.py::TestEctoCH10BinarySensor -v

# Run specific test method
pytest tests/test_devices/test_binary_sensor.py::TestEctoCH10BinarySensor::test_set_switch_state_channel_0_on -v
```

### Run Only Unit Tests (Skip Integration Tests)

```bash
pytest -m "not integration" --cov=custom_components/ecto_modbus
```

### Run Only Integration Tests

```bash
pytest -m "integration" --cov=custom_components/ecto_modbus
```

## Coverage Reports

After running tests with coverage, you can view the reports:

### HTML Coverage Report

```bash
# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Terminal Coverage Report

Coverage is automatically printed to terminal after tests run.

### XML Coverage Report

For CI/CD integration: `coverage.xml`

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── test_init.py                # Integration setup tests
├── test_devices/               # Device tests
│   ├── test_base.py           # Base device class
│   ├── test_binary_sensor.py  # Binary sensor device
│   ├── test_relay.py          # Relay device
│   └── test_temperature.py    # Temperature sensor device
├── test_transport/            # Transport layer tests
│   └── test_modbus_rtu.py     # ModBusRegisterSensor tests
└── test_entities/             # Home Assistant entity tests
    └── test_switch.py         # EctoChannelSwitch tests
```

## Key Fixtures

### Hardware Mocks

- `mock_serial` - Mock pyserial for testing without real hardware
- `mock_rs485` - Mock serial.rs485.RS485 for testing
- `mock_modbus_server` - Mock modbus_tk RtuServer for testing

### Serial Port Emulation (socat PTY)

- `pty_pair` - Creates pseudo-terminal pair for serial emulation
- `modbus_server_with_pty` - Creates real Modbus server using PTY

### Home Assistant Mocks

- `hass` - Mock Home Assistant instance
- `config_entry` - Mock ConfigEntry instance

### Device Configurations

- `temp_sensor_config` - Temperature sensor configuration
- `binary_sensor_config` - Binary sensor configuration
- `relay_config` - Relay configuration
- `integration_config` - Full integration configuration

## Writing New Tests

### Unit Test Example

```python
"""Test example."""
import pytest
from unittest.mock import MagicMock

from custom_components.ecto_modbus.devices.base import EctoDevice


class TestEctoDevice:
    """Test suite for EctoDevice."""

    def test_init_basic(self, mock_modbus_server):
        """Test basic initialization."""
        # Setup
        mock_server = MagicMock()
        mock_slave = MagicMock()
        mock_server.add_slave.return_value = mock_slave

        config = {'addr': 4}

        # Execute
        device = EctoDevice(config, mock_server)

        # Assert
        assert device.addr == 4
        assert device.DEVICE_TYPE == 0x00
```

### Integration Test Example (with PTY)

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_integration_with_pty(modbus_server_with_pty):
    """Test complete flow with emulated serial port."""
    server, slave_pty = modbus_server_with_pty

    # Create device
    config = {'addr': 4}
    device = EctoCH10BinarySensor(config, server)

    # Set switch state
    device.set_switch_state(0, True)

    # Verify register was updated
    # Add assertions here
```

## Troubleshooting

### Tests Fail with "ModuleNotFoundError"

**Solution**: Make sure you're in the virtual environment and dependencies are installed:

```bash
source venv/bin/activate
pip install -r requirements_test.txt
pip install -r requirements_dev.txt
```

### socat Tests Fail with "socat: not found"

**Solution**: Install socat or skip integration tests:

```bash
# Install socat
sudo apt-get install socat

# Or skip integration tests
pytest -m "not integration"
```

### Coverage is Low

**Solution**: Run tests with verbose output to see what's being tested:

```bash
pytest --cov=custom_components/ecto_modbus --cov-report=term-missing -v
```

### "Asyncio loop is closed" Errors

**Solution**: Make sure tests are marked as async:

```python
@pytest.mark.asyncio
async def test_my_async_test():
    await some_async_function()
```

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements_test.txt
    sudo apt-get install socat
    pytest --cov --cov-fail-under=80
```

## Current Coverage Status

| Module | Target | Priority |
|--------|--------|----------|
| transport/modBusRTU.py | 95% | HIGH |
| devices/base.py | 90% | HIGH |
| devices/binary_sensor.py | 90% | HIGH |
| devices/temperature.py | 90% | HIGH |
| switch.py | 85% | HIGH |
| __init__.py | 80% | HIGH |
| devices/relay.py | 85% | MEDIUM |
| config_flow.py | 75% | MEDIUM |
| **TOTAL** | **85%+** | - |

## Next Steps

1. ✅ Infrastructure setup (pytest, coverage, fixtures)
2. ✅ Basic unit tests for all devices
3. ⏳ Integration tests with socat PTY
4. ⏳ Error handling tests
5. ⏳ Edge case tests
6. ⏳ Performance tests

For more details, see MEMORY.md - "Test Coverage Analysis & Enhancement Plan"
