#!/usr/bin/env python3
"""Reject generated, private, or oversized files from the Git tree."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 1_000_000
FORBIDDEN_PARTS = {
    ".idea",
    ".mypy_cache",
    ".playwright-cli",
    ".playwright-mcp",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
FORBIDDEN_SUFFIXES = {
    ".bin",
    ".log",
    ".pid",
    ".pt",
    ".pth",
    ".pyc",
    ".safetensors",
    ".zip",
}


def tracked_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [Path(item.decode()) for item in result.stdout.split(b"\0") if item]


def violations() -> list[str]:
    found: list[str] = []
    for relative in tracked_paths():
        if FORBIDDEN_PARTS.intersection(relative.parts):
            found.append(f"generated/private path: {relative}")
            continue
        if relative.suffix.lower() in FORBIDDEN_SUFFIXES:
            found.append(f"forbidden file type: {relative}")
            continue
        absolute = ROOT / relative
        if absolute.is_file() and absolute.stat().st_size > MAX_FILE_BYTES:
            found.append(f"file exceeds {MAX_FILE_BYTES} bytes: {relative}")
    return found


def main() -> int:
    found = violations()
    if found:
        print("\n".join(found))
        return 1
    print("Repository hygiene: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
