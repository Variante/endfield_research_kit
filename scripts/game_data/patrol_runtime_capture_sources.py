"""Finite source-owned observational layouts for the Patrol capture preparer.

Only the caller's freshly selected NativeImage supplies facts. Source programs
establish physical storage roles; runtime class, MethodInfo and callback
selection remain observations to obtain. No saved report, open-generic field
offset, wire grammar or live selection is accepted as an input.
"""
from __future__ import annotations
import json

SCHEMA='endfield.patrol-capture-read-layouts.v1'
FAMILIES=('callbacks','points','values')
LIST='System.Collections.Generic.List`1'
POINT='Beyond.Gameplay.AI.Config.NpcPatrolPoint'
ACTION='Beyond.Gameplay.Core.PatrolAction'
EXECUTOR='Beyond.Gameplay.Actions.ActionExecutor'
PTR='Beyond.ObjectPtr`1<'+EXECUTOR+'>'


def need(check,condition):
    if not condition:raise ValueError('patrolCaptureSources.'+check)


def _owner(value):
    return {key:value[key]for key in('schema','status','nativeInputs')}


def _callbacks(manager):
    """Observe actual slot pairs selected by the independently proved callers."""
    p=manager['proof'];result={}
    for role in('actionEnter','actionExecute'):
        request=p['requiredRuntimeCallbacks'][role];program=p['programs'][role]
        declaration=request['nominalDeclaration']
        need('same-actual-callback-source:'+role,request['ordinaryAbiRequired']is True
            and request['slot']==program['callbackSlot']==declaration['slot']
            and request['callbackOffset']==program['callbackOffset']
            and request['methodInfoOffset']==program['methodInfoOffset']==request['callbackOffset']+8
            and program['callbackNormalReturnRequired']is True)
        result[role]=dict(receiverType=declaration['owner'],selector=request['slot'],
            callbackOffset=request['callbackOffset'],methodInfoOffset=request['methodInfoOffset'],byteCount=16,
            evidence=dict(owner=_owner(manager),declaration=declaration,request=request,
                source=p['sources'][role],program=program),liveSelectionObserved=False,
            actualCallbackEffectsProved=False)
    return result


def _point_transfers(points):
    p=points['proof'];programs=p['programs'];need('point-copy-programs',bool(programs))
    first=programs[0];slices=first['positionSlices'];at=0
    for offset,width in slices:
        need('contiguous-complete-position-copy',type(offset)is type(width)is int and offset==at and width>0)
        at+=width
    need('same-independent-point-copy-shapes',all(v['orderedPointTransferSourceProved']is True
        and(v['positionSlices'],v['gaitBytes'],v['subActionsReferenceBytes'])==
            (slices,first['gaitBytes'],first['subActionsReferenceBytes'])for v in programs))
    return dict(positionBytes=at,gaitBytes=first['gaitBytes'],subActionsReferenceBytes=first['subActionsReferenceBytes'],
        evidence=dict(owner=_owner(points),caller=p['caller'],programs=programs,induction=p['induction']))


def _reference_layout(element,item,add,evidence):
    """Both actual closed programs must agree on every sampled storage role."""
    need('exact-finite-reference-element',element in(POINT,ACTION))
    need('GetItem-complete-reference-return',item.get('normalReturn')is True
        and item.get('referenceBitsUnchanged')is True and item.get('elementBytes')==8)
    need('Add-complete-reference-store',add.get('normalReturn')is True
        and add.get('wholeReferenceStoredUnchanged')is True and add.get('elementBytes')==8
        and add.get('versionIncrementCount')==add.get('sizeIncrementCount')==1)
    need('independent-GetItem-and-Add-storage-agreement',item['listItemsOffset']==add['listItemsOffset']
        and item['listSizeOffset']==add['listSizeOffset']and item['arrayDataOffset']==add['arrayDataOffset'])
    slots=(item['listItemsOffset'],item['listSizeOffset'],add['listVersionOffset'])
    need('disjoint-instance-storage',all(type(n)is int and n>=16 for n in slots)
        and len(set(slots))==3 and slots[0]+8<=slots[1]and slots[1]+4<=slots[2])
    need('bounded-array-storage',type(item['arrayLengthOffset'])is int and item['arrayLengthOffset']>=16
        and type(item['arrayDataOffset'])is int and item['arrayDataOffset']>=item['arrayLengthOffset']+8)
    return dict(type=LIST+'<'+element+'>',elementType=element,countField=LIST+'::_size',
        versionField=LIST+'::_version',itemsField=LIST+'::_items',countOffset=slots[1],
        versionOffset=slots[2],storageOffset=slots[0],arrayLengthOffset=item['arrayLengthOffset'],
        arrayDataOffset=item['arrayDataOffset'],elementStride=item['elementBytes'],evidence=evidence,
        openGenericOffsetsRead=False,runtimeInflatedClassLayoutObserved=False,
        condition='The observed receiver and typed context select these independently proved closed reference-list storage programs.')


def _closed_reference_list(selected,points,role):
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack import leveldata_patrol_point_sources as source
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_value_list_context import bind_list_add_abi
    p=points['proof'];image=selected.image
    element,join_key=(POINT,'point-get-item')if role=='points'else(ACTION,'action-add')
    joins=p['closedReceiverJoins'];join=joins[join_key]
    need('actual-own-closed-reference-receiver',join['receiver']['name']==LIST+'<'+element+'>'
        and len(join['receiver']['classArguments'])==1 and join['receiver']['classArguments'][0]['name']==element
        and bytes.fromhex(join['receiver']['classArguments'][0]['rawHex'])[10:12]==b'\x12\x00')
    get_definition=joins['point-get-item']['methodDefinition'];add_definition=joins['action-add']['methodDefinition']
    entries=GenericEntries(image)
    def registered(definition,method):
        try:return entries.resolve(definition,[element],[])
        except ValueError as exc:
            raise ValueError(json.dumps(dict(validator='patrol_runtime_capture_sources',
                failedCheck='exact_closed_collection_method_source',role=role,elementType=element,
                requestedMethod=method,methodDefinition=definition,
                classArguments=[element],methodArguments=[],
                sourcePath=str(getattr(image,'gameassembly','<selected image>')),
                expected='One independently owned source for this exact closed receiver and method.',
                actual=str(exc)[:1500],nativeAdmissionGranted=False),sort_keys=True))from exc
    def actual(call_role,definition,source_key):
        declared=p['closedReceiverJoins'][call_role];target=p['actualTargets'][call_role]
        need('same-actual-closed-caller-target:'+call_role,declared['actualSourceTargetRva']==target
            and declared['methodDefinition']==definition
            and p['typedUsages'][call_role]['methodSpec'][0]==definition)
        calls=[call for program in p['programs']for call in program['calls']if call['role']==call_role]
        need('same-complete-loop-actual-target:'+call_role,bool(calls)
            and all(call['targetVa']==image.pe.image_base+target for call in calls))
        packet=owned(image,image.pe.image_base+target);old=p[source_key]['source']
        need('same-fresh-actual-source-packet:'+call_role,packet['windows']==old['windows']
            and [[a,b.hex().upper()]for a,b in packet['regions']]==old['regions'])
        return packet,dict(selection='actual-direct-closed-caller',methodDefinition=definition,
            actualClosedReceiver=declared,typedUsage=p['typedUsages'][call_role],actualCalls=calls,
            caller=p['caller'],canonicalPointerEquivalenceClaimed=False)
    if role=='points':
        get_source,get_selection=actual('point-get-item',get_definition,'item')
        add_registration=registered(add_definition,'Add');add_source=owned(image,add_registration['pointer'])
        add_selection=dict(selection='exact-closed-registration',registration=add_registration)
    else:
        add_source,add_selection=actual('action-add',add_definition,'add')
        get_registration=registered(get_definition,'get_Item');get_source=owned(image,get_registration['pointer'])
        get_selection=dict(selection='exact-closed-registration',registration=get_registration)
    item_storage=source.storage_program(get_source['regions'],get_source['pointer'],role='point-get-item')
    disabled=image.pe.image_base+p['disabledBarrier']['result']['disabledFlagRva']
    need('fresh-independently-proved-disabled-collector',type(disabled)is int and disabled>image.pe.image_base)
    add_storage=source.storage_program(add_source['regions'],add_source['pointer'],role='action-add',disabled=disabled)
    item=item_storage['program'];add=add_storage['program']
    abi=bind_list_add_abi(image,add_definition)
    need('own-by-value-Add-formal',abi['formalKind']==19 and abi['formalByRef']is False)
    def packet(value):return dict(entryRva=value['pointer']-image.pe.image_base,
        windows=value['windows'],regions=[[at,raw.hex()]for at,raw in value['regions']])
    return _reference_layout(element,item,add,dict(parent=join,GetItemSelection=get_selection,
        AddSelection=add_selection,AddFormal=abi,GetItemSource=packet(get_source),AddSource=packet(add_source),
        GetItemProgram=item,AddProgram=add,GetItemStorage=item_storage,AddStorage=add_storage,
        disabledBarrier=p['disabledBarrier'],ListDeclarations=p['ListFieldDeclarations']))


def derive_read_layouts(selected,*,families=None):
    """Called only by preparation on its exact fresh selected source owner."""
    from scripts.game_data.mission_trace_capture_prepare import SelectedMethods
    from scripts.game_data.il2cpp.native_image import NativeImage
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import pooled_source_helper
    from scripts.game_data.memorypack import leveldata_patrol_point_sources as point_sources
    from scripts.game_data.memorypack import leveldata_patrol_manager_sources as manager_sources
    from scripts.game_data.memorypack import leveldata_patrol_checkpoint_value_sources as value_sources
    from scripts.game_data.memorypack import leveldata_patrol_resource_id_sources as id_sources
    from scripts.game_data.memorypack import leveldata_patrol_radio_request_sources as radio_sources
    need('fresh-selected-native-owner',type(selected)is SelectedMethods and type(selected.image)is NativeImage)
    families=FAMILIES if families is None else families
    need('finite-source-families',type(families)in(tuple,list)and bool(families)
        and all(type(v)is str and v in FAMILIES for v in families)and len(set(families))==len(families))
    families=tuple(sorted(families))
    image=selected.image;pins=pooled_source_helper._contract()['nativeInputs'];_publication_gate(image,pins)
    result=dict(schema=SCHEMA,nativeInputs=dict(pins),sourceFamilies=list(families),containers={},values={},callbacks={},proof={},
        nativeSources=dict(gameassembly=str(image.gameassembly.resolve()),metadata=str(image.metadata_path.resolve())),
        openGenericOffsetsRead=False,runtimeSelectionObserved=False,liveContainerContentsObserved=False,wireGrammarAdmitted=False)
    if 'points'in families:
        points=point_sources.derive(image,pins)
        need('own-point-transfer-source',points['schema']==point_sources.SCHEMA and points['nativeInputs']==pins
            and points['pointFieldTransferSourceProved']is True and points['actualListItemSourceProved']is True
            and points['sufficientCapacityAddSourceProved']is True)
        for role in('points','actions'):
            layout=_closed_reference_list(selected,points,role);result['containers'][layout['type']]=layout
        result['pointTransfers']=_point_transfers(points)
        result['proof'].update(pointSource=_owner(points),nominalFields=points['proof']['nominalFields'],
                              ListDeclarations=points['proof']['ListFieldDeclarations'])
    if 'callbacks'in families or 'values'in families:
        manager=manager_sources.derive(image,pins);mp=manager['proof']
        need('own-manager-family',manager['schema']==manager_sources.SCHEMA and manager['nativeInputs']==pins
             and manager['selectedNormalManagerPostambleEffectsProved']is True)
        result['executorState']=mp['crossStageState']
        result['executorTimer']=dict(source=mp['epsilon'],program=mp['programs']['timer'])
        result['proof']['managerSource']=_owner(manager)
    if 'callbacks'in families:
        result['callbacks']=_callbacks(manager)
    if 'values'in families:
        values=value_sources.derive(image,pins);handles=id_sources.derive(image,pins);radio=radio_sources.derive(image,pins)
        need('same-current-source-inputs',all(v['nativeInputs']==pins for v in(values,handles,radio)))
        queue=mp['programs']['queueAdd'];receiver=values['proof']['programs']['receiverAdapter'];wrapper=radio['proof']['programs']['wrapper']
        need('whole-ObjectPtr-copy-source',queue['allObjectPtrBitsPreserved']is True
             and queue['entryBytes']==queue['sourceBytes']==queue['elementBytes'])
        need('whole-EntityPtr-source',values['selectedReceiverAdapter40TransferProved']is True and receiver['allValueBitsUnchanged']is True)
        need('whole-handle-source',handles['selectedConstructorAndRetainHandleEffectsProved']is True)
        need('whole-Radio-source',radio['completeRadioValue56ConstructionAndTransferProved']is True and wrapper['normalReturn']is True)
        vp=values['proof'];hp=handles['proof'];rp=radio['proof']
        value_layouts={PTR:dict(byteCount=queue['entryBytes'],evidence=dict(owner=_owner(manager),
            source=mp['sources']['queueAdd'],program=queue,typedUsages=mp['typedUsages'],
            fields=mp['fields']['Beyond.Gameplay.Actions.ActionBase'])),
        'Beyond.Gameplay.Core.EntityPtr':dict(byteCount=receiver['valueBytes'],evidence=dict(owner=_owner(values),
            source=vp['helpers']['receiverAdapter'],program=receiver,fields=vp['fields']['entityPtr'],typedRequests=vp['typedRequests'])),
        'Beyond.Resource.FAssetProxyUntrackedHandle':dict(byteCount=handles['outputBytes'],evidence=dict(owner=_owner(handles),
            source=hp['helpers']['constructor'],program=hp['programs']['constructor'],
            fields=hp['fields']['Beyond.Resource.FAssetProxyUntrackedHandle'])),
        'Beyond.Resource.FAssetProxyHandle':dict(byteCount=handles['outputBytes'],evidence=dict(owner=_owner(handles),
            source=hp['helpers']['constructor'],program=hp['programs']['constructor'])),
        radio_sources.PAYLOAD:dict(byteCount=wrapper['copiedBytes'],evidence=dict(owner=_owner(radio),
            source=rp['helpers']['wrapper'],program=wrapper,layout=rp['payloadLayout'],actualUsages=rp['actualUsages']))}
        for name,layout in value_layouts.items():
            need('bounded-source-owned-value:'+name,type(layout['byteCount'])is int and 1<=layout['byteCount']<=256)
            if name!=PTR:need('same-concrete-selected-size:'+name,selected.value_size(name)==layout['byteCount'])
            layout.update(type=name,runtimeTypeSelectionObserved=False,wireGrammarAdmitted=False)
        result['values']=value_layouts
    _publication_gate(image,pins)
    return result
