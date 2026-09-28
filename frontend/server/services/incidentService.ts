import { dbManager, IncidentRecordDB, IncidentEventDB, IncidentSignalDB, ResponsePlanDB, PostMortemDB, HypothesisDB } from '../db';
import { hindsightService } from './hindsightService';
import { auditService } from './auditService';
import crypto from 'crypto';

export class IncidentService {
  constructor() {
    this.seedDefaultIncidents();
  }

  private seedDefaultIncidents() {
    const state = dbManager.getState();
    if (state.incidents.length === 0) {
      const now = new Date();
      const detectedAt = new Date(now.getTime() - 18 * 60 * 1000 - 42 * 1000).toISOString();

      const inc2048: IncidentRecordDB = {
        id: 'inc-2048',
        incident_number: 'INC-2048',
        title: 'Payment Gateway Timeout Cascade & Thread Exhaustion',
        description: 'Intermittent 504 Gateway Timeouts on /v2/checkout/charge. Blast radius verified isolated to North America region downstream ingress.',
        severity: 'SEV-1',
        status: 'INVESTIGATING',
        service: 'Checkout API / Payment Gateway',
        environment: 'production-iad01',
        detected_at: detectedAt,
        resolved_at: null,
        created_by: 'system-otel-monitor',
        assigned_to: 'D. Mercer (Lead SRE)',
        current_hypothesis: 'Current evidence + prior experience suggest upstream payment partner throttling rather than internal deployment regression.',
        impact_summary: 'Degraded checkout purchases for ~14% of North America traffic',
        is_demo: true,
        created_at: detectedAt,
        updated_at: new Date().toISOString(),
      };

      const inc2045: IncidentRecordDB = {
        id: 'inc-2045',
        incident_number: 'INC-2045',
        title: 'Cart Sync Flapping under High Traffic Surge',
        description: 'Redis cluster cache key eviction induced CPU spike on order sync workers.',
        severity: 'SEV-2',
        status: 'RESOLVED',
        service: 'Cart Sync Worker',
        environment: 'production-fra01',
        detected_at: new Date(now.getTime() - 4 * 3600 * 1000).toISOString(),
        resolved_at: new Date(now.getTime() - 3 * 3600 * 1000).toISOString(),
        created_by: 'system-otel-monitor',
        assigned_to: 'Alex Vance',
        current_hypothesis: 'Redis protocol bump leaked persistent connection handles.',
        impact_summary: 'Cart latency elevated for 18 minutes',
        is_demo: true,
        created_at: new Date(now.getTime() - 4 * 3600 * 1000).toISOString(),
        updated_at: new Date(now.getTime() - 3 * 3600 * 1000).toISOString(),
      };

      state.incidents = [inc2048, inc2045];

      // Seed signals for INC-2048
      const signals: IncidentSignalDB[] = [
        {
          id: 'sig-1',
          incident_id: 'inc-2048',
          signal_type: 'latency',
          name: 'P99 Latency (Checkout API)',
          value: 4820,
          unit: 'ms',
          severity: 'CRITICAL',
          observed_at: new Date().toISOString(),
        },
        {
          id: 'sig-2',
          incident_id: 'inc-2048',
          signal_type: 'error_rate',
          name: '504 Gateway Timeout Rate',
          value: 14.2,
          unit: '%',
          severity: 'HIGH',
          observed_at: new Date().toISOString(),
        },
        {
          id: 'sig-3',
          incident_id: 'inc-2048',
          signal_type: 'pool_saturation',
          name: 'Socket Pool Connection Saturation',
          value: 480,
          unit: 'connections',
          severity: 'CRITICAL',
          observed_at: new Date().toISOString(),
        },
        {
          id: 'sig-4',
          incident_id: 'inc-2048',
          signal_type: 'gateway_timeout',
          name: 'Upstream Stripe Proxy Read Timeout',
          value: 1420,
          unit: 'req/min',
          severity: 'HIGH',
          observed_at: new Date().toISOString(),
        },
      ];
      state.incident_signals = signals;

      // Seed events
      const events: IncidentEventDB[] = [
        {
          id: 'evt-1',
          incident_id: 'inc-2048',
          event_type: 'INCIDENT_CREATED',
          message: 'Incident detected via OpenTelemetry automated threshold trigger on /v2/checkout/charge',
          source: 'TELEMETRY',
          metadata: { initial_latency_ms: 4820, error_code: 504 },
          created_at: detectedAt,
          created_by: 'system-otel-monitor',
        },
        {
          id: 'evt-2',
          incident_id: 'inc-2048',
          event_type: 'CONTEXT_COLLECTED',
          message: '12 error signatures, 4 service graphs, 2 deployment manifests aggregated from OpenTelemetry pipeline',
          source: 'AGENT',
          metadata: { recent_deploy: 'stripe-connector v2.14.0' },
          created_at: new Date(now.getTime() - 17 * 60 * 1000).toISOString(),
          created_by: 'Aegis-Agent-v4',
        },
        {
          id: 'evt-3',
          incident_id: 'inc-2048',
          event_type: 'MEMORY_RECALLED',
          message: 'Hindsight query executed across 14,892 historical incident embeddings. Precedent INC-1987 identified.',
          source: 'HINDSIGHT',
          metadata: { precedent_id: 'INC-1987', similarity: 0.914 },
          created_at: new Date(now.getTime() - 16 * 60 * 1000).toISOString(),
          created_by: 'HyperGraph-v4.9',
        },
        {
          id: 'evt-4',
          incident_id: 'inc-2048',
          event_type: 'HYPOTHESIS_GENERATED',
          message: 'Hypothesis formed: Upstream partner throttling rather than internal release regression.',
          source: 'AGENT',
          metadata: { confidence: 'MODERATE' },
          created_at: new Date(now.getTime() - 15 * 60 * 1000).toISOString(),
          created_by: 'Aegis-Agent-v4',
        },
        {
          id: 'evt-5',
          incident_id: 'inc-2048',
          event_type: 'RESPONSE_RECOMMENDED',
          message: 'Staged 3-action response plan grounded in INC-1987 runbook precedent.',
          source: 'AGENT',
          metadata: { actions_count: 3 },
          created_at: new Date(now.getTime() - 14 * 60 * 1000).toISOString(),
          created_by: 'Aegis-Agent-v4',
        },
      ];
      state.incident_events = events;

      // Seed Response Plan
      const initialPlan: ResponsePlanDB = {
        id: 'plan-2048',
        incident_id: 'inc-2048',
        title: 'Grounded Incident Triage Plan (INC-1987 Grounded)',
        description: 'Failover non-critical payment traffic, clamp socket timeout, and cycle saturated worker connection pool.',
        reason: 'Prevents thread pool exhaustion while keeping payment transaction flow alive.',
        evidence: 'INC-1987 recovered within 11 minutes with 0 transaction loss via 50/50 fallback split.',
        status: 'PENDING_APPROVAL',
        created_by: 'Aegis-Agent-v4',
        approved_by: null,
        approved_at: null,
        created_at: new Date(now.getTime() - 14 * 60 * 1000).toISOString(),
        actions: [
          {
            id: 'act-1',
            stepNumber: 1,
            title: 'Failover 50% non-critical traffic to secondary gateway',
            description: 'Reroutes non-instant checkout transactions to Adyen backup processor to relieve Stripe proxy thread pressure.',
            riskLevel: 'SAFE',
            status: 'READY',
            targetComponent: 'payment-gw-proxy-iad',
            commandSnippet: 'kubectl patch configmap gateway-route --type merge -p \'{"data":{"stripe_weight":"50","adyen_weight":"50"}}\'',
          },
          {
            id: 'act-2',
            stepNumber: 2,
            title: 'Enforce 1500ms timeout clamp',
            description: 'Reduces client HTTP read socket timeout from 5000ms to 1500ms to rapidly fail backlogged requests and preserve worker thread pool.',
            riskLevel: 'MITIGATE',
            status: 'READY',
            targetComponent: 'checkout-api',
            commandSnippet: 'istioctl route-rule apply --service checkout-api --timeout 1500ms',
          },
          {
            id: 'act-3',
            stepNumber: 3,
            title: 'Isolate db-pool-worker-04 connection pool',
            description: 'Terminates stuck JDBC connections and recycles container connection pool worker 04 to prevent cascading thread pool starvation.',
            riskLevel: 'CRITICAL',
            status: 'READY',
            targetComponent: 'db-pool-worker-04',
            commandSnippet: 'kubectl exec -it checkout-api-pod-84f9 -- recycle-pool --worker=db-pool-worker-04 --force',
          },
        ],
      };
      state.response_plans = [initialPlan];

      // Seed Post-Mortem draft for INC-2048
      const initialPostMortem: PostMortemDB = {
        id: 'pm-2048',
        incident_id: 'inc-2048',
        summary: 'Checkout API experienced 504 timeouts due to upstream Stripe gateway route degradation.',
        impact: '14.2% error rate on /v2/checkout/charge in North America region for ~18m.',
        timeline: '13:45 Canary Deploy -> 14:02 First 504 alert -> 14:03 Context & Memory Recall -> 14:06 Plan Staged.',
        root_cause: 'Third-party acquiring bank route degradation causing read socket timeouts exceeding 5000ms.',
        investigation: 'AI Agent correlated absence of internal CPU spikes with external status page latency telemetry.',
        response_summary: 'Traffic shaper failover 50% non-critical traffic to Adyen backup processor.',
        outcome: 'Checkout transactions restored; zero transaction drop recorded during failover.',
        lessons_learned: 'Upstream health checks must precede container restarts to avoid thread stampedes.',
        retained_experience: 'When socket timeouts spike on payment proxy without internal CPU spikes, inspect upstream third-party status before rolling back application releases.',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      state.post_mortems = [initialPostMortem];

      dbManager.saveFileStore();
      console.log('[Incident] Seeded default incidents (INC-2048 Sev-1 active, INC-2045 resolved)');
    }
  }

  public getAllIncidents(): IncidentRecordDB[] {
    return dbManager.getState().incidents;
  }

  public getIncidentById(id: string): IncidentRecordDB | null {
    const state = dbManager.getState();
    return state.incidents.find((i) => i.id === id || i.incident_number.toLowerCase() === id.toLowerCase()) || null;
  }

  public async createIncident(data: {
    title: string;
    description: string;
    severity: IncidentRecordDB['severity'];
    service: string;
    environment?: string;
    affectedServices?: string[];
    observedSymptoms?: string[];
    recentDeployments?: string[];
    isDemo?: boolean;
    createdBy?: string;
  }): Promise<IncidentRecordDB> {
    const state = dbManager.getState();
    const incidentNum = `INC-${Math.floor(1000 + Math.random() * 9000)}`;
    const now = new Date().toISOString();

    const newInc: IncidentRecordDB = {
      id: `inc-${incidentNum.toLowerCase()}`,
      incident_number: incidentNum,
      title: data.title,
      description: data.description,
      severity: data.severity,
      status: 'INVESTIGATING',
      service: data.service,
      environment: data.environment || 'production-us-east',
      detected_at: now,
      resolved_at: null,
      created_by: data.createdBy || 'operator',
      assigned_to: 'D. Mercer (Lead SRE)',
      current_hypothesis: null,
      impact_summary: `Service ${data.service} experiencing ${data.severity} impact`,
      is_demo: Boolean(data.isDemo),
      created_at: now,
      updated_at: now,
    };

    state.incidents.unshift(newInc);

    // Record creation event
    this.addEvent({
      incidentId: newInc.id,
      eventType: 'INCIDENT_CREATED',
      message: `Incident ${incidentNum} registered: ${data.title}`,
      source: 'SRE_OPERATOR',
      metadata: { severity: data.severity, service: data.service },
      createdBy: data.createdBy || 'operator',
    });

    auditService.log({
      incidentId: newInc.id,
      action: 'INCIDENT_CREATED',
      entityType: 'INCIDENT',
      entityId: newInc.id,
      metadata: { incident_number: incidentNum, title: data.title },
    });

    dbManager.saveFileStore();
    return newInc;
  }

  public updateIncident(id: string, updates: Partial<IncidentRecordDB>, userId?: string): IncidentRecordDB | null {
    const inc = this.getIncidentById(id);
    if (!inc) return null;

    Object.assign(inc, updates, { updated_at: new Date().toISOString() });

    if (updates.status === 'RESOLVED' && !inc.resolved_at) {
      inc.resolved_at = new Date().toISOString();
      this.addEvent({
        incidentId: inc.id,
        eventType: 'INCIDENT_RESOLVED',
        message: `Incident marked RESOLVED by operator.`,
        source: 'SRE_OPERATOR',
        metadata: { resolved_at: inc.resolved_at },
        createdBy: userId || 'operator',
      });
    }

    auditService.log({
      incidentId: inc.id,
      userId,
      action: 'INCIDENT_UPDATED',
      entityType: 'INCIDENT',
      entityId: inc.id,
      metadata: updates,
    });

    dbManager.saveFileStore();
    return inc;
  }

  public getEvents(incidentId: string): IncidentEventDB[] {
    const inc = this.getIncidentById(incidentId);
    const targetId = inc ? inc.id : incidentId;
    return dbManager.getState().incident_events.filter((e) => e.incident_id === targetId);
  }

  public addEvent(params: {
    incidentId: string;
    eventType: string;
    message: string;
    source: string;
    metadata?: Record<string, any>;
    createdBy?: string;
  }): IncidentEventDB {
    const state = dbManager.getState();
    const event: IncidentEventDB = {
      id: `evt-${crypto.randomUUID()}`,
      incident_id: params.incidentId,
      event_type: params.eventType,
      message: params.message,
      source: params.source,
      metadata: params.metadata || {},
      created_at: new Date().toISOString(),
      created_by: params.createdBy || 'system',
    };
    state.incident_events.push(event);
    dbManager.saveFileStore();
    return event;
  }

  public getSignals(incidentId: string): IncidentSignalDB[] {
    const inc = this.getIncidentById(incidentId);
    const targetId = inc ? inc.id : incidentId;
    return dbManager.getState().incident_signals.filter((s) => s.incident_id === targetId);
  }

  public getResponsePlans(incidentId: string): ResponsePlanDB[] {
    const inc = this.getIncidentById(incidentId);
    const targetId = inc ? inc.id : incidentId;
    return dbManager.getState().response_plans.filter((p) => p.incident_id === targetId);
  }

  public createResponsePlan(incidentId: string, planData: Partial<ResponsePlanDB>, userId?: string): ResponsePlanDB {
    const state = dbManager.getState();
    const inc = this.getIncidentById(incidentId);
    const targetId = inc ? inc.id : incidentId;

    const newPlan: ResponsePlanDB = {
      id: `plan-${crypto.randomUUID().slice(0, 8)}`,
      incident_id: targetId,
      title: planData.title || 'Response Plan',
      description: planData.description || '',
      reason: planData.reason || '',
      evidence: planData.evidence || '',
      status: 'PENDING_APPROVAL',
      created_by: userId || 'Aegis-Agent-v4',
      approved_by: null,
      approved_at: null,
      created_at: new Date().toISOString(),
      actions: planData.actions || [],
    };

    state.response_plans.unshift(newPlan);
    this.addEvent({
      incidentId: targetId,
      eventType: 'RESPONSE_RECOMMENDED',
      message: `Response Plan formulated: ${newPlan.title}`,
      source: 'AGENT',
      metadata: { plan_id: newPlan.id },
      createdBy: userId || 'agent',
    });

    auditService.log({
      incidentId: targetId,
      userId,
      action: 'RESPONSE_PLAN_CREATED',
      entityType: 'RESPONSE_PLAN',
      entityId: newPlan.id,
      metadata: { title: newPlan.title },
    });

    dbManager.saveFileStore();
    return newPlan;
  }

  public approveResponsePlan(planId: string, userId: string, operatorInitials: string = 'OP'): ResponsePlanDB {
    const state = dbManager.getState();
    const plan = state.response_plans.find((p) => p.id === planId);
    if (!plan) throw new Error('Response plan not found');

    plan.status = 'APPROVED';
    plan.approved_by = userId;
    plan.approved_at = new Date().toISOString();

    // Mark actions as executed/applied in cluster
    plan.actions.forEach((a) => {
      a.status = 'APPLIED';
    });

    this.addEvent({
      incidentId: plan.incident_id,
      eventType: 'HUMAN_APPROVAL',
      message: `Operator (${operatorInitials}) verified and authorized staged plan. Actions applied to cluster.`,
      source: 'SRE_OPERATOR',
      metadata: { plan_id: plan.id, approved_at: plan.approved_at },
      createdBy: userId,
    });

    auditService.log({
      incidentId: plan.incident_id,
      userId,
      action: 'RESPONSE_PLAN_APPROVED',
      entityType: 'RESPONSE_PLAN',
      entityId: plan.id,
      metadata: { operator_initials: operatorInitials },
    });

    dbManager.saveFileStore();
    return plan;
  }

  public rejectResponsePlan(planId: string, reason: string, userId: string): ResponsePlanDB {
    const state = dbManager.getState();
    const plan = state.response_plans.find((p) => p.id === planId);
    if (!plan) throw new Error('Response plan not found');

    plan.status = 'REJECTED';
    this.addEvent({
      incidentId: plan.incident_id,
      eventType: 'ACTION_RECORDED',
      message: `Operator rejected plan: ${reason}`,
      source: 'SRE_OPERATOR',
      metadata: { plan_id: plan.id, reason },
      createdBy: userId,
    });

    auditService.log({
      incidentId: plan.incident_id,
      userId,
      action: 'RESPONSE_PLAN_REJECTED',
      entityType: 'RESPONSE_PLAN',
      entityId: plan.id,
      metadata: { reason },
    });

    dbManager.saveFileStore();
    return plan;
  }

  public getPostMortem(incidentId: string): PostMortemDB | null {
    const inc = this.getIncidentById(incidentId);
    const targetId = inc ? inc.id : incidentId;
    return dbManager.getState().post_mortems.find((pm) => pm.incident_id === targetId) || null;
  }

  public savePostMortem(incidentId: string, data: Partial<PostMortemDB>, userId?: string): PostMortemDB {
    const state = dbManager.getState();
    const inc = this.getIncidentById(incidentId);
    const targetId = inc ? inc.id : incidentId;

    let pm = state.post_mortems.find((p) => p.incident_id === targetId);
    const now = new Date().toISOString();

    if (pm) {
      Object.assign(pm, data, { updated_at: now });
    } else {
      pm = {
        id: `pm-${crypto.randomUUID().slice(0, 8)}`,
        incident_id: targetId,
        summary: data.summary || '',
        impact: data.impact || '',
        timeline: data.timeline || '',
        root_cause: data.root_cause || '',
        investigation: data.investigation || '',
        response_summary: data.response_summary || '',
        outcome: data.outcome || '',
        lessons_learned: data.lessons_learned || '',
        retained_experience: data.retained_experience || '',
        created_at: now,
        updated_at: now,
      };
      state.post_mortems.push(pm);
    }

    this.addEvent({
      incidentId: targetId,
      eventType: 'POST_MORTEM_CREATED',
      message: `Post-Mortem document finalized and signed off by SRE.`,
      source: 'SRE_OPERATOR',
      metadata: { post_mortem_id: pm.id },
      createdBy: userId || 'operator',
    });

    auditService.log({
      incidentId: targetId,
      userId,
      action: 'POST_MORTEM_SAVED',
      entityType: 'POST_MORTEM',
      entityId: pm.id,
      metadata: { root_cause: pm.root_cause },
    });

    dbManager.saveFileStore();
    return pm;
  }
}

export const incidentService = new IncidentService();
