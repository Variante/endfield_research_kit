"""AnimationConfig publication requires the complete current MC15 reader."""
from pathlib import Path

from scripts.game_data.animation_config_binary import ANIMATION_CONFIG_FIELDS
from scripts.webui.data_inspector.contract import source_descriptor


def require_complete(decoded,size):
    fields=decoded.get('fields')
    if(decoded.get('schemaStatus')!='named_exact'or decoded.get('wholeSchemaExact')is not True
        or decoded.get('physicalEOF')is not True or decoded.get('serializedMemberCount')!=15
        or decoded.get('bytesConsumed')!=size or decoded.get('opaqueRanges')or decoded.get('unreadFields')
        or not isinstance(fields,list)or any(not isinstance(r,dict)or not isinstance(r.get('value'),dict)for r in fields)
        or[(r.get('memberIndex'),r.get('fieldName'))for r in fields]!=list(enumerate(ANIMATION_CONFIG_FIELDS))):
        raise ValueError('AnimationConfig publication requires all fifteen named fields and physical EOF')
    return{r['fieldName']:r['value']for r in fields}


def _count(value):
    if value.get('isNull')is True:return 0
    return value['count']


def _collection(value,name,items,*,signed):
    if not isinstance(value,dict)or type(value.get('isNull'))is not bool or not isinstance(value.get(items),list):
        raise ValueError('AnimationConfig complete collection shape: '+name)
    count=value.get('count')
    if value['isNull']:
        if count!=(-1 if signed else None)or value[items]:raise ValueError('AnimationConfig null collection: '+name)
    elif type(count)is not int or not 0<=count<=4096 or len(value[items])!=count:
        raise ValueError('AnimationConfig complete collection count: '+name)


def record(path:Path,export_root:Path,*,decode):
    relative=path.relative_to(export_root).as_posix()
    base=dict(id=relative,title=path.stem,source=source_descriptor(path,export_root=export_root,media_type='application/octet-stream'))
    try:
        raw=path.read_bytes();decoded=decode(raw);fields=require_complete(decoded,len(raw))
        for name in('montages','syncGroupCurves','timeRefCurves'):_collection(fields[name],name,'entries',signed=False)
        for name,items in(('boneWeightMasks','rows'),('npcMontages','rows'),('syncGroupAnimationCurves','entries')):
            _collection(fields[name],name,items,signed=True)
        facts={key:decoded[key]for key in('wholeSchemaExact','physicalEOF','serializedMemberCount','bytesConsumed')}
        for name in('controllerPath','optControllerPath','retargetAnimConfigPath'):
            value=fields[name];bits=bytes.fromhex(value['rawHex'])
            if len(bits)!=8:raise ValueError('AnimationConfig signed path hash width: '+name)
            facts[name]=int.from_bytes(bits,'little',signed=True)
        masks=fields['boneWeightMasks'];facts['boneWeightMaskCount']=_count(masks)
        facts['boneWeightMaskLayerNames']=[r['layerName']for r in masks.get('rows',[])if isinstance(r.get('layerName'),str)]
        for name,key in(('montages','montageCount'),('npcMontages','npcMontageCount'),('syncGroupAnimationCurves','syncGroupAnimationCurveCount'),
            ('syncGroupCurves','syncGroupCurveCount'),('timeRefCurves','timeRefCurveCount')):
            value=fields[name];facts[key]=0 if value.get('isNull')is True else _count(value)
        for name,key in(('montages','montageNames'),('syncGroupCurves','syncGroupCurveNames'),('timeRefCurves','timeRefCurveNames')):
            facts[key]=[r['key']for r in fields[name].get('entries',[])]
        extra=fields['extraData'];child=extra.get('record')or{}
        if type(extra.get('isNull'))is not bool:raise ValueError('AnimationConfig complete ExtraData union required')
        facts['extraDataType']=child.get('typeName')
        facts['extraDataFields']=[r['fieldName']for r in child.get('fields',[])]
        summary=['no extra data'if extra.get('isNull')is True else facts['extraDataType'],
            'montages='+str(facts['montageCount']),
            'curves='+str(facts['syncGroupCurveCount']+facts['timeRefCurveCount']+facts['syncGroupAnimationCurveCount'])]
        return dict(**base,status='named_exact',summary='; '.join(str(s)for s in summary if s is not None),
            tags=['animation','memorypack','named_exact'],facts=facts,payload=decoded,payloadKind='reader')
    except(OSError,ValueError)as error:
        return dict(**base,status='decode_error',summary=str(error)[:1800],diagnostic=str(error)[:1800],
            tags=['animation','memorypack','decode_error'])
