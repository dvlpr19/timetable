import { LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { Avatar } from '@/components/Avatar';
import { ChangePasswordCard } from '@/components/ChangePasswordCard';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

/** Profile of a staff account: who I am, my scope, language, password, sign out. */
export function AdminProfilePage() {
  const { t } = useTranslation(['common', 'admin']);
  const { user, logout } = useAuth();
  if (!user) return null;
  const details = [
    { label: t('common:profile.username'), value: user.username },
    { label: t('common:profile.role'), value: t(`common:roles.${user.role}`) },
    { label: t('common:profile.faculty'), value: user.faculty_name },
    { label: t('common:profile.department'), value: user.department_name },
  ].filter((d) => d.value);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-extrabold text-ink">{t('common:profile.title')}</h1>

      <Card className="overflow-hidden">
        <div className="flex items-center gap-4 bg-primary-900 p-5 text-ink-on-primary">
          <Avatar name={user.full_name} size="lg" className="bg-white text-primary-900" />
          <div className="min-w-0">
            <p className="truncate text-xl font-extrabold">{user.full_name}</p>
            <p className="text-sm text-mint">{t(`common:roles.${user.role}`)}</p>
          </div>
        </div>
        <dl className="grid gap-4 p-5 sm:grid-cols-2">
          {details.map((d) => (
            <div key={d.label}>
              <dt className="text-xs font-bold uppercase tracking-wide text-ink-muted">
                {d.label}
              </dt>
              <dd className="mt-1 font-semibold text-ink">{d.value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card className="space-y-3 p-4">
        <h2 className="font-bold text-ink">{t('common:language.label')}</h2>
        <LanguageSwitcher />
      </Card>

      <ChangePasswordCard />

      <Button variant="secondary" icon={<LogOut size={18} aria-hidden="true" />} onClick={logout}>
        {t('common:actions.logout')}
      </Button>
    </div>
  );
}
