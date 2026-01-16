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
        _LOGGER.debug("Initializing EctoTemperatureSensor: addr=%s", self.addr)
        reg = ModBusRegisterSensor(self.slave, cst.READ_INPUT_REGISTERS, 0x20, 1)
        self.registers[0x20] = reg
        self.entity_id = config.get('entity_id')
        self._hass = None
        _LOGGER.info("EctoTemperatureSensor initialized: addr=%s, entity_id=%s",
                    self.addr, self.entity_id)

    async def async_init(self, hass):
        """Инициализация после получения ссылки на HA"""
        _LOGGER.debug("async_init called for temperature sensor: addr=%s", self.addr)
        self._hass = hass
        if self.entity_id:
            _LOGGER.debug("Setting up state tracking for entity: %s", self.entity_id)
            async_track_state_change(
                hass, self.entity_id, self._state_changed
            )
            _LOGGER.info("State tracking enabled: addr=%s, entity=%s",
                        self.addr, self.entity_id)
        else:
            _LOGGER.warning("No entity_id configured for temperature sensor: addr=%s", self.addr)

    async def _state_changed(self, entity, old_state, new_state):
        """Обработчик изменения состояния сенсора"""
        _LOGGER.debug("State changed for temperature sensor: addr=%s, entity=%s, old=%s, new=%s",
                     self.addr, entity, old_state.state if old_state else None,
                     new_state.state if new_state else None)
        try:
            temp = float(new_state.state)
            scaled_value = int(temp * 10)
            _LOGGER.debug("Updating temperature register: addr=%s, temp=%s, scaled=%s",
                         self.addr, temp, scaled_value)
            self.registers[0x20].set_raw_value([scaled_value])
            _LOGGER.debug("Temperature register updated: addr=%s, value=%s",
                         self.addr, scaled_value)
        except (ValueError, AttributeError) as e:
            _LOGGER.error("Error updating temperature: addr=%s, entity=%s, error=%s",
                         self.addr, entity, e)