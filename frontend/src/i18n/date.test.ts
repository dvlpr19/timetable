import { describe, expect, it } from 'vitest';

import i18n from '@/i18n';

import { formatDayMonth, formatDayMonthTime, formatLongDate } from './date';

describe('formatLongDate', () => {
  const thursday = new Date(2026, 3, 9); // 9 April 2026

  it.each([
    ['uz', '9-aprel, payshanba'],
    ['ru', '9 апреля, четверг'],
    ['en', 'Thursday, 9 April'],
  ])('formats in %s', async (lng, expected) => {
    await i18n.changeLanguage(lng);
    expect(formatLongDate(thursday, i18n.t)).toBe(expected);
  });
});

describe('formatDayMonth / formatDayMonthTime', () => {
  const morning = new Date(2026, 3, 9, 8, 5);

  it.each([
    ['uz', '9-aprel', '9-aprel, 08:05'],
    ['ru', '9 апреля', '9 апреля, 08:05'],
    ['en', '9 April', '9 April, 08:05'],
  ])('formats in %s', async (lng, day, withTime) => {
    await i18n.changeLanguage(lng);
    expect(formatDayMonth(morning, i18n.t)).toBe(day);
    expect(formatDayMonthTime(morning, i18n.t)).toBe(withTime);
  });
});
