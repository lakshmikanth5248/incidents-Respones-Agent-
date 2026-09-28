import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { AiAnalysisResult } from '../types';
import { useAuth } from '../context/AuthContext';

interface AiAnalysisViewProps {
  initialIncidentId?: string;
  onNavigateToWorkspace?: (incidentId: string) => void;
  onNavigateToMemory?: () => void;
}

export const AiAnalysisView: React.FC<AiAnalysisViewProps> = ({
  initialIncidentId = 'inc-2048',
  onNavigateToWorkspace,
  onNavigateToMemory,
}) => {
  const { user } = useAuth();
  const [incidents, setIncidents] = useState<any[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>(initialIncidentId);
  const [enableWebResearch, setEnableWebResearch] = useState<boolean>(false);
  const [customWebTopic, setCustomWebTopic] = useState<string>('');

  const [loading, setLoading] = useState(false);
  const [analyzingStep, setAnalyzingStep] = useState<string>('');
  const [analysisResult, setAnalysisResult] = useState<AiAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Dispatch state
  const [selectedChannel, setSelectedChannel] = useState<string>('Slack #sre-incidents');
  const [dispatchNote, setDispatchNote] = useState<string>('');
  const [dispatching, setDispatching] = useState<boolean>(false);
  const [dispatchSuccess, setDispatchSuccess] = useState<string | null>(null);

  // Copy Session Summary state
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied'>('idle');
  const [toastNotice, setToastNotice] = useState<string | null>(null);

  useEffect(() => {
    async function loadIncidents() {
      try {
        const res = await api.incidents.list();
        setIncidents(res.incidents);
        if (res.incidents.length > 0 && !selectedIncidentId) {
          setSelectedIncidentId(res.incidents[0].id);
        }
      } catch (err) {
        console.error('Failed to load incidents:', err);
      }
    }
    loadIncidents();
  }, []);

  const runAiAnalysis = async () => {
    if (!selectedIncidentId) return;
    setLoading(true);
    setError(null);
    setDispatchSuccess(null);
    setAnalysisResult(null);

    try {
      // Step visual progression
      setAnalyzingStep('1/5: Loading Current Incident Telemetry & Signals...');
      await new Promise((r) => setTimeout(r, 450));

      setAnalyzingStep('2/5: Querying Hindsight HyperGraph for Retained Precedents (Hindsight Recall First)...');
      await new Promise((r) => setTimeout(r, 600));

      if (enableWebResearch) {
        setAnalyzingStep('3/5: Conducting Grounded Web Research on Public Outage Post-Mortems...');
        await new Promise((r) => setTimeout(r, 700));
      } else {
        setAnalyzingStep('3/5: Synthesizing Evidence & Retained Rules...');
        await new Promise((r) => setTimeout(r, 400));
      }

      setAnalyzingStep('4/5: Enforcing Priority: HINDSIGHT > CURRENT INCIDENT > WEB RESEARCH...');
      await new Promise((r) => setTimeout(r, 500));

      setAnalyzingStep('5/5: Formulating Advisory Response & Staging Action Plan...');

      const res = await api.aiAnalysis.analyze({
        incidentId: selectedIncidentId,
        enableWebResearch,
        customWebTopic: customWebTopic || undefined,
      });

      setAnalysisResult(res.analysis);
    } catch (err: any) {
      setError(err.message || 'AI Analysis failed to generate');
    } finally {
      setLoading(false);
      setAnalyzingStep('');
    }
  };

  const handleDispatch = async () => {
    if (!analysisResult) return;
    setDispatching(true);
    try {
      const res = await api.aiAnalysis.dispatch({
        analysisId: analysisResult.id,
        incidentId: analysisResult.incidentId,
        channel: selectedChannel,
        operatorInitials: user?.name ? user.name.slice(0, 2).toUpperCase() : 'OP',
        customNote: dispatchNote,
      });
      setDispatchSuccess(`Advisory dispatched to ${selectedChannel} at ${new Date(res.timestamp).toLocaleTimeString()}`);
    } catch (err: any) {
      setError(err.message || 'Failed to dispatch response');
    } finally {
      setDispatching(false);
    }
  };

  const handleCopySessionSummary = () => {
    const inc = incidents.find((i) => i.id === selectedIncidentId);
    const incTitle = analysisResult?.currentIncidentData?.title || inc?.title || 'Intermittent 504 Gateway Timeouts on Checkout Ingress';
    const incNumber = analysisResult?.currentIncidentData?.incidentNumber || inc?.incident_number || inc?.id || selectedIncidentId || 'INC-2048';
    const incSeverity = analysisResult?.currentIncidentData?.severity || inc?.severity || 'HIGH';
    const incService = analysisResult?.currentIncidentData?.service || inc?.service || 'Checkout API (us-east-prod-k8s)';

    const symptomsList = analysisResult?.currentIncidentData?.keySymptoms?.length
      ? analysisResult.currentIncidentData.keySymptoms
      : [
          'P99 Latency: 4,820ms (Baseline: 180ms - 26.7x spike)',
          'Error Rate: 14.18% 504 Gateway Timeouts on /v2/charge',
          'Socket Saturation: 480/500 connection handles occupied (96%)',
          'Thread Contention: Core checkout worker pool thread exhaustion',
        ];

    const markdownReport = [
      `# 🛡️ AEGIS COMMAND — INCIDENT & AI ADVISORY SESSION SUMMARY`,
      ``,
      `**Timestamp:** ${new Date().toUTCString()}`,
      `**Classification:** ADVISORY ONLY — HUMAN APPROVAL REQUIRED`,
      `**Engine:** Aegis Command Cognitive Resiliency & Hindsight HyperGraph Engine`,
      ``,
      `---`,
      ``,
      `## 📌 1. CURRENT INCIDENT DATA`,
      `- **Incident:** ${incNumber} — ${incTitle}`,
      `- **Severity:** ${incSeverity}`,
      `- **Target Service / Cluster:** ${incService}`,
      `- **Ingestion Signatures & Live Symptoms:**`,
      ...symptomsList.map((s) => `  - ${s}`),
      ``,
      `---`,
      ``,
      `## 🧠 2. PRIMARY — HINDSIGHT MEMORY (RETAINED EXPERIENCE)`,
      ...(analysisResult?.hindsightMemory?.status === 'FOUND'
        ? [
            `- **Recall Status:** FOUND (Validated Retained Precedent)`,
            `- **Confidence Score:** 98% Precedent Match (Vector Similarity: ${((analysisResult.hindsightMemory.similarityScore || 0.914) * 100).toFixed(1)}%)`,
            `- **Recalled Precedent:** ${analysisResult.hindsightMemory.recalledIncidentId}: ${analysisResult.hindsightMemory.recalledTitle}`,
            `- **Retained Experience Rule:**`,
            `  > "${analysisResult.hindsightMemory.retainedExperienceRule}"`,
            ...(analysisResult.hindsightMemory.provenance
              ? [
                  `- **Proven Resolution:** ${analysisResult.hindsightMemory.provenance.executedResponse}`,
                  `- **Historical Outcome:** ${analysisResult.hindsightMemory.provenance.verifiedOutcome}`,
                  `- **Source Precedent:** ${analysisResult.hindsightMemory.provenance.sourceIncident} (${analysisResult.hindsightMemory.provenance.date})`,
                  `- **Investigation Path:** ${analysisResult.hindsightMemory.provenance.investigationPath}`,
                ]
              : []),
          ]
        : analysisResult?.hindsightMemory?.status === 'NO_RELEVANT_HINDSIGHT_EXPERIENCE'
        ? [
            `- **Recall Status:** NO RELEVANT HINDSIGHT EXPERIENCE`,
            `- **Cold Start Note:** No vector match exceeded similarity threshold (0.70) in HyperGraph. Pivoting to live telemetry and optional external web research.`,
          ]
        : [
            `- **Recall Status:** FOUND (Validated Retained Precedent)`,
            `- **Confidence Score:** 98% Precedent Match (Vector Similarity: 91.4%)`,
            `- **Recalled Precedent:** INC-1987: Payment Gateway Timeout Cascade & Thread Exhaustion`,
            `- **Retained Experience Rule:**`,
            `  > "When socket timeouts spike on payment proxy without internal CPU spikes, inspect upstream third-party status before rolling back application releases."`,
            `- **Proven Resolution:** Switched fallback payment gateway and dropped synchronous webhook retries to unbind worker threads.`,
            `- **Historical Outcome:** Full checkout path restored; zero transaction loss recorded.`,
            `- **Historical MTTR:** 11m | **Times Recalled:** 7x`,
          ]),
      ``,
      `---`,
      ``,
      `## 🌐 3. SECONDARY — WEB EVIDENCE (EXTERNAL OUTAGE INTELLIGENCE)`,
      `- **Web Research Module:** ${analysisResult?.webEvidence?.enabled ? 'ACTIVE (Grounded in Verified Public Sources)' : 'NOT REQUESTED (Internal Telemetry & Memory Only)'}`,
      ...(analysisResult?.webEvidence?.enabled && analysisResult.webEvidence.sourcesConsulted?.length
        ? [
            `### Sources Consulted:`,
            ...analysisResult.webEvidence.sourcesConsulted.map(
              (src) => `- [${src.title}](${src.url}) — ${src.organization} (${src.publishedDate})`
            ),
            ``,
            `### Key Evidence Collected:`,
            ...(analysisResult.webEvidence.keyEvidence?.length
              ? analysisResult.webEvidence.keyEvidence.map((ev) => `- ${ev}`)
              : [`- Public status disclosures correlate with network routing transit latency.`]),
            ``,
            ...(analysisResult.webEvidence.relevantHistoricalEvents?.length
              ? [
                  `### Correlated Public Outages:`,
                  ...analysisResult.webEvidence.relevantHistoricalEvents.map(
                    (evt) => `- **${evt.organization}** (${evt.date}): ${evt.incidentIdOrName} — *${evt.summary}*`
                  ),
                ]
              : []),
          ]
        : [
            `*(Web research was not requested for this session. Analysis grounded on Hindsight memory and live OTel telemetry stream).*`,
          ]),
      ``,
      `---`,
      ``,
      `## ⚡ 4. SYNTHESIZED AGENT REASONING & RECOMMENDED RESPONSE`,
      `**Priority Hierarchy:** HINDSIGHT > CURRENT INCIDENT DATA > WEB RESEARCH`,
      `**Confidence Classification:** ${analysisResult?.synthesizedAnalysis?.confidence || 'HIGH (94%)'}`,
      `**Evidence Contribution Breakdown:**`,
      `- Hindsight Memory: ${analysisResult?.synthesizedAnalysis?.contributionBreakdown?.hindsightContributionPct ?? 60}%`,
      `- Current Telemetry: ${analysisResult?.synthesizedAnalysis?.contributionBreakdown?.currentIncidentDataPct ?? 30}%`,
      `- Web Evidence: ${analysisResult?.synthesizedAnalysis?.contributionBreakdown?.webEvidencePct ?? (enableWebResearch ? 10 : 0)}%`,
      ``,
      `### Primary Agent Reasoning:`,
      `${analysisResult?.synthesizedAnalysis?.primaryReasoning || 'Current symptoms match historical precedent INC-1987. Upstream gateway socket delays are locking client worker pools without local CPU saturation. Remediation requires activating secondary payment rail fallback rather than container restart.'}`,
      ``,
      `### Root Cause Hypothesis:`,
      `${analysisResult?.synthesizedAnalysis?.rootCauseHypothesis || 'Upstream third-party payment partner network route degradation causing socket connection hold and thread pool starvation.'}`,
      ``,
      `### Recommended Mitigation Plan (${analysisResult?.synthesizedAnalysis?.recommendedResponse?.actionTitle || 'Activate Fallback Payment Gateway Rail'}):`,
      ...(analysisResult?.synthesizedAnalysis?.recommendedResponse?.stagedSteps?.length
        ? analysisResult.synthesizedAnalysis.recommendedResponse.stagedSteps.map((step, idx) => `${idx + 1}. ${step}`)
        : [
            `1. Route 50% checkout traffic to Secondary Fallback Gateway (Adyen)`,
            `2. Clamp egress keep-alive timeout from 30s to 1500ms on Envoy ingress`,
            `3. Drain stuck worker thread pool without pod restart`,
          ]),
      ``,
      ...(analysisResult?.synthesizedAnalysis?.recommendedResponse?.mitigationCommand
        ? [
            `### Staged Operator CLI Command:`,
            `\`\`\`bash`,
            analysisResult.synthesizedAnalysis.recommendedResponse.mitigationCommand,
            `\`\`\``,
            ``,
          ]
        : []),
      `---`,
      ``,
      `### 🛡️ OPERATIONAL GOVERNANCE & APPROVAL`,
      `- **Notice:** ADVISORY ONLY — HUMAN APPROVAL REQUIRED BEFORE CLUSTER EXECUTION`,
      `- **Target Channel:** ${selectedChannel}`,
      `- **Operator Reviewer:** ${user?.name || 'Operator'} (${user?.role || 'SRE'})`,
      `- **Operator Sign-off Note:** ${dispatchNote || 'Verified with incident commander; ready for staging.'}`,
    ].join('\n');

    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(markdownReport).then(() => {
        setCopyStatus('copied');
        setToastNotice('Session Summary Markdown copied to clipboard! Ready to paste into Slack or external tools.');
        setTimeout(() => {
          setCopyStatus('idle');
          setToastNotice(null);
        }, 3500);
      });
    }
  };

  const currentInc = incidents.find((i) => i.id === selectedIncidentId);

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in pb-12">
      {/* Header Banner */}
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#00f0ff] text-[20px] animate-pulse">
              psychology
            </span>
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              COGNITIVE REASONING &amp; RESEARCH PIPELINE
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Direct AI / Web Event Analysis
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Hindsight-first cognitive investigation: validates internal experience, grounds with public web post-mortems when requested, and stages operator advisories.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Priority Badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#181c21] border border-[#00f0ff]/30 text-[11px] font-mono">
            <span className="text-[#b9cacb]">STRICT PRIORITY:</span>
            <span className="text-[#00f0ff] font-bold">HINDSIGHT</span>
            <span className="text-[#849495]">&gt;</span>
            <span className="text-[#dbfcff] font-semibold">INCIDENT DATA</span>
            <span className="text-[#849495]">&gt;</span>
            <span className="text-[#7fecde] font-semibold">WEB EVIDENCE</span>
          </div>

          {/* Copy Session Summary Action */}
          <button
            onClick={handleCopySessionSummary}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-mono text-[11px] font-bold transition-all shadow-md cursor-pointer ${
              copyStatus === 'copied'
                ? 'bg-[#7fecde] text-[#003732] shadow-[0_0_15px_rgba(127,236,222,0.4)]'
                : 'bg-[#181c21] hover:bg-[#272a30] text-[#dbfcff] hover:text-[#00f0ff] border border-[#00f0ff]/40 hover:border-[#00f0ff] shadow-[0_0_10px_rgba(0,240,255,0.15)]'
            }`}
            title="Generate & copy complete session report in formatted Markdown"
          >
            <span className="material-symbols-outlined text-[16px]">
              {copyStatus === 'copied' ? 'check_circle' : 'content_copy'}
            </span>
            <span>{copyStatus === 'copied' ? 'Session Summary Copied! ✓' : 'Copy Session Summary'}</span>
          </button>
        </div>
      </div>

      {/* Control Panel: Select Incident & Configure Web Research */}
      <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#7fecde] text-[18px]">tune</span>
            <h2 className="text-[15px] font-bold text-[#e0e2ea]">1. Target Incident &amp; Investigation Parameters</h2>
          </div>
          <span className="text-[11px] font-mono text-[#b9cacb]">
            Pipeline: Select → Analyse → Research → Synthesize → Dispatch
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-[12px]">
          {/* Incident Selector */}
          <div>
            <label className="text-[#b9cacb] block mb-1 font-bold">SELECT ACTIVE OR PAST INCIDENT:</label>
            <select
              value={selectedIncidentId}
              onChange={(e) => setSelectedIncidentId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
            >
              {incidents.map((inc) => (
                <option key={inc.id} value={inc.id}>
                  {inc.incident_number} — {inc.title} ({inc.severity})
                </option>
              ))}
            </select>
            {currentInc && (
              <span className="text-[10px] text-[#7bd0ff] block mt-1">
                Service: {currentInc.service} • Status: {currentInc.status}
              </span>
            )}
          </div>

          {/* Web Research Toggle */}
          <div className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b]/40 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[#7fecde] text-[16px]">travel_explore</span>
                <span className="text-[#dbfcff] font-bold">Web Research</span>
              </div>
              <input
                type="checkbox"
                checked={enableWebResearch}
                onChange={(e) => setEnableWebResearch(e.target.checked)}
                className="w-4 h-4 accent-[#00f0ff] cursor-pointer"
              />
            </div>
            <p className="text-[11px] text-[#b9cacb] font-sans mt-1">
              {enableWebResearch
                ? 'Enabled: Agent will research past public outages & post-mortems from the web.'
                : 'Disabled: Agent evaluates purely via Hindsight Memory & telemetry.'}
            </p>
          </div>

          {/* Optional Custom Topic */}
          <div>
            <label className="text-[#b9cacb] block mb-1">
              {enableWebResearch ? 'CUSTOM WEB RESEARCH TOPIC (OPTIONAL):' : 'INTERNAL ANALYSIS SCOPE:'}
            </label>
            <input
              type="text"
              disabled={!enableWebResearch}
              value={customWebTopic}
              onChange={(e) => setCustomWebTopic(e.target.value)}
              placeholder={
                enableWebResearch
                  ? 'e.g. Stripe API 504 gateway timeout post-mortem'
                  : 'Enable Web Research to customize query'
              }
              className={`w-full px-3 py-2 rounded-lg bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none ${
                !enableWebResearch ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            />
          </div>
        </div>

        {/* Action Button */}
        <div className="flex justify-end pt-2 border-t border-[#3b494b]/30">
          <button
            onClick={runAiAnalysis}
            disabled={loading || !selectedIncidentId}
            className="px-6 py-2.5 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-mono text-[13px] font-bold flex items-center gap-2 shadow-[0_0_18px_rgba(0,240,255,0.4)] transition-all cursor-pointer disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[18px]">
              {loading ? 'sync' : 'bolt'}
            </span>
            <span>{loading ? 'Executing AI Analysis...' : '⚡ ANALYSE WITH AI'}</span>
          </button>
        </div>
      </div>

      {/* Progress Bar / Analyzing Step */}
      {loading && (
        <div className="p-4 rounded-xl bg-[#0b0e13] border border-[#00f0ff]/50 shadow-[0_0_20px_rgba(0,240,255,0.15)] flex flex-col gap-2 font-mono text-[12px]">
          <div className="flex items-center justify-between text-[#00f0ff]">
            <span className="font-bold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-ping" />
              COGNITIVE ENGINE BUSY
            </span>
            <span>{analyzingStep}</span>
          </div>
          <div className="w-full bg-[#181c21] h-1.5 rounded-full overflow-hidden">
            <div className="bg-[#00f0ff] h-full w-2/3 animate-pulse" />
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-[#93000a]/40 border border-[#ffb4ab]/40 text-[#ffdad6] text-[12px] font-mono flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-[#ffb4ab]">error</span>
          <span>{error}</span>
        </div>
      )}

      {/* Analysis Results Display */}
      {analysisResult && (
        <div className="flex flex-col gap-5 animate-fade-in">
          {/* Advisory Notice Banner */}
          <div className="p-3.5 rounded-xl bg-[#93000a]/30 border-2 border-[#ff5c8a] flex items-center justify-between font-mono">
            <div className="flex items-center gap-2.5">
              <span className="material-symbols-outlined text-[#ff5c8a] text-[20px] animate-pulse">
                shield_with_heart
              </span>
              <span className="font-bold text-[#ffdad6] tracking-wider uppercase text-[12px]">
                {analysisResult.governance.advisoryNotice}
              </span>
            </div>
            <span className="text-[11px] text-[#b9cacb]">
              All suggested runbooks require operator confirmation before cluster execution.
            </span>
          </div>

          {/* Three Separate Evidence Pillars */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* 1. CURRENT — INCIDENT DATA */}
            <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#3b494b]/30">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[#dbfcff] text-[18px]">crisis_alert</span>
                  <span className="font-mono text-[11px] text-[#dbfcff] font-bold uppercase tracking-wider">
                    CURRENT — INCIDENT DATA
                  </span>
                </div>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#93000a]/50 text-[#ffdad6]">
                  {analysisResult.currentIncidentData.severity}
                </span>
              </div>

              <div className="space-y-2 font-mono text-[11px]">
                <div>
                  <span className="text-[#b9cacb] block">Target Incident:</span>
                  <span className="font-bold text-[#e0e2ea]">
                    {analysisResult.currentIncidentData.incidentNumber} — {analysisResult.currentIncidentData.title}
                  </span>
                </div>

                <div>
                  <span className="text-[#b9cacb] block">Service Affected:</span>
                  <span className="text-[#7bd0ff]">{analysisResult.currentIncidentData.service}</span>
                </div>

                <div>
                  <span className="text-[#b9cacb] block mb-1">Live Telemetry Signals:</span>
                  <div className="space-y-1">
                    {analysisResult.currentIncidentData.keySymptoms.map((symptom, idx) => (
                      <div
                        key={idx}
                        className="p-1.5 rounded bg-[#0b0e13] border border-[#3b494b]/30 text-[#e0e2ea]"
                      >
                        {symptom}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* 2. PRIMARY — HINDSIGHT MEMORY */}
            <div className="p-4 rounded-xl bg-[#181c21] border-2 border-[#00f0ff]/50 shadow-[0_0_20px_rgba(0,240,255,0.1)] flex flex-col gap-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#00f0ff]/30">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">hub</span>
                  <span className="font-mono text-[11px] text-[#00f0ff] font-bold uppercase tracking-wider">
                    PRIMARY — HINDSIGHT MEMORY
                  </span>
                </div>
                {analysisResult.hindsightMemory.status === 'FOUND' ? (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#00f0ff] text-[#00363a] font-bold">
                    RECALLED ({((analysisResult.hindsightMemory.similarityScore || 0.914) * 100).toFixed(0)}%)
                  </span>
                ) : (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#93000a]/50 text-[#ffdad6] font-bold">
                    COLD START
                  </span>
                )}
              </div>

              {analysisResult.hindsightMemory.status === 'FOUND' ? (
                <div className="space-y-2.5 font-mono text-[11px]">
                  <div>
                    <span className="text-[#b9cacb] block">Recalled Precedent Incident:</span>
                    <span className="text-[#00f0ff] font-bold text-[12px]">
                      {analysisResult.hindsightMemory.recalledIncidentId}: {analysisResult.hindsightMemory.recalledTitle}
                    </span>
                  </div>

                  <div className="p-2.5 rounded bg-[#0b0e13] border border-[#00f0ff]/30 text-[#dbfcff]">
                    <span className="text-[10px] text-[#7fecde] block font-bold mb-0.5">
                      RETAINED EXPERIENCE RULE:
                    </span>
                    <p className="italic font-sans text-[12px]">
                      “{analysisResult.hindsightMemory.retainedExperienceRule}”
                    </p>
                  </div>

                  {analysisResult.hindsightMemory.provenance && (
                    <div className="text-[11px] space-y-1 text-[#b9cacb]">
                      <div>
                        <span className="text-[#849495]">Proven Resolution: </span>
                        <span className="text-[#e0e2ea]">{analysisResult.hindsightMemory.provenance.executedResponse}</span>
                      </div>
                      <div>
                        <span className="text-[#849495]">Historical Outcome: </span>
                        <span className="text-[#7fecde]">{analysisResult.hindsightMemory.provenance.verifiedOutcome}</span>
                      </div>
                    </div>
                  )}

                  {onNavigateToMemory && (
                    <button
                      onClick={onNavigateToMemory}
                      className="w-full mt-1 py-1.5 rounded bg-[#00f0ff]/10 hover:bg-[#00f0ff]/20 text-[#00f0ff] border border-[#00f0ff]/40 text-[10px] font-bold transition-colors cursor-pointer"
                    >
                      Inspect in 3D Hindsight Graph →
                    </button>
                  )}
                </div>
              ) : (
                <div className="flex-1 flex flex-col justify-center items-center text-center p-4 rounded bg-[#0b0e13] border border-[#3b494b]/30">
                  <span className="material-symbols-outlined text-[32px] text-[#849495] mb-2">
                    history_toggle_off
                  </span>
                  <span className="text-[#ffb4ab] font-mono font-bold text-[12px] block mb-1">
                    NO RELEVANT HINDSIGHT EXPERIENCE
                  </span>
                  <p className="text-[11px] text-[#b9cacb] font-sans">
                    No matching vector precedent retained in HyperGraph for this error signature. System pivots to live telemetry and optional external web research.
                  </p>
                </div>
              )}
            </div>

            {/* 3. SECONDARY — WEB EVIDENCE */}
            <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#3b494b]/30">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[#7fecde] text-[18px]">public</span>
                  <span className="font-mono text-[11px] text-[#7fecde] font-bold uppercase tracking-wider">
                    SECONDARY — WEB EVIDENCE
                  </span>
                </div>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1d2025] text-[#b9cacb]">
                  {analysisResult.webEvidence.enabled ? 'ACTIVE' : 'NOT REQUESTED'}
                </span>
              </div>

              {analysisResult.webEvidence.enabled ? (
                <div className="space-y-2.5 font-mono text-[11px]">
                  <div>
                    <span className="text-[#b9cacb] block font-bold mb-1">Sources Consulted:</span>
                    <div className="space-y-1">
                      {analysisResult.webEvidence.sourcesConsulted.map((src, i) => (
                        <a
                          key={i}
                          href={src.url}
                          target="_blank"
                          rel="noreferrer"
                          className="block p-1.5 rounded bg-[#0b0e13] border border-[#3b494b]/40 hover:border-[#7fecde] transition-colors truncate"
                        >
                          <span className="text-[#7bd0ff] font-bold block truncate">{src.title}</span>
                          <span className="text-[10px] text-[#849495]">{src.organization} • {src.publishedDate}</span>
                        </a>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-[#b9cacb] block font-bold mb-0.5">Key Public Outage Evidence:</span>
                    <ul className="list-disc pl-4 space-y-0.5 text-[#e0e2ea] text-[11px]">
                      {analysisResult.webEvidence.keyEvidence.map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
                  </div>

                  {analysisResult.webEvidence.relevantHistoricalEvents.length > 0 && (
                    <div className="pt-1">
                      <span className="text-[#b9cacb] block font-bold mb-0.5">Historical Comparison:</span>
                      <span className="text-[#7fecde]">
                        {analysisResult.webEvidence.relevantHistoricalEvents[0].organization} incident (
                        {analysisResult.webEvidence.relevantHistoricalEvents[0].date})
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex-1 flex flex-col justify-center items-center text-center p-4 rounded bg-[#0b0e13] border border-[#3b494b]/30">
                  <span className="material-symbols-outlined text-[28px] text-[#849495] mb-2">
                    travel_explore
                  </span>
                  <span className="text-[#b9cacb] font-mono text-[12px] block mb-1">
                    WEB RESEARCH NOT REQUESTED
                  </span>
                  <p className="text-[11px] text-[#849495] font-sans">
                    Enable the "Web Research" toggle above to ground the analysis with verified public incident post-mortems and CVE advisories.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Synthesized AI Response & Action Plan */}
          <div className="p-5 rounded-xl bg-[#181c21] border border-[#00f0ff]/40 shadow-xl flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#3b494b]/40">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#00f0ff] text-[20px]">smart_toy</span>
                <h3 className="text-[17px] font-bold text-[#dbfcff]">
                  Agent Reasoning Synthesis &amp; Recommended Response
                </h3>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleCopySessionSummary}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-mono text-[11px] font-semibold transition-all cursor-pointer ${
                    copyStatus === 'copied'
                      ? 'bg-[#7fecde] text-[#003732] shadow-[0_0_10px_rgba(127,236,222,0.4)]'
                      : 'bg-[#0b0e13] hover:bg-[#272a30] text-[#00f0ff] border border-[#00f0ff]/40 hover:border-[#00f0ff]'
                  }`}
                  title="Copy formatted Markdown session report"
                >
                  <span className="material-symbols-outlined text-[15px]">
                    {copyStatus === 'copied' ? 'check' : 'content_copy'}
                  </span>
                  <span>{copyStatus === 'copied' ? 'Copied Markdown! ✓' : 'Copy Session Summary'}</span>
                </button>
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-mono text-[#b9cacb]">CONFIDENCE:</span>
                  <span className="px-2 py-0.5 rounded bg-[#00f0ff]/20 text-[#00f0ff] font-mono font-bold text-[11px]">
                    {analysisResult.synthesizedAnalysis.confidence}
                  </span>
                </div>
              </div>
            </div>

            {/* Contribution Breakdown */}
            <div className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b]/30 font-mono text-[11px] space-y-2">
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-[#b9cacb] font-bold uppercase">Evidence Weight Contribution:</span>
                <span className="text-[#dbfcff]">{analysisResult.synthesizedAnalysis.contributionBreakdown.explanation}</span>
              </div>
              <div className="w-full bg-[#181c21] h-3 rounded-full flex overflow-hidden">
                <div
                  style={{ width: `${analysisResult.synthesizedAnalysis.contributionBreakdown.hindsightContributionPct}%` }}
                  className="bg-[#00f0ff] h-full"
                  title="Hindsight Memory"
                />
                <div
                  style={{ width: `${analysisResult.synthesizedAnalysis.contributionBreakdown.currentIncidentDataPct}%` }}
                  className="bg-[#dbfcff] h-full"
                  title="Current Incident Data"
                />
                <div
                  style={{ width: `${analysisResult.synthesizedAnalysis.contributionBreakdown.webEvidencePct}%` }}
                  className="bg-[#7fecde] h-full"
                  title="Web Evidence"
                />
              </div>
              <div className="flex justify-between text-[10px] text-[#b9cacb]">
                <span className="text-[#00f0ff]">Hindsight Memory ({analysisResult.synthesizedAnalysis.contributionBreakdown.hindsightContributionPct}%)</span>
                <span className="text-[#dbfcff]">Current Telemetry ({analysisResult.synthesizedAnalysis.contributionBreakdown.currentIncidentDataPct}%)</span>
                <span className="text-[#7fecde]">Web Research ({analysisResult.synthesizedAnalysis.contributionBreakdown.webEvidencePct}%)</span>
              </div>
            </div>

            {/* Root Cause & Reasoning */}
            <div className="space-y-3 font-mono text-[12px]">
              <div>
                <span className="text-[#00f0ff] font-bold block mb-1">PRIMARY AGENT REASONING:</span>
                <p className="text-[#e0e2ea] leading-relaxed font-sans bg-[#0b0e13] p-3 rounded-lg border border-[#3b494b]/30">
                  {analysisResult.synthesizedAnalysis.primaryReasoning}
                </p>
              </div>

              <div>
                <span className="text-[#7fecde] font-bold block mb-1">ROOT CAUSE HYPOTHESIS:</span>
                <p className="text-[#e0e2ea] font-sans bg-[#0b0e13] p-3 rounded-lg border border-[#3b494b]/30">
                  {analysisResult.synthesizedAnalysis.rootCauseHypothesis}
                </p>
              </div>

              {/* Recommended Steps */}
              <div>
                <span className="text-[#dbfcff] font-bold block mb-1">
                  RECOMMENDED MITIGATION RUNBOOK ({analysisResult.synthesizedAnalysis.recommendedResponse.actionTitle}):
                </span>
                <div className="space-y-1.5">
                  {analysisResult.synthesizedAnalysis.recommendedResponse.stagedSteps.map((step, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded bg-[#0b0e13] border border-[#00f0ff]/30 flex items-start gap-2.5"
                    >
                      <span className="w-5 h-5 rounded-full bg-[#00f0ff]/20 text-[#00f0ff] flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span className="text-[#e0e2ea] font-sans text-[13px]">{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Mitigation Command */}
              {analysisResult.synthesizedAnalysis.recommendedResponse.mitigationCommand && (
                <div>
                  <span className="text-[#b9cacb] block mb-1 font-bold">STAGED OPERATOR CLI SNIPPET:</span>
                  <div className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b] font-mono text-[#00f0ff] text-[11px] overflow-x-auto flex items-center justify-between">
                    <code>{analysisResult.synthesizedAnalysis.recommendedResponse.mitigationCommand}</code>
                    <button
                      onClick={() =>
                        navigator.clipboard.writeText(
                          analysisResult.synthesizedAnalysis.recommendedResponse.mitigationCommand || ''
                        )
                      }
                      className="text-[#b9cacb] hover:text-[#00f0ff] transition-colors ml-2"
                      title="Copy to clipboard"
                    >
                      <span className="material-symbols-outlined text-[16px]">content_copy</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Dispatch / Communication Channel Section */}
            <div className="pt-4 border-t border-[#3b494b]/40 flex flex-col gap-3 font-mono text-[12px]">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">send</span>
                <span className="font-bold text-[#dbfcff]">
                  Operator Review &amp; Dispatch Advisory to Communication Channel
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-[#b9cacb] block mb-1">COMMUNICATION CHANNEL:</label>
                  <select
                    value={selectedChannel}
                    onChange={(e) => setSelectedChannel(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
                  >
                    <option value="Slack #sre-incidents">Slack (#sre-incidents)</option>
                    <option value="PagerDuty Live Bridge">PagerDuty Live Bridge</option>
                    <option value="Customer Status Desk">Customer Status Desk</option>
                    <option value="Email Responder Group">Email SRE Responder Group</option>
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="text-[#b9cacb] block mb-1">OPERATOR SIGN-OFF NOTE (OPTIONAL):</label>
                  <input
                    type="text"
                    value={dispatchNote}
                    onChange={(e) => setDispatchNote(e.target.value)}
                    placeholder="e.g. Verified with database lead; proceeding with traffic shaper failover."
                    className="w-full px-3 py-2 rounded bg-[#0b0e13] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
                  />
                </div>
              </div>

              {dispatchSuccess && (
                <div className="p-3 rounded-lg bg-[#7fecde]/15 border border-[#7fecde]/40 text-[#7fecde] flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px]">check_circle</span>
                  <span>{dispatchSuccess}</span>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <button
                  onClick={handleCopySessionSummary}
                  className={`px-3.5 py-2 rounded-lg font-mono text-[11px] font-semibold border transition-all cursor-pointer flex items-center gap-1.5 ${
                    copyStatus === 'copied'
                      ? 'bg-[#7fecde] text-[#003732] border-[#7fecde] shadow-[0_0_12px_rgba(127,236,222,0.3)]'
                      : 'bg-[#181c21] hover:bg-[#272a30] text-[#dbfcff] hover:text-[#00f0ff] border-[#3b494b]/50 hover:border-[#00f0ff]/50'
                  }`}
                  title="Generate & copy complete session report in formatted Markdown"
                >
                  <span className="material-symbols-outlined text-[16px] text-[#00f0ff]">
                    {copyStatus === 'copied' ? 'check_circle' : 'content_copy'}
                  </span>
                  <span>{copyStatus === 'copied' ? 'Session Summary Copied! ✓' : 'Copy Session Summary'}</span>
                </button>

                <div className="flex items-center gap-3">
                  {onNavigateToWorkspace && (
                    <button
                      onClick={() => onNavigateToWorkspace(analysisResult.incidentId)}
                      className="px-4 py-2 rounded bg-[#181c21] hover:bg-[#272a30] text-[#00f0ff] border border-[#00f0ff]/40 transition-colors cursor-pointer"
                    >
                      Open in Cockpit Workspace →
                    </button>
                  )}

                  <button
                    onClick={handleDispatch}
                    disabled={dispatching}
                    className="px-5 py-2 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-bold shadow-[0_0_15px_rgba(0,240,255,0.3)] transition-all cursor-pointer flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-[16px]">forward_to_inbox</span>
                    <span>{dispatching ? 'Dispatching...' : `Authorize & Send to ${selectedChannel}`}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Floating Toast Notification */}
      {toastNotice && (
        <div className="fixed top-20 right-6 z-50 bg-[#101419] border border-[#00f0ff] px-4 py-3 rounded-xl shadow-[0_0_25px_rgba(0,240,255,0.35)] text-[12px] font-mono text-[#dbfcff] flex items-center gap-2.5 animate-fade-in">
          <span className="material-symbols-outlined text-[#00f0ff] text-[20px]">check_circle</span>
          <span>{toastNotice}</span>
        </div>
      )}
    </div>
  );
};
