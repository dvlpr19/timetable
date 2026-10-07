import type { ReactNode } from 'react';

import { NotificationBell } from './NotificationBell';

/** Green rounded header at the top of every student/teacher screen. */
export function ScreenHeader({
  title,
  subtitle,
  children,
  bell = true,
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
  bell?: boolean;
}) {
  return (
    <header className="rounded-b-header bg-primary-900 px-4 pb-6 pt-[calc(16px+env(safe-area-inset-top))] text-ink-on-primary sm:px-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {subtitle && (
            <p className="text-sm font-medium text-mint first-letter:uppercase">{subtitle}</p>
          )}
          <h1 className="mt-1 text-2xl font-extrabold">{title}</h1>
        </div>
        {bell && <NotificationBell />}
      </div>
      {children}
    </header>
  );
}
