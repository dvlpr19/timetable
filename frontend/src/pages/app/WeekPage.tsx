import { CalendarRange } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { ScreenHeader } from '@/components/ScreenHeader';
import { useToday } from '@/lib/clock';
import { mondayOf, parseISO } from '@/lib/dates';
import { useAll } from '@/lib/query';
import type { EducationForm } from '@/types/timetable';
import { formatDayMonth } from '@/i18n/date';

import { WeekView } from './lessons/WeekView';

interface Period {
  id: number;
  form: number;
  start_date: string;
  end_date: string;
  weeks_count: number | null;
}

/**
 * "Hafta" / "Mening haftam". Part-time (sirtqi) students study in sessions, so the view
 * opens on the session and says when it is.
 */
export function WeekPage() {
  const { t } = useTranslation(['app', 'dates']);
  const { user } = useAuth();
  const { today, ready } = useToday();
  const teacher = user?.role === 'oqituvchi';
  const sirtqi = user?.student?.form === 'sirtqi';
  const forms = useAll<EducationForm>(sirtqi ? '/api/education-forms/' : null);
  const formId = forms.rows.find((f) => f.code === 'sirtqi')?.id;
  const periods = useAll<Period>(formId ? '/api/teaching-periods/' : null, { form: formId });
  const session = periods.rows
    .filter((p) => !p.weeks_count)
    .sort((a, b) => a.start_date.localeCompare(b.start_date))
    .find((p) => p.end_date >= today);
  const inSession = session && session.start_date <= today;
  const start = session && !inSession ? mondayOf(session.start_date) : undefined;

  if (!ready || (sirtqi && (forms.isLoading || periods.isLoading))) return null;
  return (
    <>
      <ScreenHeader
        title={teacher ? t('app:tabs.myWeek') : t('app:tabs.week')}
        subtitle={user?.student?.group.name ?? user?.teacher?.short_name}
      />
      <div className="px-4 py-5 sm:px-6">
        <WeekView
          key={start ?? 'now'}
          target={{ me: 1 }}
          viewer={teacher ? 'teacher' : 'student'}
          today={today}
          startMonday={start}
          canRequest={teacher}
          note={
            session && (
              <p className="flex items-center gap-2 rounded-button bg-lesson-seminar-bg px-3 py-2 text-sm text-ink">
                <CalendarRange size={16} aria-hidden="true" className="text-lesson-seminar" />
                {t(inSession ? 'app:week.sessionNow' : 'app:week.sessionNext', {
                  from: formatDayMonth(parseISO(session.start_date), t),
                  to: formatDayMonth(parseISO(session.end_date), t),
                })}
              </p>
            )
          }
        />
      </div>
    </>
  );
}
