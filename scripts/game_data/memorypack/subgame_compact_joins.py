"""Current typed compact-table callback/return joins; runtime choices conditional."""
import hashlib,json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,_vtable
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.memorypack import reference_adapter_sources as reference,scalar_param_native as scalar,pooled_string_list_sources as strings,pooled_nominal_key_sources
from scripts.game_data.memorypack.module_structure_models import bridge_packable_return,bridge_list_callback
from scripts.game_data.memorypack.module_structure_joins import validate_base_routes
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context

def validate_joins(image,pins,fact,world,enclosing):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);symbols=ContextSymbols(image);need=lambda k,a,b:scalar.need('subgame.joins',k,a,b);programs=[];proofs=[];dependencies={}
 def fail(k,a,b):need(k,a,b)
 def owned(p):
  windows=[];regions=[];rows=[]
  for part in image.unwind_index.family(p-base)['ranges']:
   a,z=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);windows.append(dict(startRva=a,endRva=z,sha256=hashlib.sha256(raw).hexdigest().upper()));regions.append((base+a,raw));rows+=image.body_index._decode(base+a,z-a)
  programs.append(dict(entryRva=p-base,windows=windows));return regions,rows
 def method(owner,name):
  m,=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name];return m
 def dependency(name,validator):
  p=CONTRACTS_DIR/name;raw=p.read_bytes();dependencies[p]=raw;f=json.loads(raw);need(name+'-nativeInputs',pins,f['nativeInputs']);return f,validator(image,f)
 ref=fact['referenceRoutes'];comps=fact['compositions'];task='Beyond.Gameplay.Core.SubGameInstanceData+Task';root='Beyond.Gameplay.Core.SubGameInstanceDataTable';base_type='Beyond.Gameplay.Core.SubGameInstanceData';world_type='Beyond.Gameplay.Core.WorldChallengeSubGameData'
 def comp(original):
  c,=[c for c in comps if c['registrations'][0]['originalType']==original];validate_registered_formatter_composition(image,c,label='subgame.'+original);return c
 tc,rc,bc,wc=(comp(t)for t in(task,root,base_type,world_type));core=reference.validate_reference_routes(image,ref,[tc,rc]);ww=wc['registrations'][0]['wrapperType'];validate_base_routes(image,dict(baseComposition=bc,rollingOwned=dict(wrapper=ww)),dict(referenceRoutes=ref));s={k:base+v for k,v in ref['symbolRvas'].items()};dispatch=next(p for p in ref['ownedPrograms']if p['entryRva']==s['dispatch']-base);dr=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in dispatch['windows']]
 # Actual generated World wrapper callback returns its wrapper, then inherited Base GetValue returns the original reference.
 face,=wc['interfaces'];fw=md.methods[face['formatterDeserializeMethodIndex']];re,rs=owned(image.method_pointer_va(fw));calls=[control_transfer(r)['target']for r in rs if bytes.fromhex(r['bytes'])[:1]==b'\xe8'];need('forward-helper-count',2,len(set(calls)));reader=method(ww,'Deserialize');proofs.append(prove_zero_wrapper_forwarder(rs,dict(metadataInit=calls[0],classInit=calls[1]),image.method_pointer_va(reader)));proofs.append(deserialize_slot(dr,s['dispatch'],prepare=s['prepare'],callback=image.method_pointer_va(fw)))
 clone_path=CONTRACTS_DIR/'memorypack_reader_clones_native.json';raw=clone_path.read_bytes();dependencies[clone_path]=raw;clone=json.loads(raw);need('clone-nativeInputs',pins,clone['nativeInputs']);c,=[c for c in clone['clones']if c['claim']=='MemoryPack.MemoryPackReader.ReadPackable'and c['resultAbi']=='reference'];packable=base+c['targetRva'];Build(image,pins).prove_reader_clone_target(packable,c['claim']);need('root-packable',packable,enclosing['selected']['root']['symbols']['packable']);need('union-packable',packable,enclosing['selected']['union']['symbols']['packable']);need('all-world-list-packable',{packable},{p for p,k in zip(world['symbols']['reads'],world['plan'])if k=='list'});pr,_=owned(packable);prefix=bytes.fromhex('b9050000004c8d8c24280100004c8bc7488bd3');site,=[a+i for a,b in pr for i in range(len(b)-len(prefix)+1)if b[i:i+len(prefix)]==prefix];proofs.append(bridge_packable_return(pr,site,s['dispatch']))
 string_fact,string_result=dependency('levelscript_pooled_string_list_native.json',strings.validate_components);lang_fact,lang_result=dependency('levelscript_nominal_key_param_native.json',pooled_nominal_key_sources.validate_components)
 # Every current LangKey call owns a concrete hidden16 MethodSpec and uses the maintained complete component.
 lang_target={p for p,k in zip(world['symbols']['reads'],world['plan'])if k=='lang'};need('one-lang-target',1,len(lang_target));need('same-complete-lang-source',{base+lang_fact['symbols']['value16']},lang_target);Build(image,pins).prove_named_target(next(iter(lang_target)),'MemoryPack.MemoryPackReader','ReadValue',result_abi='hidden-output-16')
 sm=method('MemoryPack.BeyondStringFormatter','Deserialize');proofs.append(deserialize_slot(dr,s['dispatch'],prepare=s['prepare'],callback=image.method_pointer_va(sm)))
 def callback(m,definition,ordinals):
  need('callback-owner',(definition,False,5,2,'void'),(image.type_name(m.declaring_type),bool(m.flags&16),m.slot,m.parameter_count,ctx.type_name(m.return_type)));_vtable(image,m.declaring_type,5,m.index,'subgame.callback');p=list(md.parameters_for(m));rr=image.pe.bytes_at_va(ctx.type_pointer(p[0].type_index),16);need('reader-byref',('MemoryPack.MemoryPackReader',17,32),(ctx.type_name(p[0].type_index),rr[10],rr[11]));out=symbols.type(ctx.type_pointer(p[1].type_index));need('output-byref',32,image.pe.bytes_at_va(ctx.type_pointer(p[1].type_index),16)[11]);args=out.get('classArguments',[out]);need('output-owned-VARs',[(m.declaring_type,n)for n in ordinals],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in args]);return out
 dictionary=enclosing['selected']['dictionary'];de=dictionary['entry'];dm=md.methods[de['methodDefinitionIndices'][0]];callback(dm,'MemoryPack.Formatters.DictionaryFormatter`2',[0,1]);proofs.append(deserialize_slot(dr,s['dispatch'],prepare=s['prepare'],callback=de['pointer']));dc=dictionary['context'];slots={e['relativeSlot']:e for e in dc['entries']}
 for slot,owner,name,ordinals,method_args in((4,'System.Collections.Generic.Dictionary`2','.ctor',[0,1],False),(6,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',[0],True),(7,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',[1],True),(9,'System.Collections.Generic.Dictionary`2','Add',[0,1],False)):
  e=slots[slot];need('dictionary-context-'+str(slot),(owner,name),(e['typeName'],e['methodName']));need('dictionary-same-owned-VARs',[(dc['definition'],n)for n in ordinals],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in e['methodArguments'if method_args else'classArguments']])
 need('same-selected-reference-provider',s['hotProvider'],dictionary['symbols']['provider']);need('same-slot-dispatch',s['dispatch'],dictionary['symbols']['dispatch'])
 # Canonical reference list loop with concrete Task inflation: no closed registration is presumed.
 lf=symbols.context(ctx.index.types['MemoryPack.Formatters.ListFormatter`1'].index);ls=symbols.context(ctx.index.types['System.Collections.Generic.List`1'].index);validate_generic_contexts(image,[lf,ls],label='subgame.taskList');validate_list_element_context(image,lf,entries,fail=fail);validate_capacity_constructor_context(image,lf,ls,entries,fail=fail);validate_list_formatter_base_context(image,lf,entries,fail=fail);lm=method('MemoryPack.Formatters.ListFormatter`1','Deserialize');le=entries.resolve(lm.index,['object'],[]);callback(lm,'MemoryPack.Formatters.ListFormatter`1',[0]);need('no-closed-task-list-registration',[],entries.observe(lm.index,[task],[]));proofs.append(deserialize_slot(dr,s['dispatch'],prepare=s['prepare'],callback=le['pointer']));lr,_=owned(le['pointer']);list_symbols={k:base+v for k,v in string_fact['listSymbols'].items()};need('same-list-entry',le['pointer'],string_fact['listEntry']['registration']['pointer']);need('same-list-prepare',s['prepare'],list_symbols['prepare']);need('same-list-provider',s['hotProvider'],list_symbols['provider']);o=scalar.reader_offsets(image,'subgame.taskList');o['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 paths=[strings.list_source(lr,le['pointer'],o,list_symbols,count=n,new=new,grow=False)for n in(-1,0,1)for new in(False,True)];path=next(p for p in paths if p['countWitness']==1 and p['newList']);site,=path['elementCallbackSites'];proofs.append(bridge_list_callback(lr,site-38,s['prepare']))
 adapter=md.methods[ref['canonicalEntries']['Deserialize']['definition']];callback(adapter,image.type_name(adapter.declaring_type),[0]);reg,=tc['registrations'];args=image.instantiations.resolve(reg['classInstantiation']).arguments;need('Task-adapter-typed-pair',[task,reg['wrapperType']],[symbols.type(a.type_pointer_va)['name']for a in args]);need('Task-adapter-reference-args',[bytes((18,0))]*2,[image.pe.bytes_at_va(a.type_pointer_va,16)[10:12]for a in args])
 ulong=enclosing['selected']['ulongList'];proofs.append(deserialize_slot(dr,s['dispatch'],prepare=s['prepare'],callback=ulong['entry']['pointer']));need('same-null-list-barrier',dictionary['symbols']['barrier'],ulong['symbols']['barrier'])
 for p,b in dependencies.items():need('dependency-bookend-'+p.name,b,p.read_bytes())
 return json.loads(json.dumps(dict(programs=programs,proofs=proofs,referenceCore=core,pooledString=string_result,langKey=lang_result,taskList=paths,condition='Matching initialized coherent declared contexts and providers, canonical selected pointer source, normal compatible disjoint helpers, disabled collector. Runtime selection, dictionary storage and gameplay execution remain conditional.')))
