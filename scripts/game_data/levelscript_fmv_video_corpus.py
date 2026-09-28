"""Join authenticated LevelScript FMV ids to current Video VFS files.

The reviewed native contract pins the selected name-resolution route. This
gate never infers playback or mission order from matching file names.

It is a selected-native plus current VFS byte gate: each stored LevelScript
``moviePath`` resolves to an exact base Video path or a complete gendered
pair under the contract's two reviewed name prefixes. Runtime playback stays
unresolved. ``--cursor`` and ``--replay`` name the LevelScript cursor and
replay reports the join reads (defaults under ``reports/game_data/`` and
``reports/animestudio/``); pass the VFS audit's
``--expected-input-set-sha256``. The default report is
``reports/story/recovery/current_levelscript_fmv_video_join.json``.

Source side: the ``PlayFmvAction`` layout in ``levelscript_union_tags.json``
and the strict ``codecs/levelscript/fmv.py`` decoder identify ``_moviePath``
as a stored constant ``Param<string>``, read inside that action's own physical
byte range, never inferred from a neighboring action. Each source is rechecked
by export SHA256 and VFS data MD5. A ``cs_video_*`` id resolves to a base
``<id>.usm`` or to one ``f_<id>`` and one ``m_<id>`` file under
``Data/Video/PC/Narrative/Cutscene/``; a missing base or an incomplete gender
pair fails rather than promoting a name match.

Native side (``levelscript_fmv_video_native.json``, unpatched bodies):
``PlayFmvAction.Execute`` reads ``_moviePath`` and calls ``GameAction.PlayFmv``
(the route also listed in ``cinematic_queue.json``). That forwards the name to
``NarrativeUtils.GetGenderedFMVId``, which prefixes literal ``f_`` or ``m_`` by
narrative gender, checks the candidate with ``_CheckIfFMVExists`` and falls
back to the unprefixed id; it then checks a ``GetCSVideoAssetSubPath`` result
(``Narrative/Cutscene/{0}``) with ``VideoManager.CheckCanPlay``.
``VideoManager.GetVideoAssetPath`` appends ``.usm`` when needed, and
``TryGetVideoPlayFullPath`` calls
``Beyond.VFS.VirtualFileSystem.TryGetAssetFullPathInfo``.

This is ``conditional`` source-to-video name resolution: selected gender,
iFix patch state, action activation, playback, mission ownership and order
are not proved by static bytes or VFS matches.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file, write_report_json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.repo_paths import REPO_ROOT


ROOT = REPO_ROOT
SCHEMA = "endfield.levelscript-fmv-video-native-contract.v1"
REPORT_SCHEMA = "endfield.levelscript-fmv-video-join.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_fmv_video_native.json"
DEFAULT_AUDIT = ROOT / "reports/animestudio/vfs_understanding_latest.json"
DEFAULT_LEDGER = ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"
DEFAULT_CURSOR = ROOT / "reports/game_data/levelscript_fmv_cursor_current.json"
DEFAULT_REPLAY = ROOT / "reports/animestudio/levelscript_fmv_replay_20260927.json"
DEFAULT_NATIVE_PROOF = ROOT / "reports/game_data/levelscript_fmv_native_proof.json"
DEFAULT_EXPORT = ROOT / "export_full"
DEFAULT_REPORT = ROOT / "reports/story/recovery/current_levelscript_fmv_video_join.json"
CONSTANT_TAIL = bytes.fromhex("ffffffff00000000ffffffff")
MOVIE_ID = re.compile(r"[A-Za-z0-9_]+\Z")


class CorpusError(ValueError):
    def __init__(self, check: str, source: str, expected: Any, actual: Any) -> None:
        self.check = check
        self.source = source
        self.expected = expected
        self.actual = actual
        super().__init__(f"{check}: {source}: expected {expected!r}, actual {actual!r}")


def _require(check: str, source: str, expected: Any, actual: Any) -> None:
    if actual != expected:
        raise CorpusError(check, source, expected, actual)


def _digest(data: bytes, name: str) -> str:
    return hashlib.new(name, data).hexdigest().upper()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CorpusError("json_root", str(path), "object", type(value).__name__)
    return value


def _native_gate(contract: dict[str, Any]) -> None:
    _require("contract_schema", str(DEFAULT_CONTRACT), SCHEMA, contract.get("schema"))
    _require("contract_status", str(DEFAULT_CONTRACT), "validated", contract.get("status"))
    _require("contract_boundary", str(DEFAULT_CONTRACT), "conditional", contract.get("evidenceBoundary"))
    pins = contract["nativeInputs"]
    native = check_installed_native_inputs(
        pins["GameAssembly.dll"], pins["global-metadata.dat"]
    )
    _require("native_inputs", str(native.gameassembly), "validated", native.status)
    unity = native.gameassembly.parent / "UnityPlayer.dll"
    _require("unity_player_present", str(unity), True, unity.is_file())
    _require(
        "unity_player_sha256", str(unity), pins["UnityPlayer.dll"].upper(),
        sha256_file(unity).upper(),
    )


def _file_rows(ledger: Path, input_set: str, wanted: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if row.get("recordType") != "file" or row.get("virtualPath") not in wanted:
                continue
            path = row["virtualPath"]
            _require("ledger_unique_path", path, False, path in found)
            _require("ledger_input_set", path, input_set, row.get("inputSetSha256"))
            _require("ledger_status", path, "verified", row.get("status"))
            _require("ledger_boundary", path, "boundary_verified", row.get("boundaryStatus"))
            _require("ledger_path_hash", path, row.get("fileNameHashDeclaredHex"), row.get("fileNameHashRecomputedHex"))
            _require("ledger_data_md5", path, row.get("declaredFileDataMd5LittleEndianHex"), row.get("recomputedFileDataMd5"))
            found[path] = row
    return found


def _source_path(value: str) -> Path:
    posix = PurePosixPath(value)
    if (
        not value.startswith("LevelScriptData/")
        or not value.endswith(".json")
        or "\\" in value
        or posix.is_absolute()
        or ".." in posix.parts
    ):
        raise CorpusError("source_path", value, "LevelScriptData/.../*.json", value)
    return Path(*posix.parts)


def audit(
    *, contract_path: Path = DEFAULT_CONTRACT,
    expected_input_set_sha256: str,
    vfs_audit_path: Path = DEFAULT_AUDIT,
    ledger_path: Path = DEFAULT_LEDGER,
    cursor_path: Path = DEFAULT_CURSOR,
    replay_path: Path = DEFAULT_REPLAY,
    native_proof_path: Path = DEFAULT_NATIVE_PROOF,
    export_root: Path = DEFAULT_EXPORT,
) -> dict[str, Any]:
    contract = _load(contract_path)
    _native_gate(contract)
    vfs = _load(vfs_audit_path)
    cursor = _load(cursor_path)
    replay = _load(replay_path)
    native_proof = _load(native_proof_path)
    input_set = vfs["inputSetSha256"]
    _require("expected_input_set", str(vfs_audit_path), expected_input_set_sha256.upper(), input_set)
    for path, report in ((cursor_path, cursor), (replay_path, replay)):
        _require("input_set", str(path), input_set, report.get("inputSetSha256"))
        _require("report_status", str(path), "validated", report.get("status"))
    _require("native_proof_status", str(native_proof_path), "validated", native_proof.get("status"))
    _require("native_proof_hash", str(native_proof_path), cursor.get("nativeProofSha256"), _digest(native_proof_path.read_bytes(), "sha256"))
    for label, sha in contract["nativeInputs"].items():
        if label in ("GameAssembly.dll", "global-metadata.dat"):
            _require("native_proof_input", label, sha.upper(), native_proof["nativeInputs"].get(label, "").upper())
    rows = cursor.get("rows")
    if not isinstance(rows, list) or not rows:
        raise CorpusError("cursor_rows", str(cursor_path), "nonempty list", type(rows).__name__)
    _require("cursor_count", str(cursor_path), len({row["path"] for row in rows}), cursor.get("filesAdvanced"))

    source = contract["source"]
    resolution = contract["resolution"]
    prefixes = resolution["genderPrefixes"]
    if not isinstance(prefixes, list) or len(prefixes) != 2 or any(
        not isinstance(prefix, str) or not prefix.endswith("_") or not MOVIE_ID.fullmatch(prefix)
        for prefix in prefixes
    ):
        raise CorpusError("gender_prefixes", str(contract_path), "two reviewed name prefixes", prefixes)
    video_path = lambda variant, movie: resolution["vfsLogicalPrefix"] + resolution["videoSubPathFormat"].format(variant + movie) + resolution["videoExtension"]

    wanted = set()
    for row in rows:
        rel = _source_path(row["path"])
        movie = row["moviePath"]["value"]
        if not MOVIE_ID.fullmatch(movie):
            raise CorpusError("movie_id", row["path"], "ASCII alphanumeric or underscore", movie)
        wanted.add("Data/Json/" + rel.as_posix())
        wanted.update(video_path(prefix, movie) for prefix in ("", *prefixes))
    ledger = _file_rows(ledger_path, input_set, wanted)
    joined = []
    for row in rows:
        rel = _source_path(row["path"])
        path = rel.as_posix()
        logical = "Data/Json/" + path
        if logical not in ledger:
            raise CorpusError("source_vfs_missing", logical, "verified file row", None)
        vfs_source = ledger[logical]
        _require("source_block", logical, "JsonData", vfs_source.get("blockName"))
        data = (export_root / "game/Json" / rel).read_bytes()
        _require("source_sha256", path, row["sha256"].upper(), _digest(data, "sha256"))
        _require("source_md5", path, vfs_source["recomputedFileDataMd5"], _digest(data, "md5"))
        _require("source_length", path, vfs_source["length"], len(data))
        start, end = row["actionStart"], row["actionEnd"]
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(data):
            raise CorpusError("action_range", path, "bounded nonempty range", [start, end, len(data)])
        header = bytes.fromhex(source["wireUnionMarkerHex"]) + struct.pack("<HH", source["unionTag"], source["memberCount"])
        _require("action_union_header", path, header.hex(), data[start:start + len(header)].hex())
        movie = row["moviePath"]["value"]
        raw = movie.encode("utf-8")
        _require("movie_path_occurrences", path, 1, data[start:end].count(raw))
        at = data.find(raw, start, end)
        if at < start + 5:
            raise CorpusError("movie_path_field", path, "tagged string within action", at)
        _require("movie_path_tag", path, 4, data[at - 5])
        _require("movie_path_length", path, len(raw), struct.unpack_from("<I", data, at - 4)[0])
        _require("movie_path_constant_tail", path, CONSTANT_TAIL.hex(), data[at + len(raw):at + len(raw) + 12].hex())
        param = row["moviePath"]
        _require("movie_path_id_ref", path, source["constantIdRef"], param["idRef"])
        _require("movie_path_param_source", path, source["constantParamSource"], param["paramSource"])
        _require("movie_path_dynamic_path", path, None, param["path"])
        candidates = []
        for prefix in ("", *prefixes):
            video = video_path(prefix, movie)
            vfs_video = ledger.get(video)
            if vfs_video is None:
                continue
            _require("video_block", video, "Video", vfs_video.get("blockName"))
            candidates.append({
                "variant": "base" if not prefix else prefix[:-1],
                "path": video,
                "length": vfs_video["length"],
                "dataMd5": vfs_video["recomputedFileDataMd5"],
                "fileNameHash": vfs_video["fileNameHashRecomputedHex"],
                "physicalChunkSource": vfs_video["physicalChunkSource"],
            })
        kinds = {item["variant"] for item in candidates}
        variant_kinds = {prefix[:-1] for prefix in prefixes}
        if "base" not in kinds and kinds != variant_kinds:
            raise CorpusError("video_resolution", path, "base file or complete gender pair", sorted(kinds))
        joined.append({
            "source": path,
            "sourceSha256": row["sha256"],
            "sourceMd5": vfs_source["recomputedFileDataMd5"],
            "actionStart": start,
            "actionEnd": end,
            "moviePathFieldOffset": at - 5,
            "moviePath": movie,
            "videoFiles": candidates,
        })
    distinct_movies = len({row["moviePath"] for row in joined})
    return {
        "schema": REPORT_SCHEMA,
        "status": "validated",
        "inputSetSha256": input_set,
        "contractSha256": _digest(contract_path.read_bytes(), "sha256"),
        "cursorSha256": _digest(cursor_path.read_bytes(), "sha256"),
        "replaySha256": _digest(replay_path.read_bytes(), "sha256"),
        "vfsAuditSha256": _digest(vfs_audit_path.read_bytes(), "sha256"),
        "vfsLedgerSha256": _digest(ledger_path.read_bytes(), "sha256"),
        "summary": {
            "sourceActionsAuthenticated": len(joined),
            "uniqueMoviePaths": distinct_movies,
            "baseVideoFiles": sum(any(v["variant"] == "base" for v in row["videoFiles"]) for row in joined),
            "genderVariantPairs": sum({v["variant"] for v in row["videoFiles"]} == variant_kinds for row in joined),
            "videoFilesBoundaryVerified": sum(len(row["videoFiles"]) for row in joined),
        },
        "evidenceBoundary": "conditional name resolution only; no runtime action activation, iFix patch state, selected gender, playback or Story order",
        "rows": joined,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--vfs-audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cursor", type=Path, default=DEFAULT_CURSOR)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--native-proof", type=Path, default=DEFAULT_NATIVE_PROOF)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    try:
        result = audit(
            contract_path=args.contract, expected_input_set_sha256=args.expected_input_set_sha256,
            vfs_audit_path=args.vfs_audit,
            ledger_path=args.ledger, cursor_path=args.cursor,
            replay_path=args.replay, native_proof_path=args.native_proof,
            export_root=args.export_root,
        )
    except (CorpusError, OSError, KeyError, ValueError) as error:
        result = {
            "schema": REPORT_SCHEMA, "status": "failed",
            "firstFailure": (
                {"check": error.check, "source": error.source,
                 "expected": error.expected, "actual": error.actual}
                if isinstance(error, CorpusError) else
                {"check": "load_or_shape", "source": type(error).__name__, "detail": str(error)[:500]}
            ),
        }
    write_report_json(args.report, result)
    if result["status"] != "validated":
        print(f"levelscript_fmv_video_corpus: {result['firstFailure']}")
        return 1
    print(f"levelscript_fmv_video_corpus: validated {result['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
