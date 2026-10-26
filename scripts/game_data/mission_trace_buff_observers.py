"""Selected closed BlackboardDouble cells for bounded passive observers.

Observe cells from current typed generated setters. Installed-format source
transfer remains a separate proof; no open generic instance offset is used.
"""
from __future__ import annotations
import re
import struct

from .il2cpp.body_claims import _writes_register


def double_field(selected, qualified: str, witness: str, current_type: str):
    owner, separator, name = qualified.partition('::')
    concrete = 'Beyond.Blackboard+BlackboardDouble'
    if not separator or owner != concrete or witness != concrete or current_type != concrete:
        raise ValueError('Buff scalar witness: concrete BlackboardDouble receiver required')
    if not hasattr(selected, '_buff_double_cells'):
        from .mission_trace_closed_cells import layout
        proof=layout(selected,'Beyond.MemoryPack.Beyond_Blackboard_BlackboardParamBase_float_double_ForMemoryPack')
        selected._buff_double_cells={name:{'destinationOffset':cell['offset']} for name,cell in proof['fields'].items()}
        selected._buff_double_proof={'closedArguments':['float','double'],
            'evidence':proof['boundary'],'sourceTransferProved':False,'runtimeTypeObserved':False,'setters':proof['fields']}
    types = {'blackboardKey': 'string', 'useBlackboardKey': 'bool', 'value': 'float'}
    if name not in types or set(selected._buff_double_cells) != set(types):
        raise ValueError('Buff scalar witness: unsupported or incomplete fields')
    cell = selected._buff_double_cells[name]
    return owner, types[name], cell['destinationOffset'], {
        **selected._buff_double_proof, 'concreteWitness': concrete,
        'field': name, 'fieldType': types[name], 'fieldOffset': cell['destinationOffset']}


def client_hp_field(selected, qualified, witness, current_type):
    """Match the ordinary HP getter's cell to its closed sequential value field.

    This is a passive storage read, not a call to that getter or evidence that
    the live virtual/IFix getter selected its ordinary body.
    """
    ability = 'Beyond.Gameplay.Core.AbilitySystem'
    generic = ability + '+SyncedValue`1'
    closed = generic + '<double>'
    owner, separator, name = qualified.partition('::')
    if (witness != ability or current_type != closed or owner != closed
            or not separator or name != '<clientValue>k__BackingField'):
        raise ValueError('HP cell witness: selected closed client-value field required')
    td = selected.index.types.get(generic)
    if td is None or td.generic_container_index < 0 or td.flags & 0x18 != 8:
        raise ValueError('HP cell witness: sequential generic value declaration required')
    if selected.parent(closed) != 'System.ValueType':
        raise ValueError('HP cell witness: value-type ancestry differs')
    metadata = selected.image.metadata
    section = metadata.sections['genericContainers'];at=section.offset+td.generic_container_index*16
    if not section.offset <= at <= section.offset+section.size-16:
        raise ValueError('HP cell witness: generic container outside metadata')
    definition, count, is_method, parameter = struct.unpack_from('<iiii', metadata.buf, at)
    declarations = list(metadata.fields_for(td))
    if (definition != td.index or count != 1 or is_method != 0 or parameter < 0
            or [metadata.string(f.name_index) for f in declarations] !=
                ['<clientValue>k__BackingField', '<serverValue>k__BackingField']
            or any(selected.type_name(f.type_index) != f'VAR[{parameter}]'
                   or selected.field_attributes(f.type_index) & 0x10 for f in declarations)):
        raise ValueError('HP cell witness: two instance fields of owned T required')
    _, storage_type, storage_offset = selected.field(ability+'::m_hp')
    if storage_type != closed:
        raise ValueError('HP cell witness: concrete storage instantiation differs')
    body = selected.index.body(ability, 'get_hp')
    rows=body.rows
    frame=re.fullmatch(r'sub rsp, (0x[0-9a-f]+)',rows[0]['text']) if rows else None
    if not frame or not 0<int(frame[1],16)<=4096:
        raise ValueError('HP cell witness: bounded stack frame required')
    reads=[]
    for i,row in enumerate(rows[:-2]):
        match=re.fullmatch(r'movsd xmm0, \[rcx\+0x([0-9a-f]+)\]',row['text'])
        if not match:continue
        prefix=rows[1:i]
        if any(r['text'].startswith('call ') or _writes_register(r, 'rcx') for r in prefix):
            raise ValueError('HP cell witness: incoming receiver changed before cell read')
        if [r['text'] for r in rows[i+1:i+3]]==[f'add rsp, {frame[1]}','ret']:
            reads.append((row,int(match[1],16)))
    if len(reads) != 1 or reads[0][1] != storage_offset:
        raise ValueError('HP cell witness: sole getter return cell is not the first stored Double')
    return owner,'double',16, {'concreteWitness':ability,'closedType':closed,
        'field':name,'fieldType':'double','fieldOffset':16,
        'getterCell':reads[0][0],'evidence':'selected sequential Double pair and ordinary getter return cell; open generic offsets unused',
        'liveGetterBranchObserved':False}
