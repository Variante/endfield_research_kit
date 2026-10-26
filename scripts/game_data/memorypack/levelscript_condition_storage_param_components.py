"""Finite storage Param children with fresh source and canonical reference joins."""
import json

from scripts.game_data.memorypack.levelscript_condition_storage_param_sources import POINTER_TYPES,SCRIPT,ENTITY

SCHEMA='endfield.story-condition-storage-param-components.v1'
TYPES=POINTER_TYPES+('long',ENTITY,SCRIPT)


def derive_many(image,pins,value_types):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.levelscript_condition_storage_param_sources import derive_one
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader,_reference_join,_capability,CAP_PREFIX,need
 from scripts.game_data.codecs.levelscript.current_condition_storage_param import SCHEMA as CAP_SCHEMA,validate
 need('explicit-distinct-storage-Param-selection',isinstance(value_types,(list,tuple))and 0<len(value_types)<=len(TYPES)
  and all(type(n)is str and n in TYPES for n in value_types)and len(set(value_types))==len(value_types))
 _publication_gate(image,pins);reader=_reader(image,pins);owners=[];capabilities={}
 for value in value_types:
  try:
   source=derive_one(image,pins,value_type=value);reference=_reference_join(image,pins,value)
   need('own-complete-storage-Param-source',source.get('sourceAdmitted')is True and source.get('nativeInputs')==pins)
   wire,width=source['constantWireKind'],source['constantWireBytes']
   cap=_capability(value,wire,width if width is not None else 14,reader,reference['adapter'])
   cap.update(schema=CAP_SCHEMA,constantValueEvaluationAdmitted=False)
   if value in POINTER_TYPES:
    cap['constantValueFields']=source['proof']['valueFields']
    getter=source['proof']['parameter']['methods']['GetValue']['methodIndex']
    need('own-pointer-Param-getter',getter==reference['getterMethodDefinition'])
   elif value=='long':
    getter=source['proof']['parameter']['methods']['GetValue']['methodIndex']
    need('own-signed-Param-getter',getter==reference['getterMethodDefinition'])
   elif value==SCRIPT:
    actual=source['proof']['source'];cap.update(constantValueFields=actual['valueFields'],
     copiedUninterpretedRanges=source['proof']['copiedUninterpretedRanges'],runtimeScriptResolutionProved=False)
    need('own-raw16-Param-getter',actual['ownedMethods']['GetValue']['pointerRva']==reference['getter']['entryRva'])
   else:
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.leveldata_entity_ptr_components import derive as derive_entity,CAP
    outer=source['proof']['source']['outer'];call=next(p['calls']['value']for p in outer['paths']if not p['outerNull'])
    entity=derive_entity(image,pins,typed_request=outer['valueContext'],source_target=control_transfer(call)['target'])
    cap.update(constantWireBytes=None,positiveWireBytes=None,positiveWireBytesRange=[14,27],constantCapability=entity['capabilities'][CAP])
    source['constantComponent']=entity
   validate(cap);key=CAP_PREFIX+source['typeName'];capabilities[key]=cap
   owners.append(dict(status='validated-conditional-Param-child',typeName=source['typeName'],valueType=value,capability=cap,
    proof=dict(wrapperSource=source,**{k:v for k,v in reference.items()if k!='getterMethodDefinition'}),
    parentFieldAdmitted=False,wholeOwnerAdmitted=False))
  except(ValueError,KeyError,IndexError,TypeError)as error:
   import traceback
   sites=[dict(function=f.name,line=f.lineno,source=f.filename.replace('\\','/').split('/scripts/',1)[-1])
    for f in traceback.extract_tb(error.__traceback__)[-8:]]
   owners.append(dict(status='pendingReview',valueType=value,typeName='Beyond.Gameplay.Actions.Param`1<'+value+'>',
    reason=str(error)[:2200],diagnostic=dict(validator='storyConditionStorageParamComponents',sourceCallSites=sites),
    parentFieldAdmitted=False,wholeOwnerAdmitted=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,referenceReader=reader,owners=owners,capabilities=capabilities,
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
