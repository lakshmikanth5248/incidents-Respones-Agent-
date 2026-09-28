import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';

interface DemoPresentationViewProps {
  onInvestigateIncident: (id: string) => void;
  onExploreMemory: () => void;
}

export const DemoPresentationView: React.FC<DemoPresentationViewProps> = ({
  onInvestigateIncident,
  onExploreMemory,
}) => {
  const [demoState, setDemoState] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);
  const autoPlayTimerRef = useRef<any>(null);

  const fetchState = async () => {
    try {
      const res = await api.demo.getState();
      setDemoState(res);
    } catch (err) {
      console.error('Failed to get demo state:', err);
    }
  };

  useEffect(() => {
    fetchState();
  }, []);

  // Auto-play loop
  useEffect(() => {
    if (autoPlay) {
      autoPlayTimerRef.current = setInterval(async () => {
        if (!demoState || demoState.currentStep >= 9) {
          setAutoPlay(false);
          return;
        }
        try {
          const res = await api.demo.next();
          setDemoState(res);
          if (res.currentStep >= 9) {
            setAutoPlay(false);
          }
        } catch (err) {
          console.error('Auto-play error:', err);
          setAutoPlay(false);
        }
      }, 3500);
    } else {
      if (autoPlayTimerRef.current) {
        clearInterval(autoPlayTimerRef.current);
        autoPlayTimerRef.current = null;
      }
    }

    return () => {
      if (autoPlayTimerRef.current) {
        clearInterval(autoPlayTimerRef.current);
      }
    };
  }, [autoPlay, demoState]);

  const handleStart = async () => {
    setLoading(true);
    try {
      const res = await api.demo.start();
      setDemoState(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleNext = async () => {
    setLoading(true);
    try {
      const res = await api.demo.next();
      setDemoState(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePrevious = async () => {
    setLoading(true);
    try {
      const res = await api.demo.previous();
      setDemoState(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGoToStep = async (stepNum: number) => {
    setLoading(true);
    try {
      const res = await api.demo.goToStep(stepNum);
      setDemoState(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setAutoPlay(false);
    setLoading(true);
    try {
      const res = await api.demo.reset();
      setDemoState(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    { num: 1, phase: 1, title: '01 INCIDENT A', desc: 'Cold-start outage created without historical memory' },
    { num: 2, phase: 1, title: '02 INVESTIGATE', desc: 'No-memory fallback triggered; first-principles triage' },
    { num: 3, phase: 1, title: '03 RESOLVE', desc: 'SRE mitigates failure via fallback diversion' },
    { num: 4, phase: 2, title: '04 POST-MORTEM', desc: 'Synthesize systemic root cause and impact' },
    { num: 5, phase: 2, title: '05 RETAIN', desc: 'Index durable operational lesson to Hindsight' },
    { num: 6, phase: 3, title: '06 INCIDENT B', desc: 'New outage occurs with alternate phrasing' },
    { num: 7, phase: 3, title: '07 RECALL', desc: 'Hindsight semantic vector search finds Incident A' },
    { num: 8, phase: 3, title: '08 CONTEXT MERGE', desc: 'Recalled experience injected into reasoning before hypothesis' },
    { num: 9, phase: 3, title: '09 RECOMMENDATION', desc: 'Precedent-grounded runbook advisory staged' },
  ];

  const currentStep = demoState?.currentStep || 0;
  const currentIncidentId = currentStep >= 6 ? demoState?.incidentBId : demoState?.incidentAId;

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in pb-12">
      {/* Header */}
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#00f0ff]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#00f0ff] animate-ping" />
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              GUIDED DEMO STORYLINE
            </span>
            <span className="px-2 py-0.5 rounded bg-[#f59e0b]/20 text-[#f59e0b] font-mono text-[10px] font-bold border border-[#f59e0b]/40">
              DETERMINISTIC 9-STAGE COGNITIVE TRACE
            </span>
          </div>
          <h1 className="text-[24px] md:text-[26px] font-bold text-[#dbfcff] tracking-tight">
            GUIDED DEMO STORYLINE — SRE EXPERIENCE RETENTION & RECALL
          </h1>
          <p className="text-[13px] text-[#b9cacb] max-w-3xl">
            Watch Aegis handle a cold-start outage with zero prior memory (Phase 1), extract and commit the operational lesson to the Hindsight HyperGraph (Phase 2), and resolve the recurrence in under 4 minutes via semantic precedent recall (Phase 3).
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2 font-mono">
          {currentStep === 0 ? (
            <button
              onClick={handleStart}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-bold text-[12px] shadow-[0_0_14px_rgba(0,240,255,0.4)] transition-all cursor-pointer flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[16px]">play_arrow</span>
              <span>START DEMO (STEP 1)</span>
            </button>
          ) : (
            <>
              <button
                onClick={handlePrevious}
                disabled={loading || currentStep <= 1}
                className="px-3 py-2 rounded-lg bg-[#181c21] hover:bg-[#272a30] text-[#e0e2ea] font-bold text-[12px] border border-[#3b494b] disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center gap-1"
                title="Go back to previous step"
              >
                <span className="material-symbols-outlined text-[16px]">arrow_back</span>
                <span>PREVIOUS</span>
              </button>

              <button
                onClick={handleNext}
                disabled={loading || currentStep >= 9}
                className="px-4 py-2 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-bold text-[12px] shadow-[0_0_12px_rgba(0,240,255,0.3)] disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center gap-1.5"
              >
                <span>NEXT STEP ({currentStep}/9)</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </button>

              <button
                onClick={() => setAutoPlay(!autoPlay)}
                className={`px-3 py-2 rounded-lg font-bold text-[11px] border transition-all cursor-pointer flex items-center gap-1.5 ${
                  autoPlay
                    ? 'bg-[#7fecde]/20 text-[#7fecde] border-[#7fecde] animate-pulse'
                    : 'bg-[#181c21] hover:bg-[#272a30] text-[#b9cacb] border-[#3b494b]'
                }`}
              >
                <span className="material-symbols-outlined text-[16px]">
                  {autoPlay ? 'pause' : 'autorenew'}
                </span>
                <span>{autoPlay ? 'PAUSE AUTO' : 'AUTO-PLAY'}</span>
              </button>
            </>
          )}

          <button
            onClick={handleReset}
            disabled={loading}
            className="px-3 py-2 rounded-lg bg-[#93000a]/20 hover:bg-[#93000a]/40 text-[#ffb4ab] text-[11px] font-bold border border-[#ffb4ab]/30 transition-colors cursor-pointer flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">restart_alt</span>
            <span>RESET</span>
          </button>
        </div>
      </div>

      {/* 3 Storyline Phases Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className={`p-3.5 rounded-xl border transition-all ${
          currentStep >= 1 && currentStep <= 3
            ? 'bg-[#00f0ff]/10 border-[#00f0ff] shadow-[0_0_12px_rgba(0,240,255,0.2)]'
            : currentStep > 3
            ? 'bg-[#181c21]/80 border-[#7fecde]/40 text-[#7fecde]'
            : 'bg-[#0b0e13] border-[#3b494b]/30 opacity-70'
        }`}>
          <div className="flex items-center justify-between font-mono text-[11px] font-bold mb-1">
            <span className="text-[#00f0ff] flex items-center gap-1">
              <span className="material-symbols-outlined text-[15px]">ac_unit</span>
              PHASE 1: COLD-START OUTAGE
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-black/40">STEPS 1–3</span>
          </div>
          <p className="text-[11px] text-[#b9cacb] leading-relaxed">
            Incident A occurs with 0 historical memory in vector graph. Aegis falls back cleanly to first-principles diagnostics. (MTTR: 54 min).
          </p>
        </div>

        <div className={`p-3.5 rounded-xl border transition-all ${
          currentStep >= 4 && currentStep <= 5
            ? 'bg-[#7bd0ff]/10 border-[#7bd0ff] shadow-[0_0_12px_rgba(123,208,255,0.2)]'
            : currentStep > 5
            ? 'bg-[#181c21]/80 border-[#7fecde]/40 text-[#7fecde]'
            : 'bg-[#0b0e13] border-[#3b494b]/30 opacity-70'
        }`}>
          <div className="flex items-center justify-between font-mono text-[11px] font-bold mb-1">
            <span className="text-[#7bd0ff] flex items-center gap-1">
              <span className="material-symbols-outlined text-[15px]">history_edu</span>
              PHASE 2: MEMORY RETENTION
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-black/40">STEPS 4–5</span>
          </div>
          <p className="text-[11px] text-[#b9cacb] leading-relaxed">
            Post-mortem synthesizes operational rule: acquiring bank latency mimicked internal DB locks. Durable memory indexed into Hindsight HyperGraph.
          </p>
        </div>

        <div className={`p-3.5 rounded-xl border transition-all ${
          currentStep >= 6
            ? 'bg-[#7fecde]/10 border-[#7fecde] shadow-[0_0_12px_rgba(127,236,222,0.25)]'
            : 'bg-[#0b0e13] border-[#3b494b]/30 opacity-70'
        }`}>
          <div className="flex items-center justify-between font-mono text-[11px] font-bold mb-1">
            <span className="text-[#7fecde] flex items-center gap-1">
              <span className="material-symbols-outlined text-[15px]">bolt</span>
              PHASE 3: PRECEDENT RECALL
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-black/40">STEPS 6–9</span>
          </div>
          <p className="text-[11px] text-[#b9cacb] leading-relaxed">
            Incident B strikes with alternate symptoms. 91.4% semantic recall injects past precedent, slashing MTTR to 3.8 min with operator runbook.
          </p>
        </div>
      </div>

      {/* 9-Step Interactive Progression Track (Click any step to jump) */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between px-1">
          <span className="font-mono text-[11px] text-[#b9cacb] uppercase tracking-wider font-semibold">
            Interactive Timeline (Click any step to inspect):
          </span>
          <span className="font-mono text-[10px] text-[#00f0ff]">
            Current State: {demoState?.stepName || 'READY'}
          </span>
        </div>

        <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
          {steps.map((st) => {
            const isDone = currentStep > st.num;
            const isCurrent = currentStep === st.num;
            return (
              <button
                key={st.num}
                onClick={() => handleGoToStep(st.num)}
                disabled={loading}
                className={`p-2.5 rounded-lg border flex flex-col justify-between text-left transition-all cursor-pointer hover:border-[#00f0ff]/80 ${
                  isCurrent
                    ? 'bg-[#272a30] border-[#00f0ff] ring-1 ring-[#00f0ff] shadow-[0_0_12px_rgba(0,240,255,0.25)]'
                    : isDone
                    ? 'bg-[#181c21] border-[#7fecde]/50 text-[#7fecde]'
                    : 'bg-[#0b0e13] border-[#3b494b]/30 opacity-60 hover:opacity-100'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono text-[11px] font-bold">
                    STEP {st.num}
                  </span>
                  {isDone ? (
                    <span className="material-symbols-outlined text-[14px] text-[#7fecde]">check_circle</span>
                  ) : isCurrent ? (
                    <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-ping" />
                  ) : null}
                </div>
                <span className="font-mono text-[10px] font-bold block truncate text-[#dbfcff]">
                  {st.title.replace(/^\d+\s*/, '')}
                </span>
                <span className="text-[9px] text-[#b9cacb] line-clamp-2 mt-0.5 leading-tight">
                  {st.desc}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Center Interactive Stage: Split Screen Context Merge */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Incident Context */}
        <div className="lg:col-span-5 p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3 shadow-md">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] font-bold text-[#e0e2ea] uppercase tracking-wider flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#ffb4ab] text-[18px]">crisis_alert</span>
              <span>LIVE INCIDENT UNDER INVESTIGATION</span>
            </span>
            <span className="px-2 py-0.5 rounded bg-[#272a30] font-mono text-[10px] text-[#ffdad6] border border-[#ffb4ab]/30">
              {currentStep >= 6 ? 'INCIDENT B (RECURRENCE)' : 'INCIDENT A (COLD-START)'}
            </span>
          </div>

          <div className="space-y-2 font-mono text-[12px]">
            <div className="p-3 rounded bg-[#1d2025] border border-[#3b494b]/30">
              <span className="text-[#b9cacb] block text-[10px]">INCIDENT TITLE:</span>
              <span className="text-[#dbfcff] font-bold">
                {currentStep >= 6
                  ? 'Card Processing Partner Latency Surge & Pod Pool Saturation'
                  : 'Cold-start: Edge Proxy Read Socket Timeouts'}
              </span>
            </div>
            <div className="p-3 rounded bg-[#1d2025] border border-[#3b494b]/30">
              <span className="text-[#b9cacb] block text-[10px]">SURFACE SYMPTOMS & TELEMETRY:</span>
              <span className="text-[#ffdad6]">
                {currentStep >= 6
                  ? '504 Gateway Timeouts on /v2/checkout/charge (1,420 req/min), Thread Pool Exhaustion'
                  : '504 Read Timeouts on /v1/checkout edge ingress proxy, P99 Latency 4,820ms'}
              </span>
            </div>
            <div className="p-3 rounded bg-[#1d2025] border border-[#3b494b]/30">
              <span className="text-[#b9cacb] block text-[10px]">DOWNSTREAM IMPACT:</span>
              <span className="text-[#7bd0ff]">
                {currentStep >= 6
                  ? 'DB worker thread capacity 96% saturated on db-pool-worker-04'
                  : 'Proxy pool queue depth: 100% capacity; checkout failures across all regions'}
              </span>
            </div>
            <div className="p-3 rounded bg-[#1d2025] border border-[#3b494b]/30 flex justify-between items-center text-[11px]">
              <div>
                <span className="text-[#b9cacb] block text-[10px]">INCIDENT ID:</span>
                <span className="text-[#00f0ff] font-bold">
                  {currentIncidentId || (currentStep >= 6 ? 'INC-2026-B' : 'INC-2026-A')}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[#b9cacb] block text-[10px]">COGNITIVE STATUS:</span>
                <span className={`font-bold ${
                  currentStep >= 7 ? 'text-[#7fecde]' : currentStep >= 1 ? 'text-[#f59e0b]' : 'text-[#b9cacb]'
                }`}>
                  {currentStep >= 8 ? 'PRECEDENT INJECTED' : currentStep >= 6 ? 'ANALYZING SIMILARITY' : currentStep >= 1 ? 'FIRST-PRINCIPLES' : 'STANDBY'}
                </span>
              </div>
            </div>
          </div>

          {currentIncidentId && (
            <button
              onClick={() => onInvestigateIncident(currentIncidentId)}
              className="mt-auto px-3.5 py-2 rounded-lg bg-[#272a30] hover:bg-[#36393f] text-[#00f0ff] font-mono text-[11px] font-bold flex items-center justify-center gap-1.5 transition-colors border border-[#00f0ff]/30 cursor-pointer"
            >
              <span>Inspect in Investigation Cockpit</span>
              <span className="material-symbols-outlined text-[15px]">open_in_new</span>
            </button>
          )}
        </div>

        {/* Center: Context Merge Connector */}
        <div className="lg:col-span-2 flex flex-col items-center justify-center p-4 rounded-xl bg-[#0b0e13] border border-[#00f0ff]/30 text-center font-mono gap-3 shadow-inner">
          <div className="w-12 h-12 rounded-full bg-[#00f0ff]/10 flex items-center justify-center border border-[#00f0ff]/40">
            <span className="material-symbols-outlined text-[28px] text-[#00f0ff] animate-pulse">
              join_inner
            </span>
          </div>
          <div>
            <span className="text-[11px] font-bold text-[#00f0ff] uppercase block">
              COGNITIVE CONTEXT MERGE
            </span>
            <p className="text-[10px] text-[#b9cacb] leading-tight mt-1">
              Current Telemetry + Recalled Precedent synthesized before hypothesis generation.
            </p>
          </div>
          <span className={`px-2.5 py-1 rounded text-[10px] font-bold border ${
            currentStep >= 8
              ? 'bg-[#7fecde]/20 text-[#7fecde] border-[#7fecde]/40 animate-pulse'
              : currentStep >= 7
              ? 'bg-[#00f0ff]/20 text-[#00f0ff] border-[#00f0ff]/40'
              : 'bg-[#272a30] text-[#b9cacb] border-[#3b494b]'
          }`}>
            {currentStep >= 8 ? 'MERGE ACTIVE (EXP-1987)' : currentStep >= 7 ? 'RECALL COMPLETE' : 'AWAITING RECALL'}
          </span>

          <div className="w-full pt-2 border-t border-[#3b494b]/30 text-[9px] text-[#859394] space-y-1">
            <div className="flex justify-between">
              <span>Grounding:</span>
              <span className="text-[#dbfcff] font-bold">{currentStep >= 7 ? 'HIGH' : 'ZERO'}</span>
            </div>
            <div className="flex justify-between">
              <span>Hallucination Risk:</span>
              <span className={currentStep >= 7 ? 'text-[#7fecde] font-bold' : 'text-[#f59e0b]'}>
                {currentStep >= 7 ? '0.00% (VERIFIED)' : 'ELEVATED'}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Recalled Experience */}
        <div className="lg:col-span-5 p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3 shadow-md">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] font-bold text-[#00f0ff] uppercase tracking-wider flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[18px]">psychology</span>
              <span>HINDSIGHT EXPERIENCE RETENTION & RECALL</span>
            </span>
            <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
              currentStep >= 7
                ? 'bg-[#7fecde]/20 text-[#7fecde] border border-[#7fecde]/40'
                : 'bg-[#272a30] text-[#b9cacb]'
            }`}>
              {currentStep >= 7 ? '91.4% SIMILARITY' : currentStep >= 5 ? '1 PRECEDENT INDEXED' : '0 HISTORICAL PRECEDENTS'}
            </span>
          </div>

          {currentStep >= 7 ? (
            <div className="space-y-2 font-mono text-[12px] animate-fade-in">
              <div className="p-3 rounded bg-[#1d2025] border border-[#00f0ff]/40">
                <span className="text-[#7bd0ff] block text-[10px] font-bold">RECALLED PRECEDENT ID:</span>
                <div className="flex items-center justify-between">
                  <span className="text-[#dbfcff] font-bold">INC-1987 / HINDSIGHT-EXP-1987</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#7fecde]/20 text-[#7fecde]">
                    MATCH SCORE 0.914
                  </span>
                </div>
              </div>
              <div className="p-3 rounded bg-[#1d2025] border border-[#00f0ff]/40">
                <span className="text-[#7bd0ff] block text-[10px] font-bold">WHY RECALLED:</span>
                <span className="text-[#e0e2ea] text-[11px]">
                  Matches upstream acquiring bank latency mimicking internal DB locks without host CPU spikes.
                </span>
              </div>
              <div className="p-3 rounded bg-[#00f0ff]/10 border border-[#00f0ff]/40">
                <span className="text-[#00f0ff] block text-[10px] font-bold">RETAINED OPERATIONAL RULE:</span>
                <span className="text-[#dbfcff] italic text-[11px]">
                  “When socket timeouts spike on payment proxy without internal CPU spikes, inspect upstream third-party status before rolling back application releases.”
                </span>
              </div>
              {currentStep >= 9 && (
                <div className="p-3 rounded bg-[#7fecde]/10 border border-[#7fecde]/40 text-[#7fecde] text-[11px]">
                  <span className="font-bold block text-[10px] uppercase">Staged Response Actions:</span>
                  <span>1. Failover 50% non-critical traffic to backup gateway (SAFE)</span>
                  <br />
                  <span>2. Enforce 1500ms timeout clamp (MITIGATE)</span>
                </div>
              )}
            </div>
          ) : currentStep >= 4 ? (
            <div className="space-y-2 font-mono text-[12px] animate-fade-in">
              <div className="p-3 rounded bg-[#1d2025] border border-[#7bd0ff]/40">
                <span className="text-[#7bd0ff] block text-[10px] font-bold">POST-MORTEM SYNTHESIS:</span>
                <span className="text-[#e0e2ea] text-[11px]">
                  Systemic analysis identified third-party partner degradation as root trigger. Operational rule extracted.
                </span>
              </div>
              <div className="p-3 rounded bg-[#7bd0ff]/10 border border-[#7bd0ff]/40">
                <span className="text-[#7bd0ff] block text-[10px] font-bold">COMMITTED TO VECTOR MEMORY:</span>
                <span className="text-[#dbfcff] text-[11px]">
                  {currentStep >= 5 ? 'Indexed to Hindsight HyperGraph with 1,536-dim vector embeddings.' : 'Awaiting retention commit (Step 5).'}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-8 text-center font-mono gap-2 text-[#b9cacb]">
              <span className="material-symbols-outlined text-[36px] text-[#3b494b]">database_off</span>
              <span className="text-[12px] font-bold text-[#e0e2ea]">NO RELEVANT EXPERIENCE FOUND</span>
              <p className="text-[11px]">
                Cold-start incident triage executing first-principles diagnostic reasoning. No historical precedent exists yet.
              </p>
            </div>
          )}

          <button
            onClick={onExploreMemory}
            className="mt-auto px-3.5 py-2 rounded-lg bg-[#272a30] hover:bg-[#36393f] text-[#7fecde] font-mono text-[11px] font-bold flex items-center justify-center gap-1.5 transition-colors border border-[#7fecde]/30 cursor-pointer"
          >
            <span>Explore Spatial Memory Constellation</span>
            <span className="material-symbols-outlined text-[15px]">hub</span>
          </button>
        </div>
      </div>

      {/* Comparative Metrics Table: Cold-Start vs Memory-Grounded */}
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 flex flex-col gap-3 font-mono">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold text-[#e0e2ea] uppercase tracking-wider flex items-center gap-2">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">query_stats</span>
            <span>EXPERIENCE ENGINE IMPACT COMPARISON</span>
          </span>
          <span className="text-[10px] text-[#7fecde] font-bold">
            93% REDUCTION IN MTTR
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px]">
          <div className="p-3 rounded-lg bg-[#181c21] border border-[#ffb4ab]/30 flex flex-col gap-1">
            <span className="text-[10px] text-[#ffdad6] font-bold uppercase">INCIDENT A (COLD-START)</span>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Time to Triage:</span>
              <span className="text-[#ffdad6] font-bold text-[14px]">38 min</span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Total MTTR:</span>
              <span className="text-[#ffdad6] font-bold text-[14px]">54 min</span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Reasoning Method:</span>
              <span className="text-[#b9cacb] text-[11px]">First-principles trial & error</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-[#181c21] border border-[#7bd0ff]/30 flex flex-col gap-1">
            <span className="text-[10px] text-[#7bd0ff] font-bold uppercase">LEARNING PHASE</span>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Post-Mortem:</span>
              <span className="text-[#dbfcff] font-bold text-[14px]">Automated</span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Vector Nodes Added:</span>
              <span className="text-[#7bd0ff] font-bold text-[14px]">+1 Rule, +4 Edges</span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Human SRE Review:</span>
              <span className="text-[#7fecde] text-[11px]">Confirmed & Retained</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-[#181c21] border border-[#7fecde]/40 flex flex-col gap-1 shadow-[0_0_12px_rgba(127,236,222,0.1)]">
            <span className="text-[10px] text-[#7fecde] font-bold uppercase">INCIDENT B (WITH RECALL)</span>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Time to Triage:</span>
              <span className="text-[#7fecde] font-bold text-[14px]">42 sec</span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Total MTTR:</span>
              <span className="text-[#7fecde] font-bold text-[14px]">3.8 min</span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-[#b9cacb] text-[11px]">Precedent Confidence:</span>
              <span className="text-[#7fecde] font-bold text-[14px]">91.4% match</span>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Log Stream */}
      <div className="p-4 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 flex flex-col gap-2 font-mono text-[11px]">
        <div className="flex items-center justify-between">
          <span className="text-[#00f0ff] font-bold uppercase tracking-wider flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[15px]">terminal</span>
            <span>LIVE DEMO EVENT LOG STREAM</span>
          </span>
          <span className="text-[10px] text-[#b9cacb]">
            {demoState?.logs?.length || 0} events recorded
          </span>
        </div>
        <div className="space-y-1 text-[#b9cacb] max-h-48 overflow-y-auto bg-[#101419] p-3 rounded-lg border border-[#3b494b]/30">
          {demoState?.logs?.length ? (
            demoState.logs.map((l: string, i: number) => (
              <div key={i} className="flex gap-2">
                <span className="text-[#00f0ff] select-none">›</span>
                <span className={l.includes('SUCCESS') ? 'text-[#7fecde]' : l.includes('Retained') ? 'text-[#7bd0ff]' : ''}>
                  {l}
                </span>
              </div>
            ))
          ) : (
            <div className="text-[#859394] italic">No events logged yet. Click START DEMO to begin.</div>
          )}
        </div>
      </div>
    </div>
  );
};
