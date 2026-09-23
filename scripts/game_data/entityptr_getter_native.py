"""Validate the reviewed EntityPtr getter semantics for the selected build.

The contract keys each getter by its managed type. What a getter *means* --
its ``resolutionKind`` and, for the two kinds Story resolves statically, the
reviewed reading of its ``GetResult`` body -- is authored. Everything a client
update moves is data in the contract: the union tag and member count (read
from the PureGetter formatter switch by ``memorypack.union_dispatch``), the
member ordinals (from ``memorypack.wrapper_members``) and the ``GetResult``
body location and hash (from ``il2cpp.method_resolver``).

``--regenerate`` re-derives all of that against the installed build. A
resolving row carries ``review.bodySha256``; if the current body hashes
differently the semantics were read from other code, so the row is refused
until it is reviewed again rather than carried forward.

Run as: python -m scripts.game_data.entityptr_getter_native --regenerate [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA = "entityPtrGetterNativeContract.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "entityptr_getter.json"
#: Stable identifier cited in Story evidence; the build lives in the contract.
NATIVE_MAPPING_ID = "entityptr-getter-semantics.v2"

#: Kinds Story resolves from stored bytes; each needs a reviewed GetResult body.
RESOLVING_KINDS = frozenset({"constant_param_alias", "constant_proxy_id_lookup"})
#: Kinds that only label a value the runtime supplies.
RUNTIME_KINDS = frozenset({
    "runtime_event_args_key", "runtime_levelscript_property",
    "runtime_list_index", "runtime_zero_field_entity",
})


def _mapping_id(contract: dict[str, Any]) -> str:
    return str(contract.get("nativeMappingId") or "")


@lru_cache(maxsize=1)
def load_entityptr_getter_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    """Return getters keyed by ``(unionTag, serializedMemberCount)``, or nothing."""
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrGetterNativeContract", "gate": gate,
                         "expected": expected, "actual": actual})

    try:
        raw = Path(contract_path).read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400])
        return {}, {"status": "validation_failed", "validationFailures": failures}
    for gate, expected, actual in (("schema", SCHEMA, contract.get("schema")),
                                   ("status", "validated", contract.get("status"))):
        if actual != expected:
            reject(gate, expected, actual)
    inputs = contract.get("nativeInputs") or {}
    native = check_installed_native_inputs(
        str(inputs.get("gameAssemblySha256") or ""), str(inputs.get("metadataSha256") or ""))
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject("installed_native_inputs", NATIVE_EVIDENCE_VALIDATED,
               {"status": native.status, "detail": native.detail})
    gameassembly = getattr(native, "gameassembly", None)
    try:
        image = Path(gameassembly).read_bytes() if gameassembly and not failures else b""
    except OSError as error:
        image = b""
        reject("read_gameassembly", True, str(error)[:400])

    out: dict[tuple[int, int], dict[str, Any]] = {}
    for getter in contract.get("getters") or []:
        key = (getter.get("unionTag"), getter.get("serializedMemberCount"))
        kind = getter.get("resolutionKind")
        if not all(isinstance(value, int) for value in key) or key in out:
            reject("unique_shape", "distinct (unionTag, serializedMemberCount)", key)
            continue
        if kind not in RESOLVING_KINDS | RUNTIME_KINDS:
            reject("resolution_kind", sorted(RESOLVING_KINDS | RUNTIME_KINDS), kind)
            continue
        body = getter.get("getResult") or {}
        if kind in RESOLVING_KINDS:
            review = getter.get("review") or {}
            if not body or str(review.get("bodySha256", "")).upper() != str(body.get("bodySha256", "")).upper():
                reject("reviewed_body", {"getter": getter.get("getterName"), "review": "matches getResult"},
                       {"review": review.get("bodySha256"), "getResult": body.get("bodySha256")})
                continue
        if body and image:
            offset, size = body.get("fileOffset"), body.get("bodySize")
            expected = str(body.get("bodySha256") or "").upper()
            if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
                reject("method_byte_range", {"offset": "int", "size": ">0"}, body)
                continue
            region = image[offset:offset + size]
            digest = hashlib.sha256(region).hexdigest().upper()
            if len(region) != size or digest != expected:
                reject("method_body_sha256", {"getter": getter.get("getterName"), "sha256": expected},
                       {"size": len(region), "sha256": digest})
                continue
        out[key] = getter
    resolving = {row.get("resolutionKind") for row in out.values()} & RESOLVING_KINDS
    if resolving != RESOLVING_KINDS:
        reject("resolving_kinds_present", sorted(RESOLVING_KINDS), sorted(resolving))
    if failures:
        out = {}
    return out, {"status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
                 "nativeMappingId": _mapping_id(contract), "validationFailures": failures}


def regenerate(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Re-derive every per-build field; return the contract and refused rows."""
    from scripts.game_data.pure_getter_rows import derive_getter_rows

    authored = contract.get("getters") or []
    derived = derive_getter_rows(
        [row["getterName"] for row in authored],
        with_get_result=[row["getterName"] for row in authored
                         if "getResult" in row or row["resolutionKind"] in RESOLVING_KINDS],
    )
    refused = list(derived["refused"])
    getters = []
    for row in authored:
        fresh = derived["rows"].get(row["getterName"])
        if fresh is None:
            continue
        fresh = {"getterName": row["getterName"], "resolutionKind": row["resolutionKind"], **fresh}
        if row.get("review"):
            fresh["review"] = row["review"]
            if fresh.get("getResult", {}).get("bodySha256") != str(row["review"].get("bodySha256", "")).upper():
                refused.append(f"{row['getterName']}: GetResult body changed since review; re-review before writing")
        getters.append(fresh)
    regenerated = {
        **{key: value for key, value in contract.items() if key not in ("getters", "nativeInputs", "union")},
        "nativeInputs": derived["nativeInputs"],
        "union": derived["union"],
        "getters": sorted(getters, key=lambda row: row["unionTag"]),
    }
    return regenerated, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true", help="write the regenerated contract")
    args = parser.parse_args(argv)
    if not args.regenerate:
        _rows, audit = load_entityptr_getter_contract(args.contract)
        print(json.dumps(audit, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    contract = json.loads(args.contract.read_bytes().decode("utf-8-sig"))
    regenerated, refused = regenerate(contract)
    encoded = (json.dumps(regenerated, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    print(json.dumps({"refused": refused, "getters": len(regenerated["getters"]),
                      "sha256": hashlib.sha256(encoded).hexdigest().upper()}, indent=1))
    if refused:
        return 1
    if args.write:
        args.contract.write_bytes(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["load_entityptr_getter_contract", "regenerate", "NATIVE_MAPPING_ID"]
