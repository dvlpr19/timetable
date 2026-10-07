import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { LoginPage } from './LoginPage';

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('LoginPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('asks for both fields before calling the server', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    renderWithProviders(<LoginPage />, { route: '/login' });

    await userEvent.click(screen.getByRole('button', { name: 'Kirish' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Login va parolni kiriting.');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('shows the server error and sends the UI language', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(401, { detail: 'Login yoki parol noto‘g‘ri.' }));
    vi.stubGlobal('fetch', fetchMock);
    renderWithProviders(<LoginPage />, { route: '/login' });

    await userEvent.type(screen.getByLabelText('Login'), 'talaba');
    await userEvent.type(screen.getByLabelText('Parol'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Kirish' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Login yoki parol');
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get('Accept-Language')).toBe('uz');
  });

  it('keeps the HEMIS button disabled', () => {
    renderWithProviders(<LoginPage />, { route: '/login' });
    expect(screen.getByRole('button', { name: /HEMIS/ })).toBeDisabled();
  });
});
