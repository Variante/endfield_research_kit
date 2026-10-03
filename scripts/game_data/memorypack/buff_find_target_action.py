"""FindTarget source fields composed through exact DirectionSettings and SelectorData children."""
import hashlib
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_direction_settings_child_receipt as direction
from scripts.game_data.memorypack import buff_selector_data_child_receipt as selector
from scripts.game_data.memorypack import buff_selector_finder_character_team as team
from scripts.game_data.memorypack import buff_selector_finder_owner_spawned as owner
from scripts.game_data.memorypack import buff_selector_geometry as geometry


def decode_selector(data,source,digest,start,end,children):
    from scripts.game_data.memorypack import buff_selector_shared_children as shared
    receipt=selector.decode_selector_data_value(data,source=source,logical_sha256=digest,start=start,end=end,native_validation=children['selector'])
    if receipt['status']!='named-direct-members-exact-span':raise ValueError('buffFindTargetAction:null-selector')
    f,post,validators=receipt['namedMembers']
    if [x['fieldName'] for x in receipt['namedMembers']]!=['finderData','postProcessorData','validatorData'] or post.get('count')!=0:
        raise ValueError('buffFindTargetAction:unsupported-selector-members')
    kw={'source':source,'logical_sha256':digest,'start':f['start'],'end':f['end']}
    if f['unionTag'] is None:
        if data[f['start']:f['end']]!=b'\xff':raise ValueError('buffFindTargetAction:null-finder')
        finder=None
    elif f['unionTag']==team.TAG:finder=team.decode_character_team_finder_span(data,**kw,native_validation=children['characterTeamFinder'])
    elif f['unionTag']==owner.TAG:finder=owner.decode_owner_spawned_finder_span(data,**kw,native_validation=children['ownerSpawnedFinder'])
    else:finder=geometry.decode_finder(data,source=source,digest=digest,start=f['start'],end=f['end'],context=children)
    validation=None
    if validators.get('count')!=0:
        validation=shared.decode_validator_list(data,source=source,digest=digest,start=validators['start'],end=validators['end'],children=children)
    return {'selector':receipt,'finder':finder,'validators':validation,'recursiveStoredSchemaExact':True}


def decode_action(data,*,source,digest,start,end,tag,native_validation):
    children=native_validation['children'];proof=children['selectorGeometry']
    spec=geometry.checked_layout(proof,'findTargetAction')
    if (tag!=spec['unionTag'] or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
        or not 0<=start<end<=len(data)
        or proof['nativeInputs']!=children['selector']['nativeInputs']):
        raise ValueError('buffFindTargetAction:native-or-source')
    reader=Reader(data,source,end);reader.pos=start;reader.nested_union_tag((tag,),'find-target');reader.header(len(spec['fields']))
    fields=[];joins={x['memberIndex']:x for x in spec['typedChildren']}
    for i,field in enumerate(spec['fields']):
        a=reader.pos;kind=field['readKind'];value={}
        if kind in ('byte','scalar32'):value['rawHex']=reader.take(1 if kind=='byte' else 4,field['name']).hex().upper()
        elif kind=='byte-payload':reader.byte_payload();value['rawHex']=data[a:reader.pos].hex().upper()
        elif kind=='direction-profile':
            if joins[i]['typeName']!=direction.DIRECTION_TYPE:raise ValueError('buffFindTargetAction:typed-direction')
            reader.direction_profile();child=direction.decode_direction_settings_value(data,source=source,logical_sha256=digest,start=a,end=reader.pos,native_validation=children['direction'])
            if child['status']!='named-direct-members-exact-span' or any(m.get('nestedTargetStatus')!='exact-null' for m in child['namedMembers'] if m['kind']=='object'):
                raise ValueError('buffFindTargetAction:positive-direction-target')
            value['child']=child
        elif kind=='selector-profile':
            if joins[i]['typeName']!=selector.SELECTOR_TYPE:raise ValueError('buffFindTargetAction:typed-selector')
            reader.selector_profile();value['child']=decode_selector(data,source,digest,a,reader.pos,children)
        else:raise ValueError('buffFindTargetAction:unsupported-kind')
        fields.append({'fieldName':field['name'],'declaredType':field['declaredType'],'kind':kind,'start':a,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError('buffFindTargetAction:action-end')
    return {'schema':'endfield.buff-recursive-action-receipt.v1','tag':tag,'start':start,'end':end,'namedFields':fields,'recursiveStoredSchemaExact':True}


def supported_tags():
    return frozenset((geometry.action_tag(),))
