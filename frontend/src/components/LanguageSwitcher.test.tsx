import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import i18n, { LANGUAGE_STORAGE_KEY } from '@/i18n';
import { LoginPage } from '@/pages/LoginPage';
import { renderWithProviders } from '@/test/render';

describe('LanguageSwitcher', () => {
  it('switches the whole UI instantly and remembers the choice', async () => {
    renderWithProviders(<LoginPage />, { route: '/login' });
    expect(screen.getByRole('heading', { name: 'Tizimga kirish' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Ruscha' }));
    expect(screen.getByRole('heading', { name: 'Вход в систему' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Русский' })).toHaveAttribute('aria-pressed', 'true');
    expect(document.documentElement.lang).toBe('ru');
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('ru');

    await userEvent.click(screen.getByRole('button', { name: 'Английский' }));
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(i18n.resolvedLanguage).toBe('en');
  });
});
