"""Replay shared Buff children and the selected zero-member finder subtype.

The current Buff and named-action receipts supply authenticated source identities
and completed union ranges. Each selected child adapter reparses its parent
action, verifies the exact field extent, and names only stored child members.
The enclosing BuffData schema remains blocked.

It replays the direct ``BlackboardDouble``, ``TargetSettings``,
``DirectionSettings`` and ``SelectorData`` members; the selected
``CharacterTeamFinder`` and ``OwnerSpawnedEntityFinder`` finder children;
the zero-member ``ExcludeOwner`` and ``MainCharacter`` validators; and the
direct ``TagValidator.query`` member with a structurally framed
``GameplayTagQuery`` body, all inside named Buff actions. Other nested
selector bodies and the recursive/whole-BuffData gaps remain.

Usage (shared by the Buff child corpora): ``--buff-report`` is the complete
``memorypack.buff_corpus`` report, ``--action-report`` the
``buff_action_receipt_corpus`` JSON
(``reports/animestudio/buff_action_receipts_current_latest.json``),
``--export-root`` the export root, and ``--expected-input-set-sha256`` the VFS
audit value both reports were built from. The default output is
``reports/animestudio/buff_shared_nested_children_current_latest.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import ROOT, canonical_json_sha256, sha256_file_upper
from scripts.game_data.memorypack.buff_action_receipt_corpus import (
    _selected_candidate, _union_records,
)
from scripts.game_data.memorypack import buff_blackboard_double_child_receipt as blackboard
from scripts.game_data.memorypack import buff_direction_settings_child_receipt as direction
from scripts.game_data.memorypack import buff_selector_data_child_receipt as selector
from scripts.game_data.memorypack import buff_selector_finder_character_team as finder_character_team
from scripts.game_data.memorypack import buff_selector_finder_owner_spawned as finder_owner_spawned
from scripts.game_data.memorypack import buff_selector_validator_zero as validator_zero
from scripts.game_data.memorypack import buff_selector_validator_tag_query as validator_tag_query
from scripts.game_data.memorypack import buff_target_settings_child_receipt as target


SCHEMA = "endfield.buff-shared-nested-child-corpus.v7"
REPORTS_ROOT = ROOT / "reports"
DEFAULT_OUTPUT = REPORTS_ROOT / "animestudio/buff_shared_nested_children_current_latest.json"
SOURCE_PATTERN = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")


def _fail(check: str, *, source: str = "", detail: str = "") -> None:
    raise ValueError(f"buffSharedNestedCorpus:{check}:source={source}; {detail}")


def _file_sha256(path: Path) -> str:
    return sha256_file_upper(path)


def build_report(
    buff: dict[str, Any], action: dict[str, Any], *,
    buff_report_path: Path, action_report_path: Path,
    export_root: Path, expected_input_set_sha256: str,
    blackboard_native: dict[str, Any], target_native: dict[str, Any],
    direction_native: dict[str, Any], selector_native: dict[str, Any],
    character_team_finder_native: dict[str, Any],
    owner_spawned_finder_native: dict[str, Any],
    zero_validator_native: dict[str, Any],
    tag_query_validator_native: dict[str, Any],
) -> dict[str, Any]:
    """Recheck all current identities, then replay every selected child span."""
    expected = expected_input_set_sha256.upper()
    files = buff.get("files")
    action_files = action.get("files")
    if not re.fullmatch(r"[0-9A-F]{64}", expected):
        _fail("expected-input-set-format", detail=expected_input_set_sha256)
    if (
        buff.get("format") != "animestudio-buffdata-current-vfs-corpus"
        or buff.get("status") != "complete"
        or buff.get("publicationEligible") is not True
        or buff.get("wholeSchemaExact") is not False
        or buff.get("inputSetSha256") != expected
        or not isinstance(files, list)
        or buff.get("summary", {}).get("filesSelected") != len(files)
        or buff["summary"].get("filesUnique") != len(files)
        or buff["summary"].get("filesFailed") != 0
        or buff["summary"].get("filesAmbiguous") != 0
        or canonical_json_sha256([
            {"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
            for row in files
        ]) != buff.get("identitySetSha256")
    ):
        _fail("buff-report-identity-or-status", detail="complete unique current corpus required")
    buff_sha = _file_sha256(buff_report_path)
    if (
        action.get("schema") != "endfield.buff-action-receipt-corpus.v7"
        or action.get("status") != "complete"
        or action.get("publicationEligible") is not True
        or action.get("wholeBuffDataExact") is not False
        or action.get("inputSetSha256") != expected
        or action.get("buffReportSha256") != buff_sha
        or action.get("sourceIdentitySetSha256") != buff["identitySetSha256"]
        or action.get("summary", {}).get("sourceFilesVerified") != len(files)
        or not isinstance(action_files, list)
    ):
        _fail("action-report-identity-or-status", detail="current Buff report join required")
    outer = buff["provenance"]["outer"]
    outer_path = Path(outer["path"])
    if (
        _file_sha256(outer_path) != outer["sha256"]
        or json.loads(outer_path.read_text(encoding="utf-8")).get("inputSetSha256")
        != expected
    ):
        _fail("outer-vfs-source-drift", detail=str(outer_path))
    if (blackboard_native.get("status") != "validated"
            or target_native.get("status") != "validated"
            or direction_native.get("status") != "validated"
            or selector_native.get("status") != "validated"
            or character_team_finder_native.get("status") != "validated"
            or owner_spawned_finder_native.get("status") != "validated"
            or zero_validator_native.get("status") != "validated"
            or tag_query_validator_native.get("status") != "validated"
            or blackboard_native.get("nativeInputs") != target_native.get("nativeInputs")
            or direction_native.get("nativeInputs") != target_native.get("nativeInputs")
            or selector_native.get("nativeInputs") != target_native.get("nativeInputs")
            or character_team_finder_native.get("nativeInputs") != target_native.get("nativeInputs")
            or owner_spawned_finder_native.get("nativeInputs") != target_native.get("nativeInputs")
            or zero_validator_native.get("nativeInputs") != target_native.get("nativeInputs")
            or tag_query_validator_native.get("nativeInputs") != target_native.get("nativeInputs")):
        _fail("selected-native-gate", detail="all child gates must validate same build")

    action_by_source = {row.get("source"): row for row in action_files}
    if len(action_by_source) != len(action_files) or None in action_by_source:
        _fail("duplicate-action-source")
    verified_sources: set[str] = set()
    rows = []
    action_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    direction_counts: Counter[int] = Counter()
    selector_counts: Counter[int] = Counter()
    blackboard_counts: Counter[int] = Counter()
    target_nulls: Counter[str] = Counter()
    direction_nulls: Counter[str] = Counter()
    direction_references: Counter[str] = Counter()
    selector_nulls: Counter[str] = Counter()
    selector_finder_tags: Counter[str] = Counter()
    selector_post_counts: Counter[str] = Counter()
    selector_validator_counts: Counter[str] = Counter()
    character_team_finder_counts: Counter[str] = Counter()
    owner_spawned_finder_counts: Counter[str] = Counter()
    owner_spawned_object_type_counts: Counter[str] = Counter()
    validator_single_entry_tags: Counter[str] = Counter()
    selected_zero_validator_tags: Counter[str] = Counter()
    tag_query_validator_states: Counter[str] = Counter()
    blackboard_nulls: Counter[str] = Counter()
    for file in files:
        identity = file["identity"]
        source = identity.get("fileName")
        if (
            not isinstance(source, str) or not SOURCE_PATTERN.fullmatch(source)
            or source in verified_sources or identity.get("virtualPath") != source
            or identity.get("status") != "verified"
            or identity.get("boundaryStatus") != "boundary_verified"
            or identity.get("inputSetSha256") != expected
        ):
            _fail("source-identity", source=str(source))
        verified_sources.add(source)
        data_path = export_root / "game" / source.removeprefix("Data/")
        data = data_path.read_bytes()
        source_sha = hashlib.sha256(data).hexdigest().upper()
        source_md5 = hashlib.md5(data).hexdigest().upper()
        if (
            len(data) != identity.get("length")
            or len(data) != identity.get("actualBytesRead")
            or source_sha != file.get("logicalSha256")
            or source_md5 != identity.get("recomputedFileDataMd5", "").upper()
        ):
            _fail("logical-source-bytes", source=source,
                  detail=f"expectedSha={file.get('logicalSha256')} actualSha={source_sha}; path={data_path}")
        action_file = action_by_source.pop(source, None)
        candidate = _selected_candidate(file, source)
        certified = {(row["tag"], row["start"], row["end"])
                     for row in _union_records(candidate, source, len(data))}
        if action_file is None:
            continue
        if action_file.get("logicalSha256") != source_sha:
            _fail("action-source-hash", source=source)
        seen: set[tuple[int, int, int]] = set()
        for parent in action_file.get("actions", []):
            tag = parent.get("tag")
            if tag not in blackboard._PARENTS and tag not in target._PARENTS:
                continue
            key = (tag, parent.get("start"), parent.get("end"))
            if key not in certified or key in seen:
                _fail("uncertified-or-repeated-action", source=source, detail=str(key))
            seen.add(key)
            row = {"source": source, "logicalSha256": source_sha,
                   "tag": tag, "start": key[1], "end": key[2]}
            if tag in blackboard._PARENTS:
                receipt = blackboard.decode_blackboard_double_action_child_receipt(
                    data, source=source, logical_sha256=source_sha,
                    tag=tag, start=key[1], end=key[2],
                    native_validation=blackboard_native,
                )
                row["blackboardDouble"] = receipt
                blackboard_counts[tag] += 1
                blackboard_nulls[receipt["child"]["status"]] += 1
            if tag in target._PARENTS:
                receipt = target.decode_target_settings_action_child_receipt(
                    data, source=source, logical_sha256=source_sha,
                    tag=tag, start=key[1], end=key[2],
                    native_validation=target_native,
                )
                row["targetSettings"] = receipt
                target_counts[tag] += len(receipt["targetChildren"])
                target_nulls.update(child["status"] for child in receipt["targetChildren"])
                direction_receipt = direction.decode_direction_settings_action_child_receipt(
                    data, source=source, logical_sha256=source_sha,
                    tag=tag, start=key[1], end=key[2],
                    native_validation=direction_native,
                )
                row["directionSettings"] = direction_receipt
                direction_counts[tag] += len(direction_receipt["directionChildren"])
                direction_nulls.update(
                    child["status"] for child in direction_receipt["directionChildren"]
                )
                direction_references.update(
                    member["nestedTargetStatus"]
                    for child in direction_receipt["directionChildren"]
                    for member in child["namedMembers"]
                    if member["nestedTargetStatus"] is not None
                )
                selector_receipt = selector.decode_selector_data_action_child_receipt(
                    data, source=source, logical_sha256=source_sha,
                    tag=tag, start=key[1], end=key[2],
                    native_validation=selector_native,
                )
                row["selectorData"] = selector_receipt
                selector_counts[tag] += len(selector_receipt["selectorChildren"])
                for child in selector_receipt["selectorChildren"]:
                    selector_nulls[child["status"]] += 1
                    if child["status"] == "named-direct-members-exact-span":
                        members = child["namedMembers"]
                        finder = members[0]["unionTag"]
                        selector_finder_tags["null" if finder is None else str(finder)] += 1
                        selector_post_counts[str(members[1]["count"])] += 1
                        selector_validator_counts[str(members[2]["count"])] += 1
                        validator_member = members[2]
                        if validator_member["count"] == 1:
                            if (validator_member["fieldName"] != "validatorData"
                                    or validator_member["end"] - validator_member["start"] < 5):
                                _fail("validator-list-parent", source=source)
                            validator_tag = data[validator_member["start"] + 4]
                            validator_single_entry_tags[str(validator_tag)] += 1
                            if validator_tag in validator_zero.TYPE_NAMES:
                                validation = validator_zero.decode_zero_validator_list(
                                    data, source=source, logical_sha256=source_sha,
                                    start=validator_member["start"],
                                    end=validator_member["end"],
                                    native_validation=zero_validator_native,
                                )
                                row.setdefault("selectedValidatorChildren", []).append(validation)
                                selected_zero_validator_tags[str(validator_tag)] += 1
                            elif validator_tag == validator_tag_query.TAG:
                                validation = validator_tag_query.decode_tag_query_validator_list(
                                    data, source=source, logical_sha256=source_sha,
                                    start=validator_member["start"],
                                    end=validator_member["end"],
                                    native_validation=tag_query_validator_native,
                                )
                                row.setdefault("selectedValidatorChildren", []).append(validation)
                                selected_element = validation["selectedElement"]
                                query = selected_element["namedMember"]
                                tag_query_validator_states[
                                    selected_element["status"] if query is None else query["status"]
                                ] += 1
                        if finder == finder_character_team.TAG:
                            finder_member = members[0]
                            if (finder_member["fieldName"] != "finderData"
                                    or finder_member["selectedSubtype"]
                                    != finder_character_team.TYPE_NAME):
                                _fail("character-team-finder-parent", source=source)
                            child = finder_character_team.decode_character_team_finder_span(
                                data, source=source, logical_sha256=source_sha,
                                start=finder_member["start"], end=finder_member["end"],
                                native_validation=character_team_finder_native,
                            )
                            row.setdefault("selectedFinderChildren", []).append(child)
                            character_team_finder_counts[child["status"]] += 1
                        elif finder == finder_owner_spawned.TAG:
                            finder_member = members[0]
                            if (finder_member["fieldName"] != "finderData"
                                    or finder_member["selectedSubtype"]
                                    != finder_owner_spawned.TYPE_NAME):
                                _fail("owner-spawned-finder-parent", source=source)
                            child = finder_owner_spawned.decode_owner_spawned_finder_span(
                                data, source=source, logical_sha256=source_sha,
                                start=finder_member["start"], end=finder_member["end"],
                                native_validation=owner_spawned_finder_native,
                            )
                            row.setdefault("selectedFinderChildren", []).append(child)
                            owner_spawned_finder_counts[child["status"]] += 1
                            if child["namedMember"] is not None:
                                owner_spawned_object_type_counts[
                                    str(child["namedMember"]["storedInt32"])
                                ] += 1
            rows.append(row)
            action_counts[tag] += 1
    if action_by_source:
        _fail("unmatched-action-sources", detail=f"remaining={len(action_by_source)}")
    for tag in set(blackboard._PARENTS) | set(target._PARENTS):
        label = f"0x{tag:04X}"
        expected_actions = action["summary"]["byTag"][label]["actionSpans"]
        if action_counts[tag] != expected_actions:
            _fail("action-span-count", detail=f"tag={label}; expected={expected_actions} actual={action_counts[tag]}")
        if tag in blackboard._PARENTS and blackboard_counts[tag] != expected_actions:
            _fail("blackboard-span-count", detail=label)
        if tag in target._PARENTS:
            expected_targets = expected_actions * len(target_native["bindings"][tag])
            if target_counts[tag] != expected_targets:
                _fail("target-span-count", detail=f"tag={label}; expected={expected_targets} actual={target_counts[tag]}")
            if direction_counts[tag] != expected_targets:
                _fail("direction-span-count", detail=f"tag={label}; expected={expected_targets} actual={direction_counts[tag]}")
            if selector_counts[tag] != expected_targets:
                _fail("selector-span-count", detail=f"tag={label}; expected={expected_targets} actual={selector_counts[tag]}")
    summary = {
        "sourceFilesAuthenticated": len(verified_sources),
        "actionsWithSharedChildren": len(rows),
        "filesWithSharedChildren": len({row["source"] for row in rows}),
        "blackboardDoubleSpans": sum(blackboard_counts.values()),
        "targetSettingsSpans": sum(target_counts.values()),
        "directionSettingsSpans": sum(direction_counts.values()),
        "selectorDataSpans": sum(selector_counts.values()),
        "blackboardByTag": {f"0x{tag:04X}": n for tag, n in sorted(blackboard_counts.items())},
        "targetByTag": {f"0x{tag:04X}": n for tag, n in sorted(target_counts.items())},
        "directionByTag": {f"0x{tag:04X}": n for tag, n in sorted(direction_counts.items())},
        "selectorByTag": {f"0x{tag:04X}": n for tag, n in sorted(selector_counts.items())},
        "blackboardNullState": dict(sorted(blackboard_nulls.items())),
        "targetNullState": dict(sorted(target_nulls.items())),
        "directionNullState": dict(sorted(direction_nulls.items())),
        "directionNestedTargetState": dict(sorted(direction_references.items())),
        "selectorNullState": dict(sorted(selector_nulls.items())),
        "selectorFinderTags": dict(sorted(selector_finder_tags.items())),
        "selectorPostProcessorCounts": dict(sorted(selector_post_counts.items())),
        "selectorValidatorCounts": dict(sorted(selector_validator_counts.items())),
        "characterTeamFinderSpans": sum(character_team_finder_counts.values()),
        "characterTeamFinderStatus": dict(sorted(character_team_finder_counts.items())),
        "ownerSpawnedEntityFinderSpans": sum(owner_spawned_finder_counts.values()),
        "ownerSpawnedEntityFinderStatus": dict(sorted(owner_spawned_finder_counts.items())),
        "ownerSpawnedObjectTypeStoredInt32": dict(sorted(owner_spawned_object_type_counts.items())),
        "validatorSingleEntryTags": dict(sorted(validator_single_entry_tags.items())),
        "selectedZeroValidatorLists": sum(selected_zero_validator_tags.values()),
        "selectedZeroValidatorByTag": dict(sorted(selected_zero_validator_tags.items())),
        "tagQueryValidatorLists": sum(tag_query_validator_states.values()),
        "tagQueryValidatorQueryState": dict(sorted(tag_query_validator_states.items())),
        "wholeBuffDataPromoted": 0,
    }
    if sum(character_team_finder_counts.values()) != selector_finder_tags[str(finder_character_team.TAG)]:
        _fail("character-team-finder-count")
    if sum(owner_spawned_finder_counts.values()) != selector_finder_tags[str(finder_owner_spawned.TAG)]:
        _fail("owner-spawned-finder-count")
    for tag in validator_zero.TYPE_NAMES:
        if selected_zero_validator_tags[str(tag)] != validator_single_entry_tags[str(tag)]:
            _fail("selected-zero-validator-count", detail=str(tag))
    if sum(tag_query_validator_states.values()) != validator_single_entry_tags[str(validator_tag_query.TAG)]:
        _fail("tag-query-validator-count")
    return {
        "schema": SCHEMA, "status": "complete", "publicationEligible": True,
        "wholeBuffDataExact": False, "inputSetSha256": expected,
        "inputs": {
            "buffReport": {"path": str(buff_report_path), "sha256": buff_sha},
            "actionReport": {"path": str(action_report_path), "sha256": _file_sha256(action_report_path)},
            "outerVfsReport": outer,
        },
        "nativeValidation": {
            "blackboardDouble": blackboard_native,
            "targetSettings": {key: value for key, value in target_native.items()
                               if key != "_registry"},
            "directionSettings": {key: value for key, value in direction_native.items()
                                  if key not in ("_registry", "targetNative")},
            "selectorData": {key: value for key, value in selector_native.items()
                             if key not in ("_registry", "targetNative")},
            "characterTeamFinder": character_team_finder_native,
            "ownerSpawnedEntityFinder": owner_spawned_finder_native,
            "selectedZeroValidators": zero_validator_native,
            "tagQueryValidator": tag_query_validator_native,
        },
        "summary": summary, "rows": rows,
        "evidenceBoundary": (
            "VFS-verified logical files and completed union ranges rejoin selected "
            "native-gated parent action fields to shared nested member readers. "
            "Only stored direct child fields are named. Direction's two nested "
            "TargetSettings references remain null in the reached corpus. "
            "CharacterTeamFinder tag 2 has a selected zero-member receipt; "
            "OwnerSpawnedEntityFinder tag 13 has a selected one-member "
            "spawnedObjectType receipt. ExcludeOwnerValidator tag 5 and "
            "MainCharacterValidator tag 9 each have an exact zero-member "
            "one-entry list receipt. TagValidator tag 11 has a selected "
            "query-member receipt and an exact bounded query profile. Other "
            "SelectorData finder bodies and query values remain structural. "
            "Live provider choice and whole BuffData remain unresolved."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--action-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if REPORTS_ROOT.resolve() not in output.parents:
        parser.error(f"output must be under {REPORTS_ROOT}")
    buff_path = args.buff_report.resolve()
    action_path = args.action_report.resolve()
    buff = json.loads(buff_path.read_text(encoding="utf-8"))
    action = json.loads(action_path.read_text(encoding="utf-8"))
    blackboard_native = blackboard.validate_current_native_contract()
    target_native = target.validate_current_native_contract()
    direction_native = direction.validate_current_native_contract(target_native=target_native)
    selector_native = selector.validate_current_native_contract(target_native=target_native)
    character_team_finder_native = finder_character_team.validate_current_native_contract(
        selector_native=selector_native,
    )
    owner_spawned_finder_native = finder_owner_spawned.validate_current_native_contract(
        selector_native=selector_native,
    )
    zero_validator_native = validator_zero.validate_current_native_contract(
        selector_native=selector_native,
    )
    tag_query_validator_native = validator_tag_query.validate_current_native_contract(
        selector_native=selector_native,
    )
    report = build_report(
        buff, action, buff_report_path=buff_path, action_report_path=action_path,
        export_root=args.export_root.resolve(),
        expected_input_set_sha256=args.expected_input_set_sha256,
        blackboard_native=blackboard_native, target_native=target_native,
        direction_native=direction_native,
        selector_native=selector_native,
        character_team_finder_native=character_team_finder_native,
        owner_spawned_finder_native=owner_spawned_finder_native,
        zero_validator_native=zero_validator_native,
        tag_query_validator_native=tag_query_validator_native,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
