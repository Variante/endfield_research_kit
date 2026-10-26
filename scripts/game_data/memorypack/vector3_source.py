"""Prove the buffered Vector3 reader and its typed optimized forwarding clone.

The caller gates the selected image before and after validation. Cold refill
paths, runtime formatter selection and parent field transfers remain separate.
"""
from __future__ import annotations

import json

from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.memorypack.vector_layout import vector_context,vector_recorder
from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL = 'memorypackVector3Source'


def forwarding_program(image, record):
    rows = record['instructions']
    scalar.program_extent(rows,record['window'],LABEL+'.forward')
    scalar.program(image,rows,[b'\x40\x53',b'\x48\x83\xec\x20',None,b'\x48\x8b\xd9',None,
                              b'\x48\x8b\xc3',b'\x48\x83\xc4\x20',b'\x5b',b'\xc3'],LABEL+'.forward')
    scalar.need(LABEL,'methodContextRegister',b'\x4c\x8b\x05',bytes.fromhex(rows[2][1])[:3])
    context = derive_typed_usage_context(image,rows[2][0],label=LABEL)
    scalar.need(LABEL,'typedSource',['MemoryPack.MemoryPackReader','ReadUnmanaged',[],['UnityEngine.Vector3']],
                [context[k] for k in ('typeName','methodName','classArguments','methodArguments')])
    raw = bytes.fromhex(rows[4][1]); scalar.need(LABEL,'sourceCallShape',(5,0xe8),(len(raw),raw[0]))
    return context, rows[4][0]+5+int.from_bytes(raw[1:],'little',signed=True)


def buffered_program(image, record, offsets, *, registered=False):
    """Check the whole selected primary program, including both frame restores."""
    cur, rem, adv, used = (offsets[k] for k in ('currentPtr', 'bufferLength', 'advancedCount', 'consumed'))
    rows = record['instructions']
    copy = [b'\xf2\x0f\x10\x00', b'\x8b\x40\x08', b'\xf2\x0f\x11\x07', b'\x89\x47\x08']
    if registered:
        expected = [b'\x48\x89\x5c\x24\x08', b'\x57', b'\x48\x83\xec\x20', b'\x83\x7a'+bytes((rem,12)),
            b'\x48\x8b\xda', b'\x48\x8b\xf9', None, b'\x45\x33\xc0', b'\xba\x0c\x00\x00\x00', b'\x48\x8b\xcb', None,
            b'\x48\x8b\x43'+bytes((cur,)), b'\xba\x0c\x00\x00\x00', b'\x48\x8b\xcb', *copy, None,
            b'\x48\x8b\x5c\x24\x30', b'\x48\x8b\xc7', b'\x48\x83\xc4\x20', b'\x5f', b'\xc3']
    else:
        expected = [b'\x48\x89\x5c\x24\x08', b'\x48\x89\x74\x24\x10', b'\x57', b'\x48\x83\xec\x20',
            b'\x83\x7a'+bytes((rem,12)), b'\x48\x8b\xda', b'\x48\x8b\xf9', None, b'\x48\x8b\x43'+bytes((cur,)), *copy,
            b'\x8b\x73'+bytes((rem,)), b'\x83\xc6\xf4', None, b'\x48\x83\x43'+bytes((cur,12)),
            b'\x83\x43'+bytes((adv,12)), b'\x83\x43'+bytes((used,12)), b'\x89\x73'+bytes((rem,)),
            b'\x48\x8b\x5c\x24\x30', b'\x48\x8b\xc7', b'\x48\x8b\x74\x24\x38', b'\x48\x83\xc4\x20', b'\x5f', b'\xc3']
    image.check_windows([record['window']], label=LABEL)
    scalar.program_extent(rows, record['window'], LABEL)
    scalar.program(image, rows, expected, LABEL)
    if registered:
        rva, encoded = rows[6]; raw = bytes.fromhex(encoded)
        scalar.need(LABEL, 'bufferGuardOpcode', b'\x7d', raw[:1]); scalar.need(LABEL, 'bufferGuardSize', 2, len(raw))
        scalar.need(LABEL, 'bufferGuardTarget', rows[11][0], rva+2+int.from_bytes(raw[1:], 'little', signed=True))
        fallback = bytes.fromhex(rows[10][1])
        scalar.need(LABEL, 'refillCallShape', (5, 0xe8), (len(fallback), fallback[0]))
        scalar.call(image, [*rows[18], record['advance']['pointerRva']], LABEL+'.advanceCall')
        scalar.advance_source(image, record['advance'], offsets, LABEL+'.advance')
    else:
        for at, opcode in ((7, b'\x0f\x8c'), (15, b'\x0f\x88')):
            rva, encoded = rows[at]; raw = bytes.fromhex(encoded)
            scalar.need(LABEL, 'coldGuardShape', (6, opcode), (len(raw), raw[:2]))
            target = rva+6+int.from_bytes(raw[2:], 'little', signed=True)
            scalar.need(LABEL, 'coldGuardOutsideBufferedProgram', False,
                        record['window']['startRva'] <= target < record['window']['endRva'])


def validate_vector3_source(image, context, target):
    """Prove a direct typed buffered source; caller owns its argument transfers."""
    base=image.pe.image_base;record=vector_recorder(image)
    entry=vector_context(image,context,3,label=LABEL)
    source = record(target); registered = record(entry['pointer']-base)
    advance_call = registered['instructions'][18]; encoded = bytes.fromhex(advance_call[1])
    scalar.need(LABEL,'advanceCallShape',(5,0xe8),(len(encoded),encoded[0]))
    registered['advance'] = record(advance_call[0]+5+int.from_bytes(encoded[1:],'little',signed=True),fragments=True)
    offsets = scalar.reader_offsets(image,LABEL)
    buffered_program(image,source,offsets); buffered_program(image,registered,offsets,registered=True)
    return {'status':'validated','sourceRva':target,'typedContext':context,'source':source,
            'registeredSource':registered,'registration':json.loads(json.dumps(entry)),'readerFieldOffsets':offsets,
            'evidenceBoundary':{'direct':'Typed Vector3 layout and complete actual/registered 8+4 byte buffered copies with twelve-byte cursor advance, restored frames and output-pointer return.',
                'conditional':'Sufficient signed buffer lengths, valid disjoint input/output/reader storage, ABI-preserving calls and matched initialized MethodInfo.',
                'unresolved':['cold refill paths','live formatter selection','parent field transfers','whole-corpus admission']}}


def validate_vector3_reader(image, forward_rva, *, source_rva=None):
    """Prove the forwarding reader and its independently typed buffered source."""
    forward=vector_recorder(image)(forward_rva)
    context,target=forwarding_program(image,forward)
    if source_rva is not None:scalar.need(LABEL,'sourceTarget',source_rva,target)
    result=validate_vector3_source(image,context,target)
    return {**result,'forward':forward,'evidenceBoundary':{**result['evidenceBoundary'],
        'direct':'Typed Vector3, complete forwarding frame and 8+4 byte buffered copies with twelve-byte cursor advance and output-pointer return.'}}
