import { useTranslation } from 'react-i18next';
import { Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';

import { isStaff } from '@/auth/roles';
import { useAuth } from '@/auth/useAuth';
import { AdminLayout } from '@/layouts/AdminLayout';
import { DashboardPage } from '@/pages/admin/DashboardPage';
import { ResourcePage } from '@/pages/admin/data/ResourcePage';
import { SchedulePage } from '@/pages/admin/schedule/SchedulePage';
import { SolverPage } from '@/pages/admin/solver/SolverPage';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';

function RequireAuth({ children, staff }: { children: ReactNode; staff?: boolean }) {
  const { t } = useTranslation();
  const { user, restoring } = useAuth();
  if (restoring) {
    return (
      <div role="status" className="flex min-h-dvh items-center justify-center text-ink-muted">
        {t('loading')}
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (staff && !isStaff(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

/** Staff land in the admin panel; students and teachers get their own home (stage 7). */
function Home() {
  const { user } = useAuth();
  return isStaff(user?.role) ? <Navigate to="/admin" replace /> : <HomePage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Home />
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAuth staff>
            <AdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="schedule" element={<SchedulePage />} />
        <Route path="solver" element={<SolverPage />} />
        <Route path="data/:resource" element={<ResourcePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
