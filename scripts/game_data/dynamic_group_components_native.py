"""Authenticate nested DataGroup components and their stored grid-local spans.

This domain reads authored references only. Native getter and builder witnesses
name the containing layouts; the independent RootComp validator owns DataGroup
and DataIndex. Resolved spans are structural relations, not activation receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_group_components_native')

from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_main_native import _checked_dump_path
from scripts.game_data.dynamic_root_comp_native import validate_native_layout as validate_root_layout
from scripts.game_data.dynamic_scalar_components_native import _validate_record, _validate_carriers, _decode_record, instruction_starts
from scripts.game_data.dynamic_stream_area_corpus import DEFAULT_OUTER, DEFAULT_LEDGER, DEFAULT_CLI, MAIN_NAME_RE, load_current_inputs
from scripts.game_data.dynamic_streaming import parse_dynamic_file, _root_layout, _table_layout, _bounded_vector, _field_span
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.protocol import canonical_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots, _guard_output_path
from scripts.game_data.corpus_common import atomic_write_text
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR / 'dynamic_group_components_native.json'
SCHEMA = 'endfield.dynamic-group-components-native-contract.v2'


class DynamicGroupComponentsError(ValueError):
    """A selected layout, source receipt or explicit group reference differs."""


def _proof_sources() -> list[dict[str, Any]]:
    sources = _parser_source_snapshots(Path(__file__))
    sources.extend(_fingerprint(path) for path in (
        CONTRACT, CONTRACTS_DIR / 'dynamic_root_comp_native.json',
        CONTRACTS_DIR / 'dynamic_data_index_native.json',
        CONTRACTS_DIR / 'dynamic_main_vector_native.json',
        CONTRACTS_DIR / 'dynamic_system_routing_native.json',
        CONTRACTS_DIR / 'dynamic_scalar_components_native.json',
        NATIVE_MAPPER_PATH, METADATA_HELPER_PATH))
    return sorted(sources, key=lambda row: row['path'])


def _guard_publication(output: Path, protected: list[Path]) -> None:
    target = output.resolve()
    repo = REPO_ROOT.resolve()
    allowed = [(repo / name).resolve() for name in ('reports', 'scratch', 'tmp')]
    if not any(root.is_relative_to(repo) and target != root and target.is_relative_to(root) for root in allowed):
        raise DynamicGroupComponentsError(f'output-root:expected ignored reports/scratch/tmp file actual={target}')
    _guard_output_path(target, protected)


def _require_unchanged(sources: list[dict[str, Any]]) -> None:
    for before in sources:
        after = _fingerprint(Path(before['path']))
        if before != after:
            raise DynamicGroupComponentsError(
                f"proof-source-drift:source={before['path']} expected={before['sha256']} actual={after['sha256']}")


def _inline_types(root: dict[str, Any], index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        index['recordType']: {'name': 'DataIndex', 'width': index['recordWidth'], 'fields': index['fields']},
        root['groupType']: {'name': 'DataGroup', 'width': root['groupWidth'], 'fields': [
            {'name': 'index', 'offset': root['groupIndexOffset'], 'type': index['recordType']},
            {'name': 'Num', 'offset': root['groupNumOffset'], 'type': 'System.Int32'},
            {'name': 'TotalInGrid', 'offset': root['groupTotalOffset'], 'type': 'System.Int32'},
        ]},
    }


def validate_native_layout(gameassembly: Path, metadata: Path):
    contract, _ = read_reviewed_contract(CONTRACT, schema=SCHEMA, label='dynamic_groups', status='validated')
    inputs = contract['nativeInputs']
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['metadataSha256'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicGroupComponentsError(f'installed_native_inputs:{gate.status}:{gate.detail}')
    root, index, main, enum, entity_enum, _, receipt = validate_root_layout(gameassembly, metadata)
    if receipt != inputs:
        raise DynamicGroupComponentsError('installed_native_inputs:mismatched:group and root builds differ')
    image = open_native_image(gameassembly, metadata)
    # Signatures use the scalar contract's canonical names, so shared inline rows
    # compare under one spelling (generic instances resolve to full names).
    selected_names = NativeReferenceContext(image)
    # The existing scalar contract owns these shared carrier witnesses.
    carrier_contract, _ = read_reviewed_contract(CONTRACTS_DIR / 'dynamic_scalar_components_native.json',
        schema='endfield.dynamic-scalar-components-native-contract.v3', label='dynamic_group_carriers', status='validated')
    if carrier_contract['nativeInputs'] != inputs:
        raise DynamicGroupComponentsError('installed_native_inputs:mismatched:carrier build differs')
    carriers = _validate_carriers(carrier_contract['layout'], image)
    inline_records = []
    for selected_type in contract['inlineTypes']:
        matches = [row for row in carrier_contract['layout']['records'] if row['type'] == selected_type]
        if len(matches) != 1 or selected_type not in carrier_contract['layout']['inlineTypes']:
            raise DynamicGroupComponentsError(f'absent or ambiguous scalar-owned inline type={selected_type}')
        inline_records.extend(matches)
    inline_method_indices = {row['builderMethodIndex'] for row in inline_records}
    inline_method_indices.update(field['getterMethodIndex'] for row in inline_records for field in row['fields'])
    method_rows = list(contract['methods']) + [row for row in carrier_contract['methods'] if row['index'] in inline_method_indices]
    methods, bodies, starts = {}, {}, {}
    for row in method_rows:
        idx = int(row['index'])
        if idx in methods:
            raise DynamicGroupComponentsError(f'duplicate method index={idx}')
        image.validate_method_row([idx, row['type'], row['method'], row['rva']], label='dynamic_groups')
        method = image.metadata.methods[idx]
        params = image.metadata.parameters_for(method)
        if ([canonical_type_name(selected_names.type_name(p.type_index)) for p in params] != row['parameters']
                or [image.metadata.string(p.name_index) for p in params] != row['parameterNames']
                or canonical_type_name(selected_names.type_name(method.return_type)) != row['returnType']):
            raise DynamicGroupComponentsError(f'{idx}:metadata signature differs')
        length = int(row['bodyExtent'])
        if not 0 < length <= 4096:
            raise DynamicGroupComponentsError(f'{idx}:invalid body extent={length}')
        body = image.pe.bytes_at_va(image.pe.image_base + row['rva'], length)
        if hashlib.sha256(body).hexdigest().upper() != row['bodySha256']:
            raise DynamicGroupComponentsError(f'{idx}:native body hash differs')
        methods[idx], bodies[idx] = row, body
    # Group-owned getter witnesses must begin decoded instructions: a pinned
    # build can place a witness byte pair inside a call displacement. The
    # scalar-owned inline records keep the scalar validator's own checks.
    for record in contract['records']:
        for idx in [record['builderMethodIndex'], *(f['getterMethodIndex'] for f in record['fields'])]:
            starts[idx] = instruction_starts(bodies[idx], image.pe.image_base + methods[idx]['rva'],
                                             image.mapper.decode_x64_subset, f'{idx}')
    inline = _inline_types(root, index)
    inline.update({record['type']: record for record in inline_records})
    vectors = {r['name']: r for r in main['vectors']}
    selected, names = set(), set()
    owned = {id(record) for record in contract['records']}
    for record in contract['records'] + inline_records:
        vector = vectors[record['name']]
        if record['name'] in names or (record['gridFieldIndex'], record['width']) != (vector['fieldIndex'], vector['elementWidth']):
            raise DynamicGroupComponentsError(f"{record['name']}:duplicate or mismatched main vector")
        names.add(record['name'])
        _validate_record(record, methods, bodies, inline_types=inline, carriers=carriers,
                         starts=starts if id(record) in owned else None)
        selected.add(record['builderMethodIndex'])
        selected.update(f['getterMethodIndex'] for f in record['fields'])
    if selected != set(methods):
        raise DynamicGroupComponentsError('unused or absent selected method')
    return contract['records'], inline, main, enum, receipt, {
        'root': root, 'index': index, 'entityEnum': entity_enum,
    }


def _resolve_group(group: dict[str, Any], *, unique_id: int, counts: dict[str, int], enum: dict[int, str], label: str) -> dict[str, Any]:
    idx = group['index']
    if idx['IsInvalid'] not in (0, 1):
        raise DynamicGroupComponentsError(f'{label}:IsInvalid expected=0/1 actual={idx["IsInvalid"]}')
    if idx['IsInvalid']:
        if group['Num'] != 0:
            raise DynamicGroupComponentsError(f'{label}:invalid group Num expected=0 actual={group["Num"]}')
        return {'status': 'invalid', 'span': None}
    target = enum.get(idx['Type'])
    if target not in counts:
        raise DynamicGroupComponentsError(f'{label}:unknown group Type={idx["Type"]}')
    first, num, total = idx['Index'], group['Num'], group['TotalInGrid']
    if first < 0 or num < 0 or total < 0 or first + num > total:
        raise DynamicGroupComponentsError(f'{label}:stored span exceeds TotalInGrid={total}:Index={first},Num={num}')
    if idx['Grid'] != unique_id:
        return {'status': 'other_grid_unresolved', 'target': target, 'gridUniqueId': idx['Grid'], 'span': None}
    count = counts[target]
    if first < 0 or num < 0 or first + num > count or total != count:
        raise DynamicGroupComponentsError(f'{label}:span expected=0..{count} actual=Index:{first},Num:{num},TotalInGrid:{total}')
    return {'status': 'empty' if num == 0 else 'resolved', 'target': target, 'gridUniqueId': unique_id,
            'span': [first, first + num], 'evidenceBoundary': 'structuralOnly'}


def decode_authenticated_main(data: bytes, *, records, inline, main, enum, source):
    """Use layouts from validate_native_layout and roster rows from load_current_inputs.

    Every output carries an exact file-relative containing span. Group spans
    use only their stored Type/Grid/Index/Num; names and proximity add no links.
    Full root/vector allocation checks precede any nested field decoding.
    """
    md5 = hashlib.md5(data).hexdigest().upper()
    if len(data) != int(source['declaredBytes']) or md5 != source['fileDataMd5'].upper():
        raise DynamicGroupComponentsError(f"{source['path']}:source join failed length={len(data)}/{source['declaredBytes']} md5={md5}/{source['fileDataMd5']}")
    widths = {r['fieldIndex']: r['elementWidth'] for r in main['vectors']}
    parse_dynamic_file('main', data, main_vector_widths=widths)
    root = _root_layout(data)
    gb, gc, _ = _bounded_vector(data, root, main['rootGridFieldIndex'], 4)
    rows = []
    for grid_ordinal in range(gc):
        slot = gb + grid_ordinal * 4
        grid = _table_layout(data, slot + struct.unpack_from('<I', data, slot)[0])
        uid = _field_span(data, grid, main['gridUniqueIdFieldIndex'], 4)
        if uid is None:
            raise DynamicGroupComponentsError(f"{source['path']}:grid[{grid_ordinal}] missing UniqueId")
        unique_id = struct.unpack_from('<I', data, uid)[0]
        vectors = {r['name']: _bounded_vector(data, grid, r['fieldIndex'], r['elementWidth']) for r in main['vectors']}
        counts = {name: vector[1] for name, vector in vectors.items()}
        for record in records:
            body, count, _ = vectors[record['name']]
            for ordinal in range(count):
                start = body + ordinal * record['width']
                label = f"{source['path']}:grid[{grid_ordinal}] {record['name']}[{ordinal}]"
                values, gap = _decode_record(data, start, record, label, inline_types=inline)
                groups = {}
                for field in record['fields']:
                    if field['type'] in inline and inline[field['type']]['name'] == 'DataGroup':
                        link = _resolve_group(values[field['name']], unique_id=unique_id, counts=counts, enum=enum, label=label+'.'+field['name'])
                        if link['span'] is not None:
                            target_body, _, _ = vectors[link['target']]
                            width = next(v['elementWidth'] for v in main['vectors'] if v['name'] == link['target'])
                            link['sourceByteSpan'] = [target_body + link['span'][0] * width, target_body + link['span'][1] * width]
                        groups[field['name']] = link
                rows.append({'gridOrdinal': grid_ordinal, 'gridUniqueId': unique_id, 'component': record['name'],
                             'componentOrdinal': ordinal, 'sourceByteSpan': [start, start + record['width']],
                             'values': values, 'groups': groups, 'nonzeroUnassignedBytes': gap})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('gameassembly', 'metadata', 'input-root'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--expected-input-set-sha256', required=True)
    parser.add_argument('--outer-report', type=Path, default=DEFAULT_OUTER)
    parser.add_argument('--ledger', type=Path, default=DEFAULT_LEDGER)
    parser.add_argument('--cli', type=Path, default=DEFAULT_CLI)
    parser.add_argument('--output-json', type=Path, default=REPO_ROOT/'reports/animestudio/dynamic_group_components_native_latest.json')
    args = parser.parse_args(argv)
    try:
        protected = [args.gameassembly, args.metadata, args.gameassembly.parent / 'UnityPlayer.dll',
                     args.input_root, args.outer_report, args.ledger, args.cli, CONTRACTS_DIR, Path(__file__)]
        _guard_publication(args.output_json, protected)
        proof_sources = _proof_sources()
        proof_inputs = [_fingerprint(path) for path in (args.gameassembly, args.metadata,
            args.gameassembly.parent / 'UnityPlayer.dll', args.outer_report, args.ledger, args.cli)]
        protected.extend(Path(row['path']) for row in proof_sources)
        _guard_publication(args.output_json, protected)
        records, inline, layout, enum, receipt, _ = validate_native_layout(args.gameassembly, args.metadata)
        for key, snapshot in zip(('gameAssemblySha256', 'metadataSha256', 'unityPlayerSha256'), proof_inputs[:3]):
            if receipt[key].upper() != snapshot['sha256'].upper():
                raise DynamicGroupComponentsError(f'native-input-drift:source={snapshot["path"]} expected={snapshot["sha256"]} actual={receipt[key]}')
        outer, files, provenance = load_current_inputs(args.outer_report, args.ledger, args.cli, args.expected_input_set_sha256,
            file_name_re=MAIN_NAME_RE, selection_label='fb_main_*.bytes')
        protected.extend(_checked_dump_path(args.input_root, row['path']) for row in files)
        _guard_publication(args.output_json, protected)
        totals, targets, statuses, samples, sources = Counter(), Counter(), Counter(), [], []
        for source in files:
            data = _checked_dump_path(args.input_root, source['path']).read_bytes()
            rows = decode_authenticated_main(data, records=records, inline=inline, main=layout, enum=enum, source=source)
            sources.append({'path': source['path'], 'length': len(data), 'fileDataMd5': source['fileDataMd5'], 'sha256': hashlib.sha256(data).hexdigest().upper(), 'records': len(rows)})
            for row in rows:
                totals[row['component']] += 1
                for field, link in row['groups'].items():
                    statuses[(row['component'], field, link['status'])] += 1
                    if link.get('target'):
                        targets[(row['component'], field, link['target'])] += 1
                if len(samples) < 32:
                    samples.append({'source': source['path'], **row})
        report = {'format': 'endfield.dynamic-group-components-native-audit.v1', 'status': 'validated',
            'nativeInputs': receipt, 'inputSetSha256': outer['inputSetSha256'], 'outer': provenance,
            'recordCounts': dict(totals), 'layouts': [r['name'] for r in records], 'files': sources,
            'groupStatuses': [{'component': c, 'field': f, 'status': s, 'count': n} for (c,f,s),n in sorted(statuses.items())],
            'storedTargets': [{'component': c, 'field': f, 'target': t, 'count': n} for (c,f,t),n in sorted(targets.items())],
            'samples': samples, 'evidenceBoundary': 'Exact selected containing layouts and authenticated file-relative byte spans. Explicit DataGroup type/grid/index/count joins are structuralOnly. Other-grid spans, runtime ownership, enum meaning and activation remain unresolved.'}
        report['proofSources'] = proof_sources
        report['proofInputs'] = proof_inputs
        encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
        _require_unchanged(proof_sources + proof_inputs)
        _guard_publication(args.output_json, protected)
        atomic_write_text(args.output_json, encoded)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as exc:
        print(f'dynamic-group-components-native-audit: {str(exc)[:1400]}', file=sys.stderr)
        return 1
    print(f'DynamicStreaming group audit passed: files={len(sources)} records={sum(totals.values())} layouts={len(records)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
