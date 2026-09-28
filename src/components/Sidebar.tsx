import React from 'react';

export type NavPath =
  | 'overview-live-command'
  | 'incidents'
  | 'investigation-workspace'
  | 'hindsight-experience-graph'
  | 'memory-lifecycle'
  | 'response-operations-actions'
  | 'incident-timeline'
  | 'analytics-post-mortem-history'
  | 'settings-integrations';

interface SidebarProps {
  currentPath: NavPath;
  onNavigate: (path: NavPath) => void;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  id: NavPath;
  label: string;
  icon: string;
  badge?: string;
  badgeColor?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPath,
  onNavigate,
  isOpenMobile,
  onCloseMobile,
}) => {
  const sections: NavSection[] = [
    {
      title: 'COMMAND',
      items: [
        { id: 'overview-live-command', label: 'Overview / Live Command', icon: 'terminal' },
        { id: 'incidents', label: 'Incidents', icon: 'crisis_alert', badge: '1 ACT', badgeColor: 'bg-error-container text-error' },
        { id: 'investigation-workspace', label: 'Investigation Workspace', icon: 'troubleshoot' },
      ],
    },
    {
      title: 'MEMORY',
      items: [
        { id: 'hindsight-experience-graph', label: 'Hindsight Experience Graph', icon: 'hub', badge: 'v4.9', badgeColor: 'bg-primary-container/20 text-primary' },
        { id: 'memory-lifecycle', label: 'Memory Lifecycle', icon: 'history_edu' },
      ],
    },
    {
      title: 'OPERATIONS',
      items: [
        { id: 'response-operations-actions', label: 'Response Operations & Actions', icon: 'bolt', badge: '3 STAGED', badgeColor: 'bg-tertiary-container/20 text-tertiary' },
        { id: 'incident-timeline', label: 'Incident Timeline', icon: 'timeline' },
      ],
    },
    {
      title: 'SYSTEM',
      items: [
        { id: 'analytics-post-mortem-history', label: 'Analytics & Post-Mortem', icon: 'analytics' },
        { id: 'settings-integrations', label: 'Settings & Integrations', icon: 'tune' },
      ],
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-30 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`fixed left-0 top-16 bottom-0 w-72 bg-[#0b0e13] border-r border-[#3b494b]/30 z-40 flex flex-col justify-between shadow-[2px_0_12px_rgba(0,0,0,0.4)] transition-transform duration-200 ease-in-out ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex-1 overflow-y-auto px-3 py-4 select-none">
          {sections.map((section) => (
            <div key={section.title} className="mb-6">
              <div className="px-2.5 mb-1.5 font-mono text-[11px] font-semibold text-[#b9cacb]/80 uppercase tracking-widest">
                {section.title}
              </div>

              <nav className="flex flex-col gap-1">
                {section.items.map((item) => {
                  const isActive = currentPath === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        onNavigate(item.id);
                        if (onCloseMobile) onCloseMobile();
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-[14px] font-medium transition-all text-left group ${
                        isActive
                          ? 'bg-[#272a30] text-[#dbfcff] shadow-[0_0_10px_rgba(0,240,255,0.18)] border-l-2 border-[#00f0ff]'
                          : 'text-[#b9cacb] hover:bg-[#272a30]/60 hover:text-[#e0e2ea]'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <span
                          className={`material-symbols-outlined text-[18px] transition-colors ${
                            isActive ? 'text-[#00f0ff]' : 'text-[#849495] group-hover:text-[#dbfcff]'
                          }`}
                        >
                          {item.icon}
                        </span>
                        <span className="truncate">{item.label}</span>
                      </div>

                      {item.badge && (
                        <span
                          className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                            item.badgeColor || 'bg-[#181c21] text-[#b9cacb]'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>

        {/* Bottom Hindsight Engine Telemetry Dock */}
        <div className="p-3 bg-[#181c21] border-t border-[#3b494b]/30 shrink-0">
          <div className="rounded bg-[#1d2025] p-2.5 mb-2.5 flex flex-col gap-1 border border-[#3b494b]/30">
            <div className="flex justify-between items-center text-[11px] font-mono">
              <span className="text-[#b9cacb]">Memory Index</span>
              <span className="text-[#dbfcff] font-bold">14,892 nodes</span>
            </div>
            <div className="flex justify-between items-center text-[11px] font-mono">
              <span className="text-[#b9cacb]">Recall Precision</span>
              <span className="text-[#7fecde] font-semibold">Calibrated</span>
            </div>
            <div className="flex justify-between items-center text-[11px] font-mono">
              <span className="text-[#b9cacb]">Agent State</span>
              <span className="text-[#7bd0ff] truncate max-w-[120px] font-medium" title="Investigating INC-2048">
                Investigating INC-2048
              </span>
            </div>
          </div>

          <div className="text-[11px] font-mono text-[#b9cacb]/80 italic text-center leading-tight tracking-tight px-1">
            “An incident ends. Its experience shouldn't.”
          </div>
        </div>
      </aside>
    </>
  );
};
