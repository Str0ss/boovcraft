import { usePageState } from '../state/PageStateContext';
import { MatchHeader } from '../components/MatchHeader';
import { TeamsGrid } from '../components/TeamsGrid';
import { ChatSection } from '../components/ChatSection';
import { ObserversSection } from '../components/ObserversSection';

export function SummaryTab() {
  const { pageState } = usePageState();
  if (!pageState.analysis) return null;
  const a = pageState.analysis;
  return (
    <section>
      <MatchHeader analysis={a} />
      <TeamsGrid analysis={a} />
      <ChatSection chat={a.chat} durationMs={a.match.durationMs} />
      <ObserversSection observers={a.observers} />
    </section>
  );
}
