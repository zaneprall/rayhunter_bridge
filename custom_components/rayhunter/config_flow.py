"""Config flow for Rayhunter."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)
from homeassistant.helpers.service_info.hassio import (
    HassioServiceInfo,
)

from .api import (
    RayhunterApiError,
    RayhunterClient,
)
from .const import (
    CONF_BASE_URL,
    DEFAULT_BASE_URL,
    DOMAIN,
)


async def validate_input(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> dict[str, str]:
    """Validate a Rayhunter Bridge connection."""

    session = async_get_clientsession(
        hass
    )

    client = RayhunterClient(
        session,
        data[CONF_BASE_URL],
    )

    status = await (
        client.async_get_status()
    )

    device_id = str(
        status.get(
            "device_id"
        )
        or "rayhunter"
    )

    device_name = str(
        status.get(
            "device_name"
        )
        or "Rayhunter"
    )

    return {
        "device_id":
            device_id,

        "device_name":
            device_name,
    }


class RayhunterConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle Rayhunter configuration."""

    VERSION = 1

    def __init__(
        self,
    ) -> None:
        """Initialize flow state."""

        self._discovered_data: (
            dict[str, str] | None
        ) = None

        self._discovered_name: (
            str | None
        ) = None


    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle manually initiated setup."""

        errors: dict[str, str] = {}

        if user_input is not None:

            base_url = (
                str(
                    user_input[
                        CONF_BASE_URL
                    ]
                )
                .strip()
                .rstrip("/")
            )

            user_input = {
                CONF_BASE_URL:
                    base_url,
            }

            try:

                info = await validate_input(
                    self.hass,
                    user_input,
                )

            except RayhunterApiError:

                errors["base"] = (
                    "cannot_connect"
                )

            except Exception:

                errors["base"] = (
                    "unknown"
                )

            else:

                await self.async_set_unique_id(
                    info["device_id"]
                )

                self._abort_if_unique_id_configured(
                    updates={
                        CONF_BASE_URL:
                            base_url,
                    }
                )

                return self.async_create_entry(
                    title=
                        info["device_name"],

                    data=
                        user_input,
                )

        return self.async_show_form(
            step_id=
                "user",

            data_schema=
                vol.Schema(
                    {
                        vol.Required(
                            CONF_BASE_URL,
                            default=
                                DEFAULT_BASE_URL,
                        ):
                            str,
                    }
                ),

            errors=
                errors,
        )


    async def async_step_hassio(
        self,
        discovery_info: HassioServiceInfo,
    ) -> ConfigFlowResult:
        """Handle Supervisor app discovery."""

        base_url = str(
            discovery_info.config.get(
                CONF_BASE_URL,
                "",
            )
        ).strip().rstrip("/")

        if not base_url:

            return self.async_abort(
                reason=
                    "invalid_discovery_info"
            )

        try:

            info = await validate_input(
                self.hass,
                {
                    CONF_BASE_URL:
                        base_url,
                },
            )

        except RayhunterApiError:

            return self.async_abort(
                reason=
                    "cannot_connect"
            )

        except Exception:

            return self.async_abort(
                reason=
                    "unknown"
            )

        await self.async_set_unique_id(
            info["device_id"]
        )

        self._abort_if_unique_id_configured(
            updates={
                CONF_BASE_URL:
                    base_url,
            }
        )

        self._discovered_data = {
            CONF_BASE_URL:
                base_url,
        }

        self._discovered_name = (
            info["device_name"]
        )

        self.context[
            "title_placeholders"
        ] = {
            "name":
                self._discovered_name,
        }

        return await (
            self.async_step_hassio_confirm()
        )


    async def async_step_hassio_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Confirm a Supervisor-discovered bridge."""

        if (
            self._discovered_data
            is None
            or self._discovered_name
            is None
        ):
            return self.async_abort(
                reason=
                    "invalid_discovery_info"
            )

        if user_input is not None:

            return self.async_create_entry(
                title=
                    self._discovered_name,

                data=
                    self._discovered_data,
            )

        return self.async_show_form(
            step_id=
                "hassio_confirm",

            data_schema=
                vol.Schema({}),

            description_placeholders={
                "name":
                    self._discovered_name,

                "url":
                    self._discovered_data[
                        CONF_BASE_URL
                    ],
            },
        )
