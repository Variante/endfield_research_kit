"""Re-prove the current bounded CharInteract stored schema per operation."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,validate_typed_usage_context,derive_typed_usage_context
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
from scripts.game_data.memorypack import char_perform_root_sources as root,char_perform_dictionary_sources as dictionaries,char_perform_factory_sources as factories,char_perform_sparse_sources as source,reference_adapter_sources as reference,scalar_param_native as scalar,primitive_param,pooled_source_helper,pooled_string_list_sources,char_perform_tag_joins as tag_joins,char_perform_tag_sources as tag_source
from scripts.game_data.memorypack.module_structure_models import bridge_packable_return
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data import levelscript_int_list_native

from scripts.game_data.memorypack import char_perform_actor_joins as actor_joins,char_perform_actor_sources as actor_source,char_perform_action_sources as action_source,char_perform_action_joins as action_joins,formatter_provider_success_sources as provider_source

CONTRACT_PATH=CONTRACTS_DIR/'char_interact_perform_sparse_native.json'
LABEL='charInteractPerformSparseNative'
MODELS=dict(root=root.root_existing,uintDictionary=dictionaries.uint_reference,referenceDictionary=dictionaries.reference_reference,factory=factories.factory,getter=factories.getter,tagList=source.tag_list,entry=source.entry_caller,entrySetter=source.entry_setter,readValue=source.read_value_transfer,packableReturn=bridge_packable_return,referenceList=pooled_string_list_sources.list_source)

def need(k,e,a):
 if e!=a:raise ValueError(f'{LABEL}.{k}:expected={str(e)[:260]}:actual={str(a)[:260]}')

def derive(image,fact):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);generic=GenericEntries(image);symbols=ContextSymbols(image);build=Build(image,fact['nativeInputs']);profile=fact['profile'];regions={};programs={};proofs=[];offsets=scalar.reader_offsets(image,LABEL);list_offsets={**offsets,'totalLength':ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16}
 def authenticate_contexts(rows):
  for r in rows:
   if 'selectedSlots'in r:
    need('bounded-dictionary-context-selection',[5,21,22,23,24],r['selectedSlots']);need('selected-context-symbols',r,symbols.context(r['definition'],is_method=r['isMethod'],slots=r['selectedSlots']))
   else:validate_generic_contexts(image,[r],label=LABEL)
 for p in profile['programs']:
  if p['leaf']:need('complete-getter-leaf',[(p['entryRva'],p['entryRva']+5)],[(w['startRva'],w['endRva'])for w in p['windows']]);need('getter-ref8-return','488b4110c3',image.pe.bytes_at_va(base+p['entryRva'],5).hex())
  else:need('complete-owned-program:'+p['role'],sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(p['entryRva'])['ranges']),sorted((w['startRva'],w['endRva'])for w in p['windows']))
  image.check_windows(p['windows'],label=LABEL);need('unique-program-role',False,p['role']in programs);programs[p['role']]=p;regions[p['role']]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in p['windows']]
 for row in profile['methods']:image.validate_method_row(row,label=LABEL)
 for role,row in profile['programMethods'].items():need('actual-program-method:'+role,row[3],programs[role]['entryRva'])
 for d in profile['abiMethods']:scalar.owned_method_abi(image,ctx,d['index'],d['owner'],tuple(d['return']),[tuple(p)for p in d['parameters']],LABEL+'.ABI')
 for d in profile['wrappers']:
  w=build.wrappers[d['wrapper']];need('wrapper-original',d['original'],w.wrapped_type);need('wrapper-member-order',d['members'],[[m.name,m.declared_type]for m in w.members]);need('holder-field',tuple(d['holder']),ctx.field(w.name+'::__instance'));need('reference-original',False,ctx.is_value_type(d['original']))
  for role in d['readerRoles']:primitive_param.reader_abi(image,ctx,md.methods[role],w)
 for row in profile['fields']:need('owned-original-field',(row[0],row[2],row[3]),ctx.field(row[0]+'::'+row[1]))
 for d in profile['entries']:need('current-canonical-registration',d['registration'],json.loads(json.dumps(generic.resolve(d['definition'],d['classArguments'],d['methodArguments']))))
 authenticate_contexts(profile['contexts'])
 for u in profile['usages']:validate_typed_usage_context(image,u,label=LABEL)
 ref=profile['referenceRoutes'];core=reference.validate_reference_routes(image,ref,profile['compositions']);s={k:base+v for k,v in ref['symbolRvas'].items()}
 def decode(value):
  if isinstance(value,list):return[decode(v)for v in value]
  if not isinstance(value,dict):return value
  if set(value)=={'regions'}:return regions[value['regions']]
  if set(value)=={'entry'}:return base+programs[value['entry']]['entryRva']
  if set(value)=={'site'}:return base+value['site']
  return{k:decode(v)for k,v in value.items()}
 need('complete-source-model-domain',set(MODELS),{r['model']for r in profile['calls']})
 domains={'root':{'rootReader'},'uintDictionary':{'bodyTypeDictionary'},'referenceDictionary':{'subEntryDictionary'},'factory':{'rootCtor','rootCreate','entryCtor','entryCreate'},'getter':{'rootGetValue','entryGetValue'},'tagList':{'tagList'},'entry':{'entryReader'},'entrySetter':{'entrySetter'},'readValue':{'readValue'},'packableReturn':{'packable'},'referenceList':{'referenceList'}}
 for model,expected in domains.items():need('source-model-programs:'+model,expected,{c['program']for c in profile['calls']if c['model']==model})
 for model,key,expected in(('uintDictionary',('null',),{(False,),(True,)}),('referenceDictionary',('null',),{(False,),(True,)}),('tagList',('null','new'),{(False,False),(False,True),(True,False),(True,True)}),('entry',('new','null'),{(False,False),(False,True),(True,False),(True,True)}),('referenceList',('count','new','grow'),{(-1,False,False),(-1,True,False),(0,False,False),(0,True,False)})):need('complete-path-domain:'+model,expected,{tuple(c['kwargs'][k]for k in key)for c in profile['calls']if c['model']==model})
 for c in profile['calls']:
  need('model-owned-regions',{'regions':c['program']},c['args'][0])
  if c['model']!='packableReturn':need('model-owned-entry',{'entry':c['program']},c['args'][1])
  if c['model']=='factory':need('factory-method-path',c['program'].endswith('Create'),c['kwargs']['create'])
  if c['model']=='root':need('root-reader-fields',offsets,c['kwargs']['offsets'])
  elif c['model']in('uintDictionary','referenceDictionary'):need('dictionary-reader-fields',offsets,c['args'][2])
  elif c['model']in('tagList','referenceList'):need('list-reader-fields',list_offsets,c['args'][2])
  try:proof=MODELS[c['model']](*decode(c['args']),**decode(c['kwargs']))
  except ValueError as error:raise ValueError(f'{LABEL}.source:{c["model"]}:{c["program"]}:expected={error}:actualWindows={programs[c["program"]]["windows"][:2]}')from error
  proofs.append(dict(model=c['model'],program=c['program'],proof=proof))
  if c['model']=='factory':
   u=derive_typed_usage_context(image,proof['classLoad']-base,label=LABEL);stem='root'if c['program'].startswith('root')else'entry';d=profile['wrappers'][0 if stem=='root'else 1];need('typed-original-allocation',d['original'],u['typeName']);need('actual-allocation-class-cell',base+u['usageCellRva'],c['args'][2]['classCell']);need('actual-original-constructor',base+programs[stem+'OriginalCtor']['entryRva'],c['args'][2]['constructor'])
  elif c['model']=='entry'and proof['typedDictionaryUsage']:
   u=derive_typed_usage_context(image,proof['typedDictionaryUsage']['site']-base,label=LABEL);d=profile['wrappers'][1];need('typed-entry-list-call',('MemoryPack.MemoryPackReader','ReadPackable',[],[d['members'][0][1]]),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']))
 main,=[r['proof']for r in proofs if r['model']=='root'];fields=profile['fieldPlan'];need('actual-root-field-plan',fields,[dict(name=m.name,type=m.declared_type,mode='out8'if m.name in('bodyTypeActDataDict','subPerformEntries')else'reference'if m.kind in('list','object')else'enum'if m.kind=='enum'else'float'if m.kind=='float32'else m.kind,offset=ctx.field(profile['original']+'::'+m.name)[2],source=m.name if m.name in('bodyTypeActDataDict','subPerformEntries')else'packable'if m.kind=='list'else'reference'if m.kind=='object'else'enum'if m.kind=='enum'else'float'if m.kind=='float32'else m.kind)for m in build.wrappers[profile['wrapper']].members]);rec=vector_recorder(image);o=scalar.reader_offsets(image,LABEL)
 for f,t in zip(fields,main['fields'],strict=True):
  contexts=[derive_typed_usage_context(image,c['instruction']-base,label=LABEL)for c in t['contextCells']]
  for u in contexts:
   expected=('Beyond.SerializeFieldDictionary`2','DeserializeV2',f['type'].split('<',1)[1][:-1].split(',',1),[])if f['mode']=='out8'else('MemoryPack.MemoryPackReader','ReadPackable'if f['source']=='packable'else'ReadUnmanaged'if f['mode']=='enum'else'ReadValue',[],[f['type']]);need('actual-typed-field-call:'+f['name'],expected,(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']))
  p=t['sourceTarget'];r=rec(p-base,fragments=True)
  if f['mode']=='bool':scalar.boolean_source(image,r,o,f['name'])
  elif f['mode']=='float':primitive_param.single_source(image,r,o)
  elif f['mode']=='enum':
   enum=ctx.index.types[f['type']];ef=[v for v in md.fields_for(enum)if not ctx.field_attributes(v.type_index)&16];need('enum-Int32-underlying',[(f['type'],'int',16)],[ctx.field(f['type']+'::'+md.string(v.name_index))for v in ef]);scalar.integer_source(image,r,o,f['name'],width=4)
  elif f['mode']=='reference':build.prove_reader_clone_target(p,'MemoryPack.MemoryPackReader.'+('ReadPackable'if f['source']=='packable'else'ReadValue'),result_abi='reference')
  else:need('dictionary-static-void-byref',profile['dictionarySources'][f['name']]['entryRva'],p-base)
 for c in profile['calls']:
  if c['model']=='readValue':need('ReadValue-dispatch',s['dispatch'],c['args'][2]['dispatch']);need('actual-default-entry-source',main['fields'][6]['sourceTarget'],base+programs[c['program']]['entryRva'])
  elif c['model']=='packableReturn':need('ReadPackable-dispatch',s['dispatch'],c['args'][2])
  elif c['model']=='entry':need('same-entry-packable',profile['packableRva'],c['args'][2]['packable']-base)
 read_context,provider=profile['readValueContexts'];validate_generic_contexts(image,[read_context,provider],label=LABEL);validate_read_value_context(image,read_context,provider,generic,fail=need)
 headers={c['args'][2]['header']for c in profile['calls']if c['model']=='entry'}|{c['args'][3]['header']for c in profile['calls']if c['model']=='uintDictionary'}
 for p in headers:primitive_param.object_header_source(image,vector_recorder(image)(p-base,fragments=True),offsets)
 build.prove_reader_clone_target(base+profile['packableRva'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
 lf,ls=profile['listContexts'];validate_generic_contexts(image,[lf,ls],label=LABEL);validate_list_element_context(image,lf,generic,fail=need);validate_capacity_constructor_context(image,lf,ls,generic,fail=need);validate_list_formatter_base_context(image,lf,generic,fail=need)
 # Dictionary helpers retain their own class-owned K/V in output, construction and unused providers.
 dc=profile['dictionaryContext'];authenticate_contexts([dc]);slots={e['relativeSlot']:e for e in dc['entries']}
 allocation=slots[21]['type'];need('dictionary-allocation-class',dc['typeName'],allocation['definition']['name']);need('dictionary-allocation-owned-VARs',[(dc['definition'],0),(dc['definition'],1)],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in allocation['classArguments']])
 for slot,owner,name,ordinals,kind in((22,dc['typeName'],'.ctor',[0,1],'classArguments'),(23,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',[0],'methodArguments'),(24,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',[1],'methodArguments')):
  d=slots[slot];need('dictionary-owned-slot',(owner,name),(d['typeName'],d['methodName']));need('dictionary-owned-VARs',[(dc['definition'],n)for n in ordinals],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in d[kind]])
 for d in profile['dictionarySources'].values():
  m=md.methods[d['definition']];need('dictionary-static-ABI',(True,'void',2),(bool(m.flags&16),ctx.type_name(m.return_type),m.parameter_count));ps=list(md.parameters_for(m));need('dictionary-reader-byref',('MemoryPack.MemoryPackReader',17,32),(ctx.type_name(ps[0].type_index),*image.pe.bytes_at_va(ctx.type_pointer(ps[0].type_index),16)[10:12]));out=symbols.type(ctx.type_pointer(ps[1].type_index));need('dictionary-self-out-byref',32,image.pe.bytes_at_va(ctx.type_pointer(ps[1].type_index),16)[11]);need('dictionary-output-owner',dc['typeName'],out['definition']['name']);need('dictionary-output-VARs',[(dc['definition'],0),(dc['definition'],1)],[(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])for a in out['classArguments']])
 ip=CONTRACTS_DIR/'levelscript_int_list_native.json';raw=ip.read_bytes();intfact=json.loads(raw);need('Int32-native-inputs',fact['nativeInputs'],intfact['nativeInputs']);int_result=levelscript_int_list_native._validate_native(image,intfact);need('Int32-contract-bookend',raw,ip.read_bytes())
 tag=tag_joins.validate_one(image,fact['nativeInputs'],fact['tagListOne']);need('tag-shared-context-helper-joins',{k:s[k]for k in('context','indexed','hotProvider','prepare','dispatch')},tag['helpers'])
 actor=actor_joins.validate_one(image,fact['nativeInputs'],fact['actorListOne'],profile,main)
 action=action_joins.validate_one(image,fact['nativeInputs'],fact['loopActionsOne'],profile,main)
 return dict(actionListOne=action,fields=fields,proofs=proofs,referenceCore=core,intList=int_result,tagListOne=tag,actorListOne=actor)

def validate(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 try:
  before=snapshot_complete_reader_inputs()
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);need('schema','endfield.char-interact-perform-sparse-native.v4',fact['schema']);need('status','conditional-current-build-wire',fact['status']);pins=fact['nativeInputs'];need('native-input-set',{'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'},set(pins))
  if(gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.both-native-paths-required')
  folder=Path(game_root)if game_root else None;gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly else folder.parent/'GameAssembly.dll'if folder else None,metadata=metadata if metadata else folder/'il2cpp_data/Metadata/global-metadata.dat'if folder else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  paths=[Path(__file__)]+[Path(m.__file__)for m in(root,dictionaries,factories,source,tag_joins,tag_source,actor_joins,actor_source,action_joins,action_source,provider_source)]+[CONTRACTS_DIR/n for n in('levelscript_int_list_native.json','memorypack_reader_clones_native.json')];saved=[p.read_bytes()for p in paths];result=derive(open_native_image(gate.gameassembly,gate.metadata),fact);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes()or saved!=[p.read_bytes()for p in paths]or before!=snapshot_complete_reader_inputs():raise ValueError(LABEL+'.inputs-changed-during-validation')
  return dict(status='validated',fields=result['fields'],actorFields=result['actorListOne']['fields'],actionFields=result['actionListOne']['fields'],nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)
