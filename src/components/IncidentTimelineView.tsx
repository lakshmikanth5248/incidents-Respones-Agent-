import React from 'react';

export const IncidentTimelineView: React.FC = () => {
  const events = [
    {
      time: '13:45:00 UTC',
      type: 'DEPLOY',
      title: 'Canary Deployment: stripe-connector v2.14.0',
      desc: '10% traffic weight diverted to new connector image with commit #d3a401b.',
      icon: 'rocket_launch',
      color: 'text-[#7bd0ff]',
    },
    {
      time: '14:02:11 UTC',
      type: 'ALERT',
      title: 'First 504 Gateway Timeout detected on /v2/checkout/charge',
      desc: 'Edge ingress logged 12 read timeout exceptions within a 10s window.',
      icon: 'warning',
      color: 'text-[#ffb4ab]',
    },
    {
      time: '14:02:18 UTC',
      type: 'AGENT',
      title: 'Aegis Incident Ingestion Initiated (INC-2048)',
      desc: 'OpenTelemetry span traces aggregated; Sev-1 classification assigned automatically.',
      icon: 'psychology',
      color: 'text-[#00f0ff]',
    },
    {
      time: '14:03:02 UTC',
      type: 'MEMORY',
      title: 'HyperGraph Spatial Memory Query',
      desc: 'Queried 14,892 historical incident embeddings with symptom vector [504, pool_lock, thread_exhaustion].',
      icon: 'hub',
      color: 'text-[#7fecde]',
    },
    {
      time: '14:04:15 UTC',
      type: 'PRECEDENT',
      title: 'Precedent Match: INC-1987 (91.4% Similarity)',
      desc: 'Identified matching pattern: third-party card processor throttling masquerading as internal app deadlock.',
      icon: 'verified',
      color: 'text-[#00f0ff]',
    },
    {
      time: '14:06:12 UTC',
      type: 'HYPOTHESIS',
      title: 'Deductive Hypothesis Formulated',
      desc: 'Recommended staged plan: failover 50% traffic to Adyen, clamp timeouts to 1500ms, recycle connection pool.',
      icon: 'playlist_add_check',
      color: 'text-[#7fecde]',
    },
    {
      time: '14:26:08 UTC',
      type: 'OPERATOR',
      title: 'SRE Operator D. Mercer Reviewing Response Plan',
      desc: 'Operator analyzing live 3D topology and grounding matrix.',
      icon: 'person',
      color: 'text-[#dbfcff]',
    },
  ];

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in">
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">timeline</span>
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              MICROSECOND TRACE CORRELATION
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Incident Timeline: INC-2048
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Chronological audit log cross-referencing code deployments, telemetry anomalies, and AI cognitive recalls.
          </p>
        </div>
      </div>

      <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-4 shadow-xl">
        <div className="relative border-l-2 border-[#3b494b]/60 ml-4 pl-6 space-y-6">
          {events.map((ev, idx) => (
            <div key={idx} className="relative group">
              {/* Dot Icon */}
              <div className="absolute -left-[35px] top-0 w-8 h-8 rounded-full bg-[#111827] border border-[#3b494b] flex items-center justify-center shadow-md">
                <span className={`material-symbols-outlined text-[16px] ${ev.color}`}>
                  {ev.icon}
                </span>
              </div>

              <div className="p-3.5 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex flex-col gap-1 hover:border-[#00f0ff]/40 transition-colors">
                <div className="flex items-center justify-between font-mono text-[11px]">
                  <span className={`font-bold ${ev.color}`}>{ev.type}</span>
                  <span className="text-[#b9cacb]">{ev.time}</span>
                </div>
                <h3 className="text-[14px] font-semibold text-[#e0e2ea]">{ev.title}</h3>
                <p className="text-[12px] text-[#b9cacb] leading-relaxed">{ev.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
