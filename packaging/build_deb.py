#!/usr/bin/env python3
"""
RIATA Native Ubuntu Package Builder (.deb)
Author: Ali Kamrani (MRThugh)

Builds a clean, standard Debian package for Ubuntu:
RIATA_<version>_amd64.deb
without bundling development artifacts, local virtual environments, or runner paths.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from packaging.validate_version import validate_versions


def calculate_dir_size_kb(path: Path) -> int:
    """Calculate directory size in KB for Debian Installed-Size field."""
    total_bytes = 0
    for p in path.rglob("*"):
        if p.is_file():
            total_bytes += p.stat().st_size
    return max(1, total_bytes // 1024)


def copy_tree_clean(src: Path, dst: Path, ignore_patterns: tuple[str, ...] = ("__pycache__", "*.pyc", "*.pyo", ".DS_Store")) -> None:
    """Copy directory structure while excluding bytecode and caches."""
    dst.mkdir(parents=True, exist_ok=True)
    for root_dir, dirs, files in os.walk(src):
        # Exclude directories in-place
        dirs[:] = [d for d in dirs if d not in ignore_patterns and not d.startswith(".")]
        rel_path = Path(root_dir).relative_to(src)
        target_dir = dst / rel_path
        target_dir.mkdir(parents=True, exist_ok=True)

        for file_name in files:
            if any(file_name.endswith(ext.replace("*", "")) for ext in ignore_patterns if "*" in ext):
                continue
            if file_name in ignore_patterns or file_name.startswith("."):
                continue
            src_file = Path(root_dir) / file_name
            dst_file = target_dir / file_name
            shutil.copy2(src_file, dst_file)
            # Standard file permission
            dst_file.chmod(0o644)


def create_checksum_files(deb_path: Path, output_dir: Path) -> tuple[str, Path, Path]:
    """Generate SHA256 checksum files for the package."""
    sha256 = hashlib.sha256()
    with open(deb_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    digest = sha256.hexdigest()

    deb_filename = deb_path.name

    # 1. Combined SHA256SUMS file
    sums_file = output_dir / "SHA256SUMS"
    sums_file.write_text(f"{digest}  {deb_filename}\n", encoding="utf-8")

    # 2. Individual artifact checksum
    single_sum_file = output_dir / f"{deb_filename}.sha256"
    single_sum_file.write_text(f"{digest}  {deb_filename}\n", encoding="utf-8")

    return digest, sums_file, single_sum_file


def verify_built_deb(deb_path: Path, expected_version: str) -> None:
    """Verify package structure, metadata, and contents with dpkg-deb."""
    print("\n🔍 Validating generated Debian package integrity...")

    # 1. dpkg-deb --info check
    info_proc = subprocess.run(
        ["dpkg-deb", "--info", str(deb_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    info_output = info_proc.stdout

    expected_fields = {
        "Package": "riata",
        "Version": expected_version,
        "Architecture": "amd64",
    }
    for field, expected_val in expected_fields.items():
        if f"{field}: {expected_val}" not in info_output:
            raise ValueError(f"Package info validation failed: '{field}: {expected_val}' not found in deb control.")

    print(f"  ✓ Control metadata verified: riata v{expected_version} (amd64)")

    # 2. dpkg-deb --contents check
    contents_proc = subprocess.run(
        ["dpkg-deb", "--contents", str(deb_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    contents_output = contents_proc.stdout

    required_paths = [
        "./usr/bin/riata",
        "./usr/lib/riata/main.py",
        "./usr/lib/riata/app/__init__.py",
        "./usr/lib/riata/languages/en/manifest.json",
        "./usr/lib/riata/languages/fa/manifest.json",
        "./usr/share/applications/riata.desktop",
        "./usr/share/icons/hicolor/scalable/apps/riata.svg",
    ]
    for req in required_paths:
        if req not in contents_output:
            raise ValueError(f"Required file missing from deb archive: {req}")

    print("  ✓ Essential payload files present (executable, core, languages, desktop, icon)")

    forbidden_patterns = [
        "__pycache__",
        ".git",
        ".github",
        "/tests/",
        "node_modules",
        ".env",
        "/home/runner",
    ]
    for pattern in forbidden_patterns:
        if pattern in contents_output:
            raise ValueError(f"Forbidden artifact detected in deb archive: {pattern}")

    print("  ✓ Zero development, test, or local runner artifacts found")


def build_deb(version: str, output_dir: Path) -> Path:
    """Build the native .deb package."""
    deb_name = f"RIATA_{version}_amd64.deb"
    final_deb_path = output_dir / deb_name

    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="riata_deb_") as tmp_dir:
        staging = Path(tmp_dir)

        # Create standard Unix filesystem structure
        debian_dir = staging / "DEBIAN"
        usr_bin = staging / "usr" / "bin"
        usr_lib_riata = staging / "usr" / "lib" / "riata"
        usr_applications = staging / "usr" / "share" / "applications"
        usr_icons = staging / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps"
        usr_pixmaps = staging / "usr" / "share" / "pixmaps"
        usr_doc = staging / "usr" / "share" / "doc" / "riata"

        for directory in [debian_dir, usr_bin, usr_lib_riata, usr_applications, usr_icons, usr_pixmaps, usr_doc]:
            directory.mkdir(parents=True, exist_ok=True)

        # 1. Application code
        copy_tree_clean(REPO_ROOT / "app", usr_lib_riata / "app")
        copy_tree_clean(REPO_ROOT / "languages", usr_lib_riata / "languages")
        shutil.copy2(REPO_ROOT / "main.py", usr_lib_riata / "main.py")
        (usr_lib_riata / "main.py").chmod(0o755)

        if (REPO_ROOT / "requirements.txt").is_file():
            shutil.copy2(REPO_ROOT / "requirements.txt", usr_lib_riata / "requirements.txt")
            (usr_lib_riata / "requirements.txt").chmod(0o644)

        # 2. Executable launcher in /usr/bin/riata
        launcher_src = REPO_ROOT / "packaging" / "riata.sh"
        launcher_dst = usr_bin / "riata"
        shutil.copy2(launcher_src, launcher_dst)
        launcher_dst.chmod(0o755)

        # 3. Desktop entry & Icon
        desktop_src = REPO_ROOT / "packaging" / "riata.desktop"
        shutil.copy2(desktop_src, usr_applications / "riata.desktop")
        (usr_applications / "riata.desktop").chmod(0o644)

        icon_src = REPO_ROOT / "assets" / "icons" / "riata.svg"
        if icon_src.is_file():
            shutil.copy2(icon_src, usr_icons / "riata.svg")
            (usr_icons / "riata.svg").chmod(0o644)
            shutil.copy2(icon_src, usr_pixmaps / "riata.svg")
            (usr_pixmaps / "riata.svg").chmod(0o644)

        # 4. Documentation & Copyright
        license_src = REPO_ROOT / "LICENSE"
        if license_src.is_file():
            shutil.copy2(license_src, usr_doc / "copyright")
            (usr_doc / "copyright").chmod(0o644)

        # 5. Post-installation & Post-removal hooks
        postinst = debian_dir / "postinst"
        postinst.write_text(
            """#!/bin/sh
set -e

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

exit 0
""",
            encoding="utf-8",
        )
        postinst.chmod(0o755)

        postrm = debian_dir / "postrm"
        postrm.write_text(
            """#!/bin/sh
set -e

if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
    fi
fi

exit 0
""",
            encoding="utf-8",
        )
        postrm.chmod(0o755)

        # Calculate installed size
        installed_size_kb = calculate_dir_size_kb(staging / "usr")

        # 6. Debian control file
        control_content = f"""Package: riata
Version: {version}
Section: utils
Priority: optional
Architecture: amd64
Installed-Size: {installed_size_kb}
Maintainer: Ali Kamrani (MRThugh) <kamrani.exe@gmail.com>
Depends: python3 (>= 3.10)
Recommends: python3-pip
Homepage: https://github.com/MRThugh/RIATA
Description: Responsive Intent Automation & Task Assistant
 Deterministic, extensible, rule-based Linux desktop Intent Assistant
 supporting Persian and English with multi-step planning and contextual memory.
"""
        control_file = debian_dir / "control"
        control_file.write_text(control_content, encoding="utf-8")
        control_file.chmod(0o644)

        # Build package with dpkg-deb
        print(f"📦 Compiling Debian package with dpkg-deb (Target: {deb_name})...")
        cmd = ["dpkg-deb", "--build", "--root-owner-group", str(staging), str(final_deb_path)]
        subprocess.run(cmd, check=True)

    # Generate checksums
    digest, sums_file, single_sum_file = create_checksum_files(final_deb_path, output_dir)
    print(f"✅ Generated package: {final_deb_path} ({final_deb_path.stat().st_size} bytes)")
    print(f"🔑 SHA-256 Checksum:  {digest}")
    print(f"📄 Checksum files:    {sums_file.name}, {single_sum_file.name}")

    # Validate package
    verify_built_deb(final_deb_path, version)

    return final_deb_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build native RIATA Ubuntu (.deb) package.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "dist",
        help="Directory where release artifacts will be written (default: dist/)",
    )
    args = parser.parse_args()

    # Validate version first
    is_valid, canonical, _, errors = validate_versions(REPO_ROOT)
    if not is_valid:
        print("❌ Cannot build package: Version validation failed.", file=sys.stderr)
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    try:
        build_deb(canonical, args.output_dir.resolve())
        print("\n🎉 RIATA Debian package built and verified successfully!")
        return 0
    except Exception as e:
        print(f"\n❌ Error building package: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
