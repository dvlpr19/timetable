import { useTranslation } from 'react-i18next';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import type { ReactNode } from 'react';

import { isStaff } from '@/auth/roles';
import { useAuth } from '@/auth/useAuth';
import { AppLayout } from '@/layouts/AppLayout';
import { AvailabilityPage } from '@/pages/app/AvailabilityPage';
import { FreeRoomsPage } from '@/pages/app/FreeRoomsPage';
import { MessagesPage } from '@/pages/app/MessagesPage';
import { ProfilePage } from '@/pages/app/ProfilePage';
import { SearchPage } from '@/pages/app/SearchPage';
import { TodayPage } from '@/pages/app/TodayPage';
import { WeekPage } from '@/pages/app/WeekPage';
import { LoginPage } from '@/pages/LoginPage';

// The admin panel (editor, drag-and-drop, solver) loads only for staff; phones get the app.
const AdminLayout = lazy(() =>
  import('@/layouts/AdminLayout').then((m) => ({ default: m.AdminLayout })),
);
const DashboardPage = lazy(() =>
  import('@/pages/admin/DashboardPage').then((m) => ({ default: m.DashboardPage })),
);
const ResourcePage = lazy(() =>
  import('@/pages/admin/data/ResourcePage').then((m) => ({ default: m.ResourcePage })),
);
const AdminProfilePage = lazy(() =>
  import('@/pages/admin/AdminProfilePage').then((m) => ({ default: m.AdminProfilePage })),
);
const ReportsPage = lazy(() =>
  import('@/pages/admin/ReportsPage').then((m) => ({ default: m.ReportsPage })),
);
const RequestsPage = lazy(() =>
  import('@/pages/admin/RequestsPage').then((m) => ({ default: m.RequestsPage })),
);
const SchedulePage = lazy(() =>
  import('@/pages/admin/schedule/SchedulePage').then((m) => ({ default: m.SchedulePage })),
);
const SolverPage = lazy(() =>
  import('@/pages/admin/solver/SolverPage').then((m) => ({ default: m.SolverPage })),
);

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

/** Staff land in the admin panel; students and teachers get the mobile app. */
function Home() {
  const { user } = useAuth();
  return isStaff(user?.role) ? <Navigate to="/admin" replace /> : <AppLayout />;
}

function TeacherOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user?.role === 'oqituvchi' ? <>{children}</> : <Navigate to="/" replace />;
}

function Loading() {
  const { t } = useTranslation();
  return (
    <div role="status" className="flex min-h-dvh items-center justify-center text-ink-muted">
      {t('loading')}
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Home />
            </RequireAuth>
          }
        >
          <Route index element={<TodayPage />} />
          <Route path="week" element={<WeekPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="messages" element={<MessagesPage />} />
          <Route
            path="rooms"
            element={
              <TeacherOnly>
                <FreeRoomsPage />
              </TeacherOnly>
            }
          />
          <Route
            path="availability"
            element={
              <TeacherOnly>
                <AvailabilityPage />
              </TeacherOnly>
            }
          />
        </Route>
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
          <Route path="requests" element={<RequestsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="profile" element={<AdminProfilePage />} />
          <Route path="data/:resource" element={<ResourcePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
