> **Language / Язык:** **English** · [Русский](README.ru.md)

# User guide: mobile app

> **This is an example** user journey on a specific project — cattle data collection
> (project "Хозяйство" / `korovas`). It shows the **general data_collector framework flow**:
> sign-in → project selection → filling the form per config → sending a package to the server.
> In your project, fields and steps will differ — they are defined by config in the admin panel
> (see [admin panel guide](../admin-panel/README.md)), but the workflow is the same.

## **1. Signing in to the app**

Enter credentials:

- **Login:** `kcow@epoch8.com`
- **Password:** `kcow@123`

![photo_5467504367679247761_y (1).jpg](photo_5467504367679247761_y_(1).jpg)

---

## **2. Selecting a project**

1. Open the **Project** tab.
2. Select the **Хозяйство** project.

**Important:** access configuration and project step customization are set by the administrator in the admin panel. See the admin panel guide for details.

Expected model: **one project per farm**. Projects may share structure but differ by name (farm name).

![image.png](image.png)

---

## **3. Filling in project fields**

Fill in the selected project's fields according to the data collection scenario requirements.

### Step 1. General parameters

![image.png](image%201.png)

### Step 2. General shooting instructions

![image.png](image%202.png)

### Steps 3–5. Instructions with examples and photo upload window (multiple angles) with sequential angle changes

![image.png](image%203.png)

### Step 6. Review form with the option to correct

![photo_5203923388659864690_y.jpg](photo_5203923388659864690_y.jpg)

## **4. Uploading data to the server**

Collected packages are initially saved locally on the phone; after data collection, send packages to the server for further processing.

1. Go to the **Server** tab.
2. Click **Upload** (cloud-with-arrow icon) to send data to the server.

![image.png](image%204.png)

---

## **5. Additional features**

| **Feature** | **Description** |
| --- | --- |
| **Package upload history** | **View history** and **current status** of a package (sending, delivery, errors, etc. — adjust wording to match your UI statuses). |
| **Theme** | Switch between light and dark theme. |
| **Interface language** | Switch language; labels and UI elements display in the selected language. Russian and English are available now; other languages can be added if needed. |
| **Help** | The help button opens a brief guide to using the app. |
| **Session** | When reopening the app, the session is **restored automatically** (where supported by app logic). |
| **Pre-fill fields from local history** | If cattle data was previously entered on the phone, it is automatically pulled from the local database |
| **Frame quality check** | Checks the frame for blur and under/over-exposure |
- **Package upload history**
    
    Each cow is grouped into its own package; you can view history of data collected per cow separately
    
    ![Data history grouped by cows and farms](photo_5203923388659864767_y.jpg)
    
    Data history grouped by cows and farms
    
    ![Packages collected per individual cow](photo_5203923388659864761_y.jpg)
    
    Packages collected per individual cow
    
    ![View package contents with export option](photo_5203923388659864748_y.jpg)
    
    View package contents with export option
    
- **Theme**
    
    ![Light and dark themes available for comfortable use in different lighting conditions](photo_5467504367679247783_y_(1).jpg)
    
    Light and dark themes available for comfortable use in different lighting conditions
    
- **Interface language**
    
    ![photo_5467504367679247784_y (1).jpg](photo_5467504367679247784_y_(1).jpg)
    
    ![photo_5467504367679247783_y (2).jpg](photo_5467504367679247783_y_(2).jpg)
    
- **Help**
    
    ![Help screen opens when tapping the question mark icon on the app home screen](photo_5467504367679247803_y_(1).jpg)
    
    Help screen opens when tapping the question mark icon on the app home screen
    
- **Session restore**
    
    ![image.png](image%205.png)
    
- **Pre-fill fields from local history**
    
    ![image.png](image%206.png)
    
- **Frame quality check**
    
    ![image.png](image%207.png)
