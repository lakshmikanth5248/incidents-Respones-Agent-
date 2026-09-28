export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type IncidentStatus = 'ACTIVE' | 'MITIGATING' | 'RESOLVED' | 'POST_MORTEM';

export interface ServiceNode {
  id: string;
  name: string;
  type: string;
  status: 'NOMINAL' | 'DEGRADED' | 'ELEVATED' | 'CRITICAL' | 'ROUTING' | 'STABLE';
  latency: number; // in ms
  errorRate: number; // percentage
  pos3D: [number, number, number];
  description: string;
  cluster: string;
  instances: number;
}

export interface MemoryPrecedent {
  id: string;
  domain: 'Payment & Billing' | 'Authentication & IAM' | 'Database & Storage' | 'Network & Mesh' | 'Deployment & Rollouts';
  title: string;
  date: string;
  rootCause: string;
  retainedExperience: string;
  recallsCount: number;
  utilityScore: number; // e.g. 96
  similarityScore: number; // e.g. 91.4
  mttrMinutes: number;
  whatHappened: string;
  agentInvestigation: string;
  executedResponse: string;
  verifiedOutcome: string;
  coords: { x: number; y: number };
  coords3D?: [number, number, number];
}

export interface IncidentRecord {
  id: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  elapsedSeconds: number;
  servicesDownCount: number;
  totalServicesCount: number;
  description: string;
  endpoint: string;
  region: string;
  cluster: string;
  rootBottleneck: string;
  symptoms: {
    name: string;
    rate: string;
    percent: number;
    color: string;
  }[];
  recentDeployments: {
    service: string;
    time: string;
    tag: string;
    commit: string;
    details: string;
  }[];
  telemetry: {
    p99Latency: number;
    baselineLatency: number;
    errorRate: number;
    baselineErrorRate: number;
    socketPoolUsed: number;
    socketPoolTotal: number;
  };
}

export interface CognitiveStage {
  number: string;
  name: string;
  timestamp: string;
  status: 'COMPLETED' | 'ACTIVE' | 'PENDING';
  summary: string;
  detail?: string;
  confidence?: 'HIGH' | 'MODERATE' | 'LOW';
  similarity?: string;
  matchedIncidentId?: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'WARN' | 'ERROR' | 'INFO' | 'AGENT' | 'DEBUG';
  source: string;
  message: string;
  highlight?: boolean;
}

export interface RunbookAction {
  id: string;
  stepNumber: number;
  title: string;
  description: string;
  riskLevel: 'SAFE' | 'MITIGATE' | 'CRITICAL';
  status: 'READY' | 'STAGED' | 'EXECUTING' | 'APPLIED' | 'FAILED';
  targetComponent: string;
  commandSnippet?: string;
}
