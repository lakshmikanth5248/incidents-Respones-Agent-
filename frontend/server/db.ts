import fs from 'fs';
import path from 'path';
import { Pool } from 'pg';

export interface UserRecord {
  id: string;
  name: string;
  email: string;
  password_hash: string;
  role: 'ADMIN' | 'RESPONDER' | 'VIEWER' | 'ANALYST';
  roles?: string[];
  permissions?: Record<string, boolean>;
  avatar_url: string;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  is_active: boolean;
}

export interface IncidentRecordDB {
  id: string;
  incident_number: string;
  title: string;
  description: string;
  severity: 'SEV-1' | 'SEV-2' | 'SEV-3' | 'SEV-4';
  status: 'DETECTED' | 'INVESTIGATING' | 'MONITORING' | 'RESOLVED' | 'ESCALATED' | 'CLOSED';
  service: string;
  environment: string;
  detected_at: string;
  resolved_at: string | null;
  created_by: string;
  assigned_to: string;
  current_hypothesis: string | null;
  impact_summary: string;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface IncidentEventDB {
  id: string;
  incident_id: string;
  event_type: string;
  message: string;
  source: string;
  metadata: Record<string, any>;
  created_at: string;
  created_by: string;
}

export interface IncidentSignalDB {
  id: string;
  incident_id: string;
  signal_type: 'latency' | 'error_rate' | 'connection_reset' | 'pool_saturation' | 'gateway_timeout' | string;
  name: string;
  value: number | string;
  unit: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NOMINAL';
  observed_at: string;
}

export interface MemoryDB {
  id: string;
  external_memory_id: string | null;
  incident_id: string;
  title: string;
  summary: string;
  memory_type: string;
  status: 'RELEVANT' | 'PARTIAL' | 'STALE' | 'CONFLICTING' | 'LOW_CONFIDENCE';
  source: string;
  retained_at: string;
  last_recalled_at: string | null;
  recall_count: number;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  // Deep experience properties
  what_happened?: string;
  agent_investigation?: string;
  executed_response?: string;
  verified_outcome?: string;
  retained_experience_rule?: string;
  utility_score?: number;
  domain?: string;
  coords3D?: [number, number, number];
}

export interface MemoryRecallDB {
  id: string;
  incident_id: string;
  memory_id: string;
  reason: string;
  relevance: 'HIGH' | 'MEDIUM' | 'LOW';
  retrieved_context: string;
  created_at: string;
}

export interface HypothesisDB {
  id: string;
  incident_id: string;
  description: string;
  supporting_evidence: string;
  source: 'AGENT' | 'OPERATOR';
  status: 'PROPOSED' | 'UNDER_REVIEW' | 'ACCEPTED' | 'REJECTED';
  created_at: string;
}

export interface ResponsePlanDB {
  id: string;
  incident_id: string;
  title: string;
  description: string;
  reason: string;
  evidence: string;
  status: 'PROPOSED' | 'PENDING_APPROVAL' | 'APPROVED' | 'MODIFIED' | 'REJECTED' | 'COMPLETED';
  created_by: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  actions: {
    id: string;
    stepNumber: number;
    title: string;
    description: string;
    riskLevel: 'SAFE' | 'MITIGATE' | 'CRITICAL';
    status: 'READY' | 'STAGED' | 'EXECUTING' | 'APPLIED' | 'FAILED';
    targetComponent: string;
    commandSnippet?: string;
  }[];
}

export interface AuditLogDB {
  id: string;
  user_id: string | null;
  incident_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  metadata: Record<string, any>;
  ip_address: string;
  created_at: string;
}

export interface PostMortemDB {
  id: string;
  incident_id: string;
  summary: string;
  impact: string;
  timeline: string;
  root_cause: string;
  investigation: string;
  response_summary: string;
  outcome: string;
  lessons_learned: string;
  retained_experience: string;
  created_at: string;
  updated_at: string;
}

export interface DatabaseState {
  users: UserRecord[];
  incidents: IncidentRecordDB[];
  incident_events: IncidentEventDB[];
  incident_signals: IncidentSignalDB[];
  memories: MemoryDB[];
  memory_recalls: MemoryRecallDB[];
  hypotheses: HypothesisDB[];
  response_plans: ResponsePlanDB[];
  audit_logs: AuditLogDB[];
  post_mortems: PostMortemDB[];
}

const DATA_DIR = path.resolve(process.cwd(), 'data');
const DATA_FILE = path.join(DATA_DIR, 'aegis_data.json');

class DatabaseManager {
  private pgPool: Pool | null = null;
  private memoryState: DatabaseState = {
    users: [],
    incidents: [],
    incident_events: [],
    incident_signals: [],
    memories: [],
    memory_recalls: [],
    hypotheses: [],
    response_plans: [],
    audit_logs: [],
    post_mortems: [],
  };
  private isPgAvailable = false;

  constructor() {
    this.initFileStore();
    this.initPg();
  }

  private initFileStore() {
    if (!fs.existsSync(DATA_DIR)) {
      fs.mkdirSync(DATA_DIR, { recursive: true });
    }
    if (fs.existsSync(DATA_FILE)) {
      try {
        const raw = fs.readFileSync(DATA_FILE, 'utf-8');
        this.memoryState = JSON.parse(raw);
      } catch (err) {
        console.error('Failed reading aegis_data.json, initializing fresh store', err);
      }
    }
  }

  private async initPg() {
    const dbUrl = process.env.DATABASE_URL;
    if (dbUrl && dbUrl.trim() !== '') {
      try {
        this.pgPool = new Pool({ connectionString: dbUrl });
        const client = await this.pgPool.connect();
        await client.query('SELECT NOW()');
        client.release();
        this.isPgAvailable = true;
        console.log('[DB] PostgreSQL successfully connected via DATABASE_URL');
      } catch (err) {
        console.warn('[DB] PostgreSQL connection failed, falling back to persistent file store:', (err as any).message);
        this.isPgAvailable = false;
      }
    } else {
      console.log('[DB] DATABASE_URL not set; using Aegis persistent JSON storage engine.');
    }
  }

  public saveFileStore() {
    try {
      fs.writeFileSync(DATA_FILE, JSON.stringify(this.memoryState, null, 2), 'utf-8');
    } catch (err) {
      console.error('Failed to write aegis_data.json:', err);
    }
  }

  public getState(): DatabaseState {
    return this.memoryState;
  }

  public isPostgres(): boolean {
    return this.isPgAvailable;
  }
}

export const dbManager = new DatabaseManager();
