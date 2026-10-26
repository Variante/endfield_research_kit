"""Exact three Module value canonical adapters, with explicit callback conditions.

Each selected nominal wrapper/source is independent. The canonical callback
zeros every Original byte on FF or transfers its complete hidden getter. A
reference-containing value retains its exact selected barrier address; it is
never treated as a reference8 element. List/array and parent joins are separate.
"""
import json,struct

from scripts.game_data.memorypack import levelscript_module_value_transfer_programs as programs

SCHEMA='endfield.story-module-value-transfer.v1'


def need(key,condition):
 if not condition:raise ValueError('storyModuleValueTransfer.'+key)


def derive(image,pins,*,type_name):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,event_args_paths,primitive_param
 from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_global_buff_id_sources as provider
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 _publication_gate(image,pins);need('finite-owned-nominal',type_name in programs.WIDTHS)
 if type_name==programs.OPERA:
  from scripts.game_data.memorypack.levelscript_opera_value_sources import derive_record
  record=derive_record(image,pins)
 else:
  from scripts.game_data.memorypack.levelscript_module_value_wrapper_sources import derive_record
  record=derive_record(image,pins,type_name=type_name)
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
 pair=derive_pair(image,type_name,wrapper.name);forwarding=pointer.registered_pair(image,pair,wrapper,label='storyModuleValueTransfer.pair')
 face,=pair['composition']['interfaces'];td=md.types[wrapper.type_definition]
 need('own-exact-getter-metadata',face['getValueMethodIndex']==record['leaves']['GetValue']['method'][0]
  and face['originalType']==type_name and face['wrapperType']==wrapper.name)
 section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8
 offsets=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8]))
 need('unique-owned-interface-hit',offsets.count((face['interfaceTypeIndex'],face['interfaceOffset']))==1)
 ordinal=offsets.index((face['interfaceTypeIndex'],face['interfaceOffset']))
 adapter_context,context_proof=buff_ptr_sources._adapter_context(image,ge);sources={};registrations={};targets={}
 for role,method_name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
  method=buff_ptr_sources._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',method_name)
  registration=ge.resolve(method.index,[type_name,'object'],[]);registrations[role]=registration
  targets[role]=registration['pointer'];sources[role]=pointer.owned(image,targets[role])
 adapters=[programs.adapter_program(sources['adapter']['regions'],targets['adapter'],type_name=type_name,**p)
  for p in({},dict(create=False),dict(null=True))]
 nonnull=[programs.nonnull_program(sources['nonnull']['regions'],targets['nonnull'],type_name=type_name,wrapper_null=n)for n in(False,True)]
 symbols={}
 for path in adapters+nonnull:
  for role,target in path['symbolTargets'].items():need('coherent-actual-helper:'+role,role not in symbols or symbols[role]==target);symbols[role]=target
 need('actual-called-canonical-nonnull',symbols['nonnull']==targets['nonnull'])
 need('named-TypeFromHandle-helper',symbols['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
 for role in('readNull','conversion','wrapperInvoke'):sources[role]=pointer.owned(image,symbols[role])
 calls=[control_transfer(row)['target']for row in sources['conversion']['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8']
 need('actual-owned-preparation-call',bool(calls));symbols['prepare']=calls[0]
 conversion=programs.conversion_program(sources['conversion']['regions'],symbols['conversion'],type_name=type_name,prepare=symbols['prepare'],ordinal=ordinal)
 nulls=[programs.null_program(sources['readNull']['regions'],symbols['readNull'],null=n,near=type_name==programs.AIRWALL)for n in(False,True)]
 for path in nulls:
  for role,target in path['symbolTargets'].items():need('coherent-null-helper:'+role,role not in symbols or symbols[role]==target);symbols[role]=target
 invocation=deserialize_slot(sources['wrapperInvoke']['regions'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
  callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
 initialized=None
 if 'classInit'in symbols:
  sources['classInit']=pointer.owned(image,symbols['classInit'])
  initialized=provider.ready_class_init(sources['classInit']['regions'],symbols['classInit'])
 sources['peek']=pointer.owned(image,symbols['peek']);reader_offsets=scalar.reader_offsets(image,'storyModuleValueTransfer')
 peek=event_args_paths.peek(sources['peek']['regions'],symbols['peek'],reader_offsets)
 header=vector_recorder(image)(symbols['header']-base);primitive_param.object_header_source(image,header,reader_offsets)
 barrier=None
 if 'barrier'in symbols:
  barrier_source,barrier_program,_=_fast_barrier(image,symbols['barrier'])
  barrier=dict(source=barrier_source,program=barrier_program)
  need('same-owned-wrapper-reference-barrier',symbols['barrier']==base+record['symbolRvas']['barrier'])
 classes=[]
 for paths,site_key,cell_key,expected in((adapters,'typeClassInstructionVa','typeClassCellVa','System.Type'),
   (nonnull,'providerClassInstructionVa','providerClassCellVa','MemoryPack.MemoryPackFormatterProvider')):
  site=next(p[site_key]for p in paths if p[site_key]is not None)
  usage=derive_typed_usage_context(image,site-base,label='storyModuleValueTransfer.'+expected)
  need('exact-selected-class:'+expected,(usage['tag'],usage['typeName'])==(1,expected)
   and all(p[cell_key]in(None,base+usage['usageCellRva'])for p in paths));classes.append(usage)
 _publication_gate(image,pins);width=programs.WIDTHS[type_name]
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-module-value-transfer',nativeInputs=pins,
  typeName=type_name,wrapperName=wrapper.name,managedBytes=width,layout=record['layout'],
  canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=width,positiveMemberCount=2 if type_name==programs.OPERA else 3 if type_name==programs.AIRWALL else 5,
  canonicalCallbackTargetRva=targets['adapter']-base,canonicalCallbackAdmitted=True,wrapperSourceAdmitted=True,
  actualCallbackEqualsCanonicalRequired=True,liveFormatterSelectionObserved=False,elementGrammarAdmitted=False,
  parentFieldAdmitted=False,containerAdmitted=False,wholeOwnerAdmitted=False,record=record,
  proof=dict(pair=pair,forwarding=forwarding,registrations=registrations,adapterContext=adapter_context,adapterContextProof=context_proof,
   interfaceOrdinal=ordinal,programs=dict(adapter=adapters,nonnull=nonnull,conversion=conversion,readNull=nulls),
   wrapperInvocation=invocation,initializedClassHelper=initialized,actualClasses=classes,peek=peek,header=header,barrier=barrier,
   symbolRvas={role:target-base for role,target in symbols.items()},
   sourceWindows={role:body['windows']for role,body in sources.items()},
   sourceRegions={role:[[at,data.hex().upper()]for at,data in body['regions']]for role,body in sources.items()}),
  evidenceBoundary=dict(exact='Own nominal inline value wrapper/source, exact eager pair/concrete formatter and interface getter metadata, canonical FF/default output and complete hidden getter transfer of all managed bytes, selected reference barrier and full normal frames.',
   conditional='Actual element slot5 callback equals this selected canonical body; coherent closed MethodInfo represents the exact Original/wrapper pair and selects its wrapper/getter. Ready metadata/classes/provider, normal helper/activation/context-resolution/preparation ABI, sufficient disjoint buffered Reader/input/output/frame and disabled collector. No runtime callback or provider selection is observed.',
   unresolved=['enclosing array/list contexts/constructor/Add/count/field joins','Opera ParamKeyValue element grammar if selected','runtime helper/provider/callback behavior','whole Module/physical EOF/publication']))))
