import type { ReactNode } from 'react';

import { BrandMark } from './BrandMark';
import { NotificationBell } from './NotificationBell';

/** Blue rounded header at the top of every student/teacher screen. */
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
    <header className="rounded-b-header bg-hero px-4 pb-7 pt-[calc(16px+env(safe-area-inset-top))] text-ink-on-primary sm:px-6">
      <div className="flex items-start justify-between gap-3">
        <BrandMark size="md" />
        <div className="min-w-0 flex-1">
          {subtitle && (
            <p className="text-sm font-medium text-mint first-letter:uppercase">{subtitle}</p>
          )}
          <h1 className="mt-1 text-2xl font-extrabold leading-tight">{title}</h1>
        </div>
        {bell && <NotificationBell />}
      </div>
      {children}
    </header>
  );
}
