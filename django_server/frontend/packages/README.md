# Packages SPA (встроен в django_server)

React UI для вкладки **Пакеты** (`/ui/packages/`).

```bash
npm ci
npm run build    # → ../../api/static/packages/
npm run dev      # Vite :5173, proxy /ui/api → Django :8000
```

Переменные: см. `.env.example` (`VITE_USE_MOCK` для офлайн-демо).
