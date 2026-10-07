import { useDroppable } from '@dnd-kit/core';
import { Check, Lock, X } from 'lucide-react';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import { cn } from '@/lib/cn';
import type { BlockedPeriod, EducationForm, GridCell, TimetableEntry } from '@/types/timetable';

import { blockedAt, entriesAt, parseDate, sortedTimes } from './grid';
import type { Day } from './grid';
import { LessonCard } from './LessonCard';
import type { GridView } from './LessonCard';
import { cellKey } from './useEditor';

interface Props {
  form: EducationForm;
  days: Day[];
  entries: TimetableEntry[];
  blocked: BlockedPeriod[];
  view: GridView;
  editable: boolean;
  conflictIds: Set<number>;
  /** while a lesson is being moved: per-cell options from the server */
  moving: boolean;
  cells: Map<string, GridCell> | null;
  onOpen: (entry: TimetableEntry) => void;
  onPick: (cell: GridCell) => void;
}

/**
 * Weekly grid: lesson times down, weekdays across. Session grid (sirtqi): dates down,
 * lesson times across, because a session has many more days than a week.
 */
export function TimetableGrid(props: Props) {
  const { t } = useTranslation(['admin', 'dates']);
  const { form, days } = props;
  const times = sortedTimes(form);
  const weekdays = t('dates:weekdays', { returnObjects: true }) as string[];
  const weekdaysShort = t('dates:weekdaysShort', { returnObjects: true }) as string[];
  const months = t('dates:monthsGenitive', { returnObjects: true }) as string[];
  const dayLabel = (day: Day) => {
    if (!day.date) return weekdays[day.weekday];
    const d = parseDate(day.date);
    return t('admin:editor.dateLabel', {
      day: d.getDate(),
      month: months[d.getMonth()],
      weekday: weekdaysShort[day.weekday],
    });
  };
  const timeLabel = (lt: (typeof times)[number]) => (
    <>
      <span className="block text-sm font-bold text-ink">
        {t('admin:editor.lessonNumber', { n: lt.number })}
      </span>
      <span className="block text-xs font-medium text-ink-muted">
        {lt.start.slice(0, 5)}–{lt.end.slice(0, 5)}
      </span>
    </>
  );

  if (!times.length || !days.length) {
    return (
      <p className="rounded-card bg-subtle p-6 text-sm text-ink-muted">
        {t('admin:editor.noGrid')}
      </p>
    );
  }

  const session = form.schedule_mode === 'session';
  const columns = session ? times.length : days.length;
  return (
    <div className="overflow-x-auto rounded-card border border-line bg-card">
      <table
        className="w-full border-collapse"
        style={{ minWidth: `${120 + columns * 150}px` }}
        aria-label={t('admin:editor.gridLabel')}
      >
        <thead>
          <tr className="bg-subtle">
            <th
              scope="col"
              className="w-28 border-b border-line px-3 py-2 text-left text-xs font-bold uppercase text-ink-muted"
            >
              {session ? t('admin:editor.date') : t('admin:editor.time')}
            </th>
            {session
              ? times.map((lt) => (
                  <th
                    key={lt.id}
                    scope="col"
                    className="border-b border-l border-line px-3 py-2 text-left"
                  >
                    {timeLabel(lt)}
                  </th>
                ))
              : days.map((day) => (
                  <th
                    key={day.key}
                    scope="col"
                    className="border-b border-l border-line px-3 py-2 text-left text-sm font-bold capitalize text-ink"
                  >
                    {dayLabel(day)}
                  </th>
                ))}
          </tr>
        </thead>
        <tbody>
          {session
            ? days.map((day) => (
                <tr key={day.key}>
                  <th
                    scope="row"
                    className="border-b border-line px-3 py-2 text-left align-top text-sm font-bold capitalize text-ink"
                  >
                    {dayLabel(day)}
                  </th>
                  {times.map((lt) => (
                    <Cell
                      key={lt.id}
                      {...props}
                      day={day}
                      time={lt}
                      label={`${dayLabel(day)}, ${lt.number}`}
                    />
                  ))}
                </tr>
              ))
            : times.map((lt) => (
                <tr key={lt.id}>
                  <th scope="row" className="border-b border-line px-3 py-2 text-left align-top">
                    {timeLabel(lt)}
                  </th>
                  {days.map((day) => (
                    <Cell
                      key={day.key}
                      {...props}
                      day={day}
                      time={lt}
                      label={`${dayLabel(day)}, ${lt.number}`}
                    />
                  ))}
                </tr>
              ))}
        </tbody>
      </table>
    </div>
  );
}

function Cell({
  form,
  day,
  time,
  label,
  entries,
  blocked,
  view,
  editable,
  conflictIds,
  moving,
  cells,
  onOpen,
  onPick,
}: Props & { day: Day; time: EducationForm['lesson_times'][number]; label: string }) {
  const { t } = useTranslation(['admin']);
  const tipId = useId();
  const key = cellKey({ weekday: day.weekday, date: day.date, lesson_time: time.id });
  const option = cells?.get(key);
  const { setNodeRef, isOver } = useDroppable({ id: key, disabled: !moving });
  const lock = blockedAt(blocked, form, day, time);
  const here = entriesAt(entries, day, time.id);
  const state = !moving || !cells ? 'idle' : option?.ok ? 'ok' : 'bad';
  const reasons = option?.reasons ?? [];

  return (
    <td
      ref={setNodeRef}
      className={cn(
        'group relative h-24 min-w-[150px] border-b border-l border-line p-1.5 align-top transition-colors',
        lock &&
          'bg-[repeating-linear-gradient(135deg,transparent,transparent_6px,rgb(var(--line))_6px,rgb(var(--line))_7px)]',
        state === 'ok' && 'bg-lesson-lecture-bg/70',
        state === 'bad' && 'bg-danger-bg/60',
        state === 'ok' && isOver && 'ring-2 ring-inset ring-primary-500',
        state === 'bad' && isOver && 'ring-2 ring-inset ring-danger-fg',
      )}
    >
      {lock && (
        <span className="mb-1 flex items-center gap-1 text-xs font-semibold text-ink-muted">
          <Lock size={12} aria-hidden="true" />
          <span className="truncate">{lock.name}</span>
        </span>
      )}
      <div className="space-y-1">
        {here.map((entry) => (
          <LessonCard
            key={entry.id}
            entry={entry}
            view={view}
            draggable={editable}
            conflict={conflictIds.has(entry.id)}
            onOpen={onOpen}
          />
        ))}
      </div>
      {state === 'ok' && option && (
        <button
          type="button"
          onClick={() => onPick(option)}
          aria-label={t('admin:editor.placeHere', { cell: label })}
          className="absolute inset-0 flex items-end justify-end p-1.5 text-primary-700 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500"
        >
          <Check size={16} aria-hidden="true" />
        </button>
      )}
      {state === 'bad' && (
        <>
          <span
            tabIndex={0}
            aria-describedby={tipId}
            aria-label={t('admin:editor.cannotPlace', { cell: label })}
            className="absolute inset-0 flex items-end justify-end p-1.5 text-danger-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-danger-fg"
          >
            <X size={16} aria-hidden="true" />
          </span>
          <div
            id={tipId}
            role="tooltip"
            className="pointer-events-none invisible absolute left-1/2 top-full z-20 mt-1 w-64 -translate-x-1/2 rounded-button bg-ink px-3 py-2 text-xs text-card opacity-0 shadow-lg transition-opacity group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100"
          >
            {reasons.length ? (
              <ul className="list-disc space-y-1 pl-4">
                {reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            ) : (
              t('admin:editor.notAvailable')
            )}
          </div>
        </>
      )}
    </td>
  );
}
