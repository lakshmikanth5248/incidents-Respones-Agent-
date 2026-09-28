import { dbManager, AuditLogDB } from '../db';
import crypto from 'crypto';

export class AuditService {
  public log(params: {
    userId?: string | null;
    incidentId?: string | null;
    action: string;
    entityType: string;
    entityId?: string | null;
    metadata?: Record<string, any>;
    ipAddress?: string;
  }): AuditLogDB {
    const state = dbManager.getState();
    const entry: AuditLogDB = {
      id: `audit-${crypto.randomUUID()}`,
      user_id: params.userId || null,
      incident_id: params.incidentId || null,
      action: params.action,
      entity_type: params.entityType,
      entity_id: params.entityId || null,
      metadata: params.metadata || {},
      ip_address: params.ipAddress || '127.0.0.1',
      created_at: new Date().toISOString(),
    };

    state.audit_logs.unshift(entry);
    dbManager.saveFileStore();
    return entry;
  }

  public getLogs(filter?: { incidentId?: string; entityType?: string; limit?: number }): AuditLogDB[] {
    const state = dbManager.getState();
    let logs = state.audit_logs;

    if (filter?.incidentId) {
      logs = logs.filter((l) => l.incident_id === filter.incidentId);
    }
    if (filter?.entityType) {
      logs = logs.filter((l) => l.entity_type === filter.entityType);
    }
    if (filter?.limit) {
      logs = logs.slice(0, filter.limit);
    }
    return logs;
  }
}

export const auditService = new AuditService();
