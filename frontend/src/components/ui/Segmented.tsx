import { cn } from '@/lib/cn';

interface Props<T extends string> {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}

/** A row of toggle buttons (one choice). */
export function Segmented<T extends string>({ label, value, options, onChange }: Props<T>) {
  return (
    <div
      role="group"
      aria-label={label}
      className="inline-flex flex-wrap gap-1 rounded-full bg-card p-1 shadow-soft dark:border dark:border-line"
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={o.value === value}
          onClick={() => onChange(o.value)}
          className={cn(
            'min-h-[36px] rounded-full px-4 text-sm font-semibold transition-colors',
            o.value === value
              ? 'bg-primary-700 text-ink-on-primary'
              : 'text-ink-muted hover:bg-subtle hover:text-ink',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
