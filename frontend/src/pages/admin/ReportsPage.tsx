import { ArrowDown, ArrowUp, FileSpreadsheet, FileText, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Segmented } from '@/components/ui/Segmented';
import { Select } from '@/components/ui/Select';
import { EmptyState, ErrorState, LoadingRows } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { currentLanguage } from '@/i18n';
import { download } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useAll, useApi, withParams } from '@/lib/query';
import type { ScheduleVersion } from '@/types/timetable';

type Kind = 'plan' | 'teachers' | 'rooms';
type Cell = string | number | null;

interface Report {
  kind: Kind;
  title: string;
  subtitle: string;
  columns: { key: string; label: string; numeric: boolean }[];
  rows: Record<string, Cell>[];
  totals: Record<string, Cell> | null;
  notes: string[];
}

const KINDS: Kind[] = ['plan', 'teachers', 'rooms'];

function show(value: Cell | undefined): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(1);
  return value;
}

/** Highlight what needs attention: lessons short of the plan, teachers over the limit. */
function tone(kind: Kind, key: string, row: Record<string, Cell>): string | undefined {
  if (kind === 'plan' && key === 'difference' && row.status === 'less')
    return 'text-danger-fg font-bold';
  if (kind === 'plan' && key === 'difference' && row.status === 'more')
    return 'text-warning-fg font-bold';
  if (kind === 'teachers' && key === 'weekly' && row.status === 'over')
    return 'text-danger-fg font-bold';
  return undefined;
}

/** Plan fulfilment, teacher workload and room occupancy, with Excel and PDF. */
export function ReportsPage() {
  const { t } = useTranslation(['admin', 'common']);
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const kind = (KINDS.includes(params.get('kind') as Kind) ? params.get('kind') : 'plan') as Kind;
  const schedules = useAll<ScheduleVersion>('/api/schedules/');
  const faculties = useAll<{ id: number; name: string }>('/api/faculties/');
  const [schedule, setSchedule] = useState('');
  const [faculty, setFaculty] = useState('');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<{ key: string; desc: boolean } | null>(null);
  const filters = {
    schedule: schedule || undefined,
    faculty: kind === 'rooms' ? undefined : faculty || undefined,
  };
  const report = useApi<Report>(`/api/reports/${kind}/`, filters);

  const rows = useMemo(() => {
    const data = report.data;
    if (!data) return [];
    const q = query.trim().toLowerCase();
    let list = q
      ? data.rows.filter((r) =>
          data.columns.some(
            (c) =>
              !c.numeric &&
              String(r[c.key] ?? '')
                .toLowerCase()
                .includes(q),
          ),
        )
      : data.rows;
    if (sort) {
      list = [...list].sort((a, b) => {
        const x = a[sort.key] ?? -Infinity;
        const y = b[sort.key] ?? -Infinity;
        const cmp =
          typeof x === 'number' && typeof y === 'number'
            ? x - y
            : String(x).localeCompare(String(y));
        return sort.desc ? -cmp : cmp;
      });
    }
    return list;
  }, [report.data, query, sort]);

  const save = (type: 'xlsx' | 'pdf') =>
    download(
      withParams(`/api/reports/${kind}/`, { ...filters, type, lang: currentLanguage() }),
      `report-${kind}.${type}`,
    ).catch(() => toast(t('common:errors.unknown'), 'error'));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-ink">{t('admin:reports.title')}</h1>
          <p className="mt-1 text-sm text-ink-muted">{t('admin:reports.hint')}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            icon={<FileSpreadsheet size={18} aria-hidden="true" />}
            onClick={() => save('xlsx')}
            disabled={!report.data}
          >
            {t('admin:reports.excel')}
          </Button>
          <Button
            variant="secondary"
            icon={<FileText size={18} aria-hidden="true" />}
            onClick={() => save('pdf')}
            disabled={!report.data}
          >
            {t('admin:reports.pdf')}
          </Button>
        </div>
      </div>

      <Card className="flex flex-wrap items-center gap-3 p-3">
        <Segmented
          label={t('admin:reports.kind')}
          value={kind}
          onChange={(v) => {
            setParams({ kind: v }, { replace: true });
            setSort(null);
          }}
          options={KINDS.map((k) => ({ value: k, label: t(`admin:reports.kinds.${k}`) }))}
        />
        <Select
          label={t('admin:reports.version')}
          hideLabel
          className="min-w-[220px]"
          value={schedule}
          onChange={(e) => setSchedule(e.target.value)}
          placeholder={t('admin:reports.published')}
          options={schedules.rows
            .filter((s) => s.status !== 'published')
            .map((s) => ({ value: s.id, label: `${s.name} — ${t(`admin:status.${s.status}`)}` }))}
        />
        {kind !== 'rooms' && (
          <Select
            label={t('admin:reports.faculty')}
            hideLabel
            className="min-w-[200px]"
            value={faculty}
            onChange={(e) => setFaculty(e.target.value)}
            placeholder={t('admin:reports.allFaculties')}
            options={faculties.rows.map((f) => ({ value: f.id, label: f.name }))}
          />
        )}
        <label className="relative ml-auto min-w-[200px] flex-1 sm:flex-none">
          <span className="sr-only">{t('admin:reports.search')}</span>
          <Search
            size={16}
            aria-hidden="true"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('admin:reports.search')}
            className="min-h-touch w-full rounded-button border border-line bg-card py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-muted"
          />
        </label>
      </Card>

      {report.isError ? (
        <ErrorState onRetry={() => report.refetch()} />
      ) : report.isLoading || !report.data ? (
        <LoadingRows rows={8} />
      ) : (
        <>
          <p className="text-sm text-ink-muted">{report.data.subtitle}</p>
          {!rows.length ? (
            <EmptyState title={t('admin:reports.empty')} />
          ) : (
            <Card className="max-h-[65dvh] overflow-auto">
              <table className="w-full min-w-[760px] border-collapse text-sm">
                <thead className="sticky top-0 z-10 bg-subtle">
                  <tr>
                    {report.data.columns.map((c) => {
                      const active = sort?.key === c.key;
                      return (
                        <th
                          key={c.key}
                          scope="col"
                          aria-sort={active ? (sort.desc ? 'descending' : 'ascending') : undefined}
                          className={cn(
                            'border-b border-line px-3 py-2 text-xs font-bold uppercase text-ink-muted',
                            c.numeric ? 'text-right' : 'text-left',
                          )}
                        >
                          <button
                            type="button"
                            onClick={() =>
                              setSort(
                                active
                                  ? { key: c.key, desc: !sort.desc }
                                  : { key: c.key, desc: c.numeric },
                              )
                            }
                            className="inline-flex items-center gap-1 uppercase hover:text-ink"
                          >
                            {c.label}
                            {active &&
                              (sort.desc ? (
                                <ArrowDown size={12} aria-hidden="true" />
                              ) : (
                                <ArrowUp size={12} aria-hidden="true" />
                              ))}
                          </button>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} className="border-b border-line last:border-0 hover:bg-subtle/60">
                      {report.data!.columns.map((c) => (
                        <td
                          key={c.key}
                          className={cn(
                            'px-3 py-2 align-top text-ink',
                            c.numeric && 'text-right tabular-nums',
                            tone(kind, c.key, row),
                          )}
                        >
                          {show(row[c.key])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
                {report.data.totals && (
                  <tfoot className="sticky bottom-0 bg-subtle font-bold">
                    <tr>
                      {report.data.columns.map((c) => (
                        <td
                          key={c.key}
                          className={cn(
                            'border-t border-line px-3 py-2 text-ink',
                            c.numeric && 'text-right tabular-nums',
                          )}
                        >
                          {report.data!.totals![c.key] === undefined
                            ? ''
                            : show(report.data!.totals![c.key])}
                        </td>
                      ))}
                    </tr>
                  </tfoot>
                )}
              </table>
            </Card>
          )}
          <ul className="space-y-1 text-xs text-ink-muted">
            {report.data.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
