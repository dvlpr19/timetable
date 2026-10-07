import { useCachedApi } from '@/lib/offline';
import type { Occurrence } from '@/types/timetable';

export type Target = { me: 1 } | { group: number } | { teacher: number } | { room: number };

/** Dated lessons (with cancellations and holidays) between two dates, cached for offline. */
export function useLessons(target: Target | null, from: string, to: string) {
  return useCachedApi<Occurrence[]>(target ? '/api/timetable/occurrences/' : null, {
    ...(target ?? {}),
    date_from: from,
    date_to: to,
  });
}
