"""Fresh nominal enum Param sources plus their own reference adapters.

The explicit requested Param names are classified by the independent enum
source owner. No enum spelling or underlying integer width activates a child.
Outer ReadValue requests, containing frames and recursive unions remain open.
"""
import json

from scripts.game_data.memorypack.levelscript_condition_param_sources import CAP_PREFIX

SCHEMA='endfield.story-condition-enum-param-components.v1'
LABEL='storyConditionEnumParamComponents'


def derive_many(image,pins,parameter_types):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.levelscript_condition_enum_param_sources import derive_one
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader,_reference_join,_capability,need
 from scripts.game_data.codecs.levelscript.current_condition_enum_param import SCHEMA as CAP_SCHEMA,validate
 need('explicit-distinct-enum-Param-selection',isinstance(parameter_types,(list,tuple))and 0<len(parameter_types)<=256
  and all(type(n)is str and n for n in parameter_types)and len(set(parameter_types))==len(parameter_types))
 _publication_gate(image,pins);reader=_reader(image,pins);owners=[];capabilities={}
 for name in parameter_types:
  try:
   source=derive_one(image,pins,type_name=name)
   need('own-complete-enum-Param-source',source.get('status')=='validated-conditional-enum-param-source'
    and source.get('nativeInputs')==pins and source.get('typeName')==name and source.get('sourceAdmitted')is True)
   value=source['valueType'];forwarder=None
   from scripts.game_data.memorypack.levelscript_bitset_param_forwarder_sources import TYPE as BITSET,derive as bitset_forwarder
   if name==BITSET:
    need('own-inline-Bitset-source-profile',source['proof'].get('sourceProfile')=='bitset-inline-enum-raw4')
    forwarder=bitset_forwarder
   reference=_reference_join(image,pins,value,forwarder_prover=forwarder)
   need('enum-source-same-actual-GetValue',source['proof']['parameter']['methods']['GetValue']['methodIndex']==reference['getterMethodDefinition'])
   cap=_capability(value,source['constantWireKind'],source['constantWireBytes'],reader,reference['adapter'])
   nominal=source['nominal']
   cap.update(schema=CAP_SCHEMA,enumSourceAdmitted=True,enumBackingType=nominal['backingType'],
    enumCarrier=nominal['carrier'],enumDeclaration=nominal['enumDeclaration'],genericHeapLayoutInferred=False)
   validate(cap);capabilities[CAP_PREFIX+name]=cap
   owners.append(dict(status='validated-conditional-Param-child',typeName=name,valueType=value,capability=cap,
    proof=dict(wrapperSource=source['proof'],enumSource=source,
     **{k:v for k,v in reference.items()if k!='getterMethodDefinition'}),parentFieldAdmitted=False,wholeOwnerAdmitted=False))
  except(ValueError,KeyError,IndexError,TypeError)as error:
   import traceback
   from pathlib import Path
   sites=[dict(source=Path(frame.filename).as_posix().split('/scripts/',1)[-1],function=frame.name,line=frame.lineno)
    for frame in traceback.extract_tb(error.__traceback__)[-8:]]
   owners.append(dict(status='pendingReview',typeName=name,reason=str(error)[:2200],
    diagnostic=dict(validator=LABEL,errorType=type(error).__name__,failedGate=str(error).split(':',1)[0],
     expected='own complete nominal enum Param source, closed reference carrier, getter and canonical adapter',actual=str(error)[:1600],sourceCallSites=sites),
    parentFieldAdmitted=False,wholeOwnerAdmitted=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,referenceReader=reader,owners=owners,capabilities=capabilities,
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
