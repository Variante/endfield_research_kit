"""Install a repo-local .NET SDK for building ``tools/AnimeStudio``.

Reads the official .NET release metadata for the selected channel (default
9.0), downloads the latest GA SDK ``win-x64`` zip, refuses it unless its
SHA-512 matches the published hash, and extracts it into
``tools/AnimeStudio/.dotnet``. An existing install with a matching SDK major is
reused unless ``--force`` is given. Nothing is added to ``PATH``; ``rebuild``
finds the local SDK itself.

Run from the repository root::

    python -m scripts.game_data.extraction.animestudio.setup_dotnet9 [--channel 9.0] [--install-dir PATH] [--force] [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from scripts.repo_paths import REPO_ROOT

ANIME_ROOT = REPO_ROOT / "tools" / "AnimeStudio"
DEFAULT_INSTALL_DIR = ANIME_ROOT / ".dotnet"
DOTNET_CLI_HOME = ANIME_ROOT / ".dotnet-cli"
RELEASE_METADATA_URL = "https://builds.dotnet.microsoft.com/dotnet/release-metadata/{channel}/releases.json"
SDK_RID = "win-x64"


def step(message: str) -> None:
    print(f"[setup-dotnet9] {message}", flush=True)


def dotnet_environment(local_root: Path | None = None) -> dict[str, str]:
    """Return the quiet, repo-local dotnet CLI environment.

    ``local_root`` pins the SDK root and disables machine-wide SDK lookup.
    """
    env = dict(os.environ)
    env.update({
        "DOTNET_CLI_HOME": str(DOTNET_CLI_HOME),
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_NOLOGO": "1",
    })
    if local_root is not None:
        env["DOTNET_ROOT"] = str(local_root)
        env["DOTNET_MULTILEVEL_LOOKUP"] = "0"
    return env


def installed_sdks(dotnet_exe: Path, env: dict[str, str]) -> list[str]:
    try:
        result = subprocess.run([str(dotnet_exe), "--list-sdks"], env=env, capture_output=True, text=True)
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def latest_sdk_file(channel: str) -> tuple[str, str, str]:
    """Return ``(version, url, sha512)`` of the latest SDK zip for ``channel``."""
    with urllib.request.urlopen(RELEASE_METADATA_URL.format(channel=channel)) as response:
        metadata = json.load(response)
    version = metadata["latest-sdk"]
    for release in metadata.get("releases", []):
        for sdk in [release.get("sdk") or {}, *(release.get("sdks") or [])]:
            if sdk.get("version") != version:
                continue
            for item in sdk.get("files", []):
                if item.get("rid") == SDK_RID and str(item.get("name", "")).endswith(".zip"):
                    return version, item["url"], item["hash"].lower()
    raise SystemExit(f"No {SDK_RID} zip for SDK {version} in the {channel} release metadata")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--channel", "-Channel", default="9.0", help="release channel (default 9.0)")
    parser.add_argument("--install-dir", "-InstallDir", type=Path, default=DEFAULT_INSTALL_DIR)
    parser.add_argument("--force", "-Force", action="store_true", help="reinstall even when a matching SDK exists")
    parser.add_argument("--dry-run", "-DryRun", action="store_true", help="print the plan without downloading")
    args = parser.parse_args(argv)

    install_dir = args.install_dir.resolve()
    dotnet_exe = install_dir / "dotnet.exe"
    major = args.channel.split(".", 1)[0] + "."
    env = dotnet_environment(install_dir)

    if not args.force and dotnet_exe.is_file():
        if any(sdk.startswith(major) for sdk in installed_sdks(dotnet_exe, env)):
            step(f"Found an existing .NET {args.channel} SDK in {install_dir}")
            subprocess.run([str(dotnet_exe), "--version"], env=env)
            return 0

    version, url, sha512 = latest_sdk_file(args.channel)
    if args.dry_run:
        step(f"Would download .NET SDK {version} from {url}")
        step(f"Would verify SHA-512 {sha512}")
        step(f"Would extract into {install_dir}")
        return 0

    with tempfile.TemporaryDirectory(prefix="animestudio-dotnet-") as work:
        archive = Path(work) / "dotnet-sdk.zip"
        step(f"Downloading .NET SDK {version}")
        digest = hashlib.sha512()
        with urllib.request.urlopen(url) as response, archive.open("wb") as handle:
            for chunk in iter(lambda: response.read(1 << 20), b""):
                digest.update(chunk)
                handle.write(chunk)
        if digest.hexdigest() != sha512:
            raise SystemExit(f".NET SDK archive SHA-512 mismatch: expected {sha512}, got {digest.hexdigest()}")
        step(f"Installing .NET SDK {version} into {install_dir}")
        install_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(install_dir)
    DOTNET_CLI_HOME.mkdir(parents=True, exist_ok=True)

    step("Installed SDKs:")
    for sdk in installed_sdks(dotnet_exe, env):
        print(sdk)
    step(f"Local .NET {args.channel} setup is ready.")
    step(r"Next step: .\scripts\game_data\extraction\animestudio\rebuild.bat --target CLI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
