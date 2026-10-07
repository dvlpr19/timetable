import { DoorOpen, Monitor, Projector, Users } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ScreenHeader } from '@/components/ScreenHeader';
import { Select } from '@/components/ui/Select';
import { EmptyState, ErrorState, LoadingRows } from '@/components/ui/States';
import { TextField } from '@/components/ui/TextField';
import { useToday } from '@/lib/clock';
import { useAll, useApi } from '@/lib/query';
import type { EducationForm } from '@/types/timetable';

interface FreeRoom {
  id: number;
  name: string;
  building: string;
  floor: number;
  capacity: number;
  room_type: string;
  has_projector: boolean;
  computer_count: number;
}

const CAPACITIES = [0, 15, 30, 50, 100];

/** Find a room that is free at a given date and lesson (published timetable). */
export function FreeRoomsPage() {
  const { t } = useTranslation(['app']);
  const { today } = useToday();
  const forms = useAll<EducationForm>('/api/education-forms/');
  const [date, setDate] = useState<string | null>(null);
  const [lessonTime, setLessonTime] = useState<string>('');
  const [capacity, setCapacity] = useState(0);
  const day = date ?? today;
  const times = forms.rows
    .filter((f) => f.requires_room)
    .flatMap((f) =>
      [...f.lesson_times]
        .sort((a, b) => a.number - b.number)
        .map((lt) => ({ ...lt, formName: f.name })),
    );
  const chosen = lessonTime || (times[0] ? String(times[0].id) : '');
  const rooms = useApi<FreeRoom[]>(chosen ? '/api/free-rooms/' : null, {
    date: day,
    lesson_time: chosen,
    capacity,
  });

  return (
    <>
      <ScreenHeader title={t('app:rooms.title')} subtitle={t('app:rooms.subtitle')} />
      <div className="space-y-4 px-4 py-5 sm:px-6">
        <div className="grid gap-3 rounded-card border border-line bg-card p-4 sm:grid-cols-3">
          <TextField
            label={t('app:rooms.date')}
            type="date"
            value={day}
            onChange={(e) => setDate(e.target.value || null)}
          />
          <Select
            label={t('app:rooms.time')}
            value={chosen}
            onChange={(e) => setLessonTime(e.target.value)}
            options={times.map((lt) => ({
              value: lt.id,
              label: `${lt.formName}: ${lt.number} · ${lt.start.slice(0, 5)}–${lt.end.slice(0, 5)}`,
            }))}
          />
          <Select
            label={t('app:rooms.capacity')}
            value={capacity}
            onChange={(e) => setCapacity(Number(e.target.value))}
            options={CAPACITIES.map((n) => ({
              value: n,
              label: n ? t('app:rooms.atLeast', { n }) : t('app:rooms.any'),
            }))}
          />
        </div>
        {rooms.isError ? (
          <ErrorState onRetry={() => rooms.refetch()} />
        ) : rooms.isLoading || forms.isLoading ? (
          <LoadingRows rows={4} />
        ) : !rooms.data?.length ? (
          <EmptyState title={t('app:rooms.none')} />
        ) : (
          <>
            <p className="text-sm font-semibold text-ink">
              {t('app:rooms.found', { n: rooms.data.length })}
            </p>
            <ul className="space-y-2">
              {rooms.data.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center gap-3 rounded-card border border-line bg-card p-3"
                >
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-button bg-lesson-lecture-bg text-lesson-lecture">
                    <DoorOpen size={20} aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-bold text-ink">{r.name}</span>
                    <span className="block text-sm text-ink-muted">
                      {t('app:lesson.building', { building: r.building, floor: r.floor })} ·{' '}
                      {r.room_type}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2 text-sm text-ink-muted">
                    <span className="inline-flex items-center gap-1" title={t('app:rooms.seats')}>
                      <Users size={14} aria-hidden="true" />
                      <span className="sr-only">{t('app:rooms.seats')}</span>
                      {r.capacity}
                    </span>
                    {r.has_projector && (
                      <Projector size={16} aria-label={t('app:rooms.projector')} />
                    )}
                    {r.computer_count > 0 && (
                      <Monitor
                        size={16}
                        aria-label={t('app:rooms.computers', { n: r.computer_count })}
                      />
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </>
  );
}
