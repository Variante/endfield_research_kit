"""The WebUI pages, the build tasks behind them, and what each task reads.

This registry is the one place that says which export a page needs. A page is
a set of root build tasks. Each task declares:

* ``commands`` -- the builder invocations, run in order;
* ``needs`` -- producer tasks of the same page whose output it cannot do
  without; selecting the task selects them too;
* ``after`` -- tasks it must follow when they run in the same build, because it
  reads their output; otherwise it reads what they last published, or goes
  without;
* ``reads`` -- export inputs that must exist and be current;
* ``optional`` -- export inputs it reads when present (its builder degrades
  without them), which must be current when they exist;
* ``uses`` -- export inputs it reads when present but never extracts itself:
  another page's extraction owns them, so without that page in the run they
  are reported as reused, never blocking.

A page may also ``serve`` export outputs directly, as files ``serve.py``
answers at browse time rather than inputs of a build task: the Data page shows
every decodable output the other pages do not.

A build selects pages. Its tasks are the closure of their roots over
``needs``; its extraction scope is the union of every task's ``reads`` and
``optional`` plus every selected page's ``serves``; its freshness check
requires each ``reads`` input to exist and every present task input to come
from the installed build. Updates compares two complete exports and is not a
page here (``build_updates.bat``).

Pages are independent: one page never builds another. ``needs`` stays inside a
page (``check_pages_independent`` enforces it), and a page that shows another
page's data -- Story's voice lines from Audio, Map's texture colours from the
Assets index -- reads what that page last published, so that data appears only
once the other page is built. No builder writes another page's output, which
is what makes any build order safe.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

from scripts.game_data.extraction.scope import (
    EVERYTHING,
    OBJECT_INDEX_JSON_TYPES,
    ExtractionScope,
)
from scripts.game_data.extraction.verify_export_freshness import Requirements
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout

#: MonoBehaviour and PlayableDirector are exported together: the object index
#: is merged from one run's JSON jobs and covers both, so selecting one alone
#: would publish an index without the other's rows.
CARRIERS = tuple(sorted(OBJECT_INDEX_JSON_TYPES))
#: The Story export is text only: tables, JsonData and the Story carrier JSON.
#: No media and no audio -- narrative video file names are bound when another
#: run has extracted video -- so first-time setup reaches Story and Text as
#: fast as possible.
STORY_TEXT = ExtractionScope.of(("table", "json-data"), ("TextAsset", *CARRIERS))
#: Exported files other pages show as media: the Assets page's videos, images,
#: sprites, models and FBX. (Audio shows decoded audio, which the exporter
#: never writes.) `scripts/webui/data_inspector/store_browser.py` leaves the
#: same game/ folders out of the Data page's file list.
PAGE_MEDIA = ExtractionScope.of(
    structured=("video", "audit-video"),
    convert_types=("Texture2D", "Sprite", "Mesh", "Animator"),
)
#: Everything decodable except those media: the Data page's file viewer.
DATA_FILES = ExtractionScope.of(
    structured=(block for block in EVERYTHING.structured_blocks if block not in PAGE_MEDIA.structured),
    json_types=EVERYTHING.json_types,
    convert_types=EVERYTHING.convert_types - PAGE_MEDIA.convert_types,
)


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    environment: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class TaskSpec:
    name: str
    commands: tuple[CommandSpec, ...]
    needs: tuple[str, ...] = ()
    after: tuple[str, ...] = ()
    reads: ExtractionScope = field(default_factory=ExtractionScope)
    optional: ExtractionScope = field(default_factory=ExtractionScope)
    uses: ExtractionScope = field(default_factory=ExtractionScope)
    #: Unity classes this task accepts from a name-filtered export.
    accepts_partial: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Page:
    name: str
    title: str
    roots: tuple[str, ...]
    #: Export outputs the page shows directly at browse time.
    serves: ExtractionScope = field(default_factory=ExtractionScope)


PAGES: dict[str, Page] = {
    page.name: page
    for page in (
        # Text only: no image, video or audio is extracted or built.
        Page("story", "Story and Text Tables", ("story",)),
        # The same pages with Story's images and videos (story_media.json).
        # Voice lines come from the Audio page's own publication.
        Page("story-media", "Story and Text Tables with images and video", ("story", "story_media")),
        Page("map", "Map", ("map_recovery_preview",)),
        Page("characters", "Characters", ("characters",)),
        Page("gameplay", "Gameplay", (
            "gameplay", "projectiles", "gameplay_skill_refs", "gameplay_asset_refs_after_graph", "combat_relationships",
        )),
        Page("production", "Production", ("production",)),
        Page("audio", "Audio", ("audio",)),
        Page("assets", "Assets", ("assets",)),
        Page("data", "Data", ("data_inspector",), serves=DATA_FILES),
    )
}
#: Text Tables are built by the Story builder.
PAGE_ALIASES = {"text": "story"}


@dataclass(frozen=True)
class BuildOptions:
    """Runtime choices the task commands depend on."""

    jobs: int = 4
    game_root: Path | None = None
    export_root: Path | None = None
    #: Decode CN audio from the installed game instead of reusing game/Audio.
    decode_audio: bool = False
    #: `build_assets --mode`; the debug build indexes every exported class.
    asset_mode: str = "default"
    full_source_graph: bool = False


def _environment(options: BuildOptions) -> tuple[tuple[str, str], ...]:
    values = {}
    if options.export_root:
        values["ENDFIELD_EXPORT_ROOT"] = str(options.export_root.resolve())
    if options.game_root:
        values["ENDFIELD_GAME_ROOT"] = str(options.game_root.resolve())
    return tuple(sorted(values.items()))


def build_tasks(options: BuildOptions) -> dict[str, TaskSpec]:
    """Every build task. Each edge names a file one task writes and the next reads."""
    environment = _environment(options)

    def module(name: str, *args: str) -> CommandSpec:
        return CommandSpec((sys.executable, "-m", name, *args), environment)

    def script(path: str, *args: str) -> CommandSpec:
        return CommandSpec((sys.executable, str(REPO_ROOT / path), *args), environment)

    jobs = str(options.jobs)
    of = ExtractionScope.of
    tasks: list[TaskSpec] = []

    # Production's catalog needs only tables; icons reuse already exported media.
    tasks.append(TaskSpec(
        "production",
        (module("scripts.webui.production.build_production", "--languages", "CN", "--default-language", "CN"),),
        reads=of(("table",)),
        uses=of(convert_types=("Texture2D", "Sprite")),
    ))

    # ---- Story and Text Tables ---------------------------------------------
    # The guide audits the object index for Story consumer evidence, the
    # evidence refresh rebuilds the intermediates under webui/data/_build/story,
    # and the builder publishes lang/CN (conv, mission, reference, actors).
    # Narrative video (cutscene and remote-comm file names) is bound when the
    # story-media mode or the Assets page has extracted it; a text-only export
    # skips those bindings.
    tasks.append(TaskSpec(
        "story",
        (
            module("scripts.webui.story.animestudio_story_guide"),
            module("scripts.webui.story.refresh_evidence"),
            module("scripts.webui.story.build", "--languages", "CN", "--default-language", "CN"),
        ),
        reads=STORY_TEXT,
        uses=of(("video", "audit-video")),
        # The setup path exports only the Story-named MonoBehaviours.
        accepts_partial=frozenset({"MonoBehaviour"}),
    ))

    # ---- Map ----------------------------------------------------------------
    # Reads lang/CN/{mission,conv,missions.json} from Story for markers.
    tasks.append(TaskSpec(
        "map_recovery",
        (module("scripts.webui.map.build_map_recovery_data", "--jobs", jobs),),
        after=("story", "data_inspector"),
        reads=of(("table", "json-data")),
        # Height grids feed the elevation underlay; Texture2D the minimap
        # chunks; Mesh the unplaced-model links.
        optional=of(("terrain-height",), convert_types=("Texture2D", "Mesh")),
    ))
    # Streams InitChunkData from the installed game and joins the exported
    # StreamingAssets asset map and Mesh; its scene list is map_recovery's
    # webui/data/map_recovery/maps.
    streaming_args = ["--all-published-map-scenes", "--jobs", jobs]
    if options.game_root:
        streaming_args += ["--game-root", str(options.game_root)]
    if options.export_root:
        layout = ExportLayout(options.export_root)
        streaming_args += [
            "--asset-map", str(layout.asset_map_dir("StreamingAssets") / "endfield_streamingassets_assets.json"),
            "--mesh-root", str(layout.unity_type_dir("Mesh")),
        ]
    tasks.append(TaskSpec(
        "map_streaming_instances",
        (module("scripts.webui.map.recover_map_streaming_instances", *streaming_args),),
        needs=("map_recovery",),
        optional=of(convert_types=("Mesh",)),
    ))
    # Reads the streaming sidecars, and the Assets page's published
    # webui/data/assets/index.json relations when present: the mesh ->
    # material -> base-colour texture chain that colours the render.
    tasks.append(TaskSpec(
        "map_recovery_preview",
        (module("scripts.webui.map.build_map_recovery_data", "--preview-only", "--jobs", jobs),),
        needs=("map_streaming_instances",),
        after=("assets",),
        optional=of(("json-data",), ("Material",), ("Texture2D", "Mesh")),
    ))

    # ---- Story media --------------------------------------------------------
    # Projects Story's inline images, CG, BigLogo and remote-comm images and its
    # videos onto the exported media: webui/data/assets/story_media.json, read
    # only by the Story page. It reads Story's published lang/CN for the ids.
    tasks.append(TaskSpec(
        "story_media",
        (module("scripts.webui.assets.build_assets", "--mode", options.asset_mode, "--publish", "story-media"),),
        after=("story",),
        optional=of(("video", "audit-video"), convert_types=("Texture2D", "Sprite")),
    ))

    # ---- Assets and Characters ----------------------------------------------
    # Indexes converted media plus Material relations; reads no other page.
    tasks.append(TaskSpec(
        "assets",
        (module("scripts.webui.assets.build_assets", "--mode", options.asset_mode, "--publish", "index"),),
        optional=of(
            ("table", "video", "audit-video"),
            ("Material",),
            ("Texture2D", "Sprite", "Mesh", "Animator"),
        ),
    ))
    # Resolves media through the published asset index (scanning game/Unity
    # when it is missing). Speaker discovery reads exported Tables directly.
    tasks.append(TaskSpec(
        "characters",
        (module("scripts.webui.characters.build_character_data", "--languages", "CN", "--default-language", "CN"),),
        after=("assets",),
        reads=of(("table",)),
        optional=of(("json-data",), convert_types=("Texture2D", "Sprite", "Mesh", "Animator")),
    ))

    # ---- Gameplay -----------------------------------------------------------
    # The tag registry resolves GameplayTagConfig through MonoScript and the
    # object index; wiki titles come from Story's lang/CN/index.json.
    tasks.append(TaskSpec(
        "gameplay",
        (module(
            "scripts.webui.gameplay.build_gameplay",
            "--stage", "base", "--stage", "audit", "--languages", "CN", "--default-language", "CN",
        ),),
        after=("story",),
        reads=of(("table",)),
        optional=of(("json-data",), ("MonoScript", *CARRIERS)),
    ))
    tasks.append(TaskSpec(
        "projectiles",
        (module("scripts.webui.gameplay.build_gameplay", "--stage", "projectiles"),),
        optional=of(json_types=CARRIERS),
    ))

    skill_ref_args = ["--stage", "skill-refs"]
    if options.export_root:
        skill_ref_args += ["--export-root", str(options.export_root)]
    if options.game_root:
        skill_ref_args += ["--game-root", str(options.game_root)]
    tasks.append(TaskSpec(
        "gameplay_skill_refs",
        (module("scripts.webui.gameplay.build_gameplay", *skill_ref_args),),
        needs=("gameplay", "projectiles"),
        after=("data_inspector",),
        optional=of(("json-data",), CARRIERS),
    ))

    def asset_refs(name: str, needs: tuple[str, ...]) -> TaskSpec:
        # Joins lang/CN/gameplay/index.json with the Assets page's published
        # webui/data/assets/index.json (skipped when there is none), adding
        # source-graph proof when the graph sqlite is current.
        return TaskSpec(
            name,
            (module("scripts.webui.gameplay.build_gameplay", "--stage", "asset-refs", "--default-language", "CN"),),
            needs=needs,
            after=("assets",),
        )

    tasks.append(asset_refs("gameplay_asset_refs", ("gameplay",)))
    graph_args = ["build", "--language", "CN"]
    if not options.full_source_graph:
        graph_args += ["--relevant-asset-maps", "--skip-reference-rows", "--skip-followups"]
    # Reads the gameplay index, the asset index (its content hash is kept in
    # the graph meta) and Story's lang/CN plus _build/story intermediates. It
    # also ingests the Audio page's outputs, which audio replaces atomically
    # and no Gameplay consumer reads back, so Audio is deliberately not an edge.
    # Combat treats the graph as stale when Story, gameplay or asset output is
    # newer, hence every producer is ordered first.
    tasks.append(TaskSpec(
        "source_graph",
        (script("tools/endfield_source_graph.py", *graph_args),),
        needs=("gameplay",),
        after=("assets", "story"),
        optional=of(("table", "json-data"), ("Material",)),
    ))
    # The same stage re-runs so the sidecar carries source-graph proof; it
    # rewrites the pre-graph run's file, so it must follow it.
    tasks.append(asset_refs("gameplay_asset_refs_after_graph", ("source_graph", "gameplay_asset_refs")))
    tasks.append(TaskSpec(
        "combat_relationships",
        (module("scripts.webui.gameplay.build_gameplay", "--stage", "combat", "--languages", "CN"),),
        needs=("source_graph",),
        optional=of(json_types=CARRIERS),
    ))

    # ---- Audio --------------------------------------------------------------
    # Reads Story's lang/CN/conv and publishes what it links to them -- line
    # voice files, event audio, dialog lifecycle hooks -- as its own
    # lang/CN/audio/conv sidecars, which the Story page merges. The gameplay
    # index, projectiles and the Map streaming sidecars
    # (webui/data/_build/map/world_placements) enrich its contexts when present.
    audio_args: list[str] = [] if options.decode_audio else ["--skip-decode"]
    if options.game_root:
        audio_args += ["--game-root", str(options.game_root)]
    if options.export_root:
        audio_args += ["--export-root", str(options.export_root)]
    tasks.append(TaskSpec(
        "audio",
        (module("scripts.webui.audio.build_audio", *audio_args),),
        after=("story", "gameplay", "projectiles", "map_streaming_instances"),
        reads=of(("table",)),
        optional=of(
            ("json-data",),
            (*CARRIERS, "AnimatorController", "AnimatorOverrideController"),
            ("AnimationClip",),
        ),
    ))

    # ---- Data ---------------------------------------------------------------
    tasks.append(TaskSpec(
        "data_inspector",
        (module("scripts.webui.data_inspector.build_data_inspector"),),
        optional=of(("json-data", "dynamic-streaming"), ("AnimatorController", "AnimatorOverrideController", "MonoBehaviour", "PlayableDirector")),
    ))

    by_name: dict[str, TaskSpec] = {}
    for task in tasks:
        if task.name in by_name:
            raise ValueError(f"duplicate build task {task.name}")
        by_name[task.name] = task
    for task in tasks:
        for dependency in (*task.needs, *task.after):
            if dependency not in by_name or dependency == task.name:
                raise ValueError(f"task {task.name} names an invalid dependency {dependency}")
    return by_name


def task_closure(tasks: dict[str, TaskSpec], roots: tuple[str, ...]) -> set[str]:
    """The roots and every task they transitively ``need``."""
    selected: set[str] = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name not in selected:
            selected.add(name)
            pending.extend(tasks[name].needs)
    return selected


def check_pages_independent(tasks: dict[str, TaskSpec]) -> None:
    """Refuse a registry in which building one page builds another.

    Two pages share build tasks only when one is a mode of the other, its roots
    containing all of the other's (story-media and story).
    """
    closures = {name: task_closure(tasks, page.roots) for name, page in PAGES.items()}
    for name, page in PAGES.items():
        for other_name, other in PAGES.items():
            if name >= other_name or set(page.roots) <= set(other.roots) or set(other.roots) <= set(page.roots):
                continue
            shared = closures[name] & closures[other_name]
            if shared:
                raise ValueError(f"pages {name} and {other_name} both build {', '.join(sorted(shared))}")


def resolve_pages(names: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Canonical page names in registry order; no names means every page."""
    if not names:
        return tuple(PAGES)
    selected: set[str] = set()
    for name in names:
        key = PAGE_ALIASES.get(name.lower(), name.lower())
        if key not in PAGES:
            known = ", ".join((*PAGES, *PAGE_ALIASES))
            raise ValueError(f"unknown page {name!r}; expected {known}")
        selected.add(key)
    return tuple(name for name in PAGES if name in selected)


@dataclass(frozen=True)
class BuildPlan:
    pages: tuple[str, ...]
    #: The selected tasks, each with `after` resolved to its edges in this plan.
    tasks: tuple[TaskSpec, ...]
    #: Union of every selected task's inputs and every selected page's served outputs.
    scope: ExtractionScope
    requirements: Requirements
    #: Tasks outside this build whose last publication a selected task reads.
    published: tuple[str, ...] = ()


def plan_build(pages: tuple[str, ...], options: BuildOptions) -> BuildPlan:
    tasks = build_tasks(options)
    check_pages_independent(tasks)
    selected = task_closure(tasks, tuple(root for page in pages for root in PAGES[page].roots))
    ordered = [task for name, task in tasks.items() if name in selected]
    resolved = tuple(
        replace(task, after=tuple(dict.fromkeys(
            (*task.needs, *(name for name in task.after if name in selected))
        )))
        for task in ordered
    )
    inputs = ExtractionScope()
    reads = ExtractionScope()
    used = ExtractionScope()
    for task in ordered:
        inputs = inputs | task.reads | task.optional
        reads = reads | task.reads
        used = used | task.uses
    served = ExtractionScope()
    for page in pages:
        served = served | PAGES[page].serves
    # What tasks use but nothing in this run extracts is taken as published.
    reused = frozenset({
        *(f"structured/{block}" for block in used.structured_blocks if block not in inputs.structured),
        *(f"unity/{name}" for name in used.json_types | used.convert_types
          if name not in inputs.json_types | inputs.convert_types),
    })
    checked = inputs | used

    def classes(scope: ExtractionScope) -> frozenset[str]:
        return scope.json_types | scope.convert_types

    # A name-filtered class is acceptable only when every task that reads it
    # accepts it, and no selected page shows it whole.
    partial_ok = frozenset(
        type_name
        for type_name in ("MonoBehaviour", "Texture2D")
        if type_name not in classes(served)
        and all(
            type_name in task.accepts_partial
            for task in ordered
            if type_name in classes(task.reads) | classes(task.optional) | classes(task.uses)
        )
    )
    # Served outputs are extracted but not checked: a page that shows files
    # reads nothing from them at build time.
    requirements = Requirements(
        structured=reads.structured_blocks,
        unity=(*reads.json_classes, *(name for name in reads.convert_classes if name not in reads.json_types)),
        optional_structured=checked.structured_blocks,
        optional_unity=(*checked.json_classes, *(name for name in checked.convert_classes if name not in checked.json_types)),
        optional_asset_map=checked.exports_unity,
        reused=reused,
        partial_ok=partial_ok,
    )
    scope = inputs | served
    published = tuple(sorted({name for task in ordered for name in task.after if name not in selected}))
    return BuildPlan(pages, resolved, scope, requirements, published)


def extraction_scope(plan: BuildPlan, *, everything: bool = False) -> ExtractionScope:
    """What a `--from-game` run exports for this plan; the debug export takes everything."""
    return EVERYTHING if everything else plan.scope
