"""Compose freshly checked Actor13 stored-wire transfers with its one-item list."""
import json
from scripts.game_data import char_interact_perform_actor_native as actor
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,derive_typed_usage_context,_vtable
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.memorypack import char_perform_actor_sources as source,reference_adapter_sources as reference,scalar_param_native as scalar,primitive_param,pooled_source_helper,pooled_inline_sources,pooled_string_list_sources as lists
from scripts.game_data.memorypack.module_structure_models import bridge_packable_return,bridge_list_callback
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.vector_layout import vector_recorder

def need(k,e,a):
 if e!=a:raise ValueError(f'charPerformActor.{k}:expected={str(e)[:240]}:actual={str(a)[:240]}')

def validate_one(image,pins,claim,profile,root):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image);symbols=ContextSymbols(image);build=Build(image,pins);paths=[actor.CONTRACT_PATH,pooled_source_helper.CONTRACT_PATH];saved=[p.read_bytes()for p in paths];fact=json.loads(saved[0]);need('actor-schema',actor.SCHEMA,fact['schema']);need('actor-status','validated',fact['status']);need('actor-native',pins,fact['nativeInputs']);actor._validate(image,fact);original,name=fact['typeName'],fact['wrapperName'];need('grammar',dict(field='chars',elementType=original,wrapper=name,memberCount=13,allowedCounts=[-1,0,1]),claim['grammar']);offsets=scalar.reader_offsets(image,'charPerformActor');regions={};programs=claim['programs']
 def load(role):
  p=programs[role];need('owned:'+role,sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(p['entryRva'])['ranges']),sorted((w['startRva'],w['endRva'])for w in p['windows']));image.check_windows(p['windows'],label='charPerformActor');regions[role]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in p['windows']];return regions[role],base+p['entryRva']
 def method(owner,n):
  found=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==n];need('method:'+n,1,len(found));return found[0]
 need('actor-reader-entry',fact['readerMethod'][3],programs['actorReader']['entryRva']);rr,rp=load('actorReader');transfer=source.existing(rr,rp,fact['fields'],offsets);record=vector_recorder(image);primitive_count=0
 for f,t in zip(fact['fields'],transfer['fields'],strict=True):
  need('field-call:'+f['name'],(base+f['sourceCall'][0],base+f['sourceTargetRva']),(t['sourceCall'],t['sourceTarget']));wire=f['wire'];r=record(f['sourceTargetRva'],fragments=True)
  if wire=='enum32':
   u,=[derive_typed_usage_context(image,c['site']-base,label='charPerformActor')for c in t['contexts']];need('enum-source',('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[f['type']]),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']));td=ctx.index.types[f['type']];fs=[ctx.field(f['type']+'::'+md.string(x.name_index))for x in md.fields_for(td)if not ctx.field_attributes(x.type_index)&16];need('Int32-enum',True,ctx.is_enum(f['type']));need('enum-field',[(f['type'],'int',16)],fs);scalar.integer_source(image,r,offsets,f['name'],width=4)
  elif wire in('int64','uint64'):scalar.integer_source(image,r,offsets,f['name'],width=8)
  elif wire=='boolByte':scalar.boolean_source(image,r,offsets,f['name'])
  elif wire=='float32':primitive_param.single_source(image,r,offsets)
  elif wire=='pooledStringIndex':continue
  else:raise ValueError('charPerformActor.unproved-child:'+wire)
  primitive_count+=1
 need('primitive-domain',9,primitive_count)
 pf=pooled_source_helper._contract();target=base+pf['targetRva'];pooled_source_helper.validate_on_image(image,target,pins);ps=pooled_inline_sources._symbols(image,pf);pr,pp=load('directPool');need('pool-entry',target,pp);poolproof=[source.direct_pool(pr,pp,ps,offsets,mode)for mode in('null','empty','lookup')];need('four-string-sources',[target]*4,[t['sourceTarget']for f,t in zip(fact['fields'],transfer['fields'],strict=True)if f['wire']=='pooledStringIndex']);pm=md.methods[pf['equivalentMethod'][0]];need('pool-static-arity',(True,1,'string'),(bool(pm.flags&16),pm.parameter_count,ctx.type_name(pm.return_type)));scalar.ordinary(image,ctx.type_pointer(pm.return_type),14,'charPerformActor.string-return');parameter,=md.parameters_for(pm);need('pool-Reader-BYREF',('MemoryPack.MemoryPackReader',17,32),(ctx.type_name(parameter.type_index),*image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)[10:12]))
 factories=[]
 for n,role in(('.ctor','actorCtor'),('CreateInstance','actorCreate')):
  m=method(name,n);scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('void',1,False),[],'charPerformActor.factory');re,p=load(role);need('factory-entry',image.method_pointer_va(m),p);s={k:base+v for k,v in claim['factorySymbolRvas'][role].items()};proof=source.factory(re,p,s,create=n=='CreateInstance');u=derive_typed_usage_context(image,proof['allocationUsageSite']-base,label='charPerformActor');need('factory-original',original,u['typeName']);need('factory-cell',base+u['usageCellRva'],proof['allocationClassCell']);factories.append(proof)
 ctor,=[m for m in md.methods_for(ctx.index.types[original])if md.string(m.name_index)=='.ctor'and m.parameter_count==0];scalar.owned_method_abi(image,ctx,ctor.index,ctor.declaring_type,('void',1,False),[],'charPerformActor.originalCtor');need('original-ActorType-zero-leaf','c7411000000000c3',image.pe.bytes_at_va(image.method_pointer_va(ctor),8).hex())
 comp=claim['composition'];need('concrete-original',original,comp['registrations'][0]['originalType']);need('concrete-wrapper',name,comp['registrations'][0]['wrapperType']);core=reference.validate_reference_routes(image,claim['referenceRoutes'],[comp]);s={k:base+v for k,v in claim['referenceRoutes']['symbolRvas'].items()};need('same-shared-helpers',profile['referenceRoutes']['symbolRvas'],claim['referenceRoutes']['symbolRvas'])
 selected,=[f for f in root['fields']if f['name']=='chars'];u,=[derive_typed_usage_context(image,c['instruction']-base,label='charPerformActor')for c in selected['contextCells']];typ='System.Collections.Generic.List`1<'+original+'>';need('actual-root-context',('MemoryPack.MemoryPackReader','ReadPackable',[],[typ]),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']));need('actual-root-field',typ,ctx.field(profile['original']+'::chars')[1]);need('actual-packable',base+profile['packableRva'],selected['sourceTarget']);build.prove_reader_clone_target(selected['sourceTarget'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference');preg,pack=load('packable');need('packable-program',pack,selected['sourceTarget']);pc,=[c for c in profile['calls']if c['model']=='packableReturn'];parent=bridge_packable_return(preg,base+pc['args'][1]['site'],s['dispatch'])
 lm=method('MemoryPack.Formatters.ListFormatter`1','Deserialize');reg=ge.resolve(lm.index,['object'],[]);need('canonical-list-registration',claim['listRegistration'],json.loads(json.dumps(reg)));lr,lp=load('list');need('list-entry',reg['pointer'],lp);lf,lc=claim['listContexts'];validate_generic_contexts(image,[lf,lc],label='charPerformActor');validate_list_element_context(image,lf,ge,fail=need);validate_capacity_constructor_context(image,lf,lc,ge,fail=need);validate_list_formatter_base_context(image,lf,ge,fail=need);_vtable(image,lm.declaring_type,5,lm.index,'charPerformActor.list.slot5');need('list-ABI',(False,5,'void',2),(bool(lm.flags&16),lm.slot,ctx.type_name(lm.return_type),lm.parameter_count));ps=list(md.parameters_for(lm));need('list-Reader-BYREF',('MemoryPack.MemoryPackReader',17,32),(ctx.type_name(ps[0].type_index),*image.pe.bytes_at_va(ctx.type_pointer(ps[0].type_index),16)[10:12]));out=symbols.type(ctx.type_pointer(ps[1].type_index));need('list-output-BYREF',bytes((21,32)),image.pe.bytes_at_va(ctx.type_pointer(ps[1].type_index),16)[10:12]);need('list-output-definition','System.Collections.Generic.List`1',out['definition']['name']);need('list-output-VAR',[(lm.declaring_type,0)],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in out['classArguments']]);dr,dp=load('dispatcher');need('dispatch-entry',s['dispatch'],dp);dispatch=deserialize_slot(dr,dp,prepare=s['prepare'],callback=lp)
 ls={k:base+v for k,v in claim['listSymbolRvas'].items()};need('provider-and-prepare',(s['hotProvider'],s['prepare']),(ls['provider'],ls['prepare']));o={**offsets,'totalLength':ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16};listproof=[]
 for new in(True,False):
  p=lists.list_source(lr,lp,o,ls,count=1,new=new,grow=False);site,=p['elementCallbackSites'];bridge_list_callback(lr,site-38,s['prepare']);listproof.append(p)
 need('dependency-bookends',saved,[p.read_bytes()for p in paths]);return dict(fields=fact['fields'],sourcePrograms=1+len(poolproof)+len(factories)+len(listproof),referenceCore=core,primitiveSources=primitive_count,liveProviderSelectionProved=False,wholeOwnerAdmitted=False)
