import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';
import type { SolverRun } from '@/types/solver';

import { RunPanel } from './RunPanel';

const base: SolverRun = {
  id: 7,
  semester: 1,
  faculty: 1,
  faculty_name: 'Islomshunoslik fakulteti',
  form: null,
  form_name: null,
  base_schedule: 1,
  base_name: 'Bahorgi semestr',
  result_schedule: null,
  result_name: null,
  params: { mode: 'rebuild', time_limit: 90 },
  status: 'running',
  status_display: 'Bajarilmoqda',
  progress: { phase: 'placing', elapsed: 9, placed: 120, total: 240 },
  created_by_name: 'Dispetcher',
  created_at: '2026-10-07T10:00:00Z',
  started_at: '2026-10-07T10:00:01Z',
  finished_at: null,
  objective: null,
  lessons_total: 0,
  lessons_placed: 0,
  hard_violations: 0,
  soft_violations: {},
  diagnostics: [],
  model_stats: {},
};

function serve(routes: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      const path = Object.keys(routes).find((p) => url.startsWith(p));
      return Promise.resolve(
        new Response(JSON.stringify(path ? routes[path] : {}), {
          status: path ? 200 : 404,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }),
  );
}

describe('RunPanel', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('shows the live phase and progress of a running job', async () => {
    serve({ '/api/solver-runs/7/': base });
    renderWithProviders(<RunPanel id={7} canEdit />);
    expect(await screen.findByText('1-bosqich: darslar joylashtirilmoqda')).toBeInTheDocument();
    const bar = screen.getByRole('progressbar', { name: 'Joylashtirildi: 120 / 240' });
    expect(bar).toHaveAttribute('aria-valuenow', '50');
    expect(screen.getByRole('button', { name: "To'xtatish" })).toBeInTheDocument();
  });

  it('shows the result, errors first, and a link to the new draft', async () => {
    serve({
      '/api/solver-runs/7/compare/': {
        result: {
          id: 9,
          name: 'Avtomatik #7',
          lessons: 250,
          missing: 2,
          hard_conflicts: 0,
          links_missing: 0,
          soft: {},
          soft_score: 400,
        },
        base: null,
        kept: 250,
        added: 250,
        removed: 0,
      },
      '/api/solver-runs/7/': {
        ...base,
        status: 'succeeded',
        status_display: 'Tugadi',
        finished_at: '2026-10-07T10:01:31Z',
        result_schedule: 9,
        lessons_total: 252,
        lessons_placed: 250,
        soft_violations: { score: 400 },
        diagnostics: [
          { code: 'assumption', severity: 'info', assignment_id: null, message: 'Taxmin' },
          {
            code: 'unplaced',
            severity: 'error',
            assignment_id: 3,
            message: 'Fiqh: 2 ta dars joylashtirilmadi',
          },
        ],
      },
    });
    renderWithProviders(<RunPanel id={7} canEdit />);
    expect(await screen.findByText('250 / 252')).toBeInTheDocument();
    expect(screen.getByText('90 s')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Qoralamani muharrirda ochish/ })).toHaveAttribute(
      'href',
      '/admin/schedule?v=9',
    );
    const notes = screen.getAllByRole('listitem').map((li) => li.textContent);
    expect(notes[0]).toContain('joylashtirilmadi');
    expect(await screen.findByText('Solishtirish')).toBeInTheDocument();
  });
});
