import { KeyRound } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextField } from '@/components/ui/TextField';
import { useToast } from '@/components/ui/Toast';
import { api, ApiError } from '@/lib/api';

type Errors = Partial<Record<'current_password' | 'new_password' | 'confirm', string>>;

function firstMessage(value: unknown): string | undefined {
  if (Array.isArray(value)) return value.join(' ');
  return typeof value === 'string' ? value : undefined;
}

/** Every account can change its own password; the current one is required. */
export function ChangePasswordCard() {
  const { t } = useTranslation(['common']);
  const toast = useToast();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [saving, setSaving] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (next !== confirm) {
      setErrors({ confirm: t('common:profile.mismatch') });
      return;
    }
    setErrors({});
    setSaving(true);
    try {
      await api('/api/auth/password/', {
        method: 'POST',
        body: { current_password: current, new_password: next },
      });
      setCurrent('');
      setNext('');
      setConfirm('');
      toast(t('common:profile.passwordChanged'));
    } catch (err) {
      const data = err instanceof ApiError ? (err.data as Record<string, unknown> | null) : null;
      if (data && (data.current_password || data.new_password)) {
        setErrors({
          current_password: firstMessage(data.current_password),
          new_password: firstMessage(data.new_password),
        });
      } else {
        toast(t('common:errors.unknown'), 'error');
      }
    } finally {
      setSaving(false);
    }
  }

  const error = (key: keyof Errors) =>
    errors[key] && (
      <p role="alert" className="mt-1 text-sm font-medium text-danger-fg">
        {errors[key]}
      </p>
    );

  return (
    <Card className="p-4">
      <form noValidate onSubmit={onSubmit} className="space-y-3">
        <h2 className="flex items-center gap-2 font-bold text-ink">
          <KeyRound size={18} aria-hidden="true" />
          {t('common:profile.password')}
        </h2>
        <div>
          <TextField
            type="password"
            autoComplete="current-password"
            label={t('common:profile.currentPassword')}
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
          />
          {error('current_password')}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <TextField
              type="password"
              autoComplete="new-password"
              label={t('common:profile.newPassword')}
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
            />
            {error('new_password')}
          </div>
          <div>
            <TextField
              type="password"
              autoComplete="new-password"
              label={t('common:profile.confirmPassword')}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
            {error('confirm')}
          </div>
        </div>
        <Button type="submit" disabled={saving || !current || !next || !confirm}>
          {t('common:profile.savePassword')}
        </Button>
      </form>
    </Card>
  );
}
