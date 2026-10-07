/** Calendar-day helpers on ISO dates (YYYY-MM-DD), free of timezone shifts. */
export function parseISO(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function toISO(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function addDays(iso: string, days: number): string {
  const d = parseISO(iso);
  d.setDate(d.getDate() + days);
  return toISO(d);
}

/** Monday of the week containing the date. */
export function mondayOf(iso: string): string {
  const d = parseISO(iso);
  return addDays(iso, -((d.getDay() + 6) % 7));
}

export function weekdayOf(iso: string): number {
  return (parseISO(iso).getDay() + 6) % 7;
}

/** "HH:MM" of the current local time. */
export function clockTime(now = new Date()): string {
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
}
