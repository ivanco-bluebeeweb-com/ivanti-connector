"""Ivanti Connector panels."""
from __future__ import annotations

from imperal_sdk import ui

import handlers as h
from app import ext


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="label"),
        node,
    ])


@ext.panel("ivanti_sidebar", slot="left", title="Ivanti")
async def ivanti_sidebar(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Text("Connect your Ivanti Service Manager tenant", variant="subtitle"),
            ui.Form(action="connect_ivanti", submit_label="Connect", children=[
                _field("Tenant label", ui.Input(param_name="label", placeholder="Acme Production")),
                _field("Tenant host", ui.Input(param_name="host", placeholder="https://acme.ivanticloud.com")),
                _field("Auth mode", ui.Select(param_name="auth_mode", options=["basic", "oauth2"], value="basic")),
                _field("Username", ui.Input(param_name="username", placeholder="service.account")),
                _field("Password", ui.Input(param_name="password", placeholder="Service account password")),
                _field("OAuth client ID (if OAuth2)", ui.Input(param_name="client_id", placeholder="Identity Broker client ID")),
                _field("OAuth client secret (if OAuth2)", ui.Input(param_name="client_secret", placeholder="Identity Broker client secret")),
            ]),
            ui.Button("How do I get OAuth2 credentials?", variant="ghost", size="sm", icon="HelpCircle",
                      on_click=ui.Call("__panel__ivanti_connect_help")),
        ])
    conn = connections[0]
    label = conn.get("label") or conn.get("host", "")
    return ui.Stack(direction="v", gap=2, align="stretch", children=[
        ui.Text(label, variant="subtitle"),
        ui.Divider(),
        ui.Button("Incidents", variant="ghost", on_click=ui.Call("__panel__ivanti_center", view="incidents")),
        ui.Button("Service requests", variant="ghost", on_click=ui.Call("__panel__ivanti_center", view="requests")),
        ui.Button("Problems", variant="ghost", on_click=ui.Call("__panel__ivanti_center", view="problems")),
        ui.Button("Changes", variant="ghost", on_click=ui.Call("__panel__ivanti_center", view="changes")),
        ui.Button("CMDB", variant="ghost", on_click=ui.Call("__panel__ivanti_center", view="cmdb")),
        ui.Button("Knowledge", variant="ghost", on_click=ui.Call("__panel__ivanti_center", view="knowledge")),
        ui.Divider(),
        ui.Button("App settings", variant="ghost", icon="Settings",
                  on_click=ui.Call("__panel__ivanti_settings")),
    ])


@ext.panel("ivanti_connect_help", slot="center", title="Connecting Ivanti", icon="HelpCircle", center_overlay=True)
async def ivanti_connect_help(ctx, **kwargs) -> ui.UINode:
    return ui.Stack(direction="v", gap=2, align="stretch", children=[
        ui.Header(text="Connecting your Ivanti tenant", level=2),
        ui.Text("Cloud tenants (Ivanti Neurons) typically use OAuth2 client-credentials via the Identity Broker -- ask your Ivanti admin for a client ID and secret. On-prem or legacy tenants usually accept Basic Auth with a service account instead.", variant="body"),
        ui.Text("Tenant host format differs by deployment: cloud is usually 'https://<tenant>.ivanticloud.com', on-prem is your own server URL.", variant="body"),
        ui.Callout(text="Credentials are stored encrypted and used only to call your tenant's ISM REST API on your behalf. OAuth2 tokens are refreshed automatically when expired.", type="info"),
    ])


@ext.panel("ivanti_center", slot="center", title="Ivanti", icon="Ticket", center_overlay=True)
async def ivanti_center(ctx, view: str = "incidents", **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Text("Connect an Ivanti tenant first.", variant="body")

    if view == "requests":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Service requests", level=2),
            ui.Form(action="list_service_requests", submit_label="List requests", children=[
                _field("OData filter (optional)", ui.Input(param_name="odata_filter", placeholder="Status eq 'Open'")),
            ]),
            ui.Divider(),
            ui.Text("Create service request", variant="subtitle"),
            ui.Form(action="create_service_request", submit_label="Create", children=[
                _field("Field values (JSON)", ui.Input(param_name="values", placeholder='{"Subject": "New laptop request"}')),
            ]),
        ])

    if view == "problems":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Problems", level=2),
            ui.Form(action="list_problems", submit_label="List problems", children=[
                _field("OData filter (optional)", ui.Input(param_name="odata_filter", placeholder="Status eq 'Open'")),
            ]),
            ui.Divider(),
            ui.Text("Create problem", variant="subtitle"),
            ui.Form(action="create_problem", submit_label="Create", children=[
                _field("Field values (JSON)", ui.Input(param_name="values", placeholder='{"Subject": "Recurring VPN drops"}')),
            ]),
        ])

    if view == "changes":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Change requests", level=2),
            ui.Form(action="list_changes", submit_label="List changes", children=[
                _field("OData filter (optional)", ui.Input(param_name="odata_filter", placeholder="Status eq 'Scheduled'")),
            ]),
            ui.Divider(),
            ui.Text("Create change request", variant="subtitle"),
            ui.Form(action="create_change", submit_label="Create", children=[
                _field("Field values (JSON)", ui.Input(param_name="values", placeholder='{"Subject": "Upgrade firewall firmware"}')),
            ]),
        ])

    if view == "cmdb":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="CMDB", level=2),
            ui.Form(action="list_cmdb_cis", submit_label="List configuration items", children=[
                _field("OData filter (optional)", ui.Input(param_name="odata_filter", placeholder="Type eq 'Server'")),
            ]),
        ])

    if view == "knowledge":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Knowledge base", level=2),
            ui.Form(action="list_knowledge_articles", submit_label="List articles", children=[]),
        ])

    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Header(text="Incidents", level=2),
        ui.Form(action="list_incidents", submit_label="List incidents", children=[
            _field("OData filter (optional)", ui.Input(param_name="odata_filter", placeholder="Status eq 'Open'")),
        ]),
        ui.Divider(),
        ui.Text("Create incident", variant="subtitle"),
        ui.Form(action="create_incident", submit_label="Create", children=[
            _field("Field values (JSON)", ui.Input(param_name="values", placeholder='{"Subject": "Email server down", "Urgency": "High"}')),
        ]),
        ui.Divider(),
        ui.Text("Health snapshot", variant="subtitle"),
        ui.Form(action="audit_instance_health", submit_label="Run health audit", children=[]),
    ])
