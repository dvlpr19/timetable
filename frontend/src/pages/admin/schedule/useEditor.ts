import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useToast } from '@/components/ui/Toast';
import { ApiError, api } from '@/lib/api';
import type {
  GridCell,
  ScheduleVersion,
  TimetableEntry,
  UnplacedItem,
  Violation,
} from '@/types/timetable';

import { pickBestCell } from './grid';

/** What is being moved: an existing lesson or a not yet placed assignment. */
export type MoveSource =
  | { kind: 'entry'; entry: TimetableEntry }
  | { kind: 'assignment'; assignment: number; label: string; online: boolean };

type Shown = Pick<TimetableEntry, 'date' | 'weekday' | 'subject'>;

export interface PendingChange {
  source: MoveSource;
  body: Record<string, unknown>;
  students: number;
  teachers: number;
  needsLink: boolean;
}

export function cellKey(cell: {
  weekday?: number | null;
  date?: string | null;
  lesson_time: number;
}) {
  return cell.date ? `d:${cell.date}:${cell.lesson_time}` : `w:${cell.weekday}:${cell.lesson_time}`;
}

function bodyFor(source: MoveSource, cell: GridCell, scheduleId: number) {
  const where = cell.date
    ? { date: cell.date, weekday: null, week_parity: null }
    : { weekday: cell.weekday, date: null };
  const body: Record<string, unknown> = { lesson_time: cell.lesson_time, ...where };
  if (cell.room) body.room = cell.room;
  if (source.kind === 'assignment') {
    body.schedule = scheduleId;
    body.assignment = source.assignment;
  }
  return body;
}

function endpoint(source: MoveSource) {
  return source.kind === 'entry'
    ? { method: 'PATCH' as const, path: `/api/entries/${source.entry.id}/` }
    : { method: 'POST' as const, path: '/api/entries/' };
}

/**
 * Move logic shared by drag-and-drop and the keyboard "move" mode:
 * load the per-cell options, apply a drop, ask for confirmation when the published
 * timetable changes (people will be notified).
 */
export function useEditor(schedule: ScheduleVersion | undefined) {
  const { t } = useTranslation(['admin', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [source, setSource] = useState<MoveSource | null>(null);
  const [cells, setCells] = useState<Map<string, GridCell> | null>(null);
  const [loadingCells, setLoadingCells] = useState(false);
  const [pending, setPending] = useState<PendingChange | null>(null);
  const [saving, setSaving] = useState(false);
  const [filling, setFilling] = useState<{ done: number; total: number } | null>(null);

  const loadCells = useCallback(
    async (next: MoveSource) => {
      const param =
        next.kind === 'entry' ? `entry=${next.entry.id}` : `assignment=${next.assignment}`;
      const data = await api<{ cells: GridCell[] }>(
        `/api/schedules/${schedule!.id}/options/?${param}`,
      );
      return data.cells;
    },
    [schedule],
  );

  const start = useCallback(
    async (next: MoveSource) => {
      if (!schedule) return;
      setSource(next);
      setCells(null);
      setLoadingCells(true);
      try {
        const list = await loadCells(next);
        setCells(new Map(list.map((c) => [cellKey(c), c])));
      } catch {
        toast(t('common:errors.unknown'), 'error');
        setSource(null);
      } finally {
        setLoadingCells(false);
      }
    },
    [loadCells, schedule, t, toast],
  );

  const cancel = useCallback(() => {
    setSource(null);
    setCells(null);
  }, []);

  const send = useCallback(
    async (change: { source: MoveSource; body: Record<string, unknown> }, comment = '') => {
      const { method, path } = endpoint(change.source);
      setSaving(true);
      try {
        await api(path, { method, body: { ...change.body, comment } });
        toast(t('admin:editor.saved'));
        await queryClient.invalidateQueries();
        return true;
      } catch (err) {
        const violations =
          (err instanceof ApiError && (err.data as { violations?: Violation[] })?.violations) || [];
        toast(violations[0]?.message ?? t('common:errors.unknown'), 'error');
        return false;
      } finally {
        setSaving(false);
      }
    },
    [queryClient, t, toast],
  );

  /**
   * Save a change. On the published timetable first ask the server who would be notified
   * and let the dispatcher confirm (with an optional comment); drafts save at once.
   */
  const change = useCallback(
    async (src: MoveSource, body: Record<string, unknown>, { quiet = false } = {}) => {
      if (!schedule) return;
      const needsLink = src.kind === 'assignment' && src.online;
      if ((schedule.status !== 'published' || quiet) && !needsLink) {
        await send({ source: src, body });
        return;
      }
      const { method, path } = endpoint(src);
      let students = 0;
      let teachers = 0;
      if (schedule.status === 'published' && !needsLink) {
        try {
          const preview = await api<{ notify_students: number; notify_teachers: number }>(path, {
            method,
            body: { ...body, dry_run: true },
          });
          students = preview.notify_students;
          teachers = preview.notify_teachers;
        } catch (err) {
          const v =
            (err instanceof ApiError && (err.data as { violations?: Violation[] })?.violations) ||
            [];
          toast(v[0]?.message ?? t('common:errors.unknown'), 'error');
          return;
        }
      }
      setPending({ source: src, body, students, teachers, needsLink });
    },
    [schedule, send, t, toast],
  );

  /** Drop the moving lesson into a cell. */
  const drop = useCallback(
    async (cell: GridCell) => {
      if (!schedule || !source || !cell.ok) return;
      const body = bodyFor(source, cell, schedule.id);
      cancel();
      await change(source, body);
    },
    [cancel, change, schedule, source],
  );

  /** Put one lesson into the best free cell (least busy day, earliest lesson). */
  const autoPlace = useCallback(
    async (src: MoveSource, shown: Shown[], subject?: string) => {
      if (!schedule) return;
      cancel();
      setLoadingCells(true);
      let cell: GridCell | undefined;
      try {
        cell = pickBestCell(await loadCells(src), shown, subject);
      } catch {
        toast(t('common:errors.unknown'), 'error');
        return;
      } finally {
        setLoadingCells(false);
      }
      if (!cell) {
        toast(t('admin:editor.noFreeCell'), 'error');
        return;
      }
      await change(src, bodyFor(src, cell, schedule.id));
    },
    [cancel, change, loadCells, schedule, t, toast],
  );

  /**
   * Place every missing lesson of the list, one by one, each in its best free cell.
   * Only on drafts: nobody is notified and nothing needs a confirmation.
   */
  const autoFill = useCallback(
    async (items: UnplacedItem[], shown: Shown[]) => {
      if (!schedule || schedule.status !== 'draft') return;
      cancel();
      const jobs = items.flatMap((item) =>
        Array.from({ length: Math.max(0, item.required - item.placed) }, () => item),
      );
      const placed: Shown[] = [...shown];
      let done = 0;
      let failed = 0;
      setFilling({ done, total: jobs.length });
      for (const item of jobs) {
        const src: MoveSource = {
          kind: 'assignment',
          assignment: item.assignment,
          label: item.subject,
          online: false,
        };
        try {
          const cell = pickBestCell(await loadCells(src), placed, item.subject);
          if (!cell) throw new Error('no cell');
          await api('/api/entries/', { method: 'POST', body: bodyFor(src, cell, schedule.id) });
          placed.push({
            date: cell.date ?? null,
            weekday: cell.weekday ?? null,
            subject: { id: 0, name: item.subject },
          });
        } catch {
          failed += 1;
        }
        done += 1;
        setFilling({ done, total: jobs.length });
      }
      setFilling(null);
      await queryClient.invalidateQueries();
      if (failed)
        toast(t('admin:editor.autoFillPartial', { placed: done - failed, failed }), 'error');
      else toast(t('admin:editor.autoFillDone', { count: done }));
    },
    [cancel, loadCells, queryClient, schedule, t, toast],
  );

  const confirm = useCallback(
    async (comment: string, link?: string) => {
      if (!pending) return;
      const body = link ? { ...pending.body, online_url: link } : pending.body;
      if (await send({ source: pending.source, body }, comment)) setPending(null);
    },
    [pending, send],
  );

  /** Edits from the lesson details panel (room change; pin is "quiet": nobody is notified). */
  const patchEntry = useCallback(
    (entry: TimetableEntry, body: Record<string, unknown>, options?: { quiet?: boolean }) =>
      change({ kind: 'entry', entry }, body, options),
    [change],
  );

  return {
    source,
    cells,
    loadingCells,
    pending,
    saving,
    filling,
    start,
    autoPlace,
    autoFill,
    cancel,
    drop,
    confirm,
    dismissPending: () => setPending(null),
    patchEntry,
  };
}
