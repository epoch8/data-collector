import { useMockApi } from '@/lib/firebase';

type TokenGetter = () => Promise<string | null>;

let tokenGetter: TokenGetter = async () => null;

export function setAuthTokenGetter(getter: TokenGetter): void {
  tokenGetter = getter;
}

const objectUrlCache = new Map<string, string>();

export async function fetchWithAuth(url: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (!useMockApi) {
    const token = await tokenGetter();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(url, { ...init, headers });
}

/** Blob URL для &lt;img&gt; (preview требует Authorization). */
export async function resolveAuthenticatedImageUrl(url: string): Promise<string> {
  if (useMockApi || !url.startsWith('/admin-api')) {
    return url;
  }
  const cached = objectUrlCache.get(url);
  if (cached) return cached;

  const res = await fetchWithAuth(url);
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

export async function downloadAuthenticatedFile(url: string, filename: string): Promise<void> {
  const res = await fetchWithAuth(url);
  if (!res.ok) throw new Error(`Не удалось скачать файл (${res.status})`);
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(objectUrl);
}
