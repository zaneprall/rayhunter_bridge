#!/command/with-contenv bashio
set -euo pipefail

# ---- Read options from Supervisor ( /data/options.json ) ----
MQTT_HOST="$(bashio::config 'mqtt_host' || true)"
MQTT_PORT="$(bashio::config 'mqtt_port' || echo 1883)"
MQTT_USER="$(bashio::config 'mqtt_user' || true)"
MQTT_PASS="$(bashio::config 'mqtt_pass' || true)"
DISCOVERY_PREFIX="$(bashio::config 'discovery_prefix' || echo homeassistant)"

POLL_INTERVAL="$(bashio::config 'poll_interval' || echo 3)"
HTTP_TIMEOUT="$(bashio::config 'http_timeout' || echo 3)"
HTTP_RETRIES="$(bashio::config 'http_retries' || echo 3)"
HTTP_BACKOFF_BASE="$(bashio::config 'http_backoff_base' || echo 0.4)"

DEVICE_ID="$(bashio::config 'device_id' || echo rayhunter_orbic)"
DEVICE_NAME="$(bashio::config 'device_name' || echo 'Rayhunter (Orbic)')"
ADB_SERIAL="$(bashio::config 'adb_serial' || true)"

ALERT_ON_NEW="$(bashio::config 'alert_on_new' || echo false)"
FORCE_ALERT_SECS="$(bashio::config 'force_alert_secs' || echo 0)"
AUTOCLEAR_SECS="$(bashio::config 'autoclear_secs' || echo 0)"

# ---- Export env consumed by rayhunter_bridge.py ----
export RAYHUNTER_BASE="http://127.0.0.1:18080"
export DISCOVERY_PREFIX="$DISCOVERY_PREFIX"
export DEVICE_ID DEVICE_NAME
export POLL_INTERVAL HTTP_TIMEOUT HTTP_RETRIES HTTP_BACKOFF_BASE
export FORCE_ALERT_SECS AUTOCLEAR_SECS
[ "$ALERT_ON_NEW" = "true" ] && export ALERT_ON_NEW=1 || true

if [ -n "${MQTT_HOST:-}" ]; then
  export MQTT_HOST="$MQTT_HOST" MQTT_PORT="$MQTT_PORT"
  [ -n "${MQTT_USER:-}" ] && export MQTT_USER
  [ -n "${MQTT_PASS:-}" ] && export MQTT_PASS
fi

bashio::log.info "MQTT target: ${MQTT_HOST:-<disabled>}:${MQTT_PORT:-}"
bashio::log.info "Device: ${DEVICE_NAME} (id=${DEVICE_ID})  ADB serial: ${ADB_SERIAL:-auto}"

# ---- USB diagnostics (one-time) ----
bashio::log.info "USB devices:"
lsusb || true
bashio::log.info "USB bus perms:"
ls -l /dev/bus/usb || true

# ---- ADB forward keeper ----
adb start-server || true

pick_serial() {
  # Prefer configured serial; otherwise pick the first available ADB target.
  if [ -n "${ADB_SERIAL:-}" ]; then
    echo "${ADB_SERIAL}"
    return 0
  fi
  adb devices 2>/dev/null     | awk 'NR>1 && $1!="" {print $1; exit}'
}

forward_exists() {
  local serial="$1"
  if [ -n "${serial}" ]; then
    adb forward --list 2>/dev/null       | awk -v s="${serial}" '$1==s && $2=="tcp:18080" && $3=="tcp:8080"{found=1} END{exit(found?0:1)}'
  else
    adb forward --list 2>/dev/null       | awk '$2=="tcp:18080" && $3=="tcp:8080"{found=1} END{exit(found?0:1)}'
  fi
}

ensure_forward() {
  local serial="$1"
  if [ -n "${serial}" ]; then
    adb -s "${serial}" forward tcp:18080 tcp:8080
  else
    adb forward tcp:18080 tcp:8080
  fi
}

keep_forward() {
  while true; do
    ACTIVE_SERIAL="$(pick_serial || true)"

    if forward_exists "${ACTIVE_SERIAL}"; then
      :
    else
      if ensure_forward "${ACTIVE_SERIAL}"; then
        bashio::log.info "Port-forward 18080->8080 active${ACTIVE_SERIAL:+ (serial=${ACTIVE_SERIAL})}"
      else
        bashio::log.warning "adb forward failed${ACTIVE_SERIAL:+ (serial=${ACTIVE_SERIAL})}; will retry"
      fi
    fi
    sleep 5
  done
}
keep_forward &

# ---- Sanity: paho version ----
python3 - <<'PY'
try:
    import paho.mqtt.client as m
    print(f"[startup] paho-mqtt {m.__version__}", flush=True)
except Exception as e:
    print("[startup] paho-mqtt import FAILED:", e, flush=True)
PY

# ---- Run bridge ----
exec python3 /opt/rayhunter/rayhunter_bridge.py
