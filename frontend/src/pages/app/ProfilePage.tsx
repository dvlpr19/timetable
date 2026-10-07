import { useQueryClient } from '@tanstack/react-query';
import {
  CalendarPlus,
  Download,
  FileSpreadsheet,
  FileText,
  LogOut,
  Smartphone,
  Trash2,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { ScreenHeader } from '@/components/ScreenHeader';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Pill } from '@/components/ui/Pill';
import { useToast } from '@/components/ui/Toast';
import { currentLanguage } from '@/i18n';
import { api, download } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useApi } from '@/lib/query';
import type { Occurrence } from '@/types/timetable';
import { formatDayMonth } from '@/i18n/date';
import { parseISO } from '@/lib/dates';

interface Request {
  id: number;
  lesson: Occurrence;
  occurrence_date: string | null;
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
  status_display: string;
  review_comment: string;
  created_at: string;
}

interface InstallPrompt extends Event {
  prompt: () => Promise<void>;
}

const STATUS: Record<Request['status'], string> = {
  pending: 'bg-warning-bg text-warning-fg',
  approved: 'bg-lesson-lecture-bg text-lesson-lecture',
  rejected: 'bg-danger-bg text-danger-fg',
};

/** Who I am, language, downloads, my requests (teachers), install, sign out. */
export function ProfilePage() {
  const { t } = useTranslation(['app', 'common']);
  const { user, logout } = useAuth();
  const toast = useToast();
  const teacher = user?.role === 'oqituvchi';
  const [install, setInstall] = useState<InstallPrompt | null>(null);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setInstall(e as InstallPrompt);
    };
    window.addEventListener('beforeinstallprompt', onPrompt);
    return () => window.removeEventListener('beforeinstallprompt', onPrompt);
  }, []);

  const save = (path: string, name: string) =>
    download(path, name).catch(() => toast(t('common:errors.unknown'), 'error'));
  const lang = currentLanguage();
  const standalone = window.matchMedia?.('(display-mode: standalone)').matches;

  return (
    <>
      <ScreenHeader
        title={user?.full_name ?? ''}
        subtitle={user ? t(`common:roles.${user.role}`) : undefined}
      >
        <p className="mt-1 text-sm text-mint">
          {user?.student
            ? `${user.student.group.name} · ${user.student.program}`
            : `${user?.teacher?.position ?? ''} · ${user?.teacher?.department ?? ''}`}
        </p>
      </ScreenHeader>
      <div className="space-y-4 px-4 py-5 sm:px-6">
        <Card className="space-y-3 p-4">
          <h2 className="font-bold text-ink">{t('common:language.label')}</h2>
          <LanguageSwitcher />
        </Card>

        <Card className="space-y-3 p-4">
          <h2 className="font-bold text-ink">{t('app:profile.downloads')}</h2>
          <p className="text-sm text-ink-muted">{t('app:profile.downloadsHint')}</p>
          <div className="grid gap-2 sm:grid-cols-3">
            <Button
              variant="secondary"
              icon={<FileText size={18} aria-hidden="true" />}
              onClick={() => save(`/api/export/?type=pdf&me=1&lang=${lang}`, 'dars-jadvali.pdf')}
            >
              {t('app:profile.pdf')}
            </Button>
            <Button
              variant="secondary"
              icon={<FileSpreadsheet size={18} aria-hidden="true" />}
              onClick={() => save(`/api/export/?type=xlsx&me=1&lang=${lang}`, 'dars-jadvali.xlsx')}
            >
              {t('app:profile.excel')}
            </Button>
            <Button
              variant="secondary"
              icon={<CalendarPlus size={18} aria-hidden="true" />}
              onClick={() => save('/api/export/ics/?me=1', 'dars-jadvali.ics')}
            >
              {t('app:profile.calendar')}
            </Button>
          </div>
        </Card>

        {teacher && <MyRequests />}

        {!standalone && (
          <Card className="space-y-3 p-4">
            <h2 className="flex items-center gap-2 font-bold text-ink">
              <Smartphone size={18} aria-hidden="true" />
              {t('app:profile.install')}
            </h2>
            <p className="text-sm text-ink-muted">{t('app:profile.installHint')}</p>
            {install && (
              <Button
                icon={<Download size={18} aria-hidden="true" />}
                onClick={async () => {
                  await install.prompt();
                  setInstall(null);
                }}
              >
                {t('app:profile.installButton')}
              </Button>
            )}
          </Card>
        )}

        <Button
          variant="secondary"
          block
          icon={<LogOut size={18} aria-hidden="true" />}
          onClick={logout}
        >
          {t('common:actions.logout')}
        </Button>
      </div>
    </>
  );
}

function MyRequests() {
  const { t } = useTranslation(['app', 'common', 'dates']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const requests = useApi<Request[]>('/api/reschedule-requests/');

  async function withdraw(id: number) {
    try {
      await api(`/api/reschedule-requests/${id}/`, { method: 'DELETE' });
      await queryClient.invalidateQueries({ queryKey: ['/api/reschedule-requests/'] });
      toast(t('app:request.withdrawn'));
    } catch {
      toast(t('common:errors.unknown'), 'error');
    }
  }

  return (
    <Card className="space-y-3 p-4">
      <h2 className="font-bold text-ink">{t('app:request.mine')}</h2>
      {!requests.data?.length ? (
        <p className="text-sm text-ink-muted">{t('app:request.none')}</p>
      ) : (
        <ul className="space-y-2">
          {requests.data.map((r) => (
            <li key={r.id} className="rounded-button border border-line p-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-bold text-ink">{r.lesson.subject.name}</p>
                  <p className="text-ink-muted">
                    {r.occurrence_date
                      ? formatDayMonth(parseISO(r.occurrence_date), t)
                      : t('app:request.weekly')}{' '}
                    · {r.lesson.groups.map((g) => g.name).join(', ')}
                  </p>
                </div>
                <Pill className={cn('shrink-0', STATUS[r.status])}>{r.status_display}</Pill>
              </div>
              <p className="mt-1 text-ink">{r.reason}</p>
              {r.review_comment && (
                <p className="mt-1 rounded-button bg-subtle p-2 text-ink">
                  {t('app:request.answer')}: {r.review_comment}
                </p>
              )}
              {r.status === 'pending' && (
                <button
                  type="button"
                  onClick={() => withdraw(r.id)}
                  className="mt-2 inline-flex min-h-[36px] items-center gap-1.5 rounded-button px-2 text-xs font-bold text-danger-fg hover:bg-danger-bg"
                >
                  <Trash2 size={14} aria-hidden="true" />
                  {t('app:request.withdraw')}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
