"""Exact-build, read-only generic-instantiation audit; JSON is emitted to stdout.

No runtime MethodInfo or serialized source cursor is inferred. Native tables
are referenced PE extents, not a claim to consume the entire PE to EOF.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp_context import ContextError, GenericInstantiationTable, method_parameter_owner

ROOT = Path(__file__).resolve().parents[2]
GA_SHA = 'C24495E51B406F03B03890C4788EE618AE022C991405BE5D5B8B787CB775AE89'
MD_SHA = '0076743397ACADF03D3B0064343A963C7C88863B8160526D397E4B3EFB96F02E'
CORPUS_SHA = 'D05C31D59864C08AC9F5BFDF991CA0B720B799C33B75C4CD708F917083E99873'
CONSUMER_WINDOWS = (
    (0x2D8BF0, 0x2D8C12, '58AEECD1D6787DA519A37F3857FB40F3950BED75D3A9A0A6AEC81DEE32569AA4'),
    (0x2D8C12, 0x2D8C79, 'F1D27E8325CBBCF568E89D23C9280969ADAB6DEE2CEDE13E0FD1F1CBCB762470'),
    (0x2D8C79, 0x2D8C83, '087CD1A1ECF2C15B53BC8CA47F008DFACD7DB6E1579D1AD1C3A77D500224D68C'),
)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def require(actual, expected, source, offset=0):
    if actual != expected:
        raise ContextError(str(source), offset, expected, actual)


def native_gate():
    gate = check_installed_native_inputs(GA_SHA, MD_SHA)
    require(gate.status, 'validated', 'selected native inputs: ' + gate.detail)
    return gate


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sweep(table):
    rows, failures = [], []
    for index in range(table.count):
        try:
            rows.append(table.resolve(index).as_dict())
        except ContextError as error:
            failures.append({'index': index, **error.diagnostics})
    return {'success': len(rows), 'failed': len(failures), 'unsupported': 0}, rows, failures


def audit():
    gate = native_gate()
    corpus_path = ROOT / 'reports/animestudio/skilldata_current_latest.json'
    require(sha(corpus_path), CORPUS_SHA, corpus_path)
    corpus = json.loads(corpus_path.read_text(encoding='utf-8'))
    mapper_path = ROOT / 'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py'
    catalog_path = ROOT / 'tools/endfield-il2cpp/catalog_option_flow_metadata.py'
    sources = [Path(__file__), Path(__file__).with_name('il2cpp_context.py'),
               mapper_path, catalog_path, ROOT / 'scripts/common.py']
    source_hashes = {str(p): sha(p) for p in sources}
    mapper = load('context_audit_mapper', mapper_path)
    catalog = load('context_audit_catalog', catalog_path)
    pe = mapper.PeImage(gate.gameassembly)
    md = catalog.Metadata(gate.metadata)
    require(hashlib.sha256(pe.buf).hexdigest().upper(), GA_SHA, gate.gameassembly)
    require(hashlib.sha256(md.buf).hexdigest().upper(), MD_SHA, gate.metadata)
    candidates = mapper.find_code_registration_candidates(pe, {md.string(x.name_index) for x in md.images})
    require(candidates, [0x18A88E640], gate.gameassembly)
    registration = mapper.find_metadata_registration(pe, candidates[0])
    require(registration, 0x18A88E860, gate.gameassembly)
    for begin, end, expected in CONSUMER_WINDOWS:
        require(hashlib.sha256(pe.bytes_at_va(pe.image_base + begin, end-begin)).hexdigest().upper(),
                expected, gate.gameassembly, begin)
    reg = mapper.metadata_registration_summary(pe, registration)
    table = GenericInstantiationTable(pe.bytes_at_va, int(reg['genericInsts'], 16),
                                     reg['genericInstsCount'], source=str(gate.gameassembly))
    summary, rows, failures = sweep(table)
    # Explicit raw MethodSpec -> pointer-table join, not an observed invocation.
    spec_index = 516756
    if not 0 <= spec_index < reg['methodSpecsCount']:
        raise ContextError(str(gate.gameassembly), registration, 'bounded MethodSpec index', spec_index)
    spec_va = int(reg['methodSpecs'], 16) + spec_index * 12
    raw = pe.bytes_at_va(spec_va, 12)
    definition, class_inst, method_inst = struct.unpack('<iii', raw)
    require((definition, class_inst, method_inst), (428394, -1, 41928), gate.gameassembly, spec_va)
    selected = table.resolve(method_inst)
    require(len(selected.arguments), 1, gate.gameassembly, selected.record_va)
    type_raw = bytes.fromhex(selected.arguments[0].raw_type_record_hex)
    require(type_raw[10], 0x1E, gate.gameassembly, selected.arguments[0].type_pointer_va)
    owner = method_parameter_owner(md.buf, struct.unpack_from('<Q', type_raw)[0],
                                   [m.generic_container_index for m in md.methods], source=str(gate.metadata))
    require(owner['methodIndex'], 428464, gate.metadata, owner['containerOffset'])
    native_gate()
    require(sha(corpus_path), CORPUS_SHA, corpus_path)
    for path, expected in source_hashes.items():
        require(sha(path), expected, path)
    return {
        'schemaVersion': 1, 'status': 'failed' if failures else 'structural-only',
        'inputSetSha256': corpus['inputSetSha256'],
        'corpusReference': {'path': str(corpus_path), 'sha256': CORPUS_SHA,
                            'boundary': 'Authenticated corpus reference; this native audit does not restream VFS bytes.'},
        'nativeInputs': {'gameassembly': str(gate.gameassembly), 'gameassemblySha256': GA_SHA,
                         'metadata': str(gate.metadata), 'metadataSha256': MD_SHA},
        'sourceHashes': source_hashes, 'registration': reg,
        'consumerWindows': CONSUMER_WINDOWS, 'summary': summary,
        'selectedMethodSpec': {'index': spec_index, 'va': spec_va, 'rawHex': raw.hex().upper(),
                               'definition': definition, 'methodInstantiation': selected.as_dict(),
                               'openMethodParameterOwner': owner},
        'boundary': 'Pointer array -> 16-byte record -> argument pointer array -> raw 16-byte type records only. No live generic context, formatter, field order, source cursor or EOF claim.',
        'failures': failures, 'rows': rows,
    }


def main():
    try:
        report = audit()
    except (ContextError, OSError, ValueError) as error:
        print(json.dumps({'status': 'failed', 'diagnostic': getattr(error, 'diagnostics', str(error))}), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
