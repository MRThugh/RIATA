"""
Unit tests for RIATA release packaging and version validation.
Author: Ali Kamrani (MRThugh)
"""

import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None

from release_tools.validate_version import SEMVER_REGEX, validate_versions
from release_tools.build_deb import calculate_dir_size_kb, copy_tree_clean


def test_semver_regex_valid():
    """Verify semantic version regex accepts valid SemVer strings."""
    assert SEMVER_REGEX.match("0.2.0")
    assert SEMVER_REGEX.match("0.3.0")
    assert SEMVER_REGEX.match("1.0.0")
    assert SEMVER_REGEX.match("1.2.5")
    assert SEMVER_REGEX.match("2.10.3")


def test_semver_regex_invalid():
    """Verify semantic version regex rejects non-standard formats."""
    assert not SEMVER_REGEX.match("v0.2.0")
    assert not SEMVER_REGEX.match("0.2")
    assert not SEMVER_REGEX.match("0.2.0-beta")
    assert not SEMVER_REGEX.match("latest")
    assert not SEMVER_REGEX.match("0.2.0.1")


def test_current_repo_versions_consistent():
    """Verify current repository version sources are completely synchronized."""
    repo_root = Path(__file__).resolve().parent.parent
    is_valid, canonical, versions, errors = validate_versions(repo_root)

    assert is_valid is True, f"Version validation failed with errors: {errors}"
    assert canonical == "0.2.0"
    assert len(errors) == 0
    assert versions["pyproject.toml (canonical)"] == "0.2.0"
    assert versions["app/core/constants.py (constants)"] == "0.2.0"
    assert versions["package.json (frontend)"] == "0.2.0"
    assert versions["metadata.json (metadata)"] == "0.2.0"


def test_version_mismatch_detection():
    """Verify validator detects mismatch when a file has a conflicting version."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.2.0"\n', encoding="utf-8")
        (tmp_path / "package.json").write_text('{"name": "riata", "version": "0.2.1"}', encoding="utf-8")
        (tmp_path / "metadata.json").write_text('{"version": "0.2.0"}', encoding="utf-8")
        app_dir = tmp_path / "app" / "core"
        app_dir.mkdir(parents=True)
        (app_dir / "constants.py").write_text('__version__ = "0.2.0"\n', encoding="utf-8")

        is_valid, canonical, versions, errors = validate_versions(tmp_path)
        assert is_valid is False
        assert canonical == "0.2.0"
        assert len(errors) > 0
        assert "Version mismatch detected" in errors[0]
        assert "package.json: 0.2.1" in errors[0]


def test_copy_tree_clean_excludes_pycache():
    """Verify copy_tree_clean skips __pycache__ and bytecode files."""
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = Path(src_dir)
        dst = Path(dst_dir)

        (src / "normal.py").write_text("print('hello')", encoding="utf-8")
        pycache = src / "__pycache__"
        pycache.mkdir()
        (pycache / "normal.cpython-310.pyc").write_bytes(b"bytecode")

        copy_tree_clean(src, dst)

        assert (dst / "normal.py").is_file()
        assert not (dst / "__pycache__").exists()
        assert not (dst / "normal.cpython-310.pyc").exists()


def test_calculate_dir_size():
    """Verify directory size calculation returns a positive integer."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        (tmp / "test.bin").write_bytes(b"0" * 4096)
        size_kb = calculate_dir_size_kb(tmp)
        assert size_kb >= 1
