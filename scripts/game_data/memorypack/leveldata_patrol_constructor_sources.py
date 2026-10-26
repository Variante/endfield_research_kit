"""Own Patrol data/action constructor stores and controller loader creation.

Selected initialized-metadata paths retain the actual object from allocation
through its constructor and reference publication. Literal defaults are read
from the owned instructions. Allocation/constructor success, initialized typed
empty arrays, zeroed allocation and the disabled collector are conditions;
no live loader, asset result, wire schema or controller invocation is observed.
The controller proof ends just after its loader publication, not after its
remaining field initialization or base constructor.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

CORE='Beyond.Gameplay.Core.PatrolData'
ACTION='Beyond.Gameplay.Core.PatrolAction'
CONTROLLER='Beyond.Gameplay.AI.NewNpcAIPatrolController'
LIST='System.Collections.Generic.List`1'
SCHEMA='endfield.story-patrol-constructor-sources.v1'
CORE_FIELDS=(('snap',4),('inLocalSpace',1),('addBornPositionAsCheckpoint',1),('forbidNpcInteract',1),
 ('bornOverrideSpeed',4),('motionType',4),('coolDownBetweenWalkAndStop',4),('motionEnterDis',4),
 ('turnCheckTime',4),('turnCheckAngle',4),('turnCheckDis',4),('turnRadio',4),('limitPlayerActionType',4))


def need(check,condition):
 if not condition:raise ValueError('storyPatrolConstructors.'+check)


def registration_observation(rows,target,*,role):
 need('bounded-constructor-registration:'+role,type(rows)is list and len(rows)<=1)
 if rows:need('existing-constructor-registration-agrees-with-actual-E8:'+role,rows[0].get('pointer')==target)
 return dict(rows=rows,canonicalRegistrationPresent=bool(rows),actualCanonicalPointerEqual=bool(rows),
  directOwnCallerAndMethodSpecSourceRequired=True,runtimeContextSelectionObserved=False,canonicalCallbackAdmitted=False)


def _start(g,*,short=False,frame=32):
 g.take('48895c2408','57','4883ec'+bytes((frame,)).hex())
 ready=g.relative('803d')+1;g.take('00','488bd9');g.branch('74'if short else'0f84',False,1 if short else 4)
 return ready


def _store(g,offset,width):
 need('bounded-store-offset',type(offset)is int and 16<=offset<2**31 and width in(1,2,4))
 g.take(('c6'if width==1 else'66c7'if width==2 else'c7')+('43'if offset<128 else'83')+
  offset.to_bytes(1 if offset<128 else 4,'little').hex())
 return dict(offset=offset,bytes=width,rawHex=g.read(width).hex().upper())


def _list(g,field,role,*,short=False,tail=False):
 context_at=g.at;allocation_cell=g.relative('488b0d');allocate=g.relative('e8')
 g.take('488bf8','4885c0');g.branch('74'if short else'0f84',False,1 if short else 4)
 method_at=g.at;method_cell=g.relative('488b15');g.take('488bc8');construct=g.relative('e8')
 g.take('488d4b'+bytes((field,)).hex(),'48897b'+bytes((field,)).hex())
 barrier=None if tail else g.relative('e8')
 return dict(role=role,fieldOffset=field,allocationUsageInstructionVa=context_at,allocationCellVa=allocation_cell,
  allocationTargetVa=allocate,constructorUsageInstructionVa=method_at,constructorCellVa=method_cell,constructorTargetVa=construct,
  publicationTargetVa=barrier,sameAllocatedReferenceConstructedAndStored=True)


def core_program(regions,entry,offsets):
 g=BytesPath(regions,entry);ready=_start(g);stores=[_store(g,offsets['snap'],4)]
 need('two-adjacent-owned-bool-fields',offsets['addBornPositionAsCheckpoint']==offsets['inLocalSpace']+1)
 stores.append(_store(g,offsets['inLocalSpace'],2));stores.append(_store(g,offsets['forbidNpcInteract'],1))
 stores.append(_store(g,offsets['bornOverrideSpeed'],4));listing=_list(g,offsets['actions'],'actions')
 for name in ('motionType','coolDownBetweenWalkAndStop','motionEnterDis','turnCheckTime','turnCheckAngle','turnCheckDis','turnRadio'):
  stores.append(_store(g,offsets[name],4))
 string_at=g.at;string_cell=g.relative('488b05');g.take('488b88b8000000','488b01')
 slot=offsets['cameraControlState'].to_bytes(4,'little').hex();g.take('488d8b'+slot,'488983'+slot);barrier=g.relative('e8')
 need('same-reference-publication-helper',barrier==listing['publicationTargetVa'])
 stores.append(_store(g,offsets['limitPlayerActionType'],4));g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,entry=entry,readyFlagVa=ready,stores=stores,lists=[listing],
  stringTypeUsageInstructionVa=string_at,stringTypeCellVa=string_cell,stringStaticFieldsOffset=184,
  stringStaticSlotOffset=0,stringStoredAt=offsets['cameraControlState'],referencePublicationTargetVa=barrier,
  entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],normalReturn=True,selectedInitializedMetadataPath=True)


def action_program(regions,entry,offsets):
 g=BytesPath(regions,entry);ready=_start(g,short=True);store=_store(g,offsets['actionType'],4)
 first=_list(g,offsets['subPositions'],'subPositions',short=True)
 second=_list(g,offsets['subActions'],'subActions',short=True,tail=True)
 g.take('488b5c2430','4883c420','5f');tail=g.relative('e9');second['publicationTargetVa']=tail
 need('same-reference-publication-helper',tail==first['publicationTargetVa'])
 return dict(selectedBytes=g.seen,entry=entry,readyFlagVa=ready,stores=[store],lists=[first,second],
  referencePublicationTargetVa=tail,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],normalReturnViaDisabledBarrier=True,
  selectedInitializedMetadataPath=True)


def loader_prefix_program(regions,entry,offsets):
 g=BytesPath(regions,entry);ready=_start(g,frame=48);store=_store(g,offsets['m_lastMoveStyleChangeT'],4)
 usage_at=g.at;cell=g.relative('488b0d');allocate=g.relative('e8');g.take('488bf8','4885c0');g.branch('0f84',False)
 g.take('41b90a000000','48c744242000000000','4533c0','b238','488bc8');construct=g.relative('e8')
 slot=offsets['m_assetLoader'].to_bytes(4,'little').hex();g.take('488d8b'+slot,'4889bb'+slot);barrier=g.relative('e8')
 return dict(selectedBytes=g.seen,entry=entry,readyFlagVa=ready,stores=[store],allocationUsageInstructionVa=usage_at,
  allocationCellVa=cell,allocationTargetVa=allocate,constructorTargetVa=construct,publicationTargetVa=barrier,
  sameAllocatedLoaderConstructedAndStored=True,loaderFieldOffset=offsets['m_assetLoader'],
  constructorArguments=dict(receiver='same allocated reference',dl=56,r8d=0,r9d=10,stackFifthArgument=0),
  continuationInstructionVa=g.at,remainingControllerConstructorProved=False,selectedInitializedMetadataPath=True)


def vector_list_constructor_program(regions,entry,*,barrier,ready=True):
 need('literal-vector-list-class-ready',type(ready)is bool)
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488bf9','488bda','488b4a20','33d2','488b89c0000000')
 indexed=g.relative('e8');g.take('83b8e000000000');g.branch('74',not ready,1);initialize=None
 if not ready:g.take('488bc8');initialize=g.relative('e8');g.jump('eb',1)
 g.take('488b4b20','33d2','488b89c0000000');need('same-vector-list-indexed-context-helper',g.relative('e8')==indexed)
 g.take('488b88b8000000','488b01','488d4f10','48894710','488b5c2430','4883c420','5f')
 need('same-vector-list-disabled-barrier-tail',g.relative('e9')==barrier)
 return dict(selectedBytes=g.seen,entry=entry,ready=ready,indexedContextTarget=indexed,classInitializerTarget=initialize,
  contextSlot=0,methodInfoClassOffset=32,classContextOffset=192,classStaticFieldsOffset=184,staticReferenceSlot=0,
  unchangedStaticReferenceStoredAtReceiverOffset=16,initializedTypedEmptyArrayRequired=True,zeroedCountAndVersionRequired=True,
  incomingMethodInfoPreserved=True,listCountAndVersionWritten=False,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],
  normalReturnViaDisabledBarrier=True)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.memorypack import leveldata_patrol_lead_sources as lead_source,pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_patrol_list_growth_sources import constructor_program
 _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);symbols=ContextSymbols(image)
 lead=lead_source.derive(image,pins);points=lead['proof']['pointTransfer'];programs={};sources={};fields={};constructors={}
 for name in(CORE,ACTION,CONTROLLER):
  td=ctx.index.types[name];need('own-ordinary-reference:'+name,not ctx.is_value_type(name)and td.generic_container_index<0)
  ctor,=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor'and m.parameter_count==0 and not m.flags&16]
  scalar.owned_method_abi(image,ctx,ctor.index,td.index,('void',1,False),[],SCHEMA+'.ctor')
  constructors[name]=dict(methodDefinition=ctor.index,targetRva=image.method_pointer_va(ctor)-base)
  own={}
  for f in md.fields_for(td):
   if ctx.field_attributes(f.type_index)&16:continue
   field=md.string(f.name_index);own[field]=dict(field=list(ctx.field(name+'::'+field)),typeName=ctx.type_name(f.type_index),
    typePointerVa=ctx.type_pointer(f.type_index),rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(f.type_index),16).hex().upper())
  fields[name]=own;body=pointer.owned(image,image.method_pointer_va(ctor));offsets={key:value['field'][2]for key,value in own.items()}
  program={CORE:core_program,ACTION:action_program,CONTROLLER:loader_prefix_program}[name](body['regions'],body['pointer'],offsets)
  programs[name]=program;sources[name]=dict(sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']])
 need('exact-conversion-Core-constructor',programs[CORE]['entry']==points['proof']['prefix']['proof']['programs'][0]['constructorTargetVa'])
 need('exact-conversion-action-constructor',programs[ACTION]['entry']==base+points['proof']['actualTargets']['construct-action'])
 scalar_fields={CORE:[name for name,width in CORE_FIELDS],ACTION:['actionType'],CONTROLLER:['m_lastMoveStyleChangeT']};enum_fields={}
 for owner,names in scalar_fields.items():
  for name in names:
   f=fields[owner][name];raw=bytes.fromhex(f['rawTypeHex']);typ=f['typeName'];kind={'bool':2,'float':12}.get(typ,17)
   need('own-scalar-default-field:'+owner+'::'+name,raw[10:12]==bytes((kind,128))and f['field'][:2]==[owner,typ])
   if kind==17:
    td=ctx.index.types[typ];backing,=[r for r in md.fields_for(td)if not ctx.field_attributes(r.type_index)&16]
    need('own-Int32-enum-default:'+typ,ctx.is_enum(typ)and md.string(backing.name_index)=='value__'and ctx.type_name(backing.type_index)=='int'
     and int.from_bytes(raw[:8],'little')==td.index)
    scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,SCHEMA+'.enumBacking');enum_fields[typ]=dict(typeDefinition=td.index,backingField=backing.index)
 usages={};list_sources={};disabled=base+points['proof']['disabledBarrier']['result']['disabledFlagRva']
 barrier=points['proof']['programs'][0]['calls'][2]['targetVa']
 for owner,p in programs.items():
  need('same-independently-owned-disabled-barrier:'+owner,p.get('referencePublicationTargetVa',p.get('publicationTargetVa'))==barrier)
  for listing in p.get('lists',[]):
   role=owner+'::'+listing['role'];allocation=derive_typed_usage_context(image,listing['allocationUsageInstructionVa']-base,label=SCHEMA+'.allocation')
   usage=derive_typed_usage_context(image,listing['constructorUsageInstructionVa']-base,label=SCHEMA+'.listCtor')
   f=fields[owner][listing['role']];receiver=symbols.type(f['typePointerVa']);args=receiver['classArguments'];arg,=args
   need('own-closed-List-field:'+role,receiver['definition']['name']==LIST and bytes.fromhex(f['rawTypeHex'])[10:12]==bytes((21,0)))
   need('exact-actual-list-constructor-request:'+role,(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
    (6,LIST,'.ctor',[arg['name']],[]))
   actual,=image.instantiations.resolve(usage['methodSpec'][1]).arguments
   allocated=symbols.type(ctx.type_pointer(allocation['typeIndex']));allocated_arg,=allocated['classArguments']
   need('same-actual-closed-list-allocation-field-and-constructor:'+role,allocation['tag']==1 and allocated['definition']['name']==LIST
    and actual.type_pointer_va==arg['typePointerVa']==allocated_arg['typePointerVa']and actual.raw_type_record_hex==arg['rawHex']==allocated_arg['rawHex'])
   entry=registration_observation(GenericEntries(image).observe(usage['methodSpec'][0],[arg['name']],[]),listing['constructorTargetVa'],role=role)
   ctor=md.methods[usage['methodSpec'][0]];scalar.owned_method_abi(image,ctx,ctor.index,ctx.index.types[LIST].index,('void',1,False),[],SCHEMA+'.listCtor')
   body=pointer.owned(image,listing['constructorTargetVa'])
   if arg['name']=='UnityEngine.Vector3':
    selected=[vector_list_constructor_program(body['regions'],body['pointer'],barrier=barrier,ready=r)for r in(True,False)]
   else:selected=[constructor_program(body['regions'],body['pointer'],disabled=disabled,ready=r)for r in(True,False)]
   usages[role]=dict(allocation=allocation,constructor=usage,actualClassInstantiation=image.instantiations.resolve(usage['methodSpec'][1]).as_dict(),fieldReceiver=receiver,registration=entry)
   list_sources[role]=dict(sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']],programs=selected)
 u=derive_typed_usage_context(image,programs[CORE]['stringTypeUsageInstructionVa']-base,label=SCHEMA+'.stringClass')
 need('own-String-static-default-source',(u.get('tag'),u.get('typeName'))==(1,'string'))
 usages['stringClass']=u
 p=programs[CONTROLLER];u=derive_typed_usage_context(image,p['allocationUsageInstructionVa']-base,label=SCHEMA+'.loaderClass')
 need('own-ordinary-concrete-loader-class',u['tag']==1 and bytes.fromhex(u['typeRawHex'])[10:12]==bytes((18,0)))
 loader=ctx.index.types[u['typeName']];ctor,=[m for m in md.methods_for(loader)if md.string(m.name_index)=='.ctor'and image.method_pointer_va(m)==p['constructorTargetVa']]
 need('own-concrete-loader-constructor',not ctor.flags&16 and ctor.parameter_count==3 and ctx.type_name(ctor.return_type)=='void')
 usages['loaderClass']=u;usages['loaderConstructor']=dict(methodDefinition=ctor.index,parameterTypes=[ctx.type_name(q.type_index)for q in md.parameters_for(ctor)])
 field=fields[CONTROLLER]['m_assetLoader'];need('own-controller-loader-interface-field',field['typeName']=='Beyond.Resource.IAssetLoader'and bytes.fromhex(field['rawTypeHex'])[10:12]==bytes((18,0)))
 need('same-selected-typed-allocation-helper',all(l['allocationTargetVa']==p['allocationTargetVa']for pr in programs.values()for l in pr.get('lists',[])))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-constructor-stores-and-loader-publication',nativeInputs=pins,
  proof=dict(lead=lead,fields=fields,constructors=constructors,programs=programs,sources=sources,actualTypedUsages=usages,listConstructorSources=list_sources,enumDeclarations=enum_fields),
  CoreAndActionInitializedConstructorStoreSourcesProved=True,actualTypedListConstructorSourcesProved=True,
  controllerLoaderCreationAndPublicationSourceProved=True,loaderConstructorBodyEffectsProved=False,
  remainingControllerConstructorProved=False,actualAllocationObserved=False,wholeConversionProved=False,wholeInitializerProved=False,
  runtimeInvocationObserved=False,playbackProved=False,evidenceBoundary=dict(exact='Own nominal fields, literal raw default stores, actual typed allocations/constructors and same-reference publications; selected complete Core/Action frames and controller loader prefix.',conditional=__doc__,
   unresolved=['concrete loader constructor body and actual successful allocation/initialized empty arrays','remaining controller constructor/base effects','asset lookup/validity and complete consumer chain']))))
