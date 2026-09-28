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

export type AppModuleKey =
  | 'incidents'
  | 'investigation'
  | 'memory'
  | 'ai_analysis'
  | 'operations'
  | 'analytics'
  | 'audit'
  | 'settings'
  | 'admin';

export interface UserAccount {
  id: string;
  name: string;
  email: string;
  role: 'ADMIN' | 'RESPONDER' | 'VIEWER' | 'ANALYST';
  roles: string[];
  permissions: Record<string, boolean>;
  avatar_url: string;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  is_active: boolean;
}

export interface WebSourceConsulted {
  title: string;
  url: string;
  sourceType: 'OFFICIAL_POST_MORTEM' | 'STATUS_PAGE' | 'ENGINEERING_BLOG' | 'PUBLIC_CVE_ADVISORY';
  organization: string;
  publishedDate: string;
  snippet: string;
}

export interface HistoricalEvent {
  incidentIdOrName: string;
  organization: string;
  date: string;
  summary: string;
  similarityToCurrent: string;
  rootCause: string;
  resolution: string;
  sourceUrl: string;
}

export interface AiAnalysisResult {
  id: string;
  incidentId: string;
  incidentNumber: string;
  analyzedAt: string;
  webResearchRequested: boolean;
  priorityOrder: string[];

  currentIncidentData: {
    incidentNumber: string;
    title: string;
    service: string;
    severity: string;
    description: string;
    detectedAt: string;
    signals: any[];
    keySymptoms: string[];
  };

  hindsightMemory: {
    status: 'FOUND' | 'NO_RELEVANT_HINDSIGHT_EXPERIENCE';
    recalledIncidentId?: string;
    recalledTitle?: string;
    similarityScore?: number;
    retainedExperienceRule?: string;
    provenance?: {
      sourceIncident: string;
      date: string;
      verifiedOutcome: string;
      investigationPath: string;
      executedResponse: string;
    };
    whyRecalled?: string;
  };

  webEvidence: {
    enabled: boolean;
    sourcesConsulted: WebSourceConsulted[];
    keyEvidence: string[];
    relevantHistoricalEvents: HistoricalEvent[];
    possibleCausesAndPatterns: string[];
    searchQueriesUsed: string[];
  };

  synthesizedAnalysis: {
    primaryReasoning: string;
    contributionBreakdown: {
      hindsightContributionPct: number;
      currentIncidentDataPct: number;
      webEvidencePct: number;
      explanation: string;
    };
    rootCauseHypothesis: string;
    confidence: 'HIGH' | 'MEDIUM' | 'LOW';
    limitations: string[];
    recommendedResponse: {
      actionTitle: string;
      stagedSteps: string[];
      mitigationCommand?: string;
      targetService: string;
      safetyNotice: string;
    };
  };

  governance: {
    advisoryNotice: 'ADVISORY ONLY — HUMAN APPROVAL REQUIRED';
    isApproved: boolean;
    approvedBy: string | null;
    dispatchedToChannel: string | null;
    dispatchedAt: string | null;
  };
}
