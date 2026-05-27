import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PackageListPage } from '@/pages/PackageListPage';
import { PackageWorkspacePage } from '@/pages/PackageWorkspacePage';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/packages" replace />} />
        <Route path="/packages" element={<PackageListPage />} />
        <Route path="/projects/:projectId/packages/:packageId" element={<PackageWorkspacePage />} />
      </Route>
    </Routes>
  );
}
