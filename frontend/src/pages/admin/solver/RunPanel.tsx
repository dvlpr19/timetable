import { useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Download, Loader2, Square } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Pill } from '@/components/ui/Pill';
import { ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api, download } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useApi } from '@/lib/query';
import type { Comparison, SolverRun } from '@/types/solver';
import { SOFT_CODES } from '@/types/solver';

import { DiagnosticList } from './DiagnosticList';
import { STATUS_PILL, duration, isActive } from './runs';

/** One run: live progress while it works, then the result, reasons and comparison. */
export function RunPanel({ id, canEdit }: { id: number; canEdit: boolean }) {
  const { t } = useTranslation(['admin', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useApi<SolverRun>(
    `/api/solver-runs/${id}/`,
    {},
    {
      refetchInterval: (q) => (q.state.data && isActive(q.state.data.status) ? 1000 : false),
      // keep watching while the dispatcher looks at another tab
      refetchIntervalInBackground: true,
    },
  );
  const run = query.data;
  const finished = run && !isActive(run.status);
  const compare = useApi<Comparison>(
    run?.result_schedule ? `/api/solver-runs/${id}/compare/` : null,
  );

  // When the run finishes, refresh lists (new draft version, run history).
  const wasActive = useRef(false);
  useEffect(() => {
    if (!run) return;
    if (isActive(run.status)) wasActive.current = true;
    else if (wasActive.current) {
      wasActive.current = false;
      void queryClient.invalidateQueries();
    }
  }, [run, queryClient]);

  if (query.isError) return <ErrorState onRetry={() => query.refetch()} />;
  if (!run) return <Skeleton className="h-64 w-full" />;

  async function cancel() {
    try {
      await api(`/api/solver-runs/${id}/cancel/`, { method: 'POST' });
      await query.refetch();
    } catch {
      toast(t('common:errors.unknown'), 'error');
    }
  }

  const p = run.progress ?? {};
  const limit = run.params.time_limit ?? 90;
  const placedPct = p.total ? Math.round((100 * (p.placed ?? 0)) / p.total) : 0;
  const timePct = Math.min(100, Math.round((100 * (p.elapsed ?? 0)) / limit));
  const scope = [
    run.faculty_name ?? t('admin:solver.allFaculties'),
    run.form_name ?? t('admin:solver.allForms'),
  ].join(' · ');

  return (
    <Card className="space-y-5 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-ink">
            {t('admin:solver.runTitle', { id: run.id })}
          </h2>
          <p className="text-sm text-ink-muted">
            {scope} · {t(`admin:solver.modes.${run.params.mode ?? 'rebuild'}`)} ·{' '}
            {t('admin:solver.seconds', { n: limit })}
          </p>
        </div>
        <Pill className={STATUS_PILL[run.status]}>
          {isActive(run.status) && (
            <Loader2 size={12} aria-hidden="true" className="animate-spin" />
          )}
          {run.status_display}
        </Pill>
      </div>

      {isActive(run.status) && (
        <div className="space-y-4" aria-live="polite">
          <p className="text-sm font-semibold text-ink">
            {run.status === 'queued'
              ? t('admin:solver.queued')
              : p.phase === 'improving'
                ? t('admin:solver.phaseImproving')
                : t('admin:solver.phasePlacing')}
          </p>
          <Bar
            label={t('admin:solver.placedBar', { placed: p.placed ?? 0, total: p.total ?? '…' })}
            percent={placedPct}
          />
          <Bar
            label={t('admin:solver.timeBar', { elapsed: Math.round(p.elapsed ?? 0), limit })}
            percent={timePct}
            muted
          />
          {canEdit && (
            <Button
              variant="secondary"
              icon={<Square size={16} aria-hidden="true" />}
              onClick={cancel}
            >
              {t('admin:solver.cancel')}
            </Button>
          )}
        </div>
      )}

      {finished && (
        <>
          <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat
              label={t('admin:solver.placed')}
              value={`${run.lessons_placed} / ${run.lessons_total}`}
              warn={run.lessons_placed < run.lessons_total}
            />
            <Stat
              label={t('admin:solver.hard')}
              value={run.hard_violations}
              warn={run.hard_violations > 0}
            />
            <Stat label={t('admin:solver.softScore')} value={run.soft_violations.score ?? '—'} />
            <Stat
              label={t('admin:solver.duration')}
              value={t('admin:solver.seconds', { n: duration(run) ?? '—' })}
            />
          </dl>

          {run.result_schedule && (
            <div className="flex flex-wrap gap-2">
              <Link
                to={`/admin/schedule?v=${run.result_schedule}`}
                className="inline-flex min-h-touch items-center gap-2 rounded-full bg-primary-700 px-5 text-base font-semibold text-ink-on-primary hover:bg-primary-900"
              >
                {t('admin:solver.openDraft')}
                <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <Button
                variant="secondary"
                icon={<Download size={18} aria-hidden="true" />}
                onClick={() =>
                  download(`/api/solver-runs/${id}/entries/`, `solver-run-${id}.csv`).catch(() =>
                    toast(t('common:errors.unknown'), 'error'),
                  )
                }
              >
                {t('admin:solver.csv')}
              </Button>
            </div>
          )}

          {compare.data && <CompareTable data={compare.data} />}

          {run.diagnostics.length > 0 && (
            <div>
              <h3 className="mb-2 text-base font-bold text-ink">{t('admin:solver.diagnostics')}</h3>
              <DiagnosticList items={run.diagnostics} />
            </div>
          )}
        </>
      )}
    </Card>
  );
}

function Bar({ label, percent, muted }: { label: string; percent: number; muted?: boolean }) {
  return (
    <div>
      <p className="mb-1 text-xs font-semibold text-ink-muted">{label}</p>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="h-2 overflow-hidden rounded-full bg-subtle"
      >
        <div
          className={cn(
            'h-2 rounded-full transition-all',
            muted ? 'bg-ink-muted/50' : 'bg-primary-500',
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function Stat({ label, value, warn }: { label: string; value: string | number; warn?: boolean }) {
  return (
    <div className="rounded-button bg-subtle p-3">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className={cn('text-xl font-extrabold', warn ? 'text-danger-fg' : 'text-ink')}>
        {value}
      </dd>
    </div>
  );
}

function CompareTable({ data }: { data: Comparison }) {
  const { t } = useTranslation(['admin']);
  const { base, result } = data;
  const rows: {
    label: string;
    base?: number | string;
    result: number | string;
    better?: boolean;
  }[] = [
    { label: t('admin:solver.cmp.lessons'), base: base?.lessons, result: result.lessons },
    {
      label: t('admin:solver.cmp.missing'),
      base: base?.missing,
      result: result.missing,
      better: base ? result.missing < base.missing : undefined,
    },
    {
      label: t('admin:solver.cmp.hard'),
      base: base?.hard_conflicts,
      result: result.hard_conflicts,
    },
    { label: t('admin:solver.cmp.links'), base: base?.links_missing, result: result.links_missing },
    ...SOFT_CODES.map((code) => ({
      label: t(`admin:soft.${code}`),
      base: base?.soft[code],
      result: result.soft[code] ?? 0,
    })),
  ];
  return (
    <div>
      <h3 className="mb-1 text-base font-bold text-ink">{t('admin:solver.cmp.title')}</h3>
      {base && (
        <p className="mb-2 text-xs text-ink-muted">
          {t('admin:solver.cmp.moves', {
            kept: data.kept,
            added: data.added,
            removed: data.removed,
          })}
        </p>
      )}
      <div className="overflow-x-auto rounded-button border border-line">
        <table className="w-full min-w-[420px] text-left text-sm">
          <thead className="bg-subtle text-xs font-bold uppercase text-ink-muted">
            <tr>
              <th scope="col" className="px-3 py-2">
                {t('admin:solver.cmp.measure')}
              </th>
              {base && (
                <th scope="col" className="px-3 py-2">
                  {base.name}
                </th>
              )}
              <th scope="col" className="px-3 py-2">
                {result.name}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label} className="border-t border-line">
                <th scope="row" className="px-3 py-2 font-medium text-ink">
                  {r.label}
                </th>
                {base && <td className="px-3 py-2 tabular-nums text-ink-muted">{r.base ?? '—'}</td>}
                <td
                  className={cn(
                    'px-3 py-2 font-semibold tabular-nums text-ink',
                    r.better && 'text-lesson-lecture',
                  )}
                >
                  {r.result}
                </td>
              </tr>
            ))}
            <tr className="border-t border-line bg-subtle/60">
              <th scope="row" className="px-3 py-2 font-bold text-ink">
                {t('admin:solver.softScore')}
              </th>
              {base && <td className="px-3 py-2 font-bold tabular-nums">{base.soft_score}</td>}
              <td className="px-3 py-2 font-bold tabular-nums">{result.soft_score}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="mt-1 text-xs text-ink-muted">{t('admin:solver.cmp.lowerBetter')}</p>
    </div>
  );
}
