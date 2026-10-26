"""Current ModelView owned types, ordered sources and formatter/context composition."""
import json,re,struct
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,validate_typed_usage_context,derive_typed_usage_context,_vtable
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata,prove_cached_field_setter
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.string_source_instructions import decode_utf8_decoder_instructions
from scripts.game_data.il2cpp import string_source_programs
from scripts.game_data.memorypack.modelview_programs import validate_programs,need
from scripts.game_data.memorypack import primitive_param,scalar_param_native as scalar,reference_adapter_sources as reference,modelview_reference_sources as references,modelview_holder_sources as setter_source,modelview_packable_sources as packable,formatter_provider_success_sources as providers,pooled_source_helper,pooled_inline_sources,char_perform_actor_sources as pool,pooled_string_list_sources as lists,levelscript_interactive_sources as holders
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.vector3_source import validate_vector3_source,validate_vector3_reader
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.packable_reference_sources import validate_packable_context
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack.module_structure_models import enclosing_header
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.levelscript_family_regenerate import Build


def _rows(image,windows):
 base=image.pe.image_base;out=[]
 for w in windows:out+=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']),base+w['startRva'])
 return out


def _regions(image,p):
 base=image.pe.image_base;windows=p.get('parts',p.get('windows'));entry=p.get('entry',base+p.get('entryRva',0));need('complete-owned-component',sorted(tuple(z['runtimeTriple'][:2])for z in image.unwind_index.family(entry-base)['ranges']),sorted((w['startRva'],w['endRva'])for w in windows));image.check_windows(windows,label='modelViewComposition');return[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows],entry


def _method(image,ctx,t,n):
 found=[m for m in image.metadata.methods_for(ctx.index.types[t])if image.metadata.string(m.name_index)==n];need('unique-method:'+t+'::'+n,1,len(found));return found[0]


def _wire(ctx,f):
 t=f.declared_type
 if f.kind=='list':
  if not t.startswith('System.Collections.Generic.List`1<')or not t.endswith('>'):raise ValueError('modelView.list-carrier')
  return['list',t.split('<',1)[1][:-1]]
 if t=='UnityEngine.Vector3':return'vector3'
 if t.endswith('.ConditionValue'):return'raw16'
 if t=='Beyond.Audio.AudioId':return'i32'
 if f.kind=='enum':
  return'i32'
 return dict(bool='bool',float32='float',scalar32='u32'if t in('uint','System.UInt32')else'i32',scalar64='i64',string='string').get(f.kind,t)


def _records(image,pins,c,build,ctx,proofs):
 base=image.pe.image_base;md=image.metadata;rec=vector_recorder(image);o=scalar.reader_offsets(image,'modelView');proved={json.dumps(q['selectedBytes'])for q in proofs};prefixes={r['type']:r for r in c['prefixes']};tails={r['type']:r for r in c['returns']};primitives=set();layout=c['layout']
 need('record-layout-domain',set(layout['records'])-{layout['unionBase']},{r['type']for r in c['records']})
 for r in c['records']:
  w=build.wrappers[r['wrapper']];need('wrapper-original',r['type'],w.wrapped_type);need('ordered-typed-fields',[(f['name'],f['type'],f['kind'])for f in r['fields']],[(m.name,m.declared_type,m.kind)for m in w.members]);need('current-wire-layout',layout['records'][r['type']],[[m.name,_wire(ctx,m)]for m in w.members]);method=_method(image,ctx,w.name,'Deserialize');primitive_param.reader_abi(image,ctx,method,w);prefix=prefixes[r['type']];need('prefix-method',method.index,prefix['method'][0]);need('prefix-proved',True,json.dumps(prefix['proof']['selectedBytes'])in proved);reader,holder=prefix['proof']['reader'],prefix['proof']['holder'];start=prefix['proof']['end'];rows=_rows(image,r['windows']);byva={int(z['va'],16):i for i,z in enumerate(rows)};carried=[];previous_receiver=None
  for member,f in zip(w.members,r['fields'],strict=True):
   q=f['transfer'];need('field-transfer-proved:'+f['name'],True,json.dumps(q['selectedBytes'])in proved);field=ctx.field(build.wrappers[member.declaring_wrapper].wrapped_type+'::'+f['name']);need('field-declared-type',f['type'],field[1]);source=f.get('source',f.get('sourceTarget'));contexts=f.get('contexts',f.get('context'));inline=f['type'].endswith('.ConditionValue');hidden=f['type']=='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition';vector=f['type']=='UnityEngine.Vector3'
   if inline:
    need('inline-field-entry',start,q['selectedBytes'][0][0]);need('inline-owned-field',field[2],q['field']);scalar.advance_source(image,rec(source-base,fragments=True),o,'modelViewConditionValue')
   else:
    if start not in byva:raise ValueError('modelView.field-start-not-instruction')
    at=byva[start];ci=next(i for i in range(at,len(rows))if rows[i]['text'].startswith('call '));call=rows[ci];setup=rows[at:ci];need('actual-source-target',source,int(call['text'].split()[1],16));need('source-transfer-contiguous',int(call['va'],16)+len(bytes.fromhex(call['bytes'])),q['selectedBytes'][0][0]);texts=[z['text']for z in setup];loads=[z['text'].split()[1].rstrip(',')for z in setup if re.fullmatch(r'mov (rsi|rbx|rdi), \['+holder+r'\]',z['text'])]
    if len(loads)==1:receiver=loads[0]
    elif not loads and'holder'in carried:receiver=previous_receiver
    else:raise ValueError('modelView.field-holder-alias:'+str(texts))
    if hidden or vector:
     need('hidden-same-reader',True,'mov rdx, '+reader in texts);outputs=[t for t in texts if t.startswith('lea rcx, [rsp+')or t.startswith('lea rcx, [rbp-')];need('hidden-one-output',1,len(outputs))
     if hidden or contexts:need('hidden-disjoint-copy-alias','lea rcx, [rsp+0x20]',outputs[0])
     allowed={f'mov {receiver}, [{holder}]',f'mov rdx, {reader}'}
     if any(t not in allowed and not t.startswith(('lea rcx, [rsp+','lea rcx, [rbp-','mov r8, [rip+'))for t in texts):raise ValueError('modelView.hidden-argument-program:'+str(texts))
    else:
     need('same-reader-argument',True,'mov rcx, '+reader in texts or'reader'in carried);allowed={f'mov {receiver}, [{holder}]',f'mov rcx, {reader}'}
     if any(t not in allowed and not t.startswith('mov rdx, [rip+')for t in texts):raise ValueError('modelView.argument-program:'+str(texts))
    actual=[derive_typed_usage_context(image,int(z['va'],16)-base,label='modelViewField')for z in setup if len(bytes.fromhex(z['bytes']))==7 and bytes.fromhex(z['bytes'])[:2]in(b'\x48\x8b',b'\x4c\x8b')and bytes.fromhex(z['bytes'])[2]&199==5];need('actual-source-contexts',contexts,actual)
    for u in contexts:
     n='ReadUnmanaged'if member.kind=='enum'or f['type']=='Beyond.Audio.AudioId'or vector and contexts else'ReadPackable'if member.kind=='list'else'ReadValue';need('field-context',('MemoryPack.MemoryPackReader',n,[],[f['type']]),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']))
    if member.kind=='enum':
     underlying=[ctx.field(f['type']+'::'+md.string(z.name_index))for z in md.fields_for(ctx.index.types[f['type']])if not ctx.field_attributes(z.type_index)&16];need('enum-i32',[(f['type'],'int',16)],underlying)
    if vector:
     if contexts:validate_vector3_source(image,contexts[0],source-base)
     else:validate_vector3_reader(image,source-base)
    elif(source,member.kind)not in primitives:
     body=rec(source-base,fragments=True)
     if member.kind=='bool':scalar.boolean_source(image,body,o,f['name'])
     elif member.kind=='float32':primitive_param.single_source(image,body,o)
     elif member.kind in('scalar32','enum'):scalar.integer_source(image,body,o,f['name'],width=4)
     elif member.kind=='scalar64':scalar.integer_source(image,body,o,f['name'],width=8)
     elif member.kind=='string':build.prove_pooled_string_target(source)
     primitives.add((source,member.kind))
    previous_receiver=receiver
   start=q['end'];carried=q.get('prefetched',[])
  tail=tails[r['type']];need('complete-field-to-return-join',start,tail['fieldEnd']);need('normal-return-proved',True,json.dumps(tail['proof']['selectedBytes'])in proved)


def _setters(image,c,build,ctx):
 md=image.metadata;base=image.pe.image_base
 for r in c['setters']:
  w=build.wrappers[r['wrapper']];member,=[f for f in w.members if f.name==r['field']];_,owner,field,_,offset,method=_setter_metadata(image,build.wrappers,member);need('setter-owning-metadata',(r['owner'],r['wrapper'],r['type'],r['fieldOffset'],r['setter'][0]),(owner.wrapped_type,owner.name,member.declared_type,offset,method.index));image.validate_method_row(r['setter'],label='modelViewSetter');p=image.method_pointer_va(method);program=c['setterPrograms'][owner.name+'::'+md.string(method.name_index)];regions,entry=_regions(image,program);need('setter-body',p,entry);rows=_rows(image,program['parts']);calls=[int(z['text'].split()[1],16)for z in rows if z['text'].startswith('call 0x')];getter=image.method_pointer_va(_method(image,ctx,owner.name,'get___instance'))
  if member.declared_type=='UnityEngine.Vector3':setter_source.vector_setter(regions,p,getter=getter,field=offset,copy_mode='rcx'if any(z['text']=='mov rcx, rax'for z in rows[:8])else'rax')
  elif member.kind=='scalar64':setter_source.qword_setter(regions,p,getter=getter,field=offset)
  elif getter in calls:
   null,=[v for v in calls if v!=getter];tails=[z for z in rows if z['text'].startswith('jmp 0x')];sy=dict(getter=getter,nullThrow=null,barrier=int(tails[-1]['text'].split()[1],16)if tails else 0);q=prove_cached_field_setter(rows,field_offset=offset,mode=r['mode'],symbols=sy);need('setter-transfer',r['proof'],q)


def _registrations(image,c,ctx):
 base=image.pe.image_base;md=image.metadata;typed=lambda u:validate_typed_usage_context(image,u,label='modelViewRegistration')
 need('registration-domain',set(c['layout']['records']),{r['originalType']for r in c['registrations']})
 for r in c['registrations']:
  if r.get('registrationKind')!='conditionalSelectedLazyCallback':validate_eager_wrap_registration(image,r,label='modelViewRegistration');continue
  for n in('allocation','constructor','key','keyUsage','delegateClass','setterContext'):typed(r[n])
  original,wrapper=r['constructor']['classArguments'];need('lazy-pair',(r['originalType'],r['wrapperType']),(original,wrapper));need('lazy-key',original,r['key']['typeName']);need('lazy-mapping-key',r['key']['typeIndex'],r['keyUsage']['typeIndex']);need('lazy-delegate','System.Func`1<bool>',r['delegateClass']['typeName']);need('lazy-dictionary-add',('System.Collections.Generic.Dictionary`2','Add',['System.Type','System.Func`1<bool>']),(r['setterContext']['typeName'],r['setterContext']['methodName'],r['setterContext']['classArguments']));image.validate_method_row(r['callback'],label='modelViewLazyCallback');m=md.methods[r['callback'][0]];need('lazy-callback-ABI',(ctx.index.types[wrapper].index,True,'bool',0),(m.declaring_type,bool(m.flags&16),ctx.type_name(m.return_type),m.parameter_count));cell=r['keyProgram']['callbackCell'];need('lazy-callback-method',m.index,unresolved_usage_index(image.pe.bytes_at_va(cell,8),len(md.methods),tag=3,source='modelViewLazy',offset=cell-base))
  for row in r['helperMethods'].values():image.validate_method_row(row,label='modelViewLazyHelper')
  actual=r['actualConstructor'];image.check_windows(actual['windows'],label='modelViewLazyConstructor')
  if actual['extraArray']:
   for u in actual['extraArray'].values():typed(u)


def _references(image,c,ctx,ge):
 base=image.pe.image_base;md=image.metadata;routes=c['referenceRoutes'];reference.validate_reference_routes(image,routes,[]);s={k:base+v for k,v in routes['symbolRvas'].items()};programs={base+p['entryRva']:p for p in routes['ownedPrograms']};regions=lambda p:[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in programs[p]['windows']]
 for comp in c['compositions']:
  validate_registered_formatter_composition(image,comp,label='modelViewAdapter');registration,=comp['registrations'];original,w=registration['originalType'],registration['wrapperType']
  if ctx.is_value_type(original):continue
  face,=comp['interfaces'];td=ctx.index.types[w];getter=_method(image,ctx,w,'GetValue');gp=image.method_pointer_va(getter);need('GetValue-ABI',(False,0,original),(bool(getter.flags&16),getter.parameter_count,ctx.type_name(getter.return_type)));raw=image.pe.bytes_at_va(gp,7);target=image.method_pointer_va(_method(image,ctx,w,'get___instance'))if raw[:3]==bytes.fromhex('33d2e9')else None;references.get_value([(gp,raw[:7 if target else 5])],gp,getter=target)
  if target is None:need('GetValue-holder',(w,original,16),ctx.field(w+'::'+('___instance'if original==c['layout']['unionBase']else'__instance')))
  sec=md.sections['interfaceOffsets'];pairs=list(struct.iter_unpack('<ii',md.buf[sec.offset+td.interface_offsets_start*8:sec.offset+(td.interface_offsets_start+td.interface_offsets_count)*8]));ordinal=pairs.index((face['interfaceTypeIndex'],face['interfaceOffset']));reference.conversion(regions(s['conversion']),s['conversion'],base+routes['conversionPrepareRva'],gp,ordinal=ordinal);fm=md.methods[face['formatterDeserializeMethodIndex']];fp=image.method_pointer_va(fm);union=original==c['layout']['unionBase'];reader=None if union else _method(image,ctx,w,'Deserialize')
  for m in((fm,)if union else(fm,reader)):
   ps=list(md.parameters_for(m));need('reference-reader-ABI',(bool(m is reader),'void',2),(bool(m.flags&16),ctx.type_name(m.return_type),len(ps)))
   for p,t,k in zip(ps,('MemoryPack.MemoryPackReader',w),(17,18),strict=True):need('reference-reader-byrefs',(t,k,32),(ctx.type_name(p.type_index),*image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)[10:12]))
  if not union:
   windows=c['wrapperForwarders'][w]['forwarderWindows'];image.check_windows(windows,label='modelViewForwarder');need('forwarder-owned',sorted(tuple(z['runtimeTriple'][:2])for z in image.unwind_index.family(fp-base)['ranges']),sorted((z['startRva'],z['endRva'])for z in windows));rows=[z for a,b in[(base+t['startRva'],image.window_bytes(t))for t in windows]for z in image.body_index._decode(a,len(b))];calls=[int(z['va'],16)+5+int.from_bytes(bytes.fromhex(z['bytes'])[1:],'little',signed=True)for z in rows if len(bytes.fromhex(z['bytes']))==5 and bytes.fromhex(z['bytes'])[0]==232];need('forwarder-two-helpers',2,len(set(calls)));prove_zero_wrapper_forwarder(rows,dict(metadataInit=calls[0],classInit=calls[1]),image.method_pointer_va(reader))
  deserialize_slot(regions(s['dispatch']),s['dispatch'],prepare=s['prepare'],callback=fp)
 packable.validate_components(image,c['nativeInputs'],c['packable'],routes)
 return s


def _lists(image,c,ctx,ge):
 base=image.pe.image_base;md=image.metadata;cs=c['referenceContexts'];validate_generic_contexts(image,cs,label='modelViewCollections');value=validate_read_value_context(image,cs[1],cs[2],ge,fail=need);pc=validate_packable_context(image,cs[0],value['readerMethodDefinition'],ge,fail=need);lf,ls=cs[3:];validate_list_element_context(image,lf,ge,fail=need);validate_capacity_constructor_context(image,lf,ls,ge,fail=need);validate_list_formatter_base_context(image,lf,ge,fail=need);m=_method(image,ctx,'MemoryPack.Formatters.ListFormatter`1','Deserialize');_vtable(image,m.declaring_type,5,m.index,'modelViewList');need('list-slot-ABI',(5,False,'void',2),(m.slot,bool(m.flags&16),ctx.type_name(m.return_type),m.parameter_count));ps=list(md.parameters_for(m));need('list-reader','MemoryPack.MemoryPackReader',ctx.type_name(ps[0].type_index))
 for p,kind in zip(ps,(17,21),strict=True):need('list-byrefs',(kind,32),tuple(image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)[10:12]))
 for t in('object','long'):need('list-canonical:'+t,c['listRegistrations'][t],json.loads(json.dumps(ge.resolve(m.index,[t],[]))))
 for r in c['records']:
  for f in r['fields']:
   if f['kind']!='list':continue
   u,=f.get('contexts',f.get('context'));validate_typed_usage_context(image,u,label='modelViewListCaller');need('list-typed-parent',(pc['packableDefinition'],'MemoryPack.MemoryPackReader','ReadPackable',[],[f['type']]),(u['methodSpec'][0],u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']));need('same-actual-packable',base+c['packable']['entryRva'],f.get('source',f.get('sourceTarget')))
 # Fresh null/zero and full positive induction run over the same current reference list.
 listing=c['referenceList'];re,p=_regions(image,listing['program']);o=scalar.reader_offsets(image,'modelViewList');o['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 for n in(-1,0):lists.list_source(re,p,o,listing['symbols'],count=n,new=True,grow=False)



def _wrappers(image,c,ctx,proofs,build):
 base=image.pe.image_base;md=image.metadata;proved={json.dumps(q['selectedBytes'])for q in proofs}
 def bound(q):need('wrapper-transfer-proved',True,json.dumps(q['selectedBytes'])in proved)
 for r in c['wrapperTypes']:
  need('wrapper-parent',r['parent'],build.wrappers[r['wrapper']].parent_name);td=ctx.index.types[r['wrapper']];fields=[[md.string(f.name_index),ctx.type_name(f.type_index),ctx.field(r['wrapper']+'::'+md.string(f.name_index))[2]]for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16];need('wrapper-owned-fields',r['fields'],fields)
  for row in r['methods']:
   image.validate_method_row(row['method'],label='modelViewWrapper');m=md.methods[row['method'][0]];need('wrapper-ABI',(row['static'],row['returns'],row['parameters']),(bool(m.flags&16),ctx.type_name(m.return_type),[ctx.type_name(p.type_index)for p in md.parameters_for(m)]))
 for r in c['resets']+c['constructors']:
  image.validate_method_row(r['method'],label='modelViewFactory');bound(r['proof']);u=r['allocation'];validate_typed_usage_context(image,u,label='modelViewOriginalAllocation');need('factory-typed-original',(r['original'],base+u['usageCellRva']),(u['typeName'],r['proof']['originalClassCell']));need('factory-wrapper-owner',r['wrapper'],r['method'][1]);scalar.owned_method_abi(image,ctx,r['method'][0],ctx.index.types[r['wrapper']].index,('void',1,False),[],'modelViewFactory')
  if r.get('parent'):validate_typed_usage_context(image,r['parent'],label='modelViewParentClass');need('factory-parent-class',ctx.parent(r['wrapper']),r['parent']['typeName'])
 for r in c['cachedGetters']:
  image.validate_method_row(r['method'],label='modelViewCachedGetter');m=md.methods[r['method'][0]];scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,(r['original'],18,True),[],'modelViewCachedGetter');fields=[ctx.field(r['wrapper']+'::'+md.string(f.name_index))for f in md.fields_for(ctx.index.types[r['wrapper']])if not ctx.field_attributes(f.type_index)&16 and ctx.type_name(f.type_index)==r['original']];need('owned-cache-field',[(r['wrapper'],r['original'],r['cache'])],fields)
  for q in[r['coherent']]+r['refresh']:
   bound(q)
   for at,hexcode in q['selectedBytes']:
    if hexcode=='488b15':u=derive_typed_usage_context(image,at-base,label='modelViewGetterClass');need('getter-compatible-class',r['original'],u['typeName'])
 for r in c['callbacks']:
  row=r['method'];image.validate_method_row(row['method'],label='modelViewOnDeserialized');m=md.methods[row['method'][0]];scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'modelViewOnDeserialized')
  for q in r['proofs']:
   bound(q)
   if q['castClassCell']is not None:
    for at,h in q['selectedBytes']:
     if h=='488b15':u=derive_typed_usage_context(image,at-base,label='modelViewCallbackClass');need('callback-owning-class',r['type'],u['typeName'])
 barrier=c['collector'];image.check_windows(barrier['windows'],label='modelViewCollector');re=[(base+w['startRva'],image.window_bytes(w))for w in barrier['windows']];q=holders.collector_disabled_program(re,base+barrier['entryRva']);need('disabled-collector-preservation',(['r8'],True,True),(q['preservesRegistersExcept'],q['unchangedReturnRegister'],q['normalReturn']))


def _union(image,c,build):
 base=image.pe.image_base;fresh=read_union_switch(image,c['union']['base'],wrappers={w.type_definition:w for w in build.wrappers.values()});need('current-union-bijection',c['union'],fresh);need('stored-union-base',c['layout']['unionBase'],next(w.wrapped_type for w in build.wrappers.values()if w.name==fresh['base']));need('stored-union-map',c['layout']['union'],{str(e['tag']):build.wrappers[e['wrapperName']].wrapped_type for e in fresh['entries']});domain={(q['kwargs']['tag'],q['kwargs']['existing'])for q in c['sourcePrograms']['calls']if q['model']=='union.new_child'};need('complete-fresh-child-routes',{(e['tag'],b)for e in fresh['entries']for b in(False,True)},domain);re,p=_regions(image,c['unionHeader']);need('same-union-header',p,c['unionSymbols']['header']);enclosing_header(re,p,scalar.reader_offsets(image,'modelViewUnion'),marker='short')


def _strings(image,pins,c):
 base=image.pe.image_base;pool_fact=pooled_source_helper._contract();p=base+pool_fact['targetRva'];pooled_source_helper.validate_on_image(image,p,pins);re,entry=_regions(image,c['poolProgram']);need('same-pooled-string-source',p,entry);need('string-callback-native-pins',pins,c['stringComponents']['nativeInputs']);lists.validate_string_components(image,c['stringComponents']);symbols=pooled_inline_sources._symbols(image,pool_fact);o=scalar.reader_offsets(image,'modelViewPool')
 for mode in('null','empty','lookup'):pool.direct_pool(re,p,symbols,o,mode)
 for r in c['records']:
  for f in r['fields']:
   if f['kind']=='string':need('same-field-pool-target',p,f.get('source',f.get('sourceTarget')))


def _envelope(image,c,ctx,ge):
 base=image.pe.image_base;md=image.metadata;d=c['envelopeTyped'];lead=c['envelope'];comp=lead['composition'];body=comp['registrations'][0]['originalType'];w=comp['registrations'][0]['wrapperType'];ac,=comp['genericContexts'];validate_generic_contexts(image,[ac],label='modelViewEnvelope');validate_conversion_context(image,ac,ge,fail=need);section=md.sections['genericContainers'];owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,section.offset+ctx.index.types[ac['typeName']].generic_container_index*16);need('value-adapter-VAR-owner',(ac['definition'],2,0),(owner,count,is_method))
 for n,static,kinds in(('Deserialize',False,[(17,32,None),(19,32,start)]),('DeserializeNotNull',True,[(17,32,None),(19,32,start),(19,0,start+1)])):
  m=_method(image,ctx,ac['typeName'],n);need('value-adapter-ABI',(static,'void',len(kinds)),(bool(m.flags&16),ctx.type_name(m.return_type),m.parameter_count))
  for p,(kind,flags,var)in zip(md.parameters_for(m),kinds,strict=True):
   raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16);need('value-adapter-arg',(kind,flags),(raw[10],raw[11]&127))
   if var is None:need('value-adapter-Reader','MemoryPack.MemoryPackReader',ctx.type_name(p.type_index))
   else:need('value-adapter-owned-VAR',var,int.from_bytes(raw[:8],'little'))
 slots={e['relativeSlot']:e for e in ac['entries']}
 for slot,owner,n,ords in((0,ac['typeName'],'ReadIsNull',[0,1]),(3,ac['typeName'],'DeserializeNotNull',[0,1]),(11,'System.Activator','CreateInstance',[1])):
  row=slots[slot];args=row['methodArguments']if slot==11 else row['classArguments'];need('value-adapter-slot',(owner,n),(row['typeName'],row['methodName']));need('value-adapter-slot-VARs',[(ac['definition'],i)for i in ords],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in args])
 rc,pc=d['readValueContext'],d['providerContext'];validate_generic_contexts(image,[rc,pc],label='modelViewEnvelope');validate_read_value_context(image,rc,pc,ge,fail=need);provider=d['providerSuccess'];need('value-provider-context',provider['methodContext'],pc);regions={};entries={}
 for role,p in provider['programs'].items():
  entries[role]=base+p['entryRva'];windows=p['parts'];image.check_windows(windows,label='modelViewEnvelopeProvider');regions[role]=[(base+z['startRva'],image.window_bytes(z))for z in windows]
  if role not in('indexed','entry'):need('provider-complete-owned:'+role,sorted(tuple(z['runtimeTriple'][:2])for z in image.unwind_index.family(p['entryRva'])['ranges']),sorted((z['startRva'],z['endRva'])for z in windows))
 need('value-canonical-provider',entries['canonical'],ge.resolve(pc['definition'],[],[body])['pointer']);ss={k:base+v for k,v in provider['symbols'].items()};hot=providers.provider(regions['actual'],entries['actual'],ss);th=providers.type_from_handle(regions['typeFromHandle'],entries['typeFromHandle'],ss);need('same-Type-cache',{k:v for k,v in hot['cache'].items()if k!='returnedObjectRegister'},{k:v for k,v in th['cache'].items()if k!='returnedObjectRegister'});need('same-Type-class',hot['typeClassCell'],th['typeClassCell']);providers.validate_provider_success(regions,entries,ss,hot);ps={k:entries[v]for k,v in dict(typeHandle='typeFromHandle',backend='providerByType',indexed='indexed',assignable='assignableClass').items()};need('value-provider-symbols',d['providerSymbols'],ps)
 from scripts.game_data.memorypack import modelview_envelope_sources as value
 re,p=_regions(image,d['programs']['typedProvider']);need('same-actual-typed-provider',lead['readValueSymbols']['provider'],p);tp=value.typed_provider(re,p,ps);need('value-provider-classes',(hot['typeClassCell'],hot['providerClassCell']),(tp['typeClassCell'],tp['providerClassCell']));face,=comp['interfaces'];fm=md.methods[face['formatterDeserializeMethodIndex']];fr,fp=_regions(image,d['programs']['wrapperForwarder']);need('value-forwarder-entry',image.method_pointer_va(fm),fp);rows=[z for a,b in fr for z in image.body_index._decode(a,len(b))];calls=[int(z['va'],16)+5+int.from_bytes(bytes.fromhex(z['bytes'])[1:],'little',signed=True)for z in rows if len(bytes.fromhex(z['bytes']))==5 and bytes.fromhex(z['bytes'])[0]==232];need('value-forwarder-two-helpers',2,len(set(calls)));reader=image.method_pointer_va(_method(image,ctx,w,'Deserialize'));prove_zero_wrapper_forwarder(rows,dict(metadataInit=calls[0],classInit=calls[1]),reader);_vtable(image,fm.declaring_type,5,fm.index,'modelViewEnvelope');dr,dp=_regions(image,d['programs']['wrapperDispatcher']);need('value-same-wrapper-dispatch',lead['notNullSymbols']['wrapperDispatch'],dp);deserialize_slot(dr,dp,prepare=lead['mainSymbols']['prepare'],callback=fp)
 for n,getter in(('.ctor',False),('CreateInstance',False),('GetValue',True)):
  m=_method(image,ctx,w,n);scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,(body,17,False)if getter else('void',1,False),[],'modelViewEnvelopeLeaf')
 need('value-holder',(w,body,16),ctx.field(w+'::__instance'));primitive_param.object_header_source(image,vector_recorder(image)(lead['mainSymbols']['header']-base,fragments=True),scalar.reader_offsets(image,'modelViewEnvelope'));return hot



def _values(image,c,ctx):
 base=image.pe.image_base;md=image.metadata
 for r in c['rawValues']:
  name=r['type'];need('owned-value-type',True,ctx.is_value_type(name));td=ctx.index.types[name];pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);need('owned-value-sizes',r['sizes'],list(struct.unpack('<IIII',image.pe.bytes_at_va(pointer,16))));fields=[[md.string(f.name_index),ctx.type_name(f.type_index),ctx.field(name+'::'+md.string(f.name_index))[2]]for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16];need('owned-value-fields',r['fields'],fields)
 reference_entry=c['referenceProgram']['entry'];value_entry=c['envelope']['programs']['actualReadValue']['entry'];read_definition=c['referenceContexts'][1]['definition'];envelope=c['envelope']['composition']['registrations'][0]['originalType']
 for r in c['records']:
  for f in r['fields']:
   if f['kind']!='object'or f['type']in('Beyond.Audio.AudioId','UnityEngine.Vector3')or f['type'].endswith('.ConditionValue'):continue
   target=f.get('source',f.get('sourceTarget'));need('actual-selected-reference/value-source',value_entry if f['type']==envelope else reference_entry,target);u,=f.get('contexts',f.get('context'));need('actual-open-ReadValue-context',read_definition,u['methodSpec'][0])



def _curve(image,c,ctx,proofs):
 base=image.pe.image_base;md=image.metadata;d=c['curve'];row=d['method'];image.validate_method_row(row,label='modelViewUnityCurve');m=md.methods[row[0]];need('Unity-curve-formatter-parent','MemoryPack.MemoryPackFormatter`1<UnityEngine.AnimationCurve>',ctx.parent(row[1]));need('Unity-curve-slot-ABI',(False,'void',2),(bool(m.flags&16),ctx.type_name(m.return_type),m.parameter_count));_vtable(image,m.declaring_type,5,m.index,'modelViewUnityCurve')
 for p,t,k in zip(md.parameters_for(m),('MemoryPack.MemoryPackReader','UnityEngine.AnimationCurve'),(17,18),strict=True):need('Unity-curve-byrefs',(t,k,32),(ctx.type_name(p.type_index),*image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)[10:12]))
 for n,u in d['allocationUsages'].items():validate_typed_usage_context(image,u,label='modelViewUnityCurveAllocation');need('Unity-curve-allocation-type','UnityEngine.Keyframe[]'if n=='keyArrayUsage'else'UnityEngine.AnimationCurve',u['typeName'])
 key=d['keyframe'];td=ctx.index.types[key['type']];need('Unity-Keyframe-valuetype',True,ctx.is_value_type(key['type']));need('Unity-Keyframe-definition',key['definition'],td.index);size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);need('Unity-Keyframe28/boxed44',(44,28),struct.unpack('<II',image.pe.bytes_at_va(size,8)));fields=[[md.string(f.name_index),*ctx.field(key['type']+'::'+md.string(f.name_index))[1:]]for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16];need('Unity-Keyframe-owned-fields',key['fields'],fields)
 for literal in d['icallLiterals']:
  actual=image.pe.bytes_at_va(literal['literalVa'],256).split(b'\0',1)[0].decode('ascii');need('Unity-curve-selected-icall-name',literal['name'],actual);store=literal['store'];image.check_instruction_windows([[int(store['va'],16)-base,store['bytes']]],label='modelViewUnityCurveIcall');raw=bytes.fromhex(store['bytes']);need('Unity-curve-cache-cell',literal['cacheCell'],int(store['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True))
 q,=[v for v in proofs if v.get('cells')and v.get('keyCountWitness')==2];names={v['cacheCell']:v['name']for v in d['icallLiterals']}
 for role,name in dict(wrap0='UnityEngine.AnimationCurve::set_preWrapMode(UnityEngine.WrapMode)',wrap1='UnityEngine.AnimationCurve::set_postWrapMode(UnityEngine.WrapMode)',keys='UnityEngine.AnimationCurve::SetKeys(UnityEngine.Keyframe[])',create='UnityEngine.AnimationCurve::Internal_Create(UnityEngine.Keyframe[])').items():need('Unity-curve-actual-icall:'+role,name,names[q['cells'][role]])
 routes=c['referenceRoutes'];sy={k:base+v for k,v in routes['symbolRvas'].items()};dp,=[p for p in routes['ownedPrograms']if base+p['entryRva']==sy['dispatch']];re=[(base+w['startRva'],image.window_bytes(w))for w in dp['windows']];deserialize_slot(re,sy['dispatch'],prepare=sy['prepare'],callback=base+row[3])


def _long(image,c,ctx,ge,hot):
 base=image.pe.image_base;md=image.metadata;d=c['long'];parent=c['longList'];method=_method(image,ctx,'MemoryPack.Formatters.UnmanagedFormatter`1','Deserialize');need('Long-formatter-slot',5,method.slot);need('Long-formatter-registration',d['callback'],json.loads(json.dumps(ge.resolve(method.index,['long'],[]))));need('Long-callback-program',d['callback']['pointer'],d['programs']['formatter']['entry']);_vtable(image,method.declaring_type,5,method.index,'modelViewLong');need('Long-formatter-ABI',(False,'void',2),(bool(method.flags&16),ctx.type_name(method.return_type),method.parameter_count));ps=list(md.parameters_for(method));need('Long-formatter-Reader','MemoryPack.MemoryPackReader',ctx.type_name(ps[0].type_index))
 for p,k in zip(ps,(17,19),strict=True):need('Long-formatter-byrefs',(k,32),tuple(image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)[10:12]))
 td=ctx.index.types['System.Int64'];size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);need('signed-Long-native8',8,image.pe.u32_at_va(size+4));fields=[list(ctx.field('System.Int64::'+md.string(f.name_index)))for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16];need('signed-Long-underlying',d['nominalFields'],fields);need('same-Long-list-registration',parent['entry'],c['listRegistrations']['long'])
 for role,symbol in(('dispatcher','dispatch'),('add','add'),('capacity','constructor'),('provider','provider')):need('same-Long-helper:'+role,parent['symbols'][symbol],d['programs'][role]['entry'])
 o=scalar.reader_offsets(image,'modelViewLong');scalar.advance_source(image,vector_recorder(image)(d['symbols']['advance']-base,fragments=True),o,'modelViewLong.Advance');provider=c['envelopeTyped']['providerSuccess'];entries={k:base+v['entryRva']for k,v in provider['programs'].items()};ps={k:entries[v]for k,v in dict(typeHandle='typeFromHandle',backend='providerByType',indexed='indexed',cast='castObject').items()};re,p=_regions(image,d['programs']['provider'])
 from scripts.game_data.memorypack import char_perform_action_sources as value
 q=value.typed_provider(re,p,ps);need('Long-provider-class-joins',(hot['typeClassCell'],hot['providerClassCell']),(q['typeClassCell'],q['providerClassCell']))
 h=c['collectionHeader'];body=h['body'];need('same-Long-header',parent['symbols']['header'],base+body['entryRva']);image.check_windows(body['codeWindows'],label='modelViewCollectionHeader');need('header-owned',sorted(tuple(z['runtimeTriple'][:2])for z in image.unwind_index.family(body['entryRva'])['ranges']),sorted((z['startRva'],z['endRva'])for z in body['codeWindows']));groups=[decode_utf8_decoder_instructions(image.mapper,image.window_bytes(w),base+w['startRva'])for w in body['codeWindows']];normal=[];cold=[]
 for rows in groups:
  if not normal or int(rows[0]['va'],16)==int(normal[-1]['va'],16)+len(bytes.fromhex(normal[-1]['bytes'])):normal+=rows
  else:cold+=rows
 string_source_programs.prove_collection_header(normal,cold,{**o,'totalLength':ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16},h['symbols'])



def _bindings(image,c,ctx):
 base=image.pe.image_base;barrier=base+c['collector']['entryRva'];header=c['envelope']['mainSymbols']['header'];calls=c['sourcePrograms']['calls'];callbacks={r['wrapper']:r for r in c['callbacks']}
 for r in c['prefixes']:
  match=[v for v in calls if v['model']=='reader.prefix'and v['entry']==base+r['method'][3]]
  if not match:continue
  call,=match;need('same-object-header-source',header,call['args'][0]['header'])
  if call['kwargs']['cached']:
   row=callbacks[r['wrapper']]['method']['method'];need('actual-owned-OnDeserialized',base+row[3],call['args'][0]['onDeserialized'])
  else:need('no-unproved-OnDeserialized',None,call['args'][0]['onDeserialized'])
 def check_barrier(v):
  if isinstance(v,list):
   for x in v:check_barrier(x)
  elif isinstance(v,dict):
   for k,x in v.items():
    if k=='barrier'and x is not None:need('same-disabled-collector-helper',barrier,x)
    elif isinstance(x,(dict,list)):check_barrier(x)
 for v in calls:
  check_barrier(v['args']);check_barrier(v['kwargs'])
  if v['model']=='graph.envelope_result32':need('same-value-copy-barrier',barrier,v['args'][1])
 for r in c['resets']+c['constructors']:
  entry=base+r['method'][3];need('factory-method-source-entry',entry,r['proof']['selectedBytes'][0][0]);model='factory.create_instance'if r['method'][2]=='CreateInstance'else'factory.wrapper_constructor';call,=[v for v in calls if v['model']==model and v['entry']==entry];sy=call['args'][0]
  if'setInstance'in sy:need('actual-typed-holder-setter',image.method_pointer_va(_method(image,ctx,r['wrapper'],'set___instance')),sy['setInstance'])
  if'constructor'in sy:
   m=_method(image,ctx,r['original'],'.ctor');need('actual-typed-original-ctor',image.method_pointer_va(m),sy['constructor']);scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'modelViewOriginalConstructor')
  if'parentConstructor'in sy:need('actual-owned-parent-ctor',image.method_pointer_va(_method(image,ctx,ctx.parent(r['wrapper']),'.ctor')),sy['parentConstructor'])
 for r in c['callbacks']:
  for q in r['proofs']:need('callback-method-source-entry',base+r['method']['method'][3],q['selectedBytes'][0][0])
 # The current raw grammar accepts the bounded current tags, nullable/empty/positive lists and curves.
 domain=lambda model,keys:{tuple(v['kwargs'][k]for k in keys)for v in calls if v['model']==model}
 need('curve-path-domain',{(True,0),(False,-1),(False,0),(False,1),(False,2)},domain('curve.unity_curve',('null','keys')))
 need('value-main-path-domain',{(a,b)for a in(False,True)for b in(False,True)},domain('envelope.main',('dispatch','null')))
 need('value-NotNull-path-domain',{(False,),(True,)},domain('envelope.not_null',('wrapper_null',)))
 need('signed-list-path-domain',{('null',),('zero',),('positive',)},domain('long.list_source',('mode',)))


def derive(image,c):
 pins=c['nativeInputs'];ctx=NativeReferenceContext(image);ge=GenericEntries(image);build=Build(image,pins);regions,proofs=validate_programs(image,c['sourcePrograms']);_bindings(image,c,ctx);_records(image,pins,c,build,ctx,proofs);_setters(image,c,build,ctx);_registrations(image,c,ctx);_wrappers(image,c,ctx,proofs,build);_references(image,c,ctx,ge);_lists(image,c,ctx,ge);_union(image,c,build);_strings(image,pins,c);hot=_envelope(image,c,ctx,ge);_values(image,c,ctx);_curve(image,c,ctx,proofs);_long(image,c,ctx,ge,hot)
 return dict(layout=c['layout'],selectedSourcePrograms=len(proofs))
