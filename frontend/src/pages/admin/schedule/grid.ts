/**
 * Pure helpers for the timetable grid: which days are shown, which lessons sit in a cell,
 * and which cells are closed by a blocked period (Friday prayer).
 */
import { weekdayIndex } from '@/i18n/date';
import type { BlockedPeriod, EducationForm, TimetableEntry } from '@/types/timetable';

export interface Day {
  key: string;
  weekday: number;
  date?: string; // ISO date for session (sirtqi) forms
}

export interface TeachingPeriod {
  id: number;
  label: string;
  form: number;
  start_date: string;
  end_date: string;
}

type LessonTime = EducationForm['lesson_times'][number];

/** Parse an ISO date as a local calendar day (no timezone shift). */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function isoDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function weeklyDays(form: EducationForm): Day[] {
  return [...form.study_weekdays]
    .sort((a, b) => a - b)
    .map((wd) => ({ key: `w:${wd}`, weekday: wd }));
}

/** Study days of a session period, e.g. every Monday–Saturday between its start and end. */
export function sessionDays(form: EducationForm, period: TeachingPeriod): Day[] {
  const days: Day[] = [];
  const end = parseDate(period.end_date);
  for (let d = parseDate(period.start_date); d <= end; d.setDate(d.getDate() + 1)) {
    const wd = weekdayIndex(d);
    if (form.study_weekdays.includes(wd))
      days.push({ key: `d:${isoDate(d)}`, weekday: wd, date: isoDate(d) });
  }
  return days;
}

export function sortedTimes(form: EducationForm): LessonTime[] {
  return [...form.lesson_times].sort((a, b) => a.number - b.number);
}

/** Lessons of one cell; odd/even week lessons share a weekly cell. */
export function entriesAt(
  entries: TimetableEntry[],
  day: Day,
  lessonTimeId: number,
): TimetableEntry[] {
  return entries
    .filter(
      (e) =>
        e.lesson_time.id === lessonTimeId &&
        (day.date ? e.date === day.date : e.date === null && e.weekday === day.weekday),
    )
    .sort((a, b) => parityOrder(a.week_parity) - parityOrder(b.week_parity));
}

function parityOrder(parity: TimetableEntry['week_parity']): number {
  return parity === 'odd' ? 1 : parity === 'even' ? 2 : 0;
}

const hhmm = (time: string) => time.slice(0, 5);

/** The hard blocked period that overlaps this lesson time on this day, if any. */
export function blockedAt(
  blocked: BlockedPeriod[],
  form: EducationForm,
  day: Day,
  time: LessonTime,
): BlockedPeriod | undefined {
  return blocked.find(
    (b) =>
      b.is_hard &&
      (b.form === null || b.form === form.id) &&
      (b.weekday === null || b.weekday === day.weekday) &&
      hhmm(b.start) < hhmm(time.end) &&
      hhmm(time.start) < hhmm(b.end),
  );
}
