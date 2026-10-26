"""Fresh typed current Patrol source composition, below runtime Audio semantics."""
import hashlib,json,re,struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_extent
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_typed_usage_context,validate_generic_contexts,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.protocol import field_defaults,native_enum_members
from scripts.game_data.memorypack.record_sources import return_field_source,typed_source_context
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.reference_adapter_sources import conversion,validate_reference_routes
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param,int_list_sources,montage_sources,pooled_string_list_sources,levelscript_interactive_sources,module_structure_models,lang_key_list_sources,patrol_source_models as models


def _direct(image,pins):
 build=Build(image,pins);ctx=NativeReferenceContext(image);base=image.pe.image_base;offsets=scalar.reader_offsets(image,'Patrol');recorder=vector_recorder(image)
 out=[]
 for type_name in('Beyond.Gameplay.AI.Config.NpcPatrolData','Beyond.Gameplay.Core.PatrolSubAction'):
  wrapper=next(w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name);body=image.body_index.body(wrapper.name,'Deserialize');ranges=[p['runtimeTriple'][:2]for p in image.unwind_index.family(body.pointer-base)['ranges']];regions=[(base+a,image.pe.bytes_at_va(base+a,b-a))for a,b in ranges];rows=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(body.pointer,body.size),body.pointer);plan=[]
  for member in wrapper.members:
   field=ctx.field(type_name+'::'+member.name);mode={'bool':'bool','float32':'single','string':'reference','list':'reference','enum':'dword','scalar32':'dword'}.get(member.kind,'dword'if member.declared_type=='Beyond.Gameplay.Core.GameplayTag'else'reference')
   op='movss'if mode=='single'else'mov';value={'bool':'al','single':'xmm0','dword':'eax','reference':'rax'}[mode];matches=[i for i,r in enumerate(rows)if re.fullmatch(op+r' \[(?:rax|rcx)\+0x'+format(field[2],'x')+r'\], '+value,r['text'])]
   if len(matches)!=1:raise ValueError('Patrol.unique-field-return-store:'+member.name+':'+str(matches))
   store=matches[0];call=max(i for i,r in enumerate(rows[:store])if r['text'].startswith('call '));target=int(rows[call]['text'].split()[1],16)
   typed=member.kind in('enum','list','object');proof=None
   if typed:
    method='ReadPackable'if member.kind=='list'else'ReadUnmanaged'if member.kind=='enum'or member.declared_type=='Beyond.Gameplay.Core.GameplayTag'else'ReadValue'
    proof=typed_source_context(image,rows[max(0,call-5):call],field=member.name,method=method,argument=member.declared_type)
    if method in('ReadPackable','ReadValue'):build.prove_reader_clone_target(target,'MemoryPack.MemoryPackReader.'+method,result_abi='reference')
   if mode=='bool':scalar.boolean_source(image,recorder(target-base),offsets,'Patrol.boolean')
   elif mode=='single':primitive_param.single_source(image,recorder(target-base),offsets)
   elif member.kind=='string':build.prove_pooled_string_target(target)
   elif mode=='dword':
    if member.declared_type=='Beyond.Gameplay.Core.GameplayTag':montage_sources.unmanaged4(image,recorder(target-base),offsets)
    else:scalar.integer_source(image,recorder(target-base),offsets,'Patrol.integer')
   plan.append(dict(name=member.name,type=member.declared_type,offset=field[2],mode=mode,wireBytes=1 if mode=='bool'else 4 if mode in('single','dword')or member.kind=='string'else None,typed=typed,target=target,typedContext=proof))
  barrier_calls=[int(r['text'].split()[1],16)for r in rows if r['text'].startswith(('call ','jmp '))and r['text'].split()[1].startswith('0x')and int(r['text'].split()[1],16)not in{f['target']for f in plan}]
  # The named direct-store address update is followed by the same actual barrier.
  store=next(i for i,r in enumerate(rows)if r['text']==f"mov [rcx+0x{next(f['offset']for f in plan if f['type']=='string'):x}], rax")
  barrier=int(rows[store+2]['text'].split()[1],16)
  program=models.direct_record(regions,body.pointer,plan,offsets,barrier,tail_barrier=type_name.endswith('NpcPatrolData'))
  out.append(dict(type=type_name,wrapper=wrapper.name,entryRva=body.pointer-base,windows=[dict(startRva=a,endRva=b,sha256=hashlib.sha256(image.pe.bytes_at_va(base+a,b-a)).hexdigest().upper())for a,b in ranges],fields=plan,barrierRva=barrier-base,program=program))
 return out



def _point(image,pins):
 build=Build(image,pins);ctx=NativeReferenceContext(image);base=image.pe.image_base;offsets=scalar.reader_offsets(image,'Patrol.point');wrapper=next(w for w in image.memorypack_wrappers.values()if w.wrapped_type=='Beyond.Gameplay.AI.Config.NpcPatrolPoint');body=image.body_index.body(wrapper.name,'Deserialize');ranges=[p['runtimeTriple'][:2]for p in image.unwind_index.family(body.pointer-base)['ranges']];regions=[(base+a,image.pe.bytes_at_va(base+a,b-a))for a,b in ranges]
 slots={m.name:ctx.field(wrapper.wrapped_type+'::'+m.name)[2]for m in wrapper.members};rows=image.body_index._decode(body.pointer,body.size);calls=[int(r['text'].split()[1],16)for r in rows if r['text'].startswith('call ')];packable=calls[0];barrier=calls[1];program=models.point_record(regions,body.pointer,offsets,slots,packable,barrier)
 usage=derive_typed_usage_context(image,program['listContext']['instruction']-base,label='Patrol.point.actions');actual=(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments']);expected=('MemoryPack.MemoryPackReader','ReadPackable',[],['System.Collections.Generic.List`1<Beyond.Gameplay.Core.PatrolSubAction>'])
 if actual!=expected or usage['usageCellRva']!=program['listContext']['cell']-base:raise ValueError('Patrol.point.typed-list-context:'+str(actual))
 build.prove_reader_clone_target(packable,'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference');enum=build.derive_enum(dict(typeName='Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType',backingType='System.Int32',width=4))
 v='UnityEngine.Vector3';td=ctx.index.types[v];fields=[[image.metadata.string(f.name_index),ctx.field(v+'::'+image.metadata.string(f.name_index))[1],ctx.field(v+'::'+image.metadata.string(f.name_index))[2]-16]for f in image.metadata.fields_for(td)if not ctx.field_attributes(f.type_index)&16];sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 if not ctx.is_value_type(v)or fields!=[['x','float',0],['y','float',4],['z','float',8]]or(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))!=(28,12):raise ValueError('Patrol.point.Vector3-managed-and-native-layout:'+str(fields))
 out=dict(status='current-point-source-order-component-no-whole-owner',nativeInputs=pins,record=dict(type=wrapper.wrapped_type,wrapper=wrapper.name,entryRva=body.pointer-base,windows=[dict(startRva=a,endRva=b,sha256=hashlib.sha256(image.pe.bytes_at_va(base+a,b-a)).hexdigest().upper())for a,b in ranges],fields=[[m.name,m.declared_type,m.kind]for m in wrapper.members],slots=slots,program=program,usage=usage,enum=enum,vectorFields=fields,barrierRva=barrier-base))
 return out['record']



def _lists(image,pins,direct,point):
 ctx=NativeReferenceContext(image);base=image.pe.image_base;md=image.metadata;entries=GenericEntries(image);build=Build(image,pins)
 def need(label,expected,actual):
  if expected!=actual:raise ValueError('Patrol.list.'+label+':'+str((expected,actual))[:1000])
 def fail(*args):raise ValueError('Patrol.list:'+str(args)[:1000])
 td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize'];context=ContextSymbols(image).context(td.index);validate_generic_contexts(image,[context],label='Patrol.list');validate_list_formatter_base_context(image,context,entries,fail=fail);list_context=ContextSymbols(image).context(ctx.index.types['System.Collections.Generic.List`1'].index);validate_generic_contexts(image,[list_context],label='Patrol.List');validate_capacity_constructor_context(image,context,list_context,entries,fail=fail)
 entry=entries.resolve(method.index,['object'],[]);ranges=[p['runtimeTriple'][:2]for p in image.unwind_index.family(entry['pointer']-base)['ranges']];regions=[(base+a,image.pe.bytes_at_va(base+a,b-a))for a,b in ranges];offsets=scalar.reader_offsets(image,'Patrol.list');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 fact_path=CONTRACTS_DIR/'levelscript_pooled_string_list_native.json';fact_bytes=fact_path.read_bytes();fact=json.loads(fact_bytes);need('component-native-inputs',pins,fact['nativeInputs']);reference=fact;need('canonical-current-entry',json.loads(json.dumps(entry)),reference['listEntry']['registration']);symbols={k:base+v for k,v in reference['listSymbols'].items()}
 namespace=vars(pooled_string_list_sources)
 programs=[namespace['list_source'](regions,entry['pointer'],offsets,symbols,count=count,new=new,grow=grow,count_limit=17)for count in range(-1,18)for new in(True,)for grow in(False,)]
 for n in range(1,18):
  for p in programs:
   if p['countWitness']==n:need('callback-count',n,len(p['elementCallbackSites']))
 
 # Exact current formatter ABI; flags are metadata semantics, not an arbitrary mask.
 from scripts.game_data.il2cpp.formatter_composition import _vtable
 need('instance-slot-arity-void',(False,5,2,'void'),(bool(method.flags&16),method.slot,method.parameter_count,ctx.type_name(method.return_type)));_vtable(image,method.declaring_type,5,method.index,'Patrol.list')
 params=list(md.parameters_for(method));reader=ctx.index.types['MemoryPack.MemoryPackReader'];byval=image.pe.bytes_at_va(ctx.type_pointer(reader.byval_type_index),16);formal=image.pe.bytes_at_va(ctx.type_pointer(params[0].type_index),16)
 need('reader-byval-flags',b'\x11\x80',byval[10:12]);need('reader-byref-flags',b'\x11\x20',formal[10:12]);need('same-reader-definition',byval[:8],formal[:8]);need('reader-value-parent','System.ValueType',ctx.parent('MemoryPack.MemoryPackReader'))
 slot0=next(e for e in context['entries']if e['relativeSlot']==0);owned=image.pe.bytes_at_va(ctx.type_pointer(slot0['index']),16);formal=image.pe.bytes_at_va(ctx.type_pointer(params[1].type_index),16);need('output-byref-flags',b'\x15\x20',formal[10:12]);need('owned-list-byval',b'\x15\x00',owned[10:12]);need('same-output-carrier',owned[:8],formal[:8])
 
 # Typed closed parent carriers are proved independently of the conditional shared source profile.
 bridges=[]
 for file,name in(('direct23.json','points'),('point26.json','actions')):
  report=dict(nativeInputs=pins,records=direct)if file=='direct23.json'else dict(nativeInputs=pins,record=point);need('parent-native-inputs',pins,report['nativeInputs'])
  if file=='direct23.json':
   record=next(r for r in report['records']if r['type'].endswith('NpcPatrolData'));field=next(f for f in record['fields']if f['name']==name);usage=field['typedContext'];parent=record['type'];kind=field['type'];target=field['target']
  else:
   record=report['record'];usage=record['usage'];parent=record['type'];kind='System.Collections.Generic.List`1<Beyond.Gameplay.Core.PatrolSubAction>';target=entry['pointer'] # Actual call is independently checked by point source/model + clone proof.
  validate_typed_usage_context(image,usage,label='Patrol.list.parent');need('typed-parent',('MemoryPack.MemoryPackReader','ReadPackable',[],[kind]),tuple(usage[k]for k in('typeName','methodName','classArguments','methodArguments')))
  owner=ctx.index.types[parent];field,=[f for f in md.fields_for(owner)if md.string(f.name_index)==name];closed=closed_generic_reference_extent(ctx,field.type_index);need('declared-list',kind,closed['type']);element,=closed['argumentTypes'];need('reference-child-value-kind',False,ctx.is_value_type(element));call=image.instantiations.resolve(usage['methodSpec'][2]).arguments;need('parent-arity',1,len(call));raw_type=image.pe.bytes_at_va(call[0].type_pointer_va,16);need('parent-ginst-flags',b'\x15\x00',raw_type[10:12]);element_record=ContextSymbols(image).type(call[0].type_pointer_va)['classArguments'][0];element_raw=bytes.fromhex(element_record['rawHex']);need('closed-element-class-flags',b'\x12\x00',element_raw[10:12]);need('closed-element-definition',ctx.index.types[element].index,int.from_bytes(element_raw[:8],'little'));need('same-parent-carrier',bytes.fromhex(closed['declaredTypeRecordHex'])[:8],raw_type[:8]);bridges.append(dict(parent=parent,field=name,declaredType=kind,element=element,usage=usage,closed=closed))
 
 # Current LevelData owning call/typed field store; earlier child wire tiers stay owned by its maintained sequential reader.
 from scripts.game_data.memorypack.record_sources import return_field_source,typed_source_context
 from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
 w=next(w for w in image.memorypack_wrappers.values()if w.wrapped_type=='Beyond.Gameplay.LevelData');body=image.body_index.body(w.name,'Deserialize');root_rows=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(body.pointer,body.size),body.pointer);field=ctx.field(w.wrapped_type+'::npcPatrol');root_source=return_field_source(image,root_rows,'npcPatrol',field[2]);call=next(i for i,r in enumerate(root_rows)if int(r['va'],16)-base==root_source['callRva']);usage=typed_source_context(image,root_rows[max(0,call-5):call],field='npcPatrol',method='ReadPackable',argument=field[1]);build.prove_reader_clone_target(base+root_source['targetRva'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference');td=ctx.index.types[w.wrapped_type];f,=[f for f in md.fields_for(td)if md.string(f.name_index)=='npcPatrol'];closed=closed_generic_reference_extent(ctx,f.type_index);need('outer-list-element',['Beyond.Gameplay.AI.Config.NpcPatrolData'],closed['argumentTypes']);bridges.append(dict(parent=w.wrapped_type,field='npcPatrol',declaredType=field[1],element=closed['argumentTypes'][0],usage=usage,closed=closed,source=root_source))
 
 # Revalidate the actual maintained List<> factory mapping, without inventing a concrete closed registration.
 fp=CONTRACTS_DIR/'levelscript_int_list_native.json';fp_bytes=fp.read_bytes();factory_fact=json.loads(fp_bytes);need('factory-inputs',pins,factory_fact['nativeInputs']);factory=factory_fact['factory']
 for u in factory['usages']:validate_typed_usage_context(image,u,label='Patrol.list.factory')
 need('factory-pair',['System.Collections.Generic.List`1','MemoryPack.Formatters.ListFormatter`1'],[u['typeName']for u in factory['usages'][:2]]);image.check_windows(factory['windows'],label='Patrol.list.factory');image.check_instruction_windows(factory['instructions'],label='Patrol.list.factory');mapping=int_list_sources.factory_pair([(base+w['startRva'],image.window_bytes(w))for w in factory['windows']],base+factory['entryRva'],type_handle=base+factory['typeHandleRva'],add=base+factory['addRva']);need('factory-cells',[base+u['usageCellRva']for u in factory['usages']],[mapping[k]for k in('keyTypeCell','valueTypeCell','addMethodInfoCell')])
 out=dict(status='current-bounded-reference-list-components-conditional-closed-sharing-not-owner',nativeInputs=pins,entry=entry,windows=[dict(startRva=a,endRva=b,sha256=hashlib.sha256(image.pe.bytes_at_va(base+a,b-a)).hexdigest().upper())for a,b in ranges],symbols=reference['listSymbols'],context=context,listContext=list_context,programs=programs,bridges=bridges,countLimit=17,boundary='Canonical registered ListFormatter<object> reference source and owned VAR slot/type/factory joins. Typed current closed Patrol uses are independent. Runtime closed inflation/provider and selection of this exact initialized reference-sharing source/context are explicit conditions, not inferred from absence of closed rows. Children, scalar field source order, wrappers/adapters and owner admission remain separate.')
 return out



def _factories(image,pins,declarations):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
 source=declarations;out=[]
 if source['nativeInputs']!=pins:raise ValueError('native inputs differ')
 for record in source['records']:
  original,name=record['original'],record['wrapper']
  if original.endswith(('PatrolSubActionData','PatrolSubActionEnvTalkData','PatrolSubPlayAudioData')):continue
  if ctx.is_value_type(original)or ctx.field(name+'::__instance')!=(name,original,16):raise ValueError('Patrol.factory.holder-layout')
  for program in record['methods']:
   row=program['method']
   if row[1]!=name or row[2]not in('.ctor','CreateInstance'):continue
   image.validate_method_row(row,label='Patrol.factory');scalar.owned_method_abi(image,ctx,row[0],ctx.index.types[name].index,('void',1,False),[],'Patrol.factory')
   parts=program['parts'];image.check_windows(parts,label='Patrol.factory');owned=[(base+p['startRva'],base+p['endRva'])for p in parts]
   if sorted((p['runtimeTriple'][0],p['runtimeTriple'][1])for p in image.unwind_index.family(row[3])['ranges'])!=sorted((a-base,b-base)for a,b in owned):raise ValueError('Patrol.factory.ownership')
   rows=[r for p in parts for r in p['rows']]
   if any(image.pe.bytes_at_va(int(r['va'],16),len(bytes.fromhex(r['bytes'])))!=bytes.fromhex(r['bytes'])for r in rows):raise ValueError('Patrol.factory.row-bytes')
   usage,=[u for u in program['usages']if(u['tag'],u['typeName'])==(1,original)and bytes.fromhex(u['instructionHex'])[:3]==bytes.fromhex('488b0d')];validate_typed_usage_context(image,usage,label='Patrol.factory')
   at=next(i for i,r in enumerate(rows)if int(r['va'],16)==base+usage['instructionRva']);following=at+1
   if rows[following]['bytes'].replace(' ','')=='48897c2438':following+=1
   allocate=rows[following];transfer=control_transfer(allocate)
   if transfer['kind']!='call':raise ValueError('Patrol.factory.allocation-adjacency')
   selected={int(allocate['va'],16):'original'};tails={int(r['va'],16):{'target':control_transfer(r)['target']}for r in rows if control_transfer(r)['kind']=='jump'and not any(a<=control_transfer(r)['target']<b for a,b in owned)}
   flow=check_reference_origins(rows,entry=base+row[3],owned_ranges=owned,incoming_registers={'rcx':'wrapper'},incoming_stack_slots={},selected_call_returns=selected,tail_exits=tails)
   stores=[];addresses=[];constructors=[]
   for r in rows:
    state=flow['registerOrigins'][int(r['va'],16)];match=re.fullmatch(r'mov \[(rdi|rbp)\+0x10\], rbx',r['text'])
    if match:
     if state[match[1]]!=['wrapper']or state['rbx']!=['original']:raise ValueError('Patrol.factory.unchanged-original-holder')
     stores.append(r)
    match=re.fullmatch(r'lea rcx, \[(rdi|rbp)\+0x10\]',r['text'])
    if match and state[match[1]]==['wrapper']:addresses.append(r)
    t=control_transfer(r)
    if t['kind']=='call':
     candidates=[m for m in md.methods_for(ctx.index.types[original])if md.string(m.name_index)=='.ctor'and image.method_pointer_va(m)==t['target']]
     if candidates:
      m,=candidates
      if state['rcx']!=['original']:raise ValueError('Patrol.factory.original-ctor-receiver')
      scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'Patrol.factory.originalCtor');constructors.append(m.index)
   if len(stores)!=1 or len(addresses)!=1 or len(tails)!=1:raise ValueError('Patrol.factory.unique-transfer')
   out.append(dict(original=original,wrapper=name,method=row,parts=parts,allocationUsage=usage,allocationCall=allocate,originalConstructors=constructors,holderStore=stores[0],collectorAddress=addresses[0],collectorTail=next(iter(tails.values())),originProof={k:v for k,v in flow.items()if k!='registerOrigins'},condition='Matching initialized typed allocation returns actual original, normal original/default-child/context/helper/barrier calls preserve unrelated nonvolatile aliases and disjoint holder storage. Serialized fields subsequently overwrite original defaults. Current Point constructor inlines defaults, including a fresh typed action list; default-child contents are not wire grammar.'))
 return out



def _empty(image,pins,direct,declarations):
 ctx=NativeReferenceContext(image);base=image.pe.image_base;md=image.metadata;entries=GenericEntries(image)
 def need(k,e,a):
  if e!=a:raise ValueError('patrolEmpty.'+k+':'+str((e,a))[:800])
 def fail(k,e,a):raise ValueError('patrolEmpty.'+k+':'+str((e,a))[:800])
 td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];m,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize'];entry=entries.resolve(m.index,['Beyond.Blackboard+DataPair'],[]);context=ContextSymbols(image).context(td.index);lc=ContextSymbols(image).context(ctx.index.types['System.Collections.Generic.List`1'].index);validate_generic_contexts(image,[context,lc],label='PatrolEmpty');validate_list_element_context(image,context,entries,fail=fail);validate_list_formatter_base_context(image,context,entries,fail=fail);validate_capacity_constructor_context(image,context,lc,entries,fail=fail)
 slots={s['relativeSlot']:s for s in context['entries']};clear=entries.resolve(slots[2]['methodSpec'][0],['Beyond.Blackboard+DataPair'],[]);ctor=entries.resolve(slots[1]['methodSpec'][0],['Beyond.Blackboard+DataPair'],[])
 ranges=[p['runtimeTriple'][:2]for p in image.unwind_index.family(entry['pointer']-base)['ranges']];regions=[(base+a,image.pe.bytes_at_va(base+a,b-a))for a,b in ranges]
 s={k:base+v for k,v in declarations['emptySymbols'].items()};need('actual-closed-clear',clear['pointer'],s['clear'])
 # Declarations are actual owned call targets, not semantic constants inferred from size.
 ns=vars(models);offsets=scalar.reader_offsets(image,'Patrol.empty');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 paths=[ns['value32_empty'](regions,entry['pointer'],offsets,s,count=count,new=new)for count in(-1,0)for new in(False,True)]
 parent=dict(nativeInputs=pins,records=direct);need('parent-inputs',pins,parent['nativeInputs']);record=next(r for r in parent['records']if r['type']=='Beyond.Gameplay.Core.PatrolSubAction');field=next(f for f in record['fields']if f['name']=='eventBBDataPairs');u=field['typedContext'];validate_typed_usage_context(image,u,label='Patrol.empty');need('typed-parent',('MemoryPack.MemoryPackReader','ReadPackable',[],['System.Collections.Generic.List`1<Beyond.Blackboard+DataPair>']),tuple(u[k]for k in('typeName','methodName','classArguments','methodArguments')))
 need('same-closed-List-context',[a['raw_type_record_hex']for a in entry['classInstantiation']['arguments']],[a['raw_type_record_hex']for a in clear['classInstantiation']['arguments']]);need('same-closed-ctor-context',clear['classInstantiation'],ctor['classInstantiation'])
 value=ctx.index.types['Beyond.Blackboard+DataPair'];need('managed-value',True,ctx.is_value_type('Beyond.Blackboard+DataPair'));sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*value.index);need('actual-boxed-native-size',(48,32),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)))
 out=dict(status='current-DataPair-null-empty-source-conditional-not-owner',nativeInputs=pins,entry=entry,windows=[dict(startRva=a,endRva=b,sha256=hashlib.sha256(image.pe.bytes_at_va(base+a,b-a)).hexdigest().upper())for a,b in ranges],symbols={k:v-base for k,v in s.items()},context=context,listContext=lc,clear=clear,constructor=ctor,parent=field,programs=paths,boundary='Exact current closed typed List32 source null/empty paths. Initialized owned context/constructor/static-empty-array and normal indexed/allocation/Clear/provider/barrier helper conditions explicit. Empty provider result is unused; no concrete element formatter assumed. Positive DataPair elements refused; helper ABI and null/new wrappers remain separate.')
 return out



def _children(image,pins,declarations,models_module=models):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);build=Build(image,pins);offsets=scalar.reader_offsets(image,'Patrol.child');programs=[];methods=[];usages=[];proofs=[]
 def need(k,e,a):
  if e!=a:raise ValueError('Patrol.child.'+k+':'+str((e,a))[:1100])
 models=vars(models_module);shared=vars(levelscript_interactive_sources);rolling=vars(module_structure_models);pooled=vars(pooled_string_list_sources);montage=vars(montage_sources)
 def own(pointer,leaf=None):
  if leaf is None:ranges=[p['runtimeTriple'][:2]for p in image.unwind_index.family(pointer-base)['ranges']]
  else:ranges=[(pointer-base,pointer-base+leaf)]
  regions=[(base+a,image.pe.bytes_at_va(base+a,b-a))for a,b in ranges];rows=[r for a,raw in regions for r in image.body_index._decode(a,len(raw))];programs.append(dict(entryRva=pointer-base,leafBytes=leaf,windows=[dict(startRva=a,endRva=b,sha256=hashlib.sha256(image.pe.bytes_at_va(base+a,b-a)).hexdigest().upper())for a,b in ranges]));return regions,rows
 def method(owner,name):
  m,=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name];p=image.method_pointer_va(m);methods.append([m.index,owner,name,p-base]);return m,p
 def calls(rows):return[int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)for r in rows if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 def usage(at,expected):
  u=derive_typed_usage_context(image,at-base,label='Patrol.child');need('typed-context',expected,(u['typeName'],u.get('methodName'),u.get('classArguments',[]),u.get('methodArguments',[])));usages.append(u);return u
 compositions=declarations['static'];need('composition-inputs',pins,compositions['nativeInputs']);adapter=declarations['adapters'];need('adapter-inputs',pins,adapter['nativeInputs']);adapter_proof=validate_reference_routes(image,adapter['referenceRoutes'],adapter['compositions']);sadapter={k:base+v for k,v in adapter['referenceRoutes']['symbolRvas'].items()}
 base_original='Beyond.Gameplay.Core.PatrolSubActionData';base_wrapper=next(w.name for w in build.wrappers.values()if w.wrapped_type==base_original);fmt=base_wrapper+'+'+base_wrapper.rsplit('.',1)[-1]+'Formatter';_,p=method(fmt,'Deserialize');re,rs=own(p);cs=calls(rs);s=dict(header=cs[0],assignable=cs[1],packable=cs[4],barrier=cs[5]);need('union-same-assignable',cs[1],cs[3]);need('union-same-packable',cs[4],cs[6]);need('union-same-barrier',cs[5],cs[7]);union=read_union_switch(image,base_wrapper.rsplit('.',1)[-1],wrappers={w.type_definition:w for w in build.wrappers.values()});need('union-tag-set',[0,1],[r['tag']for r in union['entries']]);children={r['tag']:r['wrapperName']for r in union['entries']};need('union-children',['PatrolSubActionEnvTalkDataForMemoryPack','PatrolSubPlayAudioDataForMemoryPack'],[children[i].rsplit('_',1)[-1]for i in(0,1)])
 for tag,existing in((-1,False),(0,False),(0,True),(1,False),(1,True)):
  proof=models['union'](re,p,s,tag=tag,existing=existing);proofs.append(dict(role='union',proof=proof))
  if proof['childUsage']:usage(proof['childUsage']['site'],('MemoryPack.MemoryPackReader','ReadPackable',[],[children[tag]]));build.prove_reader_clone_target(s['packable'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
  if proof['comparisonUsage']:usage(proof['comparisonUsage']['site'],(children[tag],None,[],[]))
 hr,_=own(s['header'])
 for marker in('short','false'):proofs.append(dict(role='unionHeader',proof=rolling['enclosing_header'](hr,s['header'],offsets,marker=marker)))
 # The base wrapper's empty factory is exact, while its actual slot5 is the union itself.
 base_comp,=[c for c in compositions['records']if c['registrations'][0]['originalType']==base_original];validate_registered_formatter_composition(image,base_comp,label='Patrol.base');_,gp=method(base_wrapper,'GetValue');need('base-reference-getter',bytes.fromhex('488b4110c3'),image.pe.bytes_at_va(gp,5));conversion_regions,_=own(sadapter['conversion']);dispatch_regions,_=own(sadapter['dispatch']);section=md.sections['interfaceOffsets'];td=ctx.index.types[base_wrapper];at=section.offset+td.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8]));interface=base_comp['interfaces'][0];ordinal=pairs.index((interface['interfaceTypeIndex'],interface['interfaceOffset']));proofs.append(dict(role='baseConversion',proof=conversion(conversion_regions,sadapter['conversion'],base+adapter['referenceRoutes']['conversionPrepareRva'],gp,ordinal=ordinal)));proofs.append(dict(role='baseUnionDispatch',proof=deserialize_slot(dispatch_regions,sadapter['dispatch'],prepare=sadapter['prepare'],callback=p)))
 for name in('.ctor','CreateInstance'):
  m,entry=method(base_wrapper,name);scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'Patrol.baseFactory');need('empty-base-factory',bytes.fromhex('c20000'),image.pe.bytes_at_va(entry,3));proofs.append(dict(role='baseFactory',entryRva=entry-base,bytes='C20000',noHolderOrWireEffects=True))
 child_facts=[]
 for tag,name in children.items():
  w=build.wrappers[name];original=w.wrapped_type;audio=tag==1;m,entry=method(name,'Deserialize');primitive_param.reader_abi(image,ctx,m,w);re,rs=own(entry);cs=calls(rs);ctor,cp=method(name,'.ctor');first=next(i for i,t in enumerate(cs)if t==cp);need('new-child-call-index',2,first);read_targets=cs[first+2:first+2+(2 if audio else 6):2];setter_targets=cs[first+3:first+3+(2 if audio else 6):2];sym=dict(header=cs[0],allocate=cs[1],ctor=cp,barrier=cs[3],reads=read_targets,setters=setter_targets);proof=models['child'](re,entry,sym,audio=audio);proofs.append(dict(role='childRecord',original=original,proof=proof));usage(proof['allocationUsage']['site'],(name,None,[],[]));primitive_param.object_header_source(image,vector_recorder(image,lanes=True)(sym['header']-base),offsets)
  getter,gp=method(name,'get___instance');scalar.owned_method_abi(image,ctx,getter.index,getter.declaring_type,(original,18,True),[],'Patrol.childGetter');gr,gs=own(gp);gc=calls(gs);need('getter-cast-repeat',gc[-3],gc[-2]);getter_s=dict(cast=gc[-3],barrier=gc[-1]);need('same-barrier',sym['barrier'],getter_s['barrier']);cache=[]
  for mode in('empty','different','coherent'):
   result=models['cached'](gr,gp,getter_s,mode=mode);cache.append(result)
   for u in result['classUsages']:usage(u['site'],(original,None,[],[]))
  cr,csrows=own(getter_s['cast']);cc=calls(csrows);need('one-compatible-predicate',1,len(cc));casts=[pooled['compatible_list_cast'](cr,getter_s['cast'],cc[0],null=n)for n in(False,True)]
  scalar.ordinary(image,ctx.type_pointer(getter.return_type),18,'Patrol.original',reference=True);need('derived-original-parent',base_original,ctx.parent(original));need('derived-wrapper-parent',base_wrapper,ctx.parent(name));need('cache-layout',(name,original,24),ctx.field(name+'::__realInstance'));need('base-layout',(base_wrapper,base_original,16),ctx.field(base_wrapper+'::___instance'))
  for member,target,read in zip(w.members,setter_targets,read_targets,strict=True):
   fm=md.methods[member.method_index];need('actual-setter-method',image.method_pointer_va(fm),target);field=ctx.field(original+'::'+member.name);sr,srows=own(target)
   if audio:
    u,=proof['typedReads'];usage(u['site'],('MemoryPack.MemoryPackReader','ReadUnmanaged',[],['Beyond.Audio.AudioId']));vt=ctx.index.types['Beyond.Audio.AudioId'];need('AudioId-owned-field',('Beyond.Audio.AudioId','int',16),ctx.field('Beyond.Audio.AudioId::_id'));need('AudioId-value',True,ctx.is_value_type('Beyond.Audio.AudioId'));vfields=[f for f in md.fields_for(vt)if not ctx.field_attributes(f.type_index)&16];need('AudioId-one-field',1,len(vfields));sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*vt.index);need('AudioId-boxed-native',(20,4),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)));montage['unmanaged4'](image,vector_recorder(image)(read-base),offsets);scalar.owned_method_abi(image,ctx,fm.index,fm.declaring_type,('void',1,False),[('Beyond.Audio.AudioId',17,False)],'Patrol.AudioIdSetter');sp=models['scalar_setter'](sr,target,gp,slot=field[2])
   elif member.declared_type=='bool':scalar.boolean_source(image,vector_recorder(image)(read-base),offsets,'Patrol.childBool');sp=models['scalar_setter'](sr,target,gp,slot=field[2],boolean=True)
   else:build.prove_pooled_string_target(read);sp=models['reference_setter'](sr,target,gp,sym['barrier'],slot=field[2])
   proofs.append(dict(role='childSetter',original=original,field=member.name,proof=sp))
  # Actual ctor/CreateInstance directly zero-allocate the derived original and join both holders.
  factory_proofs=[]
  for role in('.ctor','CreateInstance'):
   fm,fp=method(name,role);fr,fs=own(fp);fc=calls(fs);sfo=dict(allocate=fc[0],baseSetter=fc[1],strictCast=fc[2],barrier=sym['barrier'])if role=='.ctor'else factory_symbols
   if role=='.ctor':need('factory-repeat-strict-cast',fc[2],fc[3]);factory_symbols=sfo
   result=models['child_factory'](fr,fp,sfo,ctor=role=='.ctor');usage(result['allocationUsage']['site'],(original,None,[],[]));factory_proofs.append(result)
   base_set=next(m for m in md.methods_for(ctx.index.types[name])if md.string(m.name_index)=='set___instance');need('actual-typed-base-setter',image.method_pointer_va(base_set),sfo['baseSetter']);br,_=own(sfo['baseSetter']);proofs.append(dict(role='dualHolderSetter',proof=shared['base_setter_program'](br,sfo['baseSetter'],sym['barrier'])));rr,rrows=own(sfo['strictCast']);rc=calls(rrows);need('same-strict-and-union-predicate',s['assignable'],rc[0]);proofs.append(dict(role='strictTypedCast',proof=rolling['rolling_owned_strict_cast'](rr,sfo['strictCast'],rc[0])))
  barrier_regions,_=own(sym['barrier'],leaf=66);proofs.append(dict(role='disabledCollector',proof=shared['collector_disabled_program'](barrier_regions,sym['barrier'])))
  _,valuep=method(name,'GetValue');vr,_=own(valuep,leaf=7);vg=BytesPath(vr,valuep);vg.take('33d2');need('GetValue-cached-getter',gp,vg.relative('e9'));child_facts.append(dict(original=original,wrapper=name,sourceSymbols={k:([v-base for v in val]if isinstance(val,list)else val-base)for k,val in sym.items()},cacheProofs=cache,castProofs=casts,factoryProofs=factory_proofs))
 return dict(programs=programs,methods=methods,usages=usages,union=union,unionSymbols={k:v-base for k,v in s.items()},adapterProof=adapter_proof,children=child_facts,proofs=proofs)



def _joins(image,pins,declarations,lists):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);out=[];programs=[]
 def need(k,e,a):
  if e!=a:raise ValueError('Patrol.joins.'+k+':'+str((e,a))[:800])
 def fail(k,e,a):raise ValueError('Patrol.joins.'+k+':'+str((e,a))[:800])
 def own(pointer):
  ranges=[p['runtimeTriple'][:2]for p in image.unwind_index.family(pointer-base)['ranges']];regions=[(base+a,image.pe.bytes_at_va(base+a,b-a))for a,b in ranges];programs.append(dict(entryRva=pointer-base,windows=[dict(startRva=a,endRva=b,sha256=hashlib.sha256(image.pe.bytes_at_va(base+a,b-a)).hexdigest().upper())for a,b in ranges]));return regions,[r for a,raw in regions for r in image.body_index._decode(a,len(raw))]
 def calls(rs):return[int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)for r in rs if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 adapters=declarations['adapters'];need('adapter-inputs',pins,adapters['nativeInputs']);comp=declarations['static'];need('composition-inputs',pins,comp['nativeInputs']);s={k:base+v for k,v in adapters['referenceRoutes']['symbolRvas'].items()};dr,_=own(s['dispatch']);forwarders=[]
 for composition in comp['records']:
  reg,=composition['registrations'];name=reg['wrapperType']
  if not reg['originalType'].endswith(('PatrolSubActionEnvTalkData','PatrolSubPlayAudioData')):continue
  validate_registered_formatter_composition(image,composition,label='Patrol.childSlot');join,=composition['interfaces'];forward=md.methods[join['formatterDeserializeMethodIndex']];target=image.method_pointer_va(forward);fr,fs=own(target);methods={md.string(m.name_index):m for m in md.methods_for(ctx.index.types[name])};reader=methods['Deserialize'];rp=image.method_pointer_va(reader);fc=calls(fs);init={calls(fs[i:i+1])[0]for i,r in enumerate(fs)if r['text'].startswith('call ')and fs[i-1]['text'].startswith('lea rcx, [rip')};other={c for c in fc if c not in init}
  need('forwarder-init-helper-count',1,len(init));need('forwarder-class-helper-count',1,len(other));symbols=dict(metadataInit=next(iter(init)),classInit=next(iter(other)));proof=prove_zero_wrapper_forwarder(fs,symbols,rp);dispatch=deserialize_slot(dr,s['dispatch'],prepare=s['prepare'],callback=target);forwarders.append(dict(original=reg['originalType'],wrapper=name,forwarder=[forward.index,image.type_name(forward.declaring_type),'Deserialize',target-base],reader=[reader.index,name,'Deserialize',rp-base],symbols={k:v-base for k,v in symbols.items()},forwarderProof=proof,dispatchProof=dispatch))
 # Every current enum read by the bounded records is an actual Int32-backed enum.
 defaults=field_defaults(md);enums=[]
 for name in('Beyond.Gameplay.AI.Config.NpcPatrolData','Beyond.Gameplay.AI.Config.NpcPatrolPoint','Beyond.Gameplay.Core.PatrolSubAction'):
  w=next(w for w in image.memorypack_wrappers.values()if w.wrapped_type==name)
  for member in w.members:
   if member.kind!='enum':continue
   enum=member.declared_type;need('enum-kind',True,ctx.is_enum(enum));need('enum-owned-backing',(enum,'int',16),ctx.field(enum+'::value__'));values=native_enum_members(md,defaults,image.pe,image.registration,enum);enums.append(dict(parent=name,field=member.name,type=enum,backing=ctx.field(enum+'::value__'),members=values))
 # This source helper is generic in its own MVAR, not a width-based LangKey alias.
 ns=dict(wrapper_provider_program=lang_key_list_sources.wrapper_provider_program)
 list_fact=lists;need('list-inputs',pins,list_fact['nativeInputs']);context=list_fact['context'];validate_generic_contexts(image,[context],label='Patrol.list');typed=validate_list_element_context(image,context,entries,fail=fail);slots={x['relativeSlot']:x for x in context['entries']};provider=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[provider],label='Patrol.listProvider');ps={x['relativeSlot']:x for x in provider['entries']};need('provider-own-slots',[0,1],sorted(ps));need('provider-own-type',provider['definition'],ps[0]['type']['parameterOwner']['methodIndex']);need('provider-own-formatter-type',provider['definition'],ps[1]['type']['classArguments'][0]['parameterOwner']['methodIndex'])
 fact_path=CONTRACTS_DIR/'levelscript_int_list_native.json';fact_raw=fact_path.read_bytes();fact=json.loads(fact_raw);need('generic-inputs',pins,fact['nativeInputs']);c={k:base+v for k,v in fact['calls'].items()};symbols={k:base+v for k,v in declarations['referenceProviderSymbols'].items()};need('actual-Type-key-backend',c['backend'],symbols['backend']);need('actual-context-helper',c['resolveClass'],symbols['context']);need('actual-assignable-helper',c['assignable'],symbols['assignable']);p=base+list_fact['symbols']['provider'];pr,rs=own(p);proof=ns['wrapper_provider_program'](pr,p,symbols);proof['boundary']='Actual current initialized generic own-MVAR GetFormatter source. Actual first-probe class-to-RuntimeType cache/backend/assignability/context results coherent with exact supplied element VAR; unchanged compatible result. No concrete row/default/live selection inference from absence, and no runtime wire width assumption.'
 backend=fact['bodies']['providerBackend'];image.check_windows(backend['windows'],label='Patrol.listBackend');br=[(base+w['startRva'],image.window_bytes(w))for w in backend['windows']];backend_proof=int_list_sources.backend(br,c['backend'],{k:c[k]for k in('resolveClass','hash','equals')});validate_typed_usage_context(image,fact['backendContext'],label='Patrol.listBackend');u=fact['backendContext'];need('typed-Type-key-dictionary',('System.Collections.Concurrent.ConcurrentDictionary`2','TryGetValue',['System.Type','MemoryPack.IMemoryPackFormatter'],[]),tuple(u[k]for k in('typeName','methodName','classArguments','methodArguments')));need('same-backend-method-cell',base+u['usageCellRva'],backend_proof['methodInfoCell']);need('same-provider-class',proof['providerClassCell'],backend_proof['providerClassCell']);resolver=fact['bodies']['contextResolver'];image.check_windows(resolver['windows'],label='Patrol.listContext');resolve=int_list_sources.initialized_class([(base+w['startRva'],image.window_bytes(w))for w in resolver['windows']],c['resolveClass'],indexed=True)
 return dict(programs=programs,forwarders=forwarders,enums=enums,typedListContext=typed,providerContext=provider,providerSymbols={k:v-base for k,v in symbols.items()},providerSource=proof,backend=backend,backendContext=u,backendProof=backend_proof,contextResolver=resolver,contextResolverProof=resolve)


def derive(image,contract):
 pins=contract['nativeInputs'];declarations=contract['declarations']
 required={'Beyond.Gameplay.AI.Config.NpcPatrolData','Beyond.Gameplay.AI.Config.NpcPatrolPoint','Beyond.Gameplay.Core.PatrolSubAction','Beyond.Gameplay.Core.PatrolSubActionData','Beyond.Gameplay.Core.PatrolSubActionEnvTalkData','Beyond.Gameplay.Core.PatrolSubPlayAudioData'}
 eager=declarations['eager']['results'];pairs={r['originalType']:r['wrapperType']for r in eager};compositions=declarations['static']['records'];registered={r['originalType']:r['wrapperType']for c in compositions for r in c['registrations']}
 if len(eager)!=len(required)or set(pairs)!=required or len(compositions)!=len(required)or registered!=pairs:raise ValueError('Patrol.registration:complete-family-bijection')
 simple=required-{'Beyond.Gameplay.Core.PatrolSubActionData','Beyond.Gameplay.Core.PatrolSubActionEnvTalkData','Beyond.Gameplay.Core.PatrolSubPlayAudioData'};adapter=declarations['adapters'];rows=adapter['referenceRoutes']['wrappers']
 if len(rows)!=len(simple)or{r['original']for r in rows}!=simple or{c['registrations'][0]['originalType']for c in adapter['compositions']}!=simple:raise ValueError('Patrol.reference-adapter:complete-simple-family')

 for flow in declarations['eager']['results']:validate_eager_wrap_registration(image,flow,label='Patrol.eager')
 for fact in declarations['static']['records']:validate_registered_formatter_composition(image,fact,label='Patrol.static')
 direct=_direct(image,pins);point=_point(image,pins);lists=_lists(image,pins,direct,point)
 factories=_factories(image,pins,declarations['construction'])
 if len(factories)!=2*len(simple)or{(r['original'],r['method'][2])for r in factories}!={(name,method)for name in simple for method in('.ctor','CreateInstance')}:raise ValueError('Patrol.factory:complete-simple-family')
 return json.loads(json.dumps(dict(direct=direct,point=point,lists=lists,factories=factories,emptyList=_empty(image,pins,direct,declarations),children=_children(image,pins,declarations),joins=_joins(image,pins,declarations,lists))))


def validate_on_image(image,contract):
 actual=derive(image,contract)
 if actual!=contract['proof']:raise ValueError('Patrol.native:reviewed-source-composition-differs')
 return actual
