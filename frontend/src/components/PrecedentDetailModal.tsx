import React from 'react';
import { MemoryPrecedent } from '../types';

interface PrecedentDetailModalProps {
  precedent: MemoryPrecedent | null;
  onClose: () => void;
  onApplyHypothesis?: (precedent: MemoryPrecedent) => void;
}

export const PrecedentDetailModal: React.FC<PrecedentDetailModalProps> = ({
  precedent,
  onClose,
  onApplyHypothesis,
}) => {
  if (!precedent) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-[#111827] border border-[#00f0ff]/40 rounded-xl shadow-[0_0_30px_rgba(0,240,255,0.25)] flex flex-col overflow-hidden">
        {/* Top Header */}
        <div className="flex items-center justify-between p-4 bg-[#0b0e13] border-b border-[#3b494b]/40">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-[#00f0ff] text-[22px]">
              verified
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[16px] font-bold text-[#dbfcff]">
                  {precedent.id}
                </span>
                <span className="px-2 py-0.5 rounded bg-[#181c21] text-[11px] font-mono text-[#7bd0ff] border border-[#3b494b]/40">
                  {precedent.domain}
                </span>
                <span className="text-[11px] font-mono text-[#b9cacb]">
                  {precedent.date}
                </span>
              </div>
              <h2 className="text-[16px] font-semibold text-[#e0e2ea] mt-0.5">
                {precedent.title}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 rounded bg-[#7fecde]/20 text-[#7fecde] text-[11px] font-mono font-bold border border-[#7fecde]/40">
              RECALL UTILITY: {precedent.utilityScore}%
            </span>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded hover:bg-[#272a30] text-[#b9cacb] hover:text-[#e0e2ea] flex items-center justify-center transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto flex-1 space-y-4">
          {/* Key Metric Strip */}
          <div className="grid grid-cols-4 gap-2 bg-[#181c21] p-3 rounded-lg border border-[#3b494b]/30 text-center font-mono">
            <div>
              <span className="text-[10px] text-[#b9cacb] block uppercase">Similarity Match</span>
              <span className="text-[15px] font-bold text-[#00f0ff]">{precedent.similarityScore}%</span>
            </div>
            <div>
              <span className="text-[10px] text-[#b9cacb] block uppercase">Historical MTTR</span>
              <span className="text-[15px] font-bold text-[#7fecde]">{precedent.mttrMinutes} min</span>
            </div>
            <div>
              <span className="text-[10px] text-[#b9cacb] block uppercase">Times Recalled</span>
              <span className="text-[15px] font-bold text-[#e0e2ea]">{precedent.recallsCount}x</span>
            </div>
            <div>
              <span className="text-[10px] text-[#b9cacb] block uppercase">Root Category</span>
              <span className="text-[12px] font-medium text-[#7bd0ff] truncate block mt-0.5">{precedent.rootCause}</span>
            </div>
          </div>

          {/* Incident Anatomy */}
          <div className="space-y-3">
            <div className="bg-[#1d2025] p-3.5 rounded-lg border border-[#3b494b]/30">
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="material-symbols-outlined text-[#ffb4ab] text-[16px]">crisis_alert</span>
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#ffb4ab]">
                  What Happened
                </span>
              </div>
              <p className="text-[13px] text-[#e0e2ea] leading-relaxed">
                {precedent.whatHappened}
              </p>
            </div>

            <div className="bg-[#1d2025] p-3.5 rounded-lg border border-[#3b494b]/30">
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="material-symbols-outlined text-[#7bd0ff] text-[16px]">troubleshoot</span>
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#7bd0ff]">
                  Agent Investigation &amp; Telemetry Correlation
                </span>
              </div>
              <p className="text-[13px] text-[#e0e2ea] leading-relaxed">
                {precedent.agentInvestigation}
              </p>
            </div>

            <div className="bg-[#1d2025] p-3.5 rounded-lg border border-[#3b494b]/30">
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="material-symbols-outlined text-[#7fecde] text-[16px]">bolt</span>
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#7fecde]">
                  Executed Response Runbook
                </span>
              </div>
              <p className="text-[13px] text-[#e0e2ea] leading-relaxed">
                {precedent.executedResponse}
              </p>
            </div>

            <div className="bg-[#1d2025] p-3.5 rounded-lg border border-[#3b494b]/30">
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="material-symbols-outlined text-[#7fecde] text-[16px]">check_circle</span>
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#7fecde]">
                  Verified Outcome &amp; Impact
                </span>
              </div>
              <p className="text-[13px] text-[#e0e2ea] leading-relaxed">
                {precedent.verifiedOutcome}
              </p>
            </div>

            {/* Retained Experience Rule Highlight */}
            <div className="bg-[#00f0ff]/10 p-4 rounded-lg border border-[#00f0ff]/40 shadow-inner">
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">psychology</span>
                <span className="text-[11px] font-mono font-bold uppercase tracking-widest text-[#00f0ff]">
                  Retained Experience Rule for Future Responders
                </span>
              </div>
              <p className="text-[14px] text-[#dbfcff] font-medium italic leading-relaxed">
                “{precedent.retainedExperience}”
              </p>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-[#0b0e13] border-t border-[#3b494b]/40 flex items-center justify-between">
          <span className="text-[11px] font-mono text-[#b9cacb]">
            Grounding Anchor: <span className="text-[#dbfcff]">{precedent.id}</span> ➔ Target <span className="text-[#00f0ff]">INC-2048</span>
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded bg-[#272a30] hover:bg-[#32353b] text-[12px] font-mono text-[#e0e2ea] transition-colors"
            >
              Close Precedent
            </button>
            {onApplyHypothesis && (
              <button
                onClick={() => {
                  onApplyHypothesis(precedent);
                  onClose();
                }}
                className="px-4 py-1.5 rounded bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-bold text-[12px] font-mono transition-all shadow-[0_0_12px_rgba(0,240,255,0.3)] flex items-center gap-1.5"
              >
                <span className="material-symbols-outlined text-[16px]">link</span>
                <span>Apply Grounded Precedent to INC-2048</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
