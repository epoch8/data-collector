import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { RequireAuth } from '@/components/RequireAuth';
import { AuthLoadingScreen } from '@/components/AuthLoadingScreen';
import { UnifiedLoginPage } from '@/pages/UnifiedLoginPage';

const PackageListPage = lazy(() =>
  import('@/pages/PackageListPage').then(m => ({ default: m.PackageListPage })),
);
const PackageWorkspacePage = lazy(() =>
  import('@/pages/PackageWorkspacePage').then(m => ({ default: m.PackageWorkspacePage })),
);

export function App() {
  return (
    <Routes>
      <Route path="login" element={<UnifiedLoginPage />} />
      <Route path="packages">
        <Route index element={<Navigate to="list" replace />} />
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>
            <Route
              path="list"
              element={
                <Suspense fallback={<AuthLoadingScreen />}>
                  <PackageListPage />
                </Suspense>
              }
            />
            <Route
              path="projects/:projectId/packages/:packageId"
              element={
                <Suspense fallback={<AuthLoadingScreen />}>
                  <PackageWorkspacePage />
                </Suspense>
              }
            />
          </Route>
        </Route>
      </Route>
    </Routes>
  );
}
