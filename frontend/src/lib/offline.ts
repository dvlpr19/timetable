import { useQuery } from '@tanstack/react-query';

import { api } from './api';
import { withParams } from './query';
import type { Params } from './query';

const PREFIX = 'dj.cache:';
const MAX_ENTRIES = 40;

interface Stored<T> {
  savedAt: number;
  data: T;
}

function read<T>(key: string): Stored<T> | undefined {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw ? (JSON.parse(raw) as Stored<T>) : undefined;
  } catch {
    return undefined;
  }
}

function write<T>(key: string, data: T): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify({ savedAt: Date.now(), data }));
    const keys = Object.keys(localStorage).filter((k) => k.startsWith(PREFIX));
    if (keys.length > MAX_ENTRIES) {
      keys
        .map((k) => [k, read<unknown>(k.slice(PREFIX.length))?.savedAt ?? 0] as const)
        .sort((a, b) => a[1] - b[1])
        .slice(0, keys.length - MAX_ENTRIES)
        .forEach(([k]) => localStorage.removeItem(k));
    }
  } catch {
    // storage full or blocked: the app still works online
  }
}

/** Forget cached timetables (on sign-out: the next person must not see them). */
export function clearOfflineCache(): void {
  try {
    Object.keys(localStorage)
      .filter((k) => k.startsWith(PREFIX))
      .forEach((k) => localStorage.removeItem(k));
  } catch {
    // ignore
  }
}

/**
 * GET that keeps the last good answer in localStorage. Offline (or when the server is down)
 * the saved copy is shown together with the time it was fetched ("last updated").
 */
export function useCachedApi<T>(path: string | null, params: Params = {}) {
  const url = path ? withParams(path, params) : '';
  const stored = url ? read<T>(url) : undefined;
  const query = useQuery<T>({
    queryKey: [url],
    queryFn: async () => {
      const data = await api<T>(url);
      write(url, data);
      return data;
    },
    enabled: Boolean(path),
    initialData: stored?.data,
    initialDataUpdatedAt: stored?.savedAt,
    staleTime: 30_000,
    retry: 1,
  });
  return {
    ...query,
    /** when the shown data was fetched from the server */
    updatedAt: query.dataUpdatedAt || stored?.savedAt || 0,
    /** showing saved data because the last refresh failed */
    stale: query.isError && query.data !== undefined,
  };
}
