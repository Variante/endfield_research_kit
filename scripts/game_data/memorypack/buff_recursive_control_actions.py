"""Recursive control actions composed through independently proved typed children."""
import hashlib
from scripts.game_data.memorypack.buff_actions import Reader,SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack import buff_if_else_action_receipt as conditional
from scripts.game_data.memorypack import buff_compare_float_blackboard_children as compare
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as modify
from scripts.game_data.memorypack import buff_blackboard_double_child_receipt as double
from scripts.game_data.memorypack import buff_damage_check_buff_stack_condition_receipt as stack
from scripts.game_data.memorypack import buff_id_actions as ids
from scripts.game_data.memorypack import buff_string_actions as strings
from scripts.game_data.memorypack import buff_damage_check_decorate_mask_condition_receipt as decorate
from scripts.game_data.memorypack import buff_check_buff_id_context_advanced as advanced_ids

SUPPORTED_TAGS={conditional.TAG,compare.parent.TAG,modify.TAG,stack._contract()["unionTag"],decorate._contract()['unionTag'],advanced_ids.supported_tag()}|ids.supported_tags()|strings.supported_tags()


def decode_decorate_mask(data,source,digest,start,end,native):
    contract=decorate._contract();proof=native['children']['decorateMask']
    if (proof.get('status')!='validated' or proof.get('nativeInputs')!=contract['nativeInputs']
        or proof.get('unionTag')!=contract['unionTag'] or proof.get('actionMemberPlan')!=contract['actionMemberPlan']
        or not source or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
        or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError('buffRecursiveControlActions.decorateMask:native-or-source')
    reader=Reader(data,source,end);reader.pos=start
    reader.nested_union_tag((contract['unionTag'],),'decorate-mask-action')
    reader.header(len(contract['actionMemberPlan']));fields=[]
    for member in contract['actionMemberPlan']:
        a=reader.pos;raw=reader.take(member['width'],member['name'])
        fields.append({'name':member['name'],'declaredType':member['declaredType'],'kind':member['kind'],
                       'start':a,'end':reader.pos,'rawHex':raw.hex().upper()})
    if reader.pos!=end:raise ValueError('buffRecursiveControlActions.decorateMask:action-end')
    return {'namedFields':fields,'recursiveStoredSchemaExact':True}


def read_sequence(data,source,digest,start,end,native,depth):
    from scripts.game_data.memorypack import buff_sequence
    return buff_sequence.decode_value(data,source,digest,start,end,native,depth)


def decode_ifelse(data,source,digest,start,end,native,depth):
    # Parent certification requires actual cursor-closed nested records, never
    # caller-invented ranges or an arbitrary leap to the known parent endpoint.
    reader=Reader(data,source,end);reader.pos=start;reader.action(depth)
    if reader.pos!=end:raise ValueError('buffRecursiveControlActions.ifElse:framed-action-end')
    spans=[{k:r[k] for k in ('start','end','tag')} for r in reader.records if r['kind']=='union']
    parent=conditional.decode_if_else_action_receipt(data,source=source,logical_sha256=digest,start=start,end=end,
        native_validation=native['children']['ifElse'],certified_action_spans=spans)
    sequences={}
    for field in parent['namedFields']:
        if field['kind']=='SequenceActionData':
            sequences[field['fieldName']]=read_sequence(data,source,digest,field['start'],field['end'],native,depth+1)
    if len(sequences)!=3:raise ValueError('buffRecursiveControlActions.ifElse:three-typed-sequences')
    return {'parent':parent,'sequences':sequences,'recursiveStoredSchemaExact':True}


def decode_modify(data,source,digest,start,end,native):
    from scripts.game_data.memorypack import buff_recursive_actions as base
    children=native['children'];proof=children['modify']
    parent=modify.decode_modify_dynamic_blackboard_action_receipt(data,source=source,logical_sha256=digest,
        start=start,end=end,native_validation=proof)
    targets=[r for r in proof['directTypedChildren'] if r['typeName']=='Beyond.Gameplay.Core.TargetSettings']
    if len(targets)!=1:raise ValueError('buffRecursiveControlActions.modify:typed-target-cardinality')
    fields={r['fieldName']:r for r in parent['namedFields']};field=fields[targets[0]['fieldName']]
    if field['kind']!='member13':raise ValueError('buffRecursiveControlActions.modify:typed-target-kind')
    target=base.recursive_target(data,source,digest,field,children)
    scalar=double.decode_blackboard_double_action_child_receipt(data,source=source,logical_sha256=digest,
        start=start,end=end,tag=modify.TAG,native_validation=children['blackboard'])
    if scalar['wholeProviderByteSpanExact'] is not True:raise ValueError('buffRecursiveControlActions.modify:scalar')
    return {'parent':parent,'target':target,'blackboard':scalar,'recursiveStoredSchemaExact':True}


def decode_stack(data,source,digest,start,end,native):
    from scripts.game_data.memorypack import buff_recursive_actions as base
    children=native['children'];proof=children['checkStack'];contract=stack._contract()
    if (proof.get('status')!='validated' or proof.get('nativeInputs')!=contract['nativeInputs']
        or proof.get('unionTag')!=contract['unionTag'] or proof.get('actionMemberPlan')!=contract['actionMemberPlan']
        or any(children[name].get('status')!='validated' or children[name].get('nativeInputs')!=proof['nativeInputs']
               for name in ('findSettings','target'))
        or hashlib.sha256(data).hexdigest().upper()!=digest.upper()):
        raise ValueError('buffRecursiveControlActions.stack:current-native-child-join-or-source')
    reader=Reader(data,source,end);reader.pos=start
    reader.nested_union_tag((contract['unionTag'],),'condition-action');reader.header(len(contract['actionMemberPlan']))
    fields=[]
    for member in contract['actionMemberPlan']:
        a=reader.pos;kind=member['kind'];value={}
        if kind in ('bool-byte','enum32','int32'):value['rawHex']=reader.take(member['width'],member['name']).hex().upper()
        elif kind=='buff-find-settings':
            reader.finder_profile()
            value['child']=base.find.decode_find_settings_child_receipt(data,source=source,logical_sha256=digest,
                    start=a,end=reader.pos,native_validation=children['findSettings'])
        elif kind=='target-settings':
            reader.target_profile()
            value['child']=base.recursive_target(data,source,digest,{'start':a,'end':reader.pos},children)
        elif kind=='blackboard-double':
            reader.scalar_payload()
            value['child']=stack.blackboard.decode_adding_cooldown(data,a,reader.pos,native_validation=proof['blackboardNative'])
            if value['child'].get('wholeValueExact') is not True:raise ValueError('buffRecursiveControlActions.stack:blackboard-child')
        else:raise ValueError('buffRecursiveControlActions.stack:unsupported-member')
        fields.append({'name':member['name'],'declaredType':member['declaredType'],'kind':kind,'start':a,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError('buffRecursiveControlActions.stack:action-end')
    return {'namedFields':fields,'recursiveStoredSchemaExact':True}


def decode_action(data,*,source,digest,start,end,tag,native_validation,depth=0):
    if depth>SEQUENCE_RECURSION_LIMIT:raise ValueError('buffRecursiveControlActions.action:depth-limit')
    if tag==conditional.TAG:result=decode_ifelse(data,source,digest,start,end,native_validation,depth)
    elif tag==compare.parent.TAG:
        result={'operands':compare.decode_compare_float_blackboard_children(data,source=source,logical_sha256=digest,
                    start=start,end=end,native_validation=native_validation['children']['compare']), 'recursiveStoredSchemaExact':True}
    elif tag==modify.TAG:result=decode_modify(data,source,digest,start,end,native_validation)
    elif tag==stack._contract()['unionTag']:result=decode_stack(data,source,digest,start,end,native_validation)
    elif tag in ids.supported_tags():result=ids.decode_action(data,source=source,digest=digest,start=start,end=end,tag=tag,native_validation=native_validation)
    elif tag in strings.supported_tags():result=strings.decode_action(data,source=source,digest=digest,start=start,end=end,tag=tag,native_validation=native_validation)
    elif tag==decorate._contract()['unionTag']:result=decode_decorate_mask(data,source,digest,start,end,native_validation)
    elif tag==advanced_ids.supported_tag():result=advanced_ids.decode_action(data,source=source,digest=digest,start=start,end=end,native_validation=native_validation)
    else:raise ValueError(f'buffRecursiveControlActions:unsupported-action={tag}')
    return {'schema':'endfield.buff-recursive-action-receipt.v1','tag':tag,'start':start,'end':end,**result}
