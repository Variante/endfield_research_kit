"""ScriptTaskPtr's own pooled-key value inside a four-field reference Param."""
import hashlib
import json

from scripts.game_data.memorypack.levelscript_condition_param_sources import need
from scripts.game_data.memorypack.levelscript_condition_small_pointer_sources import TASK as VALUE

TYPE='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>'
SCHEMA='endfield.story-condition-script-task-param-components.v1'
CAPABILITY='story-condition-param:'+TYPE


def _record(image,target,method_index=None):
 base=image.pe.image_base;end=image.body_index.extents[target];raw=image.pe.bytes_at_va(target,end-target)
 result=dict(pointerRva=target-base,
  window=dict(startRva=target-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper()),
  instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()]for r in image.body_index._decode(target,end-target)])
 if method_index is not None:result['methodIndex']=method_index
 return result


def _value_reader(image,pins,usage,target,child):
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack.value_callback_slot_sources import program as slot_program
 from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,pooled_global_buff_id_sources as programs
 from scripts.game_data.memorypack.levelscript_condition_small_pointer_sources import _call
 base=image.pe.image_base;entries=GenericEntries(image)
 typed=buff_ptr_sources._typed_context(image,usage,VALUE,entries)
 registered=entries.resolve(usage['methodSpec'][0],[],[VALUE])
 need('own-ScriptTask-value-reader-registration',registered['pointer']==target)
 body=pointer.owned(image,target);s=dict(classInit=_call(body,66),provider=_call(body,78),dispatch=_call(body,99))
 need('same-ScriptTask-ready-class-helper',s['classInit']==base+child['symbolRvas']['classInit'])
 value_program=programs.value8_program(body['regions'],target,s,canonical=True)
 provider_entry=entries.resolve(typed['typedContext']['providerMethodDefinition'],[],[VALUE])
 need('own-ScriptTask-closed-provider-source',provider_entry['pointer']==s['provider'])
 provider=pointer.owned(image,s['provider']);ps={key:_call(provider,offset)for key,offset in
  dict(classInit=78,typeHandle=88,backend=111,context=127,cast=138).items()}
 need('same-ScriptTask-provider-Type-helper',ps['typeHandle']==base+child['symbolRvas']['typeHandle']and ps['classInit']==s['classInit'])
 provider_program=programs.compared_provider(provider['regions'],s['provider'],ps,canonical=True)
 cast=pointer.owned(image,ps['cast']);assignable,=pointer.calls(cast)
 cast_program=programs.successful_cast(cast['regions'],ps['cast'],assignable)
 dispatch=pointer.owned(image,s['dispatch']);prepare=_call(dispatch,27)
 need('same-ScriptTask-value-callback-preparation',prepare==base+child['symbolRvas']['prepare'])
 invocation=slot_program(dispatch['regions'],s['dispatch'],prepare=prepare)
 context_usage=derive_typed_usage_context(image,target-base+50,label='ScriptTaskParam.valueProviderClass')
 need('own-ScriptTask-value-provider-class',(context_usage['tag'],context_usage['typeName'])==(1,'MemoryPack.MemoryPackFormatterProvider'))
 return dict(typedRequest=usage,typedContext=typed,registeredReader=registered,registeredProvider=provider_entry,
  valueProgram=value_program,providerProgram=provider_program,castProgram=cast_program,slotInvocation=invocation,
  providerClassUsage=context_usage,actualCallbackEqualsCanonicalRequired=True,closedPointerEquivalenceProved=False,
  sourceWindows={k:b['windows']for k,b in(('reader',body),('provider',provider),('cast',cast),('dispatch',dispatch))},
  sourceRegions={k:[[a,raw.hex().upper()]for a,raw in b['regions']]for k,b in(('reader',body),('provider',provider),('cast',cast),('dispatch',dispatch))})


def derive_source(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param as primitive,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack.param_setter_call_programs import reader_program
 from scripts.game_data.memorypack.levelscript_condition_small_pointer_sources import derive as derive_value
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
 need('own-ScriptTask-Param-four-members',[(m.name,m.declared_type)for m in wrapper.members]==
  [('constValue',VALUE),('idRef','int'),('paramSource','int'),('path','string')])
 need('own-ScriptTask-Param-holder',ctx.field(wrapper.name+'::__instance')==(wrapper.name,TYPE,16))
 mm=pointer.methods(image,wrapper);records={};slots={};bodies={}
 for name in('.ctor','CreateInstance','GetValue','Deserialize',*('set___'+m.name+'__'for m in wrapper.members)):
  method=mm[name];target=image.method_pointer_va(method)
  if name=='GetValue':
   pointer.leaf(image,target,['488B4110','C3']);records[name]=dict(methodIndex=method.index,pointerRva=target-base,
    instructions=[[target-base,'488B4110'],[target-base+4,'C3']])
  else:bodies[name]=pointer.owned(image,target);records[name]=_record(image,target,method.index)
  if name=='Deserialize':primitive.reader_abi(image,ctx,method,wrapper);continue
  declaration={'constValue':(VALUE,17,False),'idRef':('int',8,False),'paramSource':('int',8,False),'path':('string',14,True)}
  scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,(TYPE,21,True)if name=='GetValue'else('void',1,False),
   [declaration[name[6:-2]]]if name.startswith('set___')else[],'ScriptTaskParam')
  if name.startswith('set___'):
   field=name[6:-2];rows=records[name]['instructions'];reference=field in('constValue','path')
   at=(4 if bytes.fromhex(rows[3][1])[:1]==b'\x74'else 6)if reference else 6;slots[field]=bytes.fromhex(rows[at][1])[-1]
   scalar.parameter_setter(image,rows,name='path'if reference else field,slot=slots[field],width=8,label='ScriptTaskParam')
 occupied=[i for field,size in(('constValue',8),('idRef',4),('paramSource',4),('path',8))for i in range(slots[field],slots[field]+size)]
 need('own-ScriptTask-Param-disjoint-fields',len(set(occupied))==24 and all(16<=i<128 for i in occupied))
 loads=[r for r in records['.ctor']['instructions']if bytes.fromhex(r[1]).startswith(bytes.fromhex('488B0D'))]
 need('one-ScriptTask-Original-allocation',len(loads)==1)
 allocation=derive_typed_usage_context(image,loads[0][0],label='ScriptTaskParam.Original')
 need('own-ScriptTask-Original-allocation',allocation['typeName']==TYPE)
 parameter=dict(methods=records,ownedFieldSlots=slots,allocationContext=allocation);scalar.allocation_bridge(image,ctx,parameter,'ScriptTaskParam')
 body=bodies['Deserialize'];programs=[reader_program(body['regions'],body['pointer'],existing=e,ff=f)for e,f in((False,False),(True,False),(False,True),(True,True))]
 positive=programs[0];calls=positive['sourceCalls']
 need('same-ScriptTask-positive-program-callees',calls==programs[1]['sourceCalls'])
 need('own-ScriptTask-named-setter-targets',all(calls['set'+field[0].upper()+field[1:]]==base+records['set___'+field+'__']['pointerRva']for field in slots))
 new=positive['allocation'];wrapper_usage=derive_typed_usage_context(image,new['instructionVa']-base,label='ScriptTaskParam.wrapper')
 need('own-ScriptTask-wrapper-allocation-and-constructor',(wrapper_usage['tag'],wrapper_usage['typeName'])==(1,wrapper.name)
  and new['constructorVa']==base+records['.ctor']['pointerRva'])
 usage=derive_typed_usage_context(image,positive['constantContext']['instructionVa']-base,label='ScriptTaskParam.constant')
 child=derive_value(image,pins,type_name=VALUE);value_read=_value_reader(image,pins,usage,calls['constValue'],child)
 offsets=scalar.reader_offsets(image,'ScriptTaskParam');header=_record(image,positive['headerTargetVa']);primitive.object_header_source(image,header,offsets)
 need('same-ScriptTask-two-Int32-sources',calls['idRef']==calls['paramSource'])
 integer=_record(image,calls['idRef']);scalar.integer_source(image,integer,offsets,'ScriptTaskParam.integer')
 path=pooled_source_helper.validate_on_image(image,calls['path'],pins)
 def tail(record):
  at,raw=record['instructions'][-1];raw=bytes.fromhex(raw);need('owned-ScriptTask-reference-tail',raw[:1]==b'\xe9')
  return base+at+5+int.from_bytes(raw[1:],'little',signed=True)
 barrier=tail(records['set___path__'])
 need('same-ScriptTask-output-and-reference-field-barriers',all(p['barrierTargetVa']==barrier for p in(programs[0],programs[2],programs[3]))
  and all(tail(records[n])==barrier for n in('.ctor','CreateInstance','set___constValue__')))
 _publication_gate(image,pins)
 return dict(schema='endfield.story-condition-script-task-param-source.v1',nativeInputs=pins,typeName=TYPE,valueType=VALUE,
  sourceAdmitted=True,canonicalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(parameter=parameter,programs=programs,child=child,valueRead=value_read,wrapperAllocation=wrapper_usage,
   headerSource=header,integerSource=integer,pooledPath=path,barrierTargetRva=barrier-base,
   sourceWindows=body['windows'],sourceRegions=[[a,raw.hex().upper()]for a,raw in body['regions']]))


def derive(image,pins):
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader,_reference_join,_capability
 from scripts.game_data.codecs.levelscript.current_condition_script_task_param import validate,CAP_SCHEMA
 source=derive_source(image,pins);reader=_reader(image,pins);reference=_reference_join(image,pins,VALUE)
 need('own-ScriptTask-Param-reference-getter',reference['getterMethodDefinition']==source['proof']['parameter']['methods']['GetValue']['methodIndex'])
 cap=_capability(VALUE,'script-task-ptr-value',0,reader,reference['adapter'])
 cap.update(schema=CAP_SCHEMA,constantWireBytes=None,positiveWireBytes=None,positiveWireBytesRange=[14,18],
  constantMemberCount=1,constantField='key',constantFieldEncoding='int32-pool-index',constantManagedBytes=8,
  constantDefaultZeroBytes=8,actualValueCallbackEqualsCanonicalRequired=True,runtimeTaskResolutionProved=False)
 validate(cap)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,referenceReader=reader,capabilities={CAPABILITY:cap},
  owners=[dict(status='validated-conditional-Param-child',typeName=TYPE,valueType=VALUE,capability=cap,
   proof=dict(wrapperSource=source,**{k:v for k,v in reference.items()if k!='getterMethodDefinition'}),parentFieldAdmitted=False,wholeOwnerAdmitted=False)],
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
