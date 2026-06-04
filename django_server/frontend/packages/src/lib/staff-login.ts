function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

export async function djangoStaffLogin(
  username: string,
  password: string,
  next?: string | null,
): Promise<{ ok: true; redirect: string } | { ok: false; message: string }> {
  const body = new URLSearchParams({
    username: username.trim(),
    password,
  });
  if (next) {
    const normalized = next.startsWith('/ui/') ? next : next.startsWith('/packages') ? `/ui${next}` : next;
    body.set('next', normalized);
  }

  const res = await fetch('/ui/api/v1/staff-login', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': getCsrfToken(),
    },
    body,
  });

  if (res.ok) {
    const data = (await res.json()) as { redirect: string };
    return { ok: true, redirect: data.redirect || '/ui/projects/' };
  }

  const data = (await res.json().catch(() => ({}))) as { detail?: string };
  const detail = data.detail ?? '';
  if (res.status === 403) {
    return { ok: false, message: 'Нужен аккаунт администратора (staff).' };
  }
  return {
    ok: false,
    message: detail || 'Неверный логин или пароль.',
  };
}
