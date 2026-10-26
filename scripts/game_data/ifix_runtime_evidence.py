"""Audit saved native entry profiles against IFix runtime evidence questions.

This reads retained inspection/profile/summary identities and a previously
passing IFix native audit. It never opens a process, creates a capture profile,
instruments a method or admits runtime claims. Matching a declared hook RVA
identifies a candidate recorded code site, not a closed generic type or an
executed alias branch. Entry-only profiles cannot supply paired post-copy,
rebase, context-preparation, return or storage-write observations.

Use explicit selected native inputs and repeated --inspection paths. Output is
a local capability/gap report under reports/ifix. Missing/mismatched selected
inputs, stale native receipts and malformed requirements preserve prior output.
Saved-session refusals are bounded diagnostics with no admitted claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.mission_trace_inspect import parse_json, safe_path
from scripts.repo_paths import REPO_ROOT


class RuntimeEvidenceError(ValueError):
    """A saved capability declaration or prerequisite cannot be reused."""


MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_HOOKS = 96
DEFAULT_REQUIREMENTS = CONTRACTS_DIR / 'ifix_runtime_evidence.json'
DEFAULT_NATIVE_CONTRACT = CONTRACTS_DIR / 'ifix_vm_operands_native.json'


def require(ok: bool, detail: str) -> None:
    if not ok:
        raise RuntimeEvidenceError('ifix-runtime-evidence: ' + detail)


def read(path: Path, limit: int = MAX_JSON_BYTES) -> tuple[dict[str, Any], str]:
    require(path.stat().st_size <= limit, f'JSON byte budget exceeded: {path}')
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    require(len(raw) <= limit, f'JSON grew beyond byte budget: {path}')
    obj = parse_json(raw, str(path))
    require(type(obj) is dict, f'expected object: {path}')
    return obj, hashlib.sha256(raw).hexdigest().upper()


def sha(path: Path) -> str:
    before = path.stat()
    value = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            value.update(chunk)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), f'file changed while hashing: {path}')
    return value.hexdigest().upper()


def ref(obj: dict, path: str) -> Any:
    for key in path.split('.'):
        require(type(obj) is dict and key in obj, f'missing native reference: {path}')
        obj = obj[key]
    return obj


def requirements(path: Path) -> dict:
    spec, _ = read(path)
    require(spec.get('schema') == 'endfield.ifix-runtime-evidence-requirements.v1'
            and spec.get('status') == 'reviewed' and spec.get('evidenceBoundary') == 'unresolved', 'unsupported requirements/schema/boundary')
    groups = spec.get('nativeGroups')
    require(type(groups) is list and groups and len(groups) == len(set(groups))
            and all(type(value) is str and value.endswith('Rules') for value in groups), 'native group references required')
    require(type(spec.get('methodRefs')) is list and all(type(value) is str for value in spec['methodRefs']), 'method references required')
    questions = spec.get('questions', {})
    require(type(questions) is dict and set(questions) == {'descriptorAliasing', 'genericContexts', 'patchExecution'}, 'question set differs')
    for name, question in questions.items():
        require(type(question) is dict and type(question.get('requiredObservations')) is list and question['requiredObservations']
                and all(type(value) is str and value for value in question['requiredObservations'])
                and all(type(question.get(key)) is str and question[key] for key in ('acceptance', 'stop')), 'missing observation/acceptance rule: ' + name)
    return spec


def selected_native_context(spec: dict, *, gameassembly: Path, metadata: Path,
                            native_contract: Path, native_audit: Path,
                            validation_receipt: Path, source_root: Path = REPO_ROOT) -> tuple[dict, dict]:
    """Gate explicit native inputs before loading/reusing generated proofs."""
    contract, contract_hash = read(native_contract)
    pins = contract.get('nativeInputs')
    require(type(pins) is dict and contract.get('status') == 'validated' and contract.get('evidenceBoundary') == 'direct'
            and all(type(pins.get(key)) is str and re.fullmatch(r'[0-9A-Fa-f]{64}', pins[key])
                    for key in ('gameAssemblySha256', 'globalMetadataSha256', 'unityPlayerSha256')), 'reviewed native inputs required')
    require(gameassembly is not None and metadata is not None, 'explicit native pair required')
    gate = check_installed_native_inputs(pins['gameAssemblySha256'], pins['globalMetadataSha256'],
                                         gameassembly=Path(gameassembly), metadata=Path(metadata))
    require(gate.status == 'validated', f'selected native gate {gate.status}: {gate.detail}')
    unity = Path(gameassembly).parent / 'UnityPlayer.dll'
    require(unity.is_file(), f'selected UnityPlayer missing: {unity}')
    require(sha(unity) == pins['unityPlayerSha256'].upper(), 'selected UnityPlayer hash mismatched')
    audit, audit_hash = read(native_audit)
    receipt, receipt_hash = read(validation_receipt)
    proof = audit.get('audit', {})
    require(type(proof) is dict and audit.get('status') == 'validated_selected_native_loader_and_consumer'
            and proof.get('contractSha256') == contract_hash and proof.get('nativeInputs') == pins, 'native audit not bound to current contract/build')
    require(receipt.get('schema') == 'endfield.ifix-vm-rules-validation-receipt.v2'
            and receipt.get('validation') == 'selected-combined-native-passed'
            and receipt.get('contractSchema') == contract.get('schema') and receipt.get('reportSchema') == audit.get('schema')
            and receipt.get('nativeInputs') == pins, 'passing validation receipt required')
    hashes = receipt.get('currentFileHashes', {})
    require(type(hashes) is dict and hashes.get(str(native_audit.resolve().relative_to(source_root.resolve())).replace('\\', '/')) == audit_hash,
            'native audit differs from passing receipt')
    checked = 0
    for name, expected in hashes.items():
        if name.startswith('scripts/game_data/ifix_vm') and name.endswith('.py'):
            path = safe_path(source_root.resolve(), name)
            actual = sha(path)
            require(actual == expected, f'native proof source changed: {name}; expectedSha256={expected}; actualSha256={actual}')
            checked += 1
    require(checked > 0, 'native proof source bindings missing')
    for name in spec['nativeGroups']:
        row = proof.get(name)
        require(type(contract.get(name)) is dict and type(row) is dict and str(row.get('status', '')).startswith('validated'), 'validated native group missing: ' + name)
    return contract, dict(status='validated_reused_selected_native_proof', contractSha256=contract_hash,
                          nativeAuditSha256=audit_hash, validationReceiptSha256=receipt_hash,
                          nativeInputs=pins, sourceBindingsChecked=checked,
                          boundary='unchanged prior native proof reused; no native bodies or runtime transitions reexecuted')


def targets(contract: dict, spec: dict) -> list[dict]:
    result = []
    for name in spec['methodRefs']:
        row = ref(contract, name)
        require(type(row) is dict and type(row.get('rva')) is str, 'method target declaration required: ' + name)
        result.append(dict(nativeRef=name, rva=int(row['rva'], 16)))
    group = contract['genericReferenceGetRules']
    result.append(dict(nativeRef='genericReferenceGetRules.candidateProgram', rva=int(group['candidateProgram']['rva'], 16)))
    for row in contract['genericScalarGetRules']['selections']:
        result.append(dict(nativeRef='genericScalarGetRules.' + row['argumentType'], rva=int(row['candidateProgram']['rva'], 16)))
    for row in contract['genericBridgeRules']['variants']:
        result.append(dict(nativeRef='genericBridgeRules.' + row['name'], rva=int(row['rva'], 16)))
    for row in contract['genericAdjustorRules']['cells']:
        result.append(dict(nativeRef='genericAdjustorRules.' + row['argumentType'], rva=int(row['entry']['rva'], 16)))
    require(all(0 < row['rva'] < 1 << 32 for row in result), 'target RVA outside module-relative domain')
    return result


def inspect_capabilities(inspection_path: Path, selected_targets: list[dict], pins: dict,
                         *, allowed_root: Path = REPO_ROOT) -> dict:
    """Rebind profile declarations; admit no IFix observations in this format."""
    result = dict(inspection=str(inspection_path), status='withheld', runtimeClaims=[], candidateHooks=[])
    try:
        saved, saved_hash = read(inspection_path)
        result['inspectionSha256'] = saved_hash
        require(saved.get('schema') in {'endfield.mission-trace-inspection.v1', 'endfield.mission-trace-inspection.v2'}
                and saved.get('status') == 'inspected', 'passing saved inspection required')
        require(saved.get('gaps') == [], 'saved inspection has admission gaps: ' + repr(saved.get('gaps'))[:500])
        facts = saved.get('receiptFacts', {})
        require(type(facts) is dict and facts.get('captureCompleteClaim') is True and facts.get('healthyClaim') is True
                and facts.get('allJournalRowsAccounted') is True and facts.get('failureReason') == 'none'
                and facts.get('collectionBoundFailureMarkers') == []
                and facts.get('nativeInputHashesBoundToProfile') is True, 'incomplete/unhealthy/unaccounted saved session')
        session = Path(saved['session']).resolve(strict=True)
        require(session.is_relative_to(allowed_root.resolve()), 'session outside explicit allowed root')
        inventory, inventory_hash = read(safe_path(session, 'collected/inventory.json'))
        require(type(saved.get('inventory')) is dict and inventory.get('schema') == 'endfieldCapture.collection.v1'
                and type(saved['inventory'].get('inventorySha256')) is str
                and saved['inventory']['inventorySha256'].upper() == inventory_hash
                and saved['inventory'].get('sessionId') == inventory.get('session'), 'saved inventory binding mismatch')
        rows = inventory.get('artifacts')
        require(type(rows) is list and 0 < len(rows) <= 20000 and type(inventory.get('files')) is int
                and inventory['files'] == len(rows), 'bounded artifact inventory required')
        names = [row.get('path') for row in rows if type(row) is dict]
        require(len(names) == len(rows) and all(type(name) is str for name in names)
                and len(set(names)) == len(names), 'invalid/duplicate artifact path')
        wanted = {}
        for name, key in [('private/mission-trace-build-manifest.json', 'profileSha256'), ('mission-trace/summary.json', 'providerSummarySha256')]:
            matches = [row for row in rows if row['path'] == name]
            require(len(matches) == 1, 'missing collection-bound artifact: ' + name)
            row = matches[0]; path = safe_path(session, name)
            obj, digest = read(path)
            require(type(row.get('bytes')) is int and row['bytes'] == path.stat().st_size
                    and type(row.get('sha256')) is str and row['sha256'].upper() == digest
                    and type(saved.get(key)) is str and saved[key].upper() == digest, 'saved artifact hash/size binding mismatch: ' + name)
            wanted[key] = obj
        profile = wanted['profileSha256']; summary = wanted['providerSummarySha256']
        require(profile.get('schema') == 'endfieldCapture.missionTraceBuild.v1'
                and summary.get('schema') in ('endfieldCapture.missionTraceSummary.v1', 'endfieldCapture.missionTraceSummary.v2'), 'unsupported retained profile/summary')
        require(summary.get('complete') is True and summary.get('healthy') is True, 'provider summary incomplete/unhealthy')
        require(summary.get('entryOnly') is True and summary.get('returnValuesObserved') is False, 'unsupported paired/return observation protocol')
        require(all(type(summary.get(key)) is int and summary[key] == 0 for key in
                    ('dropped', 'unrecorded', 'unreadableFields', 'truncatedFields', 'activeCallbacksAtStop', 'undrainedRecordsAtStop'))
                and all(summary.get(key) is True for key in ('stopped', 'quiescent', 'finalCountersStable', 'writeComplete'))
                and summary.get('failureReason') == 'none', 'provider loss/read/write/cleanup gate failed')
        counts = [summary.get(key) for key in ('attempted', 'admitted', 'written')]
        require(all(type(value) is int and value >= 0 for value in counts)
                and type(saved.get('decodedRows')) is int and saved['decodedRows'] >= 0
                and counts[0] == counts[1] == counts[2] == saved['decodedRows'], 'provider event accounting gate failed')
        files = profile.get('files')
        require(type(files) is dict and all(type(files.get(key)) is dict for key in ('gameAssembly', 'metadata')), 'profile native file carriers missing')
        for name, summary_key, pin in [('gameAssembly', 'gameAssemblySha256', 'gameAssemblySha256'), ('metadata', 'metadataSha256', 'globalMetadataSha256')]:
            digest = files[name].get('sha256')
            require(type(digest) is str and type(summary.get(summary_key)) is str and digest.upper() == pins[pin].upper()
                    and summary[summary_key].upper() == digest.upper(), 'saved/selected native input mismatch: ' + name)
        hooks = profile.get('missionTraceHooks'); coverage = saved.get('hookCoverage'); summary_hooks = summary.get('hooks')
        require(type(hooks) is list and 0 < len(hooks) <= MAX_HOOKS and type(coverage) is list
                and type(summary_hooks) is list and len(hooks) == len(coverage) == len(summary_hooks), 'hook/coverage/summary shape mismatch')
        candidates = []
        for index, (hook, observed, retained) in enumerate(zip(hooks, coverage, summary_hooks)):
            require(type(hook) is dict and type(observed) is dict and type(retained) is dict
                    and hook.get('abiId') == 'win64.transparent_entry_snapshot.v1'
                    and hook.get('module') == 'GameAssembly.dll', 'unsupported entry ABI/module')
            name = hook.get('name'); at = hook.get('rva')
            require(type(name) is str and type(at) in (int, str), 'hook identity missing')
            at = int(at, 16) if type(at) is str else at
            require(0 < at < 1 << 32 and type(observed.get('index')) is int and type(retained.get('index')) is int
                    and observed['index'] == retained['index'] == index
                    and observed.get('hook') == retained.get('name') == name and retained.get('rva') == at
                    and type(retained.get('rva')) is int and type(retained.get('calls')) is int
                    and type(observed.get('receiptCalls')) is int
                    and type(observed.get('observedRows')) is int and observed['observedRows'] >= 0
                    and observed['observedRows'] == observed.get('receiptCalls') == retained.get('calls'), 'hook/receipt coverage binding mismatch: ' + name)
            refs = [row['nativeRef'] for row in selected_targets if row['rva'] == at]
            named = 'IFix' in str(hook.get('type', '')) or name.lower().startswith('ifix')
            fields = hook.get('fields')
            require(type(fields) is list and len(fields) <= 64 and all(type(field) is dict for field in fields), 'bounded field declarations required: ' + name)
            if refs or named:
                candidates.append(dict(hook=name, nativeRefs=refs, recordedEntryRows=observed['observedRows'],
                                       declaredFields=[field.get('label') for field in fields],
                                       boundary='entry-profile candidate only; dedicated IFix point/paired observations and decoding absent'))
        require(sum(row['calls'] for row in summary_hooks) == counts[2], 'provider hook/event totals disagree')
        result.update(status='profile_capabilities_rebound', inspectionSha256=saved_hash, session=str(session),
                      inventorySha256=inventory_hash, sessionId=inventory['session'], profileSha256=saved['profileSha256'],
                      providerSummarySha256=saved['providerSummarySha256'], hookCount=len(hooks), candidateHooks=candidates,
                      upstreamAdmission='passing saved inspection reused; journal/native transitions not reexecuted',
                      runtimeBoundary='entry-only retained format has no supported IFix paired/point decoder; no alias/context/result claims admitted')
    except (RuntimeEvidenceError, OSError, ValueError, KeyError, TypeError) as exc:
        result['diagnostic'] = str(exc)[:1000]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--inspection', type=Path, action='append', required=True)
    parser.add_argument('--requirements', type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument('--native-contract', type=Path, default=DEFAULT_NATIVE_CONTRACT)
    parser.add_argument('--native-audit', type=Path, default=REPO_ROOT / 'reports/ifix/vm_understanding_current.json')
    parser.add_argument('--validation-receipt', type=Path, default=REPO_ROOT / 'reports/ifix/vm_rules_validation_current.json')
    parser.add_argument('--output', type=Path, default=REPO_ROOT / 'reports/ifix/runtime_evidence_current.json')
    args = parser.parse_args(argv)
    try:
        require(len(args.inspection) <= 128, 'saved inspection count budget exceeded')
        spec = requirements(args.requirements)
        contract, proof = selected_native_context(spec, gameassembly=args.gameassembly, metadata=args.metadata,
            native_contract=args.native_contract, native_audit=args.native_audit, validation_receipt=args.validation_receipt)
        sites = targets(contract, spec)
        sessions = [inspect_capabilities(path, sites, contract['nativeInputs']) for path in args.inspection]
        output = dict(schema='endfield.ifix-runtime-evidence-audit.v1', status='audited_saved_capabilities',
                      nativeProof=proof, requirements=spec, targetDeclarations=sites, sessions=sessions,
                      runtimeClaims=[], runtimeEvidenceStatus='unobserved',
                      boundary='offline saved-profile capability/gap audit; declarations and native candidates do not establish runtime observations')
    except (RuntimeEvidenceError, OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(f"IFix runtime: {len(sessions)} saved profiles audited; {sum(len(row['candidateHooks']) for row in sessions)} candidate hooks; no runtime claims admitted; {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
