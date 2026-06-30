> **Language / Язык:** **English** · [Русский](05-stage-1-mvp.ru.md)

# Stage 1: MVP Scope

Status: **completed** (historical document). Current product state — see [01-overview.md](01-overview.md).

## What was in Stage 1 scope (done)

1. ~~Mock Authentication~~ → **Firebase Email/Password** + optional offline mode without API.
2. ~~Mock Projects & Configs~~ → bundled `assets/config/` + **server catalog** `GET /v1/projects`.
3. **Dynamic UI from config:** `scroll_form` + `review`; types `text_input`, `datetime`, `instruction`, `camera_photo`.
4. **Local saving:** materialization in `packages/{id}/`, Drift index, `serverDeliveryState`.
5. **History view:** list of local packages with delivery status.

## What was out of Stage 1 scope and current status

| Was out of scope | Now |
|-------------------|--------|
| Real backend API | **Implemented:** Django `/v1/*`, Git-backed config |
| Enriched data viewer (mobile) | **Not implemented** (admin `/ui/` only) |
| Video capture | **Not implemented** |
| Background workers | **Not implemented** (manual upload from **Server** tab) |

## Current scope (post-MVP)

**In production:**

- Flutter Android (+ Web with limitations)
- Django API + web admin (staff + client-admin)
- Git-backed project config, per-project storage URIs
- Package upload protocol (blobs → manifest → commit)
- Admin visualization (`collector/viz.json`, pipeline plugins)

**Backlog:** see [todo](todo).
