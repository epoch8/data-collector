import { Outlet } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';

/** Полоса аккаунта для Firebase-клиента (Django nav не знает о Firebase-сессии). */
export function Layout() {
  const { user, signOut } = useAuth();

  return (
    <div className="packages-spa-root min-h-[60vh] text-gray-200">
      {user?.role === 'client' && (
        <header className="app-topbar">
          <span className="app-topbar__title">Пакеты</span>
          <div className="app-topbar__user">
            <span className="app-topbar__email" title={user.email}>
              {user.email || user.username}
            </span>
            <button
              type="button"
              className="app-topbar__logout"
              onClick={() => void signOut()}
            >
              Выйти
            </button>
          </div>
        </header>
      )}
      <Outlet />
    </div>
  );
}
