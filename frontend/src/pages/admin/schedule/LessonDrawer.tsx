import { useQueryClient } from '@tanstack/react-query';
import { Move, Pin, PinOff, Trash2 } from 'lucide-react';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Pill } from '@/components/ui/Pill';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { lessonTypeClasses } from '@/lib/lessonTypes';
import { needsLink } from '@/lib/links';
import { useAll, useApi } from '@/lib/query';
import type { GridCell, ScheduleVersion, TimetableEntry } from '@/types/timetable';

import { cellKey } from './useEditor';

interface Props {
  entry: TimetableEntry;
  schedule: ScheduleVersion;
  editable: boolean;
  dayLabel: string;
  onMove: () => void;
  onPatch: (body: Record<string, unknown>, options?: { quiet?: boolean }) => Promise<void>;
  onClose: () => void;
}

/** Lesson details: who, where, when; the dispatcher can move, pin, change the room or remove it. */
export function LessonDrawer({
  entry,
  schedule,
  editable,
  dayLabel,
  onMove,
  onPatch,
  onClose,
}: Props) {
  const { t } = useTranslation(['admin', 'data', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const online = !entry.room && Boolean(entry.online_url);
  const [link, setLink] = useState(needsLink(entry.online_url) ? '' : entry.online_url);

  // Free rooms at the lesson's current time (same endpoint as drag-and-drop).
  const options = useApi<{ cells: GridCell[] }>(
    editable && !online ? `/api/schedules/${schedule.id}/options/` : null,
    { entry: entry.id },
  );
  const rooms = useAll<{ id: number; name: string; capacity: number; building_name: string }>(
    editable && !online ? '/api/rooms/' : null,
  );
  const here = options.data?.cells.find(
    (c) =>
      cellKey(c) ===
      cellKey({ weekday: entry.weekday, date: entry.date, lesson_time: entry.lesson_time.id }),
  );
  const roomName = new Map(
    rooms.rows.map((r) => [r.id, `${r.name} · ${r.building_name} (${r.capacity})`]),
  );
  const freeRooms = [
    ...new Set([...(entry.room ? [entry.room.id] : []), ...(here?.free_rooms ?? [])]),
  ];

  async function remove() {
    setBusy(true);
    try {
      await api(`/api/entries/${entry.id}/`, { method: 'DELETE' });
      await queryClient.invalidateQueries();
      toast(t('admin:lesson.removed'));
      onClose();
    } catch {
      toast(t('common:errors.unknown'), 'error');
    } finally {
      setBusy(false);
      setConfirmDelete(false);
    }
  }

  async function patch(body: Record<string, unknown>, quiet = false) {
    setBusy(true);
    try {
      await onPatch(body, { quiet });
    } finally {
      setBusy(false);
    }
  }

  const colors = lessonTypeClasses(entry.lesson_type.code);
  return (
    <>
      <Modal
        open
        variant="drawer"
        title={entry.subject.name}
        onClose={onClose}
        footer={
          editable ? (
            <>
              <Button
                variant="ghost"
                className="mr-auto text-danger-fg"
                icon={<Trash2 size={18} aria-hidden="true" />}
                onClick={() => setConfirmDelete(true)}
              >
                {t('admin:lesson.remove')}
              </Button>
              <Button
                variant="secondary"
                disabled={busy}
                icon={
                  entry.is_locked ? (
                    <PinOff size={18} aria-hidden="true" />
                  ) : (
                    <Pin size={18} aria-hidden="true" />
                  )
                }
                onClick={() => patch({ is_locked: !entry.is_locked }, true)}
              >
                {entry.is_locked ? t('admin:lesson.unpin') : t('admin:lesson.pin')}
              </Button>
              <Button
                disabled={entry.is_locked}
                icon={<Move size={18} aria-hidden="true" />}
                onClick={onMove}
              >
                {t('admin:lesson.move')}
              </Button>
            </>
          ) : (
            <Button variant="secondary" onClick={onClose}>
              {t('common:actions.close')}
            </Button>
          )
        }
      >
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            <Pill className={colors.pill}>{entry.lesson_type.name}</Pill>
            {entry.week_parity && entry.week_parity !== 'every' && (
              <Pill className="bg-subtle text-ink">
                {t(`admin:editor.parityLong.${entry.week_parity}`)}
              </Pill>
            )}
            {entry.is_locked && (
              <Pill className="bg-gold/20 text-ink">
                <Pin size={12} aria-hidden="true" />
                {t('admin:lesson.pinned')}
              </Pill>
            )}
          </div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm">
            <Row label={t('admin:lesson.when')}>
              {dayLabel}, {t('admin:editor.lessonNumber', { n: entry.lesson_time.number })} ·{' '}
              {entry.lesson_time.start}–{entry.lesson_time.end}
            </Row>
            <Row label={t('admin:lesson.teacher')}>{entry.teacher.full_name}</Row>
            <Row label={t('admin:lesson.groups')}>
              {entry.stream ? `${entry.stream}: ` : ''}
              {entry.groups.map((g) => g.name).join(', ')}
              {entry.subgroup ? ` · ${t('admin:editor.subgroup', { n: entry.subgroup })}` : ''}
            </Row>
            <Row label={t('admin:lesson.students')}>{entry.student_count}</Row>
            <Row label={t('admin:lesson.room')}>
              {entry.room ? (
                `${entry.room.name} · ${entry.room.building}, ${t('admin:lesson.floor', { n: entry.room.floor })} (${entry.room.capacity})`
              ) : needsLink(entry.online_url) ? (
                <span className="font-semibold text-warning-fg">
                  {t('admin:lesson.linkNeeded')}
                </span>
              ) : entry.online_url ? (
                <a
                  href={entry.online_url}
                  target="_blank"
                  rel="noreferrer"
                  className="break-all font-semibold text-link hover:underline"
                >
                  {entry.online_url}
                </a>
              ) : (
                '—'
              )}
            </Row>
            {entry.note && <Row label={t('admin:lesson.note')}>{entry.note}</Row>}
          </dl>
          {entry.is_locked && editable && (
            <p className="rounded-button bg-subtle p-3 text-xs text-ink-muted">
              {t('admin:lesson.pinnedHint')}
            </p>
          )}
          {editable && online && (
            <form
              className="flex items-end gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (/^https?:\/\/\S+$/.test(link.trim())) void patch({ online_url: link.trim() });
              }}
            >
              <TextField
                className="flex-1"
                label={t('admin:lesson.link')}
                type="url"
                inputMode="url"
                placeholder="https://"
                value={link}
                onChange={(e) => setLink(e.target.value)}
              />
              <Button
                type="submit"
                variant="secondary"
                disabled={busy || !/^https?:\/\/\S+$/.test(link.trim())}
              >
                {t('data:actions.save')}
              </Button>
            </form>
          )}
          {editable && !online && (
            <Select
              label={t('admin:lesson.changeRoom')}
              value={entry.room?.id ?? ''}
              disabled={busy || options.isLoading}
              onChange={(e) => e.target.value && patch({ room: Number(e.target.value) })}
              placeholder={options.isLoading ? t('data:loadingOptions') : undefined}
              options={freeRooms.map((id) => ({
                value: id,
                label: roomName.get(id) ?? String(id),
              }))}
            />
          )}
        </div>
      </Modal>
      <Modal
        open={confirmDelete}
        size="sm"
        title={t('admin:lesson.removeTitle')}
        onClose={() => setConfirmDelete(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)}>
              {t('data:actions.cancel')}
            </Button>
            <Button className="bg-danger-fg hover:bg-danger-fg/90" disabled={busy} onClick={remove}>
              {t('admin:lesson.remove')}
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink">
          {schedule.status === 'published'
            ? t('admin:lesson.removePublished')
            : t('admin:lesson.removeDraft')}
        </p>
      </Modal>
    </>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="font-semibold text-ink-muted">{label}</dt>
      <dd className="text-ink">{children}</dd>
    </>
  );
}
