import { getCsrfToken } from '@/lib/csrf';
import { firebaseAuthEnabled } from '@/lib/firebase';

const objectUrlCache = new Map<string, string>();

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

let tokenGetter: (() => Promise<string | null>) | null = null;

export function setAuthTokenGetter(getter: () => Promise<string | null>): void {
  tokenGetter = getter;
}

export type TokenProvider = () => Promise<string | null>;

function needsCredentials(url: string): boolean {
  return url.startsWith('/ui/api/');
}

async function resolveBearerToken(getToken?: TokenProvider): Promise<string | null> {
  if (getToken) {
    return getToken();
  }
  if (firebaseAuthEnabled && tokenGetter) {
    return tokenGetter();
  }
  return null;
}

export async function fetchWithAuth(
  url: string,
  init?: RequestInit,
  getToken?: TokenProvider,
): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (needsCredentials(url)) {
    const csrf = getCsrfToken();
    if (csrf && !headers.has('X-CSRFToken')) {
      headers.set('X-CSRFToken', csrf);
    }
    if (firebaseAuthEnabled && !headers.has('Authorization')) {
      const token = await resolveBearerToken(getToken);
      if (token) headers.set('Authorization', `Bearer ${token}`);
    }
  }
  return fetch(url, {
    ...init,
    headers,
    credentials: USE_MOCK ? 'same-origin' : 'include',
  });
}

export async function resolveAuthenticatedImageUrl(
  url: string,
  getToken?: TokenProvider,
): Promise<string> {
  if (USE_MOCK || !needsCredentials(url)) {
    return url;
  }
  const cached = objectUrlCache.get(url);
  if (cached) return cached;

  const res = await fetchWithAuth(url, undefined, getToken);
  if (!res.ok) {
    throw new Error(`Не удалось загрузить изображение (${res.status})`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  objectUrlCache.set(url, objectUrl);
  return objectUrl;
}

export function clearAuthenticatedImageCache(): void {
  for (const objectUrl of objectUrlCache.values()) {
    URL.revokeObjectURL(objectUrl);
  }
  objectUrlCache.clear();
}

export async function downloadAuthenticatedFile(
  url: string,
  filename: string,
  getToken?: TokenProvider,
): Promise<void> {
  const res = await fetchWithAuth(url, undefined, getToken);
  if (!res.ok) throw new Error(`Не удалось скачать файл (${res.status})`);
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(objectUrl);
}
