import { Mail, Phone } from 'lucide-react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import type { CurrentUser } from '@/auth/types';
import { Avatar } from '@/components/Avatar';
import { BrandMark } from '@/components/BrandMark';
import { NotificationBell } from '@/components/NotificationBell';
import { cn } from '@/lib/cn';

/**
 * Blue gradient top of a profile: big initials avatar, name, role, the main fact about
 * the person (group or department) and contact chips. `screen` is the full-width phone header.
 */
export function ProfileHero({
  user,
  facts,
  variant = 'card',
  children,
}: {
  user: CurrentUser;
  facts: string[];
  variant?: 'card' | 'screen';
  children?: ReactNode;
}) {
  const { t } = useTranslation(['common']);
  const screen = variant === 'screen';
  const contacts = [
    user.email && { icon: Mail, text: user.email, href: `mailto:${user.email}` },
    user.phone && {
      icon: Phone,
      text: user.phone,
      href: `tel:${user.phone.replace(/[^+\d]/g, '')}`,
    },
  ].filter(Boolean) as { icon: typeof Mail; text: string; href: string }[];

  return (
    <header
      className={cn(
        'bg-hero text-ink-on-primary',
        screen
          ? 'rounded-b-header px-4 pb-8 pt-[calc(16px+env(safe-area-inset-top))] sm:px-6'
          : 'rounded-card p-6 shadow-soft sm:p-8',
      )}
    >
      {screen && (
        <div className="flex items-center justify-between">
          <BrandMark size="md" />
          <NotificationBell />
        </div>
      )}
      <div
        className={cn(
          'flex flex-col items-center gap-4 text-center sm:flex-row sm:text-left',
          screen && 'mt-2',
        )}
      >
        <Avatar name={user.full_name} size="xl" tone="light" />
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-extrabold leading-tight sm:text-3xl">{user.full_name}</h1>
          <p className="mt-2 inline-flex rounded-full bg-white/20 px-3 py-1 text-sm font-bold">
            {t(`common:roles.${user.role}`)}
          </p>
          {facts.length > 0 && (
            <p className="mt-2 text-sm font-medium text-mint">{facts.join(' · ')}</p>
          )}
          {contacts.length > 0 && (
            <ul className="mt-3 flex flex-wrap justify-center gap-2 sm:justify-start">
              {contacts.map(({ icon: Icon, text, href }) => (
                <li key={href}>
                  <a
                    href={href}
                    className="inline-flex min-h-[36px] max-w-full items-center gap-2 rounded-full bg-white/15 px-3 text-sm font-semibold hover:bg-white/25"
                  >
                    <Icon size={16} aria-hidden="true" />
                    <span className="truncate">{text}</span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      {children}
    </header>
  );
}
