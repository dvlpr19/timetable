import { BookOpen, CalendarDays, DoorOpen, GraduationCap, Layers, Users } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { Pill } from '@/components/ui/Pill';
import { Skeleton } from '@/components/ui/States';
import { lessonTypeClasses } from '@/lib/lessonTypes';
import { useApi } from '@/lib/query';

type Stats =
  | { kind: 'staff'; groups: number; teachers: number; rooms: number }
  | {
      kind: 'person';
      schedule: string | null;
      lessons?: number;
      days?: number;
      subjects?: number;
      teachers?: number;
      groups?: number;
      by_type?: { code: string; name: string; count: number }[];
    };

/** White tiles with the numbers behind the account: my lessons, or what my scope holds. */
export function StatsTiles() {
  const { t } = useTranslation(['common']);
  const { user } = useAuth();
  const { data, isLoading } = useApi<Stats>('/api/my-stats/');
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-32 rounded-tile" />
        ))}
      </div>
    );
  }
  if (!data || (data.kind === 'person' && !data.schedule)) return null;

  const tiles: { icon: LucideIcon; label: string; value: number }[] =
    data.kind === 'staff'
      ? [
          { icon: Users, label: t('common:stats.groups'), value: data.groups },
          { icon: GraduationCap, label: t('common:stats.teachers'), value: data.teachers },
          { icon: DoorOpen, label: t('common:stats.rooms'), value: data.rooms },
        ].filter((x) => x.value > 0)
      : [
          { icon: Layers, label: t('common:stats.lessons'), value: data.lessons ?? 0 },
          { icon: BookOpen, label: t('common:stats.subjects'), value: data.subjects ?? 0 },
          user?.teacher
            ? { icon: Users, label: t('common:stats.groups'), value: data.groups ?? 0 }
            : { icon: GraduationCap, label: t('common:stats.teachers'), value: data.teachers ?? 0 },
          { icon: CalendarDays, label: t('common:stats.days'), value: data.days ?? 0 },
        ];

  return (
    <section aria-label={t('common:stats.title')} className="space-y-3">
      <h2 className="text-lg font-bold text-ink">
        {data.kind === 'staff' ? t('common:stats.scope') : t('common:stats.title')}
      </h2>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {tiles.map(({ icon: Icon, label, value }) => (
          <li
            key={label}
            className="rounded-tile bg-card p-4 shadow-soft dark:border dark:border-line"
          >
            <Icon size={26} strokeWidth={1.75} aria-hidden="true" className="text-accent" />
            <p className="mt-3 text-2xl font-extrabold text-ink">{value}</p>
            <p className="text-sm font-semibold text-ink-muted">{label}</p>
          </li>
        ))}
      </ul>
      {data.kind === 'person' && data.by_type && data.by_type.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {data.by_type.map((lt) => (
            <li key={lt.code}>
              <Pill className={lessonTypeClasses(lt.code).pill}>
                {lt.name}: {lt.count}
              </Pill>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
