import { useQueryClient } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { TextField } from '@/components/ui/TextField';
import { useToast } from '@/components/ui/Toast';
import { ApiError, api } from '@/lib/api';
import type { ScheduleVersion, Violation } from '@/types/timetable';

/** Copy a version into a new draft (changes there are invisible to students until published). */
export function NewDraftDialog({
  schedule,
  onCreated,
  onClose,
}: {
  schedule: ScheduleVersion;
  onCreated: (id: number) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation(['admin', 'data', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [name, setName] = useState(() => t('admin:versions.copyName', { name: schedule.name }));
  const [busy, setBusy] = useState(false);

  async function create() {
    setBusy(true);
    try {
      const draft = await api<ScheduleVersion>('/api/schedules/', {
        method: 'POST',
        body: { semester: schedule.semester, name: name.trim(), based_on: schedule.id },
      });
      await queryClient.invalidateQueries();
      toast(t('admin:versions.created'));
      onCreated(draft.id);
      onClose();
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
      size="sm"
      title={t('admin:versions.newDraft')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('data:actions.cancel')}
          </Button>
          <Button disabled={busy || !name.trim()} onClick={create}>
            {t('admin:versions.create')}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-ink-muted">
        {t('admin:versions.draftHint', { name: schedule.name })}
      </p>
      <TextField
        label={t('admin:versions.name')}
        value={name}
        maxLength={120}
        onChange={(e) => setName(e.target.value)}
      />
    </Modal>
  );
}

/** Publish a draft; the server refuses (409) while hard conflicts remain and lists them. */
export function PublishDialog({
  schedule,
  onClose,
}: {
  schedule: ScheduleVersion;
  onClose: () => void;
}) {
  const { t } = useTranslation(['admin', 'data', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [conflicts, setConflicts] = useState<Violation[]>([]);

  async function publish() {
    setBusy(true);
    try {
      await api(`/api/schedules/${schedule.id}/publish/`, { method: 'POST' });
      await queryClient.invalidateQueries();
      toast(t('admin:versions.published'));
      onClose();
    } catch (err) {
      const list =
        err instanceof ApiError
          ? (err.data as { conflicts?: Violation[] } | null)?.conflicts
          : null;
      if (list?.length) setConflicts(list);
      else
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
      size="md"
      title={t('admin:versions.publishTitle', { name: schedule.name })}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {conflicts.length ? t('common:actions.close') : t('data:actions.cancel')}
          </Button>
          {!conflicts.length && (
            <Button disabled={busy} onClick={publish}>
              {t('admin:versions.publish')}
            </Button>
          )}
        </>
      }
    >
      {conflicts.length ? (
        <div role="alert">
          <p className="mb-3 text-sm font-bold text-danger-fg">
            {t('admin:versions.hasConflicts', { count: conflicts.length })}
          </p>
          <ul className="max-h-72 space-y-2 overflow-y-auto">
            {conflicts.map((c, i) => (
              <li
                key={i}
                className="flex gap-2 rounded-button bg-danger-bg p-3 text-sm text-danger-fg"
              >
                <AlertTriangle size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
                {c.message}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-ink">{t('admin:versions.publishText')}</p>
      )}
    </Modal>
  );
}
