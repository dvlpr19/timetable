import { Bell } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { TextField } from '@/components/ui/TextField';

import type { PendingChange } from './useEditor';

interface Props {
  pending: PendingChange;
  saving: boolean;
  onConfirm: (comment: string, link?: string) => void;
  onClose: () => void;
}

/**
 * Confirmation before changing the published timetable: how many students and teachers
 * will get a notification, plus an optional comment for them. Distance lessons ask for a link.
 */
export function ConfirmChange({ pending, saving, onConfirm, onClose }: Props) {
  const { t } = useTranslation(['admin', 'data']);
  const [comment, setComment] = useState('');
  const [link, setLink] = useState('');
  const notifies = pending.students + pending.teachers > 0;
  const linkValid = !pending.needsLink || /^https?:\/\/\S+$/.test(link.trim());

  return (
    <Modal
      open
      size="sm"
      title={pending.needsLink ? t('admin:confirm.linkTitle') : t('admin:confirm.title')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('data:actions.cancel')}
          </Button>
          <Button
            disabled={saving || !linkValid}
            onClick={() => onConfirm(comment.trim(), pending.needsLink ? link.trim() : undefined)}
          >
            {saving ? t('data:actions.saving') : t('admin:confirm.save')}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {pending.needsLink && (
          <TextField
            label={t('admin:confirm.link')}
            type="url"
            inputMode="url"
            placeholder="https://"
            value={link}
            onChange={(e) => setLink(e.target.value)}
            data-autofocus
          />
        )}
        {notifies && (
          <p className="flex gap-3 rounded-button bg-warning-bg p-3 text-sm text-warning-fg">
            <Bell size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
            <span>
              {t('admin:confirm.notify', {
                students: pending.students,
                teachers: pending.teachers,
              })}
            </span>
          </p>
        )}
        {!notifies && !pending.needsLink && (
          <p className="text-sm text-ink">{t('admin:confirm.nobody')}</p>
        )}
        {notifies && (
          <div>
            <label htmlFor="change-comment" className="mb-2 block text-sm font-semibold text-ink">
              {t('admin:confirm.comment')}
            </label>
            <textarea
              id="change-comment"
              rows={3}
              maxLength={500}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t('admin:confirm.commentPlaceholder')}
              className="w-full rounded-button border border-line bg-card px-4 py-3 text-base text-ink placeholder:text-ink-muted"
            />
          </div>
        )}
      </div>
    </Modal>
  );
}
