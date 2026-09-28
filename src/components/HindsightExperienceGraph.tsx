import React, { useState } from 'react';
import { HISTORICAL_PRECEDENTS } from '../data/mockData';
import { MemoryPrecedent } from '../types';
import { PrecedentDetailModal } from './PrecedentDetailModal';

interface HindsightExperienceGraphProps {
  onSelectPrecedentForIncident?: (precedent: MemoryPrecedent) => void;
  onNavigateToWorkspace?: () => void;
}

export const HindsightExperienceGraph: React.FC<HindsightExperienceGraphProps> = ({
  onSelectPrecedentForIncident,
  onNavigateToWorkspace,
}) => {
  const [selectedDomain, setSelectedDomain] = useState<string>('All');
  const [selectedHorizon, setSelectedHorizon] = useState<string>('All Time');
  const [selectedConfidence, setSelectedConfidence] = useState<string>('High >0.85');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [pinnedPrecedentId, setPinnedPrecedentId] = useState<string>('INC-1987');
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [appliedNotification, setAppliedNotification] = useState<string | null>(null);
  const [queryModalOpen, setQueryModalOpen] = useState<boolean>(false);

  const pinnedPrecedent: MemoryPrecedent =
    HISTORICAL_PRECEDENTS.find((p) => p.id === pinnedPrecedentId) ||
    HISTORICAL_PRECEDENTS[0];

  const filteredPrecedents = HISTORICAL_PRECEDENTS.filter((item) => {
    const matchesDomain = selectedDomain === 'All' || item.domain === selectedDomain;
    const matchesSearch =
      searchQuery === '' ||
      item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.rootCause.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.retainedExperience.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesDomain && matchesSearch;
  });

  const handleApplyHypothesis = () => {
    setAppliedNotification('Hypothesis Linked to INC-2048!');
    if (onSelectPrecedentForIncident) {
      onSelectPrecedentForIncident(pinnedPrecedent);
    }
    setTimeout(() => setAppliedNotification(null), 3000);
  };

  const handleZoom = (delta: number) => {
    setZoomLevel((prev) => Math.min(Math.max(prev + delta, 0.7), 1.8));
  };

  const handleResetView = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  return (
    <div className="flex flex-col w-full gap-4 relative animate-fade-in">
      {/* Toast */}
      {appliedNotification && (
        <div className="fixed top-20 right-6 z-50 bg-[#1d2025] border border-[#00f0ff] px-4 py-2.5 rounded-lg shadow-[0_0_20px_rgba(0,240,255,0.5)] text-[12px] font-mono text-[#00f0ff] flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">verified</span>
          <span>{appliedNotification}</span>
        </div>
      )}

      {/* HUD Sub-Header */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0b0e13] p-4 rounded-xl border border-[#3b494b]/40 shadow-xl relative overflow-hidden">
          <div className="absolute -right-16 -top-16 w-64 h-64 bg-[#00f0ff]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="flex flex-col gap-1 z-10">
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded bg-[#272a30] font-mono text-[10px] text-[#dbfcff] tracking-widest uppercase border border-[#3b494b]/40">
                EVIDENCE LAYER 04
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-[#00f0ff] animate-ping" />
              <span className="font-mono text-[11px] text-[#b9cacb] uppercase tracking-wider">
                GRAPH RUNTIME: HYPERGRAPH v4.9
              </span>
            </div>
            <h1 className="text-[28px] font-bold text-[#dbfcff] tracking-tight">
              HINDSIGHT MEMORY
            </h1>
            <p className="text-[14px] text-[#b9cacb] max-w-2xl">
              Long-Term Incident Experience Graph &amp; Spatial Knowledge Constellation
            </p>
          </div>

          <div className="flex flex-col md:flex-row items-start md:items-center gap-3 z-10">
            <div className="bg-[#272a30]/80 border border-[#3b494b]/40 p-2.5 rounded-lg flex items-center gap-3 shadow-sm">
              <div className="flex flex-col">
                <span className="font-mono text-[10px] text-[#b9cacb] uppercase">
                  SYNAPSE TRAFFIC
                </span>
                <span className="font-mono text-[16px] font-bold text-[#7fecde]">
                  3,412/sec
                </span>
              </div>
              <div className="h-8 w-px bg-[#3b494b]/60" />
              <div className="flex flex-col">
                <span className="font-mono text-[10px] text-[#b9cacb] uppercase">
                  TARGET SEED
                </span>
                <span className="font-mono text-[12px] text-[#7bd0ff] font-bold">
                  INC-2048 (ACTIVE)
                </span>
              </div>
            </div>

            <button
              onClick={() => setQueryModalOpen(true)}
              className="bg-[#00f0ff] text-[#00363a] font-semibold text-[14px] px-4 py-2.5 rounded-lg shadow-[0_0_16px_rgba(0,240,255,0.3)] hover:bg-[#7df4ff] transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">neurology</span>
              <span>Query Constellation</span>
            </button>
          </div>
        </div>

        {/* Telemetry Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-[#181c21] p-2 rounded-lg border border-[#3b494b]/40 shadow-sm">
          <div className="flex items-center gap-3 px-3 py-1">
            <span className="material-symbols-outlined text-[#00f0ff] text-[20px]">layers</span>
            <div className="flex flex-col">
              <span className="font-mono text-[10px] text-[#b9cacb] uppercase">INDEXED POST-MORTEMS</span>
              <span className="font-mono text-[14px] text-[#e0e2ea] font-bold">14,892 Nodes</span>
            </div>
          </div>
          <div className="flex items-center gap-3 px-3 py-1">
            <span className="material-symbols-outlined text-[#7bd0ff] text-[20px]">category</span>
            <div className="flex flex-col">
              <span className="font-mono text-[10px] text-[#b9cacb] uppercase">FAILURE ARCHETYPES</span>
              <span className="font-mono text-[14px] text-[#e0e2ea] font-bold">412 Profiles</span>
            </div>
          </div>
          <div className="flex items-center gap-3 px-3 py-1">
            <span className="material-symbols-outlined text-[#7fecde] text-[20px]">bolt</span>
            <div className="flex flex-col">
              <span className="font-mono text-[10px] text-[#b9cacb] uppercase">RECALL UTILITY</span>
              <span className="font-mono text-[14px] text-[#7fecde] font-bold">89.4% Validated</span>
            </div>
          </div>
          <div className="flex items-center gap-3 px-3 py-1">
            <span className="material-symbols-outlined text-[#849495] text-[20px]">update</span>
            <div className="flex flex-col">
              <span className="font-mono text-[10px] text-[#b9cacb] uppercase">LAST SYNC INGESTION</span>
              <span className="font-mono text-[12px] text-[#e0e2ea]">
                INC-2045 <span className="text-[#b9cacb] text-[10px]">(42m ago)</span>
              </span>
            </div>
          </div>
        </div>

        {/* Filter Multi-Rack */}
        <div className="bg-[#1d2025] p-2.5 rounded-lg border border-[#3b494b]/40 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[11px] text-[#b9cacb] uppercase mr-1">
              CLUSTER DOMAIN:
            </span>
            {[
              'All',
              'Payment & Billing',
              'Authentication & IAM',
              'Database & Storage',
              'Network & Mesh',
              'Deployment & Rollouts',
            ].map((domain) => (
              <button
                key={domain}
                onClick={() => setSelectedDomain(domain)}
                className={`px-3 py-1 rounded font-mono text-[11px] transition-all cursor-pointer ${
                  selectedDomain === domain
                    ? 'bg-[#00f0ff] text-[#00363a] font-bold shadow-[0_0_8px_rgba(0,240,255,0.25)]'
                    : 'bg-[#272a30] text-[#b9cacb] hover:text-[#e0e2ea]'
                }`}
              >
                {domain}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[10px] text-[#b9cacb] uppercase">HORIZON:</span>
              <div className="flex bg-[#0b0e13] p-0.5 rounded border border-[#3b494b]/30">
                {['All Time', '90 Days', '1 Year'].map((h) => (
                  <button
                    key={h}
                    onClick={() => setSelectedHorizon(h)}
                    className={`px-2 py-0.5 rounded font-mono text-[10px] ${
                      selectedHorizon === h ? 'bg-[#272a30] text-[#00f0ff]' : 'text-[#b9cacb] hover:text-[#e0e2ea]'
                    }`}
                  >
                    {h}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[10px] text-[#b9cacb] uppercase">CONFIDENCE:</span>
              <div className="flex bg-[#0b0e13] p-0.5 rounded border border-[#3b494b]/30">
                {['High >0.85', 'Mod >0.65'].map((c) => (
                  <button
                    key={c}
                    onClick={() => setSelectedConfidence(c)}
                    className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                      selectedConfidence === c
                        ? 'bg-[#00f0ff] text-[#00363a]'
                        : 'text-[#b9cacb] hover:text-[#e0e2ea]'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SPATIAL MEMORY CONSTELLATION (Top 60% Section) */}
      <div className="relative w-full h-[580px] bg-[#0b0e13] rounded-xl border border-[#3b494b]/40 shadow-2xl overflow-hidden">
        {/* Starfield & Vector Grid HUD Overlay */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#181c21] via-[#0b0e13] to-[#0b0e13] opacity-90" />
        <div
          className="absolute inset-0 opacity-15 pointer-events-none"
          style={{
            backgroundImage:
              'linear-gradient(to right, #3b494b 1px, transparent 1px), linear-gradient(to bottom, #3b494b 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        {/* Holographic Constellation Interactive Canvas (SVG) */}
        <svg
          className="absolute inset-0 w-full h-full select-none"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 1100 580"
          style={{
            transform: `scale(${zoomLevel}) translate(${panOffset.x}px, ${panOffset.y}px)`,
            transformOrigin: 'center center',
            transition: 'transform 0.2s ease-out',
          }}
        >
          <defs>
            <filter id="glow-cyan" width="200%" height="200%" x="-50%" y="-50%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="glow-gold" width="200%" height="200%" x="-50%" y="-50%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <linearGradient id="link-grad-active" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00f0ff" stopOpacity="1" />
              <stop offset="50%" stopColor="#7bd0ff" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#ffb4ab" stopOpacity="1" />
            </linearGradient>
            <linearGradient id="cluster-db" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#7bd0ff" stopOpacity="0.1" />
              <stop offset="100%" stopColor="#1d2025" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Cluster Boundary Regions */}
          {/* DB Cluster */}
          <path
            d="M 120 180 Q 240 100 360 160 T 420 340 T 260 420 T 100 300 Z"
            fill="url(#cluster-db)"
            stroke="#3b494b"
            strokeDasharray="3,3"
            strokeWidth="0.8"
          />
          <text fill="#7bd0ff" fontFamily="JetBrains Mono" fontSize="10" letterSpacing="1.5" x="140" y="150">
            CLUSTER 01 :: DATABASE &amp; STORAGE
          </text>

          {/* Auth Cluster */}
          <path
            d="M 440 80 Q 560 40 680 90 T 720 220 T 580 260 T 420 190 Z"
            fill="#00f0ff"
            fillOpacity="0.03"
            stroke="#3b494b"
            strokeDasharray="3,3"
            strokeWidth="0.8"
          />
          <text fill="#7fecde" fontFamily="JetBrains Mono" fontSize="10" letterSpacing="1.5" x="460" y="60">
            CLUSTER 02 :: AUTH &amp; IAM
          </text>

          {/* Networking Mesh Cluster */}
          <path
            d="M 680 280 Q 860 210 1020 260 T 1040 460 T 820 520 T 660 420 Z"
            fill="#006970"
            fillOpacity="0.05"
            stroke="#3b494b"
            strokeDasharray="3,3"
            strokeWidth="0.8"
          />
          <text fill="#849495" fontFamily="JetBrains Mono" fontSize="10" letterSpacing="1.5" x="740" y="240">
            CLUSTER 03 :: NETWORKING MESH
          </text>

          {/* Payment Cluster Boundary */}
          <circle
            cx="340"
            cy="360"
            r="160"
            fill="#00f0ff"
            fillOpacity="0.04"
            stroke="#00dbe9"
            strokeDasharray="4,4"
            strokeWidth="0.75"
          />
          <text fill="#00f0ff" fontFamily="JetBrains Mono" fontSize="11" fontWeight="600" letterSpacing="2" x="240" y="525">
            CLUSTER 04 :: PAYMENT &amp; BILLING PIPELINES
          </text>

          {/* Synaptic Inter-Node Mesh Vectors */}
          <g opacity="0.6" stroke="#3b494b" strokeWidth="0.7">
            <line x1="220" y1="240" x2="340" y2="340" />
            <line x1="280" y1="180" x2="340" y2="340" />
            <line x1="160" y1="310" x2="260" y2="380" />
            <line x1="480" y1="140" x2="620" y2="120" />
            <line x1="560" y1="210" x2="480" y2="140" />
            <line x1="620" y1="120" x2="780" y2="320" />
            <line x1="780" y1="320" x2="880" y2="280" />
            <line x1="880" y1="280" x2="960" y2="360" />
            <line x1="780" y1="320" x2="820" y2="440" />
            <line x1="340" y1="340" x2="480" y2="390" />
          </g>

          {/* DB Nodes */}
          <g className="cursor-pointer" onClick={() => setPinnedPrecedentId('INC-1842')}>
            <circle cx="220" cy="240" r="5" fill="#7bd0ff" opacity="0.8" />
            <text fill="#b9cacb" fontFamily="JetBrains Mono" fontSize="10" x="230" y="244">
              INC-1842
            </text>
          </g>
          <g className="cursor-pointer" onClick={() => setPinnedPrecedentId('INC-1601')}>
            <circle cx="280" cy="180" r="4.5" fill="#7bd0ff" opacity="0.7" />
            <text fill="#849495" fontFamily="JetBrains Mono" fontSize="9" x="290" y="184">
              INC-1601
            </text>
          </g>
          <circle cx="160" cy="310" r="3" fill="#7bd0ff" opacity="0.5" />

          {/* Auth Nodes */}
          <g className="cursor-pointer" onClick={() => setPinnedPrecedentId('INC-1721')}>
            <circle cx="480" cy="140" r="6" fill="#7fecde" opacity="0.9" />
            <text fill="#b9cacb" fontFamily="JetBrains Mono" fontSize="10" x="492" y="144">
              INC-1721
            </text>
          </g>
          <circle cx="620" cy="120" r="3.5" fill="#7fecde" opacity="0.6" />
          <text fill="#849495" fontFamily="JetBrains Mono" fontSize="9" x="630" y="124">
            INC-1502
          </text>
          <circle cx="560" cy="210" r="4" fill="#7fecde" opacity="0.5" />

          {/* Network Nodes */}
          <g className="cursor-pointer" onClick={() => setPinnedPrecedentId('INC-1590')}>
            <circle cx="780" cy="320" r="5.5" fill="#849495" opacity="0.8" />
            <text fill="#b9cacb" fontFamily="JetBrains Mono" fontSize="10" x="792" y="324">
              INC-1590
            </text>
          </g>
          <g className="cursor-pointer" onClick={() => setPinnedPrecedentId('INC-1402')}>
            <circle cx="880" cy="280" r="5" fill="#849495" opacity="0.8" />
            <text fill="#849495" fontFamily="JetBrains Mono" fontSize="10" x="892" y="284">
              INC-1402
            </text>
          </g>
          <circle cx="960" cy="360" r="3" fill="#849495" opacity="0.5" />
          <circle cx="820" cy="440" r="3.5" fill="#849495" opacity="0.6" />

          {/* Selected Pinned Node: INC-1987 */}
          <g
            className="cursor-pointer transition-transform hover:scale-110"
            onClick={() => setPinnedPrecedentId('INC-1987')}
          >
            <circle cx="340" cy="340" r="14" fill="#00f0ff" fillOpacity="0.18" />
            <circle cx="340" cy="340" r="7" fill="#00f0ff" filter="url(#glow-cyan)" />
            <circle cx="340" cy="340" r="2.5" fill="#002022" />
            <text fill="#00f0ff" fontFamily="JetBrains Mono" fontSize="13" fontWeight="700" x="360" y="338">
              INC-1987
            </text>
            <text fill="#7bd0ff" fontFamily="JetBrains Mono" fontSize="9" x="360" y="352">
              PAYMENT PROXY LOCK (96% MATCH)
            </text>
          </g>

          {/* Active Command Incident Node: INC-2048 */}
          <g
            className="cursor-pointer"
            onClick={() => {
              if (onNavigateToWorkspace) onNavigateToWorkspace();
            }}
          >
            <circle cx="560" cy="460" r="22" fill="#ffb4ab" fillOpacity="0.15" />
            <circle
              cx="560"
              cy="460"
              r="8"
              fill="#ffb4ab"
              filter="url(#glow-gold)"
              stroke="#93000a"
              strokeWidth="2"
            />
            <circle cx="560" cy="460" r="3" fill="#690005" />
            <text fill="#ffb4ab" fontFamily="JetBrains Mono" fontSize="13" fontWeight="700" x="580" y="458">
              INC-2048 [ACTIVE TRIAGE]
            </text>
            <text fill="#e0e2ea" fontFamily="JetBrains Mono" fontSize="9" x="580" y="472">
              SEV-1 CHECKOUT TIMEOUTS
            </text>
          </g>

          {/* CRITICAL ACTIVATION LINK: INC-1987 -> INC-2048 */}
          <line
            className="animate-pulse"
            filter="url(#glow-cyan)"
            stroke="url(#link-grad-active)"
            strokeDasharray="6,4"
            strokeWidth="2.5"
            x1="340"
            y1="340"
            x2="560"
            y2="460"
          />

          {/* Synapse Vector Pulse Indicator */}
          <circle cx="450" cy="400" r="3.5" fill="#00f0ff" filter="url(#glow-cyan)" className="animate-ping" />
        </svg>

        {/* Canvas HUD Controls (Top Left of Map) */}
        <div className="absolute top-4 left-4 flex flex-col gap-2 z-20">
          <div className="bg-[#272a30]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#00f0ff]/30 flex items-center gap-2.5 shadow-md">
            <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-ping" />
            <span className="font-mono text-[11px] text-[#00f0ff] font-bold">
              REASONING BRIDGE ACTIVE
            </span>
            <span className="text-[#b9cacb] font-mono text-[11px]">
              · Sim Score: 0.962
            </span>
          </div>

          <div className="flex items-center gap-1 bg-[#1d2025]/90 p-1 rounded-lg border border-[#3b494b]/40 w-fit backdrop-blur-sm">
            <button
              onClick={() => handleZoom(0.15)}
              className="w-7 h-7 bg-[#32353b] hover:bg-[#36393f] rounded flex items-center justify-center text-[#e0e2ea] transition-colors cursor-pointer"
              title="Zoom In"
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
            </button>
            <button
              onClick={() => handleZoom(-0.15)}
              className="w-7 h-7 bg-[#32353b] hover:bg-[#36393f] rounded flex items-center justify-center text-[#e0e2ea] transition-colors cursor-pointer"
              title="Zoom Out"
            >
              <span className="material-symbols-outlined text-[16px]">remove</span>
            </button>
            <button
              onClick={handleResetView}
              className="w-7 h-7 bg-[#32353b] hover:bg-[#36393f] rounded flex items-center justify-center text-[#e0e2ea] transition-colors cursor-pointer"
              title="Reset View"
            >
              <span className="material-symbols-outlined text-[16px]">center_focus_strong</span>
            </button>
          </div>
        </div>

        {/* Overlay: Selected Memory Card (Pinned Right HUD Drawer) */}
        <div className="absolute top-4 right-4 bottom-4 w-full max-w-[440px] bg-[#272a30]/95 backdrop-blur-xl p-4 rounded-xl border border-[#00f0ff]/30 shadow-2xl flex flex-col z-20 overflow-y-auto">
          {/* Card Top Badge Bar */}
          <div className="flex items-center justify-between gap-2 pb-2 mb-2 bg-[#32353b]/40 p-2 rounded-lg border border-[#3b494b]/30">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">
                verified
              </span>
              <span className="font-mono text-[11px] font-bold text-[#00f0ff] uppercase tracking-wider">
                HISTORICAL PRECEDENT PIN
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-[#7fecde]/20 text-[#7fecde] font-mono text-[11px] font-bold">
                RECALL UTILITY: {pinnedPrecedent.utilityScore}%
              </span>
              <button
                onClick={() => setIsModalOpen(true)}
                className="text-[#b9cacb] hover:text-[#e0e2ea]"
                title="Open detailed report"
              >
                <span className="material-symbols-outlined text-[18px]">open_in_new</span>
              </button>
            </div>
          </div>

          {/* Incident Header */}
          <div className="flex flex-col gap-1 mb-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[18px] text-[#dbfcff] font-bold">
                {pinnedPrecedent.id}
              </span>
              <span className="px-2 py-0.5 rounded bg-[#0b0e13] font-mono text-[10px] text-[#7bd0ff] border border-[#3b494b]/40">
                {pinnedPrecedent.domain}
              </span>
              <span className="font-mono text-[11px] text-[#b9cacb]">
                {pinnedPrecedent.date}
              </span>
            </div>
            <h3 className="text-[15px] font-semibold text-[#e0e2ea]">
              {pinnedPrecedent.title}
            </h3>
          </div>

          {/* Experience Anatomy Sections */}
          <div className="flex flex-col gap-2 flex-1">
            {/* WHAT HAPPENED */}
            <div className="bg-[#1d2025] p-2.5 rounded border border-[#3b494b]/30">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="material-symbols-outlined text-[#ffb4ab] text-[15px]">crisis_alert</span>
                <span className="font-mono text-[10px] text-[#ffb4ab] font-bold uppercase tracking-wider">
                  WHAT HAPPENED
                </span>
              </div>
              <p className="text-[12px] text-[#e0e2ea] leading-relaxed">
                {pinnedPrecedent.whatHappened}
              </p>
            </div>

            {/* INVESTIGATION */}
            <div className="bg-[#1d2025] p-2.5 rounded border border-[#3b494b]/30">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="material-symbols-outlined text-[#7bd0ff] text-[15px]">troubleshoot</span>
                <span className="font-mono text-[10px] text-[#7bd0ff] font-bold uppercase tracking-wider">
                  AGENT INVESTIGATION
                </span>
              </div>
              <p className="text-[12px] text-[#e0e2ea] leading-relaxed">
                {pinnedPrecedent.agentInvestigation}
              </p>
            </div>

            {/* RESPONSE */}
            <div className="bg-[#1d2025] p-2.5 rounded border border-[#3b494b]/30">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="material-symbols-outlined text-[#7fecde] text-[15px]">bolt</span>
                <span className="font-mono text-[10px] text-[#7fecde] font-bold uppercase tracking-wider">
                  EXECUTED RESPONSE
                </span>
              </div>
              <p className="text-[12px] text-[#e0e2ea] leading-relaxed">
                {pinnedPrecedent.executedResponse}
              </p>
            </div>

            {/* OUTCOME */}
            <div className="bg-[#1d2025] p-2.5 rounded border border-[#3b494b]/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#7fecde] text-[15px]">check_circle</span>
                  <span className="font-mono text-[10px] text-[#7fecde] font-bold uppercase tracking-wider">
                    VERIFIED OUTCOME
                  </span>
                </div>
                <span className="font-mono text-[11px] text-[#7fecde] font-bold">
                  MTTR: {pinnedPrecedent.mttrMinutes} MIN
                </span>
              </div>
              <p className="text-[12px] text-[#e0e2ea] mt-1">
                {pinnedPrecedent.verifiedOutcome}
              </p>
            </div>

            {/* RETAINED EXPERIENCE FOR FUTURE */}
            <div className="bg-[#00f0ff]/10 p-3 rounded border border-[#00f0ff]/40 shadow-sm">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="material-symbols-outlined text-[#00f0ff] text-[16px]">psychology</span>
                <span className="font-mono text-[10px] text-[#00f0ff] font-bold uppercase tracking-wider">
                  RETAINED EXPERIENCE RULE
                </span>
              </div>
              <p className="text-[13px] text-[#dbfcff] font-medium italic leading-snug">
                “{pinnedPrecedent.retainedExperience}”
              </p>
            </div>

            {/* Live Projection to INC-2048 */}
            <div className="bg-[#0b0e13] p-2 rounded border border-[#3b494b]/40 flex items-center justify-between mt-1">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#00f0ff] animate-pulse" />
                <span className="font-mono text-[11px] text-[#b9cacb]">
                  Active Target Match:
                </span>
                <span className="font-mono text-[11px] text-[#00f0ff] font-bold">
                  INC-2048
                </span>
              </div>

              <button
                onClick={handleApplyHypothesis}
                className="bg-[#272a30] hover:bg-[#32353b] px-3 py-1 rounded font-mono text-[11px] text-[#00f0ff] border border-[#00f0ff]/40 transition-colors cursor-pointer"
              >
                Apply Hypothesis
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* HISTORICAL INCIDENT MEMORY CATALOG (Bottom 40% Matrix) */}
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#00f0ff] text-[20px]">
              database
            </span>
            <h2 className="text-[18px] font-semibold text-[#e0e2ea]">
              Historical Incident Memory Catalog
            </h2>
            <span className="px-2 py-0.5 rounded bg-[#1d2025] font-mono text-[11px] text-[#b9cacb] border border-[#3b494b]/30">
              Showing {filteredPrecedents.length} Ranked Precedents
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-[#1d2025] border border-[#3b494b]/40 px-3 py-1.5 rounded-lg">
              <span className="material-symbols-outlined text-[16px] text-[#b9cacb]">search</span>
              <input
                type="text"
                placeholder="Filter memory signatures..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent font-mono text-[11px] text-[#e0e2ea] placeholder:text-[#849495] focus:outline-none w-52"
              />
            </div>

            <button
              onClick={() => {
                // sort or shuffle
              }}
              className="bg-[#1d2025] hover:bg-[#272a30] border border-[#3b494b]/40 px-3 py-1.5 rounded-lg font-mono text-[11px] text-[#e0e2ea] flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">tune</span>
              <span>Sort: Relevance Score</span>
            </button>
          </div>
        </div>

        {/* Matrix Table Container */}
        <div className="w-full overflow-x-auto bg-[#0b0e13] rounded-xl border border-[#3b494b]/40 shadow-xl">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-[#181c21] text-[#b9cacb] font-mono text-[10px] uppercase border-b border-[#3b494b]/40">
                <th className="py-2.5 px-4">Incident ID</th>
                <th className="py-2.5 px-4">Class Domain</th>
                <th className="py-2.5 px-4">Incident Title</th>
                <th className="py-2.5 px-4">Root Cause Category</th>
                <th className="py-2.5 px-4 min-w-[280px]">Retained Experience Lesson</th>
                <th className="py-2.5 px-4 text-center">Future Recalls</th>
                <th className="py-2.5 px-4 text-center">Utility Score</th>
                <th className="py-2.5 px-4 text-right">Precedent Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3b494b]/20 font-mono text-[11px] text-[#e0e2ea]">
              {filteredPrecedents.map((item) => {
                const isPinned = item.id === pinnedPrecedentId;
                return (
                  <tr
                    key={item.id}
                    onClick={() => setPinnedPrecedentId(item.id)}
                    className={`transition-colors cursor-pointer ${
                      isPinned
                        ? 'bg-[#272a30]/80 border-l-2 border-[#00f0ff]'
                        : 'bg-[#181c21]/40 hover:bg-[#1d2025]'
                    }`}
                  >
                    <td className="py-3 px-4 text-[#00f0ff] font-bold">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            isPinned ? 'bg-[#00f0ff]' : 'bg-[#3b494b]'
                          }`}
                        />
                        <span>{item.id}</span>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-[#181c21] text-[#7bd0ff] border border-[#3b494b]/30">
                        {item.domain}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-[#e0e2ea] font-medium font-sans text-[13px]">
                      {item.title}
                    </td>

                    <td className="py-3 px-4 text-[#b9cacb]">
                      {item.rootCause}
                    </td>

                    <td className="py-3 px-4">
                      <p className="line-clamp-2 text-[#e0e2ea] font-sans text-[12px]">
                        {item.retainedExperience}
                      </p>
                    </td>

                    <td className="py-3 px-4 text-center text-[#e0e2ea] font-bold">
                      {item.recallsCount}x
                    </td>

                    <td className="py-3 px-4 text-center">
                      <span className="px-2 py-0.5 rounded bg-[#7fecde]/20 text-[#7fecde] font-bold">
                        {item.utilityScore}%
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setPinnedPrecedentId(item.id);
                          setIsModalOpen(true);
                        }}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-all ${
                          isPinned
                            ? 'bg-[#00f0ff]/20 text-[#00f0ff] border border-[#00f0ff]/40 hover:bg-[#00f0ff] hover:text-[#00363a]'
                            : 'bg-[#272a30] text-[#b9cacb] hover:text-[#dbfcff] border border-[#3b494b]/30'
                        }`}
                      >
                        {isPinned ? 'Inspected' : 'Inspect Precedent'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Matrix Footer Pagination / Status Bar */}
          <div className="p-3 bg-[#181c21] border-t border-[#3b494b]/30 flex flex-wrap items-center justify-between text-[#b9cacb] font-mono text-[11px]">
            <div className="flex items-center gap-2">
              <span>Cluster State: <strong className="text-[#7fecde]">STABLE EMBEDDINGS</strong></span>
              <span>•</span>
              <span>Vector Distance: <strong className="text-[#00f0ff]">COSINE L2</strong></span>
              <span>•</span>
              <span>Total Precedent Depth: 14,892 Records</span>
            </div>

            <div className="flex items-center gap-1.5">
              <button className="px-2 py-0.5 rounded bg-[#1d2025] hover:bg-[#272a30] text-[#e0e2ea] border border-[#3b494b]/30">
                &lt;
              </button>
              <span className="px-2 py-0.5 text-[#e0e2ea]">Page 1 of 2,978</span>
              <button className="px-2 py-0.5 rounded bg-[#1d2025] hover:bg-[#272a30] text-[#e0e2ea] border border-[#3b494b]/30">
                &gt;
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Precedent Detail Modal */}
      {isModalOpen && (
        <PrecedentDetailModal
          precedent={pinnedPrecedent}
          onClose={() => setIsModalOpen(false)}
          onApplyHypothesis={handleApplyHypothesis}
        />
      )}

      {/* Query Constellation Interactive Dialog */}
      {queryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="w-full max-w-xl bg-[#111827] border border-[#00f0ff]/40 rounded-xl p-5 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#00f0ff] text-[20px]">psychology</span>
                <h3 className="text-[16px] font-bold text-[#dbfcff]">HyperGraph Semantic Query Console</h3>
              </div>
              <button onClick={() => setQueryModalOpen(false)} className="text-[#b9cacb] hover:text-[#e0e2ea]">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <p className="text-[12px] text-[#b9cacb]">
              Execute cosine similarity distance queries against the 14,892 node historical post-mortem vector corpus.
            </p>
            <div className="space-y-2">
              <label className="text-[11px] font-mono text-[#00f0ff] uppercase">Target Vector Query:</label>
              <textarea
                defaultValue="socket timeout spike without CPU increase on payment proxy worker threads"
                rows={3}
                className="w-full p-2.5 rounded bg-[#0b0e13] border border-[#3b494b] font-mono text-[12px] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setQueryModalOpen(false)}
                className="px-3 py-1.5 rounded bg-[#272a30] text-[#b9cacb] text-[12px] font-mono"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setQueryModalOpen(false);
                  setPinnedPrecedentId('INC-1987');
                  setAppliedNotification('Found Top Match: INC-1987 with 96.2% similarity score!');
                }}
                className="px-4 py-1.5 rounded bg-[#00f0ff] text-[#00363a] font-bold text-[12px] font-mono shadow-[0_0_12px_rgba(0,240,255,0.4)]"
              >
                Execute Vector Search
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
