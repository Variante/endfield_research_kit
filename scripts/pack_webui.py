#!/usr/bin/env python3
"""Build the WebUI code package and three complementary media packages.

The primary package contains static code and generated text. The media package
contains referenced images and videos, while the audio package contains FLAC
files referenced by normal content pages. The resources package contains every
file listed by the Assets page, including JSON, OBJ, and FBX files, plus the
remaining audio inventory and raw Audio/Assets browser indexes.
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

if __package__:
    from .common import (
        EXPORT_ROOT,
        ROOT as PROJECT_ROOT,
        normalize_posix,
    )
else:
    from common import (
        EXPORT_ROOT,
        ROOT as PROJECT_ROOT,
        normalize_posix,
    )

WEBUI_ROOT = PROJECT_ROOT / "webui"
ZIP_NAME_PREFIX = "endfield-story-exported"
MEDIA_ZIP_NAME_PREFIX = "endfield-story-exported-media"
AUDIO_ZIP_NAME_PREFIX = "endfield-story-exported-audio"
RESOURCES_ZIP_NAME_PREFIX = "endfield-story-exported-resources"

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
PACKAGE_NAMES = ("story", "media", "audio", "resource")
MEDIA_ASSET_KINDS = {"image", "video"}
ALREADY_COMPRESSED_EXTENSIONS = {
    ".flac", ".gif", ".jpeg", ".jpg", ".m4a", ".mov", ".mp3",
    ".mp4", ".ogg", ".png", ".webm", ".webp",
}

COMPANION_FEATURE_PREFIXES = (
    "data/gameplay/",
    "data/map_recovery/",
    "src/features/characters/",
    "src/features/gameplay/",
    "src/features/map_recovery/",
)
COMPANION_FEATURE_FILES = {
    "data/assets/gameplay_refs.json",
}
COMPANION_LANGUAGE_FEATURE_RE = re.compile(r"^data/lang/[^/]+/(?:characters|gameplay)(?:/|$)")

PAGE_REFERENCE_PREFIXES = ("data/gameplay/", "data/map_recovery/")
PAGE_REFERENCE_FILES = {"data/assets/gameplay_refs.json", "data/assets/story_media.json"}
PAGE_REFERENCE_LANGUAGE_RE = re.compile(
    r"^data/lang/[^/]+/(?:conv|mission|characters|gameplay)(?:/|$)"
)
RESOURCE_DATA_PREFIXES = ("data/audio/", "data/game_data/", "data/decoded/")
RESOURCE_DATA_LANGUAGE_RE = re.compile(r"^data/lang/[^/]+/progression(?:/|$)")

ASSET_VIEW_START_RE = re.compile(r'<section\s+id="assets-view"(?=[\s>])', re.IGNORECASE)
ASSET_TAB_RE = re.compile(r'(<button\s+id="assets-tab"(?=[\s>]))([^>]*>)', re.IGNORECASE)

ASSET_SHIM_JS = """(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const AVAILABLE_VIEWS = new Set(["story", "map-recovery", "characters", "gameplay", "audio", "reference", "updates"]);
  const HIDDEN_VIEWS = new Set(["assets"]);
  const DEBUG_ONLY_VIEWS = new Set();
  const DEBUG_VIEW_FALLBACKS = Object.freeze({ audio: "gameplay" });
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

This package includes Story, Text, and Updates,
the debug-only Audio semantic index, shared WebUI code, emoji images, and
compact media indexes. Map, Characters, Gameplay, and larger exported images
and videos are in the companion assets zip. Decoded audio and raw audio indexes
are in the standalone audio zip.
Extract those zips into the same directory after this one when you want
inline/wiki media or playable audio too.

The complete Assets browser, including JSON, OBJ, FBX, and model downloads, is
provided by the optional resources package.
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

It contains the Map, Characters, and Gameplay pages and their generated data,
plus exported image and video files and the full image/video indexes that
enable them. Decoded story audio is in the standalone audio package. Emoji
images, shared WebUI code, and Story/reference text data are in the main Story
package.
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

CODE_PACKAGE_README = """Endfield WebUI code and text package

Run from this extracted directory with `python serve.py`, then open the printed
localhost URL. Extract the matching media and audio zips into the same directory
for Story, Text, Map, Characters, and Gameplay media. Extract the optional
resources zip last when you need the complete Audio and Assets resource browsers.
The resources zip includes every file listed by the Assets page, including
JSON, OBJ, and FBX payloads.
"""

MEDIA_PACKAGE_README = """Endfield WebUI page media package

Extract this zip into the same directory as the matching main package. It
contains only images and videos referenced by Story, Text, Map, Characters, and
Gameplay, plus the compact matching asset index. Referenced FLAC files are in
the matching audio package.
"""

AUDIO_PAGE_PACKAGE_README = """Endfield WebUI referenced page audio package

Extract this zip into the same directory as the matching main and media
packages. It contains only FLAC files referenced by Story, Text, Map,
Characters, and Gameplay. The remaining FLAC inventory and raw Audio indexes
are in the optional resources package.
"""

RESOURCES_PACKAGE_README = """Endfield WebUI optional resources package

Extract this zip last, into the same directory as the matching main and media
packages. It contains every file listed by the Assets page, including all
indexed images, videos, JSON, OBJ, and FBX files, plus the remaining FLAC files
and complete raw Audio/Assets indexes. Assets also used by normal pages are
intentionally duplicated so this package is self-contained for the Assets page.
"""

CHINESE_USAGE_README = """Endfield WebUI 中文使用说明

本次发布包含四个压缩包：

1. *-endfield-story-exported.zip
   主程序包，包含 WebUI 程序和文本数据。必须先解压此包。

2. *-endfield-story-exported-media.zip
   常用图片和视频包，只包含剧情、文本、地图、角色和玩法页面实际引用的图片和视频。
   建议所有用户安装。请解压到主程序包所在的同一个文件夹，并允许合并目录和覆盖索引文件。

3. *-endfield-story-exported-audio.zip
   常用语音包，只包含剧情、文本、地图、角色和玩法页面实际引用的 FLAC 音频。
   需要播放常用页面语音时安装，并解压到同一个文件夹。

4. *-endfield-story-exported-resources.zip
   可选完整资源包，包含“资源”页面列出的全部文件（包括图片、视频、JSON、OBJ 和 FBX）、其余 FLAC 音频，以及“音频”和“资源”页面使用的完整索引。
   只浏览常用页面时不需要此包。需要检索完整资源时，请最后解压到同一个文件夹，并允许覆盖索引文件。

推荐解压顺序：主程序包 → 常用图片和视频包 → 常用语音包 → 可选完整资源包。

安装 Python 3 后，在解压目录中运行：

    python serve.py

然后打开命令行显示的地址，通常是 http://127.0.0.1:8765/ 。
如果端口被占用，可以运行 `python serve.py 9000`。
请不要直接双击 webui/index.html，否则浏览器可能无法加载数据和媒体文件。

打包时可用一个逗号分隔的参数自由选择压缩包，并按写入顺序列出名称。例如：

    .\\pack_webui.bat story,audio,media,resource
    .\\pack_webui.bat resource

不提供此参数时会生成全部四个压缩包。
"""


@dataclass(frozen=True)
class ExportedImage:
    rel: str
    source_path: Path
    archive_path: str


@dataclass
class PackagePlan:
    curated_asset_payload: dict
    complete_asset_payload: dict
    curated_images: list[ExportedImage]
    curated_videos: list[ExportedImage]
    resource_assets: list[ExportedImage]
    curated_audio_files: list[ExportedImage]
    resource_audio_files: list[ExportedImage]
    audio_indexes: list[ExportedImage]


def parse_package_selection(value: str) -> tuple[str, ...]:
    packages = tuple(part.strip().lower() for part in value.split(",") if part.strip())
    if not packages:
        raise argparse.ArgumentTypeError("package selection cannot be empty")
    invalid = [package for package in packages if package not in PACKAGE_NAMES]
    if invalid:
        raise argparse.ArgumentTypeError(
            f"unknown package {invalid[0]!r}; choose from {','.join(PACKAGE_NAMES)}"
        )
    if len(set(packages)) != len(packages):
        raise argparse.ArgumentTypeError("package selection contains duplicates")
    return packages


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a WebUI code/text zip, referenced visual-media and audio "
            "zips, and an optional-complete resources zip."
        ),
    )
    parser.add_argument(
        "packages",
        nargs="?",
        type=parse_package_selection,
        default=None,
        help=(
            "Comma-separated packages to build in the requested order: "
            "story,media,audio,resource. Default: all four."
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
    args = parser.parse_args(argv)
    args.packages = args.packages or PACKAGE_NAMES
    return args


def default_output_path(project_root: Path) -> Path:
    datestamp = datetime.now().strftime("%Y%m%d")
    return project_root / f"{datestamp}-{ZIP_NAME_PREFIX}.zip"


def default_media_output_path(project_root: Path) -> Path:
    datestamp = datetime.now().strftime("%Y%m%d")
    return project_root / f"{datestamp}-{MEDIA_ZIP_NAME_PREFIX}.zip"


def default_audio_output_path(project_root: Path) -> Path:
    datestamp = datetime.now().strftime("%Y%m%d")
    return project_root / f"{datestamp}-{AUDIO_ZIP_NAME_PREFIX}.zip"


def default_resources_output_path(project_root: Path) -> Path:
    datestamp = datetime.now().strftime("%Y%m%d")
    return project_root / f"{datestamp}-{RESOURCES_ZIP_NAME_PREFIX}.zip"


def companion_media_output_path(output: Path, project_root: Path) -> Path:
    if output == default_output_path(project_root):
        return default_media_output_path(project_root)
    if output.suffix.lower() == ".zip":
        return output.with_name(f"{output.stem}-media{output.suffix}")
    return output.with_name(f"{output.name}-media.zip")


def companion_audio_output_path(output: Path, project_root: Path) -> Path:
    if output == default_output_path(project_root):
        return default_audio_output_path(project_root)
    if output.suffix.lower() == ".zip":
        return output.with_name(f"{output.stem}-audio{output.suffix}")
    return output.with_name(f"{output.name}-audio.zip")


def companion_resources_output_path(output: Path, project_root: Path) -> Path:
    if output == default_output_path(project_root):
        return default_resources_output_path(project_root)
    if output.suffix.lower() == ".zip":
        return output.with_name(f"{output.stem}-resources{output.suffix}")
    return output.with_name(f"{output.name}-resources.zip")


def posix_to_path(value: str) -> Path:
    parts = [part for part in PurePosixPath(value).parts if part not in ("", ".")]
    return Path(*parts) if parts else Path()


def archive_name(path: str | Path) -> str:
    return normalize_posix(str(path))


def is_companion_feature_path(rel: str) -> bool:
    normalized = normalize_posix(rel)
    return normalized in COMPANION_FEATURE_FILES or normalized.startswith(COMPANION_FEATURE_PREFIXES) or bool(
        COMPANION_LANGUAGE_FEATURE_RE.match(normalized)
    )


def is_page_reference_path(rel: str) -> bool:
    normalized = normalize_posix(rel)
    return (
        normalized in PAGE_REFERENCE_FILES
        or normalized.startswith(PAGE_REFERENCE_PREFIXES)
        or bool(PAGE_REFERENCE_LANGUAGE_RE.match(normalized))
    )


def is_resource_data_path(rel: str) -> bool:
    normalized = normalize_posix(rel)
    return normalized.startswith(RESOURCE_DATA_PREFIXES) or bool(
        RESOURCE_DATA_LANGUAGE_RE.match(normalized)
    )


def iter_webui_text_files(webui_root: Path) -> Iterable[Path]:
    for path in sorted(webui_root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(webui_root).as_posix()
        if is_resource_data_path(rel):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def iter_page_local_media_files(webui_root: Path) -> Iterable[Path]:
    for path in sorted(webui_root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(webui_root).as_posix()
        if is_companion_feature_path(rel) and path.suffix.lower() not in TEXT_EXTENSIONS:
            yield path


def iter_resource_data_files(webui_root: Path) -> Iterable[Path]:
    for path in sorted(webui_root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(webui_root).as_posix()
        if is_resource_data_path(rel):
            yield path


def iter_page_reference_files(webui_root: Path) -> Iterable[Path]:
    for path in sorted(webui_root.rglob("*.json")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(webui_root).as_posix()
        if is_page_reference_path(rel):
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


def filtered_media_index(payload: dict, selected_entries: list[dict]) -> dict:
    selected_entries = sorted(selected_entries, key=lambda entry: str(entry.get("r") or ""))
    source_roots = payload.get("sourceRoots") if isinstance(payload.get("sourceRoots"), dict) else {}
    used_sources = {normalize_posix(str(entry.get("r") or "")).split("/")[0] for entry in selected_entries}
    image_count = sum(entry.get("k") == "image" for entry in selected_entries)
    video_count = sum(entry.get("k") == "video" for entry in selected_entries)
    counts = {
        "total": len(selected_entries),
        "image": image_count,
        "video": video_count,
        "model": 0,
        "imageIds": image_count,
        "videoRefs": video_count,
    }
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


def merged_media_asset_payload(full_payload: dict, story_payload: dict) -> dict:
    by_rel: dict[str, dict] = {}
    for entry in [*(full_payload.get("entries") or []), *(story_payload.get("entries") or [])]:
        if not isinstance(entry, dict) or entry.get("k") not in MEDIA_ASSET_KINDS or not entry.get("r"):
            continue
        by_rel[normalize_posix(str(entry["r"]))] = dict(entry)
    source_roots = {}
    for payload in (full_payload, story_payload):
        roots = payload.get("sourceRoots") if isinstance(payload.get("sourceRoots"), dict) else {}
        source_roots.update(roots)
    merged = dict(full_payload)
    merged["sourceRoots"] = source_roots
    return filtered_media_index(merged, list(by_rel.values()))


def iter_nested_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_nested_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_nested_strings(child)


def collect_page_media_references(
    paths: Iterable[Path],
    *,
    known_asset_rels: set[str],
    known_audio_rels: set[str],
) -> tuple[set[str], set[str]]:
    """Collect exact generated page references without treating debug inventories as usage."""
    asset_rels: set[str] = set()
    audio_rels: set[str] = set()
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Cannot read page media references from {path}: {exc}") from exc
        for raw in iter_nested_strings(payload):
            normalized = normalize_posix(raw).split("?", 1)[0].split("#", 1)[0]
            if normalized in known_asset_rels:
                asset_rels.add(normalized)
            for marker in ("StreamingAssets/", "Persistent/"):
                marker_index = normalized.find(marker)
                if marker_index >= 0:
                    candidate = normalized[marker_index:]
                    if candidate in known_asset_rels:
                        asset_rels.add(candidate)
            audio_index = normalized.find("structured/Audio/")
            if audio_index >= 0:
                candidate = normalized[audio_index:]
                if candidate in known_audio_rels:
                    audio_rels.add(candidate)
    return asset_rels, audio_rels


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
    compress_type = (
        zipfile.ZIP_STORED
        if source.suffix.lower() in ALREADY_COMPRESSED_EXTENSIONS
        else zipfile.ZIP_DEFLATED
    )
    zipf.write(source, normalized, compress_type=compress_type, compresslevel=6)
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
    full_asset_payload = load_required_asset_index(webui_root / "data" / "assets" / "index.json")
    media_payload = merged_media_asset_payload(full_asset_payload, story_media_payload)
    media_entries = [dict(entry) for entry in media_payload.get("entries") or []]
    entries_by_rel = {
        normalize_posix(str(entry.get("r") or "")): entry
        for entry in media_entries
        if entry.get("r")
    }

    all_audio_files = (
        [exported_file(export_root, path) for path in iter_exported_audio_files(export_root)]
        if include_audio else []
    )
    known_audio = {item.rel for item in all_audio_files}
    page_asset_rels, page_audio_rels = collect_page_media_references(
        iter_page_reference_files(webui_root),
        known_asset_rels=set(entries_by_rel),
        known_audio_rels=known_audio,
    )
    page_asset_rels.update(
        normalize_posix(str(entry.get("r") or ""))
        for entry in story_media_payload.get("entries") or []
        if isinstance(entry, dict) and entry.get("r")
    )

    curated_entries = [entries_by_rel[rel] for rel in sorted(page_asset_rels) if rel in entries_by_rel]
    curated_payload = filtered_media_index(media_payload, curated_entries)

    def resolved_assets(kind: str, rels: Iterable[str]) -> list[ExportedImage]:
        return [
            resolve_exported_image(project_root, export_root, media_payload, rel)
            for rel in sorted(rels)
            if entries_by_rel[rel].get("k") == kind
        ]

    curated_rels = set(page_asset_rels) & set(entries_by_rel)
    resource_entries_by_rel = {
        normalize_posix(str(entry.get("r") or "")): entry
        for entry in full_asset_payload.get("entries") or []
        if isinstance(entry, dict) and entry.get("r")
    }
    resource_assets = [
        resolve_exported_image(project_root, export_root, full_asset_payload, rel)
        for rel in sorted(resource_entries_by_rel)
    ]
    curated_audio_files = [item for item in all_audio_files if item.rel in page_audio_rels]
    resource_audio_files = [item for item in all_audio_files if item.rel not in page_audio_rels]
    audio_indexes = (
        [exported_file(export_root, path) for path in iter_exported_audio_indexes(export_root)]
        if include_audio
        else []
    )

    return PackagePlan(
        curated_asset_payload=curated_payload,
        complete_asset_payload=full_asset_payload,
        curated_images=resolved_assets("image", curated_rels),
        curated_videos=resolved_assets("video", curated_rels),
        resource_assets=resource_assets,
        curated_audio_files=curated_audio_files,
        resource_audio_files=resource_audio_files,
        audio_indexes=audio_indexes,
    )


def create_package(args: argparse.Namespace) -> int:
    webui_root = WEBUI_ROOT.resolve()
    project_root = PROJECT_ROOT.resolve()
    export_root = EXPORT_ROOT.resolve()
    story_output = (args.output or default_output_path(project_root)).resolve()
    outputs = {
        "story": story_output,
        "media": companion_media_output_path(story_output, project_root).resolve(),
        "audio": companion_audio_output_path(story_output, project_root).resolve(),
        "resource": companion_resources_output_path(story_output, project_root).resolve(),
    }
    selected = set(args.packages)

    if not webui_root.exists():
        raise SystemExit(f"WebUI root not found: {webui_root}")
    if not (project_root / "serve.py").exists():
        raise SystemExit(f"serve.py not found under project root: {project_root}")
    selected_outputs = [outputs[package] for package in args.packages]
    if len(set(selected_outputs)) != len(selected_outputs):
        raise SystemExit("Package output paths must be different.")

    needs_media_plan = bool(selected & {"media", "audio", "resource"})
    include_audio = bool(selected & {"audio", "resource"})
    plan = plan_package(include_audio=include_audio) if needs_media_plan else None

    source_sizes: dict[Path, int] = {}

    def partition_existing(
        items: list[ExportedImage],
    ) -> tuple[list[ExportedImage], list[ExportedImage]]:
        present: list[ExportedImage] = []
        absent: list[ExportedImage] = []
        for item in items:
            if item.source_path in source_sizes:
                present.append(item)
                continue
            try:
                source_sizes[item.source_path] = item.source_path.stat().st_size
            except OSError:
                absent.append(item)
            else:
                present.append(item)
        return present, absent

    curated_images, missing_curated_images = (
        partition_existing(plan.curated_images) if plan and "media" in selected else ([], [])
    )
    curated_videos, missing_curated_videos = (
        partition_existing(plan.curated_videos) if plan and "media" in selected else ([], [])
    )
    resource_assets, missing_resource_assets = (
        partition_existing(plan.resource_assets) if plan and "resource" in selected else ([], [])
    )
    curated_audio, missing_curated_audio = (
        partition_existing(plan.curated_audio_files) if plan and "audio" in selected else ([], [])
    )
    resource_audio, missing_resource_audio = (
        partition_existing(plan.resource_audio_files) if plan and "resource" in selected else ([], [])
    )

    copied_text_files = []
    if "story" in selected:
        copied_text_files = [
            path for path in iter_webui_text_files(webui_root)
            if path.relative_to(webui_root).as_posix() != "data/assets/index.json"
        ]
    page_local_media_files = list(iter_page_local_media_files(webui_root)) if "media" in selected else []
    resource_data_files = list(iter_resource_data_files(webui_root)) if "resource" in selected else []
    missing_media: list[ExportedImage] = []
    if plan and "media" in selected:
        missing_media.extend(missing_curated_images + missing_curated_videos)
    if plan and "audio" in selected:
        missing_media.extend(missing_curated_audio)
    if plan and "resource" in selected:
        missing_media.extend(missing_resource_assets + missing_resource_audio)

    def size_gib(paths: Iterable[Path]) -> float:
        total = 0
        for path in paths:
            if path in source_sizes:
                total += source_sizes[path]
                continue
            try:
                total += path.stat().st_size
            except OSError:
                pass
        return total / (1024 ** 3)

    print(f"WebUI root: {webui_root}")
    print(f"Export root: {export_root}")
    print(f"Selected packages: {','.join(args.packages)}")
    for package in args.packages:
        print(f"{package.title()} zip: {outputs[package]}")
    if include_audio:
        print(f"Audio format: {PACK_AUDIO_FORMAT}")
    if "story" in selected:
        print(f"Text files: {len(copied_text_files) + 4:,}")
    if "media" in selected:
        print(
            "Page image/video media:",
            f"{len(curated_images):,} images, {len(curated_videos):,} videos, "
            f"{len(page_local_media_files):,} local files "
            f"({size_gib([item.source_path for item in curated_images + curated_videos] + page_local_media_files):.2f} GiB)",
        )
    if "audio" in selected:
        print(
            "Page audio:",
            f"{len(curated_audio):,} FLAC files "
            f"({size_gib([item.source_path for item in curated_audio]):.2f} GiB)",
        )
    if "resource" in selected:
        resource_kind_counts: dict[str, int] = {}
        if plan:
            for entry in plan.complete_asset_payload.get("entries") or []:
                if isinstance(entry, dict) and entry.get("r"):
                    kind = str(entry.get("k") or "other")
                    resource_kind_counts[kind] = resource_kind_counts.get(kind, 0) + 1
        kind_summary = ", ".join(
            f"{count:,} {kind}" for kind, count in sorted(resource_kind_counts.items())
        )
        print(
            "Complete Assets-page resources:",
            f"{len(resource_assets):,} indexed files ({kind_summary}); "
            f"{len(resource_audio):,} remaining audio, "
            f"{len(resource_data_files):,} index/data files "
            f"({size_gib([item.source_path for item in resource_assets + resource_audio] + resource_data_files):.2f} GiB)",
        )
        if include_audio and plan:
            print(f"Raw exported audio indexes in resources: {len(plan.audio_indexes):,}")
    if missing_media:
        preview = ", ".join(item.rel for item in missing_media[:10])
        suffix = "..." if len(missing_media) > 10 else ""
        print(f"Missing exported media files: {len(missing_media):,} ({preview}{suffix})")
    if args.dry_run:
        return 0

    for package in args.packages:
        package_output = outputs[package]
        with staged_package_output(package_output) as staged_output:
            if package == "story":
                _write_code_package(
                    staged_output,
                    project_root=project_root,
                    webui_root=webui_root,
                    copied_text_files=copied_text_files,
                )
            elif package == "media":
                assert plan is not None
                _write_media_package(
                    staged_output,
                    webui_root=webui_root,
                    plan=plan,
                    page_local_media_files=page_local_media_files,
                    curated_images=curated_images,
                    curated_videos=curated_videos,
                )
            elif package == "audio":
                _write_page_audio_package(staged_output, curated_audio=curated_audio)
            elif package == "resource":
                assert plan is not None
                _write_resources_package(
                    staged_output,
                    webui_root=webui_root,
                    plan=plan,
                    resource_data_files=resource_data_files,
                    resource_assets=resource_assets,
                    resource_audio=resource_audio,
                )
        size_mb = package_output.stat().st_size / (1024 * 1024)
        print(f"Wrote {package} zip: {package_output} ({size_mb:.1f} MiB)", flush=True)
    return 0


@contextmanager
def staged_package_output(output: Path):
    """Atomically publish one package immediately after it is complete."""
    temp_path: Path | None = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
        )
        os.close(descriptor)
        temp_path = Path(temp_name)
        yield temp_path
        temp_path.replace(output)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _write_code_package(
    output: Path,
    *,
    project_root: Path,
    webui_root: Path,
    copied_text_files: list[Path],
) -> None:
    written: set[str] = set()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        zip_write_file(zipf, written, project_root / "serve.py", "serve.py")
        zip_writestr(zipf, written, "README.txt", CHINESE_USAGE_README)
        zip_writestr(zipf, written, "README-中文说明.txt", CHINESE_USAGE_README)
        zip_writestr(zipf, written, "README-webui-package.txt", CODE_PACKAGE_README)

        for path in copied_text_files:
            zip_write_file(zipf, written, path, webui_arcname(webui_root, path))


def _write_media_package(
    media_output: Path,
    *,
    webui_root: Path,
    plan: PackagePlan,
    page_local_media_files: list[Path],
    curated_images: list[ExportedImage],
    curated_videos: list[ExportedImage],
) -> None:
    written: set[str] = set()
    with zipfile.ZipFile(media_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        zip_writestr(zipf, written, "README.txt", CHINESE_USAGE_README)
        zip_writestr(zipf, written, "README-中文说明.txt", CHINESE_USAGE_README)
        zip_writestr(zipf, written, "README-webui-media-package.txt", MEDIA_PACKAGE_README)
        asset_index_json = json.dumps(plan.curated_asset_payload, ensure_ascii=False, separators=(",", ":"))
        zip_writestr(zipf, written, "webui/data/assets/index.json", asset_index_json)
        for path in page_local_media_files:
            zip_write_file(zipf, written, path, webui_arcname(webui_root, path))
        for item in curated_images + curated_videos:
            zip_write_file(zipf, written, item.source_path, item.archive_path)


def _write_page_audio_package(
    audio_output: Path,
    *,
    curated_audio: list[ExportedImage],
) -> None:
    written: set[str] = set()
    with zipfile.ZipFile(audio_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        zip_writestr(zipf, written, "README.txt", CHINESE_USAGE_README)
        zip_writestr(zipf, written, "README-中文说明.txt", CHINESE_USAGE_README)
        zip_writestr(zipf, written, "README-webui-audio-package.txt", AUDIO_PAGE_PACKAGE_README)
        for item in curated_audio:
            zip_write_file(zipf, written, item.source_path, item.archive_path)


def _write_resources_package(
    resources_output: Path,
    *,
    webui_root: Path,
    plan: PackagePlan,
    resource_data_files: list[Path],
    resource_assets: list[ExportedImage],
    resource_audio: list[ExportedImage],
) -> None:
    written: set[str] = set()
    with zipfile.ZipFile(resources_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        zip_writestr(zipf, written, "README.txt", CHINESE_USAGE_README)
        zip_writestr(zipf, written, "README-中文说明.txt", CHINESE_USAGE_README)
        zip_writestr(zipf, written, "README-webui-resources-package.txt", RESOURCES_PACKAGE_README)
        asset_index_json = json.dumps(plan.complete_asset_payload, ensure_ascii=False, separators=(",", ":"))
        zip_writestr(zipf, written, "webui/data/assets/index.json", asset_index_json)
        for path in resource_data_files:
            zip_write_file(zipf, written, path, webui_arcname(webui_root, path))
        for item in resource_assets + resource_audio:
            zip_write_file(zipf, written, item.source_path, item.archive_path)
        for audio_index in plan.audio_indexes:
            zip_write_file(zipf, written, audio_index.source_path, audio_index.archive_path)



def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return create_package(args)


if __name__ == "__main__":
    sys.exit(main())
