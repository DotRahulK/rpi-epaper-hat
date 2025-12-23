from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional
from urllib import request

import spotipy
from spotipy.oauth2 import SpotifyOAuth


@dataclass(frozen=True)
class TrackInfo:
    track_id: str
    title: str
    artist: str
    art_url: Optional[str]
    is_playing: bool


class SpotifyController:
    def __init__(self) -> None:
        client_id = os.environ.get("SPOTIPY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
        redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")
        if not client_id or not client_secret or not redirect_uri:
            raise ValueError(
                "Missing SPOTIPY_CLIENT_ID/SPOTIPY_CLIENT_SECRET/SPOTIPY_REDIRECT_URI."
            )

        cache_path = os.environ.get("SPOTIPY_CACHE_PATH", ".cache-spotipy")
        scope = (
            "user-read-playback-state user-read-currently-playing "
            "user-modify-playback-state user-library-modify"
        )
        self._sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scope,
                cache_path=cache_path,
            )
        )
        self._art_cache_dir = os.environ.get("SPOTIFY_ART_CACHE", "/tmp/spotify-art")
        os.makedirs(self._art_cache_dir, exist_ok=True)

    def current_track(self) -> Optional[TrackInfo]:
        playback = self._sp.current_playback()
        if not playback or not playback.get("item"):
            return None
        item = playback["item"]
        track_id = item.get("id")
        if not track_id:
            return None
        title = item.get("name", "")
        artist = ", ".join(artist["name"] for artist in item.get("artists", []))
        images = item.get("album", {}).get("images", [])
        art_url = images[0]["url"] if images else None
        return TrackInfo(
            track_id=track_id,
            title=title,
            artist=artist,
            art_url=art_url,
            is_playing=bool(playback.get("is_playing")),
        )

    def toggle_play_pause(self) -> None:
        playback = self._sp.current_playback()
        if not playback:
            return
        if playback.get("is_playing"):
            self._sp.pause_playback()
        else:
            self._sp.start_playback()

    def next_track(self) -> None:
        self._sp.next_track()

    def like_current(self) -> None:
        playback = self._sp.current_playback()
        if not playback or not playback.get("item"):
            return
        track_id = playback["item"].get("id")
        if not track_id:
            return
        self._sp.current_user_saved_tracks_add([track_id])

    def get_album_art(self, track_id: str, art_url: Optional[str]) -> Optional[bytes]:
        if not track_id or not art_url:
            return None
        cache_path = os.path.join(self._art_cache_dir, f"{track_id}.jpg")
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as handle:
                return handle.read()
        try:
            with request.urlopen(art_url, timeout=10) as response:
                data = response.read()
        except Exception:
            return None
        try:
            with open(cache_path, "wb") as handle:
                handle.write(data)
        except OSError:
            pass
        return data
