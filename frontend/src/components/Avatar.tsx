import { cn } from '@/lib/cn';

const SIZES = {
  sm: 'h-9 w-9 text-sm',
  lg: 'h-16 w-16 text-xl',
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
  className,
}: {
  name: string;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full bg-primary-700 font-extrabold text-ink-on-primary',
        SIZES[size],
        className,
      )}
    >
      {initials(name) || '?'}
    </span>
  );
}
