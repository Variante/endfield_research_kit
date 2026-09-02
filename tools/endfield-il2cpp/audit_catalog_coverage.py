#!/usr/bin/env python3
"""Audit an exact-build IL2CPP catalog against AnimeStudio recovery evidence."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "endfield-il2cpp-catalog-coverage-v1"
CATALOG_SCHEMA = "endfield-il2cpp-core-type-surface-v1"
DUMMY_INDEX_SCHEMA = "animestudio.dummydll-index.v1"
OBJECT_INDEX_SCHEMA_VERSION = 1
SAMPLE_LIMIT = 30


class AuditError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read JSON {path}: {exc}") from exc


def normalize_assembly(value: str | None) -> str:
    name = (value or "").replace("\\", "/").rsplit("/", 1)[-1]
    if name and not name.casefold().endswith(".dll"):
        name += ".dll"
    return name.casefold()


def normalize_full_name(value: str | None) -> str:
    return (value or "").replace("/", "+")


def type_key(assembly: str | None, full_name: str | None) -> tuple[str, str]:
    return normalize_assembly(assembly), normalize_full_name(full_name)


def validate_catalog(path: Path) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    catalog = load_json(path)
    if catalog.get("schema") != CATALOG_SCHEMA:
        raise AuditError(f"catalog schema is not {CATALOG_SCHEMA}: {path}")
    if catalog.get("status") not in {"complete", "complete_with_unresolved"}:
        raise AuditError(f"catalog is not complete: status={catalog.get('status')!r}")
    if int(catalog.get("coverage", {}).get("malformedTypes", -1)) != 0:
        raise AuditError("catalog contains malformed type rows")
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates = []
    for row in catalog.get("types", []):
        key = type_key(row.get("image"), row.get("fullName"))
        if not all(key):
            raise AuditError(f"catalog type is missing image/fullName: {row.get('index')}")
        if key in rows:
            duplicates.append(key)
        rows[key] = row
    if duplicates:
        raise AuditError(f"catalog contains duplicate type identities: {duplicates[:3]}")
    return catalog, rows


def validate_dummy_index(
    path: Path, root: Path, generation_path: Path, catalog: dict[str, Any]
) -> tuple[
    dict[str, Any],
    dict[tuple[str, str], dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
    str,
    dict[str, Any],
]:
    generation = load_json(generation_path)
    if generation.get("schema") != 1:
        raise AuditError(f"unsupported DummyDLL generation schema: {generation.get('schema')!r}")
    game = generation.get("game", {})
    source = catalog.get("source", {})
    expected_hashes = (
        source.get("metadataSha256"),
        source.get("gameAssemblySha256"),
    )
    actual_hashes = (game.get("metadataSha256"), game.get("gameAssemblySha256"))
    if expected_hashes != actual_hashes or not all(expected_hashes):
        raise AuditError(
            "catalog/DummyDLL native hashes differ: "
            f"catalog={expected_hashes}, generation={actual_hashes}"
        )

    inventory = load_json(path)
    if inventory.get("schema") != DUMMY_INDEX_SCHEMA or inventory.get("complete") is not True:
        raise AuditError(f"DummyDLL type inventory is incomplete or unsupported: {path}")

    manifest_files = {
        item["name"].casefold(): item for item in generation.get("assemblies", {}).get("files", [])
    }
    actual_entries = []
    types: dict[tuple[str, str], dict[str, Any]] = {}
    token_consistent_types: dict[tuple[str, str], dict[str, Any]] = {}
    catalog_by_token = {
        (normalize_assembly(row.get("image")), str(row.get("token", "")).casefold()): row
        for row in catalog.get("types", [])
    }
    duplicates: Counter[tuple[str, str]] = Counter()
    token_name_mismatches = []
    token_missing_catalog = []
    token_consistent_definition_rows = 0
    token_missing_catalog_definition_rows = 0
    type_definition_rows = 0
    seen_files = set()
    for assembly in inventory.get("assemblies", []):
        relative = assembly.get("path", "").replace("\\", "/")
        file_path = root / Path(relative)
        key_name = Path(relative).name.casefold()
        manifest = manifest_files.get(key_name)
        if manifest is None:
            raise AuditError(f"DummyDLL inventory contains an unmanifested assembly: {relative}")
        seen_files.add(key_name)
        if not file_path.is_file():
            raise AuditError(f"DummyDLL file is missing: {file_path}")
        size = file_path.stat().st_size
        digest = sha256_file(file_path)
        if size != manifest.get("bytes") or digest != manifest.get("sha256"):
            raise AuditError(f"DummyDLL file does not match generation.json: {file_path}")
        if size != assembly.get("bytes") or digest != assembly.get("sha256"):
            raise AuditError(f"DummyDLL file does not match type inventory: {file_path}")
        actual_entries.append({"path": relative, "bytes": size, "sha256": digest})
        module = assembly.get("module") or Path(relative).name
        for row in assembly.get("types", []):
            type_definition_rows += 1
            key = type_key(module, row.get("fullName"))
            if not all(key):
                raise AuditError(f"DummyDLL type is missing module/fullName: {relative}")
            if key in types:
                duplicates[key] += 1
            else:
                types[key] = {**row, "assembly": module}
            token_key = (normalize_assembly(module), str(row.get("token", "")).casefold())
            catalog_row = catalog_by_token.get(token_key)
            if catalog_row is None:
                token_missing_catalog_definition_rows += 1
                if len(token_missing_catalog) < SAMPLE_LIMIT:
                    token_missing_catalog.append({
                        "assembly": module,
                        "token": row.get("token"),
                        "dummyFullName": row.get("fullName"),
                    })
            elif normalize_full_name(catalog_row.get("fullName")) == key[1]:
                token_consistent_definition_rows += 1
                token_consistent_types.setdefault(key, {**row, "assembly": module})
            elif len(token_name_mismatches) < SAMPLE_LIMIT:
                token_name_mismatches.append({
                    "assembly": module,
                    "token": row.get("token"),
                    "dummyFullName": row.get("fullName"),
                    "catalogFullName": catalog_row.get("fullName"),
                })
    if seen_files != set(manifest_files):
        missing = sorted(set(manifest_files) - seen_files)
        raise AuditError(f"DummyDLL inventory omits generated assemblies: {missing[:5]}")
    if inventory.get("assemblyCount") != len(actual_entries) or inventory.get("typeCount") != type_definition_rows:
        raise AuditError("DummyDLL inventory terminal counts do not match its rows")
    diagnostics = {
        "typeDefinitionRows": type_definition_rows,
        "uniqueTypeIdentities": len(types),
        "invalidTypeDefinitions": int(inventory.get("invalidTypeCount", 0)),
        "duplicateTypeIdentityDefinitions": sum(duplicates.values()),
        "duplicateTypeIdentityCount": len(duplicates),
        "duplicateTypeIdentitySamples": [
            {"assembly": key[0], "fullName": key[1], "additionalDefinitions": count}
            for key, count in sorted(duplicates.items())[:SAMPLE_LIMIT]
        ],
        "tokenConsistentDefinitionRows": token_consistent_definition_rows,
        "tokenConsistentTypeIdentities": len(token_consistent_types),
        "tokenNameMismatchDefinitionRows": type_definition_rows - token_consistent_definition_rows - token_missing_catalog_definition_rows,
        "tokenMissingCatalogDefinitionRows": token_missing_catalog_definition_rows,
        "tokenNameMismatchSamples": token_name_mismatches,
        "tokenMissingCatalogSamples": token_missing_catalog,
    }
    return generation, types, token_consistent_types, stable_hash(actual_entries), diagnostics


def validate_object_index(root: Path, dummy_fingerprint: str) -> tuple[dict[str, Any] | None, str | None]:
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        return None, "missing terminal summary.json"
    try:
        summary = load_json(summary_path)
    except AuditError as exc:
        return None, str(exc)
    if summary.get("schemaVersion") != OBJECT_INDEX_SCHEMA_VERSION:
        return None, f"unsupported schemaVersion={summary.get('schemaVersion')!r}"
    if summary.get("complete") is not True or summary.get("errors"):
        return None, "summary is incomplete or records errors"
    recorded = (
        summary.get("stageSignature", {})
        .get("payload", {})
        .get("cli", {})
        .get("dummyDlls", {})
        .get("fingerprint")
    )
    if recorded != dummy_fingerprint:
        return None, f"DummyDLL fingerprint mismatch: index={recorded}, current={dummy_fingerprint}"
    for name in ("objects", "schemas"):
        output = summary.get("outputs", {}).get(name, {})
        path = root / str(output.get("path", ""))
        if not path.is_file():
            return None, f"missing committed {name} output: {path}"
        if path.stat().st_size != output.get("bytes") or sha256_file(path) != output.get("sha256"):
            return None, f"committed {name} output hash/size mismatch: {path}"
    return summary, None


def read_object_rows(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix.casefold() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditError(f"malformed object-index row {path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise AuditError(f"non-object object-index row {path}:{line_number}")
            yield row


def scan_object_index(
    root: Path,
    summary: dict[str, Any],
    catalog_types: dict[tuple[str, str], dict[str, Any]],
    dummy_types: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    decode_statuses: Counter[str] = Counter()
    type_tree_sources: Counter[str] = Counter()
    join_instances: Counter[str] = Counter()
    scripts: dict[tuple[str, str], dict[str, Any]] = {}
    mono_script_identities: Counter[tuple[str, str]] = Counter()
    invalid_mono_scripts = []
    missing_identity = []
    object_rows = 0
    mono_script_rows = 0
    mono_behaviours = 0

    for row in read_object_rows(root / summary["outputs"]["objects"]["path"]):
        if row.get("recordType") == "monoScript":
            mono_script_rows += 1
            namespace = str(row.get("namespace") or "")
            class_name = str(row.get("className") or "")
            full_name = f"{namespace}.{class_name}" if namespace and class_name else class_name
            key = type_key(row.get("assemblyName"), full_name)
            if all(key):
                mono_script_identities[key] += 1
            elif len(invalid_mono_scripts) < SAMPLE_LIMIT:
                invalid_mono_scripts.append({
                    "assemblyName": row.get("assemblyName"),
                    "namespace": row.get("namespace"),
                    "className": row.get("className"),
                    "object": row.get("object"),
                })
            continue
        if row.get("recordType") != "object":
            continue
        object_rows += 1
        if row.get("type") != "MonoBehaviour":
            continue
        mono_behaviours += 1
        status = str(row.get("decodeStatus") or "missing")
        source = str(row.get("typeTreeSource") or "missing")
        decode_statuses[status] += 1
        type_tree_sources[source] += 1
        script = row.get("script") if isinstance(row.get("script"), dict) else {}
        key = type_key(script.get("assembly"), script.get("fullName"))
        if not all(key):
            join_instances["missing_script_identity"] += 1
            if len(missing_identity) < SAMPLE_LIMIT:
                missing_identity.append({
                    "name": row.get("name"),
                    "decodeStatus": status,
                    "object": row.get("object"),
                })
            continue
        in_catalog = key in catalog_types
        in_dummy = key in dummy_types
        quadrant = f"catalog_{'yes' if in_catalog else 'no'}__dummy_{'yes' if in_dummy else 'no'}"
        join_instances[quadrant] += 1
        entry = scripts.setdefault(key, {
            "assembly": script.get("assembly"),
            "fullName": script.get("fullName"),
            "instances": 0,
            "decodeStatuses": Counter(),
            "typeTreeSources": Counter(),
            "inCatalog": in_catalog,
            "inDummyDll": in_dummy,
        })
        entry["instances"] += 1
        entry["decodeStatuses"][status] += 1
        entry["typeTreeSources"][source] += 1

    if object_rows != summary.get("counts", {}).get("objects"):
        raise AuditError(
            f"object count disagrees with summary for {root}: "
            f"rows={object_rows}, summary={summary.get('counts', {}).get('objects')}"
        )
    if mono_script_rows != summary.get("counts", {}).get("monoScripts"):
        raise AuditError(
            f"MonoScript count disagrees with summary for {root}: "
            f"rows={mono_script_rows}, summary={summary.get('counts', {}).get('monoScripts')}"
        )
    script_rows = []
    for entry in scripts.values():
        script_rows.append({
            **entry,
            "decodeStatuses": dict(sorted(entry["decodeStatuses"].items())),
            "typeTreeSources": dict(sorted(entry["typeTreeSources"].items())),
        })
    script_rows.sort(key=lambda row: (-row["instances"], row["assembly"], row["fullName"]))
    gaps = [row for row in script_rows if not row["inCatalog"] or not row["inDummyDll"]]
    decode_gaps = [
        row for row in script_rows
        if sum(count for status, count in row["decodeStatuses"].items() if status != "decoded")
    ]
    decode_gaps.sort(key=lambda row: (
        -sum(count for status, count in row["decodeStatuses"].items() if status != "decoded"),
        row["assembly"],
        row["fullName"],
    ))
    recovery_candidates = [
        row for row in decode_gaps if row["inCatalog"] and not row["inDummyDll"]
    ]
    mono_script_keys = set(mono_script_identities)
    mono_script_gaps = [key for key in mono_script_keys if key not in dummy_types]
    mono_script_catalog_gaps = [key for key in mono_script_keys if key not in catalog_types]
    referenced_keys = set(scripts)
    return {
        "root": str(root.resolve()),
        "source": summary.get("stageSignature", {}).get("payload", {}).get("source"),
        "objectRows": object_rows,
        "monoBehaviourRows": mono_behaviours,
        "monoScripts": {
            "rows": mono_script_rows,
            "distinctIdentities": len(mono_script_keys),
            "duplicateRows": sum(count - 1 for count in mono_script_identities.values()),
            "invalidIdentityRows": len(invalid_mono_scripts),
            "catalogYesDummyYes": len(mono_script_keys & set(catalog_types) & set(dummy_types)),
            "catalogYesDummyNo": len((mono_script_keys & set(catalog_types)) - set(dummy_types)),
            "catalogNoDummyYes": len((mono_script_keys & set(dummy_types)) - set(catalog_types)),
            "catalogNoDummyNo": len(mono_script_keys - set(catalog_types) - set(dummy_types)),
            "referencedByMonoBehaviours": len(mono_script_keys & referenced_keys),
            "referencedScriptsMissingMonoScriptRow": len(referenced_keys - mono_script_keys),
            "missingDummyDllSamples": [
                {"assembly": key[0], "fullName": key[1], "rows": mono_script_identities[key]}
                for key in sorted(mono_script_gaps)[:SAMPLE_LIMIT]
            ],
            "missingCatalogSamples": [
                {"assembly": key[0], "fullName": key[1], "rows": mono_script_identities[key]}
                for key in sorted(mono_script_catalog_gaps)[:SAMPLE_LIMIT]
            ],
            "invalidIdentitySamples": invalid_mono_scripts,
        },
        "distinctReferencedMonoScripts": len(scripts),
        "decodeStatuses": dict(sorted(decode_statuses.items())),
        "typeTreeSources": dict(sorted(type_tree_sources.items())),
        "joinInstances": dict(sorted(join_instances.items())),
        "joinScripts": {
            "catalogYesDummyYes": sum(row["inCatalog"] and row["inDummyDll"] for row in script_rows),
            "catalogYesDummyNo": sum(row["inCatalog"] and not row["inDummyDll"] for row in script_rows),
            "catalogNoDummyYes": sum(not row["inCatalog"] and row["inDummyDll"] for row in script_rows),
            "catalogNoDummyNo": sum(not row["inCatalog"] and not row["inDummyDll"] for row in script_rows),
        },
        "gapScriptSamples": gaps[:SAMPLE_LIMIT],
        "decodeGapScriptSamples": decode_gaps[:SAMPLE_LIMIT],
        "schemaRecoveryCandidateSamples": recovery_candidates[:SAMPLE_LIMIT],
        "missingScriptIdentitySamples": missing_identity,
        "scripts": script_rows,
    }


def build_report(
    catalog_path: Path,
    dummy_root: Path,
    generation_path: Path,
    dummy_index_path: Path,
    object_roots: list[Path],
) -> dict[str, Any]:
    catalog, catalog_types = validate_catalog(catalog_path)
    generation, dummy_types, safe_dummy_types, dummy_fingerprint, dummy_diagnostics = validate_dummy_index(
        dummy_index_path, dummy_root, generation_path, catalog
    )
    accepted = []
    rejected = []
    for root in object_roots:
        summary, reason = validate_object_index(root, dummy_fingerprint)
        if reason:
            rejected.append({"root": str(root.resolve()), "reason": reason})
            continue
        assert summary is not None
        accepted.append(scan_object_index(root, summary, catalog_types, safe_dummy_types))

    catalog_keys = set(catalog_types)
    dummy_keys = set(dummy_types)
    skipped_images = {
        normalize_assembly(name)
        for name in generation.get("cpp2il", {}).get("skippedMalformedImages", [])
    }
    missing = catalog_keys - dummy_keys
    missing_in_skipped_images = {key for key in missing if key[0] in skipped_images}
    missing_other = missing - missing_in_skipped_images
    report = {
        "schema": SCHEMA,
        "status": "complete" if accepted and not rejected else "partial_evidence" if accepted else "failed_evidence",
        "scope": "exact-build catalog versus generated DummyDLL and committed AnimeStudio object indexes",
        "sources": {
            "catalog": str(catalog_path.resolve()),
            "catalogStatus": catalog.get("status"),
            "metadataSha256": catalog.get("source", {}).get("metadataSha256"),
            "gameAssemblySha256": catalog.get("source", {}).get("gameAssemblySha256"),
            "dummyDllRoot": str(dummy_root.resolve()),
            "dummyDllGeneration": str(generation_path.resolve()),
            "dummyDllInventory": str(dummy_index_path.resolve()),
            "dummyDllFingerprint": dummy_fingerprint,
        },
        "coverage": {
            "catalogTypes": len(catalog_keys),
            "dummyDllTypeDefinitions": dummy_diagnostics["typeDefinitionRows"],
            "dummyDllTypes": len(dummy_keys),
            "dummyDllInvalidTypeDefinitions": dummy_diagnostics["invalidTypeDefinitions"],
            "dummyDllDuplicateTypeIdentityDefinitions": dummy_diagnostics["duplicateTypeIdentityDefinitions"],
            "dummyDllDuplicateTypeIdentityCount": dummy_diagnostics["duplicateTypeIdentityCount"],
            "dummyDllTokenConsistentTypeDefinitions": dummy_diagnostics["tokenConsistentDefinitionRows"],
            "dummyDllTokenConsistentTypeIdentities": dummy_diagnostics["tokenConsistentTypeIdentities"],
            "dummyDllTokenNameMismatchDefinitions": dummy_diagnostics["tokenNameMismatchDefinitionRows"],
            "dummyDllTokenMissingCatalogDefinitions": dummy_diagnostics["tokenMissingCatalogDefinitionRows"],
            "catalogTypesInDummyDll": len(catalog_keys & dummy_keys),
            "catalogTypesInTokenConsistentDummyDll": len(catalog_keys & set(safe_dummy_types)),
            "catalogTypesMissingDummyDll": len(missing),
            "catalogTypesMissingInCpp2ILSkippedImages": len(missing_in_skipped_images),
            "catalogTypesMissingOther": len(missing_other),
            "dummyDllTypesAbsentCatalog": len(dummy_keys - catalog_keys),
            "cpp2ilSkippedMalformedImages": generation.get("cpp2il", {}).get("skippedMalformedImageCount"),
            "cpp2ilSkippedMalformedTypes": generation.get("cpp2il", {}).get("skippedMalformedTypeCount"),
        },
        "objectIndexes": {"accepted": accepted, "rejected": rejected},
        "samples": {
            "dummyDllDuplicateTypeIdentities": dummy_diagnostics["duplicateTypeIdentitySamples"],
            "dummyDllTokenNameMismatches": dummy_diagnostics["tokenNameMismatchSamples"],
            "dummyDllTokensMissingCatalog": dummy_diagnostics["tokenMissingCatalogSamples"],
            "catalogTypesMissingDummyDll": [
                {"assembly": key[0], "fullName": key[1]} for key in sorted(missing)[:SAMPLE_LIMIT]
            ],
            "catalogTypesMissingOther": [
                {"assembly": key[0], "fullName": key[1]} for key in sorted(missing_other)[:SAMPLE_LIMIT]
            ],
            "dummyDllTypesAbsentCatalog": [
                {"assembly": key[0], "fullName": key[1]}
                for key in sorted(dummy_keys - catalog_keys)[:SAMPLE_LIMIT]
            ],
        },
        "interpretation": [
            "Catalog types without a MonoScript or exported MonoBehaviour are runtime-only/unobserved, not export failures.",
            "A catalog type missing from DummyDLL is a Cpp2IL schema-coverage gap; it does not mean the IL2CPP class is absent.",
            "A name-only DummyDLL match is not a usable schema: the assembly and TypeDef token must identify the same catalog type.",
            "Only object indexes with a complete terminal summary and matching output/DummyDLL fingerprints contribute rows.",
        ],
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    coverage = report["coverage"]
    lines = [
        "# IL2CPP catalog coverage audit",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Type coverage",
        "",
        f"- Exact-build catalog types: **{coverage['catalogTypes']:,}**",
        f"- Types emitted in DummyDLLs: **{coverage['dummyDllTypes']:,}**",
        f"- Named DummyDLL type definitions: **{coverage['dummyDllTypeDefinitions']:,}**",
        f"- Unnamed/invalid DummyDLL definitions: **{coverage['dummyDllInvalidTypeDefinitions']:,}**",
        f"- Duplicate-identity DummyDLL definitions: **{coverage['dummyDllDuplicateTypeIdentityDefinitions']:,}**",
        f"- Catalog types present by name in DummyDLLs: **{coverage['catalogTypesInDummyDll']:,}**",
        f"- Catalog types with matching name and TypeDef token: **{coverage['catalogTypesInTokenConsistentDummyDll']:,}**",
        f"- DummyDLL definitions with token/name disagreement: **{coverage['dummyDllTokenNameMismatchDefinitions']:,}**",
        f"- Catalog types missing from DummyDLLs: **{coverage['catalogTypesMissingDummyDll']:,}**",
        f"- Missing types in Cpp2IL-skipped images: **{coverage['catalogTypesMissingInCpp2ILSkippedImages']:,}**",
        f"- Other missing types: **{coverage['catalogTypesMissingOther']:,}**",
        f"- DummyDLL types absent from catalog: **{coverage['dummyDllTypesAbsentCatalog']:,}**",
        "",
        "## Exported MonoBehaviours",
        "",
    ]
    for item in report["objectIndexes"]["accepted"]:
        lines.extend([
            f"### {item.get('source') or Path(item['root']).parent.name}",
            "",
            f"- MonoBehaviour rows: **{item['monoBehaviourRows']:,}**",
            f"- MonoScript rows / distinct identities: **{item['monoScripts']['rows']:,} / {item['monoScripts']['distinctIdentities']:,}**",
            f"- MonoScript catalog/DummyDLL joins: `{json.dumps({key: value for key, value in item['monoScripts'].items() if key.startswith('catalog')}, sort_keys=True)}`",
            f"- Distinct scripts referenced by MonoBehaviours: **{item['distinctReferencedMonoScripts']:,}**",
            f"- Decode statuses: `{json.dumps(item['decodeStatuses'], sort_keys=True)}`",
            f"- TypeTree sources: `{json.dumps(item['typeTreeSources'], sort_keys=True)}`",
            f"- Script joins: `{json.dumps(item['joinScripts'], sort_keys=True)}`",
            "",
        ])
        candidates = item.get("schemaRecoveryCandidateSamples", [])
        if candidates:
            lines.extend(["#### Immediate schema-recovery candidates", ""])
            for candidate in candidates:
                non_decoded = sum(
                    count for status, count in candidate["decodeStatuses"].items()
                    if status != "decoded"
                )
                lines.append(
                    f"- `{candidate['assembly']}::{candidate['fullName']}`: "
                    f"{non_decoded:,} non-decoded of {candidate['instances']:,} observed instances"
                )
            lines.append("")
    if report["objectIndexes"]["rejected"]:
        lines.extend(["## Rejected evidence", ""])
        for item in report["objectIndexes"]["rejected"]:
            lines.append(f"- `{item['root']}`: {item['reason']}")
        lines.append("")
    lines.extend(["## Evidence boundary", ""])
    lines.extend(f"- {text}" for text in report["interpretation"])
    lines.append("")
    return "\n".join(lines)


def write_report(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--dummydll-root", type=Path, default=Path("tools/DummyDll"))
    parser.add_argument("--dummydll-generation", type=Path)
    parser.add_argument("--dummydll-index", type=Path, required=True)
    parser.add_argument("--object-index", type=Path, action="append", required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generation = args.dummydll_generation or args.dummydll_root / "generation.json"
    try:
        report = build_report(
            args.catalog,
            args.dummydll_root,
            generation,
            args.dummydll_index,
            args.object_index,
        )
    except AuditError as exc:
        print(f"coverage audit failed: {exc}")
        return 2
    write_report(args.out_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.out_md:
        write_report(args.out_md, render_markdown(report))
    print(
        f"coverage audit {report['status']}: "
        f"{report['coverage']['catalogTypesInDummyDll']:,}/"
        f"{report['coverage']['catalogTypes']:,} catalog types match DummyDLL names, "
        f"{report['coverage']['catalogTypesInTokenConsistentDummyDll']:,} are token-consistent; "
        f"{len(report['objectIndexes']['accepted'])} object indexes accepted, "
        f"{len(report['objectIndexes']['rejected'])} rejected"
    )
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
