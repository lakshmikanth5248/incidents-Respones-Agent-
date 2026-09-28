# Backend API Contract — Features 1, 2, 3, and 4

This document defines the formal HTTP API contract for:
* **Feature 1**: Incident Intake & Normalization
* **Feature 2**: Incident Retrieval, State & Lifecycle Management
* **Feature 3**: Current Incident Analysis (Stage 1 Reasoning: TL-001)
* **Feature 4**: Hindsight Memory Service Module (Isolated Layer, Recall, Retain, Experience)

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

The system enforces the strict 4-stage reasoning sequence:

```text
INTERPRET  (Feature 3: TL-001 Current Incident Analyzer)
   ↓
RECALL     (Feature 4: TL-002 Hindsight Recall)
   ↓
COMPARE    (Feature 5: Historical Comparison)
   ↓
HYPOTHESIZE (Feature 5: Ranked Hypotheses with Precedent)
```

**Critical Rule:** The system does NOT generate root-cause hypotheses before Hindsight recall completes. At Stage 1, `hypotheses` is strictly empty.

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
  "comparisons": [],
  "hypotheses": [],
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
Retains validated, confirmed reusable conclusions in Hindsight. Enforces server-side confirmation (`confirmed: true`) and pre-write secret scanning.

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

#### Success Response: `200 OK`
```json
{
  "status": "retained",
  "results": [
    {
      "status": "retained",
      "memory_entry_id": "mem-e3f4a5b6",
      "entry_type": "root_cause",
      "error": null
    }
  ],
  "skipped": [],
  "validation_report": {
    "valid_entries": 1,
    "rejected_entries": 0
  }
}
```

#### Error Responses
* `409 Conflict` — Unconfirmed retention attempt (`confirmed: false`).
* `422 Unprocessable Content` — Secret detected in memory candidate body (`SECRET_DETECTED`).
* `503 Service Unavailable` — Memory service unreachable during write (`HINDSIGHT_UNAVAILABLE`).

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
