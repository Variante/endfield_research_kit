"""Audit every current JsonData logical file against the authenticated VFS ledger.

This is the family registry for the JsonData block.  It proves that the
structured export is a byte-for-byte view of every current logical file, then
routes only the families with maintained readers.  A path or MemoryPack member
count never promotes an otherwise unknown payload.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from scripts.game_data.animation_config_binary import (
    AnimationConfigFramingError,
    frame_animation_config,
)
from scripts.game_data.aether_energy_lock_binary import (
    AetherEnergyLockDecodeError,
    decode_aether_energy_lock_table,
)
from scripts.game_data.atmospheric_npc_binary import (
    AtmosphericNpcFramingError,
    frame_atmospheric_npc_table,
)
from scripts.game_data.char_interact_perform_binary import (
    CharInteractPerformDecodeError,
    decode_char_interact_complete_frame,
    frame_char_interact_prefix,
)
from scripts.game_data.interactive_binary import (
    InteractiveBinaryDecodeError,
    decode_interactive_table,
    decode_model_view_state_controller,
)
from scripts.game_data.leveldata_binary import (
    LevelDataTopLevelFramingError,
    frame_leveldata_airwalls_prefix,
    frame_leveldata_empty_tail,
    frame_leveldata_named_prefix,
    frame_leveldata_terminal_suffix,
)
from scripts.game_data.levelconfig_binary import LevelConfigDecodeError, decode_level_config
from scripts.game_data.levelscript_binary import (
    LevelScriptTopLevelFramingError,
    frame_levelscript_action_map_named_prefix,
    frame_levelscript_current_action_sequence_leader_enter,
    frame_levelscript_single_call_server_leader_enter,
    frame_levelscript_empty_action_map_sequential,
    frame_levelscript_null_action_map_sequential,
    frame_levelscript_empty_action_map_prefix,
    frame_levelscript_empty_action_map_top_level,
    frame_levelscript_terminal_suffix,
)
from scripts.game_data.levelscript_template_binary import (
    LevelScriptTemplateFramingError,
    frame_levelscript_template,
)
from scripts.game_data.gpu_ui_binary import (
    GpuUiFramingError,
    decode_gpu_ui_root16,
    decode_damage_text,
    frame_damage_text,
    frame_gpu_ui_root16_prefix,
)
from scripts.game_data.gameplay_compact_binary import (
    GameplayCompactDecodeError,
    decode_mission_area_table,
    frame_subgame_table,
    frame_world_entity_registry,
)
from scripts.game_data.schemas.gold_coin_config import (
    GoldCoinConfigDecodeError,
    decode_gold_coin_config,
    is_gold_coin_config_path,
)
from scripts.game_data.schemas.gameplay_config import (
    GameplayConfigJsonDecodeError,
    decode_compact_gameplay_config_json,
    is_compact_gameplay_config_json_path,
)
from scripts.game_data.schemas.gameplay_config_polymorphic import (
    GameplayConfigPolymorphicDecodeError,
    decode_polymorphic_gameplay_config,
    is_polymorphic_gameplay_config_path,
)
from scripts.game_data.schemas.text_schema import (
    JsonDataTextSchemaDecodeError,
    decode_named_jsondata_text,
    is_named_jsondata_text_path,
)
from scripts.game_data.schemas.level_mount_point import (
    LevelMountPointJsonDecodeError,
    decode_level_mount_points,
    is_level_mount_point_path,
)
from scripts.game_data.matrix_shockwave_binary import (
    MatrixShockWaveDecodeError,
    decode_matrix_shockwave_table,
)
from scripts.game_data.schemas.map_config import (
    MapConfigDecodeError,
    decode_map_config,
    is_map_config_path,
)
from scripts.game_data.schemas.mission_runtime_meta import (
    MissionRuntimeMetaDecodeError,
    decode_mission_runtime_meta,
    is_mission_runtime_meta_path,
)
from scripts.game_data.schemas.mission_runtime_main import (
    MissionRuntimeMainDecodeError,
    decode_mission_runtime_main,
    is_mission_runtime_main_path,
)
from scripts.game_data.memorypack.corpus_gate import (
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    CensusGateError,
    _guard_output_path,
    _read_outer_and_ledger,
)
from scripts.game_data.memorypack import buff_root_no_positive
from scripts.game_data.memorypack import buff_create_action_root_receipt
from scripts.game_data.memorypack.lipsync import (
    LipSyncDecodeError,
    decode_lipsync_memorypack,
)
from scripts.game_data.memorypack.interactive import (
    decode_interactive_template_memorypack,
)
from scripts.game_data.memorypack.tables import (
    BAMBOO_RAFT_TASK_TABLE_REL,
    DAMAGE_TEXT_REL,
    DIALOG_ID_TABLE_REL,
    decode_bamboo_raft_task_table_memorypack,
    decode_dialog_id_table_memorypack,
)
from scripts.game_data.navmesh_binary import (
    NavMeshDecodeError,
    decode_luna_area,
    decode_navmesh_state_container,
)
from scripts.game_data.schemas.npc_prefab_info import (
    NpcPrefabInfoDecodeError,
    decode_npc_prefab_info,
    is_npc_prefab_info_path,
)
from scripts.game_data.schemas.npc_catalog import (
    NpcCatalogDecodeError,
    decode_npc_catalog,
    is_npc_catalog_path,
)
from scripts.game_data.schemas.ui_level_map_load_config import (
    UiLevelMapLoadConfigDecodeError,
    decode_ui_level_map_load_config,
    is_ui_level_map_load_config_path,
)
from scripts.game_data.memorypack.npc_montage import (
    NpcMontageFramingError,
    frame_npc_montage,
)
from scripts.game_data.spawner_binary import (
    SpawnerEnemyLibraryDecodeError,
    SpawnerWaveDecodeError,
    decode_spawner_enemy_library,
    decode_spawner_named_prefix,
    decode_spawner_wave_map,
    decode_spawner_wave_map_sequential,
)
from scripts.game_data.teleport_validation_binary import (
    TeleportValidationDecodeError,
    decode_teleport_validation_table,
)
from scripts.common import canonical_json_sha256
from scripts.game_data.game_file_store import (
    iter_game_tree,
    locate_game_folder,
    loose_packed_files,
    read_game_file,
)
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout


REPORT_FORMAT = "endfield-jsondata-current-corpus-v1"
DEFAULT_EXPORT = REPO_ROOT / "export_full/game/Json"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/jsondata_current_latest.json"
DEFAULT_MD = REPO_ROOT / "reports/animestudio/jsondata_current_latest.md"
DEFAULT_FILES = REPO_ROOT / "reports/animestudio/jsondata_current_files_latest.jsonl.gz"
DEFAULT_BUFF_REPORT = REPO_ROOT / "reports/animestudio/buffdata_current_latest.json"
DEFAULT_SKILL_REPORT = REPO_ROOT / "reports/animestudio/skilldata_current_latest.json"
JSONDATA_PREFIX = PurePosixPath("Data/Json")

FAMILY_REPORTS = {
    "BuffData": {
        "format": "animestudio-buffdata-current-vfs-corpus",
        "reader": "scripts.game_data.memorypack.buff_corpus",
        "status": "bounded_partial",
    },
    "SkillData": {
        "format": "animestudio-skilldata-current-vfs-corpus",
        "reader": "scripts.game_data.memorypack.skill_corpus",
        "status": "bounded_partial",
    },
}

SKILL_STATUS_PREDICATES = {
    "ambiguous-disjoint-independent-ranges": "ambiguous",
    "verified-terminal-selection-disjoint-independent-ranges": "selected",
    "verified-whole-schema-exact-empty-action-group-profile": "exact_empty",
    "verified-whole-schema-exact-capture-target": "exact_capture_target",
    "verified-whole-schema-exact-capture-target-set": "exact_capture_target_set",
    "verified-whole-schema-exact-timeline-play-animation-profile": "exact_timeline",
    "verified-empty-action-group-named-prefix-and-terminal": "partial_empty",
    "verified-action-group-named-prefix-and-terminal": "named_action_group",
    "verified-timeline-play-animation-named-prefix-and-terminal": "named_timeline_play_animation",
    "verified-timeline-play-animation-step-named-prefix-and-terminal": "named_timeline_play_animation_step",
    "verified-whole-schema-exact-timeline-play-animation-step-profile": "exact_timeline_play_animation_step",
    "verified-timeline-create-buff-first-action-named-prefix-and-terminal": "named_timeline_create_buff_action",
    "verified-timeline-create-buff-first-record-named-prefix-and-terminal": "named_timeline_create_buff_record",
    "verified-whole-schema-exact-timeline-create-buff-profile": "exact_timeline_create_buff",
    "verified-timeline-find-target-named-prefix-and-terminal": "named_timeline_find_target",
    "verified-timeline-continuous-find-target-named-prefix-and-terminal": "named_timeline_continuous_find_target",
    "verified-timeline-shared-sequence-named-prefix-and-terminal": "named_timeline_shared_sequence",
    "verified-whole-schema-exact-timeline-shared-sequence-profile": "exact_timeline_shared_sequence",
    "verified-whole-schema-exact-passive-shared-sequence-profile": "exact_passive_shared_sequence",
}


class SkillEvidenceContractError(ValueError):
    """A bounded SkillData profile failed its named consumer predicate."""

    def __init__(self, diagnostic: dict[str, Any]) -> None:
        self.diagnostic = diagnostic
        super().__init__(
            "SkillData evidence row lacks its bounded structural contract: "
            f"{diagnostic['virtualPath']!r}; "
            f"failedPredicate={diagnostic['failedPredicate']!r}; "
            f"actual={diagnostic['actual']!r}"
        )


def _exact_create_buff_later_records(profile: dict[str, Any], first_record: dict[str, Any]) -> bool:
    """Check the additional exact records in the shared CreateBuff list route."""
    if profile.get("status") != "verified-exact-timeline-create-buff-shared-sequence-records":
        return False
    count = profile.get("timelineActionsCount")
    records = profile.get("laterTimelineActions")
    cursor = first_record.get("end")
    if (
        type(count) is not int or count <= 1
        or not isinstance(records, list) or len(records) != count - 1
        or type(cursor) is not int
    ):
        return False
    for index, record in enumerate(records, 1):
        if (
            not isinstance(record, dict)
            or record.get("index") != index
            or record.get("start") != cursor
            or type(record.get("end")) is not int
            or record["end"] <= cursor
            or record.get("wholeRecordExact") is not True
        ):
            return False
        cursor = record["end"]
    return cursor == profile.get("parserCursor")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _skill_capture_target_reference(report: dict[str, Any], source_path: Path) -> dict[str, Any] | None:
    """Check the exact-source verification pinned by a SkillData corpus report."""
    provenance = report.get("provenance")
    reference = provenance.get("captureTargetVerification") if isinstance(provenance, dict) else None
    if reference is None:
        return None
    if not isinstance(reference, dict):
        raise ValueError(f"SkillData capture target provenance is malformed: {source_path}")
    recorded_path = reference.get("path")
    if not isinstance(recorded_path, str) or not Path(recorded_path).is_absolute():
        raise ValueError(f"SkillData capture target verification path is invalid: {source_path}")
    verification_path = Path(recorded_path).resolve()
    if not verification_path.is_file():
        raise ValueError(f"SkillData capture target verification is missing: {verification_path}")
    if (reference.get("length") != verification_path.stat().st_size
            or reference.get("sha256") != _sha256_path(verification_path)):
        raise ValueError(f"SkillData capture target verification bytes differ: {verification_path}")
    try:
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"SkillData capture target verification cannot be read: {verification_path}: {exc}") from exc
    if not isinstance(verification, dict):
        raise ValueError(f"SkillData capture target verification is not an object: {verification_path}")
    summary = verification.get("summary")
    captured = verification.get("captureTarget")
    verified_provenance = verification.get("provenance")
    target = reference.get("target")
    if (
        verification.get("schema") != "endfield.skillDataCursorTargetVerification.v1"
        or verification.get("status") != "complete"
        or verification.get("verificationMode") != "capture-target"
        or verification.get("inputSetSha256") != report.get("inputSetSha256")
        or not isinstance(summary, dict)
        or summary.get("failureReasons") != []
        or not isinstance(captured, dict)
        or captured.get("exactObservationCount") != 1
        or not isinstance(target, dict)
        or target != {
            "virtualPath": captured.get("logicalPath"),
            "length": captured.get("sourceLength"),
            "logicalSha256": captured.get("logicalSha256"),
        }
        or not isinstance(verified_provenance, dict)
        or not isinstance(verified_provenance.get("corpusReport"), dict)
        or verified_provenance["corpusReport"].get("identitySetSha256")
        != report.get("identitySetSha256")
    ):
        raise ValueError(f"SkillData capture target verification contract differs: {verification_path}")
    input_names = ("receipt", "corpusReport", "nativeContext", "verifier",
                   "captureTargetContract", "captureTargetVerifier")
    expected_inputs = []
    for name in input_names:
        source = verified_provenance.get(name)
        if not isinstance(source, dict):
            raise ValueError(f"SkillData capture target verification lacks {name}: {verification_path}")
        expected_inputs.append({key: source.get(key) for key in ("path", "length", "sha256")})
    if reference.get("inputs") != expected_inputs:
        raise ValueError(f"SkillData capture target input provenance differs: {verification_path}")
    return {
        "path": verification_path.as_posix(),
        "sha256": reference["sha256"],
        "target": target,
    }


def _skill_capture_target_set_reference(
    report: dict[str, Any], source_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]] | None:
    """Check the strict v3 receipt reference and index its exact source targets."""
    provenance = report.get("provenance")
    reference = provenance.get("captureTargetSetVerification") if isinstance(provenance, dict) else None
    if reference is None:
        return None
    if not isinstance(reference, dict):
        raise ValueError(f"SkillData target-set provenance is malformed: {source_path}")
    recorded_path = reference.get("path")
    if not isinstance(recorded_path, str) or not Path(recorded_path).is_absolute():
        raise ValueError(f"SkillData target-set verification path is invalid: {source_path}")
    verification_path = Path(recorded_path).resolve()
    if not verification_path.is_file():
        raise ValueError(f"SkillData target-set verification is missing: {verification_path}")
    if (reference.get("length") != verification_path.stat().st_size
            or reference.get("sha256") != _sha256_path(verification_path)):
        raise ValueError(f"SkillData target-set verification bytes differ: {verification_path}")
    try:
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"SkillData target-set verification cannot be read: {verification_path}: {exc}") from exc
    if not isinstance(verification, dict):
        raise ValueError(f"SkillData target-set verification is not an object: {verification_path}")
    summary = verification.get("summary")
    targets = verification.get("targets")
    verified_provenance = verification.get("provenance")
    if (
        verification.get("schema") != "endfield.skillDataCursorTargetSetVerification.v1"
        or verification.get("status") != "validated"
        or verification.get("coverageStatus") != "complete"
        or verification.get("inputSetSha256") != report.get("inputSetSha256")
        or not isinstance(summary, dict)
        or summary.get("globalFailureReasons") != []
        or summary.get("unresolvedExactClosed") != summary.get("unresolvedTargets")
        or summary.get("positiveControlsExactClosed") != summary.get("positiveControls")
        or not isinstance(targets, list)
        or summary.get("observationCount") != len(targets)
        or not isinstance(verified_provenance, dict)
        or not isinstance(verified_provenance.get("corpusReport"), dict)
        or verified_provenance["corpusReport"].get("identitySetSha256")
        != report.get("identitySetSha256")
    ):
        raise ValueError(f"SkillData target-set verification contract differs: {verification_path}")
    input_names = ("receipt", "corpusReport", "nativeContext", "verifier",
                   "captureTargetSetContract", "captureTargetSetVerifier")
    expected_inputs = []
    for name in input_names:
        source = verified_provenance.get(name)
        if not isinstance(source, dict):
            raise ValueError(f"SkillData target-set verification lacks {name}: {verification_path}")
        expected_inputs.append({key: source.get(key) for key in ("path", "length", "sha256")})
    if (reference.get("inputs") != expected_inputs
            or reference.get("targets") != len(targets)
            or reference.get("promoted") != summary.get("unresolvedTargets")
            or reference.get("retainedPositiveControls") != summary.get("positiveControls")):
        raise ValueError(f"SkillData target-set input provenance differs: {verification_path}")
    targets_by_path: dict[str, dict[str, Any]] = {}
    for target in targets:
        if (not isinstance(target, dict) or not isinstance(target.get("virtualPath"), str)
                or target["virtualPath"] in targets_by_path
                or target.get("status") != "observed-exact-closed"
                or target.get("captureHealth") != "clean"):
            raise ValueError(f"SkillData target-set target is malformed: {verification_path}")
        targets_by_path[target["virtualPath"]] = target
    return ({"path": verification_path.as_posix(), "sha256": reference["sha256"],
             "targets": len(targets)}, targets_by_path)


def _skill_capture_target_set_row_exact(row: dict[str, Any], target: dict[str, Any] | None) -> bool:
    """Keep the consumer's exact tier tied to one captured source and static join."""
    if not isinstance(target, dict) or target.get("role") != "unresolved":
        return False
    runtime = target.get("runtimeFieldRanges")
    terminal = target.get("selectedTerminal")
    if (target.get("virtualPath") != row.get("virtualPath")
            or target.get("sourceLength") != row.get("length")
            or target.get("logicalSha256") != row.get("logicalSha256")
            or not isinstance(runtime, list) or len(runtime) != 48
            or not isinstance(terminal, dict)):
        return False
    cursor = 1
    for index, field in enumerate(runtime):
        if (not isinstance(field, dict) or field.get("fieldIndex") != index
                or type(field.get("start")) is not int or type(field.get("end")) is not int
                or field["start"] != cursor or field["end"] <= cursor):
            return False
        cursor = field["end"]
    if (cursor != row.get("length")
            or terminal != {"start": runtime[43]["start"], "end": cursor,
                            "encoding": "one-member-wrapper", "framerCandidateCount": 2}):
        return False
    profile = row.get("timelineSharedSequenceProfile")
    if (not isinstance(profile, dict) or profile.get("wholeActionGroupDataExact") is not True
            or profile.get("status") != "exact-first-timeline-shared-sequence-record"):
        profile = row.get("passiveSharedSequenceProfile")
        if (not isinstance(profile, dict) or profile.get("wholeActionGroupDataExact") is not True
                or profile.get("status") != "exact-passive-shared-sequence-list"):
            return False
    continuation = profile.get("topLevelContinuation")
    static = continuation.get("namedFields") if isinstance(continuation, dict) else None
    if (profile.get("parserCursor") != runtime[0]["end"]
            or not isinstance(continuation, dict)
            or continuation.get("status") != "verified-exact-through-field-42"
            or continuation.get("parserCursor") != runtime[43]["start"]
            or not isinstance(static, list) or len(static) != 43):
        return False
    return all(
        isinstance(field, dict)
        and field.get("fieldIndex") == index
        and field.get("fieldName") == runtime[index].get("fieldName")
        and field.get("start") == runtime[index]["start"]
        and field.get("end") == runtime[index]["end"]
        for index, field in enumerate(static)
    )


def _safe_export_path(export_root: Path, virtual_path: str) -> tuple[Path, str, str]:
    logical = PurePosixPath(virtual_path)
    if logical.is_absolute() or ".." in logical.parts or logical.parts[:2] != JSONDATA_PREFIX.parts:
        raise ValueError(f"unsafe JsonData virtual path: {virtual_path!r}")
    relative = PurePosixPath(*logical.parts[2:])
    if not relative.parts:
        raise ValueError(f"empty JsonData relative path: {virtual_path!r}")
    candidate = (export_root / Path(*relative.parts)).resolve()
    if not candidate.is_relative_to(export_root):
        raise ValueError(f"JsonData export path escapes root: {virtual_path!r}")
    family = relative.parts[0] if len(relative.parts) > 1 else relative.name
    return candidate, relative.as_posix(), family


def _json_game_folder(json_dir: Path) -> tuple[Path, str]:
    """``(export root, game/-relative folder)`` of a JsonData directory under an export's game/.

    Packed folders (``Json/LipSync``) are not on disk, so the directory must sit
    inside an export root's ``game/`` for its files to be resolved through the
    game-file store; any other directory fails closed.
    """
    located = locate_game_folder(json_dir)
    if located is None or not located[1]:
        raise ValueError(f"JsonData directory is not a folder under an export root's game/: {json_dir}")
    return located


def _json_export_files(export_root: Path, folder: str) -> set[str]:
    """Folder-relative, casefolded paths of every JsonData file, loose and packed.

    A loose file left under a packed folder is not part of the export (packed
    folders are read only from the store), so it fails closed here instead of
    being silently ignored.
    """
    layout = ExportLayout(export_root)
    prefix = folder.casefold() + "/"
    for packed, files in loose_packed_files(layout).items():
        if (packed.casefold() + "/").startswith(prefix):
            first = sorted(files, key=str.casefold)[0]
            raise ValueError(
                f"loose file under packed folder game/{packed}: {first!r}; "
                f"pack the root before auditing it"
            )
    return {
        entry.path[len(prefix):].casefold()
        for entry in iter_game_tree(export_root, folder)
    }


def _classify_json(data: bytes) -> tuple[bool, str | None]:
    stripped = data.lstrip()
    if stripped[:1] not in (b"{", b"["):
        return False, None
    try:
        decoded = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, None
    return True, "object" if isinstance(decoded, dict) else "array" if isinstance(decoded, list) else "scalar"


def _load_family_evidence(
    path: Path,
    *,
    family: str,
    expected_input_set_sha256: str,
    expected_paths: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    contract = FAMILY_REPORTS[family]
    with path.open("r", encoding="utf-8") as handle:
        report = json.load(handle)
    if (
        report.get("format") != contract["format"]
        or report.get("schemaVersion") != 1
        or report.get("status") != "complete"
        or report.get("publicationEligible") is not True
        or report.get("inputSetSha256") != expected_input_set_sha256
        or report.get("wholeSchemaExact") is not False
    ):
        raise ValueError(f"{family} evidence report is incomplete, stale, or has an unsupported contract")
    rows = report.get("files")
    if not isinstance(rows, list):
        raise ValueError(f"{family} evidence report has no file rows")
    if family == "BuffData":
        identity_rows = [
            {"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
            for row in rows
        ]
    else:
        identity_fields = (
            "virtualPath", "blockTypeValue", "length", "logicalMd5", "logicalSha256",
            "physicalChunkPath", "physicalChunkSource", "metadataProvenance", "overlayState",
            "chunkOverlayState", "physicalOffset", "encrypted",
        )
        try:
            identity_rows = [{key: row[key] for key in identity_fields} for row in rows]
        except KeyError as exc:
            raise ValueError(f"SkillData evidence identity is incomplete: {exc}") from exc
    if canonical_json_sha256(identity_rows) != report.get("identitySetSha256"):
        raise ValueError(f"{family} evidence identity-set digest does not match its file rows")
    capture_target_reference = (
        _skill_capture_target_reference(report, path) if family == "SkillData" else None
    )
    capture_target_set_reference = (
        _skill_capture_target_set_reference(report, path) if family == "SkillData" else None
    )

    evidence: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = row.get("identity") if family == "BuffData" else row
        if not isinstance(identity, dict):
            raise ValueError(f"{family} evidence row has no identity")
        virtual_path = identity.get("virtualPath")
        if not isinstance(virtual_path, str) or virtual_path in evidence:
            raise ValueError(f"{family} evidence has an invalid or duplicate path: {virtual_path!r}")
        buff_exact_claim = family == "BuffData" and row.get("wholeSchemaExact") is True
        if (
            identity.get("inputSetSha256") != expected_input_set_sha256
            or identity.get("blockName") != "JsonData"
            or identity.get("blockTypeValue") != 19
            or (
                row.get("wholeSchemaExact") is not False
                and not (
                    buff_exact_claim
                    and row.get("boundaryClass") == "exact-closed"
                    and row.get("coverageStatus") == "unique"
                    and row.get("namedOuterFrameStatus") == "named_exact_full"
                    and (row.get("rootNoPositiveCandidate") is True
                         or row.get("rootPositiveDamageCandidate") is True
                         or row.get("rootSingleCreateActionCandidate") is True)
                )
                and not (
                    family == "SkillData"
                    and row.get("wholeSchemaExact") is True
                    and row.get("boundaryClass") == "exact-closed"
                    and row.get("coverageStatus")
                    in (
                        "verified-whole-schema-exact-empty-action-group-profile",
                        "verified-whole-schema-exact-capture-target",
                        "verified-whole-schema-exact-capture-target-set",
                        "verified-whole-schema-exact-timeline-play-animation-profile",
                        "verified-whole-schema-exact-timeline-play-animation-step-profile",
                        "verified-whole-schema-exact-timeline-create-buff-profile",
                        "verified-whole-schema-exact-timeline-shared-sequence-profile",
                        "verified-whole-schema-exact-passive-shared-sequence-profile",
                    )
                )
            )
        ):
            raise ValueError(f"{family} evidence row is not current bounded JsonData: {virtual_path!r}")
        if family == "BuffData":
            if (
                identity.get("status") != "verified"
                or identity.get("boundaryStatus") != "boundary_verified"
                or row.get("eventPrefixStatus") != "success"
                or row.get("coverageStatus") != "unique"
            ):
                raise ValueError(f"BuffData evidence row lacks its proven event prefix: {virtual_path!r}")
            logical_md5 = identity.get("recomputedFileDataMd5")
            root_receipt = row.get("rootNoPositiveReceipt")
            positive_receipt = row.get("rootPositiveDamageReceipt")
            create_receipt = row.get("rootSingleCreateActionReceipt")
            positive_condition_status = None
            if isinstance(positive_receipt, dict):
                positive_fields = positive_receipt.get("fields") or []
                if isinstance(positive_fields, list) and len(positive_fields) > 6:
                    positive_condition_status = (
                        ((positive_fields[6] or {}).get("child") or {})
                        .get("conditionChild", {}).get("status")
                    )
            if buff_exact_claim:
                positive = row.get("rootPositiveDamageCandidate") is True
                create_action = row.get("rootSingleCreateActionCandidate") is True
                no_positive = row.get("rootNoPositiveCandidate") is True
                if sum((positive, create_action, no_positive)) != 1:
                    raise ValueError(f"BuffData exact root branch is ambiguous: {virtual_path!r}")
                native_key = (
                    "buffSingleCreateActionNativeValidation" if create_action
                    else "buffPositiveDamageNativeValidation" if positive
                    else "buffRootNoPositiveNativeValidation"
                )
                native = (report.get("provenance") or {}).get(native_key) or {}
                root_native = native.get("root") if positive else native
                chosen_receipt = (create_receipt if create_action else
                                  positive_receipt if positive else root_receipt)
                fields = chosen_receipt.get("fields") if isinstance(chosen_receipt, dict) else None
                if (
                    native.get("status") != "validated"
                    or (not create_action and (
                        (root_native or {}).get("status") != "validated"
                        or ((root_native or {}).get("root") or {}).get("status") != "validated"
                        or any(((root_native or {}).get("children") or {}).get(name, {}).get("status") != "validated"
                               for name in ("addingCooldown", "dispelConfig", "iconConfig",
                                            "stackingSettings", "timelineActions",
                                            "blackboardDataPairs", "globalModifier"))
                    ))
                    or not isinstance(chosen_receipt, dict)
                    or chosen_receipt.get("schema") != (
                        "endfield.buff-root-single-create-action-receipt.v1" if create_action
                        else "endfield.buff-root-positive-damage-receipt.v12" if positive
                        else "endfield.buff-root-no-positive-receipt.v1"
                    )
                    or chosen_receipt.get("status") != (
                        "named-exact-full-proposal" if create_action else "named-exact-full"
                    )
                    or chosen_receipt.get("wholeSchemaExact") is not True
                    or chosen_receipt.get("nativeStatus") != "validated"
                    or chosen_receipt.get("source") != virtual_path
                    or chosen_receipt.get("logicalSha256") != row.get("logicalSha256")
                    or chosen_receipt.get("rootMemberCount") != 30
                    or chosen_receipt.get("headerRange") != [0, 1]
                    or chosen_receipt.get("physicalEof") != identity.get("length")
                    or chosen_receipt.get("bytesConsumed") != identity.get("length")
                    or not isinstance(fields, list)
                    or len(fields) != 30
                    or any(not isinstance(field, dict) for field in fields)
                    or [field.get("index") for field in fields] != list(range(30))
                    or fields[0].get("start") != 1
                    or any(left.get("end") != right.get("start")
                           for left, right in zip(fields, fields[1:]))
                    or fields[-1].get("end") != identity.get("length")
                    or fields[15].get("name") != "id"
                    or fields[15].get("value") != Path(virtual_path).stem
                    or (fields[4].get("child") or {}).get("status") != "exact-datapair-list"
                    or (fields[4].get("child") or {}).get("consumedEnd") != fields[4].get("end")
                    or (
                        fields[10].get("count") not in (-1, 0)
                        and (
                            (fields[10].get("child") or {}).get("status") != "exact"
                            or (fields[10].get("child") or {}).get("consumedEnd") != fields[10].get("end")
                        )
                    )
                ):
                    raise ValueError(f"BuffData exact root receipt is incomplete: {virtual_path!r}")
                if positive:
                    damage = (fields[6].get("child") or {})
                    condition = (damage.get("conditionChild") or {})
                    condition_count = condition.get("actionCount")
                    condition_exact = (
                        condition_count == 0
                        and condition.get("status") == "exact-empty-sequence"
                        and condition.get("wholeStoredSpanExact") is True
                    ) or (
                        condition_count == 1
                        and condition.get("status") == "exact-one-action-sequence"
                        and condition.get("wholeStoredSpanExact") is True
                        and condition.get("recursiveNamedSchemaExact") is True
                        and (condition.get("action") or {}).get("tag")
                        in (
                            (native.get("checkDecorateMaskCondition") or {}).get("unionTag"),
                            (native.get("checkDamageTypeCondition") or {}).get("unionTag"),
                            (native.get("checkDamageTypeMaskCondition") or {}).get("unionTag"),
                            (native.get("checkTagMatchCondition") or {}).get("unionTag"),
                            (native.get("checkMainCharacterCondition") or {}).get("unionTag"),
                            (native.get("checkBuffStackCondition") or {}).get("unionTag"),
                        ) + tuple(route.get("unionTag") for route in
                                  (native.get("checkVitalsCondition") or {}).get("routes", []))
                        and (condition.get("action") or {}).get("recursiveNamedSchemaExact") is True
                    ) or (
                        condition_count == 2
                        and condition.get("status") == "exact-two-action-sequence"
                        and condition.get("wholeStoredSpanExact") is True
                        and condition.get("recursiveNamedSchemaExact") is True
                        and [action.get("tag") for action in condition.get("actions") or []]
                            == (native.get("twoActionCondition") or {}).get("selectedActionTags")
                        and all(action.get("recursiveNamedSchemaExact") is True
                                for action in condition.get("actions") or [])
                    )
                    if not condition_exact:
                        actions = condition.get("actions") or []
                        action_tags = [action.get("tag") for action in actions]
                        origin_native = native.get("originOrCondition") or {}
                        known_native = native.get("knownCompoundCondition") or {}
                        origin_plan = origin_native.get("originActionMemberPlan") or []
                        origin_fields = ((actions[0].get("namedFields") or [])
                                         if actions else [])
                        or_fields = ((actions[1].get("namedFields") or [])
                                     if len(actions) == 2 else [])
                        origin_list = origin_fields[-1] if len(origin_fields) == 6 else {}
                        or_list = or_fields[-1] if len(or_fields) == 5 else {}
                        or_children = or_list.get("namedChildren") or []
                        nested_tags = [
                            [action.get("tag") for action in child.get("actions") or []]
                            for child in or_children
                        ]
                        stack_nested = (
                            ((or_children[1].get("actions") or [])[0]
                             if len(or_children) == 2
                             and len(or_children[1].get("actions") or []) == 1 else {})
                        )
                        stack_nested_fields = stack_nested.get("namedFields") or []
                        stack_nested_finder = (
                            (stack_nested_fields[4].get("namedChild") or {})
                            if len(stack_nested_fields) == 10 else {}
                        )
                        origin_shape = (
                            condition_count == 2
                            and condition.get("status") == "exact-two-action-sequence"
                            and condition.get("wholeStoredSpanExact") is True
                            and condition.get("recursiveNamedSchemaExact") is True
                            and len(actions) == 2
                            and all(action.get("recursiveNamedSchemaExact") is True
                                    for action in actions)
                            and [field.get("name") for field in origin_fields]
                                == [field.get("name") for field in origin_plan]
                            and origin_list.get("count") == 1
                            and origin_native.get("status") == "validated"
                        )
                        if origin_shape and condition.get("branch") == "origin-poise":
                            vitals = origin_native.get("vitalsNative") or {}
                            poise = next((route for route in vitals.get("routes") or []
                                          if route.get("unionTag") == action_tags[1]), {})
                            condition_exact = (
                                action_tags == origin_native.get("simpleActionTags")
                                and [field.get("name") for field in or_fields]
                                    == [field.get("name") for field in
                                        poise.get("actionMemberPlan") or []]
                                and (or_fields[5].get("namedChild") or {}).get("status")
                                    == "exact-simple-target"
                                and (or_fields[7].get("namedChild") or {}).get("wholeValueExact")
                                    is True
                            )
                        elif origin_shape and condition.get("branch") == "origin-or":
                            expected_flat = (
                                [origin_native.get("originUnionTag")]
                                + [tags[0] for tags in
                                   origin_native.get("orNestedSequenceTags") or []]
                                + [origin_native.get("orUnionTag")]
                            )
                            finder_shape = origin_native.get("orNestedFinderShape") or {}
                            condition_exact = (
                                action_tags == origin_native.get("nestedActionTags")
                                and [field.get("name") for field in or_fields]
                                    == [field.get("name") for field in
                                        origin_native.get("orActionMemberPlan") or []]
                                and or_list.get("count") == 2
                                and len(or_children) == 2
                                and nested_tags == origin_native.get("orNestedSequenceTags")
                                and all(child.get("status") == "exact-selected-sequence"
                                        and child.get("recursiveNamedSchemaExact") is True
                                        for child in or_children)
                                and stack_nested_finder.get("buffIdListCount")
                                    == finder_shape.get("buffIdListCount")
                                and stack_nested_finder.get("tagCount")
                                    == finder_shape.get("tagCount")
                                and (stack_nested_finder.get("namedFields") or [{}, {}, {}])[2]
                                    .get("queryStatus") == finder_shape.get("queryStatus")
                                and expected_flat == [
                                    origin_native.get("originUnionTag"),
                                    nested_tags[0][0], nested_tags[1][0],
                                    origin_native.get("orUnionTag"),
                                ]
                            )
                        if not condition_exact and known_native.get("status") == "validated":
                            selected = known_native.get("selectedActionPatterns") or []
                            known_actions = known_native.get("selectedActions") or {}
                            stack_action = next((action for action in actions
                                                 if action.get("tag") == 60), {})
                            stack_fields = stack_action.get("namedFields") or []
                            stack_finder = ((stack_fields[4].get("namedChild") or {})
                                            if len(stack_fields) == 10 else {})
                            tag_action = next((action for action in actions
                                               if action.get("tag") == 124), {})
                            tag_fields = tag_action.get("namedFields") or []
                            tag_query = ((tag_fields[5].get("namedChild") or {})
                                         if len(tag_fields) == 6 else {})
                            finder_shape = known_native.get("stackFinderShape") or {}
                            condition_exact = (
                                condition_count in (2, 3)
                                and condition.get("status")
                                    == "exact-selected-compound-sequence"
                                and condition.get("wholeStoredSpanExact") is True
                                and condition.get("recursiveNamedSchemaExact") is True
                                and action_tags in selected
                                and len(actions) == condition_count
                                and all(action.get("recursiveNamedSchemaExact") is True
                                        and [field.get("name") for field in
                                             action.get("namedFields") or []]
                                            == [field.get("name") for field in
                                                (known_actions.get(str(action.get("tag"))) or {})
                                                .get("actionMemberPlan") or []]
                                        for action in actions)
                                and stack_finder.get("buffIdListCount")
                                    == finder_shape.get("buffIdListCount")
                                and stack_finder.get("tagCount")
                                    == finder_shape.get("tagCount")
                                and (stack_finder.get("namedFields") or [{}, {}, {}])[2]
                                    .get("queryStatus") == finder_shape.get("queryStatus")
                                and (not tag_action or
                                     (tag_query.get("status") == "exact-positive-query"
                                      and (tag_query.get("namedFields") or [{}, {}])[1]
                                          .get("count")
                                          == known_native.get("tagMatchQueryTagCount")))
                            )
                        if not condition_exact:
                            if_else_native = native.get("ifElseCondition") or {}
                            if_else_fields = ((actions[0].get("namedFields") or [])
                                              if actions else [])
                            nested_children = (
                                [if_else_fields[index].get("namedChild") or {}
                                 for index in (5, 6, 7)]
                                if len(if_else_fields) == 8 else []
                            )
                            if_else_main = nested_children[0] if len(nested_children) == 3 else {}
                            if_else_empty = nested_children[1] if len(nested_children) == 3 else {}
                            if_else_return = nested_children[2] if len(nested_children) == 3 else {}
                            pattern = next(
                                (tags for tags in if_else_native.get("selectedTopActionPatterns") or []
                                 if len(tags) == condition_count), None,
                            )
                            condition_exact = (
                                if_else_native.get("status") == "validated"
                                and condition.get("status") == "exact-selected-if-else-sequence"
                                and condition.get("wholeStoredSpanExact") is True
                                and condition.get("recursiveNamedSchemaExact") is True
                                and pattern is not None and action_tags == pattern
                                and len(actions) == condition_count
                                and all(action.get("recursiveNamedSchemaExact") is True
                                        for action in actions)
                                and [field.get("fieldName") for field in if_else_fields[5:]]
                                    == ["conditionAction", "failActions", "succeedActions"]
                                and [child.get("actionCount") for child in nested_children]
                                    == [1, 0, 1]
                                and (if_else_main.get("action") or {}).get("tag") == 104
                                and (if_else_main.get("action") or {}).get("recursiveNamedSchemaExact")
                                    is True
                                and if_else_empty.get("status") == "exact-empty-sequence"
                                and (if_else_return.get("action") or {}).get("tag")
                                    == if_else_native.get("returnFalseUnionTag")
                                and [field.get("name") for field in
                                     (if_else_return.get("action") or {}).get("namedFields") or []]
                                    == [field.get("name") for field in
                                        if_else_native.get("returnFalseActionMemberPlan") or []]
                                and (condition_count != 2
                                     or [field.get("name") for field in
                                         actions[1].get("namedFields") or []]
                                         == [field.get("name") for field in
                                             (native.get("checkDecorateMaskCondition") or {})
                                             .get("actionMemberPlan") or []])
                            )
                        if not condition_exact:
                            not_next_native = native.get("notNextMainCondition") or {}
                            not_next_first = ((actions[0].get("namedFields") or [])
                                              if len(actions) == 2 else [])
                            not_next_main = ((actions[1].get("namedFields") or [])
                                             if len(actions) == 2 else [])
                            condition_exact = (
                                not_next_native.get("status") == "validated"
                                and condition_count == 2
                                and condition.get("status") == "exact-two-action-sequence"
                                and condition.get("wholeStoredSpanExact") is True
                                and condition.get("recursiveNamedSchemaExact") is True
                                and action_tags == not_next_native.get("selectedActionTags")
                                and len(actions) == 2
                                and all(action.get("recursiveNamedSchemaExact") is True
                                        for action in actions)
                                and [field.get("name") for field in not_next_first]
                                    == [field.get("name") for field in
                                        not_next_native.get("notNextActionMemberPlan") or []]
                                and [field.get("name") for field in not_next_main]
                                    == [field.get("name") for field in
                                        (not_next_native.get("mainCharacterNative") or {})
                                        .get("actionMemberPlan") or []]
                                and (not_next_main[4].get("namedChild") or {})
                                    .get("recursiveNamedSchemaExact") is True
                            )
                        if not condition_exact:
                            angle_native = native.get("twoDirectionAngleCondition") or {}
                            target_names = angle_native.get("selectedTargetMemberNames") or []
                            blackboard_name = angle_native.get("selectedBlackboardMemberName")
                            angle_plan = angle_native.get("fieldPlan") or []
                            condition_exact = (
                                angle_native.get("status") == "validated"
                                and condition_count == 2
                                and condition.get("status") == "exact-two-action-sequence"
                                and condition.get("wholeStoredSpanExact") is True
                                and condition.get("recursiveNamedSchemaExact") is True
                                and condition.get("terminalRawHex")
                                    == angle_native.get("selectedTerminalRawHex")
                                and action_tags == angle_native.get("selectedActionTags")
                                and len(actions) == 2
                                and len(target_names) == 4
                                and all(
                                    action.get("recursiveNamedSchemaExact") is True
                                    and [field.get("name") for field in
                                         action.get("namedFields") or []]
                                        == [field.get("name") for field in angle_plan]
                                    and all(
                                        (field.get("namedChild") or {}).get("status")
                                            == "exact-simple-target"
                                        and (field.get("namedChild") or {}).get("end")
                                            == field.get("end")
                                        for field in action.get("namedFields") or []
                                        if field.get("name") in target_names
                                    )
                                    and any(
                                        field.get("name") == blackboard_name
                                        and (field.get("namedChild") or {}).get("wholeValueExact")
                                            is True
                                        and (field.get("namedChild") or {}).get("consumedEnd")
                                            == field.get("end")
                                        for field in action.get("namedFields") or []
                                    )
                                    for action in actions
                                )
                            )
                    processor_child = damage.get("processorChild") or {}
                    processor_tag = processor_child.get("unionTag")
                    scalar_route = next(
                        (route for route in (native.get("processorScalar") or {}).get("routes", [])
                         if route.get("unionTag") == processor_tag),
                        None,
                    )
                    processor_native = next(
                        (
                            (native.get(name) or {}) for name in (
                                "processor", "processorModifyCalc",
                                "processorInstantModifyAttribute",
                            )
                            if (native.get(name) or {}).get("unionTag") == processor_tag
                        ),
                        ({"status": (native.get("processorScalar") or {}).get("status"),
                          "fieldPlan": scalar_route["fieldPlan"]} if scalar_route else {}),
                    )
                    processor_fields = processor_child.get("namedFields") or []
                    instant_native = native.get("processorInstantModifyAttribute") or {}
                    instant_modifier = ((processor_fields[0].get("namedChild") or {})
                                        if processor_fields else {})
                    instant_fields = instant_modifier.get("namedFields") or []
                    instant_param = instant_fields[3] if len(instant_fields) == 4 else {}
                    processor_children = damage.get("processorChildren") or []
                    processor_pair = len(processor_children) == 2
                    pair_second = processor_children[1] if processor_pair else {}
                    text_native = native.get("processorText") or {}
                    parent_elements = (damage.get("parent") or {}).get("elements") or []
                    parent_fields = ((parent_elements[0].get("fields") or [])
                                     if len(parent_elements) == 1 else [])
                    parent_processor_field = parent_fields[1] if len(parent_fields) == 3 else {}
                    parent_processors = parent_processor_field.get("processors") or []
                    processor_exact = (
                        processor_native.get("status") == "validated"
                        and processor_child.get("status") == "named-direct-members-exact-span"
                        and processor_child.get("wholeStoredSpanExact") is True
                        and processor_child.get("recursiveNamedSchemaExact") is True
                        and [field.get("name") for field in processor_fields]
                        == [field.get("name") for field in processor_native.get("fieldPlan", [])]
                        and (
                            processor_tag != (native.get("processor") or {}).get("unionTag")
                            or (
                                len(processor_fields) == 3
                                and (processor_fields[0].get("namedChild") or {}).get("wholeValueExact") is True
                                and processor_fields[0]["namedChild"].get("startOffset")
                                    == processor_fields[0].get("start")
                                and processor_fields[0]["namedChild"].get("consumedEnd")
                                    == processor_fields[0].get("end")
                            )
                        )
                        and (
                            processor_tag != (native.get("processorModifyCalc") or {}).get("unionTag")
                            or (
                                condition_count == 1
                                and (condition.get("action") or {}).get("tag") in (
                                    (native.get("checkDecorateMaskCondition") or {}).get("unionTag"),
                                    (native.get("checkDamageTypeCondition") or {}).get("unionTag"),
                                )
                                and len(processor_fields) == 3
                                and all(
                                    (processor_fields[index].get("namedChild") or {}).get("wholeValueExact") is True
                                    and (processor_fields[index]["namedChild"]).get("startOffset")
                                        == processor_fields[index].get("start")
                                    and (processor_fields[index]["namedChild"]).get("consumedEnd")
                                        == processor_fields[index].get("end")
                                    for index in (0, 2)
                                )
                            )
                        )
                        and (
                            scalar_route is None
                            or (
                                (
                                    condition_count == 1
                                    and (
                                        (scalar_route or {}).get("unionTag") == 2
                                        and (condition.get("action") or {}).get("tag")
                                        == (native.get("checkDecorateMaskCondition") or {}).get("unionTag")
                                        or (scalar_route or {}).get("unionTag") in (0, 3)
                                        and (condition.get("action") or {}).get("tag") in (
                                            (native.get("checkDecorateMaskCondition") or {}).get("unionTag"),
                                            (native.get("checkTagMatchCondition") or {}).get("unionTag"),
                                        )
                                    )
                                    or condition_count == 2
                                    and (scalar_route or {}).get("unionTag") == 4
                                    and condition.get("status") == "exact-two-action-sequence"
                                    and [action.get("tag") for action in
                                         condition.get("actions") or []]
                                        == (native.get("notNextMainCondition") or {})
                                        .get("selectedActionTags")
                                )
                                and len(processor_fields) == 1
                                and (processor_fields[0].get("namedChild") or {}).get("wholeValueExact") is True
                                and processor_fields[0]["namedChild"].get("startOffset")
                                    == processor_fields[0].get("start")
                                and processor_fields[0]["namedChild"].get("consumedEnd")
                                    == processor_fields[0].get("end")
                            )
                        )
                        and (
                            processor_tag != instant_native.get("unionTag")
                            or (
                                condition_count == 1
                                and (condition.get("action") or {}).get("tag")
                                    == (native.get("checkBuffStackCondition") or {}).get("unionTag")
                                and len(processor_fields) == 2
                                and processor_fields[0].get("end") == processor_fields[1].get("start")
                                and processor_fields[1].get("end") - processor_fields[1].get("start") == 4
                                and instant_modifier.get("status") == "named-direct-members-exact-span"
                                and instant_modifier.get("wholeStoredSpanExact") is True
                                and instant_modifier.get("recursiveNamedSchemaExact") is True
                                and instant_modifier.get("start") == processor_fields[0].get("start")
                                and instant_modifier.get("end") == processor_fields[0].get("end")
                                and [field.get("name") for field in instant_fields]
                                    == [field.get("name") for field in
                                        instant_native.get("modifierFieldPlan", [])]
                                and len(instant_fields) == 4
                                and instant_fields[0].get("start") == instant_modifier.get("start") + 1
                                and all(left.get("end") == right.get("start")
                                        for left, right in zip(instant_fields, instant_fields[1:]))
                                and instant_fields[-1].get("end") == instant_modifier.get("end")
                                and (instant_param.get("namedChild") or {}).get("wholeValueExact") is True
                                and (instant_param.get("namedChild") or {}).get("startOffset")
                                    == instant_param.get("start")
                                and (instant_param.get("namedChild") or {}).get("consumedEnd")
                                    == instant_param.get("end")
                            )
                        )
                        and (
                            (len(processor_children) == 1
                             and processor_children[0] == processor_child)
                            or (
                                processor_pair
                                and processor_children[0] == processor_child
                                and (
                                    condition_count == 0
                                    or (condition_count == 2
                                        and condition.get("status") == "exact-two-action-sequence"
                                        and [action.get("tag") for action in
                                             condition.get("actions") or []]
                                            == (native.get("twoDirectionAngleCondition") or {})
                                                .get("selectedActionTags"))
                                )
                                and processor_tag == (native.get("processor") or {}).get("unionTag")
                                and text_native.get("status") == "validated"
                                and pair_second.get("status") == "named-direct-members-exact-span"
                                and pair_second.get("wholeStoredSpanExact") is True
                                and pair_second.get("recursiveNamedSchemaExact") is True
                                and pair_second.get("unionTag") == text_native.get("unionTag")
                                and pair_second.get("start") == processor_child.get("end")
                                and parent_processor_field.get("count") == 2
                                and [row.get("tag") for row in parent_processors] == [5, 6]
                                and len(parent_processors) == 2
                                and processor_child.get("start") == parent_processors[0].get("start")
                                and processor_child.get("end") == parent_processors[0].get("end")
                                and pair_second.get("start") == parent_processors[1].get("start")
                                and pair_second.get("end") == parent_processors[1].get("end")
                                and pair_second.get("end") == parent_processor_field.get("end")
                                and [field.get("name") for field in pair_second.get("namedFields") or []]
                                    == [field.get("name") for field in text_native.get("fieldPlan", [])]
                            )
                        )
                        and (condition_count != 2
                             or (processor_pair
                                 and action_tags == (native.get("twoDirectionAngleCondition") or {})
                                     .get("selectedActionTags"))
                             or (not processor_pair
                                 and (processor_tag == (native.get("processor") or {}).get("unionTag")
                                      or (processor_tag == 4
                                          and action_tags == (native.get("notNextMainCondition") or {})
                                          .get("selectedActionTags")))))
                    )
                    if (root_receipt is not None
                            or any((native.get(name) or {}).get("status") != "validated"
                                   for name in ("damageModifier", "processor",
                                                "processorModifyCalc", "processorScalar",
                                                "processorText", "twoActionCondition",
                                                "condition",
                                                "checkDecorateMaskCondition",
                                                "checkDamageTypeCondition",
                                                "checkDamageTypeMaskCondition",
                                                "checkTagMatchCondition",
                                                "checkMainCharacterCondition",
                                                "checkBuffStackCondition",
                                                "checkVitalsCondition",
                                                "originOrCondition",
                                                "knownCompoundCondition",
                                                "ifElseCondition",
                                                "notNextMainCondition",
                                                "twoDirectionAngleCondition",
                                                "processorInstantModifyAttribute"))
                            or fields[6].get("name") != "damageModifier"
                            or fields[6].get("count") != 1
                            or damage.get("status") != "exact-composed-damage-list"
                            or damage.get("wholeListExact") is not True
                            or damage.get("startOffset") != fields[6].get("start")
                            or damage.get("consumedEnd") != fields[6].get("end")
                            or len(parent_fields) != 3
                            or condition.get("start") != parent_fields[0].get("start")
                            or condition.get("end") != parent_fields[0].get("end")
                            or not condition_exact
                            or not processor_exact):
                        raise ValueError(f"BuffData positive damage root receipt is incomplete: {virtual_path!r}")
                elif create_action:
                    action = fields[0].get("action") or {}
                    if (root_receipt is not None or positive_receipt is not None
                            or fields[0].get("count") != 1
                            or action.get("recursiveStoredSchemaExact") is not True
                            or (action.get("parent") or {}).get("tag") != 0x0092
                            or (action.get("iconDuration") or {}).get("wholeStoredSpanExact") is not True
                            or (action.get("inputList") or {}).get("wholeStoredSpanExact") is not True
                            or (action.get("blackboard") or {}).get("wholeProviderByteSpanExact") is not True):
                        raise ValueError(f"BuffData single CreateBuff root receipt is incomplete: {virtual_path!r}")
                elif positive_receipt is not None or create_receipt is not None:
                    raise ValueError(f"BuffData exact root branch has duplicate receipt: {virtual_path!r}")
            elif (root_receipt is not None or positive_receipt is not None or create_receipt is not None
                  or row.get("rootNoPositiveCandidate") is True and row.get("namedOuterFrameStatus") == "named_exact_full"
                  or row.get("rootPositiveDamageCandidate") is True
                  or row.get("rootSingleCreateActionCandidate") is True):
                raise ValueError(f"BuffData unpromoted row carries an exact root receipt: {virtual_path!r}")
            detail = {
                "boundaryClass": row.get("boundaryClass"),
                "coverageStatus": row.get("coverageStatus"),
                "eventPrefixStatus": row.get("eventPrefixStatus"),
                "rootContinuationStatus": row.get("rootContinuationStatus"),
                "namedOuterFrameStatus": row.get("namedOuterFrameStatus"),
                "wholeSchemaExact": row.get("wholeSchemaExact"),
                "rootNoPositiveReceiptStatus": (root_receipt or {}).get("status"),
                "rootPositiveDamageReceiptStatus": (positive_receipt or {}).get("status"),
                "rootPositiveDamageConditionStatus": positive_condition_status,
                "rootSingleCreateActionReceiptStatus": (create_receipt or {}).get("status"),
            }
        else:
            prefix_ok = bool(row.get("commonPrefixFraming", {}).get("provenPrefixByteLength"))
            ambiguous = (
                row.get("boundaryClass") == "ambiguous"
                and row.get("coverageStatus") == "ambiguous-disjoint-independent-ranges"
            )
            selected = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-terminal-selection-disjoint-independent-ranges"
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
            )
            exact_empty = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-empty-action-group-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and row.get("emptyActionGroupProfile", {}).get("status")
                == "verified-exact-through-field-42"
                and not row.get("opaqueByteRanges")
            )
            exact_timeline = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-timeline-play-animation-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and (row.get("timelinePlayAnimationProfile") or {}).get("status")
                == "verified-exact-first-timeline-play-animation-record"
                and (row.get("timelinePlayAnimationProfile") or {})
                .get("topLevelContinuation", {}).get("status")
                == "verified-exact-through-field-42"
                and not row.get("opaqueByteRanges")
            )
            partial_empty = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-empty-action-group-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("emptyActionGroupProfile", {}).get("status")
                == "verified-exact-through-field-41"
            )
            action_group = row.get("actionGroupPrefix", {})
            named_action_group = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-action-group-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and action_group.get("status") == "verified-named-prefix"
                and action_group.get("fieldIndex") == 0
                and action_group.get("fieldName") == "actionGroupData"
                and action_group.get("memberOrder")
                == ["passiveEventActions", "timelineActions"]
                and action_group.get("parserCursor") in (6, 10)
                and action_group.get("byteLength") == action_group.get("parserCursor") - 1
                and action_group.get("openChildList")
                in ("passiveEventActions", "timelineActions")
                and action_group.get("wholeFieldExact") is False
            )
            timeline_play_animation = row.get("timelinePlayAnimationProfile") or {}
            named_timeline_play_animation = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-play-animation-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and timeline_play_animation.get("status")
                == "verified-exact-first-timeline-play-animation-record"
                and type(timeline_play_animation.get("parserCursor")) is int
                and timeline_play_animation.get("parserCursor") > 10
                and timeline_play_animation.get("newNamedBytesAfterPriorPrefix")
                == timeline_play_animation.get("parserCursor") - 10
                and timeline_play_animation.get("wholeTimelineListExact") is False
            )
            timeline_play_animation_step = (
                row.get("timelinePlayAnimationStepProfile") or {}
            )
            step_record = timeline_play_animation_step.get("firstTimelineAction") or {}
            step_sequence = step_record.get("sequenceActionData") or {}
            step_actions = step_sequence.get("actionData") or []
            step_profile_exact = (
                timeline_play_animation_step.get("status")
                == "verified-exact-first-timeline-play-animation-step-record"
                and type(timeline_play_animation_step.get("parserCursor")) is int
                and timeline_play_animation_step.get("parserCursor") > 10
                and timeline_play_animation_step.get("newNamedBytesAfterPriorPrefix")
                == timeline_play_animation_step.get("parserCursor") - 10
                and step_record.get("wholeRecordExact") is True
                and step_sequence.get("actionDataCount") == 1
                and isinstance(step_actions, list)
                and len(step_actions) == 1
                and step_actions[0].get("tag") == 0x0116
                and step_actions[0].get("memberCount") == 30
                and step_actions[0].get("wholeActionExact") is True
            )
            named_timeline_play_animation_step = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-play-animation-step-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and row.get("parserCursor")
                == timeline_play_animation_step.get("parserCursor")
                and timeline_play_animation_step.get("wholeTimelineListExact") is False
                and timeline_play_animation_step.get("wholeActionGroupDataExact") is False
                and step_profile_exact
            )
            exact_timeline_play_animation_step = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-timeline-play-animation-step-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and timeline_play_animation_step.get("wholeTimelineListExact") is True
                and timeline_play_animation_step.get("wholeActionGroupDataExact") is True
                and timeline_play_animation_step.get("topLevelContinuation", {}).get(
                    "status"
                ) == "verified-exact-through-field-42"
                and step_profile_exact
                and not row.get("opaqueByteRanges")
            )
            timeline_create_buff = row.get("timelineCreateBuffProfile") or {}
            create_buff_record = timeline_create_buff.get("firstTimelineAction") or {}
            create_buff_sequence = create_buff_record.get("sequenceActionData") or {}
            create_buff_actions = create_buff_sequence.get("actionData") or []
            create_buff_action_exact = (
                type(timeline_create_buff.get("parserCursor")) is int
                and timeline_create_buff.get("parserCursor") > 10
                and timeline_create_buff.get("newNamedBytesAfterPriorPrefix")
                == timeline_create_buff.get("parserCursor") - 10
                and isinstance(create_buff_actions, list)
                and len(create_buff_actions) == 1
                and create_buff_actions[0].get("tag") == 0x0092
                and create_buff_actions[0].get("memberCount") == 19
                and create_buff_actions[0].get("wholeActionExact") is True
            )
            named_timeline_create_buff_action = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-create-buff-first-action-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and row.get("parserCursor") == timeline_create_buff.get("parserCursor")
                and timeline_create_buff.get("status")
                == "verified-exact-first-timeline-create-buff-action"
                and create_buff_sequence.get("actionDataCount", 0) > 1
                and create_buff_sequence.get("wholeListExact") is False
                and create_buff_record.get("wholeRecordExact") is False
                and timeline_create_buff.get("wholeFirstTimelineActionExact") is False
                and timeline_create_buff.get("wholeTimelineListExact") is False
                and timeline_create_buff.get("wholeActionGroupDataExact") is False
                and create_buff_action_exact
            )
            named_timeline_create_buff_record = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-create-buff-first-record-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and row.get("parserCursor") == timeline_create_buff.get("parserCursor")
                and timeline_create_buff.get("status")
                == "verified-exact-first-timeline-create-buff-record"
                and create_buff_sequence.get("actionDataCount") == 1
                and create_buff_sequence.get("wholeListExact") is True
                and create_buff_record.get("wholeRecordExact") is True
                and timeline_create_buff.get("wholeFirstTimelineActionExact") is True
                and timeline_create_buff.get("wholeTimelineListExact") is False
                and timeline_create_buff.get("wholeActionGroupDataExact") is False
                and create_buff_action_exact
            )
            exact_timeline_create_buff = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-timeline-create-buff-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and (
                    timeline_create_buff.get("status")
                    == "verified-exact-first-timeline-create-buff-record"
                    or _exact_create_buff_later_records(
                        timeline_create_buff, create_buff_record
                    )
                )
                and create_buff_sequence.get("actionDataCount") == 1
                and create_buff_sequence.get("wholeListExact") is True
                and create_buff_record.get("wholeRecordExact") is True
                and timeline_create_buff.get("wholeFirstTimelineActionExact") is True
                and timeline_create_buff.get("wholeTimelineListExact") is True
                and timeline_create_buff.get("wholeActionGroupDataExact") is True
                and timeline_create_buff.get("topLevelContinuation", {}).get("status")
                == "verified-exact-through-field-42"
                and create_buff_action_exact
                and not row.get("opaqueByteRanges")
            )
            timeline_find_target = row.get("timelineFindTargetProfile") or {}
            find_target_record = timeline_find_target.get("firstTimelineAction") or {}
            find_target_sequence = find_target_record.get("sequenceActionData") or {}
            find_target_actions = find_target_sequence.get("actionData") or []
            named_timeline_find_target = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-find-target-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and timeline_find_target.get("status")
                == "verified-exact-first-timeline-find-target-record"
                and type(timeline_find_target.get("parserCursor")) is int
                and timeline_find_target.get("parserCursor") > 10
                and row.get("parserCursor") == timeline_find_target.get("parserCursor")
                and timeline_find_target.get("newNamedBytesAfterPriorPrefix")
                == timeline_find_target.get("parserCursor") - 10
                and timeline_find_target.get("wholeTimelineListExact") is False
                and find_target_record.get("wholeRecordExact") is True
                and find_target_sequence.get("actionDataCount") == 1
                and isinstance(find_target_actions, list)
                and len(find_target_actions) == 1
                and find_target_actions[0].get("tag") == 0x00B2
                and find_target_actions[0].get("memberCount") == 18
                and find_target_actions[0].get("wholeActionExact") is True
            )
            timeline_continuous_find_target = (
                row.get("timelineContinuousFindTargetProfile") or {}
            )
            continuous_record = timeline_continuous_find_target.get(
                "firstTimelineAction"
            ) or {}
            continuous_sequence = continuous_record.get("sequenceActionData") or {}
            continuous_actions = continuous_sequence.get("actionData") or []
            named_timeline_continuous_find_target = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-continuous-find-target-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and timeline_continuous_find_target.get("status")
                == "verified-exact-first-timeline-continuous-find-target-record"
                and type(timeline_continuous_find_target.get("parserCursor")) is int
                and timeline_continuous_find_target.get("parserCursor") > 10
                and row.get("parserCursor")
                == timeline_continuous_find_target.get("parserCursor")
                and timeline_continuous_find_target.get("newNamedBytesAfterPriorPrefix")
                == timeline_continuous_find_target.get("parserCursor") - 10
                and timeline_continuous_find_target.get("wholeTimelineListExact") is False
                and continuous_record.get("wholeRecordExact") is True
                and continuous_sequence.get("actionDataCount") == 1
                and isinstance(continuous_actions, list)
                and len(continuous_actions) == 1
                and continuous_actions[0].get("tag") == 0x008A
                and continuous_actions[0].get("memberCount") == 19
                and continuous_actions[0].get("wholeActionExact") is True
            )
            timeline_shared_sequence = row.get("timelineSharedSequenceProfile") or {}
            shared_record = timeline_shared_sequence.get("firstTimelineAction") or {}
            shared_actions = shared_record.get("actionData") or []
            shared_profile_exact = (
                timeline_shared_sequence.get("status")
                == "verified-exact-first-timeline-shared-sequence-record"
                and type(timeline_shared_sequence.get("parserCursor")) is int
                and timeline_shared_sequence.get("parserCursor") > 10
                and timeline_shared_sequence.get("newNamedBytesAfterPriorPrefix")
                == timeline_shared_sequence.get("parserCursor") - 10
                and shared_record.get("wholeRecordExact") is True
                and isinstance(shared_actions, list)
                and bool(shared_actions)
                and all(
                    type(action.get("tag")) is int
                    and isinstance(action.get("typeName"), str)
                    and action.get("typeName")
                    and type(action.get("memberCount")) is int
                    and action.get("structurallyExact") is True
                    and type(action.get("start")) is int
                    and type(action.get("end")) is int
                    and action["end"] > action["start"]
                    for action in shared_actions
                )
            )
            named_timeline_shared_sequence = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-shared-sequence-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and row.get("parserCursor")
                == timeline_shared_sequence.get("parserCursor")
                and (
                    (
                        timeline_shared_sequence.get("wholeTimelineListExact") is False
                        and timeline_shared_sequence.get("wholeActionGroupDataExact") is False
                    )
                    or (
                        timeline_shared_sequence.get("wholeTimelineListExact") is True
                        and timeline_shared_sequence.get("wholeActionGroupDataExact") is True
                        and timeline_shared_sequence.get("topLevelContinuation", {}).get("status")
                        == "stopped-at-unsupported-top-level-field"
                    )
                )
                and shared_profile_exact
            )
            exact_timeline_shared_sequence = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-timeline-shared-sequence-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and timeline_shared_sequence.get("wholeTimelineListExact") is True
                and timeline_shared_sequence.get("wholeActionGroupDataExact") is True
                and timeline_shared_sequence.get("topLevelContinuation", {}).get(
                    "status"
                ) == "verified-exact-through-field-42"
                and shared_profile_exact
                and not row.get("opaqueByteRanges")
            )
            exact_capture_target = (
                capture_target_reference is not None
                and row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus") == "verified-whole-schema-exact-capture-target"
                and row.get("wholeSchemaExact") is True
                and isinstance(row.get("framing"), dict)
                and row["framing"].get("wholeSchemaExact") is True
                and row.get("parserCursor") == row.get("length")
                and isinstance(row.get("boundaryContext"), dict)
                and row["boundaryContext"].get("parserCursor") == row.get("length")
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding") == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and row.get("emptyActionGroupProfile", {}).get("status")
                == "verified-exact-through-field-42"
                and not row.get("opaqueByteRanges")
                and capture_target_reference["target"] == {
                    "virtualPath": virtual_path,
                    "length": row.get("length"),
                    "logicalSha256": row.get("logicalSha256"),
                }
            )
            target_set_metadata, target_set_targets = (
                capture_target_set_reference if capture_target_set_reference is not None else (None, {})
            )
            exact_capture_target_set = (
                target_set_metadata is not None
                and row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus") == "verified-whole-schema-exact-capture-target-set"
                and row.get("wholeSchemaExact") is True
                and isinstance(row.get("framing"), dict)
                and row["framing"].get("wholeSchemaExact") is True
                and row.get("parserCursor") == row.get("length")
                and isinstance(row.get("boundaryContext"), dict)
                and row["boundaryContext"].get("parserCursor") == row.get("length")
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding") == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and not row.get("opaqueByteRanges")
                and _skill_capture_target_set_row_exact(
                    row, target_set_targets.get(virtual_path)
                )
            )
            passive_shared_sequence = row.get("passiveSharedSequenceProfile") or {}
            passive_actions = passive_shared_sequence.get("actionData")
            exact_passive_shared_sequence = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-passive-shared-sequence-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and passive_shared_sequence.get("status")
                == "verified-exact-passive-shared-sequence-list"
                and type(passive_shared_sequence.get("passiveEventActionsCount")) is int
                and passive_shared_sequence["passiveEventActionsCount"] > 0
                and passive_shared_sequence.get("timelineActionsCount") == 0
                and passive_shared_sequence.get("wholeActionGroupDataExact") is True
                and passive_shared_sequence.get("topLevelContinuation", {}).get(
                    "status"
                ) == "verified-exact-through-field-42"
                and isinstance(passive_actions, list)
                and all(
                    isinstance(action, dict)
                    and type(action.get("tag")) is int
                    and isinstance(action.get("typeName"), str)
                    and bool(action["typeName"])
                    and type(action.get("start")) is int
                    and type(action.get("end")) is int
                    and action["end"] > action["start"]
                    and action.get("structurallyExact") is True
                    for action in passive_actions
                )
                and not row.get("opaqueByteRanges")
            )
            if not prefix_ok or not (
                ambiguous
                or selected
                or exact_empty
                or exact_capture_target
                or exact_capture_target_set
                or exact_timeline
                or partial_empty
                or named_action_group
                or named_timeline_play_animation
                or named_timeline_play_animation_step
                or exact_timeline_play_animation_step
                or named_timeline_create_buff_action
                or named_timeline_create_buff_record
                or exact_timeline_create_buff
                or named_timeline_find_target
                or named_timeline_continuous_find_target
                or named_timeline_shared_sequence
                or exact_timeline_shared_sequence
                or exact_passive_shared_sequence
            ):
                coverage = row.get("coverageStatus")
                raise SkillEvidenceContractError({
                    "validator": "jsondata_corpus._load_family_evidence",
                    "gate": "skill-bounded-structural-contract",
                    "virtualPath": virtual_path,
                    "sourceSha256": row.get("logicalSha256"),
                    "inputSetSha256": row.get("inputSetSha256"),
                    "failedPredicate": (
                        "common_prefix"
                        if not prefix_ok else SKILL_STATUS_PREDICATES.get(
                            coverage, "known_coverage_status"
                        )
                    ),
                    "actual": {
                        "boundaryClass": row.get("boundaryClass"),
                        "coverageStatus": coverage,
                        "terminalSelectionStatus": (
                            row.get("terminalSelection") or {}
                        ).get("status"),
                        "wholeSchemaExact": row.get("wholeSchemaExact"),
                        "timelineCreateBuffProfileStatus": timeline_create_buff.get("status"),
                        "passiveSharedSequenceProfileStatus": passive_shared_sequence.get("status"),
                        "commonPrefixByteLength": (
                            row.get("commonPrefixFraming") or {}
                        ).get("provenPrefixByteLength"),
                    },
                })
            logical_md5 = row.get("logicalMd5")
            detail = {
                "boundaryClass": row.get("boundaryClass"),
                "coverageStatus": row.get("coverageStatus"),
                "provenPrefixByteLength": row["commonPrefixFraming"]["provenPrefixByteLength"],
                "terminalCandidateCount": len(row.get("candidateCoverage", [])),
                "terminalSelection": row.get("terminalSelection"),
                "wholeSchemaExact": row.get("wholeSchemaExact"),
                "emptyActionGroupProfileStatus": row.get("emptyActionGroupProfile", {}).get("status"),
                "actionGroupPrefix": action_group if named_action_group else None,
                "timelinePlayAnimationProfile": (
                    timeline_play_animation
                    if named_timeline_play_animation or exact_timeline
                    else None
                ),
                "timelinePlayAnimationStepProfile": (
                    timeline_play_animation_step
                    if named_timeline_play_animation_step
                    or exact_timeline_play_animation_step
                    else None
                ),
                "timelineCreateBuffProfile": (
                    timeline_create_buff
                    if named_timeline_create_buff_action
                    or named_timeline_create_buff_record
                    or exact_timeline_create_buff
                    else None
                ),
                "timelineFindTargetProfile": (
                    timeline_find_target if named_timeline_find_target else None
                ),
                "timelineContinuousFindTargetProfile": (
                    timeline_continuous_find_target
                    if named_timeline_continuous_find_target
                    else None
                ),
                "timelineSharedSequenceProfile": (
                    timeline_shared_sequence
                    if named_timeline_shared_sequence
                    or exact_timeline_shared_sequence
                    else None
                ),
                "passiveSharedSequenceProfile": (
                    passive_shared_sequence if exact_passive_shared_sequence else None
                ),
            }
            if exact_capture_target:
                detail["captureTargetVerification"] = capture_target_reference
            if exact_capture_target_set:
                detail["captureTargetSetVerification"] = target_set_metadata
        evidence[virtual_path] = {
            "length": identity.get("length"),
            "logicalMd5": logical_md5,
            "logicalSha256": row.get("logicalSha256"),
            "detail": detail,
            "rootNoPositiveReceipt": root_receipt if family == "BuffData" else None,
            "rootPositiveDamageReceipt": positive_receipt if family == "BuffData" else None,
            "rootSingleCreateActionReceipt": create_receipt if family == "BuffData" else None,
        }

    if set(evidence) != expected_paths:
        missing = sorted(expected_paths - set(evidence))
        extra = sorted(set(evidence) - expected_paths)
        raise ValueError(
            f"{family} evidence paths do not match the current ledger; "
            f"missing={missing[:1]!r}; extra={extra[:1]!r}"
        )
    summary = report.get("summary", {})
    if summary.get("filesSelected") != len(expected_paths) or summary.get("filesSucceeded") != len(expected_paths):
        raise ValueError(f"{family} evidence summary does not match its file rows")
    metadata = {
        "path": path.resolve().as_posix(),
        "length": path.stat().st_size,
        "sha256": _sha256_path(path),
        "format": report["format"],
        "identitySetSha256": report.get("identitySetSha256"),
    }
    return evidence, metadata


def _run_reader(
    reader: Callable[[bytes], Any],
    data: bytes,
    errors: tuple[type[Exception], ...],
) -> tuple[bool, dict[str, Any] | None, str | None]:
    try:
        result = reader(data)
    except errors as exc:
        return False, None, str(exc)
    summary: dict[str, Any] = {}
    if isinstance(result, dict):
        for key in (
            "status", "schemaStatus", "bytesConsumed", "waveCount", "actionCount",
            "configId", "enemyLibraryCount", "enemyLibraryEndOffset", "routeMapCount",
            "waveMapOffset", "entryCount",
            "levelCount", "trackingRouteCount", "npcIdLutCount", "npcProxyCount",
            "worldEntityBriefCount", "worldEntityConfigCount", "opaqueRemainderOffset",
            "opaqueRemainderLength", "barCount", "envVfxCount", "veinCount",
            "midpointCount", "intervalCount", "activeTagCount", "collectionCount",
            "propertyCount", "atomCount", "taskCount",
            "missionId", "questCount", "typedSchemaCount", "dynamicDictionaryCount",
            "objectCount", "taggedObjectCount", "arrayCount", "scalarCount", "maxDepth",
        ):
            if key in result:
                summary[key] = result[key]
        task_diagnostics = result.get("taskDiagnostics")
        if (
            result.get("schemaStatus") == "partial"
            and isinstance(task_diagnostics, list)
            and task_diagnostics
            and isinstance(task_diagnostics[0], dict)
        ):
            first = task_diagnostics[0]
            summary["firstStopDiagnostic"] = {
                key: first[key]
                for key in (
                    "gate", "taskKey", "conditionKey", "conditionIndex",
                    "conditionOffset", "conditionUnionTag",
                    "serializedMemberCount", "expectedConditionType",
                    "expectedSerializedMemberCount", "nativeMappingId",
                )
                if key in first
            }
        action_map = result.get("actionMap")
        if result.get("schemaStatus") == "partial" and isinstance(action_map, dict):
            reason = action_map.get("unresolvedReason")
            if isinstance(reason, str):
                summary["firstStopReason"] = reason[:512]
    return True, summary, None


def _classify_binary(relative: str, family: str, data: bytes) -> dict[str, Any]:
    if family == "LipSync":
        ok, detail, diagnostic = _run_reader(
            decode_lipsync_memorypack, data, (LipSyncDecodeError, ValueError)
        )
        return {
            "status": "schema_decoded" if ok else "unsupported",
            "reader": "scripts.game_data.memorypack.lipsync",
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative.startswith("NPC/MontageJson/MontageNew/"):
        ok, detail, diagnostic = _run_reader(
            frame_npc_montage, data, (NpcMontageFramingError, ValueError)
        )
        return {
            "status": (
                "schema_decoded"
                if ok and detail and detail.get("schemaStatus") == "named_exact"
                else "format_framed" if ok else "unsupported"
            ),
            "reader": "scripts.game_data.memorypack.npc_montage",
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "CharInteractPerformCfgs":
        ok, detail, diagnostic = _run_reader(
            decode_char_interact_complete_frame,
            data,
            (CharInteractPerformDecodeError, ValueError),
        )
        if ok:
            return {
                "status": (
                    "schema_decoded"
                    if detail and detail.get("schemaStatus") == "named_exact"
                    else "format_framed"
                ),
                "reader": "scripts.game_data.char_interact_perform_binary.decode_char_interact_complete_frame",
                "detail": detail,
                "diagnostic": None,
            }
        prefix_ok, prefix_detail, prefix_diagnostic = _run_reader(
            frame_char_interact_prefix,
            data,
            (CharInteractPerformDecodeError, ValueError),
        )
        return {
            "status": "bounded_partial" if prefix_ok else "unsupported",
            "reader": "scripts.game_data.char_interact_perform_binary.frame_char_interact_prefix" if prefix_ok else None,
            "detail": prefix_detail,
            "diagnostic": prefix_diagnostic or diagnostic,
        }
    if family == "SpawnerConfig":
        prefix_ok, prefix_detail, prefix_diagnostic = _run_reader(
            decode_spawner_named_prefix,
            data,
            (SpawnerEnemyLibraryDecodeError, ValueError),
        )
        if prefix_ok:
            assert prefix_detail is not None
            try:
                wave_detail = decode_spawner_wave_map_sequential(
                    data,
                    wave_map_offset=int(prefix_detail["waveMapOffset"]),
                )
                action_tags: dict[str, int] = {}
                for wave in wave_detail["waves"]:
                    for group in wave["groupMap"]:
                        for action in group["actionMap"]:
                            key = str(action["unionTag"])
                            action_tags[key] = action_tags.get(key, 0) + 1
                return {
                    "status": "schema_decoded",
                    "reader": (
                        "scripts.game_data.spawner_binary.decode_spawner_named_prefix+"
                        "decode_spawner_wave_map_sequential"
                    ),
                    "detail": {
                        "configId": prefix_detail["configId"],
                        "enemyLibraryCount": prefix_detail["enemyLibraryCount"],
                        "routeMapCount": prefix_detail["routeMapCount"],
                        "waveMapOffset": prefix_detail["waveMapOffset"],
                        "waveCount": wave_detail["waveCount"],
                        "actionUnionTagCounts": action_tags,
                        "schemaStatus": wave_detail["schemaStatus"],
                    },
                    "diagnostic": None,
                }
            except (SpawnerWaveDecodeError, ValueError) as exc:
                return {
                    "status": "bounded_partial",
                    "reader": "scripts.game_data.spawner_binary.decode_spawner_named_prefix",
                    "detail": {
                        "configId": prefix_detail["configId"],
                        "enemyLibraryCount": prefix_detail["enemyLibraryCount"],
                        "routeMapCount": prefix_detail["routeMapCount"],
                        "waveMapOffset": prefix_detail["waveMapOffset"],
                        "schemaStatus": prefix_detail["schemaStatus"],
                    },
                    "diagnostic": str(exc),
                }
        wave_ok, wave_detail, wave_diagnostic = _run_reader(
            decode_spawner_wave_map, data, (SpawnerWaveDecodeError, ValueError)
        )
        if wave_ok:
            return {
                "status": "schema_decoded",
                "reader": "scripts.game_data.spawner_binary.decode_spawner_wave_map",
                "detail": wave_detail,
                "diagnostic": None,
            }
        enemy_ok, enemy_detail, enemy_diagnostic = _run_reader(
            decode_spawner_enemy_library,
            data,
            (SpawnerEnemyLibraryDecodeError, ValueError),
        )
        return {
            "status": "bounded_partial" if enemy_ok else "unclassified_binary",
            "reader": (
                "scripts.game_data.spawner_binary.decode_spawner_enemy_library"
                if enemy_ok else None
            ),
            "detail": enemy_detail,
            "diagnostic": enemy_diagnostic or prefix_diagnostic or wave_diagnostic,
        }
    if family == "AnimationConfig":
        ok, detail, diagnostic = _run_reader(
            frame_animation_config, data, (AnimationConfigFramingError, ValueError)
        )
        status = "unclassified_binary"
        if ok and detail and detail.get("schemaStatus") == "named_exact":
            status = "schema_decoded"
        elif ok and detail and detail.get("schemaStatus") == "anonymous_exact_frame":
            status = "format_framed_anonymous"
        elif ok:
            status = "bounded_partial"
        return {
            "status": status,
            "reader": "scripts.game_data.animation_config_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "LevelScriptData":
        for reader in (
            frame_levelscript_empty_action_map_sequential,
            frame_levelscript_null_action_map_sequential,
            frame_levelscript_single_call_server_leader_enter,
            frame_levelscript_current_action_sequence_leader_enter,
            frame_levelscript_terminal_suffix,
            frame_levelscript_empty_action_map_top_level,
            frame_levelscript_action_map_named_prefix,
            frame_levelscript_empty_action_map_prefix,
        ):
            ok, detail, diagnostic = _run_reader(
                reader, data, (LevelScriptTopLevelFramingError, ValueError)
            )
            if ok:
                return {
                    "status": (
                        "schema_decoded"
                        if detail and detail.get("schemaStatus") == "named_exact"
                        else "bounded_partial"
                    ),
                    "reader": f"scripts.game_data.levelscript_binary.{reader.__name__}",
                    "detail": detail,
                    "diagnostic": None,
                }
        return {
            "status": "unclassified_binary",
            "reader": None,
            "detail": None,
            "diagnostic": diagnostic,
        }
    if family == "LevelData":
        ok, detail, diagnostic = _run_reader(
            frame_leveldata_named_prefix,
            data,
            (LevelDataTopLevelFramingError, ValueError),
        )
        if ok:
            return {
                "status": (
                    "schema_decoded"
                    if detail and detail.get("schemaStatus") == "named_exact"
                    else "format_framed"
                    if detail and detail.get("schemaStatus") == "named_exact_frame"
                    else "bounded_partial"
                ),
                "reader": "scripts.game_data.leveldata_binary.frame_leveldata_named_prefix",
                "detail": detail,
                "diagnostic": None,
            }
        for reader in (
            frame_leveldata_empty_tail,
            frame_leveldata_terminal_suffix,
            frame_leveldata_airwalls_prefix,
        ):
            ok, detail, diagnostic = _run_reader(
                reader, data, (LevelDataTopLevelFramingError, ValueError)
            )
            if ok:
                return {
                    "status": "bounded_partial",
                    "reader": f"scripts.game_data.leveldata_binary.{reader.__name__}",
                    "detail": detail,
                    "diagnostic": None,
                }
        return {
            "status": "unclassified_binary",
            "reader": None,
            "detail": None,
            "diagnostic": diagnostic,
        }
    if family == "LevelConfig":
        ok, detail, diagnostic = _run_reader(
            decode_level_config, data, (LevelConfigDecodeError, ValueError)
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.levelconfig_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "LevelScriptTemplateData":
        ok, detail, diagnostic = _run_reader(
            frame_levelscript_template,
            data,
            (LevelScriptTemplateFramingError, ValueError),
        )
        return {
            "status": (
                "schema_decoded"
                if ok and detail and detail.get("schemaStatus") == "named_exact"
                else "bounded_partial" if ok else "unclassified_binary"
            ),
            "reader": "scripts.game_data.levelscript_template_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "AtmosphericNpcData":
        ok, detail, diagnostic = _run_reader(
            frame_atmospheric_npc_table,
            data,
            (AtmosphericNpcFramingError, ValueError),
        )
        status = "unclassified_binary"
        if ok and detail and detail.get("schemaStatus") in ("exact", "named_exact"):
            status = "schema_decoded"
        elif ok and detail and detail.get("schemaStatus") == "named_exact_frame":
            status = "format_framed"
        elif ok:
            status = "format_framed_anonymous"
        return {
            "status": status,
            "reader": "scripts.game_data.atmospheric_npc_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == "NonGeneratedConfigs/BambooRaftTaskTable.json":
        decoded = decode_bamboo_raft_task_table_memorypack(
            BAMBOO_RAFT_TASK_TABLE_REL, data, len(data)
        )
        return {
            "status": "schema_decoded" if decoded is not None else "unclassified_binary",
            "reader": "scripts.game_data.memorypack.tables" if decoded is not None else None,
            "detail": (
                {
                    "subtype": decoded.get("subtype"),
                    "rows": decoded.get("rows"),
                    "exactLength": decoded.get("decoded", {}).get("exactLength"),
                }
                if decoded is not None else None
            ),
            "diagnostic": None if decoded is not None else "current exact table reader rejected payload",
        }
    if relative == "NonGeneratedConfigs/MatrixShockWaveBeatConfigTable.json":
        ok, detail, diagnostic = _run_reader(
            decode_matrix_shockwave_table,
            data,
            (MatrixShockWaveDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.matrix_shockwave_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == "GameplayConfig/AetherEnergyLockConfigTable.json":
        ok, detail, diagnostic = _run_reader(
            decode_aether_energy_lock_table,
            data,
            (AetherEnergyLockDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.aether_energy_lock_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative in {
        "GPUISystemConfig/buff_icon.json",
        "GPUISystemConfig/buff_icon_main.json",
        "GPUISystemConfig/outscreen_target.json",
    }:
        ok, detail, diagnostic = _run_reader(
            decode_gpu_ui_root16, data, (GpuUiFramingError, ValueError)
        )
        reader = "scripts.game_data.gpu_ui_binary.decode_gpu_ui_root16"
        if not ok:
            ok, detail, diagnostic = _run_reader(
                frame_gpu_ui_root16_prefix, data, (GpuUiFramingError, ValueError)
            )
            reader = "scripts.game_data.gpu_ui_binary.frame_gpu_ui_root16_prefix"
        return {
            "status": (
                "schema_decoded"
                if ok and detail and detail.get("schemaStatus") == "named_exact"
                else "bounded_partial" if ok else "unclassified_binary"
            ),
            "reader": reader if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == DAMAGE_TEXT_REL.removeprefix("Json/"):
        ok, detail, diagnostic = _run_reader(
            decode_damage_text, data, (GpuUiFramingError, ValueError)
        )
        reader = "scripts.game_data.gpu_ui_binary.decode_damage_text"
        schema_exact = ok
        if not ok:
            ok, detail, framing_diagnostic = _run_reader(
                frame_damage_text, data, (GpuUiFramingError, ValueError)
            )
            reader = "scripts.game_data.gpu_ui_binary.frame_damage_text"
            if not ok:
                diagnostic = framing_diagnostic
        return {
            "status": "schema_decoded" if schema_exact else "format_framed" if ok else "unclassified_binary",
            "reader": reader if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == DIALOG_ID_TABLE_REL.removeprefix("Json/"):
        decoded = decode_dialog_id_table_memorypack(DIALOG_ID_TABLE_REL, data, len(data))
        return {
            "status": "schema_decoded" if decoded is not None else "unclassified_binary",
            "reader": "scripts.game_data.memorypack.tables.decode_dialog_id_table_memorypack" if decoded is not None else None,
            "detail": (
                {"subtype": decoded.get("subtype"), "rows": decoded.get("rows"), "exactLength": True}
                if decoded is not None else None
            ),
            "diagnostic": None if decoded is not None else "current exact table reader rejected payload",
        }
    compact_readers = {
        "GameplayConfigMissionAreaTable.json": (decode_mission_area_table, "schema_decoded"),
        "GameplayConfigSubGameInstanceDataTable.json": (frame_subgame_table, "schema_decoded"),
        "GameplayConfigWorldEntityRegistry.json": (frame_world_entity_registry, "schema_decoded"),
    }
    if relative in compact_readers:
        reader, success_status = compact_readers[relative]
        ok, detail, diagnostic = _run_reader(
            reader, data, (GameplayCompactDecodeError, ValueError)
        )
        return {
            "status": success_status if ok else "unclassified_binary",
            "reader": f"scripts.game_data.gameplay_compact_binary.{reader.__name__}" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "NavMesh":
        reader = (
            decode_luna_area if relative.endswith("/LunaArea.json")
            else decode_navmesh_state_container
            if relative.endswith("/NavMeshStateContainer.json") else None
        )
        if reader is not None:
            ok, detail, diagnostic = _run_reader(
                reader, data, (NavMeshDecodeError, ValueError)
            )
            return {
                "status": "schema_decoded" if ok else "unclassified_binary",
                "reader": f"scripts.game_data.navmesh_binary.{reader.__name__}" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
    if family == "GameplayConfig" and relative.endswith("TeleportValidationDataTable.json"):
        ok, detail, diagnostic = _run_reader(
            decode_teleport_validation_table,
            data,
            (TeleportValidationDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.teleport_validation_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative.startswith("Interactive/ModelViewStateControllerData/"):
        ok, detail, diagnostic = _run_reader(
            decode_model_view_state_controller,
            data,
            (InteractiveBinaryDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unsupported",
            "reader": "scripts.game_data.interactive_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == "Interactive/InteractiveTable.json":
        ok, detail, diagnostic = _run_reader(
            decode_interactive_table,
            data,
            (InteractiveBinaryDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.interactive_binary.decode_interactive_table" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative.startswith("Interactive/InteractiveData/"):
        try:
            decoded = decode_interactive_template_memorypack(
                Path(relative), data, len(data)
            )
            diagnostic = None
        except (ValueError, TypeError) as exc:
            decoded = None
            diagnostic = str(exc)
        return {
            "status": (
                "schema_decoded"
                if decoded is not None
                and decoded.get("decoded", {}).get("schemaStatus") == "named_exact"
                else "bounded_partial" if decoded is not None else "unclassified_binary"
            ),
            "reader": "scripts.game_data.memorypack.interactive" if decoded is not None else None,
            "detail": (
                {
                    "kind": decoded.get("kind"),
                    "subtype": decoded.get("subtype"),
                    "exactLength": decoded.get("decoded", {}).get("exactLength"),
                    "schemaStatus": decoded.get("decoded", {}).get("schemaStatus"),
                }
                if decoded is not None
                else None
            ),
            "diagnostic": diagnostic,
        }
    return {
        "status": "unclassified_binary",
        "reader": None,
        "detail": None,
        "diagnostic": None,
    }


def build_report(
    *,
    outer_path: Path,
    ledger_path: Path,
    export_root: Path,
    expected_input_set_sha256: str,
    buff_report_path: Path = DEFAULT_BUFF_REPORT,
    skill_report_path: Path = DEFAULT_SKILL_REPORT,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    expected = expected_input_set_sha256.upper()
    export_root = export_root.resolve()
    game_root, json_folder = _json_game_folder(export_root)
    outer, _header, ledger_rows, provenance = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected
    )
    selected = [
        row for row in ledger_rows
        if row.get("blockName") == "JsonData"
        and row.get("blockTypeValue") == 19
        and row.get("boundaryStatus") == "boundary_verified"
    ]
    selected.sort(key=lambda row: str(row["virtualPath"]))
    if not selected:
        raise ValueError("authenticated ledger has no JsonData rows")
    for row in selected:
        if row.get("inputSetSha256") != expected or row.get("status") != "verified":
            raise ValueError(
                f"JsonData ledger row is not current and verified: {row.get('virtualPath')!r}"
            )

    ledger_family_paths = {
        family: {
            str(row["virtualPath"])
            for row in selected
            if str(row["virtualPath"]).startswith(f"Data/Json/{family}/")
        }
        for family in FAMILY_REPORTS
    }
    family_evidence: dict[str, dict[str, dict[str, Any]]] = {}
    family_report_provenance: dict[str, dict[str, Any]] = {}
    for family, report_path in (
        ("BuffData", buff_report_path),
        ("SkillData", skill_report_path),
    ):
        evidence, metadata = _load_family_evidence(
            report_path,
            family=family,
            expected_input_set_sha256=expected,
            expected_paths=ledger_family_paths[family],
        )
        family_evidence[family] = evidence
        family_report_provenance[family] = metadata

    buff_native_validation = None
    buff_positive_damage_validation = None
    buff_single_create_validation = None
    if any(item["detail"].get("wholeSchemaExact") is True
           for item in family_evidence["BuffData"].values()):
        buff_native_validation = buff_root_no_positive.validate_current_native_contract()
        if buff_native_validation.get("status") != "validated":
            raise ValueError("BuffData exact root native validation is not current")
    if any(item.get("rootPositiveDamageReceipt") is not None
           for item in family_evidence["BuffData"].values()):
        buff_positive_damage_validation = buff_root_no_positive.validate_positive_damage_native_contract(
            root_validation=buff_native_validation,
        )
        if buff_positive_damage_validation.get("status") != "validated":
            raise ValueError("BuffData positive damage native validation is not current")
    if any(item.get("rootSingleCreateActionReceipt") is not None
           for item in family_evidence["BuffData"].values()):
        buff_single_create_validation = buff_create_action_root_receipt.validate_current_native_contract()
        if buff_single_create_validation.get("status") != "validated":
            raise ValueError("BuffData single CreateBuff native validation is not current")

    seen_paths: set[str] = set()
    results: list[dict[str, Any]] = []
    for ledger in selected:
        virtual_path = str(ledger["virtualPath"])
        _path, relative, family = _safe_export_path(export_root, virtual_path)
        if relative.casefold() in seen_paths:
            raise ValueError(f"case-insensitive duplicate JsonData export path: {relative}")
        seen_paths.add(relative.casefold())
        try:
            data = read_game_file(game_root, f"{json_folder}/{relative}")
        except FileNotFoundError:
            raise ValueError(f"missing JsonData export file: {relative}") from None
        expected_length = int(ledger["length"])
        expected_md5 = str(ledger["recomputedFileDataMd5"]).upper()
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != expected_length or actual_md5 != expected_md5:
            raise ValueError(
                f"JsonData export differs from VFS ledger: {relative}; "
                f"length={len(data)}/{expected_length}; md5={actual_md5}/{expected_md5}"
            )

        is_json, json_root = _classify_json(data)
        logical_sha256 = hashlib.sha256(data).hexdigest().upper()
        if is_json and is_npc_prefab_info_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_npc_prefab_info(payload, source=relative),
                data,
                (NpcPrefabInfoDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.npc_prefab_info" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_npc_catalog_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_npc_catalog(payload, source=relative),
                data,
                (NpcCatalogDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.npc_catalog" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_mission_runtime_main_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_mission_runtime_main(payload, source=relative),
                data,
                (MissionRuntimeMainDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.mission_runtime_main" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_mission_runtime_meta_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_mission_runtime_meta(payload, source=relative),
                data,
                (MissionRuntimeMetaDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.mission_runtime_meta" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_map_config_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_map_config(payload, source=relative),
                data,
                (MapConfigDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.map_config" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_ui_level_map_load_config_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_ui_level_map_load_config(payload, source=relative),
                data,
                (UiLevelMapLoadConfigDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.ui_level_map_load_config" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_gold_coin_config_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_gold_coin_config(payload, source=relative),
                data,
                (GoldCoinConfigDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.gold_coin_config" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_named_jsondata_text_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_named_jsondata_text(
                    payload, source=relative
                ),
                data,
                (JsonDataTextSchemaDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.text_schema" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_level_mount_point_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_level_mount_points(
                    payload, source=relative
                ),
                data,
                (LevelMountPointJsonDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.level_mount_point" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_compact_gameplay_config_json_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_compact_gameplay_config_json(
                    payload, source=relative
                ),
                data,
                (GameplayConfigJsonDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.gameplay_config" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_polymorphic_gameplay_config_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_polymorphic_gameplay_config(
                    payload, source=relative
                ),
                data,
                (GameplayConfigPolymorphicDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.schemas.gameplay_config_polymorphic" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        else:
            classification = (
            {
                "status": "format_framed_json",
                "reader": "python.json",
                "detail": {"rootType": json_root},
                "diagnostic": None,
            }
            if is_json
            else _classify_binary(relative, family, data)
            )
        if not is_json and family in family_evidence:
            evidence = family_evidence[family][virtual_path]
            if (
                evidence["length"] != len(data)
                or evidence["logicalMd5"] != actual_md5
                or evidence["logicalSha256"] != logical_sha256
            ):
                raise ValueError(f"{family} evidence differs from current export bytes: {virtual_path!r}")
            if family == "BuffData" and evidence["detail"].get("wholeSchemaExact") is True:
                if evidence["rootSingleCreateActionReceipt"] is not None:
                    replay = buff_create_action_root_receipt.decode_single_create_action_root(
                        data, source=virtual_path, expected_sha256=logical_sha256,
                        native_validation=buff_single_create_validation,
                    )
                    recorded = evidence["rootSingleCreateActionReceipt"]
                elif evidence["rootPositiveDamageReceipt"] is not None:
                    replay = buff_root_no_positive.decode_positive_damage_buff(
                        data, source=virtual_path, expected_sha256=logical_sha256,
                        native_validation=buff_native_validation,
                        positive_damage_validation=buff_positive_damage_validation,
                    )
                    recorded = evidence["rootPositiveDamageReceipt"]
                else:
                    replay = buff_root_no_positive.decode_no_positive_buff(
                        data, source=virtual_path, expected_sha256=logical_sha256,
                        native_validation=buff_native_validation,
                    )
                    recorded = evidence["rootNoPositiveReceipt"]
                # Compare canonical digests so IEEE NaN payloads, if a future
                # DataPair uses one, do not make an otherwise identical receipt
                # fail Python's ``nan != nan`` equality rule.
                if canonical_json_sha256(replay) != canonical_json_sha256(recorded):
                    raise ValueError(f"BuffData exact root receipt differs from current replay: {virtual_path!r}")
            contract = FAMILY_REPORTS[family]
            classification = {
                "status": (
                    "schema_decoded"
                    if family in ("SkillData", "BuffData")
                    and evidence["detail"].get("wholeSchemaExact") is True
                    else "format_framed"
                    if family == "BuffData"
                    and evidence["detail"].get("namedOuterFrameStatus") in ("named_exact_frame", "named_exact_full")
                    else "bounded_partial_ambiguous"
                    if family == "SkillData"
                    and evidence["detail"].get("boundaryClass") == "ambiguous"
                    else contract["status"]
                ),
                "reader": contract["reader"],
                "detail": evidence["detail"],
                "diagnostic": None,
            }
        results.append({
            "virtualPath": virtual_path,
            "exportRelativePath": relative,
            "family": family,
            "length": len(data),
            "logicalMd5": actual_md5,
            "logicalSha256": logical_sha256,
            "firstByte": data[:1].hex().upper(),
            **classification,
        })

    actual_files = _json_export_files(game_root, json_folder)
    extras = sorted(actual_files - seen_paths)
    if extras:
        raise ValueError(f"JsonData export contains unowned files; first={extras[0]!r}")

    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    status_counts: Counter[str] = Counter()
    for row in results:
        family_counts[row["family"]]["files"] += 1
        family_counts[row["family"]]["bytes"] += row["length"]
        family_counts[row["family"]][row["status"]] += 1
        status_counts[row["status"]] += 1
    families = {
        family: dict(sorted(counts.items()))
        for family, counts in sorted(
            family_counts.items(), key=lambda item: (-item[1]["files"], item[0])
        )
    }
    report = {
        "format": REPORT_FORMAT,
        "schemaVersion": 1,
        "status": "complete",
        "inputSetSha256": expected,
        "exportRoot": export_root.as_posix(),
        "provenance": {
            **provenance,
            "registry": {
                "path": Path(__file__).resolve().as_posix(),
                "length": Path(__file__).stat().st_size,
                "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
            },
            "familyReports": family_report_provenance,
        },
        "summary": {
            "filesSelected": len(selected),
            "filesJoined": len(results),
            "logicalBytes": sum(row["length"] for row in results),
            "statusCounts": dict(sorted(status_counts.items())),
            "familyCount": len(families),
            "families": families,
        },
        "evidenceBoundary": (
            "Every current JsonData logical identity is joined to the structured export "
            "by safe relative path, exact length, and logical MD5. JSON syntax, exact "
            "reader closures, bounded partial frames, bounded ambiguous frames, unsupported variants, and "
            "unclassified binary payloads remain separate terminal states. A path, "
            "filename extension, or leading member count never supplies a schema."
        ),
    }
    return report, results


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# JsonData current corpus registry",
        "",
        f"Status: `{report['status']}`; inputSetSha256: `{report['inputSetSha256']}`.",
        "",
        f"Joined `{summary['filesJoined']}` of `{summary['filesSelected']}` files; "
        f"logical bytes: `{summary['logicalBytes']}`; families: `{summary['familyCount']}`.",
        "",
        "## Terminal states",
        "",
        "| State | Files |",
        "|---|---:|",
    ]
    lines.extend(
        f"| `{status}` | {count} |"
        for status, count in summary["statusCounts"].items()
    )
    lines.extend((
        "",
        "## Families",
        "",
        "| Family | Files | Bytes | JSON | Schema decoded | Framed | Partial | Ambiguous partial | Unsupported | Unclassified |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ))
    for family, counts in summary["families"].items():
        framed = counts.get("format_framed", 0) + counts.get("format_framed_anonymous", 0)
        lines.append(
            f"| `{family}` | {counts['files']} | {counts['bytes']} | "
            f"{counts.get('format_framed_json', 0)} | {counts.get('schema_decoded', 0)} | "
            f"{framed} | {counts.get('bounded_partial', 0)} | "
            f"{counts.get('bounded_partial_ambiguous', 0)} | "
            f"{counts.get('unsupported', 0)} | {counts.get('unclassified_binary', 0)} |"
        )
    lines.extend(("", report["evidenceBoundary"], ""))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--export-root", type=Path, default=DEFAULT_EXPORT,
        help="The export's game/Json folder (default: export_full/game/Json). Packed "
             "folders such as Json/LipSync are read from its game/GameFiles.sqlite.",
    )
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--buff-report", type=Path, default=DEFAULT_BUFF_REPORT)
    parser.add_argument("--skill-report", type=Path, default=DEFAULT_SKILL_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--output-files", type=Path, default=DEFAULT_FILES)
    args = parser.parse_args(argv)
    try:
        outputs = [args.output_json, args.output_md, args.output_files]
        for output in outputs:
            _guard_output_path(
                output,
                [args.outer_summary, args.outer_ledger, args.export_root, args.buff_report, args.skill_report]
                + [other for other in outputs if other != output],
            )
        report, rows = build_report(
            outer_path=args.outer_summary,
            ledger_path=args.outer_ledger,
            export_root=args.export_root,
            expected_input_set_sha256=args.expected_input_set_sha256,
            buff_report_path=args.buff_report,
            skill_report_path=args.skill_report,
        )
        lines = b"".join(
            (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            for row in rows
        )
        files_bytes = gzip.compress(lines, mtime=0)
        report["provenance"]["outputFiles"] = {
            "length": len(files_bytes),
            "sha256": hashlib.sha256(files_bytes).hexdigest().upper(),
        }
        json_bytes = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        md_bytes = render_markdown(report).encode("utf-8")
        _atomic_write(args.output_json, json_bytes)
        _atomic_write(args.output_md, md_bytes)
        _atomic_write(args.output_files, files_bytes)
    except (CensusGateError, OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, SkillEvidenceContractError):
            print(json.dumps({
                "status": "failed",
                "summary": str(exc),
                "diagnostic": exc.diagnostic,
            }, ensure_ascii=False))
        else:
            print(json.dumps({"status": "failed", "diagnostic": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": report["status"], "summary": report["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
