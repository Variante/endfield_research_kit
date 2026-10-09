"""Shared bounded SelectorValidator lists and GameplayTagQuery values.

Each value requires independently authenticated same-build parent and child
owners. Names describe stored members; runtime predicate evaluation stays open.
"""
import hashlib
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_find_settings_child_receipt as query_owner
from scripts.game_data.memorypack import buff_selector_validator_tag_query as tag_owner
from scripts.game_data.memorypack import buff_selector_validator_zero as zero_owner
from scripts.game_data.memorypack import buff_selector_distance_validator as distance_owner


def query_parent_binding(parent_native, child_native):
    parent=tag_owner._contract(); child=query_owner._contract()['children'][1]
    context=parent['readOrder']['queryContext']
    expected_inputs=parent['nativeInputs']
    if (parent_native.get('status')!='validated' or child_native.get('status')!='validated'
        or parent_native.get('nativeInputs')!=expected_inputs or child_native.get('nativeInputs')!=expected_inputs
        or parent_native.get('directMemberName')!='query'
        or parent_native.get('directMemberType')!=child['runtimeTypeName']
        or context['typeDefinition']!=child['runtimeTypeDefinition']
        or context['typeName']!=child['runtimeTypeName']
        or child_native.get('readOrders',{}).get('query-profile')!=[f['name'] for f in child['fields']]):
        raise ValueError('buffSelectorSharedChildren.query:typed-parent-child-join')
    return child


def decode_query_value(data, *, source, digest, start, end, native):
    contract=query_owner._contract(); child=contract['children'][1]
    fields=child['fields']
    if (native.get('status')!='validated' or native.get('nativeInputs')!=contract['nativeInputs']
        or native.get('readOrders',{}).get('query-profile')!=[f['name'] for f in fields]
        or [f['kind'] for f in fields]!=['scalar32','counted-scalar32']):
        raise ValueError('buffSelectorSharedChildren.query:native-not-validated')
    if (not source or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
        or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError('buffSelectorSharedChildren.query:source-range-or-hash')
    reader=Reader(data,source,end);reader.pos=start;members=[]
    if reader.peek()==255:
        reader.take(1,'null-query');status='exact-null'
    else:
        reader.header(2);begin=reader.pos;reader.take(4,fields[0]['name'])
        members.append({'fieldName':fields[0]['name'],'declaredType':fields[0]['declaredType'],
                        'start':begin,'end':reader.pos,'kind':'scalar32'})
        begin=reader.pos;count=reader.count(4,nullable=True);reader.take(max(0,count)*4,'tags')
        members.append({'fieldName':fields[1]['name'],'declaredType':fields[1]['declaredType'],
                        'start':begin,'end':reader.pos,'kind':'counted-scalar32','count':count})
        status='named-direct-members-exact-span'
    if reader.pos!=end:raise ValueError('buffSelectorSharedChildren.query:field-end')
    return {'source':source,'logicalSha256':digest.upper(),'start':start,'end':end,'status':status,
            'namedFields':members,'wholeStoredSpanExact':True,'recursiveNamedSchemaExact':True,
            'runtimePredicateKnown':False}


def decode_validator_list(data, *, source, digest, start, end, children):
    query_parent_binding(children['tagQueryValidator'],children['findSettings'])
    zero=children['zeroValidators'];selector=children['selector']
    if (zero.get('status')!='validated' or selector.get('status')!='validated'
        or zero.get('nativeInputs')!=selector.get('nativeInputs')
        or children['tagQueryValidator']['nativeInputs']!=selector['nativeInputs']):
        raise ValueError('buffSelectorSharedChildren.validators:native-join')
    if (hashlib.sha256(data).hexdigest().upper()!=digest.upper()
        or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError('buffSelectorSharedChildren.validators:source-range-or-hash')
    selected={int(k):v for k,v in zero['selectedTags'].items()}
    if set(selected)!=set(zero_owner.TYPE_NAMES) or any(row.get('serializedMemberCount')!=0 for row in selected.values()):
        raise ValueError('buffSelectorSharedChildren.validators:zero-route-set-or-shape')
    reader=Reader(data,source,end);reader.pos=start;count=reader.count(1,nullable=True);values=[]
    for _ in range(max(0,count)):
        begin=reader.pos;tag=reader.nested_union_tag(tuple(selected)+(tag_owner.TAG,distance_owner.TAG),'validator')
        if tag is None:
            values.append({'start':begin,'end':reader.pos,'status':'exact-null'});continue
        if reader.peek()==255:
            reader.take(1,'null-validator-wrapper');status='exact-null-wrapper';query=None
        elif tag in selected:
            if selected[tag]['serializedMemberCount']!=0:raise ValueError('buffSelectorSharedChildren.validators:zero-plan-drift')
            reader.header(0);status='named-zero-member-validator-exact-span';query=None
        elif tag == distance_owner.TAG:
            reader.header(3);reader.take(1,'clampToXZ');reader.take(4,'compareType');reader.scalar_payload()
            status='named-distance-validator-exact-span';query=None
        else:
            reader.header(1);a=reader.pos;reader.query_profile()
            query=decode_query_value(data,source=source,digest=digest,start=a,end=reader.pos,native=children['findSettings'])
            status='named-query-member-exact-span'
        row={'start':begin,'end':reader.pos,'tag':tag,'status':status,'query':query}
        if tag == distance_owner.TAG:
            row['child']=distance_owner.decode_value(data,source=source,digest=digest,
                start=begin,end=reader.pos,children=children)
        values.append(row)
    if reader.pos!=end:raise ValueError('buffSelectorSharedChildren.validators:list-end')
    return {'start':start,'end':end,'count':count,'elements':values,'wholeStoredSchemaExact':True,
            'evidenceBoundary':'Named stored selected validator children; no runtime predicate evaluation.'}
