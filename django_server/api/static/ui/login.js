import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import { getAuth, signInWithEmailAndPassword } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';

function getCookie(name) {
  const m = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return m ? decodeURIComponent(m[2]) : '';
}

const form = document.getElementById('ui-login-form');
if (!form || form.dataset.firebaseEnabled !== '1' || !window.__UI_FIREBASE_CONFIG__) {
  /* Только staff: обычный POST формы. */
} else {
  const adminCb = document.getElementById('admin-access');
  const idInput = document.getElementById('login-username');
  const idLabel = document.getElementById('login-id-label');
  const hint = document.getElementById('login-hint');
  const errEl = document.getElementById('login-error');
  const btn = document.getElementById('login-submit');

  const app = initializeApp(window.__UI_FIREBASE_CONFIG__);
  const auth = getAuth(app);

  function isAdminMode() {
    return adminCb && adminCb.checked;
  }

  function syncMode() {
    const admin = isAdminMode();
    if (admin) {
      idLabel.textContent = 'Логин';
      idInput.type = 'text';
      idInput.autocomplete = 'username';
      hint.textContent =
        'Учётная запись Django staff. Логин без символа @.';
    } else {
      idLabel.textContent = 'Email';
      idInput.type = 'email';
      idInput.autocomplete = 'username';
      hint.textContent =
        'Email и пароль Firebase. Доступ к пакетам — по назначению в «Пользователи».';
    }
    errEl.classList.add('d-none');
  }

  if (adminCb) {
    adminCb.addEventListener('change', syncMode);
    syncMode();
  }

  form.addEventListener('submit', async e => {
    if (isAdminMode()) {
      return;
    }
    e.preventDefault();
    errEl.classList.add('d-none');
    btn.disabled = true;
    try {
      const email = idInput.value.trim();
      const password = document.getElementById('login-password').value;
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
