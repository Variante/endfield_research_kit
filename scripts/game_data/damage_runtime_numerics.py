"""Numerical summaries of an admitted damage inspection; no raw capture replay."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

IDENTITY = ("targetServerId", "targetBattleInstanceId", "targetEntityName", "attributesIdentity", "attributesInstanceUid")
BOUNDARY = "Observed client fields and synchronous hook enclosure only; no server authority, complete combat, attack count, skill ownership or reconstructed damage formula. Attribute UID/pointer equality supplies candidate target associations, not uninterrupted lifetime proof. Operator scenario claims remain unverified."


def pin(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def fields(row):
    return {f["label"]: f for f in row.get("fields", [])}


def value(f):
    return f.get("value") if f and f.get("stateName") == "exact" else None


def identity(row):
    fs = fields(row)
    result = tuple(value(fs.get(k)) for k in IDENTITY)
    return result if all(v is not None for v in result) and result[3] != 0 else None


def stats(values):
    values = [v for v in values if isinstance(v, (float, int)) and math.isfinite(v)]
    return {"count": len(values), "min": min(values, default=None), "max": max(values, default=None), "sum": math.fsum(values)}


def analyze(report, attribute_rows=()):
    if report.get("status") != "observed" or report.get("schema") != "endfield.damage-runtime-inspection.v1":
        raise ValueError("requires observed maintained damage inspection")
    rows = list(report.get("unownedObservations", []))
    for action in report["actions"]:
        rows.extend([action["enter"], action["exit"]])
        rows.extend(action["observations"])
    rows = sorted((r for r in rows if r), key=lambda r: r.get("sequence", 0))
    entries = {(r["threadId"], r["invocationId"]): r for r in rows if r["phase"] == "enter"}
    exits = {(r["threadId"], r["invocationId"]): r for r in rows if r["phase"] == "return"}
    def ancestry(row):
        result, seen = [], set()
        key = row["threadId"], row["parentInvocationId"]
        while key in entries and key not in seen:
            seen.add(key)
            parent = entries[key]
            result.append(parent["hook"])
            key = parent["threadId"], parent["parentInvocationId"]
        return result
    modifiers, incomplete, changed = [], [], []
    calls = defaultdict(Counter)
    call_values = defaultdict(list)
    for key, entered in entries.items():
        returned = exits.get(key)
        normal = returned and returned.get("invocationReceipt", {}).get("returnedNormally") is True
        hook = entered["hook"]
        if hook.startswith("damage.Pack.") or hook == "damage.Const.EfficiencyOfDef":
            if normal:
                calls[hook][json.dumps([returned.get("callerGameAssemblyRva"), ancestry(returned)])] += 1
                call_values[hook].append(returned.get("decodedReturnValue"))
        if "ApplyModifier" not in hook:
            continue
        if not normal:
            incomplete.append({"threadId": key[0], "invocationId": key[1], "hook": hook})
            continue
        before, after = fields(entered), fields(returned)
        target, end_target = identity(entered), identity(returned)
        stable = target is not None and target == end_target
        hp0, hp1, delta = (value(before.get("storedClientHp")), value(after.get("storedClientHp")), value(after.get("realDelta")))
        hp_delta = hp1 - hp0 if hp0 is not None and hp1 is not None else None
        hp_applicable = stable and before.get("targetType", {}).get("stateName") == "exact" and "Hp" in before.get("targetType", {}).get("enumNames", [])
        residual = hp_delta - delta if hp_applicable and hp_delta is not None and delta is not None else None
        item = {"threadId": key[0], "invocationId": key[1], "entrySequence": entered.get("sequence"), "returnSequence": returned.get("sequence"), "parentInvocationId": entered["parentInvocationId"], "hook": hook,
                "target": list(target) if stable else None, "entryTarget": target, "returnTarget": end_target,
                "identityStable": stable, "targetType": value(before.get("targetType")), "targetTypeNames": before.get("targetType", {}).get("enumNames"),
                "deltaTypeBefore": value(before.get("deltaType")), "deltaTypeBeforeNames": before.get("deltaType", {}).get("enumNames"),
                "deltaTypeAfter": value(after.get("deltaType")), "deltaTypeAfterNames": after.get("deltaType", {}).get("enumNames"),
                "returnEnumValue": returned.get("returnValue"), "hpBefore": hp0, "hpAfter": hp1, "hpDelta": hp_delta, "hpResidualApplicable": hp_applicable,
                "realDelta": delta, "signedResidual": residual, "magnitudeResidual": abs(hp_delta)-abs(delta) if hp_applicable and hp_delta is not None and delta is not None else None,
                "ancestry": ancestry(entered), "actionEnclosed": "damage.Action.ExecuteInternal" in ancestry(entered)}
        modifiers.append(item)
        if not stable:
            changed.append(item)
    groups = defaultdict(list)
    for item in modifiers:
        key = json.dumps([item["hook"], item["target"], item["targetType"], item["deltaTypeBefore"], item["deltaTypeAfter"], item["returnEnumValue"]])
        groups[key].append(item)
    grouped = []
    for key, items in groups.items():
        hook, target, tt, db, da, ret = json.loads(key)
        grouped.append(dict(hook=hook, target=target, targetType=tt, deltaTypeBefore=db, deltaTypeAfter=da, returnEnumValue=ret,
                            hpResidualApplicable=all(i["hpResidualApplicable"] for i in items), pairs=len(items), actionEnclosedPairs=sum(i["actionEnclosed"] for i in items),
                            **{k: stats([i[k] for i in items]) for k in ("hpDelta", "realDelta", "signedResidual", "magnitudeResidual")}))
    outer = { (i["threadId"], i["invocationId"]): i for i in modifiers if i["hook"].endswith(".ApplyModifier") }
    nested = [i for i in modifiers if i["hook"].endswith("._DoApplyModifier") and (i["threadId"],i["parentInvocationId"]) in outer]
    attr = {}
    actor_targets = defaultdict(set)
    for item in modifiers:
        if item["identityStable"]:
            actor_targets[item["target"][-1]].add(tuple(item["target"]))
    attribute_count = 0
    for snapshot in attribute_rows:
        uid = value(snapshot.get("attributesInstanceUid"))
        dump = entries.get((snapshot["threadId"], snapshot.get("dumpInvocationId")), {})
        side = dump.get("callerGameAssemblyRva")
        for vals in snapshot["values"]:
            row = dict(zip(snapshot["columns"], vals))
            number = row.get("decodedReturnValue")
            key = (uid, row.get("attributeTypeRaw"), side, snapshot.get("callerGameAssemblyRva"), row.get("thisRaw"), tuple(ancestry(dump)) if dump else ())
            state = attr.setdefault(key, {"count": 0, "min": None, "max": None, "first": number, "last": number, "transitions": 0,
                                         "attributeNames": (row.get("attributeTypeField") or {}).get("enumNames"), "thisRaw": row.get("thisRaw")})
            state["count"] += 1
            attribute_count += 1
            if number is not None:
                state["min"] = number if state["min"] is None else min(number, state["min"])
                state["max"] = number if state["max"] is None else max(number, state["max"])
                state["transitions"] += state["last"] != number
                state["last"] = number
    return dict(schema="endfield.damage-runtime-numerics.v1", status="observed", boundary=BOUNDARY, combatComplete=False,
                actionEnclosures=len(report["actions"]), decodedRows=report.get("projectionCounts", {}).get("decodedRows"),
                identityColumns=list(IDENTITY), modifierPairs=modifiers, modifierGroups=grouped, incompleteModifierPairs=incomplete,
                unstableIdentityPairs=changed, nesting={"outerApplyPairs":len(outer), "innerDoPairs":sum(i["hook"].endswith("._DoApplyModifier") for i in modifiers),
                "innerWithDirectOuterParent":len(nested), "boundary":"HP residual applies only to targetType Hp; non-HP rows compare different quantities. Separate hook views of nested execution; never sum both as independent HP changes."},
                calls={h: {"normalReturns": sum(c.values()), "callerAncestry": [dict(callerGameAssemblyRva=json.loads(k)[0], ancestry=json.loads(k)[1], count=v) for k,v in c.items()], "returnValues": stats(call_values[h])} for h,c in calls.items()},
                attributeRows=attribute_count, attributeGroups=[dict(attributesInstanceUid=k[0], attributeType=k[1], dumpCallerRva=k[2], getterCallerRva=k[3],
                dumpAncestry=list(k[5]), actorTargets=[list(t) for t in sorted(actor_targets[k[0]]) if t[3] == k[4]], **v) for k,v in sorted(attr.items(), key=lambda kv: str(kv[0]))])


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    from scripts.repo_paths import REPO_ROOT
    if not output.is_relative_to((REPO_ROOT / "reports").resolve()):
        raise ValueError("output must be under reports/")
    before = pin(source)
    report = json.loads(source.read_text(encoding="utf-8"))
    sidecar = report["attributeSnapshotSource"]
    path = Path(sidecar["path"])
    side_pin = pin(path)
    if side_pin != {k: sidecar[k] for k in ("bytes", "sha256")}:
        raise ValueError("attribute sidecar fingerprint differs")
    def stream():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                yield json.loads(line)
    result = analyze(report, stream())
    if result["attributeRows"] != sidecar["rows"]:
        raise ValueError("attribute sidecar row count differs")
    if pin(source) != before or pin(path) != side_pin:
        raise ValueError("input changed during analysis")
    result["sources"] = {"inspection": {"path":str(source), **before}, "attributeReturns": {"path":str(path), **side_pin}, "fingerprintsVerifiedBeforeAndAfter": True}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.inspection, args.output)
    print(json.dumps({k: result[k] for k in ("status", "actionEnclosures", "nesting", "attributeRows")}))

if __name__ == "__main__":
    main()
