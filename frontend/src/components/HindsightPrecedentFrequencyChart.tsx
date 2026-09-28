import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

export interface RecalledPrecedentDay {
  date: string;
  dayIndex: number;
  totalRecalls: number;
  paymentBilling: number;
  authIAM: number;
  dbStorage: number;
  networkMesh: number;
  topPrecedent: string;
  recurringTheme: string;
  cumulativeRecalls: number;
}

// Generate realistic 30-day precedent recall trajectory culminating in today's active incident
export const LAST_30_DAYS_RECALLS: RecalledPrecedentDay[] = [
  { date: 'Aug 30', dayIndex: 1, totalRecalls: 1, paymentBilling: 0, authIAM: 1, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1721', recurringTheme: 'OAuth Token TTL Expiry', cumulativeRecalls: 1 },
  { date: 'Aug 31', dayIndex: 2, totalRecalls: 2, paymentBilling: 1, authIAM: 0, dbStorage: 1, networkMesh: 0, topPrecedent: 'INC-1842', recurringTheme: 'Redis Connection Bump', cumulativeRecalls: 3 },
  { date: 'Sep 01', dayIndex: 3, totalRecalls: 0, paymentBilling: 0, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'None', recurringTheme: 'Nominal Operations', cumulativeRecalls: 3 },
  { date: 'Sep 02', dayIndex: 4, totalRecalls: 1, paymentBilling: 0, authIAM: 0, dbStorage: 0, networkMesh: 1, topPrecedent: 'INC-1590', recurringTheme: 'CoreDNS UDP Saturation', cumulativeRecalls: 4 },
  { date: 'Sep 03', dayIndex: 5, totalRecalls: 2, paymentBilling: 0, authIAM: 2, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1721', recurringTheme: 'JWKS Key Rotation Lag', cumulativeRecalls: 6 },
  { date: 'Sep 04', dayIndex: 6, totalRecalls: 1, paymentBilling: 1, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1987', recurringTheme: 'Merchant Egress Spike', cumulativeRecalls: 7 },
  { date: 'Sep 05', dayIndex: 7, totalRecalls: 3, paymentBilling: 0, authIAM: 1, dbStorage: 1, networkMesh: 1, topPrecedent: 'INC-1402', recurringTheme: 'Kafka Rebalance Storm', cumulativeRecalls: 10 },
  { date: 'Sep 06', dayIndex: 8, totalRecalls: 0, paymentBilling: 0, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'None', recurringTheme: 'Nominal Operations', cumulativeRecalls: 10 },
  { date: 'Sep 07', dayIndex: 9, totalRecalls: 1, paymentBilling: 0, authIAM: 0, dbStorage: 1, networkMesh: 0, topPrecedent: 'INC-1601', recurringTheme: 'PostgreSQL Lock Hold', cumulativeRecalls: 11 },
  { date: 'Sep 08', dayIndex: 10, totalRecalls: 2, paymentBilling: 1, authIAM: 0, dbStorage: 0, networkMesh: 1, topPrecedent: 'INC-1590', recurringTheme: 'Conntrack Exhaustion', cumulativeRecalls: 13 },
  { date: 'Sep 09', dayIndex: 11, totalRecalls: 2, paymentBilling: 0, authIAM: 2, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1721', recurringTheme: 'Auth Cache Thundering Herd', cumulativeRecalls: 15 },
  { date: 'Sep 10', dayIndex: 12, totalRecalls: 1, paymentBilling: 1, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1987', recurringTheme: 'Downstream Socket Delay', cumulativeRecalls: 16 },
  { date: 'Sep 11', dayIndex: 13, totalRecalls: 0, paymentBilling: 0, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'None', recurringTheme: 'Nominal Operations', cumulativeRecalls: 16 },
  { date: 'Sep 12', dayIndex: 14, totalRecalls: 2, paymentBilling: 0, authIAM: 0, dbStorage: 1, networkMesh: 1, topPrecedent: 'INC-1842', recurringTheme: 'Client Pool Multiplexing', cumulativeRecalls: 18 },
  { date: 'Sep 13', dayIndex: 15, totalRecalls: 1, paymentBilling: 0, authIAM: 1, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1721', recurringTheme: 'OAuth Token Spike', cumulativeRecalls: 19 },
  { date: 'Sep 14', dayIndex: 16, totalRecalls: 3, paymentBilling: 1, authIAM: 0, dbStorage: 0, networkMesh: 2, topPrecedent: 'INC-1402', recurringTheme: 'Consumer Lag Partition Skew', cumulativeRecalls: 22 },
  { date: 'Sep 15', dayIndex: 17, totalRecalls: 1, paymentBilling: 1, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1987', recurringTheme: 'Stripe API Degradation', cumulativeRecalls: 23 },
  { date: 'Sep 16', dayIndex: 18, totalRecalls: 0, paymentBilling: 0, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'None', recurringTheme: 'Nominal Operations', cumulativeRecalls: 23 },
  { date: 'Sep 17', dayIndex: 19, totalRecalls: 2, paymentBilling: 0, authIAM: 1, dbStorage: 1, networkMesh: 0, topPrecedent: 'INC-1601', recurringTheme: 'Invoice Batch Row Lock', cumulativeRecalls: 25 },
  { date: 'Sep 18', dayIndex: 20, totalRecalls: 2, paymentBilling: 0, authIAM: 0, dbStorage: 0, networkMesh: 2, topPrecedent: 'INC-1590', recurringTheme: 'NodeLocal DNS Drops', cumulativeRecalls: 27 },
  { date: 'Sep 19', dayIndex: 21, totalRecalls: 1, paymentBilling: 1, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1987', recurringTheme: 'Webhook Retries Saturation', cumulativeRecalls: 28 },
  { date: 'Sep 20', dayIndex: 22, totalRecalls: 2, paymentBilling: 0, authIAM: 2, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1721', recurringTheme: 'Token Jitter Overflow', cumulativeRecalls: 30 },
  { date: 'Sep 21', dayIndex: 23, totalRecalls: 1, paymentBilling: 0, authIAM: 0, dbStorage: 1, networkMesh: 0, topPrecedent: 'INC-1842', recurringTheme: 'Redis Idle Socket Leak', cumulativeRecalls: 31 },
  { date: 'Sep 22', dayIndex: 24, totalRecalls: 0, paymentBilling: 0, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'None', recurringTheme: 'Nominal Operations', cumulativeRecalls: 31 },
  { date: 'Sep 23', dayIndex: 25, totalRecalls: 2, paymentBilling: 0, authIAM: 1, dbStorage: 0, networkMesh: 1, topPrecedent: 'INC-1590', recurringTheme: 'Envoy Ingress Conntrack', cumulativeRecalls: 33 },
  { date: 'Sep 24', dayIndex: 26, totalRecalls: 1, paymentBilling: 1, authIAM: 0, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1987', recurringTheme: 'Payment Proxy Timeout', cumulativeRecalls: 34 },
  { date: 'Sep 25', dayIndex: 27, totalRecalls: 2, paymentBilling: 0, authIAM: 1, dbStorage: 1, networkMesh: 0, topPrecedent: 'INC-1721', recurringTheme: 'IAM Grant Invalidation', cumulativeRecalls: 36 },
  { date: 'Sep 26', dayIndex: 28, totalRecalls: 1, paymentBilling: 0, authIAM: 0, dbStorage: 0, networkMesh: 1, topPrecedent: 'INC-1402', recurringTheme: 'Sync Transformer Delay', cumulativeRecalls: 37 },
  { date: 'Sep 27', dayIndex: 29, totalRecalls: 2, paymentBilling: 1, authIAM: 1, dbStorage: 0, networkMesh: 0, topPrecedent: 'INC-1987', recurringTheme: 'Gateway Fallback Warmup', cumulativeRecalls: 39 },
  { date: 'Sep 28', dayIndex: 30, totalRecalls: 3, paymentBilling: 2, authIAM: 0, dbStorage: 0, networkMesh: 1, topPrecedent: 'INC-1987', recurringTheme: 'Thread Pool Saturation (INC-2048)', cumulativeRecalls: 42 },
];

export const TOP_RECURRING_PRECEDENTS = [
  {
    id: 'INC-1721',
    name: 'OAuth Token Revocation Avalanche',
    domain: 'Authentication & IAM',
    totalRecalls: 12,
    recurrenceRate: '31% of IAM incidents',
    color: '#7fecde',
    risk: 'CRITICAL',
    takeaway: 'Enforce randomized jitter on token renewals to prevent concurrent stampedes.',
  },
  {
    id: 'INC-1590',
    name: 'DNS Resolution Flapping / Conntrack Saturation',
    domain: 'Network & Mesh',
    totalRecalls: 9,
    recurrenceRate: '24% of network stalls',
    color: '#a78bfa',
    risk: 'HIGH',
    takeaway: 'NodeLocal DNS caches required when node worker density exceeds 65 pods.',
  },
  {
    id: 'INC-1987',
    name: 'Payment Gateway Timeout & Socket Exhaustion',
    domain: 'Payment & Billing',
    totalRecalls: 7,
    recurrenceRate: '19% of checkout degradations',
    color: '#00f0ff',
    risk: 'HIGH (ACTIVE)',
    takeaway: 'Clamp egress socket keep-alives to 1500ms; switch to secondary gateway immediately.',
  },
  {
    id: 'INC-1402',
    name: 'Kafka Partition Lag during Rebalance Storms',
    domain: 'Network & Mesh',
    totalRecalls: 6,
    recurrenceRate: '16% of pipeline alerts',
    color: '#38bdf8',
    risk: 'MEDIUM',
    takeaway: 'Decouple heavy synchronous PDF processing from main poll loop.',
  },
  {
    id: 'INC-1842',
    name: 'Redis Connection Surge post-Engine Upgrade',
    domain: 'Database & Storage',
    totalRecalls: 4,
    recurrenceRate: '11% of cache latencies',
    color: '#7bd0ff',
    risk: 'MEDIUM',
    takeaway: 'Cap persistent idle connection pool sizes via Helm values.',
  },
];

interface HindsightPrecedentFrequencyChartProps {
  onSelectPrecedent?: (precedentId: string) => void;
}

export const HindsightPrecedentFrequencyChart: React.FC<HindsightPrecedentFrequencyChartProps> = ({
  onSelectPrecedent,
}) => {
  const [viewMode, setViewMode] = useState<'stacked' | 'bar' | 'cumulative'>('stacked');
  const [selectedDomain, setSelectedDomain] = useState<string>('ALL');

  const filteredData = useMemo(() => {
    if (selectedDomain === 'ALL') return LAST_30_DAYS_RECALLS;
    return LAST_30_DAYS_RECALLS.map((day) => {
      let filteredCount = 0;
      if (selectedDomain === 'Payment & Billing') filteredCount = day.paymentBilling;
      else if (selectedDomain === 'Authentication & IAM') filteredCount = day.authIAM;
      else if (selectedDomain === 'Database & Storage') filteredCount = day.dbStorage;
      else if (selectedDomain === 'Network & Mesh') filteredCount = day.networkMesh;

      return {
        ...day,
        totalRecalls: filteredCount,
      };
    });
  }, [selectedDomain]);

  const total30DayRecalls = useMemo(() => {
    return LAST_30_DAYS_RECALLS.reduce((acc, curr) => acc + curr.totalRecalls, 0);
  }, []);

  const totalRecurringArchetypes = TOP_RECURRING_PRECEDENTS.length;

  return (
    <div className="p-5 rounded-xl bg-[#181c21] border border-[#00f0ff]/40 shadow-xl flex flex-col gap-4 relative overflow-hidden">
      {/* Background Holographic Glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-[#00f0ff]/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header and Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-[#3b494b]/30">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#00f0ff]/15 border border-[#00f0ff]/40 flex items-center justify-center text-[#00f0ff] shrink-0 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
            <span className="material-symbols-outlined text-[22px]">history_edu</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
                TACTICAL RECURRING PATTERN SURVEILLANCE
              </span>
              <span className="px-1.5 py-0.2 rounded bg-[#7fecde]/20 text-[#7fecde] font-mono text-[9px] font-bold border border-[#7fecde]/30">
                LAST 30 DAYS
              </span>
            </div>
            <h2 className="text-[18px] font-bold text-[#dbfcff]">
              Hindsight Precedent Recall Frequency &amp; Recurring Issues
            </h2>
            <p className="text-[12px] text-[#b9cacb]">
              Frequency trajectory of historical incident embeddings recalled by Aegis cognitive agents during live anomalies.
            </p>
          </div>
        </div>

        {/* View Switcher & Domain Filter */}
        <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
          {/* Domain Dropdown */}
          <div className="flex items-center gap-1.5 bg-[#0b0e13] px-2.5 py-1 rounded-lg border border-[#3b494b]/50">
            <span className="text-[#849495] text-[10px]">DOMAIN:</span>
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              className="bg-transparent text-[#e0e2ea] focus:outline-none cursor-pointer font-bold"
            >
              <option value="ALL" className="bg-[#181c21] text-[#e0e2ea]">All Domains (30D)</option>
              <option value="Payment & Billing" className="bg-[#181c21] text-[#00f0ff]">Payment &amp; Billing</option>
              <option value="Authentication & IAM" className="bg-[#181c21] text-[#7fecde]">Authentication &amp; IAM</option>
              <option value="Database & Storage" className="bg-[#181c21] text-[#7bd0ff]">Database &amp; Storage</option>
              <option value="Network & Mesh" className="bg-[#181c21] text-[#a78bfa]">Network &amp; Mesh</option>
            </select>
          </div>

          {/* Chart Display Mode Switcher */}
          <div className="flex items-center bg-[#0b0e13] p-0.5 rounded-lg border border-[#3b494b]/50">
            <button
              onClick={() => setViewMode('stacked')}
              className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all cursor-pointer ${
                viewMode === 'stacked'
                  ? 'bg-[#00f0ff] text-[#00363a] shadow-[0_0_8px_rgba(0,240,255,0.3)]'
                  : 'text-[#b9cacb] hover:text-[#e0e2ea]'
              }`}
            >
              Stacked Area
            </button>
            <button
              onClick={() => setViewMode('bar')}
              className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all cursor-pointer ${
                viewMode === 'bar'
                  ? 'bg-[#00f0ff] text-[#00363a] shadow-[0_0_8px_rgba(0,240,255,0.3)]'
                  : 'text-[#b9cacb] hover:text-[#e0e2ea]'
              }`}
            >
              Daily Bars
            </button>
            <button
              onClick={() => setViewMode('cumulative')}
              className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all cursor-pointer ${
                viewMode === 'cumulative'
                  ? 'bg-[#00f0ff] text-[#00363a] shadow-[0_0_8px_rgba(0,240,255,0.3)]'
                  : 'text-[#b9cacb] hover:text-[#e0e2ea]'
              }`}
            >
              Cumulative Growth
            </button>
          </div>
        </div>
      </div>

      {/* KPI Awareness Strips */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
        <div className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b]/30 flex flex-col">
          <span className="text-[10px] text-[#b9cacb] uppercase font-semibold">Total 30D Recalls</span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-[22px] font-bold text-[#00f0ff]">{total30DayRecalls}</span>
            <span className="text-[10px] text-[#7fecde]">events</span>
          </div>
          <span className="text-[9px] text-[#849495]">1.4 recalls / day avg</span>
        </div>

        <div className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b]/30 flex flex-col">
          <span className="text-[10px] text-[#b9cacb] uppercase font-semibold">Top Recurring Pattern</span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-[16px] font-bold text-[#7fecde] truncate">INC-1721</span>
            <span className="text-[10px] text-[#b9cacb]">(12x)</span>
          </div>
          <span className="text-[9px] text-[#849495]">OAuth Token Expiration</span>
        </div>

        <div className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b]/30 flex flex-col">
          <span className="text-[10px] text-[#b9cacb] uppercase font-semibold">Active Grounded In</span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-[16px] font-bold text-[#ffb4ab] truncate">INC-1987</span>
            <span className="text-[10px] text-[#ffdad6]">(7x)</span>
          </div>
          <span className="text-[9px] text-[#ffb4ab]">Active in INC-2048 triage</span>
        </div>

        <div className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b]/30 flex flex-col">
          <span className="text-[10px] text-[#b9cacb] uppercase font-semibold">Knowledge Retention</span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-[22px] font-bold text-[#7bd0ff]">94.2%</span>
            <span className="text-[10px] text-[#7bd0ff]">hit rate</span>
          </div>
          <span className="text-[9px] text-[#849495]">14.2m MTTR reduction</span>
        </div>
      </div>

      {/* Main Chart Visualization */}
      <div className="h-64 sm:h-72 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          {viewMode === 'stacked' ? (
            <AreaChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradientPayment" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.7} />
                  <stop offset="95%" stopColor="#00f0ff" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="gradientAuth" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7fecde" stopOpacity={0.7} />
                  <stop offset="95%" stopColor="#7fecde" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="gradientDb" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7bd0ff" stopOpacity={0.7} />
                  <stop offset="95%" stopColor="#7bd0ff" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="gradientNetwork" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.7} />
                  <stop offset="95%" stopColor="#a78bfa" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#3b494b" opacity={0.3} vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#849495"
                tick={{ fontSize: 10, fontFamily: 'monospace' }}
                interval={4}
              />
              <YAxis
                stroke="#849495"
                tick={{ fontSize: 10, fontFamily: 'monospace' }}
                allowDecimals={false}
              />
              <Tooltip content={<CustomHindsightTooltip />} />
              <Area
                type="monotone"
                dataKey="paymentBilling"
                name="Payment & Billing"
                stackId="1"
                stroke="#00f0ff"
                fill="url(#gradientPayment)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="authIAM"
                name="Authentication & IAM"
                stackId="1"
                stroke="#7fecde"
                fill="url(#gradientAuth)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="dbStorage"
                name="Database & Storage"
                stackId="1"
                stroke="#7bd0ff"
                fill="url(#gradientDb)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="networkMesh"
                name="Network & Mesh"
                stackId="1"
                stroke="#a78bfa"
                fill="url(#gradientNetwork)"
                strokeWidth={2}
              />
            </AreaChart>
          ) : viewMode === 'bar' ? (
            <BarChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3b494b" opacity={0.3} vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#849495"
                tick={{ fontSize: 10, fontFamily: 'monospace' }}
                interval={4}
              />
              <YAxis
                stroke="#849495"
                tick={{ fontSize: 10, fontFamily: 'monospace' }}
                allowDecimals={false}
              />
              <Tooltip content={<CustomHindsightTooltip />} />
              <Bar dataKey="paymentBilling" name="Payment & Billing" stackId="a" fill="#00f0ff" radius={[0, 0, 0, 0]} />
              <Bar dataKey="authIAM" name="Authentication & IAM" stackId="a" fill="#7fecde" radius={[0, 0, 0, 0]} />
              <Bar dataKey="dbStorage" name="Database & Storage" stackId="a" fill="#7bd0ff" radius={[0, 0, 0, 0]} />
              <Bar dataKey="networkMesh" name="Network & Mesh" stackId="a" fill="#a78bfa" radius={[2, 2, 0, 0]} />
            </BarChart>
          ) : (
            <AreaChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradientCumulative" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#00f0ff" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#3b494b" opacity={0.3} vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#849495"
                tick={{ fontSize: 10, fontFamily: 'monospace' }}
                interval={4}
              />
              <YAxis
                stroke="#849495"
                tick={{ fontSize: 10, fontFamily: 'monospace' }}
                allowDecimals={false}
              />
              <Tooltip content={<CustomHindsightTooltip />} />
              <Area
                type="monotone"
                dataKey="cumulativeRecalls"
                name="Cumulative Recalls"
                stroke="#00f0ff"
                fill="url(#gradientCumulative)"
                strokeWidth={2.5}
              />
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Chart Legend / Domain Indicators */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[#3b494b]/30 font-mono text-[11px]">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#00f0ff] shadow-[0_0_6px_#00f0ff]" />
            <span className="text-[#dbfcff]">Payment &amp; Billing (INC-1987)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#7fecde] shadow-[0_0_6px_#7fecde]" />
            <span className="text-[#dbfcff]">Auth &amp; IAM (INC-1721)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#7bd0ff] shadow-[0_0_6px_#7bd0ff]" />
            <span className="text-[#dbfcff]">Database &amp; Storage (INC-1842)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#a78bfa] shadow-[0_0_6px_#a78bfa]" />
            <span className="text-[#dbfcff]">Network &amp; Mesh (INC-1590)</span>
          </div>
        </div>

        <span className="text-[10px] text-[#849495]">
          Autonomous Cognitive Recall • Synchronized with OpenTelemetry Traces
        </span>
      </div>

      {/* Top Recurring Issue Cards: Tactical Awareness */}
      <div className="flex flex-col gap-2 pt-1">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase font-bold text-[#b9cacb] tracking-wider">
            Top Recurring System Archetypes (Tactical Awareness)
          </span>
          <span className="font-mono text-[10px] text-[#7bd0ff]">
            {totalRecurringArchetypes} patterns identified across HyperGraph
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          {TOP_RECURRING_PRECEDENTS.slice(0, 3).map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectPrecedent && onSelectPrecedent(item.id)}
              className="p-3 rounded-lg bg-[#0b0e13] border border-[#3b494b]/40 hover:border-[#00f0ff]/50 transition-all flex flex-col gap-1.5 group cursor-pointer"
            >
              <div className="flex items-center justify-between font-mono text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[#dbfcff] group-hover:text-[#00f0ff] transition-colors">
                    {item.id}
                  </span>
                  <span
                    className="px-1.5 py-0.2 rounded text-[9px] font-bold"
                    style={{ backgroundColor: `${item.color}20`, color: item.color }}
                  >
                    {item.totalRecalls} RECALLS
                  </span>
                </div>
                <span className="text-[10px] text-[#849495]">{item.recurrenceRate}</span>
              </div>

              <span className="text-[12px] font-semibold text-[#e0e2ea] line-clamp-1">
                {item.name}
              </span>

              <p className="font-mono text-[10px] text-[#b9cacb] line-clamp-2">
                <strong className="text-[#7fecde]">Mitigation Takeaway:</strong> {item.takeaway}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Custom Holographic Tooltip for Recharts
const CustomHindsightTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload as RecalledPrecedentDay;
    return (
      <div className="p-3 rounded-lg bg-[#0b0e13]/95 border border-[#00f0ff] shadow-[0_0_15px_rgba(0,240,255,0.3)] font-mono text-[11px] backdrop-blur-md flex flex-col gap-1.5 min-w-[210px]">
        <div className="flex items-center justify-between pb-1 border-b border-[#3b494b]/40">
          <span className="font-bold text-[#dbfcff]">{data.date} (T-{31 - data.dayIndex}d)</span>
          <span className="px-1.5 py-0.2 rounded bg-[#00f0ff]/20 text-[#00f0ff] font-bold text-[10px]">
            {data.totalRecalls} RECALL{data.totalRecalls === 1 ? '' : 'S'}
          </span>
        </div>

        {data.totalRecalls > 0 ? (
          <div className="space-y-1 text-[10px]">
            <div className="text-[#e0e2ea]">
              <span className="text-[#849495]">Primary Precedent:</span>{' '}
              <strong className="text-[#00f0ff]">{data.topPrecedent}</strong>
            </div>
            <div className="text-[#e0e2ea]">
              <span className="text-[#849495]">Recurring Pattern:</span>{' '}
              <span className="text-[#7fecde]">{data.recurringTheme}</span>
            </div>
            <div className="pt-1 border-t border-[#3b494b]/30 grid grid-cols-2 gap-1 text-[#b9cacb]">
              <div>Payment: <strong className="text-[#dbfcff]">{data.paymentBilling}</strong></div>
              <div>Auth: <strong className="text-[#7fecde]">{data.authIAM}</strong></div>
              <div>Database: <strong className="text-[#7bd0ff]">{data.dbStorage}</strong></div>
              <div>Network: <strong className="text-[#a78bfa]">{data.networkMesh}</strong></div>
            </div>
          </div>
        ) : (
          <span className="text-[#849495] text-[10px] italic">No precedent recalls triggered.</span>
        )}

        <div className="pt-0.5 text-[9px] text-[#00f0ff] flex justify-between">
          <span>Cumulative to date:</span>
          <strong>{data.cumulativeRecalls} total</strong>
        </div>
      </div>
    );
  }
  return null;
};
