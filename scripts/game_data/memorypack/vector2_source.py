"""Prove buffered Vector2 lane packing and its independently registered reader."""
from __future__ import annotations
import json
from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.memorypack.vector_layout import vector_context,vector_recorder

LABEL='memorypackVector2Source'


def buffered_program(image,record,offsets,*,registered=False):
    cur,rem,adv,used=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    rows=record['instructions']
    if registered:
        expected=[b'\x40\x53',b'\x48\x83\xec\x40',b'\x83\x79'+bytes((rem,8)),b'\x48\x8b\xd9',b'\x0f\x29\x74\x24\x30',b'\x0f\x29\x7c\x24\x20',None,
            b'\x45\x33\xc0',b'\xba\x08\x00\x00\x00',None,b'\x48\x8b\x43'+bytes((cur,)),b'\xba\x08\x00\x00\x00',b'\x48\x8b\xcb',
            b'\xf3\x0f\x10\x30',b'\xf3\x0f\x10\x78\x04',None,b'\x0f\x14\xf7',b'\x0f\x28\x7c\x24\x20',b'\x66\x48\x0f\x7e\xf0',
            b'\x0f\x28\x74\x24\x30',b'\x48\x83\xc4\x40',b'\x5b',b'\xc3']
    else:
        expected=[b'\x48\x89\x5c\x24\x08',b'\x57',b'\x48\x83\xec\x40',b'\x83\x79'+bytes((rem,8)),b'\x48\x8b\xd9',b'\x0f\x29\x74\x24\x30',b'\x0f\x29\x7c\x24\x20',None,
            b'\x48\x8b\x43'+bytes((cur,)),b'\xf3\x0f\x10\x30',b'\xf3\x0f\x10\x78\x04',b'\x8b\x7b'+bytes((rem,)),b'\x83\xc7\xf8',None,
            b'\x48\x83\x43'+bytes((cur,8)),b'\x83\x43'+bytes((adv,8)),b'\x83\x43'+bytes((used,8)),b'\x89\x7b'+bytes((rem,)),b'\x48\x8b\x5c\x24\x50',
            b'\x0f\x28\xc6',b'\x0f\x28\x74\x24\x30',b'\x0f\x14\xc7',b'\x0f\x28\x7c\x24\x20',b'\x66\x48\x0f\x7e\xc0',b'\x48\x83\xc4\x40',b'\x5f',b'\xc3']
    scalar.program_extent(rows,record['window'],LABEL);image.check_windows([record['window']],label=LABEL);scalar.program(image,rows,expected,LABEL)
    if registered:
        rva,raw=rows[6];raw=bytes.fromhex(raw)
        scalar.need(LABEL,'bufferedBranch',(2,b'\x7d',rows[10][0]),(len(raw),raw[:1],rva+2+int.from_bytes(raw[1:],'little',signed=True)))
        raw=bytes.fromhex(rows[9][1]);scalar.need(LABEL,'refillCall',(5,b'\xe8'),(len(raw),raw[:1]))
        scalar.call(image,[*rows[15],record['advance']['pointerRva']],LABEL+'.advanceCall');scalar.advance_source(image,record['advance'],offsets,LABEL+'.advance')
    else:
        for n,opcode in ((7,b'\x0f\x8c'),(13,b'\x0f\x88')):
            rva,raw=rows[n];raw=bytes.fromhex(raw);scalar.need(LABEL,'coldGuard',(6,opcode),(len(raw),raw[:2]))
            target=rva+6+int.from_bytes(raw[2:],'little',signed=True)
            scalar.need(LABEL,'coldGuardOutsideBufferedProgram',False,record['window']['startRva']<=target<record['window']['endRva'])


def validate_vector2_source(image,context,target):
    entry=vector_context(image,context,2,label=LABEL);base=image.pe.image_base;record=vector_recorder(image,lanes=True)
    source=record(target);registered=record(entry['pointer']-base)
    rva,encoded=registered['instructions'][15];raw=bytes.fromhex(encoded)
    scalar.need(LABEL,'advanceCall',(5,b'\xe8'),(len(raw),raw[:1]))
    registered['advance']=record(rva+5+int.from_bytes(raw[1:],'little',signed=True),fragments=True)
    offsets=scalar.reader_offsets(image,LABEL)
    buffered_program(image,source,offsets);buffered_program(image,registered,offsets,registered=True)
    return {'status':'validated','sourceRva':target,'typedContext':context,'source':source,'registeredSource':registered,
        'registration':json.loads(json.dumps(entry)),'readerFieldOffsets':offsets,
        'evidenceBoundary':{'direct':'Typed Vector2 layout, complete two-Single loads, low-lane packing and full eight-byte return/cursor programs with both SIMD restores.',
            'conditional':'Sufficient signed buffers, valid disjoint reader/storage, matched initialized MethodInfo and ABI-preserving callees.',
            'unresolved':['cold refill paths','live formatter selection','parent transfers','whole-corpus admission']}}
