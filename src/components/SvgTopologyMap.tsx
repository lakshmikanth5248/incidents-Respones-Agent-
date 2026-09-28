import React from 'react';

interface SvgTopologyMapProps {
  onSelectNode: (nodeId: string) => void;
  selectedNodeId?: string | null;
}

export const SvgTopologyMap: React.FC<SvgTopologyMapProps> = ({
  onSelectNode,
  selectedNodeId,
}) => {
  return (
    <div className="relative w-full rounded-xl bg-surface-container-lowest p-space-md overflow-hidden flex flex-col items-center justify-center border border-outline-variant/30">
      <svg
        className="w-full h-64 text-outline-variant select-none"
        fill="none"
        viewBox="0 0 520 220"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="flowGradActive" x1="0%" x2="100%" y1="0%" y2="0%">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#ffb4ab" stopOpacity="0.9" />
          </linearGradient>
          <linearGradient id="flowGradStable" x1="0%" x2="100%" y1="0%" y2="0%">
            <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#00dbe9" stopOpacity="0.7" />
          </linearGradient>
          <filter id="cyanGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Grid backdrop lines */}
        <path
          d="M10 30 H510 M10 70 H510 M10 110 H510 M10 150 H510 M10 190 H510"
          stroke="currentColor"
          strokeDasharray="3 3"
          strokeOpacity="0.15"
        />
        <path
          d="M70 10 V210 M170 10 V210 M270 10 V210 M370 10 V210 M470 10 V210"
          stroke="currentColor"
          strokeDasharray="3 3"
          strokeOpacity="0.15"
        />

        {/* Connective Telemetry Conduits */}
        {/* Ingress -> Envoy */}
        <path d="M90 110 L140 110" stroke="#00f0ff" strokeLinecap="round" strokeWidth="2" />
        <circle cx="115" cy="110" r="2.5" fill="#00f0ff" className="animate-pulse" />

        {/* Envoy -> Checkout API */}
        <path d="M220 110 L270 110" stroke="#00f0ff" strokeLinecap="round" strokeWidth="2" />
        <circle cx="245" cy="110" r="2.5" fill="#00f0ff" className="animate-pulse" />

        {/* Checkout API -> Payment Gateway (Degraded Path) */}
        <path
          d="M350 100 L400 65"
          stroke="url(#flowGradActive)"
          strokeDasharray="4 2"
          strokeLinecap="round"
          strokeWidth="3"
        />
        <circle cx="375" cy="82" r="3" fill="#ffb4ab" className="animate-ping" />

        {/* Checkout API -> PostgreSQL (Nominal Path) */}
        <path
          d="M350 120 L400 155"
          stroke="url(#flowGradStable)"
          strokeLinecap="round"
          strokeWidth="2"
        />
        <circle cx="375" cy="138" r="2" fill="#7fecde" />

        {/* Node 1: Cloudflare Edge */}
        <g
          transform="translate(20, 85)"
          className="cursor-pointer transition-transform hover:scale-105"
          onClick={() => onSelectNode('edge-ingress')}
        >
          <rect
            fill={selectedNodeId === 'edge-ingress' ? '#272a30' : '#181c21'}
            height="50"
            rx="4"
            stroke={selectedNodeId === 'edge-ingress' ? '#00f0ff' : '#3b494b'}
            strokeWidth="1.5"
            width="70"
          />
          <text fill="#e0e2ea" fontFamily="JetBrains Mono" fontSize="9" fontWeight="600" textAnchor="middle" x="35" y="24">
            EDGE INGRESS
          </text>
          <text fill="#7bd0ff" fontFamily="JetBrains Mono" fontSize="8" textAnchor="middle" x="35" y="38">
            Cloudflare
          </text>
        </g>

        {/* Node 2: Envoy Mesh */}
        <g
          transform="translate(140, 85)"
          className="cursor-pointer transition-transform hover:scale-105"
          onClick={() => onSelectNode('envoy-mesh')}
        >
          <rect
            fill={selectedNodeId === 'envoy-mesh' ? '#272a30' : '#181c21'}
            height="50"
            rx="4"
            stroke={selectedNodeId === 'envoy-mesh' ? '#00f0ff' : '#3b494b'}
            strokeWidth="1.5"
            width="80"
          />
          <text fill="#e0e2ea" fontFamily="JetBrains Mono" fontSize="9" fontWeight="600" textAnchor="middle" x="40" y="24">
            ENVOY MESH
          </text>
          <text fill="#00dbe9" fontFamily="JetBrains Mono" fontSize="8" textAnchor="middle" x="40" y="38">
            mTLS 1.3
          </text>
        </g>

        {/* Node 3: Checkout API (INC-2048 Anchor) */}
        <g
          transform="translate(270, 75)"
          className="cursor-pointer transition-transform hover:scale-105"
          onClick={() => onSelectNode('checkout-api')}
        >
          <rect
            fill="#272a30"
            height="70"
            rx="4"
            stroke="#00f0ff"
            strokeWidth="2"
            filter="url(#cyanGlow)"
            width="80"
          />
          <circle cx="70" cy="12" fill="#ffb4ab" r="4" className="animate-ping" />
          <text fill="#dbfcff" fontFamily="JetBrains Mono" fontSize="9" fontWeight="700" textAnchor="middle" x="40" y="26">
            CHECKOUT API
          </text>
          <text fill="#ffb4ab" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold" textAnchor="middle" x="40" y="42">
            INC-2048
          </text>
          <text fill="#b9cacb" fontFamily="JetBrains Mono" fontSize="7" textAnchor="middle" x="40" y="56">
            10 pods / NA
          </text>
        </g>

        {/* Node 4: Payment Gateway (DEGRADED) */}
        <g
          transform="translate(400, 35)"
          className="cursor-pointer transition-transform hover:scale-105"
          onClick={() => onSelectNode('payment-gw')}
        >
          <rect
            fill="#93000a"
            fillOpacity="0.35"
            height="58"
            rx="4"
            stroke="#ffb4ab"
            strokeWidth="1.5"
            width="105"
          />
          <text fill="#ffdad6" fontFamily="JetBrains Mono" fontSize="9" fontWeight="700" textAnchor="middle" x="52" y="22">
            PAYMENT GW
          </text>
          <text fill="#ffb4ab" fontFamily="JetBrains Mono" fontSize="8" textAnchor="middle" x="52" y="36">
            EXT STRIPE PROXY
          </text>
          <text fill="#ffb4ab" fontFamily="JetBrains Mono" fontSize="7" fontWeight="bold" textAnchor="middle" x="52" y="49">
            504 TIMEOUT SPIKE
          </text>
        </g>

        {/* Node 5: PostgreSQL Primary */}
        <g
          transform="translate(400, 130)"
          className="cursor-pointer transition-transform hover:scale-105"
          onClick={() => onSelectNode('postgres-primary')}
        >
          <rect
            fill={selectedNodeId === 'postgres-primary' ? '#272a30' : '#181c21'}
            height="50"
            rx="4"
            stroke={selectedNodeId === 'postgres-primary' ? '#00f0ff' : '#3b494b'}
            strokeWidth="1.5"
            width="105"
          />
          <text fill="#e0e2ea" fontFamily="JetBrains Mono" fontSize="9" fontWeight="600" textAnchor="middle" x="52" y="24">
            POSTGRESQL
          </text>
          <text fill="#7fecde" fontFamily="JetBrains Mono" fontSize="8" textAnchor="middle" x="52" y="38">
            Primary iad01-db
          </text>
        </g>
      </svg>

      {/* Floating HUD Overlay Marker */}
      <div className="absolute bottom-2 left-3 flex items-center gap-space-xs font-mono text-[11px] text-on-surface-variant">
        <span className="w-2 h-2 rounded-full bg-error animate-pulse" />
        <span>Root Bottleneck: payment-gw-proxy-iad</span>
      </div>
    </div>
  );
};
