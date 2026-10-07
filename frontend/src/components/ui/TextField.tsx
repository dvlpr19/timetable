import { forwardRef, useId } from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  trailing?: ReactNode;
}

export const TextField = forwardRef<HTMLInputElement, Props>(function TextField(
  { label, trailing, className = '', id, ...rest },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-2 block text-sm font-semibold text-ink">
        {label}
      </label>
      <div className="flex min-h-touch items-center rounded-button border border-line bg-card focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/30">
        <input
          ref={ref}
          id={inputId}
          {...rest}
          className="w-full min-w-0 flex-1 bg-transparent px-4 py-3 text-base text-ink placeholder:text-ink-muted focus:outline-none focus-visible:ring-0"
        />
        {trailing}
      </div>
    </div>
  );
});
