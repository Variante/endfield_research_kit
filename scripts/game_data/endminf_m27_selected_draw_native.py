"""Selected M27 candidate shader ABI, independent of historical Lab admission.

Native declarations and retained program bytes establish a bounded selection;
they do not identify the current particle renderer or close source publishers.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.shader.disassembler import Disassembler
from scripts.game_data.shader.dxbc import read_dxbc
from scripts.game_data.shader.instructions import read_disassembly
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR / 'endminf_m27_selected_draw_abi.json'
SCHEMA = 'endfield.endminf-m27-selected-draw-abi.v1'


def require(ok, detail):
    if not ok:
        raise ValueError('m27-selected-draw: ' + detail)


def read_inventory(executable):
    references = {}
    for row in executable['constantBufferReferences']:
        entry = references.setdefault(row['register'], dict(byteOffsets=set(), dynamicAddresses=set()))
        if row['byteOffsets'] is None:
            entry['dynamicAddresses'].add(row['address'])
        else:
            entry['byteOffsets'].update(row['byteOffsets'])
    return {key: {name: sorted(value) for name, value in row.items()}
            for key, row in sorted(references.items())}


def validate_program(raw, row, disassembler):
    frame = read_dxbc(raw)
    require((frame['stage'], frame['sha256'], frame['byteSize']) ==
            (row['stage'], row['sha256'], row['bytes']), 'program identity/stage/size differs: ' + row['stage'])
    executable = read_disassembly(disassembler.disassemble(raw), frame)
    for key, actual in (('declarations', executable['declarations']),
                        ('constantBufferReads', read_inventory(executable)),
                        ('outputs', executable['outputs'])):
        require(actual == row[key], key + ' differs: ' + row['stage'])
    result = {key: row[key] for key in ('stage', 'sha256', 'bytes', 'declarations', 'constantBufferReads', 'outputs')}
    result['constantBufferRequirements'] = {
        key: dict(declaredBytes=value['rows'] * 16,
                  staticReadPrefixBytes=max(row['constantBufferReads'].get(key, {}).get('byteOffsets', []), default=-4) + 4,
                  dynamicIndexRangeUnresolved=bool(row['constantBufferReads'].get(key, {}).get('dynamicAddresses')))
        for key, value in row['declarations'].items() if value['kind'] == 'cb'}
    return result


def validate_native(image, declaration):
    for row in declaration['methods'].values():
        image.validate_method_row([row['index'], row['owner'], row['name'], row['rva']], label='m27-selected-draw')
        method = image.metadata.methods[row['index']]
        require([image.metadata.string(p.name_index) for p in image.metadata.parameters_for(method)] == row['parameters'],
                'named parameters differ: ' + row['name'])
        expected = bytes.fromhex(row['prologue'])
        require(expected and image.pe.bytes_at_va(image.pe.image_base + row['rva'], len(expected)) == expected,
                'native entry differs: ' + row['name'])
    owners = {image.metadata.type_full_name(t): t for t in image.metadata.types}
    for row in declaration['fields'].values():
        owner = owners.get(row['owner'])
        require(owner is not None, 'missing field owner: ' + row['owner'])
        offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
        require(offsets.get(row['name']) == row['offset'], 'native field differs: ' + row['name'])
    return dict(status='validated', methods=len(declaration['methods']), fields=len(declaration['fields']))


def load(*, gameassembly=None, metadata=None, contract_path=CONTRACT, repo=REPO_ROOT):
    contract, _ = read_reviewed_contract(contract_path, schema=SCHEMA, label='m27-selected-draw', status='reviewed')
    repo = Path(repo).resolve()
    declaration = json.loads((repo / contract['captureDeclaration']).read_bytes())
    pins = contract['nativeInputs']
    ga = declaration['nativeInputs']['GameAssembly.dll']
    md = declaration['nativeInputs']['Endfield_Data/il2cpp_data/Metadata/global-metadata.dat']
    require(ga['sha256'].lower() == pins['gameAssemblySha256'].lower() and
            md['sha256'].lower() == pins['metadataSha256'].lower(), 'capture declaration selects a different build')
    gate = check_installed_native_inputs(pins['gameAssemblySha256'], pins['metadataSha256'],
        gameassembly=Path(gameassembly or ga['path']), metadata=Path(metadata or md['path']))
    require(gate.status == 'validated', 'installed native inputs: ' + gate.status + ': ' + gate.detail)
    native = validate_native(open_native_image(gate.gameassembly, gate.metadata), declaration)
    require([r['stage'] for r in contract['programs']] == ['vertex', 'fragment'], 'stage selection differs')
    disassembler = Disassembler()
    programs = [validate_program((repo / row['path']).read_bytes(), row, disassembler) for row in contract['programs']]
    for row, key in zip(programs, ('vertexShader', 'pixelShader')):
        draw = declaration['draw']
        require((row['sha256'], row['bytes']) == (draw[key + 'Sha256'], draw[key + 'Bytes']),
                'capture shader filter differs: ' + row['stage'])
    disassembler.check()
    final = check_installed_native_inputs(pins['gameAssemblySha256'], pins['metadataSha256'],
                                        gameassembly=gate.gameassembly, metadata=gate.metadata)
    require(final.status == 'validated', 'native inputs changed during review')
    return dict(schema=SCHEMA, nativeInputs=pins, nativeValidation=native, programs=programs,
                evidenceBoundary=contract['evidenceBoundary'])
