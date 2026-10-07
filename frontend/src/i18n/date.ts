import type { TFunction } from 'i18next';

/** Monday-based weekday index (0 = Monday … 6 = Sunday). */
export function weekdayIndex(date: Date): number {
  return (date.getDay() + 6) % 7;
}

/** "9-aprel, payshanba" / "9 апреля, четверг" / "Thursday, 9 April" */
export function formatLongDate(date: Date, t: TFunction): string {
  const months = t('dates:monthsGenitive', { returnObjects: true }) as string[];
  const weekdays = t('dates:weekdays', { returnObjects: true }) as string[];
  return t('dates:longDate', {
    day: date.getDate(),
    month: months[date.getMonth()],
    weekday: weekdays[weekdayIndex(date)],
  });
}

/** "9-aprel" / "9 апреля" / "9 April" (browsers lack Uzbek month names in Intl). */
export function formatDayMonth(date: Date, t: TFunction): string {
  const months = t('dates:monthsGenitive', { returnObjects: true }) as string[];
  return t('dates:dayMonth', { day: date.getDate(), month: months[date.getMonth()] });
}

/** "9-aprel, 10:42" */
export function formatDayMonthTime(date: Date, t: TFunction): string {
  const months = t('dates:monthsGenitive', { returnObjects: true }) as string[];
  const time = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
  return t('dates:dayMonthTime', { day: date.getDate(), month: months[date.getMonth()], time });
}
