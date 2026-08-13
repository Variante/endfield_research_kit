#!/usr/bin/env python3
"""Build split WebUI zips without the 3D asset browser payload.

The primary package keeps the story/gameplay/reference browser text data, code,
and emoji image files. A companion assets package contains the larger exported
image/video files that the story renderer can display, and a standalone audio
package contains lossless FLAC story audio files. OBJ/FBX files,
legacy local index folders, and the asset-browser data page are intentionally
left out.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import json
import os
import posixpath
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

from asset_builder import media_resolver
from common import (
    EXPORT_ROOT,
    ROOT as PROJECT_ROOT,
    normalize_posix,
)

WEBUI_ROOT = PROJECT_ROOT / "webui"
ZIP_NAME_PREFIX = "endfield-story-exported"
ASSETS_ZIP_NAME_PREFIX = "endfield-story-exported-assets"
AUDIO_ZIP_NAME_PREFIX = "endfield-story-exported-audio"

TEXT_EXTENSIONS = {
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".md",
    ".svg",
    ".txt",
    ".xml",
    ".yml",
    ".yaml",
}

PACK_AUDIO_FORMAT = "flac"

ASSET_VIEW_START_RE = re.compile(r'<section\s+id="assets-view"(?=[\s>])', re.IGNORECASE)
ASSET_TAB_RE = re.compile(r'(<button\s+id="assets-tab"(?=[\s>]))([^>]*>)', re.IGNORECASE)

ASSET_SHIM_JS = """(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const AVAILABLE_VIEWS = new Set(["story", "characters", "gameplay", "audio", "mission-pipeline", "reference", "updates"]);
  const HIDDEN_VIEWS = new Set(["assets"]);
  const DEBUG_ONLY_VIEWS = new Set(["mission-pipeline"]);
  const DEBUG_VIEW_FALLBACKS = Object.freeze({ audio: "gameplay", "mission-pipeline": "gameplay" });
  let activeView = "story";

  function resolveViewFromHash() {
    const hash = (window.location.hash || "").replace(/^#/, "").toLowerCase();
    return AVAILABLE_VIEWS.has(hash) ? hash : "story";
  }

  function updateHashForView(view) {
    const nextHash = AVAILABLE_VIEWS.has(view) ? `#${view}` : "#story";
    if (window.location.hash === nextHash) return;
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}${nextHash}`);
  }

  function debugViewsEnabled() {
    return document.body.classList.contains("show-debug");
  }

  function availableView(view) {
    const candidate = AVAILABLE_VIEWS.has(view) ? view : "story";
    if (!DEBUG_ONLY_VIEWS.has(candidate) || debugViewsEnabled()) return candidate;
    return DEBUG_VIEW_FALLBACKS[candidate] || "story";
  }

  function syncDebugViewVisibility() {
    const enabled = debugViewsEnabled();
    $$(".view-tab[data-debug-view]").forEach((button) => {
      button.hidden = !enabled;
    });
    if (!enabled && DEBUG_ONLY_VIEWS.has(activeView)) {
      setActiveView(DEBUG_VIEW_FALLBACKS[activeView] || "story");
    }
  }

  function setActiveView(view, { updateHash = true } = {}) {
    const requested = AVAILABLE_VIEWS.has(view) ? view : "story";
    const active = availableView(requested);
    activeView = active;
    document.body.dataset.activeView = active;

    $$(".view-tab").forEach((button) => {
      const selected = button.dataset.view === active;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
      if (selected) button.scrollIntoView({ block: "nearest", inline: "nearest" });
    });

    $$(".page-view").forEach((page) => {
      const selected = page.dataset.view === active;
      page.hidden = !selected;
      page.classList.toggle("is-active", selected);
    });

    if (updateHash || active !== requested) updateHashForView(active);
    window.dispatchEvent(new CustomEvent("webui:view-changed", { detail: { view: active } }));
    window.dispatchEvent(new Event("resize"));
  }

  $$(".view-tab").forEach((button) => {
    if (HIDDEN_VIEWS.has(button.dataset.view)) {
      button.hidden = true;
      button.setAttribute("aria-hidden", "true");
      button.tabIndex = -1;
      return;
    }
    button.addEventListener("click", () => setActiveView(button.dataset.view));
  });

  $("#view-tabs")?.addEventListener("keydown", (event) => {
    if (!event.target.matches(".view-tab") || event.target.hidden) return;
    const tabs = $$(".view-tab").filter((button) => !button.hidden && !HIDDEN_VIEWS.has(button.dataset.view));
    const currentIndex = tabs.indexOf(event.target);
    if (currentIndex < 0) return;
    let nextIndex = currentIndex;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % tabs.length;
    else if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = tabs.length - 1;
    else return;
    event.preventDefault();
    const nextTab = tabs[nextIndex];
    nextTab.focus();
    setActiveView(nextTab.dataset.view);
  });

  window.addEventListener("hashchange", () => setActiveView(resolveViewFromHash(), { updateHash: false }));
  window.addEventListener("webui:debug-changed", syncDebugViewVisibility);
  syncDebugViewVisibility();
  setActiveView(resolveViewFromHash(), { updateHash: false });
})();
"""
PACKAGE_README = """Endfield WebUI story package

Run from this extracted directory:

    python serve.py

Then open the printed localhost URL.

This package includes Story, Characters, Gameplay, Text, Updates, the
experimental Mission Pipeline, the debug-only Audio semantic index, WebUI code,
emoji images, and compact media indexes. Larger story images and videos are in
the companion assets zip. Decoded audio and raw audio indexes are in the
standalone audio zip.
Extract those zips into the same directory after this one when you want
inline/wiki media or playable audio too.

The 3D asset browser, legacy local index folders, OBJ/FBX payloads, and
Source model downloads are intentionally excluded.
"""

CHINESE_QUICKSTART_README = """Endfield WebUI 使用说明

1. 先解压主包 *-endfield-story-exported.zip。
2. 如果你还需要图片和视频，再把 *-endfield-story-exported-assets.zip 解压到同一个文件夹里；提示覆盖或合并时请选择允许。
3. 如果你还需要语音，再把 *-endfield-story-exported-audio.zip 也解压到同一个文件夹里；提示覆盖或合并时同样请选择允许。
4. 电脑需要安装 Python 3。
5. 在解压后的文件夹里打开命令行，运行：

   python serve.py

6. 命令行会显示一个本地网址，通常是：

   http://127.0.0.1:8765/

   用浏览器打开这个网址即可使用 WebUI。

如果 8765 端口被占用，可以改用：

   python serve.py 9000

然后打开命令行显示的新网址。

不要直接双击 webui/index.html；请用 serve.py 启动，否则部分数据、图片、视频或语音可能无法正常加载。
"""

ASSETS_PACKAGE_README = """Endfield WebUI story assets package

Extract this zip into the same directory as the matching story package, after
the story package has been extracted.

It contains larger exported image and video files used by inline/wiki media in
the WebUI, plus the full media indexes that enable them. Decoded story audio is
in the standalone audio package. Emoji images, WebUI code, and story/reference
text data are in the main story package.
"""

AUDIO_PACKAGE_README = """Endfield WebUI story audio package

Extract this zip into the same directory as the matching story package, after
the story package has been extracted.

It contains lossless FLAC audio files and raw audio indexes used by WebUI dialog,
cutscene, Gameplay, and debug Audio controls. Legacy WAV/WEM files are
intentionally not included. Larger image/video media is in the companion assets
package. Emoji images, WebUI code, and story/reference text data are in the main
story package.
"""


@dataclass(frozen=True)
class ExportedImage:
    rel: str
    source_path: Path
    archive_path: str


@dataclass
class PackagePlan:
    filtered_asset_payload: dict
    filtered_video_payload: dict
    exported_images: list[ExportedImage]
    exported_videos: list[ExportedImage]
    audio_files: list[ExportedImage]
    audio_indexes: list[ExportedImage]
    image_refs: int
    video_refs: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create split WebUI zips: a story/code/emoji zip and a "
            "companion larger-media assets zip plus a standalone audio zip."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Primary story zip path to write. Default: "
            f"YYYYMMDD-{ZIP_NAME_PREFIX}.zip, where YYYYMMDD is today's local date."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the package plan without writing zips.",
    )
    parser.add_argument(
        "--skip-audio",
        action="store_true",
        help="Do not scan or write the standalone audio zip.",
    )
    return parser.parse_args(argv)


def default_output_path(project_root: Path) -> Path:
    datestamp = datetime.now().strftime("%Y%m%d")
    return project_root / f"{datestamp}-{ZIP_NAME_PREFIX}.zip"


def default_assets_output_path(project_root: Path) -> Path:
    datestamp = datetime.now().strftime("%Y%m%d")
    return project_root / f"{datestamp}-{ASSETS_ZIP_NAME_PREFIX}.zip"


def default_audio_output_path(project_root: Path) -> Path:
    datestamp = datetime.now().strftime("%Y%m%d")
    return project_root / f"{datestamp}-{AUDIO_ZIP_NAME_PREFIX}.zip"


def companion_assets_output_path(output: Path, project_root: Path) -> Path:
    if output == default_output_path(project_root):
        return default_assets_output_path(project_root)
    if output.suffix.lower() == ".zip":
        return output.with_name(f"{output.stem}-assets{output.suffix}")
    return output.with_name(f"{output.name}-assets.zip")


def companion_audio_output_path(output: Path, project_root: Path) -> Path:
    if output == default_output_path(project_root):
        return default_audio_output_path(project_root)
    if output.suffix.lower() == ".zip":
        return output.with_name(f"{output.stem}-audio{output.suffix}")
    return output.with_name(f"{output.name}-audio.zip")


def posix_to_path(value: str) -> Path:
    parts = [part for part in PurePosixPath(value).parts if part not in ("", ".")]
    return Path(*parts) if parts else Path()


def archive_name(path: str | Path) -> str:
    return normalize_posix(str(path))


def iter_webui_text_files(webui_root: Path) -> Iterable[Path]:
    for path in sorted(webui_root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(webui_root).as_posix()
        if rel.startswith("data/audio/"):
            continue
        if rel.startswith("data/game_data/"):
            continue
        if rel.startswith("data/decoded/"):
            continue
        if re.match(r"^data/lang/[^/]+/progression(?:/|$)", rel):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def iter_exported_audio_files(export_root: Path) -> Iterable[Path]:
    audio_root = export_root / "structured" / "Audio"
    if not audio_root.exists():
        return
    for path in sorted(audio_root.rglob("*")):
        if path.is_file() and path.suffix.lower() == f".{PACK_AUDIO_FORMAT}":
            yield path


def iter_exported_audio_indexes(export_root: Path) -> Iterable[Path]:
    audio_root = export_root / "structured" / "Audio"
    if not audio_root.exists():
        return
    for path in sorted(audio_root.rglob("index.json")):
        if path.is_file():
            yield path


def exported_file(export_root: Path, path: Path) -> ExportedImage:
    rel = normalize_posix(path.relative_to(export_root))
    return ExportedImage(
        rel=rel,
        source_path=path,
        archive_path=archive_name(Path(export_root.name) / path.relative_to(export_root)),
    )


def load_asset_index(asset_index_path: Path) -> dict:
    if not asset_index_path.exists():
        return {"generated": None, "root": "export_full", "sourceRoots": {}, "entries": []}
    with asset_index_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_required_asset_index(asset_index_path: Path) -> dict:
    if not asset_index_path.exists():
        raise SystemExit(f"Required asset index not found: {asset_index_path}")
    return load_asset_index(asset_index_path)


def filtered_asset_index(payload: dict, selected_entries: list[dict], *, kind: str = "image") -> dict:
    selected_entries = sorted(selected_entries, key=lambda entry: str(entry.get("r") or ""))
    source_roots = payload.get("sourceRoots") if isinstance(payload.get("sourceRoots"), dict) else {}
    used_sources = {normalize_posix(str(entry.get("r") or "")).split("/")[0] for entry in selected_entries}
    counts = {
        "total": len(selected_entries),
        kind: len(selected_entries),
    }
    if kind == "image":
        counts["model"] = 0
    return {
        "generated": payload.get("generated"),
        "root": payload.get("root") or "export_full",
        "sourceRoots": {
            source: source_roots[source]
            for source in sorted(used_sources)
            if source and source in source_roots
        },
        "counts": counts,
        "entries": selected_entries,
        "relations": {},
    }


def resolve_exported_image(project_root: Path, export_root: Path, asset_payload: dict, rel: str) -> ExportedImage:
    normalized_rel = normalize_posix(rel)
    source, *rest = normalized_rel.split("/")
    rel_within_source = "/".join(rest)

    root_name = normalize_posix(str(asset_payload.get("root") or export_root.name or "export_full"))
    source_roots = asset_payload.get("sourceRoots") if isinstance(asset_payload.get("sourceRoots"), dict) else {}
    source_root = normalize_posix(str(source_roots.get(source) or ""))

    if source_root:
        source_path = Path(source_root)
        if not source_path.is_absolute():
            source_path = project_root / posix_to_path(source_root)

        archive_root = source_root
        if root_name and archive_root.startswith(f"{root_name}/"):
            archive_root = archive_root[len(root_name) + 1 :]
        elif archive_root == root_name:
            archive_root = ""
        exported_rel = posixpath.join(archive_root, rel_within_source) if archive_root else rel_within_source
        source_path = source_path / posix_to_path(rel_within_source)
    else:
        exported_rel = normalized_rel
        source_path = export_root / posix_to_path(normalized_rel)

    archive_path = archive_name(posixpath.join(export_root.name, exported_rel))
    return ExportedImage(rel=normalized_rel, source_path=source_path, archive_path=archive_path)


def strip_asset_view_from_index(index_html: str) -> str:
    lines = index_html.splitlines(keepends=True)
    output: list[str] = []
    skipping = False
    section_depth = 0

    for line in lines:
        if not skipping and ASSET_VIEW_START_RE.search(line):
            skipping = True
            section_depth = line.lower().count("<section") - line.lower().count("</section>")
            continue

        if skipping:
            section_depth += line.lower().count("<section")
            section_depth -= line.lower().count("</section>")
            if section_depth <= 0:
                skipping = False
            continue

        output.append(line)

    html_text = "".join(output)

    def hide_asset_tab(match: re.Match[str]) -> str:
        prefix, suffix = match.groups()
        attrs = suffix
        if " hidden" not in attrs:
            attrs = attrs[:-1] + ' hidden aria-hidden="true" tabindex="-1">'
        return prefix + attrs

    return ASSET_TAB_RE.sub(hide_asset_tab, html_text, count=1)


def zip_writestr(zipf: zipfile.ZipFile, written: set[str], arcname: str, data: str | bytes) -> None:
    normalized = archive_name(arcname)
    if normalized in written:
        return
    if isinstance(data, str):
        data = data.encode("utf-8")
    zipf.writestr(normalized, data)
    written.add(normalized)


def zip_write_file(zipf: zipfile.ZipFile, written: set[str], source: Path, arcname: str) -> bool:
    normalized = archive_name(arcname)
    if normalized in written:
        return False
    zipf.write(source, normalized)
    written.add(normalized)
    return True


def webui_arcname(webui_root: Path, path: Path) -> str:
    return archive_name(Path("webui") / path.relative_to(webui_root))


def plan_package(
    *,
    include_audio: bool = True,
) -> PackagePlan:
    webui_root = WEBUI_ROOT.resolve()
    project_root = PROJECT_ROOT.resolve()
    export_root = EXPORT_ROOT.resolve()

    story_media_payload = load_required_asset_index(webui_root / "data" / "assets" / "story_media.json")
    story_entries = [
        dict(entry)
        for entry in (story_media_payload.get("entries") or [])
        if isinstance(entry, dict) and entry.get("r")
    ]
    selected_images = [entry for entry in story_entries if entry.get("k") == "image"]
    selected_videos = [entry for entry in story_entries if entry.get("k") == "video"]

    filtered_payload = filtered_asset_index(story_media_payload, selected_images, kind="image")
    filtered_video_payload = filtered_asset_index(story_media_payload, selected_videos, kind="video")

    exported_images = [
        resolve_exported_image(project_root, export_root, filtered_payload, rel)
        for rel in sorted(str(entry.get("r") or "") for entry in selected_images)
    ]
    exported_videos = [
        resolve_exported_image(project_root, export_root, filtered_video_payload, rel)
        for rel in sorted(str(entry.get("r") or "") for entry in selected_videos)
    ]
    audio_files = (
        [
            exported_file(export_root, path)
            for path in iter_exported_audio_files(export_root)
        ]
        if include_audio
        else []
    )
    audio_indexes = (
        [exported_file(export_root, path) for path in iter_exported_audio_indexes(export_root)]
        if include_audio
        else []
    )
    counts = story_media_payload.get("counts") if isinstance(story_media_payload.get("counts"), dict) else {}

    return PackagePlan(
        filtered_asset_payload=filtered_payload,
        filtered_video_payload=filtered_video_payload,
        exported_images=exported_images,
        exported_videos=exported_videos,
        audio_files=audio_files,
        audio_indexes=audio_indexes,
        image_refs=int(counts.get("imageIds") or len(selected_images)),
        video_refs=int(counts.get("videoRefs") or len(selected_videos)),
    )


def create_package(args: argparse.Namespace) -> int:
    webui_root = WEBUI_ROOT.resolve()
    project_root = PROJECT_ROOT.resolve()
    export_root = EXPORT_ROOT.resolve()
    output = (args.output or default_output_path(project_root)).resolve()
    assets_output = companion_assets_output_path(output, project_root).resolve()
    audio_output = companion_audio_output_path(output, project_root).resolve() if not args.skip_audio else None

    if not webui_root.exists():
        raise SystemExit(f"WebUI root not found: {webui_root}")
    if not (project_root / "serve.py").exists():
        raise SystemExit(f"serve.py not found under project root: {project_root}")
    package_outputs = {
        "primary story zip": output,
        "companion assets zip": assets_output,
    }
    if audio_output is not None:
        package_outputs["standalone audio zip"] = audio_output
    if len(set(package_outputs.values())) != len(package_outputs):
        raise SystemExit("Package output paths must be different.")

    plan = plan_package(include_audio=audio_output is not None)
    missing_images = [image for image in plan.exported_images if not image.source_path.exists()]
    existing_images = [image for image in plan.exported_images if image.source_path.exists()]
    missing_videos = [video for video in plan.exported_videos if not video.source_path.exists()]
    existing_videos = [video for video in plan.exported_videos if video.source_path.exists()]
    emoji_images = [image for image in existing_images if media_resolver.is_story_emoji_asset(image.rel)]
    asset_images = [image for image in existing_images if not media_resolver.is_story_emoji_asset(image.rel)]

    text_files = list(iter_webui_text_files(webui_root))
    copied_text_files = [
        path for path in text_files
        if path.relative_to(webui_root).as_posix() not in {
            "data/assets/index.json",
            "assets.js",
            "index.html",
        }
    ]

    print(f"WebUI root: {webui_root}")
    print(f"Export root: {export_root}")
    print(f"Story zip: {output}")
    print(f"Assets zip: {assets_output}")
    print(f"Audio zip: {audio_output if audio_output is not None else 'skipped'}")
    if audio_output is not None:
        print(f"Audio format: {PACK_AUDIO_FORMAT}")
    generated_text_count = 6
    print(f"Text files: {len(copied_text_files) + generated_text_count:,}")
    print(f"Story image IDs: {plan.image_refs:,}")
    print(f"Resolved image files: {len(existing_images):,} ({len(emoji_images):,} emoji, {len(asset_images):,} asset)")
    print(f"Wiki video refs: {plan.video_refs:,}")
    print(f"Resolved video files: {len(existing_videos):,}")
    if audio_output is not None:
        print(f"Decoded audio files: {len(plan.audio_files):,}")
    if missing_images:
        preview = ", ".join(image.rel for image in missing_images[:10])
        suffix = "..." if len(missing_images) > 10 else ""
        print(f"Missing exported image files: {len(missing_images):,} ({preview}{suffix})")
    if missing_videos:
        preview = ", ".join(video.rel for video in missing_videos[:10])
        suffix = "..." if len(missing_videos) > 10 else ""
        print(f"Missing exported video files: {len(missing_videos):,} ({preview}{suffix})")
    print("3D/model payloads: excluded")

    if args.dry_run:
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    assets_output.parent.mkdir(parents=True, exist_ok=True)
    if audio_output is not None:
        audio_output.parent.mkdir(parents=True, exist_ok=True)
    package_paths = [output, assets_output]
    if audio_output is not None:
        package_paths.append(audio_output)

    with staged_package_outputs(package_paths) as staged:
        _write_packages(
            staged[output],
            staged[assets_output],
            staged.get(audio_output),
            project_root=project_root,
            webui_root=webui_root,
            plan=plan,
            copied_text_files=copied_text_files,
            emoji_images=emoji_images,
            asset_images=asset_images,
            existing_videos=existing_videos,
        )

    size_mb = output.stat().st_size / (1024 * 1024)
    assets_size_mb = assets_output.stat().st_size / (1024 * 1024)
    print(f"Wrote story zip: {output} ({size_mb:.1f} MiB)")
    print(f"Wrote assets zip: {assets_output} ({assets_size_mb:.1f} MiB)")
    if audio_output is not None:
        audio_size_mb = audio_output.stat().st_size / (1024 * 1024)
        print(f"Wrote audio zip: {audio_output} ({audio_size_mb:.1f} MiB)")
    return 0


@contextmanager
def staged_package_outputs(outputs: list[Path]):
    """Keep published packages intact until every replacement is complete."""
    staged: dict[Path, Path] = {}
    try:
        for output in outputs:
            output.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temp_name = tempfile.mkstemp(
                dir=output.parent,
                prefix=f".{output.name}.",
                suffix=".tmp",
            )
            os.close(descriptor)
            staged[output] = Path(temp_name)
        yield staged
        for output, temp_path in staged.items():
            temp_path.replace(output)
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)


def _write_packages(
    output: Path,
    assets_output: Path,
    audio_output: Path | None,
    *,
    project_root: Path,
    webui_root: Path,
    plan: PackagePlan,
    copied_text_files: list[Path],
    emoji_images: list[ExportedImage],
    asset_images: list[ExportedImage],
    existing_videos: list[ExportedImage],
) -> None:
    written: set[str] = set()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        zip_write_file(zipf, written, project_root / "serve.py", "serve.py")
        zip_writestr(zipf, written, "README.txt", CHINESE_QUICKSTART_README)
        zip_writestr(zipf, written, "README-webui-package.txt", PACKAGE_README)

        for path in copied_text_files:
            zip_write_file(zipf, written, path, webui_arcname(webui_root, path))

        emoji_asset_entries = [
            entry
            for entry in (plan.filtered_asset_payload.get("entries") or [])
            if isinstance(entry, dict) and media_resolver.is_story_emoji_asset(str(entry.get("r") or ""))
        ]
        story_asset_payload = filtered_asset_index(plan.filtered_asset_payload, emoji_asset_entries, kind="image")

        asset_index_json = json.dumps(story_asset_payload, ensure_ascii=False, separators=(",", ":"))
        zip_writestr(zipf, written, "webui/data/assets/index.json", asset_index_json)

        index_html = (webui_root / "index.html").read_text(encoding="utf-8")
        zip_writestr(zipf, written, "webui/index.html", strip_asset_view_from_index(index_html))
        zip_writestr(zipf, written, "webui/assets.js", ASSET_SHIM_JS)

        for image in emoji_images:
            zip_write_file(zipf, written, image.source_path, image.archive_path)

    assets_written: set[str] = set()
    with zipfile.ZipFile(assets_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        zip_writestr(zipf, assets_written, "README.txt", CHINESE_QUICKSTART_README)
        zip_writestr(zipf, assets_written, "README-webui-assets-package.txt", ASSETS_PACKAGE_README)
        asset_index_json = json.dumps(plan.filtered_asset_payload, ensure_ascii=False, separators=(",", ":"))
        zip_writestr(zipf, assets_written, "webui/data/assets/index.json", asset_index_json)
        for image in asset_images:
            zip_write_file(zipf, assets_written, image.source_path, image.archive_path)
        for video in existing_videos:
            zip_write_file(zipf, assets_written, video.source_path, video.archive_path)

    if audio_output is not None:
        audio_written: set[str] = set()
        with zipfile.ZipFile(audio_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            zip_writestr(zipf, audio_written, "README.txt", CHINESE_QUICKSTART_README)
            zip_writestr(zipf, audio_written, "README-webui-audio-package.txt", AUDIO_PACKAGE_README)
            for audio_path in plan.audio_files:
                zip_write_file(zipf, audio_written, audio_path.source_path, audio_path.archive_path)
            for audio_index in plan.audio_indexes:
                zip_write_file(zipf, audio_written, audio_index.source_path, audio_index.archive_path)



def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return create_package(args)


if __name__ == "__main__":
    sys.exit(main())
