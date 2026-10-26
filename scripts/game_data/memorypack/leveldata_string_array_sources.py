"""Exact current STRING14 array and independently pooled string callbacks.

The reference-slot loop supplies no element grammar. The dedicated current
BeyondStringFormatter/pool source supplies signed index -2/null, -1/empty and
nonnegative lookup. Matching compatible ready provider/callback contexts,
fresh typed arrays, disabled collector, buffered disjoint storage and normal
helpers are conditions; actual runtime provider selection is not observed.
"""
import json
from scripts.game_data.memorypack import scalar_param_native as scalar

TYPE='string'
ARRAY='string[]'
CAP='story-pooled-string-array'
LIMIT=4096


def need(k,e,a):scalar.need('storyStringArray',k,e,a)


def require_string(raw):
 need('exact-undecorated-STRING14',True,isinstance(raw,bytes)and len(raw)==16 and raw[10:12]==b'\x0e\x00')


def derive(image,pins,*,typed_request,call_target,count_limit=LIMIT):
 import copy
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,derive_typed_usage_context
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import modelview_packable_sources
 from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
 from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 from scripts.game_data.memorypack.skill_reference_array_sources import array_program,induction,provider_program
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 _publication_gate(image,pins);need('finite-literal-count-limit',True,type(count_limit)is int and 3<=count_limit<=LIMIT)
 base=image.pe.image_base;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
 validate_typed_usage_context(image,typed_request,label='storyStringArray.actualCaller')
 bind_typed_read(image,typed_request,method_name='ReadArray',argument=TYPE,kind=14,reference=True)
 argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 raw=image.pe.bytes_at_va(argument.type_pointer_va,16);require_string(raw)
 core=_load('npc_runtime_native.json',pins)['readPackable'];generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
 routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
 reference=modelview_packable_sources.validate_components(image,pins,core,routes)
 body=owned(image,call_target)
 def call(source,offset):
  row,=[r for r in source['rows']if int(r['va'],16)==source['pointer']+offset];raw=bytes.fromhex(row['bytes'])
  need('actual-direct-source-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
 s={name:call(body,offset)for name,offset in dict(arrayAllocate=247,provider=373,prepare=435).items()}
 offsets=scalar.reader_offsets(image,'storyStringArray');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 programs=[array_program(body['regions'],call_target,offsets,s,count=n,count_limit=3)for n in(-1,0,1,2,3)]
 certificate=induction(programs,count_limit=count_limit)
 symbols=ContextSymbols(image);first=symbols.context(typed_request['methodSpec'][0],is_method=True)
 second=symbols.context(first['entries'][0]['methodSpec'][0],is_method=True)
 validate_generic_contexts(image,[first,second],label='storyStringArray.overloads')
 array_context=validate_read_array_context(image,[first,second],typed_request,ge,argument.type_pointer_va,
  reference['valueContext']['formatterDeserializeDefinition'],fail=need)
 need('same-owned-GetFormatter-definition',reference['valueContext']['providerMethodDefinition'],second['entries'][3]['methodSpec'][0])
 provider=owned(image,s['provider'])
 ps={name:call(provider,offset)for name,offset in dict(classFromType=88,hash=145,compare=238,backend=376,indexedType=393,assignable=409).items()}
 provider_proof=provider_program(provider['regions'],s['provider'],ps)
 need('same-provider-cache-root',reference['source']['providerClassCell'],provider_proof['providerClassCell'])
 provider_usages=[]
 for program in programs:
  at=program['providerUsageInstruction']
  if at is None:continue
  usage=derive_typed_usage_context(image,at-base,label='storyStringArray.providerCell')
  need('named-current-provider',(1,'MemoryPack.MemoryPackFormatterProvider'),(usage['tag'],usage['typeName']))
  need('same-owned-provider-cell',base+usage['usageCellRva'],provider_proof['providerClassCell']);provider_usages.append(usage)
 pooled_fact=_load('levelscript_pooled_string_list_native.json',pins)
 pooled=validate_string_components(image,pooled_fact)
 need('independent-pooled-string-source',(5,4,8,False),
  (pooled['stringFormatterSlot'],pooled['wireBytes'],pooled['managedReferenceBytes'],pooled['liveProviderSelectionProved']))
 callback,=[r for r in pooled_fact['programs']if r['role']=='string']
 model=_load('model_view_state_controller_native.json',pins);barrier=_barrier(image,base+model['collector']['entryRva'])
 for program in programs:need('same-disabled-collector',base+barrier['result']['disabledFlagRva'],program['collectorFlag'])
 _publication_gate(image,pins)
 cap=dict(typeName=ARRAY,elementType=TYPE,elementRawKind=14,capability=CAP,headerBytes=4,elementWireBytes=4,managedElementBytes=8,
  countLimit=count_limit,countRange=[-1,count_limit],nullable=True,positiveCountsAdmitted=True,elementGrammarAdmitted=True,
  elementEncoding='signed-int32-pool-index',nullElementIndex=-2,emptyElementIndex=-1,initiallyNullArrayRequired=True,
  arrayReaderMethodDefinition=typed_request['methodSpec'][0],arrayReaderTargetRva=call_target-base,
  actualCallbackEqualsPooledStringRequired=True,liveFormatterSelectionObserved=False,wholeGrammarAdmitted=True)
 return json.loads(json.dumps(dict(schema='endfield.story-pooled-string-array-component.v1',status='validated-conditional-pooled-string-array',
  nativeInputs=pins,capability=cap,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(typedRequest=typed_request,closedElementRawHex=raw.hex(),arrayPrograms=programs,induction=certificate,
   ownedContexts=[first,second],arrayContext=array_context,commonReference=reference,pooledString=pooled,
   pooledCallback=dict(entryRva=callback['entryRva'],windows=callback['windows'],actualSelectedCallbackEqualityRequired=True),
   provider=provider_proof,providerUsages=provider_usages,barrier=barrier,helperRvas={k:v-base for k,v in s.items()},
   sourceWindows=body['windows'],providerWindows=provider['windows']),evidenceBoundary=dict(
    exact='Actual STRING14 ReadArray request and reciprocal overload/array/provider/slot5 MVAR contexts; full selected null/empty/fresh-positive source and finite count induction. Independently current pooled-string formatter/pool programs supply element grammar.',
    conditional=__doc__,unresolved=['actual enclosing field/local/store','runtime provider/default/override selection','cold/refill/inline-string paths','whole owner/physical EOF']))))


def bind_array(pins,parent,component,key):
 """Finite STRING14 compiler join; source gates run in the owning operation."""
 cap=component.get('capabilities',{}).get(key,{});fact=component.get('source',{});usage=parent.get('typedRequest',{})
 if (key!=CAP or component.get('nativeInputs')!=pins or fact.get('nativeInputs')!=pins
  or fact.get('schema')!='endfield.story-pooled-string-array-component.v1'
  or fact.get('status')!='validated-conditional-pooled-string-array'
  or fact.get('capability')!=cap or parent.get('arraySource')!=fact
  or fact.get('parentFieldAdmitted')is not False or fact.get('wholeOwnerAdmitted')is not False
  or parent.get('typeName')!=ARRAY or cap.get('typeName')!=ARRAY or cap.get('elementType')!=TYPE
  or cap.get('capability')!=CAP or cap.get('countRange')!=[-1,LIMIT]
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(elementRawKind=14,headerBytes=4,
   elementWireBytes=4,managedElementBytes=8,countLimit=LIMIT,nullElementIndex=-2,emptyElementIndex=-1).items())
  or cap.get('elementEncoding')!='signed-int32-pool-index'
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted',
   'initiallyNullArrayRequired','actualCallbackEqualsPooledStringRequired','wholeGrammarAdmitted'))
  or cap.get('liveFormatterSelectionObserved')is not False
  or usage.get('methodName')!='ReadArray'or usage.get('methodArguments')!=[TYPE]
  or fact.get('proof',{}).get('typedRequest')!=usage
  or not isinstance(usage.get('methodSpec'),(tuple,list))or len(usage['methodSpec'])!=3
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
  or type(cap.get('arrayReaderMethodDefinition'))is not int or type(cap.get('arrayReaderTargetRva'))is not int
  or(cap['arrayReaderMethodDefinition'],cap['arrayReaderTargetRva'])!=(usage['methodSpec'][0],parent['sourceTargetRva'])):
  raise ValueError('storyStringArray.exact-current-STRING14-parent')
 return dict(fieldName=parent['fieldName'],typeName=ARRAY,capability=CAP,
  readerMethodDefinition=cap['arrayReaderMethodDefinition'],sourceTargetRva=cap['arrayReaderTargetRva'],countLimit=LIMIT,
  initiallyNullArrayRequired=True,actualCallbackEqualsPooledStringRequired=True)
