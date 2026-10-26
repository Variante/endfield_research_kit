"""Private finite Char record cursor with shared budget and explicit children.

Union tags, collection framing and containing routes belong to their owners.
Each delegated operation supplies an independent capability validator as well
as its parser; all child capabilities are checked before even a record FF.
"""
from scripts.game_data.memorypack.animation_record_codec import AnimationRecordReader
from scripts.game_data.memorypack.char_record_components import PLANS,CAP_PREFIX,WIRE

ATOMS={'bool-byte':1,'byte':1,'scalar32':4,'gameplay-tag32':4,'float32-bits':4,
 'scalar64-bits':8,'float64-bits':8,'vector2-raw8':8,'unity-vector3-raw12':12,
 'unity-quaternion-raw16':16,'animation-clip-raw36':36,'char-hand-ik-raw8':8,
 'layer-mask-raw4':4,'audio-id-raw4':4}
PROFILES={'body-type-def-value':'body-type-def-value','alpha-blend-value':'skill-alpha-blend',
 'beyond-curve-value':'beyond-curve-value','transform-desc-profile':'animation-transform-desc','byte-payload':'byte-payload'}


def need(key,condition):
 if not condition:raise ValueError('charRecordCodec.'+key)


def require_capability(cap,*,ordinary=False):
 need('finite-exact-whole-record',isinstance(cap,dict)and cap.get('typeName')in PLANS
  and type(cap.get('memberCount'))is int and cap['memberCount']==PLANS[cap['typeName']]
  and type(cap.get('wrapperName'))is str and bool(cap['wrapperName'])
  and cap.get('nullable')is True and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
  and cap.get('wholeGrammarAdmitted')is True and cap.get('directWrapperGrammarAdmitted')is True
  and cap.get('actualContainingRouteAdmitted')is False and cap.get('wholeOwnerAdmitted')is False)
 reads=cap.get('orderedReads',[])
 need('complete-current-ordered-fields',isinstance(reads,list)and len(reads)==cap['memberCount']
  and len({r.get('fieldName')for r in reads})==len(reads)
  and all(type(r.get('memberIndex'))is int and r['memberIndex']==i and type(r.get('fieldName'))is str
   and bool(r['fieldName'])and type(r.get('kind'))is str and bool(r['kind'])
   and(r.get('childCapability')is None if r['kind']in ATOMS else type(r.get('childCapability'))is str and bool(r['childCapability']))for i,r in enumerate(reads)))
 for read in reads:
  if read['kind']in PROFILES:need('exact-standard-profile-key',read['childCapability']==PROFILES[read['kind']])
 if ordinary:
  need('own-ordinary-original-and-callback',all(cap.get(k)is True for k in('ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved',
   'ownConcreteFactorySemanticsProved','callbackSelectionConditional','actualCallbackEqualsProvedChildRequired','ordinaryOriginalCallbackAdmitted'))
   and cap.get('valueStorageKind')=='reference8'
   and cap.get('sourceReferenceKind')==18 and type(cap.get('sourceReferenceKind'))is int
   and cap.get('referenceOutputBytes')==8 and type(cap.get('referenceOutputBytes'))is int
   and all(type(cap.get(k))is int and cap[k]>0 for k in('originalTypeDefinition','canonicalAdapterTargetRva',
    'formatterDeserializeMethodDefinition','referenceReaderMethodDefinition','referenceReaderTargetRva')))
 return cap


def _standard_validator(wire,cap):
 if wire=='body-type-def-value':
  from scripts.game_data.memorypack.body_type_value_codec import require_capability
 elif wire=='alpha-blend-value':
  from scripts.game_data.memorypack.alpha_blend_value_codec import require_capability
 elif wire=='beyond-curve-value':
  from scripts.game_data.memorypack.beyond_curve_value_codec import require_capability
 elif wire=='transform-desc-profile':
  from scripts.game_data.memorypack.animation_transform_desc_codec import require_capability as transform
  return transform(cap,ordinary=True)
 else:
  need('own-pooled-string-capability',wire=='byte-payload'and cap.get('wholeGrammarAdmitted')is True
   and cap.get('encoding')=='int32-pool-index'and cap.get('emptyIndex')==-1 and cap.get('nullIndex')==-2)
  return cap
 return require_capability(cap)


class CharRecordReader(AnimationRecordReader):
 def __init__(self,data,source,limit=None,*,operation,child_handlers=None,child_validators=None):
  super().__init__(data,source,limit,operation=operation)
  self.child_handlers=dict(child_handlers or{});self.child_validators=dict(child_validators or{})
  need('paired-explicit-child-handlers',set(self.child_handlers)==set(self.child_validators)
   and all(callable(x)for x in list(self.child_handlers.values())+list(self.child_validators.values())))

 def record(self,capability,*,depth=0,budget=None):
  need('literal-bounded-record-depth',type(depth)is int and 0<=depth<=64)
  budget={'remaining':100000}if budget is None else budget
  need('shared-bounded-node-budget',isinstance(budget,dict)and set(budget)=={'remaining'}
   and type(budget['remaining'])is int and 0<budget['remaining']<=1000000)
  cap=require_capability(self.operation.child(capability))
  need('same-exact-primary-record-key',capability==CAP_PREFIX+cap['typeName'])
  # Capability checks precede FF, so null never bypasses a missing child proof.
  for read in cap['orderedReads']:
   wire=read['kind'];child=read['childCapability']
   if wire in ATOMS:continue
   child_cap=self.operation.child(child)
   if wire in PROFILES:_standard_validator(wire,child_cap)
   elif wire==WIRE:
    require_capability(child_cap,ordinary=True);need('same-finite-record-child-key',child==CAP_PREFIX+child_cap['typeName'])
   else:
    need('owned-explicit-child-wire',wire in self.child_handlers and wire in self.child_validators)
    self.child_validators[wire](child,child_cap)
  budget['remaining']-=1;start=self.pos;fields=[];null=self.peek()==255
  if null:self.take(1,capability+'.null')
  else:
   self.header(cap['memberCount'])
   for read in cap['orderedReads']:
    at=self.pos;wire=read['kind'];child=read['childCapability'];extra={}
    if wire in ATOMS:
     raw=self.take(ATOMS[wire],capability+'.'+read['fieldName']);extra['rawHex']=raw.hex().upper()
     if wire=='animation-clip-raw36':extra.update(wrapperFramingUsed=False,boolBytesNormalized=False,paddingHex=raw[34:36].hex().upper())
    elif wire=='byte-payload':extra['value']=self.byte_payload()
    elif wire=='body-type-def-value':
     from scripts.game_data.memorypack.body_type_value_codec import read as read_body
     extra['child']=read_body(self,child,depth=depth+1)
    elif wire=='alpha-blend-value':
     from scripts.game_data.memorypack.alpha_blend_value_codec import read_alpha
     extra['child']=read_alpha(self,child,depth=depth+1)
    elif wire=='beyond-curve-value':
     from scripts.game_data.memorypack.beyond_curve_value_codec import read_curve
     extra['child']=read_curve(self,child)
    elif wire=='transform-desc-profile':
     from scripts.game_data.memorypack.animation_transform_desc_codec import read as read_transform
     extra['child']=read_transform(self,child,depth=depth+1)
    elif wire==WIRE:extra['child']=self.record(child,depth=depth+1,budget=budget)
    else:extra['child']=self.child_handlers[wire](self,child,depth=depth+1,budget=budget)
    fields.append(dict(fieldName=read['fieldName'],kind=wire,start=at,end=self.pos,**extra))
  result=dict(kind=capability,typeName=cap['typeName'],start=start,end=self.pos,isNull=null,fields=fields,
   containingRouteClaimed=False,runtimeAnimationProved=False)
  self.records.append(result);return result
