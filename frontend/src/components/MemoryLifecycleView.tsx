import React from 'react';

export const MemoryLifecycleView: React.FC = () => {
  const steps = [
    {
      num: '01',
      title: 'TELEMETRY INGESTION',
      sub: 'OpenTelemetry, PagerDuty & Logs',
      desc: 'Real-time extraction of raw 504 error signatures, flamegraphs, container logs, and deployment manifests.',
      badge: 'Continuous Streaming',
      badgeColor: 'text-[#00f0ff] bg-[#00f0ff]/10',
    },
    {
      num: '02',
      title: 'LATENT EMBEDDING & INDEXING',
      sub: 'HyperGraph 1536-dim Vector Space',
      desc: 'Incidents mapped to dense semantic vectors across service topology graphs, symptom vectors, and MTTR coordinates.',
      badge: '14,892 Nodes Active',
      badgeColor: 'text-[#7bd0ff] bg-[#7bd0ff]/10',
    },
    {
      num: '03',
      title: 'ARCHETYPE CLUSTERING',
      sub: 'Cosine L2 Similarity Engine',
      desc: 'Automatic grouping into 412 Failure Archetypes (e.g. Socket Leaks, Pool Starvation, Cache Stampedes).',
      badge: '412 Archetypes',
      badgeColor: 'text-[#7fecde] bg-[#7fecde]/10',
    },
    {
      num: '04',
      title: 'EXPERIENCE RULE SYNTHESIS',
      sub: 'Deductive Heuristic Formation',
      desc: 'Distills natural language operational wisdom: “When socket timeouts spike on payment proxy without CPU increase, inspect upstream status.”',
      badge: '89.4% Verified Utility',
      badgeColor: 'text-[#00f0ff] bg-[#00f0ff]/10',
    },
    {
      num: '05',
      title: 'HUMAN FEEDBACK CALIBRATION',
      sub: 'SRE Validation & Grounding',
      desc: 'Operator feedback strengthens positive links and deprecates ineffective precedents (such as container restart stampedes).',
      badge: 'Operator In-The-Loop',
      badgeColor: 'text-[#7bd0ff] bg-[#7bd0ff]/10',
    },
  ];

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in">
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">history_edu</span>
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              MEMORY EVOLUTION ENGINE
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Hindsight Experience Lifecycle
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            How an ephemeral outage transforms into permanent, actionable collective intelligence.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {steps.map((st) => (
          <div
            key={st.num}
            className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col justify-between shadow-md relative overflow-hidden"
          >
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[22px] font-bold text-[#00f0ff]">{st.num}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${st.badgeColor}`}>
                  {st.badge}
                </span>
              </div>
              <h3 className="font-mono text-[13px] font-bold text-[#e0e2ea]">{st.title}</h3>
              <span className="text-[11px] font-mono text-[#7bd0ff]">{st.sub}</span>
              <p className="text-[12px] text-[#b9cacb] leading-relaxed mt-1">{st.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3">
        <h2 className="text-[16px] font-bold text-[#e0e2ea] flex items-center gap-2">
          <span className="material-symbols-outlined text-[#7fecde] text-[18px]">tune</span>
          <span>HyperGraph Memory Retention &amp; Decay Policies</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-[11px]">
          <div className="p-3 bg-[#1d2025] rounded-lg border border-[#3b494b]/30">
            <span className="text-[#00f0ff] font-bold block mb-1">HALF-LIFE CALIBRATION:</span>
            <span className="text-[#e0e2ea]">Heuristics without verification decay by 15% annual confidence half-life.</span>
          </div>
          <div className="p-3 bg-[#1d2025] rounded-lg border border-[#3b494b]/30">
            <span className="text-[#7fecde] font-bold block mb-1">CROSS-CLUSTER BRIDGING:</span>
            <span className="text-[#e0e2ea]">Incidents in EU-Central propagate failure signatures to US-East in &lt;1.2s.</span>
          </div>
          <div className="p-3 bg-[#1d2025] rounded-lg border border-[#3b494b]/30">
            <span className="text-[#ffb4ab] font-bold block mb-1">STAMPEDE WARNING GUARD:</span>
            <span className="text-[#e0e2ea]">Prevents automated container restarts when socket saturation is confirmed.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
