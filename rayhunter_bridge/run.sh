#!/command/with-contenv bashio
set -euo pipefail

export HOME="/data"
mkdir -p "${HOME}/.android"

HTTP_TIMEOUT="$(bashio::config 'http_timeout' || echo 3)"
HTTP_RETRIES="$(bashio::config 'http_retries' || echo 3)"
HTTP_BACKOFF_BASE="$(bashio::config 'http_backoff_base' || echo 0.4)"

DEVICE_ID="$(bashio::config 'device_id' || echo rayhunter_orbic)"
DEVICE_NAME="$(bashio::config 'device_name' || echo 'Rayhunter (Orbic)')"
ADB_SERIAL="$(bashio::config 'adb_serial' || true)"

export RAYHUNTER_BASE="http://127.0.0.1:18080"
export DEVICE_ID
export DEVICE_NAME
export HTTP_TIMEOUT
export HTTP_RETRIES
export HTTP_BACKOFF_BASE

bashio::log.info "============================================================"
bashio::log.info "Rayhunter Bridge startup"
bashio::log.info "============================================================"
bashio::log.info "Device: ${DEVICE_NAME}"
bashio::log.info "Device ID: ${DEVICE_ID}"
bashio::log.info "Configured ADB serial: ${ADB_SERIAL:-<automatic>}"

bashio::log.info "============================================================"
bashio::log.info "USB diagnostics"
bashio::log.info "============================================================"

bashio::log.info "lsusb output:"
lsusb || bashio::log.warning "lsusb failed"

bashio::log.info "Raw /dev/bus/usb device nodes:"

if [ -d /dev/bus/usb ]; then
    find /dev/bus/usb \
        -mindepth 2 \
        -maxdepth 2 \
        -type c \
        -exec ls -l {} \; \
        2>/dev/null || true
else
    bashio::log.error "/dev/bus/usb does not exist inside the app"
fi

bashio::log.info "============================================================"
bashio::log.info "ADB initialization"
bashio::log.info "============================================================"

bashio::log.info "ADB version:"
adb version || true

adb start-server
sleep 2

bashio::log.info "ADB device list:"
adb devices -l || true

ADB_CMD=(adb)

if [ -n "${ADB_SERIAL:-}" ]; then
    ADB_CMD+=( -s "${ADB_SERIAL}" )
fi

if [ -n "${ADB_SERIAL:-}" ]; then

    ADB_STATE="$(
        "${ADB_CMD[@]}" get-state 2>/dev/null || true
    )"

    if [ "${ADB_STATE}" != "device" ]; then
        bashio::log.error \
            "Configured ADB device '${ADB_SERIAL}' is not usable. State: ${ADB_STATE:-not found}"

        bashio::log.error "Current ADB device list:"
        adb devices -l || true

        exit 1
    fi

else

    DEVICE_COUNT="$(
        adb devices |
        awk '
            NR > 1 && $2 == "device" {
                count++
            }
            END {
                print count+0
            }
        '
    )"

    UNAUTHORIZED_COUNT="$(
        adb devices |
        awk '
            NR > 1 && $2 == "unauthorized" {
                count++
            }
            END {
                print count+0
            }
        '
    )"

    OFFLINE_COUNT="$(
        adb devices |
        awk '
            NR > 1 && $2 == "offline" {
                count++
            }
            END {
                print count+0
            }
        '
    )"

    if [ "${UNAUTHORIZED_COUNT}" -gt 0 ]; then
        bashio::log.error \
            "ADB can see the USB device, but at least one device is unauthorized."
        exit 1
    fi

    if [ "${OFFLINE_COUNT}" -gt 0 ]; then
        bashio::log.error \
            "ADB can see the USB device, but at least one device is offline."
        exit 1
    fi

    if [ "${DEVICE_COUNT}" -eq 0 ]; then
        bashio::log.error \
            "No usable ADB devices were detected."
        exit 1
    fi

    if [ "${DEVICE_COUNT}" -gt 1 ]; then
        bashio::log.error \
            "Multiple usable ADB devices were detected. Set adb_serial to select the Orbic."

        adb devices -l || true

        exit 1
    fi
fi

bashio::log.info "ADB target is online."

bashio::log.info "ADB target serial:"
"${ADB_CMD[@]}" get-serialno || true

bashio::log.info "ADB target state:"
"${ADB_CMD[@]}" get-state || true

bashio::log.info "============================================================"
bashio::log.info "ADB port forwarding"
bashio::log.info "============================================================"

"${ADB_CMD[@]}" forward \
    --remove tcp:18080 \
    2>/dev/null || true

if "${ADB_CMD[@]}" forward tcp:18080 tcp:8080; then

    bashio::log.info \
        "ADB forwarding established: 127.0.0.1:18080 -> Orbic:8080"

else

    bashio::log.error \
        "Unable to establish ADB port forwarding."

    exit 1
fi

bashio::log.info "Current ADB forwarding table:"
adb forward --list || true

bashio::log.info "============================================================"
bashio::log.info "Rayhunter HTTP test"
bashio::log.info "============================================================"

python3 - <<'PY'
import sys
import time
import urllib.request

url = "http://127.0.0.1:18080/api/system-stats"

for attempt in range(1, 6):
    try:
        with urllib.request.urlopen(
            url,
            timeout=3,
        ) as response:
            body = (
                response
                .read(1024)
                .decode(
                    "utf-8",
                    "replace",
                )
            )

            status = response.status

        print(
            "[startup] Rayhunter HTTP reachable: "
            f"status={status} body={body!r}",
            flush=True,
        )

        sys.exit(0)

    except Exception as exc:
        print(
            "[startup] Rayhunter HTTP attempt "
            f"{attempt}/5 failed: {exc}",
            flush=True,
        )

        if attempt < 5:
            time.sleep(2)

print(
    "[startup] WARNING: ADB forwarding succeeded, "
    "but /api/system-stats was not reachable.",
    flush=True,
)
PY


keep_forward() {

    while true; do

        sleep 10

        STATE="$(
            "${ADB_CMD[@]}" get-state \
                2>/dev/null || true
        )"

        if [ "${STATE}" != "device" ]; then

            bashio::log.warning \
                "ADB target unavailable; current state: ${STATE:-not found}"

            continue
        fi

        if ! \
            "${ADB_CMD[@]}" forward --list \
                2>/dev/null |
            grep -q 'tcp:18080'
        then

            bashio::log.warning \
                "ADB forwarding disappeared; restoring it."

            if \
                "${ADB_CMD[@]}" forward \
                    tcp:18080 \
                    tcp:8080
            then

                bashio::log.info \
                    "ADB forwarding restored: 127.0.0.1:18080 -> Orbic:8080"

            else

                bashio::log.warning \
                    "Unable to restore ADB forwarding."
            fi
        fi
    done
}


bridge_ready() {

    python3 - <<'PY'
import sys
import urllib.request

try:
    with urllib.request.urlopen(
        "http://127.0.0.1:8099/healthz",
        timeout=2,
    ) as response:
        sys.exit(
            0
            if response.status == 200
            else 1
        )

except Exception:
    sys.exit(1)
PY
}


shutdown() {

    bashio::log.info \
        "Stopping Rayhunter Bridge."

    if [ -n "${BRIDGE_PID:-}" ]; then
        kill -TERM \
            "${BRIDGE_PID}" \
            2>/dev/null || true

        wait \
            "${BRIDGE_PID}" \
            2>/dev/null || true
    fi
}


keep_forward &

bashio::log.info "============================================================"
bashio::log.info "Starting Rayhunter local API bridge"
bashio::log.info "============================================================"

python3 \
    /opt/rayhunter/rayhunter_bridge.py &

BRIDGE_PID="$!"

trap shutdown SIGTERM SIGINT


bashio::log.info \
    "Waiting for bridge API readiness."

BRIDGE_READY=false

for attempt in $(seq 1 20); do

    if bridge_ready; then
        BRIDGE_READY=true
        break
    fi

    if ! kill -0 \
        "${BRIDGE_PID}" \
        2>/dev/null
    then
        bashio::log.error \
            "Rayhunter Bridge process exited during startup."

        wait "${BRIDGE_PID}"
        exit $?
    fi

    sleep 0.5
done


if [ "${BRIDGE_READY}" = "true" ]; then

    bashio::log.info \
        "Bridge API is ready."

    BRIDGE_URL="http://$(hostname):8099"

    DISCOVERY_CONFIG="$(
        bashio::var.json \
            base_url \
            "${BRIDGE_URL}"
    )"

    if \
        bashio::discovery \
            "rayhunter" \
            "${DISCOVERY_CONFIG}" \
            >/dev/null
    then

        bashio::log.info \
            "Published Rayhunter discovery information: ${BRIDGE_URL}"

    else

        bashio::log.warning \
            "Unable to publish Rayhunter discovery information."

        bashio::log.warning \
            "The bridge remains available for manual Home Assistant configuration."
    fi

else

    bashio::log.error \
        "Bridge API did not become ready."

    shutdown
    exit 1
fi


wait "${BRIDGE_PID}"
