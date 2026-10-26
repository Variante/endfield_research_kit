"""Project admitted collision observations onto exact Assets geometry variants.

Selections are local inputs, never cached proof. Every publication replays the
maintained geometry audit against the selected installed binaries and receipts.
Name matches, accepted filter candidates and missing observations cannot prove
movement selection or solver participation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from scripts.common import rel_path, resolve_installed_game_data_root, write_json
from scripts.game_data import collision_runtime_geometry
from scripts.game_data.cooked_collision_corpus import check_receipt_snapshot, validate_receipt

SELECTION_SCHEMA = "endfield.assets-collision-runtime-selection.v1"
PROJECTION_SCHEMA = "endfield.assets-collision-runtime.v1"


def object_key(identity: dict) -> tuple:
    cab = identity["sourceFile"].lower()
    if not re.fullmatch(r"cab-[0-9a-f]{32}", cab):
        raise ValueError("runtime projection requires a full serialized CAB identity")
    value = identity["pathId"]
    if isinstance(value, bool) or not re.fullmatch(r"-?[0-9]+", str(value)):
        raise ValueError("invalid serialized PathID")
    pid = int(value)
    if not -(1 << 63) <= pid < (1 << 64):
        raise ValueError("serialized PathID outside signed/unsigned 64-bit range")
    offset = int(identity["sourceOffset"])
    if offset < 0:
        raise ValueError("negative serialized source offset")
    # These fields identify the physical stored object too. CAB/PathID alone
    # cannot silently select a different overlay copy.
    source = str(identity["sourceOriginalPath"]).replace("\\", "/").casefold()
    return cab, pid & ((1 << 64) - 1), source, offset


def variant_key(collision: dict) -> tuple:
    return (*object_key(collision["identity"]), collision["kind"],
            collision["rawSha256"], collision["bufferSha256"])


def project_samples(entries: list[dict], audits: list[dict]) -> dict:
    """Aggregate only exact joins from already admitted audits; stage mutations."""
    variants = {}
    for entry in entries:
        if "cl" in entry:
            key = variant_key(entry["cl"])
            if key in variants:
                raise ValueError("duplicate physical collision variant in Assets")
            variants[key] = entry
    groups = defaultdict(lambda: defaultdict(set))
    captures, seen_journals = [], set()
    unmatched = set()
    for audit in audits:
        if (audit.get("schema") != "endfield.collision-runtime-geometry.v2"
                or audit.get("status") != "validated_sampled_geometry_identity"
                or audit.get("nativeIndexGate", {}).get("status") != "validated"):
            raise ValueError("runtime geometry audit/native gate did not validate")
        journal = audit["journalSha256"]
        if journal in seen_journals:
            continue
        seen_journals.add(journal)
        captures.append({"session": Path(audit["session"]).name,
                         "journalSha256": journal, "archiveSha256": audit["archiveSha256"]})
        for sample in audit["samples"]:
            stored = sample.get("storedMesh")
            if stored is None:
                unmatched.add((journal, sample["getterCall"]))
                continue
            identity = object_key(stored["identity"])
            origin = sample["serializedOrigin"]
            if identity[:2] != (origin["cab"].lower(), int(origin["pathId"]) & ((1 << 64) - 1)):
                raise ValueError("runtime/stored serialized identity differs")
            key = (*identity, "triangle", stored["rawSha256"], stored["payloadSha256"])
            if key not in variants:
                unmatched.add((journal, sample["getterCall"]))
                continue
            collision = variants[key]["cl"]
            if (not stored["countsMatch"] or collision["vertexCount"] != stored["vertices"]
                    or collision["faceCount"] != stored["triangles"]):
                raise ValueError("runtime/Assets geometry dimensions differ")
            group = groups[key]
            group["querySamples"].add((journal, sample["conversionCall"]))
            if sample.get("vertexIndexEquality") == "captured_arrays_match":
                group["completeArraySamples"].add((journal, sample["arrayObservationCall"]))
            elif sample.get("arrayPrefixEquality"):
                spans = sample["arrayPrefixEquality"]
                if any(spans[name]["capturedBytes"] > 0 for name in ("vertices", "indices")):
                    group["prefixArraySamples"].add((journal, sample["arrayObservationCall"]))
            eligible = sample.get("sweepFeature", {}).get("status") != "initial_overlap_or_nonpositive_distance"
            if not eligible:
                group["excludedSweepPoints"].add((journal, sample["conversionCall"]))
            elif sample.get("currentSurface", {}).get("status") == "conditional_current_surface":
                group["conditionalSurfaceSamples"].add((journal, sample["conversionCall"]))
            consumption = sample["queryConsumption"]
            for owner in consumption["selectedOwnerReturns"]:
                if owner["status"] == "unique_physical_hit_fields" and owner["kind"] in ("floor_query", "movement_query"):
                    group["movementResults"].add((journal, owner["ownerCall"], owner["queryHitCall"]))
                    if owner.get("floor", {}).get("walkableFloor") is True:
                        group["walkableFloorResults"].add((journal, owner["ownerCall"], owner["queryHitCall"]))
            for decision in consumption["filterDecisions"]:
                if decision["accepted"] and decision["joinStatus"] == "unique_same_owner_returned_proxy":
                    group["acceptedFilterCandidates"].add((journal, decision["filterCall"]))
    fields = ("querySamples", "completeArraySamples", "prefixArraySamples", "movementResults",
              "walkableFloorResults", "acceptedFilterCandidates", "conditionalSurfaceSamples", "excludedSweepPoints")
    projected = {key: {"schema": PROJECTION_SCHEMA, "queryObserved": True,
                       "counts": {name: len(group[name]) for name in fields},
                       "solverContacts": "unproved"} for key, group in groups.items()}
    # A fresh failed or missing selection never leaves previous runtime claims.
    for entry in entries:
        if "cl" in entry:
            entry["cl"].pop("runtime", None)
    for key, evidence in projected.items():
        variants[key]["cl"]["runtime"] = evidence
    totals = Counter()
    for evidence in projected.values():
        totals.update(evidence["counts"])
    return {"schema": PROJECTION_SCHEMA, "status": "validated", "captures": captures,
            "counts": {"queryObservedVariants": len(projected),
                       "movementResultVariants": sum(v["counts"]["movementResults"] > 0 for v in projected.values()),
                       "completeArrayVariants": sum(v["counts"]["completeArraySamples"] > 0 for v in projected.values()),
                       "prefixOnlyVariants": sum(v["counts"]["prefixArraySamples"] > 0 and not v["counts"]["completeArraySamples"] for v in projected.values()),
                       "unmatchedGetterSamples": len(unmatched), **dict(totals)},
            "evidenceBoundary": "Direct sampled query geometry and exact stored identities/hashes. Unique movement returns and accepted filter candidates are separate. Surface comparisons use separately timed poses and remain conditional; initial-overlap points are excluded. Solver contacts and continuous activation remain unproved."}


def apply_runtime_publication(payload: dict, *, root: Path, selection_path: Path,
                              corpus_path: Path, sessions: list[Path] | None = None,
                              stored_receipts: list[Path] | None = None,
                              summary_path: Path | None = None) -> dict:
    """Revalidate local selections, publish runtime metadata, retain stored OBJs."""
    entries = payload["entries"]
    for entry in entries:
        if "cl" in entry:
            entry["cl"].pop("runtime", None)
    evidence = {"schema": PROJECTION_SCHEMA, "status": "missing",
                "diagnostic": "No selected runtime collision capture."}
    try:
        explicit = sessions is not None or stored_receipts is not None
        selection_bytes = None
        if explicit:
            if not selection_path.resolve().is_relative_to((root / "reports").resolve()):
                raise ValueError("generated runtime selections must be saved under reports/")
            if not sessions or not stored_receipts:
                raise ValueError("select both runtime sessions and authenticated stored receipts")
            selection = {"schema": SELECTION_SCHEMA, "sessions": [rel_path(p.resolve(), root) for p in sessions],
                         "storedReceipts": [rel_path(p.resolve(), root) for p in stored_receipts]}
        elif selection_path.is_file():
            selection_bytes = selection_path.read_bytes()
            selection = json.loads(selection_bytes)
        else:
            payload.setdefault("collision", {})["runtime"] = evidence
            return evidence
        if selection["schema"] != SELECTION_SCHEMA:
            raise ValueError("unsupported runtime collision selection schema")
        resolved = {}
        for field, limit in (("sessions", 8), ("storedReceipts", 16)):
            paths = selection[field]
            if not isinstance(paths, list) or not 1 <= len(paths) <= limit or any(not isinstance(p, str) or not p for p in paths):
                raise ValueError("invalid/bounded runtime selection: " + field)
            resolved[field] = list(dict.fromkeys((root / p).resolve() for p in paths))
        corpus_bytes = corpus_path.read_bytes()
        corpus = validate_receipt(corpus_path, summary_path=summary_path)
        if payload.get("collision", {}).get("receiptSha256") != hashlib.sha256(corpus_bytes).hexdigest():
            raise ValueError("Assets collision publication differs from selected corpus; refresh --publish collision first")
        # Compare index identities to the admitted current selection as well as
        # its receipt marker. The runtime audit independently rejoins actual
        # raw/typed buffers for every source used by a runtime label.
        admitted = {}
        for row in corpus["objects"]:
            for item in row["payloads"]:
                key = (*object_key(row["identity"]), item["kind"], row["rawSha256"], item["sha256"])
                admitted[key] = (item["vertexCount"], item.get("triangleCount", item.get("polygonCount")))
        indexed = {}
        for entry in entries:
            if "cl" in entry:
                indexed[variant_key(entry["cl"])] = (entry["cl"]["vertexCount"], entry["cl"]["faceCount"])
        if indexed != admitted:
            raise ValueError("Assets collision identities/hashes/counts differ from authenticated corpus")
        game_root = resolve_installed_game_data_root()
        if game_root is None:
            raise ValueError("selected installed game root unavailable")
        audits = [collision_runtime_geometry.audit(session, stored_receipt=resolved["storedReceipts"], game_root=game_root)
                  for session in resolved["sessions"]]
        for audit in audits:
            if audit.get("status") != "validated_sampled_geometry_identity":
                detail = json.dumps(audit.get("diagnostics", []), ensure_ascii=False)[:1200]
                raise ValueError(f"runtime geometry audit failed: {Path(audit['session']).name}: {detail}")
        check_receipt_snapshot(corpus)
        if corpus_path.read_bytes() != corpus_bytes:
            raise ValueError("selected collision corpus changed during runtime publication")
        if selection_bytes is not None and selection_path.read_bytes() != selection_bytes:
            raise ValueError("runtime collision selection changed during publication")
        evidence = project_samples(entries, audits)
        if explicit:
            write_json(selection_path, selection)
    except (OSError, ValueError, KeyError, TypeError) as error:
        for entry in entries:
            if "cl" in entry:
                entry["cl"].pop("runtime", None)
        evidence = {"schema": PROJECTION_SCHEMA, "status": "unavailable", "diagnostic": str(error)[:1800]}
    payload.setdefault("collision", {})["runtime"] = evidence
    return evidence
