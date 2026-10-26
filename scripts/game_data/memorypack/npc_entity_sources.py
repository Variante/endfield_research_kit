"""Current EntityAttract source closure under an already selected NPC image."""
import json,struct
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.memorypack import npc_entity_programs as models,entity_attract_sources as setters,list64_sources as list64,ulong_list_sources as ulong,null_list_param,reference_adapter_sources as reference,scalar_param_native as scalar,primitive_param
from scripts.game_data.memorypack.record_sources import ordered_record
from scripts.game_data.memorypack.vector_layout import vector_recorder


def validate_components(image,pins,fact,reference_fact):
    if fact.get("schema")!="endfield.npc-entity-attract-source-component.v1"or fact.get("countLimit")!=53:raise ValueError("npcEntity.schema/profile")
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);build=Build(image,pins);entries=GenericEntries(image);record=fact['record'];original=record['typeName'];wrapper=record['wrapperName'];composition=fact['composition'];td=ctx.index.types[wrapper];methods={md.string(m.name_index):m for m in md.methods_for(td)}
    if pins!=fact['nativeInputs']or pins!=reference_fact['nativeInputs']:raise ValueError('npcEntity.selected-inputs')
    validate_eager_wrap_registration(image,fact['eager'],label='npcEntity');w,=[w for w in build.wrappers.values()if w.wrapped_type==original]
    if w.name!=wrapper or[[m.name,m.declared_type]for m in w.members]!=[[m['name'],m['declaredType']]for m in record['members']]:raise ValueError('npcEntity.current-fields')
    def owned(pointer):
        regions=[];rows=[];windows=[]
        for p in image.unwind_index.family(pointer-base)['ranges']:
            a,z=p['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);regions.append((base+a,raw));rows+=decode_type_data_initialization_instructions(image.mapper,raw,base+a);windows.append(dict(startRva=a,endRva=z))
        return dict(pointer=pointer,regions=regions,rows=rows,windows=windows)
    for m in record['methods']:
        image.validate_method_row([m['methodIndex'],wrapper,m['name'],m['entryRva']],label='npcEntity')
        if 'windows'in m:
            if sorted((p['startRva'],p['endRva'])for p in m['windows'])!=sorted((p['startRva'],p['endRva'])for p in owned(base+m['entryRva'])['windows']):raise ValueError('npcEntity.complete-owned-source')
            image.check_windows(m['windows'],label='npcEntity')
    s={k:base+v for k,v in fact['symbols'].items()};offsets=scalar.reader_offsets(image,'npcEntity');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16;rec=vector_recorder(image);primitive_param.object_header_source(image,rec(s['header']-base),offsets)
    source=owned(image.method_pointer_va(methods['Deserialize']));prefixes=[models.prefix(source['regions'],source['pointer'],s,created=a,null=n)for a in(False,True)for n in(False,True)];constructors=[models.constructor(owned(image.method_pointer_va(methods[name]))['regions'],image.method_pointer_va(methods[name]),s,factory=name=='CreateInstance')for name in('.ctor','CreateInstance')]
    for proof in prefixes+constructors:
        cell=proof.get('allocationClassCellVA')
        if cell:
            address=next(a for a,b in proof['selectedBytes']if b=='488b0d'and a+7+int.from_bytes(image.pe.bytes_at_va(a+3,4),'little',signed=True)==cell);usage=derive_typed_usage_context(image,address-base,label='npcEntity.allocation')
            if(usage['tag'],usage['typeName'])!=(1,original if proof in constructors else wrapper):raise ValueError('npcEntity.actual-allocation-type')
    ctor,=[m for m in md.methods_for(ctx.index.types[original])if md.string(m.name_index)=='.ctor'and image.method_pointer_va(m)==s['originalConstructor']]
    if ctor.flags&16 or ctor.parameter_count or ctx.type_name(ctor.return_type)!='void':raise ValueError('npcEntity.original-constructor-ABI')
    composition=json.loads(json.dumps(composition));interface,=composition['interfaces'];section=md.sections['interfaceOffsets'];a=section.offset+td.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[a:a+td.interface_offsets_count*8]));ordinal=pairs.index((interface['interfaceTypeIndex'],interface['interfaceOffset']));getter=image.method_pointer_va(methods['GetValue']);forward=md.methods[interface['formatterDeserializeMethodIndex']];forward_pointer=image.method_pointer_va(forward);core=json.loads(json.dumps(reference_fact['referenceRoutes']));core['ownedPrograms']+=[dict(entryRva=getter-base,windows=[composition['codeWindows'][0]],leaf=True),dict(entryRva=forward_pointer-base,windows=composition['codeWindows'][1:],leaf=False)];core['wrappers']=[dict(original=original,wrapper=wrapper,getter=next(m for m in composition['methods']if m[2]=='GetValue'),forwarder=next(m for m in composition['methods']if m[2]=='Deserialize'),reader=[methods['Deserialize'].index,wrapper,'Deserialize',source['pointer']-base],interfaceOrdinal=ordinal,forwarderSymbolRvas=core['wrappers'][0]['forwarderSymbolRvas'])];adapter=reference.validate_reference_routes(image,core,[composition])
    reviewed=dict(typeName=original,wrapperName=wrapper,fields=[[m.name,m.declared_type]for m in w.members]);ordered=ordered_record(build,reviewed)
    for row,m in zip(ordered['orderedReads'],w.members,strict=True):
        if m.kind=='enum':
            enum=ctx.index.types[m.declared_type]
            if [ctx.type_name(f.type_index)for f in md.fields_for(enum)if md.string(f.name_index)=='value__']!=['int']:raise ValueError('npcEntity.enum-int32')
        if m.kind in('enum','scalar64'):scalar.integer_source(image,rec(row['targetRva'],fragments=True),offsets,'npcEntity.'+m.name,width=8 if m.kind=='scalar64'else 4)
    first=ordered['orderedReads'][0];build.prove_reader_clone_target(base+first['targetRva'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
    positive_starts={p['nextAddress']for p in prefixes if not p['null']}
    if len(positive_starts)!=1 or positive_starts!={base+first['typedContext']['instructionRva']}:raise ValueError('npcEntity.exact-prefix-field-join')
    suffix=models.positive(source['regions'],next(iter(positive_starts)),[base+r['targetRva']for r in ordered['orderedReads']],[image.method_pointer_va(md.methods[m.method_index])for m in w.members])
    owner=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];method,=[m for m in md.methods_for(owner)if md.string(m.name_index)=='Deserialize'];entry=entries.resolve(method.index,['ulong'],[]);body=owned(entry['pointer']);nullzero=ulong.derive(image,pins,ctx,entry,body,constructor_program=null_list_param.empty_list_constructor);ls={k:base+v for k,v in nullzero['helperRvas'].items()};rows=body['rows']
    def target(r):raw=bytes.fromhex(r['bytes']);return int(r['va'],16)+len(raw)+int.from_bytes(raw[-4:],'little',signed=True)
    callback={target(r)for r in rows if bytes.fromhex(r['bytes'])[:3]==bytes.fromhex('488d3d')}
    if len(callback)!=1:raise ValueError('npcEntity.callback-unique')
    ls['callback']=callback.pop();ls['arrayAllocate']=next(target(r)for i,r in enumerate(rows)if bytes.fromhex(r['bytes'])[:1]==b'\xe8'and i>1 and rows[i-1]['text']=='mov rcx, rax'and rows[i-2]['text']=='mov rdx, rbp');ls['prepare']=next(target(r)for i,r in enumerate(rows)if bytes.fromhex(r['bytes'])[:1]==b'\xe8'and i and rows[i-1]['text']=='mov rcx, [r15]');co=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1'];cm,=[m for m in md.methods_for(co)if md.string(m.name_index)=='Deserialize'];closed=entries.resolve(cm.index,['ulong'],[])
    if closed['pointer']!=ls['callback']or cm.slot!=5:raise ValueError('npcEntity.actual-ulong-slot5')
    cb=owned(ls['callback']);list64.formatter(cb['regions'],cb['pointer'],offsets)
    for count in range(1,fact['countLimit']+1):list64.positive_list(body['regions'],body['pointer'],offsets,ls,count=count,count_limit=fact['countLimit'])
    for m in w.members:
        field=ctx.field(original+'::'+m.name);instance=ctx.field(wrapper+'::__instance');b=owned(image.method_pointer_va(md.methods[m.method_index]));nulls={target(r)for i,r in enumerate(b['rows'])if bytes.fromhex(r['bytes'])[:1]==b'\xe8'and i+1<len(b['rows'])and b['rows'][i+1]['text']=='int3'}
        if len(nulls)!=1:raise ValueError('npcEntity.setter-null-failure')
        setters.setter(b['regions'],b['pointer'],field=field[2],kind='reference'if m.kind=='list'else'qword'if m.kind=='scalar64'else'dword',instance=instance[2],null_throw=nulls.pop(),barrier=ls['barrier'])
    return dict(fields=4,positiveArgumentReturnProgram=suffix,positiveListLimit=fact['countLimit'],adapterPrograms=adapter['selectedPrograms'],sourceEntryRva=source['pointer']-base,listEntryRva=entry['pointer']-base,wholeOwnerAdmitted=False,liveProviderSelectionProved=False)
