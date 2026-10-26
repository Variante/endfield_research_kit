"""Fresh current one-AddMultiTags stored-wire source composition; no runtime selection."""
import json,struct
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,derive_typed_usage_context,_vtable
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack import char_perform_action_sources as source,formatter_provider_success_sources as providers,levelscript_interactive_sources as holders,reference_adapter_sources as reference,scalar_param_native as scalar,primitive_param,vector2_source,pooled_source_helper,pooled_inline_sources,char_perform_actor_sources as pool,pooled_string_list_sources as lists,char_perform_tag_sources as tags
from scripts.game_data.memorypack.module_structure_models import rolling_owned_strict_cast,enclosing_header,bridge_packable_return,bridge_list_callback


def need(k,e,a):
 if e!=a:raise ValueError('charPerformAction.'+k+':expected='+str(e)[:240]+':actual='+str(a)[:240])


def validate_one(image,pins,c,profile,root):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image);sy=ContextSymbols(image);build=Build(image,pins);programs=c['programs'];regions={};proofs=[];o=scalar.reader_offsets(image,'charPerformAction')
 def load(role):
  p=programs[role];entry=base+p['entryRva'];windows=p['windows'];owned=[(w['startRva'],w['endRva'])for w in windows]
  if p['ownership']=='leaf':
   leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(entry,512),entry);end=max(int(r['va'],16)+len(bytes.fromhex(r['bytes']))for r in leaf['rows']);need('closed-leaf:'+role,[(entry-base,end-base)],owned)
  elif p['ownership']=='selected-return-prefix':need('barrier-prefix:'+role,'wrapper:disabledBarrier',role)
  else:need('complete-owned:'+role,sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(entry-base)['ranges']),sorted(owned))
  image.check_windows(windows,label='charPerformAction');re=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows];regions[role]=re;return re,entry
 def symbols(k):return{k:base+v for k,v in c[k].items()}
 def run(fn,role,*args,**kw):
  re,p=load(role);q=fn(re,p,*args,**kw);proofs.append(q);return q
 def method(t,n):
  found=[m for m in md.methods_for(ctx.index.types[t])if md.string(m.name_index)==n];need('unique-method:'+t+'::'+n,1,len(found));return found[0]
 def at(role):return base+programs[role]['entryRva']
 def method_role(t,n,role):
  m=method(t,n);need('method-entry:'+role,image.method_pointer_va(m),at(role));return m
 def usage(site):return derive_typed_usage_context(image,site-base,label='charPerformAction')
 def typed(u,owner,name,ca,ma):need('typed-call',(owner,name,ca,ma),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']))
 for role in programs:load(role)
 g=c['grammar'];original='Beyond.Gameplay.Core.CharInteractPerform.AddMultiTagsActData';w=build.wrappers[g['child']];bo=ctx.parent(original);bw=ctx.parent(w.name)
 need('grammar',dict(field='loopActions',elementType=bo,wrapper=bw,child=w.name,unionTag=1,unionEntries=48,memberCount=18,allowedCounts=[-1,0,1],bodyType='Beyond.Gameplay.BodyTypeDef',bodyMemberCount=3),g);need('child-original',original,w.wrapped_type);need('current18-fields',[dict(name=m.name,type=m.declared_type,kind=m.kind,setter=m.method_index)for m in w.members],c['fields']);need('current18-count',18,len(w.members))
 parent_method=method_role(w.name,'Deserialize','action:reader');primitive_param.reader_abi(image,ctx,parent_method,w);s=symbols('actionSymbols');parent=run(source.child_new,'action:reader',c['fields'],s);alloc=usage(parent['allocationUsageSite']);need('typed-child-allocation',(w.name,parent['allocationClassCell']),(alloc['typeName'],base+alloc['usageCellRva']));need('child-ctor-source',at('wrapper:constructor'),s['ctor']);primitive_param.object_header_source(image,vector_recorder(image)(s['header']-base,fragments=True),o)
 # Every primitive/pooled source and actual typed child call is re-proved from its reached caller.
 ps=pooled_inline_sources._symbols(image,pooled_source_helper._contract());pool_pointer=base+pooled_source_helper._contract()['targetRva'];pooled_source_helper.validate_on_image(image,pool_pointer,pins);pr,pp=load('body:directPool');need('same-direct-pool',pool_pointer,pp)
 for mode in('null','empty','lookup'):proofs.append(pool.direct_pool(pr,pp,ps,o,mode))
 for f,t in zip(c['fields'],parent['fields'],strict=True):
  name,kind=f['name'],f['kind'];target=t['sourceTarget'];record=vector_recorder(image)(target-base,fragments=True)
  if name=='bodyType':
   typed(usage(t['contextSite']),'MemoryPack.MemoryPackReader','ReadValue',[],[g['bodyType']]);need('same-managed32-source',at('value:readValue32'),target);continue
  need('actual-owned-setter',image.method_pointer_va(md.methods[f['setter']]),t['setter'])
  if kind=='float32':primitive_param.single_source(image,record,o)
  elif kind=='bool':scalar.boolean_source(image,record,o,name)
  elif kind=='scalar32':scalar.integer_source(image,record,o,name,width=4)
  elif kind=='string':need('same-string-source',pool_pointer,target)
  elif name=='phaseEndWindow':
   u,=[usage(q['site'])for q in t['contexts']];typed(u,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],['UnityEngine.Vector2']);vector2_source.validate_vector2_source(image,u,target-base)
  elif name in('activeTags','guardActiveTags'):
   u,=[usage(q['site'])for q in t['contexts']];typed(u,'MemoryPack.MemoryPackReader','ReadPackable',[],['System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>']);need('same-Tag-list-packable',base+profile['packableRva'],target)
  else:raise ValueError('charPerformAction.unproved-child:'+name)
 # Typed concrete wrapper creation establishes the inherited holder and derived cache before all setters.
 ws=symbols('wrapperSymbols');need('same-child-constructor',at('wrapper:originalConstructor'),ws['originalConstructor']);need('same-base-setter',at('wrapper:baseSetter'),ws['baseSetter']);need('same-disabled-barrier',at('wrapper:disabledBarrier'),ws['barrier']);need('same-parent-barrier',s['barrier'],ws['barrier']);need('derived-holder',(w.name,original,24),ctx.field(w.name+'::__realInstance'));base_fields=[ctx.field(bw+'::'+md.string(f.name_index))for f in md.fields_for(ctx.index.types[bw])if not ctx.field_attributes(f.type_index)&16];need('base-holder',[(bw,bo,16)],base_fields)
 for n,role,fn in(('.ctor','wrapper:constructor',source.wrapper_ctor),('CreateInstance','wrapper:create',holders.wrapper_create_program)):
  m=method_role(w.name,n,role);scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'charActionFactory');q=run(fn,role,ws);u=usage(q['allocationInstruction']);need('factory-original',(original,q['originalTypeCell']),(u['typeName'],base+u['usageCellRva']))
  if n=='.ctor':
   site=next(a for a,h in q['selectedBytes']if h=='488b0d');u=usage(site);need('inline-base-ready-type',(bw,q['baseReadyClassCell']),(u['typeName'],base+u['usageCellRva']))
 dual=method_role(w.name,'set___instance','wrapper:baseSetter');scalar.owned_method_abi(image,ctx,dual.index,dual.declaring_type,('void',1,False),[(original,18,True)],'charActionDualSetter')
 ctor=method_role(original,'.ctor','wrapper:originalConstructor');scalar.owned_method_abi(image,ctx,ctor.index,ctor.declaring_type,('void',1,False),[],'charActionOriginalCtor');load('wrapper:originalConstructor');run(holders.base_setter_program,'wrapper:baseSetter',ws['barrier']);run(holders.collector_disabled_program,'wrapper:disabledBarrier');getter=method_role(w.name,'get___instance','wrapper:getter');scalar.owned_method_abi(image,ctx,getter.index,getter.declaring_type,(original,18,False),[],'charActionCachedGetter');run(holders.getter_coherent_program,'wrapper:getter');cast_regions,_=load('wrapper:checkedCast');hits=[]
 for start,raw in cast_regions:
  pos=0
  while(pos:=raw.find(bytes.fromhex('488b09e8'),pos))>=0:hits.append(start+pos+8+int.from_bytes(raw[pos+4:pos+8],'little',signed=True));pos+=1
 need('strict-cast-selected-callee',1,len(set(hits)));assignable=hits[0];run(rolling_owned_strict_cast,'wrapper:checkedCast',assignable)
 for f in c['fields'][1:]:
  name=f['name'];m=md.methods[f['setter']];owner=original if name in('activeTags','guardActiveTags','id')else bo;wrapper=w.name if owner==original else bw;need('setter-declaration:'+name,ctx.index.types[wrapper].index,m.declaring_type);field=ctx.field(owner+'::'+name);p,=md.parameters_for(m);need('setter-ABI:'+name,(False,'void',field[1]),(bool(m.flags&16),ctx.type_name(m.return_type),ctx.type_name(p.type_index)));scalar.ordinary(image,ctx.type_pointer(m.return_type),1,'charActionSetter.return');scalar.ordinary(image,ctx.type_pointer(p.type_index),dict(bool=2,float32=12,scalar32=9,string=14,object=17,list=21)[f['kind']],'charActionSetter.argument');role='wrapper:setter::'+name;need('setter-entry:'+name,image.method_pointer_va(m),at(role))
  if owner==original:run(source.reference_setter,role,at('wrapper:getter'),ws['barrier'],field[2])
  else:run(source.inherited_setter,role,field[2],f['kind'],ws['barrier'])
 _values(image,pins,c,load,run,at,method,method_role,usage,typed,proofs)
 # Current exact family bijection is independent of the selected tag/cursor/return program.
 switch=read_union_switch(image,bw,wrappers={w.type_definition:w for w in build.wrappers.values()});need('current48-union',c['union'],switch);row,=[r for r in switch['entries']if r['tag']==1];need('current-tag1-child',w.name,row['wrapperName']);up=at('union:union');need('current-union-entry',int(switch['dispatcherVa'],16),up);table=int(switch['tableVa'],16);selected=int(row['targetVa'],16);need('current-table-entry',selected,base+image.pe.u32_at_va(table+4));us=symbols('unionSymbols');need('same-union-packable/barrier',(base+profile['packableRva'],ws['barrier'],assignable),(us['packable'],us['barrier'],us['assignable']))
 for existing in(False,True):
  q=run(source.union_new,'union:union',us,tag=1,count=48,table=table,selected=selected,existing=existing);typed(usage(q['childContext']['instruction']),'MemoryPack.MemoryPackReader','ReadPackable',[],[w.name])
  if existing:need('typed-union-comparison',w.name,usage(q['comparisonTypeUsage']['instruction'])['typeName'])
 hr,hp=load('union:header');need('actual-header',us['header'],hp);proofs.append(enclosing_header(hr,hp,o,marker='short'));fm=method_role(w.name+'+'+w.name.rsplit('.',1)[-1]+'Formatter','Deserialize','union:childFormatter');_vtable(image,fm.declaring_type,5,fm.index,'charActionChild.slot5');fr,fp=load('union:childFormatter');rows=[r for a,b in fr for r in image.body_index._decode(a,len(b))];cs=[int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)for r in rows if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==232];need('child-forwarder-call-count',2,len(set(cs)));prove_zero_wrapper_forwarder(rows,dict(metadataInit=cs[0],classInit=cs[1]),at('action:reader'))
 comp=c['baseComposition'];validate_registered_formatter_composition(image,comp,label='charActionBase');face,=comp['interfaces'];need('base-composition-pair',(bo,bw),(comp['registrations'][0]['originalType'],comp['registrations'][0]['wrapperType']));bm=md.methods[face['getValueMethodIndex']];need('base-getter-entry',image.method_pointer_va(bm),at('enclosing:baseGetter'));br,bp=load('enclosing:baseGetter');need('base-full-ref8-getter','488b4110c3',image.pe.bytes_at_va(bp,5).hex());td=ctx.index.types[w.name];sec=md.sections['interfaceOffsets'];pairs=list(struct.iter_unpack('<ii',md.buf[sec.offset+td.interface_offsets_start*8:sec.offset+(td.interface_offsets_start+td.interface_offsets_count)*8]));pair=(face['interfaceTypeIndex'],face['interfaceOffset']);need('dynamic-base-interface-ordinal',c['baseInterfaceOrdinal'],pairs.index(pair));_vtable(image,td.index,face['interfaceOffset'],bm.index,'charActionDynamicBaseGetter');rs=symbols('referenceSymbols');need('same-open-reference-helpers',{k:base+v for k,v in profile['referenceRoutes']['symbolRvas'].items()},rs);run(reference.conversion,'enclosing:conversion',base+profile['referenceRoutes']['conversionPrepareRva'],bp,ordinal=c['baseInterfaceOrdinal']);dr,dp=load('enclosing:dispatch');need('same-reference-dispatch',rs['dispatch'],dp);need('actual-union-slot5',up,image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]));proofs.append(deserialize_slot(dr,dp,prepare=rs['prepare'],callback=up))
 for create in(False,True):run(reference.main,'enclosing:main',rs,create=create,wrapper_null=False)
 run(reference.nonnull,'enclosing:nonnull',rs,wrapper_null=False)
 chosen,=[f for f in root['fields']if f['name']=='loopActions'];u,=[usage(q['instruction'])for q in chosen['contextCells']];typed(u,'MemoryPack.MemoryPackReader','ReadPackable',[],['System.Collections.Generic.List`1<'+bo+'>']);need('actual-root-list-call',base+profile['packableRva'],chosen['sourceTarget']);build.prove_reader_clone_target(chosen['sourceTarget'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference');pr,pp=load('enclosing:packable');need('same-packable-source',chosen['sourceTarget'],pp);pc,=[r for r in profile['calls']if r['model']=='packableReturn'];proofs.append(bridge_packable_return(pr,base+pc['args'][1]['site'],rs['dispatch']));lm=method('MemoryPack.Formatters.ListFormatter`1','Deserialize');reg=ge.resolve(lm.index,['object'],[]);need('canonical-reference-list',c['listRegistration'],json.loads(json.dumps(reg)));lf,lc=c['listContexts'];validate_generic_contexts(image,[lf,lc],label='charActionList');validate_list_element_context(image,lf,ge,fail=need);validate_capacity_constructor_context(image,lf,lc,ge,fail=need);validate_list_formatter_base_context(image,lf,ge,fail=need);_vtable(image,lm.declaring_type,5,lm.index,'charActionList.slot5');lr,lp=load('enclosing:list');need('actual-list-program',reg['pointer'],lp);proofs.append(deserialize_slot(dr,dp,prepare=rs['prepare'],callback=lp));ls=symbols('listSymbols');need('same-list-provider/prepare',(rs['hotProvider'],rs['prepare']),(ls['provider'],ls['prepare']));lo={**o,'totalLength':ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16}
 for new in(False,True):
  q=lists.list_source(lr,lp,lo,ls,count=1,new=new,grow=False);proofs.append(q);site,=q['elementCallbackSites'];proofs.append(bridge_list_callback(lr,site-38,rs['prepare']))
 return dict(fields=c['fields'],selectedPrograms=len(proofs),wholeOwnerAdmitted=False,liveProviderSelectionProved=False)


def _values(image,pins,c,load,run,at,method,method_role,usage,typed,proofs):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image);sy=ContextSymbols(image);body=c['grammar']['bodyType'];comp=c['valueComposition'];validate_registered_formatter_composition(image,comp,label='charActionBody32');registration,=comp['registrations'];need('body32-original',body,registration['originalType']);w=registration['wrapperType'];build=Build(image,pins);bw=build.wrappers[w];need('body32-field-order',[('bodyType','Beyond.Gameplay.BodyType'),('CustomId','int'),('CustomName','string')],[(m.name,m.declared_type)for m in bw.members]);need('body32-runtime-fields',c['bodyFields'],{md.string(f.name_index):list(ctx.field(body+'::'+md.string(f.name_index)))for f in md.fields_for(ctx.index.types[body])if not ctx.field_attributes(f.type_index)&16});need('managed-value',True,ctx.is_value_type(body));size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+ctx.index.types[body].index*8);need('managed32-boxed48',48,image.pe.u32_at_va(size));bm=method_role(w,'Deserialize','body:bodyReader');primitive_param.reader_abi(image,ctx,bm,bw);bs={k:base+v for k,v in c['bodyReadSymbols'].items()};o=scalar.reader_offsets(image,'charActionBody32')
 for new in(False,True):
  q=run(source.body_reader,'body:bodyReader',bs,new=new);typed(usage(q['byteContextSite']),'MemoryPack.MemoryPackReader','ReadUnmanaged',[],['Beyond.Gameplay.BodyType'])
  if new:
   u=usage(q['allocation']['site']);need('body-wrapper-allocation',(w,q['allocation']['cell']),(u['typeName'],base+u['usageCellRva']))
 enum='Beyond.Gameplay.BodyType';need('body-byte-enum',True,ctx.is_enum(enum));need('body-enum-byte',[(enum,'byte',16)],[ctx.field(enum+'::'+md.string(f.name_index))for f in md.fields_for(ctx.index.types[enum])if not ctx.field_attributes(f.type_index)&16]);rec=vector_recorder(image);primitive_param.object_header_source(image,rec(bs['header']-base,fragments=True),o);scalar.raw_byte_source(image,rec(bs['byte']-base,fragments=True),o);scalar.integer_source(image,rec(bs['integer']-base,fragments=True),o,'CustomId',width=4);need('same-Body-pool',at('body:directPool'),bs['string']);need('same-Body-barrier',at('wrapper:disabledBarrier'),bs['barrier']);main={k:base+v for k,v in c['bodyValueSymbols'].items()};ns={k:base+v for k,v in c['notNullSymbols'].items()};rvs=dict(provider=at('value:typedProvider'),dispatch=at('value:valueDispatcher32'));run(source.read_value32,'value:readValue32',rvs)
 for n,d in c['valueCanonicalEntries'].items():
  m=method('Beyond.MemoryPack.GenericMemoryPackFormatter`2',n);need('managed32-canonical-owner','Beyond.MemoryPack.GenericMemoryPackFormatter`2',ctx.type_name(md.types[m.declaring_type].byval_type_index));need('managed32-canonical-name',n,md.string(m.name_index));need('managed32-canonical-entry:'+n,json.loads(json.dumps(d)),json.loads(json.dumps(ge.resolve(m.index,[body,'object'],[]))))
 need('managed32-main-entry',c['valueCanonicalEntries']['Deserialize']['pointer'],at('value:main32'));need('managed32-NotNull-entry',c['valueCanonicalEntries']['DeserializeNotNull']['pointer'],at('value:notNull32'));run(source.adapter,'value:main32',main);run(source.adapter,'value:valueDispatcher32',main,dispatch=True);run(source.not_null,'value:notNull32',ns);run(source.conversion,'value:conversion32',main['prepare'],ordinal=c['valueInterfaceOrdinal']);face,=comp['interfaces'];td=ctx.index.types[w];sec=md.sections['interfaceOffsets'];pairs=list(struct.iter_unpack('<ii',md.buf[sec.offset+td.interface_offsets_start*8:sec.offset+(td.interface_offsets_start+td.interface_offsets_count)*8]));need('managed32-conversion-ordinal',c['valueInterfaceOrdinal'],pairs.index((face['interfaceTypeIndex'],face['interfaceOffset'])))
 for n,getter in(('.ctor',False),('CreateInstance',False),('GetValue',True)):
  role='value:wrapper::'+n;m=method_role(w,n,role);scalar.owned_method_abi(image,ctx,m.index,td.index,(body,17,False)if getter else('void',1,False),[],'charActionValue32.wrapper');run(source.value_leaf,role,getter=getter)
 need('managed32-holder',(w,body,16),ctx.field(w+'::__instance'));ac=c['valueAdapterContext'];validate_generic_contexts(image,[ac],label='charActionValue32');validate_conversion_context(image,ac,ge,fail=need);section=md.sections['genericContainers'];owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,section.offset+ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'].generic_container_index*16);need('managed32-adapter-VAR-owner',(ac['definition'],2,0),(owner,count,is_method))
 for n,static,kinds in(('Deserialize',False,[(17,32,None),(19,32,start)]),('DeserializeNotNull',True,[(17,32,None),(19,32,start),(19,0,start+1)])):
  m=method(ac['typeName'],n);need('managed32-adapter-ABI',(static,'void',len(kinds)),(bool(m.flags&16),ctx.type_name(m.return_type),m.parameter_count))
  for p,(kind,flags,var)in zip(md.parameters_for(m),kinds,strict=True):
   raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16);need('managed32-adapter-arg',(kind,flags),(raw[10],raw[11]&127))
   if var is not None:need('managed32-adapter-owned-VAR',var,int.from_bytes(raw[:8],'little'))
   else:need('managed32-actual-Reader','MemoryPack.MemoryPackReader',ctx.type_name(p.type_index))
 slots={r['relativeSlot']:r for r in ac['entries']}
 for slot,owner,n,ords in((0,ac['typeName'],'ReadIsNull',[0,1]),(3,ac['typeName'],'DeserializeNotNull',[0,1]),(11,'System.Activator','CreateInstance',[1])):
  row=slots[slot];args=row['methodArguments']if slot==11 else row['classArguments'];need('managed32-adapter-slot',(owner,n),(row['typeName'],row['methodName']));need('managed32-adapter-slot-VARs',[(ac['definition'],i)for i in ords],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in args])
 rc,pc=c['readValueContext'],c['providerContext'];validate_generic_contexts(image,[rc,pc],label='charActionValue32');validate_read_value_context(image,rc,pc,ge,fail=need);need('same-provider-context',c['providerSuccess']['methodContext'],pc);u=derive_typed_usage_context(image,next(r['contextSite']for r in run(source.child_new,'action:reader',c['fields'],{k:base+v for k,v in c['actionSymbols'].items()})['fields']if r['name']=='bodyType')-base,label='charActionValue32');need('actual-ReadValue-context',rc,sy.context(u['methodSpec'][0],is_method=True));reg=ge.resolve(pc['definition'],[],[body]);provider=c['providerSuccess'];pregions={};entries={}
 for role,p in provider['programs'].items():
  entries[role]=base+p['entryRva'];windows=p['parts']
  if role not in('indexed','entry'):need('provider-owned:'+role,sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(p['entryRva'])['ranges']),sorted((w['startRva'],w['endRva'])for w in windows))
  image.check_windows(windows,label='charActionProvider');pregions[role]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows]
 need('canonical-provider-registration',entries['canonical'],reg['pointer']);ss={k:base+v for k,v in provider['symbols'].items()};hot=providers.provider(pregions['actual'],entries['actual'],ss);th=providers.type_from_handle(pregions['typeFromHandle'],entries['typeFromHandle'],ss);need('same-successful-Type-cache',{k:v for k,v in hot['cache'].items()if k!='returnedObjectRegister'},{k:v for k,v in th['cache'].items()if k!='returnedObjectRegister'});need('same-Type-class',hot['typeClassCell'],th['typeClassCell']);proofs.append(providers.validate_provider_success(pregions,entries,ss,hot));ps={k:entries[v]for k,v in dict(typeHandle='typeFromHandle',backend='providerByType',indexed='indexed',cast='castObject').items()};need('typed-provider-shared-targets',ps,{k:base+v for k,v in c['providerSymbols'].items()});tp=run(source.typed_provider,'value:typedProvider',ps);need('typed-provider-same-classes',(hot['typeClassCell'],hot['providerClassCell']),(tp['typeClassCell'],tp['providerClassCell']))
 ref={k:base+v for k,v in c['referenceSymbols'].items()};need('same-shared-value-reference-helpers',(ref['context'],ref['hotProvider'],ref['indexed'],ref['dispatch'],ref['prepare']),(ns['context'],ns['hotProvider'],ns['indexed'],ns['wrapperDispatch'],main['prepare']));forwarder=md.methods[face['formatterDeserializeMethodIndex']];need('body-forwarder-entry',image.method_pointer_va(forwarder),at('value:wrapperForwarder'));fr,fp=load('value:wrapperForwarder');rows=[r for a,b in fr for r in image.body_index._decode(a,len(b))];cs=[int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)for r in rows if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==232];need('body-forwarder-helper-count',2,len(set(cs)));prove_zero_wrapper_forwarder(rows,dict(metadataInit=cs[0],classInit=cs[1]),at('body:bodyReader'));wr,wp=load('value:wrapperDispatcher');need('same-NotNull-dispatch',ns['wrapperDispatch'],wp);proofs.append(deserialize_slot(wr,wp,prepare=main['prepare'],callback=fp));rr,rp=load('value:readNull');kr,kp=load('value:peek');need('same-ReadIsNull-registration',c['valueCanonicalEntries']['ReadIsNull']['pointer'],rp);proofs.append(tags.read_null_positive(rr,rp,kp));proofs.append(tags.peek_null(kr,kp,o))
