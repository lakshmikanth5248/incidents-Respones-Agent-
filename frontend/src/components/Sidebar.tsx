import React from 'react';
import { useAuth } from '../context/AuthContext';

export type NavPath =
  | 'overview-live-command'
  | 'incidents'
  | 'investigation-workspace'
  | 'hindsight-experience-graph'
  | 'memory-lifecycle'
  | 'response-operations-actions'
  | 'incident-timeline'
  | 'analytics-post-mortem-history'
  | 'settings-integrations'
  | 'demo'
  | 'audit-trail'
  | 'ai-analysis'
  | 'admin'
  | 'profile'
  | 'login';

interface SidebarProps {
  currentPath: NavPath;
  onNavigate: (path: NavPath) => void;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
  onCreateIncident?: () => void;
}

interface NavItem {
  id: NavPath;
  label: string;
  icon: string;
  badge?: string;
  badgeColor?: string;
  moduleKey?: string;
}

interface NavSection {
  title: string;
  adminOnly?: boolean;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPath,
  onNavigate,
  isOpenMobile,
  onCloseMobile,
  onCreateIncident,
}) => {
  const { user, logout, isAdmin, hasPermission } = useAuth();

  const sections: NavSection[] = [
    {
      title: 'COMMAND',
      items: [
        { id: 'overview-live-command', label: 'Overview / Live Command', icon: 'terminal' },
        { id: 'incidents', label: 'Incidents Radar', icon: 'crisis_alert', badge: '1 ACT', badgeColor: 'bg-error-container text-error', moduleKey: 'incidents' },
        { id: 'investigation-workspace', label: 'Investigation Workspace', icon: 'troubleshoot', moduleKey: 'investigation' },
      ],
    },
    {
      title: 'AI & COGNITIVE ENGINE',
      items: [
        { id: 'ai-analysis', label: 'Direct AI & Web Analysis', icon: 'psychology', badge: 'GROUNDED', badgeColor: 'bg-[#7fecde]/20 text-[#7fecde]', moduleKey: 'ai_analysis' },
        { id: 'demo', label: 'Guided Demo Storyline', icon: 'auto_stories', badge: '9 STEPS', badgeColor: 'bg-[#00f0ff]/20 text-[#00f0ff]' },
      ],
    },
    {
      title: 'MEMORY',
      items: [
        { id: 'hindsight-experience-graph', label: 'Hindsight Experience Graph', icon: 'hub', badge: 'v4.9', badgeColor: 'bg-primary-container/20 text-primary', moduleKey: 'memory' },
        { id: 'memory-lifecycle', label: 'Memory Lifecycle', icon: 'history_edu', moduleKey: 'memory' },
      ],
    },
    {
      title: 'OPERATIONS',
      items: [
        { id: 'response-operations-actions', label: 'Response Operations', icon: 'bolt', badge: '3 STAGED', badgeColor: 'bg-tertiary-container/20 text-tertiary', moduleKey: 'operations' },
        { id: 'incident-timeline', label: 'Incident Timeline', icon: 'timeline', moduleKey: 'operations' },
      ],
    },
    {
      title: 'SYSTEM & COMPLIANCE',
      items: [
        { id: 'analytics-post-mortem-history', label: 'Analytics & Post-Mortem', icon: 'analytics', moduleKey: 'analytics' },
        { id: 'audit-trail', label: 'Immutable Audit Trail', icon: 'policy', moduleKey: 'audit' },
        { id: 'settings-integrations', label: 'Settings & Integrations', icon: 'tune', moduleKey: 'settings' },
      ],
    },
    // Admin / Access Control: Only visible in authenticated admin sidebar
    ...(isAdmin
      ? [
          {
            title: 'ADMIN / ACCESS CONTROL',
            adminOnly: true,
            items: [
              {
                id: 'admin' as NavPath,
                label: 'User & Access Control',
                icon: 'admin_panel_settings',
                badge: 'ROOT',
                badgeColor: 'bg-[#ff5c8a]/20 text-[#ff5c8a] border border-[#ff5c8a]/30',
                moduleKey: 'admin',
              },
            ],
          },
        ]
      : []),
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
        <div className="flex-1 overflow-y-auto px-3 py-3 select-none flex flex-col gap-3">
          {/* Prominent Actions Rack */}
          <div className="flex flex-col gap-1.5 pt-1">
            <button
              onClick={() => {
                if (onCreateIncident) onCreateIncident();
                if (onCloseMobile) onCloseMobile();
              }}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-mono text-[12px] font-bold shadow-[0_0_12px_rgba(0,240,255,0.3)] transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[17px]">add</span>
              <span>+ CREATE INCIDENT</span>
            </button>

            <button
              onClick={() => {
                onNavigate('ai-analysis');
                if (onCloseMobile) onCloseMobile();
              }}
              className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg font-mono text-[12px] font-bold transition-all cursor-pointer ${
                currentPath === 'ai-analysis'
                  ? 'bg-[#00f0ff]/25 text-[#dbfcff] border border-[#00f0ff] shadow-[0_0_12px_rgba(0,240,255,0.25)]'
                  : 'bg-[#00f0ff]/10 hover:bg-[#00f0ff]/20 text-[#00f0ff] border border-[#00f0ff]/40 shadow-[0_0_8px_rgba(0,240,255,0.1)]'
              }`}
            >
              <span className="material-symbols-outlined text-[17px] text-[#00f0ff]">bolt</span>
              <span>⚡ ANALYSE WITH AI</span>
            </button>
          </div>

          <div className="h-px w-full bg-[#3b494b]/30" />

          {/* Navigation Sections */}
          {sections.map((section) => {
            const filteredItems = section.items.filter((item) => {
              if (item.moduleKey && !hasPermission(item.moduleKey)) {
                return false;
              }
              return true;
            });

            if (filteredItems.length === 0) return null;

            return (
              <div key={section.title} className="mb-2">
                <div
                  className={`px-2.5 mb-1 font-mono text-[10px] font-semibold uppercase tracking-widest ${
                    section.adminOnly ? 'text-[#ff5c8a]' : 'text-[#b9cacb]/80'
                  }`}
                >
                  {section.title}
                </div>

                <nav className="flex flex-col gap-0.5">
                  {filteredItems.map((item) => {
                    const isActive = currentPath === item.id;
                    const isAdminItem = item.id === 'admin';
                    const isAiItem = item.id === 'ai-analysis';

                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          onNavigate(item.id);
                          if (onCloseMobile) onCloseMobile();
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-[13px] font-medium transition-all text-left group ${
                          isActive
                            ? 'bg-[#272a30] text-[#dbfcff] shadow-[0_0_10px_rgba(0,240,255,0.2)] border-l-2 border-[#00f0ff]'
                            : isAdminItem
                            ? 'text-[#ff5c8a] hover:bg-[#ff5c8a]/10 hover:text-[#ffdad6]'
                            : isAiItem
                            ? 'text-[#7fecde] hover:bg-[#7fecde]/10'
                            : 'text-[#b9cacb] hover:bg-[#272a30]/60 hover:text-[#e0e2ea]'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <span
                            className={`material-symbols-outlined text-[17px] transition-colors ${
                              isActive
                                ? 'text-[#00f0ff]'
                                : isAdminItem
                                ? 'text-[#ff5c8a]'
                                : isAiItem
                                ? 'text-[#7fecde]'
                                : 'text-[#849495] group-hover:text-[#dbfcff]'
                            }`}
                          >
                            {item.icon}
                          </span>
                          <span className="truncate">{item.label}</span>
                        </div>

                        {item.badge && (
                          <span
                            className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded ${
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
            );
          })}
        </div>

        {/* Bottom Hindsight Engine Telemetry Dock */}
        <div className="p-3 bg-[#181c21] border-t border-[#3b494b]/30 shrink-0 flex flex-col gap-2">
          {user && (
            <div className="flex items-center justify-between p-2 rounded bg-[#1d2025] border border-[#3b494b]/30 font-mono text-[11px]">
              <div
                onClick={() => onNavigate('profile')}
                className="flex items-center gap-2 cursor-pointer truncate hover:text-[#00f0ff] transition-colors"
              >
                <div className="w-6 h-6 rounded-full bg-[#00f0ff]/20 border border-[#00f0ff] flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-[14px] text-[#00f0ff]">person</span>
                </div>
                <div className="flex flex-col truncate">
                  <span className="text-[#e0e2ea] font-bold truncate leading-tight">{user.name}</span>
                  <span className="text-[9px] text-[#7bd0ff] uppercase">{user.role}</span>
                </div>
              </div>
              <button
                onClick={() => {
                  logout();
                  onNavigate('login');
                }}
                className="text-[#849495] hover:text-[#ffdad6] p-1 transition-colors cursor-pointer"
                title="Sign out"
              >
                <span className="material-symbols-outlined text-[16px]">logout</span>
              </button>
            </div>
          )}

          <div className="rounded bg-[#1d2025] p-2 flex flex-col gap-0.5 border border-[#3b494b]/30">
            <div className="flex justify-between items-center text-[10px] font-mono">
              <span className="text-[#b9cacb]">Memory Index</span>
              <span className="text-[#dbfcff] font-bold">14,892 nodes</span>
            </div>
            <div className="flex justify-between items-center text-[10px] font-mono">
              <span className="text-[#b9cacb]">Recall Precision</span>
              <span className="text-[#7fecde] font-semibold">Calibrated</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
