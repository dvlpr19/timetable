import { useApi } from './query';
import { toISO } from './dates';

interface Meta {
  today: string;
  now: string;
  demo_date: boolean;
}

/**
 * The app's "today". The server may pin a demo date (DEMO_NOW) so the demo semester has
 * lessons; the time of day is always the real one.
 */
export function useToday(): { today: string; demo: boolean; ready: boolean } {
  const meta = useApi<Meta>('/api/meta/', {}, { staleTime: 5 * 60_000 });
  return {
    today: meta.data?.today ?? toISO(new Date()),
    demo: Boolean(meta.data?.demo_date),
    ready: !meta.isLoading,
  };
}
