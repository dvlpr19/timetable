import {
  AlertTriangle,
  CalendarCheck,
  CalendarClock,
  DoorOpen,
  UserSquare,
  Users,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/ui/Card';
import { Segmented } from '@/components/ui/Segmented';
import { ErrorState, Skeleton } from '@/components/ui/States';
import { cn } from '@/lib/cn';
import { useApi } from '@/lib/query';
import type { Violation } from '@/types/timetable';

interface Dashboard {
  schedule: { id: number; name: string; status: string };
  groups: number;
  teachers: number;
  rooms: number;
  lessons_placed: number;
  lessons_unplaced: number;
  conflict_count: number;
  conflicts: Violation[];
  faculties: { id: number; name: string; placed: number; required: number; percent: number }[];
}

const FORMS = ['', 'kunduzgi', 'kechki', 'sirtqi', 'masofaviy'] as const;
type FormFilter = (typeof FORMS)[number];

export function DashboardPage() {
  const { t } = useTranslation(['admin', 'common']);
  const [form, setForm] = useState<FormFilter>('');
  const { data, isLoading, isError, refetch } = useApi<Dashboard>('/api/dashboard/', { form });

  const stats = data
    ? [
        { icon: Users, label: t('admin:dashboard.groups'), value: data.groups },
        { icon: UserSquare, label: t('admin:dashboard.teachers'), value: data.teachers },
        { icon: DoorOpen, label: t('admin:dashboard.rooms'), value: data.rooms },
        { icon: CalendarCheck, label: t('admin:dashboard.placed'), value: data.lessons_placed },
        {
          icon: CalendarClock,
          label: t('admin:dashboard.unplaced'),
          value: data.lessons_unplaced,
          warn: data.lessons_unplaced > 0,
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-ink">{t('admin:dashboard.title')}</h1>
          {data && (
            <p className="mt-1 text-sm text-ink-muted">
              {data.schedule.name} · {t(`admin:status.${data.schedule.status}`)}
            </p>
          )}
        </div>
        <Segmented
          label={t('admin:dashboard.formFilter')}
          value={form}
          onChange={setForm}
          options={FORMS.map((f) => ({ value: f, label: t(`admin:forms.${f || 'all'}`) }))}
        />
      </div>

      {isError ? (
        <ErrorState onRetry={() => refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
            {isLoading
              ? Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-28" />)
              : stats.map(({ icon: Icon, label, value, warn }) => (
                  <Card key={label} className="p-4">
                    <Icon
                      size={22}
                      aria-hidden="true"
                      className={warn ? 'text-warning-fg' : 'text-primary-700'}
                    />
                    <p className="mt-3 text-3xl font-extrabold text-ink">{value}</p>
                    <p className="text-sm text-ink-muted">{label}</p>
                  </Card>
                ))}
          </div>
          <p className="text-xs text-ink-muted">{t('admin:dashboard.unitsNote')}</p>

          <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
            <Card className="p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-bold text-ink">{t('admin:dashboard.conflicts')}</h2>
                {data && (
                  <span
                    className={cn(
                      'rounded-full px-3 py-1 text-sm font-bold',
                      data.conflict_count
                        ? 'bg-danger-bg text-danger-fg'
                        : 'bg-lesson-lecture-bg text-lesson-lecture',
                    )}
                  >
                    {data.conflict_count}
                  </span>
                )}
              </div>
              {isLoading ? (
                <Skeleton className="mt-4 h-24" />
              ) : data && data.conflicts.length > 0 ? (
                <ul className="mt-4 space-y-2">
                  {data.conflicts.map((c, i) => (
                    <li
                      key={i}
                      className="flex gap-3 rounded-button bg-danger-bg p-3 text-sm text-danger-fg"
                    >
                      <AlertTriangle size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
                      <span>
                        <span className="font-bold">
                          {t('admin:dashboard.constraint', { n: c.constraint })}:{' '}
                        </span>
                        {c.message}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-4 rounded-button bg-subtle p-4 text-sm text-ink-muted">
                  {t('admin:dashboard.noConflicts')}
                </p>
              )}
            </Card>

            <Card className="p-5">
              <h2 className="text-lg font-bold text-ink">{t('admin:dashboard.readiness')}</h2>
              <ul className="mt-4 space-y-4">
                {isLoading && <Skeleton className="h-16" />}
                {data?.faculties.map((f) => (
                  <li key={f.id}>
                    <div className="flex items-baseline justify-between gap-2 text-sm">
                      <span className="font-semibold text-ink">{f.name}</span>
                      <span className="font-bold text-ink">{f.percent}%</span>
                    </div>
                    <div
                      role="progressbar"
                      aria-label={f.name}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={f.percent}
                      className="mt-2 h-2 overflow-hidden rounded-full bg-subtle"
                    >
                      <div
                        className="h-2 rounded-full bg-primary-500"
                        style={{ width: `${f.percent}%` }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-ink-muted">
                      {t('admin:dashboard.placedOf', { placed: f.placed, required: f.required })}
                    </p>
                  </li>
                ))}
              </ul>
              <Link
                to="/admin/schedule"
                className="mt-6 inline-flex min-h-touch items-center text-sm font-bold text-link hover:underline"
              >
                {t('admin:dashboard.openEditor')}
              </Link>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
