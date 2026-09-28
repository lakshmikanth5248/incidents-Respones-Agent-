import React from 'react';

interface ConfidenceScoreIndicatorProps {
  score: number; // e.g., 98 or 91.4
  vectorSim?: number; // e.g., 91.4
  symptomMatch?: number; // e.g., 98
  topologyMatch?: number; // e.g., 94
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  showDetails?: boolean;
  className?: string;
}

export const ConfidenceScoreIndicator: React.FC<ConfidenceScoreIndicatorProps> = ({
  score,
  vectorSim = 91.4,
  symptomMatch = 98,
  topologyMatch = 94,
  label = 'Confidence Score',
  size = 'md',
  showDetails = true,
  className = '',
}) => {
  const roundedScore = Math.round(score);
  // SVG radius 15.9155 gives a circumference of exactly 100
  const strokeDash = `${Math.min(100, Math.max(0, roundedScore))}, 100`;
  const isHigh = roundedScore >= 85;
  const isMedium = roundedScore >= 70 && roundedScore < 85;

  const glowColor = isHigh ? 'rgba(0, 240, 255, 0.45)' : isMedium ? 'rgba(123, 208, 255, 0.35)' : 'rgba(255, 180, 171, 0.35)';
  const strokeColor = isHigh ? '#00f0ff' : isMedium ? '#7bd0ff' : '#ffb4ab';

  const dim = size === 'sm' ? 'w-10 h-10' : size === 'lg' ? 'w-16 h-16' : 'w-12 h-12';
  const textDim = size === 'sm' ? 'text-[11px]' : size === 'lg' ? 'text-[16px]' : 'text-[13px]';

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Radial Holographic Ring */}
      <div className={`relative ${dim} shrink-0 flex items-center justify-center`}>
        <svg className={`${dim} -rotate-90`} viewBox="0 0 36 36">
          <path
            className="text-[#272a30]"
            strokeWidth="3.2"
            stroke="currentColor"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path
            strokeDasharray={strokeDash}
            strokeWidth="3.2"
            strokeLinecap="round"
            stroke={strokeColor}
            fill="none"
            style={{ filter: `drop-shadow(0 0 5px ${glowColor})` }}
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center font-mono select-none">
          <span className={`${textDim} font-bold text-[#dbfcff] leading-none`}>
            {roundedScore}%
          </span>
          <span className="text-[7px] text-[#7fecde] tracking-tighter uppercase font-semibold">
            MATCH
          </span>
        </div>
      </div>

      {/* Metric Breakdown & Classification */}
      <div className="flex flex-col min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-mono text-[10px] uppercase font-bold text-[#b9cacb] tracking-wider">
            {label}
          </span>
          <span
            className={`px-1.5 py-0.2 rounded font-mono text-[9px] font-bold tracking-wider uppercase ${
              isHigh
                ? 'bg-[#00f0ff]/15 text-[#00f0ff] border border-[#00f0ff]/30 shadow-[0_0_8px_rgba(0,240,255,0.2)]'
                : isMedium
                ? 'bg-[#7bd0ff]/15 text-[#7bd0ff] border border-[#7bd0ff]/30'
                : 'bg-[#ffb4ab]/15 text-[#ffb4ab] border border-[#ffb4ab]/30'
            }`}
          >
            {isHigh ? `${roundedScore}% MATCH • OPTIMAL` : `${roundedScore}% MATCH`}
          </span>
        </div>

        {showDetails && (
          <div className="flex items-center gap-2 mt-1 text-[10px] font-mono text-[#849495] flex-wrap">
            <span>
              Vector: <strong className="text-[#dbfcff] font-semibold">{vectorSim}%</strong>
            </span>
            <span className="text-[#3b494b]">•</span>
            <span>
              Symptom: <strong className="text-[#7fecde] font-semibold">{symptomMatch}%</strong>
            </span>
            <span className="text-[#3b494b]">•</span>
            <span>
              Topology: <strong className="text-[#7bd0ff] font-semibold">{topologyMatch}%</strong>
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
