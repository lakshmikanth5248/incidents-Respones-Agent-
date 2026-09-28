import React, { useState, useEffect } from 'react';
import { CURRENT_INCIDENT, SERVICE_NODES, HISTORICAL_PRECEDENTS, RECOMMENDED_RUNBOOK_ACTIONS, INITIAL_TELEMETRY_LOGS } from '../data/mockData';
import { ServiceNode, MemoryPrecedent, LogEntry } from '../types';
import { ThreeTopologyScene } from './ThreeTopologyScene';
import { SvgTopologyMap } from './SvgTopologyMap';
import { PrecedentDetailModal } from './PrecedentDetailModal';
import { DispatchRunbookModal } from './DispatchRunbookModal';

interface InvestigationWorkspaceProps {
  onNavigateToGraph?: () => void;
  onOpenPrecedentTrace?: (precedentId: string) => void;
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  onNavigateToGraph,
  onOpenPrecedentTrace,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(18 * 60 + 42);
  const [viewMode, setViewMode] = useState<'3d' | '2d'>('3d');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('checkout-api');
  const [selectedPrecedent, setSelectedPrecedent] = useState<MemoryPrecedent | null>(null);
  const [isDispatchModalOpen, setIsDispatchModalOpen] = useState(false);
  const [hypothesisAcknowledged, setHypothesisAcknowledged] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [escalated, setEscalated] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_TELEMETRY_LOGS);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Ticking incident timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTimer = (totalSecs: number) => {
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleSelectNode = (nodeId: string) => {
    setSelectedNodeId(nodeId);
  };

  const selectedNodeData: ServiceNode | undefined = SERVICE_NODES.find(
    (n) => n.id === selectedNodeId
  );

  const handleInspect1987 = () => {
    const inc1987 = HISTORICAL_PRECEDENTS.find((p) => p.id === 'INC-1987');
    if (inc1987) {
      setSelectedPrecedent(inc1987);
    }
  };

  const handleSelectPrecedentId = (precedentId: string) => {
    const found = HISTORICAL_PRECEDENTS.find((p) => p.id === precedentId);
    if (found) {
      setSelectedPrecedent(found);
    }
  };

  const handleAcknowledgeClick = () => {
    setHypothesisAcknowledged(true);
    setIsDispatchModalOpen(true);
  };

  // Add periodic live simulated telemetry
  useEffect(() => {
    const logInterval = setInterval(() => {
      const now = new Date();
      const timeStr = `${String(now.getUTCHours()).padStart(2, '0')}:${String(now.getUTCMinutes()).padStart(2, '0')}:${String(now.getUTCSeconds()).padStart(2, '0')}`;
      const mockEvents = [
        { level: 'WARN' as const, source: 'EnvoyIngress', message: `Retry budget 88% consumed on iad01 egress path` },
        { level: 'AGENT' as const, source: 'HindsightEngine', message: `Precedent INC-1987 confidence sustained at 91.4%` },
        { level: 'INFO' as const, source: 'AdyenFallback', message: `Secondary gateway warmup health probe: OK (latency 19ms)` },
        { level: 'ERROR' as const, source: 'WorkerThreadMonitor', message: `Thread pool high-water mark: 488 active worker threads` },
      ];
      const randomEvent = mockEvents[Math.floor(Math.random() * mockEvents.length)];
      setLogs((prev) => [
        ...prev.slice(-15),
        {
          id: `log-${Date.now()}`,
          timestamp: timeStr,
          level: randomEvent.level,
          source: randomEvent.source,
          message: randomEvent.message,
          highlight: randomEvent.level === 'AGENT',
        },
      ]);
    }, 12000);
    return () => clearInterval(logInterval);
  }, []);

  return (
    <div className="flex flex-col w-full gap-4 relative animate-fade-in">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-[#1d2025] border border-[#00f0ff] px-4 py-2.5 rounded-lg shadow-[0_0_20px_rgba(0,240,255,0.4)] text-[12px] font-mono text-[#dbfcff] flex items-center gap-2">
          <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">info</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Operational Mission Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 shadow-xl">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#93000a] text-[#ffdad6] border border-[#ffb4ab]/40">
            <span className="material-symbols-outlined text-[18px] text-[#ffb4ab] animate-pulse">
              crisis_alert
            </span>
            <span className="font-mono text-[11px] font-bold text-[#ffb4ab] tracking-wider">
              ACTIVE INCIDENT: INC-2048
            </span>
          </div>

          <div className="h-4 w-px bg-[#32353b]" />

          <div className="flex items-center gap-1.5 font-mono text-[11px] text-[#b9cacb]">
            <span className="material-symbols-outlined text-[16px] text-[#7bd0ff]">
              database
            </span>
            <span>
              EXPERIENCE COGNITION: <span className="text-[#7fecde] font-bold">ONLINE</span>
            </span>
          </div>

          <div className="h-4 w-px bg-[#32353b]" />

          <span className="font-mono text-[11px] text-[#b9cacb]">
            CLUSTER: <span className="text-[#e0e2ea] font-semibold">us-east-prod-k8s</span>
          </span>
          <span className="font-mono text-[11px] text-[#b9cacb]">
            REGION: <span className="text-[#e0e2ea] font-semibold">North America (iad01)</span>
          </span>
        </div>

        {/* Mandatory Human Boundary Guard */}
        <div className="flex items-center gap-2 px-3 py-1 rounded bg-[#272a30] border border-[#00a6e0]/30 shadow-inner">
          <span className="material-symbols-outlined text-[16px] text-[#00a6e0]">
            shield_with_heart
          </span>
          <span className="font-mono text-[11px] font-bold text-[#7bd0ff] tracking-widest uppercase">
            ADVISORY ONLY — NO AUTOMATED EXECUTION
          </span>
          <div className="w-2 h-2 rounded-full bg-[#00a6e0] animate-ping" />
        </div>
      </div>

      {/* 3-Column Engineering Cockpit: 28% / 42% / 30% */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* ========================================== */}
        {/* LEFT COLUMN: INCIDENT CONTEXT & SIGNALS   */}
        {/* ========================================== */}
        <section className="lg:col-span-3 flex flex-col gap-4">
          {/* Incident Header Card */}
          <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 shadow-md flex flex-col gap-2 relative overflow-hidden">
            <div className="absolute -top-12 -right-12 w-28 h-28 rounded-full bg-[#93000a]/20 blur-xl pointer-events-none" />
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="font-mono text-[10px] text-[#b9cacb] uppercase tracking-wider font-semibold">
                  INCIDENT RECORD
                </span>
                <span className="text-[18px] font-bold text-[#dbfcff]">
                  INC-2048
                </span>
              </div>
              <span className="px-2 py-0.5 rounded bg-[#93000a] text-[#ffdad6] font-mono text-[10px] font-bold border border-[#ffb4ab]/40">
                HIGH SEVERITY
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="p-2 rounded bg-[#1d2025] flex flex-col border border-[#3b494b]/30">
                <span className="font-mono text-[10px] text-[#b9cacb]">ELAPSED TIME</span>
                <span className="font-mono text-[16px] font-bold text-[#ffb4ab]">
                  {formatTimer(elapsedSeconds)}
                </span>
              </div>
              <div className="p-2 rounded bg-[#1d2025] flex flex-col border border-[#3b494b]/30">
                <span className="font-mono text-[10px] text-[#b9cacb]">SERVICES DOWN</span>
                <span className="font-mono text-[16px] font-bold text-[#7bd0ff]">
                  {CURRENT_INCIDENT.servicesDownCount} / {CURRENT_INCIDENT.totalServicesCount}
                </span>
              </div>
            </div>

            <p className="text-[12px] text-[#b9cacb] leading-relaxed pt-1">
              Intermittent <code className="px-1 py-0.5 rounded bg-[#272a30] text-[#ffb4ab] font-mono text-[11px]">504 Gateway Timeouts</code> on{' '}
              <span className="text-[#e0e2ea] font-mono text-[11px]">{CURRENT_INCIDENT.endpoint}</span>. Blast radius verified isolated to North America region downstream ingress.
            </p>
          </div>

          {/* Error Vector Distribution */}
          <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 shadow-md flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] font-semibold text-[#b9cacb] uppercase tracking-wider">
                SYMPTOM SIGNATURES
              </span>
              <span className="font-mono text-[11px] text-[#7bd0ff]">Ingest P99</span>
            </div>

            <div className="flex flex-col gap-2">
              {CURRENT_INCIDENT.symptoms.map((symptom) => (
                <div key={symptom.name} className="p-2 rounded bg-[#1d2025] flex flex-col gap-1 border border-[#3b494b]/30">
                  <div className="flex justify-between items-center font-mono text-[11px]">
                    <span className="text-[#e0e2ea]">{symptom.name}</span>
                    <span className="font-bold text-[#ffb4ab]">{symptom.rate}</span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-[#32353b] overflow-hidden">
                    <div
                      className={`h-full ${symptom.color} rounded-full transition-all duration-500`}
                      style={{ width: `${symptom.percent}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Temporal Changes */}
          <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 shadow-md flex flex-col gap-2">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-[#00f0ff]">
                published_with_changes
              </span>
              <span className="font-mono text-[11px] font-semibold text-[#b9cacb] uppercase tracking-wider">
                RECENT DEPLOYMENTS (T-60m)
              </span>
            </div>

            <div className="flex flex-col gap-2 font-mono text-[11px]">
              {CURRENT_INCIDENT.recentDeployments.map((dep) => (
                <div key={dep.service} className="p-2 rounded bg-[#1d2025] flex flex-col gap-0.5 border border-[#3b494b]/30">
                  <div className="flex justify-between items-center">
                    <span className="text-[#e0e2ea] font-semibold">{dep.service}</span>
                    <span className="text-[#b9cacb]">{dep.time}</span>
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="px-1.5 py-0.2 rounded bg-[#272a30] text-[#7bd0ff] text-[10px]">
                      {dep.tag}
                    </span>
                    <span className="text-[#b9cacb] text-[10px]">{dep.commit}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Raw Ingestion Log Stream */}
          <div className="p-4 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-inner flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00f0ff] animate-pulse" />
                <span className="font-mono text-[11px] font-bold text-[#00f0ff] uppercase">
                  RAW TELEMETRY STREAM
                </span>
              </div>
              <span className="font-mono text-[10px] text-[#b9cacb]">
                buffer: {logs.length} lines
              </span>
            </div>

            <div className="font-mono text-[11px] text-[#b9cacb] flex flex-col gap-1.5 p-2 rounded bg-[#101419] max-h-48 overflow-y-auto border border-[#3b494b]/30 select-all">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className={`leading-tight transition-colors ${
                    log.highlight ? 'bg-[#272a30]/80 p-1 rounded border-l-2 border-[#00f0ff]' : ''
                  }`}
                >
                  <span className="text-[#b9cacb]/60">[{log.timestamp}]</span>{' '}
                  <span
                    className={`font-bold ${
                      log.level === 'WARN'
                        ? 'text-[#7bd0ff]'
                        : log.level === 'ERROR'
                        ? 'text-[#ffb4ab]'
                        : log.level === 'AGENT'
                        ? 'text-[#7fecde]'
                        : 'text-[#00f0ff]'
                    }`}
                  >
                    {log.level}
                  </span>{' '}
                  <span className="text-[#e0e2ea]">{log.source}:</span>{' '}
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* CENTER COLUMN: TOPOLOGY & BLAST RADIUS     */}
        {/* ========================================== */}
        <section className="lg:col-span-5 flex flex-col gap-4">
          <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 shadow-xl flex flex-col gap-3 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-[#00f0ff]">
                  account_tree
                </span>
                <span className="font-mono text-[11px] font-bold text-[#e0e2ea] uppercase tracking-wider">
                  LIVE TOPOLOGY &amp; BLAST RADIUS MAP
                </span>
              </div>

              <div className="flex items-center gap-2">
                {/* 3D / 2D View Switcher */}
                <div className="flex items-center bg-[#0b0e13] p-0.5 rounded-lg border border-[#3b494b]/40">
                  <button
                    onClick={() => setViewMode('3d')}
                    className={`px-2.5 py-1 rounded text-[11px] font-mono flex items-center gap-1 transition-all ${
                      viewMode === '3d'
                        ? 'bg-[#00f0ff] text-[#00363a] font-bold shadow-[0_0_8px_rgba(0,240,255,0.3)]'
                        : 'text-[#b9cacb] hover:text-[#e0e2ea]'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[14px]">view_in_ar</span>
                    <span>3D Hologram</span>
                  </button>
                  <button
                    onClick={() => setViewMode('2d')}
                    className={`px-2.5 py-1 rounded text-[11px] font-mono flex items-center gap-1 transition-all ${
                      viewMode === '2d'
                        ? 'bg-[#00f0ff] text-[#00363a] font-bold shadow-[0_0_8px_rgba(0,240,255,0.3)]'
                        : 'text-[#b9cacb] hover:text-[#e0e2ea]'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[14px]">schema</span>
                    <span>2D Mesh</span>
                  </button>
                </div>

                <div className="flex items-center gap-1.5 font-mono text-[10px] px-2 py-1 rounded bg-[#272a30] text-[#ffdad6] border border-[#ffb4ab]/30">
                  <span className="w-2 h-2 rounded-full bg-[#ffb4ab] animate-ping" />
                  <span>CRITICAL PATH DOWN</span>
                </div>
              </div>
            </div>

            {/* Topology Visualizer Container */}
            <div className="h-[270px] w-full">
              {viewMode === '3d' ? (
                <ThreeTopologyScene
                  onSelectNode={handleSelectNode}
                  onSelectPrecedent={handleSelectPrecedentId}
                  selectedNodeId={selectedNodeId}
                />
              ) : (
                <SvgTopologyMap
                  onSelectNode={handleSelectNode}
                  selectedNodeId={selectedNodeId}
                />
              )}
            </div>

            {/* Selected Node Telemetry Inspector Drawer */}
            {selectedNodeData && (
              <div className="p-2.5 rounded-lg bg-[#1d2025] border border-[#00f0ff]/30 flex items-center justify-between font-mono text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded bg-[#0b0e13] text-[#00f0ff] font-bold">
                    {selectedNodeData.name}
                  </span>
                  <span className="text-[#b9cacb]">{selectedNodeData.type}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                      selectedNodeData.status === 'CRITICAL'
                        ? 'bg-[#93000a] text-[#ffdad6]'
                        : selectedNodeData.status === 'DEGRADED'
                        ? 'bg-[#f59e0b]/20 text-[#f59e0b]'
                        : 'bg-[#7fecde]/20 text-[#7fecde]'
                    }`}
                  >
                    {selectedNodeData.status}
                  </span>
                </div>

                <div className="flex items-center gap-3 text-[#b9cacb]">
                  <span>P99: <strong className="text-[#dbfcff]">{selectedNodeData.latency}ms</strong></span>
                  <span>Errors: <strong className="text-[#ffb4ab]">{selectedNodeData.errorRate}%</strong></span>
                  <span>Pods: <strong className="text-[#7bd0ff]">{selectedNodeData.instances}</strong></span>
                </div>
              </div>
            )}

            {/* Live Telemetry Instrument Gauges */}
            <div className="grid grid-cols-3 gap-2 pt-1">
              {/* Gauge 1: P99 Latency */}
              <div className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-[#b9cacb] font-semibold">P99 LATENCY</span>
                  <span className="font-mono text-[10px] text-[#ffb4ab] font-bold">26.7x BL</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="font-mono text-[24px] font-bold text-[#ffb4ab]">
                    {CURRENT_INCIDENT.telemetry.p99Latency.toLocaleString()}
                  </span>
                  <span className="font-mono text-[11px] text-[#b9cacb]">ms</span>
                </div>
                <div className="flex justify-between items-center font-mono text-[10px] text-[#b9cacb]">
                  <span>Baseline: {CURRENT_INCIDENT.telemetry.baselineLatency}ms</span>
                  <span className="text-[#ffb4ab] font-bold">CRITICAL</span>
                </div>
                <div className="w-full h-1 bg-[#32353b] rounded-full overflow-hidden mt-1">
                  <div className="h-full bg-[#ffb4ab] rounded-full" style={{ width: '95%' }} />
                </div>
              </div>

              {/* Gauge 2: Error Rate */}
              <div className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-[#b9cacb] font-semibold">ERROR RATE</span>
                  <span className="font-mono text-[10px] text-[#ffb4ab] font-bold">+14.18%</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="font-mono text-[24px] font-bold text-[#ffb4ab]">
                    {CURRENT_INCIDENT.telemetry.errorRate}
                  </span>
                  <span className="font-mono text-[11px] text-[#b9cacb]">%</span>
                </div>
                <div className="flex justify-between items-center font-mono text-[10px] text-[#b9cacb]">
                  <span>Baseline: {CURRENT_INCIDENT.telemetry.baselineErrorRate}%</span>
                  <span className="text-[#ffb4ab] font-bold">SPIKE</span>
                </div>
                <div className="w-full h-1 bg-[#32353b] rounded-full overflow-hidden mt-1">
                  <div className="h-full bg-[#ffb4ab] rounded-full" style={{ width: '71%' }} />
                </div>
              </div>

              {/* Gauge 3: In-flight Socket Pool */}
              <div className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-[#b9cacb] font-semibold">SOCKET POOL</span>
                  <span className="font-mono text-[10px] text-[#ffb4ab] font-bold">96% SAT</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="font-mono text-[24px] font-bold text-[#7bd0ff]">
                    {CURRENT_INCIDENT.telemetry.socketPoolUsed}
                  </span>
                  <span className="font-mono text-[11px] text-[#b9cacb]">/{CURRENT_INCIDENT.telemetry.socketPoolTotal}</span>
                </div>
                <div className="flex justify-between items-center font-mono text-[10px] text-[#b9cacb]">
                  <span>Cap: 500 conns</span>
                  <span className="text-[#7fecde] font-bold">SATURATED</span>
                </div>
                <div className="w-full h-1 bg-[#32353b] rounded-full overflow-hidden mt-1">
                  <div className="h-full bg-[#00a6e0] rounded-full" style={{ width: '96%' }} />
                </div>
              </div>
            </div>

            {/* Telemetry Actions Instrument Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => showToast('Memory Snapshot captured and indexed into HyperGraph.')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#272a30] hover:bg-[#36393f] text-[#e0e2ea] font-mono text-[11px] transition-all shadow-sm cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[16px] text-[#00f0ff]">camera</span>
                  <span>Snapshot Memory State</span>
                </button>
                <button
                  onClick={() => showToast('Pinned current trace to Incident War Room log.')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#272a30] hover:bg-[#36393f] text-[#e0e2ea] font-mono text-[11px] transition-all shadow-sm cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[16px] text-[#7fecde]">push_pin</span>
                  <span>Pin to Log</span>
                </button>
              </div>

              <button
                onClick={() => showToast('Exporting OTel telemetry archive: inc-2048-trace-iad01.json')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#272a30] hover:bg-[#36393f] text-[#b9cacb] hover:text-[#e0e2ea] font-mono text-[11px] transition-all cursor-pointer"
              >
                <span className="material-symbols-outlined text-[16px]">file_download</span>
                <span>Export Incident Telemetry</span>
              </button>
            </div>
          </div>

          {/* Historical Precedent Comparison Panel */}
          <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 shadow-md flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[18px] text-[#7bd0ff]">
                  compare_arrows
                </span>
                <span className="font-mono text-[11px] text-[#e0e2ea] uppercase tracking-wider font-semibold">
                  PREVIOUS EXECUTION RUNBOOK MATRIX
                </span>
              </div>
              <span className="px-2 py-0.5 rounded bg-[#272a30] font-mono text-[11px] text-[#7fecde] border border-[#3b494b]/40">
                GROUNDED IN 1987
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-1 font-mono text-[11px]">
              <div className="p-2.5 rounded bg-[#1d2025] flex flex-col gap-1 border border-[#0d9488]/40">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px] text-[#7fecde]">
                    check_circle
                  </span>
                  <span className="font-bold text-[#7fecde] text-[10px] uppercase">
                    PREVIOUSLY SUCCESSFUL
                  </span>
                </div>
                <span className="text-[#e0e2ea] font-semibold">Gateway Split 50/50</span>
                <span className="text-[#b9cacb] text-[10px]">Validated in INC-1987 (14m recovery)</span>
              </div>

              <div className="p-2.5 rounded bg-[#1d2025] flex flex-col gap-1 border border-[#ffb4ab]/30">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px] text-[#ffb4ab]">
                    cancel
                  </span>
                  <span className="font-bold text-[#ffb4ab] text-[10px] uppercase">
                    INEFFECTIVE PRECEDENT
                  </span>
                </div>
                <span className="text-[#e0e2ea] line-through font-semibold">Container Restart</span>
                <span className="text-[#b9cacb] text-[10px]">Resulted in socket stampede (INC-1822)</span>
              </div>

              <div className="p-2.5 rounded bg-[#1d2025] flex flex-col gap-1 border border-[#3b494b]/40">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px] text-[#7bd0ff]">
                    explore
                  </span>
                  <span className="font-bold text-[#7bd0ff] text-[10px] uppercase">
                    HEURISTIC CANDIDATE
                  </span>
                </div>
                <span className="text-[#e0e2ea] font-semibold">1500ms Socket Clamp</span>
                <span className="text-[#b9cacb] text-[10px]">Unvalidated in live cluster</span>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* RIGHT COLUMN: AGENT REASONING PIPELINE     */}
        {/* ========================================== */}
        <section className="lg:col-span-4 flex flex-col gap-4">
          <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 shadow-xl flex flex-col gap-3">
            {/* Pipeline Header */}
            <div className="flex items-center justify-between pb-1">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-[#00f0ff]">
                  psychology
                </span>
                <div className="flex flex-col">
                  <span className="font-mono text-[10px] text-[#b9cacb] uppercase tracking-wider font-semibold">
                    HINDSIGHT AI REASONING
                  </span>
                  <span className="text-[15px] font-semibold text-[#dbfcff]">
                    5-Stage Cognitive Pipeline
                  </span>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded bg-[#1d2025] text-[#7fecde] font-mono text-[11px] font-semibold border border-[#7fecde]/30">
                STAGE 05 / ACTIVE
              </span>
            </div>

            {/* Step Progression Track */}
            <div className="flex flex-col gap-2.5">
              {/* Stage 1 */}
              <div className="p-2.5 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex flex-col gap-1 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-[#7fecde]">
                      check_circle
                    </span>
                    <span className="font-mono text-[11px] font-bold text-[#7fecde]">
                      01 CONTEXT COLLECTED
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-[#b9cacb]">14:02:18 UTC</span>
                </div>
                <p className="font-mono text-[11px] text-[#b9cacb] pl-5">
                  12 error signatures, 4 service graphs, 2 deployment manifests aggregated from OpenTelemetry pipeline.
                </p>
              </div>

              {/* Stage 2 */}
              <div className="p-2.5 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex flex-col gap-1 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-[#7fecde]">
                      check_circle
                    </span>
                    <span className="font-mono text-[11px] font-bold text-[#7fecde]">
                      02 MEMORY RECALL
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-[#b9cacb]">14:03:02 UTC</span>
                </div>
                <p className="font-mono text-[11px] text-[#b9cacb] pl-5">
                  Hindsight query executed across <span className="text-[#00f0ff] font-bold">14,892 historical incident embeddings</span>.
                </p>
              </div>

              {/* Stage 3 (Highlighted Precedent Match) */}
              <div className="p-3 rounded-lg bg-[#272a30] border border-[#00f0ff]/40 flex flex-col gap-1.5 shadow-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-[#00f0ff]">
                      hub
                    </span>
                    <span className="font-mono text-[11px] font-bold text-[#00f0ff]">
                      03 RELEVANT EXPERIENCE FOUND
                    </span>
                  </div>
                  <span className="px-1.5 py-0.5 rounded bg-[#32353b] text-[#7fecde] font-mono text-[11px] font-bold">
                    91.4% SIM
                  </span>
                </div>

                <div className="pl-5 flex flex-col gap-1">
                  <span className="text-[13px] font-semibold text-[#e0e2ea]">
                    INC-1987 (Payment Gateway Timeout Cascade)
                  </span>
                  <p className="font-mono text-[11px] text-[#b9cacb]">
                    Key observations matched: downstream socket hanging, pool lock contention, NA-east localized latency.
                  </p>
                  <div className="pt-1 flex items-center gap-2">
                    <button
                      onClick={handleInspect1987}
                      className="px-2 py-1 rounded bg-[#181c21] hover:bg-[#32353b] text-[#7bd0ff] font-mono text-[11px] flex items-center gap-1 border border-[#3b494b]/40 transition-colors"
                    >
                      <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                      <span>Inspect INC-1987 Precedent Trace</span>
                    </button>
                    {onNavigateToGraph && (
                      <button
                        onClick={onNavigateToGraph}
                        className="px-2 py-1 rounded bg-[#181c21] hover:bg-[#32353b] text-[#7fecde] font-mono text-[11px] flex items-center gap-1 border border-[#3b494b]/40 transition-colors"
                      >
                        <span className="material-symbols-outlined text-[14px]">hub</span>
                        <span>Graph View</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Stage 4: Hypothesis */}
              <div className="p-2.5 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex flex-col gap-1 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-[#7fecde]">
                      check_circle
                    </span>
                    <span className="font-mono text-[11px] font-bold text-[#7fecde]">
                      04 DEDUCTIVE HYPOTHESIS
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-[#7fecde] font-bold">
                    MODERATE CONFIDENCE
                  </span>
                </div>
                <p className="text-[13px] text-[#e0e2ea] pl-5 leading-relaxed">
                  “Current evidence + prior experience suggest <strong className="text-[#00f0ff]">upstream payment partner throttling</strong> rather than internal deployment regression.”
                </p>
              </div>

              {/* Stage 5: Recommended Interventions */}
              <div className="p-3 rounded-lg bg-[#272a30] border border-[#3b494b]/40 flex flex-col gap-2 shadow-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[18px] text-[#00f0ff] animate-pulse">
                      playlist_add_check
                    </span>
                    <span className="font-mono text-[11px] font-bold text-[#00f0ff]">
                      05 RECOMMENDED RESPONSE PLAN
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-[#b9cacb]">
                    3 Actions Prepared
                  </span>
                </div>

                <div className="flex flex-col gap-1.5 font-mono text-[11px]">
                  {RECOMMENDED_RUNBOOK_ACTIONS.map((action) => (
                    <div
                      key={action.id}
                      className="p-2 rounded bg-[#181c21] border border-[#3b494b]/30 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[#00f0ff] font-bold">{action.stepNumber}.</span>
                        <span className="text-[#e0e2ea]">{action.title}</span>
                      </div>
                      <span
                        className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded ${
                          action.riskLevel === 'SAFE'
                            ? 'text-[#7fecde] bg-[#7fecde]/20'
                            : action.riskLevel === 'MITIGATE'
                            ? 'text-[#7bd0ff] bg-[#7bd0ff]/20'
                            : 'text-[#ffb4ab] bg-[#93000a]/40'
                        }`}
                      >
                        {action.riskLevel}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Human Confirmation Action Footer */}
            <div className="pt-1 flex flex-col gap-2">
              <button
                onClick={handleAcknowledgeClick}
                className={`w-full py-2.5 px-4 rounded font-semibold text-[14px] transition-all flex items-center justify-center gap-2 cursor-pointer ${
                  hypothesisAcknowledged
                    ? 'bg-[#7fecde] text-[#003732] shadow-[0_0_16px_rgba(127,236,222,0.4)]'
                    : 'bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] shadow-[0_0_14px_rgba(0,240,255,0.3)]'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">
                  {hypothesisAcknowledged ? 'check' : 'verified'}
                </span>
                <span>
                  {hypothesisAcknowledged
                    ? 'Hypothesis Staged — Awaiting Operator Dispatch'
                    : 'Acknowledge Hypothesis & Stage Plan'}
                </span>
              </button>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    setFeedbackGiven(true);
                    showToast('Feedback recorded: Tuning vector similarity threshold for cluster iad01');
                  }}
                  className={`py-2 px-2 rounded font-mono text-[11px] transition-all text-center border border-[#3b494b]/40 cursor-pointer ${
                    feedbackGiven
                      ? 'bg-[#272a30] text-[#7fecde]'
                      : 'bg-[#272a30] hover:bg-[#36393f] text-[#b9cacb] hover:text-[#e0e2ea]'
                  }`}
                >
                  {feedbackGiven ? 'Feedback Recorded ✓' : 'Reject / Feedback'}
                </button>

                <button
                  onClick={() => {
                    setEscalated(true);
                    showToast('Sev-1 Escalation broadcast dispatched to #incident-payment-core on Slack & PagerDuty.');
                  }}
                  className={`py-2 px-2 rounded font-mono text-[11px] font-semibold transition-all text-center border border-[#ffb4ab]/40 cursor-pointer ${
                    escalated
                      ? 'bg-[#93000a] text-[#ffdad6]'
                      : 'bg-[#93000a]/30 hover:bg-[#93000a] text-[#ffb4ab] hover:text-[#ffdad6]'
                  }`}
                >
                  {escalated ? 'Escalated to Slack ✓' : 'Escalate to Payment Core'}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Precedent Inspection Modal */}
      {selectedPrecedent && (
        <PrecedentDetailModal
          precedent={selectedPrecedent}
          onClose={() => setSelectedPrecedent(null)}
          onApplyHypothesis={(prec) => {
            showToast(`Precedent ${prec.id} linked as primary grounding anchor.`);
          }}
        />
      )}

      {/* Dispatch Runbook Execution Modal */}
      {isDispatchModalOpen && (
        <DispatchRunbookModal
          actions={RECOMMENDED_RUNBOOK_ACTIONS}
          onClose={() => setIsDispatchModalOpen(false)}
          onExecuteAction={(actId) => {
            showToast(`Dispatched action ${actId} in cluster.`);
          }}
          onExecuteAll={() => {
            showToast('3-Step plan executed! P99 latency dropping back to baseline...');
          }}
        />
      )}
    </div>
  );
};
