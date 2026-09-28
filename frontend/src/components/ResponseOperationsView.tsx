import React, { useState } from 'react';
import { RECOMMENDED_RUNBOOK_ACTIONS } from '../data/mockData';
import { RunbookAction } from '../types';

export const ResponseOperationsView: React.FC = () => {
  const [actions, setActions] = useState<RunbookAction[]>(RECOMMENDED_RUNBOOK_ACTIONS);
  const [canaryWeight, setCanaryWeight] = useState<number>(50);
  const [timeoutClamp, setTimeoutClamp] = useState<number>(1500);
  const [statusLog, setStatusLog] = useState<string[]>([
    '[14:06:12] 3 Runbook Actions staged by Cognitive Agent based on INC-1987 precedent.',
    '[14:15:30] Awaiting Human Operator sign-off before cluster state change.',
  ]);

  const handleExecute = (id: string) => {
    setActions((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: 'APPLIED' } : a))
    );
    setStatusLog((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] Executed action ${id} successfully. Applied to cluster.`,
    ]);
  };

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in">
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#7fecde] text-[18px]">bolt</span>
            <span className="font-mono text-[10px] text-[#7fecde] uppercase tracking-wider font-bold">
              OPERATIONS DISPATCH DESK
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Response Operations &amp; Runbook Actions
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Human-in-the-loop remediation console grounded in verified historical precedents.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#272a30] border border-[#00a6e0]/30 font-mono text-[11px] text-[#7bd0ff]">
          <span className="material-symbols-outlined text-[16px] text-[#00a6e0]">shield_with_heart</span>
          <span>AUTONOMOUS EXECUTION: DISABLED (OPERATOR CONFIRMATION REQUIRED)</span>
        </div>
      </div>

      {/* Grid: Actions & Canary Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8 flex flex-col gap-3">
          <h2 className="text-[16px] font-bold text-[#e0e2ea] flex items-center gap-2">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">playlist_play</span>
            <span>Staged Runbook Directives (INC-2048)</span>
          </h2>

          <div className="space-y-3">
            {actions.map((act) => (
              <div
                key={act.id}
                className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-2.5 shadow-md"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="w-6 h-6 rounded bg-[#272a30] text-[#00f0ff] font-mono text-[12px] font-bold flex items-center justify-center">
                      {act.stepNumber}
                    </span>
                    <h3 className="text-[14px] font-semibold text-[#e0e2ea]">{act.title}</h3>
                  </div>

                  <div className="flex items-center gap-2 font-mono text-[10px]">
                    <span
                      className={`px-2 py-0.5 rounded font-bold uppercase ${
                        act.riskLevel === 'SAFE'
                          ? 'bg-[#7fecde]/20 text-[#7fecde]'
                          : act.riskLevel === 'MITIGATE'
                          ? 'bg-[#00a6e0]/20 text-[#7bd0ff]'
                          : 'bg-[#93000a]/40 text-[#ffb4ab]'
                      }`}
                    >
                      {act.riskLevel}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded font-bold uppercase ${
                        act.status === 'APPLIED' ? 'bg-[#7fecde] text-[#003732]' : 'bg-[#272a30] text-[#b9cacb]'
                      }`}
                    >
                      {act.status}
                    </span>
                  </div>
                </div>

                <p className="text-[12px] text-[#b9cacb]">{act.description}</p>

                {act.commandSnippet && (
                  <pre className="p-2.5 rounded bg-[#0b0e13] font-mono text-[11px] text-[#00f0ff] border border-[#3b494b]/30 overflow-x-auto">
                    <code>{act.commandSnippet}</code>
                  </pre>
                )}

                <div className="flex justify-between items-center pt-1 border-t border-[#3b494b]/30">
                  <span className="font-mono text-[11px] text-[#b9cacb]">
                    Target: <strong className="text-[#dbfcff]">{act.targetComponent}</strong>
                  </span>

                  <button
                    onClick={() => handleExecute(act.id)}
                    disabled={act.status === 'APPLIED'}
                    className={`px-4 py-1.5 rounded font-mono text-[11px] font-bold flex items-center gap-1.5 transition-all ${
                      act.status === 'APPLIED'
                        ? 'bg-[#272a30] text-[#7fecde] cursor-default'
                        : 'bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] shadow-[0_0_10px_rgba(0,240,255,0.3)] cursor-pointer'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      {act.status === 'APPLIED' ? 'check' : 'play_arrow'}
                    </span>
                    <span>{act.status === 'APPLIED' ? 'Applied in Cluster' : 'Authorize & Execute'}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Live Tuners & Controls */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3 shadow-md">
            <h3 className="text-[14px] font-bold text-[#e0e2ea] flex items-center gap-2">
              <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">tune</span>
              <span>Dynamic Traffic Shaper</span>
            </h3>

            <div className="space-y-3 font-mono text-[11px]">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-[#b9cacb]">Gateway Failover Ratio:</span>
                  <span className="text-[#00f0ff] font-bold">{canaryWeight}% Secondary</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={canaryWeight}
                  onChange={(e) => setCanaryWeight(Number(e.target.value))}
                  className="w-full accent-[#00f0ff] bg-[#0b0e13]"
                />
                <div className="flex justify-between text-[10px] text-[#849495] mt-1">
                  <span>100% Primary (Stripe)</span>
                  <span>100% Fallback (Adyen)</span>
                </div>
              </div>

              <div className="pt-2 border-t border-[#3b494b]/30">
                <div className="flex justify-between mb-1">
                  <span className="text-[#b9cacb]">Socket Timeout Clamp:</span>
                  <span className="text-[#ffb4ab] font-bold">{timeoutClamp}ms</span>
                </div>
                <input
                  type="range"
                  min="500"
                  max="5000"
                  step="250"
                  value={timeoutClamp}
                  onChange={(e) => setTimeoutClamp(Number(e.target.value))}
                  className="w-full accent-[#ffb4ab] bg-[#0b0e13]"
                />
                <div className="flex justify-between text-[10px] text-[#849495] mt-1">
                  <span>500ms (Aggressive)</span>
                  <span>5000ms (Default)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Audit Log */}
          <div className="p-4 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 flex flex-col gap-2">
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              CLUSTER DISPATCH AUDIT LOG
            </span>
            <div className="font-mono text-[11px] text-[#b9cacb] space-y-1.5 max-h-56 overflow-y-auto">
              {statusLog.map((log, i) => (
                <div key={i} className="leading-tight">
                  {log}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
