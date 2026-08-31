"""Pydantic input contracts and SDL result entities for Ivanti Connector."""
from __future__ import annotations

from imperal_sdk import sdl
from pydantic import BaseModel, Field


class NoParams(BaseModel):
    pass


class ConnectionRefParams(BaseModel):
    connection_id: str = Field("", description="Optional saved Ivanti connection ID. Omit to use the first connected tenant.")


class ConnectIvantiParams(BaseModel):
    label: str = Field("", description="Friendly tenant label, e.g. 'Acme Production'.")
    host: str = Field(..., description="Ivanti ISM tenant host, e.g. 'https://acme.ivanticloud.com' (cloud) or 'https://host' (on-prem).")
    auth_mode: str = Field("basic", description="Authentication mode: 'oauth2' (Ivanti Identity Broker, cloud) or 'basic' (service account, on-prem/legacy).")
    username: str = Field("", description="Service account username. Required when auth_mode is 'basic'.")
    password: str = Field("", description="Service account password. Required when auth_mode is 'basic'.")
    client_id: str = Field("", description="OAuth2 client id. Required when auth_mode is 'oauth2'.")
    client_secret: str = Field("", description="OAuth2 client secret. Required when auth_mode is 'oauth2'.")
    token_url: str = Field("", description="Optional OAuth2 token URL override. Defaults to '<host>/oauth/token'.")


class DisconnectIvantiParams(ConnectionRefParams):
    connection_id: str = Field(..., description="Saved Ivanti connection ID to remove from Imperal.")


class RecIdParams(ConnectionRefParams):
    rec_id: str = Field(..., description="Business Object record id (RecId), e.g. 'INC0012345'.")


class ListIncidentsParams(ConnectionRefParams):
    odata_filter: str = Field("", description="Optional OData $filter expression, e.g. \"Status eq 'Open'\".")
    limit: int = Field(50, description="Max records to return.")


class CreateIncidentParams(ConnectionRefParams):
    values: dict = Field(..., description="Business Object field name/value pairs for the new incident, e.g. {'Subject': '...', 'Urgency': 'High'}.")


class UpdateIncidentParams(RecIdParams):
    values: dict = Field(..., description="Business Object field name/value pairs to update, e.g. {'Status': 'Resolved'}.")


class ListServiceRequestsParams(ConnectionRefParams):
    odata_filter: str = Field("", description="Optional OData $filter expression.")
    limit: int = Field(50, description="Max records to return.")


class CreateServiceRequestParams(ConnectionRefParams):
    values: dict = Field(..., description="Business Object field name/value pairs for the new service request.")


class UpdateServiceRequestParams(RecIdParams):
    values: dict = Field(..., description="Business Object field name/value pairs to update.")


class ListProblemsParams(ConnectionRefParams):
    odata_filter: str = Field("", description="Optional OData $filter expression.")
    limit: int = Field(50, description="Max records to return.")


class CreateProblemParams(ConnectionRefParams):
    values: dict = Field(..., description="Business Object field name/value pairs for the new problem.")


class UpdateProblemParams(RecIdParams):
    values: dict = Field(..., description="Business Object field name/value pairs to update.")


class ListChangesParams(ConnectionRefParams):
    odata_filter: str = Field("", description="Optional OData $filter expression.")
    limit: int = Field(50, description="Max records to return.")


class CreateChangeParams(ConnectionRefParams):
    values: dict = Field(..., description="Business Object field name/value pairs for the new change request.")


class UpdateChangeParams(RecIdParams):
    values: dict = Field(..., description="Business Object field name/value pairs to update.")


class ListCIsParams(ConnectionRefParams):
    odata_filter: str = Field("", description="Optional OData $filter expression, e.g. \"CIType eq 'Server'\".")
    limit: int = Field(50, description="Max records to return.")


class ListKnowledgeParams(ConnectionRefParams):
    limit: int = Field(50, description="Max records to return.")


class GenericBOParams(ConnectionRefParams):
    bo_name: str = Field(..., description="Exact Ivanti Business Object name, e.g. 'Incident#'.")
    odata_filter: str = Field("", description="Optional OData $filter expression.")
    limit: int = Field(50, description="Max records to return.")


class GenericRecordParams(ConnectionRefParams):
    bo_name: str = Field(..., description="Exact Ivanti Business Object name.")
    rec_id: str = Field(..., description="Record id (RecId).")


class GenericCreateParams(ConnectionRefParams):
    bo_name: str = Field(..., description="Exact Ivanti Business Object name.")
    values: dict = Field(..., description="Field name/value pairs for the new record.")


class GenericUpdateParams(GenericRecordParams):
    values: dict = Field(..., description="Field name/value pairs to update.")


class AuditHealthParams(ConnectionRefParams):
    pass


class IvantiConnection(sdl.Entity):
    id: str
    title: str
    label: str = ""
    host: str = ""
    auth_mode: str = "basic"
    connected: bool = True


class ConnectionList(sdl.Entity):
    id: str = "connections"
    title: str = "Ivanti connections"
    connections: list[IvantiConnection] = []


class DeleteResult(sdl.Entity):
    title: str = ""
    id: str
    deleted: bool = True


class Incident(sdl.Entity):
    id: str = ""
    rec_id: str
    title: str
    subject: str = ""
    status: str = ""
    urgency: str = ""
    raw: dict = {}


class IncidentList(sdl.Entity):
    id: str = "incidents"
    title: str = "Incidents"
    incidents: list[Incident] = []


class ServiceRequest(sdl.Entity):
    id: str = ""
    rec_id: str
    title: str
    subject: str = ""
    status: str = ""
    raw: dict = {}


class ServiceRequestList(sdl.Entity):
    id: str = "requests"
    title: str = "Service requests"
    requests: list[ServiceRequest] = []


class Problem(sdl.Entity):
    id: str = ""
    rec_id: str
    title: str
    subject: str = ""
    status: str = ""
    raw: dict = {}


class ProblemList(sdl.Entity):
    id: str = "problems"
    title: str = "Problems"
    problems: list[Problem] = []


class ChangeRequest(sdl.Entity):
    id: str = ""
    rec_id: str
    title: str
    subject: str = ""
    status: str = ""
    raw: dict = {}


class ChangeRequestList(sdl.Entity):
    id: str = "changes"
    title: str = "Change requests"
    changes: list[ChangeRequest] = []


class ConfigItem(sdl.Entity):
    id: str = ""
    rec_id: str
    title: str
    ci_type: str = ""
    status: str = ""
    raw: dict = {}


class ConfigItemList(sdl.Entity):
    id: str = "cis"
    title: str = "Configuration items"
    items: list[ConfigItem] = []


class KnowledgeArticle(sdl.Entity):
    id: str = ""
    rec_id: str
    title: str
    raw: dict = {}


class KnowledgeArticleList(sdl.Entity):
    id: str = "knowledge"
    title: str = "Knowledge articles"
    articles: list[KnowledgeArticle] = []


class GenericRecord(sdl.Entity):
    id: str = ""
    rec_id: str
    title: str
    raw: dict = {}


class GenericRecordList(sdl.Entity):
    id: str = "records"
    title: str = "Records"
    records: list[GenericRecord] = []


class HealthAudit(sdl.Entity):
    id: str = "audit"
    title: str = "Ivanti health audit"
    open_incident_count: int = 0
    open_service_request_count: int = 0
    open_problem_count: int = 0
    open_change_count: int = 0
    raw: dict = {}
