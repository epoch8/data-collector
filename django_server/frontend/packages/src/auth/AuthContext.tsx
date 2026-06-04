import {
  createContext,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { onAuthStateChanged, type User as FirebaseUser } from 'firebase/auth';
import {
  clearAuthenticatedImageCache,
  setAuthTokenGetter,
  type TokenProvider,
} from '@/lib/authenticated-media';
import { fetchWithAuth } from '@/lib/authenticated-media';
import { firebaseAuthEnabled, getFirebaseAuth } from '@/lib/firebase';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export interface SessionUser {
  role: 'staff' | 'client';
  email: string;
  username: string;
  project_ids: string[] | null;
}

export interface AuthContextValue {
  ready: boolean;
  user: SessionUser | null;
  email: string | null;
  bypass: boolean;
  authMode: 'session' | 'firebase' | 'mock' | null;
  authError: string | null;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

async function fetchMe(getToken?: TokenProvider): Promise<{
  user: SessionUser | null;
  status: number;
}> {
  const res = await fetchWithAuth('/ui/api/v1/me', undefined, getToken);
  if (res.status === 401 || res.status === 403) {
    return { user: null, status: res.status };
  }
  if (!res.ok) {
    return { user: null, status: res.status };
  }
  const user = (await res.json()) as SessionUser;
  return { user, status: res.status };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(USE_MOCK);
  const [user, setUser] = useState<SessionUser | null>(
    USE_MOCK ? { role: 'staff', email: 'dev@local', username: 'dev', project_ids: null } : null,
  );
  const [authMode, setAuthMode] = useState<'session' | 'firebase' | 'mock' | null>(
    USE_MOCK ? 'mock' : null,
  );
  const [authError, setAuthError] = useState<string | null>(null);
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);

  const getIdToken = useCallback(async () => {
    if (!firebaseAuthEnabled || !firebaseUser) return null;
    return firebaseUser.getIdToken();
  }, [firebaseUser]);

  useLayoutEffect(() => {
    setAuthTokenGetter(getIdToken);
  }, [getIdToken]);

  useEffect(() => {
    if (USE_MOCK) return;

    let cancelled = false;
    let unsubFirebase: (() => void) | undefined;

    async function bootstrap() {
      const { user: sessionUser, status } = await fetchMe();
      if (cancelled) return;

      if (sessionUser) {
        setUser(sessionUser);
        setAuthMode('session');
        setAuthError(null);
        setReady(true);
        return;
      }

      if (!firebaseAuthEnabled) {
        setAuthError(
          status === 403
            ? 'Нет проектов в Client-admin. Попросите администратора назначить доступ.'
            : null,
        );
        setReady(true);
        return;
      }

      const auth = getFirebaseAuth();
      if (!auth) {
        setAuthError('Firebase Auth не инициализирован в браузере.');
        setReady(true);
        return;
      }

      unsubFirebase = onAuthStateChanged(auth, async fbUser => {
        if (cancelled) return;
        setFirebaseUser(fbUser);
        if (!fbUser) {
          setUser(null);
          setAuthMode(null);
          setAuthError(null);
          setReady(true);
          return;
        }

        const getToken = () => fbUser.getIdToken();
        const { user: me, status: meStatus } = await fetchMe(getToken);
        if (cancelled) return;

        if (me) {
          setUser(me);
          setAuthMode('firebase');
          setAuthError(null);
        } else {
          setUser(null);
          setAuthMode(null);
          setAuthError(
            meStatus === 403
              ? 'Нет доступа к проектам: отметьте Client-admin в «Пользователи» для этого email.'
              : 'Не удалось проверить сессию на сервере (ошибка ' + meStatus + ').',
          );
        }
        setReady(true);
      });
    }

    void bootstrap();

    return () => {
      cancelled = true;
      unsubFirebase?.();
    };
  }, []);

  const signOut = useCallback(async () => {
    clearAuthenticatedImageCache();
    setUser(null);
    setAuthError(null);
    if (authMode === 'firebase') {
      const auth = getFirebaseAuth();
      if (auth) {
        const { signOut: fbSignOut } = await import('firebase/auth');
        await fbSignOut(auth);
      }
      window.location.href = '/ui/login/';
      return;
    }
    window.location.href = '/ui/logout/';
  }, [authMode]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready,
      user,
      email: user?.email ?? null,
      bypass: USE_MOCK,
      authMode,
      authError,
      signOut,
    }),
    [ready, user, authMode, authError, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
