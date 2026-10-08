import { AlertCircle, Eye, EyeOff, LogIn } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate } from 'react-router-dom';

import { useAuth } from '@/auth/useAuth';
import { BrandMark } from '@/components/BrandMark';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { ApiError, NetworkError } from '@/lib/api';

export function LoginPage() {
  const { t } = useTranslation(['auth', 'common']);
  const { user, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError(t('auth:required'));
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      if (err instanceof ApiError && err.detail) setError(err.detail);
      else if (err instanceof NetworkError) setError(t('common:errors.network'));
      else setError(t('common:errors.unknown'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-page">
      <header className="rounded-b-header bg-hero px-4 pb-24 pt-[calc(16px+env(safe-area-inset-top))] text-ink-on-primary sm:px-8">
        <div className="flex justify-end">
          <LanguageSwitcher tone="dark" />
        </div>
        <div className="mx-auto mt-4 flex max-w-md flex-col items-center text-center">
          <BrandMark size="xl" className="mb-5 shadow-lift" />
          <p className="text-sm font-semibold text-mint">{t('common:academyName')}</p>
          <h1 className="mt-1 text-3xl font-extrabold">{t('common:appName')}</h1>
        </div>
      </header>

      <main className="-mt-16 flex flex-1 justify-center px-4 pb-10">
        <div className="w-full max-w-[420px]">
          <form
            noValidate
            onSubmit={onSubmit}
            className="rounded-tile bg-card p-6 shadow-lift dark:border dark:border-line sm:p-8"
          >
            <h2 className="text-lg font-bold text-ink">{t('auth:title')}</h2>
            <p className="mt-1 text-sm text-ink-muted">{t('auth:subtitle')}</p>

            {error && (
              <div
                role="alert"
                className="mt-4 flex items-start gap-2 rounded-button bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
              >
                <AlertCircle size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}

            <TextField
              className="mt-6"
              label={t('auth:username')}
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <TextField
              className="mt-4"
              label={t('auth:password')}
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              trailing={
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? t('auth:hidePassword') : t('auth:showPassword')}
                  className="flex min-h-touch min-w-touch items-center justify-center text-ink-muted hover:text-ink"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              }
            />

            <Button
              type="submit"
              block
              className="mt-6"
              disabled={submitting}
              icon={<LogIn size={20} aria-hidden="true" />}
            >
              {submitting ? t('auth:submitting') : t('auth:submit')}
            </Button>

            <div className="my-4 flex items-center gap-3 text-xs font-medium text-ink-muted">
              <span className="h-px flex-1 bg-line" />
              {t('auth:or')}
              <span className="h-px flex-1 bg-line" />
            </div>

            <Button variant="secondary" block disabled aria-describedby="hemis-soon">
              {t('auth:hemis')}
              <span
                id="hemis-soon"
                className="rounded-full bg-subtle px-2 py-0.5 text-xs font-semibold text-ink-muted"
              >
                {t('auth:soon')}
              </span>
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}
