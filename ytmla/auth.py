"""OAuth for the YouTube Data API.

Scope note: `youtube.upload` alone is NOT enough. Setting localizations, status and
thumbnails needs `youtube.force-ssl`. Requesting only `.upload` produces 403s on update.
"""
from __future__ import annotations
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def load_token(creds_path: str | Path, client_secret: str | Path) -> Credentials:
    """Load a stored token, refreshing if needed.

    Accepts the `installed` or `web` shape of client_secret.json, and tolerates a token
    file that stores only refresh_token (as long as client id/secret are in the secret file).
    """
    cp, sp = Path(creds_path), Path(client_secret)
    secret = json.loads(sp.read_text())
    secret = secret.get("installed") or secret.get("web") or secret
    tok = json.loads(cp.read_text())
    creds = Credentials(
        token=tok.get("token"),
        refresh_token=tok["refresh_token"],
        token_uri=tok.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=tok.get("client_id") or secret["client_id"],
        client_secret=tok.get("client_secret") or secret["client_secret"],
        scopes=tok.get("scopes") or SCOPES,
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds


def authorize(client_secret: str | Path, token_out: str | Path, port: int = 0) -> Credentials:
    """One-time interactive consent; writes a token file for later headless use."""
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    creds = flow.run_local_server(port=port)
    Path(token_out).write_text(creds.to_json())
    return creds


def service(creds_path: str | Path, client_secret: str | Path):
    return build("youtube", "v3",
                 credentials=load_token(creds_path, client_secret),
                 cache_discovery=False)
