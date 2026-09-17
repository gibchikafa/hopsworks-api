"""One HTTP door for the whole client.

Every resource handle talks through this: it knows the project's base URL, how
the caller is entitled to talk to it, and how a refusal is turned into an error
that says which rule refused and why -- the API's own message, never a bare
status. Paths are relative to ``/hopsworks-api/api/project/{id}``, so the same
transport reaches the evaluation API and the tracing API.
"""

from __future__ import annotations

import os
from typing import Any

from ..api import EvalApiError, _StaticAuth, hopsworks_session


TIMEOUT_S = 60


class AgentEvalsError(EvalApiError):
    """A refusal from the API, carrying the reason it gave and the status."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def _message(response: Any) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(body, dict):
        return (
            body.get("usrMsg") or body.get("errorMsg") or f"HTTP {response.status_code}"
        )
    return f"HTTP {response.status_code}"


class Transport:
    def __init__(
        self,
        host: str,
        project_id: int,
        *,
        api_key: str | None = None,
        verify: bool | str = True,
        session: Any = None,
    ):
        self.host = host.rstrip("/")
        self.project_id = int(project_id)
        self.base = f"{self.host}/hopsworks-api/api/project/{self.project_id}"
        if session is not None:
            self._session = session
        elif api_key:
            import requests

            self._session = requests.Session()
            self._session.auth = _StaticAuth("ApiKey " + api_key)
            self._session.verify = verify
        else:
            # whatever this container has: a job's JWT, a notebook's connected client
            self._session = hopsworks_session()
            if verify is not True:
                self._session.verify = verify

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        clean = None
        if params:
            # None means "not given", never the string "None"
            clean = {k: v for k, v in params.items() if v is not None} or None
        response = self._session.request(
            method, self.base + path, params=clean, json=json, timeout=TIMEOUT_S
        )
        if response.status_code >= 400:
            raise AgentEvalsError(_message(response), response.status_code)
        if not getattr(response, "content", b""):
            return None
        return response.json()

    def get(self, path: str, **params: Any) -> Any:
        return self.request("GET", path, params=params or None)

    def post(self, path: str, json: Any = None, **params: Any) -> Any:
        return self.request("POST", path, params=params or None, json=json)

    def put(self, path: str, json: Any = None, **params: Any) -> Any:
        return self.request("PUT", path, params=params or None, json=json)

    def delete(self, path: str, **params: Any) -> Any:
        return self.request("DELETE", path, params=params or None)


def host_from_env() -> str:
    host = os.environ.get("HOPSWORKS_HOST") or os.environ.get("REST_ENDPOINT")
    if not host:
        raise AgentEvalsError("no host: pass host= or set HOPSWORKS_HOST")
    if not host.startswith("http"):
        host = "https://" + host
    return host


class HopsworksClientSession:
    """A ``requests``-shaped session over the connected hopsworks client.

    Inside Hopsworks -- a job, a notebook, ``hopsworks.login()`` -- the client
    already holds the caller's token and the cluster's certificates, so the
    evaluation client borrows it rather than building a second one. Only what
    :class:`Transport` calls is implemented: ``request`` returning an object
    with ``status_code``, ``content`` and ``json()``.
    """

    def __init__(self, client: Any):
        self._client = client

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        timeout: float | None = None,
    ) -> Any:
        import json as json_module  # noqa: PLC0415

        from hopsworks_common.client.exceptions import RestAPIError  # noqa: PLC0415

        # the client adds the scheme, host and "hopsworks-api/api" itself
        marker = "/hopsworks-api/api/"
        path = url.split(marker, 1)[1] if marker in url else url.lstrip("/")
        path_params = [segment for segment in path.split("/") if segment]
        headers = {"content-type": "application/json"} if json is not None else None
        try:
            body = self._client._send_request(
                method,
                path_params,
                query_params=params,
                headers=headers,
                data=None if json is None else json_module.dumps(json),
                timeout=timeout,
            )
        except RestAPIError as err:
            return _ClientResponse(err.response.status_code, _error_body(err))
        return _ClientResponse(200, body)


class _ClientResponse:
    def __init__(self, status_code: int, body: Any):
        self.status_code = status_code
        self._body = body
        self.content = b"" if body is None else b"x"

    def json(self) -> Any:
        return self._body


def _error_body(err: Any) -> dict[str, Any]:
    try:
        body = err.response.json()
        return body if isinstance(body, dict) else {"errorMsg": str(body)}
    except Exception:  # noqa: BLE001 -- a body that is not JSON still has a status
        return {"errorMsg": str(err)}


def connected_transport() -> Transport | None:
    """A transport over the connected hopsworks client, or None when nothing is connected."""
    try:
        from hopsworks_common import client as hopsworks_client  # noqa: PLC0415

        instance = hopsworks_client.get_instance()
    except Exception:  # noqa: BLE001 -- not connected, or the library is not there
        return None
    if instance is None:
        return None
    project_id = getattr(instance, "_project_id", None)
    base_url = getattr(instance, "_base_url", None) or ""
    if project_id is None:
        return None
    host = base_url.split("/hopsworks-api", 1)[0] if base_url else "https://hopsworks"
    return Transport(host, int(project_id), session=HopsworksClientSession(instance))
