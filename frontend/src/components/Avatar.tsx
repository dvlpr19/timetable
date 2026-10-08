import { cn } from '@/lib/cn';

const SIZES = {
  sm: 'h-9 w-9 text-sm',
  lg: 'h-16 w-16 text-xl',
  xl: 'h-24 w-24 text-3xl',
};

const TONES = {
  primary: 'bg-primary-700 text-ink-on-primary',
  light: 'bg-white text-primary-700 shadow-lift',
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('');
}

/** Round badge with the person's initials. Decorative: the name is always shown next to it. */
export function Avatar({
  name,
  size = 'sm',
  tone = 'primary',
  className,
}: {
  name: string;
  size?: keyof typeof SIZES;
  tone?: keyof typeof TONES;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full font-extrabold',
        TONES[tone],
        SIZES[size],
        className,
      )}
    >
      {initials(name) || '?'}
    </span>
  );
}
