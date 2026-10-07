import { ArrowLeft, ChevronRight, Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import { ScreenHeader } from '@/components/ScreenHeader';
import { Segmented } from '@/components/ui/Segmented';
import { EmptyState, LoadingRows } from '@/components/ui/States';
import { useToday } from '@/lib/clock';
import { useApi } from '@/lib/query';
import type { Paginated } from '@/lib/query';

import { WeekView } from './lessons/WeekView';
import type { Target } from './lessons/useLessons';

type Kind = 'group' | 'teacher' | 'room';
type Row = {
  id: number;
  name?: string;
  full_name?: string;
  short_name?: string;
  building_name?: string;
  capacity?: number;
  department_name?: string;
  student_count?: number;
};

const PATHS: Record<Kind, string> = {
  group: '/api/groups/',
  teacher: '/api/teachers/',
  room: '/api/rooms/',
};

function title(kind: Kind, r: Row): string {
  return (kind === 'teacher' ? r.full_name : r.name) ?? String(r.id);
}

/** Find another group's, a teacher's or a room's timetable. */
export function SearchPage() {
  const { t } = useTranslation(['app']);
  const { today } = useToday();
  const [params, setParams] = useSearchParams();
  const kind = (
    ['group', 'teacher', 'room'].includes(params.get('type') ?? '') ? params.get('type') : 'group'
  ) as Kind;
  const id = Number(params.get('id')) || null;
  const [text, setText] = useState('');
  const [query, setQuery] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => setQuery(text.trim()), 250);
    return () => clearTimeout(timer);
  }, [text]);

  const list = useApi<Paginated<Row>>(id ? null : PATHS[kind], {
    search: query || undefined,
    page_size: 30,
  });
  const picked = useApi<Row>(id ? `${PATHS[kind]}${id}/` : null);

  if (id) {
    const target = { [kind]: id } as Target;
    const name = picked.data ? title(kind, picked.data) : '…';
    return (
      <>
        <ScreenHeader title={name} subtitle={t(`app:search.kinds.${kind}`)}>
          <button
            type="button"
            onClick={() => setParams({ type: kind })}
            className="mt-3 inline-flex min-h-touch items-center gap-2 rounded-button bg-white/10 px-3 text-sm font-semibold"
          >
            <ArrowLeft size={18} aria-hidden="true" />
            {t('app:search.back')}
          </button>
        </ScreenHeader>
        <div className="px-4 py-5 sm:px-6">
          <WeekView
            target={target}
            viewer={kind === 'teacher' ? 'teacher' : 'student'}
            today={today}
          />
        </div>
      </>
    );
  }

  const rows = list.data?.results ?? [];
  return (
    <>
      <ScreenHeader title={t('app:search.title')} subtitle={t('app:search.subtitle')}>
        <label className="relative mt-4 block">
          <span className="sr-only">{t('app:search.placeholder')}</span>
          <Search
            size={18}
            aria-hidden="true"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
          />
          <input
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t(`app:search.placeholders.${kind}`)}
            className="min-h-touch w-full rounded-button border-0 bg-card py-3 pl-10 pr-4 text-base text-ink placeholder:text-ink-muted"
          />
        </label>
      </ScreenHeader>
      <div className="space-y-4 px-4 py-5 sm:px-6">
        <Segmented
          label={t('app:search.what')}
          value={kind}
          onChange={(v) => setParams({ type: v })}
          options={(['group', 'teacher', 'room'] as const).map((k) => ({
            value: k,
            label: t(`app:search.kinds.${k}`),
          }))}
        />
        {list.isLoading ? (
          <LoadingRows rows={5} />
        ) : !rows.length ? (
          <EmptyState title={t('app:search.nothing')} />
        ) : (
          <ul className="divide-y divide-line overflow-hidden rounded-card border border-line bg-card">
            {rows.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => setParams({ type: kind, id: String(r.id) })}
                  className="flex min-h-touch w-full items-center gap-3 px-4 py-3 text-left hover:bg-subtle"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block font-bold text-ink">{title(kind, r)}</span>
                    <span className="block truncate text-sm text-ink-muted">
                      {kind === 'teacher' && r.department_name}
                      {kind === 'room' &&
                        t('app:search.roomLine', { building: r.building_name, n: r.capacity })}
                      {kind === 'group' && t('app:lesson.students', { n: r.student_count })}
                    </span>
                  </span>
                  <ChevronRight size={18} aria-hidden="true" className="text-ink-muted" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
