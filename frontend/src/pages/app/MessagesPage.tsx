import { CheckCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { ScreenHeader } from '@/components/ScreenHeader';
import { Button } from '@/components/ui/Button';
import { EmptyState, ErrorState, LoadingRows } from '@/components/ui/States';
import { useMarkRead, useNotifications } from '@/lib/notifications';

import { MessageCard } from './MessageCard';

/** "Xabarlar": what changed, newest first; the old state is crossed out. */
export function MessagesPage() {
  const { t } = useTranslation(['app', 'dates']);
  const list = useNotifications();
  const mark = useMarkRead();
  const unread = list.items.filter((n) => !n.is_read).length;

  return (
    <>
      <ScreenHeader
        title={t('app:messages.title')}
        subtitle={t('app:messages.subtitle')}
        bell={false}
      />
      <div className="space-y-4 px-4 py-5 sm:px-6">
        {unread > 0 && (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-ink">
              {t('app:messages.unread', { n: unread })}
            </p>
            <Button
              variant="ghost"
              icon={<CheckCheck size={18} aria-hidden="true" />}
              onClick={() => void mark.all()}
            >
              {t('app:messages.readAll')}
            </Button>
          </div>
        )}
        {list.isError ? (
          <ErrorState onRetry={() => list.refetch()} />
        ) : list.isLoading ? (
          <LoadingRows rows={4} />
        ) : !list.items.length ? (
          <EmptyState title={t('app:messages.empty')} text={t('app:messages.emptyHint')} />
        ) : (
          <ul className="space-y-2">
            {list.items.map((n) => (
              <li key={n.id}>
                <MessageCard n={n} onRead={() => void mark.one(n.id)} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
