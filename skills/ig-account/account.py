#!/usr/bin/env python3
"""Resolve local account files without a global active-account setting."""

import argparse
import json
from pathlib import Path
import re


FILES = {name: name + ".md" for name in ("voice", "strategy", "plan", "swipe", "log", "results")}
FILES["publications"] = "publications.json"
FILES["lexicon"] = "slop.json"
FILES["lexicon_tr"] = "slop.tr.json"
DEFAULT_ROOT = "~/.claude/instagram"


def normalize_handle(value):
    handle = value.strip().removeprefix("@").lower()
    if not re.fullmatch(r"[a-z0-9_.]{1,30}", handle) or handle in (".", ".."):
        raise ValueError("use an Instagram handle (1–30 letters, digits, underscores or periods)")
    return handle


def accounts_directory(root):
    directory = Path(root).expanduser().resolve() / "accounts"
    if directory.is_symlink():
        raise ValueError("accounts directory must not be a symbolic link")
    return directory


def list_accounts(root=DEFAULT_ROOT):
    directory = accounts_directory(root)
    if not directory.exists():
        return []
    return sorted(p.name for p in directory.iterdir()
                  if p.is_dir() and not p.is_symlink()
                  and re.fullmatch(r"[a-z0-9_.]{1,30}", p.name))


def context(directory, handle):
    paths = {}
    for name, filename in FILES.items():
        path = directory / filename
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError(f"account file must be a regular file: {path}")
        paths[name] = str(path)
    return {"account": handle, "mode": "account" if handle else "legacy",
            "directory": str(directory), "paths": paths}


def resolve(root=DEFAULT_ROOT, account=None):
    root = Path(root).expanduser().resolve()
    accounts = accounts_directory(root)
    if account is None:
        # Even a single named account needs explicit selection. Two chats must
        # never change each other's target via a persistent active-account flag.
        if accounts.exists() and any(accounts.iterdir()):
            raise ValueError("choose the publishing account with --account HANDLE; "
                             "no global active account is used")
        return context(root, None)
    handle = normalize_handle(account)
    directory = accounts / handle
    if directory.is_symlink():
        raise ValueError("account directory must not be a symbolic link")
    if not directory.is_dir():
        raise ValueError(f"unknown account @{handle}; run account.py init {handle} first")
    # Never fall back to legacy or another account when a file is missing.
    return context(directory, handle)


def initialize(root, account):
    handle = normalize_handle(account)
    directory = accounts_directory(root) / handle
    if directory.is_symlink():
        raise ValueError("account directory must not be a symbolic link")
    directory.mkdir(parents=True, exist_ok=True)
    return context(directory, handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=DEFAULT_ROOT, help="local data root")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("init", help="create an account folder; never import legacy files")
    create.add_argument("handle")
    commands.add_parser("list", help="list account handles without reading their content")
    show = commands.add_parser("show", help="resolve paths; does not read or create files")
    show.add_argument("--account")
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = initialize(args.root, args.handle)
        elif args.command == "list":
            result = {"accounts": list_accounts(args.root)}
        else:
            result = resolve(args.root, args.account)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
