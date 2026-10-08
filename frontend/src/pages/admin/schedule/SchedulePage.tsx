import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core';
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  CopyPlus,
  FileSpreadsheet,
  FileText,
  History,
  Loader2,
  Send,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import { useAuth } from '@/auth/useAuth';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Pill } from '@/components/ui/Pill';
import { Segmented } from '@/components/ui/Segmented';
import { Select } from '@/components/ui/Select';
import { ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { download } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useAll, useApi } from '@/lib/query';
import type {
  BlockedPeriod,
  EducationForm,
  ScheduleVersion,
  TimetableEntry,
  UnplacedItem,
  Violation,
} from '@/types/timetable';

import { ConfirmChange } from './ConfirmChange';
import { parseDate, sessionDays, weeklyDays } from './grid';
import type { TeachingPeriod } from './grid';
import { HistoryDrawer } from './HistoryDrawer';
import { LessonCardPreview } from './LessonCard';
import type { GridView } from './LessonCard';
import { LessonDrawer } from './LessonDrawer';
import { NewDraftDialog, PublishDialog } from './VersionDialogs';
import { TimetableGrid } from './TimetableGrid';
import { UnplacedPanel } from './UnplacedPanel';
import { useEditor } from './useEditor';
import type { MoveSource } from './useEditor';

type Named = { id: number; name?: string; short_name?: string; label?: string };

const TARGETS: Record<GridView, { path: string; label: (r: Named) => string }> = {
  group: { path: '/api/groups/', label: (r) => r.name ?? String(r.id) },
  teacher: { path: '/api/teachers/', label: (r) => r.short_name ?? String(r.id) },
  room: { path: '/api/rooms/', label: (r) => r.name ?? String(r.id) },
};

const STATUS_PILL: Record<ScheduleVersion['status'], string> = {
  published: 'bg-lesson-lecture-bg text-lesson-lecture',
  draft: 'bg-warning-bg text-warning-fg',
  archived: 'bg-subtle text-ink-muted',
};

/** The dispatcher's timetable editor (read-only for the dean's office and heads of department). */
export function SchedulePage() {
  const { t } = useTranslation(['admin', 'common', 'dates']);
  const { user } = useAuth();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const set = (patch: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(patch)) {
          if (v) next.set(k, v);
          else next.delete(k);
        }
        return next;
      },
      { replace: true },
    );

  // ----- what is shown: version, education form, group/teacher/room
  const schedules = useAll<ScheduleVersion>('/api/schedules/');
  const forms = useAll<EducationForm>('/api/education-forms/');
  const schedule =
    schedules.rows.find((s) => String(s.id) === params.get('v')) ??
    schedules.rows.find((s) => s.status === 'published') ??
    schedules.rows[0];
  const form = forms.rows.find((f) => String(f.id) === params.get('form')) ?? forms.rows[0];
  const view = (
    ['group', 'teacher', 'room'].includes(params.get('view') ?? '') ? params.get('view') : 'group'
  ) as GridView;

  const targets = useAll<Named>(
    form ? TARGETS[view].path : null,
    view === 'group'
      ? { program_form__form: form?.id }
      : view === 'room'
        ? { is_active: true }
        : {},
  );
  const target = targets.rows.find((r) => String(r.id) === params.get('target')) ?? targets.rows[0];
  const targetIndex = target ? targets.rows.indexOf(target) : -1;

  const periods = useAll<TeachingPeriod>(
    schedule && form?.schedule_mode === 'session' ? '/api/teaching-periods/' : null,
    { semester: schedule?.semester, form: form?.id },
  );
  const period = periods.rows.find((p) => String(p.id) === params.get('period')) ?? periods.rows[0];

  const timetable = useApi<{ entries: TimetableEntry[] }>(
    schedule && target ? '/api/timetable/' : null,
    { schedule: schedule?.id, [view]: target?.id },
  );
  const blocked = useAll<BlockedPeriod>('/api/blocked-periods/');
  const conflicts = useApi<{ count: number; items: Violation[] }>(
    schedule ? `/api/schedules/${schedule.id}/conflicts/` : null,
  );
  const unplaced = useApi<UnplacedItem[]>(
    schedule ? `/api/schedules/${schedule.id}/unplaced/` : null,
    {
      form: form?.code,
      group: view === 'group' ? target?.id : undefined,
      teacher: view === 'teacher' ? target?.id : undefined,
    },
  );

  const entries = useMemo(
    () => (timetable.data?.entries ?? []).filter((e) => e.form === form?.code),
    [timetable.data, form?.code],
  );
  const conflictIds = useMemo(
    () => new Set((conflicts.data?.items ?? []).flatMap((c) => c.entries ?? [])),
    [conflicts.data],
  );
  const days = useMemo(() => {
    if (!form) return [];
    if (form.schedule_mode === 'weekly') return weeklyDays(form);
    return period ? sessionDays(form, period) : [];
  }, [form, period]);

  // ----- editing
  const editable = user?.role === 'admin' && schedule?.status !== 'archived';
  const editor = useEditor(schedule);
  const [dragging, setDragging] = useState<MoveSource | null>(null);
  const [openEntry, setOpenEntry] = useState<TimetableEntry | null>(null);
  const [dialog, setDialog] = useState<'history' | 'draft' | 'publish' | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));
  const moving = Boolean(editor.source);

  // Esc leaves the "choose a cell" mode.
  const { cancel } = editor;
  useEffect(() => {
    if (!moving || dragging) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && cancel();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [moving, dragging, cancel]);

  // Keep the open details panel in sync after edits (pin, room change).
  const shownEntry = openEntry && (entries.find((e) => e.id === openEntry.id) ?? openEntry);

  function onDragStart(event: DragStartEvent) {
    const source = event.active.data.current?.source as MoveSource | undefined;
    if (!source) return;
    setDragging(source);
    void editor.start(source);
  }

  function onDragEnd(event: DragEndEvent) {
    setDragging(null);
    const cell = event.over ? editor.cells?.get(String(event.over.id)) : undefined;
    if (cell?.ok) {
      void editor.drop(cell);
      return;
    }
    if (cell) toast(cell.reasons[0] ?? t('admin:editor.notAvailable'), 'error');
    editor.cancel();
  }

  const dayLabelOf = (e: TimetableEntry) => {
    const weekdays = t('dates:weekdays', { returnObjects: true }) as string[];
    if (!e.date) return weekdays[e.weekday ?? 0];
    const d = parseDate(e.date);
    return `${e.date.split('-').reverse().join('.')}, ${weekdays[(d.getDay() + 6) % 7]}`;
  };

  const exportFile = (type: 'xlsx' | 'pdf') => {
    if (!schedule || !target) return;
    const name = TARGETS[view].label(target).replace(/[^\p{L}\p{N}_-]+/gu, '_');
    download(
      `/api/export/?type=${type}&schedule=${schedule.id}&${view}=${target.id}`,
      `${name}.${type}`,
    ).catch(() => toast(t('common:errors.unknown'), 'error'));
  };

  if (schedules.isError || forms.isError) {
    return <ErrorState onRetry={() => (schedules.refetch(), forms.refetch())} />;
  }
  if (schedules.isLoading || forms.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-[480px] w-full" />
      </div>
    );
  }
  if (!schedule || !form) {
    return (
      <p className="rounded-card bg-subtle p-6 text-ink-muted">{t('admin:editor.noSchedule')}</p>
    );
  }

  const movingLabel =
    editor.source?.kind === 'entry'
      ? `${editor.source.entry.subject.name} · ${editor.source.entry.lesson_type.name}`
      : (editor.source?.label ?? '');

  return (
    <DndContext
      sensors={sensors}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragCancel={() => (setDragging(null), editor.cancel())}
    >
      <div className="space-y-4">
        {/* ----- title + version actions */}
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl font-extrabold text-ink">{t('admin:editor.title')}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Select
                label={t('admin:editor.version')}
                hideLabel
                className="min-w-[240px]"
                value={schedule.id}
                onChange={(e) => set({ v: e.target.value })}
                options={schedules.rows.map((s) => ({
                  value: s.id,
                  label: `${s.name} — ${t(`admin:status.${s.status}`)}`,
                }))}
              />
              <Pill className={STATUS_PILL[schedule.status]}>
                {t(`admin:status.${schedule.status}`)}
              </Pill>
              {conflicts.data && conflicts.data.count > 0 && (
                <Pill className="bg-danger-bg text-danger-fg">
                  <AlertTriangle size={12} aria-hidden="true" />
                  {t('admin:editor.conflictCount', { count: conflicts.data.count })}
                </Pill>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              icon={<History size={18} aria-hidden="true" />}
              onClick={() => setDialog('history')}
            >
              {t('admin:history.title')}
            </Button>
            <Button
              variant="secondary"
              icon={<FileSpreadsheet size={18} aria-hidden="true" />}
              onClick={() => exportFile('xlsx')}
              disabled={!target}
            >
              {t('admin:editor.exportXlsx')}
            </Button>
            <Button
              variant="secondary"
              icon={<FileText size={18} aria-hidden="true" />}
              onClick={() => exportFile('pdf')}
              disabled={!target}
            >
              {t('admin:editor.exportPdf')}
            </Button>
            {user?.role === 'admin' && (
              <Button
                variant="secondary"
                icon={<CopyPlus size={18} aria-hidden="true" />}
                onClick={() => setDialog('draft')}
              >
                {t('admin:versions.newDraft')}
              </Button>
            )}
            {user?.role === 'admin' && schedule.status === 'draft' && (
              <Button
                icon={<Send size={18} aria-hidden="true" />}
                onClick={() => setDialog('publish')}
              >
                {t('admin:versions.publish')}
              </Button>
            )}
          </div>
        </div>

        {/* ----- what to show */}
        <Card className="flex flex-wrap items-center gap-3 p-3">
          <Segmented
            label={t('admin:editor.form')}
            value={String(form.id)}
            onChange={(v) => set({ form: v, target: null, period: null })}
            options={forms.rows.map((f) => ({ value: String(f.id), label: f.name }))}
          />
          <Segmented
            label={t('admin:editor.viewBy')}
            value={view}
            onChange={(v) => set({ view: v, target: null })}
            options={(['group', 'teacher', 'room'] as const).map((v) => ({
              value: v,
              label: t(`admin:editor.views.${v}`),
            }))}
          />
          <div className="flex items-center gap-1">
            <StepButton
              label={t('admin:editor.prevTarget')}
              icon={ChevronLeft}
              disabled={targetIndex <= 0}
              onClick={() => set({ target: String(targets.rows[targetIndex - 1].id) })}
            />
            <Select
              label={t(`admin:editor.views.${view}`)}
              hideLabel
              className="min-w-[200px]"
              value={target?.id ?? ''}
              disabled={targets.isLoading}
              onChange={(e) => set({ target: e.target.value })}
              options={targets.rows.map((r) => ({ value: r.id, label: TARGETS[view].label(r) }))}
            />
            <StepButton
              label={t('admin:editor.nextTarget')}
              icon={ChevronRight}
              disabled={targetIndex < 0 || targetIndex >= targets.rows.length - 1}
              onClick={() => set({ target: String(targets.rows[targetIndex + 1].id) })}
            />
          </div>
          {form.schedule_mode === 'session' && periods.rows.length > 1 && (
            <Select
              label={t('admin:editor.period')}
              hideLabel
              className="min-w-[200px]"
              value={period?.id ?? ''}
              onChange={(e) => set({ period: e.target.value })}
              options={periods.rows.map((p) => ({ value: p.id, label: p.label }))}
            />
          )}
        </Card>

        {editable && <Steps />}

        {/* ----- "choose a cell" banner (keyboard / click path, also shown while dragging) */}
        {(moving || editor.loadingCells) && (
          <div
            role="status"
            className="flex flex-wrap items-center gap-3 rounded-card bg-feature px-4 py-3 text-sm text-ink-on-primary shadow-soft"
          >
            {editor.loadingCells && (
              <Loader2 size={18} aria-hidden="true" className="animate-spin" />
            )}
            <span className="font-semibold">
              {editor.loadingCells
                ? t('admin:editor.checking')
                : t('admin:editor.chooseCell', { name: movingLabel })}
            </span>
            {moving && !dragging && (
              <button
                type="button"
                onClick={editor.cancel}
                className="ml-auto inline-flex min-h-[36px] items-center gap-1 rounded-button px-3 font-bold text-mint hover:bg-white/10"
              >
                <X size={16} aria-hidden="true" />
                {t('admin:editor.cancelMove')}
              </button>
            )}
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-[1fr_300px]">
          <div className="min-w-0">
            {timetable.isError ? (
              <ErrorState onRetry={() => timetable.refetch()} />
            ) : timetable.isLoading || targets.isLoading ? (
              <Skeleton className="h-[480px] w-full" />
            ) : !target ? (
              <p className="rounded-card bg-subtle p-6 text-sm text-ink-muted">
                {t('admin:editor.noTargets')}
              </p>
            ) : (
              <TimetableGrid
                form={form}
                days={days}
                entries={entries}
                blocked={blocked.rows}
                view={view}
                editable={editable}
                conflictIds={conflictIds}
                moving={moving}
                cells={editor.cells}
                onOpen={setOpenEntry}
                onPick={(cell) => void editor.drop(cell)}
              />
            )}
            <Legend />
          </div>
          <UnplacedPanel
            items={view === 'room' ? [] : (unplaced.data ?? [])}
            loading={unplaced.isLoading}
            editable={editable}
            online={!form.requires_room}
            onPlace={(source) => void editor.start(source)}
            onAuto={(source, item) => void editor.autoPlace(source, entries, item.subject)}
            fillBlocked={
              schedule.status !== 'draft'
                ? t('admin:editor.autoFillDraftOnly')
                : !form.requires_room
                  ? t('admin:editor.autoFillOnline')
                  : null
            }
            filling={editor.filling}
            onAutoFill={() => void editor.autoFill(unplaced.data ?? [], entries)}
          />
        </div>
      </div>

      <DragOverlay dropAnimation={null}>
        {dragging && (
          <LessonCardPreview
            title={dragging.kind === 'entry' ? dragging.entry.subject.name : dragging.label}
            subtitle={
              dragging.kind === 'entry'
                ? `${dragging.entry.lesson_type.name} · ${dragging.entry.teacher.short_name}`
                : t('admin:editor.newLesson')
            }
          />
        )}
      </DragOverlay>

      {shownEntry && (
        <LessonDrawer
          key={shownEntry.id}
          entry={shownEntry}
          schedule={schedule}
          editable={editable}
          dayLabel={dayLabelOf(shownEntry)}
          onMove={() => {
            setOpenEntry(null);
            void editor.start({ kind: 'entry', entry: shownEntry });
          }}
          onPatch={(body, options) => editor.patchEntry(shownEntry, body, options)}
          onClose={() => setOpenEntry(null)}
        />
      )}
      {editor.pending && (
        <ConfirmChange
          pending={editor.pending}
          saving={editor.saving}
          onConfirm={(comment, link) => void editor.confirm(comment, link)}
          onClose={editor.dismissPending}
        />
      )}
      {dialog === 'history' && (
        <HistoryDrawer schedule={schedule} editable={editable} onClose={() => setDialog(null)} />
      )}
      {dialog === 'draft' && (
        <NewDraftDialog
          schedule={schedule}
          onCreated={(id) => set({ v: String(id) })}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog === 'publish' && (
        <PublishDialog schedule={schedule} onClose={() => setDialog(null)} />
      )}
    </DndContext>
  );
}

function StepButton({
  label,
  icon: Icon,
  disabled,
  onClick,
}: {
  label: string;
  icon: typeof ChevronLeft;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="flex min-h-touch min-w-touch items-center justify-center rounded-full text-primary-700 hover:bg-primary-700/10 disabled:opacity-30"
    >
      <Icon size={20} aria-hidden="true" />
    </button>
  );
}

/** Three-step reminder of how a timetable is made. */
function Steps() {
  const { t } = useTranslation(['admin']);
  const steps = [
    t('admin:editor.steps.pick'),
    t('admin:editor.steps.place'),
    t('admin:editor.steps.publish'),
  ];
  return (
    <ol className="grid gap-2 sm:grid-cols-3">
      {steps.map((text, i) => (
        <li
          key={text}
          className="flex items-center gap-3 rounded-card bg-card px-4 py-3 text-sm shadow-soft"
        >
          <span
            aria-hidden="true"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-700 text-sm font-extrabold text-ink-on-primary"
          >
            {i + 1}
          </span>
          <span className="font-semibold text-ink">{text}</span>
        </li>
      ))}
    </ol>
  );
}

function Legend() {
  const { t } = useTranslation(['admin']);
  const items = [
    { cls: 'bg-lesson-lecture-bg', label: t('admin:legend.free') },
    { cls: 'bg-danger-bg', label: t('admin:legend.busy') },
    {
      cls: 'border border-line bg-[repeating-linear-gradient(135deg,transparent,transparent_3px,rgb(var(--line))_3px,rgb(var(--line))_4px)]',
      label: t('admin:legend.blocked'),
    },
    { cls: 'ring-2 ring-danger-fg', label: t('admin:legend.conflict') },
  ];
  return (
    <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-muted">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-2">
          <span aria-hidden="true" className={cn('h-3.5 w-3.5 rounded', i.cls)} />
          {i.label}
        </li>
      ))}
    </ul>
  );
}
