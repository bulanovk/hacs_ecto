from homeassistant.components.switch import SwitchEntity
from . import DOMAIN

class EctoChannelSwitch(SwitchEntity):
    def __init__(self, device, channel):
        self._device = device
        self._channel = channel
        self._register_index = channel // 16
        self._bitmask = 1 << (channel % 16)
        self._state = False

    @property
    def unique_id(self):
        return f"ecto_{self._device.addr}_ch{self._channel}"

    @property
    def name(self):
        return f"Device {self._device.addr} Ch.{self._channel+1}"

    @property
    def is_on(self):
        return self._state

    async def async_turn_on(self, **kwargs):
        self._update_state(True)

    async def async_turn_off(self, **kwargs):
        self._update_state(False)

    def _update_state(self, state):
        reg = self._device.input_registers[self._register_index]
        self._device.input_registers[self._register_index] = reg | self._bitmask if state else reg & ~self._bitmask
        self._state = state
        self.async_write_ha_state()

async def async_setup_platform(hass, config, async_add_entities, discovery_info):
    devices = hass.data[DOMAIN]["devices"]
    async_add_entities(
        EctoChannelSwitch(device, channel)
        for device in devices
        for channel in range(device.CHANNEL_COUNT)
    )