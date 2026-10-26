"""Current pooled LevelScript templates; stop at the first unproved child."""
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


def _action_map(data,cursor,strings):
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
                value,cursor=decode_reviewed_node(data,cursor,family,strings=strings);values.append(value)
            data_map[field]=None if count==-1 else values
    try:blackboard,cursor=decode_param_blackboard(data,cursor,strings=strings)
    except ParamGraphDecodeError as error:raise LevelScriptTemplateFramingError(str(error)) from error
    return {'startOffset':start,'endOffset':cursor,'status':'exact_named_action_map','fields':{'dataMap':data_map,'paramBlackboard':blackboard}},cursor


def frame_levelscript_template(data:bytes,*,strings:StringPool|None=None):
    """Read the current order sequentially; never scan an opaque suffix for an ID."""
    gate=native.check_root_native_inputs()
    if gate.status!='validated':raise LevelScriptTemplateFramingError(f'template.native:{gate.status}:{gate.detail}')
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
            if field=='actionMap':value,end=_action_map(data,cursor,strings)
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
