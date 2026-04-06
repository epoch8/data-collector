# User Journey & Screens

## 1. Authentication Flow
* **Login Screen:** User enters credentials.
* *Error Handling:* Invalid credentials flash message.
* *Success:* Proceed to Dashboard; tokens stored securely.

## 2. Dashboard & Projects List
* **Dashboard Screen:** 
  * Header shows User Profile & Sync Status.
  * List of assigned `Projects`.
  * Visual indicator for Projects (e.g., "X packages collected", "Y configs pending update").
* **Action:** Clicking a Project opens the Project Details Screen.

## 3. Project Details & History
* **Project Dashboard:**
  * Tab 1: **History:** List of all packages collected for this project. Shows indicators for (Draft, Pending Upload, Uploaded, Enriched).
  * Tab 2: **Config Overview:** Brief overview of what this project collects.
* **Action:** Floating Action Button (FAB) -> `"+" (New Collection)` triggers the Guided Collection Flow.

## 4. Data Collection Form (Open Flow)
* Single scrollable UI ordered by the `Config` schema's priority fields.
* **Form Layout (Dynamic):**
  * All required fields are displayed on a single scrollable form.
  * User can fill out fields out-of-order if they need to.
  * Inputs: Camera viewfinder, text fields, or selection widgets depending on `type`.
  * Visual indicators for validation (e.g., green checkmark for completed photo).
* **Auto-Save:** User can exit at any point; the drafted Package is saved locally.
* **Action:** Submit -> Validates fields exist, saves Package as "Completed" and optionally triggers the Upload worker.

## 5. Enriched Data Viewer
* Accessible from the History tab in the Project Dashboard.
* **Visualizing specific steps:** If a photo step has an ML prediction, we display read-only bounding boxes or tags layered over the image.
