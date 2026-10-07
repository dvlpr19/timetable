import { ChevronDown } from 'lucide-react';
import { forwardRef, useId } from 'react';
import type { SelectHTMLAttributes } from 'react';

import { cn } from '@/lib/cn';

export interface Option {
  value: string | number;
  label: string;
}

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Option[];
  placeholder?: string;
  hideLabel?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { label, options, placeholder, hideLabel, className = '', id, ...rest },
  ref,
) {
  const autoId = useId();
  const selectId = id ?? autoId;
  return (
    <div className={className}>
      {label && (
        <label
          htmlFor={selectId}
          className={cn('mb-2 block text-sm font-semibold text-ink', hideLabel && 'sr-only')}
        >
          {label}
        </label>
      )}
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          {...rest}
          className="min-h-touch w-full appearance-none rounded-button border border-line bg-card py-2.5 pl-4 pr-10 text-base text-ink focus:border-primary-500"
        >
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown
          size={18}
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-muted"
        />
      </div>
    </div>
  );
});
