import { CalendarDays } from 'lucide-react';

export function BrandMark({ className = '' }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex h-12 w-12 items-center justify-center rounded-button bg-primary-900 text-gold ${className}`}
    >
      <CalendarDays size={26} strokeWidth={2} />
    </span>
  );
}
