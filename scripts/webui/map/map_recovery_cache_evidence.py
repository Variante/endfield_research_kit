#!/usr/bin/env python3
"""Content evidence for the map-recovery render caches.

The persistent render cache used to be invalidated by ``size + mtime_ns`` of
every exported OBJ/PNG/Material JSON, of the renderer sidecar and of the 845 MB
asset map.  A ``export.bat --from-game`` run rewrites all of those files even
when the game data did not change, so every scene missed its cache and the full
render was repeated from scratch.

Nothing about that was a real change of input.  The exporter already publishes
content evidence for each of those inputs:

  * every asset-map entry carries ``Hash`` - the XXH64 of the raw Unity object
    bytes (``AssetsHelper.cs``: ``Hash = obj.GetHash()``), which is stable
    across re-exports of unchanged objects;
  * the exported file name ends in ``_p<hex PathID>``, so an exported file can
    be joined back to its asset-map entry without reading the file;
  * each streaming sidecar publishes ``source.files[].packedSha256`` per
    ``InitChunkData`` file plus the ``source.cliSha256`` of the exporter.

This module turns those into render-cache evidence.  It is deliberately
fail-closed: a source that cannot be joined to an asset-map object falls back
to a SHA-256 of the file's own bytes and says so in the payload.  It never
falls back to mtime, and missing evidence is recorded as missing rather than
silently dropped, so it can never turn an unknown input into a cache hit.
"""

from __future__ import annotations
from scripts.common import EXPORT_LAYOUT

import json
import os
import re
from functools import lru_cache
from pathlib import Path

from scripts.repo_paths import REPO_ROOT

ROOT = REPO_ROOT

from scripts.webui.map.audit_map_asset_closure import iter_asset_entries, sha256_file
from scripts.webui.map.map_recovery_sources import projection_streaming_scene

DEFAULT_ASSET_MAP = EXPORT_LAYOUT.asset_map_dir("StreamingAssets") / "endfield_streamingassets_assets.json"
# Lives beside `hlod_grid_index.json`, which keys its own cache the same way.
OBJECT_HASH_INDEX = ROOT / "reports/assets/map_recovery/asset_object_hashes.json"
OBJECT_HASH_SCHEMA = 1

# Only the object types the renderer actually consumes are indexed; indexing
# every type would triple the persisted file for entries nothing reads.
EVIDENCE_TYPES = ("Material", "Mesh", "Texture2D")

UINT64_MASK = (1 << 64) - 1
# AnimeStudio appends `_p<hex PathID>` to every exported file name. Real
# exports use the full 16 hex digits; shorter suffixes are accepted because
# `_path_id_file` also resolves the unpadded form.
_PATH_ID_SUFFIX_RE = re.compile(r"_p([0-9A-Fa-f]{1,16})$")
# Guard the streaming-sidecar prefix scan: `source` is the fourth top-level
# key, so it is always inside the first few megabytes of even a 343 MB sidecar.
_SIDECAR_SOURCE_SCAN_LIMIT = 64 << 20

_OBJECT_INDEX_MEMO: dict[tuple[str, str], dict] = {}
_CONTENT_SHA_MEMO: dict[tuple[str, int, int], str] = {}


def repo_rel(path: Path) -> str:
    """Path as a stable repo-relative POSIX string, so signatures survive moves."""
    resolved = Path(path)
    if resolved.is_absolute() and resolved.is_relative_to(ROOT):
        return resolved.relative_to(ROOT).as_posix()
    return resolved.as_posix()


def path_id_from_export_path(path: Path | str) -> int | None:
    """Recover the unsigned PathID AnimeStudio encoded in an exported file name."""
    matched = _PATH_ID_SUFFIX_RE.search(Path(path).stem)
    return int(matched.group(1), 16) if matched else None


def path_id_key(path_id: int) -> str:
    return f"{path_id & UINT64_MASK:016X}"


@lru_cache(maxsize=8)
def asset_map_sha256(asset_map: Path = DEFAULT_ASSET_MAP) -> str | None:
    """SHA-256 of the asset map, computed once per process (0.6 s for 845 MB)."""
    return sha256_file(asset_map) if Path(asset_map).is_file() else None


def build_object_hash_index(asset_map: Path = DEFAULT_ASSET_MAP) -> dict:
    """One streaming pass: PathID -> ``Type:Hash`` for renderer-consumed types.

    A PathID that resolves to two different ``Type:Hash`` values, or to an
    entry with no published ``Hash``, is ambiguous evidence and is recorded as
    such instead of being indexed - its consumers fall back to hashing the
    exported file itself.
    """
    objects: dict[str, str] = {}
    ambiguous: set[str] = set()
    wanted = set(EVIDENCE_TYPES)
    for entry in iter_asset_entries(asset_map):
        object_type = entry.get("Type")
        if object_type not in wanted:
            continue
        path_id = entry.get("PathID")
        object_hash = entry.get("Hash")
        if not isinstance(path_id, int):
            continue
        key = path_id_key(path_id)
        if not object_hash or not isinstance(object_hash, str):
            ambiguous.add(key)
            continue
        token = f"{object_type}:{object_hash}"
        previous = objects.get(key)
        if previous is None:
            objects[key] = token
        elif previous != token:
            ambiguous.add(key)
    for key in ambiguous:
        objects.pop(key, None)
    return {
        "schemaVersion": OBJECT_HASH_SCHEMA,
        "assetMap": repo_rel(asset_map),
        "assetMapSha256": asset_map_sha256(asset_map),
        "types": list(EVIDENCE_TYPES),
        "objects": objects,
        "ambiguous": sorted(ambiguous),
    }


def _empty_object_index(asset_map: Path, reason: str) -> dict:
    return {
        "schemaVersion": OBJECT_HASH_SCHEMA,
        "assetMap": repo_rel(asset_map),
        "assetMapSha256": None,
        "types": list(EVIDENCE_TYPES),
        "objects": {},
        "ambiguous": [],
        "unavailable": reason,
    }


def _read_object_hash_index(cache: Path, expected_sha256: str) -> dict | None:
    if not cache.is_file():
        return None
    cached = json.loads(cache.read_text(encoding="utf-8"))
    if cached.get("schemaVersion") != OBJECT_HASH_SCHEMA:
        return None
    if cached.get("assetMapSha256") != expected_sha256:
        return None
    if list(cached.get("types") or []) != list(EVIDENCE_TYPES):
        return None
    if not isinstance(cached.get("objects"), dict):
        return None
    return cached


def load_object_hash_index(
    asset_map: Path = DEFAULT_ASSET_MAP,
    cache: Path = OBJECT_HASH_INDEX,
    refresh: bool = False,
) -> dict:
    """Return the PathID -> ``Type:Hash`` index, building it at most once.

    The persisted file is keyed by the asset map's own SHA-256 - the same
    identity `load_hlod_index` uses - so a `--from-game` rewrite that produces
    identical bytes reuses it instead of streaming 845 MB again.
    """
    asset_map = Path(asset_map)
    if not asset_map.is_file():
        return _empty_object_index(asset_map, "assetMapMissing")
    digest = asset_map_sha256(asset_map)
    memo_key = (str(asset_map), str(digest))
    if not refresh and memo_key in _OBJECT_INDEX_MEMO:
        return _OBJECT_INDEX_MEMO[memo_key]
    cached = None if refresh else _read_object_hash_index(cache, digest)
    if cached is None:
        cached = build_object_hash_index(asset_map)
        cache.parent.mkdir(parents=True, exist_ok=True)
        # Worker processes may reach this concurrently after an asset-map
        # change; a PID-unique temporary keeps the replace atomic per writer.
        temporary = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(cached, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        temporary.replace(cache)
    _OBJECT_INDEX_MEMO[memo_key] = cached
    return cached


def content_sha256(path: Path) -> str:
    """SHA-256 of one file, memoized per process by its identity on disk.

    The stat only decides whether this process may reuse its own earlier read
    of the same file; it never reaches the cache signature, so a touched file
    still produces the same evidence and a rewritten one still produces new
    evidence.
    """
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    digest = _CONTENT_SHA_MEMO.get(key)
    if digest is None:
        digest = sha256_file(path)
        _CONTENT_SHA_MEMO[key] = digest
    return digest


def source_evidence(path: Path, index: dict) -> dict:
    """Content evidence for one exported render input.

    Preference order: the asset map's own object hash for the PathID encoded in
    the file name, else a SHA-256 of the file's bytes.  The fallback is named
    in the payload so a signature shows which inputs had no asset-map evidence.

    The object hash identifies the *source* Unity object.  The exported OBJ /
    PNG / Material JSON is a deterministic conversion of it, so the exported
    byte length is carried alongside as a content property of the derived file
    - it is identical across a re-export of unchanged data but changes the
    moment the exported file itself is rewritten with different bytes.  Hashing
    all 56 GB of exported artefacts on every run instead would cost minutes of
    pure I/O per process, which is the cost this join exists to avoid.
    """
    path = Path(path)
    record: dict[str, object] = {"path": repo_rel(path)}
    if not path.is_file():
        record["evidence"] = "missing"
        return record
    record["bytes"] = path.stat().st_size
    path_id = path_id_from_export_path(path)
    if path_id is None:
        record["evidence"] = "contentSha256"
        record["fallback"] = "noPathIdInFileName"
        record["sha256"] = content_sha256(path)
        return record
    key = path_id_key(path_id)
    token = (index.get("objects") or {}).get(key)
    if token:
        record["evidence"] = "assetMapObjectHash"
        record["object"] = token
        return record
    record["evidence"] = "contentSha256"
    if index.get("unavailable"):
        record["fallback"] = str(index["unavailable"])
    elif key in set(index.get("ambiguous") or ()):
        record["fallback"] = "ambiguousPathId"
    else:
        record["fallback"] = "pathIdNotInAssetMap"
    record["sha256"] = content_sha256(path)
    return record


def source_evidence_list(paths, asset_map: Path = DEFAULT_ASSET_MAP) -> list[dict]:
    """Sorted content evidence for a set of exported render inputs."""
    index = load_object_hash_index(asset_map)
    return [source_evidence(path, index) for path in sorted(set(map(Path, paths)), key=str)]


def file_content_evidence(path: Path) -> dict:
    """Content evidence for a source that carries no PathID, e.g. a sidecar index."""
    path = Path(path)
    if not path.is_file():
        return {"path": repo_rel(path), "evidence": "missing"}
    return {"path": repo_rel(path), "evidence": "contentSha256", "sha256": content_sha256(path)}


def _sidecar_source_block(sidecar: Path) -> dict | None:
    """Decode only the leading ``source`` object of a streaming sidecar.

    Sidecars reach 343 MB, so the whole document is never parsed; ``source`` is
    the fourth top-level key and is always inside the scanned prefix.
    """
    decoder = json.JSONDecoder()
    with sidecar.open("r", encoding="utf-8") as stream:
        buffer = ""
        cursor = 0
        while True:
            found = buffer.find('"source"', cursor)
            if found >= 0:
                colon = buffer.find(":", found + len('"source"'))
                start = colon + 1
                # `raw_decode` does not skip leading whitespace of its own.
                while colon >= 0 and start < len(buffer) and buffer[start] in " \t\r\n":
                    start += 1
                if colon >= 0 and start < len(buffer):
                    try:
                        value, _ = decoder.raw_decode(buffer, start)
                    except json.JSONDecodeError:
                        # The object is still truncated; read more and retry.
                        value = None
                    else:
                        if isinstance(value, dict) and "cliSha256" in value:
                            return value
                        cursor = found + len('"source"')
                        continue
                cursor = found
            else:
                cursor = max(0, len(buffer) - len('"source"'))
            chunk = stream.read(1 << 20)
            if not chunk or len(buffer) > _SIDECAR_SOURCE_SCAN_LIMIT:
                return None
            buffer += chunk


@lru_cache(maxsize=256)
def streaming_source_evidence(level_id: str) -> dict:
    """Per-``InitChunkData`` content evidence for a streaming-backed scene.

    The instance geometry a point render rasterizes comes from these packed
    chunk files via ``AnimeStudio.CLI``; ``packedSha256`` and ``cliSha256`` are
    exactly the inputs that decide what the sidecar contains.
    """
    projection = projection_streaming_scene(level_id)
    if not projection:
        return {"evidence": "noStreamingScene"}
    sidecar = projection.get("instanceSource")
    record: dict[str, object] = {"sceneId": projection.get("sceneId")}
    if not isinstance(sidecar, Path) or not sidecar.is_file():
        record["evidence"] = "missingSidecar"
        return record
    block = _sidecar_source_block(sidecar)
    if block is None:
        record["evidence"] = "missingSourceBlock"
        record["sidecar"] = repo_rel(sidecar)
        return record
    files = block.get("files")
    record["evidence"] = "initChunkDataPackedSha256"
    record["sidecar"] = repo_rel(sidecar)
    record["cliSha256"] = block.get("cliSha256")
    record["files"] = sorted(
        [str(row.get("fileName")), str(row.get("packedSha256"))]
        for row in files
        if isinstance(row, dict)
    ) if isinstance(files, list) else None
    return record


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return repo_rel(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda row: str(row[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def binding_relations(bindings: dict | None) -> list:
    """The resolved mesh -> material -> texture relations, as signature evidence.

    These relations are what the asset map (plus the renderer sidecar and the
    WebUI asset index) actually contributes to a render.  Recording the
    resolved relations instead of a whole-asset-map token keeps invalidation
    scene-local: a change to an unrelated object elsewhere in the 845 MB map no
    longer invalidates all 84 scenes, while a change to a relation this scene
    draws still does.
    """
    if not isinstance(bindings, dict):
        return []
    return [[str(key), _jsonable(value)] for key, value in sorted(bindings.items(), key=lambda row: str(row[0]))]
