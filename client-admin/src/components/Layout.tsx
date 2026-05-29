import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import { firebaseAuthEnabled } from '@/lib/firebase';

/** Оболочка без бокового меню — навигация через хлебные крошки на страницах. */
export function Layout() {
  const { email, bypass, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await signOut();
    if (firebaseAuthEnabled) navigate('/login');
  }

  return (
    <div className="min-h-screen bg-[var(--color-surface)] text-gray-200">
      {(firebaseAuthEnabled || email) && (
        <header className="app-topbar">
          <span className="app-topbar__title">client-admin</span>
          <div className="app-topbar__user">
            {email && <span className="app-topbar__email">{email}</span>}
            {firebaseAuthEnabled && (
              <button type="button" className="app-topbar__logout" onClick={() => void handleSignOut()}>
                Выйти
              </button>
            )}
            {bypass && !firebaseAuthEnabled && (
              <span className="app-topbar__dev">dev без auth</span>
            )}
          </div>
        </header>
      )}
      <main className="min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
