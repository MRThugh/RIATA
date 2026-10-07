"""
Tests for R.I.A.T.A v0.1.1 Configuration Boolean Parsing Bug Fix.
Author: Ali Kamrani (MRThugh)

Verifies:
- Explicit boolean parsing handles string values ('false', '0', 'no') accurately.
- Avoids Python's unsafe bool("false") -> True trap.
"""

from app.core.config import Config, _parse_bool


def test_parse_bool_helper():
    # False values that bool("false") would misinterpret as True
    assert _parse_bool("false") is False
    assert _parse_bool("False") is False
    assert _parse_bool("0") is False
    assert _parse_bool("no") is False
    assert _parse_bool("off") is False
    assert _parse_bool(False) is False
    assert _parse_bool(0) is False

    # True values
    assert _parse_bool("true") is True
    assert _parse_bool("True") is True
    assert _parse_bool("1") is True
    assert _parse_bool("yes") is True
    assert _parse_bool("on") is True
    assert _parse_bool(True) is True
    assert _parse_bool(1) is True


def test_config_load_with_boolean_strings(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"dry_run": "false", "debug": "false", "safe_execution": "true"}')

    cfg = Config.load(config_file)
    assert cfg.dry_run is False
    assert cfg.debug is False
    assert cfg.safe_execution is True
