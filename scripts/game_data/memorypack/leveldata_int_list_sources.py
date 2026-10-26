"""Fresh current Int32 collection binding, without an enclosing owner witness.

The reviewed current Int32 owner supplies full list/callback/Add/growth and
provider source programs. Each caller separately authenticates its exact
closed reference request, actual helper and carrier. Matching ready callbacks,
normal helpers and buffered disjoint storage remain explicit conditions.
"""
TYPE='System.Collections.Generic.List`1<int>'
CAP='story-int32-list'
LIMIT=4096


def bind(usage,carrier,call_target,reference,*,base,count_limit):
 if (type(count_limit)is not int or not 0<=count_limit<=LIMIT
   or type(call_target)is not int or type(base)is not int or call_target<=base
   or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[TYPE]
   or not isinstance(usage.get('methodSpec'),(list,tuple))or len(usage['methodSpec'])!=3
   or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
   or carrier.get('name')!=TYPE or carrier.get('definition',{}).get('name')!='System.Collections.Generic.List`1'
   or not isinstance(carrier.get('classArguments'),list)or len(carrier['classArguments'])!=1
   or carrier['classArguments'][0].get('name')!='int'
   or bytes.fromhex(carrier['classArguments'][0].get('rawHex',''))[10:12]!=b'\x08\x80'
   or reference.get('entryRva')!=call_target-base):
  raise ValueError('storyIntList.exact-current-caller')
 return dict(typeName=TYPE,elementType='int',capability=CAP,headerBytes=4,elementWireBytes=4,managedElementBytes=4,
  countLimit=count_limit,countRange=[-1,count_limit],nullable=True,positiveCountsAdmitted=count_limit>0,
  rawBitsPreserved=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
  packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=call_target-base,
  wholeGrammarAdmitted=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,*,typed_request,call_target,count_limit=LIMIT):
 import copy
 import json
 from scripts.game_data import levelscript_int_list_native as integers
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import modelview_packable_sources,scalar_param_native as scalar
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
 need=lambda k,e,a:scalar.need('storyIntList',k,e,a)
 _publication_gate(image,pins);need('literal-finite-count-limit',True,type(count_limit)is int and 0<=count_limit<=LIMIT)
 base=image.pe.image_base;validate_typed_usage_context(image,typed_request,label='storyIntList.actualCaller')
 bind_typed_read(image,typed_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
 argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 carrier=ContextSymbols(image).type(argument.type_pointer_va)
 path=integers.CONTRACT_PATH;raw=path.read_bytes();fact=_load(path.name,pins)
 need('exact-current-Int32-contract',(integers.SCHEMA,'exact-current-build','List<int>'),(fact['schema'],fact['status'],fact['codecKind']))
 list_source=integers._validate_native(image,fact)
 core=_load('npc_runtime_native.json',pins)['readPackable'];generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
 routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
 reference=modelview_packable_sources.validate_components(image,pins,core,routes)
 cap=bind(typed_request,carrier,call_target,core,base=base,count_limit=count_limit)
 need('current-contract-bookend',raw,path.read_bytes());_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-int32-list-component.v1',status='validated-conditional-int32-list',
  nativeInputs=pins,capability=cap,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(typedRequest=typed_request,closedCarrier=carrier,reference=reference,sourceContract=path.name,
   int32Source=fact,sourceValidation=list_source),evidenceBoundary=dict(exact='Fresh actual closed Int32-list caller and reference helper, current exact Int32 list/callback/Add/growth/capacity/provider source declaration fully revalidated on the same selected image.',
   conditional=__doc__,unresolved=['actual enclosing field/local/store','runtime provider/formatter selection','whole owner/physical EOF']))))
