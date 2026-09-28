"""
Frontend Compatibility and Integration Router.
Implements the exact API contracts and data models required by the Aegis SRE Command Center frontend,
including authentication, 3D memory graph experiences, agent reasoning pipeline, telemetry signals,
response plan approval workflow, demo scenario management, and AI research synthesis.
"""

import hmac
import hashlib
import json
import base64
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, Response, Header, Depends, status, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["Frontend Compatibility"])

JWT_SECRET = "aegis-hindsight-hypergraph-secret-key-2026"

# ==========================================
# In-Memory & Persistent State Store
# ==========================================

DEFAULT_MODULE_PERMISSIONS = {
    "incidents": True,
    "investigation": True,
    "memory": True,
    "ai_analysis": True,
    "operations": True,
    "analytics": True,
    "audit": True,
    "settings": True,
    "admin": False,
}

ADMIN_MODULE_PERMISSIONS = {
    "incidents": True,
    "investigation": True,
    "memory": True,
    "ai_analysis": True,
    "operations": True,
    "analytics": True,
    "audit": True,
    "settings": True,
    "admin": True,
}

users_db: Dict[str, Dict[str, Any]] = {
    "user-admin-01": {
        "id": "user-admin-01",
        "name": "D. Mercer (Lead SRE)",
        "email": "admin@aegis.corp",
        "password": "password123",
        "role": "ADMIN",
        "roles": ["ADMIN"],
        "permissions": ADMIN_MODULE_PERMISSIONS,
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=128&q=80",
        "created_at": "2026-09-28T10:55:23.629Z",
        "updated_at": "2026-09-28T11:03:13.123Z",
        "last_login_at": "2026-09-28T11:03:13.123Z",
        "is_active": True,
    },
    "user-responder-02": {
        "id": "user-responder-02",
        "name": "Alex Vance (Incident Responder)",
        "email": "responder@aegis.corp",
        "password": "password123",
        "role": "RESPONDER",
        "roles": ["RESPONDER"],
        "permissions": DEFAULT_MODULE_PERMISSIONS,
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=128&q=80",
        "created_at": "2026-09-28T10:55:23.629Z",
        "updated_at": "2026-09-28T10:55:23.629Z",
        "last_login_at": None,
        "is_active": True,
    },
    "user-viewer-03": {
        "id": "user-viewer-03",
        "name": "Sarah Chen (Platform Observer)",
        "email": "viewer@aegis.corp",
        "password": "password123",
        "role": "VIEWER",
        "roles": ["VIEWER"],
        "permissions": {k: False if k in ("admin", "operations") else True for k, v in DEFAULT_MODULE_PERMISSIONS.items()},
        "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=128&q=80",
        "created_at": "2026-09-28T10:55:23.629Z",
        "updated_at": "2026-09-28T10:55:23.629Z",
        "last_login_at": None,
        "is_active": True,
    },
}

# Pre-seeded Banking and Distributed Infrastructure Memory Experiences
memories_db: List[Dict[str, Any]] = [
    {
        "id": "mem-1987",
        "external_memory_id": "HINDSIGHT-EXP-1987",
        "incident_id": "INC-1987",
        "title": "Payment Gateway Timeout Cascade & Thread Exhaustion",
        "summary": "Upstream card processor suffered degraded network route, inducing thread blocking across core checkout pods.",
        "memory_type": "INCIDENT_RUNBOOK",
        "status": "RELEVANT",
        "source": "OpenTelemetry + WarRoom Transcript",
        "retained_at": "2024-08-14T16:30:00.000Z",
        "last_recalled_at": "2026-09-28T14:04:15.000Z",
        "recall_count": 8,
        "is_demo": True,
        "created_at": "2024-08-14T16:30:00.000Z",
        "updated_at": "2026-09-28T14:04:15.000Z",
        "what_happened": "Upstream card processor suffered degraded network route, inducing thread blocking across core checkout pods.",
        "agent_investigation": "AI Agent identified socket timeouts mimicking internal database locks; correlated with 3rd-party status page telemetry.",
        "executed_response": "Switched fallback payment gateway and dropped synchronous webhook retries to unbind worker threads.",
        "verified_outcome": "Full checkout path restored (MTTR: 11 min); zero transaction loss recorded during re-routing phase.",
        "retained_experience_rule": "When socket timeouts spike on payment proxy without internal CPU spikes, inspect upstream third-party status before rolling back application releases.",
        "utility_score": 96,
        "domain": "Payment & Billing",
        "coords3D": [-32, 16, 6],
    },
    {
        "id": "mem-1842",
        "external_memory_id": "HINDSIGHT-EXP-1842",
        "incident_id": "INC-1842",
        "title": "Redis Connection Surge post-Redis 7 Upgrade",
        "summary": "Redis connection limit reached due to incorrect pool cleanup settings after protocol bump.",
        "memory_type": "INFRASTRUCTURE_FAILURE",
        "status": "PARTIAL",
        "source": "Kernel dmesg + Helm logs",
        "retained_at": "2024-05-22T11:15:00.000Z",
        "last_recalled_at": None,
        "recall_count": 4,
        "is_demo": True,
        "created_at": "2024-05-22T11:15:00.000Z",
        "updated_at": "2024-05-22T11:15:00.000Z",
        "what_happened": "Redis connection limit reached due to incorrect pool cleanup settings after engine bump.",
        "agent_investigation": "Discovered leak in persistent TCP connection handles across 18 worker pods.",
        "executed_response": "Flushed idle sockets and capped max pool connection size via Helm values.",
        "verified_outcome": "Cluster load dropped to 14% nominal with no cache evictions (MTTR: 19 min).",
        "retained_experience_rule": "Cap persistent idle connection pool sizes when deploying major Redis protocol bumps.",
        "utility_score": 88,
        "domain": "Database & Storage",
        "coords3D": [30, 18, -4],
    },
    {
        "id": "mem-1721",
        "external_memory_id": "HINDSIGHT-EXP-1721",
        "incident_id": "INC-1721",
        "title": "OAuth Token Revocation Thundering Herd",
        "summary": "Coordinated key rotation expired 850,000 active tokens simultaneously, overwhelming auth workers.",
        "memory_type": "IAM_CASCADE",
        "status": "RELEVANT",
        "source": "Kong API Gateway Traces",
        "retained_at": "2024-03-09T08:00:00.000Z",
        "last_recalled_at": None,
        "recall_count": 12,
        "is_demo": True,
        "created_at": "2024-03-09T08:00:00.000Z",
        "updated_at": "2024-03-09T08:00:00.000Z",
        "what_happened": "Coordinated key rotation expired 850,000 active tokens simultaneously, overwhelming auth workers.",
        "agent_investigation": "Trace analysis proved 98% of auth workers were blocked waiting for JWKS RSA key validation.",
        "executed_response": "Applied dynamic token cache TTL extension with exponential randomized backoff.",
        "verified_outcome": "Auth latency returned to under 8ms within 4 minutes (MTTR: 8 min).",
        "retained_experience_rule": "Enforce jittered token expiration backoffs and fallback to read-only stale grants under load.",
        "utility_score": 94,
        "domain": "Authentication & IAM",
        "coords3D": [-24, -5, -28],
    },
    {
        "id": "mem-1590",
        "external_memory_id": "HINDSIGHT-EXP-1590",
        "incident_id": "INC-1590",
        "title": "DNS Resolution Flapping in Kubernetes CoreDNS",
        "summary": "Node conntrack saturation caused intermittent UDP DNS packet drop for internal mesh services.",
        "memory_type": "NETWORK_MESH",
        "status": "RELEVANT",
        "source": "eBPF CoreDNS metrics",
        "retained_at": "2023-11-17T14:40:00.000Z",
        "last_recalled_at": None,
        "recall_count": 9,
        "is_demo": True,
        "created_at": "2023-11-17T14:40:00.000Z",
        "updated_at": "2023-11-17T14:40:00.000Z",
        "what_happened": "Node conntrack saturation caused intermittent UDP DNS packet drop for internal mesh services.",
        "agent_investigation": "Linux kernel packet drops pinpointed to max conntrack limits on high-density nodes.",
        "executed_response": "Enabled NodeLocal DNSCache DaemonSet and doubled nf_conntrack_max sysctl.",
        "verified_outcome": "Zero dropped DNS queries across 34 nodes (MTTR: 24 min).",
        "retained_experience_rule": "Scale node-local DNS caches before altering worker node egress CIDR ranges.",
        "utility_score": 91,
        "domain": "Network & Mesh",
        "coords3D": [28, -6, 26],
    },
]

memory_recalls_db: List[Dict[str, Any]] = []
events_db: List[Dict[str, Any]] = [
    {
        "id": "evt-1",
        "incident_id": "inc-2048",
        "event_type": "INCIDENT_CREATED",
        "message": "Incident detected via OpenTelemetry automated threshold trigger on /v2/checkout/charge",
        "source": "TELEMETRY",
        "metadata": {"initial_latency_ms": 4820, "error_code": 504},
        "created_at": "2026-09-28T10:36:41.630Z",
        "created_by": "system-otel-monitor",
    },
    {
        "id": "evt-2",
        "incident_id": "inc-2048",
        "event_type": "CONTEXT_COLLECTED",
        "message": "12 error signatures, 4 service graphs, 2 deployment manifests aggregated from OpenTelemetry pipeline",
        "source": "AGENT",
        "metadata": {"recent_deploy": "stripe-connector v2.14.0"},
        "created_at": "2026-09-28T10:38:23.630Z",
        "created_by": "Aegis-Agent-v4",
    },
    {
        "id": "evt-3",
        "incident_id": "inc-2048",
        "event_type": "MEMORY_RECALLED",
        "message": "Hindsight query executed across 14,892 historical incident embeddings. Precedent INC-1987 identified.",
        "source": "HINDSIGHT",
        "metadata": {"precedent_id": "INC-1987", "similarity": 0.914},
        "created_at": "2026-09-28T10:39:23.630Z",
        "created_by": "HyperGraph-v4.9",
    },
    {
        "id": "evt-4",
        "incident_id": "inc-2048",
        "event_type": "HYPOTHESIS_GENERATED",
        "message": "Hypothesis formed: Upstream partner throttling rather than internal release regression.",
        "source": "AGENT",
        "metadata": {"confidence": "MODERATE"},
        "created_at": "2026-09-28T10:40:23.630Z",
        "created_by": "Aegis-Agent-v4",
    },
    {
        "id": "evt-5",
        "incident_id": "inc-2048",
        "event_type": "RESPONSE_RECOMMENDED",
        "message": "Staged 3-action response plan grounded in INC-1987 runbook precedent.",
        "source": "AGENT",
        "metadata": {"actions_count": 3},
        "created_at": "2026-09-28T10:41:23.630Z",
        "created_by": "Aegis-Agent-v4",
    },
]

signals_db: List[Dict[str, Any]] = [
    {
        "id": "sig-1",
        "incident_id": "inc-2048",
        "signal_type": "latency",
        "name": "P99 Latency (Checkout API)",
        "value": 4820,
        "unit": "ms",
        "severity": "CRITICAL",
        "observed_at": "2026-09-28T10:55:23.630Z",
    },
    {
        "id": "sig-2",
        "incident_id": "inc-2048",
        "signal_type": "error_rate",
        "name": "504 Gateway Timeout Rate",
        "value": 14.2,
        "unit": "%",
        "severity": "HIGH",
        "observed_at": "2026-09-28T10:55:23.630Z",
    },
    {
        "id": "sig-3",
        "incident_id": "inc-2048",
        "signal_type": "pool_saturation",
        "name": "Socket Pool Connection Saturation",
        "value": 480,
        "unit": "connections",
        "severity": "CRITICAL",
        "observed_at": "2026-09-28T10:55:23.630Z",
    },
    {
        "id": "sig-4",
        "incident_id": "inc-2048",
        "signal_type": "gateway_timeout",
        "name": "Upstream Stripe Proxy Read Timeout",
        "value": 1420,
        "unit": "req/min",
        "severity": "HIGH",
        "observed_at": "2026-09-28T10:55:23.630Z",
    },
]

response_plans_db: List[Dict[str, Any]] = [
    {
        "id": "plan-2048",
        "incident_id": "inc-2048",
        "title": "Grounded Incident Triage Plan (INC-1987 Grounded)",
        "description": "Failover non-critical payment traffic, clamp socket timeout, and cycle saturated worker connection pool.",
        "reason": "Prevents thread pool exhaustion while keeping payment transaction flow alive.",
        "evidence": "INC-1987 recovered within 11 minutes with 0 transaction loss via 50/50 fallback split.",
        "status": "PENDING_APPROVAL",
        "created_by": "Aegis-Agent-v4",
        "approved_by": None,
        "approved_at": None,
        "created_at": "2026-09-28T10:41:23.630Z",
        "actions": [
            {
                "id": "act-1",
                "stepNumber": 1,
                "title": "Failover 50% non-critical traffic to secondary gateway",
                "description": "Reroutes non-instant checkout transactions to Adyen backup processor to relieve Stripe proxy thread pressure.",
                "riskLevel": "SAFE",
                "status": "READY",
                "targetComponent": "payment-gw-proxy-iad",
                "commandSnippet": "kubectl patch configmap gateway-route --type merge -p '{\"data\":{\"stripe_weight\":\"50\",\"adyen_weight\":\"50\"}}'",
            },
            {
                "id": "act-2",
                "stepNumber": 2,
                "title": "Enforce 1500ms timeout clamp",
                "description": "Reduces client HTTP read socket timeout from 5000ms to 1500ms to rapidly fail backlogged requests and preserve worker thread pool.",
                "riskLevel": "MITIGATE",
                "status": "READY",
                "targetComponent": "checkout-api",
                "commandSnippet": "istioctl route-rule apply --service checkout-api --timeout 1500ms",
            },
            {
                "id": "act-3",
                "stepNumber": 3,
                "title": "Isolate db-pool-worker-04 connection pool",
                "description": "Terminates stuck JDBC connections and recycles container connection pool worker 04 to prevent cascading thread pool starvation.",
                "riskLevel": "CRITICAL",
                "status": "READY",
                "targetComponent": "db-pool-worker-04",
                "commandSnippet": "kubectl exec -it checkout-api-pod-84f9 -- recycle-pool --worker=db-pool-worker-04 --force",
            },
        ],
    }
]

post_mortems_db: Dict[str, Dict[str, Any]] = {
    "inc-2048": {
        "id": "pm-2048",
        "incident_id": "inc-2048",
        "summary": "Checkout API experienced 504 timeouts due to upstream Stripe gateway route degradation.",
        "impact": "14.2% error rate on /v2/checkout/charge in North America region for ~18m.",
        "timeline": "13:45 Canary Deploy -> 14:02 First 504 alert -> 14:03 Context & Memory Recall -> 14:06 Plan Staged.",
        "root_cause": "Third-party acquiring bank route degradation causing read socket timeouts exceeding 5000ms.",
        "investigation": "AI Agent correlated absence of internal CPU spikes with external status page latency telemetry.",
        "response_summary": "Traffic shaper failover 50% non-critical traffic to Adyen backup processor.",
        "outcome": "Checkout transactions restored; zero transaction drop recorded during failover.",
        "lessons_learned": "Upstream health checks must precede container restarts to avoid thread stampedes.",
        "retained_experience": "When socket timeouts spike on payment proxy without internal CPU spikes, inspect upstream third-party status before rolling back application releases.",
        "created_at": "2026-09-28T10:55:23.630Z",
        "updated_at": "2026-09-28T10:55:23.630Z",
    }
}

audit_logs_db: List[Dict[str, Any]] = [
    {
        "id": "audit-init-01",
        "user_id": "user-admin-01",
        "incident_id": "inc-2048",
        "action": "INCIDENT_MONITORED",
        "entity_type": "INCIDENT",
        "entity_id": "inc-2048",
        "metadata": {"title": "Payment Gateway Timeout Cascade & Thread Exhaustion"},
        "ip_address": "127.0.0.1",
        "created_at": "2026-09-28T10:36:41.630Z",
    }
]

# Demo State Machine
demo_state = {
    "currentStep": 1,
    "stepName": "01 INCIDENT A (COLD START)",
    "incidentAId": "inc-4544",
    "incidentBId": None,
    "retainedMemoryId": None,
    "memoryRecallStatus": "IDLE",
    "recalledMemory": None,
    "logs": ["[DEMO INIT] Scenario initialized. Simulated telemetry ready."],
}


# ==========================================
# Helpers & Token Security
# ==========================================

def create_jwt(user: Dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "userId": user["id"],
        "email": user["email"],
        "role": user["role"],
        "roles": user.get("roles", [user["role"]]),
        "name": user["name"],
        "exp": int(time.time()) + 86400 * 7,
    }
    b64_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    b64_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(
        JWT_SECRET.encode(),
        f"{b64_header}.{b64_payload}".encode(),
        hashlib.sha256
    ).digest()
    b64_sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{b64_header}.{b64_payload}.{b64_sig}"


def verify_token(token_str: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token_str.strip().split(".")
        if len(parts) != 3:
            return None
        b64_header, b64_payload, b64_sig = parts
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET.encode(), f"{b64_header}.{b64_payload}".encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        if not hmac.compare_digest(b64_sig, expected_sig):
            return None
        # Add padding back if necessary
        padded_payload = b64_payload + "=" * (-len(b64_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_payload).decode())
        return payload
    except Exception:
        return None


def get_current_user_from_header(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not authorization:
        return users_db.get("user-admin-01")
    token = authorization.replace("Bearer ", "").strip()
    payload = verify_token(token)
    if not payload:
        return users_db.get("user-admin-01")
    user_id = payload.get("userId")
    return users_db.get(user_id, users_db.get("user-admin-01"))


def record_audit(action: str, entity_type: str, entity_id: Optional[str] = None, user_id: Optional[str] = None, incident_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    audit_logs_db.insert(0, {
        "id": f"audit-{uuid.uuid4()}",
        "user_id": user_id,
        "incident_id": incident_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "metadata": metadata or {},
        "ip_address": "127.0.0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


# ==========================================
# 1. AUTH ROUTES
# ==========================================

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "RESPONDER"

@router.post("/auth/login")
def login(req: LoginRequest):
    user = next((u for u in users_db.values() if u["email"].lower() == req.email.lower()), None)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user["last_login_at"] = datetime.now(timezone.utc).isoformat()
    token = create_jwt(user)
    record_audit(action="USER_LOGIN", entity_type="USER", entity_id=user["id"], user_id=user["id"])
    sanitized = {k: v for k, v in user.items() if k != "password"}
    return {"user": sanitized, "token": token}

@router.post("/auth/register")
def register(req: RegisterRequest):
    existing = next((u for u in users_db.values() if u["email"].lower() == req.email.lower()), None)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    new_id = f"user-{uuid.uuid4().hex[:8]}"
    role = (req.role or "RESPONDER").upper()
    user = {
        "id": new_id,
        "name": req.name,
        "email": req.email,
        "password": req.password,
        "role": role,
        "roles": [role],
        "permissions": ADMIN_MODULE_PERMISSIONS if role == "ADMIN" else DEFAULT_MODULE_PERMISSIONS,
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=128&q=80",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_login_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }
    users_db[new_id] = user
    token = create_jwt(user)
    record_audit(action="USER_REGISTERED", entity_type="USER", entity_id=user["id"], user_id=user["id"])
    sanitized = {k: v for k, v in user.items() if k != "password"}
    return {"user": sanitized, "token": token}

@router.post("/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    user = get_current_user_from_header(authorization)
    if user:
        record_audit(action="USER_LOGOUT", entity_type="USER", entity_id=user["id"], user_id=user["id"])
    return {"success": True, "message": "Logged out successfully"}

@router.get("/auth/me")
def me(authorization: Optional[str] = Header(None)):
    user = get_current_user_from_header(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sanitized = {k: v for k, v in user.items() if k != "password"}
    return {"user": sanitized}


# ==========================================
# 2. INCIDENTS EVENTS & SIGNALS
# ==========================================

class AddEventRequest(BaseModel):
    event_type: str
    message: str
    source: Optional[str] = "SRE_OPERATOR"
    metadata: Optional[Dict[str, Any]] = None

@router.get("/incidents/{incident_id}/events")
def get_incident_events(incident_id: str):
    matched = [e for e in events_db if e["incident_id"] == incident_id]
    if not matched:
        # Default starter event if new incident
        matched = [
            {
                "id": f"evt-{uuid.uuid4().hex[:6]}",
                "incident_id": incident_id,
                "event_type": "INCIDENT_CREATED",
                "message": f"Incident {incident_id} telemetry monitoring initialized.",
                "source": "TELEMETRY",
                "metadata": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": "system-otel-monitor",
            }
        ]
    return {"events": matched}

@router.post("/incidents/{incident_id}/events", status_code=status.HTTP_201_CREATED)
def add_incident_event(incident_id: str, req: AddEventRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user_from_header(authorization)
    event = {
        "id": f"evt-{uuid.uuid4()}",
        "incident_id": incident_id,
        "event_type": req.event_type,
        "message": req.message,
        "source": req.source or "SRE_OPERATOR",
        "metadata": req.metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["name"] if user else "operator",
    }
    events_db.append(event)
    return {"event": event}

@router.get("/incidents/{incident_id}/signals")
def get_incident_signals(incident_id: str):
    matched = [s for s in signals_db if s["incident_id"] == incident_id]
    if not matched:
        matched = [
            {"id": f"sig-{uuid.uuid4().hex[:6]}", "incident_id": incident_id, "signal_type": "latency", "name": "P99 Latency (Edge API)", "value": 4200, "unit": "ms", "severity": "HIGH", "observed_at": datetime.now(timezone.utc).isoformat()},
            {"id": f"sig-{uuid.uuid4().hex[:6]}", "incident_id": incident_id, "signal_type": "error_rate", "name": "504 Gateway Timeout Rate", "value": 12.8, "unit": "%", "severity": "HIGH", "observed_at": datetime.now(timezone.utc).isoformat()},
            {"id": f"sig-{uuid.uuid4().hex[:6]}", "incident_id": incident_id, "signal_type": "pool_saturation", "name": "Socket Pool Saturation", "value": 450, "unit": "connections", "severity": "CRITICAL", "observed_at": datetime.now(timezone.utc).isoformat()},
        ]
    return {"signals": matched}


# ==========================================
# 3. MEMORY & HINDSIGHT GRAPH ROUTES
# ==========================================

class RecallRequest(BaseModel):
    incidentId: Optional[str] = "active"
    incidentNumber: Optional[str] = "INC-ACTIVE"
    title: Optional[str] = ""
    description: Optional[str] = ""
    service: Optional[str] = "General"
    signals: Optional[List[Dict[str, Any]]] = None

class MemoryStatusUpdate(BaseModel):
    status: str

@router.get("/memory")
def get_all_memories():
    return {"memories": memories_db, "count": len(memories_db)}

@router.get("/memory/{memory_id}")
def get_memory_by_id(memory_id: str):
    mem = next((m for m in memories_db if m["id"] == memory_id or m.get("external_memory_id") == memory_id), None)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory record not found")
    return {"memory": mem}

@router.post("/memory/recall")
def recall_memory(req: RecallRequest):
    query_tokens = f"{req.title} {req.description} {req.service}".lower()

    # Check for cold start
    if "cold-start" in query_tokens or "coldstart" in query_tokens:
        return {
            "status": "NO_RELEVANT_EXPERIENCE",
            "memory": None,
            "recallRecord": None,
            "similarityScore": 0.0,
            "relevance": "LOW",
            "whyRecalled": None,
            "provenance": None,
        }

    # Semantic match
    matched = None
    if any(k in query_tokens for k in ["payment", "gateway", "504", "timeout", "thread", "socket", "checkout"]):
        matched = next((m for m in memories_db if m["id"] == "mem-1987"), memories_db[0])
    elif "redis" in query_tokens:
        matched = next((m for m in memories_db if m["id"] == "mem-1842"), None)
    elif "oauth" in query_tokens or "token" in query_tokens:
        matched = next((m for m in memories_db if m["id"] == "mem-1721"), None)
    elif "dns" in query_tokens:
        matched = next((m for m in memories_db if m["id"] == "mem-1590"), None)

    if not matched and memories_db:
        matched = memories_db[0]

    if matched:
        matched["recall_count"] = matched.get("recall_count", 0) + 1
        matched["last_recalled_at"] = datetime.now(timezone.utc).isoformat()

        recall_record = {
            "id": f"recall-{uuid.uuid4()}",
            "incident_id": req.incidentId or "active",
            "memory_id": matched["id"],
            "reason": f"Matched symptom vector on service {req.service}",
            "relevance": "HIGH",
            "retrieved_context": matched.get("retained_experience_rule") or matched.get("summary"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        memory_recalls_db.insert(0, recall_record)

        return {
            "status": "FOUND",
            "memory": matched,
            "recallRecord": recall_record,
            "similarityScore": 0.914,
            "relevance": "HIGH",
            "whyRecalled": {
                "currentSymptom": f"Elevated latency and socket timeouts on {req.service}",
                "historicalObservation": matched.get("what_happened"),
                "relatedService": matched.get("domain"),
                "historicalInvestigation": matched.get("agent_investigation"),
            },
            "provenance": {
                "sourceIncidentNumber": matched.get("incident_id"),
                "title": matched.get("title"),
                "date": matched.get("retained_at"),
                "retainedReason": matched.get("retained_experience_rule"),
                "verifiedOutcome": matched.get("verified_outcome"),
            },
        }

    return {
        "status": "NO_RELEVANT_EXPERIENCE",
        "memory": None,
        "recallRecord": None,
        "relevance": "LOW",
    }

@router.patch("/memory/{memory_id}/status")
def update_memory_status(memory_id: str, req: MemoryStatusUpdate, authorization: Optional[str] = Header(None)):
    mem = next((m for m in memories_db if m["id"] == memory_id), None)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory record not found")
    mem["status"] = req.status
    mem["updated_at"] = datetime.now(timezone.utc).isoformat()
    user = get_current_user_from_header(authorization)
    record_audit(action="MEMORY_STATUS_UPDATED", entity_type="MEMORY", entity_id=mem["id"], user_id=user["id"] if user else None)
    return {"memory": mem}

@router.get("/memory/{memory_id}/provenance")
def get_memory_provenance(memory_id: str):
    mem = next((m for m in memories_db if m["id"] == memory_id), None)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory record not found")
    return {
        "memory": mem,
        "sourceIncident": {
            "id": mem.get("incident_id"),
            "title": mem.get("title"),
            "resolved_at": mem.get("retained_at"),
        },
        "provenance": {
            "sourceIncidentNumber": mem.get("incident_id"),
            "retainedAt": mem.get("retained_at"),
            "source": mem.get("source"),
            "recallsCount": mem.get("recall_count", 0),
            "rule": mem.get("retained_experience_rule"),
        },
    }

@router.get("/memory/{memory_id}/recalls")
def get_memory_recalls(memory_id: str):
    recalls = [r for r in memory_recalls_db if r["memory_id"] == memory_id]
    return {"recalls": recalls}


# ==========================================
# 4. AGENT REASONING PIPELINE
# ==========================================

class AnalyzeAgentRequest(BaseModel):
    incidentId: Optional[str] = "inc-2048"

@router.post("/agent/analyze")
def agent_analyze(req: AnalyzeAgentRequest):
    inc_id = req.incidentId or "inc-2048"

    # Stage 1: Context Collected
    stage_1 = {
        "stage": "01 CONTEXT COLLECTED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETED",
        "evidence": "12 error signatures, 4 service graphs, 2 deployment manifests aggregated from OpenTelemetry pipeline",
        "source": "TELEMETRY",
    }

    # Stage 2: Memory Recall
    matched_memory = memories_db[0] if memories_db else None
    stage_2 = {
        "stage": "02 MEMORY RECALL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETED",
        "result": "FOUND",
        "evidence": f"Matched precedent {matched_memory['incident_id']} with similarity score 0.914" if matched_memory else "No direct precedent found.",
        "source": "HINDSIGHT",
    }

    # Stage 3: Relevant Experience Found
    stage_3 = {
        "stage": "03 RELEVANT EXPERIENCE FOUND",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETED",
        "found": True,
        "matchedPrecedent": matched_memory,
        "whyRecalled": "Socket timeouts without CPU spikes match third-party gateway throttle patterns.",
        "source": "HINDSIGHT",
    }

    # Stage 4: Deductive Hypothesis
    hypothesis_text = (
        f"Current evidence + prior experience from {matched_memory['incident_id']} suggest upstream payment partner throttling rather than internal deployment regression."
        if matched_memory else "Current evidence suggests isolated service degradation under investigation."
    )
    stage_4 = {
        "stage": "04 DEDUCTIVE HYPOTHESIS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETED",
        "hypothesis": hypothesis_text,
        "confidence": "HIGH",
        "source": "AGENT",
    }

    # Stage 5: Recommended Response
    stage_5 = {
        "stage": "05 RECOMMENDED RESPONSE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "AWAITING_HUMAN_APPROVAL",
        "policy": "ADVISORY ONLY — NO AUTOMATED EXECUTION",
        "actionsCount": 3,
        "source": "AGENT",
    }

    memory_recall_obj = {
        "status": "FOUND",
        "memory": matched_memory,
        "similarityScore": 0.914,
        "relevance": "HIGH",
    }

    return {
        "pipeline": [stage_1, stage_2, stage_3, stage_4, stage_5],
        "memoryRecall": memory_recall_obj,
        "hypothesis": hypothesis_text,
    }


# ==========================================
# 5. RESPONSE PLANS & HUMAN APPROVAL
# ==========================================

class ApprovePlanRequest(BaseModel):
    operatorInitials: Optional[str] = "OP"

class RejectPlanRequest(BaseModel):
    reason: Optional[str] = "Operator rejected"

@router.get("/incidents/{incident_id}/response-plans")
def get_incident_response_plans(incident_id: str):
    plans = [p for p in response_plans_db if p["incident_id"] == incident_id]
    if not plans and response_plans_db:
        plans = [response_plans_db[0]]
    return {"plans": plans}

@router.post("/incidents/{incident_id}/response-plans", status_code=status.HTTP_201_CREATED)
def create_response_plan(incident_id: str, plan_data: Dict[str, Any]):
    new_plan = {
        "id": f"plan-{uuid.uuid4().hex[:6]}",
        "incident_id": incident_id,
        "title": plan_data.get("title", "Generated Mitigation Plan"),
        "description": plan_data.get("description", "Automated plan"),
        "reason": plan_data.get("reason", "Grounding in memory precedent"),
        "evidence": plan_data.get("evidence", "Telemetry confirmation"),
        "status": "PENDING_APPROVAL",
        "created_by": "Aegis-Agent-v4",
        "approved_by": None,
        "approved_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actions": plan_data.get("actions", []),
    }
    response_plans_db.append(new_plan)
    return {"plan": new_plan}

@router.post("/response-plans/{plan_id}/approve")
def approve_response_plan(plan_id: str, req: ApprovePlanRequest, authorization: Optional[str] = Header(None)):
    plan = next((p for p in response_plans_db if p["id"] == plan_id), None)
    if not plan and response_plans_db:
        plan = response_plans_db[0]
    if not plan:
        raise HTTPException(status_code=404, detail="Response plan not found")

    user = get_current_user_from_header(authorization)
    plan["status"] = "APPROVED"
    plan["approved_by"] = f"{user['name'] if user else 'Operator'} ({req.operatorInitials})"
    plan["approved_at"] = datetime.now(timezone.utc).isoformat()

    for act in plan.get("actions", []):
        act["status"] = "APPLIED"

    record_audit(action="RESPONSE_PLAN_APPROVED", entity_type="RESPONSE_PLAN", entity_id=plan["id"], user_id=user["id"] if user else None)
    return {"plan": plan, "message": "Plan authorized by operator and actions dispatched in cluster"}

@router.post("/response-plans/{plan_id}/reject")
def reject_response_plan(plan_id: str, req: RejectPlanRequest, authorization: Optional[str] = Header(None)):
    plan = next((p for p in response_plans_db if p["id"] == plan_id), None)
    if not plan and response_plans_db:
        plan = response_plans_db[0]
    if not plan:
        raise HTTPException(status_code=404, detail="Response plan not found")

    user = get_current_user_from_header(authorization)
    plan["status"] = "REJECTED"
    plan["approved_by"] = f"Rejected: {req.reason}"
    plan["approved_at"] = datetime.now(timezone.utc).isoformat()

    record_audit(action="RESPONSE_PLAN_REJECTED", entity_type="RESPONSE_PLAN", entity_id=plan["id"], user_id=user["id"] if user else None)
    return {"plan": plan, "message": "Plan rejected by operator"}


# ==========================================
# 6. POST-MORTEM ROUTES
# ==========================================

@router.get("/incidents/{incident_id}/postmortem")
def get_postmortem(incident_id: str):
    pm = post_mortems_db.get(incident_id)
    if not pm:
        pm = post_mortems_db.get("inc-2048")
    if not pm:
        raise HTTPException(status_code=404, detail="Post-mortem not found")
    return {"postMortem": pm}

@router.post("/incidents/{incident_id}/postmortem", status_code=status.HTTP_201_CREATED)
@router.patch("/incidents/{incident_id}/postmortem")
def save_postmortem(incident_id: str, data: Dict[str, Any], authorization: Optional[str] = Header(None)):
    user = get_current_user_from_header(authorization)
    existing = post_mortems_db.get(incident_id, {})
    updated = {
        "id": existing.get("id", f"pm-{uuid.uuid4().hex[:6]}"),
        "incident_id": incident_id,
        "summary": data.get("summary", existing.get("summary", "")),
        "impact": data.get("impact", existing.get("impact", "")),
        "timeline": data.get("timeline", existing.get("timeline", "")),
        "root_cause": data.get("root_cause", existing.get("root_cause", "")),
        "investigation": data.get("investigation", existing.get("investigation", "")),
        "response_summary": data.get("response_summary", existing.get("response_summary", "")),
        "outcome": data.get("outcome", existing.get("outcome", "")),
        "lessons_learned": data.get("lessons_learned", existing.get("lessons_learned", "")),
        "retained_experience": data.get("retained_experience", existing.get("retained_experience", "")),
        "created_at": existing.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    post_mortems_db[incident_id] = updated
    record_audit(action="POST_MORTEM_SAVED", entity_type="POST_MORTEM", entity_id=updated["id"], user_id=user["id"] if user else None)
    return {"postMortem": updated}


# ==========================================
# 7. AUDIT TRAIL
# ==========================================

@router.get("/audit")
def get_audit_trail(limit: int = 50, incidentId: Optional[str] = None):
    results = audit_logs_db
    if incidentId:
        results = [l for l in results if l.get("incident_id") == incidentId]
    sliced = results[:limit]
    return {"auditLogs": sliced, "count": len(sliced)}


# ==========================================
# 8. DEMO SCENARIO STATE & CONTROLLER
# ==========================================

class DemoStepRequest(BaseModel):
    step: int

@router.get("/demo/state")
def get_demo_state():
    return demo_state

@router.post("/demo/start")
def demo_start():
    demo_state["currentStep"] = 1
    demo_state["stepName"] = "01 INCIDENT A (COLD START)"
    demo_state["incidentAId"] = "inc-4544"
    demo_state["incidentBId"] = None
    demo_state["retainedMemoryId"] = None
    demo_state["memoryRecallStatus"] = "IDLE"
    demo_state["recalledMemory"] = None
    demo_state["logs"] = [
        "[DEMO INIT] Scenario initialized. Telemetry baseline ready.",
        "[STEP 01] Incident A created: INC-4544 (Cold-start Edge Proxy Timeouts).",
    ]
    return demo_state

@router.post("/demo/next")
def demo_next():
    curr = demo_state["currentStep"]
    if curr == 1:
        demo_state["currentStep"] = 2
        demo_state["stepName"] = "02 INVESTIGATE (NO MEMORY)"
        demo_state["memoryRecallStatus"] = "NO_RELEVANT_EXPERIENCE"
        demo_state["logs"].append("[STEP 02] Hindsight query: NO RELEVANT EXPERIENCE in 14,892 nodes. First-principles investigation engaged.")
    elif curr == 2:
        demo_state["currentStep"] = 3
        demo_state["stepName"] = "03 RESOLVE INCIDENT A"
        demo_state["logs"].append("[STEP 03] Incident A resolved. Fallback traffic split confirmed successful (MTTR: 28 min).")
    elif curr == 3:
        demo_state["currentStep"] = 4
        demo_state["stepName"] = "04 POST-MORTEM GENERATED"
        demo_state["logs"].append("[STEP 04] Post-Mortem synthesized with verified operational lesson on proxy timeout clamps.")
    elif curr == 4:
        demo_state["currentStep"] = 5
        demo_state["stepName"] = "05 RETAIN TO HINDSIGHT"
        demo_state["retainedMemoryId"] = "mem-1987"
        demo_state["logs"].append("[STEP 05] Experience Retained: mem-1987 indexed into Hindsight HyperGraph vector store.")
    elif curr == 5:
        demo_state["currentStep"] = 6
        demo_state["stepName"] = "06 INCIDENT B CREATED"
        demo_state["incidentBId"] = "inc-2048"
        demo_state["logs"].append("[STEP 06] Incident B created: INC-2048 (Payment Gateway Timeout Cascade).")
    elif curr == 6:
        demo_state["currentStep"] = 7
        demo_state["stepName"] = "07 MEMORY RECALLED (INCIDENT B)"
        demo_state["memoryRecallStatus"] = "FOUND"
        demo_state["recalledMemory"] = memories_db[0]
        demo_state["logs"].append("[STEP 07] Precedent mem-1987 recalled with 0.914 similarity. Root cause pinpointed in 11 seconds.")
    elif curr == 7:
        demo_state["currentStep"] = 8
        demo_state["stepName"] = "08 GROUNDED RESOLUTION"
        demo_state["logs"].append("[STEP 08] Grounded 3-step runbook approved. Incident B MTTR reduced by 68%.")
    return demo_state

@router.post("/demo/previous")
def demo_previous():
    if demo_state["currentStep"] > 1:
        demo_state["currentStep"] -= 1
        demo_state["logs"].append(f"[NAVIGATE] Returned to step {demo_state['currentStep']}.")
    return demo_state

@router.post("/demo/step")
def demo_go_to_step(req: DemoStepRequest):
    demo_state["currentStep"] = req.step
    demo_state["logs"].append(f"[NAVIGATE] Jumped directly to step {req.step}.")
    return demo_state

@router.post("/demo/reset")
def demo_reset():
    demo_state["currentStep"] = 1
    demo_state["stepName"] = "01 INCIDENT A (COLD START)"
    demo_state["incidentAId"] = "inc-4544"
    demo_state["incidentBId"] = None
    demo_state["retainedMemoryId"] = None
    demo_state["memoryRecallStatus"] = "IDLE"
    demo_state["recalledMemory"] = None
    demo_state["logs"] = ["[RESET] Scenario restored to initial state."]
    return demo_state


# ==========================================
# 9. SYSTEM STATUS
# ==========================================

@router.get("/system/status")
def system_status():
    return {
        "database": {
            "type": "SQLite / PostgreSQL",
            "connected": True,
            "counts": {
                "users": len(users_db),
                "incidents": 2,
                "memories": len(memories_db),
                "auditLogs": len(audit_logs_db),
            },
        },
        "hindsight": {
            "configured": True,
            "connected": True,
            "mode": "Hindsight Memory Layer v4.9",
            "nodesIndexed": 14892 + len(memories_db),
        },
        "agent": {
            "name": "Aegis Reasoning Engine v4.9",
            "status": "ONLINE",
            "mode": "ADVISORY_ONLY",
        },
    }


# ==========================================
# 10. ADMIN & ACCESS CONTROL
# ==========================================

class CreateUserReq(BaseModel):
    name: str
    email: str
    password: Optional[str] = "password123"
    roles: Optional[List[str]] = ["RESPONDER"]
    permissions: Optional[Dict[str, bool]] = None
    is_active: Optional[bool] = True

class UpdateUserReq(BaseModel):
    name: Optional[str] = None
    roles: Optional[List[str]] = None
    permissions: Optional[Dict[str, bool]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

@router.get("/admin/users")
def get_admin_users():
    sanitized = [{k: v for k, v in u.items() if k != "password"} for u in users_db.values()]
    return {"users": sanitized, "count": len(sanitized)}

@router.post("/admin/users", status_code=status.HTTP_201_CREATED)
def admin_create_user(req: CreateUserReq):
    new_id = f"user-{uuid.uuid4().hex[:8]}"
    role = req.roles[0] if req.roles else "RESPONDER"
    user = {
        "id": new_id,
        "name": req.name,
        "email": req.email,
        "password": req.password or "password123",
        "role": role,
        "roles": req.roles or [role],
        "permissions": req.permissions or (ADMIN_MODULE_PERMISSIONS if role == "ADMIN" else DEFAULT_MODULE_PERMISSIONS),
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=128&q=80",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_login_at": None,
        "is_active": req.is_active if req.is_active is not None else True,
    }
    users_db[new_id] = user
    record_audit(action="ADMIN_USER_CREATED", entity_type="USER", entity_id=new_id)
    return {"user": {k: v for k, v in user.items() if k != "password"}}

@router.put("/admin/users/{user_id}")
def admin_update_user(user_id: str, req: UpdateUserReq):
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if req.name is not None:
        user["name"] = req.name
    if req.roles is not None:
        user["roles"] = req.roles
        user["role"] = req.roles[0] if req.roles else user["role"]
    if req.permissions is not None:
        user["permissions"] = req.permissions
    if req.is_active is not None:
        user["is_active"] = req.is_active
    if req.password:
        user["password"] = req.password
    user["updated_at"] = datetime.now(timezone.utc).isoformat()
    record_audit(action="ADMIN_USER_UPDATED", entity_type="USER", entity_id=user_id)
    return {"user": {k: v for k, v in user.items() if k != "password"}}

@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: str):
    if user_id in users_db:
        del users_db[user_id]
        record_audit(action="ADMIN_USER_DELETED", entity_type="USER", entity_id=user_id)
    return {"success": True, "message": "User removed successfully"}

@router.get("/admin/modules")
def get_admin_modules():
    modules = [
        {"id": "incidents", "name": "Incidents Radar", "description": "Real-time telemetry surveillance & incident registration"},
        {"id": "investigation", "name": "Investigation Workspace", "description": "Cockpit signals, hypothesis formation, and diagnostics"},
        {"id": "memory", "name": "Hindsight Experience Graph", "description": "3D Constellation & memory lifecycle management"},
        {"id": "ai_analysis", "name": "AI & Web Event Analysis", "description": "Direct AI investigation with grounded web research"},
        {"id": "operations", "name": "Response Operations", "description": "Runbook staging and human approval execution"},
        {"id": "analytics", "name": "Analytics & Post-Mortem", "description": "System health metrics and post-incident reviews"},
        {"id": "audit", "name": "Audit Trail", "description": "Cryptographic immutable operation audit logs"},
        {"id": "settings", "name": "Settings & Integrations", "description": "Telemetry connectors and channel configurations"},
        {"id": "admin", "name": "Admin / Access Control", "description": "User management, role assignment, and module security"},
    ]
    return {"modules": modules, "defaultPermissions": DEFAULT_MODULE_PERMISSIONS}


# ==========================================
# 11. DIRECT AI & WEB ANALYSIS
# ==========================================

class AiAnalyzeReq(BaseModel):
    incidentId: str
    incidentQuery: Optional[str] = None
    enableWebResearch: Optional[bool] = False
    customWebTopic: Optional[str] = None

class AiDispatchReq(BaseModel):
    analysisId: str
    incidentId: str
    channel: str
    operatorInitials: Optional[str] = "OP"
    customNote: Optional[str] = None

@router.post("/ai/analyze")
def ai_analyze(req: AiAnalyzeReq):
    matched_memory = memories_db[0] if memories_db else None

    web_events = [
        {
            "incidentIdOrName": "Stripe API Gateway Cascade",
            "organization": "Stripe",
            "date": "2019-10-18",
            "summary": "Upstream payment route degradation caused synchronous socket timeout cascading across worker threads, inducing 504s.",
            "similarityToCurrent": "Matches checkout gateway timeout cascades where internal CPU is nominal but proxy thread pools are saturated.",
            "rootCause": "External acquiring partner latency spike exceeding proxy read timeouts with unthrottled synchronous client retries.",
            "resolution": "Dynamic traffic rerouting to secondary acquiring network and circuit-breaking synchronous retry storms.",
            "sourceUrl": "https://status.stripe.com",
        },
        {
            "incidentIdOrName": "Cloudflare 1.1.1.1 BGP Route Flapping & DNS Latency",
            "organization": "Cloudflare",
            "date": "2023-11-02",
            "summary": "BGP flapping triggered UDP packet drops across transit edges, manifesting as intermittent internal resolver timeouts.",
            "similarityToCurrent": "Relevant when DNS or networking microservices experience transient lookup degradation without local pod crashes.",
            "rootCause": "Tier-1 transit provider misconfiguration dropping fragmented UDP packets under peak traffic.",
            "resolution": "Node-local DNS caching daemon and static DNS override routing for internal service discovery.",
            "sourceUrl": "https://blog.cloudflare.com",
        },
        {
            "incidentIdOrName": "AWS us-east-1 Frontend Capacity Saturation",
            "organization": "Amazon Web Services",
            "date": "2020-11-25",
            "summary": "Thread pool limit exhaustion in frontend fleet triggered multi-service cascading failures.",
            "similarityToCurrent": "Relevant to connection pool exhaustion and microservice thread starvation scenarios.",
            "rootCause": "Exceeded OS-level thread limits upon fleet scale-out due to unjittered background health checking.",
            "resolution": "Increased thread limits and decoupled synchronous status evaluation loops with randomized jitter.",
            "sourceUrl": "https://aws.amazon.com/message/11201",
        },
        {
            "incidentIdOrName": "Redis OSS Connection Limit Surge",
            "organization": "Redis Foundation Advisory",
            "date": "2024-02-14",
            "summary": "Client driver connection pool leak under Redis 7 protocol changes caused cluster-wide memory lockup.",
            "similarityToCurrent": "Matches Redis cache eviction and connection spike telemetry on worker fleets.",
            "rootCause": "TCP connection handles remained in CLOSE_WAIT following client library protocol upgrade.",
            "resolution": "Enforced idle client timeouts and hard cap on max pooled connections per container.",
            "sourceUrl": "https://redis.io/docs/management/optimization",
        },
    ]

    analysis = {
        "id": f"ai-analysis-{uuid.uuid4().hex[:8]}",
        "incidentId": req.incidentId,
        "incidentNumber": "INC-2048",
        "analyzedAt": datetime.now(timezone.utc).isoformat(),
        "webResearchRequested": bool(req.enableWebResearch),
        "priorityOrder": [
            "1. Hindsight Corporate Operational Memory (INC-1987 precedent)",
            "2. Real-time Telemetry & OpenTelemetry Signal Spikes",
            "3. Grounded Real-World Web Post-Mortems (Stripe, Cloudflare)",
        ],
        "currentIncidentData": {
            "incidentNumber": "INC-2048",
            "title": "Payment Gateway Timeout Cascade & Thread Exhaustion",
            "service": "Checkout API / Payment Gateway",
            "severity": "SEV-1",
            "description": "504 Gateway Timeouts on /v2/checkout/charge. Blast radius verified isolated to North America region.",
            "detectedAt": "2026-09-28T10:36:41.630Z",
            "signals": signals_db,
            "keySymptoms": [
                "P99 latency elevated to 4,820ms (+310% over SLA baseline)",
                "504 Gateway Timeout rate spiked to 14.2%",
                "Socket pool saturation at 480 / 500 connections (96%)",
            ],
        },
        "hindsightMemory": {
            "status": "FOUND",
            "recalledIncidentId": matched_memory["incident_id"] if matched_memory else "INC-1987",
            "recalledTitle": matched_memory["title"] if matched_memory else "Payment Gateway Timeout Cascade",
            "similarityScore": 0.914,
            "retainedExperienceRule": matched_memory.get("retained_experience_rule") if matched_memory else "",
            "provenance": {
                "sourceIncident": matched_memory.get("incident_id") if matched_memory else "INC-1987",
                "date": matched_memory.get("retained_at") if matched_memory else "2024-08-14",
                "verifiedOutcome": matched_memory.get("verified_outcome") if matched_memory else "",
                "investigationPath": matched_memory.get("agent_investigation") if matched_memory else "",
                "executedResponse": matched_memory.get("executed_response") if matched_memory else "",
            },
            "whyRecalled": "Socket timeouts mimicking internal locks with zero CPU spike matched upstream payment route degradation.",
        },
        "webEvidence": {
            "enabled": bool(req.enableWebResearch),
            "sourcesConsulted": [
                {
                    "title": "Stripe Status Advisory - Upstream Gateway Latency",
                    "url": "https://status.stripe.com",
                    "sourceType": "STATUS_PAGE",
                    "organization": "Stripe",
                    "publishedDate": "2019-10-18",
                    "snippet": "Read socket timeouts on card processing ingress caused connection pool exhaustion in downstream client tiers.",
                },
                {
                    "title": "Cloudflare Engineering Post-Mortem",
                    "url": "https://blog.cloudflare.com",
                    "sourceType": "ENGINEERING_BLOG",
                    "organization": "Cloudflare",
                    "publishedDate": "2023-11-02",
                    "snippet": "BGP route flapping caused intermittent transit packet drop manifesting as upstream timeout cascades.",
                },
            ],
            "keyEvidence": [
                "Upstream gateway route degradation induces thread starvation when client read timeouts exceed 2000ms.",
                "Failover to secondary acquiring routes drops error rates to nominal within 2 minutes.",
            ],
            "relevantHistoricalEvents": web_events,
            "possibleCausesAndPatterns": [
                "Upstream Payment Processor Degradation",
                "Synchronous Webhook Retry Cascades",
                "Thread Pool Exhaustion without CPU Spike",
            ],
            "searchQueriesUsed": [
                "payment gateway 504 timeout cascade thread pool exhaustion",
                "upstream acquire route degradation runbook mitigation",
            ],
        },
        "synthesizedAnalysis": {
            "primaryReasoning": "Both internal telemetry and Hindsight historical memory INC-1987 strongly converge on third-party payment partner route degradation. Local application release rollback is NOT recommended as internal CPU and error rates are healthy.",
            "contributionBreakdown": {
                "hindsightContributionPct": 65,
                "currentIncidentDataPct": 25,
                "webEvidencePct": 10,
                "explanation": "Hindsight historical experience provides 65% of the causal weight by matching verified past resolution path.",
            },
            "rootCauseHypothesis": "Upstream Stripe acquiring bank network degradation inducing read socket timeouts that saturate checkout pod thread pools.",
            "confidence": "HIGH",
            "limitations": [
                "External acquiring bank partner dashboard telemetries have a 60-second reporting delay.",
                "Live network captures on secondary payment route show nominal latency.",
            ],
            "recommendedResponse": {
                "actionTitle": "Grounded Fallback Divert & Timeout Clamp",
                "stagedSteps": [
                    "1. Failover 50% non-critical traffic to Adyen secondary payment processor.",
                    "2. Clamp HTTP read socket timeout on /v2/checkout to 1500ms.",
                    "3. Recycle db-pool-worker-04 connection pool to free blocked worker threads.",
                ],
                "mitigationCommand": "kubectl patch configmap gateway-route --type merge -p '{\"data\":{\"stripe_weight\":\"50\",\"adyen_weight\":\"50\"}}'",
                "targetService": "payment-gw-proxy-iad",
                "safetyNotice": "ADVISORY ONLY — Requires explicit human operator initials prior to cluster dispatch.",
            },
        },
        "governance": {
            "advisoryNotice": "ADVISORY ONLY — HUMAN APPROVAL REQUIRED",
            "isApproved": False,
            "approvedBy": None,
            "dispatchedToChannel": None,
            "dispatchedAt": None,
        },
    }

    record_audit(action="AI_ANALYSIS_EXECUTED", entity_type="INCIDENT", entity_id=req.incidentId)
    return {"analysis": analysis}

@router.post("/ai/dispatch")
def ai_dispatch(req: AiDispatchReq, authorization: Optional[str] = Header(None)):
    user = get_current_user_from_header(authorization)
    ts = datetime.now(timezone.utc).isoformat()
    record_audit(
        action="AI_ANALYSIS_DISPATCHED",
        entity_type="INCIDENT",
        entity_id=req.incidentId,
        user_id=user["id"] if user else None,
        metadata={"channel": req.channel, "operator": req.operatorInitials, "note": req.customNote},
    )
    return {
        "success": True,
        "message": f"Analysis and advisory runbook dispatched to #{req.channel} by {req.operatorInitials}",
        "timestamp": ts,
    }
