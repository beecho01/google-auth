# Google Auth — Master Token Retriever

A NiceGUI-based web application for Google OAuth2 authentication and master token retrieval via `gpsoauth`. Retrieve Google master tokens through two methods: an automatic OAuth2 redirect flow or a manual EmbeddedSetup flow.

---

## Features

- **OAuth2 redirect flow** — Click "Sign in with Google" for automatic authentication and token retrieval
- **EmbeddedSetup manual flow** — Authenticate via Google's EmbeddedSetup page with no Cloud Console configuration needed
- **Master token exchange** — Exchange OAuth2 tokens for a Google master token using `gpsoauth`
- **Copy to clipboard** — One-click copy for access tokens and master tokens
- **Full response viewer** — Expandable JSON view of the complete `gpsoauth` response
- **Dual credential loading** — Load Google OAuth credentials from `.env` or `client_secret.json`

---

## Prerequisites

- **Python 3.14+**
- **Google Cloud Console project** with an OAuth 2.0 Client ID (required for Method 1 only)
  - Create an OAuth client at [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
  - Add `http://localhost:5012/auth` (or your custom port) to **Authorized redirect URIs**
  - Use **localhost** (not `127.0.0.1`) — Google requires this for the redirect URI

---

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/google-auth.git
   cd google-auth
   ```

2. **Install dependencies with [uv](https://docs.astral.sh/uv/):**

   ```bash
   uv sync
   ```

3. **Configure credentials** — see [Configuration](#configuration) below.

---

## Configuration

### Environment Variables (`.env`)

Create a `.env` file in the project root:

```env
EMAIL=your-email@gmail.com
ANDROID_ID=0123456789abcdef
PORT=5012
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `EMAIL` | No | `""` | Default email for master token exchange |
| `ANDROID_ID` | No | `0123456789abcdef` | Android device ID used by `gpsoauth` |
| `PORT` | No | `5012` | Port the app listens on |
| `GOOGLE_CLIENT_ID` | No* | — | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | No* | — | Google OAuth2 client secret |

\* If `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are not set in `.env`, the app loads them from `client_secret.json` automatically.

### `client_secret.json`

Download this file from the [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) page (click **Download JSON** on your OAuth 2.0 client). Place it in the project root. It must follow the `installed` application format:

```json
{
  "installed": {
    "client_id": "your-client-id.apps.googleusercontent.com",
    "client_secret": "your-client-secret",
    ...
  }
}
```

> ⚠️ **Security:** `client_secret.json` contains sensitive credentials. **Never commit it to version control.** Add it to `.gitignore`.

---

## Usage

Run the application:

```bash
uv run main.py
```

Or directly:

```bash
uv run python main.py
```

The app starts at **http://localhost:5012**.

### Method 1: Sign in with Google (OAuth2 Redirect)

1. Ensure `http://localhost:<PORT>/auth` is listed in your Google Cloud Console **Authorized redirect URIs**.
2. Click **"Sign in with Google"** on the main page.
3. Authenticate with Google in the redirect flow.
4. The app exchanges the OAuth2 token for a master token automatically.

### Method 2: EmbeddedSetup (No Cloud Console Setup Needed)

1. Click **"Open EmbeddedSetup in new tab"** on the main page.
2. Sign in to Google and agree to the terms.
3. Open browser DevTools → **Application** → **Cookies** and find the `oauth_token` cookie (starts with `oauth2_4/...`).
4. Copy the cookie value and paste it into the **oauth_token value** input field.
5. Click **"Exchange for master token"**.

---

## How It Works

### OAuth2 Redirect Flow (Method 1)

The app uses `authlib` to initiate a standard OAuth2 authorization code flow with Google. After the user authenticates, Google redirects back to `/auth` with an authorization code. The app exchanges this code for an access token and ID token, validates the token claims, and then attempts to exchange the access token for a Google master token via `gpsoauth.exchange_token()`.

### EmbeddedSetup Flow (Method 2)

This method uses Google's device/installed-app authentication flow. The user opens Google's EmbeddedSetup page directly, authenticates, and extracts the `oauth_token` cookie from their browser. The app then passes this token to `gpsoauth.exchange_token()` along with the configured email and Android ID to retrieve the master token. No redirect URI configuration is required.

---

## License

This project is licensed under the terms found in the `LICENSE` file.

---

## Acknowledgements

- [gpsoauth](https://github.com/simon-weber/gpsoauth) — Google Play Services OAuth2 token exchange
- [NiceGUI](https://nicegui.io) — Python-based web UI framework
- [Authlib](https://authlib.org) — OAuth2 client library for Python
- [itsdangerous](https://itsdangerous.palletsprojects.com/) — Secure data signing