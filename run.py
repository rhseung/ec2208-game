from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
MIN_PYTHON = (3, 9)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up and run the EC2208 dungeon crawler.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("run", "test"),
        default="run",
        help="run the game or run the test suite",
    )
    parser.add_argument(
        "--reinstall",
        action="store_true",
        help="force reinstalling dependencies before running",
    )
    args = parser.parse_args()

    if sys.version_info < MIN_PYTHON:
        version = ".".join(map(str, MIN_PYTHON))
        print(f"Python {version}+ is required. Current Python is {platform_version()}.", file=sys.stderr)
        return 1

    ensure_venv()
    python = venv_python()
    if args.reinstall or not dependency_available(python, "textual"):
        install_dependencies(python)

    command = [str(python), "-m", "unittest"] if args.command == "test" else [str(python), "main.py"]
    return subprocess.call(command, cwd=ROOT)


def ensure_venv() -> None:
    python = venv_python()
    if python.exists():
        return
    print("Creating virtual environment in .venv...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=ROOT)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def install_dependencies(python: Path) -> None:
    ensure_pip(python)
    print("Installing dependencies from requirements.txt...")
    subprocess.check_call(
        [
            str(python),
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            "-r",
            str(REQUIREMENTS),
        ],
        cwd=ROOT,
    )


def ensure_pip(python: Path) -> None:
    if subprocess.run(
        [str(python), "-m", "pip", "--version"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0:
        return

    print("Bootstrapping pip in the virtual environment...", flush=True)
    try:
        subprocess.check_call([str(python), "-m", "ensurepip", "--upgrade"], cwd=ROOT)
    except subprocess.CalledProcessError:
        print("Could not bootstrap pip automatically.", file=sys.stderr)
        print("Try running: python3 -m ensurepip --upgrade", file=sys.stderr)
        raise


def dependency_available(python: Path, module_name: str) -> bool:
    result = subprocess.run(
        [str(python), "-c", f"import {module_name}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def platform_version() -> str:
    return ".".join(str(part) for part in sys.version_info[:3])


if __name__ == "__main__":
    raise SystemExit(main())
