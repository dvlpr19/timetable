import { Download } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import { useAuth } from '@/auth/useAuth';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Pill } from '@/components/ui/Pill';
import { EmptyState, ErrorState, LoadingRows } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { download } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useAll } from '@/lib/query';
import type { SolverRun } from '@/types/solver';

import { RunPanel } from './RunPanel';
import { STATUS_PILL, duration, isActive } from './runs';
import { StartForm } from './StartForm';

/** Automatic timetabling (CP-SAT): start a run, watch it, compare the result. */
export function SolverPage() {
  const { t, i18n } = useTranslation(['admin', 'common']);
  const { user } = useAuth();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const canEdit = user?.role === 'admin';
  const runs = useAll<SolverRun>('/api/solver-runs/');
  const selected = Number(params.get('run')) || runs.rows[0]?.id;
  const select = (id: number) => setParams({ run: String(id) }, { replace: true });
  const date = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: 'short',
    timeStyle: 'short',
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-ink">{t('admin:solver.title')}</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink-muted">{t('admin:solver.intro')}</p>
      </div>

      {canEdit && <StartForm onStarted={(run) => (select(run.id), void runs.refetch())} />}

      <div className="grid gap-6 xl:grid-cols-[3fr_2fr]">
        <div className="min-w-0">
          {selected ? <RunPanel key={selected} id={selected} canEdit={canEdit} /> : null}
        </div>

        <Card className="min-w-0 p-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-ink">{t('admin:solver.history')}</h2>
            <Button
              variant="ghost"
              icon={<Download size={16} aria-hidden="true" />}
              disabled={!runs.rows.length}
              onClick={() =>
                download('/api/solver-runs/export/', 'solver-runs.csv').catch(() =>
                  toast(t('common:errors.unknown'), 'error'),
                )
              }
            >
              {t('admin:solver.exportRuns')}
            </Button>
          </div>
          {runs.isLoading ? (
            <LoadingRows rows={4} />
          ) : runs.isError ? (
            <ErrorState onRetry={() => runs.refetch()} />
          ) : !runs.rows.length ? (
            <EmptyState
              title={t('admin:solver.noRuns')}
              text={canEdit ? t('admin:solver.noRunsHint') : undefined}
            />
          ) : (
            <ul className="space-y-2">
              {runs.rows.map((run) => (
                <li key={run.id}>
                  <button
                    type="button"
                    onClick={() => select(run.id)}
                    aria-current={run.id === selected ? 'true' : undefined}
                    className={cn(
                      'w-full rounded-button border p-3 text-left text-sm transition-colors',
                      run.id === selected
                        ? 'border-primary-500 bg-subtle'
                        : 'border-line hover:bg-subtle/60',
                    )}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="font-bold text-ink">#{run.id}</span>
                      <Pill className={STATUS_PILL[run.status]}>{run.status_display}</Pill>
                    </span>
                    <span className="mt-1 block text-xs text-ink-muted">
                      {date.format(new Date(run.created_at))} ·{' '}
                      {run.faculty_name ?? t('admin:solver.allFaculties')} ·{' '}
                      {run.form_name ?? t('admin:solver.allForms')}
                    </span>
                    {!isActive(run.status) && run.status !== 'cancelled' && (
                      <span className="mt-1 block text-xs text-ink">
                        {t('admin:solver.historyLine', {
                          placed: run.lessons_placed,
                          total: run.lessons_total,
                          hard: run.hard_violations,
                          score: run.soft_violations.score ?? '—',
                          seconds: duration(run) ?? '—',
                        })}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
