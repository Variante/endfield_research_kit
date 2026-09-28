"""Selected SkillData positive DamageUnit GameplayTag list.

This is the tenth DamageUnit source member.  The current generic list call
and generated element reader are pinned independently; the active inflated
list provider remains conditional until a live provider witness exists.

The generic callsite, element formatter and list-count source each have an
independent native window.  The wire accepted here is a signed nullable
count, then elements that are either ``FF`` or a one-member wrapper header
followed by one four-byte tag -- the ``List<T>`` element framing, as opposed
to a packed ``T[]``.  The following DamageUnit tail is retained as a separate
bounded region, and the parent action, ActionGroup and top-level fields must
rejoin before a whole file becomes exact.  This is a stored-layout proof, not
a claim that a tag caused damage.
"""

from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_actions import Reader


CONTRACT_PATH = CONTRACTS_DIR / "skill_damage_unit_gameplay_tag_list_native.json"
LABEL = "skillDamageUnitGameplayTagList"
SOURCE_NAMES = ("buff_9a_native.json", "buff_c5_native.json", "buff_b4_native.json")


@lru_cache(maxsize=1)
def _contract_and_sources() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    contract = json.loads(CONTRACT_PATH.read_bytes())
    if (contract.get("schema") != "endfield.skill-damage-unit-gameplay-tag-list-native-contract.v1"
            or contract.get("status") != "exact-current-build"):
        raise ValueError(f"{LABEL}.contract:identity")
    refs = contract.get("sourceContracts")
    if not isinstance(refs, list) or [row.get("path") for row in refs] != list(SOURCE_NAMES):
        raise ValueError(f"{LABEL}.contract:source-contracts")
    sources = {name: json.loads((CONTRACTS_DIR / name).read_bytes()) for name in SOURCE_NAMES}
    if any(source.get("schemaVersion") != 1 for source in sources.values()):
        raise ValueError(f"{LABEL}.contract:source-schema")
    shared = json.loads((CONTRACTS_DIR / "skill_timeline_shared_sequence_native.json").read_bytes())
    if (contract.get("nativeInputs") != shared.get("nativeInputs")
            or not all(contract["nativeInputs"].get(key) for key in (
                "gameassemblySha256", "globalMetadataSha256", "unityplayerSha256"))):
        raise ValueError(f"{LABEL}.contract:native-inputs")

    owner = contract.get("owner")
    wire = contract.get("wire")
    if (not isinstance(owner, dict) or not isinstance(wire, dict)
            or owner.get("typeName") != "Beyond.Gameplay.Core.DamageAction+DamageUnit"
            or owner.get("sourceMemberIndex") != 9
            or owner.get("sourceReadKind") != "list"
            or owner.get("listTypeName") != "System.Collections.Generic.List`1"
            or owner.get("elementTypeName") != "Beyond.Gameplay.Core.GameplayTag"
            or wire != {
                "listCount": "signed-i32-null-minus-one",
                "nullElement": "FF",
                "nonNullElementMemberCount": 1,
                "nonNullElementReadKinds": ["scalar32"],
                "minimumFollowingDamageUnitBytes": 38,
            }):
        raise ValueError(f"{LABEL}.contract:reader-shape")

    damage = sources["buff_9a_native.json"]
    contexts = damage.get("nestedContexts")
    reads = damage.get("anonymousReadOrder", {}).get("member33")
    if (not isinstance(contexts, list) or not isinstance(reads, list)
            or len(reads) != 33 or reads[owner["sourceMemberIndex"]] != "empty-list"):
        raise ValueError(f"{LABEL}.contract:damage-unit-read-order")
    selected = [row for row in contexts
                if row.get("instructionRva") == owner.get("listCallsiteRva")]
    if len(selected) != 1:
        raise ValueError(f"{LABEL}.contract:list-callsite")
    context = selected[0]
    generic = context.get("generic")
    if (context.get("methodSpecIndex") != owner.get("listMethodSpecIndex")
            or context.get("methodSpec") != owner.get("listMethodSpec")
            or context.get("typeName") != owner.get("listTypeName")
            or not isinstance(generic, dict)
            or generic.get("elementInstantiationIndex") != owner.get("elementInstantiationIndex")
            or generic.get("elementArguments") != [owner.get("elementArgumentRawHex")]):
        raise ValueError(f"{LABEL}.contract:damage-list-provider-drift")

    tags = sources["buff_c5_native.json"]
    tag_contexts = [row for row in tags.get("nestedContexts", [])
                    if row.get("methodSpecIndex") == owner["listMethodSpecIndex"]]
    if (len(tag_contexts) != 1
            or tag_contexts[0].get("methodSpec") != context["methodSpec"]
            or tag_contexts[0].get("generic") != generic
            or tags.get("anonymousReadOrder", {}).get("tagElement") != ["member1", "scalar32"]
            or not any("Core_GameplayTagForMemoryPack" in row[1]
                       and row[2] == "Deserialize" for row in tags.get("methods", []))):
        raise ValueError(f"{LABEL}.contract:element-source-drift")
    count_source = sources["buff_b4_native.json"]
    if not any("shared List<Object> conditional count/element loop" in row.get("boundary", "")
               for row in count_source.get("codeWindows", [])):
        raise ValueError(f"{LABEL}.contract:list-count-source-drift")
    return contract, sources


def validate_current_native_contract() -> dict[str, Any]:
    """Fail closed on installed-build drift and source-window drift."""
    contract, sources = _contract_and_sources()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["gameassemblySha256"], expected["globalMetadataSha256"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (not unityplayer.is_file()
            or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
            != expected["unityplayerSha256"]):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    for name, source in sources.items():
        for row in source["methods"]:
            image.validate_method_row(row, label=f"{LABEL}.{name}")
        image.check_windows(source["codeWindows"], label=f"{LABEL}.{name}")
    return {
        "status": "validated",
        "nativeInputs": expected,
        "sourceWindowValidation": list(sources),
    }


def read_positive_member_ten_list(reader: Reader) -> int:
    """Consume the direct nullable list and retain its exact source range."""
    contract, _sources = _contract_and_sources()
    start = reader.pos
    reader.tag_elements(reserve=contract["wire"]["minimumFollowingDamageUnitBytes"])
    count = struct.unpack_from("<i", reader.data, start)[0]
    reader.records.append({
        "start": start, "end": reader.pos,
        "kind": "skill-damage-unit-gameplay-tag-list",
        "count": count,
        "damageUnitMemberIndex": contract["owner"]["sourceMemberIndex"],
    })
    return count
