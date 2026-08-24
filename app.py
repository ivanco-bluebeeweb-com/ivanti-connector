"""Ivanti Connector extension declaration.

Ivanti Service Manager (ISM) / Neurons for ITSM exposes its Business Object data
model through an OData-conventions REST API. Auth: OAuth2 client-credentials (cloud)
or Basic Auth (on-prem/legacy).
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "ivanti-connector",
    version="0.1.0",
    display_name="Ivanti",
    description=(
        "Connect your own Ivanti Service Manager (ISM) / Neurons for ITSM tenant to "
        "manage Incidents, Service Requests, Problems, Changes, Configuration Items, "
        "and Knowledge Articles through the OData Business Object API, plus a generic "
        "BO passthrough."
    ),
    icon="icon.svg",
    capabilities=["ivanti:read", "ivanti:write"],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="ivanti",
    description=(
        "Ivanti Connector — manage Incidents, Service Requests, Problems, Changes, "
        "Configuration Items, and Knowledge Articles through the ISM OData Business "
        "Object API."
    ),
)

ext.secret(
    "ivanti_connections",
    "JSON list of connected Ivanti Service Manager tenants and encrypted credentials. Managed only through connect_ivanti and disconnect_ivanti.",
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=90,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Report whether at least one Ivanti tenant is configured."""
    raw = await ctx.secrets.get("ivanti_connections")
    import json
    try:
        connections = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        connections = []
    if not connections:
        return {"healthy": True, "detail": "No Ivanti tenant connected yet."}
    return {"healthy": True, "detail": f"{len(connections)} tenant(s) connected."}
