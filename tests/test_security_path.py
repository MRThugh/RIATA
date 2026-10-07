"""
Security regression tests for filesystem containment and symlink escape prevention.
Author: Ali Kamrani (MRThugh)
"""

import os
from pathlib import Path
import pytest

from app.executor.files import is_allowed_path, resolve_folder_path


def test_path_containment_positive(tmp_path: Path):
    """Verify normal paths inside home and tmp are properly allowed."""
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    tmp = tmp_path / "tmp"
    tmp.mkdir(parents=True)

    # File inside home
    doc = home / "project" / "doc.txt"
    assert is_allowed_path(doc, base_dir=home, allow_tmp=False) is True

    # Nested subfolder inside home
    nested = home / "a" / "b" / "c"
    assert is_allowed_path(nested, base_dir=home, allow_tmp=False) is True

    # Safe relative traversal that stays inside home
    stay_inside = home / "project" / "sub" / ".." / "doc.txt"
    assert is_allowed_path(stay_inside, base_dir=home, allow_tmp=False) is True


def test_path_prefix_bypass_rejected(tmp_path: Path):
    """
    CRITICAL VULNERABILITY REGRESSION TEST:
    Ensure /home/user2 does NOT bypass checks for /home/user.
    String startswith('/home/user') would incorrectly return True for '/home/user2'.
    pathlib.Path containment (relative_to) MUST reject it.
    """
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)

    other_user = tmp_path / "home" / "user2"
    other_user.mkdir(parents=True)
    other_file = other_user / "secret.txt"

    assert is_allowed_path(other_file, base_dir=home, allow_tmp=False) is False
    assert is_allowed_path(other_user, base_dir=home, allow_tmp=False) is False


def test_directory_traversal_escape_rejected(tmp_path: Path):
    """Verify traversal using .. escaping the home sandbox is rejected."""
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)

    # Attempt to escape via ..
    escape1 = home / "project" / ".." / ".." / ".." / "etc" / "passwd"
    assert is_allowed_path(escape1, base_dir=home, allow_tmp=False) is False

    escape2 = home / ".." / "secret.txt"
    assert is_allowed_path(escape2, base_dir=home, allow_tmp=False) is False

    # Absolute system files
    assert is_allowed_path("/etc/passwd", base_dir=home, allow_tmp=False) is False
    assert is_allowed_path("/etc/shadow", base_dir=home, allow_tmp=False) is False


def test_symlink_escape_attack_rejected(tmp_path: Path):
    """
    SYMLINK ESCAPE VULNERABILITY TEST:
    A symlink inside allowed home pointing to an external directory (e.g. /etc)
    must resolve to the external target and be REJECTED.
    """
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)

    outside = tmp_path / "outside_system"
    outside.mkdir(parents=True)
    secret_target = outside / "confidential.conf"
    secret_target.write_text("secret_data")

    # Create symlink inside user home pointing to outside directory
    symlink_dir = home / "safe_looking_link"
    try:
        symlink_dir.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation not supported in this environment")

    # Path that appears inside user home syntactically but traverses to external target
    exploit_path = symlink_dir / "confidential.conf"

    assert is_allowed_path(exploit_path, base_dir=home, allow_tmp=False) is False


def test_symlink_to_file_outside_rejected(tmp_path: Path):
    """Verify a symlink pointing directly to an external file is rejected."""
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside")

    link_file = home / "link_to_outside.txt"
    try:
        link_file.symlink_to(outside_file)
    except OSError:
        pytest.skip("Symlink creation not supported in this environment")

    assert is_allowed_path(link_file, base_dir=home, allow_tmp=False) is False


def test_sensitive_credentials_subdirs_rejected(tmp_path: Path):
    """Verify access to sensitive credential directories like .ssh, .gnupg, .aws, .docker is blocked."""
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)

    ssh_key = home / ".ssh" / "id_rsa"
    assert is_allowed_path(ssh_key, base_dir=home, allow_tmp=False) is False

    gnupg_key = home / ".gnupg" / "secring.gpg"
    assert is_allowed_path(gnupg_key, base_dir=home, allow_tmp=False) is False

    aws_cred = home / ".aws" / "credentials"
    assert is_allowed_path(aws_cred, base_dir=home, allow_tmp=False) is False

    docker_config = home / ".docker" / "config.json"
    assert is_allowed_path(docker_config, base_dir=home, allow_tmp=False) is False

    kube_config = home / ".kube" / "config"
    assert is_allowed_path(kube_config, base_dir=home, allow_tmp=False) is False


def test_resolve_folder_path_security(tmp_path: Path):
    """Verify resolve_folder_path respects the containment boundaries."""
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)

    # Standard XDG folder
    downloads = resolve_folder_path("Downloads", base_dir=home)
    assert downloads is not None
    assert downloads == (home / "Downloads").resolve()

    # Traversal attempt
    assert resolve_folder_path("../../../etc", base_dir=home) is None
    assert resolve_folder_path("/etc", base_dir=home) is None
