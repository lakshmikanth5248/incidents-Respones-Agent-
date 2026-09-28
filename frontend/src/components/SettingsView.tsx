import React, { useState } from 'react';

export const SettingsView: React.FC = () => {
  const [similarityThreshold, setSimilarityThreshold] = useState(0.85);
  const [autoExecuteLocked, setAutoExecuteLocked] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in">
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">tune</span>
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              ENGINE &amp; INTEGRATIONS CONFIGURATION
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Settings &amp; Integrations
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Telemetry sources, safety guardrail boundaries, and HyperGraph vector parameters.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="px-4 py-2 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-mono text-[12px] font-bold flex items-center gap-1.5 shadow-[0_0_12px_rgba(0,240,255,0.3)] transition-all cursor-pointer"
        >
          <span className="material-symbols-outlined text-[16px]">save</span>
          <span>{saved ? 'Settings Saved ✓' : 'Save Configurations'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Guardrail Policy */}
        <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-4">
          <h2 className="text-[16px] font-bold text-[#e0e2ea] flex items-center gap-2">
            <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">security</span>
            <span>Safety Boundaries &amp; Execution Policy</span>
          </h2>

          <div className="space-y-3 font-mono text-[12px]">
            <label className="flex items-center justify-between p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 cursor-pointer">
              <div className="flex flex-col">
                <span className="text-[#e0e2ea] font-bold">Advisory-Only Autonomous Lock</span>
                <span className="text-[11px] text-[#b9cacb]">Mandates human operator sign-off before applying any kubectl / Istio mutations.</span>
              </div>
              <input
                type="checkbox"
                checked={autoExecuteLocked}
                onChange={(e) => setAutoExecuteLocked(e.target.checked)}
                className="w-4 h-4 rounded text-[#00f0ff] bg-[#0b0e13] border-[#3b494b]"
              />
            </label>

            <div className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 space-y-2">
              <div className="flex justify-between">
                <span className="text-[#e0e2ea]">Vector Recall Similarity Threshold:</span>
                <span className="text-[#00f0ff] font-bold">{(similarityThreshold * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="0.98"
                step="0.01"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                className="w-full accent-[#00f0ff] bg-[#0b0e13]"
              />
              <span className="text-[10px] text-[#849495] block">
                Precedents with similarity score below this threshold are marked as "Unvalidated Heuristics".
              </span>
            </div>
          </div>
        </div>

        {/* Telemetry Connectors */}
        <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-4">
          <h2 className="text-[16px] font-bold text-[#e0e2ea] flex items-center gap-2">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">hub</span>
            <span>Connected Telemetry Ingress</span>
          </h2>

          <div className="space-y-2 font-mono text-[11px]">
            <div className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-[#7fecde]" />
                <span className="text-[#e0e2ea] font-bold">OpenTelemetry Collector</span>
              </div>
              <span className="text-[#7fecde]">CONNECTED (grpc://otel-ingest.iad01)</span>
            </div>

            <div className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-[#7fecde]" />
                <span className="text-[#e0e2ea] font-bold">Kubernetes API</span>
              </div>
              <span className="text-[#7fecde]">us-east-prod-k8s (v1.30.2)</span>
            </div>

            <div className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-[#7fecde]" />
                <span className="text-[#e0e2ea] font-bold">PagerDuty Webhook Gateway</span>
              </div>
              <span className="text-[#7fecde]">Active (#sre-oncall-p1)</span>
            </div>

            <div className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-[#7fecde]" />
                <span className="text-[#e0e2ea] font-bold">HyperGraph 1536-dim Vector DB</span>
              </div>
              <span className="text-[#00f0ff]">14,892 Nodes Indexed</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
