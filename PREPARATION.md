# Ivanti Connector — Preparation

**Version:** 0.1.0 (planning)
**Date:** 2026-08-24
**Related task:** BBW Imperal Apps #2443
**Scope decision:** maximum feasible capability against the publicly documented Ivanti
Service Manager (ISM) OData REST API (per standing "максимальный функционал" instruction).

## 1. App passport

**Name:** Ivanti Connector
**One-line purpose:** Connect your own Ivanti Service Manager (ISM) / Neurons for ITSM
tenant to manage Incidents, Service Requests, Problems, Changes, Configuration Items,
and Knowledge Articles through the OData Business Object API, plus a generic BO
passthrough for anything else your tenant's data model exposes.

**What it is not:**
- Not an Ivanti Neurons Discovery/Patch/UEM connector — ITSM (Service Manager) scope only.
- Not a workflow/BO-designer replacement — no schema/form editing.
- Does not model every possible custom Business Object with typed schemas — Tier-1
  ITSM objects get typed wrappers; everything else via the honest generic passthrough.

## 2. Human problem

> An IT service desk agent or ITSM admin at a company running Ivanti Service Manager
> needs to look up, create, and update incidents/requests/problems/changes without
> switching to the ISM console — especially for quick triage, bulk updates, or a daily
> health snapshot.

### Personas
| Persona | Trigger | Value |
|---|---|---|
| Service desk agent | "What's the status of my ticket?" | Instant lookup without opening ISM console |
| ITSM admin | Needs to bulk-close a batch of resolved incidents | Bulk wrapper over generic BO API |
| Ops engineer | Wants a daily open-ticket snapshot | audit_instance_health value-add report |
| Change manager | Needs to see changes awaiting approval | list_changes filtered by status |

## 3. Auth & connection model

OAuth2 client-credentials against the tenant's Identity Broker (primary, cloud) or Basic
Auth with a service account (fallback, on-prem/legacy) — both validated with a real GET
before saving, same dual-mode pattern used successfully in ServiceNow Connector.

## 4. Scope: maximum functionality (per standing instruction)

**Core ITSM objects (typed):**
- Incidents (`Incident#`): list/get/create/update.
- Service Requests (`ServiceReq#`): list/get/create/update.
- Problems (`Problem#`): list/create/update.
- Change Requests (`ChangeReq#`): list/create/update.
- Configuration Items (`CI#`): list, filterable by CI class/type.
- Knowledge Articles (`KnowledgeArticle#`): list.

**Generic Business Object passthrough:**
- list_table/get_record/create_record/update_record/delete_record by BO name — for any
  business object the tenant's data model exposes (custom BOs, other Ivanti modules).

**Value-add:**
- audit_instance_health — aggregated open-ticket snapshot across incidents/requests/
  problems/changes.
- bulk_update_records — apply the same field values to several records of one BO type
  in one call, for routine bulk hygiene (e.g. closing a batch of resolved tickets).

## 5. Non-goals for v0.1.0

- No file/attachment upload endpoints (ISM's attachment API varies significantly by
  version; add if a real tenant surfaces the need).
- No workflow-stage transition modeling beyond direct field updates (ISM statuses are
  free-text BO field values, not a fixed state machine like Jira transitions).
