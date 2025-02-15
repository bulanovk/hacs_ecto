# custom_components/ecto/devices/temperature.py
from homeassistant.helpers.event import async_track_state_change
from .base import EctoDevice

class EctoTemperatureSensor(EctoDevice):
    """Температурный датчик с 1 каналом"""
    DEVICE_TYPE = 0x22
    CHANNEL_COUNT = 1
    SCALE_FACTOR = 10  # Масштабирование значений (0.1°C)

    def __init__(self, config):
        super().__init__(config)
        self.entity_id = config.get('entity_id')
        self._hass = None

    async def async_init(self, hass):
        """Инициализация после получения ссылки на HA"""
        self._hass = hass
        if self.entity_id:
            async_track_state_change(
                hass, self.entity_id, self._state_changed
            )

    async def _state_changed(self, entity, old_state, new_state):
        """Обработчик изменения состояния сенсора"""
        try:
            temp = float(new_state.state)
            self.input_registers[0] = int(temp * self.SCALE_FACTOR)
        except (ValueError, AttributeError) as e:
            _LOGGER.error(f"Error updating temperature: {e}")