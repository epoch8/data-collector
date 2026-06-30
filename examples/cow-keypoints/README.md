> **Language / Язык:** **English** · [Русский](README.ru.md)

# Example project: Cow Keypoints (cattle)

A demonstration, **domain-specific** project built on the data_collector framework.
Shows how concrete collection scenarios are assembled from shared entities — here,
photographing cattle from multiple viewpoints for keypoint labeling and scoring.

This example is **not included in the default client bundle** — the framework core is neutral.
Use it as a reference when creating your own project.

## Contents

| File | Purpose |
|------|---------|
| `config.json` | Collection config (`flow.steps`, `fields`, `ui`). Placed in the project Git repository as `collector/config.json`. |
| `viz.json` | Pipeline visualization config in the admin panel. Placed as `collector/viz.json`. |
| `schemas/` | Source domain schemas (`.drawio`) from early versions. |

## What this example demonstrates

- **Viewpoint-based collection** (`scroll_form` + `camera_photo` + `instruction`) with pose examples.
- **Subject ID hints** — `cow_id_hints` / `cow_id_field_id` fields
  (shared mechanism to "suggest values from past packages by subject ID"; here the subject is an animal).
- **Visualization** via viz plugins: `keypoint_korovas` (cattle keypoints), `cvat_link`, `depth_map`.

## How to use

1. Create a project with a Git repository in the admin panel (`/ui/projects/`).
2. Place `config.json` → `collector/config.json` and `viz.json` → `collector/viz.json` in that repository.
3. If steps include `example_asset_path` (pose examples), add images to the client build
   (by default the core looks for placeholder `assets/placeholders/example_pose_placeholder.jpg`).

For config format details — [`specs/config/09-project-json-builder-guide.md`](../../specs/config/09-project-json-builder-guide.md),
for visualization — [`specs/collector-vis-config.md`](../../specs/collector-vis-config.md).
