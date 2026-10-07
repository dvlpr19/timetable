import { AlertTriangle, Inbox } from 'lucide-react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { cn } from '@/lib/cn';

import { Button } from './Button';

export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div aria-hidden="true" className={cn('animate-pulse rounded-button bg-subtle', className)} />
  );
}

export function LoadingRows({ rows = 5 }: { rows?: number }) {
  const { t } = useTranslation();
  return (
    <div role="status" aria-label={t('loading')} className="space-y-2">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  text,
  action,
}: {
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-card border border-dashed border-line bg-card px-6 py-12 text-center">
      <span className="mb-2 flex h-14 w-14 items-center justify-center rounded-full bg-subtle text-ink-muted">
        <Inbox size={26} aria-hidden="true" />
      </span>
      <p className="text-base font-bold text-ink">{title}</p>
      {text && <p className="max-w-sm text-sm text-ink-muted">{text}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorState({ text, onRetry }: { text?: string; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-2 rounded-card bg-danger-bg px-6 py-10 text-center text-danger-fg"
    >
      <AlertTriangle size={26} aria-hidden="true" />
      <p className="text-base font-bold">{t('errors.loadFailed')}</p>
      <p className="max-w-md text-sm">{text ?? t('errors.unknown')}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-2" onClick={onRetry}>
          {t('actions.retry')}
        </Button>
      )}
    </div>
  );
}
