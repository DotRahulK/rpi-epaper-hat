#!/usr/bin/env bash

# Complete Spotify OAuth by pasting the full redirect URL.
# Usage:
#   source /home/dot/venvs/waveshare/bin/activate
#   set -a; source .env; set +a
#   bash scripts/spotify-auth-url.sh
#   # Open the URL in a browser, login, then copy the full redirect URL.
#   bash scripts/spotify-auth-complete.sh "http://127.0.0.1:8000/callback?code=..."
# Or run without args and paste when prompted.

set -euo pipefail

redirect_url="${1:-}"

python - "$redirect_url" <<'PY'
import os
import sys
from spotipy.oauth2 import SpotifyOAuth

redirect_url = sys.argv[1] if len(sys.argv) > 1 else ""
if not redirect_url:
    redirect_url = input("Paste the full redirect URL: ").strip()

scope = (
    "user-read-playback-state user-read-currently-playing "
    "user-modify-playback-state user-library-modify"
)
auth = SpotifyOAuth(
    client_id=os.environ["SPOTIPY_CLIENT_ID"],
    client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
    scope=scope,
    cache_path=os.environ.get("SPOTIPY_CACHE_PATH", ".cache-spotipy"),
)
code = auth.parse_response_code(redirect_url)
if not code:
    print("Could not parse code from redirect URL.", file=sys.stderr)
    sys.exit(1)

token_info = auth.get_access_token(code, as_dict=True)
if not token_info:
    print("Failed to exchange code for token.", file=sys.stderr)
    sys.exit(1)

print("Token cached successfully.")
PY
