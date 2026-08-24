"""Chat functions for Ivanti Connector."""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import ivanti_client as ic
from app import chat
from schemas import (
    AuditHealthParams, ChangeRequest, ChangeRequestList, ConfigItem,
    ConfigItemList, ConnectIvantiParams, ConnectionList, ConnectionRefParams,
    CreateChangeParams, CreateIncidentParams, CreateProblemParams,
    CreateServiceRequestParams, DeleteResult, DisconnectIvantiParams,
    GenericBOParams, GenericCreateParams, GenericRecord, GenericRecordList,
    GenericRecordParams, GenericUpdateParams, HealthAudit, Incident,
    IncidentList, IvantiConnection, KnowledgeArticle, KnowledgeArticleList,
    ListChangesParams, ListCIsParams, ListIncidentsParams,
    ListKnowledgeParams, ListProblemsParams, ListServiceRequestsParams,
    NoParams, Problem, ProblemList, RecIdParams, ServiceRequest,
    ServiceRequestList, UpdateChangeParams, UpdateIncidentParams,
    UpdateProblemParams, UpdateServiceRequestParams,
)

_SECRET_NAME = "ivanti_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


def _connection_entity(connection: dict) -> IvantiConnection:
    label = connection.get("label") or connection.get("host", "")
    return IvantiConnection(
        id=connection.get("id", ""), title=label, label=label,
        host=connection.get("host", ""), auth_mode=connection.get("auth_mode", "basic"),
        connected=True,
    )


def _find_connection(connections: list[dict], connection_id: str) -> dict | None:
    if not connections:
        return None
    if not connection_id:
        return connections[0]
    for c in connections:
        if c.get("id") == connection_id:
            return c
    return None


def _client_from(connection: dict) -> ic.IvantiClient:
    return ic.IvantiClient(
        connection.get("host", ""), connection.get("auth_mode", "basic"),
        username=connection.get("username", ""), password=connection.get("password", ""),
        client_id=connection.get("client_id", ""), client_secret=connection.get("client_secret", ""),
        token_url=connection.get("token_url", ""),
    )


async def _resolve_client(ctx, connection_id: str) -> tuple[dict, ic.IvantiClient]:
    connections = await _load_connections(ctx)
    connection = _find_connection(connections, connection_id)
    if not connection:
        raise ic.IvantiError("No Ivanti tenant connected yet. Use connect_ivanti first.")
    return connection, _client_from(connection)


@chat.function("connect_ivanti", "Connect an Ivanti Service Manager (ISM) tenant via OAuth2 or Basic Auth, after validating connectivity.", action_type="write", chain_callable=True, data_model=IvantiConnection, event="ivanti-connector.connect_ivanti", effects=["ivanti.provider.connected"])
async def connect_ivanti(ctx, params: ConnectIvantiParams) -> ActionResult:
    """Imperal action: connect_ivanti."""
    try:
        client = ic.IvantiClient(
            params.host, params.auth_mode, username=params.username, password=params.password,
            client_id=params.client_id, client_secret=params.client_secret, token_url=params.token_url,
        )
        await client.ping()
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_CONNECT_FAILED", retryable=exc.retryable)
    connections = await _load_connections(ctx)
    connection = {
        "id": str(uuid.uuid4()), "label": params.label, "host": client.base_url,
        "auth_mode": params.auth_mode, "username": params.username, "password": params.password,
        "client_id": params.client_id, "client_secret": params.client_secret, "token_url": params.token_url,
    }
    connections.append(connection)
    await _save_connections(ctx, connections)
    return ActionResult.success(data=_connection_entity(connection), summary=f"Connected to {client.base_url}.")


@chat.function("disconnect_ivanti", "Remove a saved Ivanti tenant connection.", action_type="write", chain_callable=True, data_model=DeleteResult, event="ivanti-connector.disconnect_ivanti", effects=["ivanti.provider.disconnected"])
async def disconnect_ivanti(ctx, params: DisconnectIvantiParams) -> ActionResult:
    """Imperal action: disconnect_ivanti."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("Connection not found.", code="IVANTI_CONNECTION_NOT_FOUND", retryable=False)
    await _save_connections(ctx, remaining)
    return ActionResult.success(data=DeleteResult(id=params.connection_id, deleted=True), summary="Disconnected.")


@chat.function("list_connections", "List all connected Ivanti tenants.", action_type="read", chain_callable=True, data_model=ConnectionList, event="ivanti-connector.list_connections")
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """Imperal action: list_connections."""
    connections = await _load_connections(ctx)
    return ActionResult.success(data=ConnectionList(connections=[_connection_entity(c) for c in connections]))


def _to_incident(item: dict) -> Incident:
    return Incident(
        rec_id=str(item.get("RecId", item.get("rec_id", ""))),
        title=item.get("Subject", str(item.get("RecId", ""))),
        subject=item.get("Subject", ""), status=item.get("Status", ""),
        urgency=item.get("Urgency", ""), raw=item,
    )


@chat.function("list_incidents", "List incidents on the connected Ivanti tenant, optionally filtered by an OData expression.", action_type="read", chain_callable=True, data_model=IncidentList, event="ivanti-connector.list_incidents")
async def list_incidents(ctx, params: ListIncidentsParams) -> ActionResult:
    """Imperal action: list_incidents."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_incidents(odata_filter=params.odata_filter, limit=params.limit)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_LIST_INCIDENTS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=IncidentList(incidents=[_to_incident(i) for i in items]))


@chat.function("get_incident", "Read one incident in full by record id.", action_type="read", chain_callable=True, data_model=Incident, event="ivanti-connector.get_incident")
async def get_incident(ctx, params: RecIdParams) -> ActionResult:
    """Imperal action: get_incident."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get_incident(params.rec_id)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_GET_INCIDENT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_incident(item))


@chat.function("create_incident", "Create a new incident.", action_type="write", chain_callable=True, data_model=Incident, event="ivanti-connector.create_incident", effects=["create:incident"])
async def create_incident(ctx, params: CreateIncidentParams) -> ActionResult:
    """Imperal action: create_incident."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_incident(params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_CREATE_INCIDENT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_incident(item), summary="Incident created.")


@chat.function("update_incident", "Update selected fields of an existing incident. Only given fields are changed.", action_type="write", chain_callable=True, data_model=Incident, event="ivanti-connector.update_incident", effects=["update:incident"])
async def update_incident(ctx, params: UpdateIncidentParams) -> ActionResult:
    """Imperal action: update_incident."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_incident(params.rec_id, params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_UPDATE_INCIDENT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_incident(item), summary="Incident updated.")


def _to_request(item: dict) -> ServiceRequest:
    return ServiceRequest(
        rec_id=str(item.get("RecId", "")), title=str(item.get("RecId", "")),
        subject=item.get("Subject", ""), status=item.get("Status", ""), raw=item,
    )


@chat.function("list_service_requests", "List service requests on the connected Ivanti tenant.", action_type="read", chain_callable=True, data_model=ServiceRequestList, event="ivanti-connector.list_service_requests")
async def list_service_requests(ctx, params: ListServiceRequestsParams) -> ActionResult:
    """Imperal action: list_service_requests."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_service_requests(odata_filter=params.odata_filter, limit=params.limit)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_LIST_REQUESTS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ServiceRequestList(requests=[_to_request(i) for i in items]))


@chat.function("get_service_request", "Read one service request in full by record id.", action_type="read", chain_callable=True, data_model=ServiceRequest, event="ivanti-connector.get_service_request")
async def get_service_request(ctx, params: RecIdParams) -> ActionResult:
    """Imperal action: get_service_request."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get_service_request(params.rec_id)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_GET_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_request(item))


@chat.function("create_service_request", "Create a new service request.", action_type="write", chain_callable=True, data_model=ServiceRequest, event="ivanti-connector.create_service_request", effects=["create:service_request"])
async def create_service_request(ctx, params: CreateServiceRequestParams) -> ActionResult:
    """Imperal action: create_service_request."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_service_request(params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_CREATE_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_request(item), summary="Service request created.")


@chat.function("update_service_request", "Update selected fields of an existing service request.", action_type="write", chain_callable=True, data_model=ServiceRequest, event="ivanti-connector.update_service_request", effects=["update:service_request"])
async def update_service_request(ctx, params: UpdateServiceRequestParams) -> ActionResult:
    """Imperal action: update_service_request."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_service_request(params.rec_id, params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_UPDATE_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_request(item), summary="Service request updated.")


def _to_problem(item: dict) -> Problem:
    return Problem(
        rec_id=str(item.get("RecId", "")), title=str(item.get("RecId", "")),
        subject=item.get("Subject", ""), status=item.get("Status", ""), raw=item,
    )


@chat.function("list_problems", "List problems on the connected Ivanti tenant.", action_type="read", chain_callable=True, data_model=ProblemList, event="ivanti-connector.list_problems")
async def list_problems(ctx, params: ListProblemsParams) -> ActionResult:
    """Imperal action: list_problems."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_problems(odata_filter=params.odata_filter, limit=params.limit)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_LIST_PROBLEMS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ProblemList(problems=[_to_problem(i) for i in items]))


@chat.function("create_problem", "Create a new problem record.", action_type="write", chain_callable=True, data_model=Problem, event="ivanti-connector.create_problem", effects=["create:problem"])
async def create_problem(ctx, params: CreateProblemParams) -> ActionResult:
    """Imperal action: create_problem."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_problem(params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_CREATE_PROBLEM_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_problem(item), summary="Problem created.")


@chat.function("update_problem", "Update selected fields of an existing problem.", action_type="write", chain_callable=True, data_model=Problem, event="ivanti-connector.update_problem", effects=["update:problem"])
async def update_problem(ctx, params: UpdateProblemParams) -> ActionResult:
    """Imperal action: update_problem."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_problem(params.rec_id, params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_UPDATE_PROBLEM_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_problem(item), summary="Problem updated.")


def _to_change(item: dict) -> ChangeRequest:
    return ChangeRequest(
        rec_id=str(item.get("RecId", "")), title=str(item.get("RecId", "")),
        subject=item.get("Subject", ""), status=item.get("Status", ""), raw=item,
    )


@chat.function("list_changes", "List change requests on the connected Ivanti tenant.", action_type="read", chain_callable=True, data_model=ChangeRequestList, event="ivanti-connector.list_changes")
async def list_changes(ctx, params: ListChangesParams) -> ActionResult:
    """Imperal action: list_changes."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_changes(odata_filter=params.odata_filter, limit=params.limit)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_LIST_CHANGES_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ChangeRequestList(changes=[_to_change(i) for i in items]))


@chat.function("create_change", "Create a new change request.", action_type="write", chain_callable=True, data_model=ChangeRequest, event="ivanti-connector.create_change", effects=["create:change"])
async def create_change(ctx, params: CreateChangeParams) -> ActionResult:
    """Imperal action: create_change."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_change(params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_CREATE_CHANGE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_change(item), summary="Change request created.")


@chat.function("update_change", "Update selected fields of an existing change request.", action_type="write", chain_callable=True, data_model=ChangeRequest, event="ivanti-connector.update_change", effects=["update:change"])
async def update_change(ctx, params: UpdateChangeParams) -> ActionResult:
    """Imperal action: update_change."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_change(params.rec_id, params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_UPDATE_CHANGE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_change(item), summary="Change request updated.")


@chat.function("list_cmdb_cis", "List Configuration Items (CIs) from the Ivanti CMDB, optionally filtered.", action_type="read", chain_callable=True, data_model=ConfigItemList, event="ivanti-connector.list_cmdb_cis")
async def list_cmdb_cis(ctx, params: ListCIsParams) -> ActionResult:
    """Imperal action: list_cmdb_cis."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_cis(odata_filter=params.odata_filter, limit=params.limit)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_LIST_CIS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ConfigItemList(items=[
        ConfigItem(rec_id=str(i.get("RecId", "")), title=i.get("Name", str(i.get("RecId", ""))), ci_type=i.get("Type", ""), status=i.get("Status", ""), raw=i) for i in items
    ]))


@chat.function("list_knowledge_articles", "List knowledge base articles on the connected Ivanti tenant.", action_type="read", chain_callable=True, data_model=KnowledgeArticleList, event="ivanti-connector.list_knowledge_articles")
async def list_knowledge_articles(ctx, params: ListKnowledgeParams) -> ActionResult:
    """Imperal action: list_knowledge_articles."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_knowledge_articles(limit=params.limit)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_LIST_KNOWLEDGE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=KnowledgeArticleList(articles=[
        KnowledgeArticle(rec_id=str(i.get("RecId", "")), title=i.get("Subject", str(i.get("RecId", ""))), raw=i) for i in items
    ]))


@chat.function("list_table", "List records from any Ivanti Business Object by name -- a generic passthrough for objects not covered by typed wrappers.", action_type="read", chain_callable=True, data_model=GenericRecordList, event="ivanti-connector.list_table")
async def list_table(ctx, params: GenericBOParams) -> ActionResult:
    """Imperal action: list_table."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_entries(params.bo_name, odata_filter=params.odata_filter, limit=params.limit)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_LIST_TABLE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=GenericRecordList(records=[
        GenericRecord(rec_id=str(i.get("RecId", "")), title=str(i.get("RecId", "")), raw=i) for i in items
    ]))


@chat.function("get_record", "Read one record from any Ivanti Business Object by record id.", action_type="read", chain_callable=True, data_model=GenericRecord, event="ivanti-connector.get_record")
async def get_record(ctx, params: GenericRecordParams) -> ActionResult:
    """Imperal action: get_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get_entry(params.bo_name, params.rec_id)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_GET_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=GenericRecord(rec_id=params.rec_id, title=params.rec_id, raw=item))


@chat.function("create_record", "Create a new record on any Ivanti Business Object -- a generic passthrough for objects not covered by typed wrappers.", action_type="write", chain_callable=True, data_model=GenericRecord, event="ivanti-connector.create_record", effects=["create:record"])
async def create_record(ctx, params: GenericCreateParams) -> ActionResult:
    """Imperal action: create_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_entry(params.bo_name, params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_CREATE_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=GenericRecord(rec_id=str(item.get("RecId", "")), title=str(item.get("RecId", "")), raw=item), summary="Record created.")


@chat.function("update_record", "Update fields on any Ivanti Business Object record by id.", action_type="write", chain_callable=True, data_model=GenericRecord, event="ivanti-connector.update_record", effects=["update:record"])
async def update_record(ctx, params: GenericUpdateParams) -> ActionResult:
    """Imperal action: update_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_entry(params.bo_name, params.rec_id, params.values)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_UPDATE_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=GenericRecord(rec_id=params.rec_id, title=params.rec_id, raw=item), summary="Record updated.")


@chat.function("delete_record", "Delete a record from any Ivanti Business Object by id. Irreversible.", action_type="write", chain_callable=True, data_model=DeleteResult, event="ivanti-connector.delete_record", effects=["delete:record"])
async def delete_record(ctx, params: GenericRecordParams) -> ActionResult:
    """Imperal action: delete_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.delete_entry(params.bo_name, params.rec_id)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_DELETE_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=DeleteResult(id=params.rec_id, deleted=True), summary="Record deleted.")


@chat.function("audit_instance_health", "Build one aggregated health report across the connected Ivanti tenant: open incidents, service requests, problems, and changes.", action_type="read", chain_callable=True, data_model=HealthAudit, event="ivanti-connector.audit_instance_health")
async def audit_instance_health(ctx, params: AuditHealthParams) -> ActionResult:
    """Imperal action: audit_instance_health."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        incidents = await client.list_incidents(limit=100)
        requests = await client.list_service_requests(limit=100)
        problems = await client.list_problems(limit=100)
        changes = await client.list_changes(limit=100)
    except ic.IvantiError as exc:
        return ActionResult.error(str(exc), code="IVANTI_AUDIT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=HealthAudit(
        open_incident_count=len(incidents), open_service_request_count=len(requests),
        open_problem_count=len(problems), open_change_count=len(changes),
    ), summary=f"{len(incidents)} incident(s), {len(requests)} request(s), {len(problems)} problem(s), {len(changes)} change(s) open.")
