import { useQueryClient } from '@tanstack/react-query';
import { CalendarClock, Clock, ExternalLink, MapPin, Send, UserRound, Users } from 'lucide-react';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Pill } from '@/components/ui/Pill';
import { Segmented } from '@/components/ui/Segmented';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { formatLongDate } from '@/i18n/date';
import { ApiError, api } from '@/lib/api';
import { parseISO } from '@/lib/dates';
import { lessonTypeClasses } from '@/lib/lessonTypes';
import { needsLink } from '@/lib/links';
import { useAll } from '@/lib/query';
import type { EducationForm, Occurrence } from '@/types/timetable';

interface Props {
  lesson: Occurrence;
  /** teachers can ask the dispatcher to move their own lesson */
  canRequest: boolean;
  onClose: () => void;
}

/** Everything about one lesson; for the teacher also "ask to move it". */
export function LessonSheet({ lesson, canRequest, onClose }: Props) {
  const { t } = useTranslation(['app', 'dates', 'common']);
  const [asking, setAsking] = useState(false);
  const colors = lessonTypeClasses(lesson.lesson_type.code);
  const date = lesson.date ? formatLongDate(parseISO(lesson.date), t) : '';
  const room = lesson.room;

  return (
    <Modal open variant="sheet" title={lesson.subject.name} onClose={onClose}>
      {asking ? (
        <RequestForm lesson={lesson} onDone={onClose} onBack={() => setAsking(false)} />
      ) : (
        <div className="space-y-5 pb-2">
          <div className="flex flex-wrap gap-2">
            <Pill className={colors.pill}>{lesson.lesson_type.name}</Pill>
            {lesson.status === 'cancelled' && (
              <Pill className="bg-danger-bg text-danger-fg">{t('app:lesson.cancelled')}</Pill>
            )}
            {lesson.status === 'reschedule' && (
              <Pill className="bg-warning-bg text-warning-fg">{t('app:lesson.holidayLong')}</Pill>
            )}
          </div>
          <ul className="space-y-4 text-base">
            <Row icon={<Clock size={20} />} label={t('app:lesson.when')}>
              <span className="first-letter:uppercase">{date}</span>
              <span className="block text-sm text-ink-muted">
                {t('app:lesson.numberTime', {
                  n: lesson.lesson_time.number,
                  start: lesson.lesson_time.start,
                  end: lesson.lesson_time.end,
                })}
              </span>
            </Row>
            <Row icon={<MapPin size={20} />} label={t('app:lesson.where')}>
              {room ? (
                <>
                  {room.name}
                  <span className="block text-sm text-ink-muted">
                    {t('app:lesson.building', { building: room.building, floor: room.floor })}
                  </span>
                </>
              ) : needsLink(lesson.online_url) ? (
                <span className="text-ink-muted">{t('app:lesson.linkSoonLong')}</span>
              ) : (
                <a
                  href={lesson.online_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex min-h-touch items-center gap-2 rounded-button bg-primary-700 px-4 font-semibold text-ink-on-primary"
                >
                  <ExternalLink size={18} aria-hidden="true" />
                  {t('app:lesson.join')}
                </a>
              )}
            </Row>
            <Row icon={<UserRound size={20} />} label={t('app:lesson.teacher')}>
              {lesson.teacher.full_name}
            </Row>
            <Row icon={<Users size={20} />} label={t('app:lesson.groups')}>
              {lesson.stream ? `${lesson.stream}: ` : ''}
              {lesson.groups.map((g) => g.name).join(', ')}
              {lesson.subgroup ? ` · ${t('app:lesson.subgroup', { n: lesson.subgroup })}` : ''}
              <span className="block text-sm text-ink-muted">
                {t('app:lesson.students', { n: lesson.student_count })}
              </span>
            </Row>
          </ul>
          {lesson.note && (
            <p className="rounded-button bg-subtle p-3 text-sm text-ink">{lesson.note}</p>
          )}
          {canRequest && lesson.status === 'scheduled' && (
            <Button
              variant="secondary"
              block
              icon={<CalendarClock size={18} aria-hidden="true" />}
              onClick={() => setAsking(true)}
            >
              {t('app:request.ask')}
            </Button>
          )}
        </div>
      )}
    </Modal>
  );
}

function Row({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <li className="flex gap-3">
      <span aria-hidden="true" className="mt-0.5 text-primary-700">
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-xs font-semibold uppercase tracking-wide text-ink-muted">
          {label}
        </span>
        <span className="block text-ink">{children}</span>
      </span>
    </li>
  );
}

function RequestForm({
  lesson,
  onDone,
  onBack,
}: {
  lesson: Occurrence;
  onDone: () => void;
  onBack: () => void;
}) {
  const { t } = useTranslation(['app', 'dates', 'common']);
  const toast = useToast();
  const queryClient = useQueryClient();
  const forms = useAll<EducationForm>('/api/education-forms/');
  const form = forms.rows.find((f) => f.code === lesson.form);
  const weekdays = t('dates:weekdays', { returnObjects: true }) as string[];
  const [scope, setScope] = useState<'once' | 'weekly'>('once');
  const [reason, setReason] = useState('');
  const [weekday, setWeekday] = useState('');
  const [time, setTime] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!reason.trim()) {
      setError(t('app:request.reasonRequired'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api('/api/reschedule-requests/', {
        method: 'POST',
        body: {
          entry: lesson.id,
          occurrence_date: scope === 'once' ? lesson.date : null,
          reason: reason.trim(),
          desired_weekday: weekday === '' ? null : Number(weekday),
          desired_lesson_time: time === '' ? null : Number(time),
          desired_note: note.trim(),
        },
      });
      await queryClient.invalidateQueries({ queryKey: ['/api/reschedule-requests/'] });
      toast(t('app:request.sent'));
      onDone();
    } catch (err) {
      setError(err instanceof ApiError && err.detail ? err.detail : t('common:errors.unknown'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      noValidate
      className="space-y-4 pb-2"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <p className="text-sm text-ink-muted">{t('app:request.hint')}</p>
      {error && (
        <p role="alert" className="rounded-button bg-danger-bg px-4 py-3 text-sm text-danger-fg">
          {error}
        </p>
      )}
      <div>
        <p className="mb-2 text-sm font-semibold text-ink">{t('app:request.which')}</p>
        <Segmented
          label={t('app:request.which')}
          value={scope}
          onChange={setScope}
          options={[
            { value: 'once', label: t('app:request.once') },
            { value: 'weekly', label: t('app:request.weekly') },
          ]}
        />
      </div>
      <div>
        <label htmlFor="request-reason" className="mb-2 block text-sm font-semibold text-ink">
          {t('app:request.reason')} *
        </label>
        <textarea
          id="request-reason"
          rows={3}
          maxLength={1000}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder={t('app:request.reasonPlaceholder')}
          className="w-full rounded-button border border-line bg-card px-4 py-3 text-base text-ink placeholder:text-ink-muted"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Select
          label={t('app:request.day')}
          value={weekday}
          onChange={(e) => setWeekday(e.target.value)}
          placeholder={t('app:request.any')}
          options={(form?.study_weekdays ?? [0, 1, 2, 3, 4, 5]).map((d) => ({
            value: d,
            label: weekdays[d],
          }))}
        />
        <Select
          label={t('app:request.time')}
          value={time}
          onChange={(e) => setTime(e.target.value)}
          placeholder={t('app:request.any')}
          options={(form?.lesson_times ?? []).map((lt) => ({
            value: lt.id,
            label: `${lt.number} · ${lt.start.slice(0, 5)}`,
          }))}
        />
      </div>
      <div>
        <label htmlFor="request-note" className="mb-2 block text-sm font-semibold text-ink">
          {t('app:request.note')}
        </label>
        <input
          id="request-note"
          value={note}
          maxLength={255}
          onChange={(e) => setNote(e.target.value)}
          className="min-h-touch w-full rounded-button border border-line bg-card px-4 text-base text-ink"
        />
      </div>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onBack}>
          {t('app:request.back')}
        </Button>
        <Button
          type="submit"
          className="flex-1"
          disabled={busy}
          icon={<Send size={18} aria-hidden="true" />}
        >
          {t('app:request.send')}
        </Button>
      </div>
    </form>
  );
}
