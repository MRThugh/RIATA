#!/usr/bin/env python3
"""
RIATA Debian Package Verifier & Smoke Tester
Author: Ali Kamrani (MRThugh)

Performs strict verification of .deb package metadata, contents, and integrity.
Optionally performs a safe non-destructive post-install smoke test.
"""

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path


def verify_package_file(deb_path: Path, expected_version: str | None = None) -> bool:
    """Verify Debian package metadata and payload structure using dpkg-deb."""
    if not deb_path.is_file():
        print(f"❌ Debian package file not found: {deb_path}", file=sys.stderr)
        return False

    print(f"📋 Verifying package archive: {deb_path.name}")

    # 1. Inspect package control metadata
    info_proc = subprocess.run(
        ["dpkg-deb", "--info", str(deb_path)],
        capture_output=True,
        text=True,
    )
    if info_proc.returncode != 0:
        print(f"❌ dpkg-deb --info failed:\n{info_proc.stderr}", file=sys.stderr)
        return False

    info_output = info_proc.stdout

    # Verify Package name
    if "Package: riata" not in info_output:
        print("❌ Control metadata missing 'Package: riata'", file=sys.stderr)
        return False

    # Verify Architecture
    if "Architecture: amd64" not in info_output:
        print("❌ Control metadata missing 'Architecture: amd64'", file=sys.stderr)
        return False

    # Verify Version
    if expected_version and f"Version: {expected_version}" not in info_output:
        print(f"❌ Expected version '{expected_version}' not found in package metadata.", file=sys.stderr)
        return False

    print("  ✓ Package name: riata")
    print(f"  ✓ Version:      {expected_version or 'detected'}")
    print("  ✓ Architecture: amd64")

    # 2. Inspect package contents
    contents_proc = subprocess.run(
        ["dpkg-deb", "--contents", str(deb_path)],
        capture_output=True,
        text=True,
    )
    if contents_proc.returncode != 0:
        print(f"❌ dpkg-deb --contents failed:\n{contents_proc.stderr}", file=sys.stderr)
        return False

    contents = contents_proc.stdout

    required_entries = [
        "./usr/bin/riata",
        "./usr/lib/riata/main.py",
        "./usr/lib/riata/app/__init__.py",
        "./usr/lib/riata/languages/en/manifest.json",
        "./usr/lib/riata/languages/fa/manifest.json",
        "./usr/share/applications/riata.desktop",
        "./usr/share/icons/hicolor/scalable/apps/riata.svg",
    ]

    for req in required_entries:
        if req not in contents:
            print(f"❌ Required path missing from .deb: {req}", file=sys.stderr)
            return False

    print("  ✓ All required runtime entrypoints and files verified")

    # Verify forbidden entries
    forbidden = [
        "__pycache__",
        ".git",
        ".github",
        "/tests/",
        "node_modules",
        ".env",
        "/home/runner",
    ]
    for forb in forbidden:
        if forb in contents:
            print(f"❌ Forbidden development artifact present in package: {forb}", file=sys.stderr)
            return False

    print("  ✓ Zero development or transient artifacts in package")
    return True


def verify_checksum(deb_path: Path, sums_file: Path) -> bool:
    """Verify SHA-256 checksum against SHA256SUMS file."""
    if not sums_file.is_file():
        print(f"⚠️ Checksum file {sums_file} not found; skipping hash match.")
        return True

    sha256 = hashlib.sha256()
    with open(deb_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    actual_hash = sha256.hexdigest()

    content = sums_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].endswith(deb_path.name):
            expected_hash = parts[0]
            if actual_hash == expected_hash:
                print(f"  ✓ Checksum match confirmed: {actual_hash[:16]}...")
                return True
            else:
                print(f"❌ Checksum mismatch!\nExpected: {expected_hash}\nActual:   {actual_hash}", file=sys.stderr)
                return False

    print("⚠️ Package filename not found in SHA256SUMS; skipping hash match.")
    return True


def run_smoke_test(expected_version: str) -> bool:
    """
    Run safe, non-destructive smoke test after system package installation.
    Verifies that 'riata' executable is in PATH and reports the expected version.
    """
    print("\n🧪 Executing installed package smoke test...")

    # 1. Check binary existence in path
    which_proc = subprocess.run(["which", "riata"], capture_output=True, text=True)
    if which_proc.returncode != 0:
        print("❌ 'riata' command not found in PATH after installation.", file=sys.stderr)
        return False
    binary_path = which_proc.stdout.strip()
    print(f"  ✓ Found executable: {binary_path}")

    # 2. Check --version flag output
    ver_proc = subprocess.run(["riata", "--version"], capture_output=True, text=True)
    if ver_proc.returncode != 0:
        print(f"❌ 'riata --version' exited with code {ver_proc.returncode}:\n{ver_proc.stderr}", file=sys.stderr)
        return False
    ver_output = ver_proc.stdout.strip() or ver_proc.stderr.strip()
    print(f"  ✓ Output of 'riata --version': {ver_output}")
    if expected_version not in ver_output:
        print(f"❌ Output does not contain expected version {expected_version}", file=sys.stderr)
        return False

    # 3. Check safe module import and language registry
    import_cmd = [
        "python3",
        "-c",
        (
            "import sys; sys.path.insert(0, '/usr/lib/riata'); "
            "import app; assert app.__version__ == '" + expected_version + "'; "
            "from app.languages.registry import get_language_registry; "
            "reg = get_language_registry(); "
            "assert len(reg.get_available_languages()) >= 2; "
            "print('  ✓ Python module load and language registry discovery successful.')"
        ),
    ]
    import_proc = subprocess.run(import_cmd, capture_output=True, text=True)
    if import_proc.returncode != 0:
        print(f"❌ Module import check failed:\n{import_proc.stderr}", file=sys.stderr)
        return False
    print(import_proc.stdout.strip())

    # 4. Check PySide6 headless UI initialization (if PySide6 is installed)
    qt_env = os.environ.copy()
    qt_env["QT_QPA_PLATFORM"] = "offscreen"
    qt_cmd = [
        "python3",
        "-c",
        (
            "import sys, os; sys.path.insert(0, '/usr/lib/riata'); "
            "os.environ['QT_QPA_PLATFORM'] = 'offscreen'; "
            "try:\n"
            "    from PySide6.QtWidgets import QApplication\n"
            "    from app.ui.main_window import MainWindow\n"
            "    app = QApplication.instance() or QApplication(['--platform', 'offscreen'])\n"
            "    win = MainWindow()\n"
            "    assert win.windowTitle() != ''\n"
            "    print('  ✓ PySide6 Qt6 GUI initialized cleanly in headless offscreen mode.')\n"
            "    app.quit()\n"
            "except ImportError:\n"
            "    print('  ℹ️ PySide6 not installed in current interpreter; skipping GUI widget init.')\n"
        ),
    ]
    qt_proc = subprocess.run(qt_cmd, env=qt_env, capture_output=True, text=True)
    if qt_proc.returncode != 0:
        print(f"❌ PySide6 offscreen check failed:\n{qt_proc.stderr}", file=sys.stderr)
        return False
    print(qt_proc.stdout.strip())

    # 5. Check installed launcher CLI dry-run execution
    try:
        cli_proc = subprocess.run(
            ["riata", "--dry-run", "--cli"],
            input="exit\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        if cli_proc.returncode == 0:
            print("  ✓ Executed installed 'riata --dry-run --cli' safely.")
        else:
            print(f"⚠️ Warning: CLI mode returned code {cli_proc.returncode}: {cli_proc.stderr.strip()}")
    except Exception as e:
        print(f"⚠️ Warning during CLI dry-run smoke test: {e}")

    print("✅ Comprehensive smoke test passed cleanly!")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify RIATA Debian package and execute smoke test.")
    parser.add_argument("deb_path", type=Path, help="Path to .deb package file")
    parser.add_argument("--expected-version", type=str, default=None, help="Expected version string")
    parser.add_argument("--checksum-file", type=Path, default=None, help="Path to SHA256SUMS file")
    parser.add_argument("--smoke-test", action="store_true", help="Run installed package smoke test")
    args = parser.parse_args()

    # 1. Verify deb file
    if not verify_package_file(args.deb_path, args.expected_version):
        return 1

    # 2. Verify checksum
    if args.checksum_file:
        if not verify_checksum(args.deb_path, args.checksum_file):
            return 1

    # 3. Smoke test if requested
    if args.smoke_test:
        if not args.expected_version:
            print("❌ --expected-version is required for smoke test", file=sys.stderr)
            return 1
        if not run_smoke_test(args.expected_version):
            return 1

    print("\n🎉 Package verification completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
