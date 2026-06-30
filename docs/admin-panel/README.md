> **Language / Язык:** **English** · [Русский](README.ru.md)

# User guide: admin panel

Instructions for configuring projects, user access, and viewing uploaded packages (with pipeline result visualization).

Screenshots are from the product presentation [`specs/presentation/Data-Collector.pptx`](../../specs/presentation/Data-Collector.pptx) (source frames are in `specs/presentation/img/`). The interface is evolving, so individual frames may differ from the current version — rely on the text.

**Panel URL:** your instance's web admin at `/ui/`.

---

## **1. Signing in**

1. Open your instance's web admin at `…/ui/login/`.
2. Sign in with an administrator account (Django **staff**) — issued by the instance administrator.
3. After sign-in, the project list opens.

---

## **2. Interface overview**

The top menu has three sections:

| **Section** | **Purpose** |
| --- | --- |
| **Projects** | Create and configure data collection scenarios, media for instructions |
| **Users** | Firebase accounts and access to projects in the mobile app |
| **Packages** | View data uploaded from phones |

![Top menu: Projects, Users, Packages](image.png)

---

## **3. Projects**

### **3.1. Project list**

The **Projects** section is a catalog of all projects (collection initiatives). For each one you see `project_id`, name, config version, and last updated date.

Create a **separate project** for each site/initiative (for example, `my-project-2026`). Config structure can be identical while names and `project_id` differ.

![Project list](<image 1.png>)

### **3.2. Creating a new project**

> **Important:** project config is stored **not in the database, but in a Git repository** (`collector/config.json`). When creating a project, specify the repository and set up SSH deploy key access. Data storage (DB/media) is **optional**.

Click **"New project"** and fill in the form:

1. **project_id** — Latin characters, must match the `id` field in `collector/config.json` (for example, `my-project-2026`).
2. **Name** — how the project appears in the app.
3. **Git repository** — URL of the repo with the config (public or private; access via SSH deploy key).
4. **Branch** — defaults to `main`.
5. **SSH key** — leave **"Generate SSH key on server"** enabled (recommended) or paste your own private key (OpenSSH format).
6. **Data storage** (optional block) — see 3.4. If left empty: SQLite + local folder on the server.

Click **"Create project"**.

!["New project" form](<image 2.png>)

After creation, **grant the server access to the repository**: copy the public deploy key (see 3.3) and add it in the repository settings with **write** access. The server can then read the config and save changes.

### **3.3. Git: deploy key and config sync**

Config (`collector/config.json`), visualization (`collector/viz.json`), and instruction media (`collector/media/`) live in the project's Git repository.

- On the project card, open **"SSH key"** — the **public deploy key** is shown there. Add it to the repository (Deploy keys) with **write access**. If needed, you can paste your own private key instead.
- The **"Check Git"** button on the card performs sync (pull) and on first run may create a starter `config.json`.
- Saving in the editor/JSON = commit + push to the repository.

Principle: **1 repository = 1 project**.

### **3.4. Data storage (DB and media) — optional**

Where **packages and media** for a specific project are stored is configured separately (project card → **Storage** section). If fields are empty — **SQLite + local folder** on the server (fine for getting started).

Fields:

- **Media (blobs)** — `storage_uri`: for example `s3://bucket/my-project/` or `gs://bucket/`. Empty — local folder.
- **S3 / MinIO** — endpoint, key, and secret (only needed for `s3://`).
- **PostgreSQL — address** — `database_uri` without login/password (for example `postgresql+psycopg2://host:5432/proj_my_project`). **The database is created automatically** on save.
- **PostgreSQL — login and password** — separate fields.

After changing the address, click **"Check storage"**. Changing the address **does not migrate** already stored data.

### **3.5. Project card**

Open a project from the list. On the card:

![Project card](<image 3.png>)

**Basic information:**

- config version;
- list of files on disk — media for instructions (for example, reference frames/angles);
- number of package upload sessions — you can open uploaded packages for this project.

**Buttons:**

- **Editor** — visual config editor;
- **JSON** — project configuration as JSON;
- **Files** — upload files for instructions;
- **Packages** — view uploaded packages for the project;
- **SSH key**, **Storage**, **Check Git/storage** — Git and storage setup (see 3.3–3.4).

![Project card: actions](<image 4.png>)

### **3.6. Visual editor (collection scenario setup)**

The config defines **what** the mobile app collects: fields, screens, step order.

To edit the config, go to the visual editor ("Editor" button):

![Visual config editor](<image 5.png>)

Main elements:

1. **Fields** — define fields for the app (text, date, instructions (md), photos, etc.).
    
    ![Editor: fields](<image 6.png>)
    
2. **Scenario (flow)** — order and placement of fields across screens: `scroll_form` (scrollable form) and `review` (review before submit).
    
    ![Editor: scenario (flow)](<image 7.png>)
    
3. **JSON mode** — edit the entire config file manually for experienced administrators.
    
    ![Editor: JSON mode](<image 8.png>)
    

### **3.7. Project files (media)**

The **"Files"** section on the project card:

- upload images and other files for instructions in the config;
- files are served to the client as `/v1/projects/<project_id>/assets/…`;
- in JSON/Markdown, use paths like `assets/uploads/…`.

![Project files](<image 9.png>)

### **3.8. Deleting a project**

At the bottom of the card — **"Danger zone"**. To confirm, enter the exact `project_id`. Only the catalog entry and local git cache are removed; package files and the project database are preserved.

---

## **4. Users (mobile app access)**

Users sign in to the app via **Firebase** (email/password). The panel stores the mapping Firebase UID ↔ accessible projects.

### **4.1. Users appearing in the list**

- Click **"Sync with Firebase"** — pull accounts from Firebase Authentication;
- **or** wait for the user's first sign-in to the app (a record may be created automatically).

![User list](<image 10.png>)

### **4.2. Assigning projects**

1. Open a user → **"Configure"**.
2. Check the projects they see in the app and can upload packages to.
3. Click **"Save"**.

![Assigning projects to a user](<image 11.png>)

---

## **5. Packages (field data)**

The **Packages** section contains everything operators sent from phones.

### **5.1. List**

- Up to **500** most recent sessions.
- Filter by project in the dropdown.
- Columns: project, `package_id`, uploader email/UID, **phase**, date.

![Package list](<image 12.png>)

### **5.2. Ingestion phases**

| **Phase** | **Meaning** |
| --- | --- |
| **awaiting_blobs** | Awaiting files (photos, etc.) |
| **ready_to_commit** | Files received, awaiting finalization |
| **completed** | Package successfully accepted |
| **failed** | Error during ingestion |

### **5.3. Package card (workspace)**

The package workspace has tabs. At the top — project package switcher and **"Revert" / "Save"** buttons (manifest edits are written to the change history).

| Tab | What it shows |
| --- | --- |
| **Data** | Form field values (per `config.fields`), grouped by step. Fields can be edited here. |
| **Media** | All package blobs (photos) with preview and **"Download"** button; in-form shots are marked with a badge. |
| **Visualization** | Pipeline overlays on frames (see 5.4). |
| **Change history** | Who changed what in the manifest and when (before → after, reason). |

**"Data" tab**

![Data tab](workspace-data.png)

**"Media" tab**

![Media tab](workspace-media.png)

**"Change history" tab**

![Change history tab](workspace-history.png)

**Details** also opens the **blob** list (files) with **"Download"** and the **manifest** (JSON after upload completes).

![Package blobs and manifest](<image 13.png>)

The package list for a specific project is also available from the project card (**"Packages"**).

### **5.4. Visualization (viewing pipeline results)**

The **"Visualization"** tab draws pipeline data (keypoints, bbox, depth, annotations) **over package frames**. Visualization config is stored in the project's Git repository — file `collector/viz.json` (layers → tables in project DB + rendering plugin). Details — [`specs/collector-vis-config.md`](../../specs/collector-vis-config.md).

![Visualization tab: keypoints and metrics](workspace-visualization.png)

What's on screen:

- **Layer toggles** at the top: for example **GT** (ground truth) and **Inference** (model prediction), **Depth**, **BBox** (object box), **Labels** (point/measurement names).
- **CVAT** — link to frame annotation in CVAT; **Export** — export visualization.
- **Point list** on the right (`kp_1`, `kp_2`, …) with model confidence (%).
- **Metrics (cm)** — derived measurements for the object (in the cattle example: body length, withers/croup height, chest girth behind shoulder blades, etc.).
- At the bottom — package frame strip to switch between photos.

Layer set and plugins are defined per project. Available rendering plugins: keypoints, bbox/detection (YOLO), depth map, CVAT link. For visualization to appear, the project repository must have `collector/viz.json`, and the project DB must have tables with pipeline data.

---

## **6. Typical administrator workflow**

1. **Create a project**: specify `project_id`, name, **Git repository**, and generate an SSH key.
2. **Grant server access to the repository**: add the public deploy key with write access, click **"Check Git"**.
3. (Optional) **Configure storage** (DB/media) and click **"Check storage"**; otherwise — SQLite + local folder.
4. In the **editor**, configure fields and the collection scenario; upload images to **"Files"** if needed.
5. **Save** the config (commit/push) and verify the version on the project card.
6. In **Users**, sync Firebase and grant staff access to the project.
7. After field work — in **Packages**, check status, view data/visualization, download files/manifest.

---

## **7. Connection to the mobile app**

| **Admin action** | **Effect in the app** |
| --- | --- |
| Project and config created/changed | Project and collection form appear after sync |
| Projects assigned to user | Project visible on the **Project** tab |
| Files uploaded to "Files" | Images in instructions load via API |
| Package accepted on server | Visible in admin; on phone — in upload history/status |

More about operator workflow — [mobile app guide](../mobile-app/README.md).

---
