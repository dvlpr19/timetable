import { AlertCircle, AlertTriangle, Info } from 'lucide-react';

import { cn } from '@/lib/cn';
import type { Diagnostic } from '@/types/solver';

const STYLE = {
  error: { icon: AlertCircle, cls: 'bg-danger-bg text-danger-fg' },
  warning: { icon: AlertTriangle, cls: 'bg-warning-bg text-warning-fg' },
  info: { icon: Info, cls: 'bg-card text-ink-muted' },
};

const ORDER = { error: 0, warning: 1, info: 2 };

/** Solver messages, errors first. */
export function DiagnosticList({ items }: { items: Diagnostic[] }) {
  const sorted = [...items].sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);
  return (
    <ul className="max-h-80 space-y-2 overflow-y-auto">
      {sorted.map((d, i) => {
        const { icon: Icon, cls } = STYLE[d.severity];
        return (
          <li key={i} className={cn('flex gap-2 rounded-button p-3 text-sm', cls)}>
            <Icon size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
            <span>{d.message}</span>
          </li>
        );
      })}
    </ul>
  );
}
