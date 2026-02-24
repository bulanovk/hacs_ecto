# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom component for Ectocontrol RS485 Modbus RTU devices. The integration acts as a **Modbus RTU server/simulator**, allowing Home Assistant to interface with Ectocontrol hardware over RS485 or serial connections.

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements_dev.txt
pip install -r requirements_test.txt
```

### Running Tests
```bash
# Run all tests with coverage
./run_tests.sh

# Or directly with pytest
pytest --cov=custom_components/ecto_modbus --cov-report=html -v

# Run specific test file
pytest tests/test_devices/test_binary_sensor.py -v

# Run specific test case
pytest tests/test_devices/test_binary_sensor.py::TestEctoCH10BinarySensor::test_set_switch_state_channel_0_on -v

# Run only unit tests (skip integration tests requiring socat)
pytest -m "not integration" --cov=custom_components/ecto_modbus

# Run with coverage threshold (CI uses 75%)
pytest --cov=custom_components/ecto_modbus --cov-fail-under=75
```

### Linting
```bash
# Check for syntax errors and undefined names
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Full lint (warnings only, max line length 127)
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

## Architecture

### Component Structure
```
custom_components/ecto_modbus/
├── __init__.py      # Integration setup, Modbus server initialization, LoggingSerialWrapper
├── const.py         # Domain constants, device types, port types
├── switch.py        # EctoChannelSwitch entities for binary sensor channels
├── config_flow.py   # UI config (disabled, uses YAML)
├── devices/
│   ├── base.py          # EctoDevice base class
│   ├── binary_sensor.py # EctoCH10BinarySensor (10-channel, DEVICE_TYPE=0x59)
│   ├── relay.py         # EctoRelay10CH (10-channel relay, DEVICE_TYPE=0xC1)
│   └── temperature.py   # EctoTemperatureSensor (DEVICE_TYPE=0x22)
└── transport/
    └── modBusRTU.py     # ModBusRegisterSensor abstraction
```

### Device Hierarchy
```
EctoDevice (base class)
├── Creates Modbus slave with device address
├── UID calculation: 0x800000 + (addr - 3)
├── Holding registers 0-3: [0x80, (addr-3), addr, (TYPE << 8) | CHN_CNT]
│   - Register 3 format per protocol: MSB=TYPE, LSB=CHN_CNT
└── Subclasses add device-specific registers
    ├── EctoCH10BinarySensor → Input register 0x10 (channel states, TYPE=0x59, CHN=10)
    ├── EctoRelay10CH → Holding register 0x10 (states), 0x20-0x29 (timers, TYPE=0xC1, CHN=10)
    └── EctoTemperatureSensor → Input register 0x20 (temp * 10, TYPE=0x22, CHN=1)
```

### Data Flow
1. **Integration setup** (`__init__.py:async_setup`):
   - Creates RS485/Serial port (wrapped with LoggingSerialWrapper for packet logging)
   - Starts `modbus_tk.RtuServer`
   - Instantiates device classes based on YAML config
   - Loads switch platform for binary sensor channels

2. **Binary Sensor channels**:
   - `EctoChannelSwitch` entities control `EctoCH10BinarySensor.set_switch_state()`
   - Channel mapping: `num = 7 - channel` (reversed bit order)
   - Register value: `(bit_pattern << 8)` where bits represent channel states

3. **Temperature sensor**:
   - Listens to HA entity state changes via `async_track_state_change`
   - Scales temperature by 10 (0.1°C precision) before writing to register

### Key Implementation Details

- **Channel bit reversal**: Binary sensor channels use reversed indexing (`7 - channel`)
- **Temperature scaling**: Values multiplied by 10 (e.g., 22.5°C → 225)
- **State persistence**: `EctoChannelSwitch` extends `RestoreEntity` for HA restart recovery
- **Packet logging**: `LoggingSerialWrapper` logs all RT/TX bytes as hex

### Configuration (YAML only)
```yaml
ecto_modbus:
  port: /dev/ttyUSB0
  port_type: rs485        # or 'serial'
  baudrate: 19200         # default
  devices:
    - type: temperature_sensor
      addr: 4             # range: 3-32
      entity_id: sensor.living_room_temperature
    - type: binary_sensor_10ch
      addr: 3
    - type: relay_10ch
      addr: 5
```

### Testing Notes

- Virtual environment is required for test execution
- Integration tests require `socat` for PTY serial emulation (auto-skipped if unavailable)
- Coverage target: 75% minimum (CI enforced), 85%+ goal
- Async tests use `pytest-asyncio` with `asyncio_mode = auto`
