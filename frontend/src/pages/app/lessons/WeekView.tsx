import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { ErrorState, Skeleton } from '@/components/ui/States';
import { addDays, mondayOf, parseISO } from '@/lib/dates';
import type { Occurrence } from '@/types/timetable';
import { formatDayMonth } from '@/i18n/date';

import { DayList } from './DayList';
import { LastUpdated } from './LastUpdated';
import { LessonSheet } from './LessonSheet';
import { useLessons } from './useLessons';
import type { Target } from './useLessons';

interface Props {
  target: Target;
  viewer: 'student' | 'teacher';
  today: string;
  /** first week to show (defaults to the week of today) */
  startMonday?: string;
  canRequest?: boolean;
  /** extra line under the week switcher, e.g. the session dates */
  note?: ReactNode;
}

/** A week of real dates: Monday–Saturday (Sunday only if it has lessons). */
export function WeekView({ target, viewer, today, startMonday, canRequest = false, note }: Props) {
  const { t } = useTranslation(['app', 'dates']);
  const [monday, setMonday] = useState(startMonday ?? mondayOf(today));
  const [open, setOpen] = useState<Occurrence | null>(null);
  const sunday = addDays(monday, 6);
  const lessons = useLessons(target, monday, sunday);
  const weekdays = t('dates:weekdays', { returnObjects: true }) as string[];
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i)).filter(
    (d, i) => i < 6 || lessons.data?.some((l) => l.date === d),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 rounded-card border border-line bg-card p-2">
        <button
          type="button"
          onClick={() => setMonday(addDays(monday, -7))}
          aria-label={t('app:week.previous')}
          className="flex min-h-touch min-w-touch items-center justify-center rounded-button text-ink hover:bg-subtle"
        >
          <ChevronLeft size={22} aria-hidden="true" />
        </button>
        <div className="text-center">
          <p className="text-sm font-bold text-ink">
            {formatDayMonth(parseISO(monday), t)} – {formatDayMonth(parseISO(sunday), t)}
          </p>
          {monday !== mondayOf(today) && (
            <button
              type="button"
              onClick={() => setMonday(mondayOf(today))}
              className="text-xs font-semibold text-link hover:underline"
            >
              {t('app:week.thisWeek')}
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={() => setMonday(addDays(monday, 7))}
          aria-label={t('app:week.next')}
          className="flex min-h-touch min-w-touch items-center justify-center rounded-button text-ink hover:bg-subtle"
        >
          <ChevronRight size={22} aria-hidden="true" />
        </button>
      </div>
      {note}

      {lessons.isError && !lessons.data ? (
        <ErrorState onRetry={() => lessons.refetch()} />
      ) : !lessons.data ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        days.map((day) => (
          <section key={day} aria-labelledby={`day-${day}`}>
            <h2 id={`day-${day}`} className="mb-2 flex items-baseline gap-2 px-1">
              <span className="text-base font-extrabold capitalize text-ink">
                {weekdays[(parseISO(day).getDay() + 6) % 7]}
              </span>
              <span className="text-sm text-ink-muted">{formatDayMonth(parseISO(day), t)}</span>
              {day === today && (
                <span className="rounded-full bg-primary-700 px-2 text-xs font-bold text-ink-on-primary">
                  {t('app:day.today')}
                </span>
              )}
            </h2>
            <DayList
              lessons={lessons.data.filter((l) => l.date === day)}
              viewer={viewer}
              isToday={day === today}
              onOpen={setOpen}
            />
          </section>
        ))
      )}

      <LastUpdated
        at={lessons.updatedAt}
        stale={lessons.stale}
        fetching={lessons.isFetching}
        onRefresh={() => void lessons.refetch()}
      />
      {open && <LessonSheet lesson={open} canRequest={canRequest} onClose={() => setOpen(null)} />}
    </div>
  );
}
