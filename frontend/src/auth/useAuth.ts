import { createContext, useContext } from 'react';

import type { Language } from '@/i18n';

import type { CurrentUser } from './types';

export interface AuthState {
  user: CurrentUser | null;
  /** True while the stored session is being restored on startup. */
  restoring: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setLanguage: (lng: Language) => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
