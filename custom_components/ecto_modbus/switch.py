import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN
from .devices.binary_sensor import EctoCH10BinarySensor

_LOGGER = logging.getLogger(__name__)


class EctoChannelSwitch(SwitchEntity, RestoreEntity):
    def __init__(self, device, channel):
        super().__init__()
        self._device: EctoCH10BinarySensor = device
        self._channel = channel
        self._state = False

    @property
    def unique_id(self):
        return f"ecto_{self._device.addr}_ch{self._channel}"

    @property
    def name(self):
        return f"Device {self._device.addr} Ch.{self._channel + 1}"

    @property
    def is_on(self):
        return self._state

    async def async_turn_on(self, **kwargs):
        _LOGGER.warning("Turn on Channel %s", str(self._channel))
        self._update_state(True)

    async def async_turn_off(self, **kwargs):
        _LOGGER.warning("Turn off Channel %s", str(self._channel))
        self._update_state(False)

    def _update_state(self, state):
        _LOGGER.warning("Switch channel %s to state %s", str(self._channel), str(state))
        if state:
            self._device.set_switch_state(self._channel, 1)
        else:
            self._device.set_switch_state(self._channel, 0)
        self._state = state
        self.async_schedule_update_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "local_ecto_unit")},
            name="Ecto Unit",
            model="1.1.1",
            manufacturer="Ectostroy"
        )

    async def async_internal_added_to_hass(self) -> None:
        """Call when the button is added to hass."""
        await super().async_internal_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state not in (STATE_UNAVAILABLE, None):
            self._update_state(state.state)


async def async_setup_platform(hass, config, async_add_entities, discovery_info):
    devices = hass.data[DOMAIN]["devices"]
    relay = []
    for device in devices:
        if isinstance(device, EctoCH10BinarySensor):
            for channel in range(device.CHANNEL_COUNT):
                relay.append(EctoChannelSwitch(device, channel))
    async_add_entities(relay)
