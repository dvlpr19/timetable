import { useQueries } from '@tanstack/react-query';

import { api } from '@/lib/api';
import { withParams } from '@/lib/query';
import type { Paginated } from '@/lib/query';

import type { Resource, Row } from './resources';

/** Human label for a related row in the current language. */
export function optionLabel(row: Row): string {
  for (const key of ['label', 'short_name', 'name', 'code']) {
    const value = row[key];
    if (typeof value === 'string' && value) return value;
  }
  return String(row.id);
}

export function allUrl(path: string): string {
  return withParams(path, { page_size: 1000 });
}

export async function fetchAll(path: string): Promise<Row[]> {
  const data = await api<Paginated<Row> | Row[]>(allUrl(path));
  return Array.isArray(data) ? data : data.results;
}

/** id → label maps for every list column that points to another collection. */
export function useOptionMaps(resource: Resource): Record<string, Map<number, string>> {
  const remoteColumns = resource.columns
    .map((c) => ({ column: c, field: resource.fields.find((f) => f.key === c.key) }))
    .filter(({ field }) => field?.path && (field.type === 'remote' || field.type === 'remotes'));
  const results = useQueries({
    queries: remoteColumns.map(({ field }) => ({
      queryKey: [allUrl(field!.path!)],
      queryFn: () => api<Paginated<Row> | Row[]>(allUrl(field!.path!)),
      staleTime: 60_000,
    })),
  });
  const maps: Record<string, Map<number, string>> = {};
  remoteColumns.forEach(({ column }, i) => {
    const data = results[i].data;
    const rows = Array.isArray(data) ? data : (data?.results ?? []);
    maps[column.key] = new Map(rows.map((r) => [r.id, optionLabel(r)]));
  });
  return maps;
}
