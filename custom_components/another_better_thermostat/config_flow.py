"""Adds config flow for Blueprint."""

from __future__ import annotations
from os import error

import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_USERNAME  # noqa: F401
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import (
    async_create_clientsession,  # noqa: F401
)

from custom_components.another_better_thermostat.adapters.delegate import load_adapter
from .utils.helpers import get_device_model, get_trv_intigration

from .utils.const import (
    CONF_HEATER,
    CONF_HUMIDITY,
    CONF_MODEL,
    CONF_NAME,
    CONF_SENSOR,
    CONF_SENSOR_WINDOW,
    DOMAIN,
    LOGGER,
)


class ABTFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.name = ""
        self.data = None
        self.model = None
        self.conf_sensor = None
        self.heater_entity_id = None
        self.trv_bundle = []
        self.integration = None
        self.i = 0

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> data_entry_flow.FlowResult:
        """Config Flow Step 1."""
        errors = {}

        if user_input is not None:
            if self.data is None:
                self.data = user_input
            self.heater_entity_id = self.data[CONF_HEATER]
            self.conf_sensor = self.data[CONF_SENSOR]
            if self.data[CONF_NAME] == "":
                errors["base"] = "no_name"
            if "base" not in errors:
                for trv in self.heater_entity_id:
                    _intigration = await get_trv_intigration(self, trv)
                    self.trv_bundle.append(
                        {
                            "trv": trv,
                            "integration": _intigration,
                            "model": await get_device_model(self, trv),
                            "adapter": load_adapter(self, _intigration, trv),
                        }
                    )
                self.data[CONF_MODEL] = "/".join([x["model"] for x in self.trv_bundle])
                return await self.async_step_advanced(None, self.trv_bundle[0])

        user_input = user_input or {}

        return self.async_show_form(
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, "")): str,
                    vol.Required(CONF_HEATER): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="climate", multiple=True)
                    ),
                    vol.Required(CONF_SENSOR): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "number", "input_number"],
                            device_class="temperature",
                            multiple=False,
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders=None,
            last_step=False,
        )

    async def async_step_confirm(
        self, user_input: dict | None = None, confirm_type=None
    ) -> data_entry_flow.FlowResult:
        """Config Flow Step 1."""
        errors = {}
        self.data[CONF_HEATER] = self.trv_bundle
        if user_input is not None:
            if self.data is not None:
                LOGGER.debug("Confirm: %s", self.data[CONF_HEATER])
                unique_trv_string = "_".join([x["trv"] for x in self.data[CONF_HEATER]])
                await self.async_set_unique_id(
                    f"{self.data['name']}_{unique_trv_string}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=self.data["name"], data=self.data)
        if confirm_type is not None:
            errors["base"] = confirm_type
        _trvs = ",".join([x["trv"] for x in self.data[CONF_HEATER]])
        return self.async_show_form(
            step_id="confirm",
            errors=errors,
            description_placeholders={"name": self.data[CONF_NAME], "trv": _trvs},
        )
