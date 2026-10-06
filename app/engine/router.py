"""
Intent Router and Execution Coordinator for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.constants import (
    INTENT_CLARIFY,
    INTENT_EXIT_APPLICATION,
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_FILE,
    INTENT_OPEN_FILE_MANAGER,
    INTENT_OPEN_FOLDER,
    INTENT_OPEN_SETTINGS,
    INTENT_OPEN_TERMINAL,
    INTENT_PLAY_MUSIC,
    INTENT_SHOW_SYSTEM_INFO,
    INTENT_TAKE_SCREENSHOT,
    INTENT_UNKNOWN,
    LANG_PERSIAN,
)
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.engine.matcher import BaseIntentParser, get_intent_parser
from app.executor.application import execute_open_application
from app.executor.files import execute_open_file, execute_open_folder
from app.executor.music import execute_play_music
from app.executor.response_generator import get_response_generator
from app.executor.result import (
    STATUS_EXECUTION_ERROR,
    STATUS_INVALID_COMMAND,
    STATUS_PERMISSION_DENIED,
    ExecutionResult,
)
from app.executor.system import (
    execute_exit_application,
    execute_open_file_manager,
    execute_open_settings,
    execute_open_terminal,
    execute_show_system_info,
    execute_take_screenshot,
)
from app.languages.loader import get_language_loader

logger = get_logger("riata.router")


@dataclass
class ProcessOutput:
    """End-to-end output of processing user input."""

    response_text: str
    intent: Intent
    result: Optional[ExecutionResult] = None
    is_exit: bool = False
    direction: str = "ltr"  # 'rtl' or 'ltr'


class IntentRouter:
    """Dispatches intents to appropriate executors with context retention."""

    def __init__(self, parser: Optional[BaseIntentParser] = None) -> None:
        self.parser = parser or get_intent_parser()
        self.response_generator = get_response_generator()
        self.loader = get_language_loader()
        self.context: dict[str, Any] = {}

    def process(self, user_input: str) -> ProcessOutput:
        """Parse user command, execute action safely, and generate response."""
        # 1. Parse intent
        intent = self.parser.parse(user_input, context=self.context)

        # Clear awaiting selection if context was consumed
        if self.context.get("awaiting_selection") and intent.name != INTENT_UNKNOWN:
            self.context.clear()

        # Get direction from language pack
        pack = self.loader.get_pack(intent.language)
        direction = pack.direction

        # 2. Check for dangerous actions or clarification or unknown
        if intent.is_dangerous:
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_PERMISSION_DENIED,
                intent_name=intent.name,
                message_key="dangerous_command",
                error="Dangerous action blocked for safety",
                message="Action blocked for security reasons.",
            )
            response_text = self.response_generator.generate(res, intent)
            return ProcessOutput(
                response_text=response_text,
                intent=intent,
                result=res,
                direction=direction,
            )
        elif intent.is_clarification_needed:
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_INVALID_COMMAND,
                intent_name=intent.name,
                message_key="clarify_general",
                message=intent.clarification_prompt or "Clarification required.",
            )
            response_text = self.response_generator.generate(res, intent)
            return ProcessOutput(
                response_text=response_text,
                intent=intent,
                result=res,
                direction=direction,
            )
        elif intent.name == INTENT_UNKNOWN:
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_INVALID_COMMAND,
                intent_name=intent.name,
                message_key="unknown_intent",
                message="Unknown command.",
            )
            response_text = self.response_generator.generate(res, intent)
            return ProcessOutput(
                response_text=response_text,
                intent=intent,
                result=res,
                direction=direction,
            )

        # 3. Route to dedicated executor
        result = self._dispatch(intent)

        # 4. Update context if executor requested follow-up
        if result.requires_context:
            self.context = dict(result.context_data)
        else:
            self.context.clear()

        # 5. Format localized response
        response_text = self.response_generator.generate(result, intent)
        is_exit = intent.name == INTENT_EXIT_APPLICATION

        return ProcessOutput(
            response_text=response_text,
            intent=intent,
            result=result,
            is_exit=is_exit,
            direction=direction,
        )

    def _dispatch(self, intent: Intent) -> ExecutionResult:
        """Route to appropriate executor based on intent name."""
        handlers = {
            INTENT_OPEN_APPLICATION: execute_open_application,
            INTENT_OPEN_FOLDER: execute_open_folder,
            INTENT_OPEN_FILE: execute_open_file,
            INTENT_PLAY_MUSIC: execute_play_music,
            INTENT_OPEN_TERMINAL: execute_open_terminal,
            INTENT_OPEN_FILE_MANAGER: execute_open_file_manager,
            INTENT_OPEN_SETTINGS: execute_open_settings,
            INTENT_SHOW_SYSTEM_INFO: execute_show_system_info,
            INTENT_TAKE_SCREENSHOT: execute_take_screenshot,
            INTENT_EXIT_APPLICATION: execute_exit_application,
        }

        handler = handlers.get(intent.name)
        if not handler:
            return ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_INVALID_COMMAND,
                intent_name=intent.name,
                message_key="unknown_intent",
                params={},
            )

        try:
            return handler(intent)
        except Exception as e:
            logger.exception("Unexpected error executing %s: %s", intent.name, e)
            return ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_EXECUTION_ERROR,
                intent_name=intent.name,
                message_key="app_launch_failed",
                params={"app_name": intent.name, "error": str(e)},
                error=str(e),
            )

    def reset_context(self) -> None:
        """Clear active conversation context."""
        self.context.clear()


_GLOBAL_ROUTER: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    """Retrieve global IntentRouter instance."""
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = IntentRouter()
    return _GLOBAL_ROUTER
