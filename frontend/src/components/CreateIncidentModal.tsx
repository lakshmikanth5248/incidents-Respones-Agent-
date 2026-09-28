import React, { useState } from 'react';
import { api } from '../services/api';

interface CreateIncidentModalProps {
  onClose: () => void;
  onCreated: (incidentId: string) => void;
}

export const CreateIncidentModal: React.FC<CreateIncidentModalProps> = ({ onClose, onCreated }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<'SEV-1' | 'SEV-2' | 'SEV-3' | 'SEV-4'>('SEV-1');
  const [service, setService] = useState('Payment Gateway Proxy');
  const [environment, setEnvironment] = useState('production-us-east (iad01)');
  const [affectedServices, setAffectedServices] = useState('Checkout API, Order Worker, Envoy Mesh');
  const [observedSymptoms, setObservedSymptoms] = useState('504 Gateway Timeout, Socket Pool Saturation');
  const [recentDeployments, setRecentDeployments] = useState('stripe-connector v2.14.0 (Canary 10%)');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.incidents.create({
        title,
        description,
        severity,
        service,
        environment,
        affectedServices: affectedServices.split(',').map((s) => s.trim()),
        observedSymptoms: observedSymptoms.split(',').map((s) => s.trim()),
        recentDeployments: recentDeployments.split(',').map((s) => s.trim()),
      });
      onCreated(res.incident.id);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create incident');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-2xl bg-[#111827] border border-[#00f0ff]/40 rounded-xl shadow-[0_0_30px_rgba(0,240,255,0.25)] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 bg-[#0b0e13] border-b border-[#3b494b]/40">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[#ffb4ab] text-[22px]">
              add_alert
            </span>
            <div>
              <span className="font-mono text-[10px] text-[#ffb4ab] uppercase tracking-wider font-bold block">
                MANUAL INCIDENT REGISTRATION
              </span>
              <h2 className="text-[16px] font-semibold text-[#e0e2ea]">
                Create Production Incident
              </h2>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded hover:bg-[#272a30] text-[#b9cacb] hover:text-[#e0e2ea] flex items-center justify-center">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-3.5 max-h-[75vh] overflow-y-auto font-mono text-[12px]">
          {error && (
            <div className="p-2.5 rounded bg-[#93000a]/40 border border-[#ffb4ab]/40 text-[#ffdad6]">
              {error}
            </div>
          )}

          <div>
            <label className="text-[#b9cacb] block mb-1">INCIDENT TITLE *</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Payment Gateway Read Timeout Cascade"
              className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[#b9cacb] block mb-1">SEVERITY CLASSIFICATION *</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value as any)}
                className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
              >
                <option value="SEV-1">SEV-1 (Critical Business Outage)</option>
                <option value="SEV-2">SEV-2 (High Degradation)</option>
                <option value="SEV-3">SEV-3 (Moderate Partial Impact)</option>
                <option value="SEV-4">SEV-4 (Low / Minor Diagnostic)</option>
              </select>
            </div>

            <div>
              <label className="text-[#b9cacb] block mb-1">CORE SERVICE *</label>
              <input
                type="text"
                required
                value={service}
                onChange={(e) => setService(e.target.value)}
                className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-[#b9cacb] block mb-1">ENVIRONMENT / CLUSTER</label>
            <input
              type="text"
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
            />
          </div>

          <div>
            <label className="text-[#b9cacb] block mb-1">INCIDENT DESCRIPTION &amp; SYMPTOMS</label>
            <textarea
              rows={3}
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe observed behavior, error signatures, and blast radius..."
              className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[#b9cacb] block mb-1">OBSERVED SYMPTOMS (Comma Separated)</label>
              <input
                type="text"
                value={observedSymptoms}
                onChange={(e) => setObservedSymptoms(e.target.value)}
                className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[#b9cacb] block mb-1">RECENT DEPLOYMENTS (T-60m)</label>
              <input
                type="text"
                value={recentDeployments}
                onChange={(e) => setRecentDeployments(e.target.value)}
                className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 bg-[#0b0e13] border-t border-[#3b494b]/40 flex items-center justify-between -mx-5 -mb-5 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded bg-[#272a30] hover:bg-[#32353b] text-[#b9cacb] transition-colors"
            >
              CANCEL
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-bold shadow-[0_0_14px_rgba(0,240,255,0.3)] transition-all flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[16px]">crisis_alert</span>
              <span>{loading ? 'CREATING...' : 'CREATE INCIDENT'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
