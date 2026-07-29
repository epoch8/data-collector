---
name: firebase-data-collector
description: >-
  Sets up Firebase Auth for this Data Collector repo (Flutter client + Django
  Admin SDK + admin panel users). Use when the user asks to configure Firebase,
  fix 401 on /v1/*, sync google-services.json / firebase_options, service
  account, FIREBASE_WEB_*, or follow docs/architecture/firebase-setup.ru.md.
---

# Firebase setup — Data Collector

Human guide (short): `docs/architecture/firebase-setup.ru.md`.

## Goal

One Firebase project wired to:

| Piece | Path / place |
| --- | --- |
| Android SDK | `android/app/google-services.json` |
| Flutter options | `lib/firebase_options.dart` (android + web = same `projectId`) |
| Django token verify | `django_server/firebase-service-account.json` (gitignored) |
| Admin Web login | `FIREBASE_WEB_*` / `FIREBASE_WEB_CONFIG` in `django_server/collector_site/settings.py` |
| Mobile project ACL | Admin UI → Users → Sync → `mobile_projects` |

**Hard rule:** client `projectId`, Web config, and SA JSON `project_id` must match. Mismatch → login OK, `/v1/*` → **401**.

Default Android package in this repo: `com.example.data_collector`.

## Before changing anything

1. Ask: existing Project ID or create new?
2. Confirm MCP `plugin-firebase-firebase` is usable (`firebase_get_environment` / login).
3. Do **not** commit service account JSON or paste private keys into git.

## Agent workflow

Copy and track:

```
- [ ] 1. Login + active project
- [ ] 2. Android + Web apps exist
- [ ] 3. Write google-services.json + update firebase_options (android/web)
- [ ] 4. Enable Auth Email/Password; remind user to create test user
- [ ] 5. User places SA JSON (MCP cannot download private key)
- [ ] 6. Align FIREBASE_WEB_* / settings defaults with Web SDK config
- [ ] 7. Tell user: Sync users + mobile_projects; restart Django; full Flutter restart
```

### 1. Login and project

Use Firebase MCP (server `plugin-firebase-firebase`):

1. `firebase_login` if needed.
2. `firebase_list_projects` → pick or `firebase_create_project`.
3. `firebase_get_environment` / `firebase_update_environment` so the active project is correct.

CLI fallback (same project):

```bash
npx -y firebase-tools@latest login
npx -y firebase-tools@latest use <PROJECT_ID>
```

Always prefer `npx -y firebase-tools@latest …`, never bare `firebase`.

### 2. Apps

- `firebase_list_apps`
- If missing: `firebase_create_app` for `android` (`package_name`: `com.example.data_collector`) and `web`.
- iOS only if user asks (Bundle ID often `com.example.dataCollector`).

### 3. SDK configs into the repo

- `firebase_get_sdk_config` for Android → write `android/app/google-services.json`.
- `firebase_get_sdk_config` for Web → fill **web** (and keep android in sync) in `lib/firebase_options.dart`.

`appId` for web must contain `:web:`; do not copy the Android appId into the web block.

Optional CLI:

```bash
npx -y firebase-tools@latest apps:sdkconfig ANDROID <ANDROID_APP_ID> > android/app/google-services.json
npx -y firebase-tools@latest apps:sdkconfig WEB <WEB_APP_ID>
```

### 4. Authentication

- Enable Email/Password via `firebase_update_environment` when the tool supports it; otherwise tell the user: Console → Authentication → Sign-in method.
- Test user: Console → Users → Add user (agent cannot always create Auth users via MCP — guide the user).
- Authorized domains must include `localhost` and `127.0.0.1` for local admin login.

### 5. Service account (manual)

Tell the user clearly:

1. Console → Project settings → Service accounts → Generate new private key.
2. Save as `django_server/firebase-service-account.json`.
3. Verify JSON `project_id` equals the client project.

Or: `FIREBASE_SERVICE_ACCOUNT_PATH` / `FIREBASE_SERVICE_ACCOUNT_JSON` / `GOOGLE_APPLICATION_CREDENTIALS`.

Never invent a fake SA file.

### 6. Django Web config

Match Web SDK fields via env or defaults in `settings.py`:

- `FIREBASE_WEB_API_KEY`
- `FIREBASE_WEB_AUTH_DOMAIN`
- `FIREBASE_WEB_PROJECT_ID`
- `FIREBASE_WEB_STORAGE_BUCKET`
- `FIREBASE_WEB_MESSAGING_SENDER_ID`
- `FIREBASE_WEB_APP_ID`

Do **not** set `FIREBASE_AUTH_ENABLED=false` for the real auth path.  
Presence of SA JSON usually enables auth automatically — restart `runserver` after changes.

### 7. Users and mobile

Remind user (Django UI, not Firebase MCP):

1. `http://127.0.0.1:8000/ui/` as staff.
2. Users → Sync with Firebase.
3. Grant `mobile_projects`.
4. Re-login in the app.

Flutter:

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

(emulator; physical device → PC LAN IP).

## Demo bypass

Only if user asks for API without Auth:

```powershell
$env:FIREBASE_AUTH_ENABLED = "false"
```

Say this skips Firebase JWT checks.

## Troubleshooting (agent)

| Symptom | Check |
| --- | --- |
| 401 on `/v1/*` | SA vs client `project_id`; Django restart; Flutter full restart + re-login |
| No projects after login | `mobile_projects` + sync |
| Admin Web login fails | `FIREBASE_WEB_*`, authorized domains |
| Init fails | package name vs `google-services.json`, `firebase_options` |
| Mixed projects in repo | android/web may be `e8-gke` while ios/macos point elsewhere — fix platforms the user actually runs |

## What MCP is for

Use MCP to: login, list/create projects and apps, fetch SDK config, inspect/update environment, answer Firebase docs (`developerknowledge_*`).

Do **not** expect MCP to: download service account private keys, grant Django `mobile_projects`, or replace reading this skill / `firebase-setup.ru.md`.

## Official Firebase skills

If generic Firebase CLI/MCP setup is broken, also follow the installed `firebase-basics` skill (Cursor plugin). This skill is **project-specific** wiring for Data Collector.
