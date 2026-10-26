"""Pure pooled Brief/spawner children for a separately authenticated owner.

These cursors provide no selected-source, provenance, host or physical-EOF
authority. The owning current operation must compose each reached capability.
"""
from scripts.game_data.codecs.levelscript.current_collections import Reader,decode
from scripts.game_data.codecs.levelscript.param_graph import ParamGraphDecodeError


def decode_brief_dictionary(data,offset,*,strings):
    reader=Reader(data,offset,strings,'levelScriptBriefDataDict');start=offset
    count=reader.count(reader.field);rows=[];seen=set()
    for index in range(max(0,count)):
        child=f'{reader.field}[{index}]';at=reader.offset;key=reader.number('<Q',child+'.key')
        if key in seen:raise ParamGraphDecodeError(f'{child}:duplicate-key,offset={at},actual={key}')
        seen.add(key)
        if not reader.member(child,9):
            rows.append(dict(keyOffset=at,endOffset=reader.offset,scriptId=str(key),value=None));continue
        ranges={}
        def number(name,fmt):
            before=reader.offset;value=reader.number(fmt,child+'.'+name)
            ranges[name]=dict(startOffset=before,endOffset=reader.offset);return value
        def collection(name,kind):
            before=reader.offset;value,reader.offset=decode(data,reader.offset,kind,strings=strings)
            ranges[name]=dict(startOffset=before,endOffset=reader.offset);return value
        path_hash=number('dataPath','<Q')
        risks=collection('interactiveActiveRiskEntityIdList','System.Collections.Generic.List`1<ulong>')
        kind=number('levelScriptType','<i');max_stage=number('maxStage','<i')
        if kind not in range(6)or not 0<=max_stage<=1_000_000:
            raise ParamGraphDecodeError(f'{child}:unsupported-script-type-or-stage,offset={ranges["levelScriptType"]["startOffset"]}')
        parent=number('parentLevelScriptId','<Q')
        properties=collection('properties','System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>')
        mapping=collection('propertyIdToKeyMap','System.Collections.Generic.Dictionary`2<int,string>')
        refs=collection('refWorldEntityIdList','System.Collections.Generic.List`1<ulong>')
        embedded=number('scriptId','<Q')
        if embedded!=key:
            raise ParamGraphDecodeError(f'{child}:script-id-key-mismatch,offset={ranges["scriptId"]["startOffset"]},key={key},actual={embedded}')
        rows.append(dict(keyOffset=at,endOffset=reader.offset,scriptId=str(key),dataPathHash=str(path_hash),
            serializedMemberCount=9,interactiveActiveRiskEntityIdList=risks.get('values'),
            levelScriptType=kind,maxStage=max_stage,parentLevelScriptId=str(parent),
            propertyCount=properties.get('count'),properties=properties.get('values'),
            propertyMapCount=mapping.get('count'),propertyIdToKeyMap={str(r['key']):r['value']for r in mapping.get('entries')or[]},
            refWorldEntityCount=refs.get('count'),refWorldEntityIds=refs.get('values'),fieldRanges=ranges))
    return dict(startOffset=start,endOffset=reader.offset,count=count,entries=rows,
        value=None if count==-1 else rows)


def decode_spawner_list(data,offset,*,strings):
    reader=Reader(data,offset,strings,'spawners');start=offset;count=reader.count(reader.field);rows=[]
    for index in range(max(0,count)):
        child=f'spawners[{index}]';at=reader.offset
        if not reader.member(child,6):
            rows.append(dict(indexInCollection=index,startOffset=at,endOffset=reader.offset,value=None));continue
        belong=reader.number('<Q',child+'.belongLevelScriptId');config=reader.string(child+'.configId')
        event=reader.boolean(child+'.enableWaveDieEvent')
        position=[reader.single(child+'.position.'+axis)for axis in'xyz']
        rotation=[reader.single(child+'.rotation.'+axis)for axis in'xyz']
        identity=reader.number('<Q',child+'.spawnerId')
        rows.append(dict(indexInCollection=index,startOffset=at,endOffset=reader.offset,memberCount=6,
            belongLevelScriptId=str(belong),configId=config,enableWaveDieEvent=event,
            position=position,rotation=rotation,spawnerId=str(identity)))
    return dict(startOffset=start,endOffset=reader.offset,count=count,rows=rows,
        value=None if count==-1 else rows,itemFieldOrder=['belongLevelScriptId','configId',
            'enableWaveDieEvent','position','rotation','spawnerId'])
