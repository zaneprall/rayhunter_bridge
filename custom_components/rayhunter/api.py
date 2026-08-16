"""HTTP client for the Rayhunter Bridge add-on."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError, ClientSession


class RayhunterApiError(Exception):
    """Base exception for Rayhunter Bridge communication."""


class RayhunterClient:
    """Client for the local Rayhunter Bridge API."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
    ) -> None:
        """Initialize the client."""

        self._session = session
        self._base_url = base_url.rstrip("/")

    async def async_get_status(self) -> dict[str, Any]:
        """Fetch current Rayhunter state."""

        url = f"{self._base_url}/api/status"

        try:
            async with asyncio.timeout(8):
                response = await self._session.get(url)

                if response.status != 200:
                    body = await response.text()

                    raise RayhunterApiError(
                        f"Bridge returned HTTP {response.status}: "
                        f"{body[:300]}"
                    )

                data = await response.json()

        except TimeoutError as exc:
            raise RayhunterApiError(
                "Timed out communicating with Rayhunter Bridge"
            ) from exc

        except ClientError as exc:
            raise RayhunterApiError(
                f"Unable to communicate with Rayhunter Bridge: {exc}"
            ) from exc

        except ValueError as exc:
            raise RayhunterApiError(
                "Rayhunter Bridge returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise RayhunterApiError(
                "Rayhunter Bridge returned an invalid response"
            )

        if data.get("available") is not True:
            raise RayhunterApiError(
                str(
                    data.get("error")
                    or "Rayhunter is unavailable"
                )
            )

        return data
