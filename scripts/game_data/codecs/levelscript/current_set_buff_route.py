"""Pure exact nested SetBuff cursor; native authority lives in its gateway."""
from scripts.game_data.memorypack.levelscript_set_buff_route_sources import CAP_SCHEMA,WRAPPER,TYPE,CHILD


def validate(cap):
    from scripts.game_data.codecs.levelscript.current_generated_action_route import validate as ordinary,SCHEMA
    if not isinstance(cap,dict)or cap.get('schema')!=CAP_SCHEMA:
        raise ValueError('currentSetBuff.owned-capability')
    nested=cap.get('nestedUnion');expected=dict(tag=0,wrapperName=CHILD,typeName='Beyond.Gameplay.Actions.SetBuff',
        canonicalFFAdmitted=True,shortAndExtendedTagsAdmitted=True,initiallyNullOutputRequired=True)
    if not(isinstance(nested,dict)and set(nested)==set(expected)
        and all(type(nested[k])is type(v)and nested[k]==v for k,v in expected.items())
        and cap.get('family')=='ActionBase'and cap.get('wrapperName')==WRAPPER and cap.get('typeName')==TYPE
        and cap.get('memberCount')==10):raise ValueError('currentSetBuff.exact-nominal-nested-branch')
    plain={k:v for k,v in cap.items()if k!='nestedUnion'};plain['schema']=SCHEMA;ordinary(plain)
    return cap


def _tag(reader,field):
    tag=reader.number('<B',field)
    if tag==250:return reader.number('<H',field+'.wide'),False
    if tag>=250 and tag!=255:raise ValueError(field+':reserved-union-marker')
    return tag,tag==255


def decode(data,offset,*,field,capability,strings):
    from scripts.game_data.codecs.levelscript.param_graph import Reader
    from scripts.game_data.codecs.levelscript.current_generated_action_route import read_record,project_record,SCHEMA
    cap=validate(capability);reader=Reader(data,offset,strings,field);start=offset
    if _tag(reader,field+'.tag')!=(cap['tag'],False):raise ValueError(field+':outer-union-tag')
    nested_at=reader.offset;tag,ff=_tag(reader,field+'.SetBuff.tag')
    if ff:raw=None
    elif tag==0:
        plain={k:v for k,v in cap.items()if k!='nestedUnion'};plain['schema']=SCHEMA
        raw=read_record(reader,field+'.SetBuff.record',plain)
    else:raise ValueError(field+':SetBuff-tag-zero-required')
    result,end=project_record(raw,cap,start,reader.offset)
    result['nestedUnion']=dict(sourceOffset=nested_at,unionTag=tag,wrapperName=CHILD)
    return result,end
