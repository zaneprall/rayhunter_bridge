"""Shared Rayhunter entity definitions."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN
from .coordinator import RayhunterCoordinator


class RayhunterEntity(
    CoordinatorEntity[RayhunterCoordinator]
):
    """Base class for Rayhunter entities."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return Rayhunter device information."""

        data = self.coordinator.data

        device_id = str(
            data.get("device_id")
            or "rayhunter"
        )

        device_name = str(
            data.get("device_name")
            or "Rayhunter"
        )

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    device_id,
                )
            },
            name=device_name,
            manufacturer="Orbic",
            model="RC400L",
            sw_version=(
                str(data["rayhunter_version"])
                if data.get("rayhunter_version")
                else None
            ),
        )
