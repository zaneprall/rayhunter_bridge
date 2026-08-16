"""Sensors for Rayhunter."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfInformation,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
)
from homeassistant.util import dt as dt_util

from . import RayhunterConfigEntry
from .entity import RayhunterEntity


GPS_MODES = {
    0: "disabled",
    1: "fixed",
    2: "api",
}

_SIZE_RE = re.compile(
    r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGT]?)\s*$",
    re.IGNORECASE,
)


def _nested_dict(
    data: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    """Return a nested dictionary or an empty dictionary."""

    value = data.get(key)

    if isinstance(value, dict):
        return value

    return {}


def _current_entry(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Return current manifest entry."""

    return _nested_dict(
        data,
        "current_entry",
    )


def _latest_completed_entry(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Return latest completed manifest entry."""

    return _nested_dict(
        data,
        "latest_completed_entry",
    )


def _parse_percent(
    value: Any,
) -> int | float | None:
    """Convert values such as '4%' to numeric percentage."""

    if value is None:
        return None

    text = str(value).strip()

    if text.endswith("%"):
        text = text[:-1]

    try:
        number = float(text)

    except ValueError:
        return None

    if number.is_integer():
        return int(number)

    return number


def _parse_rayhunter_size_bytes(
    value: Any,
) -> int | None:
    """
    Convert Rayhunter human-readable size to bytes.

    Rayhunter values look like:

        512K
        24.6M
        1.2G

    Rayhunter's formatter is binary-based, so:

        K = 1024 bytes
        M = 1024 KiB
        G = 1024 MiB
    """

    if value is None:
        return None

    if isinstance(value, int):
        return value

    text = str(value).strip()

    match = _SIZE_RE.match(text)

    if not match:
        return None

    number = float(
        match.group(1)
    )

    suffix = (
        match.group(2)
        .upper()
    )

    multiplier = {
        "": 1,
        "K": 1024,
        "M": 1024 ** 2,
        "G": 1024 ** 3,
        "T": 1024 ** 4,
    }.get(suffix)

    if multiplier is None:
        return None

    return round(
        number * multiplier
    )


def _bytes_to_mib(
    value: Any,
) -> float | None:
    """Convert bytes to MiB."""

    if value is None:
        return None

    try:
        number = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None

    return round(
        number / (1024 ** 2),
        1,
    )


def _bytes_to_kib(
    value: Any,
) -> float | None:
    """Convert bytes to KiB."""

    if value is None:
        return None

    try:
        number = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None

    return round(
        number / 1024,
        1,
    )


def _rayhunter_size_to_mib(
    value: Any,
) -> float | None:
    """Convert Rayhunter human-readable size to MiB."""

    byte_value = _parse_rayhunter_size_bytes(
        value
    )

    return _bytes_to_mib(
        byte_value
    )


def _parse_timestamp(
    value: Any,
) -> datetime | None:
    """Convert Rayhunter ISO timestamp to HA datetime."""

    if not value:
        return None

    return dt_util.parse_datetime(
        str(value)
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RayhunterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Rayhunter sensors."""

    coordinator = entry.runtime_data

    async_add_entities(
        [
            # Warning state.
            RayhunterSeveritySensor(
                coordinator
            ),
            RayhunterWarningCountSensor(
                coordinator
            ),
            RayhunterLastWarningSensor(
                coordinator
            ),
            RayhunterLastWarningTimeSensor(
                coordinator
            ),

            # Device state.
            RayhunterBatterySensor(
                coordinator
            ),

            # Recording state.
            RayhunterCurrentRecordingSensor(
                coordinator
            ),
            RayhunterCurrentRecordingSizeSensor(
                coordinator
            ),
            RayhunterCurrentRecordingStartSensor(
                coordinator
            ),
            RayhunterCurrentRecordingLastMessageSensor(
                coordinator
            ),
            RayhunterCurrentRecordingGpsModeSensor(
                coordinator
            ),
            RayhunterCompletedRecordingCountSensor(
                coordinator
            ),
            RayhunterTotalRecordingCountSensor(
                coordinator
            ),

            # Disk.
            RayhunterDiskTotalSensor(
                coordinator
            ),
            RayhunterDiskUsedSensor(
                coordinator
            ),
            RayhunterDiskFreeSensor(
                coordinator
            ),
            RayhunterDiskUsedPercentSensor(
                coordinator
            ),

            # Memory.
            RayhunterMemoryTotalSensor(
                coordinator
            ),
            RayhunterMemoryUsedSensor(
                coordinator
            ),
            RayhunterMemoryFreeSensor(
                coordinator
            ),

            # Catch-all.
            RayhunterBridgeDataSensor(
                coordinator
            ),
        ]
    )


class RayhunterSeveritySensor(
    RayhunterEntity,
    SensorEntity,
):
    """Highest warning severity in current recording."""

    _attr_name = "Warning severity"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "clear",
        "low",
        "medium",
        "high",
    ]

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_warning_severity"
        )

    @property
    def native_value(self) -> str:
        """Return current severity."""

        value = str(
            self.coordinator.data.get(
                "severity",
                "clear",
            )
        ).lower()

        if value not in self._attr_options:
            return "clear"

        return value

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Return warning context."""

        data = self.coordinator.data

        return {
            "warning_count":
                data.get("warning_count"),

            "last_warning":
                data.get("last_warning"),

            "last_warning_time":
                data.get("last_warning_time"),

            "report_version":
                data.get("report_version"),
        }


class RayhunterWarningCountSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Warning count for current recording."""

    _attr_name = "Warning count"
    _attr_native_unit_of_measurement = "warnings"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_warning_count"
        )

    @property
    def native_value(self) -> int:
        """Return warning count."""

        return int(
            self.coordinator.data.get(
                "warning_count",
                0,
            )
            or 0
        )


class RayhunterBatterySensor(
    RayhunterEntity,
    SensorEntity,
):
    """Orbic battery level."""

    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_battery"
        )

    @property
    def native_value(
        self,
    ) -> int | float | None:
        """Return battery percentage."""

        return self.coordinator.data.get(
            "battery_level"
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Expose complete battery payload."""

        return _nested_dict(
            self.coordinator.data,
            "battery_status",
        )


class RayhunterCurrentRecordingSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Current recording identifier."""

    _attr_name = "Current recording"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_current_recording"
        )

    @property
    def native_value(
        self,
    ) -> str | None:
        """Return current recording identifier."""

        value = self.coordinator.data.get(
            "current_recording"
        )

        if value is None:
            return None

        return str(value)

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Expose complete current ManifestEntry."""

        return dict(
            _current_entry(
                self.coordinator.data
            )
        )


class RayhunterCurrentRecordingSizeSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Size of current QMDL recording."""

    _attr_name = "Current recording size"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = (
        UnitOfInformation.KIBIBYTES
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_current_recording_size"
        )

    @property
    def native_value(
        self,
    ) -> float | None:
        """Return current recording size in KiB."""

        value = _current_entry(
            self.coordinator.data
        ).get(
            "qmdl_size_bytes"
        )

        return _bytes_to_kib(
            value
        )


class RayhunterCurrentRecordingStartSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Start time of current recording."""

    _attr_name = "Current recording start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_current_recording_start"
        )

    @property
    def native_value(
        self,
    ) -> datetime | None:
        """Return recording start time."""

        return _parse_timestamp(
            _current_entry(
                self.coordinator.data
            ).get(
                "start_time"
            )
        )


class RayhunterCurrentRecordingLastMessageSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Timestamp of last message in current recording."""

    _attr_name = "Current recording last message"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_current_recording_last_message"
        )

    @property
    def native_value(
        self,
    ) -> datetime | None:
        """Return last message timestamp."""

        return _parse_timestamp(
            _current_entry(
                self.coordinator.data
            ).get(
                "last_message_time"
            )
        )


class RayhunterCurrentRecordingGpsModeSensor(
    RayhunterEntity,
    SensorEntity,
):
    """GPS mode for current recording."""

    _attr_name = "Current recording GPS mode"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "disabled",
        "fixed",
        "api",
    ]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_current_recording_gps_mode"
        )

    @property
    def native_value(
        self,
    ) -> str | None:
        """Return current recording GPS mode."""

        raw = _current_entry(
            self.coordinator.data
        ).get(
            "gps_mode"
        )

        try:
            numeric = int(raw)

        except (
            TypeError,
            ValueError,
        ):
            return None

        return GPS_MODES.get(
            numeric
        )


class RayhunterLastWarningSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Most recent Rayhunter warning."""

    _attr_name = "Last warning"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_last_warning"
        )

    @property
    def native_value(
        self,
    ) -> str | None:
        """Return short warning message."""

        value = self.coordinator.data.get(
            "last_warning"
        )

        if value is None:
            return None

        return str(value)[:250]

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Expose full warning details."""

        data = self.coordinator.data

        return {
            "full_message":
                data.get("last_warning"),

            "warning_time":
                data.get("last_warning_time"),

            "severity":
                data.get("severity"),

            "warning_count":
                data.get("warning_count"),
        }


class RayhunterLastWarningTimeSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Timestamp of most recent warning."""

    _attr_name = "Last warning time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_last_warning_time"
        )

    @property
    def native_value(
        self,
    ) -> datetime | None:
        """Return last warning time."""

        return _parse_timestamp(
            self.coordinator.data.get(
                "last_warning_time"
            )
        )


class RayhunterCompletedRecordingCountSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Completed recording count."""

    _attr_name = "Completed recordings"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_completed_recordings"
        )

    @property
    def native_value(
        self,
    ) -> int:
        """Return completed recording count."""

        return int(
            self.coordinator.data.get(
                "completed_recording_count",
                0,
            )
            or 0
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Expose newest completed entry."""

        entry = _latest_completed_entry(
            self.coordinator.data
        )

        if not entry:
            return {}

        return {
            "latest_completed_entry":
                dict(entry)
        }


class RayhunterTotalRecordingCountSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Total recording count."""

    _attr_name = "Total recordings"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_total_recordings"
        )

    @property
    def native_value(
        self,
    ) -> int:
        """Return total recording count."""

        return int(
            self.coordinator.data.get(
                "total_recording_count",
                0,
            )
            or 0
        )


class RayhunterDiskTotalSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Total Rayhunter storage."""

    _attr_name = "Disk total"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = (
        UnitOfInformation.MEBIBYTES
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_disk_total"
        )

    @property
    def native_value(
        self,
    ) -> float | None:
        """Return total storage in MiB."""

        return _rayhunter_size_to_mib(
            _nested_dict(
                self.coordinator.data,
                "disk_stats",
            ).get(
                "total_size"
            )
        )


class RayhunterDiskUsedSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Used Rayhunter storage."""

    _attr_name = "Disk used"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = (
        UnitOfInformation.MEBIBYTES
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_disk_used"
        )

    @property
    def native_value(
        self,
    ) -> float | None:
        """Return used storage in MiB."""

        return _rayhunter_size_to_mib(
            _nested_dict(
                self.coordinator.data,
                "disk_stats",
            ).get(
                "used_size"
            )
        )


class RayhunterDiskFreeSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Available Rayhunter storage."""

    _attr_name = "Disk free"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = (
        UnitOfInformation.MEBIBYTES
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_disk_free"
        )

    @property
    def native_value(
        self,
    ) -> float | None:
        """Return available storage in MiB."""

        disk = _nested_dict(
            self.coordinator.data,
            "disk_stats",
        )

        exact = disk.get(
            "available_bytes"
        )

        if exact is not None:
            value = _bytes_to_mib(
                exact
            )

            if value is not None:
                return value

        return _rayhunter_size_to_mib(
            disk.get(
                "available_size"
            )
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Expose filesystem location."""

        disk = _nested_dict(
            self.coordinator.data,
            "disk_stats",
        )

        return {
            "partition":
                disk.get("partition"),

            "mounted_on":
                disk.get("mounted_on"),

            "reported_available_size":
                disk.get("available_size"),

            "available_bytes":
                disk.get("available_bytes"),
        }


class RayhunterDiskUsedPercentSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Percentage of storage in use."""

    _attr_name = "Disk used percentage"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_disk_used_percentage"
        )

    @property
    def native_value(
        self,
    ) -> int | float | None:
        """Return disk percentage."""

        return _parse_percent(
            _nested_dict(
                self.coordinator.data,
                "disk_stats",
            ).get(
                "used_percent"
            )
        )


class RayhunterMemoryTotalSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Total device memory."""

    _attr_name = "Memory total"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = (
        UnitOfInformation.MEBIBYTES
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_memory_total"
        )

    @property
    def native_value(
        self,
    ) -> float | None:
        """Return total memory in MiB."""

        return _rayhunter_size_to_mib(
            _nested_dict(
                self.coordinator.data,
                "memory_stats",
            ).get(
                "total"
            )
        )


class RayhunterMemoryUsedSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Used device memory."""

    _attr_name = "Memory used"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = (
        UnitOfInformation.MEBIBYTES
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_memory_used"
        )

    @property
    def native_value(
        self,
    ) -> float | None:
        """Return used memory in MiB."""

        return _rayhunter_size_to_mib(
            _nested_dict(
                self.coordinator.data,
                "memory_stats",
            ).get(
                "used"
            )
        )


class RayhunterMemoryFreeSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Free device memory."""

    _attr_name = "Memory free"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = (
        UnitOfInformation.MEBIBYTES
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_memory_free"
        )

    @property
    def native_value(
        self,
    ) -> float | None:
        """Return free memory in MiB."""

        return _rayhunter_size_to_mib(
            _nested_dict(
                self.coordinator.data,
                "memory_stats",
            ).get(
                "free"
            )
        )


class RayhunterBridgeDataSensor(
    RayhunterEntity,
    SensorEntity,
):
    """Catch-all bridge diagnostic entity."""

    _attr_name = "Bridge data"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.data['device_id']}"
            "_bridge_data"
        )

    @property
    def native_value(
        self,
    ) -> str:
        """Use bridge version as state."""

        return str(
            self.coordinator.data.get(
                "bridge_version"
            )
            or "unknown"
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Return complete bounded bridge response."""

        return dict(
            self.coordinator.data
        )
