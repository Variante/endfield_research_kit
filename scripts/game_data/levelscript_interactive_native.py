"""Authenticate the current sparse pooled LevelScript interactive dictionary.

The contract (schema v2) declares ``dependencies`` as the array of
``{"path", "schema"}`` entries that ``scripts.game_data.dependency_snapshot``
resolves; each named contract must carry that schema, ``exact-current-build``
and the same ``nativeInputs``, and its bytes must be unchanged at exit.
"""
import copy,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols,validate_claims
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.memorypack import levelscript_interactive_sources as source,scalar_param_native as scalar,primitive_param,pooled_source_helper,reference_adapter_sources as reference,int_list_sources,lang_key_list_sources
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.record_sources import typed_source_context
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.list_reference_sources import validate_list_element_context
from scripts.game_data.levelscript_param_list_native import _validate_native as graph_validate
from scripts.game_data.levelscript_int_list_native import _validate_native as int_validate
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_interactive_native.json'
SCHEMA='endfield.levelscript-interactive-pooled-native.v2'
KIND='LevelScriptData.interactives.sparse'
LABEL='levelscriptInteractiveNative'
def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)
def _validate_native(image,fact):
 base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;build=Build(image,fact['nativeInputs']);entries=GenericEntries(image);w=build.wrappers[fact['wrapper']];fields=[]
 for m in w.members:
  owner=build.wrappers[m.declaring_wrapper].wrapped_type;fields.append(dict(name=m.name,typeName=m.declared_type,owner=owner,field=list(ctx.field(owner+'::'+m.name)),kind=m.kind,declaringWrapper=m.declaring_wrapper))
 need('owned-fields',fact['fields'],fields);need('parent-kind',False,ctx.is_value_type(w.wrapped_type));need('original-parent','Beyond.Gameplay.LevelEntityData',ctx.parent(w.wrapped_type));methods={md.string(m.name_index):m for m in md.methods_for(md.types[w.type_definition])};primitive_param.reader_abi(image,ctx,methods['Deserialize'],w)
 scalar.owned_method_abi(image,ctx,methods['GetValue'].index,w.type_definition,(w.wrapped_type,18,True),[],LABEL+'.GetValue')
 for name in('.ctor','CreateInstance'):scalar.owned_method_abi(image,ctx,methods[name].index,w.type_definition,('void',1,False),[],LABEL+'.'+name)
 root_wrapper,=[r for r in build.wrappers.values()if r.wrapped_type=='Beyond.Gameplay.LevelScriptData'];root_methods={md.string(m.name_index):m for m in md.methods_for(md.types[root_wrapper.type_definition])};primitive_param.reader_abi(image,ctx,root_methods['Deserialize'],root_wrapper);need('root-original-holder',(root_wrapper.name,root_wrapper.wrapped_type,16),ctx.field(root_wrapper.name+'::__instance'))
 for f in fact['holderFields']:need('owned-holder',f['field'],list(ctx.field(f['owner']+'::'+f['name'])))
 for row in fact['methods']:image.validate_method_row(row,label=LABEL)
 bodies={}
 for name,record in fact['sources'].items():
  windows=record['windows'];image.check_windows(windows,label=LABEL+'.'+name)
  if record['ownership']=='completeUnwindFamily':need('complete-owned-'+name,sorted((p['startRva'],p['endRva'])for p in windows),sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(record['entryRva'])['ranges']))
  elif record['ownership']!='selectedCollectorDisabledReturnPrefix':raise ValueError(LABEL+'.source-ownership:'+name)
  bodies[name]=([(base+p['startRva'],image.pe.bytes_at_va(base+p['startRva'],p['endRva']-p['startRva']))for p in windows],base+record['entryRva'])
 s={k:base+v for k,v in fact['symbols'].items()};offsets=scalar.reader_offsets(image,LABEL);reader=ctx.index.types['MemoryPack.MemoryPackReader'];offsets['totalLength']=runtime_type_field_offsets(md,image.pe,image.registration,reader.index)['totalLength']-16;need('reader-fields',fact['readerFields'],offsets);p={}
 p['element']=[source.element_program(*bodies['element'],s,fields,null=n,new=c)for n in(False,True)for c in(False,True)]
 ds=dict(s,constructor=s['dictionaryConstructor']);p['uintDictionary']=[source.dictionary_u32_program(*bodies['uintDictionary'],ds,count=-1)]+[source.dictionary_u32_program(*bodies['uintDictionary'],ds,count=n,new=v)for n in(0,1)for v in(False,True)];p['intDictionary']=[source.dictionary_i32_program(*bodies['intDictionary'],s,offsets,count=n,new=v)for n in(-1,0,1,2)for v in(False,True)]
 p['header']=source.dictionary_header_program(*bodies['header'],offsets);p['uintDispatch']=source.u32_dispatch_program(*bodies['uintDispatch'],s,offsets);p['uintCallback']=source.unmanaged_u32_program(*bodies['uintCallback'],s,offsets);p['intCallback']=int_list_sources.integer(*bodies['intCallback'],offsets);p['keyProvider']=source.key_provider_program(*bodies['keyProvider'],s);p['enumKeyProvider']=source.enum_key_provider_program(*bodies['enumKeyProvider'],s);p['valueProvider']=lang_key_list_sources.wrapper_provider_program(*bodies['valueProvider'],s);p['readValue']=source.read_value_reference_program(*bodies['readValue'],s);p['keyBackendForward']=source.key_backend_forward_program(*bodies['keyBackendForward'],s['backend']);p['dictionaryConstructor']=[source.dictionary_capacity_program(*bodies['dictionaryConstructor'],s,positive=v,same_comparer=e)for v in(False,True)for e in(False,True)];p['dictionaryAdd']=source.dictionary_add_program(*bodies['dictionaryAdd'],s)
 p['wrapperConstructor']=[source.wrapper_constructor_program(*bodies['wrapperConstructor'],s,default_comparer_null=v)for v in(False,True)];p['create']=source.wrapper_create_program(*bodies['create'],s);p['baseSetter']=source.base_setter_program(*bodies['baseSetter'],s['barrier']);p['getter']=source.getter_coherent_program(*bodies['getter']);p['barrier']=source.collector_disabled_program(*bodies['barrier']);p['parent']=source.parent_program(bodies['parent'][0],base+fact['parentEntryRva'],s['packable'],ctx.field('Beyond.Gameplay.LevelScriptData::interactives')[2]);source.parent_aliases(image,bodies['parent'][0],p['parent']['readCall'])
 recorder=vector_recorder(image);scalar.integer_source(image,recorder(s['qword']-base),offsets,LABEL+'.qword',width=8);scalar.boolean_source(image,recorder(s['bool']-base),offsets,LABEL+'.bool');primitive_param.single_source(image,recorder(s['float']-base),offsets);scalar.advance_source(image,recorder(s['advance']-base,fragments=True),offsets,LABEL+'.advance');pooled_source_helper.validate_on_image(image,s['pool'],fact['nativeInputs'])
 for enum in fact['enums']:need('enum',enum,build.derive_enum(enum))
 for name,boxed,native,expected in fact['valueLayouts']:
  td=ctx.index.types[name];need('value-type',True,ctx.is_value_type(name));size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);need('value-size',(boxed,native),(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4)))
  for field in expected:need('value-owned-field',field[1:],list(ctx.field(name+'::'+field[0]))[1:])
 for usage in fact['usageContexts']:validate_typed_usage_context(image,usage,label=LABEL)
 usage_map={u['instructionRva']:u for u in fact['usageContexts']};need('unique-usage-instructions',len(fact['usageContexts']),len(usage_map))
 for child in p['element'][0]['typedUsages']:
  u=usage_map[child['instruction']-base];declared=next(f for f in fields if f['name']==child['field']);method='ReadValue'if child['kind']=='condition'else'ReadPackable';need('typed-child',(6,'MemoryPack.MemoryPackReader',method,[],[declared['typeName']],child['cell']-base),(u['tag'],u['typeName'],u['methodName'],u['classArguments'],u['methodArguments'],u['usageCellRva']));build.prove_reader_clone_target(s[child['kind']],'MemoryPack.MemoryPackReader.'+method,result_abi='reference')
 need('parent-owned-type','System.Collections.Generic.Dictionary`2<uint,Beyond.Gameplay.LevelInteractiveData>',ctx.field('Beyond.Gameplay.LevelScriptData::interactives')[1])
 u=usage_map[fact['parentEntryRva']];need('typed-parent',(6,'ReadPackable',['System.Collections.Generic.Dictionary`2<uint,Beyond.Gameplay.LevelInteractiveData>'],p['parent']['typeUsageCell']-base),(u['tag'],u['methodName'],u['methodArguments'],u['usageCellRva']))
 expected_allocations=dict(base='Beyond.Gameplay.LevelEntityData',original='Beyond.Gameplay.LevelInteractiveData',defaultProperties='System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>',defaultComponents='System.Collections.Generic.Dictionary`2<Beyond.Gameplay.InteractiveComponentType,System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>>')
 for allocation in p['wrapperConstructor'][0]['allocations']:
  u=usage_map[allocation['instruction']-base];need('typed-allocation',(1,expected_allocations[allocation['role']],allocation['cell']-base),(u['tag'],u['typeName'],u['usageCellRva']))
 for site,owner,args in zip(p['wrapperConstructor'][0]['methodContexts'],('System.Collections.Generic.List`1','System.Collections.Generic.Dictionary`2'),(['Beyond.Gameplay.ParamKeyValue'],['Beyond.Gameplay.InteractiveComponentType','System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>']),strict=True):
  u=usage_map[site-base];need('default-constructor-context',(6,owner,'.ctor',args,[]),(u['tag'],u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']))
 u=usage_map[p['create']['allocationInstruction']-base];need('typed-create',(1,expected_allocations['original'],p['create']['originalTypeCell']-base),(u['tag'],u['typeName'],u['usageCellRva']))
 p['dictionaryContext']=source.dictionary_context(image,fact['dictionaryContext']);symbols=ContextSymbols(image)
 for row in fact['methodContexts']:validate_claims(row,symbols.context(row['definition'],is_method=True),label=LABEL+'.method-context')
 fail=lambda check,expected,actual:need(check,expected,actual);p['readValueContext']=validate_read_value_context(image,*fact['methodContexts'],entries,fail=fail);validate_claims(fact['listContext'],symbols.context(fact['listContext']['definition']),label=LABEL+'.list-context');p['listContext']=validate_list_element_context(image,fact['listContext'],entries,fail=fail)
 for role,definition,ca,ma in fact['entries']:need('actual-entry-'+role,bodies[role][1],entries.resolve(definition,ca,ma)['pointer'])
 for flow,composition in zip(fact['registrations'],fact['compositions'],strict=True):validate_eager_wrap_registration(image,flow,label=LABEL);validate_registered_formatter_composition(image,composition,label=LABEL)
 join=fact['compositions'][0]['interfaces'][0];forward=md.methods[join['formatterDeserializeMethodIndex']];need('forwarder-abi',(False,5,2,'void'),(bool(forward.flags&16),forward.slot,forward.parameter_count,ctx.type_name(forward.return_type)))
 for arg,name,kind in zip(md.parameters_for(forward),('MemoryPack.MemoryPackReader',w.name),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(arg.type_index),16);need('forwarder-byrefs',(name,kind,32,ctx.index.types[name].index),(ctx.type_name(arg.type_index),raw[10],raw[11],int.from_bytes(raw[:8],'little')))

 deps={};raws={}
 need('dependency-shape',True,isinstance(fact['dependencies'],list)and all(isinstance(d,dict)and set(d)=={'path','schema'}and isinstance(d['path'],str)and isinstance(d['schema'],str)for d in fact['dependencies']))
 need('dependency-paths',['levelscript_param_list.json','levelscript_int_list_native.json','levelscript_blackboard_native.json'],[d['path']for d in fact['dependencies']])
 for filename,schema in((d['path'],d['schema'])for d in fact['dependencies']):
  path=CONTRACTS_DIR/filename;raws[filename]=path.read_bytes();deps[filename]=json.loads(raws[filename]);need('dependency-schema',(schema,'exact-current-build'),(deps[filename]['schema'],deps[filename]['status']));need('dependency-inputs',fact['nativeInputs'],deps[filename]['nativeInputs'])
 graph=deps['levelscript_param_list.json'];graph_validate(image,graph);integer=deps['levelscript_int_list_native.json'];int_validate(image,integer);ref=copy.deepcopy(deps['levelscript_blackboard_native.json']['referenceRoutes']);ref['wrappers']=[];p['referenceCore']=reference.validate_reference_routes(image,ref,[]);rs={k:base+v for k,v in ref['symbolRvas'].items()};regions={r['entryRva']:[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in r['windows']]for r in ref['ownedPrograms']};p['conversion']=reference.conversion(regions[rs['conversion']-base],rs['conversion'],base+ref['conversionPrepareRva'],bodies['getter'][1],ordinal=fact['interfaceOrdinal']);p['dispatch']=deserialize_slot(regions[rs['dispatch']-base],rs['dispatch'],prepare=rs['prepare'],callback=bodies['forwarder'][1]);rows=[r for at,data in bodies['forwarder'][0]for r in image.body_index._decode(at,len(data))];p['forwarder']=prove_zero_wrapper_forwarder(rows,{k:base+v for k,v in fact['forwarderSymbols'].items()},bodies['element'][1]);need('same-dispatch',rs['dispatch'],s['referenceDispatcher'])
 graph_usage,=[u for u in graph['usageContexts']if u.get('methodArguments')==['System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>']]
 for usage in fact['usageContexts']:
  if usage.get('methodArguments')==graph_usage['methodArguments']:need('same-KV-list-source',graph_usage['methodSpec'],usage['methodSpec'])
 factory=integer['factory'];regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in factory['windows']];mapping=int_list_sources.factory_pair(regions,base+fact['dictionaryFactory']['entryRva'],type_handle=base+factory['typeHandleRva'],add=base+factory['addRva']);need('dictionary-open-mapping-cells',[base+u['usageCellRva']for u in fact['dictionaryFactory']['usages']],[mapping[k]for k in('keyTypeCell','valueTypeCell','addMethodInfoCell')]);need('dictionary-open-types',['System.Collections.Generic.Dictionary`2','MemoryPack.Formatters.DictionaryFormatter`2'],[u['typeName']for u in fact['dictionaryFactory']['usages'][:2]])
 for u in fact['dictionaryFactory']['usages']:validate_typed_usage_context(image,u,label=LABEL)
 for filename,raw in raws.items():need('dependency-stable',raw,(CONTRACTS_DIR/filename).read_bytes())
 return json.loads(json.dumps(p))
def validate(*,game_root=None,gameassembly=None,metadata=None,contract_path=CONTRACT_PATH):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);need('schema',(SCHEMA,'exact-current-build',KIND),(fact['schema'],fact['status'],fact['codecKind']));need('layout',json.dumps(dict(dictionaryCounts=[-1,0,1],componentCounts=[-1,0,1,2],intListCounts=[-1],condition='null-only',stringEncoding='int32-pool-index'),sort_keys=True),json.dumps(fact['layout'],sort_keys=True))
  if(gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.both-native-paths-required')
  root=Path(game_root)if game_root is not None else None;pins=fact['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,codecKinds=[],failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return dict(codecKinds=[],**failed)
  proof=_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact);need('selected-programs',fact['programs'],proof);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,codecKinds=[],detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return dict(codecKinds=[],**failed)
  need('contract-stable',raw,path.read_bytes());return dict(status='validated',codecKinds=[KIND],layout=fact['layout'],nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:return dict(codecKinds=[],**native_validation_failure(error,label=LABEL,source_path=contract_path))
