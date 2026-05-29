import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { RequireAuth } from '@/components/RequireAuth';
import { RootRedirect } from '@/components/RootRedirect';
import { AuthLoadingScreen } from '@/components/AuthLoadingScreen';
import { LoginPage } from '@/pages/LoginPage';

const PackageListPage = lazy(() =>
  import('@/pages/PackageListPage').then(m => ({ default: m.PackageListPage })),
);
const PackageWorkspacePage = lazy(() =>
  import('@/pages/PackageWorkspacePage').then(m => ({ default: m.PackageWorkspacePage })),
);

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RootRedirect />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route
            path="/packages"
            element={
              <Suspense fallback={<AuthLoadingScreen />}>
                <PackageListPage />
              </Suspense>
            }
          />
          <Route
            path="/projects/:projectId/packages/:packageId"
            element={
              <Suspense fallback={<AuthLoadingScreen />}>
                <PackageWorkspacePage />
              </Suspense>
            }
          />
        </Route>
      </Route>
    </Routes>
  );
}
