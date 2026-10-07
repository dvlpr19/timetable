import { Bell } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { useUnreadCount } from '@/lib/notifications';

/** Bell with the number of unread messages (refreshed every 25 seconds). */
export function NotificationBell() {
  const { t } = useTranslation(['app']);
  const count = useUnreadCount();
  return (
    <Link
      to="/messages"
      aria-label={count ? t('app:messages.bellUnread', { n: count }) : t('app:messages.bell')}
      className="relative flex min-h-touch min-w-touch items-center justify-center rounded-full bg-white/10 text-ink-on-primary hover:bg-white/20"
    >
      <Bell size={20} aria-hidden="true" />
      {count > 0 && (
        <span
          aria-hidden="true"
          className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-gold px-1 text-[11px] font-extrabold text-primary-900"
        >
          {count > 99 ? '99+' : count}
        </span>
      )}
    </Link>
  );
}
