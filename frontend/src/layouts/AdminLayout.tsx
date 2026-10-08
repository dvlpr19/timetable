import {
  BarChart3,
  CalendarClock,
  CalendarDays,
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Menu,
  Wand2,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/auth/useAuth';
import { Avatar } from '@/components/Avatar';
import { BrandMark } from '@/components/BrandMark';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { cn } from '@/lib/cn';
import { RESOURCE_GROUPS, RESOURCES } from '@/pages/admin/data/resources';
import type { Resource, ResourceGroup } from '@/pages/admin/data/resources';

function NavItem({
  to,
  icon: Icon,
  label,
  end,
}: {
  to: string;
  icon: typeof Menu;
  label: string;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex min-h-touch items-center gap-3 rounded-full px-4 text-sm font-semibold transition-colors',
          isActive ? 'bg-primary-700 text-ink-on-primary shadow-soft' : 'text-ink hover:bg-subtle',
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            size={20}
            aria-hidden="true"
            className={isActive ? 'text-ink-on-primary' : 'text-accent'}
          />
          <span className="truncate">{label}</span>
        </>
      )}
    </NavLink>
  );
}

/** A collapsible sub-category of the data menu; the one holding the open page starts expanded. */
function NavGroup({ group, items }: { group: ResourceGroup; items: Resource[] }) {
  const { t } = useTranslation(['admin', 'data']);
  const { pathname } = useLocation();
  const active = items.some((r) => pathname === `/admin/data/${r.key}`);
  const [open, setOpen] = useState(active);
  useEffect(() => {
    if (active) setOpen(true);
  }, [active]);
  const id = `nav-group-${group}`;
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className={cn(
          'flex min-h-touch w-full items-center gap-2 rounded-full px-4 text-left text-sm font-bold transition-colors hover:bg-subtle',
          active ? 'text-primary-700' : 'text-ink',
        )}
      >
        <span className="flex-1 truncate">{t(`admin:nav.groups.${group}`)}</span>
        <ChevronDown
          size={16}
          aria-hidden="true"
          className={cn('shrink-0 transition-transform', open && 'rotate-180')}
        />
      </button>
      {open && (
        <div id={id} className="ml-4 space-y-1 border-l border-line pl-2">
          {items.map((r) => (
            <NavItem
              key={r.key}
              to={`/admin/data/${r.key}`}
              icon={r.icon}
              label={t(`data:resources.${r.key}.title`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function Sidebar() {
  const { t } = useTranslation(['admin', 'data', 'common']);
  const { user } = useAuth();
  const sections = RESOURCES.filter((r) => !r.roles || (user && r.roles.includes(user.role)));
  return (
    <nav
      aria-label={t('admin:nav.label')}
      className="flex h-full flex-col gap-6 overflow-y-auto p-4"
    >
      <div className="flex flex-col items-center gap-2 rounded-tile bg-hero px-3 py-5 text-center shadow-soft">
        <BrandMark size="lg" />
        <p className="text-base font-extrabold text-ink-on-primary">{t('common:appName')}</p>
        <p className="text-xs leading-snug text-mint">{t('common:academyName')}</p>
      </div>
      <div className="space-y-1">
        <NavItem to="/admin" end icon={LayoutDashboard} label={t('admin:nav.dashboard')} />
        <NavItem to="/admin/schedule" icon={CalendarDays} label={t('admin:nav.schedule')} />
        <NavItem to="/admin/solver" icon={Wand2} label={t('admin:nav.solver')} />
        <NavItem to="/admin/requests" icon={CalendarClock} label={t('admin:nav.requests')} />
        <NavItem to="/admin/reports" icon={BarChart3} label={t('admin:nav.reports')} />
      </div>
      <div className="space-y-1">
        <p className="px-4 pb-1 text-xs font-bold uppercase tracking-wider text-ink-muted">
          {t('admin:nav.data')}
        </p>
        {RESOURCE_GROUPS.map((group) => {
          const items = sections.filter((r) => r.group === group);
          return items.length ? <NavGroup key={group} group={group} items={items} /> : null;
        })}
      </div>
    </nav>
  );
}

export function AdminLayout() {
  const { t } = useTranslation(['admin', 'common']);
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setMenuOpen(false), [location.pathname]);

  return (
    <div className="flex min-h-dvh bg-page">
      <a
        href="#main"
        className="sr-only z-50 rounded-button bg-card px-4 py-2 focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        {t('admin:skipToContent')}
      </a>
      <aside className="hidden w-72 shrink-0 border-r border-line bg-card lg:block">
        <div className="sticky top-0 h-dvh">
          <Sidebar />
        </div>
      </aside>
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-ink/40"
            aria-hidden="true"
            onClick={() => setMenuOpen(false)}
          />
          <aside className="relative h-full w-72 max-w-[85vw] bg-card">
            <button
              type="button"
              onClick={() => setMenuOpen(false)}
              aria-label={t('common:actions.close')}
              className="absolute right-2 top-2 z-10 flex min-h-touch min-w-touch items-center justify-center rounded-full bg-white/20 text-ink-on-primary"
            >
              <X size={22} aria-hidden="true" />
            </button>
            <Sidebar />
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-card/90 px-4 py-2 backdrop-blur sm:px-6">
          <button
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-label={t('admin:nav.open')}
            className="flex min-h-touch min-w-touch items-center justify-center rounded-button text-ink hover:bg-subtle lg:hidden"
          >
            <Menu size={22} aria-hidden="true" />
          </button>
          <div className="ml-auto flex items-center gap-3">
            <LanguageSwitcher />
            <Link
              to="/admin/profile"
              title={t('admin:nav.profile')}
              className="flex min-h-touch items-center gap-2 rounded-full px-1.5 hover:bg-subtle sm:pr-4"
            >
              <Avatar name={user?.full_name ?? ''} size="sm" />
              <span className="hidden text-left sm:block">
                <span className="block text-sm font-bold text-ink">{user?.full_name}</span>
                <span className="block text-xs text-ink-muted">
                  {user && t(`common:roles.${user.role}`)}
                </span>
              </span>
              <span className="sr-only sm:hidden">{t('admin:nav.profile')}</span>
            </Link>
            <button
              type="button"
              onClick={logout}
              aria-label={t('common:actions.logout')}
              title={t('common:actions.logout')}
              className="flex min-h-touch min-w-touch items-center justify-center rounded-button text-ink-muted hover:bg-subtle hover:text-ink"
            >
              <LogOut size={20} aria-hidden="true" />
            </button>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
