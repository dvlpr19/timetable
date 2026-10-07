import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';

import { api } from './api';
import { useApi } from './query';
import type { Paginated } from './query';

export interface AppNotification {
  id: number;
  kind: string;
  title: string;
  body: string;
  comment: string;
  entry: number | null;
  lesson_date: string | null;
  was: string | null;
  now: string | null;
  is_read: boolean;
  created_at: string;
}

/** Kinds that describe a change to a lesson (shown as the yellow card on "Today"). */
export const LESSON_CHANGES = [
  'room_changed',
  'time_changed',
  'cancelled',
  'teacher_changed',
  'link_changed',
  'lesson_added',
];

// 25 s + the ~2 s announcement keeps "changed → seen in the app" under 30 s even without push
const POLL_MS = 25_000;

/** The bell: unread count, refreshed every 25 seconds (also in a background tab). */
export function useUnreadCount() {
  const q = useApi<{ count: number; latest: number | null }>(
    '/api/notifications/unread-count/',
    {},
    {
      refetchInterval: POLL_MS,
      refetchIntervalInBackground: true,
      staleTime: 10_000,
    },
  );
  return q.data?.count ?? 0;
}

export function useNotifications(params: { unread?: boolean } = {}) {
  const q = useApi<Paginated<AppNotification>>(
    '/api/notifications/',
    {
      unread: params.unread ? 1 : undefined,
      page_size: 50,
    },
    { refetchInterval: POLL_MS, refetchIntervalInBackground: true },
  );
  return { ...q, items: q.data?.results ?? [] };
}

export function useMarkRead() {
  const queryClient = useQueryClient();
  const refresh = useCallback(
    () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['/api/notifications/unread-count/'] }),
        queryClient.invalidateQueries({
          predicate: (q) => String(q.queryKey[0]).startsWith('/api/notifications/?'),
        }),
      ]),
    [queryClient],
  );
  const one = useCallback(
    async (id: number) => {
      await api(`/api/notifications/${id}/read/`, { method: 'POST' });
      await refresh();
    },
    [refresh],
  );
  const all = useCallback(async () => {
    await api('/api/notifications/read-all/', { method: 'POST' });
    await refresh();
  }, [refresh]);
  return { one, all };
}
