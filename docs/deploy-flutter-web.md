> **Language / Язык:** **English** · [Русский](deploy-flutter-web.ru.md)

# Deploying Flutter Web (collector)


## What you get

After `flutter build web`, the **`build/web/`** directory is a plain **static site** (HTML, JS, WASM, assets). Serve it with nginx, a CDN, object storage with a public URL, or any other static host. No separate "Flutter server" is needed for production.

## Build

From the **repository root** (next to `pubspec.yaml`):

```bash
flutter pub get
flutter build web --release --dart-define=API_BASE_URL=https://your-api.example.com
```

- **`API_BASE_URL`** — base URL of the Django admin/API


More details: `lib/core/api/api_environment.dart`, general context — `README.md`.

## Serving files

1. Copy the contents of **`build/web/`** to your host (or deploy the pipeline artifact).
2. Configure **SPA behavior**: for requests to non-existent paths (except real files), serve **`index.html`**; otherwise direct URL access or page refresh will return 404.
3. Prefer **HTTPS** (Firebase and modern browsers).

## Django and CORS

The browser sends requests from your web app's **origin**. In **`django_server/collector_site/settings.py`**, CORS is configured via `django-cors-headers`.

- In **production** (`DEBUG=False`), the default regex only allows `localhost` / `127.0.0.1` on any port. You must explicitly allow the **production app origin** with the environment variable:

  **`DJANGO_CORS_ALLOWED_ORIGINS`** — comma-separated list, for example:

  `https://collector.example.com,https://www.collector.example.com`

- After changing the origin, rebuilding Flutter is **not required** if you did not change `API_BASE_URL`.

## Firebase

Client config: `lib/firebase_options.dart` (and if needed, steps from `README.md` / `flutterfire configure`). For web login, the Firebase console must allow the **app domain** (Authorized domains) from which the built site is opened.

## Related notes

Web vs APK differences (files, camera, network): **`docs/web-vs-android.md`**.
