"""
Placeholder client for all Headscale REST API operations used by

"""

from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass
class HeadscaleConfig:
    base_url: str
    api_key: str


class HeadscaleClient:
    """
    Placeholder client for all Headscale REST API operations used by
    cluster-builder. Extend this class with one method per Headscale
    operation as they're needed (user provisioning, node listing,
    preauth key issuance, etc).
    """

    def __init__(self, config: HeadscaleConfig):
        self.base_url = config.base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {config.api_key}"})

    # TODO(error-handling placeholders):
    # - Validate Headscale service reachability before API calls
    #   (for example: check that the Headscale VM/service is active).
    # - Add request timeouts and retries for transient network failures.
    # - Convert HTTP errors (4xx/5xx) into clear domain exceptions.
    # - Handle auth failures (expired/invalid API key) with actionable messages.
    # - Handle malformed JSON/unexpected response payloads safely.
    # - Add structured logs for request/response failures.
    
    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def create_user(self, name: str) -> dict:
        """TODO: POST to the Headscale user creation endpoint."""
        raise NotImplementedError

    def list_users(self) -> list[dict]:
        """TODO: GET the Headscale user list endpoint."""
        raise NotImplementedError

    def delete_user(self, user_id: str) -> None:
        """TODO: DELETE a Headscale user."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Preauth keys
    # ------------------------------------------------------------------
    def create_preauth_key(
        self, user: str, reusable: bool = False, ephemeral: bool = False
    ) -> dict:
        """TODO: POST to create a preauth key for a given user."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------
    def list_nodes(self) -> list[dict]:
        """TODO: GET the Headscale node list endpoint."""
        raise NotImplementedError

    def delete_node(self, node_id: str) -> None:
        """TODO: DELETE a Headscale node (e.g. on edge node teardown)."""
        raise NotImplementedError
