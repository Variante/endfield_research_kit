"""Selected complete New Patrol initializer control and local-reference flow.

Every external helper must return normally with its documented Win64 argument,
frame and nonvolatile obligations. Lookup results, the conversion's effects and
live virtual selections are separate proofs. Logging/replacement alternatives
and runtime invocation are not supplied by these finite normal source paths.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_patrol_config_prefix_sources import CONTROLLER,CONFIG,CORE

SCHEMA='endfield.story-patrol-initializer-control-source.v1'
LEVEL_NPC='Beyond.Gameplay.LevelNpcData'
ENTITY='Beyond.Gameplay.Core.Entity'
MODES=('null-config','disabled','entity-lookup-miss','config-lookup-miss-kept','converted')


def need(check,condition):
 if not condition:raise ValueError('storyPatrolInitializer.'+check)


def program(regions,entry,offsets,*,mode,eligibility='enabled-new',replacement_table_present=False):
 """Full selected caller, including its real entry frame and normal RET.

The selector-set/get helper relation is deliberately not assumed. Eligibility
is the actual LevelNpc input expression; the selected getter return is a
separate condition of each path.
"""
 need('finite-normal-source-mode',mode in MODES)
 need('finite-input-eligibility',eligibility in('disabled','other-config-kind','enabled-new'))
 need('literal-replacement-presence',type(replacement_table_present)is bool)
 need('exact-own-named-input-fields',set(offsets)=={'doPatrol','patrolCfgType','patrolId','entity','entityKey'}
  and all(type(v)is int and 16<=v<2**31 for v in offsets.values()))
 d=lambda name:offsets[name].to_bytes(4,'little').hex()
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
 def finish():g.take('488b5c2450','488b742458','4883c440','5f','c3')
 g.take('4889742410','57','4883ec40');replacement=g.relative('488b05')
 g.take('488bf9','488bf2','488b4838','4885c9');g.branch('0f85',replacement_table_present)
 if replacement_table_present:
  g.take('488b81f09a0000','4885c0');g.branch('0f84',True)
 g.take('48895c2450','33db','48895c2468','48895c2430','48895c2438','4885f6')
 g.branch('74',mode=='null-config',1)
 if mode=='null-config':finish()
 else:
  g.take('389a'+d('doPatrol'));g.branch('74',eligibility=='disabled',1)
  if eligibility!='disabled':
   g.take('399a'+d('patrolCfgType'));g.branch('74',eligibility=='enabled-new',1)
  if eligibility=='enabled-new':g.take('b801000000');g.jump('eb',1)
  else:g.take('8bc3')
  g.take('4885ff');g.branch('74',False,1)
  g.take('85c0');g.branch('75',eligibility=='enabled-new',1)
  if eligibility=='enabled-new':g.take('41b001');g.jump('eb',1)
  else:g.take('4533c0')
  g.take('b906000000','488bd7');call('set-doPatrol-slot6')
  g.take('b905000000','488bd7');call('get-doPatrol-slot5')
  g.take('84c0');g.branch('0f85',mode!='disabled')
  if mode=='disabled':
   g.take('4533c0','488bd7');call('install-null-Core');finish()
  else:
   g.take('488b8f'+d('entity'),'4885c9');g.branch('0f84',False)
   need('literal-small-entity-key-displacement',16<=offsets['entityKey']<128)
   g.take('8b49'+bytes((offsets['entityKey'],)).hex(),'488d542468','4533c0');call('lookup-entity-config')
   g.take('84c0');g.branch('0f84',mode=='entity-lookup-miss')
   if mode=='entity-lookup-miss':finish()
   else:
    g.take('488b4c2468','4885c9');g.branch('0f84',False)
    g.take('8b96'+d('patrolId'),'4c8d442430','4533c9');call('lookup-patrol-config')
    g.take('84c0');g.branch('74',mode=='config-lookup-miss-kept',1)
    if mode=='converted':
     g.take('488b542430','4c8d442438','4533c9','488bcf');call('convert-Config-to-Core')
     g.take('4c8b442438','488bd7');call('install-converted-Core')
    g.take('b907000000','488bd7');call('get-patrolData-slot7')
    g.take('4885c0');g.branch('0f85',True);finish()
 return dict(selectedBytes=g.seen,mode=mode,inputEligibility=eligibility,replacementTablePresent=replacement_table_present,
  replacementRootCellVa=replacement,selectedReplacementAbsentRequired=True,calls=calls,
  eligibleInputExpression='LevelNpcData.doPatrol != 0 and LevelNpcData.patrolCfgType == 0',
  requestedDoPatrolValue=None if mode=='null-config'else eligibility=='enabled-new',
  selectedDoPatrolGetterResult=None if mode=='null-config'else mode!='disabled',
  selectedEntityLookupResult=None if mode in('null-config','disabled')else mode!='entity-lookup-miss',
  selectedConfigLookupResult=None if mode in('null-config','disabled','entity-lookup-miss')else mode=='converted',
  selectedFinalCoreGetterNonnullRequired=mode in('config-lookup-miss-kept','converted'),
  locals=dict(configReference=[48,56],coreReference=[56,64],entityConfigReference=[104,112]),
  frame=dict(entryRspDelta=-72,callShadow=[0,32],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushed=['rdi']),
  entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'],entryAlignmentPreservedForCalls=True,
  lookupOutputLocalsInitiallyZero=True,configLocalPassedToConversion=mode=='converted',
  sameCoreOutputLocalValuePassedToInstall=mode=='converted',normalReturn=True,
  helperEffectsProved=False,conversionEffectsProved=False,installedCoreSemanticsProved=False,
  wholeInitializerProved=False,runtimeInvocationObserved=False,playbackProved=False)


def derive(image,pins):
 """Fresh exact New controller/LevelNpc fields, helpers and complete source."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import _vtable
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_patrol_install_sources import derive as install_source
 _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
 installation=install_source(image,pins);owner=ctx.index.types[CONTROLLER]
 initializer,=[m for m in md.methods_for(owner)if md.string(m.name_index)=='_InitLevelData']
 scalar.owned_method_abi(image,ctx,initializer.index,owner.index,('void',1,False),[(LEVEL_NPC,18,True)],'storyPatrolInitializer.method')
 caller=pointer.owned(image,image.method_pointer_va(initializer));fields=[];offsets={}
 for role,typ,name,kind in(('doPatrol',LEVEL_NPC,'doPatrol',2),('patrolCfgType',LEVEL_NPC,'patrolCfgType',17),
  ('patrolId',LEVEL_NPC,'patrolId_New',8),('entity',CONTROLLER,'m_entity',18)):
  td=ctx.index.types[typ];field,=[f for f in md.fields_for(td)if md.string(f.name_index)==name]
  fact=list(ctx.field(typ+'::'+name));scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'storyPatrolInitializer.'+role,reference=kind==18)
  expected={'doPatrol':'bool','patrolCfgType':'Beyond.Gameplay.Core.NpcPatrolCfgType','patrolId':'int','entity':ENTITY}[role]
  need('exact-input-field-type:'+role,fact[:2]==[typ,expected]);offsets[role]=fact[2];fields.append(dict(role=role,field=fact))
 enum=ctx.index.types[fields[1]['field'][1]];backing,=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
 need('own-Int32-config-kind-enum',ctx.is_enum(md.type_full_name(enum))and md.string(backing.name_index)=='value__'and ctx.type_name(backing.type_index)=='int')
 scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,'storyPatrolInitializer.configKindBacking')
 # The selected owned input load supplies the offset. Resolve its unique exact
 # ordinary named field through the actual Entity ancestor chain, not by width.
 loads=[r for r in caller['rows']if bytes.fromhex(r['bytes'])[:2]==bytes.fromhex('8b49')and len(bytes.fromhex(r['bytes']))==3]
 load,=loads;offsets['entityKey']=int.from_bytes(bytes.fromhex(load['bytes'])[2:],'little',signed=True)
 candidates=[];name=ENTITY;trail=set()
 while name and name not in trail:
  trail.add(name);td=ctx.index.types[name]
  for f in md.fields_for(td):
   if ctx.field_attributes(f.type_index)&16:continue
   fact=list(ctx.field(name+'::'+md.string(f.name_index)))
   if fact[2]==offsets['entityKey']:candidates.append((f,fact))
  parent=ctx.parent(name)
  if parent=='object':
   # IL2CPP_TYPE_OBJECT is a primitive terminal code, not a constructed-name
   # alias or an invitation to apply the generic named-field resolver.
   scalar.ordinary(image,ctx.type_pointer(td.parent_index),28,'storyPatrolInitializer.terminalObject',reference=True)
   root=ctx.index.types['System.Object']
   need('primitive-Object-terminal-has-no-instance-fields',root.parent_index<0
    and not[f for f in md.fields_for(root)if not ctx.field_attributes(f.type_index)&16])
   break
  need('named-owned-Entity-ancestor',not parent or parent in ctx.index.types)
  name=parent
 need('one-own-Entity-key-field',len(candidates)==1)
 field,fact=candidates[0]
 scalar.ordinary(image,ctx.type_pointer(field.type_index),8,'storyPatrolInitializer.entityKey')
 fields.append(dict(role='entityKey',field=fact))
 programs=[program(caller['regions'],caller['pointer'],offsets,mode=mode,eligibility=eligibility,replacement_table_present=replaced)
  for mode in MODES for eligibility in(('enabled-new',)if mode=='null-config'else('disabled','other-config-kind','enabled-new'))for replaced in(False,True)]
 targets={}
 for p in programs:
  for c in p['calls']:
   need('one-current-target:'+c['role'],c['role']not in targets or targets[c['role']]==c['targetVa']);targets[c['role']]=c['targetVa']
 install=base+installation['proof']['helperTargetRva'];convert=base+installation['proof']['prefix']['proof']['metadataJoin']['method']['targetRva']
 need('same-own-installation-and-conversion',targets['install-null-Core']==targets['install-converted-Core']==install
  and targets['convert-Config-to-Core']==convert)
 methods=[]
 for method_name,slot,result,params in(('set_doPatrol',6,('void',1,False),[('bool',2,False)]),('get_doPatrol',5,('bool',2,False),[]),
  ('get_patrolData',7,(CORE,18,False),[])):
  method,=[m for m in md.methods_for(owner)if md.string(m.name_index)==method_name]
  scalar.owned_method_abi(image,ctx,method.index,owner.index,result,params,'storyPatrolInitializer.'+method_name)
  need('actual-unique-own-virtual-slot:'+method_name,method.slot==slot);_vtable(image,owner.index,slot,method.index,'storyPatrolInitializer.slot')
  methods.append(dict(method=[method.index,CONTROLLER,method_name,image.method_pointer_va(method)-base],slot=slot,
   actualSelectedCallbackEqualsOwnMethodRequired=True,callbackSourceEffectsProved=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-selected-initializer-control',nativeInputs=pins,
  proof=dict(method=[initializer.index,CONTROLLER,'_InitLevelData',caller['pointer']-base],namedFields=fields,
   sourceWindows=caller['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in caller['regions']],programs=programs,
   actualTargets={k:v-base for k,v in targets.items()},ownSelectedVirtualMethods=methods,installation=installation),
  selectedCompleteCallerControlProved=True,successfulConversionLocalFlowProved=True,
  wholeInitializerProved=False,wholeConversionProved=False,controllerInstallationObserved=False,
  helperEffectsProved=False,checkpointProducerProved=False,checkpointFilterProved=False,
  runtimeInvocationObserved=False,playbackProved=False,evidenceBoundary=dict(
   exact='Complete selected New-controller initializer normal control, own input expression, exact helper-call arguments, zeroed disjoint lookup/Config/Core locals, same conversion-output value passed to installation, complete entry frame and RET.',
   conditional=__doc__,unresolved=['external Boolean/lookup helper effects and nominal callback selection','full conversion semantics and installed value','logging, exception and replacement alternatives','live controller/initializer selection, checkpoints and playback']))))
