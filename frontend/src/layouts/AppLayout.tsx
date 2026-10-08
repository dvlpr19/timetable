import {
  CalendarDays,
  CalendarRange,
  DoorOpen,
  Search,
  SlidersHorizontal,
  UserRound,
  WifiOff,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet } from 'react-router-dom';

import { useAuth } from '@/auth/useAuth';
import { cn } from '@/lib/cn';

interface Tab {
  to: string;
  icon: LucideIcon;
  label: string;
  end?: boolean;
}

function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => {
      window.removeEventListener('online', on);
      window.removeEventListener('offline', off);
    };
  }, []);
  return online;
}

/** Student and teacher app: one column, tab bar at the bottom (thumb reach on phones). */
export function AppLayout() {
  const { t } = useTranslation(['app']);
  const { user } = useAuth();
  const online = useOnline();
  const teacher = user?.role === 'oqituvchi';
  const tabs: Tab[] = teacher
    ? [
        { to: '/', icon: CalendarDays, label: t('app:tabs.today'), end: true },
        { to: '/week', icon: CalendarRange, label: t('app:tabs.myWeek') },
        { to: '/rooms', icon: DoorOpen, label: t('app:tabs.rooms') },
        { to: '/availability', icon: SlidersHorizontal, label: t('app:tabs.availability') },
        { to: '/profile', icon: UserRound, label: t('app:tabs.profile') },
      ]
    : [
        { to: '/', icon: CalendarDays, label: t('app:tabs.today'), end: true },
        { to: '/week', icon: CalendarRange, label: t('app:tabs.week') },
        { to: '/search', icon: Search, label: t('app:tabs.search') },
        { to: '/profile', icon: UserRound, label: t('app:tabs.profile') },
      ];

  return (
    <div className="min-h-dvh bg-page pb-[calc(72px+env(safe-area-inset-bottom))]">
      <a
        href="#main"
        className="sr-only z-50 rounded-button bg-card px-4 py-2 focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        {t('app:skipToContent')}
      </a>
      {!online && (
        <div
          role="status"
          className="flex items-center justify-center gap-2 bg-warning-bg px-4 py-2 text-sm font-semibold text-warning-fg"
        >
          <WifiOff size={16} aria-hidden="true" />
          {t('app:offline')}
        </div>
      )}
      <main id="main" className="mx-auto w-full max-w-xl">
        <Outlet />
      </main>
      <nav
        aria-label={t('app:tabs.label')}
        className="fixed inset-x-0 bottom-0 z-30 rounded-t-header bg-card/95 pb-[env(safe-area-inset-bottom)] shadow-lift backdrop-blur"
      >
        <ul className="mx-auto flex max-w-xl">
          {tabs.map(({ to, icon: Icon, label, end }) => (
            <li key={to} className="flex-1">
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-[64px] flex-col items-center justify-center gap-1 px-1 text-[11px] font-semibold transition-colors',
                    isActive ? 'font-bold text-primary-700' : 'text-ink-muted hover:text-ink',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={cn(
                        'flex h-8 w-14 items-center justify-center rounded-full transition-colors',
                        isActive && 'bg-primary-700 text-ink-on-primary shadow-soft',
                      )}
                    >
                      <Icon size={20} aria-hidden="true" />
                    </span>
                    <span className="max-w-full truncate">{label}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
