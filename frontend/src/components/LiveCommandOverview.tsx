import React from 'react';
import { ALL_INCIDENTS, CURRENT_INCIDENT } from '../data/mockData';
import { HindsightPrecedentFrequencyChart } from './HindsightPrecedentFrequencyChart';

interface LiveCommandOverviewProps {
  onInvestigate: (incidentId: string) => void;
  onExploreGraph: () => void;
  onNavigateToDemo?: () => void;
}

export const LiveCommandOverview: React.FC<LiveCommandOverviewProps> = ({
  onInvestigate,
  onExploreGraph,
  onNavigateToDemo,
}) => {
  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in">
      {/* Featured Guided Demo Storyline Card */}
      {onNavigateToDemo && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-[#00f0ff]/15 via-[#00f0ff]/5 to-transparent border border-[#00f0ff]/40 shadow-[0_0_20px_rgba(0,240,255,0.12)] flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-[#00f0ff]/20 border border-[#00f0ff] flex items-center justify-center text-[#00f0ff] shrink-0">
              <span className="material-symbols-outlined text-[24px]">auto_stories</span>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
                  FEATURED EVALUATION WALKTHROUGH
                </span>
                <span className="px-1.5 py-0.5 rounded bg-[#00f0ff] text-[#00363a] font-mono text-[9px] font-extrabold">
                  9 INTERACTIVE STEPS
                </span>
              </div>
              <h2 className="text-[17px] font-bold text-[#dbfcff]">
                Guided Demo Storyline: Dual-Incident Memory Precedent Recall
              </h2>
              <p className="text-[12px] text-[#b9cacb]">
                Step through Incident A resolution, HyperGraph persistence, Incident B semantic retrieval, and runbook staging.
              </p>
            </div>
          </div>
          <button
            onClick={onNavigateToDemo}
            className="px-4 py-2 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-mono text-[12px] font-bold flex items-center gap-2 shadow-[0_0_15px_rgba(0,240,255,0.3)] transition-all cursor-pointer shrink-0"
          >
            <span className="material-symbols-outlined text-[18px]">play_circle</span>
            <span>Launch Guided Demo Storyline</span>
          </button>
        </div>
      )}

      {/* Top Banner */}
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#00f0ff] animate-pulse" />
            <span className="font-mono text-[11px] text-[#00f0ff] uppercase tracking-wider font-bold">
              GLOBAL SRE RADAR
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Tactical Operations Command
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Continuous autonomous telemetry surveillance and cross-incident memory synthesis.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onInvestigate('INC-2048')}
            className="px-4 py-2 rounded-lg bg-[#93000a] hover:bg-[#93000a]/90 text-[#ffdad6] font-mono text-[12px] font-bold flex items-center gap-2 border border-[#ffb4ab]/40 shadow-[0_0_12px_rgba(147,0,10,0.4)] cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px] animate-pulse">crisis_alert</span>
            <span>Jump to Active Sev-1 (INC-2048)</span>
          </button>
          <button
            onClick={onExploreGraph}
            className="px-4 py-2 rounded-lg bg-[#272a30] hover:bg-[#32353b] text-[#00f0ff] font-mono text-[12px] flex items-center gap-2 border border-[#00f0ff]/30 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">hub</span>
            <span>Open Experience Graph</span>
          </button>
        </div>
      </div>

      {/* Fleet Telemetry Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-[#181c21] border border-[#ffb4ab]/30 flex flex-col gap-1">
          <div className="flex justify-between items-center text-[#b9cacb] font-mono text-[11px]">
            <span>ACTIVE INCIDENTS</span>
            <span className="material-symbols-outlined text-[#ffb4ab] text-[18px]">warning</span>
          </div>
          <span className="text-[28px] font-mono font-bold text-[#ffb4ab]">1 SEV-1</span>
          <span className="text-[11px] font-mono text-[#b9cacb]">INC-2048 in Payment Gateway</span>
        </div>

        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <div className="flex justify-between items-center text-[#b9cacb] font-mono text-[11px]">
            <span>SYSTEM HEALTH</span>
            <span className="material-symbols-outlined text-[#7fecde] text-[18px]">check_circle</span>
          </div>
          <span className="text-[28px] font-mono font-bold text-[#7fecde]">99.82%</span>
          <span className="text-[11px] font-mono text-[#b9cacb]">28 of 32 microservices nominal</span>
        </div>

        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <div className="flex justify-between items-center text-[#b9cacb] font-mono text-[11px]">
            <span>HINDSIGHT RECALL RATE</span>
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">psychology</span>
          </div>
          <span className="text-[28px] font-mono font-bold text-[#00f0ff]">91.4% SIM</span>
          <span className="text-[11px] font-mono text-[#b9cacb]">Precedent INC-1987 grounded</span>
        </div>

        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <div className="flex justify-between items-center text-[#b9cacb] font-mono text-[11px]">
            <span>AVERAGE MTTR REDUCTION</span>
            <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">trending_down</span>
          </div>
          <span className="text-[28px] font-mono font-bold text-[#7bd0ff]">-64%</span>
          <span className="text-[11px] font-mono text-[#b9cacb]">Across 412 Failure Archetypes</span>
        </div>
      </div>

      {/* 30-Day Hindsight Precedent Recall Frequency & Recurring System Issues */}
      <HindsightPrecedentFrequencyChart onSelectPrecedent={onInvestigate} />

      {/* Main Grid: Active Incidents Radar & Cluster Topology */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Active Incidents Feed */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[16px] font-bold text-[#e0e2ea] flex items-center gap-2">
              <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">crisis_alert</span>
              <span>Active &amp; Recent Incidents</span>
            </h2>
            <span className="text-[11px] font-mono text-[#b9cacb]">
              Showing {ALL_INCIDENTS.length} records
            </span>
          </div>

          <div className="flex flex-col gap-2.5">
            {ALL_INCIDENTS.map((inc) => (
              <div
                key={inc.id}
                onClick={() => onInvestigate(inc.id)}
                className={`p-4 rounded-lg border transition-all cursor-pointer flex flex-col gap-2 ${
                  inc.status === 'ACTIVE'
                    ? 'bg-[#272a30] border-[#00f0ff]/50 shadow-[0_0_12px_rgba(0,240,255,0.15)]'
                    : 'bg-[#1d2025] border-[#3b494b]/30 hover:border-[#3b494b]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[14px] font-bold text-[#dbfcff]">
                      {inc.id}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        inc.severity === 'HIGH'
                          ? 'bg-[#93000a] text-[#ffdad6]'
                          : inc.severity === 'MEDIUM'
                          ? 'bg-[#f59e0b]/20 text-[#f59e0b]'
                          : 'bg-[#7fecde]/20 text-[#7fecde]'
                      }`}
                    >
                      {inc.severity} SEVERITY
                    </span>
                    <span className="text-[11px] font-mono text-[#b9cacb]">
                      {inc.region}
                    </span>
                  </div>

                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-bold ${
                      inc.status === 'ACTIVE'
                        ? 'bg-[#93000a] text-[#ffdad6] animate-pulse'
                        : 'bg-[#181c21] text-[#7fecde]'
                    }`}
                  >
                    {inc.status}
                  </span>
                </div>

                <div className="text-[14px] font-semibold text-[#e0e2ea]">{inc.title}</div>
                <p className="text-[12px] text-[#b9cacb] line-clamp-2">{inc.description}</p>

                <div className="flex items-center justify-between pt-1 border-t border-[#3b494b]/30 text-[11px] font-mono text-[#b9cacb]">
                  <div className="flex items-center gap-3">
                    <span>Endpoint: <strong className="text-[#dbfcff]">{inc.endpoint}</strong></span>
                    <span>P99: <strong className="text-[#ffb4ab]">{inc.telemetry.p99Latency}ms</strong></span>
                  </div>
                  <span className="text-[#00f0ff] hover:underline flex items-center gap-1">
                    <span>Launch Investigation</span>
                    <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cognitive AI Agent Status & Reasoning Log */}
        <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3">
          <h2 className="text-[16px] font-bold text-[#e0e2ea] flex items-center gap-2">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">neurology</span>
            <span>Agent Cognitive Heartbeat</span>
          </h2>

          <div className="bg-[#1d2025] p-3 rounded-lg border border-[#3b494b]/30 flex flex-col gap-2 font-mono text-[11px]">
            <div className="flex justify-between items-center">
              <span className="text-[#b9cacb]">Primary Engine:</span>
              <span className="text-[#00f0ff] font-bold">Aegis-Reason-v4</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#b9cacb]">Vector Embedding Store:</span>
              <span className="text-[#7fecde]">HyperGraph 1536-dim</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#b9cacb]">Current Active Triage:</span>
              <span className="text-[#ffb4ab] font-bold">INC-2048</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#b9cacb]">Execution Policy:</span>
              <span className="text-[#7bd0ff]">Advisory-Only (Gated)</span>
            </div>
          </div>

          <div className="flex flex-col gap-2 pt-1">
            <span className="font-mono text-[10px] text-[#b9cacb] uppercase tracking-wider font-bold">
              Cognitive Stream Insights
            </span>
            <div className="space-y-2 font-mono text-[11px]">
              <div className="p-2 rounded bg-[#0b0e13] border border-[#3b494b]/30">
                <span className="text-[#00f0ff] font-bold">[14:05:40]</span> Correlated 504 timeouts with historical card processor throttling in INC-1987.
              </div>
              <div className="p-2 rounded bg-[#0b0e13] border border-[#3b494b]/30">
                <span className="text-[#7fecde] font-bold">[14:06:12]</span> Staged 3 non-destructive remediation runbook actions.
              </div>
              <div className="p-2 rounded bg-[#0b0e13] border border-[#3b494b]/30">
                <span className="text-[#7bd0ff] font-bold">[14:12:00]</span> Monitoring canary route weight on Adyen fallback.
              </div>
            </div>
          </div>

          <button
            onClick={() => onInvestigate('INC-2048')}
            className="w-full mt-auto py-2.5 rounded-lg bg-[#00f0ff] text-[#00363a] font-bold text-[13px] font-mono hover:bg-[#7df4ff] transition-all shadow-[0_0_12px_rgba(0,240,255,0.3)] flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">troubleshoot</span>
            <span>Open Investigation Workspace</span>
          </button>
        </div>
      </div>
    </div>
  );
};
