"""Current pooled LevelScript templates; stop at the first unproved child.

Evidence and admission boundary:

Exact whole-template naming requires one sequential cursor and the matching
StringPool through physical EOF; the former inline terminal-suffix scan is
removed. Positive unsupported blackboard/property/task children stop before
contents and keep later bytes opaque, including apparent terminal IDs.
Bounded continuation diagnostics disappear only on named EOF. The selected
root fact proves declared order and terminal pooled source/owned setter;
reviewed nodes still need their own child gates. A final setup may reuse the
holder register for its pointee: preserve argument identity to that load and
prove the exact setup moves, not the dead old holder. Historical closures and
isolated children do not admit current owners or runtime provider choice.
"""
from __future__ import annotations
import struct
from scripts.game_data import serialization_roots_native as native
from scripts.game_data.codecs.levelscript.action_map import ActionMapCodecError,decode_reviewed_node
from scripts.game_data.string_pool import StringPool,resolve_string_pool_index
from scripts.game_data.codecs.levelscript.param_graph import decode_param_blackboard,ParamGraphDecodeError

ROOT_FIELDS=('actionMap','maxStage','properties','propertyIdToKeyMap','taskMap','templateId')
ROOT_MEMBER_COUNT=len(ROOT_FIELDS)


class LevelScriptTemplateFramingError(ValueError):
    """A selected template field cannot be read at its physical cursor."""


def _need(data,cursor,size,field):
    if cursor<0 or cursor+size>len(data):
        raise LevelScriptTemplateFramingError(f'{field}: truncated offset={cursor} size={size} length={len(data)}')


def _count(data,cursor,field):
    _need(data,cursor,4,field);value=struct.unpack_from('<i',data,cursor)[0]
    if not -1<=value<=10000:raise LevelScriptTemplateFramingError(f'{field}: invalid count={value} offset={cursor}')
    return value,cursor+4


def _empty_collection(data,cursor,field,empty):
    count,end=_count(data,cursor,field)
    if count>0:raise LevelScriptTemplateFramingError(f'{field}: positive count={count} offset={cursor}; current child composition is unproved')
    return None if count==-1 else empty,end


def _action_map(data,cursor,strings,*,game_root=None,null_list_params=None,numeric_list_params=None,camera_shake_params=None,buff_ptr_params=None,entity_list_params=None):
    start=cursor;_need(data,cursor,1,'actionMap')
    if data[cursor]==255:return None,cursor+1
    if data[cursor]!=2:raise LevelScriptTemplateFramingError(f'actionMap: expected memberCount=2 actual={data[cursor]} offset={cursor}')
    cursor+=1;_need(data,cursor,1,'actionMap.dataMap');data_map=None
    if data[cursor]==255:cursor+=1
    else:
        if data[cursor]!=3:raise LevelScriptTemplateFramingError(f'actionMap.dataMap: expected memberCount=3 actual={data[cursor]} offset={cursor}')
        cursor+=1;data_map={}
        for field,family in (('actionList','ActionBase'),('getterList','GetterBase'),('headerList','ActionHeader')):
            count,cursor=_count(data,cursor,'actionMap.dataMap.'+field);values=[]
            for _ in range(max(0,count)):
                value,cursor=decode_reviewed_node(data,cursor,family,strings=strings,game_root=game_root,null_list_params=null_list_params,numeric_list_params=numeric_list_params,camera_shake_params=camera_shake_params,buff_ptr_params=buff_ptr_params,entity_list_params=entity_list_params);values.append(value)
            data_map[field]=None if count==-1 else values
    try:blackboard,cursor=decode_param_blackboard(data,cursor,strings=strings,game_root=game_root)
    except ParamGraphDecodeError as error:raise LevelScriptTemplateFramingError(str(error)) from error
    return {'startOffset':start,'endOffset':cursor,'status':'exact_named_action_map','fields':{'dataMap':data_map,'paramBlackboard':blackboard}},cursor


def frame_levelscript_template(data:bytes,*,strings:StringPool|None=None,game_root=None,null_list_params=None,numeric_list_params=None,camera_shake_params=None,buff_ptr_params=None,entity_list_params=None):
    """Read the current order sequentially; never scan an opaque suffix for an ID."""
    gate=native.check_root_native_inputs(game_root=game_root)
    if gate.status!='validated':raise LevelScriptTemplateFramingError(f'template.native:{gate.status}:{gate.detail}')
    from importlib import import_module
    for owner,operation in (('null_list',null_list_params),('numeric_list',numeric_list_params),('camera_shake',camera_shake_params),('buff_ptr',buff_ptr_params),('entity_list',entity_list_params)):
        if operation is None:continue
        component=import_module('scripts.game_data.levelscript_'+owner+'_param_native')
        keywords={'game_root':game_root,'strings':strings}
        if owner in ('null_list','numeric_list'):keywords['codec_kind']=None
        getattr(component,'prepared_'+owner+'_audit')(operation,**keywords)
    records=[r for r in native.read_contract()['records'] if r['typeName']=='Beyond.Gameplay.LevelScriptTemplateData']
    if (len(records)!=1 or tuple(name for name,_ in records[0]['fields'])!=ROOT_FIELDS
            or records[0]['fields'][-1][1]!='string'):
        raise LevelScriptTemplateFramingError('template.native: current root declaration/source is unproved')
    if not data or data[0]!=ROOT_MEMBER_COUNT:
        raise LevelScriptTemplateFramingError(f'template member count mismatch: expected={ROOT_MEMBER_COUNT} actual={data[0] if data else None}')
    cursor=1;fields={};spans={};diagnostic=None;stop=None
    for field in ROOT_FIELDS:
        start=cursor
        try:
            if field=='actionMap':value,end=_action_map(data,cursor,strings,game_root=game_root,null_list_params=null_list_params,numeric_list_params=numeric_list_params,camera_shake_params=camera_shake_params,buff_ptr_params=buff_ptr_params,entity_list_params=entity_list_params)
            elif field=='maxStage':
                _need(data,cursor,4,field);value=struct.unpack_from('<i',data,cursor)[0];end=cursor+4
            elif field in ('properties','propertyIdToKeyMap','taskMap'):
                value,end=_empty_collection(data,cursor,field,[] if field=='properties' else {})
            else:
                _need(data,cursor,4,field);value=resolve_string_pool_index(struct.unpack_from('<i',data,cursor)[0],strings,field);end=cursor+4
        except (ActionMapCodecError,ValueError,IndexError,KeyError,struct.error) as error:
            stop=field;diagnostic={'gate':'sequentialField','field':field,'offset':start,'detail':str(error)[:1200]};break
        fields[field]=value;spans[field]={'startOffset':start,'endOffset':end};cursor=end
    if stop is None and cursor!=len(data):
        stop='physicalEOF';diagnostic={'gate':'physicalEOF','offset':cursor,'detail':f'expected EOF={cursor} actual length={len(data)}'}
    result={'status':'exact_named_template' if stop is None else 'exact_named_template_prefix','schemaStatus':'named_exact' if stop is None else 'partial',
            'serializedMemberCount':ROOT_MEMBER_COUNT,'bytesConsumed':cursor,'fieldOrder':list(fields),'fields':fields,'ranges':spans,
            'actionMap':fields.get('actionMap'),'opaqueMiddle':None if stop is None else {'startOffset':cursor,'endOffset':len(data),'length':len(data)-cursor},
            'evidenceBoundary':'Sequential current stored fields only. An unproved child stops the cursor and leaves all following bytes opaque; no runtime activation or graph execution is inferred.'}
    if 'templateId' in fields:result['templateId']={**spans['templateId'],'value':fields['templateId']}
    if stop is not None:result.update(stopField=stop,diagnostics=[diagnostic])
    return result
