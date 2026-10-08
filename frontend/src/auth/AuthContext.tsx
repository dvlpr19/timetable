import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import i18n, { currentLanguage, type Language } from '@/i18n';
import { api } from '@/lib/api';
import { clearOfflineCache } from '@/lib/offline';
import { disablePush } from '@/lib/push';
import { tokenStore } from '@/lib/tokens';

import type { CurrentUser } from './types';
import { AuthContext } from './useAuth';

/**
 * The profile language wins once the user has chosen one. On the very first sign-in
 * (language_auto) the browser-detected language is stored in the profile instead.
 */
async function syncLanguage(user: CurrentUser): Promise<CurrentUser> {
  if (user.language_auto) {
    return api<CurrentUser>('/api/auth/me/', {
      method: 'PATCH',
      body: { language: currentLanguage() },
    });
  }
  if (user.language !== currentLanguage()) await i18n.changeLanguage(user.language);
  return user;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [restoring, setRestoring] = useState(() => tokenStore.access !== null);

  const loadUser = useCallback(async () => {
    const me = await api<CurrentUser>('/api/auth/me/');
    setUser(await syncLanguage(me));
  }, []);

  useEffect(() => {
    if (!tokenStore.access) return;
    loadUser()
      .catch(() => tokenStore.clear())
      .finally(() => setRestoring(false));
  }, [loadUser]);

  const login = useCallback(
    async (username: string, password: string) => {
      const tokens = await api<{ access: string; refresh: string }>('/api/auth/login/', {
        method: 'POST',
        body: { username, password },
        auth: false,
      });
      tokenStore.set(tokens.access, tokens.refresh);
      await loadUser();
    },
    [loadUser],
  );

  const logout = useCallback(() => {
    // The next person on this device must not get this person's messages.
    void disablePush()
      .catch(() => undefined)
      .finally(() => {
        tokenStore.clear();
        clearOfflineCache();
        setUser(null);
        queryClient.clear();
      });
  }, [queryClient]);

  const setLanguage = useCallback(
    async (lng: Language) => {
      await i18n.changeLanguage(lng);
      if (!user) return;
      try {
        setUser(
          await api<CurrentUser>('/api/auth/me/', { method: 'PATCH', body: { language: lng } }),
        );
      } catch {
        // The UI already switched; the profile will be synced on the next change.
      }
    },
    [user],
  );

  /** Save editable profile fields (e-mail, phone); errors are left to the caller. */
  const updateProfile = useCallback(
    async (patch: Partial<Pick<CurrentUser, 'email' | 'phone'>>) => {
      setUser(await api<CurrentUser>('/api/auth/me/', { method: 'PATCH', body: patch }));
    },
    [],
  );

  const value = useMemo(
    () => ({ user, restoring, login, logout, setLanguage, updateProfile }),
    [user, restoring, login, logout, setLanguage, updateProfile],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
