# Ivanti Connector — Connector Discovery

**Discovery date:** 2026-08-24
**Release scope:** maximum functionality against the publicly documented Ivanti Service
Manager (ISM) / Neurons for ITSM REST API (per standing "максимальный функционал" instruction).
**Related task:** BBW Imperal Apps #2443.

## 1. What Ivanti Service Manager actually is

Ivanti Service Manager (ISM, formerly HEAT/FrontRange) is a business-object-model ITSM
platform. Every record type — Incident, Service Request, Problem, Change, Employee,
Configuration Item — is a **Business Object (BO)** defined in the ISM data model
(e.g. `Incident#`, `ServiceReq#`, `Problem#`, `ChangeReq#`, `Employee#`, `CI#`), similar
in spirit to ServiceNow tables / BMC Helix AR forms. Ivanti exposes this model through a
**REST API following the OData v2/v4 conventions**, letting any business object be
listed/read/created/updated/deleted generically, plus authentication via OAuth2 (Ivanti
Identity Broker) or Basic Auth depending on deployment (cloud vs on-prem).

## 2. Chosen integration surface

**Ivanti ISM REST API** (`/api/odata/businessobject/{boName}` on the tenant host):
- **Auth**: OAuth2 client-credentials against the tenant's Identity Broker (cloud), or
  Basic Auth with a service account (on-prem/legacy). Token used as
  `Authorization: Bearer <token>` (OAuth2) or `Authorization: Basic <b64>` (Basic).
- **Generic Business Object API**: `/api/odata/businessobject/{boName}` — GET (list,
  with OData `$filter`/`$top`/`$select`), POST (create); `/api/odata/businessobject/{boName}({recId})`
  — GET (read one), PATCH (update), DELETE (delete). This generic surface is the
  ServiceNow-Table-API / AR-System-Entry-API equivalent for Ivanti, targeting:
  `Incident#` (incidents), `ServiceReq#` (service requests), `Problem#` (problems),
  `ChangeReq#` (changes), `Employee#` (people/requesters), `CI#` (configuration items),
  `KnowledgeArticle#` (knowledge).
- **OData query syntax**: `$filter=Status eq 'Open'`, `$top=50`, `$select=...` — Ivanti's
  own filtering language, distinct from ServiceNow's sysparm_query and AR System's
  qualification syntax.

## 3. Scope decision

Typed wrappers for the Tier-1 ITSM objects (Incident/Problem/Change/ServiceReq/CI/
Knowledge) plus a generic Business Object passthrough (list/get/create/update/delete by
BO name) for anything else the tenant's data model exposes (custom BOs, HR/Facilities
modules on the same platform, etc.) — mirroring the ServiceNow and BMC Helix connectors'
generic-passthrough pattern for forward compatibility without per-tenant customization.

## 4. Auth model decision

OAuth2 client-credentials is the primary supported flow (Ivanti Neurons cloud tenants);
Basic Auth with a service account is offered as a fallback for on-prem/legacy ISM
deployments that don't have Identity Broker configured — both validated with a real
`GET` against a lightweight endpoint before saving.
