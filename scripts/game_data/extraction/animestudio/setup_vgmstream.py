"""Install the pinned vgmstream CLI that Audio decode uses.

Downloads the pinned ``vgmstream-win64.zip`` release, refuses it unless its
SHA-256 matches the pinned digest, and copies the folder holding
``vgmstream-cli.exe`` into ``tools/vgmstream/``. An existing install is reused
unless ``--force`` is given.

Run from the repository root::

    python -m scripts.game_data.extraction.animestudio.setup_vgmstream [--force] [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from scripts.repo_paths import REPO_ROOT

VERSION = "r2117"
ARCHIVE_SHA256 = "6c4a8a3813864fefed081bbd337dbc0ad93bf88e0b92f5db98d7ab258b22dc6c"
DOWNLOAD_URL = f"https://github.com/vgmstream/vgmstream/releases/download/{VERSION}/vgmstream-win64.zip"
INSTALL_ROOT = REPO_ROOT / "tools" / "vgmstream"
EXECUTABLE = INSTALL_ROOT / "vgmstream-cli.exe"


def step(message: str) -> None:
    print(f"[setup-vgmstream] {message}", flush=True)


def download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", "-Force", action="store_true", help="reinstall even when vgmstream-cli.exe exists")
    parser.add_argument("--dry-run", "-DryRun", action="store_true", help="print the plan without downloading")
    args = parser.parse_args(argv)

    if EXECUTABLE.is_file() and not args.force:
        step(f"Reusing {EXECUTABLE}")
        return 0
    if args.dry_run:
        step(f"Would download {DOWNLOAD_URL}")
        step(f"Would verify SHA-256 {ARCHIVE_SHA256}")
        step(f"Would install to {INSTALL_ROOT}")
        return 0

    with tempfile.TemporaryDirectory(prefix="fluffy-dump-vgmstream-") as work:
        work_root = Path(work)
        archive = work_root / "vgmstream-win64.zip"
        stage = work_root / "stage"
        step(f"Downloading vgmstream {VERSION}...")
        download(DOWNLOAD_URL, archive)
        actual = sha256_file(archive)
        if actual != ARCHIVE_SHA256:
            raise SystemExit(f"vgmstream archive SHA-256 mismatch: expected {ARCHIVE_SHA256}, got {actual}")
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(stage)
        staged = next(stage.rglob("vgmstream-cli.exe"), None)
        if staged is None:
            raise SystemExit("Downloaded archive does not contain vgmstream-cli.exe")
        shutil.copytree(staged.parent, INSTALL_ROOT, dirs_exist_ok=True)
    if not EXECUTABLE.is_file():
        raise SystemExit(f"vgmstream-cli.exe was not installed at {EXECUTABLE}")
    step(f"Installed {EXECUTABLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
