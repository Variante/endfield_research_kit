"""Explicit selected-animation extension of the current CharInteract cursor.

The caller owns the active native/pool operation. The legacy sparse framing
continues to handle every other root field; tag1 remains its one-element
profile. Only the independently proved tag8 list uses the bounded extension.
This pure codec cannot authenticate a component or enable a public reader.
"""
import json
from scripts.game_data.memorypack.char_perform_sparse import frame as sparse_frame,SparsePerformDecodeError
from scripts.game_data.memorypack.animation_union_codec import AnimationUnionReader
from scripts.game_data.memorypack.animation_char_loop_sources import CAPABILITY,UNION_CAPABILITY,ROOT,TYPE


def need(check,condition):
    if not condition:raise ValueError('charPerformCurrentCodec.'+check)


def _same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def frame(data,component,*,operation):
    need('own-selected-list-source',component.get('schema')=='endfield.animation-char-loop-sources.v1'
        and component.get('status')=='validated-conditional-animation-char-loop'
        and component.get('capability')==CAPABILITY and component.get('wholeOwnerAdmitted')is False)
    cap=operation.child(CAPABILITY);selected=component.get('capabilities',{}).get(CAPABILITY,{})
    need('same-operation-owned-list',_same(cap,selected)and cap.get('parentType')==ROOT
        and cap.get('parentField')=='loopActions'and cap.get('actualParentFieldAdmitted')is True
        and cap.get('elementType')==TYPE and cap.get('elementCapability')==UNION_CAPABILITY
        and cap.get('selectedElementTags')==[8]and cap.get('otherElementTagsAdmitted')is False
        and cap.get('positiveCountsAdmitted')is True and cap.get('elementGrammarAdmitted')is True
        and cap.get('nullable')is True and cap.get('nullElementMarker')==255
        and type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=10000)
    legacy=component.get('legacySparseProfile',{})
    need('same-root-full-sparse-profile',legacy.get('nativeInputs')==component.get('nativeInputs')
        and isinstance(legacy.get('fields'),list)and len(legacy['fields'])==28
        and [f['name']for f in legacy['fields']].count('loopActions')==1
        and isinstance(legacy.get('actorFields'),list)and len(legacy['actorFields'])==13
        and isinstance(legacy.get('actionFields'),list)and len(legacy['actionFields'])==18
        and legacy.get('allOtherRootProfilesUnchanged')is True)
    def decode_selected(payload,start,name,index):
        reader=AnimationUnionReader(payload,name,operation=operation);reader.pos=start
        value=reader.selected_union(UNION_CAPABILITY)
        need('exact-selected-char-animation',value.get('isNull')is False and value.get('tag')==8
            and value.get('typeName')=='Beyond.Gameplay.Core.CharInteractPerform.CharAnimActionData')
        action=dict(typeName='CharAnimActionData',qualifiedTypeName=value['typeName'],unionTag=8,unionTagHex='0x0008',
            memberCount=31,record=value['child'],runtimeAnimationProved=False)
        return dict(endOffset=reader.pos,action=action)
    try:
        result=sparse_frame(bytes(data),legacy['fields'],actor_fields=legacy['actorFields'],
            action_fields=legacy['actionFields'],strings=getattr(operation,'strings',None),
            selected_action_decoder=decode_selected,selected_action_count_limit=cap['countLimit'])
    except ValueError as error:
        if isinstance(error,SparsePerformDecodeError):raise
        raise SparsePerformDecodeError('loopActions selected current source: '+str(error))from error
    result.update(status='exact_current_char_interact_selected_animation_frame',
        schemaMappingId='endfield.char-interact-perform-current-animation.v1',unionMappingId=UNION_CAPABILITY,
        nativeInputs=component['nativeInputs'],selectedAnimationListAdmitted=True,
        allOtherRootProfilesUnchanged=True,runtimeAnimationProved=False,evidenceBoundary=__doc__)
    return result
