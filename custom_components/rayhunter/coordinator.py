"""Data coordinator for the Rayhunter integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import RayhunterApiError, RayhunterClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class RayhunterCoordinator(
    DataUpdateCoordinator[dict[str, Any]]
):
    """Coordinate polling of the Rayhunter Bridge."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: RayhunterClient,
    ) -> None:
        """Initialize the coordinator."""

        self.client = client

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                seconds=DEFAULT_SCAN_INTERVAL
            ),
            always_update=False,
        )

    async def _async_update_data(
        self,
    ) -> dict[str, Any]:
        """Fetch the latest Rayhunter state."""

        try:
            return await self.client.async_get_status()

        except RayhunterApiError as exc:
            raise UpdateFailed(
                f"Error communicating with Rayhunter: {exc}"
            ) from exc
