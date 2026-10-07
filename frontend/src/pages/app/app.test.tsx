import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthContext } from '@/auth/useAuth';
import type { CurrentUser } from '@/auth/types';
import { useCachedApi } from '@/lib/offline';
import type { Occurrence } from '@/types/timetable';

import { AvailabilityPage } from './AvailabilityPage';
import { DayList } from './lessons/DayList';

const teacherUser: CurrentUser = {
  id: 1,
  username: 'oqituvchi',
  first_name: 'Sardor',
  last_name: 'Yusupov',
  full_name: 'Yusupov Sardor',
  role: 'oqituvchi',
  language: 'uz',
  language_auto: false,
  student: null,
  teacher: { id: 9, short_name: 'Yusupov S.', department: 'Tafsir', position: 'Dotsent' },
};

function renderApp(ui: ReactElement, user: CurrentUser = teacherUser) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth = { user, restoring: false, login: vi.fn(), logout: vi.fn(), setLanguage: vi.fn() };
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AuthContext.Provider value={auth}>{ui}</AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function lesson(
  id: number,
  start: string,
  end: string,
  over: Partial<Occurrence> = {},
): Occurrence {
  return {
    id,
    schedule: 1,
    assignment: id,
    weekday: 2,
    week_parity: 'every',
    date: '2026-04-08',
    lesson_time: { id, number: id, start, end, shift: 1 },
    form: 'kunduzgi',
    subject: { id, name: `Fan ${id}` },
    lesson_type: { code: 'lecture', name: "Ma'ruza" },
    teacher: { id: 9, short_name: 'Yusupov S.', full_name: 'Yusupov Sardor' },
    groups: [{ id: 1, name: 'IS-301' }],
    subgroup: null,
    stream: null,
    student_count: 25,
    room: { id: 1, name: 'A-204', building: 'A bino', floor: 2, capacity: 30 },
    online_url: '',
    is_locked: false,
    note: '',
    status: 'scheduled',
    ...over,
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('DayList', () => {
  it('marks the lesson on now and the next one, and dims a holiday', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 3, 8, 10, 30));
    renderApp(
      <DayList
        isToday
        viewer="student"
        onOpen={vi.fn()}
        lessons={[
          lesson(3, '11:30', '12:50'),
          lesson(1, '08:30', '09:50'),
          lesson(2, '10:00', '11:20'),
          lesson(4, '13:30', '14:50', { status: 'reschedule' }),
        ]}
      />,
    );
    const items = screen.getAllByRole('listitem');
    expect(items.map((li) => within(li).getByText(/^Fan/).textContent)).toEqual([
      'Fan 1',
      'Fan 2',
      'Fan 3',
      'Fan 4',
    ]);
    expect(within(items[1]).getByText('Hozir')).toBeInTheDocument();
    expect(within(items[2]).getByText('Keyingi')).toBeInTheDocument();
    expect(within(items[3]).getByText('Bayram')).toBeInTheDocument();
    expect(within(items[0]).queryByText('Hozir')).toBeNull();
  });

  it('says when a day is free', () => {
    renderApp(<DayList lessons={[]} viewer="teacher" onOpen={vi.fn()} />);
    expect(screen.getByText("Bu kuni dars yo'q")).toBeInTheDocument();
  });
});

function CacheProbe() {
  const q = useCachedApi<{ value: number }>('/api/thing/');
  return (
    <p>
      {q.data ? `value ${q.data.value}` : 'empty'} · {q.stale ? 'stale' : 'fresh'}
    </p>
  );
}

describe('offline cache', () => {
  it('shows the saved copy when the server cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ value: 1 })));
    const first = renderApp(<CacheProbe />);
    expect(await screen.findByText('value 1 · fresh')).toBeInTheDocument();
    first.unmount();
    // a copy saved a minute ago is old enough to be refreshed
    const key = 'dj.cache:/api/thing/';
    const saved = JSON.parse(localStorage.getItem(key)!);
    localStorage.setItem(key, JSON.stringify({ ...saved, savedAt: Date.now() - 60_000 }));

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    renderApp(<CacheProbe />);
    expect(screen.getByText(/value 1/)).toBeInTheDocument(); // instantly, from storage
    expect(await screen.findByText('value 1 · stale', {}, { timeout: 4000 })).toBeInTheDocument();
  });
});

describe('AvailabilityPage', () => {
  it('cycles cell states and saves only what differs from "possible"', async () => {
    const form = {
      id: 1,
      code: 'kunduzgi',
      name: 'Kunduzgi',
      schedule_mode: 'weekly',
      requires_room: true,
      study_weekdays: [0, 1],
      lesson_times: [
        { id: 11, form: 1, number: 1, start: '08:30:00', end: '09:50:00', shift: 1 },
        { id: 12, form: 1, number: 2, start: '10:00:00', end: '11:20:00', shift: 1 },
      ],
    };
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url.startsWith('/api/education-forms/'))
        return Promise.resolve(json({ count: 1, results: [form] }));
      if (url.startsWith('/api/teacher-availability/replace/'))
        return Promise.resolve(json(JSON.parse(String(init?.body)).rows));
      if (url.startsWith('/api/teacher-availability/'))
        return Promise.resolve(json([{ weekday: 1, lesson_time: null, level: 'unavailable' }]));
      return Promise.resolve(json({}, 404));
    });
    vi.stubGlobal('fetch', fetchMock);
    renderApp(<AvailabilityPage />);

    const mondayFirst = await screen.findByRole('button', { name: 'dushanba, 1-para: Mumkin' });
    await userEvent.click(mondayFirst); // possible → preferred
    await userEvent.click(screen.getByRole('button', { name: 'dushanba, 2-para: Mumkin' }));
    await userEvent.click(screen.getByRole('button', { name: 'dushanba, 2-para: Qulay' })); // → unavailable
    // Tuesday is unavailable as a whole day, so its cells are locked
    expect(
      screen.getByRole('button', { name: 'seshanba, 1-para: Bo‘lmaydi'.replace('‘', "'") }),
    ).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Saqlash' }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/teacher-availability/replace/',
        expect.anything(),
      ),
    );
    const call = fetchMock.mock.calls.find(([u]) => u === '/api/teacher-availability/replace/')!;
    const body = JSON.parse(String(call[1]?.body));
    expect(body.teacher).toBe(9);
    expect(body.rows).toEqual(
      expect.arrayContaining([
        { weekday: 1, lesson_time: null, level: 'unavailable' },
        { weekday: 0, lesson_time: 11, level: 'preferred' },
        { weekday: 0, lesson_time: 12, level: 'unavailable' },
      ]),
    );
    expect(body.rows).toHaveLength(3);
  });
});
