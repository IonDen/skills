#!/usr/bin/env python3
"""Build a reproducible skills-only upload ZIP. Requires the validator's PyYAML."""
import argparse
import hashlib
import stat
import sys
import zipfile
from pathlib import Path

from validate_skills import PLUGIN_DIR, ROOT, validate_all


def build_zip(root: Path, output: Path) -> None:
    """Validate and archive only the plugin, with fixed timestamps and permissions."""
    plugin = root / PLUGIN_DIR
    if output.resolve().is_relative_to(plugin.resolve()):
        raise ValueError("ZIP output must be outside the plugin directory")
    if plugin.is_symlink():
        raise ValueError(f"symlink is not allowed: {plugin}")
    files = []
    for path in sorted(plugin.rglob("*")):
        relative = path.relative_to(plugin)
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed: {relative}")
        if any(part in {".DS_Store", "__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        hidden = [part for part in relative.parts if part.startswith(".")]
        if hidden and not (relative.parts[0] in {".claude-plugin", ".codex-plugin"} and len(hidden) == 1):
            raise ValueError(f"hidden supporting file is not allowed: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"not a regular file: {relative}")
        files.append(path)
    if validate_all(root):
        raise ValueError("plugin validation failed; no ZIP created")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            name = (Path(plugin.name) / path.relative_to(plugin)).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    print(f"ZIP {output} ({len(files)} files)")
    print(f"SHA256 {hashlib.sha256(output.read_bytes()).hexdigest()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repository)")
    parser.add_argument("--output", type=Path, required=True, help="new ZIP path outside the plugin")
    args = parser.parse_args()
    try:
        build_zip(args.root, args.output)
    except (OSError, ValueError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
