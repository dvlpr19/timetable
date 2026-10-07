import {
  ArrowRight,
  BellOff,
  CalendarClock,
  CalendarX,
  CheckCheck,
  DoorOpen,
  Link2,
  Megaphone,
  Plus,
  UserRoundCog,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { formatDayMonthTime } from '@/i18n/date';
import { cn } from '@/lib/cn';
import type { AppNotification } from '@/lib/notifications';

const ICONS: Record<string, LucideIcon> = {
  room_changed: DoorOpen,
  time_changed: CalendarClock,
  cancelled: CalendarX,
  teacher_changed: UserRoundCog,
  link_changed: Link2,
  lesson_added: Plus,
  reminder: CalendarClock,
  daily_digest: CalendarClock,
  schedule_published: Megaphone,
  request_answered: CheckCheck,
};

/** One message; unread ones are yellow, the old state of a lesson is crossed out. */
export function MessageCard({
  n,
  onRead,
  compact,
}: {
  n: AppNotification;
  onRead?: () => void;
  compact?: boolean;
}) {
  const { t } = useTranslation(['app', 'dates']);
  const Icon = ICONS[n.kind] ?? BellOff;
  const urgent = n.kind === 'cancelled' || n.kind === 'time_changed';
  return (
    <button
      type="button"
      onClick={onRead}
      aria-label={n.is_read ? undefined : `${t('app:messages.new')}: ${n.title}`}
      className={cn(
        'flex w-full gap-3 rounded-card border p-4 text-left transition-colors',
        n.is_read ? 'border-line bg-card' : 'border-gold/60 bg-warning-bg/60',
      )}
    >
      <span
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
          urgent ? 'bg-danger-bg text-danger-fg' : 'bg-lesson-lecture-bg text-lesson-lecture',
        )}
      >
        <Icon size={20} aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-start justify-between gap-2">
          <span className="font-bold text-ink">{n.title}</span>
          {!n.is_read && (
            <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-gold" aria-hidden="true" />
          )}
        </span>
        {n.was && n.now && (
          <span className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-ink-muted line-through">{n.was}</span>
            <ArrowRight size={14} aria-hidden="true" className="text-ink-muted" />
            <span className={cn('font-bold', urgent ? 'text-danger-fg' : 'text-ink')}>{n.now}</span>
          </span>
        )}
        {!compact && <span className="mt-1 block text-sm text-ink">{n.body}</span>}
        {n.comment && (
          <span className="mt-2 block rounded-button bg-card/70 px-3 py-2 text-sm text-ink">
            {t('app:messages.comment')}: {n.comment}
          </span>
        )}
        <span className="mt-2 block text-xs text-ink-muted">
          {formatDayMonthTime(new Date(n.created_at), t)}
        </span>
      </span>
    </button>
  );
}
