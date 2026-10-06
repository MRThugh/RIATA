"""Executor package for R.I.A.T.A."""

from app.executor.application import execute_open_application
from app.executor.files import execute_open_file, execute_open_folder
from app.executor.music import execute_play_music
from app.executor.response_generator import (
    ResponseGenerator,
    get_response_generator,
)
from app.executor.result import ExecutionResult
from app.executor.system import (
    execute_exit_application,
    execute_open_file_manager,
    execute_open_settings,
    execute_open_terminal,
    execute_show_system_info,
    execute_take_screenshot,
)

__all__ = [
    "ExecutionResult",
    "ResponseGenerator",
    "get_response_generator",
    "execute_open_application",
    "execute_open_folder",
    "execute_open_file",
    "execute_play_music",
    "execute_open_terminal",
    "execute_open_file_manager",
    "execute_open_settings",
    "execute_show_system_info",
    "execute_take_screenshot",
    "execute_exit_application",
]
