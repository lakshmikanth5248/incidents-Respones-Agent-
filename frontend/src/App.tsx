import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
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
import { AuditTrailView } from './components/AuditTrailView';
import { DemoPresentationView } from './components/DemoPresentationView';
import { AdminAccessControlView } from './components/AdminAccessControlView';
import { AiAnalysisView } from './components/AiAnalysisView';
import { CinematicOpening } from './components/CinematicOpening';
import { AuthPages } from './components/AuthPages';
import { CreateIncidentModal } from './components/CreateIncidentModal';
import { MemoryPrecedent } from './types';

function AppContent() {
  const { user, loading } = useAuth();
  const [currentPath, setCurrentPath] = useState<NavPath>('overview-live-command');
  const [authView, setAuthView] = useState<'login' | 'register' | 'forgot-password'>('login');
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isCreateIncidentOpen, setIsCreateIncidentOpen] = useState(false);
  const [activeInvestigationId, setActiveInvestigationId] = useState<string>('INC-2048');
  const [showCinematicIntro, setShowCinematicIntro] = useState<boolean>(() => {
    return !sessionStorage.getItem('aegis_cinematic_opening_shown');
  });

  const handleCinematicComplete = () => {
    sessionStorage.setItem('aegis_cinematic_opening_shown', 'true');
    setShowCinematicIntro(false);
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b0e13] flex flex-col items-center justify-center p-6 text-[#dbfcff] font-mono">
        <div className="relative w-16 h-16 mb-4">
          <div className="absolute inset-0 rounded-full border-2 border-[#3b494b] border-t-[#00f0ff] animate-spin" />
          <div className="absolute inset-2 rounded-full border-2 border-transparent border-b-[#7fecde] animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        </div>
        <div className="text-[14px] font-bold tracking-widest uppercase text-[#00f0ff] animate-pulse">
          INITIALIZING AEGIS SRE RUNTIME
        </div>
        <div className="text-[11px] text-[#b9cacb] mt-1">
          Connecting to HyperGraph v4.9 &amp; Telemetry Bus...
        </div>
      </div>
    );
  }

  // Unauthenticated view
  if (!user) {
    return (
      <div className="min-h-screen bg-[#101419] text-[#e0e2ea] flex flex-col justify-center p-4 relative">
        {showCinematicIntro && (
          <CinematicOpening onComplete={handleCinematicComplete} />
        )}
        <AuthPages
          view={authView}
          onNavigate={(target) => {
            if (target === 'command') {
              setCurrentPath('overview-live-command');
            } else if (target === 'admin') {
              setCurrentPath('admin');
            } else if (target === 'investigation') {
              setCurrentPath('investigation-workspace');
            } else if (target === 'memory') {
              setCurrentPath('hindsight-experience-graph');
            } else if (target === 'profile') {
              // Stay in auth
            } else {
              setAuthView(target as any);
            }
          }}
        />
      </div>
    );
  }

  // Authenticated state
  const handleNavigate = (path: NavPath) => {
    setCurrentPath(path);
  };

  const handleOpenActiveIncident = (id?: string) => {
    if (id) setActiveInvestigationId(id);
    setCurrentPath('investigation-workspace');
  };

  const handlePrecedentSelectedFromGraph = (precedent: MemoryPrecedent) => {
    setCurrentPath('investigation-workspace');
  };

  return (
    <div className="min-h-screen bg-[#101419] text-[#e0e2ea] flex flex-col font-sans selection:bg-[#00f0ff]/30 selection:text-[#dbfcff] relative">
      {/* Cinematic Curtains Opening Animation (plays once on initial load) */}
      {showCinematicIntro && (
        <CinematicOpening onComplete={handleCinematicComplete} />
      )}

      {/* Global Header */}
      <Header
        onIncidentClick={() => handleOpenActiveIncident('INC-2048')}
        onProfileClick={() => setCurrentPath('profile')}
        onToggleSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        onDemoClick={() => setCurrentPath('demo')}
      />

      {/* Global Left Navigation Sidebar */}
      <Sidebar
        currentPath={currentPath}
        onNavigate={handleNavigate}
        isOpenMobile={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        onCreateIncident={() => setIsCreateIncidentOpen(true)}
      />

      {/* Global Create Incident Modal */}
      {isCreateIncidentOpen && (
        <CreateIncidentModal
          onClose={() => setIsCreateIncidentOpen(false)}
          onCreated={(newId) => {
            setActiveInvestigationId(newId);
            setCurrentPath('investigation-workspace');
          }}
        />
      )}

      {/* Main Content Area */}
      <div className="lg:pl-72 flex-1 flex flex-col">
        <main className="w-full pt-16 min-h-screen bg-[#101419] px-4 md:px-6 py-5">
          {currentPath === 'overview-live-command' && (
            <LiveCommandOverview
              onInvestigate={(id) => handleOpenActiveIncident(id)}
              onExploreGraph={() => setCurrentPath('hindsight-experience-graph')}
              onNavigateToDemo={() => setCurrentPath('demo')}
            />
          )}

          {currentPath === 'incidents' && (
            <IncidentsList
              onInvestigate={(id) => handleOpenActiveIncident(id)}
              onCreateIncident={() => setIsCreateIncidentOpen(true)}
            />
          )}

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

          {currentPath === 'memory-lifecycle' && <MemoryLifecycleView />}

          {currentPath === 'response-operations-actions' && <ResponseOperationsView />}

          {currentPath === 'incident-timeline' && <IncidentTimelineView />}

          {currentPath === 'analytics-post-mortem-history' && <PostMortemAnalyticsView />}

          {currentPath === 'audit-trail' && <AuditTrailView />}

          {currentPath === 'demo' && (
            <DemoPresentationView
              onInvestigateIncident={(id) => handleOpenActiveIncident(id)}
              onExploreMemory={() => setCurrentPath('hindsight-experience-graph')}
            />
          )}

          {currentPath === 'settings-integrations' && <SettingsView />}

          {currentPath === 'ai-analysis' && (
            <AiAnalysisView
              initialIncidentId={activeInvestigationId}
              onNavigateToWorkspace={(id) => handleOpenActiveIncident(id)}
              onNavigateToMemory={() => setCurrentPath('hindsight-experience-graph')}
            />
          )}

          {currentPath === 'admin' && <AdminAccessControlView />}

          {currentPath === 'profile' && (
            <AuthPages
              view="profile"
              onNavigate={(target) => {
                if (target === 'command') setCurrentPath('overview-live-command');
                else if (target === 'login') setCurrentPath('overview-live-command');
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
