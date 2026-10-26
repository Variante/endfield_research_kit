"""Finite list-valued Params with separately proved selected element sources.

Each actual Param ReadPackable call retains its own closed MethodSpec and
source target. The string callback consumes pool indices; UInt32 owns its
unsigned callback; EntityPtr owns MC3/default and the whole hidden40 copy.
Matching callback/provider choice, normal helpers, initialized contexts and
adequate fresh or reused-empty capacity remain explicit conditions.
"""
import json

from scripts.game_data.memorypack.levelscript_condition_param_sources import PREFIX,need

SCHEMA='endfield.story-condition-list-param-sources.v1'
LIST='System.Collections.Generic.List`1<'
ENTITY='Beyond.Gameplay.Core.EntityPtr'
LSM='Beyond.Gameplay.Core.LsmPtr'
ELEMENTS=('string','uint',ENTITY,LSM)
TYPES=tuple(LIST+element+'>'for element in ELEMENTS)


def constant_call(parent,value_type):
 """Select only the actual E8 immediately following this closed typed read."""
 usage=parent.get('typedRead',{})
 need('own-list-Param-closed-request',value_type in TYPES
  and(usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))
    ==('MemoryPack.MemoryPackReader','ReadPackable',[],[value_type])
  and type(usage.get('instructionRva'))is int and type(usage.get('instructionHex'))is str)
 rows=parent.get('parent',{}).get('instructions',[])
 sites=[i for i,row in enumerate(rows)if row==[usage['instructionRva'],usage['instructionHex']]]
 need('one-own-list-Param-context-site',len(sites)==1)
 calls=[row for row in rows[sites[0]+1:]if bytes.fromhex(row[1])[:1]==b'\xe8']
 need('own-list-Param-value-call',bool(calls))
 site,encoded=calls[0];raw=bytes.fromhex(encoded)
 need('exact-list-Param-E8',type(site)is int and len(raw)==5 and raw[0]==232)
 target=site+5+int.from_bytes(raw[1:],'little',signed=True)
 need('positive-list-Param-source-target',target>0)
 return dict(sourceInstruction=[site,encoded],sourceTargetRva=target,typedRequest=usage)


def _derive_one(image,pins,element):
 if element==LSM:
  from scripts.game_data.memorypack.levelscript_condition_lsm_list_sources import derive
  return derive(image,pins)
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _reference_join
 from scripts.game_data.memorypack import reference_param,numeric_list_sources,entity_list_sources,skill_pooled_string_list_sources
 value_type=LIST+element+'>';dependencies={}
 def load(name):
  raw=(CONTRACTS_DIR/name).read_bytes();fact=json.loads(raw)
  need('list-Param-same-reviewed-inputs:'+name,fact.get('nativeInputs')==pins)
  dependencies[name]=raw;return fact
 if element=='string':
  fact=load('levelscript_null_list_param_native.json')
  row,=[r for r in fact['components']if r['valueType']==value_type]
  parent,*_=reference_param.derive_reference_parameter(image,pins,row['profile'],value_type,reader_method='ReadPackable')
  call=constant_call(parent,value_type)
  child=skill_pooled_string_list_sources.derive(image,pins,typed_request=call['typedRequest'],
   call_target=image.pe.image_base+call['sourceTargetRva'],count_limit=10000)
  limit=child['capabilities'][skill_pooled_string_list_sources.CAPABILITY]['countLimit']
 elif element=='uint':
  from scripts.game_data import levelscript_int_list_native
  from scripts.game_data.memorypack.counted_loop_sources import prove_induction
  fact=load('levelscript_numeric_list_param_native.json');dependency=load('levelscript_int_list_native.json')
  levelscript_int_list_native._validate_native(image,dependency)
  row,=[r for r in fact['components']if r['elementType']=='uint']
  child=numeric_list_sources.derive(image,pins,row,dependency);parent=child['parent'];call=constant_call(parent,value_type)
  listing=child['child'];certificate=prove_induction(listing['listPrograms'],initial='458bfe',increment='41ffc7',
   comparison='453bfd',counter='r15d',saved_count='R13D loaded once from signed collection header; R14D proved zero before R15D copy.')
  child['countInduction']=certificate;limit=certificate['maxCount']
 else:
  need('finite-owned-Entity-list-element',element==ENTITY)
  child=entity_list_sources.derive(image,pins);parent=child['parent'];call=constant_call(parent,value_type)
  limit=child['countInduction']['maxCount']
 reference=_reference_join(image,pins,value_type)
 getter=parent['ownedMethods']['GetValue']['pointerRva']
 need('same-own-list-Param-getter',getter==reference['getter']['entryRva'])
 image.check_instruction_windows([call['sourceInstruction']],label='conditionListParam.actualConstantCall')
 for name,raw in dependencies.items():need('list-Param-contract-bookend:'+name,(CONTRACTS_DIR/name).read_bytes()==raw)
 return dict(status='validated-conditional-list-Param-source',typeName=PREFIX+value_type+'>',valueType=value_type,
  elementType=element,countLimit=limit,sourceAdmitted=True,canonicalAdapterAdmitted=True,
  actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
  proof=dict(parent=parent,elementList=child,actualConstantCall=call,
   **{k:v for k,v in reference.items()if k!='getterMethodDefinition'}),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,*,element_types):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 need('explicit-distinct-list-Param-elements',isinstance(element_types,(tuple,list))and 0<len(element_types)<=len(ELEMENTS)
  and all(type(e)is str and e in ELEMENTS for e in element_types)and len(set(element_types))==len(element_types))
 _publication_gate(image,pins);owners=[]
 for element in element_types:
  try:owners.append(_derive_one(image,pins,element))
  except(ValueError,KeyError,IndexError,TypeError)as error:
   import traceback
   sites=[dict(function=f.name,line=f.lineno,source=f.filename.replace('\\','/').split('/scripts/',1)[-1])
    for f in traceback.extract_tb(error.__traceback__)[-8:]]
   owners.append(dict(status='pendingReview',valueType=LIST+element+'>',elementType=element,sourceAdmitted=False,
    reason=str(error)[:2200],diagnostic=dict(errorType=type(error).__name__,sourceCallSites=sites),
    canonicalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,owners=owners,
  complete=sum(o.get('sourceAdmitted')is True for o in owners),parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
