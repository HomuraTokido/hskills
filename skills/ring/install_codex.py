"""Backed-up, narrow deployment of this Skill to the local Codex copy."""
import argparse
import datetime
import os
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    home = Path.home()
    target = home / ".codex" / "skills" / "ring"
    names = ("ring.py", "SKILL.md")
    if not target.is_dir() or target.is_symlink() or target.is_junction():
        raise RuntimeError("Expected an existing regular Codex ring directory")
    for name in names:
        path = target / name
        if not path.is_file() or path.is_symlink() or path.is_junction():
            raise RuntimeError(f"Expected existing regular file: {path}")
        print(f"{source / name} -> {path}")
    if not args.apply:
        return
    backup = home / ".ring" / "backups" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True, exist_ok=False)
    for name in names:
        shutil.copy2(target / name, backup / name)
    try:
        for name in names:
            path = target / name
            temporary = target / (name + ".sync-tmp")
            with temporary.open("xb") as handle:
                handle.write((source / name).read_bytes())
            os.replace(temporary, path)
        for name in names:
            if (target / name).read_bytes() != (source / name).read_bytes():
                raise RuntimeError(f"Deployment mismatch: {name}")
    except Exception:
        for name in names:
            shutil.copy2(backup / name, target / name)
        raise
    print(f"Verified exact source copies. Backup: {backup}")


if __name__ == "__main__":
    main()
