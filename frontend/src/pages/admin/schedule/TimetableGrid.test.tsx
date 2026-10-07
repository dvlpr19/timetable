import { DndContext } from '@dnd-kit/core';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import '@/i18n';
import type { BlockedPeriod, EducationForm, GridCell } from '@/types/timetable';

import { weeklyDays } from './grid';
import { TimetableGrid } from './TimetableGrid';

const form: EducationForm = {
  id: 1,
  code: 'kunduzgi',
  name: 'Kunduzgi',
  schedule_mode: 'weekly',
  requires_room: true,
  study_weekdays: [3, 4],
  lesson_times: [{ id: 13, form: 1, number: 3, start: '11:30:00', end: '12:50:00', shift: 1 }],
};

const friday: BlockedPeriod = {
  id: 1,
  name: 'Juma namozi',
  weekday: 4,
  start: '12:00:00',
  end: '14:00:00',
  form: null,
  is_hard: true,
};

function cell(weekday: number, ok: boolean, reasons: string[] = []): GridCell {
  return { weekday, lesson_time: 13, number: 3, ok, room: ok ? 7 : null, free_rooms: [], reasons };
}

function renderGrid(cells: Map<string, GridCell> | null, onPick = vi.fn()) {
  render(
    <DndContext>
      <TimetableGrid
        form={form}
        days={weeklyDays(form)}
        entries={[]}
        blocked={[friday]}
        view="group"
        editable
        conflictIds={new Set()}
        moving={cells !== null}
        cells={cells}
        onOpen={vi.fn()}
        onPick={onPick}
      />
    </DndContext>,
  );
  return onPick;
}

describe('TimetableGrid', () => {
  it('marks the Friday prayer time as closed', () => {
    renderGrid(null);
    expect(screen.getByText('Juma namozi')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /payshanba/i })).toBeInTheDocument();
  });

  it('lets the dispatcher pick a green cell and explains a red one', async () => {
    const cells = new Map([
      ['w:3:13', cell(3, true)],
      ['w:4:13', cell(4, false, ['Juma namozi vaqtiga dars qo‘yilmaydi.'])],
    ]);
    const onPick = renderGrid(cells);

    await userEvent.click(screen.getByRole('button', { name: /Shu yerga qo'yish: payshanba, 3/i }));
    expect(onPick).toHaveBeenCalledWith(cells.get('w:3:13'));

    const red = screen.getByLabelText(/Qo'yib bo'lmaydi: juma, 3/i);
    expect(red).toHaveAccessibleDescription('Juma namozi vaqtiga dars qo‘yilmaydi.');
  });
});
