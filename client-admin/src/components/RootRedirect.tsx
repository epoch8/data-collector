import { Navigate } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import { AuthLoadingScreen } from '@/components/AuthLoadingScreen';

export function RootRedirect() {
  const { ready, user, bypass } = useAuth();

  if (!ready) return <AuthLoadingScreen />;

  if (bypass || user) {
    return <Navigate to="/packages" replace />;
  }

  return <Navigate to="/login" replace />;
}
