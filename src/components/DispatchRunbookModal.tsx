import React, { useState } from 'react';
import { RunbookAction } from '../types';

interface DispatchRunbookModalProps {
  actions: RunbookAction[];
  onClose: () => void;
  onExecuteAction: (actionId: string) => void;
  onExecuteAll: () => void;
}

export const DispatchRunbookModal: React.FC<DispatchRunbookModalProps> = ({
  actions,
  onClose,
  onExecuteAction,
  onExecuteAll,
}) => {
  const [operatorInitials, setOperatorInitials] = useState('DM');
  const [safetyChecked, setSafetyChecked] = useState(false);
  const [isExecutingAll, setIsExecutingAll] = useState(false);
  const [executionLogs, setExecutionLogs] = useState<string[]>([
    '[INIT] Human-in-the-loop operator authorization gate opened.',
    '[ADVISORY] Grounded on INC-1987 precedent runbook matrix.',
  ]);

  const handleRunAll = () => {
    if (!safetyChecked) return;
    setIsExecutingAll(true);
    setExecutionLogs((prev) => [
      ...prev,
      `[14:27:01] Dispatch authorization confirmed by Operator ${operatorInitials}`,
      '[14:27:02] Staging Action 1: Failover 50% non-critical traffic...',
      '[14:27:04] Patch applied to gateway-route configmap successfully.',
      '[14:27:05] Staging Action 2: Enforcing 1500ms timeout clamp via istioctl...',
      '[14:27:07] Route rule applied. P99 timeout capped at 1500ms.',
      '[14:27:08] Staging Action 3: Isolating db-pool-worker-04...',
      '[14:27:10] Connection pool recycled. Socket pool recovery underway.',
      '[14:27:12] SUCCESS: All 3 actions successfully staged and applied in cluster us-east-prod-k8s.',
    ]);
    onExecuteAll();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-2xl bg-[#111827] border border-[#00f0ff]/40 rounded-xl shadow-[0_0_30px_rgba(0,240,255,0.25)] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 bg-[#0b0e13] border-b border-[#3b494b]/40">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[#00f0ff] text-[22px]">
              verified_user
            </span>
            <div>
              <span className="font-mono text-[11px] font-bold text-[#00f0ff] uppercase tracking-wider block">
                HUMAN-IN-THE-LOOP DISPATCH DESK
              </span>
              <h2 className="text-[16px] font-semibold text-[#e0e2ea]">
                Execute Recommended Staged Response Plan
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded hover:bg-[#272a30] text-[#b9cacb] hover:text-[#e0e2ea] flex items-center justify-center transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* Advisory Notice */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-[#272a30]/80 border border-[#00a6e0]/30 text-[12px] font-mono text-[#7bd0ff]">
            <span className="material-symbols-outlined text-[20px] text-[#00a6e0] shrink-0">
              shield_with_heart
            </span>
            <span>
              Autonomous execution is restricted by design. Each remedial cluster mutation requires deliberate operator sign-off.
            </span>
          </div>

          {/* Action List */}
          <div className="space-y-2">
            <span className="text-[11px] font-mono font-bold text-[#b9cacb] uppercase tracking-wider block">
              Staged Runbook Steps ({actions.length})
            </span>

            {actions.map((act) => (
              <div
                key={act.id}
                className="p-3 rounded-lg bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono text-[13px]">
                    <span className="text-[#00f0ff] font-bold">{act.stepNumber}.</span>
                    <span className="text-[#e0e2ea] font-medium">{act.title}</span>
                  </div>

                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                      act.riskLevel === 'SAFE'
                        ? 'bg-[#7fecde]/20 text-[#7fecde]'
                        : act.riskLevel === 'MITIGATE'
                        ? 'bg-[#00a6e0]/20 text-[#7bd0ff]'
                        : 'bg-[#93000a]/40 text-[#ffb4ab]'
                    }`}
                  >
                    {act.riskLevel}
                  </span>
                </div>

                <p className="text-[12px] text-[#b9cacb]">{act.description}</p>

                {act.commandSnippet && (
                  <pre className="p-2 rounded bg-[#0b0e13] text-[11px] font-mono text-[#00f0ff] overflow-x-auto border border-[#3b494b]/30">
                    <code>{act.commandSnippet}</code>
                  </pre>
                )}

                <div className="flex justify-end pt-1">
                  <button
                    onClick={() => onExecuteAction(act.id)}
                    className="px-3 py-1 rounded bg-[#272a30] hover:bg-[#32353b] text-[#dbfcff] text-[11px] font-mono flex items-center gap-1 transition-colors"
                  >
                    <span className="material-symbols-outlined text-[14px]">play_arrow</span>
                    <span>Dispatch Step {act.stepNumber} Only</span>
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Operator Confirmation Checklist */}
          <div className="p-3.5 rounded-lg bg-[#1d2025] border border-[#3b494b]/40 space-y-3 font-mono">
            <label className="flex items-center gap-2.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={safetyChecked}
                onChange={(e) => setSafetyChecked(e.target.checked)}
                className="w-4 h-4 rounded border-[#3b494b] text-[#00f0ff] focus:ring-0 focus:ring-offset-0 bg-[#0b0e13]"
              />
              <span className="text-[12px] text-[#e0e2ea]">
                I verify that this plan is grounded in precedent <strong className="text-[#00f0ff]">INC-1987</strong> and poses acceptable cluster blast radius.
              </span>
            </label>

            <div className="flex items-center gap-3 pt-1">
              <span className="text-[11px] text-[#b9cacb]">Operator Sign-off:</span>
              <input
                type="text"
                value={operatorInitials}
                onChange={(e) => setOperatorInitials(e.target.value.toUpperCase())}
                maxLength={4}
                className="w-16 px-2 py-1 rounded bg-[#0b0e13] border border-[#3b494b] text-[#00f0ff] text-center text-[12px] font-bold"
              />
              <span className="text-[11px] text-[#b9cacb]">SRE on-call (D. Mercer)</span>
            </div>
          </div>

          {/* Execution Stream */}
          {executionLogs.length > 2 && (
            <div className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b]/40 space-y-1 font-mono text-[11px]">
              <div className="text-[#00f0ff] font-bold mb-1">CLUSTER AUDIT TRAIL:</div>
              {executionLogs.map((log, idx) => (
                <div key={idx} className="text-[#b9cacb]">
                  {log}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-[#0b0e13] border-t border-[#3b494b]/40 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-[#272a30] hover:bg-[#32353b] text-[12px] font-mono text-[#b9cacb] transition-colors"
          >
            Cancel Dispatch
          </button>

          <button
            onClick={handleRunAll}
            disabled={!safetyChecked || isExecutingAll}
            className={`px-5 py-2 rounded text-[13px] font-mono font-bold flex items-center gap-2 transition-all ${
              safetyChecked && !isExecutingAll
                ? 'bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] shadow-[0_0_16px_rgba(0,240,255,0.4)] cursor-pointer'
                : 'bg-[#272a30] text-[#849495] cursor-not-allowed opacity-60'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">
              {isExecutingAll ? 'autorenew' : 'rocket_launch'}
            </span>
            <span>
              {isExecutingAll ? 'Staging Execution in Cluster...' : 'Confirm & Dispatch 3-Step Plan'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};
