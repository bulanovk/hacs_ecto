import logging

from homeassistant.components.switch import SwitchEntity

from . import DOMAIN
from .devices.binary_sensor import EctoCH10BinarySensor

_LOGGER = logging.getLogger(__name__)


class EctoChannelSwitch(SwitchEntity):
    def __init__(self, device, channel):
        self._device: EctoCH10BinarySensor = device
        self._channel = channel
        self._register_index = channel // 16
        self._bitmask = 1 << (channel % 16)
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
        self._update_state(True)

    async def async_turn_off(self, **kwargs):
        self._update_state(False)

    def _update_state(self, state):
        _LOGGER.warning("Switch channel %s to state %s", self._channel, state)
        if state:
            self._device.set_switch_state(1, self._channel)
        else:
            self._device.set_switch_state(0, self._channel)
        self._state = state
        self.async_write_ha_state()


async def async_setup_platform(hass, config, async_add_entities, discovery_info):
    devices = hass.data[DOMAIN]["devices"]
    relay = []
    for device in devices:
        if isinstance(device, EctoCH10BinarySensor):
            for channel in range(device.CHANNEL_COUNT):
                relay.append(EctoChannelSwitch(device, channel))
    async_add_entities(relay)
