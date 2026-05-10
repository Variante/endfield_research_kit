#!/usr/bin/env python3
"""Build a self-contained WebUI zip without the 3D asset browser payload.

The package keeps the story/reference browser text data and copies only the
exported media files that the story renderer can display from inline
``<image...>`` tags or inferred wiki-entry media. OBJ/FBX files, Blender
bundles, and the asset-browser data page are intentionally left out.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import html
import json
import posixpath
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEBUI_ROOT = PROJECT_ROOT / "webui"
EXPORT_ROOT = PROJECT_ROOT / "export_full"
ZIP_NAME_PREFIX = "endfield-story-exported"

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

IMAGE_TOKEN_RE = re.compile(
    r"<image\b(?!\s*=)[^>]*>[\s\S]*?</image>"
    r"|<image\s*=[^>]+>"
    r"|<image\b(?=[^>]*(?:src|source|path|name|id)\s*=)[^>]*>",
    re.IGNORECASE,
)

ASSET_VIEW_START_RE = re.compile(r'<section\s+id="assets-view"(?=[\s>])', re.IGNORECASE)
ASSET_TAB_RE = re.compile(r'(<button\s+id="assets-tab"(?=[\s>]))([^>]*>)', re.IGNORECASE)

ASSET_SHIM_JS = """(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function resolveViewFromHash() {
    const hash = (window.location.hash || "").toLowerCase();
    if (hash === "#reference") return "reference";
    if (hash === "#updates") return "updates";
    return "story";
  }

  function updateHashForView(view) {
    const nextHash = view === "reference" ? "#reference" : view === "updates" ? "#updates" : "#story";
    if (window.location.hash === nextHash) return;
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}${nextHash}`);
  }

  function setActiveView(view, { updateHash = true } = {}) {
    const active = view === "reference" || view === "updates" ? view : "story";
    document.body.dataset.activeView = active;

    $$(".view-tab").forEach((button) => {
      const selected = button.dataset.view === active;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-selected", String(selected));
    });

    $$(".page-view").forEach((page) => {
      const selected = page.dataset.view === active;
      page.hidden = !selected;
      page.classList.toggle("is-active", selected);
    });

    if (updateHash) updateHashForView(active);
    window.dispatchEvent(new CustomEvent("webui:view-changed", { detail: { view: active } }));
    window.dispatchEvent(new Event("resize"));
  }

  const assetTab = $("#assets-tab");
  if (assetTab) {
    assetTab.hidden = true;
    assetTab.setAttribute("aria-hidden", "true");
    assetTab.tabIndex = -1;
  }

  $$(".view-tab").forEach((button) => {
    if (button.dataset.view === "assets") return;
    button.addEventListener("click", () => setActiveView(button.dataset.view));
  });

  window.addEventListener("hashchange", () => setActiveView(resolveViewFromHash(), { updateHash: false }));
  setActiveView(resolveViewFromHash(), { updateHash: false });
})();
"""

PACKAGE_README = """Self-contained Endfield WebUI package

Run from this extracted directory:

    python serve.py

Then open the printed localhost URL.

This package includes the story/reference text data and only the exported image
and video files needed by inline/wiki media in the WebUI. The 3D asset browser,
OBJ/FBX payloads, and Blender bundle downloads are intentionally excluded.
"""


@dataclass(frozen=True)
class AssetCandidate:
    rel: str
    name: str
    stem: str
    score: int
    entry: dict


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
    unresolved_image_ids: set[str]
    unresolved_video_ids: set[str]
    image_ids: set[str]
    video_refs: set[tuple[str, str]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a self-contained WebUI zip with text data and displayed wiki media only.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Zip path to write. Default: "
            f"{ZIP_NAME_PREFIX}-YYYYMMDD.zip, where YYYYMMDD is today's local date."
        ),
    )
    parser.add_argument(
        "--webui-root",
        type=Path,
        default=WEBUI_ROOT,
        help=f"WebUI directory to package. Default: {WEBUI_ROOT}",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=EXPORT_ROOT,
        help=f"Export root used by serve.py. Default: {EXPORT_ROOT}",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=f"Project root containing serve.py. Default: {PROJECT_ROOT}",
    )
    parser.add_argument(
        "--include-asset-browser",
        action="store_true",
        help=(
            "Keep the original asset-browser UI files, but still package only "
            "the filtered media indexes and no model or bundle files."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the package plan without writing the zip.",
    )
    return parser.parse_args(argv)


def default_output_path(project_root: Path) -> Path:
    datestamp = datetime.now().strftime("%Y%m%d")
    return project_root / f"{ZIP_NAME_PREFIX}-{datestamp}.zip"


def normalize_posix(value: str) -> str:
    return str(value or "").replace("\\", "/").strip("/")


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
        if path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def clean_inline_image_id_value(value: str) -> str:
    text = html.unescape(str(value or "")).strip()
    text = text.replace(r"\"", '"').replace(r"\'", "'")
    for _ in range(3):
        unwrapped = re.sub(r'^[\'"]+|[\'"]+$', "", text).strip()
        if unwrapped == text:
            break
        text = unwrapped
    return text


def normalize_inline_image_id(value: str) -> str:
    trimmed = clean_inline_image_id_value(value).replace("\\", "/")
    if not trimmed:
        return ""
    without_prefix = re.sub(r"^SNS/Emoji/", "", trimmed, flags=re.IGNORECASE)
    last_segment = without_prefix.split("/")[-1] or without_prefix
    return re.sub(r"\.[^.]+$", "", last_segment, flags=re.IGNORECASE).lower()


def inline_image_number_key(value: str) -> str:
    match = re.search(r"(?:^|[_-])(\d{1,3})$", str(value or ""))
    if not match:
        return ""
    return str(int(match.group(1)))


def extract_inline_image_id_from_tag(raw_tag: str) -> str:
    raw = str(raw_tag or "").strip()
    if not raw:
        return ""

    body_match = re.match(r"^<image\b(?!\s*=)[^>]*>([\s\S]*?)</image>$", raw, flags=re.IGNORECASE)
    if body_match:
        return clean_inline_image_id_value(body_match.group(1))

    quoted_direct = re.match(r"""^<image\s*=\s*(["'])([\s\S]*?)\1""", raw, flags=re.IGNORECASE)
    if quoted_direct:
        return clean_inline_image_id_value(quoted_direct.group(2))

    loose_direct = re.match(r"^<image\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE)
    if loose_direct:
        return clean_inline_image_id_value(loose_direct.group(1))

    quoted_attr = re.search(
        r"""\b(?:src|source|path|name|id)\s*=\s*(["'])([\s\S]*?)\1""",
        raw,
        flags=re.IGNORECASE,
    )
    if quoted_attr:
        return clean_inline_image_id_value(quoted_attr.group(2))

    loose_attr = re.search(r"\b(?:src|source|path|name|id)\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE)
    return clean_inline_image_id_value(loose_attr.group(1)) if loose_attr else ""


def collect_inline_image_ids(webui_root: Path) -> set[str]:
    """Collect normalized image IDs from files the story UI renders as rich text."""
    roots: list[Path] = [
        webui_root / "data" / "conv",
        webui_root / "data" / "mission",
    ]
    lang_root = webui_root / "data" / "lang"
    if lang_root.exists():
        for lang_dir in sorted(path for path in lang_root.iterdir() if path.is_dir()):
            roots.append(lang_dir / "conv")
            roots.append(lang_dir / "mission")

    image_ids: set[str] = set()

    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("*.json")) if root.exists() else []
        for path in files:
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in IMAGE_TOKEN_RE.finditer(text):
                image_id = normalize_inline_image_id(extract_inline_image_id_from_tag(match.group(0)))
                if image_id:
                    image_ids.add(image_id)

    return image_ids


def wiki_media_candidate_ids(value: object) -> list[str]:
    normalized = normalize_inline_image_id(str(value or ""))
    if not normalized:
        return []

    ids: list[str] = []

    def push(image_id: str) -> None:
        key = normalize_inline_image_id(image_id)
        if key and key not in ids:
            ids.append(key)

    push(normalized)

    if normalized.startswith("wiki_"):
        push(normalized[len("wiki_") :])
    if normalized.startswith("wiki_item_"):
        push(f"item_{normalized[len('wiki_item_') :]}")
    elif normalized.startswith("wiki_wpn_"):
        push(f"wpn_{normalized[len('wiki_wpn_') :]}")
    elif normalized.startswith("wiki_eny_"):
        push(f"eny_{normalized[len('wiki_eny_') :]}")

    for prefix in (
        "sketch_guide_video_",
        "guide_video_",
        "wiki_video_tut_adv_",
        "wiki_video_",
        "video_",
    ):
        if not normalized.startswith(prefix):
            continue
        suffix = normalized[len(prefix) :]
        if not suffix:
            continue
        push(suffix)
        push(f"image_{suffix}")
        push(f"wiki_pic_{suffix}")
        push(f"guide_pic_{suffix}")
        for idx in range(1, 6):
            push(f"guide_pic_{suffix}_{idx}")
            push(f"wiki_pic_{suffix}_{idx}")

    return ids


def collect_wiki_media_image_ids(webui_root: Path) -> set[str]:
    """Collect exact image IDs inferred by the runtime wiki media resolver."""
    roots: list[Path] = [
        webui_root / "data" / "conv",
    ]
    lang_root = webui_root / "data" / "lang"
    if lang_root.exists():
        for lang_dir in sorted(path for path in lang_root.iterdir() if path.is_dir()):
            roots.append(lang_dir / "conv")

    image_ids: set[str] = set()

    def add(value: object) -> None:
        for image_id in wiki_media_candidate_ids(value):
            image_ids.add(image_id)

    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("wiki_*.json")) if root.exists() else []
        for path in files:
            if "__pycache__" in path.parts:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("kind") != "wiki":
                continue

            debug_source = ((payload.get("_debug") or {}).get("source") or {}).get("source") or {}
            if isinstance(debug_source, dict):
                add(debug_source.get("refItemId"))
                add(debug_source.get("refMonsterTemplateId"))

            for line in payload.get("lines") or []:
                if not isinstance(line, dict):
                    continue
                source = (line.get("_debug") or {}).get("source") or {}
                if not isinstance(source, dict):
                    continue
                add(source.get("image"))
                add(source.get("video"))
                for ref_id in source.get("refWikiEntryIds") or []:
                    add(ref_id)

    return image_ids


def collect_wiki_video_refs(webui_root: Path) -> set[tuple[str, str]]:
    """Collect wiki tutorial video IDs and preferred device variants."""
    roots: list[Path] = [
        webui_root / "data" / "conv",
    ]
    lang_root = webui_root / "data" / "lang"
    if lang_root.exists():
        for lang_dir in sorted(path for path in lang_root.iterdir() if path.is_dir()):
            roots.append(lang_dir / "conv")

    refs: set[tuple[str, str]] = set()

    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("wiki_*.json")) if root.exists() else []
        for path in files:
            if "__pycache__" in path.parts:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("kind") != "wiki":
                continue

            for line in payload.get("lines") or []:
                if not isinstance(line, dict):
                    continue
                source = (line.get("_debug") or {}).get("source") or {}
                if not isinstance(source, dict):
                    continue
                video_id = normalize_inline_image_id(str(source.get("video") or ""))
                if video_id:
                    refs.add((video_id, str(source.get("videoDeviceType") or "")))

    return refs


def video_device_folders(device_type: str) -> tuple[str, ...]:
    normalized = str(device_type or "").strip().lower()
    if normalized in {"mouseandkeyboard", "pc"}:
        return ("PC", "Common")
    if normalized in {"controller", "ct"}:
        return ("CT", "Common")
    if normalized in {"touch", "mobile", "mb"}:
        return ("CT", "Common", "PC")
    return ("Common", "PC", "CT")


def is_browser_playable_video(rel: str) -> bool:
    return re.search(r"\.(?:mp4|webm|ogv|ogg|mov|m4v)$", str(rel or ""), flags=re.IGNORECASE) is not None


def score_wiki_video_asset(rel: str, device_type: str = "") -> int:
    rel_normalized = normalize_posix(rel)
    rel_lower = rel_normalized.lower()
    score = 1
    for index, folder in enumerate(video_device_folders(device_type)):
        if f"/guide/{folder.lower()}/" in rel_lower:
            score += 100 - index * 10
            break
    if is_browser_playable_video(rel_normalized):
        score += 40
    if rel_lower.startswith(("streamingassets-structured/", "persistent-structured/")):
        score += 10
    elif rel_lower.startswith("raw_vfs/"):
        score += 1
    return score


def score_inline_image_asset(rel: str, stem: str) -> int:
    rel_lower = str(rel or "").lower()
    score = 1
    if "/sprite/" in rel_lower:
        score += 40
    elif "/texture2d/" in rel_lower:
        score += 20

    if stem.startswith("deco_sns_tweet_decorate_"):
        score += 140
    elif stem.startswith("bg_sns_tweet_decorate_"):
        score += 120
    elif stem.startswith("sns_sticker_"):
        score += 90
    elif stem.startswith("emoji_"):
        score += 60
    elif "sns" in stem:
        score += 40
    elif "emoji" in stem:
        score += 30
    return score


def remember_best(mapping: dict[str, AssetCandidate], key: str, candidate: AssetCandidate) -> None:
    if not key:
        return
    current = mapping.get(key)
    if current is None or candidate.score > current.score or (
        candidate.score == current.score and candidate.rel < current.rel
    ):
        mapping[key] = candidate


def is_sns_inline_image_stem(stem: str) -> bool:
    normalized = str(stem or "").lower()
    return "sns" in normalized or "emoji" in normalized


def load_asset_index(asset_index_path: Path) -> dict:
    if not asset_index_path.exists():
        return {"generated": None, "root": "export_full", "sourceRoots": {}, "entries": []}
    with asset_index_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_inline_image_lookup(entries: Iterable[dict]) -> tuple[dict[str, AssetCandidate], dict[str, AssetCandidate]]:
    by_stem: dict[str, AssetCandidate] = {}
    by_number: dict[str, AssetCandidate] = {}

    for raw in entries:
        if not raw or raw.get("k") != "image" or not raw.get("r"):
            continue
        rel = normalize_posix(str(raw.get("r") or ""))
        if not rel:
            continue
        name = rel.split("/")[-1] or rel
        stem = re.sub(r"\.[^.]+$", "", name, flags=re.IGNORECASE).lower()
        if not stem:
            continue

        candidate = AssetCandidate(
            rel=rel,
            name=name,
            stem=stem,
            score=score_inline_image_asset(rel, stem),
            entry=raw,
        )
        remember_best(by_stem, stem, candidate)

        number_key = inline_image_number_key(stem)
        if number_key and is_sns_inline_image_stem(stem):
            remember_best(by_number, number_key, candidate)

    return by_stem, by_number


def build_video_lookup(entries: Iterable[dict]) -> dict[str, list[AssetCandidate]]:
    by_stem: dict[str, list[AssetCandidate]] = {}

    for raw in entries:
        if not raw or raw.get("k") != "video" or not raw.get("r"):
            continue
        rel = normalize_posix(str(raw.get("r") or ""))
        if not rel:
            continue
        name = rel.split("/")[-1] or rel
        stem = re.sub(r"\.[^.]+$", "", name, flags=re.IGNORECASE).lower()
        if not stem:
            continue
        candidate = AssetCandidate(
            rel=rel,
            name=name,
            stem=stem,
            score=score_wiki_video_asset(rel),
            entry=raw,
        )
        by_stem.setdefault(stem, []).append(candidate)

    for candidates in by_stem.values():
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.rel))

    return by_stem


def resolve_inline_image_assets(
    image_id: str,
    by_stem: dict[str, AssetCandidate],
    by_number: dict[str, AssetCandidate],
) -> list[AssetCandidate]:
    normalized = normalize_inline_image_id(image_id)
    if not normalized:
        return []

    matches: dict[str, AssetCandidate] = {}

    def add(candidate: AssetCandidate | None) -> None:
        if candidate:
            matches[candidate.rel] = candidate

    for stem in (normalized, f"{normalized}_m", f"{normalized}_f"):
        add(by_stem.get(stem))

    if normalized.startswith("sns_image_"):
        sns_suffix = normalized[len("sns_image_") :]
        add(by_stem.get(f"cg_image_{sns_suffix}"))

    number_key = inline_image_number_key(normalized)
    if number_key:
        padded2 = number_key.zfill(2)
        for stem in (
            f"deco_sns_tweet_decorate_{padded2}",
            f"bg_sns_tweet_decorate_{padded2}",
            f"sns_sticker_{padded2}",
            f"emoji_02_{number_key.zfill(3)}",
            f"emoji_01_{number_key.zfill(3)}",
        ):
            add(by_stem.get(stem))
        add(by_number.get(number_key))

    return list(matches.values())


def resolve_exact_image_assets(
    image_id: str,
    by_stem: dict[str, AssetCandidate],
) -> list[AssetCandidate]:
    normalized = normalize_inline_image_id(image_id)
    if not normalized:
        return []

    matches: dict[str, AssetCandidate] = {}
    for stem in (normalized, f"{normalized}_m", f"{normalized}_f"):
        candidate = by_stem.get(stem)
        if candidate:
            matches[candidate.rel] = candidate
    return list(matches.values())


def wiki_video_candidate_stems(video_id: str) -> list[str]:
    normalized = normalize_inline_image_id(video_id)
    if not normalized:
        return []

    stems: list[str] = []

    def push(stem: str) -> None:
        key = normalize_inline_image_id(stem)
        if key and key not in stems:
            stems.append(key)

    push(normalized)
    if normalized.endswith("_mb"):
        base = normalized[:-3]
        push(f"{base}_ct")
        push(base)
        push(f"{base}_pc")
    elif normalized.endswith(("_ct", "_pc")):
        push(re.sub(r"_(?:ct|pc)$", "", normalized, flags=re.IGNORECASE))

    return stems


def resolve_exact_video_asset(
    video_id: str,
    device_type: str,
    by_stem: dict[str, list[AssetCandidate]],
) -> AssetCandidate | None:
    candidates_by_rel: dict[str, AssetCandidate] = {}
    for stem in wiki_video_candidate_stems(video_id):
        for candidate in by_stem.get(stem) or []:
            candidates_by_rel[candidate.rel] = candidate
    candidates = list(candidates_by_rel.values())
    if not candidates:
        return None

    return sorted(
        candidates,
        key=lambda candidate: (-score_wiki_video_asset(candidate.rel, device_type), candidate.rel),
    )[0]


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


def plan_package(args: argparse.Namespace) -> PackagePlan:
    webui_root = args.webui_root.resolve()
    project_root = args.project_root.resolve()
    export_root = args.export_root.resolve()

    asset_payload = load_asset_index(webui_root / "data" / "assets" / "index.json")
    video_payload = load_asset_index(webui_root / "data" / "assets" / "videos.json")
    image_ids = collect_inline_image_ids(webui_root)
    wiki_image_ids = collect_wiki_media_image_ids(webui_root)
    video_refs = collect_wiki_video_refs(webui_root)
    by_stem, by_number = build_inline_image_lookup(asset_payload.get("entries") or [])
    video_by_stem = build_video_lookup(video_payload.get("entries") or [])

    selected_by_rel: dict[str, dict] = {}
    unresolved_ids: set[str] = set()
    unresolved_video_ids: set[str] = set()
    for image_id in sorted(image_ids):
        candidates = resolve_inline_image_assets(image_id, by_stem, by_number)
        if not candidates:
            unresolved_ids.add(image_id)
            continue
        for candidate in candidates:
            entry = dict(candidate.entry)
            entry["k"] = "image"
            entry["r"] = candidate.rel
            selected_by_rel[candidate.rel] = entry

    for image_id in sorted(wiki_image_ids):
        candidates = resolve_exact_image_assets(image_id, by_stem)
        if not candidates:
            continue
        for candidate in candidates:
            entry = dict(candidate.entry)
            entry["k"] = "image"
            entry["r"] = candidate.rel
            selected_by_rel[candidate.rel] = entry

    selected_video_by_rel: dict[str, dict] = {}
    for video_id, device_type in sorted(video_refs):
        candidate = resolve_exact_video_asset(video_id, device_type, video_by_stem)
        if not candidate:
            unresolved_video_ids.add(video_id)
            continue
        entry = dict(candidate.entry)
        entry["k"] = "video"
        entry["r"] = candidate.rel
        selected_video_by_rel[candidate.rel] = entry

    filtered_payload = filtered_asset_index(asset_payload, list(selected_by_rel.values()), kind="image")
    filtered_video_payload = filtered_asset_index(video_payload, list(selected_video_by_rel.values()), kind="video")

    exported_images = [
        resolve_exported_image(project_root, export_root, filtered_payload, rel)
        for rel in sorted(selected_by_rel)
    ]
    exported_videos = [
        resolve_exported_image(project_root, export_root, filtered_video_payload, rel)
        for rel in sorted(selected_video_by_rel)
    ]

    return PackagePlan(
        filtered_asset_payload=filtered_payload,
        filtered_video_payload=filtered_video_payload,
        exported_images=exported_images,
        exported_videos=exported_videos,
        unresolved_image_ids=unresolved_ids,
        unresolved_video_ids=unresolved_video_ids,
        image_ids=image_ids | wiki_image_ids,
        video_refs=video_refs,
    )


def create_package(args: argparse.Namespace) -> int:
    webui_root = args.webui_root.resolve()
    project_root = args.project_root.resolve()
    export_root = args.export_root.resolve()
    output = (args.output or default_output_path(project_root)).resolve()

    if not webui_root.exists():
        raise SystemExit(f"WebUI root not found: {webui_root}")
    if not (project_root / "serve.py").exists():
        raise SystemExit(f"serve.py not found under project root: {project_root}")

    plan = plan_package(args)
    missing_images = [image for image in plan.exported_images if not image.source_path.exists()]
    existing_images = [image for image in plan.exported_images if image.source_path.exists()]
    missing_videos = [video for video in plan.exported_videos if not video.source_path.exists()]
    existing_videos = [video for video in plan.exported_videos if video.source_path.exists()]

    text_files = list(iter_webui_text_files(webui_root))
    copied_text_files = [
        path for path in text_files
        if path.relative_to(webui_root).as_posix() not in {
            "data/assets/index.json",
            "data/assets/videos.json",
            "assets.js",
            "index.html",
        }
        and not path.relative_to(webui_root).as_posix().startswith("data/assets/bundles/")
    ]
    if args.include_asset_browser:
        copied_text_files = [
            path for path in text_files
            if path.relative_to(webui_root).as_posix() not in {
                "data/assets/index.json",
                "data/assets/videos.json",
            }
            and not path.relative_to(webui_root).as_posix().startswith("data/assets/bundles/")
        ]

    print(f"WebUI root: {webui_root}")
    print(f"Export root: {export_root}")
    print(f"Output zip: {output}")
    generated_text_count = 5 if args.include_asset_browser else 6
    print(f"Text files: {len(copied_text_files) + generated_text_count:,}")
    print(f"Story image IDs: {len(plan.image_ids):,}")
    print(f"Resolved image files: {len(existing_images):,}")
    print(f"Wiki video refs: {len(plan.video_refs):,}")
    print(f"Resolved video files: {len(existing_videos):,}")
    if plan.unresolved_image_ids:
        preview = ", ".join(sorted(plan.unresolved_image_ids)[:10])
        suffix = "..." if len(plan.unresolved_image_ids) > 10 else ""
        print(f"Unresolved image IDs: {len(plan.unresolved_image_ids):,} ({preview}{suffix})")
    if plan.unresolved_video_ids:
        preview = ", ".join(sorted(plan.unresolved_video_ids)[:10])
        suffix = "..." if len(plan.unresolved_video_ids) > 10 else ""
        print(f"Unresolved video IDs: {len(plan.unresolved_video_ids):,} ({preview}{suffix})")
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
    if output.exists():
        output.unlink()

    written: set[str] = set()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        zip_write_file(zipf, written, project_root / "serve.py", "serve.py")
        zip_writestr(zipf, written, "README-webui-package.txt", PACKAGE_README)

        for path in copied_text_files:
            zip_write_file(zipf, written, path, webui_arcname(webui_root, path))

        asset_index_json = json.dumps(plan.filtered_asset_payload, ensure_ascii=False, separators=(",", ":"))
        zip_writestr(zipf, written, "webui/data/assets/index.json", asset_index_json)
        video_index_json = json.dumps(plan.filtered_video_payload, ensure_ascii=False, separators=(",", ":"))
        zip_writestr(zipf, written, "webui/data/assets/videos.json", video_index_json)

        if args.include_asset_browser:
            bundles_index = {
                "generated": plan.filtered_asset_payload.get("generated"),
                "bundles": [],
                "byAssetRel": {},
            }
            zip_writestr(
                zipf,
                written,
                "webui/data/assets/bundles/index.json",
                json.dumps(bundles_index, ensure_ascii=False, separators=(",", ":")),
            )
        else:
            index_html = (webui_root / "index.html").read_text(encoding="utf-8")
            zip_writestr(zipf, written, "webui/index.html", strip_asset_view_from_index(index_html))
            zip_writestr(zipf, written, "webui/assets.js", ASSET_SHIM_JS)

        for image in existing_images:
            zip_write_file(zipf, written, image.source_path, image.archive_path)
        for video in existing_videos:
            zip_write_file(zipf, written, video.source_path, video.archive_path)

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Wrote {output} ({size_mb:.1f} MiB)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return create_package(args)


if __name__ == "__main__":
    sys.exit(main())
