import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { useAuth } from '@/auth/useAuth';
import { ScreenHeader } from '@/components/ScreenHeader';
import { ErrorState, Skeleton } from '@/components/ui/States';
import { formatLongDate } from '@/i18n/date';
import { useToday } from '@/lib/clock';
import { cn } from '@/lib/cn';
import { addDays, mondayOf, parseISO } from '@/lib/dates';
import { LESSON_CHANGES, useMarkRead, useNotifications } from '@/lib/notifications';
import type { Occurrence } from '@/types/timetable';

import { DayList } from './lessons/DayList';
import { MessageCard } from './MessageCard';
import { LastUpdated } from './lessons/LastUpdated';
import { LessonSheet } from './lessons/LessonSheet';
import { useLessons } from './lessons/useLessons';

/** "Bugun": today's lessons with what is on now and next; a strip to peek at the week. */
export function TodayPage() {
  const { t } = useTranslation(['app', 'dates', 'common']);
  const { user } = useAuth();
  const { today, demo } = useToday();
  const [picked, setPicked] = useState<string | null>(null);
  const [open, setOpen] = useState<Occurrence | null>(null);
  const day = picked ?? today;
  const monday = mondayOf(today);
  const lessons = useLessons({ me: 1 }, monday, addDays(monday, 6));
  const teacher = user?.role === 'oqituvchi';
  const unread = useNotifications({ unread: true });
  const mark = useMarkRead();
  const notices = unread.items.filter((n) => LESSON_CHANGES.includes(n.kind)).slice(0, 2);
  const short = t('dates:weekdaysShort', { returnObjects: true }) as string[];
  const strip = Array.from({ length: 7 }, (_, i) => addDays(monday, i)).filter(
    (d, i) => i < 6 || lessons.data?.some((l) => l.date === d),
  );
  const ofDay = (lessons.data ?? []).filter((l) => l.date === day);
  const count = (d: string) =>
    (lessons.data ?? []).filter((l) => l.date === d && l.status === 'scheduled').length;
  const subtitle = user?.student
    ? `${user.student.group.name}${user.student.subgroup ? ` · ${t('app:lesson.subgroup', { n: user.student.subgroup })}` : ''}`
    : user?.teacher?.department;

  return (
    <>
      <ScreenHeader
        subtitle={formatLongDate(parseISO(today), t)}
        title={t('app:today.greeting', { name: user?.first_name || user?.username })}
      >
        <p className="mt-1 text-sm text-mint">{subtitle}</p>
        {demo && (
          <p className="mt-2 inline-block rounded-full bg-white/10 px-3 py-1 text-xs text-mint">
            {t('app:today.demo')}
          </p>
        )}
        <div
          role="tablist"
          aria-label={t('app:today.days')}
          className="mt-5 flex justify-between gap-1"
        >
          {strip.map((d) => {
            const selected = d === day;
            const n = count(d);
            return (
              <button
                key={d}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-label={`${formatLongDate(parseISO(d), t)}: ${t('app:today.lessonsCount', { n })}`}
                onClick={() => setPicked(d)}
                className={cn(
                  'flex min-h-[64px] flex-1 flex-col items-center justify-center gap-1 rounded-button text-sm font-bold transition-colors',
                  selected ? 'bg-gold text-primary-900' : 'text-ink-on-primary hover:bg-white/10',
                  d === today && !selected && 'ring-1 ring-gold',
                )}
              >
                <span className="text-xs font-semibold opacity-80">
                  {short[(parseISO(d).getDay() + 6) % 7]}
                </span>
                <span className="text-lg leading-none">{parseISO(d).getDate()}</span>
                <span
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    n ? (selected ? 'bg-primary-900' : 'bg-gold') : 'bg-transparent',
                  )}
                />
              </button>
            );
          })}
        </div>
      </ScreenHeader>

      <div className="space-y-4 px-4 py-5 sm:px-6">
        {notices.length > 0 && (
          <section aria-label={t('app:messages.attention')} className="space-y-2">
            {notices.map((n) => (
              <MessageCard key={n.id} n={n} compact onRead={() => void mark.one(n.id)} />
            ))}
            {unread.items.length > notices.length && (
              <Link
                to="/messages"
                className="inline-flex min-h-touch items-center text-sm font-bold text-link hover:underline"
              >
                {t('app:messages.all', { n: unread.items.length })}
              </Link>
            )}
          </section>
        )}
        <h2 className="text-lg font-extrabold text-ink">
          {day === today ? (
            t('app:today.title')
          ) : (
            <span className="capitalize">{formatLongDate(parseISO(day), t)}</span>
          )}
        </h2>
        {lessons.isError && !lessons.data ? (
          <ErrorState onRetry={() => lessons.refetch()} />
        ) : !lessons.data ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
        ) : (
          <DayList
            lessons={ofDay}
            viewer={teacher ? 'teacher' : 'student'}
            isToday={day === today}
            onOpen={setOpen}
          />
        )}
        <LastUpdated
          at={lessons.updatedAt}
          stale={lessons.stale}
          fetching={lessons.isFetching}
          onRefresh={() => void lessons.refetch()}
        />
      </div>
      {open && <LessonSheet lesson={open} canRequest={teacher} onClose={() => setOpen(null)} />}
    </>
  );
}
