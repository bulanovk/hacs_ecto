"""Tests for EctoChannelSwitch entity."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.ecto_modbus.switch import EctoChannelSwitch


class TestEctoChannelSwitch:
    """Test suite for EctoChannelSwitch class."""

    def test_init_basic(self):
        """Test basic initialization."""
        # Setup
        mock_device = MagicMock()
        mock_device.addr = 3

        # Execute
        switch = EctoChannelSwitch(mock_device, channel=0)

        # Assert
        assert switch._device is mock_device
        assert switch._channel == 0
        assert switch._state is False

    def test_unique_id(self):
        """Test unique_id property."""
        # Setup
        mock_device = MagicMock()
        mock_device.addr = 4

        switch = EctoChannelSwitch(mock_device, channel=5)

        # Execute & Assert
        assert switch.unique_id == "ecto_4_ch5"

    def test_name(self):
        """Test name property."""
        # Setup
        mock_device = MagicMock()
        mock_device.addr = 3

        switch = EctoChannelSwitch(mock_device, channel=0)

        # Execute & Assert
        assert switch.name == "Device 3 Ch.1"

        switch2 = EctoChannelSwitch(mock_device, channel=7)
        assert switch2.name == "Device 3 Ch.8"

    def test_is_on(self):
        """Test is_on property."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=0)

        # Assert - Initial state
        assert switch.is_on is False

        # Change state
        switch._state = True
        assert switch.is_on is True

    @pytest.mark.asyncio
    async def test_async_turn_on(self):
        """Test turning switch on."""
        # Setup
        mock_device = MagicMock()
        mock_device.addr = 3
        switch = EctoChannelSwitch(mock_device, channel=2)

        # Execute
        await switch.async_turn_on()

        # Assert
        assert switch._state is True
        mock_device.set_switch_state.assert_called_once_with(2, 1)

    @pytest.mark.asyncio
    async def test_async_turn_off(self):
        """Test turning switch off."""
        # Setup
        mock_device = MagicMock()
        mock_device.addr = 3
        switch = EctoChannelSwitch(mock_device, channel=5)

        # Execute
        await switch.async_turn_off()

        # Assert
        assert switch._state is False
        mock_device.set_switch_state.assert_called_once_with(5, 0)

    @pytest.mark.asyncio
    async def test_async_turn_on_with_kwargs(self):
        """Test turning switch on with additional kwargs."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=1)

        # Execute
        await switch.async_turn_on(some_kwarg="value")

        # Assert
        assert switch._state is True
        mock_device.set_switch_state.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_async_turn_off_with_kwargs(self):
        """Test turning switch off with additional kwargs."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=3)

        # Execute
        await switch.async_turn_off(some_kwarg="value")

        # Assert
        assert switch._state is False
        mock_device.set_switch_state.assert_called_once_with(3, 0)

    def test_update_state_on(self):
        """Test _update_state with True."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=0)
        switch.async_schedule_update_ha_state = MagicMock()
        switch.hass = MagicMock()  # Set up hass for HA 2025.12.4 compatibility

        # Execute
        switch._update_state(True)

        # Assert
        assert switch._state is True
        mock_device.set_switch_state.assert_called_once_with(0, 1)
        switch.async_schedule_update_ha_state.assert_called_once()

    def test_update_state_off(self):
        """Test _update_state with False."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=7)
        switch.async_schedule_update_ha_state = MagicMock()
        switch.hass = MagicMock()  # Set up hass for HA 2025.12.4 compatibility

        # Execute
        switch._update_state(False)

        # Assert
        assert switch._state is False
        mock_device.set_switch_state.assert_called_once_with(7, 0)
        switch.async_schedule_update_ha_state.assert_called_once()

    def test_device_info(self):
        """Test device_info property."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=0)

        # Execute
        device_info = switch.device_info

        # Assert
        assert device_info['identifiers'] == {('ecto_modbus', 'local_ecto_unit')}
        assert device_info['name'] == "Ecto Unit"
        assert device_info['model'] == "1.1.1"
        assert device_info['manufacturer'] == "Ectostroy"

    @pytest.mark.asyncio
    async def test_async_internal_added_to_hass_no_previous_state(self):
        """Test async_internal_added_to_hass when no previous state exists."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=0)
        switch.async_get_last_state = AsyncMock(return_value=None)

        # Set up platform mock
        mock_platform = MagicMock()
        mock_platform.platform_name = 'switch'
        switch.platform = mock_platform

        # Set up hass mock
        mock_hass = MagicMock()
        mock_hass.data = {}
        switch.hass = mock_hass

        # Execute
        await switch.async_internal_added_to_hass()

        # Assert - Should not call _update_state
        mock_device.set_switch_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_internal_added_to_hass_with_on_state(self):
        """Test async_internal_added_to_hass when previous state is ON."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=0)

        mock_last_state = MagicMock()
        mock_last_state.state = STATE_ON

        switch.async_get_last_state = AsyncMock(return_value=mock_last_state)

        # Set up platform mock
        mock_platform = MagicMock()
        mock_platform.platform_name = 'switch'
        switch.platform = mock_platform

        # Set up hass mock
        mock_hass = MagicMock()
        mock_hass.data = {}
        switch.hass = mock_hass

        # Execute
        await switch.async_internal_added_to_hass()

        # Assert
        assert switch._state is True
        mock_device.set_switch_state.assert_called_once_with(0, 1)

    @pytest.mark.asyncio
    async def test_async_internal_added_to_hass_with_off_state(self):
        """Test async_internal_added_to_hass when previous state is OFF."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=3)

        mock_last_state = MagicMock()
        mock_last_state.state = STATE_OFF

        switch.async_get_last_state = AsyncMock(return_value=mock_last_state)

        # Set up platform mock
        mock_platform = MagicMock()
        mock_platform.platform_name = 'switch'
        switch.platform = mock_platform

        # Set up hass mock
        mock_hass = MagicMock()
        mock_hass.data = {}
        switch.hass = mock_hass

        # Execute
        await switch.async_internal_added_to_hass()

        # Assert
        assert switch._state is False
        mock_device.set_switch_state.assert_called_once_with(3, 0)

    @pytest.mark.asyncio
    async def test_async_internal_added_to_hass_with_unavailable_state(self):
        """Test async_internal_added_to_hass when previous state is unavailable."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=0)

        mock_last_state = MagicMock()
        mock_last_state.state = "unavailable"

        switch.async_get_last_state = AsyncMock(return_value=mock_last_state)

        # Set up platform mock
        mock_platform = MagicMock()
        mock_platform.platform_name = 'switch'
        switch.platform = mock_platform

        # Set up hass mock
        mock_hass = MagicMock()
        mock_hass.data = {}
        switch.hass = mock_hass

        # Execute
        await switch.async_internal_added_to_hass()

        # Assert - Should not restore state
        mock_device.set_switch_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_internal_added_to_hass_with_none_state(self):
        """Test async_internal_added_to_hass when previous state is None."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=0)

        mock_last_state = MagicMock()
        mock_last_state.state = None

        switch.async_get_last_state = AsyncMock(return_value=mock_last_state)

        # Set up platform mock
        mock_platform = MagicMock()
        mock_platform.platform_name = 'switch'
        switch.platform = mock_platform

        # Set up hass mock
        mock_hass = MagicMock()
        mock_hass.data = {}
        switch.hass = mock_hass

        # Execute
        await switch.async_internal_added_to_hass()

        # Assert - Should not restore state
        mock_device.set_switch_state.assert_not_called()

    def test_multiple_channels_same_device(self):
        """Test creating multiple switches for same device."""
        # Setup
        mock_device = MagicMock()
        mock_device.addr = 3

        # Execute
        switches = [EctoChannelSwitch(mock_device, i) for i in range(8)]

        # Assert
        assert len(switches) == 8
        for i, switch in enumerate(switches):
            assert switch._channel == i
            assert switch._device is mock_device
            assert switch.unique_id == f"ecto_3_ch{i}"
            assert switch.name == f"Device 3 Ch.{i + 1}"

    @pytest.mark.asyncio
    async def test_state_toggle(self):
        """Test toggling switch state multiple times."""
        # Setup
        mock_device = MagicMock()
        switch = EctoChannelSwitch(mock_device, channel=0)

        # Execute - Turn on
        await switch.async_turn_on()
        assert switch._state is True

        # Execute - Turn off
        await switch.async_turn_off()
        assert switch._state is False

        # Execute - Turn on again
        await switch.async_turn_on()
        assert switch._state is True

        # Assert - Should have 3 calls
        assert mock_device.set_switch_state.call_count == 3

    def test_different_device_addresses(self):
        """Test switches for different device addresses."""
        # Setup
        mock_device_3 = MagicMock()
        mock_device_3.addr = 3

        mock_device_10 = MagicMock()
        mock_device_10.addr = 10

        # Execute
        switch1 = EctoChannelSwitch(mock_device_3, channel=0)
        switch2 = EctoChannelSwitch(mock_device_10, channel=0)

        # Assert
        assert switch1.unique_id == "ecto_3_ch0"
        assert switch2.unique_id == "ecto_10_ch0"
        assert switch1.name == "Device 3 Ch.1"
        assert switch2.name == "Device 10 Ch.1"
