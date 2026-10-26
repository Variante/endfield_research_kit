"""Re-prove narrow Buff action consumer calls on the explicitly selected build.

This is a native consumer audit, independent of MemoryPack coverage. A group
whose named claims no longer hold becomes pendingReview and supplies no rows.
Compiled call presence never proves live branch selection or value ownership.

Evidence and admission boundary:

The independent names-only consumer groups in
`buff_action_consumers_native.json` prove the incoming owned CastSkill Data
reads, `caster` flowing to `GetFirstTarget.targetSettings`, and `skillId`
flowing to `ActionBlackboardExtensions.GetValue.param`. They also prove the
three flag reads and the named target-view/cast calls. The target-view operand
forwarding remains a separate obligation: the current reference-flow checker
excludes that callee's aggregate return ABI. Its false-IFix property path
returns the typed `CustomReturnType` enum through a complete return epilogue.

The separate names-only animator consumer groups prove `OnEnd` reading the
incoming owned Data's `actionOnEnd` byte, and owner-getter calls in `OnEnd`
and `ExecuteInternal`. The false-IFix return-policy getter reaches the typed
`AlwaysReturnTrue` enum through a complete epilogue. These claims do not
establish the flag branch outcome or selected animator. The two nested
configuration operands, their helper/receiver ownership and actual parameter
writes still require independent flow proofs; a return-policy enum is not an
observed animation result.

Evidence and admission boundary:

The contract is the route inventory. Each admitted group is direct static call,
owned Data read, typed argument forwarding or conditional return evidence as
explicitly claimed; none implies a later rung. Missing claims empty that group
as pendingReview; selected native drift empties all groups. Ordinary paths
retain IFix, returning-callee, storage and noninterference conditions.
Field ownership needs the incoming receiver's independently proved closed Data
slot. Fieldless concrete witnesses or explicit contiguous scalar/reference
suffixes are permitted; open-generic offsets, padding and ObjectPtr value
suffixes are not. LaunchProjectile's string suffix supports emitPos/id/source/
target reads and the proved source/target argument transfers. CreateGlobalBuff
and Switch have separately proved closed List-reference suffixes; generic
callee forwarding is not inferred. Unknown instructions/partial pointers erase
provenance. Complete CMP operands prove reads only, not forwarded registers,
flags or branch outcomes. Bounded local branch paths establish compiled
reachability, not predicate feasibility; exact local forward jumps preserve
aliases only to owned instruction boundaries.
CheckHp/Poise, skill-setting, battle-signal, cooldown/mode, armor/time dilation,
hurt/marker/tag/infliction, target/interrupt, entity/projectile/impulse, Buff
lifecycle and server-projection groups keep their independently named sinks.
Call presence never supplies argument ownership, handle identity or effects.
The time-dilation stop call is proved while finishByAction's instantiated Data
layout remains a separate gap. OnSpell's isStart byte is owned while its
abnormalType chain remains interrupted. Weapon visibility/VFX call and policy
claims do not repair its noncontiguous configuration suffix. RecoverLock's
ObjectPtr field cannot use the reference suffix witness. HitStop owns target
reads but not its curve's live argument. Keyword inherited execution, event
payload identity and target/filter quantifiers remain separate joins.
GetAITransData's aiTransKey reaches TryGetAITransData.key; saveTo reaches
UpdateTargetGroup.key around SetTarget, not a proved Blackboard assignment.
CreateGlobalBuff count/source and SetBuffDuration finder/target/value reach
their named evaluation/selection arguments; operation/early-finish reads and
lifetime sinks do not prove arithmetic or accepted writes. Switch owns choice/
options and forwards choice, but does not identify a live Option sequence.
PauseBuffTime supplies its owned isPaused byte to Buff.SetPaused.isPaused;
the independent callee proof stores that byte into its own m_isPaused after
false IFix. This compiled field-to-field path leaves the returned/cast Buff
receiver, serialized assignment and timer/tick effects unresolved.
SpellInflictionOnChar and the shorter SpellInfliction independently forward
source to GetFirstTarget and target to GetTargets_Dispose; crossed mappings
refuse. CharHurtAnim's attacker/defender and Ignite's target have independent
selection arguments. Bit-test decoding preserves CheckSpell's saved receiver
but proves no bit-test result or saved-key sink argument.
NotNextCheck, HitStop, RefreshBuffAttrModifierValue, global creation and duration
have typed AlwaysReturnTrue policy getters on their checked false-IFix paths.
Switch, CheckTargetsEqual, Vulnerable, SpellInflictionOnChar and the explicitly
contracted other actions have their own CustomReturnType getters. These enum
policies are not action/sequence results. Switch's separate Boolean
AlwaysReturnTrue returns the owned alwaysNext byte on false-IFix/non-null Data;
normalization and caller use remain unresolved. Complete literal/zero return
programs, guards and epilogues are required. DebugPrint's false-IFix path
returns AL=1 without a print call; the patched path remains opaque.
Buff.Reset/load/start/execute claims establish compiled loading stages.
ConvertToServer/_ConvertAction project into BUFF_RES on the client; they prove
no transport, server processing or parity. Initialization claims separately
join SequenceAction.Init to NewAction and environment forwarding. The anonymous
helper compares the metadata-derived AssignData virtual slot with its shared
generic implementation: equal can inline nongeneric environment/state writes;
unequal forwards receiver/data/environment/MethodInfo through the checked
virtual dispatch. This conditionally explains why named AssignData entries can
be absent; it observes no selected branch, completed assignment, generic data
slot, cast, returned action or consumer association.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract

CONTRACT_PATH = CONTRACTS_DIR / "buff_action_consumers_native.json"
SCHEMA = "endfield.buff-action-consumer-claims.v18"


def load_consumer_claims(*, gameassembly: Path | None = None,
                        metadata: Path | None = None) -> dict[str, Any]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
        status="reviewed", label="buff_action_consumers")
    gate = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
    result = {"schema": "endfield.buff-action-consumer-audit.v1",
              "status": gate.status, "detail": gate.detail,
              "contract": CONTRACT_PATH.as_posix(), "groups": {}, "failures": [],
              "evidenceBoundary": contract["evidenceBoundary"], "runtimeMeaningExact": False}
    if gate.status != "validated":
        return result
    pins = {"GameAssembly.dll": gate.gameassembly_sha256,
            "global-metadata.dat": gate.metadata_sha256}
    result["nativeInputs"] = pins
    index = BodyIndex(open_native_image(gate.gameassembly, gate.metadata))
    for name, group in contract["groups"].items():
        rows, failures = evaluate(index, group["methods"])
        diagnostics = [{**f, "group": name, "validator": "buff_action_consumers",
                        "source": CONTRACT_PATH.as_posix(), "nativeInputs": pins}
                       for f in failures]
        result["failures"].extend(diagnostics)
        result["groups"][name] = {"status": "pendingReview" if failures else "validated",
                                   "rows": [] if failures else rows,
                                   "failures": diagnostics}
    after = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != "validated":
        result.update(status=after.status, detail=after.detail, groups={})
        result["failures"].append({"validator": "buff_action_consumers",
            "check": "native-inputs-after", "source": str(gate.gameassembly),
            "expected": pins, "actual": after.detail})
        return result
    result["status"] = "pendingReview" if result["failures"] else "validated"
    result["detail"] = f"{len(result['failures'])} failed claim(s)" if result["failures"] else ""
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    # Every tool artifact belongs under an ignored root.
    from scripts.repo_paths import REPO_ROOT
    target = args.output.resolve()
    if not any(target.is_relative_to(REPO_ROOT / root) for root in ("reports", "scratch", "tmp")):
        parser.error("--output must be under reports/, scratch/ or tmp/")
    result = load_consumer_claims(gameassembly=args.gameassembly, metadata=args.metadata)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "groups": {k: v["status"] for k, v in result["groups"].items()},
                      "failures": result["failures"], "detail": result["detail"]}, ensure_ascii=False))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
