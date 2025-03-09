# custom_components/ecto/devices/temperature.py
import logging

from homeassistant.helpers.event import async_track_state_change
from .base import EctoDevice
import modbus_tk.defines as cst
from ..transport.modBusRTU import ModBusRegisterSensor
from modbus_tk.modbus_rtu import RtuServer

_LOGGER = logging.getLogger(__name__)


class EctoTemperatureSensor(EctoDevice):
    """Температурный датчик с 1 каналом"""
    DEVICE_TYPE = 0x2201
    CHANNEL_COUNT = 1
    SCALE_FACTOR = 10  # Масштабирование значений (0.1°C)

    def __init__(self, config, server: RtuServer):
        super().__init__(config, server)
        reg = ModBusRegisterSensor(self.slave, cst.READ_INPUT_REGISTERS, 0x20, 1)
        self.registers[0x20] = reg
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
            print("Set Temrature to: "+str(int(temp * 10)))
            self.registers[0x20].set_raw_value([int(temp * 10)])
        except (ValueError, AttributeError) as e:
            _LOGGER.error(f"Error updating temperature: {e}")