"""Thin OData REST client for Ivanti Service Manager (ISM).

Auth: OAuth2 client-credentials (cloud) or Basic Auth (on-prem). Data: generic
Business Object API /api/odata/businessobject/{boName}.
"""
from __future__ import annotations

import base64
from typing import Any

import httpx


class IvantiError(RuntimeError):
    """A safe provider-facing error; never includes credentials."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


_BO_INCIDENT = "Incident#"
_BO_SERVICE_REQ = "ServiceReq#"
_BO_PROBLEM = "Problem#"
_BO_CHANGE = "ChangeReq#"
_BO_CI = "CI#"
_BO_KNOWLEDGE = "KnowledgeArticle#"


class IvantiClient:
    """REST client for Ivanti ISM's OData Business Object API."""

    def __init__(self, host: str, auth_mode: str, *, username: str = "", password: str = "",
                 client_id: str = "", client_secret: str = "", token_url: str = "",
                 timeout: float = 30.0):
        url = (host or "").strip().rstrip("/")
        if not url:
            raise IvantiError("Tenant host is required, e.g. 'https://acme.ivanticloud.com'.")
        if not url.startswith("http"):
            url = f"https://{url}"
        self.base_url = url
        self.auth_mode = (auth_mode or "basic").lower()
        self.username = username or ""
        self.password = password or ""
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""
        self.token_url = token_url or f"{self.base_url}/oauth/token"
        self.timeout = timeout
        self._token: str | None = None
        if self.auth_mode == "oauth2" and not (self.client_id and self.client_secret):
            raise IvantiError("OAuth2 mode requires both client_id and client_secret.")
        if self.auth_mode == "basic" and not (self.username and self.password):
            raise IvantiError("Basic Auth mode requires both username and password.")

    async def _get_oauth_token(self) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    self.token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except httpx.TimeoutException:
                raise IvantiError("Connection to Ivanti Identity Broker timed out.", retryable=True)
            except httpx.RequestError as exc:
                raise IvantiError(f"Could not reach Ivanti Identity Broker: {exc}", retryable=True)
        if resp.status_code == 401:
            raise IvantiError("Invalid client_id/client_secret.")
        if resp.status_code >= 400:
            raise IvantiError(f"OAuth2 token request failed ({resp.status_code}).", retryable=resp.status_code >= 500)
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise IvantiError("OAuth2 response did not include an access_token.")
        return token

    def _auth_header(self) -> dict:
        if self.auth_mode == "oauth2":
            return {"Authorization": f"Bearer {self._token}"}
        raw = f"{self.username}:{self.password}".encode("utf-8")
        return {"Authorization": f"Basic {base64.b64encode(raw).decode('ascii')}"}

    async def request(self, method: str, path: str, *, params: dict | None = None,
                       json_body: dict | None = None, _retry: bool = True) -> Any:
        if self.auth_mode == "oauth2" and not self._token:
            self._token = await self._get_oauth_token()
        headers = {"Accept": "application/json", **self._auth_header()}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.request(method, url, params=params, json=json_body, headers=headers)
            except httpx.TimeoutException:
                raise IvantiError("Connection to Ivanti Service Manager timed out.", retryable=True)
            except httpx.RequestError as exc:
                raise IvantiError(f"Could not reach Ivanti Service Manager: {exc}", retryable=True)
        if resp.status_code == 401 and self.auth_mode == "oauth2" and _retry:
            self._token = await self._get_oauth_token()
            return await self.request(method, path, params=params, json_body=json_body, _retry=False)
        if resp.status_code == 401:
            raise IvantiError("Authentication failed -- check your Ivanti credentials.")
        if resp.status_code == 403:
            raise IvantiError("Not authorized for this operation on the connected tenant.")
        if resp.status_code == 404:
            raise IvantiError("Record or business object not found.")
        if resp.status_code >= 500:
            raise IvantiError(f"Ivanti Service Manager server error ({resp.status_code}).", retryable=True)
        if resp.status_code >= 400:
            raise IvantiError(f"Ivanti Service Manager request failed ({resp.status_code}): {resp.text[:300]}")
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    async def ping(self) -> dict:
        return await self.request("GET", "/api/odata/businessobject/Employee#", params={"$top": 1})

    async def list_entries(self, bo_name: str, *, odata_filter: str = "", limit: int = 50) -> list[dict]:
        params: dict = {"$top": limit}
        if odata_filter:
            params["$filter"] = odata_filter
        data = await self.request("GET", f"/api/odata/businessobject/{bo_name}", params=params)
        return data.get("value", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

    async def get_entry(self, bo_name: str, rec_id: str) -> dict:
        return await self.request("GET", f"/api/odata/businessobject/{bo_name}({rec_id})")

    async def create_entry(self, bo_name: str, values: dict) -> dict:
        return await self.request("POST", f"/api/odata/businessobject/{bo_name}", json_body=values)

    async def update_entry(self, bo_name: str, rec_id: str, values: dict) -> dict:
        await self.request("PATCH", f"/api/odata/businessobject/{bo_name}({rec_id})", json_body=values)
        return await self.get_entry(bo_name, rec_id)

    async def delete_entry(self, bo_name: str, rec_id: str) -> None:
        await self.request("DELETE", f"/api/odata/businessobject/{bo_name}({rec_id})")

    async def list_incidents(self, *, odata_filter: str = "", limit: int = 50) -> list[dict]:
        return await self.list_entries(_BO_INCIDENT, odata_filter=odata_filter, limit=limit)

    async def get_incident(self, rec_id: str) -> dict:
        return await self.get_entry(_BO_INCIDENT, rec_id)

    async def create_incident(self, values: dict) -> dict:
        return await self.create_entry(_BO_INCIDENT, values)

    async def update_incident(self, rec_id: str, values: dict) -> dict:
        return await self.update_entry(_BO_INCIDENT, rec_id, values)

    async def list_service_requests(self, *, odata_filter: str = "", limit: int = 50) -> list[dict]:
        return await self.list_entries(_BO_SERVICE_REQ, odata_filter=odata_filter, limit=limit)

    async def get_service_request(self, rec_id: str) -> dict:
        return await self.get_entry(_BO_SERVICE_REQ, rec_id)

    async def create_service_request(self, values: dict) -> dict:
        return await self.create_entry(_BO_SERVICE_REQ, values)

    async def update_service_request(self, rec_id: str, values: dict) -> dict:
        return await self.update_entry(_BO_SERVICE_REQ, rec_id, values)

    async def list_problems(self, *, odata_filter: str = "", limit: int = 50) -> list[dict]:
        return await self.list_entries(_BO_PROBLEM, odata_filter=odata_filter, limit=limit)

    async def create_problem(self, values: dict) -> dict:
        return await self.create_entry(_BO_PROBLEM, values)

    async def update_problem(self, rec_id: str, values: dict) -> dict:
        return await self.update_entry(_BO_PROBLEM, rec_id, values)

    async def list_changes(self, *, odata_filter: str = "", limit: int = 50) -> list[dict]:
        return await self.list_entries(_BO_CHANGE, odata_filter=odata_filter, limit=limit)

    async def create_change(self, values: dict) -> dict:
        return await self.create_entry(_BO_CHANGE, values)

    async def update_change(self, rec_id: str, values: dict) -> dict:
        return await self.update_entry(_BO_CHANGE, rec_id, values)

    async def list_cis(self, *, odata_filter: str = "", limit: int = 50) -> list[dict]:
        return await self.list_entries(_BO_CI, odata_filter=odata_filter, limit=limit)

    async def list_knowledge_articles(self, *, limit: int = 50) -> list[dict]:
        return await self.list_entries(_BO_KNOWLEDGE, limit=limit)
