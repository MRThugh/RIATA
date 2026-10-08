#!/usr/bin/env python3
"""
RIATA Version Validator & Consistency Checker
Author: Ali Kamrani (MRThugh)

Extracts and validates the canonical version from pyproject.toml and verifies
that all important version sources across the repository agree.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Semantic version regex (strict MAJOR.MINOR.PATCH)
SEMVER_REGEX = re.compile(r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")


def get_repo_root() -> Path:
    """Find repository root by looking for pyproject.toml."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path.cwd()


def extract_from_pyproject(root: Path) -> str | None:
    """Extract canonical version from pyproject.toml [project] section."""
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        return None
    content = pyproject_path.read_text(encoding="utf-8")
    # Match version = "0.2.0" inside [project]
    in_project_section = False
    for line in content.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("[") and line_clean.endswith("]"):
            in_project_section = (line_clean == "[project]")
            continue
        if in_project_section and line_clean.startswith("version"):
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', line_clean)
            if match:
                return match.group(1).strip()
    # Fallback to general search if section parsing did not match
    match = re.search(r'\[project\][\s\S]*?version\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1).strip() if match else None


def extract_from_package_json(root: Path) -> str | None:
    """Extract version from package.json."""
    pkg_path = root / "package.json"
    if not pkg_path.is_file():
        return None
    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
        return str(data.get("version", "")).strip() or None
    except Exception:
        return None


def extract_from_constants(root: Path) -> str | None:
    """Extract __version__ from app/core/constants.py."""
    constants_path = root / "app" / "core" / "constants.py"
    if not constants_path.is_file():
        return None
    content = constants_path.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*(?::\s*[^=]+)?=\s*["\']([^"\']+)["\']', content)
    return match.group(1).strip() if match else None


def extract_from_metadata(root: Path) -> str | None:
    """Extract version from metadata.json."""
    meta_path = root / "metadata.json"
    if not meta_path.is_file():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return str(data.get("version", "")).strip() or None
    except Exception:
        return None


def validate_versions(root: Path | None = None) -> tuple[bool, str, dict[str, str | None], list[str]]:
    """
    Validate version consistency across the codebase.
    Returns:
        (is_valid, canonical_version, versions_dict, error_messages)
    """
    if root is None:
        root = get_repo_root()

    versions: dict[str, str | None] = {
        "pyproject.toml (canonical)": extract_from_pyproject(root),
        "app/core/constants.py (constants)": extract_from_constants(root),
        "package.json (frontend)": extract_from_package_json(root),
        "metadata.json (metadata)": extract_from_metadata(root),
    }

    errors: list[str] = []
    canonical = versions["pyproject.toml (canonical)"]

    # 1. Canonical source check
    if not canonical:
        errors.append("Could not extract canonical version from pyproject.toml.")
        return False, "", versions, errors

    # 2. Semantic version format check
    if not SEMVER_REGEX.match(canonical):
        errors.append(
            f"Canonical version '{canonical}' in pyproject.toml is not a valid semantic version.\n"
            f"Expected format: MAJOR.MINOR.PATCH (e.g., 0.2.0, 0.3.0, 1.0.0)"
        )
        return False, canonical, versions, errors

    # 3. Check consistency across all sources
    mismatches: dict[str, str | None] = {}
    for source_name, ver in versions.items():
        if ver is None or ver != canonical:
            mismatches[source_name] = ver

    if mismatches:
        err_msg = [
            "Version mismatch detected:",
            "",
            f"pyproject.toml: {versions.get('pyproject.toml (canonical)')}",
            f"package.json: {versions.get('package.json (frontend)')}",
            f"app/core/constants.py: {versions.get('app/core/constants.py (constants)')}",
            f"metadata.json: {versions.get('metadata.json (metadata)')}",
            "",
            "Release aborted.",
        ]
        errors.append("\n".join(err_msg))
        return False, canonical, versions, errors

    return True, canonical, versions, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate RIATA version consistency across all project sources."
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Write version outputs to GITHUB_OUTPUT environment file if valid",
    )
    parser.add_argument(
        "--print-version",
        action="store_true",
        help="Print only the validated version string and exit",
    )
    parser.add_argument(
        "--print-tag",
        action="store_true",
        help="Print only the validated git tag (e.g. v0.2.0) and exit",
    )
    args = parser.parse_args()

    root = get_repo_root()
    is_valid, canonical, versions, errors = validate_versions(root)

    if not is_valid:
        print("=" * 60, file=sys.stderr)
        print("❌ RIATA VERSION VALIDATION FAILED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        for err in errors:
            print(err, file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        return 1

    if args.print_version:
        print(canonical)
        return 0

    if args.print_tag:
        print(f"v{canonical}")
        return 0

    print("=" * 60)
    print("✅ RIATA VERSION VALIDATION PASSED")
    print("=" * 60)
    print(f"Canonical version:     {canonical}")
    print(f"Target Git tag:        v{canonical}")
    print(f"Debian package name:   RIATA_{canonical}_amd64.deb")
    print("\nVerified sources:")
    for src, val in versions.items():
        print(f"  • {src}: {val}")
    print("=" * 60)

    if args.github_output:
        gh_output = os.environ.get("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a", encoding="utf-8") as f:
                f.write(f"version={canonical}\n")
                f.write(f"tag=v{canonical}\n")
                f.write(f"deb_name=RIATA_{canonical}_amd64.deb\n")
            print(f"[CI] Exported variables to GITHUB_OUTPUT: version={canonical}, tag=v{canonical}")
        else:
            print("[CI] GITHUB_OUTPUT not set; skipped writing to environment file.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
