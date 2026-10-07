import { useDraggable } from '@dnd-kit/core';
import { CheckCircle2, GripVertical, MousePointerClick } from 'lucide-react';
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
}

/** Side panel: lessons of the plan that are not in the grid yet. */
export function UnplacedPanel({ items, loading, editable, online, onPlace }: Props) {
  const { t } = useTranslation(['admin']);
  return (
    <Card className="flex max-h-[calc(100dvh-180px)] flex-col">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-bold text-ink">{t('admin:editor.unplaced')}</h2>
        <p className="text-xs text-ink-muted">
          {editable ? t('admin:editor.unplacedHint') : t('admin:editor.unplacedReadOnly')}
        </p>
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
}: {
  item: UnplacedItem;
  editable: boolean;
  online: boolean;
  onPlace: (source: MoveSource) => void;
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
        <button
          type="button"
          onClick={() => onPlace(source)}
          className="mt-2 inline-flex min-h-[36px] items-center gap-1.5 rounded-button px-2 text-xs font-bold text-link hover:bg-subtle"
        >
          <MousePointerClick size={15} aria-hidden="true" />
          {t('admin:editor.choosePlace')}
        </button>
      )}
    </div>
  );
}
