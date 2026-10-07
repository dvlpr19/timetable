import { useTranslation } from 'react-i18next';
import { Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';

import { useAuth } from '@/auth/useAuth';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';

function RequireAuth({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { user, restoring } = useAuth();
  if (restoring) {
    return (
      <div role="status" className="flex min-h-dvh items-center justify-center text-ink-muted">
        {t('loading')}
      </div>
    );
  }
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <HomePage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
