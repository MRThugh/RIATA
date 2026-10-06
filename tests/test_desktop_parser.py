"""
Unit tests for Linux .desktop Exec line parser.
Author: Ali Kamrani (MRThugh)
"""

import pytest

from app.registry.applications import parse_desktop_exec_line


def test_standard_exec_parsing():
    assert parse_desktop_exec_line("firefox %u") == "firefox"
    assert parse_desktop_exec_line("gedit --new-window %F") == "gedit"
    assert parse_desktop_exec_line("vlc") == "vlc"


def test_quoted_executable_paths():
    line1 = '"/opt/google/chrome/google-chrome" --profile-directory=Default %U'
    assert parse_desktop_exec_line(line1) == "/opt/google/chrome/google-chrome"

    line2 = '"/usr/bin/my app with spaces" -a -b %F'
    assert parse_desktop_exec_line(line2) == "/usr/bin/my app with spaces"


def test_env_wrapper_handling():
    line = "env FOO=bar GDK_BACKEND=x11 myapp --flag %U"
    assert parse_desktop_exec_line(line) == "myapp"


def test_field_codes_stripped():
    assert parse_desktop_exec_line("%u") is None
    assert parse_desktop_exec_line("%F") is None


def test_shell_metacharacters_rejected():
    assert parse_desktop_exec_line("myapp; rm -rf /") is None
    assert parse_desktop_exec_line("myapp | ls") is None
    assert parse_desktop_exec_line("myapp & rm") is None


def test_malformed_lines_graceful():
    # Unclosed quote
    res = parse_desktop_exec_line('"/opt/unclosed quote path')
    assert res is not None

    # Empty strings
    assert parse_desktop_exec_line("") is None
    assert parse_desktop_exec_line("   ") is None
    assert parse_desktop_exec_line(None) is None
