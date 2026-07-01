> **Language / Язык:** **English** · [Русский](README.ru.md)

# User guide: mobile app

> **This is an example** user journey on a specific project — cattle data collection
> (project "Хозяйство" / `korovas`). It shows the **general data_collector framework flow**:
> sign-in → project selection → filling the form per config → sending a package to the server.
> In your project, fields and steps will differ — they are defined by config in the admin panel
> (see [admin panel guide](../admin-panel/README.md)), but the workflow is the same.

Screenshots below are from the product presentation ([`specs/presentation/img/Flutter_en/`](../../specs/presentation/img/Flutter_en/)), assembled as an animated walkthrough.

## **Main workflow**

Sign in → configs from server → fill the form (multiple steps) → project cache and upload.

![Mobile app: sign-in, config, form, upload](../../specs/presentation/img/flutter-steps-app-en.gif)

### **1. Signing in**

Enter credentials (example):

- **Login:** `kcow@epoch8.com`
- **Password:** `kcow@123`

### **2. Selecting a project**

1. Open the **Project** tab.
2. Select the **Хозяйство** project.

**Important:** access configuration and project step customization are set by the administrator in the admin panel. See the admin panel guide for details.

Expected model: **one project per farm**. Projects may share structure but differ by name (farm name).

### **3. Filling in project fields**

Fill in the selected project's fields according to the data collection scenario requirements. The form is driven by the project config: general parameters, shooting instructions, photo capture steps, and a review screen before submit.

### **4. Uploading data to the server**

Collected packages are initially saved locally on the phone; after data collection, send packages to the server for further processing.

1. Go to the **Server** tab.
2. Click **Upload** (cloud-with-arrow icon) to send data to the server.

---

## **5. Additional features**

| **Feature** | **Description** |
| --- | --- |
| **Package upload history** | View history and current status of a package (sending, delivery, errors, etc.). Each cow can be grouped into its own package; history is available per cow and per farm. |
| **Theme** | Switch between light and dark theme for comfortable use in different lighting conditions. |
| **Interface language** | Switch language; labels and UI elements display in the selected language. Russian and English are available now; other languages can be added if needed. |
| **Help** | The help button (question mark on the home screen) opens a brief guide to using the app. |
| **Session** | When reopening the app, the session is **restored automatically** (where supported by app logic). |
| **Pre-fill fields from local history** | If cattle data was previously entered on the phone, it is automatically pulled from the local database. |
| **Frame quality check** | Checks the frame for blur and under/over-exposure. |
