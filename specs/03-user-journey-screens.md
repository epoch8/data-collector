> **Language / Язык:** **English** · [Русский](03-user-journey-screens.ru.md)

# User Journey & Screens

Status: **current** (June 2026). Code: `lib/main.dart` (GoRouter), `lib/features/*/presentation/`.

## 1. Authentication

| Mode | Behavior |
|-------|-----------|
| **Online** (`API_BASE_URL` set) | `LoginScreen`: email + password → Firebase Auth. Token automatically attached in Dio (`dio_provider.dart`). |
| **Offline** | Login skipped; projects from bundled assets. |

Login errors — snackbar. After success → Dashboard.

## 2. Dashboard (main screen)

`main.dart` — bottom navigation with tabs:

| Tab | Screen | Contents |
|---------|-------|------------|
| **Projects** | List of `Project` from `projectsProvider` | Project cards; tap → start collection |
| **History** | `HistoryTab` | Local packages across all projects; border color by `serverDeliveryState` |
| **Server** | `ServerSyncTab` | Upload queue; "Upload all" / one-by-one |
| **Help** | `HelpTab` | Static help |

Config sync indicator — on pull-to-refresh / `projectsProvider` restart.

## 3. Data collection

**Entry:** tap project → `CollectionFlowScreen(projectId)`.

### 3.1 Single `scroll_form` step

If the config has a single step and it is `scroll_form` → go directly to `ScrollFormCollectionScreen` (all step fields on one scroll).

### 3.2 Multiple steps

`CollectionFlowScreen` + `_FlowStepShell`:

1. One or more **`scroll_form`** steps — fields from the step's `field_ids`.
2. Optional **`review`** — summary before submit.

Widget types by `field.type`: text, date/time, Markdown instruction, camera (`camera_photo`).

### 3.3 Submit

- Required field validation.
- `submitLocalPackage` → materialization (`blobs/` + payload) → Drift, `status: completed`, `serverDeliveryState: pending`.
- **Auto-upload to server does not start** — user goes to the **Server** tab.

## 4. Server tab (outbox)

`ServerSyncTab`:

- List of packages with `serverDeliveryState != completed` and `status != draft`.
- Bulk and per-item upload buttons.
- Progress: `uploading` / `failed` with error text.
- Protocol: see [08-server-api-package-upload.md](08-server-api-package-upload.md).

## 5. History

`HistoryTab` / package detail view:

| `serverDeliveryState` | Indication |
|----------------------|-----------|
| `pending` | Yellow — device only |
| `uploading` | In progress |
| `completed` | Green — accepted by server |
| `failed` | Error; retry from **Server** tab |

Manifest export (share) — `history/` feature.

## 6. Web admin (`/ui/`)

Not part of the Flutter app; Django templates:

| Role | Access |
|------|--------|
| Staff | Projects, users, all packages |
| Client-admin (Firebase) | Assigned projects' packages only |

Package workspace: **Data / Media / Visualization / Change history**.

## 7. Not implemented in the mobile client

- Enriched / ML viewer (bounding boxes on device) — admin only.
- Background upload when network appears.
- Video capture.
