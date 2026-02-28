"""Config flow for Movie Night integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_API_KEY,
    CONF_APPLE_TV_ENTITY,
    CONF_COUNTRY,
    CONF_POLL_INTERVAL,
    DEFAULT_COUNTRY,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)
from .tmdb_client import TMDBClient

_LOGGER = logging.getLogger(__name__)

COUNTRIES = [
    {"value": "GB", "label": "United Kingdom"},
    {"value": "US", "label": "United States"},
    {"value": "CA", "label": "Canada"},
    {"value": "AU", "label": "Australia"},
    {"value": "DE", "label": "Germany"},
    {"value": "FR", "label": "France"},
    {"value": "ES", "label": "Spain"},
    {"value": "IT", "label": "Italy"},
    {"value": "NL", "label": "Netherlands"},
    {"value": "SE", "label": "Sweden"},
    {"value": "NO", "label": "Norway"},
    {"value": "DK", "label": "Denmark"},
    {"value": "FI", "label": "Finland"},
    {"value": "BR", "label": "Brazil"},
    {"value": "MX", "label": "Mexico"},
    {"value": "JP", "label": "Japan"},
    {"value": "KR", "label": "South Korea"},
    {"value": "IN", "label": "India"},
]


class MovieNightConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Movie Night."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: API key and country."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the TMDB API key
            session = async_get_clientsession(self.hass)
            client = TMDBClient(session, user_input[CONF_API_KEY])

            if await client.validate_key():
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                # Store data and move to Apple TV step
                self._user_data = user_input
                return await self.async_step_apple_tv()
            else:
                errors["base"] = "invalid_api_key"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): SelectSelector(
                        SelectSelectorConfig(
                            options=COUNTRIES,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_apple_tv(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the optional Apple TV configuration step."""
        if user_input is not None:
            data = {**self._user_data}
            if user_input.get(CONF_APPLE_TV_ENTITY):
                data[CONF_APPLE_TV_ENTITY] = user_input[CONF_APPLE_TV_ENTITY]
            return self.async_create_entry(title="Movie Night", data=data)

        return self.async_show_form(
            step_id="apple_tv",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_APPLE_TV_ENTITY): EntitySelector(
                        EntitySelectorConfig(domain="media_player")
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow handler."""
        return MovieNightOptionsFlow(config_entry)


class MovieNightOptionsFlow(OptionsFlow):
    """Handle Movie Night options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_country = self._config_entry.options.get(
            CONF_COUNTRY,
            self._config_entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY),
        )
        current_apple_tv = self._config_entry.options.get(
            CONF_APPLE_TV_ENTITY,
            self._config_entry.data.get(CONF_APPLE_TV_ENTITY, ""),
        )
        current_poll = self._config_entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COUNTRY, default=current_country): SelectSelector(
                        SelectSelectorConfig(
                            options=COUNTRIES,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_APPLE_TV_ENTITY, default=current_apple_tv
                    ): EntitySelector(
                        EntitySelectorConfig(domain="media_player")
                    ),
                    vol.Required(
                        CONF_POLL_INTERVAL, default=current_poll
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=24,
                            step=1,
                            unit_of_measurement="hours",
                            mode=NumberSelectorMode.SLIDER,
                        )
                    ),
                }
            ),
        )
