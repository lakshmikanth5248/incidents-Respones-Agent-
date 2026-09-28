export const API_BASE = '/api';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('aegis_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `HTTP error ${response.status}: ${response.statusText}`);
  }

  return data as T;
}

export const api = {
  auth: {
    login: (credentials: { email: string; password: string }) =>
      request<{ user: any; token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      }),
    register: (userData: { name: string; email: string; password: string; role?: string }) =>
      request<{ user: any; token: string }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData),
      }),
    logout: () =>
      request<{ success: boolean }>('/auth/logout', {
        method: 'POST',
      }),
    me: () => request<{ user: any }>('/auth/me'),
  },

  incidents: {
    list: () => request<{ incidents: any[]; count: number }>('/incidents'),
    get: (id: string) => request<{ incident: any }>(`/incidents/${id}`),
    create: (data: any) =>
      request<{ incident: any }>('/incidents', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: string, updates: any) =>
      request<{ incident: any }>(`/incidents/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      }),
    events: (id: string) => request<{ events: any[] }>(`/incidents/${id}/events`),
    addEvent: (id: string, event: any) =>
      request<{ event: any }>(`/incidents/${id}/events`, {
        method: 'POST',
        body: JSON.stringify(event),
      }),
    signals: (id: string) => request<{ signals: any[] }>(`/incidents/${id}/signals`),
  },

  memory: {
    list: () => request<{ memories: any[]; count: number }>('/memory'),
    get: (id: string) => request<{ memory: any }>(`/memory/${id}`),
    recall: (params: any) =>
      request<any>('/memory/recall', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
    retain: (data: any) =>
      request<{ memory: any; message: string }>('/memory/retain', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      request<{ memory: any }>(`/memory/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
    getProvenance: (id: string) => request<any>(`/memory/${id}/provenance`),
    getRecalls: (id: string) => request<{ recalls: any[] }>(`/memory/${id}/recalls`),
  },

  agent: {
    analyze: (incidentId: string) =>
      request<any>('/agent/analyze', {
        method: 'POST',
        body: JSON.stringify({ incidentId }),
      }),
  },

  responsePlans: {
    list: (incidentId: string) => request<{ plans: any[] }>(`/incidents/${incidentId}/response-plans`),
    create: (incidentId: string, plan: any) =>
      request<{ plan: any }>(`/incidents/${incidentId}/response-plans`, {
        method: 'POST',
        body: JSON.stringify(plan),
      }),
    approve: (planId: string, operatorInitials: string) =>
      request<{ plan: any; message: string }>(`/response-plans/${planId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ operatorInitials }),
      }),
    reject: (planId: string, reason: string) =>
      request<{ plan: any; message: string }>(`/response-plans/${planId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }),
  },

  postMortem: {
    get: (incidentId: string) => request<{ postMortem: any }>(`/incidents/${incidentId}/postmortem`),
    save: (incidentId: string, data: any) =>
      request<{ postMortem: any }>(`/incidents/${incidentId}/postmortem`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  audit: {
    list: (params?: { incidentId?: string; limit?: number }) => {
      const query = new URLSearchParams();
      if (params?.incidentId) query.set('incidentId', params.incidentId);
      if (params?.limit) query.set('limit', String(params.limit));
      return request<{ auditLogs: any[]; count: number }>(`/audit?${query.toString()}`);
    },
  },

  demo: {
    getState: () => request<any>('/demo/state'),
    start: () => request<any>('/demo/start', { method: 'POST' }),
    next: () => request<any>('/demo/next', { method: 'POST' }),
    previous: () => request<any>('/demo/previous', { method: 'POST' }),
    goToStep: (step: number) =>
      request<any>('/demo/step', {
        method: 'POST',
        body: JSON.stringify({ step }),
      }),
    reset: () => request<any>('/demo/reset', { method: 'POST' }),
  },

  system: {
    status: () => request<any>('/system/status'),
  },

  admin: {
    getUsers: () => request<{ users: any[]; count: number }>('/admin/users'),
    createUser: (data: {
      name: string;
      email: string;
      password?: string;
      roles: string[];
      permissions?: Record<string, boolean>;
      is_active?: boolean;
    }) =>
      request<{ user: any }>('/admin/users', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateUser: (
      id: string,
      updates: {
        name?: string;
        roles?: string[];
        permissions?: Record<string, boolean>;
        is_active?: boolean;
        password?: string;
      }
    ) =>
      request<{ user: any }>(`/admin/users/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      }),
    deleteUser: (id: string) =>
      request<{ success: boolean; message: string }>(`/admin/users/${id}`, {
        method: 'DELETE',
      }),
    getModules: () =>
      request<{ modules: any[]; defaultPermissions: Record<string, boolean> }>('/admin/modules'),
  },

  aiAnalysis: {
    analyze: (params: {
      incidentId: string;
      incidentQuery?: string;
      enableWebResearch?: boolean;
      customWebTopic?: string;
    }) =>
      request<{ analysis: any }>('/ai/analyze', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
    dispatch: (params: {
      analysisId: string;
      incidentId: string;
      channel: string;
      operatorInitials?: string;
      customNote?: string;
    }) =>
      request<{ success: boolean; message: string; timestamp: string }>('/ai/dispatch', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
  },
};
