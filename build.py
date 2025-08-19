#!/usr/bin/env python3
"""
Build script for Windows EXE using PyInstaller.

Usage examples:
  python build.py                  # onefile, windowed, name=SystemCheckPy, target=main.py
  python build.py --console        # onefile, console
  python build.py --name MyApp     # custom exe name
  python build.py --target gui.py  # build from another entry point
  python build.py --clean          # clean build/ and dist/ before building
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "SystemCheckPy.spec"


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd, shell=False)


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except Exception:
        print("PyInstaller not found. Installing...")
        code = run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"]) or \
               run([sys.executable, "-m", "pip", "install", "pyinstaller"]) 
        if code != 0:
            print("Failed to install PyInstaller. Exiting.")
            sys.exit(code)


def clean():
    for p in (DIST, BUILD, SPEC):
        if p.is_dir():
            print(f"Removing dir: {p}")
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file():
            print(f"Removing file: {p}")
            p.unlink(missing_ok=True)


def build(args):
    ensure_pyinstaller()

    if args.clean:
        clean()

    name = args.name or "SystemCheckPy"
    target = args.target or "main.py"

    pyi_args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", name,
    ]

    if not args.console:
        pyi_args.append("--windowed")

    pyi_args.append(target)

    code = run(pyi_args)
    if code != 0:
        print("PyInstaller failed with exit code", code)
        sys.exit(code)

    exe_path = DIST / f"{name}.exe"
    if exe_path.exists():
        print("Build finished. EXE path:", exe_path)
        sys.exit(0)
    else:
        print("Build finished, but EXE not found at:", exe_path)
        # list dist contents to help debug
        if DIST.exists():
            print("dist/ contents:")
            for p in DIST.iterdir():
                print(" -", p)
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build EXE with PyInstaller")
    ap.add_argument("--name", help="Executable name (default: SystemCheckPy)")
    ap.add_argument("--target", help="Entry script (default: main.py)")
    ap.add_argument("--console", action="store_true", help="Build console app (omit --windowed)")
    ap.add_argument("--clean", action="store_true", help="Clean build/, dist/ before building")
    return ap.parse_args()


if __name__ == "__main__":
    build(parse_args())
