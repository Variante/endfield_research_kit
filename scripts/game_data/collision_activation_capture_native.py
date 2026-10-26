"""Validate original destruction stages and passive typed field layouts."""
import hashlib
import json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from scripts.game_data.collision_capture_prepare import _selected

CONTRACT = CONTRACTS_DIR / 'collision_activation_capture_native.json'
SCHEMA = 'endfield.collision-activation-capture-native.v3'
LEGACY_SCHEMA = 'endfield.collision-activation-capture-native.v2'


def load(image, native_inputs, contract=None):
    c = contract or read_reviewed_contract(CONTRACT, schema=SCHEMA, label='collision-activation', status='reviewed')[0]
    if c['schema'] not in (SCHEMA,LEGACY_SCHEMA) or c['status'] != 'reviewed' or c['nativeInputs'] != {k:v.lower() for k,v in native_inputs.items()}:
        raise ValueError('activation selected native inputs/schema differ')
    pe = image.pe; md = image.metadata; selected = _selected(image)
    table, size, raw = read_exception_directory(pe)
    index = UnwindChainIndex(raw, lambda a,n:pe.bytes_at_va(pe.image_base+a,n), table_rva=table, image_size=size)
    windows = {}; pins = []
    for w in c['codeWindows']:
        if w['module'] != 'gameAssembly' or w['role'] in windows or not 1 <= w['bytes'] <= 4096:
            raise ValueError('activation window identity/bounds')
        data = pe.bytes_at_va(pe.image_base+w['rva'], w['bytes'])
        if hashlib.sha256(data).hexdigest() != w['sha256']:
            raise ValueError('activation native window:'+w['role'])
        windows[w['role']] = (w,data)
        pins.append(dict(module=w['module'], rva=w['rva'], expectedBytes=data.hex()))
    covered = set()
    for family in c['codeFamilies']:
        ranges = [p['runtimeTriple'] for p in index.family(family['rva'])['ranges']]
        if ranges != family['runtimeRanges']:
            raise ValueError('activation original unwind family:'+family['role'])
        slices = sorted((w['rva'],w['rva']+w['bytes'],role) for role,(w,_) in windows.items()
            if role == family['role'] or role.startswith(family['role']+'_part_'))
        for a,b,_ in ranges:
            cursor = a
            for start,end,role in slices:
                if a <= start < b:
                    if start != cursor or end > b:
                        raise ValueError('activation incomplete/overlapping family:'+role)
                    cursor = end; covered.add(role)
            if cursor != b:
                raise ValueError('activation missing original family bytes:'+family['role'])
    if covered != set(windows):
        raise ValueError('activation undeclared family windows')
    expected = ((94,'load_data',2,'void'),(95,'interactive_break',2,'void'),
                (96,'prepare_attack',3,'void'),(97,'attack_callback',3,'void'),(98,'manager_submit',3,'bool'))
    if tuple((h['kind'],h['role'],len(h['abi']['arguments']),h['abi']['returnMode']) for h in c['hooks']) != expected:
        raise ValueError('activation compiled hook identity/order')
    selected_entries={pe.image_base+h['rva']:h['method'][0] for h in c['hooks']}
    aliases={address:[] for address in selected_entries}
    for method in md.methods:
        address=image.method_pointer_va(method)
        if address in aliases:aliases[address].append(method.index)
    if any(aliases[address]!=[index] for address,index in selected_entries.items()):
        raise ValueError('activation folded/ambiguous native method entry')
    hooks = []
    for h in c['hooks']:
        image.validate_method_row(h['method'], label='activation:'+h['role'])
        m = md.methods[h['method'][0]]; parameters = list(md.parameters_for(m))
        actual = [dict(name=md.string(p.name_index), type=selected.type_name(p.type_index)) for p in parameters]
        if actual != h['parameters'] or bool(m.flags&16) != h['static'] or selected.type_name(m.return_type) != h['returnType']:
            raise ValueError('activation selected method signature:'+h['role'])
        if h['static'] or h['abi']['arguments'] != ['pointer']*(len(parameters)+2):
            raise ValueError('activation compiled receiver/MethodInfo ABI:'+h['role'])
        for p in parameters:
            type_name = selected.type_name(p.type_index)
            if selected.is_value_type(type_name) and (type_name != 'UnityEngine.Vector3' or selected.value_size(type_name) != 12):
                raise ValueError('activation unsupported value parameter:'+h['role'])
        entry = bytes.fromhex(h['entryHex']); w,data = windows[h['role']]
        if h['module'] != 'gameAssembly' or h['rva'] != w['rva'] or not 5 <= len(entry) <= 32 or not data.startswith(entry):
            raise ValueError('activation hook entry:'+h['role'])
        hooks.append(dict(**h, expectedBytes=entry.hex()))
    layout = {}
    for row in c['types']:
        t = md.types[row['index']]
        if md.type_full_name(t) != row['type']:
            raise ValueError('activation selected type identity:'+row['role'])
        fields = {md.string(f.name_index):f for f in md.fields_for(t)}
        offsets = runtime_type_field_offsets(md, pe, image.registration, t.index)
        layout[row['role']] = {}
        for f in row['fields']:
            if selected.type_name(fields[f['name']].type_index) != f['type'] or (row['role']!='list' or c['schema']==LEGACY_SCHEMA) and offsets[f['name']] != f['offset']:
                raise ValueError('activation selected field coordinate:'+row['role']+'.'+f['name'])
            if f['alias'] in layout[row['role']]:
                raise ValueError('activation duplicate field alias')
            layout[row['role']][f['alias']] = f['offset']
    required = dict(mono={'settings','colliderCount','timerId'}, settings={'items'}, interactive={'mono','handle','broken'},
                    manager={'count'}, handle={'mono','valid'}, list={'count'})
    if {k:set(v) for k,v in layout.items()} != required or set(c['limits'])!={'maxEventsPerStage','maxItems'} or any(type(v) is not int or not 1<=v<=8192 for v in c['limits'].values()):
        raise ValueError('activation compiled fields/sample bounds differ')
    if c['schema']==SCHEMA:
        validate_list_count_accessor(c,windows,layout)
    elif layout['list']['count']!=0 or 'listCountAccessor' in c:
        raise ValueError('activation unsupported historical generic placeholder')
    return dict(contract=c, hooks=hooks, pins=pins, layout=layout)


def _accessor_mov(raw, at, opcode, width, *, register_source=False):
    """Decode the bounded register/disp8/disp32 MOV forms used by this chain."""
    start = at
    if type(at) is not int or not 0 <= at < len(raw):
        raise ValueError('clipped MOV')
    rex = raw[at] if 0x40 <= raw[at] <= 0x4f else 0
    at += bool(rex)
    if bool(rex & 8) != (width == 8) or rex & 2 or at + 2 > len(raw) or raw[at] != opcode:
        raise ValueError('MOV opcode/width')
    modrm = raw[at + 1]
    at += 2
    mod = modrm >> 6
    reg = ((modrm >> 3) & 7) + (8 if rex & 4 else 0)
    base = (modrm & 7) + (8 if rex & 1 else 0)
    if register_source:
        if mod != 3:
            raise ValueError('MOV register source')
        return reg, base, 0, at - start
    if mod not in (1, 2) or modrm & 7 == 4:
        raise ValueError('MOV field addressing')
    size = 1 if mod == 1 else 4
    if at + size > len(raw):
        raise ValueError('clipped MOV displacement')
    displacement = int.from_bytes(raw[at:at + size], 'little', signed=True)
    return reg, base, displacement, at + size - start


def validate_list_count_accessor(contract,windows,layout):
    """Prove the concrete list's size read, never an open generic offset."""
    accessor=contract['listCountAccessor'];offset=accessor['offset']
    settings=next(t for t in contract['types'] if t['role']=='settings')
    if accessor['type']!=settings['fields'][0]['type'] or type(offset) is not int or not 1<=offset<=127 or layout['list']['count']!=offset:
        raise ValueError('activation concrete list accessor identity/offset')
    field=next(t for t in contract['types'] if t['role']=='list')['fields']
    if len(field)!=1 or field[0]['name']!='_size' or field[0]['type']!='int':
        raise ValueError('activation concrete list size field identity')
    reads=accessor['reads']
    if len(reads)!=4:raise ValueError('activation concrete list accessor read order')
    if any(r['windowRole'] not in windows or
           (r['windowRole']!='load_data' and not r['windowRole'].startswith('load_data_part_')) for r in reads):
        raise ValueError('activation concrete list accessor original family')
    addresses=[windows[r['windowRole']][0]['rva']+r['offset'] for r in reads]
    if addresses!=sorted(set(addresses)):
        raise ValueError('activation concrete list accessor read order')
    try:
        data=[windows[r['windowRole']][1] for r in reads];at=[r['offset'] for r in reads]
        owner,source,_,_=_accessor_mov(data[0],at[0],0x8b,8,register_source=True)
        settings,base,disp,_=_accessor_mov(data[1],at[1],0x8b,8)
        nonvolatile={3,5,6,7,12,13,14,15}
        if source!=1 or owner not in nonvolatile or settings==owner or base!=owner or disp!=layout['mono']['settings']:
            raise ValueError('receiver -> settings')
        items,base,disp,_=_accessor_mov(data[2],at[2],0x8b,8)
        if items not in nonvolatile or items==owner or base!=settings or disp!=layout['settings']['items']:
            raise ValueError('settings -> items')
        count,base,disp,size=_accessor_mov(data[3],at[3],0x8b,4)
        if count==owner or base!=items or disp!=offset:raise ValueError('items -> int32 size')
        value,base,disp,_=_accessor_mov(data[3],at[3]+size,0x89,4)
        if value!=count or base!=owner or disp!=layout['mono']['colliderCount']:
            raise ValueError('int32 size -> receiver collider count')
    except ValueError as error:
        raise ValueError('activation concrete list accessor code:'+str(error)) from error
