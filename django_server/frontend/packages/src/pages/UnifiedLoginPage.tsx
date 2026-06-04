import { useEffect, useState } from 'react';
import { signInWithEmailAndPassword, signOut as fbSignOut } from 'firebase/auth';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import { fetchWithAuth } from '@/lib/authenticated-media';
import { firebaseAuthEnabled, getFirebaseAuth } from '@/lib/firebase';
import { djangoStaffLogin } from '@/lib/staff-login';

async function fetchMeWithToken(getToken: () => Promise<string | null>) {
  const res = await fetchWithAuth('/ui/api/v1/me', undefined, getToken);
  if (res.status === 401 || res.status === 403) {
    return { user: null, status: res.status };
  }
  if (!res.ok) {
    return { user: null, status: res.status };
  }
  return { user: await res.json(), status: res.status };
}

function normalizeNext(next: string | null): string | null {
  if (!next) return null;
  if (next.startsWith('/ui/')) return next;
  if (next.startsWith('/packages')) return `/ui${next}`;
  return next.startsWith('/') ? next : null;
}

function defaultRedirect(role: 'staff' | 'client', next: string | null): string {
  const target = normalizeNext(next);
  if (target) return target;
  return role === 'staff' ? '/ui/projects/' : '/ui/packages/list';
}

export function UnifiedLoginPage() {
  const { ready, user } = useAuth();
  const [searchParams] = useSearchParams();
  const next = searchParams.get('next');

  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ready || !user) return;
    window.location.href = defaultRedirect(user.role, next);
  }, [ready, user, next]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const loginTrim = login.trim();
    const tryFirebase = firebaseAuthEnabled && loginTrim.includes('@');

    try {
      if (tryFirebase) {
        const auth = getFirebaseAuth();
        if (!auth) {
          setError('Сервис входа клиента недоступен');
          return;
        }
        try {
          await signInWithEmailAndPassword(auth, loginTrim, password);
          const fbUser = auth.currentUser;
          if (fbUser) {
            const getToken = () => fbUser.getIdToken();
            const { user: me, status } = await fetchMeWithToken(getToken);
            if (me?.role === 'client') {
              window.location.href = defaultRedirect('client', next);
              return;
            }
            if (status === 403) {
              await fbSignOut(auth);
              setError(
                'Нет доступа к проектам: отметьте Client-admin в «Пользователи» для этого email.',
              );
              return;
            }
          }
        } catch {
          /* пробуем вход администратора */
        }
      }

      const staff = await djangoStaffLogin(loginTrim, password, next);
      if (staff.ok) {
        window.location.href = staff.redirect;
        return;
      }

      if (tryFirebase) {
        setError('Неверный email/пароль или нет прав администратора.');
      } else {
        setError(staff.message);
      }
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center px-4">
        <p className="login-card__sub" style={{ margin: 0 }}>
          Загрузка…
        </p>
      </div>
    );
  }

  if (user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center px-4">
        <p className="login-card__sub" style={{ margin: 0 }}>
          Перенаправление…
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-[50vh] items-center justify-center px-4">
      <div className="login-card">
        <h1 className="login-card__title">Вход</h1>
        <p className="login-card__sub">
          Email — клиент (Firebase). Логин без @ — администратор (Django).
        </p>
        <form className="login-form" onSubmit={e => void handleSubmit(e)}>
          <label className="login-field">
            Логин или email
            <input
              type="text"
              value={login}
              onChange={e => setLogin(e.target.value)}
              required
              autoComplete="username"
              autoFocus
            />
          </label>
          <label className="login-field">
            Пароль
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error && <p className="login-form__error">{error}</p>}
          <button type="submit" className="login-form__submit" disabled={loading}>
            {loading ? '…' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}
