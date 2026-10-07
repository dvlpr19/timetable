import { CloudOff, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { cn } from '@/lib/cn';
import { formatDayMonthTime } from '@/i18n/date';

/** "Last updated 10:42" — and a warning when the copy shown is the saved one. */
export function LastUpdated({
  at,
  stale,
  fetching,
  onRefresh,
}: {
  at: number;
  stale: boolean;
  fetching: boolean;
  onRefresh: () => void;
}) {
  const { t } = useTranslation(['app', 'dates']);
  if (!at) return null;
  const when = formatDayMonthTime(new Date(at), t);
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 rounded-button px-3 py-2 text-xs',
        stale ? 'bg-warning-bg text-warning-fg' : 'text-ink-muted',
      )}
    >
      <span className="inline-flex items-center gap-1.5">
        {stale && <CloudOff size={14} aria-hidden="true" />}
        {stale ? t('app:updated.saved', { when }) : t('app:updated.at', { when })}
      </span>
      <button
        type="button"
        onClick={onRefresh}
        disabled={fetching}
        className="inline-flex min-h-[32px] items-center gap-1 rounded-button px-2 font-semibold hover:bg-subtle disabled:opacity-60"
      >
        <RefreshCw size={14} aria-hidden="true" className={cn(fetching && 'animate-spin')} />
        {t('app:updated.refresh')}
      </button>
    </div>
  );
}
