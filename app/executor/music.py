"""
Local music playback executor for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
Security Hardening: Honest execution reporting and sandbox containment on audio paths.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import get_config
from app.core.constants import INTENT_PLAY_MUSIC, SUPPORTED_AUDIO_EXTENSIONS
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.executor.files import is_allowed_path
from app.executor.result import (
    STATUS_EXECUTION_ERROR,
    STATUS_FAILED,
    STATUS_NOT_SUPPORTED,
    STATUS_PATH_NOT_ALLOWED,
    STATUS_SUCCESS,
    ExecutionResult,
)

logger = get_logger("riata.executor.music")


def find_audio_files(directory: Path) -> list[Path]:
    """Scan music directory recursively for supported audio tracks."""
    if not directory.exists() or not directory.is_dir():
        return []

    tracks: list[Path] = []
    try:
        for ext in SUPPORTED_AUDIO_EXTENSIONS:
            tracks.extend(directory.rglob(f"*{ext}"))
            tracks.extend(directory.rglob(f"*{ext.upper()}"))
    except Exception as e:
        logger.debug("Error scanning audio directory %s: %s", directory, e)

    # Sort tracks alphabetically by stem
    return sorted(list(set(tracks)), key=lambda p: p.stem.lower())


def execute_play_music(intent: Intent) -> ExecutionResult:
    """Execute PLAY_MUSIC intent using local files."""
    config = get_config()
    music_dir = Path(config.music_directory).expanduser().resolve()

    # Ensure directory exists
    if not music_dir.exists():
        try:
            music_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # Direct selection passed via entity (from context disambiguation)
    selected_path = intent.entities.get("selected_path")
    if selected_path:
        track_path = Path(selected_path).expanduser().resolve()
        # Security sandbox check on track path
        if not is_allowed_path(track_path, allow_tmp=True):
            logger.warning("Selected audio path escapes allowed sandbox: %s", track_path)
            return ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_PATH_NOT_ALLOWED,
                intent_name=INTENT_PLAY_MUSIC,
                message_key="music_not_found",
                params={"song_name": track_path.stem},
                error="Path outside allowed sandbox",
            )
        if track_path.is_file():
            return _launch_track(track_path, config.dry_run)

    # Scan library
    all_tracks = find_audio_files(music_dir)
    requested_song = intent.entities.get("song")

    if not all_tracks:
        logger.info("Music directory is empty: %s", music_dir)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_FAILED,
            intent_name=INTENT_PLAY_MUSIC,
            message_key="music_dir_empty" if not requested_song else "music_not_found",
            params={"song_name": requested_song or ""},
            action_summary="Music directory empty",
        )

    # If no specific song was requested (e.g. "play music" / "آهنگ پخش کن")
    if not requested_song:
        # Play the first track in the library
        return _launch_track(all_tracks[0], config.dry_run)

    # Search matching tracks
    query_clean = requested_song.strip().lower()
    matches = [
        t for t in all_tracks
        if query_clean in t.stem.lower() or query_clean in t.name.lower()
    ]

    # Zero matches
    if not matches:
        logger.info("No local audio files matched query '%s'", requested_song)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_FAILED,
            intent_name=INTENT_PLAY_MUSIC,
            message_key="music_not_found",
            params={"song_name": requested_song},
            action_summary=f"No matches for {requested_song}",
        )

    # Exactly 1 match
    if len(matches) == 1:
        return _launch_track(matches[0], config.dry_run)

    # Multiple matches -> Disambiguate! Do not randomly choose
    formatted_list = "\n".join([f"{i + 1}. {m.stem}" for i, m in enumerate(matches[:5])])
    candidate_paths = [str(m) for m in matches[:5]]

    logger.info("Multiple music matches found (%d tracks). Asking user to select.", len(matches))
    return ExecutionResult(
        success=True,
        executed=False,
        status=STATUS_SUCCESS,
        intent_name=INTENT_PLAY_MUSIC,
        message_key="music_multiple",
        params={
            "count": len(matches),
            "list": formatted_list,
        },
        requires_context=True,
        context_data={
            "intent": INTENT_PLAY_MUSIC,
            "awaiting_selection": True,
            "candidates": candidate_paths,
            "entities": intent.entities,
            "language": intent.language,
        },
        action_summary=f"Disambiguating {len(matches)} tracks",
    )


def _launch_track(track_path: Path, dry_run: bool) -> ExecutionResult:
    """Launch the chosen audio track with system default player."""
    track_title = track_path.stem

    if dry_run:
        logger.info("Executing track: %s", track_path)
        logger.info("Execution successful [DRY RUN — NOT EXECUTED]")
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_PLAY_MUSIC,
            message_key="music_playing",
            params={"song_name": track_title},
            is_dry_run=True,
            action_summary=f"xdg-open {track_path} [DRY RUN]",
        )

    player = shutil.which("xdg-open")
    if not player:
        # Fallback to common cli/gui audio players if installed
        for p in ("vlc", "mpv", "totem", "rhythmbox", "aplay"):
            player = shutil.which(p)
            if player:
                break

    if not player:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_PLAY_MUSIC,
            message_key="music_not_found",
            params={"song_name": track_title},
            error="No audio player available on system",
        )

    try:
        logger.info("Executing track: %s using %s", track_path, player)
        subprocess.Popen(
            [player, str(track_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("Playback initiated successfully")
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_PLAY_MUSIC,
            message_key="music_playing",
            params={"song_name": track_title},
            action_summary=f"Playing {track_path}",
        )
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.error("Failed to play track %s: %s", track_path, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_PLAY_MUSIC,
            message_key="music_not_found",
            params={"song_name": track_title},
            error=str(e),
        )
