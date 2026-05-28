"""AP Systems EasyPower Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import APSystemsAPI, APSystemsAPIError, APSystemsAuthError
from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import APSystemsCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AP Systems EasyPower from a config entry."""
    api = APSystemsAPI(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    try:
        await api.authenticate()
    except APSystemsAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except APSystemsAPIError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = APSystemsCoordinator(hass, api)
    # Discover inverters before first data refresh so sensor entities can be created
    try:
        await coordinator.async_discover_inverters()
    except APSystemsAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except APSystemsAPIError as err:
        raise ConfigEntryNotReady(str(err)) from err
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        await entry_data[DATA_COORDINATOR].api.close()
    return unload_ok
