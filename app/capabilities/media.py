"""
Media capability for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)
"""

from app.capabilities.base import BaseCapability
from app.core.constants import INTENT_PLAY_MUSIC
from app.engine.intent import Intent
from app.executor.music import execute_play_music
from app.executor.result import ExecutionResult


class MediaCapability(BaseCapability):
    """Handles local media scanning, disambiguation, and playback."""

    @property
    def id(self) -> str:
        return "media"

    @property
    def name(self) -> str:
        return "Media & Audio Playback"

    @property
    def supported_intents(self) -> tuple[str, ...]:
        return (INTENT_PLAY_MUSIC,)

    def execute(self, intent: Intent) -> ExecutionResult:
        return execute_play_music(intent)
