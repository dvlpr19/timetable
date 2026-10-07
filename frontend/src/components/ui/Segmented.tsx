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
      className="inline-flex flex-wrap gap-1 rounded-button bg-subtle p-1"
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={o.value === value}
          onClick={() => onChange(o.value)}
          className={cn(
            'min-h-[36px] rounded-[10px] px-3 text-sm font-semibold transition-colors',
            o.value === value ? 'bg-card text-ink shadow-sm' : 'text-ink-muted hover:text-ink',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
