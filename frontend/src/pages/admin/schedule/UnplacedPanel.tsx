import { useDraggable } from '@dnd-kit/core';
import { CheckCircle2, GripVertical, Loader2, MousePointerClick, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Card } from '@/components/ui/Card';
import { Pill } from '@/components/ui/Pill';
import { LoadingRows } from '@/components/ui/States';
import { cn } from '@/lib/cn';
import { lessonTypeClasses } from '@/lib/lessonTypes';
import type { UnplacedItem } from '@/types/timetable';

import type { MoveSource } from './useEditor';

interface Props {
  items: UnplacedItem[];
  loading: boolean;
  editable: boolean;
  online: boolean;
  onPlace: (source: MoveSource) => void;
  onAuto: (source: MoveSource, item: UnplacedItem) => void;
  /** "place all" is offered on drafts of forms with rooms; otherwise the reason why not */
  fillBlocked: string | null;
  filling: { done: number; total: number } | null;
  onAutoFill: () => void;
}

/** Side panel: lessons of the plan that are not in the grid yet. */
export function UnplacedPanel({
  items,
  loading,
  editable,
  online,
  onPlace,
  onAuto,
  fillBlocked,
  filling,
  onAutoFill,
}: Props) {
  const { t } = useTranslation(['admin']);
  const missing = items.reduce((n, i) => n + Math.max(0, i.required - i.placed), 0);
  return (
    <Card className="flex max-h-[calc(100dvh-180px)] flex-col">
      <div className="border-b border-line px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-bold text-ink">{t('admin:editor.unplaced')}</h2>
          {missing > 0 && (
            <span className="rounded-full bg-primary-700 px-2.5 py-0.5 text-xs font-bold text-ink-on-primary">
              {missing}
            </span>
          )}
        </div>
        <p className="text-xs text-ink-muted">
          {editable ? t('admin:editor.unplacedHint') : t('admin:editor.unplacedReadOnly')}
        </p>
        {editable && missing > 0 && (
          <div className="mt-3">
            <button
              type="button"
              onClick={onAutoFill}
              disabled={Boolean(fillBlocked) || Boolean(filling)}
              className="inline-flex min-h-touch w-full items-center justify-center gap-2 rounded-full bg-gradient-to-r from-primary-700 to-primary-500 px-4 text-sm font-bold text-ink-on-primary shadow-soft transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {filling ? (
                <Loader2 size={18} aria-hidden="true" className="animate-spin" />
              ) : (
                <Sparkles size={18} aria-hidden="true" />
              )}
              {filling
                ? t('admin:editor.autoFilling', filling)
                : t('admin:editor.autoFill', { count: missing })}
            </button>
            {filling && (
              <div
                className="mt-2 h-1.5 overflow-hidden rounded-full bg-subtle"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={filling.total}
                aria-valuenow={filling.done}
              >
                <div
                  className="h-full rounded-full bg-primary-500 transition-all"
                  style={{ width: `${(filling.done / Math.max(1, filling.total)) * 100}%` }}
                />
              </div>
            )}
            {fillBlocked && <p className="mt-1.5 text-xs text-ink-muted">{fillBlocked}</p>}
          </div>
        )}
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {loading ? (
          <LoadingRows rows={3} />
        ) : items.length === 0 ? (
          <p className="flex items-center gap-2 rounded-button bg-lesson-lecture-bg p-3 text-sm font-semibold text-lesson-lecture">
            <CheckCircle2 size={18} aria-hidden="true" />
            {t('admin:editor.allPlaced')}
          </p>
        ) : (
          items.map((item) => (
            <UnplacedRow
              key={item.assignment}
              item={item}
              editable={editable}
              online={online}
              onPlace={onPlace}
              onAuto={onAuto}
            />
          ))
        )}
      </div>
    </Card>
  );
}

function UnplacedRow({
  item,
  editable,
  online,
  onPlace,
  onAuto,
}: {
  item: UnplacedItem;
  editable: boolean;
  online: boolean;
  onPlace: (source: MoveSource) => void;
  onAuto: (source: MoveSource, item: UnplacedItem) => void;
}) {
  const { t } = useTranslation(['admin']);
  const source: MoveSource = {
    kind: 'assignment',
    assignment: item.assignment,
    label: `${item.subject} · ${item.lesson_type.name}`,
    online,
  };
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `assignment-${item.assignment}`,
    data: { source },
    disabled: !editable,
  });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        'rounded-button border border-line bg-card p-3 text-sm',
        isDragging && 'opacity-40',
      )}
    >
      <div className="flex items-start gap-2">
        {editable && (
          <span
            {...attributes}
            {...listeners}
            aria-hidden="true"
            tabIndex={-1}
            className="mt-0.5 cursor-grab text-ink-muted active:cursor-grabbing"
          >
            <GripVertical size={18} />
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="font-bold text-ink">{item.subject}</p>
          <p className="truncate text-xs text-ink-muted">
            {item.target} · {item.teacher}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Pill className={lessonTypeClasses(item.lesson_type.code).pill}>
              {item.lesson_type.name}
            </Pill>
            <span className="text-xs font-semibold text-ink">
              {t('admin:editor.placedOf', { placed: item.placed, required: item.required })}
            </span>
          </div>
        </div>
      </div>
      {editable && (
        <div className="mt-2 flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => onAuto(source, item)}
            className="inline-flex min-h-[36px] items-center gap-1.5 rounded-full bg-primary-700/10 px-3 text-xs font-bold text-primary-700 hover:bg-primary-700/15"
          >
            <Sparkles size={15} aria-hidden="true" />
            {t('admin:editor.autoPlace')}
          </button>
          <button
            type="button"
            onClick={() => onPlace(source)}
            className="inline-flex min-h-[36px] items-center gap-1.5 rounded-full px-3 text-xs font-bold text-link hover:bg-subtle"
          >
            <MousePointerClick size={15} aria-hidden="true" />
            {t('admin:editor.choosePlace')}
          </button>
        </div>
      )}
    </div>
  );
}
