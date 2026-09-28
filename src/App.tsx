import React, { useState } from 'react';
import { Header } from './components/Header';
import { Sidebar, NavPath } from './components/Sidebar';
import { InvestigationWorkspace } from './components/InvestigationWorkspace';
import { HindsightExperienceGraph } from './components/HindsightExperienceGraph';
import { LiveCommandOverview } from './components/LiveCommandOverview';
import { IncidentsList } from './components/IncidentsList';
import { MemoryLifecycleView } from './components/MemoryLifecycleView';
import { ResponseOperationsView } from './components/ResponseOperationsView';
import { IncidentTimelineView } from './components/IncidentTimelineView';
import { PostMortemAnalyticsView } from './components/PostMortemAnalyticsView';
import { SettingsView } from './components/SettingsView';
import { MemoryPrecedent } from './types';

export default function App() {
  const [currentPath, setCurrentPath] = useState<NavPath>('investigation-workspace');
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const handleNavigate = (path: NavPath) => {
    setCurrentPath(path);
  };

  const handleOpenActiveIncident = () => {
    setCurrentPath('investigation-workspace');
  };

  const handlePrecedentSelectedFromGraph = (precedent: MemoryPrecedent) => {
    // Navigate back to workspace with the grounded precedent active
    setCurrentPath('investigation-workspace');
  };

  return (
    <div className="min-h-screen bg-[#101419] text-[#e0e2ea] flex flex-col font-sans selection:bg-[#00f0ff]/30 selection:text-[#dbfcff]">
      {/* Fixed Global Header */}
      <Header
        onIncidentClick={handleOpenActiveIncident}
        onProfileClick={() => setCurrentPath('settings-integrations')}
        onToggleSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
      />

      {/* Fixed Left Navigation Sidebar */}
      <Sidebar
        currentPath={currentPath}
        onNavigate={handleNavigate}
        isOpenMobile={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="lg:pl-72 flex-1 flex flex-col">
        <main className="w-full pt-16 min-h-screen bg-[#101419] px-4 md:px-6 py-5">
          {currentPath === 'investigation-workspace' && (
            <InvestigationWorkspace
              onNavigateToGraph={() => setCurrentPath('hindsight-experience-graph')}
              onOpenPrecedentTrace={(id) => {
                setCurrentPath('hindsight-experience-graph');
              }}
            />
          )}

          {currentPath === 'hindsight-experience-graph' && (
            <HindsightExperienceGraph
              onSelectPrecedentForIncident={handlePrecedentSelectedFromGraph}
              onNavigateToWorkspace={() => setCurrentPath('investigation-workspace')}
            />
          )}

          {currentPath === 'overview-live-command' && (
            <LiveCommandOverview
              onInvestigate={(id) => setCurrentPath('investigation-workspace')}
              onExploreGraph={() => setCurrentPath('hindsight-experience-graph')}
            />
          )}

          {currentPath === 'incidents' && (
            <IncidentsList
              onInvestigate={(id) => setCurrentPath('investigation-workspace')}
            />
          )}

          {currentPath === 'memory-lifecycle' && <MemoryLifecycleView />}

          {currentPath === 'response-operations-actions' && <ResponseOperationsView />}

          {currentPath === 'incident-timeline' && <IncidentTimelineView />}

          {currentPath === 'analytics-post-mortem-history' && <PostMortemAnalyticsView />}

          {currentPath === 'settings-integrations' && <SettingsView />}
        </main>
      </div>
    </div>
  );
}
