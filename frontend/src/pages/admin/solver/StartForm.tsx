import { ClipboardCheck, Play, SlidersHorizontal } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Segmented } from '@/components/ui/Segmented';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { ApiError, api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useAll } from '@/lib/query';
import type { Precheck, SolverRun } from '@/types/solver';
import { DEFAULT_WEIGHTS, SOFT_CODES } from '@/types/solver';
import type { ScheduleVersion } from '@/types/timetable';

import { DiagnosticList } from './DiagnosticList';

const TIME_LIMITS = [30, 60, 90, 120, 300];

type Named = { id: number; name: string };

/** What to build: scope, starting version, mode, time limit and soft-constraint weights. */
export function StartForm({ onStarted }: { onStarted: (run: SolverRun) => void }) {
  const { t } = useTranslation(['admin', 'common']);
  const toast = useToast();
  const faculties = useAll<Named>('/api/faculties/');
  const forms = useAll<Named>('/api/education-forms/');
  const schedules = useAll<ScheduleVersion>('/api/schedules/');
  const [faculty, setFaculty] = useState('');
  const [form, setForm] = useState('');
  const [base, setBase] = useState('');
  const [mode, setMode] = useState<'rebuild' | 'fill'>('rebuild');
  const [timeLimit, setTimeLimit] = useState(90);
  const [weights, setWeights] = useState<Record<string, number>>({ ...DEFAULT_WEIGHTS });
  const [showWeights, setShowWeights] = useState(false);
  const [check, setCheck] = useState<Precheck | null>(null);
  const [busy, setBusy] = useState<'check' | 'start' | null>(null);

  const body = () => ({
    faculty: faculty ? Number(faculty) : null,
    form: form ? Number(form) : null,
    base_schedule: base ? Number(base) : null,
    mode,
    time_limit: timeLimit,
    weights,
  });

  async function send(kind: 'check' | 'start') {
    setBusy(kind);
    try {
      if (kind === 'check') {
        setCheck(
          await api<Precheck>('/api/solver-runs/precheck/', { method: 'POST', body: body() }),
        );
      } else {
        const run = await api<SolverRun>('/api/solver-runs/', { method: 'POST', body: body() });
        toast(t('admin:solver.started'));
        setCheck(null);
        onStarted(run);
      }
    } catch (err) {
      toast(
        err instanceof ApiError && err.detail ? err.detail : t('common:errors.unknown'),
        'error',
      );
    } finally {
      setBusy(null);
    }
  }

  const reset = () => setCheck(null);
  const published = schedules.rows.find((s) => s.status === 'published');

  return (
    <Card className="space-y-5 p-5">
      <h2 className="text-lg font-bold text-ink">{t('admin:solver.newRun')}</h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Select
          label={t('admin:solver.faculty')}
          value={faculty}
          onChange={(e) => (setFaculty(e.target.value), reset())}
          placeholder={t('admin:solver.allFaculties')}
          options={faculties.rows.map((f) => ({ value: f.id, label: f.name }))}
        />
        <Select
          label={t('admin:solver.form')}
          value={form}
          onChange={(e) => (setForm(e.target.value), reset())}
          placeholder={t('admin:solver.allForms')}
          options={forms.rows.map((f) => ({ value: f.id, label: f.name }))}
        />
        <Select
          label={t('admin:solver.base')}
          value={base}
          onChange={(e) => (setBase(e.target.value), reset())}
          placeholder={published ? t('admin:solver.basePublished', { name: published.name }) : '—'}
          options={schedules.rows
            .filter((s) => s.status !== 'published')
            .map((s) => ({ value: s.id, label: `${s.name} — ${t(`admin:status.${s.status}`)}` }))}
        />
        <Select
          label={t('admin:solver.timeLimit')}
          value={timeLimit}
          onChange={(e) => setTimeLimit(Number(e.target.value))}
          options={TIME_LIMITS.map((s) => ({
            value: s,
            label: t('admin:solver.seconds', { n: s }),
          }))}
        />
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold text-ink">{t('admin:solver.mode')}</p>
        <Segmented
          label={t('admin:solver.mode')}
          value={mode}
          onChange={(v) => (setMode(v), reset())}
          options={[
            { value: 'rebuild', label: t('admin:solver.modes.rebuild') },
            { value: 'fill', label: t('admin:solver.modes.fill') },
          ]}
        />
        <p className="mt-2 text-xs text-ink-muted">{t(`admin:solver.modeHint.${mode}`)}</p>
      </div>

      <div>
        <button
          type="button"
          aria-expanded={showWeights}
          onClick={() => setShowWeights((v) => !v)}
          className="inline-flex min-h-touch items-center gap-2 text-sm font-bold text-link"
        >
          <SlidersHorizontal size={16} aria-hidden="true" />
          {t('admin:solver.weights')}
        </button>
        {showWeights && (
          <div className="mt-2 grid gap-x-6 gap-y-3 sm:grid-cols-2 xl:grid-cols-3">
            {SOFT_CODES.map((code) => (
              <label key={code} className="flex items-center gap-3 text-sm text-ink">
                <span className="flex-1">{t(`admin:soft.${code}`)}</span>
                <input
                  type="range"
                  min={0}
                  max={20}
                  value={weights[code]}
                  onChange={(e) => setWeights((w) => ({ ...w, [code]: Number(e.target.value) }))}
                  className="w-28 accent-[rgb(var(--primary-700))]"
                />
                <span className="w-6 text-right font-bold tabular-nums">{weights[code]}</span>
              </label>
            ))}
            <p className="text-xs text-ink-muted sm:col-span-2 xl:col-span-3">
              {t('admin:solver.weightsHint')}
            </p>
          </div>
        )}
      </div>

      {check && (
        <div className="space-y-3 rounded-button bg-subtle p-4">
          <p className="text-sm font-semibold text-ink">
            {t('admin:solver.checkSummary', {
              units: check.units,
              lessons: check.lessons,
              kept: check.kept,
              replaced: check.replaced,
            })}
          </p>
          {check.diagnostics.length ? (
            <DiagnosticList items={check.diagnostics} />
          ) : (
            <p className="text-sm text-ink-muted">{t('admin:solver.checkClean')}</p>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          disabled={busy !== null}
          icon={<ClipboardCheck size={18} aria-hidden="true" />}
          onClick={() => send('check')}
        >
          {busy === 'check' ? t('admin:solver.checking') : t('admin:solver.check')}
        </Button>
        <Button
          disabled={busy !== null}
          icon={<Play size={18} aria-hidden="true" />}
          onClick={() => send('start')}
          className={cn(busy === 'start' && 'opacity-80')}
        >
          {t('admin:solver.start')}
        </Button>
      </div>
    </Card>
  );
}
