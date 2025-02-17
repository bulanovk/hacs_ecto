# custom_components/ecto/config_flow.py
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol
from .const import DOMAIN, DEFAULT_BAUDRATE, DEVICE_TYPES

class EctoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=f"Ecto Modbus ({user_input['port']})",
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("port"): str,
                vol.Optional("baudrate", default=DEFAULT_BAUDRATE): int
            })
        )

    async def async_step_device(self, user_input=None) -> FlowResult:
        if user_input is not None:
            config_entry = self.hass.config_entries.async_get_entry(
                self.context["entry_id"]
            )
            new_data = dict(config_entry.data)
            new_data.setdefault("devices", []).append(user_input)

            self.hass.config_entries.async_update_entry(
                config_entry,
                data=new_data
            )
            return self.async_abort(reason="device_added")

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required("type"): vol.In(DEVICE_TYPES),
                vol.Required("addr"): int,
                vol.Optional("entity_id"): str
            })
        )

class EctoOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_device_list()

    async def async_step_device_list(self, user_input=None):
        devices = self.config_entry.data.get("devices", [])
        return self.async_show_menu(
            step_id="device_list",
            menu_options=["add_device", "remove_device"]
        )