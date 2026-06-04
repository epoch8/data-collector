import { Outlet } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import { AuthLoadingScreen } from '@/components/AuthLoadingScreen';

export function RequireAuth() {
  const { ready, user, bypass } = useAuth();

  if (!ready) {
    return <AuthLoadingScreen />;
  }

  if (!bypass && !user) {
    const next = encodeURIComponent(
      window.location.pathname + window.location.search,
    );
    window.location.href = `/ui/login/?next=${next}`;
    return <AuthLoadingScreen />;
  }

  return <Outlet />;
}
