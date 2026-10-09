"""Render the maintained export workflow SVG from the page/task registry."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

from scripts.game_data.extraction.scope import EVERYTHING, RAW_BLOCKS, ExtractionScope
from scripts.repo_paths import REPO_ROOT
from scripts.webui.build_graph import dependency_depths
from scripts.webui.pages import BuildOptions, PAGES, plan_build


def render() -> str:
    options = BuildOptions(decode_audio=True)
    plan = plan_build(tuple(PAGES), options)
    # Whole Terrain suppresses the height-only step in the normalized command.
    if plan.scope.exporter_args() != EVERYTHING.exporter_args():
        raise ValueError("all-page extraction no longer covers EVERYTHING; review the diagram")
    scopes = {}
    for name in PAGES:
        selected = plan_build((name,), options)
        categories = {key: ExtractionScope() for key in ("R", "O", "U")}
        for task in selected.tasks:
            for key, attr in (("R", "reads"), ("O", "optional"), ("U", "uses")):
                categories[key] = categories[key] | getattr(task, attr)
        scopes[name] = {**categories, "F": PAGES[name].serves}

    rows = [
        ("Table", "structured", {"table"}),
        ("JsonData", "structured", {"json-data"}),
        ("Video / AuditVideo", "structured", {"video", "audit-video"}),
        ("Terrain: height grids / whole", "structured", {"terrain-height", "terrain"}),
        ("Lua", "structured", {"lua"}),
        ("Raw payload families", "structured", set(RAW_BLOCKS)),
        ("TextAsset JSON", "json_types", {"TextAsset"}),
        ("MonoBehaviour / PlayableDirector", "json_types", {"MonoBehaviour", "PlayableDirector"}),
        ("Material JSON", "json_types", {"Material"}),
        ("Controllers and other JSON", "json_types", set(EVERYTHING.json_types) - {
            "TextAsset", "MonoBehaviour", "PlayableDirector", "Material"}),
        ("Texture2D images", "convert_types", {"Texture2D"}),
        ("Sprite crops", "convert_types", {"Sprite"}),
        ("Mesh / Animator FBX", "convert_types", {"Mesh", "Animator"}),
        ("AnimationClip documents", "convert_types", {"AnimationClip"}),
        ("Shader / Font / TextAsset Convert", "convert_types", {"Shader", "Font", "TextAsset"}),
    ]
    # Refuse a silent omission when the supported vocabulary grows.
    for attr in ("structured", "json_types", "convert_types"):
        covered = set().union(*(members for _, kind, members in rows if kind == attr))
        missing = set(getattr(EVERYTHING, attr)) - covered
        if missing:
            raise ValueError(f"diagram omits {attr}: {sorted(missing)}")

    elements = []

    def text(x, y, value, *, size=16, fill="#334155", weight=400, anchor="start"):
        elements.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
                        f'font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')

    def box(x, y, w, h, fill="#fff", stroke="#e2e8f0", radius=12):
        elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
                        f'fill="{fill}" stroke="{stroke}"/>')

    def line(x1, y1, x2, y2, *, arrow=False):
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        elements.append(f'<path d="M{x1} {y1}H{x2}" stroke="#94a3b8" fill="none"{marker}/>'
                        if y1 == y2 else f'<path d="M{x1} {y1}L{x2} {y2}" stroke="#e2e8f0"/>')

    text(44, 56, "From installed Endfield data to the WebUI", size=30, weight=700, fill="#0f172a")
    text(44, 87, "export.bat selects page inputs; AnimeStudio extracts them; independent builders publish each page.")
    box(44, 113, 1272, 142, "#f8fafc")
    for y, command, description in (
        (147, "export.bat", "Rebuild every page from the existing export."),
        (188, "export.bat --from-game", "Extract every supported family, then rebuild every page."),
        (229, "export.bat PAGE --from-game --show-plan", "Inspect scope, freshness requirements and tasks without running them."),
    ):
        text(65, y, command, size=17, fill="#9a3412", weight=600)
        text(637, y, description, size=16)

    steps = (
        ("1  Index and select", "VFS indexes for both installed layers", "Newest overlay wins; resolve page scope"),
        ("2  Extract selected inputs", "Structured data, exact Unity documents", "Media and raw payloads in their stores"),
        ("3  Check and build", "Verify current builder inputs", "Run ready tasks within the job limit"),
        ("4  Publish the WebUI", "Each builder owns its page outputs", "Record timings and memory reports"),
    )
    for i, (title, first, second) in enumerate(steps):
        x = 44 + i * 326
        box(x, 290, 294, 94, "#fff7ed" if i < 2 else "#f0fdfa")
        text(x + 14, 316, title, size=18, weight=600, fill="#0f172a")
        text(x + 14, 341, first, size=14)
        text(x + 14, 364, second, size=14)
        if i < 3:
            line(x + 299, 337, x + 320, 337, arrow=True)
    text(44, 410, "Plain export.bat starts at step 3. --changed-only syncs installed data, then builds every page and Updates.", size=15)

    text(44, 455, "What each page selects", size=24, weight=700, fill="#0f172a")
    text(44, 480, "Grouped cells show any matching input. Hover a cell for exact class/block names.", size=15)
    box(44, 499, 1272, 534)
    labels = {"story": "Story", "story-media": "Story media", "map": "Map", "characters": "Characters",
              "gameplay": "Gameplay", "production": "Production", "audio": "Audio", "assets": "Assets", "data": "Data"}
    for i, name in enumerate(PAGES):
        text(382 + i * 109, 528, labels[name], size=13, weight=600, anchor="middle")
    colors = {"R": "#0f766e", "O": "#b45309", "U": "#64748b", "F": "#0369a1"}
    for row, (label, attr, members) in enumerate(rows):
        y = 543 + row * 30
        if row % 2 == 0:
            box(45, y, 1270, 30, "#f8fafc", "none", 0)
        text(62, y + 21, label, size=14)
        for column, name in enumerate(PAGES):
            hits = {key: sorted(getattr(scope, attr) & members) for key, scope in scopes[name].items()}
            keys = [key for key, values in hits.items() if values]
            x = 382 + column * 109
            if keys:
                details = "; ".join(f"{key}: {', '.join(hits[key])}" for key in keys)
                elements.append(f'<g><title>{escape(name + " — " + details)}</title>')
                text(x, y + 21, " · ".join(keys), size=14, fill=colors[keys[0]], weight=700, anchor="middle")
                elements.append("</g>")
            else:
                text(x, y + 21, "—", size=13, fill="#cbd5e1", anchor="middle")
    text(62, 1018, "VFS metadata is always indexed during extraction; carrier JSON runs also publish the object index.", size=14)
    for x, key, label in ((44, "R", "Required builder input"), (370, "O", "Optional builder input"),
                          (696, "U", "Reused export input"), (1022, "F", "Files served by Data")):
        text(x, 1061, key, fill=colors[key], weight=700)
        text(x + 24, 1061, label, size=15)
    text(44, 1089, "R / O / F enter the --from-game scope. U is extracted only when another selected page owns it.", size=15)
    text(44, 1114, "production builds the catalog shown inside Gameplay. Story media adds images/video; Audio publishes voice sidecars.", size=15)

    text(44, 1161, "All-page build order", size=24, weight=700, fill="#0f172a")
    text(44, 1186, "Earliest dependency depth; tasks start as their inputs succeed (default: 4 concurrent builders).", size=15)
    depths = dependency_depths(plan.tasks)
    max_depth = max(depths.values())
    width = (1272 - max_depth * 20) / (max_depth + 1)
    panel_height = 61 + max(list(depths.values()).count(d) for d in range(max_depth + 1)) * 31
    for depth in range(max_depth + 1):
        x = 44 + depth * (width + 20)
        box(x, 1208, width, panel_height, "#f8fafc")
        text(x + 16, 1238, f"Depth {depth}", size=18, weight=600, fill="#0f766e")
        names = [task.name for task in plan.tasks if depths[task.name] == depth]
        for i, name in enumerate(names):
            text(x + 16, 1273 + i * 31, name, size=13)
    end = 1208 + panel_height
    text(44, end + 36, "A standalone page builds its own tasks and reads other pages' last publications.", size=16, weight=600)
    graph_y = end + 72
    text(44, graph_y, "Which pages read another page's output", size=24, weight=700, fill="#0f172a")
    text(44, graph_y + 26, "Arrows point from the publisher to the reader. Each page writes only its own publication.", size=15)
    links = (
        ("Story + Text", "Map / Audio / Gameplay", "Mission markers, conversations, Wiki titles and source graph", "Build-time read"),
        ("Assets", "Characters / Map / Gameplay", "Media paths, material colours and asset references", "Build-time read"),
        ("Map + Gameplay", "Audio", "World placements, gameplay index and projectile references", "Build-time read"),
        ("Audio", "Story + Text", "Voice and event sidecars: lang/<LANG>/audio/conv/", "Browser read"),
        ("Story + Text", "Characters", "Appearance navigation after exact source, speaker and text checks", "Browser read"),
        ("Data", "Map / Gameplay", "Last published encounter and skill datasets", "Optional build-time read"),
        ("Production + Gameplay", "Gameplay browser", "Combined Items, Recipes and Machines; independent publications", "Browser read"),
    )
    for i, (publisher, reader, information, kind) in enumerate(links):
        y = graph_y + 50 + i * 82
        box(44, y, 260, 58, "#f8fafc")
        box(474, y, 290, 58, "#f0fdfa" if kind == "Browser read" else "#f8fafc")
        text(174, y + 34, publisher, size=16, weight=600, anchor="middle")
        text(619, y + 34, reader, size=16, weight=600, anchor="middle")
        line(310, y + 37, 465, y + 37, arrow=True)
        text(387, y + 17, kind, size=11, anchor="middle")
        text(788, y + 24, information, size=13)
    text(44, graph_y + 642, "Missing optional publications reduce detail; they never cause a page to rebuild another page.", size=15)

    notes_y = graph_y + 672
    box(44, notes_y, 1272, 172, "#fff7ed", "#fed7aa")
    text(63, notes_y + 29, "What “everything” means here", size=20, weight=600, fill="#9a3412")
    for i, note in enumerate((
        "All pages equal the supported full extraction scope. Debug adds broader asset indexing and Sprite image checks.",
        "Decoded blocks → game/; packed small files → GameFiles.sqlite; exact Unity documents → Unity.sqlite; raw families → raw/.",
        "Raw payloads and excluded Unity objects retain their evidence boundary; extraction does not recover every runtime meaning.",
        "The wrapper publishes CN and decodes CN audio. Changed-only compares complete exports with the last successful sync.",
    )):
        text(63, notes_y + 59 + i * 25, note, size=15)
    height = notes_y + 217
    text(44, height - 16, "Generated from scripts/webui/pages.py and extraction/scope.py · python -m scripts.webui.export_diagram", size=13, fill="#64748b")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="{height}" viewBox="0 0 1360 {height}" '
            'role="img" aria-labelledby="title desc">\n'
            '<title id="title">Endfield export and WebUI build workflow</title>\n'
            '<desc id="desc">Commands, page extraction scopes, build dependencies and the boundary of full supported coverage.</desc>\n'
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>\n'
            f'<rect width="1360" height="{height}" fill="#fff"/>\n'
            '<g font-family="Segoe UI, Arial, sans-serif">\n' + "\n".join(elements) + '\n</g>\n</svg>\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "res/export_pages.svg")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(), encoding="utf-8", newline="\n")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
