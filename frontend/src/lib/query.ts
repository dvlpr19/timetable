import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';

import { api } from './api';

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type Params = Record<string, string | number | boolean | null | undefined>;

export function withParams(path: string, params: Params = {}): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value));
  }
  const query = qs.toString();
  return query ? `${path}${path.includes('?') ? '&' : '?'}${query}` : path;
}

/** GET returning a typed body; the query key is the URL itself. */
export function useApi<T>(
  path: string | null,
  params: Params = {},
  options: Omit<UseQueryOptions<T>, 'queryKey' | 'queryFn'> = {},
) {
  const url = path ? withParams(path, params) : '';
  return useQuery<T>({
    queryKey: [url],
    queryFn: () => api<T>(url),
    enabled: Boolean(path) && options.enabled !== false,
    ...options,
  });
}

/** All rows of a (small) collection, e.g. options for a select. */
export function useAll<T>(path: string | null, params: Params = {}) {
  const query = useApi<Paginated<T> | T[]>(path, { page_size: 1000, ...params });
  const data = query.data;
  return { ...query, rows: Array.isArray(data) ? data : (data?.results ?? []) };
}

/** Mutation that refreshes every cached GET afterwards (lists are cheap to refetch). */
export function useApiMutation<TBody, TResult = unknown>(
  method: 'POST' | 'PATCH' | 'PUT' | 'DELETE',
  path: string | ((body: TBody) => string),
) {
  const queryClient = useQueryClient();
  return useMutation<TResult, Error, TBody>({
    mutationFn: (body: TBody) =>
      api<TResult>(typeof path === 'function' ? path(body) : path, {
        method,
        body: method === 'DELETE' ? undefined : body,
      }),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}
