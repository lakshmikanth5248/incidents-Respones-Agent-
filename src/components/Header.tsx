import React, { useState, useEffect } from 'react';

interface HeaderProps {
  onIncidentClick?: () => void;
  onProfileClick?: () => void;
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onIncidentClick,
  onProfileClick,
  onToggleSidebar,
}) => {
  const [utcTime, setUtcTime] = useState<string>('');
  const [syncSeconds, setSyncSeconds] = useState<number>(4);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hours = String(now.getUTCHours()).padStart(2, '0');
      const minutes = String(now.getUTCMinutes()).padStart(2, '0');
      const seconds = String(now.getUTCSeconds()).padStart(2, '0');
      setUtcTime(`UTC ${hours}:${minutes}:${seconds}`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setSyncSeconds((prev) => (prev >= 12 ? 1 : prev + 1));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="fixed top-0 left-0 right-0 h-16 z-50 bg-[#0b0e13]/90 backdrop-blur-xl border-b border-[#3b494b]/30 shadow-[0_1px_12px_rgba(0,0,0,0.5)]">
      <div className="h-16 w-full px-4 md:px-6 flex items-center justify-between gap-3">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-3 shrink-0">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="lg:hidden p-1.5 rounded hover:bg-surface-container text-on-surface-variant"
              aria-label="Toggle navigation"
            >
              <span className="material-symbols-outlined text-[20px]">menu</span>
            </button>
          )}

          <img
            alt="Aegis Command Emblem"
            className="h-8 w-auto object-contain drop-shadow-[0_0_8px_rgba(0,240,255,0.4)]"
            src="https://lh3.googleusercontent.com/aida/AEtjO1W2YjyToyzAKSH7eXM6qMzMWjBT8gn-VWBjFH3qnKZRAgGCi9Nwpq5BKMi0HjAychva1EAm3MOXoT0v0ImBdNCKsfxcS0VHqrYsIgoImc4YPbS2k3dwoy_VgRM4rOJR8TffDRRIi0NsizNhRjpJfYlwbaAkFVFOB97BljNO5bIw777q737u1kb-T1fsmkm1eNXmbsA1h8h6nnrLdGsTUnNs1Ll7d1Uq5S7dWJAxZq5BZMw9WIBgY4GLFqHV"
          />

          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-[15px] text-[#dbfcff] tracking-wider uppercase">
                AEGIS COMMAND
              </span>
              <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-[#272a30] text-[10px] font-mono text-[#b9cacb] border border-[#3b494b]/40">
                CLASSIFICATION: PRODUCTION SRE
              </span>
            </div>
            <span className="text-[11px] font-mono text-[#b9cacb] tracking-wide">
              AI INCIDENT RESPONSE &amp; HINDSIGHT ENGINE
            </span>
          </div>
        </div>

        {/* Center: System Telemetry Status Rack */}
        <div className="hidden xl:flex items-center gap-4 px-3.5 py-1.5 rounded bg-[#181c21] border border-[#3b494b]/40 shadow-[0_0_8px_rgba(0,240,255,0.05)]">
          <div className="flex items-center gap-3 text-[11px] font-mono">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#7fecde] animate-pulse" />
              <span className="text-[#d3fff7]">SYSTEM OPERATIONAL</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-pulse" />
              <span className="text-[#dbfcff]">AGENT ONLINE</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#00a6e0] animate-pulse" />
              <span className="text-[#7bd0ff]">HINDSIGHT CONNECTED</span>
            </div>
          </div>

          <div className="h-4 w-px bg-[#3b494b]" />

          <div className="flex items-center gap-2 text-[11px] font-mono text-[#b9cacb]">
            <span>
              Cluster: <span className="text-[#e0e2ea] font-medium">us-east-prod-k8s</span>
            </span>
            <span>•</span>
            <span>
              Latency: <span className="text-[#00f0ff] font-semibold">14ms</span>
            </span>
            <span>•</span>
            <span>
              Last Sync: <span className="text-[#e0e2ea]">{syncSeconds}s ago</span>
            </span>
          </div>
        </div>

        {/* Right: Real-time Incident Alert & Time */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden md:flex flex-col items-end">
            <span className="text-[13px] font-mono text-[#e0e2ea] font-bold tracking-tight">
              {utcTime || 'UTC 14:26:08'}
            </span>
            <span className="text-[11px] font-mono text-[#b9cacb]">
              SRE On-Call: <span className="text-[#00f0ff] font-medium">D. Mercer</span>
            </span>
          </div>

          {/* Active Incident Warning Badge */}
          <button
            onClick={onIncidentClick}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#93000a] text-[#ffdad6] border border-[#ffb4ab]/40 shadow-[0_0_10px_rgba(147,0,10,0.45)] hover:bg-[#93000a]/90 transition-all cursor-pointer"
            title="Click to jump to INC-2048"
          >
            <span className="material-symbols-outlined text-[#ffb4ab] text-[16px] animate-pulse">
              warning
            </span>
            <span className="text-[11px] font-mono font-bold tracking-tight text-[#ffdad6]">
              INC-2048 HIGH SEVERITY
            </span>
          </button>

          {/* User Profile */}
          <button
            onClick={onProfileClick}
            className="w-8 h-8 rounded-full bg-[#dbfcff] hover:bg-[#00f0ff] flex items-center justify-center shrink-0 transition-colors shadow-sm"
            title="SRE Operator Profile: D. Mercer"
          >
            <span className="material-symbols-outlined text-[#00363a] text-[18px]">
              person
            </span>
          </button>
        </div>
      </div>
    </header>
  );
};
