"""Extract what the selected WebUI pages read, then build those pages.

``export.bat`` loads ``endfield_paths.bat`` and runs this module. A run names
its pages; ``scripts/webui/pages.py`` turns them into build tasks, the export
scope those tasks read, and the freshness requirements the build checks.

    export.bat                        rebuild every page from the current export
    export.bat --from-game            extract what every page reads, then build
    export.bat story --from-game      the lean Story/Text extraction and build
    export.bat map audio --from-game  only what Map and Audio read
    export.bat debug --from-game      every structured block and Unity class
    export.bat --changed-only         synchronize all inputs, build all + Updates

Every run writes a wall-time and process-tree memory benchmark under
``reports/export/`` and the build-step timing report beside it.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    raise SystemExit("Run this maintained entry point as: python -m scripts.webui.export")

from scripts.common import OUT_DIR, read_json, require_export_layout, resolve_installed_game_data_root
from scripts.game_data.extraction import benchmark_export
from scripts.game_data.extraction.scope import STRUCTURED_LEVELS
from scripts.game_data.extraction.export_changed_game_data import exclusive_workflow_lock
from scripts.game_data.extraction.export_sync import SyncTransaction, SyncError, input_identity, sync_root
from scripts.game_data.extraction.verify_export_freshness import verify
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout, configured_export_root
from scripts.webui.build_graph import (
    REPORT_MD,
    phase_payloads,
    plan_lines,
    run_graph,
    write_reports,
)
from scripts.webui.pages import PAGE_ALIASES, PAGES, BuildOptions, BuildPlan, extraction_scope, plan_build, resolve_pages

DEBUG = "debug"
ALL = "all"
TARGETS = (*PAGES, *PAGE_ALIASES, ALL, DEBUG)
HELP_TOKENS = {"-h", "--help", "/?", "/h", "help"}
#: The Story MonoBehaviour name filter the first-time setup passes through.
STORY_NAME_FILTER = "--animestudio-story-monobehaviour-names"
#: Changed-only refreshes these structured levels; the local snapshot records one.
CHANGED_ONLY_LEVELS = ("focused", "default")
OWN_FLAGS = {"--from-game", "--changed-only", "--skip-freshness", "--full-source-graph", "--show-plan"}
OWN_VALUE_OPTIONS = {"--game-root", "--webui-jobs", "--structured-dump-mode", "--previous-export-root"}

USAGE = """\
Usage: export.bat [PAGE ...] [--from-game | --changed-only] [options]

Builds WebUI pages from the export root (export_full). With --from-game it
first extracts from the installed client exactly what those pages read.

Pages (default: every page; Updates compares two exports, see build_updates.bat):
  story        Story and Text Tables, text only: Table, JsonData and the Story
               carrier JSON (TextAsset, MonoBehaviour, PlayableDirector); no
               image, video or audio. `text` is an alias.
  story-media  Story and Text Tables with Story's images and videos; with
               --from-game it extracts those media too.
  map          Map recovery, its streaming sidecars and rendered previews.
  characters   Characters.
  gameplay     Gameplay, projectiles, the curated source graph and combat.
  audio        Audio, including the voice lines Story plays. With --from-game
               it also decodes CN audio.
  assets       The Assets index.
  data         The Data page: its decoded datasets, and as files every
               decodable output the other pages do not show.
  all          Every page above; the same as naming none. With --from-game
               this extracts everything, because Data shows the rest.
  debug        Every page, extracting every structured block and Unity class.

A page builds only itself. What it shows from another page -- Story's voice
lines from Audio, the render colours and asset links from the Assets index --
is that page's last publication, so it appears once that page is built;
--show-plan lists them.

Where the data comes from:
  (default)         The current export, after checking that everything the
                    pages read exists and was extracted from the installed
                    build.
  --from-game       Re-extract the pages' inputs from the installed client.
  --changed-only    Synchronize every page's inputs, including Unity, indexes
                    and CN/shared audio. Structured files use the local delta;
                    other inputs use the normal exporter and its valid caches.
                    Build every page and Updates against the last successful
                    sync. Failed runs keep that baseline; unchanged runs keep
                    the last Updates feed. Missing delta evidence falls back
                    to a full extraction.

Options:
  --game-root PATH  Installed Endfield_Data folder (default: endfield_paths.bat).
  --previous-export-root PATH
                    Initial old export for --changed-only if the current root
                    is incomplete/mixed (default: ENDFIELD_PREVIOUS_EXPORT_ROOT).
                    Subsequent runs use the automatic successful-sync snapshot.
  --skip-freshness  Skip the freshness check for this run. It does not refresh
                    anything; use it only with an export known to be compatible.
  --webui-jobs N    Concurrent builders, and Map's own worker count. Default 4.
  --full-source-graph
                    Index every AssetMap row and emit follow-up reports.
  --structured-dump-mode focused|default
                    Structured level for --changed-only (default focused;
                    `default` adds the Terrain height grids).
  --show-plan       Print the pages, build tasks, extraction scope and
                    freshness requirements, then exit.
  --help            This text.

With --from-game or --changed-only, any other option goes to
scripts\\game_data\\extraction\\export_full_from_game.py, for example
--asset-jobs N, --animestudio-dummy-dlls PATH, --animestudio-no-asset-cache or
--animestudio-story-monobehaviour-names (Story-only runs). Run
"python -m scripts.game_data.extraction.export_full_from_game --help" for them.

Examples:
  export.bat
  export.bat --from-game
  export.bat story --from-game
  export.bat story-media --from-game
  export.bat map --from-game --asset-jobs 4
  export.bat debug --from-game
  export.bat gameplay --skip-freshness
"""


def split_exporter_args(argv: list[str]) -> tuple[list[str], list[str]]:
    """Separate this wrapper's arguments from options meant for the exporter.

    An unknown option passes through with the values that follow it, up to the
    next option or page name; everything after ``--`` passes through as is.
    """
    own: list[str] = []
    exporter: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--":
            exporter.extend(argv[index + 1:])
            break
        name = token.split("=", 1)[0]
        if not token.startswith("-") or name in OWN_FLAGS or token in HELP_TOKENS:
            own.append(token)
        elif name in OWN_VALUE_OPTIONS:
            own.append(token)
            if "=" not in token and index + 1 < len(argv):
                index += 1
                own.append(argv[index])
        else:
            exporter.append(token)
            while (
                "=" not in token
                and index + 1 < len(argv)
                and not argv[index + 1].startswith("-")
                and argv[index + 1].lower() not in TARGETS
            ):
                index += 1
                exporter.append(argv[index])
        index += 1
    return own, exporter


def parse_args(argv: list[str]) -> argparse.Namespace:
    own, exporter = split_exporter_args(argv)
    parser = argparse.ArgumentParser(
        prog="export.bat", add_help=False, usage="export.bat [PAGE ...] [options]; export.bat --help for all of them",
    )
    parser.add_argument("targets", nargs="*", type=str.lower)
    parser.add_argument("--from-game", action="store_true")
    parser.add_argument("--changed-only", action="store_true")
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--previous-export-root", type=Path)
    parser.add_argument("--skip-freshness", action="store_true")
    parser.add_argument("--webui-jobs", type=int, default=4)
    parser.add_argument("--full-source-graph", action="store_true")
    parser.add_argument("--structured-dump-mode", choices=CHANGED_ONLY_LEVELS)
    parser.add_argument("--show-plan", action="store_true")
    # Pages may come before or after options.
    args = parser.parse_intermixed_args(own)
    args.exporter_args = exporter

    def fail(message: str) -> None:
        parser.exit(2, f"export.bat: {message}\n")

    unknown = [target for target in args.targets if target not in TARGETS]
    if unknown:
        fail(f"unknown page {', '.join(unknown)}; expected {', '.join(TARGETS)}")
    args.debug = DEBUG in args.targets
    pages = [target for target in args.targets if target not in (ALL, DEBUG)]
    if ALL in args.targets and (pages or args.debug):
        fail("all already builds every page; name no other page with it")
    if args.debug and pages:
        fail("debug already builds every page; name no other page with it")
    if args.webui_jobs < 1:
        fail("--webui-jobs must be at least 1")
    if args.changed_only:
        if pages or args.debug:
            fail("--changed-only builds every page before its local snapshot advances; name no page")
        if args.from_game:
            fail("choose --changed-only or --from-game")
        if args.skip_freshness:
            fail("--changed-only requires its freshness checks; drop --skip-freshness")
        args.from_game = False
    elif args.structured_dump_mode:
        fail("--structured-dump-mode chooses the --changed-only level; page runs derive their scope")
    if args.previous_export_root and not args.changed_only:
        fail("--previous-export-root initializes the --changed-only comparison")
    if args.changed_only:
        managed = {"--output", "--sources", "--structured", "--skip-structured", "--skip-animestudio",
                   "--skip-vfs-index", "--report-only", "--structured-incremental-manifest",
                   "--unity-json", "--unity-convert", "--animestudio-scope", "--asset-mode",
                   "--animestudio-asset-mode", "--webui-textures-only", "--animestudio-stages",
                   "--animestudio", "--structured-dumper", "--fluffy"}
        refused = [token for token in args.exporter_args if token.split("=", 1)[0] in managed]
        if refused:
            fail(f"--changed-only owns its complete extraction scope; drop {refused[0]}")
    if args.exporter_args and not (args.from_game or args.changed_only):
        fail(
            f'"{args.exporter_args[0]}" only applies while re-extracting from the installed game; '
            "add --from-game, or drop that option"
        )
    args.pages = resolve_pages(pages)
    return args


def log(message: str) -> None:
    print(f"[export {time.strftime('%H:%M:%S')}] {message}", flush=True)


def stage(title: str) -> None:
    print(flush=True)
    log(f"=== {title} ===")


def run(argv: list[str]) -> int:
    log(subprocess.list2cmdline([Path(argv[0]).name, *argv[1:]]))
    return subprocess.run(argv, cwd=REPO_ROOT, check=False).returncode


def build_options(args: argparse.Namespace, game_root: Path, export_root: Path) -> BuildOptions:
    return BuildOptions(
        jobs=args.webui_jobs,
        game_root=game_root,
        export_root=export_root,
        decode_audio=args.from_game or args.changed_only,
        asset_mode="debug" if args.debug else "default",
        full_source_graph=args.full_source_graph,
    )


def exporter_command(plan: BuildPlan, args: argparse.Namespace, game_root: Path, export_root: Path) -> list[str]:
    scope = extraction_scope(plan, everything=args.debug)
    command = [
        sys.executable, "-m", "scripts.game_data.extraction.export_full_from_game",
        *scope.exporter_args(),
        "--game-root", str(game_root),
        "--output", str(export_root),
    ]
    # The object index is merged from the carrier JSON jobs, so every run that
    # re-exports them republishes it; Story and Audio read it.
    if scope.exports_object_index_types:
        command.append("--animestudio-object-index")
    # The debug export also keeps AnimeStudio's own Sprite images
    # (game/Sprite.sqlite) and checks every Sprite crop document against them.
    if args.debug and "Sprite" in scope.convert_types:
        command.append("--sprite-images")
    return command + list(args.exporter_args)


def changed_only_exporter_command(
    plan: BuildPlan, args: argparse.Namespace, game_root: Path, export_root: Path, manifest: Path,
) -> list[str]:
    """Refresh the rest of the complete scope alongside the authenticated delta."""
    scope = extraction_scope(plan)
    level = args.structured_dump_mode or "focused"
    remaining = replace(scope, structured=scope.structured - frozenset(STRUCTURED_LEVELS[level]))
    command = [sys.executable, "-m", "scripts.game_data.extraction.export_full_from_game",
               *remaining.exporter_args(), "--structured-incremental-manifest", str(manifest),
               "--game-root", str(game_root), "--output", str(export_root)]
    if scope.exports_object_index_types:
        command.append("--animestudio-object-index")
    return command + list(args.exporter_args)


def print_plan(plan: BuildPlan, args: argparse.Namespace) -> None:
    print(f"pages: {', '.join(plan.pages)}")
    if args.changed_only:
        level = args.structured_dump_mode or "focused"
        print(f"extraction: structured delta at the {level} level; all remaining inputs refreshed")
        print("comparison: last successful sync -> current export; Updates published on success")
    elif args.from_game:
        print(f"extraction: {extraction_scope(plan, everything=args.debug).describe()}")
    else:
        print("extraction: none (the current export is reused)")
    requirements = plan.requirements
    print(f"requires current: structured {', '.join(requirements.structured) or '-'}; "
          f"Unity {', '.join(requirements.unity) or '-'}")
    print(f"current when present: structured {', '.join(requirements.optional_structured) or '-'}; "
          f"Unity {', '.join(requirements.optional_unity) or '-'}")
    if plan.published:
        print(f"reads the last publication of: {', '.join(plan.published)}")
    print("build tasks:")
    for line in plan_lines(plan.tasks):
        print(f"  {line}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if any(token in HELP_TOKENS for token in argv):
        print(USAGE)
        return 0
    args = parse_args(argv)
    game_root = (args.game_root or resolve_installed_game_data_root()).resolve()
    export_root = configured_export_root().resolve()
    plan = plan_build(args.pages, build_options(args, game_root, export_root))
    name_filtered = any(token.split("=", 1)[0] == STORY_NAME_FILTER for token in args.exporter_args)
    if name_filtered and "MonoBehaviour" not in plan.requirements.partial_ok:
        print(
            f"export.bat: {STORY_NAME_FILTER} exports only Story-named MonoBehaviours, "
            f"which {', '.join(page for page in plan.pages if page != 'story')} cannot use; "
            "pass it only for a story run",
            file=sys.stderr,
        )
        return 2
    if args.show_plan:
        print_plan(plan, args)
        return 0

    if not os.environ.get(benchmark_export.ACTIVE_ENV):
        # Re-run this module under the process-tree benchmark, which marks the
        # child active so it does not wrap itself again.
        print("[export] Starting a monitored run; benchmark reports go to reports/export.", flush=True)
        label = "export_changed" if args.changed_only else "export"
        return benchmark_export.main(["--label", label, "--", sys.executable, "-m", "scripts.webui.export", *argv])

    try:
        with exclusive_workflow_lock(export_root, state_root=sync_root(export_root)):
            return execute_export(args, plan, game_root, export_root)
    except (SyncError, OSError, ValueError, RuntimeError) as exc:
        print(f"export.bat: {exc}", file=sys.stderr)
        return 1


def execute_export(args: argparse.Namespace, plan: BuildPlan, game_root: Path, export_root: Path) -> int:
    # Children resolve the installed client and export root from these, so a
    # --game-root run agrees across every stage.
    os.environ["ENDFIELD_GAME_ROOT"] = str(game_root)
    os.environ["ENDFIELD_EXPORT_ROOT"] = str(export_root)

    stage("Resolved export plan")
    log(f"pages: {', '.join(plan.pages)}")
    log(f"game root: {game_root}")
    log(f"export root: {export_root}")
    if args.changed_only:
        log("source: synchronize the installed game; compare against the last successful sync")
    elif args.from_game:
        log(f"source: installed game; {extraction_scope(plan, everything=args.debug).describe()}")
    else:
        log("source: the current export")
    log(f"build tasks: {', '.join(task.name for task in plan.tasks)} (jobs {args.webui_jobs})")

    requirements = plan.requirements
    changed_manifest = ExportLayout(export_root).extraction_incremental_dir / "pending_manifest.json"
    changed_prepared = False
    transaction = None
    identity = None

    def abort_changed(code: int) -> int:
        if changed_prepared:
            log("a later stage failed; the local changed-only snapshot will not advance")
            run([sys.executable, "-m", "scripts.game_data.extraction.export_changed_game_data",
                 "abort", "--manifest", str(changed_manifest)])
        return code

    if args.changed_only:
        stage("Preserving the last successful export for comparison")
        transaction = SyncTransaction(export_root)
        identity = input_identity(game_root)
        previous = args.previous_export_root
        if previous is None:
            configured = os.environ.get("ENDFIELD_PREVIOUS_EXPORT_ROOT", "").strip().strip('"')
            if configured:
                candidate = Path(configured)
                candidate = candidate if candidate.is_absolute() else REPO_ROOT / candidate
                if candidate.is_dir():
                    previous = candidate
        summary = read_json(REPO_ROOT / "reports/export/export_full_summary.json", {})
        # Explicit producer options must take effect even if the installed
        # bytes have not changed. A no-op also requires the declared inputs
        # to exist; a deleted store or media folder needs repair.
        allow_noop = not args.exporter_args and not args.full_source_graph and not args.structured_dump_mode
        if (allow_noop and transaction.state.get("status") == "complete"
                and transaction.state.get("lastSuccessfulInputs") == identity):
            allow_noop = verify(game_root=game_root, output_root=export_root, requirements=requirements) == 0
        if transaction.begin(identity, summary, previous, allow_noop=allow_noop):
            log("installed inputs are unchanged since the last successful sync; keeping the last Updates feed")
            return 0
        log(f"comparison baseline: {transaction.baseline or 'none (initial synchronization)'}")
        log(f"baseline origin: {transaction.state['baselineKind']}")
        level = args.structured_dump_mode or "focused"
        # A killed prepare can leave a pending manifest. Its applied files
        # remain retryable; the independent Updates baseline stays untouched.
        pending = read_json(changed_manifest, {})
        if pending.get("applied") is True and pending.get("baselineAdvanced") is not True:
            code = run([sys.executable, "-m", "scripts.game_data.extraction.export_changed_game_data",
                        "abort", "--manifest", str(changed_manifest)])
            if code:
                return code
        stage("Exporting only changed structured files")
        code = run([
            sys.executable, "-m", "scripts.game_data.extraction.export_changed_game_data", "prepare",
            "--game-root", str(game_root), "--output", str(export_root),
            "--structured-dump-mode", level, "--manifest", str(changed_manifest),
        ])
        if code:
            stage("Delta unavailable; extracting the complete current scope")
            code = run(exporter_command(plan, args, game_root, export_root))
            if code:
                return code
            # The full export now provides a current authenticated starting
            # point; seed the private logical-file snapshot without old data.
            code = run([sys.executable, "-m", "scripts.game_data.extraction.export_changed_game_data", "prepare",
                        "--game-root", str(game_root), "--output", str(export_root),
                        "--structured-dump-mode", level, "--manifest", str(changed_manifest),
                        "--initialize-from-full-export"])
            changed_prepared = code == 0
        else:
            changed_prepared = True
            stage("Refreshing Unity, indexes and all remaining structured inputs")
            code = run(changed_only_exporter_command(plan, args, game_root, export_root, changed_manifest))
        if code:
            return abort_changed(code)
    elif args.from_game:
        stage("Extracting the pages' inputs from the installed game")
        code = run(exporter_command(plan, args, game_root, export_root))
        if code:
            return code

    stage("Checking that the pages' inputs are current")
    if args.skip_freshness:
        log("skipped by --skip-freshness")
    else:
        code = verify(game_root=game_root, output_root=export_root, requirements=requirements)
        if code:
            return abort_changed(code)
    require_export_layout(export_root)

    stage(f"Building {', '.join(PAGES[page].title for page in plan.pages)}")
    started = time.perf_counter()
    returncode, runs = run_graph(plan.tasks, args.webui_jobs)
    wall_seconds = round(time.perf_counter() - started, 3)
    phases = phase_payloads(runs)
    serial = round(sum(task["seconds"] for phase in phases for task in phase["tasks"]), 3)
    write_reports({
        "schemaVersion": 3,
        "generated": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if returncode == 0 else "failed",
        "returnCode": returncode,
        "jobs": args.webui_jobs,
        "wallSeconds": wall_seconds,
        "serialTaskSeconds": serial,
        "overlapSecondsSaved": round(max(0.0, serial - wall_seconds), 3),
        "options": {
            "pages": list(plan.pages),
            "fromGame": args.from_game,
            "changedOnly": args.changed_only,
            "debug": args.debug,
            "fullSourceGraph": args.full_source_graph,
            "exportRoot": str(export_root),
            "gameRoot": str(game_root),
        },
        "graph": [{"name": task.name, "after": list(task.after)} for task in plan.tasks],
        "phases": phases,
    })
    log(f"timing report: {REPORT_MD.relative_to(REPO_ROOT)}")
    if returncode:
        return abort_changed(returncode)

    if args.changed_only:
        current_identity = input_identity(game_root)
        if current_identity != identity:
            raise SyncError("installed inputs changed during the run; repeat synchronization with the game updater idle")
        updates_stage = transaction.root / "pending-updates"
        if transaction.baseline is not None:
            if updates_stage.exists():
                import shutil
                if updates_stage.is_symlink() or updates_stage.resolve().parent != transaction.root.resolve():
                    raise SyncError(f"unsafe Updates staging cleanup: {updates_stage}")
                shutil.rmtree(updates_stage)
            stage("Comparing exports for Updates")
            code = run([sys.executable, "-m", "scripts.webui.updates.build_updates",
                        "--previous-export-root", str(transaction.baseline), "--export-root", str(export_root),
                        "--refresh-previous-export-baseline", "--exact",
                        "--state-dir", str(transaction.root / "updates-cache"),
                        "--out", str(updates_stage / "latest.json"),
                        "--characters-out", str(updates_stage / "characters.json")])
            if code:
                return abort_changed(code)
        else:
            log("no prior complete export: initializing the baseline without inventing an all-added update")
        stage("Committing the local changed-only snapshot")
        code = run([sys.executable, "-m", "scripts.game_data.extraction.export_changed_game_data",
                    "finalize", "--manifest", str(changed_manifest)])
        if code:
            return abort_changed(code)
        if input_identity(game_root) != identity:
            raise SyncError("installed inputs changed during comparison; the successful-sync baseline was not advanced")
        transaction.commit(identity, publish=(lambda: publish_updates(updates_stage)) if transaction.baseline else None,
                           current_inputs=lambda: input_identity(game_root))
    stage("Export complete")
    return 0


def publish_updates(staged: Path) -> None:
    """Replace the feed and all page sidecars as one directory publication."""
    import shutil
    destination = OUT_DIR / "updates"
    backup = staged.parent / "previous-updates-publication"
    if not (staged / "latest.json").is_file():
        raise SyncError(f"missing staged Updates feed: {staged}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        if backup.is_symlink() or backup.resolve().parent != staged.parent.resolve():
            raise SyncError(f"unsafe Updates publication recovery: {backup}")
        if destination.exists():
            shutil.rmtree(backup)
        else:
            backup.replace(destination)
    had_previous = destination.exists()
    if had_previous:
        destination.replace(backup)
    try:
        staged.replace(destination)
    except BaseException:
        if had_previous:
            backup.replace(destination)
        raise
    if had_previous:
        # backup is an explicitly named managed directory, outside the export.
        if backup.resolve().parent != staged.parent.resolve():
            raise SyncError(f"unsafe publication cleanup: {backup}")
        shutil.rmtree(backup)


if __name__ == "__main__":
    raise SystemExit(main())
