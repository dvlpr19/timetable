import { Mail, Phone, Save } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextField } from '@/components/ui/TextField';
import { useToast } from '@/components/ui/Toast';
import { ApiError } from '@/lib/api';

type Field = 'email' | 'phone';

/** E-mail and phone of the signed-in account, editable by the person themselves. */
export function ContactCard() {
  const { t } = useTranslation(['common']);
  const { user, updateProfile } = useAuth();
  const toast = useToast();
  const [email, setEmail] = useState(user?.email ?? '');
  const [phone, setPhone] = useState(user?.phone ?? '');
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [saving, setSaving] = useState(false);
  const changed = email.trim() !== (user?.email ?? '') || phone.trim() !== (user?.phone ?? '');

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setErrors({});
    setSaving(true);
    try {
      await updateProfile({ email: email.trim(), phone: phone.trim() });
      toast(t('common:profile.contactsSaved'));
    } catch (err) {
      const data = err instanceof ApiError ? (err.data as Record<string, unknown> | null) : null;
      const first = (v: unknown) => (Array.isArray(v) ? v.join(' ') : undefined);
      if (data && (data.email || data.phone)) {
        setErrors({ email: first(data.email), phone: first(data.phone) });
      } else {
        toast(t('common:errors.unknown'), 'error');
      }
    } finally {
      setSaving(false);
    }
  }

  const error = (key: Field) =>
    errors[key] && (
      <p role="alert" className="mt-1 text-sm font-medium text-danger-fg">
        {errors[key]}
      </p>
    );

  return (
    <Card className="p-5">
      <form noValidate onSubmit={onSubmit} className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-ink">{t('common:profile.contacts')}</h2>
          <p className="mt-1 text-sm text-ink-muted">{t('common:profile.contactsHint')}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <TextField
              type="email"
              inputMode="email"
              autoComplete="email"
              label={t('common:profile.email')}
              placeholder="ism@example.uz"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              trailing={<Mail size={18} aria-hidden="true" className="mr-4 text-accent" />}
            />
            {error('email')}
          </div>
          <div>
            <TextField
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              label={t('common:profile.phone')}
              placeholder="+998 90 123 45 67"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              trailing={<Phone size={18} aria-hidden="true" className="mr-4 text-accent" />}
            />
            {error('phone')}
          </div>
        </div>
        <Button
          type="submit"
          disabled={saving || !changed}
          icon={<Save size={18} aria-hidden="true" />}
        >
          {saving ? t('common:profile.saving') : t('common:profile.saveContacts')}
        </Button>
      </form>
    </Card>
  );
}
