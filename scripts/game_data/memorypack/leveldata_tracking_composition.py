"""Atomic finite Tracking child composition, without Route/MissionArea authority.

Inputs must be independently derived on the same selected native image. This
pure helper preserves complete reduced child capabilities, authenticates the
native source bytes and binds actual closed list requests/callbacks. It never
opens inputs, selects runtime providers or grants an enclosing field or EOF.
"""
import copy
import json

from scripts.game_data.memorypack import leveldata_tracking_components as profiles
from scripts.game_data.memorypack import leveldata_tracking_raw_sources as raw_owner
from scripts.game_data.memorypack import leveldata_tracking_list_sources as lists
from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,POINT,SPECS

SCHEMA='endfield.story-tracking-child-composition.v1'


def need(check,condition):
 if not condition:raise ValueError('storyTrackingComposition.'+check)


def _same(left,right):
 """JSON shape equality preserves the distinction between booleans and ints."""
 encode=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
 return encode(left)==encode(right)


def _usage_request(usage,register):
 """Recheck a producer's literal encoded usage link; fresh metadata is separate."""
 need('literal-owned-usage-row',type(usage)is dict and register in('r8','rdx'))
 at=usage.get('instructionRva');cell=usage.get('usageCellRva');index=usage.get('methodSpecIndex')
 raw=bytes.fromhex(usage.get('instructionHex',''));encoded=bytes.fromhex(usage.get('usageRawHex',''))
 need('same-actual-usage-cell',type(at)is int and at>=0 and type(cell)is int and cell>=0
  and len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05'if register=='r8'else'488b15')
  and at+len(raw)+int.from_bytes(raw[3:],'little',signed=True)==cell)
 need('same-encoded-closed-MethodSpec',type(index)is int and 0<=index<1<<28 and type(usage.get('tag'))is int
  and usage['tag']==6 and len(encoded)==8 and int.from_bytes(encoded,'little')==(6<<29|index<<1|1))


def _list_caps(component,value,pins,base):
 from scripts.game_data.codecs.leveldata.current_tracking import validate_list
 need('literal-independent-components',type(component)is dict and type(value)is dict)
 need('finite-independent-value-type',type(value.get('typeName'))is str and value['typeName']in SPECS)
 name=value['typeName'];expected=profiles.value_capability(value,pins);own=component.get('proof',{})
 need('same-current-list-component:'+name,component.get('schema')=='endfield.story-tracking-value-list.v1'
  and component.get('status')=='validated-conditional-tracking-value-list'and component.get('nativeInputs')==pins
  and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
 caps=component.get('capabilities',{});need('only-own-two-child-caps:'+name,set(caps)=={profiles.VALUE_CAPS[name],profiles.LIST_CAPS[name]})
 need('complete-independent-canonical-child:'+name,_same(own.get('value'),value)and _same(caps[profiles.VALUE_CAPS[name]],expected))
 cap=caps[profiles.LIST_CAPS[name]];validate_list(cap,expected,name)
 context=own.get('context',{});usage=context.get('typedRequest',{});closed='System.Collections.Generic.List`1<'+name+'>'
 _usage_request(usage,'rdx')
 spec=usage.get('methodSpec')
 need('actual-closed-list-request:'+name,context.get('nativeInputs')==pins and context.get('elementType')==name
  and context.get('elementValueType')is True and context.get('closedListType')==closed
  and usage.get('tag')==6 and(usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   ('MemoryPack.MemoryPackReader','ReadPackable',[],[closed])
  and isinstance(spec,(list,tuple))and len(spec)==3 and all(type(n)is int for n in spec)and spec[0]>=0 and spec[1]==-1 and spec[2]>=0
  and cap['packableReaderMethodDefinition']==spec[0]and context.get('callTargetRva')==cap['packableReaderTargetRva'])
 carrier=context.get('closedCarrier',{});arguments=carrier.get('classArguments',[])
 need('exact-one-closed-list-element:'+name,carrier.get('name')==closed and len(arguments)==1)
 argument=bytes.fromhex(arguments[0].get('rawHex',''));definition=value['record']['layout']['typeDefinition']
 need('same-own-value17-argument:'+name,len(argument)==16 and argument[10:12]==bytes((17,128))
  and type(definition)is int and int.from_bytes(argument[:8],'little')==definition)
 formal,=next(row for row in context['listContext']['entries']if row['relativeSlot']==0)['type']['classArguments']
 fields=own.get('listFields',{})
 need('same-declared-fields-without-open-offsets:'+name,
  _same(lists.list_field_declarations(fields.get('declarations'),owned_parameter_pointer=formal['typePointerVa']),fields))
 symbols=own.get('symbolRvas',{});need('literal-source-role-targets:'+name,
  all(type(symbols.get(k))is int and symbols[k]>0 for k in('header','context','allocate','constructor','barrier','classInit','provider','dispatch','Add')))
 s={k:base+rva for k,rva in symbols.items()};windows=own.get('sourceWindows',{});payloads=own.get('sourceRegions',{})
 resolver=own.get('contextResolver',{})
 need('actual-nonindexed-class-resolver-prefix:'+name,resolver.get('entryRva')==symbols['context']
  and resolver.get('ownership')=='selectedInitializedPrefixOnly'and resolver.get('canonicalEntryIdentityClaimed')is False
  and resolver.get('fullPhysicalExtentProved')is False)
 rr=raw_owner._owned_regions(own.get('contextResolverRegions'),resolver.get('windows'),base=base,label='tracking-ready-class-prefix')
 from scripts.game_data.memorypack.int_list_sources import initialized_class
 need('same-actual-ready-class-effect:'+name,_same(initialized_class(rr,s['context'],indexed=False),own.get('contextResolverProgram')))
 roles={'list','header','constructor','provider','Add','dispatch','classInit','cast'}|({'AddCore'}if name==BOUNDS else set())
 need('complete-owned-source-inventory:'+name,set(windows)==set(payloads)==roles)
 regions={role:raw_owner._owned_regions(payloads[role],windows[role],base=base,label='tracking-list:'+name+':'+role)for role in sorted(roles)}
 entry=context.get('registration',{}).get('pointer');need('same-selected-closed-list-entry:'+name,type(entry)is int
  and context.get('sourceWindows')==windows['list'])
 normalize=lambda v:json.loads(json.dumps(v))
 programs=[lists.list_program(regions['list'],entry,s,type_name=name,count=count)for count in(-1,0,1,2,3)]
 need('all-null-zero-positive-programs:'+name,_same(normalize(programs),own.get('programs')))
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 induction=prove_induction(programs[1:],initial='458bfd'if name==BOUNDS else'4533ff',increment='41ffc7',
  comparison='443b7d6f'if name==BOUNDS else'443b7c2478',counter='r15d',
  saved_count='unchanged entry RSP+16 Int32 (body RBP+111)'if name==BOUNDS else'unchanged entry RSP+16 Int32 (body RSP+120)',max_count=lists.LIMIT)
 need('exact-count-induction:'+name,_same(normalize(induction),own.get('induction')))
 dispatch=lists.dispatch_program(regions['dispatch'],s['dispatch'],prepare=base+value['proof']['symbolRvas']['prepare'])
 need('same-canonical-slot5-ABI:'+name,_same(normalize(dispatch),own.get('dispatch')))
 add=own.get('Add',{});selected=add.get('selectedBytes',[]);need('literal-concrete-Add-entry:'+name,bool(selected)and type(selected[0][0])is int)
 if name==BOUNDS:
  thunk=lists.bounds_add_forwarder(regions['Add'],s['Add'],target=selected[0][0])
  need('distinct-owned-Add36-delegate:'+name,_same(normalize(thunk),own.get('AddForwarder')))
 else:need('same-direct-Add16-entry',selected[0][0]==s['Add']and own.get('AddForwarder')is None)
 replay=lists.add_program(regions['AddCore'if name==BOUNDS else'Add'],selected[0][0],type_name=name)
 need('full-typed-Add-stores:'+name,_same(normalize(replay),add))
 observation=component.get('actualParentObservation')
 if observation is not None:
  need('same-independent-actual-parent-observation:'+name,observation.get('typedRequest')==usage and observation.get('parentFieldAdmitted')is False)
  raw_owner.bind_call(usage,observation['sourceInstruction'],source_target=base+cap['packableReaderTargetRva'],base=base)
 return caps


def bind_collection(component,value,pins,*,typed_request,call_target,source_instruction,image_base):
 """Join one freshly authenticated outer request; its argument/frame stays open."""
 need('literal-outer-source-addresses',type(image_base)is int and image_base>0
  and type(call_target)is int and call_target>image_base)
 caps=_list_caps(component,value,pins,image_base);name=value['typeName'];key=profiles.LIST_CAPS[name];cap=caps[key]
 need('same-actual-outer-list-request',typed_request==component['proof']['context']['typedRequest']
  and call_target==image_base+cap['packableReaderTargetRva'])
 raw_owner.bind_call(typed_request,source_instruction,source_target=call_target,base=image_base)
 observed=component.get('actualParentObservation')
 if observed is not None:need('same-owned-outer-source-instruction',source_instruction==observed['sourceInstruction'])
 return dict(capability=key,typeName=cap['typeName'],elementType=name,elementCapability=profiles.VALUE_CAPS[name],
  packableReaderMethodDefinition=cap['packableReaderMethodDefinition'],packableReaderTargetRva=cap['packableReaderTargetRva'],
  listCapability=copy.deepcopy(cap),elementCapabilityShape=copy.deepcopy(caps[profiles.VALUE_CAPS[name]]),
  typedRequest=copy.deepcopy(typed_request),sourceInstruction=copy.deepcopy(source_instruction),
  initiallyNullListRequired=True,parentArgumentLocalStoreFrameRequired=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def compose(raw,values,collections,pins,*,image_base,existing=None):
 """Validate all five scopes before returning a new complete child-cap map."""
 need('literal-selected-image-base',type(image_base)is int and image_base>0)
 need('literal-component-maps',type(raw)is dict and type(values)is dict and type(collections)is dict
  and(existing is None or type(existing)is dict))
 need('exact-finite-value-and-list-domains',set(values)==set(collections)=={BOUNDS,POINT})
 need('same-named-value-map',all(type(values[name])is dict and values[name].get('typeName')==name for name in(BOUNDS,POINT)))
 need('same-complete-raw-bounds-source',raw_owner.verify(raw,pins)==image_base)
 usage=raw['proof']['typedRequest'];_usage_request(usage,'r8')
 context=dict(methodOwner=usage['typeName'],methodName=usage['methodName'],register='r8',
  fullTypeName=BOUNDS,typeKind=17,typeDefinition=raw['typeDefinition'],methodSpec=usage['methodSpec'],
  instructionRva=usage['instructionRva'],instructionHex=usage['instructionHex'])
 profiles.bind_raw(context,image_base+raw['sourceTargetRva'],raw,pins,base=image_base)
 staged={raw_owner.CAPABILITY:copy.deepcopy(raw)}
 for name in(BOUNDS,POINT):
  own=_list_caps(collections[name],values[name],pins,image_base)
  for key,cap in own.items():
   need('equal-composed-overlap:'+key,key not in staged or _same(staged[key],cap));staged[key]=copy.deepcopy(cap)
 result=copy.deepcopy(existing or{})
 for key,cap in staged.items():
  need('equal-existing-overlap:'+key,key not in result or _same(result[key],cap))
 result.update(staged);return result


def derive(image,pins,*,raw_request,raw_target,raw_instruction,list_requests):
 """Derive all five finite scopes on one supplied image, never from reports."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 need('exact-fresh-list-request-domain',type(list_requests)is dict and set(list_requests)=={BOUNDS,POINT}
  and all(type(row)is dict and set(row)=={'typed_request','call_target','source_instruction'}for row in list_requests.values()))
 _publication_gate(image,pins);base=image.pe.image_base
 raw=raw_owner.derive(image,pins,typed_request=raw_request,source_target=raw_target,source_instruction=raw_instruction)
 values={};collections={};bindings={}
 for name in(BOUNDS,POINT):
  request=list_requests[name]
  raw_owner.bind_call(request['typed_request'],request['source_instruction'],source_target=request['call_target'],base=base)
  image.check_instruction_windows([request['source_instruction']],label='storyTrackingComposition.actualListE8:'+name)
  component=lists.derive(image,pins,typed_request=request['typed_request'],call_target=request['call_target'],element_type=name)
  component['actualParentObservation']=dict(typedRequest=copy.deepcopy(request['typed_request']),
   sourceInstruction=copy.deepcopy(request['source_instruction']),parentFieldAdmitted=False)
  collections[name]=component;values[name]=component['proof']['value']
  bindings[name]=bind_collection(component,values[name],pins,image_base=base,**request)
 caps=compose(raw,values,collections,pins,image_base=base)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-tracking-children',nativeInputs=pins,
  capabilities=caps,proof=dict(raw=raw,collections=collections,actualListBindings=bindings),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Same selected image: direct Bounds raw36, separate canonical Bounds MC3/Point MC2/default conversions, both signed4 counted lists and actual typed source E8/callback/Add/constructor/provider joins.',
   conditional='All independently declared ready-context, canonical callback selection, fresh-list state, allocator/helper and disjoint frame/input/output conditions remain required. No runtime callback selection is observed.',
   structuralOnly='All tracking coordinate and enum bits are retained without runtime tracking interpretation.',
   unresolved=['actual enclosing argument/local/store/frame and fresh-list state','runtime provider/callback replacement','whole Route/MissionArea and physical EOF']))))
