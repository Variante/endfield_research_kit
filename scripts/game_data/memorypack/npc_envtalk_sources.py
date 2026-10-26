"""Exact selected current generated three-field reference record; children separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def source(regions,entry,offsets,symbols,fields,*,null=False,new=False):
 if len(fields)!=3:raise ValueError('EnvTalk.source-field-count')
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=g.relative('803d');g.take('00','488bfa','488bd9');g.branch('0f84',False)
 rem,cur,adv,used=(bytes((offsets[n],)).hex()for n in('bufferLength','currentPtr','advancedCount','consumed'))
 g.take('837b'+rem+'01');g.branch('0f8c',False);g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
 g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',null)
 usages=[];stores=[]
 if null:
  g.take('488bcf','48c70700000000');g.call(symbols['barrier']);g.jump('eb',1)
 else:
  g.take('48833f00');g.branch('0f84',new)
  if new:
   cell=g.relative('488b0d');g.call(symbols['allocateWrapper']);g.take('488be8','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(symbols['wrapperCtor']);g.take('488bcf','48892f');g.call(symbols['barrier']);g.take('90');g.jump('e9')
  else:cell=None
  g.take('4080fe03');g.branch('0f85',False)
  for index,field in enumerate(fields):
   if index<2:
    usages.append(g.relative('488b15'));g.take('488bcb','488b37');g.call(field['target']);g.take('4885f6');g.branch('0f84'if index==0 else'74',False,4 if index==0 else 1);g.take('488b4e10','4885c9');g.branch('74',False,1)
    stores.append(g.at);slot=bytes((field['offset'],)).hex();g.take('488941'+slot,'4883c1'+slot);g.call(symbols['barrier'])
   else:
    g.take('488b3f','488bcb');g.call(field['target']);g.take('4885ff');g.branch('74',False,1);g.take('488b4f10','4885c9');g.branch('74',False,1);stores.append(g.at);g.take('8841'+bytes((field['offset'],)).hex())
 g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,null=null,newHolder=new,wireHeaderBytes=1,memberCount=3,reader='entry RCX preserved RBX',holder='entry RDX preserved RDI',originalHolderOffset=16,typedContextCells=usages,fieldStoreSites=stores,initializedFlagCell=ready,wrapperTypeCell=cell if not null else None,normalReturn=True,childrenIndependentlyRequired=True,condition='Current initialized type data; buffered disjoint Reader/holder/output; selected FF or exact MC3; nonnull wrapper original; normal exact allocation/constructor and disabled-collector helpers; child readers separately gated. No live provider selection or owner admission.')


from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def construct(regions,entry,allocate,barrier,*,create=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d');g.take('00','488bd9');g.branch('75'if create else'74',create,1);load=g.at;cell=g.relative('488b0d');g.call(allocate);g.take('4885c0');g.branch('75'if create else'74',create,1);g.take('c6402001','488d4b10','48894310','4883c420','5b')
 if g.relative('e9')!=barrier:raise ValueError('npcEnvTalk.constructor-barrier')
 return dict(selectedBytes=g.seen,allocationUsageSite=load,allocationTypeCell=cell,defaultBooleanFieldOffset=32,defaultBooleanValue=True,holderOffset=16,normalReturn=True,condition='Initialized matching metadata; fresh correctly typed original allocation returns nonnull normally; disabled collector. All three MC3 fields overwrite original defaults. No runtime execution/provider choice is proved.')

import struct
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,validate_registered_formatter_composition,derive_typed_usage_context,_vtable
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.context import method_parameter_owner
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier
from scripts.game_data.memorypack.reference_adapter_sources import validate_reference_routes
from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
from scripts.game_data.memorypack import scalar_param_native as scalar,npc_array_sources as arrays
from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive


def validate(image,pins,fact,string_fact,copy_fact):
 """Fresh child proof inside its selected owning NPC operation; no opener/cache."""
 def need(k,e,a):
  if e!=a:raise ValueError('npcEnvTalk.'+k+':expected='+str(e)[:240]+':actual='+str(a)[:240])
 def fail(k,e,a):need(k,e,a)
 need('schema','endfield.npc-envtalk-source-component.v1',fact['schema']);need('selected-native',pins,fact['nativeInputs']);need('string-native',pins,string_fact['nativeInputs'])
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);regions={}
 for p in fact['programs']:
  if not p.get('leafBytes'):need('complete-'+p['role'],sorted(tuple(z['runtimeTriple'][:2])for z in image.unwind_index.family(p['entryRva'])['ranges']),sorted((w['startRva'],w['endRva'])for w in p['windows']))
  else:need('bounded-barrier-prefix',('barrier',66), (p['role'],p['leafBytes']))
  image.check_windows(p['windows'],label='npcEnvTalk');regions[p['role']]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in p['windows']]
 programs={p['role']:p for p in fact['programs']}
 def args(role):return regions[role],base+programs[role]['entryRva']
 original=fact['typeName'];wrapper=fact['wrapperName'];build=Build(image,pins);w=build.wrappers[wrapper]
 need('ordinary-child',False,ctx.is_value_type(original));need('wrapper-original',original,w.wrapped_type);need('exact-current-members',[('envTalkIds','string[]'),('envTalkOdd','int[]'),('envTalkOverrideNpc','bool')],[(m.name,m.declared_type)for m in w.members]);need('holder',(wrapper,original,16),ctx.field(wrapper+'::__instance'))
 for f in fact['fields']:need('original-'+f['field'],(original,f['type'],f['offset']),ctx.field(original+'::'+f['field']))
 for method in fact['methods']:image.validate_method_row(method,label='npcEnvTalk')
 methods={md.string(m.name_index):m for m in md.methods_for(ctx.index.types[wrapper])}
 for name,role in(('Deserialize','source'),('.ctor','constructor'),('CreateInstance','create')):need('method-'+name,base+programs[role]['entryRva'],image.method_pointer_va(methods[name]))
 for name in('.ctor','CreateInstance'):scalar.owned_method_abi(image,ctx,methods[name].index,methods[name].declaring_type,('void',1,False),[],'npcEnvTalk.factory')
 parent=fact['parent'];need('parent-field',tuple(parent['ownedField']),ctx.field(parent['typeName']+'::'+parent['field']));need('parent-child',original,parent['ownedField'][1]);u=parent['source']['typedContext'];validate_typed_usage_context(image,u,label='npcEnvTalk.parent');need('parent-typed-call',('MemoryPack.MemoryPackReader','ReadValue',[original]),(u['typeName'],u['methodName'],u['methodArguments']));build.prove_reader_clone_target(base+parent['source']['targetRva'],'MemoryPack.MemoryPackReader.ReadValue',result_abi='reference');call=base+parent['source']['callRva'];raw=image.pe.bytes_at_va(call,5);need('parent-actual-call-opcode',232,raw[0]);need('parent-actual-call-target',base+parent['source']['targetRva'],call+5+int.from_bytes(raw[1:],'little',signed=True));parent_method=next(m for m in md.methods_for(ctx.index.types[parent['wrapperName']])if md.string(m.name_index)=='Deserialize');ranges=image.unwind_index.family(image.method_pointer_va(parent_method)-base)['ranges'];need('parent-call-owned',True,any(base+r['runtimeTriple'][0]<=call<call+5<=base+r['runtimeTriple'][1]for r in ranges))
 offsets=scalar.reader_offsets(image,'npcEnvTalk');field_plans=[dict(f,target=base+f['targetRva'])for f in fact['fields']];symbols={k:base+v for k,v in fact['symbols'].items()};paths=[source(*args('source'),offsets,symbols,field_plans,**mode)for mode in(dict(null=True),dict(new=False),dict(new=True))]
 for u in fact['contexts']:validate_typed_usage_context(image,u,label='npcEnvTalk.array')
 for path in paths[1:]:need('same-array-context-cells',[base+u['usageCellRva']for u in fact['contexts']],path['typedContextCells'])
 allocation_cell=paths[2]['wrapperTypeCell'];allocation_rows=[r for at,raw in regions['source']for r in decode_type_data_initialization_instructions(image.mapper,raw,at)if bytes.fromhex(r['bytes'])[:3]==bytes.fromhex('488b0d')and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==allocation_cell]
 allocation_row,=allocation_rows;au=derive_typed_usage_context(image,int(allocation_row['va'],16)-base,label='npcEnvTalk.wrapperAllocation');need('typed-new-wrapper',(1,wrapper),(au['tag'],au['typeName']))
 bool_field,=[f for f in field_plans if f['type']=='bool'];prove_primitive(image,bool_field['target'],'bool-byte')
 barrier=validate_fast_reference_barrier(image,fact['barrier'],fail=fail);need('same-barrier',symbols['barrier']-base,barrier['entryRva'])
 constructors=[]
 for role in('constructor','create'):
  f=fact['construction'][role];validate_typed_usage_context(image,f['allocationUsage'],label='npcEnvTalk.constructor');need('original-allocation',(1,original),(f['allocationUsage']['tag'],f['allocationUsage']['typeName']));p=construct(*args(role),base+f['allocationTargetRva'],symbols['barrier'],create=role=='create');need('allocation-cell',base+f['allocationUsage']['usageCellRva'],p['allocationTypeCell']);need('allocation-site',base+f['allocationUsage']['instructionRva'],p['allocationUsageSite']);constructors.append(p)
 need('source-constructor',image.method_pointer_va(methods['.ctor']),symbols['wrapperCtor']);need('original-bool-default',(original,'bool',32),ctx.field(original+'::envTalkOverrideNpc'))
 eager_type=ctx.index.types['Beyond.MemoryPack.MemoryPackGeneratedInit_Gameplay_Beyond'];init,=[m for m in md.methods_for(eager_type)if md.string(m.name_index)=='InitEager'];ranges=image.unwind_index.family(image.method_pointer_va(init)-base)['ranges'];need('eager-selected-block-owned',True,any(p['runtimeTriple'][0]<=fact['eager']['window']['startRva']<fact['eager']['window']['endRva']<=p['runtimeTriple'][1]for p in ranges))
 validate_eager_wrap_registration(image,fact['eager'],label='npcEnvTalk.eager');validate_registered_formatter_composition(image,fact['composition'],label='npcEnvTalk.static');reference=validate_reference_routes(image,fact['referenceRoutes'],[fact['composition']])
 sf=fact['stringArray'];validate_generic_contexts(image,sf['contexts'],label='npcEnvTalk.array');u=sf['usage'];need('actual-string-usage',fact['contexts'][0],u);fd,=[f for f in md.fields_for(ctx.index.types[original])if md.string(f.name_index)=='envTalkIds'];raw=image.pe.bytes_at_va(ctx.type_pointer(fd.type_index),16);need('owned-string-array',(29,0),(raw[10],raw[11]));element=int.from_bytes(raw[:8],'little');formatter=md.methods[sf['contexts'][1]['entries'][5]['methodSpec'][0]];typed=validate_read_array_context(image,sf['contexts'],u,entries,element,formatter.index,fail=fail)
 need('formatter-declaration',('MemoryPack.MemoryPackFormatter`1','Deserialize',5,False,2,'void'),(image.type_name(formatter.declaring_type),md.string(formatter.name_index),formatter.slot,bool(formatter.flags&16),formatter.parameter_count,ctx.type_name(formatter.return_type)));need('abstract-generic-formatter',0x440,formatter.flags&0x440);owner=md.types[formatter.declaring_type];section=md.sections['vtableMethods'];slot=section.offset+4*(owner.vtable_start+5);need('abstract-slot-placeholder',1,struct.unpack_from('<I',md.buf,slot)[0])
 for parameter,kind in zip(md.parameters_for(formatter),(17,19),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16);need('formatter-byref',(kind,32),(raw[10],raw[11]))
 need('string-actual-source',programs['stringArray']['entryRva'],fact['fields'][0]['targetRva']);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16;strings=[arrays.string_array(*args('stringArray'),offsets,{k:base+v for k,v in sf['symbols'].items()},count=n)for n in range(-1,6)];callback=validate_string_components(image,string_fact)
 ints=validate_int_array(image,ctx,entries,fact,regions,programs,offsets,copy_fact)
 return dict(childMembers=3,selectedObjectPaths=len(paths),selectedStringArrayPaths=len(strings),selectedIntArrayPaths=ints['selectedPaths'],reference=reference,stringCallback=callback,wholeOwnerAdmitted=False,liveProviderSelectionProved=False,condition='Current matched initialized generated-route selection and ordinary normal helpers, disabled collector, valid disjoint buffered Reader/outputs. Signed arrays -1/0/1..5 only; positive string callbacks require current pooled-string formatter provider selection. Parent NPC admission and live runtime inflation/default choice remain separate.')


from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.il2cpp.bounded_copy_sources import prove_bounded_copy
from scripts.game_data.il2cpp.memory_moves import decode_memory_move_instructions

def validate_int_array(image,ctx,entries,fact,regions,programs,offsets,copy_fact):
 base=image.pe.image_base;md=image.metadata;f=fact['intArray'];contexts=f['contexts'];u=f['usage']
 def need(k,e,a):
  if e!=a:raise ValueError('npcIntArray.'+k+':expected='+str(e)[:220]+':actual='+str(a)[:220])
 def args(role):return regions[role],base+programs[role]['entryRva']
 validate_generic_contexts(image,contexts,label='npcIntArray');validate_typed_usage_context(image,u,label='npcIntArray');need('actual-usage',fact['contexts'][1],u);need('typed-reader',('MemoryPack.MemoryPackReader','ReadUnmanagedArray',[],['int']),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']))
 fd,=[z for z in md.fields_for(ctx.index.types[fact['typeName']])if md.string(z.name_index)=='envTalkOdd'];raw=image.pe.bytes_at_va(ctx.type_pointer(fd.type_index),16);need('original-array-kind',(29,0),(raw[10],raw[11]));element=int.from_bytes(raw[:8],'little');scalar.ordinary(image,element,8,'npcIntArray.element');arguments=image.instantiations.resolve(u['methodSpec'][2]).arguments;need('closed-original-element',[element],[a.type_pointer_va for a in arguments])
 named={c['methodName']:c for c in contexts if c['isMethod']};first=named['ReadUnmanagedArray'];danger=named['DangerousReadUnmanagedArray'];need('first-definition',u['methodSpec'][0],first['definition']);need('first-nested',danger['definition'],first['entries'][0]['methodSpec'][0]);need('danger-slots',[0,1,2],[e['relativeSlot']for e in danger['entries']]);need('nested-method-names',['Empty','AllocateUninitializedArray','GetArrayDataReference'],[e['methodName']for e in danger['entries']])
 section=md.sections['genericContainers'];containers=[m.generic_container_index for m in md.methods]
 def variable(row):
  m=md.methods[row['definition']];at=section.offset+m.generic_container_index*16
  if m.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:raise ValueError('npcIntArray.generic-container')
  owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at);identity=method_parameter_owner(md.buf,start,containers,source='npcIntArray');need('reciprocal-method-parameter',(m.index,1,1,m.index,0),(owner,count,is_method,identity['methodIndex'],identity['ordinal']));return m,start
 def array_type(index,var):
  r=image.pe.bytes_at_va(ctx.type_pointer(index),16);need('return-SZARRAY',(29,0),(r[10],r[11]));v=image.pe.bytes_at_va(int.from_bytes(r[:8],'little'),16);need('same-owned-MVAR',(var,30,0),(int.from_bytes(v[:8],'little'),v[10],v[11]))
 for row in(first,danger):
  m,var=variable(row);need('instance-no-explicit-parameters',(False,0),(bool(m.flags&16),m.parameter_count));array_type(m.return_type,var)
 dm,dvar=variable(danger)
 for slot,row in enumerate(danger['entries']):
  method_args=image.instantiations.resolve(row['methodSpec'][2]).arguments;need('nested-arity',1,len(method_args));v=image.pe.bytes_at_va(method_args[0].type_pointer_va,16);need('nested-own-MVAR',(dvar,30,0),(int.from_bytes(v[:8],'little'),v[10],v[11]));need('nested-method-owner',row['methodSpec'][0],named[row['methodName']]['definition'])
 for name in('Empty','AllocateUninitializedArray'):
  row=named[name];m,var=variable(row);need('static-helper',True,bool(m.flags&16));array_type(m.return_type,var)
 empty=named['Empty'];need('Empty-arity',0,md.methods[empty['definition']].parameter_count);alloc=named['AllocateUninitializedArray'];am=md.methods[alloc['definition']];need('allocation-arguments',['int','bool'],[ctx.type_name(p.type_index)for p in md.parameters_for(am)])
 for p,kind in zip(md.parameters_for(am),(8,2),strict=True):scalar.ordinary(image,ctx.type_pointer(p.type_index),kind,'npcIntArray.allocateArg')
 data=named['GetArrayDataReference'];dm,dv=variable(data);dp,=md.parameters_for(dm);need('data-reference-static',True,bool(dm.flags&16));array_type(dp.type_index,dv);r=image.pe.bytes_at_va(ctx.type_pointer(dm.return_type),16);need('data-reference-result',(dv,30,32),(int.from_bytes(r[:8],'little'),r[10],r[11]))
 aspan=named['AsSpan'];asm,asvar=variable(aspan);asp,=md.parameters_for(asm);array_type(asp.type_index,asvar);need('AsSpan-static',True,bool(asm.flags&16));need('AsSpan-ctor-slot',(1,'System.Span`1','.ctor'),(aspan['entries'][1]['relativeSlot'],aspan['entries'][1]['typeName'],aspan['entries'][1]['methodName']));spanctor=md.methods[aspan['entries'][1]['methodSpec'][0]];need('SpanCtor-signature',('System.Span`1','.ctor',False,1,'void'),(image.type_name(spanctor.declaring_type),md.string(spanctor.name_index),bool(spanctor.flags&16),spanctor.parameter_count,ctx.type_name(spanctor.return_type)))

 def own_argument(spec,var):
  args=image.instantiations.resolve(spec).arguments;need('one-own-type-argument',1,len(args));r=image.pe.bytes_at_va(args[0].type_pointer_va,16);need('same-own-type-argument',(var,30,0),(int.from_bytes(r[:8],'little'),r[10],r[11]))
 _,firstvar=variable(first);own_argument(first['entries'][0]['methodSpec'][2],firstvar);own_argument(data['entries'][0]['methodSpec'][2],dv);own_argument(aspan['entries'][1]['methodSpec'][1],asvar)
 sr=image.pe.bytes_at_va(ctx.type_pointer(asm.return_type),16);need('AsSpan-return-generic-value',(21,128),(sr[10],sr[11]));definition,inst=struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(sr[:8],'little'),16));dr=image.pe.bytes_at_va(definition,16);need('AsSpan-return-Span',(ctx.index.types['System.Span`1'].index,17),(int.from_bytes(dr[:8],'little'),dr[10]));own_argument(image.instantiations.resolve_pointer(inst).index,asvar)
 span=ctx.index.types['System.Span`1'];need('Span-value-type',True,ctx.is_value_type('System.Span`1'));owner,count,ismethod,spanvar=struct.unpack_from('<iiii',md.buf,section.offset+span.generic_container_index*16);need('Span-one-class-parameter',(span.index,1,0),(owner,count,ismethod));sp,=md.parameters_for(spanctor);r=image.pe.bytes_at_va(ctx.type_pointer(sp.type_index),16);need('SpanCtor-array',(29,0),(r[10],r[11]));er=image.pe.bytes_at_va(int.from_bytes(r[:8],'little'),16);need('SpanCtor-own-VAR',(spanvar,19,0),(int.from_bytes(er[:8],'little'),er[10],er[11]))
 s={k:base+v for k,v in f['symbols'].items()};need('actual-source',programs['intArray']['entryRva'],fact['fields'][1]['targetRva']);paths=[arrays.int_array(*args('intArray'),offsets,s,count=n)for n in range(-1,6)]
 for name,role in(('empty','intEmpty'),('allocate','intAllocate'),('dataReference','intDataReference'),('asSpan','intAsSpan'),('spanConstructor','intSpanConstructor')):need('actual-helper-'+name,base+programs[role]['entryRva'],s[name])
 helpers=[arrays.int_empty(*args('intEmpty'),s),arrays.int_allocate(*args('intAllocate'),s),arrays.int_data_reference(*args('intDataReference'),s),arrays.array_as_span(*args('intAsSpan'),s),arrays.array_span_constructor(*args('intSpanConstructor'))]
 need('copy-selected-native',fact['nativeInputs'],copy_fact['nativeInputs']);need('actual-copy',base+copy_fact['entryRva'],s['copy']);need('copy-complete-ownership',sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(copy_fact['entryRva'])['ranges']),sorted((w['startRva'],w['endRva'])for w in copy_fact['ownedWindows']));image.check_windows(copy_fact['ownedWindows'],label='npcIntArray.copy');copy_regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in copy_fact['ownedWindows']];rows=[r for at,raw in copy_regions for r in decode_memory_move_instructions(image.mapper,raw,at)];tables={}
 for t in copy_fact['tables']:
  raw=image.pe.bytes_at_va(base+t['startRva'],t['endRva']-t['startRva']);need('actual-copy-table',t['raw'],raw.hex());tables[t['startRva']]=raw
 copy=prove_bounded_copy(copy_regions,s['copy'],rows=rows,tables=tables,image_base=base);need('bounded-copy-at-least20',True,copy['maxBytes']>=20);advance=scalar.advance_source(image,vector_recorder(image)(s['advance']-base,fragments=True),{k:offsets[k]for k in('currentPtr','bufferLength','advancedCount','consumed')},'npcIntArray.advance')
 return dict(selectedPaths=len(paths),helperPaths=len(helpers),copyMaxBytes=copy['maxBytes'],completeReturn=True,emptyIdentityProved=False)
