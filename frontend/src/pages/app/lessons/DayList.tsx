import { Coffee } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { clockTime } from '@/lib/dates';
import type { Occurrence } from '@/types/timetable';

import { LessonItem } from './LessonItem';
import type { Moment } from './LessonItem';

interface Props {
  lessons: Occurrence[];
  viewer: 'student' | 'teacher';
  /** the day shown is today: mark the current and the next lesson */
  isToday?: boolean;
  onOpen: (lesson: Occurrence) => void;
}

/** Lessons of one day in time order, with "now" and "next" on today. */
export function DayList({ lessons, viewer, isToday, onOpen }: Props) {
  const { t } = useTranslation(['app']);
  const sorted = [...lessons].sort((a, b) =>
    a.lesson_time.start.localeCompare(b.lesson_time.start),
  );
  if (!sorted.length) {
    return (
      <p className="flex items-center gap-3 rounded-card border border-dashed border-line bg-card px-4 py-6 text-sm text-ink-muted">
        <Coffee size={20} aria-hidden="true" />
        {t('app:day.free')}
      </p>
    );
  }
  const now = clockTime();
  const live = sorted.filter((l) => l.status === 'scheduled');
  const current = isToday
    ? live.find((l) => l.lesson_time.start <= now && now < l.lesson_time.end)
    : undefined;
  const next = isToday ? live.find((l) => l.lesson_time.start > now) : undefined;
  const moment = (l: Occurrence): Moment => {
    if (!isToday) return null;
    if (l === current) return 'now';
    if (l === next) return 'next';
    return l.lesson_time.end <= now ? 'past' : null;
  };
  return (
    <ul className="space-y-2">
      {sorted.map((lesson) => (
        <li key={`${lesson.id}-${lesson.date}`}>
          <LessonItem lesson={lesson} viewer={viewer} moment={moment(lesson)} onOpen={onOpen} />
        </li>
      ))}
    </ul>
  );
}
