# Quick Start: Running Tests

## Prerequisites Check ✅

Before running tests, ensure you have the following:

### 1. Python Virtual Environment (REQUIRED)

```bash
# Create venv if it doesn't exist
python3 -m venv venv

# Activate venv (IMPORTANT!)
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install test dependencies
pip install -r requirements_test.txt

# Install dev dependencies
pip install -r requirements_dev.txt
```

### 3. Install socat for Integration Tests (OPTIONAL)

```bash
# Ubuntu/Debian
sudo apt-get install socat

# Check if installed
socat -V
```

**Note**: If socat is not installed, integration tests will be automatically skipped.

## Run Tests 🚀

### Option 1: Use the Test Runner Script (Recommended)

```bash
# From project root
./run_tests.sh
```

This will:
- Check if you're in a virtual environment
- Check if socat is installed
- Run all tests with coverage
- Generate HTML, terminal, and XML coverage reports

### Option 2: Run pytest Directly

```bash
# Run all tests
pytest --cov=custom_components/ecto_modbus --cov-report=html -v

# Run only unit tests (skip integration)
pytest -m "not integration" --cov=custom_components/ecto_modbus -v

# Run specific test file
pytest tests/test_devices/test_binary_sensor.py -v

# Run specific test
pytest tests/test_devices/test_binary_sensor.py::TestEctoCH10BinarySensor::test_set_switch_state_channel_0_on -v
```

## View Coverage Reports 📊

### HTML Report (Best for detailed analysis)

```bash
# Open in browser
open htmlcov/index.html        # macOS
xdg-open htmlcov/index.html    # Linux
start htmlcov/index.html       # Windows
```

### Terminal Report

Coverage is automatically displayed in the terminal after tests run.

## What Tests Are Included? 📝

### Unit Tests ✅
- ✅ Transport layer (ModBusRegisterSensor)
- ✅ Base device class (EctoDevice)
- ✅ Binary sensor device (EctoCH10BinarySensor)
- ✅ Temperature sensor device (EctoTemperatureSensor)
- ✅ Relay device (EctoRelay8CH)
- ✅ Switch entities (EctoChannelSwitch)
- ✅ Integration setup (async_setup, config validation)

### Integration Tests (with socat PTY) 🔌
- ✅ Binary sensor with emulated serial port
- ✅ Temperature sensor with emulated serial port
- ✅ Relay with emulated serial port
- ✅ Multiple devices on same server
- ✅ Device address range testing
- ✅ Switch state transitions

## Expected Results 🎯

When all tests pass, you should see:

```
========================================  passed in 10.15s =========================================

Name                                              Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------------------------
custom_components/ecto_modbus/__init__.py            75     15    80%   126-152
custom_components/ecto_modbus/config_flow.py         30      8    73%   61-68
custom_components/ecto_modbus/const.py                8      0   100%
custom_components/ecto_modbus/devices/__init__.py     3      0   100%
custom_components/ecto_modbus/devices/base.py         25      2    92%   28-29
custom_components/ecto_modbus/devices/binary_sensor.py 55      5    91%   53-54
custom_components/ecto_modbus/devices/relay.py         3      0   100%
custom_components/ecto_modbus/devices/temperature.py  42      4    90%   43-44
custom_components/ecto_modbus/switch.py               45      7    84%   70-76
custom_components/ecto_modbus/transport/modBusRTU.py  28      1    96%   26
-----------------------------------------------------------------------------------------------
TOTAL                                                  324     42    87%


Required test coverage has been reached: 87.00% >= 75%
```

## Troubleshooting 🔧

### Problem: "ModuleNotFoundError: No module named 'pytest'"

**Solution**: Make sure you activated the virtual environment and installed dependencies:

```bash
source venv/bin/activate
pip install -r requirements_test.txt
```

### Problem: "socat: not found" warnings

**Solution**: Either install socat or skip integration tests:

```bash
# Install socat
sudo apt-get install socat

# Or skip integration tests
pytest -m "not integration" --cov=custom_components/ecto_modbus
```

### Problem: Tests fail with "asyncio loop is closed"

**Solution**: This is usually a timing issue. Try running tests again:

```bash
pytest --cov=custom_components/ecto_modbus -v
```

### Problem: Coverage is low

**Solution**: This is expected! We're still building out the test suite. Current focus is on core functionality.

## Next Steps 📋

1. ✅ Run the tests and verify they pass
2. ✅ Check the coverage report
3. ⏳ Add more tests for edge cases
4. ⏳ Improve coverage to 85%+
5. ⏳ Add performance tests

## Need Help? 🆘

- Check `tests/README.md` for detailed documentation
- Review `MEMORY.md` for the complete test plan
- Look at existing tests in `tests/` for examples

Happy Testing! 🎉
