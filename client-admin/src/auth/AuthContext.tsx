import {
  createContext,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth';
import { firebaseAuthEnabled, getFirebaseAuth } from '@/lib/firebase';
import { clearAuthenticatedImageCache, setAuthTokenGetter } from '@/lib/authenticated-media';

export interface AuthContextValue {
  ready: boolean;
  user: User | null;
  email: string | null;
  bypass: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(!firebaseAuthEnabled);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!firebaseAuthEnabled) return;

    const auth = getFirebaseAuth();
    if (auth?.currentUser) {
      setUser(auth.currentUser);
      setReady(true);
    }

    let cancelled = false;
    const timeoutId = window.setTimeout(() => {
      if (!cancelled) setReady(true);
    }, 3000);

    if (!auth) {
      setReady(true);
      clearTimeout(timeoutId);
      return;
    }

    const unsub = onAuthStateChanged(auth, u => {
      if (cancelled) return;
      setUser(u);
      setReady(true);
      clearTimeout(timeoutId);
    });

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
      unsub();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const auth = getFirebaseAuth();
    if (!auth) throw new Error('Firebase Auth не настроен');
    await signInWithEmailAndPassword(auth, email.trim(), password);
  }, []);

  const signOut = useCallback(async () => {
    clearAuthenticatedImageCache();
    const auth = getFirebaseAuth();
    if (auth) await firebaseSignOut(auth);
    setUser(null);
  }, []);

  const getIdToken = useCallback(async () => {
    if (!firebaseAuthEnabled) return null;
    const auth = getFirebaseAuth();
    const current = auth?.currentUser;
    if (!current) return null;
    return current.getIdToken();
  }, [user]);

  useLayoutEffect(() => {
    setAuthTokenGetter(getIdToken);
  }, [getIdToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready,
      user,
      email: user?.email ?? null,
      bypass: !firebaseAuthEnabled,
      signIn,
      signOut,
      getIdToken,
    }),
    [ready, user, signIn, signOut, getIdToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
