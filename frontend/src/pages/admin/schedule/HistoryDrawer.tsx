import { useQueryClient } from '@tanstack/react-query';
import { BellRing, Undo2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Pill } from '@/components/ui/Pill';
import { EmptyState, ErrorState, LoadingRows } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { ApiError, api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useApi } from '@/lib/query';
import type { ScheduleVersion } from '@/types/timetable';

interface Change {
  id: number;
  batch: string;
  reverts: number | null;
  action: string;
  action_display: string;
  comment: string;
  user_name: string;
  created_at: string;
  undone: boolean;
  notified: boolean;
  occurrence_date: string | null;
}

/** Change history of a version; the dispatcher can undo the last batch of changes. */
export function HistoryDrawer({
  schedule,
  editable,
  onClose,
}: {
  schedule: ScheduleVersion;
  editable: boolean;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation(['admin', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const changes = useApi<Change[]>(`/api/schedules/${schedule.id}/changes/`);
  const rows = changes.data ?? [];
  const canUndo = editable && rows.some((c) => !c.undone && !c.reverts);
  const format = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  async function undo() {
    setBusy(true);
    try {
      await api(`/api/schedules/${schedule.id}/undo/`, { method: 'POST' });
      await queryClient.invalidateQueries();
      toast(t('admin:history.undone'));
    } catch (err) {
      toast(
        err instanceof ApiError && err.detail ? err.detail : t('common:errors.unknown'),
        'error',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      variant="drawer"
      title={t('admin:history.title')}
      onClose={onClose}
      footer={
        editable && (
          <Button
            icon={<Undo2 size={18} aria-hidden="true" />}
            disabled={!canUndo || busy}
            onClick={undo}
          >
            {t('admin:history.undo')}
          </Button>
        )
      }
    >
      {changes.isLoading ? (
        <LoadingRows rows={6} />
      ) : changes.isError ? (
        <ErrorState onRetry={() => changes.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState title={t('admin:history.empty')} />
      ) : (
        <ol className="space-y-2">
          {rows.map((c) => (
            <li
              key={c.id}
              className={cn(
                'rounded-button border border-line p-3 text-sm',
                c.undone && 'opacity-60',
              )}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className={cn('font-bold text-ink', c.undone && 'line-through')}>
                  {c.action_display}
                </span>
                {c.occurrence_date && <span className="text-ink-muted">{c.occurrence_date}</span>}
                {c.undone && (
                  <Pill className="bg-subtle text-ink-muted">{t('admin:history.wasUndone')}</Pill>
                )}
                {c.notified && (
                  <span title={t('admin:history.notified')} className="text-ink-muted">
                    <BellRing size={14} aria-label={t('admin:history.notified')} />
                  </span>
                )}
              </div>
              {c.comment && <p className="mt-1 text-ink">“{c.comment}”</p>}
              <p className="mt-1 text-xs text-ink-muted">
                {[c.user_name, format.format(new Date(c.created_at))].filter(Boolean).join(' · ')}
              </p>
            </li>
          ))}
        </ol>
      )}
    </Modal>
  );
}
