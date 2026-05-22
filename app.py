"""
NiceGUI app for Google OAuth2 authentication and master token retrieval.

Two methods are available:

  Method 1 — OAuth2 redirect flow (requires Cloud Console setup):
    Click "Sign in with Google" for automatic token retrieval.
    Requires adding http://localhost:<PORT>/auth to "Authorized redirect URIs"
    in your Google Cloud Console OAuth client settings.

  Method 2 — EmbeddedSetup (no Cloud Console changes needed):
    Open Google's EmbeddedSetup page, sign in, then manually copy the
    'oauth_token' cookie from DevTools and paste it below.
    This uses Google's device/installed-app flow — no redirect URI needed.

Credentials are loaded from .env or client_secret.json.
"""

import json
import logging
import os
import time
from pathlib import Path

from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv
from fastapi import Request
from starlette.responses import RedirectResponse

from nicegui import app, ui

import gpsoauth

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

EMAIL = os.getenv("EMAIL", "")
ANDROID_ID = os.getenv("ANDROID_ID", "0123456789abcdef")
PORT = int(os.getenv("PORT", 5012))

# Load Google OAuth credentials from .env or client_secret.json
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    _secret_path = Path(__file__).parent / "client_secret.json"
    if _secret_path.exists():
        with open(_secret_path) as f:
            _secret = json.load(f)["installed"]
        GOOGLE_CLIENT_ID = GOOGLE_CLIENT_ID or _secret["client_id"]
        GOOGLE_CLIENT_SECRET = GOOGLE_CLIENT_SECRET or _secret["client_secret"]

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError(
        "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env "
        "or provide a client_secret.json file."
    )

# ---------------------------------------------------------------------------
# OAuth2 setup (authlib + Starlette)
# ---------------------------------------------------------------------------
oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    client_kwargs={"scope": "openid email profile"},
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAuth callback endpoint
# ---------------------------------------------------------------------------
@app.get("/auth")
async def google_oauth(request: Request) -> RedirectResponse:
    """Handle the OAuth2 redirect callback from Google."""
    try:
        token_data = await oauth.google.authorize_access_token(request)
        user_info = token_data.get("userinfo", {})

        # Validate the token
        if not _is_valid(user_info):
            logger.warning("Invalid user info received from Google")
            return RedirectResponse("/?error=invalid_token")

        # Store user info and tokens
        app.storage.user["user_info"] = user_info
        app.storage.user["access_token"] = token_data.get("access_token", "")
        app.storage.user["refresh_token"] = token_data.get("refresh_token", "")

        # Try to get master token using the access token
        _try_master_token(token_data, user_info)

    except (OAuthError, Exception):
        logging.exception("Could not authorize access token")
        return RedirectResponse("/?error=auth_failed")

    return RedirectResponse("/")


def _is_valid(user_info: dict) -> bool:
    """Validate Google OAuth2 user info."""
    try:
        return all(
            [
                int(user_info.get("exp", 0)) > int(time.time()),
                user_info.get("aud") == GOOGLE_CLIENT_ID,
                user_info.get("iss")
                in {"https://accounts.google.com", "accounts.google.com"},
                str(user_info.get("email_verified", "")).lower() == "true",
            ]
        )
    except Exception:
        return False


def _try_master_token(token_data: dict, user_info: dict) -> None:
    """Attempt to exchange the OAuth token for a gpsoauth master token."""
    email = user_info.get("email", EMAIL)
    access_token = token_data.get("access_token", "")

    if not email or not access_token:
        return

    try:
        master_response = gpsoauth.exchange_token(email, access_token, ANDROID_ID)
        if "Token" in master_response:
            app.storage.user["master_token"] = master_response["Token"]
            app.storage.user["master_response"] = master_response
    except Exception:
        logging.exception("Failed to exchange for master token")


# ---------------------------------------------------------------------------
# UI Pages
# ---------------------------------------------------------------------------
@ui.page("/")
async def main_page(request: Request):
    """Main page — shows login or results depending on auth state."""

    user_info = app.storage.user.get("user_info", {})
    error = request.query_params.get("error")

    # --- Header ---
    ui.label("Google Auth — Master Token Retriever").classes("text-h4 q-mb-md")

    if error:
        ui.label(f"⚠️ Error: {error}").classes("text-red q-mb-md")

    if not user_info:
        # Not logged in — show both methods
        ui.label("Choose a method to authenticate:").classes("text-body1 q-mb-md")

        # Method 1: OAuth2 redirect flow
        with ui.card().classes("w-full q-mb-lg"):
            ui.label("Method 1: Sign in with Google (OAuth2 redirect)").classes("text-h6")
            ui.label(
                "Automatic flow — requires http://localhost:{PORT}/auth "
                "in your Cloud Console redirect URIs."
            ).classes("text-body2 text-grey q-mb-sm")

            async def on_login():
                redirect_uri = request.url_for("google_oauth")
                await oauth.google.authorize_redirect(request, redirect_uri)

            ui.button("Sign in with Google", on_click=on_login).props(
                "color=primary icon=login"
            )

        # Method 2: EmbeddedSetup manual flow
        _manual_token_section()

    else:
        # Logged in — show results
        _show_results(user_info)


def _show_results(user_info: dict):
    """Display the authenticated user's info and tokens."""

    with ui.card().classes("w-full q-mb-lg"):
        ui.label(f"✅ Authenticated as: {user_info.get('email', 'unknown')}").classes(
            "text-h6 text-green"
        )
        ui.label(f"Name: {user_info.get('name', 'N/A')}").classes("text-body1")
        ui.label(f"Email verified: {user_info.get('email_verified', False)}").classes(
            "text-body2"
        )

    # Access token
    access_token = app.storage.user.get("access_token", "")
    if access_token:
        with ui.card().classes("w-full q-mb-lg"):
            ui.label("Access Token").classes("text-h6")
            ui.code(access_token[:80] + "..." if len(access_token) > 80 else access_token)
            ui.button("Copy", on_click=lambda: ui.run_javascript(f'navigator.clipboard.writeText("{access_token}")')).props(
                "flat icon=content_copy size=sm"
            )

    # Master token
    master_token = app.storage.user.get("master_token")
    master_response = app.storage.user.get("master_response")

    if master_token:
        with ui.card().classes("w-full q-mb-lg"):
            ui.label("Master Token").classes("text-h6 text-green")
            ui.code(master_token).classes("w-full")
            ui.button(
                "Copy",
                on_click=lambda: ui.run_javascript(f'navigator.clipboard.writeText("{master_token}")'),
            ).props("flat icon=content_copy size=sm")
    else:
        with ui.card().classes("w-full q-mb-lg"):
            ui.label("Master Token").classes("text-h6 text-orange")
            ui.label(
                "The OAuth2 access token could not be exchanged for a master token "
                "automatically. Use the manual method below."
            ).classes("text-body2 text-grey")

    # Full response
    if master_response:
        with ui.expansion("Full gpsoauth response (JSON)", icon="data_object").classes(
            "w-full q-mb-lg"
        ):
            ui.code(json.dumps(master_response, indent=2), language="json")

    # Method 2 fallback
    _manual_token_section()

    # Logout
    ui.button("Logout", on_click=_logout).props("color=negative icon=logout").classes(
        "q-mt-lg"
    )


EMBEDDED_SETUP_URL = "https://accounts.google.com/EmbeddedSetup"


def _manual_token_section():
    """Manual oauth_token input fallback using EmbeddedSetup (no redirect URI needed)."""
    with ui.card().classes("w-full q-mb-lg"):
        ui.label("Method 2: EmbeddedSetup (no Cloud Console setup needed)").classes("text-h6")
        ui.label(
            "Open Google's EmbeddedSetup page, sign in and agree to terms, "
            "then find the 'oauth_token' cookie (starts with oauth2_4/...) "
            "in DevTools → Application → Cookies and paste it below."
        ).classes("text-body2 text-grey q-mb-sm")

        ui.button(
            "Open EmbeddedSetup in new tab",
            on_click=lambda: ui.run_javascript(f'window.open("{EMBEDDED_SETUP_URL}", "_blank")'),
        ).props("icon=open_in_new").classes("q-mb-sm")

        token_input = ui.input(
            "oauth_token value",
            placeholder="oauth2_4/...",
        ).classes("w-full").props("outlined")

        result_label = ui.label("").classes("text-body1 q-mt-md")

        async def on_exchange():
            token = token_input.value.strip()
            if not token:
                result_label.text = "⚠️ Please paste the oauth_token value first."
                result_label.classes(remove="text-green", add="text-red")
                return

            result_label.text = "⏳ Exchanging token..."
            result_label.classes(remove="text-red text-green", add="text-orange")

            try:
                email = app.storage.user.get("user_info", {}).get("email", EMAIL)
                master_response = gpsoauth.exchange_token(email, token, ANDROID_ID)

                if "Token" not in master_response:
                    error = master_response.get("Error", "Unknown error")
                    result_label.text = f"❌ Error: {error}"
                    result_label.classes(remove="text-orange text-green", add="text-red")
                else:
                    app.storage.user["master_token"] = master_response["Token"]
                    app.storage.user["master_response"] = master_response
                    result_label.text = f"✅ Master token: {master_response['Token']}"
                    result_label.classes(remove="text-orange text-red", add="text-green")

            except Exception as e:
                result_label.text = f"❌ Exception: {e}"
                result_label.classes(remove="text-orange text-green", add="text-red")

        ui.button("Exchange for master token", on_click=on_exchange).classes(
            "q-mt-sm"
        ).props("color=primary")


def _logout():
    """Clear stored user info and redirect to main page."""
    app.storage.user.pop("user_info", None)
    app.storage.user.pop("access_token", None)
    app.storage.user.pop("refresh_token", None)
    app.storage.user.pop("master_token", None)
    app.storage.user.pop("master_response", None)
    ui.navigate.to("/")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def start():
    """Entry point for the NiceGUI app."""
    ui.run(
        title="Google Auth — Master Token Retriever",
        host="localhost",  # Required for Google OAuth2 (not 127.0.0.1)
        port=PORT,
        reload=False,
        show=False,
        storage_secret="change-this-to-a-random-secret",
    )


if __name__ == "__main__":
    start()