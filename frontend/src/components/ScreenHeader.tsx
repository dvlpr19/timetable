import type { ReactNode } from 'react';

/** Green rounded header at the top of every student/teacher screen. */
export function ScreenHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <header className="rounded-b-header bg-primary-900 px-4 pb-6 pt-[calc(16px+env(safe-area-inset-top))] text-ink-on-primary sm:px-6">
      {subtitle && (
        <p className="text-sm font-medium text-mint first-letter:uppercase">{subtitle}</p>
      )}
      <h1 className="mt-1 text-2xl font-extrabold">{title}</h1>
      {children}
    </header>
  );
}
