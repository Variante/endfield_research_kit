"""Join the authenticated Streaming marker17 consumer to the ECS decoder.

Resource spans are native reads, not complete target extents or Unity PPtrs.
Only reviewed default callback paths are interpreted; no live selection follows.

Evidence and admission boundary
-------------------------------
The exact entry, extent and code-byte join between independently authenticated
marker-17 and ECS decoder roles gives stored bodies their collision-definition
interpretation. Selected default callbacks are conditional; registration, runtime
root pairing, load and scene activation are unresolved. Mesh count/ordered keys
and the separate fixed terrain key consume resource spans whose first qword is
the full lookup key; following words stay explicit. Read width is not allocation
extent. Terrain supplies the decoder's heightmap argument, not an ordered Mesh.
A newer Collision observer's independent constructor/selector/resource proofs do
not validate an older field-2/marker contract or stored Streaming projection.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.ecs_collision_native import load as load_ecs
from scripts.game_data.streaming.marker17_native import DEFAULT_CONTRACT as MARKER_CONTRACT
from scripts.game_data.streaming.marker17_native import validate_marker17_native_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract

CONTRACT = CONTRACTS_DIR / 'streaming_collision_native.json'
SCHEMA = 'endfield.streaming-collision-native.v2'


def validate_join(pe, contract, ecs, marker):
    """Pure selected-image proof; dependency validators authenticate their bodies."""
    def need(ok, detail):
        if not ok:
            raise ValueError('streaming-collision-native:' + detail)

    need(contract['schema'] == SCHEMA and contract['status'] == 'reviewed', 'schema/status')
    for dep in (ecs, marker):
        need({k:v.lower() for k,v in dep['nativeInputs'].items()} == contract['nativeInputs'], 'dependency native inputs')
    ew = {r['role']:r for r in ecs['codeWindows']}
    mw = {r['role']:r for r in marker['unityPlayerRanges']}
    bridge = contract['decoderBridge']
    decoder, consumer = ew[bridge['ecsRole']], mw[bridge['markerRole']]
    need((decoder['rva'],decoder['bytes'],decoder['sha256'].lower()) ==
         (consumer['rva'],consumer['size'],consumer['bodySha256'].lower()), 'decoder body bridge')
    windows = {}
    for spec in contract['codeWindows']:
        need(spec['role'] not in windows and 0 < spec['bytes'] <= 16384, 'window identity/bound')
        raw = pe.bytes_at_va(pe.image_base+spec['rva'],spec['bytes'])
        need(hashlib.sha256(raw).hexdigest() == spec['sha256'], 'window hash:' + spec['role'])
        windows[spec['role']] = (spec,raw)
    for probe in contract['probes']:
        _,raw = windows[probe['role']]; at=probe['offset']; expected=bytes.fromhex(probe['hex'])
        need(0 <= at <= len(raw)-len(expected) and raw[at:at+len(expected)] == expected, 'probe:' + probe['role'])

    def direct_call(at, target):
        raw = pe.bytes_at_va(pe.image_base+at,5)
        need(raw[0] == 0xe8 and at+5+struct.unpack_from('<i',raw,1)[0] == target, 'direct resource call')

    selected = {r['selector']:r['key'] for r in marker['selectedDefaultSlot3']}
    need(sorted(r['selector'] for r in contract['meshSources']) == [5,6,9], 'mesh profile selectors')
    for spec in contract['meshSources']:
        producer = ew[spec['producerRole']]
        need(spec['bodyKey'] == selected[spec['selector']], 'body selection key')
        literal = spec['countLiteral']; raw=pe.bytes_at_va(pe.image_base+literal['rva'],12)
        need(raw == bytes.fromhex(literal['hex']) and list(struct.unpack('<3I',raw)) == spec['countKey'], 'count key literal')
        for at,size,disp_at,target,prefix in (
            (literal['loadRva'],8,4,literal['rva'],b'\xf2\x0f\x10\x05'),
            (literal['tailLoadRva'],6,2,literal['rva']+8,b'\x8b\x05')):
            instruction=pe.bytes_at_va(pe.image_base+at,size)
            need(instruction.startswith(prefix) and at+size+struct.unpack_from('<i',instruction,disp_at)[0] == target, 'count key RIP load')
        for probe in spec['sourceProbes']:
            raw=bytes.fromhex(probe['hex']); at=probe['rva']
            need(producer['rva'] <= at <= producer['rva']+producer['bytes']-len(raw), 'producer probe bound')
            need(pe.bytes_at_va(pe.image_base+at,len(raw)) == raw, 'producer probe')
        for probe in spec['immediateKeyProbes']:
            raw=pe.bytes_at_va(pe.image_base+probe['rva'],probe['bytes'])
            need(raw.startswith(b'\xc7\x45') and struct.unpack_from('<I',raw,probe['operandOffset'])[0] == spec['meshKeyBase'][probe['keyWord']], 'mesh key immediate')
        direct_call(spec['resourceCallRva'],windows['resource_copy'][0]['rva'])
    need([s['selector'] for s in contract['fixedResourceSources']] == [7], 'fixed resource selectors')
    for spec in contract['fixedResourceSources']:
        need(spec['bodyKey'] == selected[spec['selector']], 'fixed resource body key')
        literal=spec['literal'];raw=pe.bytes_at_va(pe.image_base+literal['rva'],12)
        need(raw == bytes.fromhex(literal['hex']) and list(struct.unpack('<3I',raw)) == spec['resourceKey'], 'fixed resource key literal')
        for at,size,disp_at,target,prefix in (
            (literal['loadRva'],8,4,literal['rva'],b'\xf2\x0f\x10\x05'),
            (literal['tailLoadRva'],6,2,literal['rva']+8,b'\x8b\x05')):
            instruction=pe.bytes_at_va(pe.image_base+at,size)
            need(instruction.startswith(prefix) and at+size+struct.unpack_from('<i',instruction,disp_at)[0] == target,'fixed resource RIP load')
        producer=ew[spec['producerRole']];probe=spec['decoderArgumentProbe'];raw=bytes.fromhex(probe['hex']);at=probe['rva']
        need(producer['rva'] <= at <= producer['rva']+producer['bytes']-len(raw) and pe.bytes_at_va(pe.image_base+at,len(raw)) == raw,'fixed resource decoder arguments')
        direct_call(spec['resourceCallRva'],windows[spec['resourceTargetRole']][0]['rva'])
    need(contract['resourceRead']['bytes'] == 16 and contract['resourceRead']['key64Offset'] == 0
         and contract['resourceRead']['word8Offset'] == 8 and contract['resourceRead']['word12Offset'] == 12,
         'resource span layout')
    return contract


def load(*, game_root: Path, contract_path: Path = CONTRACT):
    root=game_root.resolve()
    if root.name == 'Endfield_Data':root=root.parent
    audit=dict(validator='streaming_collision_native',status='failed',diagnostics=[])
    try:
        contract,digest=read_reviewed_contract(contract_path,schema=SCHEMA,label='streaming-collision',status='reviewed')
        ecs,ecs_gate=load_ecs(gameassembly=root/'GameAssembly.dll',metadata=root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',unityplayer=root/'UnityPlayer.dll')
        audit['ecsGate']=ecs_gate
        if ecs is None:
            audit.update(status=ecs_gate['status'],detail=ecs_gate.get('detail',''));return None,None,audit
        marker_gate=validate_marker17_native_contract(game_root=root/'Endfield_Data')
        audit['markerGate']=marker_gate
        if marker_gate['status'] != 'validated':
            audit['diagnostics']=marker_gate['validationFailures'];return None,None,audit
        marker=json.loads(MARKER_CONTRACT.read_bytes())
        pe=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(root/'UnityPlayer.dll')
        validate_join(pe,contract,ecs,marker)
        # The image opened for the new windows must itself match the selected input.
        if hashlib.sha256(pe.buf).hexdigest() != contract['nativeInputs']['unityPlayerSha256']:
            raise ValueError('UnityPlayer changed before source proof')
        audit.update(status='validated',contractSha256=digest,nativeInputs=contract['nativeInputs'],
                     evidenceBoundary=contract['evidenceBoundary'])
        return contract,ecs,audit
    except (OSError,ValueError,KeyError,TypeError,struct.error) as exc:
        audit['diagnostics']=[dict(check='streaming_collision_source',source=str(contract_path),detail=str(exc)[:1200])]
        return None,None,audit
