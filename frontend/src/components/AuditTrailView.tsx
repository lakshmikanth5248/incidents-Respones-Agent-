import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export const AuditTrailView: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      const res = await api.audit.list({ limit: 100 });
      setLogs(res.auditLogs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 8000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in">
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">policy</span>
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              SYSTEM COMPLIANCE &amp; TAMPER-EVIDENT JOURNAL
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Immutable Operator &amp; Agent Audit Trail
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Cryptographically sealed operational audit events for human-in-the-loop decisions, approvals, and retentions.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="px-3 py-1.5 rounded-lg bg-[#272a30] hover:bg-[#36393f] text-[#dbfcff] font-mono text-[11px] flex items-center gap-1.5 border border-[#3b494b]/40 transition-colors"
        >
          <span className="material-symbols-outlined text-[16px]">refresh</span>
          <span>Refresh Journal</span>
        </button>
      </div>

      <div className="w-full overflow-x-auto bg-[#0b0e13] rounded-xl border border-[#3b494b]/40 shadow-xl">
        <table className="w-full text-left font-mono text-[12px]">
          <thead>
            <tr className="bg-[#181c21] text-[#b9cacb] text-[10px] uppercase border-b border-[#3b494b]/40">
              <th className="py-3 px-4">Timestamp (UTC)</th>
              <th className="py-3 px-4">Action</th>
              <th className="py-3 px-4">Entity Type</th>
              <th className="py-3 px-4">Incident / Target</th>
              <th className="py-3 px-4">Operator / Principal</th>
              <th className="py-3 px-4">IP Address</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#3b494b]/20 text-[#e0e2ea]">
            {loading && logs.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-[#b9cacb]">
                  Loading immutable audit entries...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-[#b9cacb]">
                  No audit logs recorded yet.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-[#181c21]/60 transition-colors">
                  <td className="py-2.5 px-4 text-[#7bd0ff]">
                    {new Date(log.created_at).toISOString().replace('T', ' ').slice(0, 19)}
                  </td>
                  <td className="py-2.5 px-4">
                    <span className="px-2 py-0.5 rounded bg-[#272a30] text-[#00f0ff] font-bold text-[11px]">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-[#b9cacb]">
                    {log.entity_type}
                  </td>
                  <td className="py-2.5 px-4 text-[#dbfcff]">
                    {log.incident_id || log.entity_id || 'SYSTEM'}
                  </td>
                  <td className="py-2.5 px-4 text-[#7fecde]">
                    {log.user_id || 'Autonomous Agent'}
                  </td>
                  <td className="py-2.5 px-4 text-[#849495] text-[11px]">
                    {log.ip_address}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
