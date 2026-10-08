import {
  Building2,
  CalendarClock,
  CalendarPlus,
  Landmark,
  LogOut,
  ShieldCheck,
  User,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { ChangePasswordCard } from '@/components/ChangePasswordCard';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { ContactCard } from '@/components/profile/ContactCard';
import { DetailsCard } from '@/components/profile/DetailsCard';
import { ProfileHero } from '@/components/profile/ProfileHero';
import { StatsTiles } from '@/components/profile/StatsTiles';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { formatDayMonth, formatDayMonthTime } from '@/i18n/date';

/** Profile of a staff account: who I am, my scope, contacts, language, password, sign out. */
export function AdminProfilePage() {
  const { t } = useTranslation(['common', 'admin', 'dates']);
  const { user, logout } = useAuth();
  if (!user) return null;
  const joined = user.date_joined ? new Date(user.date_joined) : null;
  const lastLogin = user.last_login ? new Date(user.last_login) : null;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <ProfileHero
        user={user}
        facts={[user.faculty_name, user.department_name, t('common:academyName')].filter(
          (x): x is string => Boolean(x),
        )}
      />

      <StatsTiles />

      <div className="grid gap-6 lg:grid-cols-2">
        <DetailsCard
          title={t('common:profile.account')}
          items={[
            { icon: User, label: t('common:profile.username'), value: user.username },
            {
              icon: ShieldCheck,
              label: t('common:profile.role'),
              value: t(`common:roles.${user.role}`),
            },
            { icon: Landmark, label: t('common:profile.faculty'), value: user.faculty_name },
            { icon: Building2, label: t('common:profile.department'), value: user.department_name },
            {
              icon: CalendarPlus,
              label: t('common:profile.memberSince'),
              value: joined && `${formatDayMonth(joined, t)} ${joined.getFullYear()}`,
            },
            {
              icon: CalendarClock,
              label: t('common:profile.lastLogin'),
              value: lastLogin && formatDayMonthTime(lastLogin, t),
            },
          ]}
        />
        <ContactCard />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <Card className="space-y-3 p-5">
          <h2 className="text-lg font-bold text-ink">{t('common:language.label')}</h2>
          <LanguageSwitcher />
        </Card>
        <ChangePasswordCard />
      </div>

      <Button variant="secondary" icon={<LogOut size={18} aria-hidden="true" />} onClick={logout}>
        {t('common:actions.logout')}
      </Button>
    </div>
  );
}
