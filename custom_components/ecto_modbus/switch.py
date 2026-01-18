import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_ON
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
        _LOGGER.debug("EctoChannelSwitch created: device_addr=%s, channel=%s",
                     self._device.addr, self._channel)

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
        _LOGGER.info("Turning ON channel %s for device %s",
                    self._channel, self._device.addr)
        _LOGGER.debug("async_turn_on called: device_addr=%s, channel=%s, kwargs=%s",
                     self._device.addr, self._channel, kwargs)
        self._update_state(True)

    async def async_turn_off(self, **kwargs):
        _LOGGER.info("Turning OFF channel %s for device %s",
                    self._channel, self._device.addr)
        _LOGGER.debug("async_turn_off called: device_addr=%s, channel=%s, kwargs=%s",
                     self._device.addr, self._channel, kwargs)
        self._update_state(False)

    def _update_state(self, state):
        _LOGGER.debug("Updating switch state: device_addr=%s, channel=%s, state=%s",
                     self._device.addr, self._channel, state)
        if state:
            self._device.set_switch_state(self._channel, 1)
        else:
            self._device.set_switch_state(self._channel, 0)
        self._state = state
        if self.hass is not None:
            self.async_schedule_update_ha_state()
        _LOGGER.debug("Switch state updated and HA state scheduled: device_addr=%s, channel=%s, is_on=%s",
                     self._device.addr, self._channel, self._state)

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
        _LOGGER.debug("Switch added to HA: device_addr=%s, channel=%s",
                     self._device.addr, self._channel)
        await super().async_internal_added_to_hass()
        state = await self.async_get_last_state()
        _LOGGER.debug("Restoring previous state: device_addr=%s, channel=%s, previous_state=%s",
                     self._device.addr, self._channel, state.state if state else None)
        if state is not None and state.state not in (STATE_UNAVAILABLE, None):
            if state.state == STATE_ON:
                _LOGGER.info("Restoring switch to ON: device_addr=%s, channel=%s",
                           self._device.addr, self._channel)
                self._device.set_switch_state(self._channel, 1)
                self._state = True
            else:
                _LOGGER.info("Restoring switch to OFF: device_addr=%s, channel=%s",
                           self._device.addr, self._channel)
                self._device.set_switch_state(self._channel, 0)
                self._state = False
        else:
            _LOGGER.debug("No previous state to restore: device_addr=%s, channel=%s",
                         self._device.addr, self._channel)


async def async_setup_platform(hass, config, async_add_entities, discovery_info):
    _LOGGER.info("Setting up Ecto switch platform")
    devices = hass.data[DOMAIN]["devices"]
    relay = []
    for device in devices:
        if isinstance(device, EctoCH10BinarySensor):
            _LOGGER.debug("Creating switches for device: addr=%s, channels=%s",
                         device.addr, device.CHANNEL_COUNT)
            for channel in range(device.CHANNEL_COUNT):
                relay.append(EctoChannelSwitch(device, channel))
    _LOGGER.info("Created %d switch(es) for %d device(s)", len(relay), len(devices))
    async_add_entities(relay)
