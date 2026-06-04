import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import { getAuth, signInWithEmailAndPassword } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';

function getCookie(name) {
  const m = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return m ? decodeURIComponent(m[2]) : '';
}

const form = document.getElementById('firebase-login-form');
if (form && window.__UI_FIREBASE_CONFIG__) {
  const app = initializeApp(window.__UI_FIREBASE_CONFIG__);
  const auth = getAuth(app);

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const errEl = document.getElementById('fb-error');
    const btn = document.getElementById('fb-submit');
    errEl.classList.add('d-none');
    btn.disabled = true;
    try {
      const email = document.getElementById('fb-email').value.trim();
      const password = document.getElementById('fb-password').value;
      const cred = await signInWithEmailAndPassword(auth, email, password);
      const idToken = await cred.user.getIdToken();
      const res = await fetch('/ui/login/firebase/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          id_token: idToken,
          next: window.__UI_LOGIN_NEXT__ || '',
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Ошибка входа');
      }
      window.location.href = data.redirect || '/ui/packages/';
    } catch (err) {
      errEl.textContent = err?.message || String(err);
      errEl.classList.remove('d-none');
    } finally {
      btn.disabled = false;
    }
  });
}
