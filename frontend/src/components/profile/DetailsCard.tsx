import type { LucideIcon } from 'lucide-react';

import { Card } from '@/components/ui/Card';

export interface Detail {
  icon: LucideIcon;
  label: string;
  value: string | number | null | undefined;
}

/** A titled card of label / value rows, each with a blue line icon. Empty values are skipped. */
export function DetailsCard({ title, items }: { title: string; items: Detail[] }) {
  const shown = items.filter((d) => d.value !== null && d.value !== undefined && d.value !== '');
  if (!shown.length) return null;
  return (
    <Card className="p-5">
      <h2 className="text-lg font-bold text-ink">{title}</h2>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        {shown.map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex items-start gap-3 rounded-2xl bg-subtle/60 p-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-card text-accent shadow-soft">
              <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <dt className="text-xs font-semibold text-ink-muted">{label}</dt>
              <dd className="mt-0.5 break-words font-bold text-ink">{value}</dd>
            </div>
          </div>
        ))}
      </dl>
    </Card>
  );
}
