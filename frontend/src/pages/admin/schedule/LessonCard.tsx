import { useDraggable } from '@dnd-kit/core';
import { AlertTriangle, Pin, Video } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { cn } from '@/lib/cn';
import { lessonTypeClasses } from '@/lib/lessonTypes';
import { needsLink } from '@/lib/links';
import type { TimetableEntry } from '@/types/timetable';

import type { MoveSource } from './useEditor';

export type GridView = 'group' | 'teacher' | 'room';

interface Props {
  entry: TimetableEntry;
  view: GridView;
  draggable: boolean;
  conflict: boolean;
  onOpen: (entry: TimetableEntry) => void;
}

/** One lesson in a grid cell. Drag to move (dispatcher), click to open details. */
export function LessonCard({ entry, view, draggable, conflict, onOpen }: Props) {
  const { t } = useTranslation(['admin']);
  const source: MoveSource = { kind: 'entry', entry };
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `entry-${entry.id}`,
    data: { source },
    disabled: !draggable || entry.is_locked,
  });
  const colors = lessonTypeClasses(entry.lesson_type.code);
  // Show what the current view does not already tell: the group view hides the group, etc.
  const who = [
    view !== 'teacher' && entry.teacher.short_name,
    view !== 'group' && (entry.stream ?? entry.groups.map((g) => g.name).join(', ')),
    entry.subgroup && t('admin:editor.subgroup', { n: entry.subgroup }),
  ].filter(Boolean);
  const where = entry.room
    ? entry.room.name
    : needsLink(entry.online_url)
      ? t('admin:lesson.linkNeeded')
      : t('admin:editor.online');

  return (
    <button
      ref={setNodeRef}
      type="button"
      {...attributes}
      {...listeners}
      onClick={() => onOpen(entry)}
      aria-label={t('admin:editor.cardLabel', {
        subject: entry.subject.name,
        type: entry.lesson_type.name,
        teacher: entry.teacher.short_name,
        room: where || '—',
      })}
      className={cn(
        'relative w-full rounded-[10px] border-l-4 px-2 py-1.5 text-left text-xs leading-snug text-ink transition-shadow',
        colors.card,
        conflict ? 'border-danger-fg ring-2 ring-danger-fg' : 'border-transparent',
        draggable && !entry.is_locked ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer',
        isDragging && 'opacity-40',
        'hover:shadow-md',
      )}
    >
      <span className="flex items-start gap-1">
        <span className={cn('mt-1 h-2 w-2 shrink-0 rounded-full', colors.dot)} aria-hidden="true" />
        <span className="line-clamp-2 font-bold">{entry.subject.name}</span>
        <span className="ml-auto flex shrink-0 gap-0.5 text-ink-muted">
          {conflict && <AlertTriangle size={13} aria-hidden="true" className="text-danger-fg" />}
          {entry.is_locked && <Pin size={13} aria-hidden="true" />}
          {entry.online_url && (
            <Video
              size={13}
              aria-hidden="true"
              className={needsLink(entry.online_url) ? 'text-warning-fg' : undefined}
            />
          )}
        </span>
      </span>
      <span className="mt-0.5 block truncate text-ink-muted">
        {entry.lesson_type.name}
        {entry.week_parity && entry.week_parity !== 'every' && (
          <span className="ml-1 rounded bg-card px-1 font-bold text-ink">
            {t(`admin:editor.parity.${entry.week_parity}`)}
          </span>
        )}
      </span>
      {who.length > 0 && <span className="block truncate">{who.join(' · ')}</span>}
      {view !== 'room' && where && <span className="block truncate font-semibold">{where}</span>}
    </button>
  );
}

/** The floating copy that follows the pointer while dragging. */
export function LessonCardPreview({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="w-48 rounded-[10px] border border-primary-500 bg-card px-3 py-2 text-xs shadow-xl">
      <p className="font-bold text-ink">{title}</p>
      <p className="text-ink-muted">{subtitle}</p>
    </div>
  );
}
