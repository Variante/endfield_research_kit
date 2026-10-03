"""Exact typed-parent composition of stored BlackboardString children."""
import hashlib
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_blackboard_double_child_receipt as double

from scripts.game_data.memorypack import buff_blackboard_string_child_receipt as child
def tag_for_role(role):
    return child._contract()['parents'][role]['unionTag']


def supported_tags():
    return frozenset(tag_for_role(role) for role in ('checkSkillId','raiseTrainLevelEvent'))


def _parent_key(tag):
    rows=[role for role in ('checkSkillId','raiseTrainLevelEvent') if tag_for_role(role)==tag]
    if len(rows)!=1:raise ValueError('buffStringActions.native:unsupported-or-ambiguous-parent-tag')
    return rows[0]


def _native(native,tag):
    c=child._contract();parent_key=_parent_key(tag)
    expected=c['parents'][parent_key];parent=native['parents'][parent_key]
    if (native.get('status')!='validated' or native.get('nativeInputs')!=c['nativeInputs']
        or native.get('selectedReadOrder')!=list(child.READ_ORDER)
        or parent.get('status')!='validated' or parent.get('unionTag')!=tag
        or (parent_key=='checkSkillId' and any(parent.get(k)!=expected[k] for k in ('memberNames','readKinds','fieldBinding')))
        or (parent_key=='raiseTrainLevelEvent' and parent.get('fieldBindings')!=expected['fieldBindings'])):
        raise ValueError('buffStringActions.native:typed-parent-or-child-drift')
    return parent


def _value(data,source,digest,start,end,native):
    result=child.decode_blackboard_string_value(data,source=source,logical_sha256=digest,start=start,end=end,native_validation=native)
    if result.get('wholeStoredSpanExact') is not True or [result.get('start'),result.get('end')]!=[start,end]:
        raise ValueError('buffStringActions.child:incomplete-span')
    return result


def decode_list(data,source,digest,start,end,native):
    _native(native,tag_for_role('checkSkillId'))
    if (not source or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError('buffStringActions.list:source-or-range')
    reader=Reader(data,source,end);reader.pos=start;count=reader.count(1,nullable=True);elements=[]
    for _ in range(max(0,count)):
        a=reader.pos;reader.paired_payload();elements.append(_value(data,source,digest,a,reader.pos,native))
    if reader.pos!=end:raise ValueError('buffStringActions.list:end')
    return {'start':start,'end':end,'count':count,'elements':elements,'wholeStoredSpanExact':True}


def decode_action(data,*,source,digest,start,end,tag,native_validation):
    children=native_validation['children'];native=children['blackboardString'];proof=_native(native,tag)
    if hashlib.sha256(data).hexdigest().upper()!=digest.upper() or not 0<=start<end<=len(data):
        raise ValueError('buffStringActions.action:source-or-range')
    if _parent_key(tag)=='checkSkillId':
        reader=Reader(data,source,end);reader.pos=start;reader.nested_union_tag((tag,),'check-skill-id');reader.header(5);fields=[]
        for name,kind in zip(proof['memberNames'],proof['readKinds'],strict=True):
            a=reader.pos
            if kind in ('byte','scalar32'):
                value={'rawHex':reader.take(1 if kind=='byte' else 4,name).hex().upper()}
            elif kind=='list-blackboard-string':
                for _ in range(max(0,reader.count(1,nullable=True))):reader.paired_payload()
                value={'child':decode_list(data,source,digest,a,reader.pos,native)}
            else:raise ValueError('buffStringActions.action:unsupported-read-kind')
            fields.append({'fieldName':name,'kind':kind,'start':a,'end':reader.pos,**value})
        if reader.pos!=end:raise ValueError('buffStringActions.action:end')
        result={'namedFields':fields}
    else:
        parent=double.raise_event.decode_raise_train_level_event_receipt(data,source=source,logical_sha256=digest,
            start=start,end=end,native_validation=children['blackboard']['parentNative'][tag])
        strings={}
        for binding in proof['fieldBindings']:
            field=parent['namedFields'][binding['memberIndex']]
            if field['fieldName']!=binding['fieldName'] or field['kind']!='paired-payload':
                raise ValueError('buffStringActions.action:typed-field-drift')
            strings[binding['fieldName']]=_value(data,source,digest,field['start'],field['end'],native)
        scalar=double.decode_blackboard_double_action_child_receipt(data,source=source,logical_sha256=digest,
            start=start,end=end,tag=tag,native_validation=children['blackboard'])
        if scalar.get('wholeProviderByteSpanExact') is not True:raise ValueError('buffStringActions.action:double-incomplete')
        result={'parent':parent,'strings':strings,'blackboard':scalar}
    return {'schema':'endfield.buff-recursive-action-receipt.v1','tag':tag,'start':start,'end':end,
            'recursiveStoredSchemaExact':True,**result}
