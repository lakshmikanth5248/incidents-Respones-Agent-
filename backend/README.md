# Incident Response Agent — Backend

**Hindsight-Enabled Incident Memory and Resolution Assistant for Site Reliability Engineers**

This is the backend service for the Incident Response Agent, built in accordance with the PRD Part 1 and Part 2 specifications.

---

## 1. Technology Stack

* **Language**: Python 3.14+
* **Framework**: FastAPI (0.135+)
* **Data Layer / ORM**: SQLAlchemy 2.0+ (relational database: SQLite for development, PostgreSQL-ready)
* **Data Validation & Settings**: Pydantic v2 & Pydantic-Settings
* **Server**: Uvicorn
* **Testing**: Pytest & HTTPX TestClient

---

## 2. Implemented Features

### Feature 1 — Incident Intake & Normalization
* Request validation, length bounds, and malformed payload rejection.
* Secret scanning: credential-shaped inputs are rejected without leaking sensitive values.
* Verbatim raw input preservation (`symptoms_raw`).
* Deterministic normalization into structured incident facts without hallucinating root causes.
* Stable, sequential ID generation (`INC-YYYY-XXXX`).

### Feature 2 — Incident Retrieval, State & Lifecycle
* Controlled finite state machine:
  `created` → `analyzing` / `investigating` → `analyzed` → `recommendation_ready` → `resolving` / `mitigated` → `resolved` → `closed` (Terminal).
* Terminal-state protection: closed incidents cannot be modified or re-opened.
* Optimistic concurrency control: updates with mismatched `expected_revision` or `from_status` return `409 Conflict` (`CONFLICT`).
* Comprehensive audit trail: every state transition records `actor`, `timestamp`, `action`, `previous_state`, `new_state`, and `outcome`.
* Advanced query filtering: `status`, `service`, `environment`, `severity`, date ranges (`from_date`, `to_date`).
* Pagination & stable deterministic ordering.
* Safe retrieval: `GET` endpoints never trigger Hindsight memory or LLM reasoning.

### Feature 3 — Current Incident Analysis (Stage 1 Reasoning: TL-001)
* First reasoning stage producing structured interpretation of current evidence.
* **Strict Architectural Invariant (D-02):** `INTERPRET -> RECALL -> COMPARE -> HYPOTHESIZE`. No root-cause hypotheses are formed before Hindsight recall completes.
* Provenance tracking: every fact and inference carries `source: "current_incident"`.
* Unknowns and information gaps are explicitly declared without hallucination.
* Versioned prompt templates (`backend/prompts/v1/incident_interpretation.txt`).
* Pluggable model provider architecture (Mock deterministic provider, OpenAI, Anthropic).
* Strict schema validation: malformed output surfaces as `502 Bad Gateway` (`MODEL_OUTPUT_INVALID`).
* Immutable revisioning: each analysis run increments revision; prior revisions remain auditable via `GET /api/incidents/{id}/analysis?revision=N`.
* Full observability: prompt tokens, completion tokens, total tokens, and duration are logged and persisted.

### Feature 4 — Hindsight Memory Service Module
* **Strict Isolation Invariant:** Hindsight is reachable through **strictly ONE backend module** (`src/memory/`).
  ```text
  Agent / API Route
    ↓
  Memory Interface (MemoryService)
    ↓
  Hindsight Client (HindsightClient / HindsightTestDouble)
    ↓
  Hindsight Memory System
  ```
* Standard interface operations:
  * `recall(RecallRequest) -> RecallResult`
  * `retain(RetainRequest) -> RetainResult`
  * `get_experience(entry_id) -> Optional[MemoryEntry]`
  * `flag_experience(entry_id, flag_type, reason, note) -> MemoryEntry`
  * `health_check() -> Tuple[bool, str]`
* Memory status normalization: `ok`, `empty`, `degraded`, `suppressed`.
* **Never-Fake Guarantee:** Hindsight failure sets `memory_status = degraded` and returns HTTP 503 (`HINDSIGHT_UNAVAILABLE`); never returns an empty array as if recall succeeded.
* Stable internal entry schema: `entry_id`, `entry_type`, `service`, `component`, `body`, `outcome_label`, `confidence`, `relevance_score`, `relevance_basis`, `source_incident_ref`, `retained_at`, `flagged`.
* Deterministic ranking layer (RL-012, RL-013, RL-014): incorporates entry-type weights, service matching, signature overlap, outcome bonuses, confidence, and human-readable `relevance_basis` explanations in words.
* Pre-write secret scanning (SEC-008, HM-015): detects credential-shaped patterns in memory candidate bodies and rejects with 422 `SECRET_DETECTED`.
* Server-side confirmation gate (D-12, API-021): rejects unconfirmed retention requests with 409 `CONFLICT`.
* Drop-in test double (`HindsightTestDouble`) supporting offline simulation of success, empty, unavailable, timeout, malformed responses, partial retain, transient retries, and experience flagging.
* Independent memory endpoints:
  * `POST /api/memory/recall` (API-011)
  * `POST /api/memory/retain` (API-012)
  * `GET /api/memory/experience` (API-013)
  * `POST /api/memory/experience/{id}/flag` (API-014)
### Feature 5 — Hindsight Recall for Incident Analysis
* **Primary Recall Workflow:**
  ```text
  Normalized Incident → Recall Intent → Hindsight → Candidate Experiences → Deterministic Filtering/Ranking → Recall Record
  ```
* **Strict Retrieval Intent Derivation:** Queries are derived solely from `service`, `environment`, `failure_mode`, `normalized_symptoms`, `error_signatures`, and `affected_components` (no arbitrary or noisy incident text).
* **Reasoning Sequence Integrity (D-02):** Core Stage 2 RECALL (`TL-002`) integrates into `POST /api/incidents/{id}/analyze` following `INTERPRET` (`TL-001`). Hypotheses remain strictly empty (`hypotheses = []`) prior to comparison.
* **Recall Record Persistence:** All 8 required fields persisted on analysis and incident records:
  `query`, `query_version`, `timestamp`, `memory_status`, `returned_entries`, `ranking`, `relevance_basis`, `duration_ms`.
* **Four Distinguishable Memory Statuses:**
  * `memory_status = "ok"`: Relevant memory retrieved and ranked.
  * `memory_status = "empty"`: No relevant prior memories exist (200 OK, empty list).
  * `memory_status = "degraded"`: Hindsight is down or unreachable (503 `HINDSIGHT_UNAVAILABLE`, never empty array).
  * `memory_status = "suppressed"`: Memory deliberately disabled via `memory_isolated=True`.
* **Deterministic Ranking & Conflict Detection:**
  * Multi-dimensional scoring formula: entry type weight (root causes > procedures > lessons), service match (+0.30), signature/query overlap (with stemming & synonym expansion), failure mode match, outcome bonus (+0.10 for successful), confidence multiplier, flag penalty (-0.40).
  * Deterministic sorting by `(-relevance_score, entry_id)`.
  * Conflict detection across historical records (FR-027, ERR-09): flags conflicting root causes across prior incidents in `relevance_basis`.
* **Endpoints:**
  * `POST /api/memory/recall` (API-011): Direct recall returning `RecallResult` and full `RecallRecord`.
  * `POST /api/incidents/{id}/analyze` (API-005): Executes recall and links `recall_record` to incident & analysis.
  * `GET /api/incidents/{id}/memory` (API-007): Retrieves recalled memories and `recall_record`, with support for `entry_type`, `outcome_label`, and `relevance_min` query filters. Always returns 503 during outages.

### Features 6–7 — Current/Historical Comparison and Hypothesis Generation
* **Strict 6-Stage Reasoning Sequence:**
  `Current analysis -> Hindsight recall -> Memory context assembly -> Comparison -> Hypothesis -> Recommendation`
* **Evidence Comparison Layer (FR-023–FR-028, AC2-04):**
  * Compares current evidence (`current symptoms`, `current metrics`, `current logs`, `recent changes`, `current service`) against historical experience (`previous symptoms`, `previous failure mode`, `root cause`, `resolution`, `outcome`, `failed approaches`, `lessons`).
  * Generates structured comparison items containing:
    `matching_signals`, `differences`, `historical_patterns`, `conflicts`, `confidence`, `provenance`, `match_strength`, `applicability`.
* **Hypothesis Formation Layer (FR-029–FR-034, AC2-05):**
  * Generates structured candidate root-cause explanations containing:
    `hypothesis`, `supporting_current_evidence`, `supporting_memory_entries`, `contradicting_evidence`, `unknowns`, `confidence`, `provenance`, `rank`, `precedent_backed`.
* **Critical Anti-Hallucination Invariant:**
  * The agent may ONLY claim historical facts that exist in the recalled memory set.
  * If a memory does not contain a specific outcome (e.g. rollback), the agent does NOT claim rollback succeeded; missing items are explicitly declared as `unknown`.
* **Conflict Surfacing (FR-027, AC2-04a, AC2-05b):**
  * Disagreements across prior memories (e.g. differing causes for the same failure mode) or contradictions with current telemetry are surfaced in `conflicts` and `contradicting_evidence`, never silently reconciled.
* **Deterministic Output:** All comparison match scores and hypothesis rankings are 100% reproducible.

### Feature 8 — Recommendation + Runbook Intelligence

* **Agent Tool Registry & Autonomous Action Prohibition (FR-043, NG-02, NG-03):**
  * `src/agent/tools.py`: `ToolRegistry` with read-only advisory tools only.
  * `AgentTool.__init__` enforces both prohibited-name guard **and** `is_read_only=True` at registration time, raising `AutonomousActionProhibitedError` for violations.
  * Prohibited tools: `kubectl`, `rollback`, `rollback_api`, `delete_production_resource`, `restart_production_service`, `database_mutation_tool`.
  * Permitted advisory tools: `recall_memory`, `search_runbooks`, `inspect_telemetry`, `read_logs`, `generate_comparison`, `generate_hypotheses`, `generate_recommendations`.

* **Runbook Reference Catalog (API-015):**
  * `src/runbooks/schemas.py`: `RunbookTrackRecord`, `Runbook`, `RunbookListResponse`.
  * `src/services/runbook_service.py`: Pre-seeded catalog with 6 runbooks (`RB-PAY-001`, `RB-PAY-ROLLBACK-002`, `RB-CHECKOUT-001`, `RB-CACHE-001`, `RB-AUTH-001`, `RB-SEARCH-001`).
  * Memory track-record joining: `times_applied`, `times_successful`, `times_ineffective`, `last_outcome` derived from retained memories.
  * `set_available(bool)` toggle for outage simulation, raising `503 RUNBOOK_SET_UNAVAILABLE`.
  * `find_matching_runbooks()` by `service`, `failure_mode`, and `symptoms` overlap.
  * Endpoints:
    * `GET /api/runbooks` — List and search (filter by service, failure_mode_label, q)
    * `GET /api/runbooks/{id}` — Single runbook (404 `RUNBOOK_NOT_FOUND`, 503 `RUNBOOK_SET_UNAVAILABLE`)

* **Recommendation Generation (FR-035–FR-044):**
  * `src/services/reasoning_service.py`: `generate_recommendations()` — Stage 6 after hypothesis generation.
  * **Diagnostic first** (FR-039): Investigative step always placed first before any remediation.
  * **Deployment regression detection**: Checks all incident text sources (`symptoms_raw`, `symptoms_normalized`, `recent_changes`) for deployment keywords.
  * **Precedent ordering** (FR-038): `successful` → `untested` → `ineffective`.
  * **Failed runbook memory** (FR-037, FR-042): `ineffective` runbooks surface `WARNING` in reason, `risk = "high"`, `safer_alternative` required, confidence capped at 0.40, never presented as proven.
  * **Runbook outage** (FR-041): When `RUNBOOK_SET_UNAVAILABLE`, explicitly states absence, provides evidence-based fallback, never fabricates a runbook.
  * **No matching runbook** (FR-041): Explicit `"Runbook coverage: None"` stated, `runbook_reference = null`.
  * **High-risk/destructive** (FR-042): `risk = "high"`, `is_destructive = True`, `safer_alternative` mandatory.
  * **Full provenance** (FR-040, FR-045): Every recommendation carries `provenance`, `supporting_evidence`, `expected_observation`, `confidence`.
  * **Advisory invariant** (FR-043): `advisory = True` always set; `advisory_note` explicitly states human authorization required.

* **Analysis Pipeline Integration:**
  * `src/services/analysis_service.py`: Stage 6 wired after hypothesis generation; `recommendation_ready` status set.
  * `src/data/models/analysis.py`: `recommendations` JSON column + `to_dict()` mapping.
  * `src/api/schemas/analysis.py`: `RecommendationItem` (10 required fields); `AnalysisResponse` includes `recommendations` list.

* **New Endpoints:**
  * `GET /api/runbooks` (API-015)
  * `GET /api/runbooks/{id}` (API-015)
  * `GET /api/incidents/{id}/recommendations` (API-008)

* **Feature 9 — Human Decision and Resolution (FR-049–FR-052):**
  * `src/data/models/resolution.py`: `ResolutionRecord` SQLAlchemy model with unique constraint on `incident_id` for idempotent resolution tracking.
  * `src/api/schemas/resolution.py`: `ResolveIncidentRequest`, `ResolutionResponse`, `RecommendationOutcome` schemas.
  * **Human Authority Principle** (FR-049): AI cannot resolve production incidents — the human operator decides.
  * **Closing Rule Gate** (FR-050): Incidents cannot be closed without remediation actions and verified outcome unless `close_without_resolution=true` AND `confirm_close_without_resolution=true`.
  * **Outcome Values**: Supported PRD outcomes (`successful`, `ineffective`, `inconclusive`, `unknown`).
  * **Recommendation Dispositions**: Tracked per recommendation item (`followed`, `skipped`, `attempted_and_failed`).
  * **Idempotency & Concurrency** (FR-051): Repeated identical resolution returns existing record (`200 OK`); conflicting attempt on resolved incident returns `409 Conflict`.
  * **Endpoints**:
    * `POST /api/incidents/{id}/resolve` (API-009)
    * `GET /api/incidents/{id}/resolution`

---

## 3. Running Automated Tests

Run the complete test suite:
```bash
cd backend
python -m pytest -v
```

All **132 tests** cover:
* Valid incident creation (201)
* Request validation & secret scanning
* Verbatim raw input preservation & normalization
* Idempotency & duplicate detection
* Database failure simulation (500)
* ShopKart Payment API real-world scenario
* Lifecycle state machine progression & terminal state protection
* Optimistic locking and concurrency conflicts (409)
* Incident retrieval, filtering, and stable ordering
* Audit event recording & retrieval
* Stage 1 Current Incident Analysis execution (200)
* Architectural rule: no hypothesis before recall (`hypotheses == []`)
* Statement provenance (`source: "current_incident"`)
* Unknown fields preservation
* Provider unavailable (`MODEL_UNAVAILABLE` 502)
* Malformed provider output (`MODEL_OUTPUT_INVALID` 502)
* Analysis revisioning and auditability (`GET /api/incidents/{id}/analysis?revision=1`)
* Deterministic output verification
* Hindsight retain and recall loop success (HT-01, HT-02)
* Distinguishable cold-start empty result vs. degraded failure (HT-05, ERR-02)
* Outage & network error handling (`HINDSIGHT_UNAVAILABLE` 503)
* Timeout handling and malformed response degradation
* Partial retain per-entry tracking (AC2-07a, ERR-03)
* Transient failure retry behavior
* Status mapping: `ok`, `empty`, `degraded`, `suppressed`
* Pre-write secret scanning for memory candidates (422)
* Server-side retention confirmation gate (409)
* Experience flagging and ranking deprioritization (API-014, FR-074)
* Same wording recall with exact signature matching
* Different wording recall with synonyms & semantic equivalence
* Relevant vs. irrelevant memory ranking & scoring
* Multiple memories recall and deterministic rank assignment
* Conflicting memories detection & cross-incident conflict notation
* Empty memory handling (status=empty, 200 OK)
* Hindsight outage handling (503 HINDSIGHT_UNAVAILABLE, never success + empty array)
* Provenance preservation across the entire recall lifecycle
* Analysis integration with Stage 2 recall and hypothesis invariant
* Matching memory comparison & precedent-backed hypothesis generation
* Cold-start / no-memory handling without memory fabrication
* Contradictory memory and cross-incident conflict surfacing
* Irrelevant memory handling and weak match grading
* Anti-hallucination verification (unsupported historical claims prevented)
* Missing evidence with explicit unknowns declaration
* Structured confidence and provenance tracking
* Deterministic comparison and hypothesis ranking across trials
* Strict reasoning order halting points (interpret -> recall -> compare -> hypothesize)
* **Feature 8 tests:**
  * Runbook catalog list, filtering, and full-text search
  * Unknown runbook 404 (`RUNBOOK_NOT_FOUND`)
  * Runbook service unavailable 503 (`RUNBOOK_SET_UNAVAILABLE`) on catalog and incident analysis fallback
  * Recommendation with successful runbook (precedent-ordered, `successful` labelled, GET /recommendations endpoint)
  * Recommendation without runbook (explicit absence, `no_matching_runbook`, no fabrication)
  * Failed runbook memory (ineffective, warning surfaced, safer alternative, never presented as proven)
  * Recommendation provenance (every item carries source, statement, confidence, expected_observation, advisory=True)
  * No autonomous action prohibition (tool registry check, prohibited tool registration guard, is_read_only=False guard)
  * Recommendation schema completeness (all 10 PRD-required fields present)
* **Feature 9 tests:**
  * Human-in-the-loop resolution recording (`POST /api/incidents/{id}/resolve`)
  * Resolution outcome recording (`successful`, `ineffective`, `inconclusive`, `unknown`)
  * Recommendation disposition tracking (`followed`, `skipped`, `attempted_and_failed`)
  * Closing rule gate: mandatory resolution info & outcome unless `close_without_resolution=true`
  * Explicit confirmation check: rejection if `confirm_close_without_resolution=false` (422)
  * Incident status transition to `resolved`
  * Resolution idempotency on repeated calls (200 OK)
  * Concurrency and conflict protection on already-resolved incidents (409)
  * Resolution record retrieval (`GET /api/incidents/{id}/resolution`)
  * Resolution audit trail logging
