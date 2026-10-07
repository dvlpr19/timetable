import { useQueryClient } from '@tanstack/react-query';
import { Ban, Check, Minus, Save, Star } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { ScreenHeader } from '@/components/ScreenHeader';
import { Button } from '@/components/ui/Button';
import { Segmented } from '@/components/ui/Segmented';
import { ErrorState, LoadingRows } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useAll, useApi } from '@/lib/query';
import type { EducationForm } from '@/types/timetable';

type Level = 'possible' | 'preferred' | 'unavailable';
interface Row {
  weekday: number;
  lesson_time: number | null;
  level: Level;
}

const NEXT: Record<Level, Level> = {
  possible: 'preferred',
  preferred: 'unavailable',
  unavailable: 'possible',
};
const STYLE: Record<Level, string> = {
  possible: 'border-line bg-card text-ink-muted',
  preferred: 'border-lesson-lecture bg-lesson-lecture-bg text-lesson-lecture',
  unavailable: 'border-danger-fg/40 bg-danger-bg text-danger-fg',
};
const ICON = { possible: Minus, preferred: Star, unavailable: Ban };

/** "Qulay kunlarim": tap a cell to cycle possible → preferred → unavailable. */
export function AvailabilityPage() {
  const { t } = useTranslation(['app', 'dates', 'common']);
  const { user } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const teacherId = user?.teacher?.id;
  const forms = useAll<EducationForm>('/api/education-forms/');
  const saved = useApi<Row[]>(teacherId ? '/api/teacher-availability/' : null, {
    teacher: teacherId,
  });
  const [formId, setFormId] = useState<number | null>(null);
  const [cells, setCells] = useState<Map<string, Level>>(new Map()); // `${weekday}:${lt}`
  const [days, setDays] = useState<Map<number, Level>>(new Map()); // whole-day levels
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const weekdays = t('dates:weekdays', { returnObjects: true }) as string[];

  useEffect(() => {
    if (!saved.data) return;
    const c = new Map<string, Level>();
    const d = new Map<number, Level>();
    for (const r of saved.data) {
      if (r.lesson_time === null) d.set(r.weekday, r.level);
      else c.set(`${r.weekday}:${r.lesson_time}`, r.level);
    }
    setCells(c);
    setDays(d);
    setDirty(false);
  }, [saved.data]);

  const form =
    forms.rows.find((f) => f.id === formId) ??
    forms.rows.find((f) => f.code === 'kunduzgi') ??
    forms.rows[0];
  const times = useMemo(
    () => [...(form?.lesson_times ?? [])].sort((a, b) => a.number - b.number),
    [form],
  );
  const studyDays = [...(form?.study_weekdays ?? [])].sort((a, b) => a - b);

  const cycleCell = (weekday: number, lt: number) => {
    const key = `${weekday}:${lt}`;
    setCells((prev) => new Map(prev).set(key, NEXT[prev.get(key) ?? 'possible']));
    setDirty(true);
  };
  const cycleDay = (weekday: number) => {
    setDays((prev) => new Map(prev).set(weekday, NEXT[prev.get(weekday) ?? 'possible']));
    setDirty(true);
  };

  async function save() {
    if (!teacherId) return;
    const rows: Row[] = [];
    days.forEach(
      (level, weekday) => level !== 'possible' && rows.push({ weekday, lesson_time: null, level }),
    );
    cells.forEach((level, key) => {
      const [weekday, lt] = key.split(':').map(Number);
      if (level !== 'possible' && (days.get(weekday) ?? 'possible') === 'possible') {
        rows.push({ weekday, lesson_time: lt, level });
      }
    });
    setBusy(true);
    try {
      await api('/api/teacher-availability/replace/', {
        method: 'PUT',
        body: { teacher: teacherId, rows },
      });
      await queryClient.invalidateQueries({
        queryKey: ['/api/teacher-availability/'],
        exact: false,
      });
      setDirty(false);
      toast(t('app:availability.saved'));
    } catch {
      toast(t('common:errors.unknown'), 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <ScreenHeader title={t('app:tabs.availability')} subtitle={user?.teacher?.short_name} />
      <div className="space-y-4 px-4 py-5 sm:px-6">
        <p className="text-sm text-ink-muted">{t('app:availability.hint')}</p>
        <ul className="flex flex-wrap gap-3 text-xs">
          {(['preferred', 'possible', 'unavailable'] as Level[]).map((level) => {
            const Icon = ICON[level];
            return (
              <li
                key={level}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-semibold',
                  STYLE[level],
                )}
              >
                <Icon size={13} aria-hidden="true" />
                {t(`app:availability.levels.${level}`)}
              </li>
            );
          })}
        </ul>
        {forms.rows.length > 1 && form && (
          <Segmented
            label={t('app:availability.form')}
            value={String(form.id)}
            onChange={(v) => setFormId(Number(v))}
            options={forms.rows.map((f) => ({ value: String(f.id), label: f.name }))}
          />
        )}
        {saved.isError ? (
          <ErrorState onRetry={() => saved.refetch()} />
        ) : saved.isLoading || forms.isLoading ? (
          <LoadingRows rows={6} />
        ) : (
          <div className="space-y-3">
            {studyDays.map((weekday) => {
              const dayLevel = days.get(weekday) ?? 'possible';
              const DayIcon = ICON[dayLevel];
              return (
                <section key={weekday} className="rounded-card border border-line bg-card p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <h2 className="font-bold capitalize text-ink">{weekdays[weekday]}</h2>
                    <button
                      type="button"
                      onClick={() => cycleDay(weekday)}
                      aria-label={t('app:availability.wholeDayLabel', {
                        day: weekdays[weekday],
                        level: t(`app:availability.levels.${dayLevel}`),
                      })}
                      className={cn(
                        'inline-flex min-h-[36px] items-center gap-1.5 rounded-full border px-3 text-xs font-semibold',
                        STYLE[dayLevel],
                      )}
                    >
                      <DayIcon size={13} aria-hidden="true" />
                      {dayLevel === 'possible'
                        ? t('app:availability.wholeDay')
                        : t(`app:availability.levels.${dayLevel}`)}
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
                    {times.map((lt) => {
                      const level =
                        dayLevel !== 'possible'
                          ? dayLevel
                          : (cells.get(`${weekday}:${lt.id}`) ?? 'possible');
                      const Icon = ICON[level];
                      return (
                        <button
                          key={lt.id}
                          type="button"
                          disabled={dayLevel !== 'possible'}
                          onClick={() => cycleCell(weekday, lt.id)}
                          aria-label={t('app:availability.cellLabel', {
                            day: weekdays[weekday],
                            n: lt.number,
                            level: t(`app:availability.levels.${level}`),
                          })}
                          className={cn(
                            'flex min-h-[56px] flex-col items-center justify-center rounded-button border text-xs font-semibold transition-colors disabled:opacity-70',
                            STYLE[level],
                          )}
                        >
                          <span className="flex items-center gap-1">
                            <Icon size={12} aria-hidden="true" />
                            {lt.number}
                          </span>
                          <span className="font-normal">{lt.start.slice(0, 5)}</span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        )}
        <div className="sticky bottom-[calc(76px+env(safe-area-inset-bottom))] z-10">
          <Button
            block
            disabled={!dirty || busy}
            onClick={save}
            icon={
              dirty ? <Save size={18} aria-hidden="true" /> : <Check size={18} aria-hidden="true" />
            }
            className="shadow-lg"
          >
            {dirty ? t('app:availability.save') : t('app:availability.upToDate')}
          </Button>
        </div>
      </div>
    </>
  );
}
