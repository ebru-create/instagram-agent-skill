#!/usr/bin/env python3
"""Install/check the complete skill bundle without touching account data."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ".instagram-agent-install.json"
BACKUPS = ".instagram-agent-backups"
IGNORED = {"__pycache__", ".DS_Store"}
REQUIRED_SKILLS = {"ig-" + name for name in
                   "account audit caption carousel comment dm human plan profile reel reply repurpose story viral".split()}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_files(directory):
    for path in sorted(directory.rglob("*")):
        if any(part in IGNORED for part in path.relative_to(directory).parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"symbolic links are not supported in bundle folders: {path}")
        if path.is_file():
            yield path


def bundle(source=ROOT):
    source = Path(source).resolve()
    skills = sorted(path for path in (source / "skills").glob("ig-*") if path.is_dir())
    if not skills:
        raise ValueError("no skill bundle found")
    if not REQUIRED_SKILLS.issubset({path.name for path in skills}):
        raise ValueError("incomplete source bundle; use a full repository checkout")
    files = {}
    for skill in skills:
        if skill.is_symlink() or not (skill / "SKILL.md").is_file():
            raise ValueError(f"missing regular skill entrypoint: {skill}")
        for path in tree_files(skill):
            files[str(path.relative_to(source / "skills"))] = path
    for name in ("voice.md", "strategy.md"):
        path = source / "templates" / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing regular template: {path}")
        files["ig-account/assets/templates/" + name] = path
    required = ("ig-account/ig_language.py", "ig-account/account.py", "ig-reel/hooks.json",
                "ig-reel/hooks.tr.json", "ig-human/slop.json", "ig-human/slop.tr.json",
                "ig-human/humanize.py", "ig-human/detect.py", "ig-reel/hookscore.py",
                "ig-reel/beats.py", "ig-caption/caption.py", "ig-viral/swipe.py",
                "ig-audit/analyse.py", "ig-audit/template.csv", "ig-audit/example.synthetic.csv",
                "ig-plan/experiment.py", "ig-plan/example.experiment.tr.json",
                "ig-account/publication.py", "ig-account/example.publication.tr.json",
                "ig-account/turkce.py",
                "ig-carousel/render.py", "ig-carousel/requirements.txt", "ig-carousel/example.tr.json")
    if any(name not in files for name in required):
        raise ValueError("incomplete source bundle; use a full repository checkout")
    for path in files.values():
        if path.suffix == ".py":
            compile(path.read_bytes(), str(path), "exec")
    version = json.loads((source / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
    return files, {"schema_version": 1, "version": version,
                   "skills": [path.name for path in skills],
                   "files": {name: digest(path) for name, path in sorted(files.items())}}


def destination(value, source=ROOT):
    path = Path(value).expanduser()
    if path.is_symlink():
        raise ValueError("skills destination must not be a symbolic link")
    path = path.resolve()
    skill_source = (Path(source) / "skills").resolve()
    if path == skill_source or path in skill_source.parents or skill_source in path.parents:
        raise ValueError("destination must not overlap the source skills directory")
    data = (Path.home() / ".claude/instagram").resolve()
    if path == data or data in path.parents:
        raise ValueError("choose a skills directory, not the Instagram account-data directory")
    if path.exists() and not path.is_dir():
        raise ValueError("skills destination must be a directory")
    return path


def read_manifest(target, names):
    path = target / MANIFEST
    if path.is_symlink():
        raise ValueError("installation manifest must not be a symbolic link")
    if not path.exists():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") != 1 or not isinstance(state.get("files"), dict):
        raise ValueError("invalid installation manifest")
    for key, value in state["files"].items():
        relative = PurePosixPath(key)
        if (relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 2
                or relative.parts[0] not in names or str(relative) != key or "\\" in key
                or not isinstance(value, str) or len(value) != 64):
            raise ValueError("invalid managed-file path/hash in installation manifest")
    return state


def conflicts(target, previous, desired):
    issues = []
    if previous:
        for name, expected in previous["files"].items():
            path = target / name
            if path.exists() and (not path.is_file() or digest(path) != expected):
                issues.append(name)
    for name, expected in desired["files"].items():
        path = target / name
        for parent in path.parents:
            if parent == target:
                break
            if parent.exists() and not parent.is_dir():
                issues.append(str(parent.relative_to(target)))
        if path.exists() and (not previous or name not in previous["files"]):
            if not path.is_file() or digest(path) != expected:
                issues.append(name)
    return sorted(set(issues))


def smoke_check(target):
    """Use only supplied input and a nonexistent scratch profile; no real data."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    checks = 0
    samples = {"ig-human/humanize.py": "Üç örneği senin için hazırladım.",
               "ig-human/detect.py": "Üç örneği senin için hazırladım.",
               "ig-reel/hookscore.py": "Üç günde iki saat kazandım",
               "ig-reel/beats.py": "Üç günde iki saat kazandım.",
               "ig-caption/caption.py": "Üç örneği kaydet.",
               "ig-viral/swipe.py": "account\tfollowers\tmedian\tviews\thook\n@sample\t1000\t100\t500\tKimse sana bunu söylemiyor\n"}
    for language in ("en", "tr"):
        for name, text in samples.items():
            if language == "en":
                text = ("account\tfollowers\tmedian\tviews\thook\n@sample\t1000\t100\t500\tI lost three hours\n"
                        if "swipe.py" in name else "I made three examples for you. Save this.")
            result = subprocess.run([sys.executable, str(target / name), "--language", language, "--json"],
                                    input=text, text=True, capture_output=True, timeout=15, env=env)
            try:
                report = json.loads(result.stdout)
                if result.returncode not in (0, 1) or report["language"] != language:
                    raise ValueError("unexpected status or language")
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"installed tool check failed: {name} ({language}): {result.stderr.strip()}") from exc
            checks += 1
    with tempfile.TemporaryDirectory(prefix="instagram-profile-check-") as scratch:
        result = subprocess.run([sys.executable, str(target / "ig-account/account.py"),
                                 "--root", str(Path(scratch) / "unused"), "show"],
                                text=True, capture_output=True, timeout=15, env=env)
        if result.returncode or json.loads(result.stdout).get("mode") != "legacy":
            raise ValueError("installed account resolver check failed")
    return checks + 1


def _install(target, source=ROOT, *, update=False, replace_existing=False, dry_run=False, check=False):
    files, desired = bundle(source)
    target = destination(target, source)
    for name in desired["skills"]:
        path = target / name
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError(f"skill destination must be a regular directory: {path}")
        if path.exists():
            list(tree_files(path))  # Refuse links before any copy/rename.
    previous = read_manifest(target, desired["skills"])
    existing = [name for name in desired["skills"] if (target / name).exists()]
    modified = conflicts(target, previous, desired)
    if check:
        if not previous:
            raise ValueError("no managed installation found; install the complete bundle first")
        missing = [name for name in previous["files"] if not (target / name).is_file()]
        if modified or missing:
            raise ValueError("installed files modified or missing: " + ", ".join(sorted(set(modified + missing))))
        if previous["files"] != desired["files"] or previous.get("version") != desired["version"]:
            raise ValueError("installation differs from this checkout; run --update")
        return {"status": "ok", "version": desired["version"], "skills": len(desired["skills"]),
                "smoke_checks": smoke_check(target)}
    if (existing or previous) and not update:
        raise ValueError("installation already exists; use --update (local edits are protected)")
    if existing and not previous and not replace_existing:
        raise ValueError("unmanaged skill folders found; use --update --replace-existing to back them up and replace")
    if modified and not replace_existing:
        raise ValueError("local edits conflict: " + ", ".join(modified) + "; use --update --replace-existing only to replace with a backup")
    result = {"status": "dry-run" if dry_run else "installed", "version": desired["version"],
              "destination": str(target), "skills": len(desired["skills"]), "files": len(files),
              "replacing_local_changes": modified, "backup": None}
    if dry_run:
        return result
    target.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".instagram-agent-stage-", dir=target))
    backup = target / BACKUPS / uuid.uuid4().hex
    moved, activated = [], []
    manifest_moved = False
    try:
        for name in existing:
            shutil.copytree(target / name, stage / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        if previous:
            for name in previous["files"]:
                if name not in files and (stage / name).is_file():
                    (stage / name).unlink()
        for name, source_path in files.items():
            path = stage / name
            if path.is_dir():
                # An explicit replacement may repair a file/directory clash.
                # The live copy remains untouched until activation and backup.
                shutil.rmtree(path)
            parents = []
            for parent in path.parents:
                if parent == stage:
                    break
                parents.append(parent)
            for parent in reversed(parents):
                if parent.is_file():
                    parent.unlink()
                parent.mkdir(exist_ok=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, path)
        result["smoke_checks"] = smoke_check(stage)
        (stage / MANIFEST).write_text(json.dumps(desired, indent=2) + "\n", encoding="utf-8")
        if existing or (target / MANIFEST).exists():
            if (target / BACKUPS).is_symlink():
                raise ValueError("backup directory must not be a symbolic link")
            backup.mkdir(parents=True)
        for name in desired["skills"]:
            if name in existing:
                (target / name).rename(backup / name)
                moved.append(name)
            (stage / name).rename(target / name)
            activated.append(name)
        if (target / MANIFEST).exists():
            (target / MANIFEST).rename(backup / MANIFEST)
            manifest_moved = True
        (stage / MANIFEST).rename(target / MANIFEST)
        result["backup"] = str(backup) if backup.exists() else None
        return result
    except Exception:
        for name in reversed(activated):
            shutil.rmtree(target / name)
        for name in moved:
            (backup / name).rename(target / name)
        if manifest_moved:
            if (target / MANIFEST).exists():
                (target / MANIFEST).unlink()
            (backup / MANIFEST).rename(target / MANIFEST)
        raise
    finally:
        shutil.rmtree(stage)


def install(target, source=ROOT, *, update=False, replace_existing=False, dry_run=False, check=False):
    target = destination(target, source)
    lock = target / ".instagram-agent-install.lock"
    if dry_run or check:
        if lock.exists() or lock.is_symlink():
            raise ValueError("installation is locked by another run; retry when it finishes")
        return _install(target, source, update=update, replace_existing=replace_existing,
                        dry_run=dry_run, check=check)
    bundle(source)  # Reject incomplete sources before creating any destination.
    target.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ValueError("installation is locked by another run; retry when it finishes") from exc
    try:
        return _install(target, source, update=update, replace_existing=replace_existing)
    finally:
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", default="~/.claude/skills", help="explicit destination for all ig-* folders")
    parser.add_argument("--update", action="store_true", help="update a managed installation, backing up replaced folders")
    parser.add_argument("--replace-existing", action="store_true", help="with --update, explicitly replace local edits/unmanaged folders with backup")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="preflight only; write nothing")
    mode.add_argument("--check", action="store_true", help="verify installed hashes and tools without changing files")
    args = parser.parse_args()
    if args.replace_existing and not args.update:
        parser.error("--replace-existing requires --update")
    if args.check and (args.update or args.replace_existing):
        parser.error("--check cannot be combined with update flags")
    try:
        result = install(args.skills_dir, update=args.update, replace_existing=args.replace_existing,
                         dry_run=args.dry_run, check=args.check)
    except (OSError, ValueError, SyntaxError, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
