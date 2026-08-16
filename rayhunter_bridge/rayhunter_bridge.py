#!/usr/bin/env python3
"""
Rayhunter -> Home Assistant local API bridge.

The Home Assistant add-on owns:

    Orbic USB
        -> ADB
        -> TCP forward
        -> Rayhunter HTTP API

This process exposes a read-only API to the Home Assistant custom
integration.

MQTT is not used.
"""

from __future__ import annotations

import json
import os
import random
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BRIDGE_VERSION = "1.1.1"
API_VERSION = 1

BASE = os.getenv(
    "RAYHUNTER_BASE",
    "http://127.0.0.1:18080",
).rstrip("/")

HTTP_TIMEOUT = max(
    0.5,
    float(os.getenv("HTTP_TIMEOUT", "3")),
)

HTTP_RETRIES = max(
    1,
    int(os.getenv("HTTP_RETRIES", "3")),
)

HTTP_BACKOFF_BASE = max(
    0.05,
    float(os.getenv("HTTP_BACKOFF_BASE", "0.4")),
)

DEVICE_ID = os.getenv(
    "DEVICE_ID",
    "rayhunter_orbic",
)

DEVICE_NAME = os.getenv(
    "DEVICE_NAME",
    "Rayhunter (Orbic)",
)

API_BIND = "0.0.0.0"
API_PORT = 8099

SEVERITY = {
    "Informational": 0,
    "Low": 1,
    "Medium": 2,
    "High": 3,
}

_shutdown = threading.Event()
_last_summary = ""


def backoff(attempt: int) -> None:
    """Sleep between Rayhunter HTTP retries."""

    delay = HTTP_BACKOFF_BASE * (
        2 ** max(0, attempt - 1)
    )

    time.sleep(
        min(
            5.0,
            delay
            + random.uniform(
                0,
                delay / 2,
            ),
        )
    )


def http_get(path: str) -> str:
    """Fetch text from the forwarded Rayhunter API."""

    request = Request(
        f"{BASE}{path}",
        headers={
            "User-Agent":
                f"rayhunter-bridge/{BRIDGE_VERSION}",
        },
    )

    last_error: Exception | None = None

    for attempt in range(
        1,
        HTTP_RETRIES + 1,
    ):
        try:
            with urlopen(
                request,
                timeout=HTTP_TIMEOUT,
            ) as response:
                return response.read().decode(
                    "utf-8",
                    "replace",
                )

        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
        ) as exc:
            last_error = exc

            if attempt < HTTP_RETRIES:
                backoff(attempt)

    raise RuntimeError(
        f"GET {path} failed: {last_error}"
    )


def json_get(path: str) -> Any:
    """Fetch and decode JSON from Rayhunter."""

    try:
        return json.loads(
            http_get(path)
        )

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON from {path}: {exc}"
        ) from exc


def parse_report(
    text: str,
) -> dict[str, Any]:
    """
    Parse Rayhunter analysis NDJSON.

    Report version 2:

        line 1: ReportMetadata
        line 2+: AnalysisRow

    Informational events are not warnings.
    Low, Medium, and High events are warnings.
    """

    highest = "Informational"

    warning_count = 0

    last_warning = None
    last_warning_time = None

    report_version = None

    first = True

    for raw_line in text.splitlines():

        if not raw_line.strip():
            continue

        try:
            row = json.loads(
                raw_line
            )

        except json.JSONDecodeError:
            continue

        if not isinstance(
            row,
            dict,
        ):
            continue

        if first:
            first = False

            report_version = row.get(
                "report_version"
            )

            continue

        events = row.get(
            "events"
        )

        if not isinstance(
            events,
            list,
        ):
            continue

        timestamp = row.get(
            "packet_timestamp"
        )

        for event in events:

            if not isinstance(
                event,
                dict,
            ):
                continue

            event_type = event.get(
                "event_type"
            )

            if not isinstance(
                event_type,
                str,
            ):
                continue

            if event_type not in SEVERITY:
                continue

            if SEVERITY[event_type] == 0:
                continue

            warning_count += 1

            if (
                SEVERITY[event_type]
                >
                SEVERITY[highest]
            ):
                highest = event_type

            message = str(
                event.get("message")
                or ""
            ).strip()

            last_warning = (
                message
                or None
            )

            last_warning_time = (
                str(timestamp)
                if timestamp
                else None
            )

    return {
        "active_warning":
            warning_count > 0,

        "severity":
            (
                "clear"
                if warning_count == 0
                else highest.lower()
            ),

        "warning_count":
            warning_count,

        "last_warning":
            last_warning,

        "last_warning_time":
            last_warning_time,

        "report_version":
            report_version,
    }


def newest_completed_entry(
    entries: list[Any],
) -> dict[str, Any] | None:
    """Return the newest completed manifest entry."""

    valid_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict)
    ]

    if not valid_entries:
        return None

    def sort_value(
        entry: dict[str, Any],
    ) -> str:
        return str(
            entry.get("start_time")
            or entry.get("name")
            or ""
        )

    return max(
        valid_entries,
        key=sort_value,
    )


def build_status() -> dict[str, Any]:
    """
    Build the Home Assistant-facing state object.

    We expose:

      - normalized high-value fields
      - complete /api/system-stats payload
      - complete current ManifestEntry
      - complete newest completed ManifestEntry
      - recording counts

    We intentionally do not embed every historical manifest entry
    because that list grows without bound.

    Communication failures raise rather than returning a false
    "safe" state.
    """

    stats = json_get(
        "/api/system-stats"
    )

    manifest = json_get(
        "/api/qmdl-manifest"
    )

    if not isinstance(
        stats,
        dict,
    ):
        raise RuntimeError(
            "/api/system-stats "
            "did not return an object"
        )

    if not isinstance(
        manifest,
        dict,
    ):
        raise RuntimeError(
            "/api/qmdl-manifest "
            "did not return an object"
        )

    runtime = stats.get(
        "runtime_metadata"
    )

    if not isinstance(
        runtime,
        dict,
    ):
        runtime = {}

    battery = stats.get(
        "battery_status"
    )

    if not isinstance(
        battery,
        dict,
    ):
        battery = {}

    disk_stats = stats.get(
        "disk_stats"
    )

    if not isinstance(
        disk_stats,
        dict,
    ):
        disk_stats = {}

    memory_stats = stats.get(
        "memory_stats"
    )

    if not isinstance(
        memory_stats,
        dict,
    ):
        memory_stats = {}

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        entries = []

    current = manifest.get(
        "current_entry"
    )

    if not isinstance(
        current,
        dict,
    ):
        current = None

    latest_completed = (
        newest_completed_entry(
            entries
        )
    )

    recording = (
        current is not None
    )

    current_recording = None

    if (
        current is not None
        and current.get("name")
        is not None
    ):
        current_recording = str(
            current["name"]
        )

    completed_count = len(
        [
            entry
            for entry in entries
            if isinstance(entry, dict)
        ]
    )

    total_count = (
        completed_count
        + (1 if recording else 0)
    )

    status: dict[str, Any] = {
        # Bridge metadata.
        "api_version":
            API_VERSION,

        "bridge_version":
            BRIDGE_VERSION,

        "device_id":
            DEVICE_ID,

        "device_name":
            DEVICE_NAME,

        # Availability / recording state.
        "available":
            True,

        "recording":
            recording,

        "current_recording":
            current_recording,

        "completed_recording_count":
            completed_count,

        "total_recording_count":
            total_count,

        # Warning state.
        "active_warning":
            False,

        "severity":
            "clear",

        "warning_count":
            0,

        "last_warning":
            None,

        "last_warning_time":
            None,

        "report_version":
            None,

        # Common device fields promoted to top level.
        "battery_level":
            battery.get("level"),

        "plugged_in":
            battery.get(
                "is_plugged_in"
            ),

        "rayhunter_version":
            runtime.get(
                "rayhunter_version"
            ),

        "system_os":
            runtime.get(
                "system_os"
            ),

        "arch":
            runtime.get(
                "arch"
            ),

        # Exact current Rayhunter system-stats sections.
        "disk_stats":
            disk_stats,

        "memory_stats":
            memory_stats,

        "runtime_metadata":
            runtime,

        "battery_status":
            battery,

        # Bounded recording metadata.
        "current_entry":
            current,

        "latest_completed_entry":
            latest_completed,

        # Exact source endpoint names, useful for diagnostics.
        "source_endpoints": [
            "/api/system-stats",
            "/api/qmdl-manifest",
            (
                "/api/analysis-report/live"
                if recording
                else None
            ),
        ],
    }

    # Remove null endpoint marker.
    status["source_endpoints"] = [
        endpoint
        for endpoint
        in status["source_endpoints"]
        if endpoint is not None
    ]

    if recording:

        report = http_get(
            "/api/analysis-report/live"
        )

        status.update(
            parse_report(report)
        )

    return status


def build_raw() -> dict[str, Any]:
    """
    Return exact upstream JSON payloads.

    This endpoint is for manual diagnostics and is NOT polled by
    Home Assistant, because the historical manifest can grow large.
    """

    return {
        "system_stats":
            json_get(
                "/api/system-stats"
            ),

        "qmdl_manifest":
            json_get(
                "/api/qmdl-manifest"
            ),
    }


class Handler(
    BaseHTTPRequestHandler
):
    """Read-only internal Rayhunter Bridge API."""

    server_version = (
        "RayhunterBridge/1.1"
    )

    def log_message(
        self,
        _format: str,
        *_args: Any,
    ) -> None:
        """Suppress standard HTTP request logging."""

        return

    def send_json(
        self,
        status_code: int,
        value: Any,
    ) -> None:
        """Send a JSON response."""

        body = json.dumps(
            value,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode(
            "utf-8"
        )

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    def do_GET(
        self,
    ) -> None:
        """Handle supported GET endpoints."""

        if self.path not in (
            "/api/status",
            "/api/raw",
            "/healthz",
        ):
            self.send_json(
                404,
                {
                    "error":
                        "not found",
                },
            )

            return

        try:

            if self.path == "/api/raw":
                self.send_json(
                    200,
                    build_raw(),
                )

                return

            status = build_status()

        except Exception as exc:

            print(
                "[bridge] "
                f"request failed: {exc}",
                flush=True,
            )

            self.send_json(
                503,
                {
                    "available":
                        False,

                    "error":
                        str(exc),
                },
            )

            return

        if self.path == "/healthz":

            self.send_json(
                200,
                {
                    "ok":
                        True,

                    "api_version":
                        API_VERSION,

                    "bridge_version":
                        BRIDGE_VERSION,
                },
            )

            return

        global _last_summary

        warning = (
            "ON"
            if status[
                "active_warning"
            ]
            else "OFF"
        )

        summary = (
            "hb=ok "
            f"recording="
            f"{'yes' if status['recording'] else 'no'} "
            f"severity={status['severity']} "
            f"warning={warning} "
            f"count={status['warning_count']} "
            f"recordings={status['total_recording_count']}"
        )

        if summary != _last_summary:

            print(
                summary,
                flush=True,
            )

            _last_summary = (
                summary
            )

        self.send_json(
            200,
            status,
        )


def stop(
    _sig: int,
    _frame: Any,
) -> None:
    """Handle container shutdown."""

    _shutdown.set()


def main() -> None:
    """Run the bridge API."""

    signal.signal(
        signal.SIGINT,
        stop,
    )

    signal.signal(
        signal.SIGTERM,
        stop,
    )

    server = ThreadingHTTPServer(
        (
            API_BIND,
            API_PORT,
        ),
        Handler,
    )

    server.timeout = 0.5

    print(
        "[bridge] local API listening on "
        f"{API_BIND}:{API_PORT}; "
        "MQTT not used",
        flush=True,
    )

    try:

        while not _shutdown.is_set():

            server.handle_request()

    finally:

        server.server_close()


if __name__ == "__main__":
    main()
