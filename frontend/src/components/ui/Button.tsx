import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  icon?: ReactNode;
  block?: boolean;
}

const variants: Record<Variant, string> = {
  primary: 'bg-primary-700 text-ink-on-primary shadow-soft hover:bg-primary-900',
  secondary: 'border border-line bg-card text-ink hover:border-primary-500/40 hover:bg-subtle',
  ghost: 'text-link hover:bg-subtle',
};

export function Button({
  variant = 'primary',
  icon,
  block,
  className = '',
  children,
  ...rest
}: Props) {
  return (
    <button
      type="button"
      {...rest}
      className={`inline-flex min-h-touch items-center justify-center gap-2 rounded-full px-5 py-2.5 text-base font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
        variants[variant]
      } ${block ? 'w-full' : ''} ${className}`}
    >
      {icon}
      {children}
    </button>
  );
}
