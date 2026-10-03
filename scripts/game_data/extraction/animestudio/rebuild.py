"""Rebuild the managed ``tools/AnimeStudio`` projects the export wrappers use.

Prefers the repo-local SDK installed by ``setup_dotnet9`` and requires a .NET 9
SDK unless ``--use-system-dotnet`` is given. Each target is restored (unless
``--no-restore``) and built, and its output executable path is printed.

Run from the repository root::

    python -m scripts.game_data.extraction.animestudio.rebuild [--target CLI|GUI|Patcher|AllManaged] [--configuration Debug|Release] [--no-restore] [--use-system-dotnet] [--dry-run]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from scripts.game_data.extraction.animestudio.setup_dotnet9 import (
    ANIME_ROOT,
    DEFAULT_INSTALL_DIR,
    DOTNET_CLI_HOME,
    dotnet_environment,
)

LOCAL_DOTNET_EXE = DEFAULT_INSTALL_DIR / "dotnet.exe"
SETUP_HINT = r".\scripts\game_data\extraction\animestudio\setup_dotnet9.bat"
PROJECTS = {
    "CLI": ("AnimeStudio.CLI", "net9.0-windows"),
    "GUI": ("AnimeStudio.GUI", "net9.0-windows"),
    "Patcher": ("AnimeStudio.Patcher", "net9.0"),
}
TARGETS = {**{name: [name] for name in PROJECTS}, "AllManaged": list(PROJECTS)}


def step(message: str) -> None:
    print(f"[rebuild-animestudio] {message}", flush=True)


def format_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def find_dotnet(use_system: bool) -> Path:
    if not use_system and LOCAL_DOTNET_EXE.is_file():
        return LOCAL_DOTNET_EXE
    system = shutil.which("dotnet.exe") or shutil.which("dotnet")
    if system:
        return Path(system)
    raise SystemExit(f"dotnet.exe was not found. Run {SETUP_HINT} first.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", "-Target", choices=list(TARGETS), default="CLI")
    parser.add_argument("--configuration", "-Configuration", choices=["Debug", "Release"], default="Release")
    parser.add_argument("--no-restore", "-NoRestore", action="store_true")
    parser.add_argument("--use-system-dotnet", "-UseSystemDotnet", action="store_true")
    parser.add_argument("--dry-run", "-DryRun", action="store_true", help="print the commands without running them")
    args = parser.parse_args(argv)

    dotnet_exe = find_dotnet(args.use_system_dotnet)
    is_local = dotnet_exe == LOCAL_DOTNET_EXE
    env = dotnet_environment(dotnet_exe.parent if is_local else None)

    def run(command: list[str]) -> None:
        if args.dry_run:
            step(f"Would run: {format_command(command)}")
            return
        result = subprocess.run(command, env=env)
        if result.returncode != 0:
            raise SystemExit(f"Command failed with exit code {result.returncode}: {format_command(command)}")

    if args.dry_run:
        step("Dry run mode is enabled.")
    else:
        DOTNET_CLI_HOME.mkdir(parents=True, exist_ok=True)
        version = subprocess.run([str(dotnet_exe), "--version"], env=env, capture_output=True, text=True).stdout.strip()
        if not version.startswith("9."):
            if not args.use_system_dotnet:
                raise SystemExit(
                    f"Found SDK {version or '<none>'} at {dotnet_exe}. Run {SETUP_HINT}, "
                    "or rerun with --use-system-dotnet to override."
                )
            print(f"WARNING: Using non-.NET 9 SDK {version} because --use-system-dotnet was specified.", flush=True)
        step(f"Using dotnet SDK {version} from {dotnet_exe}")

    for name in TARGETS[args.target]:
        project_name, framework = PROJECTS[name]
        project = ANIME_ROOT / project_name / f"{project_name}.csproj"
        output = ANIME_ROOT / project_name / "bin" / args.configuration / framework / f"{project_name}.exe"
        step(f"Preparing {name} build")
        if not args.no_restore:
            run([str(dotnet_exe), "restore", str(project),
                 "-p:RestoreIgnoreFailedSources=true", "-p:NuGetAudit=false"])
        build = [str(dotnet_exe), "build", str(project), "-c", args.configuration, "-f", framework]
        if args.no_restore:
            build.append("--no-restore")
        run(build)
        step(f"{name} output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
