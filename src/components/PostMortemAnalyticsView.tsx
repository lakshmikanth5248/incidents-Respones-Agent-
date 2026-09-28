import React, { useState } from 'react';

export const PostMortemAnalyticsView: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const postMortemMarkdown = `# Post-Mortem Report: INC-2048
## Summary
- **Incident ID**: INC-2048
- **Date**: 2026-09-28
- **Severity**: HIGH (Sev-1)
- **Impacted Service**: Checkout API & Payment Gateway Proxy (/v2/checkout/charge)
- **Blast Radius**: North America Region (iad01)
- **Time to Detect (TTD)**: 1m 07s
- **Precedent Match**: INC-1987 (Payment Gateway Timeout Cascade) - 91.4% Similarity
- **Estimated MTTR**: 14m 20s (Grounded on historical runbook)

## Root Cause
Upstream card processing gateway experienced silent network degradation and read latency spikes exceeding 5000ms. Core checkout pods exhausted internal worker thread pools awaiting socket responses.

## Action Items & Experience Rule Retained
1. [PREVENT] Enforce strict client HTTP read socket timeout clamp of 1500ms on all payment proxy egress routes.
2. [AUTOMATE] Configure dynamic automatic traffic shifting to secondary gateway when 504 error rate exceeds 3% over 60s.
3. [RETAINED RULE]: "When socket timeouts spike on payment proxy without internal CPU spikes, inspect upstream third-party status before rolling back application releases."
`;

  const handleCopy = () => {
    navigator.clipboard.writeText(postMortemMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in">
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">analytics</span>
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              KNOWLEDGE SYNTHESIS &amp; MTTR ANALYTICS
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Analytics &amp; Automated Post-Mortem
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Continuous extraction of durable systemic lessons and MTTR benchmark comparisons.
          </p>
        </div>

        <button
          onClick={handleCopy}
          className="px-4 py-2 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-mono text-[12px] font-bold flex items-center gap-1.5 shadow-[0_0_12px_rgba(0,240,255,0.3)] transition-all cursor-pointer"
        >
          <span className="material-symbols-outlined text-[16px]">content_copy</span>
          <span>{copied ? 'Copied Markdown ✓' : 'Export Post-Mortem (Markdown)'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono">
        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <span className="text-[10px] text-[#b9cacb] uppercase">Mean Time to Resolve (MTTR)</span>
          <span className="text-[28px] font-bold text-[#7fecde]">14.2 min</span>
          <span className="text-[11px] text-[#7bd0ff]">Down from 48.0 min (unassisted)</span>
        </div>
        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <span className="text-[10px] text-[#b9cacb] uppercase">Precedent Accuracy Rate</span>
          <span className="text-[28px] font-bold text-[#00f0ff]">94.8%</span>
          <span className="text-[11px] text-[#b9cacb]">Across 14,892 indexed incidents</span>
        </div>
        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <span className="text-[10px] text-[#b9cacb] uppercase">Experience Rules In Force</span>
          <span className="text-[28px] font-bold text-[#dbfcff]">1,280</span>
          <span className="text-[11px] text-[#b9cacb]">Active guardrails guarding deploys</span>
        </div>
      </div>

      {/* Markdown Post-Mortem Preview */}
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 flex flex-col gap-3 shadow-xl">
        <div className="flex items-center justify-between pb-2 border-b border-[#3b494b]/40">
          <span className="font-mono text-[11px] font-bold text-[#00f0ff] uppercase tracking-wider">
            AUTOMATED POST-MORTEM DRAFT (INC-2048)
          </span>
          <span className="text-[11px] font-mono text-[#b9cacb]">Format: GitHub Markdown</span>
        </div>

        <pre className="p-4 rounded-lg bg-[#111827] font-mono text-[12px] text-[#e0e2ea] overflow-x-auto leading-relaxed border border-[#3b494b]/30">
          <code>{postMortemMarkdown}</code>
        </pre>
      </div>
    </div>
  );
};
