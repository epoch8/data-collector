import { initializeApp, getApps, type FirebaseApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';

/** Те же ключи, что ios в lib/firebase_options.dart (data-collector-dev-e8). */
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY ?? 'AIzaSyCGtNxCn-rs7Gd3LEbG754GimCxz1yOi7c',
  authDomain:
    import.meta.env.VITE_FIREBASE_AUTH_DOMAIN ?? 'data-collector-dev-e8.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID ?? 'data-collector-dev-e8',
  storageBucket:
    import.meta.env.VITE_FIREBASE_STORAGE_BUCKET ?? 'data-collector-dev-e8.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID ?? '181572319604',
  appId: import.meta.env.VITE_FIREBASE_APP_ID ?? '1:181572319604:ios:0000000000000000000000',
};

export const useMockApi = import.meta.env.VITE_USE_MOCK === 'true';

/** Локальная разработка без Firebase на Django — можно VITE_FIREBASE_AUTH_ENABLED=false */
export const firebaseAuthEnabled =
  !useMockApi && import.meta.env.VITE_FIREBASE_AUTH_ENABLED !== 'false';

let app: FirebaseApp | undefined;
let auth: Auth | undefined;

export function getFirebaseAuth(): Auth | null {
  if (!firebaseAuthEnabled) return null;
  try {
    if (!app) {
      app = getApps().length ? getApps()[0]! : initializeApp(firebaseConfig);
    }
    if (!auth) {
      auth = getAuth(app);
    }
    return auth;
  } catch (err) {
    console.error('Firebase initializeApp failed', err);
    return null;
  }
}
