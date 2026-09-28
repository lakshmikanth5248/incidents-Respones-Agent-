import React, { useState } from 'react';
import { ALL_INCIDENTS } from '../data/mockData';
import { Severity, IncidentStatus } from '../types';

interface IncidentsListProps {
  onInvestigate: (incidentId: string) => void;
}

export const IncidentsList: React.FC<IncidentsListProps> = ({ onInvestigate }) => {
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filtered = ALL_INCIDENTS.filter((inc) => {
    const matchesSev = severityFilter === 'ALL' || inc.severity === severityFilter;
    const matchesStatus = statusFilter === 'ALL' || inc.status === statusFilter;
    const matchesSearch =
      searchTerm === '' ||
      inc.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSev && matchesStatus && matchesSearch;
  });

  return (
    <div className="flex flex-col w-full gap-4 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0b0e13] p-4 rounded-xl border border-[#3b494b]/40 shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#ffb4ab] text-[18px]">crisis_alert</span>
            <span className="font-mono text-[10px] text-[#ffb4ab] uppercase tracking-wider font-bold">
              INCIDENT REGISTRY
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Fleet Production Incidents
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Unified triage log across all production Kubernetes clusters and ingress edge regions.
          </p>
        </div>

        <button
          onClick={() => onInvestigate('INC-2048')}
          className="px-4 py-2 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-mono text-[12px] font-bold flex items-center gap-1.5 shadow-[0_0_12px_rgba(0,240,255,0.3)] transition-all cursor-pointer"
        >
          <span className="material-symbols-outlined text-[16px]">troubleshoot</span>
          <span>Open Active Triage (INC-2048)</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="p-3 rounded-lg bg-[#181c21] border border-[#3b494b]/40 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 bg-[#0b0e13] border border-[#3b494b]/40 px-3 py-1.5 rounded-lg">
            <span className="material-symbols-outlined text-[16px] text-[#b9cacb]">search</span>
            <input
              type="text"
              placeholder="Search incidents or root causes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-transparent font-mono text-[11px] text-[#e0e2ea] placeholder:text-[#849495] focus:outline-none w-56"
            />
          </div>

          <div className="flex items-center gap-1 bg-[#0b0e13] p-1 rounded-lg border border-[#3b494b]/40">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2.5 py-0.5 rounded font-mono text-[10px] font-bold transition-all ${
                  severityFilter === sev ? 'bg-[#00f0ff] text-[#00363a]' : 'text-[#b9cacb] hover:text-[#e0e2ea]'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 bg-[#0b0e13] p-1 rounded-lg border border-[#3b494b]/40">
            {['ALL', 'ACTIVE', 'MITIGATING', 'RESOLVED', 'POST_MORTEM'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-0.5 rounded font-mono text-[10px] font-bold transition-all ${
                  statusFilter === st ? 'bg-[#7fecde] text-[#003732]' : 'text-[#b9cacb] hover:text-[#e0e2ea]'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        <span className="text-[11px] font-mono text-[#b9cacb]">
          Showing {filtered.length} incidents
        </span>
      </div>

      {/* Incidents Table */}
      <div className="w-full overflow-x-auto bg-[#0b0e13] rounded-xl border border-[#3b494b]/40 shadow-xl">
        <table className="w-full text-left font-mono text-[12px]">
          <thead>
            <tr className="bg-[#181c21] text-[#b9cacb] text-[10px] uppercase border-b border-[#3b494b]/40">
              <th className="py-3 px-4">Incident ID</th>
              <th className="py-3 px-4">Severity</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Target Endpoint</th>
              <th className="py-3 px-4">Cluster / Region</th>
              <th className="py-3 px-4">P99 Latency</th>
              <th className="py-3 px-4">Error Rate</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#3b494b]/20 text-[#e0e2ea]">
            {filtered.map((inc) => (
              <tr
                key={inc.id}
                onClick={() => onInvestigate(inc.id)}
                className={`transition-colors cursor-pointer ${
                  inc.status === 'ACTIVE'
                    ? 'bg-[#272a30]/80 border-l-2 border-[#ffb4ab]'
                    : 'bg-[#181c21]/40 hover:bg-[#1d2025]'
                }`}
              >
                <td className="py-3 px-4 font-bold text-[#dbfcff]">
                  <div className="flex items-center gap-2">
                    {inc.status === 'ACTIVE' && (
                      <span className="w-2 h-2 rounded-full bg-[#ffb4ab] animate-pulse" />
                    )}
                    <span>{inc.id}</span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      inc.severity === 'HIGH'
                        ? 'bg-[#93000a] text-[#ffdad6]'
                        : inc.severity === 'MEDIUM'
                        ? 'bg-[#f59e0b]/20 text-[#f59e0b]'
                        : 'bg-[#7fecde]/20 text-[#7fecde]'
                    }`}
                  >
                    {inc.severity}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <span className="text-[#b9cacb] uppercase text-[11px] font-bold">
                    {inc.status}
                  </span>
                </td>
                <td className="py-3 px-4 text-[#7bd0ff]">
                  {inc.endpoint}
                </td>
                <td className="py-3 px-4 text-[#b9cacb]">
                  {inc.cluster}
                </td>
                <td className="py-3 px-4 text-[#ffb4ab] font-bold">
                  {inc.telemetry.p99Latency}ms
                </td>
                <td className="py-3 px-4 text-[#ffdad6]">
                  {inc.telemetry.errorRate}%
                </td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onInvestigate(inc.id);
                    }}
                    className="px-3 py-1 rounded bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-bold text-[11px] transition-all"
                  >
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
