# custom_components/ecto_modbus/switch.py
from homeassistant.components.switch import SwitchEntity
from . import DOMAIN

class EctoChannelSwitch(SwitchEntity):
    def __init__(self, device_id, channel, device):
        self._device_id = device_id
        self._channel = channel
        self._device = device
        self._state = False

    @property
    def unique_id(self):
        return f"ecto_{self._device_id}_ch{self._channel}"

    @property
    def name(self):
        return f"Device {self._device_id} Ch.{self._channel+1}"

    @property
    def is_on(self):
        return self._state

    async def async_turn_on(self, **kwargs):
        self._update_state(True)

    async def async_turn_off(self, **kwargs):
        self._update_state(False)

    def _update_state(self, state):
        mask = 1 << self._channel
        if state:
            self._device.input_registers[0] |= mask
        else:
            self._device.input_registers[0] &= ~mask
        self._state = state
        self.async_write_ha_state()

async def async_setup_platform(hass, config, async_add_entities, discovery_info):
    devices = hass.data[DOMAIN]["devices"]
    switches = []

    for idx, device in enumerate(devices):
        for channel in range(device.CHANNEL_COUNT):
            switches.append(
                EctoChannelSwitch(device.addr, channel, device)
            )

    async_add_entities(switches)