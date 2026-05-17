import { PageStateProvider, usePageState } from './state/PageStateContext';
import { FilePicker } from './components/FilePicker';
import { DropZone } from './components/DropZone';
import { TabStrip } from './components/TabStrip';
import { SummaryTab } from './tabs/SummaryTab';
import { TimelinesTab } from './tabs/TimelinesTab';
import { TeamTab } from './tabs/TeamTab';
import { MapTab } from './tabs/MapTab';
import { AnalysisStub } from './tabs/AnalysisStub';
import { MapStub } from './tabs/MapStub';

function ErrorBanner() {
  const { pageState, dispatchers } = usePageState();
  if (!pageState.errorMessage) return null;
  return (
    <div className="error-banner" role="alert">
      {pageState.errorMessage}
      <button
        type="button"
        onClick={dispatchers.clearError}
        className="error-banner__dismiss"
        aria-label="Dismiss error"
      >
        ×
      </button>
    </div>
  );
}

function ActiveTabBody() {
  const { pageState } = usePageState();
  if (!pageState.analysis) return null;
  switch (pageState.activeTab) {
    case 'summary': return <SummaryTab />;
    case 'timelines': return <TimelinesTab />;
    case 'team': return <TeamTab analysis={pageState.analysis} />;
    case 'analysis': return <AnalysisStub />;
    case 'map': {
      // Feature 008 — Map tab is enabled when team.centroidTimeline is
      // present in the loaded JSON. Pre-008 files fall through to the
      // existing MapStub placeholder.
      const team = pageState.analysis.team;
      const hasTimeline = team && team.applicable && team.centroidTimeline;
      return hasTimeline
        ? <MapTab analysis={pageState.analysis} />
        : <MapStub />;
    }
  }
}

function Shell() {
  return (
    <main id="app">
      <header className="page-header">
        <h1>Boovcraft Replay Visualizer</h1>
        <p className="page-instruction">
          Pick a <code>.analysis.json</code> produced by{' '}
          <code>processor/analyze.py</code>, or drag one onto this page.
        </p>
        <FilePicker />
      </header>
      <ErrorBanner />
      <TabStrip />
      <ActiveTabBody />
      <DropZone />
    </main>
  );
}

export function App() {
  return (
    <PageStateProvider>
      <Shell />
    </PageStateProvider>
  );
}
