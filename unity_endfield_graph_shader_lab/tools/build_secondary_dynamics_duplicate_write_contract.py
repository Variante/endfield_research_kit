#!/usr/bin/env python3
"""Build the pinned Endminf duplicate-transform write contract.

This contract answers only the duplicate publication question.  It preserves
all 126 DynamicBoneTransformManager entries, pins the native writeback bodies
and call sites, and derives per-path write eligibility from the exact manager
flags.  It does not install a runtime policy or claim that Unity's parallel
TransformAccess schedule executes in source order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DATA_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_WRITEBACK = DATA_ROOT / "secondary_dynamics_transform_writeback_contract.json"
DEFAULT_READ = DATA_ROOT / "secondary_dynamics_transform_read_contract.json"
DEFAULT_CALLBACK = DATA_ROOT / "secondary_dynamics_callback_contract.json"
DEFAULT_SCHEDULE = DATA_ROOT / "secondary_dynamics_schedule_contract.json"
DEFAULT_PAYLOAD = DATA_ROOT / "secondary_dynamics_payload_decode.json"
DEFAULT_OUTPUT = DATA_ROOT / "secondary_dynamics_duplicate_write_contract.json"

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_INPUTS = {
    "writeback": (102059, "e5f9b12aeecd89e92e82484111f9492459782e04bd1c99353a28085e556d249e"),
    "read": (170018, "67167af46bc3363f2b0676f82896fecbfe7d3d22c7e218e3e7748006afd21d9a"),
    "callback": (17561, "f10af3ffc84f3283af1773e62b1214198bb042712882fb90ad7b5946662f0ac0"),
    "schedule": (14618, "d442c5ee85e85e863923a13af5b1caf6bb696c8f4e3ecb554a47d9991357288e"),
    "payload": (1161329, "6c8eed435f2acd645d3fb3560acf7c993b5ef34c8ff2336de1a9fa87a1cbff1a"),
}

# Full managed/native method spans where available.  The WriteTransformJob hot
# prefix is also retained because it contains every TransformAccess setter and
# the flag/team/weight branch used by this target contract.
NATIVE_SPANS = (
    ("ClothManager.ClothUpdate", 384441, "0x182f918a0", 0x2F8FEA0, 6256,
     "a1065dd5aaa62d715dc756e8ce87a4630d629d303494df34fb9d949b2231d077"),
    ("DynamicBoneTransformManager.WriteTransform", 384497, "0x18672641c", 0x6724A1C, 552,
     "0d2bd0087b25250cd8d88bf8325bbc9bac4da0b58622537e4891dc8fb5acd0f7"),
    ("DynamicBoneTransformManager.WriteTransformJob.Execute", 384566, "0x18672e7e0", 0x672CDE0, 11452,
     "8bb838d1118e5910d0794f5790cecad8a92981c760e802799e3244189cfd4676"),
    ("WriteTransformJob.Execute.hot", 384566, "0x18672e7e0", 0x672CDE0, 2003,
     "be8906f5f1bbca55200b7941031e56cb8e0a260054cc7a892ba056c2644dd91e"),
    ("IJobParallelForTransformExtensions.Schedule wrapper span", None, "0x1803698c8", 0x368CC8, 118,
     "84d0c36acbe0b117db909abe436a6a90e5786e7077bad4753207c2c3e628d255"),
    ("Schedule<WriteTransformJob> generic body", None, "0x183b12d60", 0x3B11360, 240,
     "891f42acb49be0849ff45440f1b272489211db8b86220305a658fa2f4a1d3095"),
)

CALL_SITES = (
    ("ClothUpdate -> WriteTransform", "0x182f9245c", 0x2F90A5C, "e8bb3f7903", "0x18672641c"),
    ("WriteTransform -> concrete Schedule wrapper", "0x1867265c1", 0x6724BC1, "e80233c4f9", "0x1803698c8"),
    ("concrete Schedule wrapper -> generic Schedule", "0x18036992d", 0x368D2D, "e82e947a03", "0x183b12d60"),
    ("generic Schedule -> ScheduleParallelForTransform_Injected", "0x183b12df7", 0x3B113F7, "ffd0", "icall slot 0x18f36eea0"),
    ("WriteTransformJob -> set_localPosition", "0x18672ea78", 0x672D078, "e83f05cb04", "0x18b3defbc"),
    ("WriteTransformJob -> set_localRotation", "0x18672eb33", 0x672D133, "40e89704cb04", "0x18b3defd0"),
    ("WriteTransformJob -> set_rotation", "0x18672ed13", 0x672D313, "40e8f302cb04", "0x18b3df00c"),
    ("WriteTransformJob -> set_position", "0x18672f54e", 0x672D54E, "e8a500cb04", "0x18b3deff8"),
)

OWNER_ORDER = ("MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_pinned(label: str, path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.is_file():
        raise ContractError(f"missing {label}: {path}")
    actual = (path.stat().st_size, _sha(path))
    if actual != EXPECTED_INPUTS[label]:
        raise ContractError(f"{label} drift: {actual} != {EXPECTED_INPUTS[label]}")
    return json.loads(path.read_text(encoding="utf-8")), {
        "repoPath": _repo_path(path), "size": actual[0], "sha256": actual[1]
    }


def _native_gate(game_assembly: Path | None, metadata: Path | None) -> tuple[Path, dict[str, Any]]:
    gate = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not gate.validated:
        raise ContractError(f"native gate [{gate.status}]: {gate.detail}")
    ga = Path(gate.gameassembly)
    md = Path(gate.metadata)
    return ga, {
        "status": gate.status,
        "gameAssembly": {"path": _repo_path(ga), "size": ga.stat().st_size, "sha256": gate.gameassembly_sha256},
        "globalMetadata": {"path": _repo_path(md), "size": md.stat().st_size, "sha256": gate.metadata_sha256},
    }


def _pin_native(game_assembly: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    image = game_assembly.read_bytes()
    spans = []
    for name, method_index, va, offset, size, expected in NATIVE_SPANS:
        digest = hashlib.sha256(image[offset:offset + size]).hexdigest()
        if digest != expected:
            raise ContractError(f"native span drift for {name}: {digest}")
        spans.append({"name": name, "methodIndex": method_index, "va": va,
                      "fileOffset": f"0x{offset:x}", "bytes": size, "sha256": digest})
    calls = []
    for name, va, offset, expected_hex, target in CALL_SITES:
        actual = image[offset:offset + len(bytes.fromhex(expected_hex))].hex()
        if actual != expected_hex:
            raise ContractError(f"native call-site drift for {name}: {actual}")
        calls.append({"name": name, "instructionVa": va, "fileOffset": f"0x{offset:x}",
                      "instructionBytes": " ".join(actual[i:i + 2] for i in range(0, len(actual), 2)),
                      "target": target})
    return spans, calls


def _branch(flag: int) -> str:
    if flag & 0x02:
        return "world"
    if flag & 0x04:
        return "local"
    return "none"


def _ordered_entries(read_contract: dict[str, Any]) -> list[dict[str, Any]]:
    source = read_contract["endminf"]["orderedEntries"]
    if len(source) != 126 or [row["managerIndex"] for row in source] != list(range(126)):
        raise ContractError("ordered 126-entry manager mapping drift")
    if tuple(read_contract["endminf"]["ownerOrder"]) != OWNER_ORDER:
        raise ContractError("Endminf owner order drift")
    rows = []
    for item in source:
        source_flag = int(item["sourceFlag"])
        active_flag = int(item["activeManagerFlag"])
        if active_flag != (source_flag | 0x10):
            raise ContractError(f"active flag drift at manager index {item['managerIndex']}")
        branch = _branch(active_flag)
        rows.append({
            "managerIndex": item["managerIndex"],
            "owner": item["owner"],
            "ownerLocalIndex": item["ownerLocalIndex"],
            "hierarchyPath": item["hierarchyPath"],
            "transformPathId": item["transformPathId"],
            "attribute": item["attribute"],
            "sourceFlag": source_flag,
            "sourceFlagHex": f"0x{source_flag:02x}",
            "activeManagerFlag": active_flag,
            "activeManagerFlagHex": f"0x{active_flag:02x}",
            "staticWriteBranch": branch,
            "writeEligibleBeforeDynamicGates": branch != "none",
        })
    counts = Counter(row["staticWriteBranch"] for row in rows)
    if counts != Counter({"local": 67, "none": 36, "world": 23}):
        raise ContractError(f"write-branch census drift: {counts}")
    return rows


def _duplicate_groups(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in entries:
        by_path[row["hierarchyPath"]].append(row)
    groups = []
    winner_counts: Counter[str] = Counter()
    branch_counts: Counter[str] = Counter()
    for path, members in by_path.items():
        if len(members) == 1:
            continue
        if len(members) != 2:
            raise ContractError(f"unsupported duplicate cardinality for {path}: {len(members)}")
        writers = [row for row in members if row["writeEligibleBeforeDynamicGates"]]
        if len(writers) > 1:
            resolution = "unresolved_competing_writers"
            winner = None
        elif len(writers) == 1:
            resolution = "sole_write_eligible_entry"
            winner = writers[0]["managerIndex"]
            winner_counts[writers[0]["owner"]] += 1
            branch_counts[writers[0]["staticWriteBranch"]] += 1
        else:
            resolution = "no_write_eligible_entry"
            winner = None
            winner_counts["none"] += 1
        groups.append({
            "hierarchyPath": path,
            "managerIndices": [row["managerIndex"] for row in members],
            "members": [{
                "managerIndex": row["managerIndex"], "owner": row["owner"],
                "ownerLocalIndex": row["ownerLocalIndex"], "attribute": row["attribute"],
                "activeManagerFlagHex": row["activeManagerFlagHex"],
                "staticWriteBranch": row["staticWriteBranch"],
            } for row in members],
            "writeEligibleManagerIndices": [row["managerIndex"] for row in writers],
            "resolution": resolution,
            "staticallyProvenWriterManagerIndex": winner,
            "coatFallbackWhenSoleWriterDynamicallyGatedOff": False,
        })
    groups.sort(key=lambda row: row["managerIndices"])
    if len(groups) != 26:
        raise ContractError(f"duplicate path count drift: {len(groups)}")
    resolution_counts = Counter(row["resolution"] for row in groups)
    expected_resolution = Counter({"sole_write_eligible_entry": 24, "no_write_eligible_entry": 2})
    if resolution_counts != expected_resolution:
        raise ContractError(f"duplicate resolution drift: {resolution_counts}")
    if winner_counts != Counter({"MC_Ribbon": 18, "MC_Ribbon2": 6, "none": 2}):
        raise ContractError(f"duplicate writer census drift: {winner_counts}")
    if branch_counts != Counter({"local": 19, "world": 5}):
        raise ContractError(f"duplicate branch census drift: {branch_counts}")
    summary = {
        "bindingEntries": 126,
        "uniqueTransforms": 100,
        "duplicateEntries": 26,
        "duplicatePathCount": 26,
        "resolutionCounts": dict(resolution_counts),
        "staticallyProvenSoleWriterByOwner": dict(winner_counts),
        "soleWriterBranchCounts": dict(branch_counts),
        "competingWriterPathCount": 0,
        "allPathsResolvedWithoutExecutionOrdering": True,
    }
    return groups, summary


def build_contract(*, game_assembly: Path | None = None, metadata: Path | None = None,
                   writeback_path: Path = DEFAULT_WRITEBACK, read_path: Path = DEFAULT_READ,
                   callback_path: Path = DEFAULT_CALLBACK, schedule_path: Path = DEFAULT_SCHEDULE,
                   payload_path: Path = DEFAULT_PAYLOAD) -> dict[str, Any]:
    ga, native_gate = _native_gate(game_assembly, metadata)
    writeback, writeback_source = _load_pinned("writeback", writeback_path)
    read_contract, read_source = _load_pinned("read", read_path)
    callback, callback_source = _load_pinned("callback", callback_path)
    schedule, schedule_source = _load_pinned("schedule", schedule_path)
    payload, payload_source = _load_pinned("payload", payload_path)

    if writeback["status"] != "transform_writeback_contract_closed_with_duplicate_boundary":
        raise ContractError("writeback status drift")
    if schedule["status"] != "unpatched_schedule_and_transform_access_writeback_closed":
        raise ContractError("schedule status drift")
    if schedule["writeTransform"]["genericSchedule"]["scheduleModeLane"] != 1:
        raise ContractError("TransformAccess parallel schedule mode drift")
    critical = {(row["offset"], row["method"]) for row in callback["writeback"]["criticalCalls"]}
    if (3004, "WriteTransform") not in critical or (4448, "CompleteMasterJob") not in critical:
        raise ContractError("callback write/completion call sites drift")
    if payload["actors"]["endminf"]["character_id"] != "chr_0003_endminf":
        raise ContractError("payload actor drift")
    boundary = writeback["writeback"]["endminfBindingBoundary"]
    if (boundary["bindingEntries"], boundary["uniqueTransforms"], boundary["duplicateEntries"]) != (126, 100, 26):
        raise ContractError("writeback duplicate boundary drift")

    spans, call_sites = _pin_native(ga)
    entries = _ordered_entries(read_contract)
    groups, duplicate_summary = _duplicate_groups(entries)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-duplicate-write.v1",
        "status": "endminf_transform_access_duplicates_closed_full_target_route_fail_closed",
        "nativeGate": native_gate,
        "sources": {
            "transformWriteback": writeback_source,
            "transformRead": read_source,
            "callback": callback_source,
            "schedule": schedule_source,
            "payloadDecode": payload_source,
        },
        "native": {
            "bodyPins": spans,
            "callSites": call_sites,
            "route": "unpatched native WriteTransform route only",
            "ifixWriteTransformPatchId": "0x32a",
            "ifixPatchedRouteRecovered": False,
        },
        "ordering": {
            "managerEntryOrder": "126 entries retain AddTransform/source insertion order and managerIndex 0..125",
            "transformAccessEntryMapping": "each manager index maps to the corresponding TransformAccessArray entry; duplicate Transform objects remain separate entries",
            "scheduleApi": "ScheduleParallelForTransform_Injected",
            "scheduleModeLane": 1,
            "sourceOrderExecutionProven": False,
            "parallelTransformAccessOrderProven": False,
            "reason": "The pinned managed bridge schedules one parallel-for-transform job over the array. GameAssembly contains no serial loop, owner priority, duplicate grouping, or completion-order winner rule for individual indices.",
            "impact": "Execution order is immaterial for Endminf's 26 duplicate paths because no path has two write-eligible entries.",
        },
        "callbackRouteBoundary": {
            "writeTransformCallOffset": "0xbbc",
            "writeTransformSelector": "ClothUpdate tests a native mode byte at the pinned +0xb8c comparison before the +0xbbc WriteTransform call",
            "animatorWriteCallOffset": "0x10b5",
            "animatorWriteSelector": "a separate native mode-byte branch reaches WriteAnimatorBufferData",
            "targetSelectedRouteProven": False,
            "reason": "The accepted static payload, callback, schedule, and ui_overview clip evidence do not contain the live global mode-byte values. The existing transform-read contract therefore also leaves the target ReadTransform/animator-buffer branch unresolved.",
            "consequence": "The exact result below applies to the pinned unpatched TransformAccess WriteTransform route; it is not promoted to a full retail ui_overview_start/loop winner claim.",
        },
        "writeGating": {
            "staticBranchPrecedence": "world when (flag & 0x02) != 0; else local when (flag & 0x04) != 0; else no TransformAccess setter",
            "enableGate": "(flag & 0x10) != 0",
            "teamGates": ["team is not culling-invisible", "native team/TransformAccess validity gates pass"],
            "weightEquation": "w = float32(team.clothSimulateWeight * team.clothLodFadeWeight)",
            "weightRole": "interpolation input, not a pairwise exclusion gate; w < 1 still follows the selected setter branch",
            "pairwiseOwnerComparison": False,
            "teamOrWeightMutualExclusionProven": False,
            "independentGateConsequence": "if the sole write-eligible Ribbon/Ribbon2 entry is dynamically gated off, the read-only Coat duplicate does not become a fallback writer",
        },
        "endminf": {
            "targetClips": ["ui_overview_start", "ui_overview_loop"],
            "ownerOrder": list(OWNER_ORDER),
            "orderedEntries": entries,
            "duplicateSummary": duplicate_summary,
            "duplicateGroups": groups,
            "targetRuntimeStateBoundary": "No per-frame TeamData/culling/weight telemetry for the target clips is present in the accepted static inputs. It is unnecessary for conflict resolution because static flags limit every duplicate path to at most one writer.",
        },
        "runtimePolicyBoundary": {
            "transformAccessRoutePolicyCanBeEvidenceBacked": True,
            "fullTargetRuntimeDuplicatePolicyCanBeEvidenceBacked": False,
            "policy": "On the pinned TransformAccess route, preserve all 126 entries and apply the native per-entry flags and dynamic gates. A route-local deduplicated publication view may use the sole write-eligible Ribbon2/Ribbon entry on 24 paths and publish nothing from either entry on the two fixed/fixed paths.",
            "ownerWinnerCounts": {"MC_Ribbon2": 6, "MC_Ribbon": 18, "none": 2},
            "coatWinnerCount": 0,
            "requiresAssumedSourceOrderWinner": False,
            "requiresCompatibilityPriority": False,
            "staticallyProvenFullTargetWinner": False,
            "failClosedReason": "ui_overview_start/loop lacks a pinned live callback-route selector, and the animator-buffer duplicate write route is not closed by this contract.",
            "failClosedRule": "Do not enable a full target runtime duplicate policy until the target callback route is selected by pinned evidence. Any future duplicate group containing more than one write-eligible entry, any source/hash drift, or any IFix-patched route also fails closed; never infer a winner from manager index or owner order.",
            "runtimeModified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        contract = build_contract(game_assembly=args.game_assembly, metadata=args.metadata)
    except ContractError as exc:
        print(f"duplicate-write contract unavailable: {exc}", file=sys.stderr)
        return 2
    encoded = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            print(f"generated contract differs: {args.output}", file=sys.stderr)
            return 1
        print(f"generated contract matches: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
