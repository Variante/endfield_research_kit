"""Fresh current module typed Reader/output/callback composition checks."""
import copy, hashlib, json, struct
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import _vtable, validate_registered_formatter_composition, validate_generic_contexts
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.memorypack import reference_adapter_sources as reference, scalar_param_native as scalar, pooled_source_helper
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.memorypack.module_structure_models import bridge_packable_return as packable_return, bridge_list_callback as list_callback


def _entity_ptr_component(image,pins):
    """Reprove this dependency on the supplied image; no nested opener/cache."""
    from scripts.game_data import levelscript_entity_ptr_param_native as native
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    path=native.DEFAULT_CONTRACT;raw=path.read_bytes();fact=native._contract(path)
    if fact['nativeInputs']!=pins:raise ValueError('moduleWire.EntityPtr.selected-inputs')
    pool_path=pooled_source_helper.CONTRACT_PATH;pool=pool_path.read_bytes()
    native._validate_native(image,fact)
    _publication_gate(image,pins)
    if path.read_bytes()!=raw or pool_path.read_bytes()!=pool:raise ValueError('moduleWire.EntityPtr.declaration-drift')
    return dict(status='validated',codecKind=native.KIND,memberCount=4,rawSize=40,
        pathEncoding='int32-pool-index',nativeInputs=pins,evidenceBoundary=fact['proof']['evidenceBoundary'])

def validate_wire_joins(image, pins, components):
    base = image.pe.image_base
    md = image.metadata
    ctx = NativeReferenceContext(image)
    entries = GenericEntries(image)
    symbols = ContextSymbols(image)
    build = Build(image, pins)
    family, parents, launcher, lists, floats, float_provider, provider, enclosing = (components[k] for k in ('family', 'parents', 'launcher', 'lists', 'floats', 'float_provider', 'provider', 'enclosing'))
    launcher_type = 'Beyond.Gameplay.RollingStoneControllerData+LauncherData'
    rolling_type = 'Beyond.Gameplay.RollingStoneControllerData'
    module_type = 'Beyond.Gameplay.LevelScriptModuleData'
    lcomp, = [c for c in family['records'] if c['registrations'][0]['originalType'] == launcher_type]
    rcomp, = [c for c in family['records'] if c['registrations'][0]['originalType'] == rolling_type]
    validate_registered_formatter_composition(image, lcomp, label='moduleWire.launcher')
    validate_registered_formatter_composition(image, rcomp, label='moduleWire.rolling')
    rolling, = [r for r in parents['records'] if r['originalType'] == rolling_type]
    ref = copy.deepcopy(components['referenceRoutes'])
    s = {k: base + v for k, v in ref['symbolRvas'].items()}

    def method(owner, name):
        found = [m for m in md.methods_for(ctx.index.types[owner]) if md.string(m.name_index) == name]
        m, = found
        return m

    def record(pointer):
        regions = []
        windows = []
        rows = []
        for part in image.unwind_index.family(pointer - base)['ranges']:
            a, b = part['runtimeTriple'][:2]
            raw = image.pe.bytes_at_va(base + a, b - a)
            regions.append((base + a, raw))
            windows.append(dict(startRva=a, endRva=b, sha256=hashlib.sha256(raw).hexdigest().upper()))
            rows += image.body_index._decode(base + a, b - a)
        return (dict(entryRva=pointer - base, windows=windows, leaf=False), regions, rows)

    def ordinary_void(m):
        if not ctx.type_name(m.return_type) == 'void':
            raise ValueError("moduleWire.ctx.type_name(m.return_type) == 'void'")
        scalar.ordinary(image, ctx.type_pointer(m.return_type), 1, 'moduleWire.void')

    def callback_abi(index, owner, output_definition, ordinals):
        m = md.methods[index]
        if not (image.type_name(m.declaring_type) == owner and md.string(m.name_index) == 'Deserialize' and (m.slot == 5) and (not m.flags & 16) and (m.parameter_count == 2)):
            raise ValueError("moduleWire.image.type_name(m.declaring_type) == owner and md.string(m.name_index) == 'Deserialize' and (m.slot == 5) and (not m.flags & 16) and (m.parameter_count == 2)")
        ordinary_void(m)
        _vtable(image, m.declaring_type, 5, m.index, 'moduleWire.slot5')
        ps = list(md.parameters_for(m))
        r = image.pe.bytes_at_va(ctx.type_pointer(ps[0].type_index), 16)
        if not (ctx.type_name(ps[0].type_index), r[10], r[11]) == ('MemoryPack.MemoryPackReader', 17, 32):
            raise ValueError("moduleWire.(ctx.type_name(ps[0].type_index), r[10], r[11]) == ('MemoryPack.MemoryPackReader', 17, 32)")
        raw = image.pe.bytes_at_va(ctx.type_pointer(ps[1].type_index), 16)
        if not (raw[10], raw[11]) == (21, 32):
            raise ValueError('moduleWire.(raw[10], raw[11]) == (21, 32)')
        out = symbols.type(ctx.type_pointer(ps[1].type_index))
        if not (out['definition']['name'] == output_definition and [a['parameterOwner']['ordinal'] for a in out['classArguments']] == ordinals and all((a['parameterOwner']['typeIndex'] == m.declaring_type for a in out['classArguments']))):
            raise ValueError("moduleWire.out['definition']['name'] == output_definition and [a['parameterOwner']['ordinal'] for a in out['classArguments']] == ordinals and all((a['parameterOwner']['typeIndex'] == m.declar")
        return dict(definition=m.index, slot=5, readerByref=True, outputByref=out)
    registration, = lcomp['registrations']
    interface, = lcomp['interfaces']
    name = registration['wrapperType']
    getter = method(name, 'GetValue')
    reader = method(name, 'Deserialize')
    forwarder = md.methods[interface['formatterDeserializeMethodIndex']]
    fp = image.method_pointer_va(forwarder)
    owned, regions, rows = record(fp)
    owned['role'] = 'Launcher typed formatter forwarder'
    ref['ownedPrograms'].append(owned)
    calls = [control_transfer(r)['target'] for r in rows if bytes.fromhex(r['bytes'])[:1] == b'\xe8']
    if not len(set(calls)) == 2:
        raise ValueError('moduleWire.len(set(calls)) == 2')
    td = ctx.index.types[name]
    section = md.sections['interfaceOffsets']
    a = section.offset + td.interface_offsets_start * 8
    pairs = list(struct.iter_unpack('<ii', md.buf[a:a + td.interface_offsets_count * 8]))
    ordinal = pairs.index((interface['interfaceTypeIndex'], interface['interfaceOffset']))
    row = dict(original=launcher_type, wrapper=name, getter=[getter.index, name, 'GetValue', image.method_pointer_va(getter) - base], forwarder=[forwarder.index, image.type_name(forwarder.declaring_type), 'Deserialize', fp - base], reader=[reader.index, name, 'Deserialize', image.method_pointer_va(reader) - base], interfaceOrdinal=ordinal, forwarderSymbolRvas=dict(metadataInit=calls[0] - base, classInit=calls[1] - base))
    ref['wrappers'] = [row]
    launcher_core = reference.validate_reference_routes(image, ref, [lcomp])
    clones_path = CONTRACTS_DIR / 'memorypack_reader_clones_native.json'
    clones_raw = clones_path.read_bytes()
    clones = json.loads(clones_raw)
    if not clones['nativeInputs'] == pins:
        raise ValueError("moduleWire.clones['nativeInputs'] == pins")
    c, = [c for c in clones['clones'] if c['claim'] == 'MemoryPack.MemoryPackReader.ReadPackable' and c['resultAbi'] == 'reference']
    packable = base + c['targetRva']
    build.prove_reader_clone_target(packable, c['claim'])
    packable_owned, pregions, prows = record(packable)
    root_usage = enclosing['rootField']['typedContext']
    root_call = base + root_usage['instructionRva'] + 10
    raw = image.pe.bytes_at_va(root_call, 5)
    if not (raw[0] == 232 and root_call + 5 + int.from_bytes(raw[1:], 'little', signed=True) == packable):
        raise ValueError("moduleWire.raw[0] == 232 and root_call + 5 + int.from_bytes(raw[1:], 'little', signed=True) == packable")
    if not (enclosing['moduleUnion']['symbols']['packable'] == packable and rolling['symbols']['reads'][2] == packable and (launcher['symbols']['reads'][2] == packable)):
        raise ValueError("moduleWire.enclosing['moduleUnion']['symbols']['packable'] == packable and rolling['symbols']['reads'][2] == packable and (launcher['symbols']['reads'][2] == packable)")
    prefix = bytes.fromhex('b9050000004c8d8c24280100004c8bc7488bd3')
    hits = [at + i for at, b in pregions for i in range(len(b) - len(prefix) + 1) if b[i:i + len(prefix)] == prefix]
    tail, = hits
    returned = packable_return(pregions, tail, s['dispatch'])
    dispatch_record = next((p for p in ref['ownedPrograms'] if p['entryRva'] == s['dispatch'] - base))
    dregions = [(base + w['startRva'], image.pe.bytes_at_va(base + w['startRva'], w['endRva'] - w['startRva'])) for w in dispatch_record['windows']]
    dict_method = enclosing['dictionary']['registration']['methodDefinitionIndices'][0]
    dict_entry = entries.resolve(dict_method, ['ulong', 'object'], [])
    if not dict_entry['pointer'] == enclosing['dictionary']['registration']['pointer']:
        raise ValueError("moduleWire.dict_entry['pointer'] == enclosing['dictionary']['registration']['pointer']")
    dict_abi = callback_abi(dict_method, 'MemoryPack.Formatters.DictionaryFormatter`2', 'System.Collections.Generic.Dictionary`2', [0, 1])
    dict_dispatch = deserialize_slot(dregions, s['dispatch'], prepare=s['prepare'], callback=dict_entry['pointer'])
    dict_closed = entries.observe(dict_method, ['ulong', module_type], [])
    root_inst = image.instantiations.resolve(root_usage['methodSpec'][2])
    arg, = root_inst.arguments
    closed_dict = symbols.type(arg.type_pointer_va)
    if not (closed_dict['definition']['name'] == 'System.Collections.Generic.Dictionary`2' and [a['name'] for a in closed_dict['classArguments']] == ['ulong', module_type]):
        raise ValueError("moduleWire.closed_dict['definition']['name'] == 'System.Collections.Generic.Dictionary`2' and [a['name'] for a in closed_dict['classArguments']] == ['ulong', module_type]")
    if not [bytes.fromhex(a['rawHex'])[10] for a in closed_dict['classArguments']] == [11, 18]:
        raise ValueError("moduleWire.[bytes.fromhex(a['rawHex'])[10] for a in closed_dict['classArguments']] == [11, 18]")
    if not enclosing['dictionary']['symbols']['valueProvider'] == lists['symbols']['provider'] == base + provider['records']['actual']['entryRva'] == s['hotProvider']:
        raise ValueError("moduleWire.enclosing['dictionary']['symbols']['valueProvider'] == lists['symbols']['provider'] == base + provider['records']['actual']['entryRva'] == s['hotProvider']")
    if not enclosing['dictionary']['symbols']['keyProvider'] == base + float_provider['actual']['pointerRva']:
        raise ValueError("moduleWire.enclosing['dictionary']['symbols']['keyProvider'] == base + float_provider['actual']['pointerRva']")
    list_method = lists['entry']['methodDefinitionIndices'][0]
    list_entry = entries.resolve(list_method, ['object'], [])
    if not list_entry['pointer'] == lists['entry']['pointer']:
        raise ValueError("moduleWire.list_entry['pointer'] == lists['entry']['pointer']")
    list_abi = callback_abi(list_method, 'MemoryPack.Formatters.ListFormatter`1', 'System.Collections.Generic.List`1', [0])
    list_dispatch = deserialize_slot(dregions, s['dispatch'], prepare=s['prepare'], callback=list_entry['pointer'])
    list_closed = entries.observe(list_method, [launcher_type], [])
    child_usage, = [r['usage'] for r in rolling['usages'] if r['field'] == 'launcherDataList']
    inst = image.instantiations.resolve(child_usage['methodSpec'][2])
    arg, = inst.arguments
    closed_list = symbols.type(arg.type_pointer_va)
    if not (closed_list['definition']['name'] == 'System.Collections.Generic.List`1' and closed_list['classArguments'][0]['name'] == launcher_type):
        raise ValueError("moduleWire.closed_list['definition']['name'] == 'System.Collections.Generic.List`1' and closed_list['classArguments'][0]['name'] == launcher_type")
    list_type = ctx.index.types['System.Collections.Generic.List`1']
    list_context = symbols.context(list_type.index)
    validate_generic_contexts(image, [list_context], label='moduleWire.ListClass')
    slots = {e['relativeSlot']: e for e in lists['context']['entries']}
    ctor = slots[1]
    if not (ctor['kind'], ctor['typeName'], ctor['methodName']) == (3, 'System.Collections.Generic.List`1', '.ctor'):
        raise ValueError("moduleWire.(ctor['kind'], ctor['typeName'], ctor['methodName']) == (3, 'System.Collections.Generic.List`1', '.ctor')")
    if not (len(ctor['classArguments']) == 1 and ctor['classArguments'][0]['parameterOwner']['typeIndex'] == lists['context']['definition'] and (ctor['classArguments'][0]['parameterOwner']['ordinal'] == 0)):
        raise ValueError("moduleWire.len(ctor['classArguments']) == 1 and ctor['classArguments'][0]['parameterOwner']['typeIndex'] == lists['context']['definition'] and (ctor['classArguments'][0]['parameterOwner']['or")
    cm = md.methods[ctor['methodSpec'][0]]
    cp, = md.parameters_for(cm)
    if not ctx.type_name(cp.type_index) == 'int':
        raise ValueError("moduleWire.ctx.type_name(cp.type_index) == 'int'")
    scalar.ordinary(image, ctx.type_pointer(cp.type_index), 8, 'moduleWire.capacity')
    array_slot = next((e for e in list_context['entries'] if e['relativeSlot'] == 1))
    raw = image.pe.bytes_at_va(ctx.type_pointer(array_slot['index']), 16)
    if not raw[10:12] == bytes((29, 0)):
        raise ValueError('moduleWire.raw[10:12] == bytes((29, 0))')
    element = symbols.type(int.from_bytes(raw[:8], 'little'))
    if not (element['parameterOwner']['typeIndex'] == list_type.index and element['parameterOwner']['ordinal'] == 0):
        raise ValueError("moduleWire.element['parameterOwner']['typeIndex'] == list_type.index and element['parameterOwner']['ordinal'] == 0")
    lregions = []
    for p in lists['parts']:
        raw = image.pe.bytes_at_va(base + p['startRva'], p['endRva'] - p['startRva'])
        if not hashlib.sha256(raw).hexdigest().upper() == p['sha256']:
            raise ValueError("moduleWire.hashlib.sha256(raw).hexdigest().upper() == p['sha256']")
        lregions.append((base + p['startRva'], raw))
    if not sorted(((p['startRva'], p['endRva']) for p in lists['parts'])) == sorted((tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(list_entry['pointer'] - base)['ranges'])):
        raise ValueError("moduleWire.sorted(((p['startRva'], p['endRva']) for p in lists['parts'])) == sorted((tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(list_entry['pointer'] - base)['ranges']))")
    path, = [p for p in lists['paths'] if p['countWitness'] == 1 and p['newList'] and (not p['growthDelegate'])]
    site, = path['elementCallbackSites']
    direct = list_callback(lregions, site - 38, lists['symbols']['prepare'])
    if not lists['symbols']['prepare'] == s['prepare']:
        raise ValueError("moduleWire.lists['symbols']['prepare'] == s['prepare']")
    adapter = md.methods[ref['canonicalEntries']['Deserialize']['definition']]
    if not (adapter.slot == 5 and (not adapter.flags & 16) and (adapter.parameter_count == 2)):
        raise ValueError('moduleWire.adapter.slot == 5 and (not adapter.flags & 16) and (adapter.parameter_count == 2)')
    ordinary_void(adapter)
    _vtable(image, adapter.declaring_type, 5, adapter.index, 'moduleWire.LauncherAdapterSlot5')
    ps = list(md.parameters_for(adapter))
    rr = image.pe.bytes_at_va(ctx.type_pointer(ps[0].type_index), 16)
    out = image.pe.bytes_at_va(ctx.type_pointer(ps[1].type_index), 16)
    if not (rr[10], rr[11], out[10], out[11]) == (17, 32, 19, 32):
        raise ValueError('moduleWire.(rr[10], rr[11], out[10], out[11]) == (17, 32, 19, 32)')
    owned_output = symbols.type(ctx.type_pointer(ps[1].type_index))
    if not (owned_output['parameterOwner']['typeIndex'] == adapter.declaring_type and owned_output['parameterOwner']['ordinal'] == 0):
        raise ValueError("moduleWire.owned_output['parameterOwner']['typeIndex'] == adapter.declaring_type and owned_output['parameterOwner']['ordinal'] == 0")
    largs = image.instantiations.resolve(registration['classInstantiation']).arguments
    if not ([symbols.type(a.type_pointer_va)['name'] for a in largs] == [launcher_type, name] and all((image.pe.bytes_at_va(a.type_pointer_va, 16)[10:12] == bytes((18, 0)) for a in largs))):
        raise ValueError("moduleWire.[symbols.type(a.type_pointer_va)['name'] for a in largs] == [launcher_type, name] and all((image.pe.bytes_at_va(a.type_pointer_va, 16)[10:12] == bytes((18, 0)) for a in largs))")
    float_method = floats['entry']['methodDefinitionIndices'][0]
    float_entry = entries.resolve(float_method, ['float'], [])
    float_abi = callback_abi(float_method, 'MemoryPack.Formatters.ListFormatter`1', 'System.Collections.Generic.List`1', [0])
    float_dispatch = deserialize_slot(dregions, s['dispatch'], prepare=s['prepare'], callback=float_entry['pointer'])
    ri, = rcomp['interfaces']
    fw = md.methods[ri['formatterDeserializeMethodIndex']]
    fwrow, fwregions, fwrows = record(image.method_pointer_va(fw))
    calls = [control_transfer(r)['target'] for r in fwrows if bytes.fromhex(r['bytes'])[:1] == b'\xe8']
    if not len(set(calls)) == 2:
        raise ValueError('moduleWire.len(set(calls)) == 2')
    target = method(ri['wrapperType'], 'Deserialize')
    forward = prove_zero_wrapper_forwarder(fwrows, dict(metadataInit=calls[0], classInit=calls[1]), image.method_pointer_va(target))
    _vtable(image, fw.declaring_type, 5, fw.index, 'moduleWire.RollingWrapperSlot5')
    rolling_dispatch = deserialize_slot(dregions, s['dispatch'], prepare=s['prepare'], callback=image.method_pointer_va(fw))
    entity = _entity_ptr_component(image,pins)
    if not entity['status'] == 'validated':
        raise ValueError("moduleWire.entity['status'] == 'validated'")
    return dict(referenceRoutes=ref, referenceCore=launcher_core, entityPtr=entity)


def validate_owned_values(image,pins,c):
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 from scripts.game_data.memorypack import primitive_param
 from scripts.game_data.il2cpp.reference_field_programs import preserved_argument
 from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
 base=image.pe.image_base;ctx=NativeReferenceContext(image);r=c['rollingOwned'];s=c['lifecycleSymbols'];build=Build(image,pins)
 def need(label,expected,actual):
  if expected!=actual:raise ValueError('moduleValues.'+label+':expected='+str(expected)[:240]+',actual='+str(actual)[:240])
 def source(d):
  parts=d.get('parts',d.get('windows'));entry=d.get('entryRva',d.get('pointerRva'));need('owned-ranges',sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(entry)['ranges']),sorted((p['startRva'],p['endRva'])for p in parts));image.check_windows(parts,label='moduleValues');return [(base+p['startRva'],image.pe.bytes_at_va(base+p['startRva'],p['endRva']-p['startRva']))for p in parts]
 tg=r['typedGetter'];g=BytesPath([(base+tg['getValue'][3],image.pe.bytes_at_va(base+tg['getValue'][3],7))],base+tg['getValue'][3]);g.take('33d2');need('typed-getter-forwarder',base+tg['accessor'][3],g.relative('e9'))
 d=r['instanceSet']['source'];g=BytesPath(source(d),base+d['entryRva']);g.take('4883ec28','4c8bd1','48895118','4883c118','4c8bca');g.call(s['barrier']);g.take('498d4a10','4d894a10','4883c428');need('same-reference-dual-store-barrier',s['barrier'],g.relative('e9'))
 # Exact selected disabled-collector leaf preserves R9/R10 across both stores.
 g=BytesPath([(s['barrier'],image.pe.bytes_at_va(s['barrier'],256))],s['barrier']);g.relative('833d');g.take('00','4c8bc1');g.branch('74',True,1);g.take('c3')
 for d in r['inheritedSetters']:
  g=BytesPath(source(d['source']),base+d['method'][3]);g.take('4883ec28','488b4110','4885c0');g.branch('74',False,1);g.take(('8850'if d['field']=='disableWhenCompleted'else'488950')+bytes((d['slot'],)).hex(),'4883c428','c3')
 for name,d in c['launcherOwned']['helperPrograms'].items():
  source(d);offsets=scalar.reader_offsets(image,'moduleValues')
  if name=='header':primitive_param.object_header_source(image,d,offsets)
  elif name=='boolean':scalar.boolean_source(image,d,offsets,'moduleValues.boolean')
  elif name=='single':primitive_param.single_source(image,d,offsets)
  elif name=='uint64'and 'advance'in d:scalar.uint64_source(image,d,offsets)
  else:scalar.integer_source(image,d,offsets,'moduleValues.'+name,width=8 if name=='uint64'else 4)
 h=c['launcher']['hiddenForwarder'];entry=base+h['entryRva'];parts=image.unwind_index.family(h['entryRva'])['ranges'];need('hidden40-single-range',1,len(parts));a,z=parts[0]['runtimeTriple'][:2];g=BytesPath([(base+a,image.pe.bytes_at_va(base+a,z-a))],entry);g.take('4053','4883ec20');site=g.at;g.relative('4c8b05');g.take('488bd9');target=g.relative('e8');g.take('488bc3','4883c420','5b','c3');need('hidden40-complete-return',base+z,g.at);need('hidden40-typed-usage',h['usage']['instructionRva'],site-base);need('hidden40-clone-target',h['actualCloneTargetRva'],target-base);build.prove_reader_clone_target(target,'MemoryPack.MemoryPackReader.ReadValue',result_abi='hidden-output-40')
 # The root's earlier generated calls must preserve both incoming aliases.
 at=c['enclosing']['rootField']['typedContext']['instructionRva'];prefix=[]
 for p in c['rootSource']['parts']:
  if p['startRva']>=at:continue
  end=min(p['endRva'],at-3);prefix+=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(base+p['startRva'],end-p['startRva']),base+p['startRva'])
 need('root-incoming-aliases',dict(rcx='r13',rdx='r15'),{arg:preserved_argument(prefix,arg)for arg in ('rcx','rdx')})


def validate_base_routes(image,c,wire):
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);comp=c['baseComposition'];validate_registered_formatter_composition(image,comp,label='moduleBase');registration,=comp['registrations'];interface,=comp['interfaces'];name=registration['wrapperType'];original=registration['originalType'];getter=md.methods[interface['getValueMethodIndex']];pointer=image.method_pointer_va(getter)
 scalar.owned_method_abi(image,ctx,getter.index,ctx.index.types[name].index,(original,18,True),[],'moduleBase.getter');g=BytesPath([(pointer,image.pe.bytes_at_va(pointer,5))],pointer);g.take('488b4110','c3')
 f=wire['referenceRoutes'];s={k:base+v for k,v in f['symbolRvas'].items()};regions={base+p['entryRva']:[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in p['windows']]for p in f['ownedPrograms']}
 reader=md.methods[interface['formatterDeserializeMethodIndex']]
 if reader.slot!=5 or reader.flags&16 or ctx.type_name(reader.return_type)!='void' or reader.parameter_count!=2:raise ValueError('moduleBase.union-callback-ABI')
 ps=list(md.parameters_for(reader))
 for p,expected,kind in zip(ps,('MemoryPack.MemoryPackReader',name),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
  if (ctx.type_name(p.type_index),raw[10],raw[11])!=(expected,kind,32):raise ValueError('moduleBase.union-byref-parameters')
 _vtable(image,reader.declaring_type,5,reader.index,'moduleBase.union-slot5');deserialize_slot(regions[s['dispatch']],s['dispatch'],prepare=s['prepare'],callback=image.method_pointer_va(reader))
 for owner in (name,c['rollingOwned']['wrapper']):
  td=ctx.index.types[owner];section=md.sections['interfaceOffsets'];a=section.offset+td.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[a:a+td.interface_offsets_count*8]));ordinal,pair=next((i,p)for i,p in enumerate(pairs)if p[0]==interface['interfaceTypeIndex']);_vtable(image,td.index,pair[1],getter.index,'moduleBase.inherited-original-getter');reference.conversion(regions[s['conversion']],s['conversion'],base+f['conversionPrepareRva'],pointer,ordinal=ordinal)
