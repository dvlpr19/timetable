import { ChevronLeft, ChevronRight, Eye, FileUp, Pencil, Plus, Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, useParams } from 'react-router-dom';

import { canWrite } from '@/auth/roles';
import { useAuth } from '@/auth/useAuth';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { EmptyState, ErrorState, LoadingRows } from '@/components/ui/States';
import { cn } from '@/lib/cn';
import { useAll, useApi } from '@/lib/query';
import type { Paginated } from '@/lib/query';

import { ImportDialog } from './ImportDialog';
import { ResourceForm } from './ResourceForm';
import { findResource } from './resources';
import type { Column, Resource, Row } from './resources';
import { optionLabel, useOptionMaps } from './options';

const PAGE_SIZE = 25;

export function ResourcePage() {
  const { resource: key } = useParams();
  const resource = findResource(key);
  if (!resource) return <Navigate to="/admin" replace />;
  return <ResourceView key={resource.key} resource={resource} />;
}

function ResourceView({ resource }: { resource: Resource }) {
  const { t } = useTranslation(['data', 'common']);
  const { user } = useAuth();
  const writable = canWrite(user?.role, resource.key);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Row | 'new' | null>(null);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  const list = useApi<Paginated<Row> | Row[]>(resource.path, {
    page,
    page_size: PAGE_SIZE,
    search: query || undefined,
    ...filters,
  });
  const rows = Array.isArray(list.data) ? list.data : (list.data?.results ?? []);
  const count = Array.isArray(list.data) ? list.data.length : (list.data?.count ?? 0);
  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const maps = useOptionMaps(resource);
  const title = t(`data:resources.${resource.key}.title`);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-ink">{title}</h1>
          <p className="mt-1 text-sm text-ink-muted">{t(`data:resources.${resource.key}.hint`)}</p>
        </div>
        {writable && (
          <div className="flex flex-wrap gap-2">
            {resource.importable && (
              <Button
                variant="secondary"
                icon={<FileUp size={18} aria-hidden="true" />}
                onClick={() => setImporting(true)}
              >
                {t('data:actions.import')}
              </Button>
            )}
            <Button icon={<Plus size={18} aria-hidden="true" />} onClick={() => setEditing('new')}>
              {t('data:actions.add')}
            </Button>
          </div>
        )}
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap gap-3">
          {resource.search && (
            <label className="relative min-w-[220px] flex-1">
              <span className="sr-only">{t('data:actions.search')}</span>
              <Search
                size={18}
                aria-hidden="true"
                className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
              />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t('data:actions.search')}
                className="min-h-touch w-full rounded-button border border-line bg-card py-2.5 pl-10 pr-4 text-base text-ink placeholder:text-ink-muted"
              />
            </label>
          )}
          {resource.filters?.map((f) => (
            <FilterSelect
              key={f.param}
              filter={f}
              value={filters[f.param] ?? ''}
              onChange={(value) => {
                setFilters((prev) => ({ ...prev, [f.param]: value }));
                setPage(1);
              }}
            />
          ))}
        </div>
      </Card>

      {list.isLoading ? (
        <LoadingRows rows={8} />
      ) : list.isError ? (
        <ErrorState onRetry={() => list.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState
          title={t('data:empty.title')}
          text={
            query || Object.values(filters).some(Boolean)
              ? t('data:empty.filtered')
              : t('data:empty.text')
          }
          action={
            writable && (
              <Button
                icon={<Plus size={18} aria-hidden="true" />}
                onClick={() => setEditing('new')}
              >
                {t('data:actions.add')}
              </Button>
            )
          }
        />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line bg-subtle text-xs font-bold uppercase tracking-wide text-ink-muted">
                {resource.columns.map((c) => (
                  <th key={c.key} scope="col" className="px-4 py-3">
                    {t(`data:fields.${c.label}`)}
                  </th>
                ))}
                <th scope="col" className="w-16 px-4 py-3 text-right">
                  <span className="sr-only">{t('data:actions.column')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-line last:border-0 hover:bg-subtle/60">
                  {resource.columns.map((c, i) => (
                    <td key={c.key} className="px-4 py-3 align-top text-ink">
                      {i === 0 ? (
                        <button
                          type="button"
                          onClick={() => setEditing(row)}
                          className="min-h-[28px] text-left font-semibold text-link hover:underline"
                        >
                          {renderCell(row, c, maps, t)}
                        </button>
                      ) : (
                        renderCell(row, c, maps, t)
                      )}
                    </td>
                  ))}
                  <td className="px-2 py-1.5 text-right align-middle">
                    <RowAction
                      writable={writable}
                      name={renderCell(row, resource.columns[0], maps, t)}
                      onClick={() => setEditing(row)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {pages > 1 && (
        <nav
          className="flex items-center justify-end gap-2"
          aria-label={t('data:pagination.label')}
        >
          <span className="text-sm text-ink-muted">
            {t('data:pagination.status', { page, pages, count })}
          </span>
          <Button
            variant="secondary"
            aria-label={t('data:pagination.previous')}
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft size={18} aria-hidden="true" />
          </Button>
          <Button
            variant="secondary"
            aria-label={t('data:pagination.next')}
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            <ChevronRight size={18} aria-hidden="true" />
          </Button>
        </nav>
      )}

      {editing && (
        <ResourceForm
          resource={resource}
          row={editing === 'new' ? null : editing}
          readOnly={!writable}
          onClose={() => setEditing(null)}
        />
      )}
      {importing && <ImportDialog resource={resource} onClose={() => setImporting(false)} />}
    </div>
  );
}

/** Pencil (or eye when read-only) button at the end of each row: opens the edit form. */
function RowAction({
  writable,
  name,
  onClick,
}: {
  writable: boolean;
  name: ReactNode;
  onClick: () => void;
}) {
  const { t } = useTranslation(['data']);
  const label = writable ? t('data:actions.edit') : t('data:actions.view');
  const Icon = writable ? Pencil : Eye;
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      className="inline-flex min-h-touch min-w-touch items-center justify-center rounded-button text-primary-700 transition-colors hover:bg-primary-500/10 hover:text-primary-900"
    >
      <Icon size={18} aria-hidden="true" />
      <span className="sr-only">
        {label}: {name}
      </span>
    </button>
  );
}

function FilterSelect({
  filter,
  value,
  onChange,
}: {
  filter: NonNullable<Resource['filters']>[number];
  value: string;
  onChange: (value: string) => void;
}) {
  const { t } = useTranslation(['data']);
  const remote = useAll<Row>(filter.path ?? null);
  const options = filter.path
    ? remote.rows.map((r) => ({ value: r.id, label: optionLabel(r) }))
    : (filter.values ?? []).map((v) => ({
        value: v,
        label: filter.choices ? t(`data:choices.${filter.choices}.${v}`) : String(v),
      }));
  return (
    <Select
      className="min-w-[180px]"
      label={t(`data:fields.${filter.label}`)}
      hideLabel
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={`${t(`data:fields.${filter.label}`)}: ${t('data:filters.all')}`}
      options={options}
    />
  );
}

function renderCell(
  row: Row,
  column: Column,
  maps: Record<string, Map<number, string>>,
  t: (key: string, options?: Record<string, unknown>) => string,
) {
  const value = row[column.key];
  if (column.kind === 'choice') {
    return value === '' || value === null || value === undefined
      ? '—'
      : t(`data:choices.${column.choices}.${value}`);
  }
  if (column.kind === 'bool') return value ? t('data:yes') : t('data:no');
  if (column.kind === 'load') {
    const max = Number(row.max_weekly_lessons ?? 0);
    const load = Number(value ?? 0);
    return (
      <span className={cn('font-semibold', load > max && 'text-danger-fg')}>
        {t('data:loadValue', { load, max })}
      </span>
    );
  }
  if (column.kind === 'hours') {
    return ['hours_lecture', 'hours_practice', 'hours_seminar', 'hours_lab']
      .map((k) => row[k] ?? 0)
      .join(' / ');
  }
  const map = maps[column.key];
  if (map) {
    if (Array.isArray(value)) return value.map((v) => map.get(Number(v)) ?? v).join(', ');
    return value === null || value === undefined ? '—' : (map.get(Number(value)) ?? String(value));
  }
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'string' && /^\d\d:\d\d:\d\d$/.test(value)) return value.slice(0, 5);
  return String(value);
}
