# Home Assistant official base image.
# Includes S6 Overlay, Bashio, and TempIO.
FROM ghcr.io/home-assistant/base:3.24

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="app"

# No third-party Python packages are required.
RUN apk add --no-cache \
    android-tools \
    python3 \
    usbutils

WORKDIR /opt/rayhunter

COPY rayhunter_bridge.py /opt/rayhunter/rayhunter_bridge.py
COPY run.sh /run.sh

RUN chmod +x /run.sh

CMD ["/run.sh"]
