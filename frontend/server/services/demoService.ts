import { dbManager } from '../db';
import { incidentService } from './incidentService';
import { hindsightService } from './hindsightService';
import { auditService } from './auditService';

export interface DemoStepState {
  currentStep: number;
  stepName: string;
  incidentAId: string | null;
  incidentBId: string | null;
  retainedMemoryId: string | null;
  memoryRecallStatus: 'SEARCHING' | 'FOUND' | 'NO_RELEVANT_EXPERIENCE' | 'IDLE';
  recalledMemory: any | null;
  logs: string[];
}

export class DemoService {
  private demoState: DemoStepState = {
    currentStep: 1,
    stepName: '01 INCIDENT A (COLD START)',
    incidentAId: null,
    incidentBId: null,
    retainedMemoryId: null,
    memoryRecallStatus: 'IDLE',
    recalledMemory: null,
    logs: ['[DEMO INIT] Scenario initialized. Simulated telemetry ready.'],
  };

  public getDemoState(): DemoStepState {
    return this.demoState;
  }

  public async startDemo(): Promise<DemoStepState> {
    await this.resetDemo();
    this.demoState.currentStep = 1;
    this.demoState.stepName = '01 INCIDENT A (COLD START)';

    // Create Incident A: Cold-start incident without prior experience in memory
    const incA = await incidentService.createIncident({
      title: 'Cold-start: Edge Proxy Read Socket Timeouts',
      description: 'First observed occurrence of edge proxy 504 timeouts on /v1/checkout. Unknown root cause; no historical precedent exists in vector store.',
      severity: 'SEV-1',
      service: 'Payment Gateway Proxy',
      environment: 'production-iad01',
      isDemo: true,
      createdBy: 'demo-system',
    });

    this.demoState.incidentAId = incA.id;
    this.demoState.logs.push(`[STEP 01] Incident A created: ${incA.incident_number} (Cold-start).`);
    return this.demoState;
  }

  public async advanceDemoStep(): Promise<DemoStepState> {
    const current = this.demoState.currentStep;

    switch (current) {
      case 1: {
        // Step 2: Investigate Incident A (Memory query executes -> No relevant memory found)
        this.demoState.currentStep = 2;
        this.demoState.stepName = '02 INVESTIGATE (NO MEMORY)';
        this.demoState.memoryRecallStatus = 'NO_RELEVANT_EXPERIENCE';

        if (this.demoState.incidentAId) {
          incidentService.addEvent({
            incidentId: this.demoState.incidentAId,
            eventType: 'MEMORY_RECALLED',
            message: 'Hindsight search executed. NO RELEVANT EXPERIENCE FOUND in 14,892 nodes. Agent operating on first-principles.',
            source: 'HINDSIGHT',
            createdBy: 'HyperGraph',
          });
        }
        this.demoState.logs.push('[STEP 02] Hindsight search: NO RELEVANT EXPERIENCE. First-principles investigation engaged.');
        break;
      }

      case 2: {
        // Step 3: Resolve Incident A
        this.demoState.currentStep = 3;
        this.demoState.stepName = '03 RESOLVE INCIDENT A';
        if (this.demoState.incidentAId) {
          incidentService.updateIncident(this.demoState.incidentAId, {
            status: 'RESOLVED',
            current_hypothesis: 'Identified third-party upstream bank gateway throttling causing worker thread lock contention.',
          });
          incidentService.addEvent({
            incidentId: this.demoState.incidentAId,
            eventType: 'INCIDENT_RESOLVED',
            message: 'Incident A mitigated via 50/50 fallback gateway traffic diversion.',
            source: 'SRE_OPERATOR',
            createdBy: 'D. Mercer',
          });
        }
        this.demoState.logs.push('[STEP 03] Incident A resolved. Fallback traffic split confirmed successful.');
        break;
      }

      case 3: {
        // Step 4: Post-Mortem Generated
        this.demoState.currentStep = 4;
        this.demoState.stepName = '04 POST-MORTEM GENERATED';
        if (this.demoState.incidentAId) {
          incidentService.savePostMortem(this.demoState.incidentAId, {
            summary: 'Cold-start payment gateway degradation resolved by isolating upstream third-party partner throttling.',
            root_cause: 'Acquiring bank endpoint silent degradation without local CPU spike.',
            lessons_learned: 'Inspect third-party status before assuming internal code regression.',
            retained_experience: 'When socket timeouts spike on payment proxy without internal CPU spikes, inspect upstream third-party status before rolling back application releases.',
          });
        }
        this.demoState.logs.push('[STEP 04] Post-Mortem synthesized with verified operational lesson.');
        break;
      }

      case 4: {
        // Step 5: Retain Experience into Hindsight Memory
        this.demoState.currentStep = 5;
        this.demoState.stepName = '05 RETAIN TO HINDSIGHT';
        const incA = this.demoState.incidentAId ? incidentService.getIncidentById(this.demoState.incidentAId) : null;
        const incNum = incA ? incA.incident_number : 'INC-A';

        const retained = await hindsightService.retainExperience({
          incidentId: this.demoState.incidentAId || 'inc-a',
          incidentNumber: incNum,
          title: 'Payment Gateway Proxy Upstream Throttling & Thread Lock',
          summary: 'Upstream payment processor network degradation caused socket hanging across core checkout pods.',
          whatHappened: 'Card processor silent degradation caused 504 timeouts and thread pool exhaustion.',
          agentInvestigation: 'AI correlated socket timeout spike with absence of internal CPU surge.',
          executedResponse: 'Split 50% non-critical traffic to secondary gateway and clamped socket timeouts to 1500ms.',
          verifiedOutcome: 'Full checkout path restored in 11 minutes with zero loss.',
          retainedExperienceRule: 'When socket timeouts spike on payment proxy without internal CPU spikes, inspect upstream third-party status before rolling back application releases.',
          domain: 'Payment & Billing',
          isDemo: true,
        });

        this.demoState.retainedMemoryId = retained.id;
        this.demoState.logs.push(`[STEP 05] Experience Retained: ${retained.id} indexed into Hindsight HyperGraph vector store.`);
        break;
      }

      case 5: {
        // Step 6: Create Incident B (Different wording, related failure characteristics)
        this.demoState.currentStep = 6;
        this.demoState.stepName = '06 INCIDENT B CREATED';

        const incB = await incidentService.createIncident({
          title: 'Card Processing Partner Latency Surge & Pod Pool Saturation',
          description: 'Downstream merchant checkout pods report escalating 504 read timeouts on payment proxy route. DB worker thread capacity reaching 96%.',
          severity: 'SEV-1',
          service: 'Payment Gateway Proxy',
          environment: 'production-iad01',
          isDemo: true,
          createdBy: 'demo-system',
        });

        this.demoState.incidentBId = incB.id;
        this.demoState.logs.push(`[STEP 06] Incident B created: ${incB.incident_number} (Uses alternative phrasing for matching symptoms).`);
        break;
      }

      case 6: {
        // Step 7: Recall Experience for Incident B
        this.demoState.currentStep = 7;
        this.demoState.stepName = '07 HINDSIGHT RECALL';
        this.demoState.memoryRecallStatus = 'FOUND';

        const recallRes = await hindsightService.recallExperience({
          incidentId: this.demoState.incidentBId || 'inc-b',
          incidentNumber: 'INC-B',
          title: 'Card Processing Partner Latency Surge',
          description: '504 read timeouts on payment proxy route',
          service: 'Payment Gateway Proxy',
        });

        this.demoState.recalledMemory = recallRes.memory;
        if (this.demoState.incidentBId) {
          incidentService.addEvent({
            incidentId: this.demoState.incidentBId,
            eventType: 'MEMORY_RECALLED',
            message: `Hindsight Match Found! Precedent ${recallRes.memory?.incident_id} retrieved with 91.4% similarity.`,
            source: 'HINDSIGHT',
            metadata: { memory_id: recallRes.memory?.id },
            createdBy: 'HyperGraph',
          });
        }
        this.demoState.logs.push(`[STEP 07] MEMORY RECALL SUCCESS: Precedent ${recallRes.memory?.incident_id} retrieved and injected into reasoning context.`);
        break;
      }

      case 7: {
        // Step 8: Context-Aware Reasoning (Recalled Context placed BEFORE final hypothesis)
        this.demoState.currentStep = 8;
        this.demoState.stepName = '08 CONTEXT-AWARE REASONING';

        if (this.demoState.incidentBId) {
          incidentService.updateIncident(this.demoState.incidentBId, {
            current_hypothesis: 'Current evidence + prior experience suggest upstream payment partner throttling rather than internal release regression.',
          });
          incidentService.addEvent({
            incidentId: this.demoState.incidentBId,
            eventType: 'HYPOTHESIS_GENERATED',
            message: 'Context + Recalled Experience merged: Formulated Deductive Hypothesis.',
            source: 'AGENT',
            createdBy: 'Aegis-Agent-v4',
          });
        }
        this.demoState.logs.push('[STEP 08] Context Merge: Incident Context + Retained Experience rule generated high-confidence hypothesis.');
        break;
      }

      case 8: {
        // Step 9: Grounded Response Recommendation
        this.demoState.currentStep = 9;
        this.demoState.stepName = '09 RESPONSE RECOMMENDATION';

        if (this.demoState.incidentBId) {
          incidentService.createResponsePlan(this.demoState.incidentBId, {
            title: 'Grounded Incident B Response Plan (Precedent Verified)',
            description: 'Apply proven 50/50 fallback split and enforce 1500ms socket clamp.',
            reason: 'Validated in prior incident to clear thread pool lock in 11 minutes.',
            actions: [
              {
                id: 'act-demo-1',
                stepNumber: 1,
                title: 'Failover 50% non-critical traffic to backup gateway',
                description: 'Relieves thread pressure while retaining full transaction throughput.',
                riskLevel: 'SAFE',
                status: 'READY',
                targetComponent: 'payment-gw-proxy-iad',
                commandSnippet: 'kubectl patch configmap gateway-route --type merge -p \'{"data":{"stripe_weight":"50","adyen_weight":"50"}}\'',
              },
              {
                id: 'act-demo-2',
                stepNumber: 2,
                title: 'Enforce 1500ms timeout clamp',
                description: 'Fast-fails backlogged queries to preserve core checkout workers.',
                riskLevel: 'MITIGATE',
                status: 'READY',
                targetComponent: 'checkout-api',
                commandSnippet: 'istioctl route-rule apply --service checkout-api --timeout 1500ms',
              },
            ],
          });
        }
        this.demoState.logs.push('[STEP 09] Operator advisory plan staged. Ready for human authorization.');
        break;
      }

      default:
        break;
    }

    return this.demoState;
  }

  public async goToStep(targetStep: number): Promise<DemoStepState> {
    if (targetStep < 1 || targetStep > 9) return this.demoState;
    if (this.demoState.currentStep === targetStep && this.demoState.incidentAId) {
      return this.demoState;
    }
    if (!this.demoState.incidentAId || this.demoState.currentStep === 0 || targetStep < this.demoState.currentStep) {
      await this.startDemo();
    }
    while (this.demoState.currentStep < targetStep && this.demoState.currentStep < 9) {
      await this.advanceDemoStep();
    }
    return this.demoState;
  }

  public async previousStep(): Promise<DemoStepState> {
    const target = Math.max(1, this.demoState.currentStep - 1);
    return this.goToStep(target);
  }

  public async resetDemo(): Promise<DemoStepState> {
    const state = dbManager.getState();
    // Safely remove only demo incidents created in demo runs (except baseline seeds if wanted, or reset cleanly)
    state.incidents = state.incidents.filter((i) => !i.title.startsWith('Cold-start:') && !i.title.startsWith('Card Processing Partner'));
    state.memories = state.memories.filter((m) => !m.title.startsWith('Payment Gateway Proxy Upstream Throttling'));

    this.demoState = {
      currentStep: 0,
      stepName: 'IDLE (READY TO START)',
      incidentAId: null,
      incidentBId: null,
      retainedMemoryId: null,
      memoryRecallStatus: 'IDLE',
      recalledMemory: null,
      logs: ['[RESET] Demo state cleanly reset. Real user data untouched.'],
    };

    dbManager.saveFileStore();
    return this.demoState;
  }
}

export const demoService = new DemoService();
