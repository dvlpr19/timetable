import { MapPin, Video } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Pill } from '@/components/ui/Pill';
import { cn } from '@/lib/cn';
import { lessonTypeClasses } from '@/lib/lessonTypes';
import { needsLink } from '@/lib/links';
import type { Occurrence } from '@/types/timetable';

export type Moment = 'now' | 'next' | 'past' | null;

interface Props {
  lesson: Occurrence;
  /** who looks: students see the teacher, teachers see the groups */
  viewer: 'student' | 'teacher';
  moment?: Moment;
  onOpen: (lesson: Occurrence) => void;
}

/** One lesson in a day list: time on the left, what / where / who on the right. */
export function LessonItem({ lesson, viewer, moment = null, onOpen }: Props) {
  const { t } = useTranslation(['app']);
  const colors = lessonTypeClasses(lesson.lesson_type.code);
  const off = lesson.status !== 'scheduled';
  const groups = lesson.stream ?? lesson.groups.map((g) => g.name).join(', ');
  const who =
    viewer === 'student'
      ? lesson.teacher.short_name
      : groups + (lesson.subgroup ? ` · ${t('app:lesson.subgroup', { n: lesson.subgroup })}` : '');
  return (
    <button
      type="button"
      onClick={() => onOpen(lesson)}
      className={cn(
        'flex w-full gap-3 rounded-card border bg-card p-3 text-left transition-shadow hover:shadow-md',
        moment === 'now' ? 'border-primary-500 ring-2 ring-primary-500/30' : 'border-line',
        (off || moment === 'past') && 'opacity-60',
      )}
    >
      <span className="w-14 shrink-0 text-center">
        <span className="block text-sm font-extrabold text-ink">{lesson.lesson_time.start}</span>
        <span className="block text-xs text-ink-muted">{lesson.lesson_time.end}</span>
        <span className="mt-1 block text-[11px] font-semibold text-ink-muted">
          {t('app:lesson.number', { n: lesson.lesson_time.number })}
        </span>
      </span>
      <span className={cn('w-1 shrink-0 rounded-full', colors.dot)} aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-1.5">
          {moment === 'now' && (
            <Pill className="bg-primary-700 text-ink-on-primary">{t('app:lesson.now')}</Pill>
          )}
          {moment === 'next' && <Pill className="bg-gold/25 text-ink">{t('app:lesson.next')}</Pill>}
          {lesson.status === 'cancelled' && (
            <Pill className="bg-danger-bg text-danger-fg">{t('app:lesson.cancelled')}</Pill>
          )}
          {lesson.status === 'reschedule' && (
            <Pill className="bg-warning-bg text-warning-fg">{t('app:lesson.holiday')}</Pill>
          )}
        </span>
        <span className={cn('mt-0.5 block font-bold text-ink', off && 'line-through')}>
          {lesson.subject.name}
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
          <Pill className={colors.pill}>{lesson.lesson_type.name}</Pill>
          <span className="inline-flex items-center gap-1">
            {lesson.room ? (
              <>
                <MapPin size={14} aria-hidden="true" />
                {lesson.room.name}
              </>
            ) : (
              <>
                <Video size={14} aria-hidden="true" />
                {needsLink(lesson.online_url) ? t('app:lesson.linkSoon') : t('app:lesson.online')}
              </>
            )}
          </span>
        </span>
        <span className="mt-1 block truncate text-sm text-ink">{who}</span>
      </span>
    </button>
  );
}
