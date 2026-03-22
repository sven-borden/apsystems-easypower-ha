"""Config flow for AP Systems EasyPower integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .api import APSystemsAPI, APSystemsAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class APSystemsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the AP Systems EasyPower config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api = APSystemsAPI(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            try:
                await api.authenticate()
            except APSystemsAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during AP Systems authentication")
                errors["base"] = "cannot_connect"
            else:
                await api.close()
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"AP Systems ({user_input[CONF_USERNAME]})",
                    data=user_input,
                )
            await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
