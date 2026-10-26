"""Three exact Module value adapter/getter schedules, without nominal admission.

These finite byte programs own complete selected normal effects and frames.
Their callers must independently join the actual nominal type, registration,
wrapper source, conversion interface and callback selection. No size alias,
wire grammar or generic managed-value domain follows from a matching schedule.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

EFFECT='Beyond.Gameplay.FogNestControllerData+EffectInfo'
AIRWALL='Beyond.Gameplay.Core.AirWallPtr'
OPERA='Beyond.Gameplay.EncounterData+OperaSegment'
WIDTHS={EFFECT:48,AIRWALL:24,OPERA:16}


def need(key,condition):
 if not condition:raise ValueError('moduleValueTransferProgram.'+key)


def _calls(g,symbols):
 roles={}
 def call(role):
  at=g.at;target=g.relative('e8');need('same-role:'+role,role not in roles or roles[role]==target)
  if symbols is not None:need('independent-role:'+role,symbols.get(role)==target)
  roles[role]=target;return at
 return roles,call


def adapter_program(regions,entry,*,type_name,symbols=None,null=False,create=True):
 need('literal-finite-profile',type_name in WIDTHS and type(null)is bool and type(create)is bool)
 g=BytesPath(regions,entry);roles,call=_calls(g,symbols);air=type_name==AIRWALL;effect=type_name==EFFECT
 if air:
  g.take('48896c2410','4889742418','57','4883ec20');ready=flag(g)
  g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
  g.take('488b4720','488bce','488b90c0000000','488b12');call('readNull');g.take('84c0');g.branch('0f85',null)
  type_site=None;type_cell=None
  if null:g.take('0f57c0','33c0','0f114500','48894510');g.jump('e9')
  else:
   g.take('48895c2430','488b4720');type_site=g.at;type_cell=g.relative('488b0d')
   g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
   g.take('33d2','488bcb');call('typeHandle');g.take('488b5c2430','4885c0');g.branch('74',False,1)
   g.take('33d2','488bc8');call('creationTest');g.take('84c0');g.branch('75',not create,1)
   if create:g.take('488b4720','488b88c0000000','488b4958');call('activate')
   else:g.take('33c0');g.jump('eb',1)
   g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');call('nonnull')
  g.take('488b6c2438','488b742440','4883c420','5f','c3')
 else:
  g.take('488bc4','48895808','48896810','48897018','48897820','4156','4883ec20',
   '33f6'if effect else'33ff','498be9'if effect else'498bf1')
  ready=g.relative('403835'if effect else'40383d')
  g.take('498bf8'if effect else'498be8','4c8bf2');g.branch('75',True,1)
  context='488b4520'if effect else'488b4620'
  g.take(context,'498bce','488b90c0000000','488b12');call('readNull');g.take('84c0');g.branch('75',null,1)
  type_site=None;type_cell=None
  if null:
   g.take('0f57c0')
   if effect:g.take('0f1107','0f114710','0f114720')
   else:g.take('0f114500')
  else:
   g.take(context);type_site=g.at;type_cell=g.relative('488b0d')
   g.take('488b98c0000000','488b5b50');call('classInit');g.take('33d2','488bcb');call('typeHandle')
   g.take('4885c0');g.branch('75',True,1)
   g.take('33d2','488bc8');call('creationTest');g.take('84c0');g.branch('75',not create,1)
   if create:
    g.take(context,'488b88c0000000','488b4958');call('activate');g.take('488bf0'if effect else'488bf8')
   g.take('488b4d20'if effect else'488b4e20','4c8bc6'if effect else'4c8bc7',
    '488bd7'if effect else'488bd5','4c8b89c0000000','498bce','4d8b4918');call('nonnull');g.jump('eb',1)
  g.take('488b5c2430','488b6c2438','488b742440','488b7c2448','4883c420','415e','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,symbolTargets=roles,metadataReadyFlagVa=ready,
  typeClassInstructionVa=type_site,typeClassCellVa=type_cell,canonicalFF=null,createWrapper=None if null else create,
  defaultZeroOutputBytes=WIDTHS[type_name]if null else 0,managedOutputBytes=WIDTHS[type_name],
  actualNullWireBytes=1 if null else None,sameIncomingReaderAndOutput=True,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  nominalAdmissionGranted=False,wrapperWireGrammarAdmitted=False,actualCallbackSelectionObserved=False)


def nonnull_program(regions,entry,*,type_name,symbols=None,wrapper_null=False):
 need('literal-finite-profile',type_name in WIDTHS and type(wrapper_null)is bool)
 g=BytesPath(regions,entry);roles,call=_calls(g,symbols);air=type_name==AIRWALL;effect=type_name==EFFECT
 frame=64 if air else 80 if effect else 48;home=frame+32
 g.take('48895c2408','4889742410','4c89442418','57','4883ec'+bytes((frame,)).hex());ready=flag(g)
 g.take(*(('498bf9','488bf2','488bd9')if air else('498bf1','488bda','488bf9')))
 g.branch('0f84',False)if air else g.branch('75',True,1)
 provider_site=g.at;provider_cell=g.relative('488b0d')
 if air:g.take('83b9e000000000');g.branch('0f84',False)
 else:call('classInit')
 g.take('488b4f20'if air else'488b4e20');call('resolve')
 g.take('488b88c0000000','488b4920');call('wrapperProvider');g.take('4885c0')
 g.branch('0f84',False)if air else g.branch('75',True,1)
 g.take('b905000000','4c8d4c24'+bytes((home,)).hex(),'4c8bc3'if air else'4c8bc7','488bd0')
 invoke=call('wrapperInvoke');g.take(('488b5c24'if air else'488b7c24')+bytes((home,)).hex(),'4885db'if air else'4885ff')
 g.branch('0f84',wrapper_null)if air else g.branch('75',not wrapper_null,1)
 conversion=None;barrier_offset=None
 if wrapper_null:
  g.take('0f57c0')
  if air:g.take('33c0','0f1106','48894610');g.jump('e9')
  elif effect:g.take('0f1103','0f114310','0f114320');g.jump('eb',1)
  else:g.take('0f1103');g.jump('eb',1)
 else:
  g.take('488b4f20'if air else'488b4e20');call('resolve')
  if air:g.take('ba08000000','488b88c0000000');call('indexed');g.take('4c8bc0','488d4c2420','33d2','4c8bcb')
  else:g.take('488b88c0000000','488b4940');call('resolve');g.take('4c8bcf','488d4c2420','4c8bc0')
  conversion=call('conversion')
  if air:g.take('0f1008','f20f104010','0f110e','f20f114610')
  elif effect:
   g.take('488bcb','0f1000','0f104810','0f105020','0f1103','0f114b10','0f115320');call('barrier');barrier_offset=0
  else:g.take('488d4b08','0f1000','f30f7f03');call('barrier');barrier_offset=8
 g.take('488b5c24'+bytes((frame+16,)).hex(),'488b7424'+bytes((frame+24,)).hex(),
  '4883c4'+bytes((frame,)).hex(),'5f','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,symbolTargets=roles,metadataReadyFlagVa=ready,
  providerClassInstructionVa=provider_site,providerClassCellVa=provider_cell,wrapperNull=wrapper_null,
  managedOutputBytes=WIDTHS[type_name],defaultZeroBytes=WIDTHS[type_name]if wrapper_null else 0,
  wholeGetterCopiedBytes=0 if wrapper_null else WIDTHS[type_name],selectedBarrierOutputOffset=barrier_offset,
  wrapperInvokeInstructionVa=invoke,conversionInstructionVa=conversion,wrapperSlot=5,conversionMethodSlot=0,
  sameIncomingReaderAndOutput=True,frame=dict(entryRspDelta=-(frame+8),shadowRspRange=[0,32],
   hiddenGetterLocal=[32,32+WIDTHS[type_name]],wrapperEntryHome=[24,32]),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,nominalAdmissionGranted=False)


def conversion_program(regions,entry,*,type_name,prepare,ordinal):
 need('finite-conversion-hit',type_name in WIDTHS and type(ordinal)is int and 0<=ordinal<=32)
 g=BytesPath(regions,entry);air=type_name==AIRWALL;effect=type_name==EFFECT;frame=64 if air else 80 if effect else 48
 g.take('48895c2408','48896c2410','4889742418')
 if air:g.take('48897c2420','4156','4883ec40','498b39','488bf1','488bcf','0fb7ea','4d8bf1','498bd8')
 else:g.take('57','4883ec'+bytes((frame,)).hex(),'498b19','488be9','488bcb','498bf9','498bf0')
 g.call(prepare)
 if air:g.take('440fb78730010000','33c0','66413bc0')
 else:g.take('440fb78330010000','33d2','66413bd0')
 g.branch('73',False,1);g.take('488b97b0000000'if air else'488b8bb0000000')
 for index in range(ordinal+1):
  g.take('0fb7c8'if air else'0fb7c2','4803c9'if air else'4803c0','48391cca'if air else'483934c1')
  g.branch('74',index==ordinal,1)
  if index<ordinal:g.take('66ffc0'if air else'66ffc2','66413bc0'if air else'66413bd0');g.branch('72',True,1)
 if air:g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7')
 else:
  g.take('488b83b0000000','0fb7ca','4803c9','486344c808','4883c014','48c1e004','4803c3');g.jump('eb',1)
 g.take('4c8b08','488d4c2420','4c8b4008','498bd6'if air else'488bd7');site=g.at;g.take('41ffd1')
 if air:g.take('488b5c2450','488b6c2458','488b7c2468','0f1000','f20f104810','488bc6','0f1106','f20f114e10',
  '488b742460','4883c440','415e','c3')
 elif effect:g.take('488b5c2460','488b742470','0f1000','0f104810','0f114500','0f104020','488bc5','0f114d10','0f114520',
  '488b6c2468','4883c450','5f','c3')
 else:g.take('488b5c2440','488b742450','0f1000','488bc5','0f114500','488b6c2448','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,interfaceOrdinal=ordinal,getValueMethodSlot=0,
  incomingSelectorRequired=0 if air else None,managedOutputBytes=WIDTHS[type_name],getterCallInstructionVa=site,
  copiedSlices=[[0,16],[16,8]]if air else[[0,16],[16,16],[32,16]]if effect else[[0,16]],
  sameOutputReturnedInRax=True,entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  interfaceFallbackAdmitted=False,nominalAdmissionGranted=False)


def null_program(regions,entry,*,symbols=None,null=False,near=False):
 need('literal-null-path',type(null)is bool and type(near)is bool)
 g=BytesPath(regions,entry);roles,call=_calls(g,symbols)
 g.take('4053','4883ec20','488bd9','c644243000');call('peek');g.take('84c0')
 g.branch('0f85'if near else'75',null,4 if near else 1)
 if null:
  g.take('488d542430','488bcb');call('header');g.take('b001')
  if near:g.jump('e9')
 elif not near:g.jump('eb',1)
 g.take('4883c420','5b','c3')
 return dict(selectedBytes=g.seen,symbolTargets=roles,null=null,consumedBytes=int(null),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True)
