#!/usr/bin/env python3
"""
Build script for Windows EXE using PyInstaller.

Usage examples:
  python build.py                  # onefile, windowed, name=SystemCheckPy, target=main.py
  python build.py --console        # onefile, console
  python build.py --name MyApp     # custom exe name
  python build.py --target main.py # build from specific entry point
  python build.py --clean          # clean build/ and dist/ before building
  python build.py --version        # show version and exit
  python build.py --add-data "dir1;dir2"  # add additional data files
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Union

# Version of the build script
__version__ = "1.1.0"

# Paths
ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "SystemCheckPy.spec"
VERSION_FILE = ROOT / "VERSION"

# Default files to include
DEFAULT_DATA_FILES = [
    ("commands.py", "."),
    ("system_checks.py", "."),
    ("logger.py", "."),
    ("admin_check.py", "."),
    ("logs", "logs"),
]


def get_version() -> str:
    """Get version from VERSION file or use default."""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding='utf-8').strip()
    return __version__


def run(cmd: List[str], cwd: Optional[Union[str, Path]] = None) -> int:
    """Run a command and return its exit code."""
    print("$", " ".join(f'"{x}"' if ' ' in str(x) else str(x) for x in cmd))
    try:
        return subprocess.call(cmd, cwd=cwd, shell=False)
    except Exception as e:
        print(f"Error running command: {e}", file=sys.stderr)
        return 1


def ensure_pyinstaller() -> None:
    """Ensure PyInstaller is installed."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found. Installing...")
        code = run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"]) or \
               run([sys.executable, "-m", "pip", "install", "pyinstaller>=5.0"])
        if code != 0:
            print("Failed to install PyInstaller. Exiting.", file=sys.stderr)
            sys.exit(code)


def clean() -> None:
    """Clean build artifacts."""
    print("Cleaning build artifacts...")
    for p in (DIST, BUILD, SPEC):
        if p.is_dir():
            print(f"Removing directory: {p}")
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file():
            print(f"Removing file: {p}")
            p.unlink(missing_ok=True)
    print("Clean complete.")


def parse_add_data(args: List[str]) -> List[Tuple[str, str]]:
    """Parse --add-data arguments into PyInstaller format."""
    data_files = []
    for item in args:
        if ';' in item:
            src, dst = item.split(';', 1)
            data_files.append((src.strip(), dst.strip()))
        else:
            data_files.append((item, '.'))
    return data_files


def build(args: argparse.Namespace) -> None:
    """Build the application using PyInstaller."""
    ensure_pyinstaller()

    if args.clean:
        clean()
        if args.clean_only:
            return

    name = args.name or "SystemCheckPy"
    target = args.target or "main.py"
    version = get_version()

    # Prepare PyInstaller arguments
    pyi_args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", name,
        "--add-data", f"{ROOT / 'commands.py'};.",
        "--add-data", f"{ROOT / 'system_checks.py'};.",
        "--add-data", f"{ROOT / 'logger.py'};.",
        "--add-data", f"{ROOT / 'admin_check.py'};.",
        "--add-data", f"{ROOT / 'logs'};logs",
    ]

    # Add additional data files
    if args.add_data:
        for src, dst in parse_add_data(args.add_data):
            if not (ROOT / src).exists():
                print(f"Warning: Source file/directory not found: {src}")
                continue
            pyi_args.extend(["--add-data", f"{src};{dst}"])

    # Console/Windowed mode
    if not args.console:
        pyi_args.append("--windowed")
        pyi_args.append("--noconsole")
    
    # Version info
    if args.version_info:
        pyi_args.extend(["--version-file", str(ROOT / 'version_info.txt')])
    
    # Add target file
    pyi_args.append(target)

    # Run PyInstaller
    print(f"Building {name} v{version}...")
    print("Command:", " ".join(f'"{x}"' if ' ' in x else x for x in pyi_args))
    
    code = run(pyi_args)
    if code != 0:
        print(f"PyInstaller failed with exit code {code}", file=sys.stderr)
        sys.exit(code)

    # Verify the build
    exe_path = DIST / f"{name}.exe"
    if exe_path.exists():
        print("\nBuild successful!")
        print(f"Executable: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / (1024*1024):.2f} MB")
        
        # Copy additional files to dist directory
        if args.copy_to_dist:
            print("\nCopying additional files to dist directory...")
            for item in args.copy_to_dist:
                src = ROOT / item
                dst = DIST / item
                try:
                    if src.is_file():
                        shutil.copy2(src, dst)
                        print(f"Copied: {src} -> {dst}")
                    elif src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                        print(f"Copied directory: {src} -> {dst}")
                except Exception as e:
                    print(f"Error copying {src}: {e}", file=sys.stderr)
        
        sys.exit(0)
    else:
        print("\nBuild completed, but EXE not found at:", exe_path, file=sys.stderr)
        if DIST.exists():
            print("\nContents of dist/:", "\n  " + "\n  ".join(str(p.name) for p in DIST.iterdir()))
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"Build SystemCheckPy v{get_version()} with PyInstaller",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--name",
        help="Output executable name (without .exe)",
        default="SystemCheckPy"
    )
    
    parser.add_argument(
        "--target",
        help="Entry point script",
        default="main.py"
    )
    
    parser.add_argument(
        "--console",
        action="store_true",
        help="Build as console application (show console window)"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts before building"
    )
    
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Only clean build artifacts and exit"
    )
    
    parser.add_argument(
        "--add-data",
        action="append",
        help="Additional files/directories to include (format: src;dst)",
        default=[]
    )
    
    parser.add_argument(
        "--copy-to-dist",
        action="append",
        help="Files/directories to copy to dist folder after build",
        default=[]
    )
    
    parser.add_argument(
        "--version-info",
        action="store_true",
        help="Include version info from version_info.txt"
    )
    
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {get_version()}"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    try:
        if platform.system() != 'Windows':
            print("Warning: This script is optimized for Windows. "
                  "You may encounter issues on other platforms.",
                  file=sys.stderr)
        
        args = parse_args()
        if args.clean_only:
            clean()
            return
            
        build(args)
        
    except KeyboardInterrupt:
        print("\nBuild cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args and args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
