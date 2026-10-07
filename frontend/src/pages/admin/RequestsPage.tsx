import { useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Check, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { useAuth } from '@/auth/useAuth';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Pill } from '@/components/ui/Pill';
import { Segmented } from '@/components/ui/Segmented';
import { EmptyState, ErrorState, LoadingRows } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { useApi } from '@/lib/query';
import type { TimetableEntry } from '@/types/timetable';
import { formatDayMonth } from '@/i18n/date';
import { parseISO } from '@/lib/dates';

interface Request {
  id: number;
  teacher_name: string;
  lesson: TimetableEntry;
  occurrence_date: string | null;
  reason: string;
  desired_weekday: number | null;
  desired_date: string | null;
  desired_lesson_number: number | null;
  desired_note: string;
  status: 'pending' | 'approved' | 'rejected';
  status_display: string;
  review_comment: string;
  created_at: string;
}

const STATUS = {
  pending: 'bg-warning-bg text-warning-fg',
  approved: 'bg-lesson-lecture-bg text-lesson-lecture',
  rejected: 'bg-danger-bg text-danger-fg',
};

/** Teachers' reschedule requests; the dispatcher answers and moves the lesson in the editor. */
export function RequestsPage() {
  const { t } = useTranslation(['admin', 'dates', 'common']);
  const { user } = useAuth();
  const [status, setStatus] = useState<'pending' | 'all'>('pending');
  const requests = useApi<Request[]>('/api/reschedule-requests/', {
    status: status === 'pending' ? 'pending' : undefined,
  });
  const canAnswer = user?.role === 'admin';
  const weekdays = t('dates:weekdays', { returnObjects: true }) as string[];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-ink">{t('admin:requests.title')}</h1>
          <p className="mt-1 text-sm text-ink-muted">{t('admin:requests.hint')}</p>
        </div>
        <Segmented
          label={t('admin:requests.filter')}
          value={status}
          onChange={setStatus}
          options={[
            { value: 'pending', label: t('admin:requests.pending') },
            { value: 'all', label: t('admin:requests.all') },
          ]}
        />
      </div>
      {requests.isError ? (
        <ErrorState onRetry={() => requests.refetch()} />
      ) : requests.isLoading ? (
        <LoadingRows rows={4} />
      ) : !requests.data?.length ? (
        <EmptyState title={t('admin:requests.empty')} />
      ) : (
        <ul className="grid gap-3 lg:grid-cols-2">
          {requests.data.map((r) => {
            const l = r.lesson;
            const when = r.occurrence_date
              ? formatDayMonth(parseISO(r.occurrence_date), t)
              : l.weekday !== null
                ? t('admin:requests.everyWeek', { day: weekdays[l.weekday] })
                : (l.date ?? '');
            const wish = [
              r.desired_date && formatDayMonth(parseISO(r.desired_date), t),
              r.desired_weekday !== null && weekdays[r.desired_weekday],
              r.desired_lesson_number &&
                t('admin:editor.lessonNumber', { n: r.desired_lesson_number }),
              r.desired_note,
            ].filter(Boolean);
            return (
              <li key={r.id}>
                <Card className="space-y-3 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-bold text-ink">
                        {l.subject.name} · {l.lesson_type.name}
                      </p>
                      <p className="text-sm text-ink-muted">
                        {r.teacher_name} · {l.groups.map((g) => g.name).join(', ')}
                      </p>
                    </div>
                    <Pill className={STATUS[r.status]}>{r.status_display}</Pill>
                  </div>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                    <dt className="text-ink-muted">{t('admin:requests.lessonAt')}</dt>
                    <dd className="text-ink">
                      {when}, {t('admin:editor.lessonNumber', { n: l.lesson_time.number })}
                      {l.room ? ` · ${l.room.name}` : ''}
                    </dd>
                    <dt className="text-ink-muted">{t('admin:requests.reason')}</dt>
                    <dd className="text-ink">{r.reason}</dd>
                    {wish.length > 0 && (
                      <>
                        <dt className="text-ink-muted">{t('admin:requests.wish')}</dt>
                        <dd className="text-ink">{wish.join(', ')}</dd>
                      </>
                    )}
                    {r.review_comment && (
                      <>
                        <dt className="text-ink-muted">{t('admin:requests.answer')}</dt>
                        <dd className="text-ink">{r.review_comment}</dd>
                      </>
                    )}
                  </dl>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      to={`/admin/schedule?view=teacher&target=${l.teacher.id}`}
                      className="inline-flex min-h-touch items-center gap-1 text-sm font-bold text-link hover:underline"
                    >
                      {t('admin:requests.openEditor')}
                      <ArrowRight size={16} aria-hidden="true" />
                    </Link>
                    {canAnswer && r.status === 'pending' && <Answer id={r.id} />}
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function Answer({ id }: { id: number }) {
  const { t } = useTranslation(['admin', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);

  async function send(status: 'approved' | 'rejected') {
    setBusy(true);
    try {
      await api(`/api/reschedule-requests/${id}/review/`, {
        method: 'POST',
        body: { status, comment },
      });
      await queryClient.invalidateQueries({
        queryKey: ['/api/reschedule-requests/'],
        exact: false,
      });
      toast(t('admin:requests.answered'));
    } catch {
      toast(t('common:errors.unknown'), 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ml-auto flex w-full flex-wrap gap-2 sm:w-auto">
      <input
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={500}
        aria-label={t('admin:requests.comment')}
        placeholder={t('admin:requests.comment')}
        className="min-h-touch min-w-0 flex-1 rounded-button border border-line bg-card px-3 text-sm text-ink placeholder:text-ink-muted sm:w-48"
      />
      <Button
        variant="secondary"
        disabled={busy}
        icon={<X size={16} aria-hidden="true" />}
        onClick={() => send('rejected')}
      >
        {t('admin:requests.reject')}
      </Button>
      <Button
        disabled={busy}
        icon={<Check size={16} aria-hidden="true" />}
        onClick={() => send('approved')}
      >
        {t('admin:requests.approve')}
      </Button>
    </div>
  );
}
