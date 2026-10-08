import { describe, expect, it } from 'vitest';

import type { BlockedPeriod, EducationForm, GridCell, TimetableEntry } from '@/types/timetable';

import { blockedAt, entriesAt, pickBestCell, sessionDays, weeklyDays } from './grid';

const form: EducationForm = {
  id: 1,
  code: 'kunduzgi',
  name: 'Kunduzgi',
  schedule_mode: 'weekly',
  requires_room: true,
  study_weekdays: [5, 0, 1, 2, 3, 4],
  lesson_times: [
    { id: 11, form: 1, number: 1, start: '08:30:00', end: '09:50:00', shift: 1 },
    { id: 13, form: 1, number: 3, start: '11:30:00', end: '12:50:00', shift: 1 },
    { id: 14, form: 1, number: 4, start: '13:00:00', end: '14:20:00', shift: 2 },
  ],
};

const friday: BlockedPeriod = {
  id: 1,
  name: 'Juma namozi',
  weekday: 4,
  start: '12:00:00',
  end: '14:00:00',
  form: null,
  is_hard: true,
};

function entry(over: Partial<TimetableEntry>): TimetableEntry {
  return {
    id: 1,
    schedule: 1,
    assignment: 1,
    weekday: 1,
    week_parity: 'every',
    date: null,
    lesson_time: { id: 11, number: 1, start: '08:30', end: '09:50', shift: 1 },
    form: 'kunduzgi',
    subject: { id: 1, name: 'Fiqh' },
    lesson_type: { code: 'lecture', name: "Ma'ruza" },
    teacher: { id: 1, short_name: 'A. Karimov', full_name: 'Karimov Anvar' },
    groups: [{ id: 1, name: 'IS-301' }],
    subgroup: null,
    stream: null,
    student_count: 25,
    room: null,
    online_url: '',
    is_locked: false,
    note: '',
    ...over,
  };
}

describe('timetable grid helpers', () => {
  it('lists study weekdays in order', () => {
    expect(weeklyDays(form).map((d) => d.weekday)).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it('expands a session period into study dates', () => {
    const days = sessionDays(
      { ...form, study_weekdays: [0, 1, 2, 3, 4, 5] },
      { id: 1, label: 'Sessiya', form: 1, start_date: '2026-04-11', end_date: '2026-04-14' },
    );
    // 11 April 2026 is a Saturday, 12 April a Sunday (not a study day).
    expect(days.map((d) => d.date)).toEqual(['2026-04-11', '2026-04-13', '2026-04-14']);
    expect(days[0].weekday).toBe(5);
  });

  it('puts odd and even week lessons in the same weekly cell, odd first', () => {
    const list = [
      entry({ id: 2, week_parity: 'even' }),
      entry({ id: 3, week_parity: 'odd' }),
      entry({ id: 4, weekday: 2 }),
      entry({ id: 5, weekday: null, date: '2026-04-14' }),
    ];
    expect(entriesAt(list, { key: 'w:1', weekday: 1 }, 11).map((e) => e.id)).toEqual([3, 2]);
    expect(
      entriesAt(list, { key: 'd:2026-04-14', weekday: 1, date: '2026-04-14' }, 11).map((e) => e.id),
    ).toEqual([5]);
  });

  it('closes Friday lessons that overlap the prayer time only', () => {
    const fri = { key: 'w:4', weekday: 4 };
    const [first, third, fourth] = form.lesson_times;
    expect(blockedAt([friday], form, fri, first)).toBeUndefined();
    expect(blockedAt([friday], form, fri, third)?.name).toBe('Juma namozi');
    expect(blockedAt([friday], form, fri, fourth)?.name).toBe('Juma namozi');
    expect(blockedAt([friday], form, { key: 'w:3', weekday: 3 }, third)).toBeUndefined();
    expect(blockedAt([{ ...friday, is_hard: false }], form, fri, third)).toBeUndefined();
  });
});

describe('pickBestCell', () => {
  const cell = (weekday: number, number: number, ok = true): GridCell => ({
    weekday,
    lesson_time: number,
    number,
    ok,
    room: 1,
    free_rooms: [1],
    reasons: [],
  });
  const lesson = (weekday: number, subject: string) => ({
    weekday,
    date: null,
    subject: { id: 1, name: subject },
  });

  it('skips busy cells and prefers the earliest lesson', () => {
    expect(pickBestCell([cell(0, 1, false), cell(0, 3), cell(0, 2)], [])).toMatchObject({
      weekday: 0,
      number: 2,
    });
  });

  it('spreads lessons to the least busy day without the same subject', () => {
    const entries = [lesson(0, 'Fiqh'), lesson(1, 'Arab tili'), lesson(1, 'Tarix')];
    expect(pickBestCell([cell(0, 2), cell(1, 1), cell(2, 4)], entries, 'Fiqh')).toMatchObject({
      weekday: 2,
    });
    expect(pickBestCell([cell(0, 2), cell(1, 1)], entries, 'Fiqh')).toMatchObject({ weekday: 1 });
  });

  it('returns nothing when no cell is free', () => {
    expect(pickBestCell([cell(0, 1, false)], [])).toBeUndefined();
  });
});
