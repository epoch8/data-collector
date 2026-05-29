import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import { AuthLoadingScreen } from '@/components/AuthLoadingScreen';

export function RequireAuth() {
  const { ready, user, bypass } = useAuth();

  if (!ready) {
    return <AuthLoadingScreen />;
  }

  if (!bypass && !user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
