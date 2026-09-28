# Backend API Contract — Features 1–8

This document defines the formal HTTP API contract for:
* **Feature 1**: Incident Intake & Normalization
* **Feature 2**: Incident Retrieval, State & Lifecycle Management
* **Feature 3**: Current Incident Analysis (Stage 1 Reasoning: TL-001)
* **Feature 4**: Hindsight Memory Service Module (Isolated Layer, Recall, Retain, Experience)
* **Feature 5**: Hindsight Recall (POST /api/memory/recall, integrated into analysis)
* **Feature 6**: Current/Historical Comparison
* **Feature 7**: Hypothesis Generation
* **Feature 8**: Recommendation + Runbook Intelligence

---

## 1. Global Conventions

* **Base URL**: `/api`
* **Content-Type**: `application/json`
* **Authentication**: None in MVP (PRD BE-013, SEC-003). Application runs within an access-controlled boundary. Default implicit operator: `sre-operator`.
* **Standard Error Envelope** (PRD BE-015):
  ```json
  {
    "error": {
      "code": "MACHINE_READABLE_CODE",
      "message": "Human-readable explanation of error.",
      "retryable": false,
      "details": {}
    }
  }
  ```
* **Request Correlation**: All responses return `X-Request-ID` header matching the request's correlation ID.

---

## 2. Core Architectural Invariant: Reasoning Order (D-02)

The system enforces the strict 6-stage reasoning sequence:

```text
INTERPRET  (Stage 1: Current Incident Analyzer)
   ↓
RECALL     (Stage 2: Hindsight Recall)
   ↓
CONTEXT ASSEMBLY (Stage 3: Memory Context Categorization)
   ↓
COMPARE    (Stage 4: Current vs Historical Comparison)
   ↓
HYPOTHESIZE (Stage 5: Ranked Precedent-Backed Hypotheses)
   ↓
RECOMMEND  (Stage 6: Advisory Recommendations + Runbook Intelligence)
```

**Critical Invariants:**
1. The system does NOT generate root-cause hypotheses before Hindsight recall completes.
2. The system does NOT generate recommendations before hypotheses are formed.
3. Anti-hallucination guarantee: The agent may ONLY claim historical facts that exist in recalled memory.
4. Unknowns are explicitly declared when evidence is insufficient.
5. Conflicting historical memories are surfaced, never silently suppressed.
6. **Advisory-only**: The agent recommends and does NOT execute any production action.

---

## 3. Endpoints

### 3.1 `POST /api/incidents` — Create & Normalize Incident (API-001)

#### Description
Receives free-form symptom text from the engineer, validates input, scans for sensitive credentials, preserves raw description unmodified, deterministically normalizes facts, assigns a durable sequential ID (`INC-YYYY-XXXX`), and persists in initial state `created`.

#### Success Response: `201 Created`
```json
{
  "id": "INC-2026-0001",
  "status": "created",
  "state": "created",
  "raw_symptom_description": "Payment API is failing...",
  "symptoms_raw": "Payment API is failing...",
  "service": "payment-api",
  "environment": "production",
  "severity": "critical",
  "normalized": {},
  "created_at": "2026-09-28T10:15:30.123456+00:00",
  "revision": 1,
  "analysis_revision": 0,
  "resolution_status": "unresolved"
}
```

---

### 3.2 `GET /api/incidents` — List Incidents (API-002)

#### Description
Retrieves a paginated list of incidents with multi-criteria filtering and stable deterministic ordering.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `status` | string | No | `null` | Filter by incident status |
| `service` | string | No | `null` | Filter by service name |
| `environment` | string | No | `null` | Filter by environment |
| `severity` | string | No | `null` | Filter by severity |
| `from_date` | string (ISO-8601) | No | `null` | Filter incidents created on or after timestamp |
| `to_date` | string (ISO-8601) | No | `null` | Filter incidents created on or before timestamp |
| `order_by` | string | No | `created_at` | Sort column: `created_at`, `detected_at`, `id`, `updated_at` |
| `order_dir` | string | No | `desc` | Sort direction: `asc` or `desc` |
| `limit` | integer | No | `50` | Maximum items to return (1–100) |
| `offset` | integer | No | `0` | Pagination offset |

---

### 3.3 `GET /api/incidents/{id}` — Retrieve Incident Detail (API-003)

Retrieves full incident record by ID without executing the agent. Includes lifecycle metrics, analysis revision, memory status, resolution status, and post-mortem status.

---

### 3.4 `PATCH /api/incidents/{id}` — Patch Incident (API-004)

Updates mutable fields or state with optimistic concurrency protection (`expected_revision`).

---

### 3.5 `POST /api/incidents/{id}/transition` — Transition Lifecycle State

Explicitly transitions an incident to a new state in accordance with the state machine. Enforces optimistic concurrency and terminal-state protection. Emits an audit event.

---

### 3.6 `GET /api/incidents/{id}/audit` — Retrieve Audit Trail

Retrieves full chronological audit log of all lifecycle transitions, mutations, and actions recorded for the incident.

---

### 3.7 `POST /api/incidents/{id}/analyze` — Current Incident Analysis (API-005)

#### Description
Executes Stage 1 analysis (TL-001 Incident Analyzer). Uses the configured model provider and versioned prompt (`v1.0.0`) to produce a structured interpretation of current evidence. Enforces the strict rule that **no root-cause hypotheses are generated before Hindsight recall**.

#### Request Body (Optional)
```json
{
  "memory_isolated": false,
  "operator_note": "Focus on connection pool"
}
```

#### Success Response: `200 OK`
```json
{
  "analysis_id": "ANA-INC-2026-0001-r1",
  "incident_id": "INC-2026-0001",
  "revision": 1,
  "status": "ready_for_recall",
  "memory_status": null,
  "recall_record": null,
  "symptom_analysis": {
    "affected_scope": {
      "service": "payment-api",
      "environment": "production",
      "affected_components": [
        "connection-pool",
        "database",
        "payment-api"
      ]
    },
    "failure_mode": "database_connection_exhaustion",
    "facts": [
      {
        "source": "current_incident",
        "statement": "Payment operations are experiencing failures."
      },
      {
        "source": "current_incident",
        "statement": "Database connections are exhausted."
      }
    ],
    "inferences": [
      {
        "source": "current_incident",
        "statement": "Connection pool saturation is starving query processing."
      }
    ],
    "unknowns": [
      "Exact database thread pool configuration."
    ],
    "information_gaps": [
      "Active database connection count metric graph."
    ],
    "normalized_signatures": [
      "DB_CONN_EXHAUSTION"
    ]
  },
  "comparisons": [
    {
      "prior_incident_id": "INC-2025-0042",
      "entry_id": "mem-1a2b3c4d",
      "matching_signals": [
        "Matching service: payment-api",
        "Symptom overlap on terms: connection, pool, exhaustion"
      ],
      "differences": [
        "Recent changes: unknown in current evidence"
      ],
      "historical_patterns": [
        "Prior root cause (INC-2025-0042): HikariCP connection leak during unclosed cursor in bulk checkout."
      ],
      "conflicts": [],
      "confidence": {
        "score": 0.88,
        "level": "confirmed",
        "basis": "Score 0.88 based on 2 matching signal(s), 1 difference(s), and 0 conflict(s)."
      },
      "provenance": [
        {
          "source": "current_incident",
          "statement": "Current service is payment-api"
        },
        {
          "source": "recalled_memory:mem-1a2b3c4d",
          "statement": "Historical incident INC-2025-0042 occurred on service payment-api"
        }
      ],
      "match_strength": "full",
      "applicability": "applicable"
    }
  ],
  "hypotheses": [
    {
      "hypothesis": "Candidate Cause: HikariCP connection leak during unclosed cursor in bulk checkout. (Precedent: INC-2025-0042)",
      "supporting_current_evidence": [
        "Service alignment: payment-api",
        "Current failure mode: database_connection_exhaustion",
        "Signal: Matching service: payment-api",
        "Signal: Symptom overlap on terms: connection, pool, exhaustion"
      ],
      "supporting_memory_entries": [
        "mem-1a2b3c4d"
      ],
      "contradicting_evidence": [],
      "unknowns": [
        "Exact database thread pool configuration.",
        "unknown: Whether rollback or restart was previously attempted for this instance"
      ],
      "confidence": {
        "score": 0.82,
        "level": "confirmed",
        "basis": "Precedent-backed by INC-2025-0042 (relevance 0.88). Supported by 4 current evidence item(s)."
      },
      "provenance": [
        {
          "source": "current_incident",
          "statement": "Current symptoms: Payment API is failing due to database pool exhaustion."
        },
        {
          "source": "recalled_memory:mem-1a2b3c4d",
          "statement": "Historical precedent from INC-2025-0042: HikariCP connection leak during unclosed cursor in bulk checkout."
        }
      ],
      "rank": 1,
      "precedent_backed": true,
      "status": "candidate"
    }
  ],
  "unknowns": [
    "Exact database thread pool configuration."
  ],
  "information_gaps": [
    "Active database connection count metric graph."
  ],
  "model_metadata": {
    "model_identifier": "mock-reasoner-v1",
    "prompt_version": "v1.0.0",
    "prompt_tokens": 280,
    "completion_tokens": 120,
    "total_tokens": 400,
    "duration_ms": 15.2
  },
  "created_at": "2026-09-28T10:45:00.123456+00:00"
}
```

#### Error Responses
* `409 Conflict` — Incident is closed:
  ```json
  {
    "error": {
      "code": "INCIDENT_CLOSED",
      "message": "Cannot analyze incident 'INC-2026-0001' because it is closed.",
      "retryable": false,
      "details": {}
    }
  }
  ```
* `502 Bad Gateway` — Model provider unreachable or quota exceeded:
  ```json
  {
    "error": {
      "code": "MODEL_UNAVAILABLE",
      "message": "The analysis model could not be reached. Nothing was changed — retry.",
      "retryable": true,
      "details": {}
    }
  }
  ```
* `502 Bad Gateway` — Model output unparseable or fails schema validation:
  ```json
  {
    "error": {
      "code": "MODEL_OUTPUT_INVALID",
      "message": "Model output failed structured schema validation.",
      "retryable": true,
      "details": {}
    }
  }
  ```

---

### 3.8 `GET /api/incidents/{id}/analysis` — Retrieve Incident Analysis (API-006)

#### Description
Retrieves the current analysis artefact, or a specific historical revision (`?revision=N`) for auditability.

#### Query Parameters
| Parameter | Type | Required | Description |
|---|---|---|---|
| `revision` | integer | No | Specific revision number to retrieve. If omitted, returns latest analysis. |

#### Error Responses
* `404 Not Found` — Incident not found or no analysis generated yet (`ANALYSIS_NOT_FOUND`).

---

### 3.9 `GET /api/incidents/{id}/memory` — Retrieve Recalled Memory for Incident (API-007)

#### Description
Retrieves historical memory entries recalled from Hindsight for this incident, with deterministic ranking scores and explanatory relevance basis strings.

#### Query Parameters
| Parameter | Type | Required | Description |
|---|---|---|---|
| `entry_type` | string | No | Filter by entry type (`root_cause`, `resolution_procedure`, etc.) |
| `outcome_label` | string | No | Filter by outcome label (`successful`, `ineffective`, etc.) |
| `relevance_min` | float | No | Minimum relevance threshold (0.0 to 1.0) |

#### Success Response: `200 OK`
```json
{
  "incident_id": "INC-2026-0001",
  "memory_status": "ok",
  "recall_record": {
    "query": "Database connection pool exhaustion",
    "query_version": "v1.0.0",
    "timestamp": "2026-09-28T10:30:00+00:00",
    "memory_status": "ok",
    "returned_entries": [
      {
        "entry_id": "mem-1a2b3c4d",
        "entry_type": "root_cause",
        "service": "checkout-service",
        "component": "connection_pool",
        "body": "HikariCP connection leak during unclosed cursor in bulk checkout.",
        "outcome_label": "successful",
        "confidence": "confirmed",
        "relevance_score": 0.88,
        "relevance_basis": "Strong match: Service match (checkout-service); Error signature overlap (2 matching tokens); Prior successful outcome",
        "source_incident_ref": "INC-2025-0042",
        "retained_at": "2026-09-28T10:00:00Z",
        "flagged": null,
        "provenance_group_id": "prov-0042",
        "is_synthetic": true
      }
    ],
    "ranking": [
      {
        "entry_id": "mem-1a2b3c4d",
        "rank": 1,
        "score": 0.88,
        "relevance_basis": "Strong match: Service match (checkout-service); Error signature overlap (2 matching tokens); Prior successful outcome"
      }
    ],
    "relevance_basis": {
      "mem-1a2b3c4d": "Strong match: Service match (checkout-service); Error signature overlap (2 matching tokens); Prior successful outcome"
    },
    "duration_ms": 12.4,
    "scope": {
      "service": "checkout-service",
      "environment": "production",
      "failure_mode": "database_exhaustion"
    }
  },
  "entries": [
    {
      "entry_id": "mem-1a2b3c4d",
      "entry_type": "root_cause",
      "service": "checkout-service",
      "component": "connection_pool",
      "body": "HikariCP connection leak during unclosed cursor in bulk checkout.",
      "outcome_label": "successful",
      "confidence": "confirmed",
      "relevance_score": 0.88,
      "relevance_basis": "Strong match: Service match (checkout-service); Error signature overlap (2 matching tokens); Prior successful outcome",
      "source_incident_ref": "INC-2025-0042",
      "retained_at": "2026-09-28T10:00:00Z",
      "flagged": null,
      "provenance_group_id": "prov-0042",
      "is_synthetic": true
    }
  ]
}
```

#### Error Responses
* `404 Not Found` — Incident not found (`INCIDENT_NOT_FOUND`).
* `503 Service Unavailable` — Memory service unreachable or errored (`HINDSIGHT_UNAVAILABLE`). **Never returns empty entries on failure!**

---

### 3.10 `POST /api/memory/recall` — Explicit Memory Recall (API-011)

#### Description
Independent operator-initiated memory recall against Hindsight via the isolated `MemoryService` interface.

#### Request Body
```json
{
  "query": "Redis cache eviction latency spike",
  "service": "session-service",
  "environment": "production",
  "limit": 5,
  "memory_isolated": false
}
```

#### Success Response: `200 OK`
```json
{
  "memory_status": "ok",
  "query_recorded": "Redis cache eviction latency spike",
  "scope": {
    "service": "session-service",
    "environment": "production"
  },
  "total_found": 1,
  "entries": [
    {
      "entry_id": "mem-f9a8b7c6",
      "entry_type": "root_cause",
      "service": "session-service",
      "body": "Redis maxmemory limit reached without eviction policy.",
      "outcome_label": "successful",
      "confidence": "confirmed",
      "relevance_score": 0.85,
      "relevance_basis": "Strong match: Service match (session-service); Symptom query term overlap",
      "source_incident_ref": "INC-2025-0010"
    }
  ],
  "recall_record": {
    "query": "Redis cache eviction latency spike",
    "query_version": "v1.0.0",
    "timestamp": "2026-09-28T10:30:00+00:00",
    "memory_status": "ok",
    "returned_entries": [
      {
        "entry_id": "mem-f9a8b7c6",
        "entry_type": "root_cause",
        "service": "session-service",
        "body": "Redis maxmemory limit reached without eviction policy.",
        "outcome_label": "successful",
        "confidence": "confirmed",
        "relevance_score": 0.85,
        "relevance_basis": "Strong match: Service match (session-service); Symptom query term overlap",
        "source_incident_ref": "INC-2025-0010"
      }
    ],
    "ranking": [
      {
        "entry_id": "mem-f9a8b7c6",
        "rank": 1,
        "score": 0.85,
        "relevance_basis": "Strong match: Service match (session-service); Symptom query term overlap"
      }
    ],
    "relevance_basis": {
      "mem-f9a8b7c6": "Strong match: Service match (session-service); Symptom query term overlap"
    },
    "duration_ms": 11.2,
    "scope": {
      "service": "session-service",
      "environment": "production"
    }
  }
}
```

#### Error Responses
* `422 Unprocessable Content` — Empty query with no service scope.
* `503 Service Unavailable` — Hindsight memory service down (`HINDSIGHT_UNAVAILABLE`).

---

### 3.11 `POST /api/memory/retain` — Retain Operational Experience (API-012)

#### Description
Retains validated, confirmed reusable conclusions in Hindsight. Enforces server-side confirmation and pre-write secret scanning.

Retention is gated on the **stored** post-mortem state, not the client flag alone:

1. The incident must exist (`404 INCIDENT_NOT_FOUND`).
2. The request must carry `confirmed: true` and the post-mortem must exist in state
   `confirmed` (`409 CONFLICT` / `POSTMORTEM_NOT_FOUND` / `POSTMORTEM_NOT_CONFIRMED`).
3. Every entry is validated and secret-scanned **before any write occurs**; a secret
   anywhere in the batch rejects the whole request with `422 SECRET_DETECTED`.
4. Provenance is server-authoritative: a missing `service` is inherited from the
   incident and `source_incident_ref` is always forced to the request's `incident_id`.

#### Request Body
```json
{
  "incident_id": "INC-2026-0001",
  "confirmed": true,
  "entries": [
    {
      "entry_type": "root_cause",
      "service": "checkout-service",
      "component": "connection_pool",
      "body": "HikariCP pool leak fixed by setting leakDetectionThreshold.",
      "outcome_label": "successful",
      "confidence": "confirmed",
      "source_incident_ref": "INC-2026-0001"
    }
  ]
}
```

`service` and `source_incident_ref` may be omitted; the server fills them from the incident.

#### Success Response: `200 OK`
```json
{
  "status": "retained",
  "incident_id": "INC-2026-0001",
  "retain_id": "RET-INC-2026-0001-1BE9816D",
  "memory_entry_id": "mem-e3f4a5b6",
  "memory_entry_ids": ["mem-e3f4a5b6"],
  "results": [
    {
      "status": "retained",
      "memory_entry_id": "mem-e3f4a5b6",
      "entry_type": "root_cause",
      "entry_index": 0,
      "entry_key": "9b2af605b396b32079a31ae6efb52bf3",
      "error": null
    }
  ],
  "skipped": [],
  "validation_report": {
    "submitted_entries": 1,
    "valid_entries": 1,
    "rejected_entries": 0,
    "provenance_corrected": 0,
    "secret_scan": "passed",
    "incident_service": "checkout-service",
    "written_entries": 1,
    "idempotent_entries": 0,
    "failed_entries": 0,
    "retain_id": "RET-INC-2026-0001-1BE9816D",
    "postmortem_status": "confirmed",
    "postmortem_id": "pm-412aa89bd173"
  },
  "idempotent": false,
  "retry_pending": false,
  "retained_at": "2026-09-28T11:00:00+00:00"
}
```

#### Response Semantics

`status` is never reported as complete success when any entry failed (D-11, ERR-03):

| `status` | Meaning |
|---|---|
| `retained` | Every eligible entry is now in Hindsight (written or already present) |
| `partial` | At least one entry was written **and** at least one failed; `retry_pending` is `true` |
| `failed` | No entry was written; surfaced as `503` with the composed records preserved |

Per-entry `results[].status` values:

| Value | Meaning |
|---|---|
| `retained` | Written to Hindsight by this request |
| `already_retained` | The same `(incident_id, entry identity)` already exists; no duplicate written |
| `failed` | The write did not complete; the composed record is persisted for retry |
| `skipped` | Rejected by server-side validation; never reached Hindsight |

`skipped[]` reports validation rejections separately from write failures:
```json
{ "entry_index": 1, "entry_type": "resolution_procedure", "reason": "Missing required outcome_label for procedure/action entry (RP-012)" }
```

#### Idempotency
Each entry gets a stable SHA-256 `entry_key` over its identity (incident, entry type,
service, component, body, outcome label, confidence). Re-submitting the same entries
returns `already_retained` with the original `memory_entry_id`, sets `idempotent: true`,
and writes nothing to Hindsight.

#### Error Responses
* `404 Not Found` — Incident does not exist (`INCIDENT_NOT_FOUND`).
* `409 Conflict` — `confirmed` is `false` (`CONFLICT`), no post-mortem exists
  (`POSTMORTEM_NOT_FOUND`), or the stored post-mortem is not `confirmed`
  (`POSTMORTEM_NOT_CONFIRMED`).
* `422 Unprocessable Content` — Secret detected in a memory candidate body
  (`SECRET_DETECTED`), or an entry fails server-side validation. The response reports
  only the offending entry index, entry type, and secret category; credentials are never
  echoed.
* `503 Service Unavailable` — Hindsight unreachable during write (`HINDSIGHT_UNAVAILABLE`).
  `retryable: true`, and the composed records are persisted so the request can be retried.

---

### 3.12 `GET /api/memory/experience` — Browse Retained Experience (API-013)

#### Description
Enables inspection and browsing of retained experience across services and incident classes.

#### Query Parameters
| Parameter | Type | Required | Description |
|---|---|---|---|
| `service` | string | No | Filter by service name |
| `failure_mode_label` | string | No | Filter by failure mode label |
| `entry_type` | string | No | Filter by entry type |
| `include_flagged` | boolean | No | Whether to include flagged records (default: true) |

---

### 3.13 `POST /api/memory/experience/{id}/flag` — Flag Experience (API-014)

#### Description
Marks a retained memory record as `incorrect`, `inapplicable`, or `outdated`, attaching reasoning and deprioritizing it in future recalls.

#### Request Body
```json
{
  "flag_type": "outdated",
  "reason": "Service migrated from Mailgun to AWS SES.",
  "note": "Updated runbook 14 applies now."
}
```

#### Success Response: `200 OK`
```json
{
  "entry_id": "mem-e3f4a5b6",
  "flagged": {
    "flag_type": "outdated",
    "reason": "Service migrated from Mailgun to AWS SES.",
    "note": "Updated runbook 14 applies now.",
    "flagged_at": "2026-09-28T11:00:00Z"
  },
  "action_taken": "Flagged as outdated and deprioritized in future recall ranking."
}
```

---

## Feature 8: Recommendation + Runbook Intelligence

### 3.14 `GET /api/runbooks` — List & Search Runbooks (API-015)

#### Description
Returns the runbook reference catalog, filtered by service, failure mode, or free-text search. Each runbook is joined with its historical outcome track record from Hindsight retained memory.

#### Query Parameters
| Parameter | Type | Description |
|---|---|---|
| `service` | `string` | Filter by service name (e.g. `payment-api`) |
| `failure_mode_label` | `string` | Filter by failure mode (e.g. `database_connection_exhaustion`) |
| `q` | `string` | Full-text search across title, steps, and applicable symptoms |

#### Success Response: `200 OK`
```json
{
  "total": 2,
  "runbooks": [
    {
      "id": "RB-PAY-001",
      "title": "Payment API Connection Pool Recovery",
      "service": "payment-api",
      "failure_mode_label": "database_connection_exhaustion",
      "steps": [
        "1. Query pg_stat_activity for idle-in-transaction connections older than 60s.",
        "2. Inspect transaction manager connection leak timeout configuration.",
        "3. Gracefully terminate stale database connection leases.",
        "4. Verify active connection count drops below pool capacity ceiling."
      ],
      "applicable_symptoms": ["connection pool exhausted", "HikariPool", "connection timeout"],
      "risk_level": "medium",
      "is_destructive": false,
      "safer_diagnostic_alternative": "Query pg_stat_activity read-only metrics before terminating any connection.",
      "track_record": {
        "times_applied": 3,
        "times_successful": 3,
        "times_ineffective": 0,
        "last_outcome": "successful",
        "outcome_source": "retained_memory"
      }
    }
  ]
}
```

#### Error Responses
| Code | Error Code | Condition |
|---|---|---|
| `503 Service Unavailable` | `RUNBOOK_SET_UNAVAILABLE` | Runbook catalog is offline |

---

### 3.15 `GET /api/runbooks/{id}` — Get Runbook (API-015)

#### Description
Retrieve a single runbook by ID, joined with its historical outcome track record.

#### Success Response: `200 OK`
Returns a single `Runbook` object (same schema as above).

#### Error Responses
| Code | Error Code | Condition |
|---|---|---|
| `404 Not Found` | `RUNBOOK_NOT_FOUND` | Runbook ID not in catalog |
| `503 Service Unavailable` | `RUNBOOK_SET_UNAVAILABLE` | Runbook catalog is offline |

---

### 3.16 `POST /api/incidents/{id}/analyze` — Stage 6 Additions

The `/analyze` endpoint now also produces `recommendations` as Stage 6 of the reasoning pipeline (after hypotheses). The response `AnalysisResponse` now includes:

```json
{
  "recommendations": [
    {
      "recommendation_id": "REC-INC-2026-0001-001",
      "action": "Inspect payment-api telemetry, active error logs, and component configurations for database_connection_exhaustion.",
      "investigation": "1. Inspect error rates...\n2. Validate connection pool limits...",
      "action_type": "diagnostic",
      "reason": "Ground truth verification of database_connection_exhaustion before applying any operational procedures.",
      "supporting_evidence": ["Current symptom: connection pool exhausted"],
      "memory_references": ["mem-abc123"],
      "runbook_reference": null,
      "runbook_outcome": "no_record",
      "hypothesis_reference": "Candidate Cause: ...",
      "risk": "low",
      "is_destructive": false,
      "safer_alternative": null,
      "expected_observation": "Identify whether failure is isolated to recent changes without disrupting live production traffic.",
      "confidence": {"score": 0.85, "level": "confirmed", "basis": "..."},
      "provenance": [{"source": "current_incident", "statement": "Observed failure mode: ..."}],
      "advisory": true,
      "advisory_note": "Advisory only. The agent does not execute production actions. Human engineer authorization required."
    }
  ]
}
```

**Recommendation ordering (FR-038):**
1. Diagnostic investigation steps first (FR-039)
2. Remediation steps ordered by prior outcome: `successful` → `untested` → `ineffective`

**Runbook absence (FR-041):** When no matching runbook exists or runbook catalog is offline, `runbook_reference = null` is explicitly set and the reason states why. A runbook is never fabricated.

**Failed runbooks (FR-037, FR-042):** When `runbook_outcome = "ineffective"`, the recommendation includes a prominent warning in `reason`, `risk = "high"`, and a `safer_alternative`.

**Advisory invariant (FR-043):** `advisory = true` is always set. The agent never executes any production action.

---

### 3.17 `GET /api/incidents/{id}/recommendations` — Get Recommendations (API-008)

#### Description
Returns the advisory recommendations generated for this incident during the most recent analysis run.

#### Success Response: `200 OK`
Returns a JSON array of `RecommendationItem` objects (same schema as within `AnalysisResponse`).

#### Error Responses
| Code | Error Code | Condition |
|---|---|---|
| `404 Not Found` | `ANALYSIS_NOT_FOUND` | No analysis has been run yet for this incident |
| `404 Not Found` | `INCIDENT_NOT_FOUND` | Incident not found |


---

### 3.18 `POST /api/incidents/{id}/resolve` — Human Decision and Resolution (API-009, FR-049 to FR-052)

#### Description
Records human operator resolution decisions for an incident. Enforces the strict architectural requirement that **the AI cannot resolve production incidents — the engineer decides** (FR-049).

Records actual remediation actions taken, runbook used, contributing factors, root cause, verified outcome, recommendation disposition, and operator rationale.

#### Request Body
```json
{
  "actions": ["Rolled back payment service deployment to v2.4.0", "Restarted degraded worker pods"],
  "runbook_id": "rb-pay-001",
  "runbook_version": "1.2.0",
  "contributing_factors": ["Connection pool configuration miscalculation", "Sudden flash sale traffic spike"],
  "root_cause": "Database connection exhaustion in payment service pool",
  "result": "Latency recovered to <120ms, error rate dropped to 0.01%",
  "outcome": "successful",
  "recommendation_outcomes": [
    {
      "recommendation_id": "rec-pay-pool-01",
      "decision": "followed",
      "reason": "Runbook step verified effective",
      "notes": "Pool size expanded to 50"
    },
    {
      "recommendation_id": "rec-pay-pool-02",
      "decision": "skipped",
      "reason": "Not necessary after pool rollback"
    }
  ],
  "operator_notes": "Resolved during on-call rotation after confirming metrics stabilization.",
  "close_without_resolution": false,
  "confirm_close_without_resolution": false,
  "resolved_by": "alice@ops.example.com"
}
```

#### Fields
| Field | Type | Description |
|---|---|---|
| `actions` | `list[str]` | Remediation actions taken. Required unless `close_without_resolution=true`. |
| `runbook_id` | `str \| null` | Runbook ID referenced, if any. |
| `runbook_version` | `str \| null` | Version of the runbook referenced. |
| `contributing_factors` | `list[str]` | Contributing environmental or architectural factors. |
| `root_cause` | `str \| null` | Verified or suspected root cause. |
| `result` | `str \| null` | Observable result after actions taken. |
| `outcome` | `str` | Must be one of: `"successful"`, `"ineffective"`, `"inconclusive"`, `"unknown"`. Required unless `close_without_resolution=true`. |
| `recommendation_outcomes` | `list[object]` | Disposition for each recommendation: `recommendation_id`, `decision` (`"followed"`, `"skipped"`, `"attempted_and_failed"`), `reason`, `notes`. |
| `operator_notes` | `str \| null` | Freeform engineer notes. |
| `close_without_resolution` | `bool` | Default `false`. If `true`, closes incident without full resolution data. |
| `confirm_close_without_resolution` | `bool` | Default `false`. Must be `true` when `close_without_resolution=true`. |
| `resolved_by` | `str` | Identity of the engineer who resolved the incident. |

#### Closing Rule Gate (FR-050)
* An incident cannot be closed without resolution information (`actions`) and an `outcome`.
* If `close_without_resolution = true`, `confirm_close_without_resolution = true` is strictly required. Otherwise returns `422 Unprocessable Content` (`CLOSE_WITHOUT_RESOLUTION_NOT_CONFIRMED`).

#### Idempotency & Concurrency (FR-051)
* Calling resolve with identical parameters returns `200 OK` with the existing resolution record.
* Attempting to resolve an already-resolved incident with conflicting parameters returns `409 Conflict` (`INCIDENT_ALREADY_RESOLVED`).

#### Response: `200 OK`
```json
{
  "id": "res-uuid",
  "incident_id": "inc-uuid",
  "outcome": "successful",
  "actions": ["Rolled back payment service deployment to v2.4.0"],
  "runbook_id": "rb-pay-001",
  "runbook_version": "1.2.0",
  "contributing_factors": ["Connection pool exhaustion"],
  "root_cause": "Database connection exhaustion in payment service pool",
  "result": "Latency recovered to normal",
  "recommendation_outcomes": [
    {
      "recommendation_id": "rec-pay-pool-01",
      "decision": "followed",
      "reason": "Verified effective"
    }
  ],
  "operator_notes": "Resolved by on-call engineer.",
  "close_without_resolution": false,
  "resolved_by": "alice@ops.example.com",
  "resolved_at": "2026-09-28T13:45:00Z",
  "incident_status": "resolved"
}
```

#### Error Responses
| Code | Error Code | Condition |
|---|---|---|
| `404 Not Found` | `INCIDENT_NOT_FOUND` | Incident does not exist |
| `422 Unprocessable Content` | `RESOLUTION_INFORMATION_REQUIRED` | Missing actions or outcome when not closing without resolution |
| `422 Unprocessable Content` | `CLOSE_WITHOUT_RESOLUTION_NOT_CONFIRMED` | `close_without_resolution=true` without `confirm_close_without_resolution=true` |
| `409 Conflict` | `INCIDENT_ALREADY_RESOLVED` | Incident is already resolved with conflicting data |

---

### 3.19 `GET /api/incidents/{id}/resolution` — Get Resolution Record

#### Description
Returns the resolution record and human decision audit trail for a resolved incident.

#### Success Response: `200 OK`
Returns the `ResolutionResponse` object.

#### Error Responses
| Code | Error Code | Condition |
|---|---|---|
| `404 Not Found` | `INCIDENT_NOT_FOUND` | Incident does not exist |
| `404 Not Found` | `RESOLUTION_NOT_FOUND` | Incident has not been resolved yet |


---

### 3.20 `POST /api/incidents/{id}/verify` — Resolution Outcome Verification (Feature 10)

#### Description
Verifies what happened after the engineer's action. Enforces the strict rule: **Do not assume that an action worked merely because the engineer marked it successful.**
Records available evidence and computes observed changes across baseline and post-action measurements without manufacturing data.

#### Request Body
```json
{
  "before_metrics": {
    "error_rate": "31%",
    "latency": "4.8s",
    "db_connections": "100/100"
  },
  "after_metrics": {
    "error_rate": "2%",
    "latency": "420ms",
    "db_connections": "38/100"
  },
  "observations": [
    "Worker pool stabilized",
    "Error spike subsided"
  ],
  "operator_result": "successful",
  "verification_notes": "Telemetry confirms all metrics returned to nominal baselines."
}
```

#### Fields
| Field | Type | Description |
|---|---|---|
| `before_metrics` | `dict` | Baseline metrics prior to resolution action. Stored verbatim. |
| `after_metrics` | `dict` | Measurements observed following resolution action. Stored verbatim. |
| `observations` | `list[str]` | Qualitative engineering observations following action. |
| `operator_result` | `str \| null` | Declared operator outcome (`successful`, `ineffective`, `inconclusive`, `unknown`). If omitted and incident is resolved, automatically inherits from `ResolutionRecord.outcome`. |
| `verification_notes` | `str \| null` | Verifying engineer's reasoning, notes, or operational context. |

#### Verification Statuses
- `confirmed` — All evaluated metrics improved to recovered state, no conflicting degradation.
- `failed` — Measurements degraded or remained at incident failure thresholds (even if engineer marked successful).
- `inconclusive` — Incomplete telemetry (missing before or after data) or conflicting metrics (some improved while others degraded).
- `unknown` — Operator declared unknown outcome with no decisive telemetry.

#### Invariant: No Manufactured Measurements
The system records only actual provided metrics in `before_state` and `after_state`. Default, synthetic, or unobserved metrics are never fabricated.

#### Integration
- **Resolution feeds verification**: Inherits `operator_result` and links `resolution_id` when resolution record is present.
- **Verification feeds post-mortem & memory candidate**: Exports structured context (`to_postmortem_context()`, `to_memory_candidate_context()`) with outcome labels and confidence markers.

#### Response: `200 OK`
```json
{
  "id": "ver-7a2e9b01",
  "incident_id": "INC-2026-0001",
  "resolution_id": "res-uuid",
  "verification_status": "confirmed",
  "operator_result": "successful",
  "before_state": {
    "error_rate": "31%",
    "latency": "4.8s",
    "db_connections": "100/100"
  },
  "after_state": {
    "error_rate": "2%",
    "latency": "420ms",
    "db_connections": "38/100"
  },
  "observed_changes": [
    {
      "metric": "error_rate",
      "before": "31%",
      "after": "2%",
      "delta": "-29.0%",
      "direction": "improved",
      "details": "error_rate changed from 31% to 2% (-29.0%, improved)"
    },
    {
      "metric": "latency",
      "before": "4.8s",
      "after": "420ms",
      "delta": "-4380ms",
      "direction": "improved",
      "details": "latency changed from 4.8s to 420ms (-4380ms, improved)"
    },
    {
      "metric": "db_connections",
      "before": "100/100",
      "after": "38/100",
      "delta": "-62/100",
      "direction": "improved",
      "details": "db_connections changed from 100/100 to 38/100 (-62/100, improved)"
    }
  ],
  "evidence": [
    {
      "source": "metric:error_rate",
      "claim": "error_rate moved from 31% to 2%",
      "assessment": "supports_recovery",
      "details": "error_rate changed from 31% to 2% (-29.0%, improved)"
    },
    {
      "source": "telemetry_recovery",
      "claim": "All 3 evaluated metrics improved to recovered state",
      "assessment": "supports_recovery",
      "details": "Improved metrics: ['db_connections', 'error_rate', 'latency']"
    }
  ],
  "verification_notes": "Telemetry confirms all metrics returned to nominal baselines.",
  "verified_by": "sre-verifier",
  "verified_at": "2026-09-28T14:15:00Z",
  "created_at": "2026-09-28T14:15:00Z",
  "incident_status": "resolved"
}
```

#### Error Responses
| Code | Error Code | Condition |
|---|---|---|
| `404 Not Found` | `INCIDENT_NOT_FOUND` | Incident does not exist |

---

### 3.21 `GET /api/incidents/{id}/verification` — Get Verification Record

#### Description
Retrieves the outcome verification record and evidence assessment for an incident.

#### Success Response: `200 OK`
Returns the `VerificationResponse` object.

#### Error Responses
| Code | Error Code | Condition |
|---|---|---|
| `404 Not Found` | `INCIDENT_NOT_FOUND` | Incident does not exist |
| `404 Not Found` | `VERIFICATION_NOT_FOUND` | Incident has not been verified yet |

---

## Agent Tool Registry — Autonomous Action Prohibition (FR-043, NG-02, NG-03)

The agent has a **read-only advisory tool registry** (`ToolRegistry`). The following production-mutating tools are permanently prohibited and will raise `AutonomousActionProhibitedError` at registration time:

| Prohibited Tool | Reason |
|---|---|
| `kubectl` | Direct production cluster mutation |
| `rollback` / `rollback_api` | Direct deployment rollback |
| `delete_production_resource` | Production resource deletion |
| `restart_production_service` | Live service restart |
| `database_mutation_tool` | Database write mutation |

Any `AgentTool` registered with `is_read_only=False` is also prohibited.

**Permitted advisory tools:**
- `recall_memory` — Query Hindsight for prior operational experiences
- `search_runbooks` — Search runbook reference catalog
- `inspect_telemetry` — Read current metrics and telemetry facts
- `read_logs` — Inspect log excerpts and error signatures
- `generate_comparison` — Compare current evidence against historical experience
- `generate_hypotheses` — Formulate candidate root-cause explanations
- `generate_recommendations` — Formulate advisory investigation and resolution guidance
