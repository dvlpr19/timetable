import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

export function Pill({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-bold',
        className,
      )}
    >
      {children}
    </span>
  );
}
