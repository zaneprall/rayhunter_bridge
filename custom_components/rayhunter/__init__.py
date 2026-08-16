"""Rayhunter Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
    UnitOfInformation,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)

from .api import RayhunterClient
from .const import CONF_BASE_URL, DOMAIN
from .coordinator import RayhunterCoordinator


PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


type RayhunterConfigEntry = ConfigEntry[
    RayhunterCoordinator
]


# Preferred display units for data-size entities.
#
# Home Assistant stores a sensor's suggested/display unit in the
# entity registry. Earlier Rayhunter versions exposed these entities
# in raw bytes, so existing installations may still have "B" stored
# even after the entity's native unit changes.
#
# Updating sensor.private changes the integration-suggested unit
# without overriding an explicit unit chosen by the user.
DISPLAY_UNITS = {
    "_current_recording_size":
        UnitOfInformation.KIBIBYTES,

    "_disk_total":
        UnitOfInformation.MEBIBYTES,

    "_disk_used":
        UnitOfInformation.MEBIBYTES,

    "_disk_free":
        UnitOfInformation.MEBIBYTES,

    "_memory_total":
        UnitOfInformation.MEBIBYTES,

    "_memory_used":
        UnitOfInformation.MEBIBYTES,

    "_memory_free":
        UnitOfInformation.MEBIBYTES,
}


def _apply_preferred_display_units(
    hass: HomeAssistant,
    coordinator: RayhunterCoordinator,
) -> None:
    """
    Update integration-suggested units for existing entities.

    This fixes entities that were originally registered using bytes.

    Explicit user-selected units stored under the normal "sensor"
    options namespace still take precedence over these private
    integration suggestions.
    """

    registry = er.async_get(
        hass
    )

    device_id = str(
        coordinator.data.get(
            "device_id"
        )
        or "rayhunter"
    )

    for suffix, unit in DISPLAY_UNITS.items():

        unique_id = (
            f"{device_id}{suffix}"
        )

        entity_id = (
            registry.async_get_entity_id(
                Platform.SENSOR,
                DOMAIN,
                unique_id,
            )
        )

        if entity_id is None:
            continue

        registry_entry = (
            registry.async_get(
                entity_id
            )
        )

        if registry_entry is None:
            continue

        private_options = dict(
            registry_entry.options.get(
                "sensor.private",
                {},
            )
        )

        private_options[
            "suggested_unit_of_measurement"
        ] = str(unit)

        registry.async_update_entity_options(
            entity_id,
            "sensor.private",
            private_options,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RayhunterConfigEntry,
) -> bool:
    """Set up Rayhunter from a config entry."""

    session = async_get_clientsession(
        hass
    )

    client = RayhunterClient(
        session,
        entry.data[
            CONF_BASE_URL
        ],
    )

    coordinator = RayhunterCoordinator(
        hass,
        entry,
        client,
    )

    await (
        coordinator
        .async_config_entry_first_refresh()
    )

    entry.runtime_data = (
        coordinator
    )

    await (
        hass.config_entries
        .async_forward_entry_setups(
            entry,
            PLATFORMS,
        )
    )

    # Entity registry entries now exist, so migrate the old byte
    # display units to the preferred KiB/MiB units.
    _apply_preferred_display_units(
        hass,
        coordinator,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: RayhunterConfigEntry,
) -> bool:
    """Unload a Rayhunter config entry."""

    return await (
        hass.config_entries
        .async_unload_platforms(
            entry,
            PLATFORMS,
        )
    )
