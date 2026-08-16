"""Binary sensors for Rayhunter."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
)

from . import RayhunterConfigEntry
from .entity import RayhunterEntity


def _current_entry(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Return current recording manifest entry."""

    value = data.get(
        "current_entry"
    )

    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RayhunterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Rayhunter binary sensors."""

    coordinator = entry.runtime_data

    async_add_entities(
        [
            RayhunterActiveWarningSensor(
                coordinator
            ),

            RayhunterRecordingSensor(
                coordinator
            ),

            RayhunterPluggedInSensor(
                coordinator
            ),

            RayhunterCurrentRecordingCompressedSensor(
                coordinator
            ),
        ]
    )


class RayhunterActiveWarningSensor(
    RayhunterEntity,
    BinarySensorEntity,
):
    """Whether Rayhunter has an active warning."""

    _attr_name = "Active warning"

    _attr_device_class = (
        BinarySensorDeviceClass.SAFETY
    )

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize entity."""

        super().__init__(
            coordinator
        )

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_active_warning"
        )

    @property
    def is_on(
        self,
    ) -> bool:
        """Return warning state."""

        return bool(
            self.coordinator.data.get(
                "active_warning",
                False,
            )
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Return warning details."""

        data = self.coordinator.data

        return {
            "severity":
                data.get(
                    "severity"
                ),

            "warning_count":
                data.get(
                    "warning_count"
                ),

            "last_warning":
                data.get(
                    "last_warning"
                ),

            "last_warning_time":
                data.get(
                    "last_warning_time"
                ),

            "current_recording":
                data.get(
                    "current_recording"
                ),
        }


class RayhunterRecordingSensor(
    RayhunterEntity,
    BinarySensorEntity,
):
    """Whether Rayhunter is recording."""

    _attr_name = "Recording"

    _attr_device_class = (
        BinarySensorDeviceClass.RUNNING
    )

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize entity."""

        super().__init__(
            coordinator
        )

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_recording"
        )

    @property
    def is_on(
        self,
    ) -> bool:
        """Return recording state."""

        return bool(
            self.coordinator.data.get(
                "recording",
                False,
            )
        )


class RayhunterPluggedInSensor(
    RayhunterEntity,
    BinarySensorEntity,
):
    """Whether Orbic reports external power."""

    _attr_name = "Plugged in"

    _attr_device_class = (
        BinarySensorDeviceClass.PLUG
    )

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize entity."""

        super().__init__(
            coordinator
        )

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_plugged_in"
        )

    @property
    def is_on(
        self,
    ) -> bool | None:
        """Return external-power state."""

        value = self.coordinator.data.get(
            "plugged_in"
        )

        if value is None:
            return None

        return bool(value)


class RayhunterCurrentRecordingCompressedSensor(
    RayhunterEntity,
    BinarySensorEntity,
):
    """Whether the current recording is compressed."""

    _attr_name = "Current recording compressed"

    _attr_entity_category = (
        EntityCategory.DIAGNOSTIC
    )

    _attr_icon = "mdi:archive"

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize entity."""

        super().__init__(
            coordinator
        )

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_current_recording_compressed"
        )

    @property
    def is_on(
        self,
    ) -> bool | None:
        """Return recording compression state."""

        entry = _current_entry(
            self.coordinator.data
        )

        if not entry:
            return None

        value = entry.get(
            "compressed"
        )

        if value is None:
            return None

        return bool(value)
