import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ReportsPage } from './ReportsPage';

const report = {
  kind: 'plan',
  title: "O'quv reja bajarilishi",
  subtitle: '2025-2026, bahorgi semestr',
  columns: [
    { key: 'subject', label: 'Fan', numeric: false },
    { key: 'planned', label: 'Rejada', numeric: true },
    { key: 'difference', label: 'Farq', numeric: true },
  ],
  rows: [
    { subject: 'Aqida', planned: 15, difference: -15, status: 'less' },
    { subject: 'Tafsir', planned: 30, difference: 0, status: 'ok' },
  ],
  totals: { subject: 'Jami', planned: 45, difference: -15 },
  notes: ["2 ta yuklamadan 1 tasi rejaga to'liq mos."],
};

function json(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('ReportsPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('shows the table with totals, flags shortfalls and sorts by a column', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        Promise.resolve(json(url.startsWith('/api/reports/') ? report : { count: 0, results: [] })),
      ),
    );
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <MemoryRouter>
          <ReportsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText('Aqida')).toBeInTheDocument();
    const [head, ...body] = screen.getAllByRole('rowgroup');
    expect(within(head).getAllByRole('columnheader')).toHaveLength(3);
    expect(within(body[0]).getByText('-15')).toHaveClass('text-danger-fg');
    expect(within(body[1]).getByText('Jami')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Rejada' })); // numbers: largest first
    const first = within(screen.getAllByRole('rowgroup')[1]).getAllByRole('row')[0];
    expect(within(first).getByText('Tafsir')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Rejada' })).toHaveAttribute(
      'aria-sort',
      'descending',
    );
  });
});
