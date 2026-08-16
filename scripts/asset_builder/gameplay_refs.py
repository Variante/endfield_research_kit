"""Build the small entity-to-asset index consumed by the Gameplay view.

The Assets view owns the broad exported asset index.  Gameplay only needs a
few representative image/model paths for the currently selected entity, so
keeping that relationship in a compact sidecar avoids loading the 100+ MB
asset index just to render a thumbnail.
"""
from __future__ import annotations

import json
import hashlib
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

if __package__.startswith("scripts."):
    from ..common import read_json, write_json
else:
    from common import read_json, write_json


SCHEMA_VERSION = "gameplayAssetRefs.v10"
SOURCE_GRAPH_SCHEMA_VERSION = "sourceGraph.v1"
DEFAULT_OUTPUT = Path("webui/data/assets/gameplay_refs.json")
PATH_ID_SUFFIX_RE = re.compile(r"_p[0-9a-f]{16}$", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

IMAGE_CATEGORIES_BY_KIND = {
    "character": ("chr_thumb", "character", "icon", "icon_round", "background"),
    "weapon": ("weapon", "icon", "icon_round"),
    "equipment": ("item", "icon", "item_potential"),
    "item": ("item", "item_potential", "icon", "icon_round"),
    "enemy": ("enemy", "boss", "icon"),
}
MATERIAL_ITEM_LIST_KEYS = frozenset({
    "requiredItem",
    "itemBundle",
    "items",
    "costs",
    "dropItems",
    "randomItems",
    "probableItems",
})
DISPLAY_ICON_KINDS = frozenset({"weapon", "equipment", "item"})


def _clean_token(value: Any) -> str:
    return str(value or "").strip().lower()


def _token_variants(value: Any) -> list[str]:
    token = _clean_token(value)
    if not token:
        return []
    variants = [token]
    # CharacterPotentialTable calls these `item_pic_*`, while exported image
    # names use the shorter `pic_*` stem.
    if token.startswith("item_pic_"):
        variants.append(token[len("item_"):])
    # Some exports store a potential's card token as item_topic_*, while the
    # authored full theme-card images use business_card_topic_*.
    if token.startswith("item_topic_"):
        variants.append(f"business_card_topic_{token[len('item_topic_'):]}")
    return list(dict.fromkeys(variants))


def _is_item_picture_token(value: Any) -> bool:
    token = _clean_token(value)
    return token.startswith("pic_") or token.startswith("item_pic_")


def _asset_base_name(rel: Any) -> str:
    name = Path(str(rel or "").replace("\\", "/")).stem.lower()
    return PATH_ID_SUFFIX_RE.sub("", name)


def _asset_representation(asset: dict[str, Any]) -> str:
    """Return the stable exported representation directory, if present."""
    rel = str(asset.get("r") or "").replace("\\", "/")
    parts = rel.split("/")
    return parts[1].lower() if len(parts) > 1 else ""


def _asset_content_sha256(assets: Iterable[dict[str, Any]]) -> str:
    """Fingerprint the deterministic Assets entries consumed by this builder."""
    payload = [asset for asset in assets if isinstance(asset, dict)]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _strict_token_assets(
    token: str,
    assets_by_base: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Match only an exact basename (after removing the PathID suffix)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for variant in _token_variants(token):
        for asset in assets_by_base.get(variant, []):
            rel = str(asset.get("r") or "").replace("\\", "/")
            if not rel or rel in seen:
                continue
            seen.add(rel)
            out.append(asset)
    return out


def _source_graph_proof(
    graph_path: Path | None,
    assets_by_path: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Read only validated ``uses_icon_asset`` edges from the graph.

    The graph's visual-token bridge is evidence only when its token, path,
    PathID and representation all agree with the current Assets index.
    """
    report: dict[str, Any] = {
        "status": "unavailable",
        "diagnostics": [],
        "validatedEdgeCount": 0,
    }
    if graph_path is None or not graph_path.is_file():
        report["diagnostics"].append({
            "code": "source-graph-unavailable",
            "message": "source graph file is missing",
        })
        return {}, report
    proofs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    try:
        connection = sqlite3.connect(
            f"file:{graph_path.resolve().as_posix()}?mode=ro", uri=True
        )
    except (OSError, sqlite3.Error) as exc:
        report["status"] = "invalid"
        report["diagnostics"].append({
            "code": "source-graph-open-failed",
            "actual": str(exc),
        })
        return {}, report
    try:
        try:
            meta = {
                str(key): str(value or "")
                for key, value in connection.execute("SELECT key, value FROM meta")
            }
        except sqlite3.Error as exc:
            report["status"] = "invalid"
            report["diagnostics"].append({
                "code": "source-graph-metadata-invalid",
                "actual": str(exc),
            })
            return {}, report
        report["schemaVersion"] = meta.get("schemaVersion")
        required_meta = (
            "schemaVersion",
            "language",
            "generated",
            "assetIndexContentSha256",
            "asset_map_scope",
        )
        for key in required_meta:
            if not meta.get(key):
                report["diagnostics"].append({
                    "code": "source-graph-metadata-missing",
                    "field": key,
                })
        if meta.get("schemaVersion") and meta.get("schemaVersion") != SOURCE_GRAPH_SCHEMA_VERSION:
            report["diagnostics"].append({
                "code": "source-graph-schema-mismatch",
                "expected": SOURCE_GRAPH_SCHEMA_VERSION,
                "actual": meta.get("schemaVersion"),
            })
        if meta.get("language") and meta.get("language").upper() != "CN":
            report["diagnostics"].append({
                "code": "source-graph-language-mismatch",
                "expected": "CN",
                "actual": meta.get("language"),
            })
        if meta.get("asset_map_scope") and meta.get("asset_map_scope") not in {"full", "relevant"}:
            report["diagnostics"].append({
                "code": "source-graph-asset-map-scope-invalid",
                "expected": "full|relevant",
                "actual": meta.get("asset_map_scope"),
            })
        try:
            generated = int(meta.get("generated") or 0)
            if generated <= 0:
                raise ValueError("generated must be positive")
        except (TypeError, ValueError) as exc:
            report["diagnostics"].append({
                "code": "source-graph-metadata-invalid",
                "field": "generated",
                "actual": str(exc),
            })
        scope = meta.get("asset_map_scope")
        if scope == "relevant":
            for key in ("asset_map_required_path_ids", "asset_map_matched_path_ids"):
                if not meta.get(key):
                    report["diagnostics"].append({
                        "code": "source-graph-metadata-missing",
                        "field": key,
                    })
            try:
                required = int(meta.get("asset_map_required_path_ids") or 0)
                matched = int(meta.get("asset_map_matched_path_ids") or 0)
                if required < 0 or matched < 0 or matched < required:
                    raise ValueError("invalid relevant asset-map coverage")
            except (TypeError, ValueError) as exc:
                report["diagnostics"].append({
                    "code": "source-graph-metadata-invalid",
                    "field": "asset_map_required_path_ids/asset_map_matched_path_ids",
                    "actual": str(exc),
                })

        current_hash = _asset_content_sha256(list(assets_by_path.values()))
        report["assetIndexContentSha256"] = current_hash
        graph_hash = str(meta.get("assetIndexContentSha256") or "").lower()
        if graph_hash and graph_hash != current_hash:
            report["diagnostics"].append({
                "code": "source-graph-stale-assets-index",
                "field": "assetIndexContentSha256",
                "expected": current_hash,
                "actual": graph_hash,
            })

        metadata_valid = not report["diagnostics"]
        rows = connection.execute(
            """
            SELECT e.src, e.dst, e.evidence, e.data, n.path, n.data
            FROM edges AS e
            JOIN nodes AS n ON n.id = e.dst
            WHERE e.kind = 'uses_icon_asset' AND n.kind = 'asset'
            ORDER BY e.src, e.dst
            """
        )
        for src, dst, evidence, edge_data, node_path, node_data in rows:
            try:
                edge = json.loads(edge_data or "{}")
            except (TypeError, ValueError) as exc:
                report["diagnostics"].append({
                    "code": "source-graph-edge-json-invalid",
                    "src": str(src),
                    "dst": str(dst),
                    "actual": str(exc),
                })
                continue
            token = _clean_token(edge.get("token"))
            edge_path = str(edge.get("assetPath") or "").replace("\\", "/")
            graph_node_path = str(node_path or "").replace("\\", "/")
            if edge_path and graph_node_path and edge_path.lower() != graph_node_path.lower():
                continue
            path = graph_node_path or edge_path
            asset = assets_by_path.get(path.lower())
            if not token or asset is None:
                continue
            try:
                node = json.loads(node_data or "{}")
            except (TypeError, ValueError) as exc:
                report["diagnostics"].append({
                    "code": "source-graph-node-json-invalid",
                    "src": str(src),
                    "dst": str(dst),
                    "actual": str(exc),
                })
                continue
            graph_pid = str(node.get("pid") or "").lower()
            asset_pid = str(asset.get("pid") or "").lower()
            graph_representation = str(
                edge.get("representation") or _asset_representation({"r": path})
            ).lower()
            if (
                _asset_base_name(path) != token
                or not graph_pid
                or graph_pid != asset_pid
                or graph_representation != _asset_representation(asset)
            ):
                continue
            if not metadata_valid:
                continue
            proofs[token].append({
                "source": "source_graph",
                "edgeKind": "uses_icon_asset",
                "src": str(src),
                "dst": str(dst),
                "evidence": str(evidence or ""),
                "rel": path,
                "pathId": str(asset.get("pid") or ""),
                "representation": _asset_representation(asset),
            })
    except sqlite3.Error as exc:
        report["status"] = "invalid"
        report["diagnostics"].append({
            "code": "source-graph-query-failed",
            "actual": str(exc),
        })
        return {}, report
    finally:
        connection.close()
    if report["diagnostics"]:
        report["status"] = "stale" if any(
            item.get("code") == "source-graph-stale-assets-index"
            for item in report["diagnostics"]
        ) else "invalid"
    else:
        report["status"] = "validated"
    report["validatedEdgeCount"] = sum(len(rows) for rows in proofs.values())
    return dict(proofs), report


def _token_candidates(entry: dict[str, Any]) -> list[str]:
    values: list[Any] = [entry.get("id"), entry.get("iconId"), entry.get("iconCompositeId"), entry.get("modelKey")]
    model_path = str(entry.get("modelPath") or "").replace("\\", "/")
    if model_path:
        values.append(Path(model_path).stem)
    # The playable administrator record is a gender-agnostic wrapper, while
    # its authored skill/potential rows use the two concrete portrait IDs.
    if _clean_token(entry.get("id")) == "chr_9000_endmin":
        values.extend(("chr_0002_endminm", "chr_0003_endminf"))
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _clean_token(value)
        if not token or token in seen or len(token) < 4:
            continue
        seen.add(token)
        out.append(token)
    return out


def _entry_icon_tokens(entry: dict[str, Any]) -> list[str]:
    """Return direct authored icon IDs, which require strict asset joins."""
    out: list[str] = []
    seen: set[str] = set()
    for key in ("iconId", "iconCompositeId"):
        token = _clean_token(entry.get(key))
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _nested_asset_tokens(entry: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    for group in entry.get("skillGroups") or []:
        if isinstance(group, dict):
            values.append(group.get("iconId"))
    for group in entry.get("talentGroups") or []:
        if not isinstance(group, dict):
            continue
        for level in group.get("levels") or []:
            if isinstance(level, dict):
                values.append(level.get("iconId"))
    for talent in entry.get("talents") or []:
        if isinstance(talent, dict):
            values.append(talent.get("iconId"))
    for level in (entry.get("potentials") or {}).get("levels") or []:
        if not isinstance(level, dict):
            continue
        values.append(level.get("unlockCardTopicItem"))
        values.extend(level.get("unlockCharPictureItemList") or [])

    def collect_material_items(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if key in MATERIAL_ITEM_LIST_KEYS:
                    rows = nested if isinstance(nested, list) else [nested]
                    for row in rows:
                        item_id = row.get("id") if isinstance(row, dict) else row
                        token = _clean_token(item_id)
                        if token.startswith("item_"):
                            values.append(token)
                collect_material_items(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_material_items(nested)

    collect_material_items(entry)
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _clean_token(value)
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _buff_icon_candidates(gameplay_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Collect verified raw buff icon references without traversing opaque data."""
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    buffs = gameplay_payload.get("buffs")
    if not isinstance(buffs, dict):
        return out
    for owner, buff in buffs.items():
        if not isinstance(buff, dict) or buff.get("idStringVerified") is not True:
            continue
        refs = buff.get("refs")
        if not isinstance(refs, list):
            continue
        source = buff.get("source") if isinstance(buff.get("source"), dict) else {}
        for ref in refs:
            token = _clean_token(ref)
            if token.startswith("icon_"):
                out[token].append({
                    "owner": str(owner),
                    "rawToken": str(ref),
                    "sourcePath": str(source.get("path") or ""),
                })
    for rows in out.values():
        rows.sort(key=lambda row: (row["owner"], row["rawToken"], row["sourcePath"]))
    return out


def _token_pattern(tokens: Iterable[str]) -> re.Pattern[str] | None:
    escaped = sorted({_clean_token(token) for token in tokens if _clean_token(token)}, key=len, reverse=True)
    if not escaped:
        return None
    # Underscores are deliberately treated as separators.  Use a zero-width
    # lookahead so a prefixed nested token such as
    # `pic_1_chr_0017_yvonne` indexes under both `pic_1_...` and the owning
    # character id instead of consuming the latter match.
    return re.compile(r"(?=(?<![a-z0-9])(" + "|".join(re.escape(token) for token in escaped) + r")(?![a-z0-9]))", re.IGNORECASE)


def _source_rank(rel: str) -> int:
    source = rel.split("/", 1)[0].lower()
    return 0 if source == "streamingassets" else 1 if source == "persistent" else 2


def _asset_dimensions(asset: dict[str, Any]) -> tuple[int, int] | None:
    """Return indexed pixel dimensions, keeping compatibility with fixtures."""
    try:
        width = int(asset.get("iw") or asset.get("width") or asset.get("w") or 0)
        height = int(asset.get("ih") or asset.get("height") or 0)
    except (TypeError, ValueError):
        return None
    return (width, height) if width > 0 and height > 0 else None


def _asset_area(asset: dict[str, Any]) -> int:
    dimensions = _asset_dimensions(asset)
    if dimensions:
        return dimensions[0] * dimensions[1]
    try:
        return int(asset.get("s") or 0)
    except (TypeError, ValueError):
        return 0


def _resolution_rank(asset: dict[str, Any]) -> tuple[int, int, int]:
    dimensions = _asset_dimensions(asset) or (0, 0)
    return (-_asset_area(asset), -dimensions[0], -dimensions[1])


def _is_squareish(asset: dict[str, Any]) -> bool:
    dimensions = _asset_dimensions(asset)
    if not dimensions:
        # Older hand-built indexes have no dimensions; preserve their semantic
        # ordering and let file size remain the fallback resolution signal.
        return True
    width, height = dimensions
    ratio = width / height if height else 0
    return 0.625 <= ratio <= 1.6


def _icon_shape_rank(asset: dict[str, Any]) -> tuple[int, float]:
    dimensions = _asset_dimensions(asset)
    if not dimensions:
        return (0, 0.0)
    width, height = dimensions
    ratio = width / height if height else 0
    shape_rank = 0 if 0.625 <= ratio <= 1.6 else 1
    aspect_delta = abs(width - height) / max(width, height)
    return (shape_rank, aspect_delta)


def _asset_identity(asset: dict[str, Any]) -> str:
    content_hash = str(asset.get("h") or "").strip().lower()
    if content_hash:
        return f"hash:{content_hash}"
    return str(asset.get("r") or "").replace("\\", "/")


def _asset_rank(asset: dict[str, Any], kind: str, token: str) -> tuple[Any, ...]:
    rel = str(asset.get("r") or "").replace("\\", "/")
    lower = rel.lower()
    category = str(asset.get("ic") or "").lower()
    preferred_categories = IMAGE_CATEGORIES_BY_KIND.get(kind, ())
    category_rank = preferred_categories.index(category) if category in preferred_categories else len(preferred_categories) + 2
    directory_rank = 0 if "/sprite/" in lower else 1 if "/texture2d/" in lower else 2
    exact_rank = 0 if _asset_base_name(rel) == token else 1
    shape_rank = _icon_shape_rank(asset)
    material_rank = 1 if asset.get("mt") else 0
    # Category is the semantic gate; within one category choose the largest
    # original pixel dimensions before source/directory tie-breakers.  This is
    # important when StreamingAssets and Persistent both contain the same
    # logical icon at different resolutions.
    if kind in DISPLAY_ICON_KINDS:
        return (category_rank, material_rank, *shape_rank, *_resolution_rank(asset), _source_rank(rel), directory_rank, exact_rank, rel)
    return (category_rank, material_rank, *_resolution_rank(asset), _source_rank(rel), directory_rank, exact_rank, rel)


def _model_rank(asset: dict[str, Any], token: str) -> tuple[int, int, int, str]:
    rel = str(asset.get("r") or "").replace("\\", "/")
    lower = rel.lower()
    exact_rank = 0 if _asset_base_name(rel) == token else 1
    preview_rank = 0 if asset.get("p") else 1
    animator_rank = 0 if "/animator/" in lower else 1
    return (_source_rank(rel), exact_rank + preview_rank, animator_rank, rel)


def _nested_image_rank(asset: dict[str, Any], token: str) -> tuple[Any, ...]:
    rel = str(asset.get("r") or "").replace("\\", "/")
    lower = rel.lower()
    category = str(asset.get("ic") or "").lower()
    topic_token = token.startswith("item_topic_") or token.startswith("business_card_topic_")
    if token.startswith("facskill_"):
        category_rank = 0 if category == "factory_skill" else 1
    elif token.startswith("icon_"):
        category_rank = 0 if category == "icon" else 1
    elif token.startswith("pic_") or token.startswith("item_pic_"):
        category_rank = 0 if category == "character" else 1
    elif topic_token:
        category_rank = 0 if category == "business_card" else 1
    else:
        category_rank = 0
    shape_rank = _icon_shape_rank(asset)
    material_rank = 1 if asset.get("mt") else 0
    directory_rank = 0 if "/sprite/" in lower else 1 if "/texture2d/" in lower else 2
    exact_rank = 0 if _asset_base_name(rel) == token else 1
    # A topic token often has a tiny blurred thumbnail next to the authored
    # full card. Prefer the original card before aspect/resolution ranking.
    blur_rank = 1 if topic_token and "_blur" in _asset_base_name(rel) else 0
    if topic_token:
        return (
            category_rank,
            material_rank,
            blur_rank,
            *_resolution_rank(asset),
            _source_rank(rel),
            directory_rank + exact_rank,
            rel,
        )
    return (
        category_rank,
        material_rank,
        (0, 0.0) if _is_item_picture_token(token) else shape_rank,
        *_resolution_rank(asset),
        _source_rank(rel),
        directory_rank + exact_rank,
        rel,
    )


def _is_character_full_image(asset: dict[str, Any]) -> bool:
    if str(asset.get("ic") or "").lower() != "chr_thumb":
        return False
    dimensions = _asset_dimensions(asset)
    if not dimensions:
        # The pre-dimension sidecar used the largest chr_thumb as the full
        # portrait fallback; retain that behavior for small test/legacy maps.
        return True
    width, height = dimensions
    ratio = width / height if height else 0
    # The lower ratio bound is 0.5, not the "vertical" crop group's 0.85: a
    # large (>=800px), moderately tall export (e.g. 1182x1992, ratio ~0.59)
    # is still the same full-body illustration as the square portrait, just
    # cropped a little tighter — not the narrow ~0.15-0.3 ratio banner strip
    # every character also exports for the "vertical" role. Left at 0.6, a
    # crop like that would dodge the full-portrait dedup below, get bucketed
    # as "vertical", and then outrank the real (smaller) banner strip on
    # resolution alone.
    return min(width, height) >= 800 and 0.5 <= ratio <= 1.6


def _character_crop_group(asset: dict[str, Any]) -> str:
    dimensions = _asset_dimensions(asset)
    if not dimensions:
        return "neutral"
    width, height = dimensions
    ratio = width / height if height else 0
    if ratio < 0.85:
        return "vertical"
    if ratio > 1.45:
        return "horizontal"
    return "neutral"


def _is_undersized_neutral_crop(asset: dict[str, Any]) -> bool:
    # Alongside the ground-shadow blob, several characters also export a
    # small solid-color reveal/teaser silhouette (no reliable name marker —
    # it shares the `chr_<id>_p<hash>` pattern with real crops). It happens
    # to be roughly square, so once a duplicate full portrait is no longer
    # eligible for the "neutral" role it can become the only remaining
    # candidate there. A genuine neutral pose/alt-art illustration is sized
    # to be its own thumbnail; nothing legitimate in this dataset is both
    # squarish *and* this small, so gate the neutral role on size.
    dimensions = _asset_dimensions(asset)
    if not dimensions:
        return False
    width, height = dimensions
    return min(width, height) < 500


def _character_image_rank(asset: dict[str, Any]) -> tuple[Any, ...]:
    rel = str(asset.get("r") or "").replace("\\", "/")
    return (*_resolution_rank(asset), _source_rank(rel), rel)


def _dedupe_asset_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for asset in candidates:
        identity = _asset_identity(asset)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        out.append(asset)
    return out


def _is_ground_shadow_asset(asset: dict[str, Any], token: str) -> bool:
    # Every character has a `<id>_s_p<hash>` ground-shadow blob (a blurred
    # silhouette meant to sit under the model in 3D scenes). It shares the
    # chr_thumb category and is often squarish, so unfiltered it can win the
    # "neutral" gallery slot for characters that lack a second illustration
    # (e.g. a single-art operator with no alternate/elite pose) and shows up
    # as a stray dark blob instead of art. It never belongs in the gallery.
    rel = str(asset.get("r") or "")
    return _asset_base_name(rel) == f"{token}_s"


def _select_single_identity_images(
    portrait_assets: list[dict[str, Any]],
    limit: int,
    group_order: tuple[str, ...] = ("vertical", "horizontal", "neutral"),
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append(asset: dict[str, Any] | None) -> None:
        if not asset or len(selected) >= limit:
            return
        identity = _asset_identity(asset)
        if not identity or identity in seen:
            return
        seen.add(identity)
        selected.append(asset)

    full = [asset for asset in portrait_assets if _is_character_full_image(asset)]
    full.sort(key=_character_image_rank)
    append(full[0] if full else None)
    # The "full portrait" role is filled at most once. A second asset that
    # independently qualifies as full-portrait-shaped is usually the same
    # illustration exported at another crop/resolution (or, at best, a
    # duplicate-looking alt piece) — showing both reads as a repeated image
    # rather than a useful second thumbnail, so only the higher-resolution
    # one (picked above) survives.
    has_full_portrait = bool(full)

    # Fill the remaining slots with the highest-resolution original vertical
    # and horizontal transparent crops, then the best neutral crop/pose.
    for group in group_order:
        group_candidates = [
            asset for asset in portrait_assets
            if asset not in selected
            and _character_crop_group(asset) == group
            and not (has_full_portrait and _is_character_full_image(asset))
            and not (group == "neutral" and _is_undersized_neutral_crop(asset))
        ]
        group_candidates.sort(key=_character_image_rank)
        append(group_candidates[0] if group_candidates else None)

    if len(selected) < limit:
        # Only reached when a semantic group above had no candidate at all.
        # Still skip crop groups that are already represented: the leftovers
        # within a filled group are lower-resolution or alternate-source
        # exports of the same crop (e.g. a second horizontal face banner),
        # not a distinct role, so let a later, genuinely different group
        # fill the slot instead of doubling up.
        filled_groups = {_character_crop_group(asset) for asset in selected}
        fallback = sorted(
            (
                asset for asset in portrait_assets
                if asset not in selected
                and not (has_full_portrait and _is_character_full_image(asset))
                and not (
                    _character_crop_group(asset) == "neutral"
                    and _is_undersized_neutral_crop(asset)
                )
            ),
            key=lambda asset: _asset_rank(asset, "character", ""),
        )
        for asset in fallback:
            if len(selected) >= limit:
                break
            group = _character_crop_group(asset)
            if group in filled_groups:
                continue
            before = len(selected)
            append(asset)
            if len(selected) > before:
                filled_groups.add(group)
            if len(selected) >= limit:
                break
    return selected[:limit]


def _select_character_images(
    candidates: list[tuple[dict[str, Any], str]],
    limit: int,
) -> list[dict[str, Any]]:
    # The opening strip is the original character portrait gallery. Keep it
    # separate from the unlockable pic_1/pic_3/pic_5 potential images; those
    # remain available in the potential cards through their own token refs.
    portrait_candidates = [
        (asset, token) for asset, token in candidates
        if str(asset.get("ic") or "").lower() == "chr_thumb"
        and not _is_ground_shadow_asset(asset, token)
    ]
    # Each asset is tagged with whichever id token matched it. Most entries
    # resolve to a single identity, but a wrapper entry like the playable
    # Administrator (chr_9000_endmin) matches two concrete portrait ids —
    # one per gender (see `_token_candidates`).
    identities = sorted({token for _asset, token in portrait_candidates})
    if len(identities) > 1:
        # Give every identity its own full role budget (full portrait +
        # vertical + horizontal + neutral) instead of splitting one shared
        # budget across them — splitting would let plain resolution ranking
        # hand every slot to a single identity, and even an even split still
        # forces each identity to skip one of its roles (e.g. no vertical
        # crop) purely because of the shared cap. The Administrator's two
        # gender portraits are the only entries this affects today, so the
        # combined gallery ends up with each gender's full set (typically
        # full + vertical + horizontal) back to back.
        selected: list[dict[str, Any]] = []
        for identity in identities:
            group = _dedupe_asset_candidates(
                asset for asset, token in portrait_candidates if token == identity
            )
            selected.extend(_select_single_identity_images(group, limit))
        return selected

    portrait_assets = _dedupe_asset_candidates(asset for asset, _token in portrait_candidates)
    return _select_single_identity_images(portrait_assets, limit)


def _weapon_image_role(asset: dict[str, Any]) -> str:
    """Classify the two authored weapon image roles.

    Every weapon currently has a small square inventory icon and one weapon
    illustration.  Unity exports the illustration twice: once as a tightly
    cropped Sprite and once on a common 1024x2048 Texture2D canvas.  The
    illustration's crop can be horizontal, vertical, or nearly square, so its
    aspect ratio alone must not create a third gallery slot.
    """
    dimensions = _asset_dimensions(asset)
    if not dimensions:
        return "illustration"
    width, height = dimensions
    ratio = width / height if height else 0
    rel = str(asset.get("r") or "").replace("\\", "/").lower()
    if 0.8 <= ratio <= 1.25 and ("/texture2d/" in rel or max(width, height) <= 300):
        return "icon"
    return "illustration"


def _weapon_illustration_rank(asset: dict[str, Any]) -> tuple[Any, ...]:
    rel = str(asset.get("r") or "").replace("\\", "/")
    lower = rel.lower()
    # Prefer Unity's tightly cropped Sprite over the same artwork on the
    # common transparent Texture2D canvas.  Source and resolution remain
    # deterministic fallbacks for incomplete/older indexes.
    crop_rank = 0 if "/sprite/" in lower else 1
    return (_source_rank(rel), crop_rank, *_resolution_rank(asset), rel)


def _select_weapon_images(
    candidates: list[tuple[dict[str, Any], str]],
    weapon_id: str,
) -> list[dict[str, Any]]:
    """Keep the best icon and illustration belonging to one weapon.

    Model paths can legitimately alias a differently named prefab.  Those
    aliases are useful for model lookup but are not image ownership evidence;
    only candidates matched through the entry's own weapon id may contribute
    to its gallery.
    """
    assets = _dedupe_asset_candidates(
        asset
        for asset, token in candidates
        if token == weapon_id
        and str(asset.get("ic") or "").lower() == "weapon"
        and not asset.get("mt")
    )
    icons = [asset for asset in assets if _weapon_image_role(asset) == "icon"]
    illustrations = [asset for asset in assets if _weapon_image_role(asset) == "illustration"]
    illustrations.sort(key=_weapon_illustration_rank)
    return [group[0] for group in (icons, illustrations) if group]


def _path_ref(asset: dict[str, Any]) -> dict[str, Any]:
    result = {
        "rel": str(asset.get("r") or "").replace("\\", "/"),
        "kind": str(asset.get("k") or ""),
    }
    for source_key, output_key in (("ic", "category"), ("p", "previewRel"), ("pid", "pathId")):
        value = asset.get(source_key)
        if value not in (None, ""):
            result[output_key] = str(value).replace("\\", "/")
    dimensions = _asset_dimensions(asset)
    if dimensions:
        result["width"], result["height"] = dimensions
    return result


def build_gameplay_asset_refs(
    gameplay_payload: dict[str, Any],
    asset_entries: Iterable[dict[str, Any]],
    *,
    max_images: int = 4,
    max_models: int = 3,
    source_graph_path: Path | None = None,
) -> dict[str, Any]:
    """Return representative image/model refs keyed by ``kind:id``.

    Matching is identifier-based and intentionally bounded.  A path is not
    treated as proof that a texture is a UI portrait; category and directory
    preference only choose a useful preview among exported candidates.
    """
    entries = [entry for entry in gameplay_payload.get("entries") or [] if isinstance(entry, dict)]
    assets_list = [asset for asset in asset_entries if isinstance(asset, dict)]
    tokens_by_key: dict[str, list[str]] = {}
    nested_tokens: set[str] = set()
    raw_buff_icon_candidates = _buff_icon_candidates(gameplay_payload)
    icon_tokens: set[str] = set(raw_buff_icon_candidates)
    all_tokens: set[str] = set()
    for entry in entries:
        key = f"{entry.get('kind', '')}:{entry.get('id', '')}"
        tokens = _token_candidates(entry)
        if not key.endswith(":") and tokens:
            tokens_by_key[key] = tokens
            all_tokens.update(tokens)
        entry_nested_tokens = _nested_asset_tokens(entry)
        nested_tokens.update(entry_nested_tokens)
        icon_tokens.update(
            token for token in entry_nested_tokens
            if token.startswith("icon_") or token.startswith("facskill_")
        )
    nested_tokens.update(icon_tokens)
    for token in nested_tokens:
        all_tokens.update(_token_variants(token))

    pattern = _token_pattern(all_tokens)
    assets_by_token: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if pattern:
        for asset in assets_list:
            rel = str(asset.get("r") or "").replace("\\", "/")
            if not rel:
                continue
            base = _asset_base_name(rel)
            for match in pattern.finditer(base):
                token = match.group(1).lower()
                assets_by_token[token].append(asset)

    assets_by_base: dict[str, list[dict[str, Any]]] = defaultdict(list)
    assets_by_path: dict[str, dict[str, Any]] = {}
    for asset in assets_list:
        rel = str(asset.get("r") or "").replace("\\", "/")
        if not rel:
            continue
        assets_by_base[_asset_base_name(rel)].append(asset)
        assets_by_path[rel.lower()] = asset
    source_proofs, source_graph_report = _source_graph_proof(source_graph_path, assets_by_path)

    output: dict[str, dict[str, list[dict[str, Any]]]] = {}
    matched_images = 0
    matched_models = 0
    for entry in entries:
        key = f"{entry.get('kind', '')}:{entry.get('id', '')}"
        tokens = tokens_by_key.get(key) or []
        if not tokens:
            continue
        kind = str(entry.get("kind") or "")
        direct_icon_tokens = _entry_icon_tokens(entry)
        strict_icon_rels = {
            str(asset.get("r") or "").replace("\\", "/")
            for token in direct_icon_tokens
            for asset in _strict_token_assets(token, assets_by_base)
            if str(asset.get("k") or "") == "image"
        }
        candidates: list[tuple[dict[str, Any], str]] = []
        seen: set[str] = set()
        for token in tokens:
            for asset in assets_by_token.get(token, []):
                rel = str(asset.get("r") or "").replace("\\", "/")
                if not rel or rel in seen:
                    continue
                if str(asset.get("k") or "") == "image" and direct_icon_tokens:
                    if strict_icon_rels:
                        if rel not in strict_icon_rels:
                            continue
                    elif token in direct_icon_tokens:
                        continue
                seen.add(rel)
                candidates.append((asset, token))
        image_candidates = [item for item in candidates if str(item[0].get("k") or "") == "image"]
        model_candidates = [item for item in candidates if str(item[0].get("k") or "") == "model"]
        if direct_icon_tokens and not strict_icon_rels and kind in DISPLAY_ICON_KINDS:
            image_candidates = []
        image_candidates.sort(key=lambda item: _asset_rank(item[0], kind, item[1]))
        model_candidates.sort(key=lambda item: _model_rank(item[0], item[1]))
        if kind == "character":
            selected_images = _select_character_images(image_candidates, max(0, max_images))
        elif kind == "weapon":
            selected_images = _select_weapon_images(image_candidates, _clean_token(entry.get("id")))
        elif kind == "enemy":
            # Enemy exports commonly contain 256px/128px Texture2D copies and
            # their cropped Sprite counterparts. The semantic/resolution rank
            # already puts the best original first; keep that one image only.
            selected_images = _dedupe_asset_candidates(asset for asset, _token in image_candidates[:1])
        elif kind in DISPLAY_ICON_KINDS:
            selected_images = _dedupe_asset_candidates(asset for asset, _token in image_candidates[:1])
        else:
            selected_images = _dedupe_asset_candidates(asset for asset, _token in image_candidates[:max(0, max_images)])
        images = [_path_ref(asset) for asset in selected_images]
        models = [_path_ref(asset) for asset, _token in model_candidates[:max(0, max_models)]]
        if images or models:
            output[key] = {"images": images, "models": models}
            matched_images += bool(images)
            matched_models += bool(models)

    token_output: dict[str, dict[str, list[dict[str, Any]]]] = {}
    token_evidence: dict[str, dict[str, Any]] = {}
    evidence_counts: defaultdict[str, int] = defaultdict(int)
    for token in sorted(nested_tokens):
        strict_candidates = _strict_token_assets(token, assets_by_base)
        broad_candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        for variant in _token_variants(token):
            for asset in assets_by_token.get(variant, []):
                rel = str(asset.get("r") or "").replace("\\", "/")
                if not rel or rel in seen or str(asset.get("k") or "") != "image":
                    continue
                seen.add(rel)
                broad_candidates.append(asset)
        strict_candidates = [
            asset for asset in strict_candidates
            if str(asset.get("k") or "") == "image"
        ]
        strict_candidates.sort(key=lambda asset: _nested_image_rank(asset, _token_variants(token)[-1]))
        broad_candidates.sort(key=lambda asset: _nested_image_rank(asset, _token_variants(token)[-1]))
        if strict_candidates:
            classification = (
                "exact-unique" if len(strict_candidates) == 1
                else "representation-pathid-multi"
            )
            evidence_candidates = strict_candidates
        elif broad_candidates:
            classification = "basename-only"
            evidence_candidates = broad_candidates
        else:
            classification = "unresolved"
            evidence_candidates = []
        evidence_counts[classification] += 1
        proof_rows = source_proofs.get(_clean_token(token), [])
        proof_validated = source_graph_report.get("status") == "validated" and bool(proof_rows)
        candidate_refs = [_path_ref(asset) for asset in evidence_candidates]
        strict_rel = {
            str(asset.get("r") or "").replace("\\", "/")
            for asset in strict_candidates
        }
        rejected_refs = [
            _path_ref(asset) for asset in broad_candidates
            if str(asset.get("r") or "").replace("\\", "/") not in strict_rel
        ]
        preview = candidate_refs[0] if candidate_refs else None
        # The selected Texture2D is a display policy, not source evidence.
        for candidate in candidate_refs:
            if candidate.get("rel", "").lower().split("/")[1:2] == ["texture2d"]:
                preview = candidate
                break
        token_evidence[token] = {
            "classification": classification,
            "assetResolution": {
                "classification": classification,
                "candidates": candidate_refs,
                "rejectedBasenameCandidates": rejected_refs,
                "preview": preview,
                "representationPolicy": "Texture2D" if preview else None,
            },
            "candidates": candidate_refs,
            "rejectedBasenameCandidates": rejected_refs,
            "sourceProof": {
                "status": "validated" if proof_validated else "unproven",
                "edges": proof_rows,
                "diagnostics": list(source_graph_report.get("diagnostics") or [])
                + ([] if proof_rows else [{
                    "code": "source-proof-not-validated",
                    "token": token,
                }]),
            },
            "proofStatus": "validated" if proof_validated else "unproven",
            "preview": preview,
            "representationPolicy": "Texture2D" if preview else None,
        }
        # One canonical icon per token avoids Sprite/Texture2D duplicates in
        # chips and skill headers.  The rank above prefers the highest original
        # resolution while keeping square icon sources together.  This preview
        # choice deliberately does not upgrade the evidence classification.
        max_token_images = 1
        images = [_path_ref(asset) for asset in strict_candidates[:max_token_images]]
        if images:
            texture_images = [
                image for image in images
                if image.get("rel", "").lower().split("/")[1:2] == ["texture2d"]
            ]
            if texture_images:
                images = texture_images[:max_token_images]
            token_output[token] = {"images": images}

    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": "identifier-matched exported asset index",
        "counts": {
            "entries": len(entries),
            "matchedEntries": len(output),
            "withImages": matched_images,
            "withModels": matched_models,
            "tokenRefs": len(token_output),
            "tokenEvidence": len(token_evidence),
            "iconEvidence": len(icon_tokens),
            "evidenceClassifications": dict(sorted(evidence_counts.items())),
        },
        "entries": output,
        "tokens": token_output,
        "tokenEvidence": token_evidence,
        "sourceGraph": source_graph_report,
        "rawBuffIconCandidates": {
            token: rows for token, rows in sorted(raw_buff_icon_candidates.items())
        },
        "iconEvidence": {
            token: token_evidence[token]
            for token in sorted(icon_tokens)
            if token in token_evidence
        },
    }


def build_from_paths(
    gameplay_path: Path,
    asset_index_path: Path,
    output_path: Path = DEFAULT_OUTPUT,
    source_graph_path: Path | None = None,
) -> dict[str, Any]:
    gameplay = read_json(gameplay_path, {})
    asset_index = read_json(asset_index_path, {})
    if not isinstance(gameplay, dict):
        raise FileNotFoundError(f"Gameplay payload is missing or invalid: {gameplay_path}")
    if not isinstance(asset_index, dict):
        raise FileNotFoundError(f"Asset index is missing or invalid: {asset_index_path}")
    if source_graph_path is None:
        # The source graph is optional because the normal WebUI phase may run
        # before graph rebuild.  When present, it contributes proof only.
        repo_root = asset_index_path.resolve().parents[3]
        candidate_graph = repo_root / "reports" / "source_graph" / "endfield_source_graph.sqlite"
        source_graph_path = candidate_graph if candidate_graph.is_file() else None
    payload = build_gameplay_asset_refs(
        gameplay,
        asset_index.get("entries") or [],
        source_graph_path=source_graph_path,
    )
    payload["sourcePath"] = str(asset_index_path).replace("\\", "/")
    write_json(output_path, payload, trailing_newline=True)
    return payload
