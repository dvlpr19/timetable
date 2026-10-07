import { Download, FileSpreadsheet } from 'lucide-react';
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { useToast } from '@/components/ui/Toast';
import { ApiError, api, download } from '@/lib/api';

import type { Resource } from './resources';

interface RowError {
  row: number;
  column: string;
  message: string;
}

export function ImportDialog({ resource, onClose }: { resource: Resource; onClose: () => void }) {
  const { t } = useTranslation(['data', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<RowError[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function upload() {
    if (!file) return;
    setBusy(true);
    setErrors([]);
    setMessage(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const result = await api<{ created: number; updated: number }>(`${resource.path}import/`, {
        method: 'POST',
        body: form,
      });
      await queryClient.invalidateQueries();
      toast(t('data:import.done', result));
      onClose();
    } catch (err) {
      const data = err instanceof ApiError ? (err.data as { errors?: RowError[] } | null) : null;
      if (data?.errors) setErrors(data.errors);
      else
        setMessage(err instanceof ApiError && err.detail ? err.detail : t('common:errors.unknown'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      title={t('data:import.title', { name: t(`data:resources.${resource.key}.title`) })}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('data:actions.cancel')}
          </Button>
          <Button onClick={upload} disabled={!file || busy}>
            {busy ? t('data:import.uploading') : t('data:import.upload')}
          </Button>
        </>
      }
    >
      <ol className="list-decimal space-y-4 pl-5 text-sm text-ink">
        <li>
          <p>{t('data:import.step1')}</p>
          <Button
            variant="secondary"
            className="mt-2"
            icon={<Download size={18} aria-hidden="true" />}
            onClick={() => download(`${resource.path}import-template/`, `${resource.key}.xlsx`)}
          >
            {t('data:import.template')}
          </Button>
        </li>
        <li>
          <p>{t('data:import.step2')}</p>
        </li>
        <li>
          <p>{t('data:import.step3')}</p>
          <label className="mt-2 flex min-h-touch cursor-pointer items-center gap-3 rounded-button border border-dashed border-line bg-subtle px-4 py-3 font-semibold">
            <FileSpreadsheet size={20} aria-hidden="true" className="text-primary-700" />
            <span className="truncate">{file ? file.name : t('data:import.choose')}</span>
            <input
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="sr-only"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </li>
      </ol>
      <p className="mt-4 text-xs text-ink-muted">{t('data:import.allOrNothing')}</p>
      {message && (
        <p
          role="alert"
          className="mt-4 rounded-button bg-danger-bg px-4 py-3 text-sm text-danger-fg"
        >
          {message}
        </p>
      )}
      {errors.length > 0 && (
        <div role="alert" className="mt-4 rounded-button bg-danger-bg p-4 text-sm text-danger-fg">
          <p className="font-bold">{t('data:import.failed', { count: errors.length })}</p>
          <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
            {errors.map((e, i) => (
              <li key={i}>{t('data:import.rowError', { row: e.row, message: e.message })}</li>
            ))}
          </ul>
        </div>
      )}
    </Modal>
  );
}
