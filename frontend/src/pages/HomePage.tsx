import { LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { Button } from '@/components/ui/Button';
import { formatLongDate } from '@/i18n/date';

/** Temporary landing page; replaced by role-specific screens in stages 5 and 7. */
export function HomePage() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="min-h-dvh bg-page">
      <header className="rounded-b-header bg-primary-900 px-4 pb-8 pt-6 text-ink-on-primary sm:px-8">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
          <p className="text-sm font-medium text-mint">{formatLongDate(new Date(), t)}</p>
          <LanguageSwitcher tone="dark" />
        </div>
        <div className="mx-auto mt-6 max-w-3xl">
          <h1 className="text-2xl font-extrabold">
            {t('home.greeting', { name: user.first_name || user.username })}
          </h1>
          <p className="mt-1 text-sm font-medium text-mint">{t(`roles.${user.role}`)}</p>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-6 sm:px-8">
        <div className="rounded-card border border-line bg-card p-6 text-ink-muted">
          {t('home.comingSoon')}
        </div>
        <Button
          variant="secondary"
          className="mt-6"
          onClick={logout}
          icon={<LogOut size={18} aria-hidden="true" />}
        >
          {t('actions.logout')}
        </Button>
      </main>
    </div>
  );
}
