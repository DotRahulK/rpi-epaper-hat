#!/usr/bin/env bash

# Print the Spotify OAuth URL for the current .env settings.
# Usage:
#   source /home/dot/venvs/waveshare/bin/activate
#   set -a; source .env; set +a
#   bash scripts/spotify-auth-url.sh

set -euo pipefail

python - <<'PY'
import os
from spotipy.oauth2 import SpotifyOAuth

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
print(auth.get_authorize_url())
PY
