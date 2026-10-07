import { useQueryClient } from '@tanstack/react-query';
import { BellRing, Share } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { currentSubscription, disablePush, enablePush, pushSupport } from '@/lib/push';
import { useApi } from '@/lib/query';

interface Preferences {
  disabled_kinds: string[];
  reminder_enabled: boolean;
  reminder_minutes: number;
  daily_digest_enabled: boolean;
  optional_kinds: string[];
  mandatory_kinds: string[];
}

const MINUTES = [5, 10, 15, 30, 60];

function Toggle({
  label,
  hint,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex min-h-touch cursor-pointer items-center justify-between gap-4 py-1">
      <span>
        <span className="block text-sm font-semibold text-ink">{label}</span>
        {hint && <span className="block text-xs text-ink-muted">{hint}</span>}
      </span>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="peer sr-only"
      />
      <span
        aria-hidden="true"
        className="relative h-7 w-12 shrink-0 rounded-full bg-line transition-colors after:absolute after:left-1 after:top-1 after:h-5 after:w-5 after:rounded-full after:bg-card after:shadow after:transition-transform peer-checked:bg-primary-700 peer-checked:after:translate-x-5 peer-focus-visible:ring-2 peer-focus-visible:ring-primary-500 peer-disabled:opacity-60"
      />
    </label>
  );
}

/** Push on this device, reminders, the evening summary and which messages to get. */
export function NotificationSettings() {
  const { t } = useTranslation(['app', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const prefs = useApi<Preferences>('/api/notifications/preferences/');
  const push = useApi<{ enabled: boolean; public_key: string }>('/api/notifications/push/');
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);
  const support = pushSupport();

  useEffect(() => {
    void currentSubscription().then((s) => setSubscribed(Boolean(s)));
  }, []);

  async function save(patch: Partial<Preferences>) {
    try {
      const data = await api<Preferences>('/api/notifications/preferences/', {
        method: 'PATCH',
        body: patch,
      });
      queryClient.setQueryData(['/api/notifications/preferences/'], data);
    } catch {
      toast(t('common:errors.unknown'), 'error');
    }
  }

  async function togglePush() {
    setBusy(true);
    try {
      if (subscribed) {
        await disablePush();
        setSubscribed(false);
      } else if (push.data?.public_key) {
        const ok = await enablePush(push.data.public_key);
        setSubscribed(ok);
        if (!ok) toast(t('app:notify.denied'), 'error');
        else toast(t('app:notify.pushOn'));
      }
    } catch {
      toast(t('common:errors.unknown'), 'error');
    } finally {
      setBusy(false);
    }
  }

  const p = prefs.data;
  return (
    <Card className="space-y-4 p-4">
      <h2 className="flex items-center gap-2 font-bold text-ink">
        <BellRing size={18} aria-hidden="true" />
        {t('app:notify.title')}
      </h2>

      <div className="rounded-button bg-subtle p-3">
        <p className="text-sm font-semibold text-ink">{t('app:notify.push')}</p>
        {support === 'ios-needs-install' ? (
          <p className="mt-1 flex gap-2 text-sm text-ink-muted">
            <Share size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
            {t('app:notify.iosHint')}
          </p>
        ) : support === 'unsupported' ? (
          <p className="mt-1 text-sm text-ink-muted">{t('app:notify.unsupported')}</p>
        ) : !push.data?.enabled ? (
          <p className="mt-1 text-sm text-ink-muted">{t('app:notify.serverOff')}</p>
        ) : (
          <>
            <p className="mt-1 text-sm text-ink-muted">
              {subscribed ? t('app:notify.pushOnHint') : t('app:notify.pushOffHint')}
            </p>
            <Button
              variant={subscribed ? 'secondary' : 'primary'}
              className="mt-2"
              disabled={busy}
              onClick={togglePush}
            >
              {subscribed ? t('app:notify.disable') : t('app:notify.enable')}
            </Button>
          </>
        )}
      </div>

      {p && (
        <>
          <div className="divide-y divide-line">
            <div className="pb-2">
              <Toggle
                label={t('app:notify.reminder')}
                hint={t('app:notify.reminderHint')}
                checked={p.reminder_enabled}
                onChange={(v) => save({ reminder_enabled: v })}
              />
              {p.reminder_enabled && (
                <Select
                  label={t('app:notify.minutes')}
                  value={p.reminder_minutes}
                  onChange={(e) => save({ reminder_minutes: Number(e.target.value) })}
                  options={MINUTES.map((m) => ({
                    value: m,
                    label: t('app:notify.minutesValue', { n: m }),
                  }))}
                />
              )}
            </div>
            <div className="py-2">
              <Toggle
                label={t('app:notify.digest')}
                hint={t('app:notify.digestHint')}
                checked={p.daily_digest_enabled}
                onChange={(v) => save({ daily_digest_enabled: v })}
              />
            </div>
          </div>
          <div>
            <p className="mb-1 text-sm font-semibold text-ink">{t('app:notify.which')}</p>
            {p.mandatory_kinds.map((kind) => (
              <Toggle
                key={kind}
                label={t(`app:notify.kinds.${kind}`)}
                hint={t('app:notify.mandatory')}
                checked
                disabled
                onChange={() => undefined}
              />
            ))}
            {p.optional_kinds.map((kind) => (
              <Toggle
                key={kind}
                label={t(`app:notify.kinds.${kind}`)}
                checked={!p.disabled_kinds.includes(kind)}
                onChange={(on) =>
                  save({
                    disabled_kinds: on
                      ? p.disabled_kinds.filter((k) => k !== kind)
                      : [...p.disabled_kinds, kind],
                  })
                }
              />
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
