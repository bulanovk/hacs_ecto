"""Pytest configuration and shared fixtures for Ectocontrol Modbus tests."""
import asyncio
import os
import subprocess
import time
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# Serial Port Emulation Fixtures (socat PTY)
# ============================================================================

@pytest.fixture(scope="session")
def check_socat():
    """Check if socat is available on the system."""
    try:
        result = subprocess.run(
            ["which", "socat"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            pytest.skip("socat is not installed. Install with: sudo apt-get install socat")
        return True
    except Exception as e:
        pytest.skip(f"Could not check for socat: {e}")


@pytest.fixture(scope="function")
def pty_pair(check_socat):
    """
    Create a pseudo-terminal pair for serial port emulation using socat.

    This fixture creates two linked pseudo-terminals that can be used
    to emulate serial port communication without physical hardware.

    Returns:
        tuple: (master_pty_path, slave_pty_path) - paths to the PTY devices

    Example:
        server uses master_pty, client uses slave_pty
    """
    # Generate unique PTY names based on process ID and test function
    test_id = f"{os.getpid()}_{id(pty_pair)}"
    pty_master = f"/tmp/pty_master_{test_id}"
    pty_slave = f"/tmp/pty_slave_{test_id}"

    _LOGGER.debug(f"Creating PTY pair: {pty_master} <-> {pty_slave}")

    # Start socat to create PTY pair
    # -d -d: verbose logging for debugging
    # pty,link=...,raw,echo=0: create PTY with specified link, raw mode, no echo
    # Note: removed 'waitslave' flag as it can cause blocking
    proc = subprocess.Popen([
        "socat",
        "-d", "-d",
        f"pty,link={pty_master},raw,echo=0",
        f"pty,link={pty_slave},raw,echo=0"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for both PTY symlinks to be created
    # Socat creates both PTYs almost immediately, so we just need to wait for the symlinks
    max_wait = 5  # seconds
    start_time = time.time()
    while not os.path.exists(pty_master) or not os.path.exists(pty_slave):
        if time.time() - start_time > max_wait:
            proc.terminate()
            proc.wait(timeout=2)
            pytest.fail(f"PTY symlink creation timed out after {max_wait}s. "
                       f"Files: {pty_master}={os.path.exists(pty_master)}, {pty_slave}={os.path.exists(pty_slave)}")
        time.sleep(0.1)

    # Give socat a moment to fully initialize
    time.sleep(0.3)

    _LOGGER.debug(f"PTY pair created successfully")

    yield pty_master, pty_slave

    # Cleanup
    _LOGGER.debug(f"Cleaning up PTY pair: {pty_master}, {pty_slave}")
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    # Remove PTY links if they still exist
    for pty_path in [pty_master, pty_slave]:
        try:
            if os.path.exists(pty_path):
                os.unlink(pty_path)
        except Exception as e:
            _LOGGER.warning(f"Could not remove PTY {pty_path}: {e}")


@pytest.fixture
def modbus_server_with_pty(pty_pair):
    """
    Create a real Modbus RTU server using PTY for serial port emulation.

    This fixture sets up a functional Modbus server that can be used
    for integration testing without physical hardware.

    Args:
        pty_pair: Fixture providing the PTY pair

    Returns:
        tuple: (RtuServer, slave_pty_path)
            - RtuServer: The modbus_tk RTU server instance
            - slave_pty_path: Path to the slave PTY for client connections
    """
    from modbus_tk import modbus_rtu
    from serial import Serial

    master_pty, slave_pty = pty_pair

    _LOGGER.debug(f"Creating Modbus server on {master_pty}")

    # Create serial port on master PTY
    serial_port = Serial(
        port=master_pty,
        baudrate=19200,
        timeout=1,
        bytesize=8,
        parity='N',
        stopbits=1
    )

    # Create and start Modbus server
    server = modbus_rtu.RtuServer(
        serial_port,
        interchar_multiplier=1,
        error_on_missing_slave=False
    )
    server.start()

    _LOGGER.info(f"Modbus server started on {master_pty}, client PTY: {slave_pty}")

    yield server, slave_pty

    # Cleanup
    _LOGGER.debug("Stopping Modbus server")
    server.stop()
    serial_port.close()


# ============================================================================
# Home Assistant Fixtures
# ============================================================================

@pytest.fixture
def hass():
    """
    Create a mock Home Assistant instance for testing.

    Returns:
        MagicMock: Mocked HomeAssistant instance with common attributes
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.async_add_executor_job = AsyncMock()

    # Mock common HA methods
    hass.async_run_job = AsyncMock()
    hass.async_create_task = AsyncMock()

    return hass


@pytest.fixture
def config_entry():
    """
    Create a mock ConfigEntry for testing.

    Returns:
        MagicMock: Mocked ConfigEntry instance
    """
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "port": "/dev/ttyUSB0",
        "port_type": "rs485",
        "baudrate": 19200,
        "devices": []
    }
    entry.options = {}
    entry.title = "Ecto Modbus Test"
    return entry


# ============================================================================
# Mock Fixtures for Hardware Dependencies
# ============================================================================

@pytest.fixture
def mock_serial():
    """Mock pyserial for testing without real hardware."""
    with patch('serial.Serial') as mock:
        mock_instance = MagicMock()
        mock_instance.write = MagicMock(return_value=0)
        mock_instance.read = MagicMock(return_value=b'')
        mock_instance.in_waiting = 0
        mock_instance.is_open = True
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_rs485():
    """Mock serial.rs485.RS485 for testing."""
    with patch('serial.rs485.RS485') as mock:
        mock_instance = MagicMock()
        mock_instance.write = MagicMock(return_value=0)
        mock_instance.read = MagicMock(return_value=b'')
        mock_instance.in_waiting = 0
        mock_instance.is_open = True
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_modbus_server():
    """Mock modbus_tk RtuServer for testing."""
    with patch('modbus_tk.modbus_rtu.RtuServer') as mock:
        mock_instance = MagicMock()
        mock_instance.start = MagicMock()
        mock_instance.stop = MagicMock()
        mock_instance.add_slave = MagicMock(return_value=MagicMock())
        mock.return_value = mock_instance
        yield mock


# ============================================================================
# Device Configuration Fixtures
# ============================================================================

@pytest.fixture
def temp_sensor_config():
    """Configuration for temperature sensor tests."""
    return {
        'type': 'temperature_sensor',
        'addr': 4,
        'entity_id': 'sensor.test_temperature'
    }


@pytest.fixture
def binary_sensor_config():
    """Configuration for binary sensor tests."""
    return {
        'type': 'binary_sensor_10ch',
        'addr': 3
    }


@pytest.fixture
def relay_config():
    """Configuration for relay tests."""
    return {
        'type': 'relay_8ch',
        'addr': 5
    }


@pytest.fixture
def integration_config():
    """Full integration configuration for testing."""
    return {
        'port': '/dev/ttyUSB0',
        'port_type': 'rs485',
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
            }
        ]
    }


# ============================================================================
# Test Helper Functions
# ============================================================================

def wait_for_condition(condition, timeout=5, interval=0.1):
    """
    Wait for a condition to become true.

    Args:
        condition: Callable that returns bool
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds

    Returns:
        bool: True if condition was met, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(interval)
    return False


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
