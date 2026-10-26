"""Own two exact Module value-list sources and their conditional callbacks.

The scalar wrappers/canonical conversions, closed List contexts, actual count
loop, capacity constructor, dispatch, complete Add/storage and frames are all
authenticated independently. Element wire grammar and parent fields are joined
by the Module composer. No other list is admitted by a managed byte width.
"""
import json

from scripts.game_data.memorypack import levelscript_module_value_list_programs as programs

SCHEMA='endfield.story-module-value-list-source.v1'
LIMIT=4096


def need(key,condition):
 if not condition:raise ValueError('storyModuleValueList.'+key)


def derive(image,pins,*,typed_request,call_target,element_type):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import scalar_param_native as scalar,float_list_sources,int_list_sources,pooled_global_buff_id_sources as provider_helpers
 from scripts.game_data.memorypack import levelscript_module_value_transfer_sources as transfer,leveldata_tracking_list_sources as shared
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack.skill_value_list_context import derive as list_context,bind_list_add_abi
 from scripts.game_data.memorypack.leveldata_vector_tuple_list_sources import normal_call_after
 from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_header_program
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 _publication_gate(image,pins);need('finite-selected-value',element_type in programs.WIDTHS)
 base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=element_type)
 value=transfer.derive(image,pins,type_name=element_type);effect=element_type==programs.EFFECT
 paths=[programs.list_program(body['regions'],body['pointer'],type_name=element_type,count=n)for n in(-1,0,1,2,3)]
 s=paths[-1]['symbolTargets']
 need('same-complete-selected-helper-sites',all(all(s.get(k)==v for k,v in p['symbolTargets'].items())for p in paths))
 induction=prove_induction(paths[1:],initial='458bfd'if effect else'33ed',increment='41ffc7'if effect else'ffc5',
  comparison='443b7d6f'if effect else'413bef',counter='r15d'if effect else'ebp',
  saved_count='unchanged entry RSP+16 Int32'if effect else'immutable R15D loaded once from entry RSP+16 before that dead count home is reused by captured high8',
  max_count=LIMIT,backedge_sites=[paths[2]['backedgeInstructionVa']])
 sources={role:owned(image,s[role])for role in('header','constructor','provider','Add','dispatch')}
 def calls(source):return[control_transfer(r)['target']for r in source['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 slots={r['relativeSlot']:r for r in context['context']['entries']}
 offset=scalar.reader_offsets(image,'storyModuleValueList');offset['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 header=dictionary_header_program(sources['header']['regions'],s['header'],offset)
 add_forwarder=None;storage=None
 if effect:
  targets=calls(sources['Add']);need('one-actual-Add48-copy-delegate',len(targets)==1)
  sources['AddCore']=owned(image,targets[0]);add_forwarder=programs.effect_add_forwarder(sources['Add']['regions'],s['Add'],target=targets[0])
  core=sources['AddCore'];rows=core['rows'];index=next(i for i,r in enumerate(rows)if r['bytes'].replace(' ','').lower()=='4c8d442420')
  call=next(r for r in rows[index:]if bytes.fromhex(r['bytes'])[:1]==b'\xe8');actual_storage=control_transfer(call)['target']
  sources['storage']=owned(image,actual_storage)
  add=programs.effect_add_core(core['regions'],core['pointer'],storage=actual_storage)
  storage=programs.effect_storage(sources['storage']['regions'],actual_storage,barrier=s['barrier'])
 else:add=programs.airwall_add(sources['Add']['regions'],s['Add'])
 abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
 definitions=dict(list=context['registration']['methodDefinitionIndices'][0],
  callback=value['proof']['registrations']['adapter']['methodDefinitionIndices'][0],capacity=slots[1]['methodSpec'][0],
  Add=slots[6]['methodSpec'][0],Clear=slots[2]['methodSpec'][0])
 abis=float_list_sources._method_abis(image,ctx,definitions,context['context'])
 fields=[];list_td=ctx.index.types['System.Collections.Generic.List`1']
 for name,kind in(('_items',29),('_size',8),('_version',8)):
  field,=[f for f in md.fields_for(list_td)if md.string(f.name_index)==name]
  scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'storyModuleValueList.'+name,reference=kind==29)
  fields.append(dict(owner='System.Collections.Generic.List`1',field=name,definition=field.index,
   typeRawHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()))
 formal,=next(r for r in context['listContext']['entries']if r['relativeSlot']==0)['type']['classArguments']
 fields=shared.list_field_declarations(fields,owned_parameter_pointer=formal['typePointerVa'])
 constructor_registration=ge.resolve(slots[1]['methodSpec'][0],[element_type],[])
 need('exact-owned-closed-constructor',constructor_registration['pointer']==s['constructor'])
 initialized=None;ctor=sources['constructor']
 if effect:
  sources['classInit']=owned(image,s['classInit']);initialized=provider_helpers.ready_class_init(sources['classInit']['regions'],s['classInit'])
  need('same-actual-ready-class-helper',s['classInit']==base+value['proof']['symbolRvas']['classInit'])
  cs=dict(context=s['context'],barrier=s['barrier'],classInit=s['classInit'],
   arrayAllocate=normal_call_after(ctor['rows'],'mov rcx, rax',preceding='8bd3'))
  constructors=[shared.capacity_program(ctor['regions'],s['constructor'],cs,positive=v)for v in(False,True)]
  pcalls=calls(sources['provider']);need('complete-effect-provider-call-profile',len(pcalls)>=9)
  ps={k:pcalls[i]for k,i in dict(classInit=3,typeHandle=4,backend=6,context=7,cast=8).items()}
  provider=shared.provider_program(sources['provider']['regions'],s['provider'],ps)
  need('same-effect-provider-ready-context',ps['classInit']==s['classInit']and ps['context']==s['context'])
  dc=calls(sources['dispatch']);need('one-exact-wrapper-prepare',len(dc)==1 and dc[0]==base+value['proof']['symbolRvas']['prepare'])
  dispatch=[shared.dispatch_program(sources['dispatch']['regions'],s['dispatch'],prepare=dc[0])]
 else:
  constructors=[programs.airwall_capacity(ctor['regions'],s['constructor'],positive=v)for v in(False,True)]
  need('same-actual-capacity-helper-contexts',all(p['symbolTargets']['context']==s['context']and p['symbolTargets']['barrier']==s['barrier']for p in constructors))
  provider=programs.airwall_provider(sources['provider']['regions'],s['provider']);ps=provider['symbolTargets']
  need('same-airwall-provider-context',ps['context']==s['context'])
  dispatch=[programs.airwall_dispatch(sources['dispatch']['regions'],s['dispatch'],canonical=base+value['canonicalCallbackTargetRva'],**mode)
   for mode in({},dict(create=False),dict(null=True))]
  need('same-complete-canonical-inline-helper-ABI',all(all(base+value['proof']['symbolRvas'].get(k,-1)==v for k,v in p['symbolTargets'].items())for p in dispatch))
 need('same-own-TypeFromHandle',ps['typeHandle']==base+value['proof']['symbolRvas']['typeHandle'])
 pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[pc],label='storyModuleValueList.provider')
 pcs={r['relativeSlot']:r for r in pc['entries']};pm=md.methods[pc['definition']]
 need('provider-exact-owned-slots',sorted(pcs)==[0,1])
 need('provider-static-noparam-owned-return',(image.type_name(pm.declaring_type),md.string(pm.name_index),bool(pm.flags&16),pm.parameter_count)==
  ('MemoryPack.MemoryPackFormatterProvider','GetFormatter',True,0)and ctx.type_pointer(pm.return_type)==ctx.type_pointer(pcs[1]['index']))
 need('formatter-result-definition',pcs[1]['type']['definition']['name']=='MemoryPack.MemoryPackFormatter`1')
 for child in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):need('same-owned-provider-MVAR',
  (child['parameterOwner']['methodIndex'],child['parameterOwner']['ordinal'])==(pm.index,0))
 sources['cast']=owned(image,ps['cast']);predicates=calls(sources['cast']);need('one-actual-compatible-cast',len(predicates)==1)
 casts=[provider_helpers.successful_cast(sources['cast']['regions'],ps['cast'],predicates[0],null=v)for v in(False,True)]
 path=CONTRACTS_DIR/'levelscript_int_list_native.json';before=path.read_bytes();fact=json.loads(before)
 need('same-context-dependency-build',pins==fact['nativeInputs'])
 resolver=shared.resolver_prefix(fact['bodies']['contextResolver'],s['context']-base)
 image.check_windows(resolver['windows'],label='storyModuleValueList.contextResolver')
 rr=[(base+w['startRva'],image.window_bytes(w))for w in resolver['windows']]
 if not effect:
  # The indexed entry is a real forwarding body. Its exact E9 selects a
  # separately owned initialized-class prefix; the two entries are not aliases.
  from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
  g=BytesPath(rr,s['context']);g.take('488bc1','4863ca','488b0cc8');delegated=g.relative('e9')
  need('distinct-initialized-class-delegate',delegated!=s['context'])
  ready=shared.resolver_prefix(fact['bodies']['contextResolver'],delegated-base)
  image.check_windows(ready['windows'],label='storyModuleValueList.contextResolver.readyDelegate')
  rr.extend((base+w['startRva'],image.window_bytes(w))for w in ready['windows'])
  resolver=dict(resolver,delegatedInitializedPrefix=ready,pointerEquivalenceClaimed=False)
 resolver_program=int_list_sources.initialized_class(rr,s['context'],indexed=not effect)
 usages=[]
 for site,cell,name in((provider['typeClassInstructionVa'],provider['typeClassCell'],'System.Type'),
  (provider['providerClassInstructionVa'],provider['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider')):
  usage=derive_typed_usage_context(image,site-base,label='storyModuleValueList.namedClass')
  need('actual-exact-named-class',(usage['tag'],usage['typeName'],usage['usageCellRva'])==(1,name,cell-base));usages.append(usage)
 need('same-selected-provider-class-in-list',provider['providerClassCell']==paths[1]['providerClassCell'])
 barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
 need('unchanged-context-declaration',before==path.read_bytes());_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-module-value-list-source',nativeInputs=pins,
  elementType=element_type,typeName=context['closedListType'],typedRequest=typed_request,callTargetRva=call_target-base,
  headerBytes=4,countLimit=LIMIT,countRange=[-1,LIMIT],managedElementBytes=programs.WIDTHS[element_type],elementWireBytes=None,
  initiallyNullListRequired=True,actualCallbackEqualsCanonicalRequired=True,elementCanonicalCallbackTargetRva=value['canonicalCallbackTargetRva'],
  positiveCountsAdmitted=True,wholeManagedValueStored=True,elementGrammarAdmitted=False,parentFieldAdmitted=False,
  wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False,
  proof=dict(context=context,value=value,programs=paths,induction=induction,header=header,Add=add,AddForwarder=add_forwarder,
   storage=storage,AddAbi=abi,listFields=fields,methodAbis=abis,constructors=constructors,constructorRegistration=constructor_registration,
   dispatch=dispatch,provider=provider,providerContext=pc,casts=casts,initializedClassHelper=initialized,
   contextResolver=resolver,contextResolverProgram=resolver_program,contextResolverRegions=[[a,h.hex().upper()]for a,h in rr],
   classUsages=usages,barrier=dict(source=barrier,program=barrier_proof),symbolRvas={k:v-base for k,v in s.items()},
   sourceWindows=dict(list=body['windows'],**{k:v['windows']for k,v in sources.items()}),
   sourceRegions=dict(list=[[a,h.hex().upper()]for a,h in body['regions']],**{k:[[a,h.hex().upper()]for a,h in v['regions']]for k,v in sources.items()})),
  evidenceBoundary=dict(exact='Own closed value list contexts/ABI, signed4 count with fresh count-sized capacity, byte-identical induction, selected canonical callback/default/full value transfer, operational Add storage/stride/barrier and complete selected normal frames.',
   conditional='Initially null output; normal fresh zeroed typed allocations, coherent ready closed MethodInfo/provider contexts, actual element callback equals the independently authenticated canonical Original body. Compatible normal helper/cast/barrier ABI, disabled collector and stable disjoint buffered input/Reader/output/frame. No runtime provider or callback selection is observed.',
   unresolved=['element wire capability/codec','actual enclosing field/local/fresh-list state','growth/refill/errors','live provider selection','whole Module/physical EOF/publication']))))
