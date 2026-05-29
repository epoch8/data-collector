import { useState, type FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { FirebaseError } from 'firebase/app';
import { useAuth } from '@/auth/useAuth';
import { AuthLoadingScreen } from '@/components/AuthLoadingScreen';
import { firebaseAuthEnabled } from '@/lib/firebase';

export function LoginPage() {
  const { ready, user, bypass, signIn } = useAuth();
  const [loginEmail, setLoginEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!ready) {
    return <AuthLoadingScreen label="Проверка сессии Firebase…" />;
  }

  if (bypass || user) {
    return <Navigate to="/packages" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(loginEmail, password);
    } catch (err) {
      if (err instanceof FirebaseError) {
        setError(err.message || err.code);
      } else {
        setError(err instanceof Error ? err.message : 'Не удалось войти');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <p className="login-card__brand">EPOCH8</p>
        <h1 className="login-card__title">Data Collector Admin</h1>
        <p className="login-card__sub">
          Вход тем же аккаунтом Firebase, что и в мобильном приложении. Доступ к проектам — в Django →
          Пользователи (Firebase).
        </p>
        <form onSubmit={onSubmit} className="login-form">
          <label className="login-field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="email"
              value={loginEmail}
              onChange={e => setLoginEmail(e.target.value)}
              required
            />
          </label>
          <label className="login-field">
            <span>Пароль</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <p className="login-form__error">{error}</p>}
          <button type="submit" className="login-form__submit" disabled={busy}>
            {busy ? 'Вход…' : 'Войти'}
          </button>
        </form>
        {!firebaseAuthEnabled && (
          <p className="login-form__error" style={{ marginTop: '1rem' }}>
            Firebase отключён в сборке.
          </p>
        )}
      </div>
    </div>
  );
}
