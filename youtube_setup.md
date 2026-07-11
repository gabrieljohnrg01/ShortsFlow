# 📺 YouTube Upload Setup Guide

To allow ShortsFlow to automatically upload videos to your YouTube channel, you need to provide it with permission via the Google Cloud Console. Follow these steps to generate the required `client_secrets.json` file.

## Step 1: Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown near the top-left and select **New Project**.
3. Name it "ShortsFlow" (or anything you like) and click **Create**.
4. Make sure your new project is selected.

## Step 2: Enable the YouTube Data API v3
1. In the search bar at the top, type **YouTube Data API v3** and select it.
2. Click the blue **Enable** button.

## Step 3: Configure the OAuth Consent Screen
1. Go to **APIs & Services > OAuth consent screen** from the left-hand navigation menu.
2. Select **External** (unless you are a Google Workspace user and want it internal) and click **Create**.
3. **App information**: Give your app a name (e.g., "ShortsFlow Uploader") and enter your email address for support.
4. Scroll down and enter your email again in the **Developer contact information** section, then click **Save and Continue**.
5. **Scopes**: You can skip this page and click **Save and Continue**.
6. **Test users**: Click **Add Users** and add the email address of the YouTube channel you want to upload to. *This is critical, otherwise you won't be able to log in.* Click **Save and Continue**.

## Step 4: Create Credentials
1. Go to **APIs & Services > Credentials** from the left-hand menu.
2. Click **+ Create Credentials** at the top and select **OAuth client ID**.
3. Under **Application type**, select **Desktop app**.
4. Give it a name (e.g., "ShortsFlow Desktop") and click **Create**.
5. A window will pop up with your Client ID and Secret. Click the **Download JSON** button to download the credential file.

## Step 5: Add to ShortsFlow
1. Rename the downloaded file to exactly `client_secrets.json`.
2. Move this `client_secrets.json` file into the main folder of your ShortsFlow project (the same folder as `main.py`).

## Step 6: First-Time Authentication
The first time you run `scheduler.py` or `main.py` and it tries to upload a video, it will automatically open a browser window (or give you a URL in the terminal) asking you to log in. 
- Log in with the Google account that owns the YouTube channel. 
- You will likely see a warning saying "Google hasn't verified this app." Click **Advanced** and then **Go to [App Name] (unsafe)**.
- Grant the requested permissions.

Once completed, a `token.json` file will be created in your folder. ShortsFlow will use this token to upload all future videos without ever needing you to log in again!
