"""Data update coordinator for AP Systems EasyPower."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import APSystemsAPI, APSystemsAPIError, APSystemsAuthError, APSystemsInverterOfflineError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class APSystemsCoordinator(DataUpdateCoordinator):
    """Coordinator that discovers inverters on startup and polls them on a schedule."""

    def __init__(self, hass: HomeAssistant, api: APSystemsAPI) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api
        # Populated after async_discover_inverters()
        self.inverters: list[dict] = []   # list of inverter info dicts
        self.system_id: str | None = None

    async def async_discover_inverters(self) -> None:
        """Discover all inverters for this account. Call once after authentication."""
        try:
            user_info = await self.api.get_user_info()
            system_list = user_info.get("systemInfo", [])
            if not system_list:
                raise APSystemsAPIError("No systems found for this account")

            # Use the first system
            system = system_list[0] if isinstance(system_list, list) else system_list
            self.system_id = system["system_id"]
            _LOGGER.debug("Discovered system_id=%s", self.system_id)

            self.inverters = await self.api.get_inverter_list(self.system_id)
            _LOGGER.info(
                "Discovered %d inverter(s) for system %s: %s",
                len(self.inverters),
                self.system_id,
                [inv.get("inverter_dev_id") for inv in self.inverters],
            )
        except APSystemsAuthError as err:
            raise UpdateFailed(f"Authentication failed during discovery: {err}") from err
        except APSystemsAPIError as err:
            raise UpdateFailed(f"API error during discovery: {err}") from err

    async def _async_update_data(self) -> dict:
        """Fetch current data for all discovered inverters."""
        if not self.inverters:
            await self.async_discover_inverters()

        result = {}
        try:
            for inv in self.inverters:
                dev_id = inv["inverter_dev_id"]
                prev = (self.data or {}).get(dev_id, {})

                # Statistic (todayEnergy, monthEnergy, lifetimeEnergy, lastPower)
                # Fall back to last known values if inverter is offline.
                try:
                    statistic = await self.api.get_inverter_statistic(dev_id)
                except APSystemsInverterOfflineError:
                    statistic = prev.get("statistic", {})
                    _LOGGER.debug("Inverter %s offline — keeping cached statistic", dev_id)

                # Realtime (current power per channel) — empty when inverter is offline.
                try:
                    realtime = await self.api.get_inverter_realtime(dev_id)
                    offline = False
                except APSystemsInverterOfflineError:
                    realtime = {}
                    offline = True
                    _LOGGER.debug("Inverter %s is offline — realtime unavailable", dev_id)

                result[dev_id] = {
                    "info": inv,
                    "statistic": statistic,
                    "realtime": realtime,
                    "offline": offline,
                }
                _LOGGER.debug(
                    "Inverter %s: offline=%s, power=%sW, todayEnergy=%s kWh, lifetimeEnergy=%s kWh",
                    dev_id,
                    offline,
                    realtime.get("power"),
                    statistic.get("todayEnergy"),
                    statistic.get("lifetimeEnergy"),
                )
        except APSystemsAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except APSystemsAPIError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

        return result
