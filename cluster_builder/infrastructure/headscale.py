from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


@dataclass
class HeadscaleConfig:
    #Configuration required to connect to Headscale.

    base_url: str
    api_key: str
    timeout: int = 10


class HeadscaleError(Exception):
    """Base exception for Headscale client errors."""


class HeadscaleConnectionError(HeadscaleError):
    """Raised when Headscale cannot be reached."""


class HeadscaleAuthenticationError(HeadscaleError):
    """Raised when Headscale rejects authentication."""


class HeadscaleAPIError(HeadscaleError):
    """Raised when Headscale returns an HTTP error."""


class HeadscaleResponseError(HeadscaleError):
    """Raised when Headscale returns an unexpected response."""


class HeadscaleClient:
    """Client for Headscale REST API operations."""

    def __init__(self, config: HeadscaleConfig):
        if not config.base_url.strip():
            raise ValueError("Headscale base URL cannot be empty.")

        if not config.api_key.strip():
            raise ValueError("Headscale API key cannot be empty.")

        if config.timeout <= 0:
            raise ValueError("Request timeout must be greater than zero.")

        self.base_url = config.base_url.rstrip("/")
        self.timeout = config.timeout
        self.session = requests.Session()

        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }
        )

        # Retry temporary server errors on GET requests only.
        retry = Retry(
            total=3,
            connect=3,
            read=0,
            status=3,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )

        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ------------------------------------------------------------------
    # Internal request handling
    # ------------------------------------------------------------------

    def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        """Send an HTTP request and translate common errors."""

        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)

        except requests.exceptions.Timeout as exc:
            logger.warning("Headscale request timed out: %s", url)
            raise HeadscaleConnectionError(
                f"Headscale request timed out after {self.timeout} seconds."
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.warning("Unable to connect to Headscale: %s", url)
            raise HeadscaleConnectionError(
                f"Unable to connect to Headscale at {self.base_url}."
            ) from exc

        except requests.exceptions.RequestException as exc:
            logger.exception("Headscale request failed: %s", url)
            raise HeadscaleError(
                f"Headscale request failed: {exc}"
            ) from exc

        if response.status_code in (401, 403):
            logger.warning(
                "Headscale authentication rejected (HTTP %s).",
                response.status_code,
            )
            raise HeadscaleAuthenticationError(
                "Headscale authentication failed. Check the API key "
                "and its permissions."
            )

        if not response.ok:
            logger.warning(
                "Headscale API returned HTTP %s for %s.",
                response.status_code,
                url,
            )
            raise HeadscaleAPIError(
                f"Headscale API returned HTTP {response.status_code} "
                f"for {method} {url}."
            )

        return response

    def _json(self, response: requests.Response) -> dict[str, Any]:
        """Parse a JSON response and verify its top-level structure."""

        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("Headscale returned invalid JSON.")
            raise HeadscaleResponseError(
                "Headscale returned an invalid JSON response."
            ) from exc

        if not isinstance(data, dict):
            raise HeadscaleResponseError(
                "Unexpected Headscale response: expected a JSON object."
            )

        return data

    def _list_from_response(
        self, response: requests.Response, field: str
    ) -> list[dict[str, Any]]:
        """Extract and validate a list from a JSON response."""

        data = self._json(response)
        items = data.get(field, [])

        if not isinstance(items, list) or not all(
            isinstance(item, dict) for item in items
        ):
            raise HeadscaleResponseError(
                f"Unexpected Headscale response: '{field}' "
                "must be a list of objects."
            )

        return items

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def create_user(self, name: str) -> dict[str, Any]:
        """Create a Headscale user."""

        response = self._request(
            "POST",
            f"{self.base_url}/api/v1/user",
            json={"name": name},
        )
        return self._json(response)

    def list_users(self) -> list[dict[str, Any]]:
        """Return all Headscale users."""

        response = self._request(
            "GET",
            f"{self.base_url}/api/v1/user",
        )
        return self._list_from_response(response, "users")

    def delete_user(self, user_id: str) -> None:
        """Delete a Headscale user."""

        encoded_id = quote(user_id, safe="")
        self._request(
            "DELETE",
            f"{self.base_url}/api/v1/user/{encoded_id}",
        )

    # ------------------------------------------------------------------
    # Pre-authentication keys
    # ------------------------------------------------------------------

    def create_preauth_key(
        self,
        user: str,
        reusable: bool = False,
        ephemeral: bool = False,
    ) -> dict[str, Any]:
        """Create a Headscale pre-authentication key."""

        response = self._request(
            "POST",
            f"{self.base_url}/api/v1/preauthkey",
            json={
                "user": user,
                "reusable": reusable,
                "ephemeral": ephemeral,
            },
        )
        return self._json(response)

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    def list_nodes(self) -> list[dict[str, Any]]:
        """Return all Headscale nodes."""

        response = self._request(
            "GET",
            f"{self.base_url}/api/v1/node",
        )
        return self._list_from_response(response, "nodes")

    def delete_node(self, node_id: str) -> None:
        """Delete a Headscale node."""

        encoded_id = quote(node_id, safe="")
        self._request(
            "DELETE",
            f"{self.base_url}/api/v1/node/{encoded_id}",
        )