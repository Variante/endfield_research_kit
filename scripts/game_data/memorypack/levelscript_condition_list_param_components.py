"""Canonical reference Param children with independently owned positive lists."""
import json

from scripts.game_data.memorypack.levelscript_condition_list_param_sources import ELEMENTS,ENTITY,LSM,LIST

SCHEMA='endfield.story-condition-list-param-components.v1'


def capability(owner,reader):
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _capability,need
 from scripts.game_data.codecs.levelscript.current_condition_list_param import SCHEMA as CAP_SCHEMA,validate
 element=owner.get('elementType');value=LIST+str(element)+'>'
 need('same-owned-list-Param-composition',element in ELEMENTS and owner.get('valueType')==value
  and owner.get('status')=='validated-conditional-list-Param-source'and owner.get('sourceAdmitted')is True
  and owner.get('canonicalAdapterAdmitted')is True and type(owner.get('countLimit'))is int and owner['countLimit']==10000)
 cap=_capability(value,'owned-list',0,reader,owner['proof']['adapter'])
 cap.update(schema=CAP_SCHEMA,constantWireBytes=None,positiveWireBytes=None,elementType=element,
  collectionCountEncoding='signed-int32',collectionNullCount=-1,countLimit=owner['countLimit'],
  elementWireKind={'string':'pooled-string-index','uint':'u32',ENTITY:'entity-ptr-mc3',LSM:'lsm-ptr-mc1'}[element],
  elementWireBytes=None if element in(ENTITY,LSM)else 4,listSourceAdmitted=True,elementSourceAdmitted=True,
  callbackSelectionConditional=True,runtimeConstantEvaluationAdmitted=False,freshListsAdmitted=True,
  reusedListsRequireInitialCount=0,reusedListsRequireCapacityAtLeastCount=True)
 if element==ENTITY:
  source=owner['proof']['elementList'];cap.update(elementGrammar=source['elementGrammar'],runtimeEntityResolutionProved=False)
 if element==LSM:
  source=owner['proof']['elementList']['child']
  need('own-full-Lsm-MC1-default-and-canonical-child',source.get('status')=='validated-conditional-small-pointer-value'
   and source.get('typeName')==LSM and source.get('managedBytes')==8 and source.get('positiveWireBytes')==9
   and source.get('nullWireBytes')==1 and source.get('defaultZeroBytes')==8 and source.get('fieldName')=='id'
   and source.get('fieldType')=='ulong'and source.get('actualCallbackEqualsCanonicalRequired')is True)
  cap.update(elementGrammar=dict(nullMarker=255,memberCount=1,fields=['uint64'],nullOutput='default-zero8'),
   elementManagedBytes=8,actualElementValueCallbackEqualsCanonicalRequired=True,runtimeLsmResolutionProved=False)
 validate(cap);return cap


def derive_many(image,pins,*,element_types):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.levelscript_condition_list_param_sources import derive
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader,CAP_PREFIX
 _publication_gate(image,pins);source=derive(image,pins,element_types=element_types);reader=_reader(image,pins);owners=[];caps={}
 for row in source['owners']:
  if not row.get('sourceAdmitted'):owners.append(row);continue
  cap=capability(row,reader);caps[CAP_PREFIX+row['typeName']]=cap
  owners.append(dict(status='validated-conditional-Param-child',typeName=row['typeName'],valueType=row['valueType'],capability=cap,
   proof=dict(wrapperSource=row,**{k:v for k,v in row['proof'].items()if k in('closedCarrier','adapter','getter')}),
   parentFieldAdmitted=False,wholeOwnerAdmitted=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,referenceReader=reader,capabilities=caps,owners=owners,
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
