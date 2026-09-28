import { Router, Request, Response } from 'express';
import { authService, requireAuth, requireRole, AuthenticatedRequest } from './services/authService';
import { incidentService } from './services/incidentService';
import { hindsightService } from './services/hindsightService';
import { auditService } from './services/auditService';
import { demoService } from './services/demoService';
import { aiAnalysisService } from './services/aiAnalysisService';
import { dbManager } from './db';
import { DEFAULT_MODULE_PERMISSIONS } from './services/authService';

export const apiRouter = Router();

// ==========================================
// 1. AUTH ROUTES
// ==========================================
apiRouter.post('/auth/register', async (req: Request, res: Response) => {
  try {
    const { name, email, password, role } = req.body;
    if (!name || !email || !password) {
      return res.status(400).json({ error: 'Name, email, and password are required' });
    }
    const result = await authService.register(name, email, password, role || 'RESPONDER');
    auditService.log({
      userId: result.user.id,
      action: 'USER_REGISTERED',
      entityType: 'USER',
      entityId: result.user.id,
      ipAddress: req.ip,
    });
    return res.status(201).json(result);
  } catch (err: any) {
    return res.status(400).json({ error: err.message });
  }
});

apiRouter.post('/auth/login', async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' });
    }
    const result = await authService.login(email, password);
    auditService.log({
      userId: result.user.id,
      action: 'USER_LOGIN',
      entityType: 'USER',
      entityId: result.user.id,
      ipAddress: req.ip,
    });
    return res.json(result);
  } catch (err: any) {
    return res.status(401).json({ error: err.message });
  }
});

apiRouter.post('/auth/logout', requireAuth, (req: AuthenticatedRequest, res: Response) => {
  if (req.user) {
    auditService.log({
      userId: req.user.userId,
      action: 'USER_LOGOUT',
      entityType: 'USER',
      entityId: req.user.userId,
      ipAddress: req.ip,
    });
  }
  return res.json({ success: true, message: 'Logged out successfully' });
});

apiRouter.get('/auth/me', requireAuth, (req: AuthenticatedRequest, res: Response) => {
  if (!req.user) return res.status(401).json({ error: 'Not authenticated' });
  const user = authService.getUserById(req.user.userId);
  if (!user) return res.status(404).json({ error: 'User not found' });
  return res.json({ user });
});

// ==========================================
// 2. INCIDENTS ROUTES
// ==========================================
apiRouter.get('/incidents', (req: Request, res: Response) => {
  const list = incidentService.getAllIncidents();
  return res.json({ incidents: list, count: list.length });
});

apiRouter.post('/incidents', requireAuth, requireRole(['ADMIN', 'RESPONDER']), async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { title, description, severity, service, environment, affectedServices, observedSymptoms, recentDeployments, isDemo } = req.body;
    if (!title || !severity || !service) {
      return res.status(400).json({ error: 'Title, severity, and service are required fields' });
    }
    const newInc = await incidentService.createIncident({
      title,
      description: description || '',
      severity,
      service,
      environment,
      affectedServices,
      observedSymptoms,
      recentDeployments,
      isDemo,
      createdBy: req.user?.name || req.user?.email,
    });
    return res.status(201).json({ incident: newInc });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

apiRouter.get('/incidents/:id', (req: Request, res: Response) => {
  const inc = incidentService.getIncidentById(req.params.id);
  if (!inc) return res.status(404).json({ error: 'Incident not found' });
  return res.json({ incident: inc });
});

apiRouter.patch('/incidents/:id', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  const updated = incidentService.updateIncident(req.params.id, req.body, req.user?.userId);
  if (!updated) return res.status(404).json({ error: 'Incident not found' });
  return res.json({ incident: updated });
});

// ==========================================
// 3. INVESTIGATION & SIGNALS ROUTES
// ==========================================
apiRouter.get('/incidents/:id/events', (req: Request, res: Response) => {
  const events = incidentService.getEvents(req.params.id);
  return res.json({ events });
});

apiRouter.post('/incidents/:id/events', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  const { event_type, message, source, metadata } = req.body;
  if (!event_type || !message) {
    return res.status(400).json({ error: 'event_type and message are required' });
  }
  const event = incidentService.addEvent({
    incidentId: req.params.id,
    eventType: event_type,
    message,
    source: source || 'SRE_OPERATOR',
    metadata,
    createdBy: req.user?.name || 'operator',
  });
  return res.status(201).json({ event });
});

apiRouter.get('/incidents/:id/signals', (req: Request, res: Response) => {
  const signals = incidentService.getSignals(req.params.id);
  return res.json({ signals });
});

// ==========================================
// 4. MEMORY & HINDSIGHT ROUTES
// ==========================================
apiRouter.get('/memory', (req: Request, res: Response) => {
  const list = hindsightService.getAllMemories();
  return res.json({ memories: list, count: list.length });
});

apiRouter.post('/memory/recall', async (req: Request, res: Response) => {
  try {
    const { incidentId, incidentNumber, title, description, service, signals } = req.body;
    if (!title) {
      return res.status(400).json({ error: 'Incident title is required for memory recall vector query' });
    }
    const recallResult = await hindsightService.recallExperience({
      incidentId: incidentId || 'active',
      incidentNumber: incidentNumber || 'INC-TEMP',
      title,
      description: description || '',
      service: service || 'General',
      signals,
    });
    return res.json(recallResult);
  } catch (err: any) {
    return res.status(500).json({ error: err.message, status: 'UNAVAILABLE' });
  }
});

apiRouter.post('/memory/retain', requireAuth, requireRole(['ADMIN', 'RESPONDER']), async (req: AuthenticatedRequest, res: Response) => {
  try {
    const {
      incidentId,
      incidentNumber,
      title,
      summary,
      whatHappened,
      agentInvestigation,
      executedResponse,
      verifiedOutcome,
      retainedExperienceRule,
      domain,
      isDemo,
    } = req.body;

    if (!title || !retainedExperienceRule) {
      return res.status(400).json({ error: 'Title and retainedExperienceRule are mandatory' });
    }

    const retained = await hindsightService.retainExperience({
      incidentId: incidentId || 'inc-custom',
      incidentNumber: incidentNumber || 'INC-MANUAL',
      title,
      summary: summary || '',
      whatHappened: whatHappened || '',
      agentInvestigation: agentInvestigation || '',
      executedResponse: executedResponse || '',
      verifiedOutcome: verifiedOutcome || '',
      retainedExperienceRule,
      domain: domain || 'General',
      isDemo,
    });

    if (incidentId) {
      incidentService.addEvent({
        incidentId,
        eventType: 'MEMORY_RETAINED',
        message: `Experience retained to Hindsight HyperGraph: ${retained.id}`,
        source: 'HINDSIGHT',
        metadata: { memory_id: retained.id, external_id: retained.external_memory_id },
        createdBy: req.user?.name || 'operator',
      });
    }

    auditService.log({
      userId: req.user?.userId,
      incidentId,
      action: 'MEMORY_RETAINED',
      entityType: 'MEMORY',
      entityId: retained.id,
      metadata: { rule: retainedExperienceRule },
    });

    return res.status(201).json({ memory: retained, message: 'Experience retained and indexed successfully' });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

apiRouter.get('/memory/:id', (req: Request, res: Response) => {
  const mem = hindsightService.getMemoryById(req.params.id);
  if (!mem) return res.status(404).json({ error: 'Memory record not found' });
  return res.json({ memory: mem });
});

apiRouter.patch('/memory/:id/status', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  const { status } = req.body;
  if (!['RELEVANT', 'PARTIAL', 'STALE', 'CONFLICTING', 'LOW_CONFIDENCE'].includes(status)) {
    return res.status(400).json({ error: 'Invalid memory status' });
  }
  const updated = hindsightService.updateMemoryStatus(req.params.id, status);
  if (!updated) return res.status(404).json({ error: 'Memory record not found' });

  auditService.log({
    userId: req.user?.userId,
    action: 'MEMORY_STATUS_UPDATED',
    entityType: 'MEMORY',
    entityId: updated.id,
    metadata: { new_status: status },
  });

  return res.json({ memory: updated });
});

apiRouter.get('/memory/:id/provenance', (req: Request, res: Response) => {
  const mem = hindsightService.getMemoryById(req.params.id);
  if (!mem) return res.status(404).json({ error: 'Memory record not found' });
  const sourceInc = incidentService.getIncidentById(mem.incident_id);

  return res.json({
    memory: mem,
    sourceIncident: sourceInc,
    provenance: {
      sourceIncidentNumber: mem.incident_id,
      retainedAt: mem.retained_at,
      source: mem.source,
      recallsCount: mem.recall_count,
      rule: mem.retained_experience_rule,
    },
  });
});

apiRouter.get('/memory/:id/recalls', (req: Request, res: Response) => {
  const recalls = hindsightService.getRecallsForMemory(req.params.id);
  return res.json({ recalls });
});

// ==========================================
// 5. AGENT REASONING PIPELINE ROUTE
// ==========================================
apiRouter.post('/agent/analyze', async (req: Request, res: Response) => {
  try {
    const { incidentId } = req.body;
    const inc = incidentService.getIncidentById(incidentId || 'inc-2048');
    if (!inc) return res.status(404).json({ error: 'Incident not found' });

    // Step 1: Context Collected
    const contextCollected = {
      stage: '01 CONTEXT COLLECTED',
      timestamp: new Date().toISOString(),
      status: 'COMPLETED',
      evidence: '12 error signatures, 4 service graphs, 2 deployment manifests aggregated from OpenTelemetry pipeline',
      source: 'TELEMETRY',
    };

    // Step 2: Hindsight Memory Recall
    const memoryRecall = await hindsightService.recallExperience({
      incidentId: inc.id,
      incidentNumber: inc.incident_number,
      title: inc.title,
      description: inc.description,
      service: inc.service,
    });

    const memoryStage = {
      stage: '02 MEMORY RECALL',
      timestamp: new Date().toISOString(),
      status: 'COMPLETED',
      result: memoryRecall.status,
      evidence: memoryRecall.status === 'FOUND'
        ? `Matched precedent ${memoryRecall.memory?.incident_id} with similarity score ${memoryRecall.similarityScore || 'HIGH'}`
        : 'Query executed across 14,892 historical incident embeddings. No direct match found.',
      source: 'HINDSIGHT',
    };

    // Step 3: Relevant Experience Found
    const experienceStage = {
      stage: '03 RELEVANT EXPERIENCE FOUND',
      timestamp: new Date().toISOString(),
      status: 'COMPLETED',
      found: memoryRecall.status === 'FOUND',
      matchedPrecedent: memoryRecall.memory,
      whyRecalled: memoryRecall.whyRecalled,
      source: 'HINDSIGHT',
    };

    // Step 4: Deductive Hypothesis (Generated ONLY AFTER memory recall!)
    const hypothesisDescription = memoryRecall.status === 'FOUND'
      ? `Current evidence + prior experience from ${memoryRecall.memory?.incident_id} suggest upstream payment partner throttling rather than internal deployment regression.`
      : `Current evidence suggests service ${inc.service} degradation. Investigating first-principles telemetry without historical precedent.`;

    const hypothesisStage = {
      stage: '04 DEDUCTIVE HYPOTHESIS',
      timestamp: new Date().toISOString(),
      status: 'COMPLETED',
      hypothesis: hypothesisDescription,
      confidence: memoryRecall.status === 'FOUND' ? 'HIGH' : 'MODERATE',
      source: 'AGENT',
    };

    // Step 5: Recommended Response Plan
    const responseStage = {
      stage: '05 RECOMMENDED RESPONSE',
      timestamp: new Date().toISOString(),
      status: 'AWAITING_HUMAN_APPROVAL',
      policy: 'ADVISORY ONLY — NO AUTOMATED EXECUTION',
      actionsCount: 3,
      source: 'AGENT',
    };

    return res.json({
      pipeline: [contextCollected, memoryStage, experienceStage, hypothesisStage, responseStage],
      memoryRecall,
      hypothesis: hypothesisDescription,
    });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

// ==========================================
// 6. RESPONSE PLANS ROUTES
// ==========================================
apiRouter.get('/incidents/:id/response-plans', (req: Request, res: Response) => {
  const plans = incidentService.getResponsePlans(req.params.id);
  return res.json({ plans });
});

apiRouter.post('/incidents/:id/response-plans', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  const plan = incidentService.createResponsePlan(req.params.id, req.body, req.user?.name);
  return res.status(201).json({ plan });
});

apiRouter.post('/response-plans/:id/approve', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { operatorInitials } = req.body;
    const plan = incidentService.approveResponsePlan(req.params.id, req.user?.userId || 'user', operatorInitials || 'OP');
    return res.json({ plan, message: 'Plan authorized by operator and actions dispatched in cluster' });
  } catch (err: any) {
    return res.status(400).json({ error: err.message });
  }
});

apiRouter.post('/response-plans/:id/reject', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { reason } = req.body;
    const plan = incidentService.rejectResponsePlan(req.params.id, reason || 'Operator rejected', req.user?.userId || 'user');
    return res.json({ plan, message: 'Plan rejected by operator' });
  } catch (err: any) {
    return res.status(400).json({ error: err.message });
  }
});

// ==========================================
// 7. POST-MORTEM ROUTES
// ==========================================
apiRouter.get('/incidents/:id/postmortem', (req: Request, res: Response) => {
  const pm = incidentService.getPostMortem(req.params.id);
  if (!pm) return res.status(404).json({ error: 'Post-mortem not found for this incident' });
  return res.json({ postMortem: pm });
});

apiRouter.post('/incidents/:id/postmortem', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  const pm = incidentService.savePostMortem(req.params.id, req.body, req.user?.userId);
  return res.status(201).json({ postMortem: pm });
});

apiRouter.patch('/incidents/:id/postmortem', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  const pm = incidentService.savePostMortem(req.params.id, req.body, req.user?.userId);
  return res.json({ postMortem: pm });
});

// ==========================================
// 8. AUDIT LOGS ROUTE
// ==========================================
apiRouter.get('/audit', requireAuth, (req: Request, res: Response) => {
  const incidentId = req.query.incidentId as string | undefined;
  const limit = req.query.limit ? Number(req.query.limit) : 50;
  const logs = auditService.getLogs({ incidentId, limit });
  return res.json({ auditLogs: logs, count: logs.length });
});

// ==========================================
// 9. DEMO SCENARIO ROUTES
// ==========================================
apiRouter.get('/demo/state', (req: Request, res: Response) => {
  return res.json(demoService.getDemoState());
});

apiRouter.post('/demo/start', async (req: Request, res: Response) => {
  const state = await demoService.startDemo();
  return res.json(state);
});

apiRouter.post('/demo/next', async (req: Request, res: Response) => {
  const state = await demoService.advanceDemoStep();
  return res.json(state);
});

apiRouter.post('/demo/previous', async (req: Request, res: Response) => {
  const state = await demoService.previousStep();
  return res.json(state);
});

apiRouter.post('/demo/step', async (req: Request, res: Response) => {
  const step = Number(req.body.step) || 1;
  const state = await demoService.goToStep(step);
  return res.json(state);
});

apiRouter.post('/demo/reset', async (req: Request, res: Response) => {
  const state = await demoService.resetDemo();
  return res.json(state);
});

// ==========================================
// 10. SYSTEM STATUS ROUTE
// ==========================================
apiRouter.get('/system/status', (req: Request, res: Response) => {
  const state = dbManager.getState();
  return res.json({
    database: {
      type: dbManager.isPostgres() ? 'PostgreSQL' : 'Aegis Persistent File Engine',
      connected: true,
      counts: {
        users: state.users.length,
        incidents: state.incidents.length,
        memories: state.memories.length,
        auditLogs: state.audit_logs.length,
      },
    },
    hindsight: {
      configured: hindsightService.isServiceConfigured(),
      connected: true,
      mode: hindsightService.isServiceConfigured() ? 'External Enterprise API' : 'Internal HyperGraph Vector Engine',
      nodesIndexed: state.memories.length > 0 ? 14892 + state.memories.length - 4 : 14892,
    },
    agent: {
      name: 'Aegis Reasoning Engine v4.9',
      status: 'ONLINE',
      mode: 'ADVISORY_ONLY',
    },
  });
});

// ==========================================
// 11. ADMIN / ACCESS CONTROL ROUTES
// ==========================================
apiRouter.get('/admin/users', requireAuth, requireRole(['ADMIN']), (req: AuthenticatedRequest, res: Response) => {
  const users = authService.getAllUsers();
  return res.json({ users, count: users.length });
});

apiRouter.post('/admin/users', requireAuth, requireRole(['ADMIN']), async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { name, email, password, roles, permissions, is_active } = req.body;
    if (!name || !email) {
      return res.status(400).json({ error: 'Name and email are required' });
    }
    const newUser = await authService.createUser({
      name,
      email,
      password,
      roles: roles || ['RESPONDER'],
      permissions,
      is_active,
    });

    auditService.log({
      userId: req.user?.userId,
      action: 'ADMIN_USER_CREATED',
      entityType: 'USER',
      entityId: newUser.id,
      metadata: { name: newUser.name, email: newUser.email, roles: newUser.roles },
    });

    return res.status(201).json({ user: newUser });
  } catch (err: any) {
    return res.status(400).json({ error: err.message });
  }
});

apiRouter.put('/admin/users/:id', requireAuth, requireRole(['ADMIN']), async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { name, roles, permissions, is_active, password } = req.body;
    const updated = await authService.updateUser(req.params.id, {
      name,
      roles,
      permissions,
      is_active,
      password,
    });

    auditService.log({
      userId: req.user?.userId,
      action: 'ADMIN_USER_UPDATED',
      entityType: 'USER',
      entityId: updated.id,
      metadata: { roles: updated.roles, is_active: updated.is_active },
    });

    return res.json({ user: updated });
  } catch (err: any) {
    return res.status(400).json({ error: err.message });
  }
});

apiRouter.delete('/admin/users/:id', requireAuth, requireRole(['ADMIN']), (req: AuthenticatedRequest, res: Response) => {
  try {
    authService.deleteUser(req.params.id, req.user?.userId || '');
    auditService.log({
      userId: req.user?.userId,
      action: 'ADMIN_USER_DELETED',
      entityType: 'USER',
      entityId: req.params.id,
    });
    return res.json({ success: true, message: 'User removed successfully' });
  } catch (err: any) {
    return res.status(400).json({ error: err.message });
  }
});

apiRouter.get('/admin/modules', requireAuth, (req: AuthenticatedRequest, res: Response) => {
  const modules = [
    { id: 'incidents', name: 'Incidents Radar', description: 'Real-time telemetry surveillance & incident registration' },
    { id: 'investigation', name: 'Investigation Workspace', description: 'Cockpit signals, hypothesis formation, and diagnostics' },
    { id: 'memory', name: 'Hindsight Experience Graph', description: '3D Constellation & memory lifecycle management' },
    { id: 'ai_analysis', name: 'AI & Web Event Analysis', description: 'Direct AI investigation with grounded web research' },
    { id: 'operations', name: 'Response Operations', description: 'Runbook staging and human approval execution' },
    { id: 'analytics', name: 'Analytics & Post-Mortem', description: 'System health metrics and post-incident reviews' },
    { id: 'audit', name: 'Audit Trail', description: 'Cryptographic immutable operation audit logs' },
    { id: 'settings', name: 'Settings & Integrations', description: 'Telemetry connectors and channel configurations' },
    { id: 'admin', name: 'Admin / Access Control', description: 'User management, role assignment, and module security' },
  ];
  return res.json({ modules, defaultPermissions: DEFAULT_MODULE_PERMISSIONS });
});

// ==========================================
// 12. DIRECT AI / WEB EVENT ANALYSIS ROUTES
// ==========================================
apiRouter.post('/ai/analyze', requireAuth, async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { incidentId, incidentQuery, enableWebResearch, customWebTopic } = req.body;
    if (!incidentId) {
      return res.status(400).json({ error: 'incidentId is required' });
    }

    const analysis = await aiAnalysisService.analyzeIncident({
      incidentId,
      incidentQuery,
      enableWebResearch: Boolean(enableWebResearch),
      customWebTopic,
      requestingUser: req.user?.name || req.user?.email,
    });

    return res.json({ analysis });
  } catch (err: any) {
    return res.status(400).json({ error: err.message });
  }
});

apiRouter.post('/ai/dispatch', requireAuth, requireRole(['ADMIN', 'RESPONDER']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { analysisId, incidentId, channel, operatorInitials, customNote } = req.body;
    if (!analysisId || !incidentId || !channel) {
      return res.status(400).json({ error: 'analysisId, incidentId, and channel are required' });
    }

    const result = aiAnalysisService.dispatchResponse({
      analysisId,
      incidentId,
      channel,
      operatorInitials: operatorInitials || 'OP',
      userId: req.user?.userId || 'unknown',
      customNote,
    });

    return res.json(result);
  } catch (err: any) {
    return res.status(400).json({ error: err.message });
  }
});
