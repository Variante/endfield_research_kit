"""Bounded TickInterval parent and separately gated recursive stored adapter.

The caller supplies the original fresh complete recursive context and the
independent current Tick source/helper composition packet separately. Bounded
field/child receipts do not prove actual native callback cursor equality,
runtime scheduling or any enclosing Timeline/list/root receipt.
"""
from __future__ import annotations
import hashlib
from scripts.game_data.memorypack.buff_actions import Reader,SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack import buff_tick_interval_composition as composition
from scripts.game_data.memorypack import buff_sequence as sequence
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack import buff_tick_interval_union_route as unions

LABEL='buffTickIntervalAction'


def decode_action(data,*,source,digest,start,end,composition_native,recursive_native,depth=0,require_end=True):
    c=composition.sources._contract();pins=c['nativeInputs'];native=composition_native
    if (native.get('status')!='validated' or native.get('scope')!=composition.SCOPE
            or native.get('nativeInputs')!=pins or recursive_native.get('status')!='validated'
            or recursive_native.get('nativeInputs')!=pins
            or not isinstance(data,bytes) or not isinstance(digest,str) or not source
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)
            or type(depth) is not int or not 0<=depth<=SEQUENCE_RECURSION_LIMIT
            or type(require_end) is not bool):
        raise ValueError(f'{LABEL}.decode:native-source-span-or-depth')
    summary=native.get('summary',{});parent=summary.get('parentSource',{})
    wire=summary.get('primitiveWireProfile',{});join=summary.get('parentSequenceJoin',{})
    if (parent.get('completeConditionalSourceOutputFlowsProved') is not True
            or parent.get('currentConcreteMetadataSlotFiveJoined') is not True
            or parent.get('caller',{}).get('conditionalFFClearsFullWrapperOutputAndReturns') is not True
            or join.get('completeConditionalSequenceResultToOwnedParentFieldProved') is not True
            or join.get('fieldName')!='actionOnTick'
            or wire.get('samePhysicalPrimitiveHelpersAsOriginalParentProved') is not True
            or wire.get('selectedBufferedPrimitiveWireRepresentationsProved') is not True
            or wire.get('singleLow32BitSourceAndSetterTransferProved') is not True):
        raise ValueError(f'{LABEL}.decode:incomplete-current-source-composition')
    if data[start]!=250:raise ValueError(f'{LABEL}.decode:canonical-extended-union-required')
    reader=Reader(data,source,end);reader.pos=start
    tag=reader.nested_union_tag((composition.sources.candidate.TAG,),'tick-interval')
    if tag!=composition.sources.candidate.TAG:raise ValueError(f'{LABEL}.decode:current-union-tag')
    fields=[]
    if reader.peek()==255:
        reader.take(1,'null-tick-wrapper');status='exact-null-wrapper'
    else:
        reader.header(len(c['fields']));status='conditional-named-tick-stored-span'
        for member in c['fields']:
            at=reader.pos;kind=member['readKind'];value={}
            if kind in ('bool-byte','scalar32','float32-bits'):
                value['rawHex']=reader.take(1 if kind=='bool-byte' else 4,member['fieldName']).hex().upper()
            elif kind=='sequence-profile':
                child=sequence.decode_value(data,source,digest,at,end,recursive_native,depth+1,require_end=False)
                if (child.get('recursiveStoredSchemaExact') is not True or child.get('start')!=at
                        or type(child.get('end')) is not int or not at<child['end']<=end):
                    raise ValueError(f'{LABEL}.decode:incomplete-sequence-child')
                reader.pos=child['end'];value['child']=child
            elif kind=='byte-payload':
                reader.byte_payload()
                value['child']=strings.decode_source_string(data,source=source,digest=digest,start=at,end=reader.pos,
                    source_helper_rva=member['readerEntryRva'],native_validation=wire.get('stringSource',{}))
            else:raise ValueError(f'{LABEL}.decode:unsupported-proved-field-kind={kind}')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],
                'kind':kind,'start':at,'end':reader.pos,**value})
    if require_end and reader.pos!=end:raise ValueError(f'{LABEL}.decode:parent-end={reader.pos}; expected={end}')
    return {'schema':'endfield.buff-tick-interval-stored-parent-receipt.v1','source':source,
        'logicalSha256':digest.upper(),'tag':tag,'typeName':c['wrapper']['wrappedType'],
        'start':start,'end':reader.pos,'status':status,'namedFields':fields,
        'recursiveStoredSchemaExact':True,'nativeSourceSelectionConditional':True,
        'nativeActionCallbackCursorEqualityProved':False,'runtimeSchedulingOrEffectsObserved':False,
        'wholeActionAdmitted':False,'positiveListAdmitted':False,'wholeRootAdmitted':False,
        'evidenceBoundary':'Exact bounded stored fields and independently receipted recursive children under the current conditional source/helper joins. This receipt supplies an isolated parent span; recursive composition additionally requires the independent complete union route and fresh complete recursive native context. No enclosing element/list/root or actual execution is admitted.'}


def supported_tags():
    return frozenset((composition.sources.candidate._contract()['dispatcher']['unionTag'],))


def decode_recursive_action(data, *, source, digest, start, end, tag, native_validation, depth=0):
    """Use only separately owned Tick proofs from a current full native return."""
    c=composition.sources._contract();pins=c['nativeInputs'];wrapper=c['wrapper']
    children=native_validation.get('children',{});proof=children.get('tickInterval',{})
    route=children.get('tickIntervalUnionRoute',{});summary=route.get('summary',{})
    if (native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=pins
            or type(tag) is not int or tag not in supported_tags()
            or proof.get('status')!='validated' or proof.get('scope')!=composition.SCOPE or proof.get('nativeInputs')!=pins
            or route.get('status')!='validated' or route.get('scope')!=unions.SCOPE or route.get('nativeInputs')!=pins
            or summary.get('completeConditionalTickUnionOutputReturnProved') is not True
            or summary.get('sameConcreteWrapperDefinition')!=wrapper['typeDefinition']
            or summary.get('sameConcreteWrapperName')!=wrapper['wrapperName']
            or summary.get('sameConcreteOriginalType')!=wrapper['wrappedType']
            or summary.get('selectedIndexedUnionPrefix',{}).get('selectedTag')!=tag
            or summary.get('completeNewChildRoute',{}).get('completeNewChildRouteReturn') is not True
            or summary.get('completeNewChildRoute',{}).get('sameChildReturnStoredAndBarrierValue') is not True
            or summary.get('completeNewChildRoute',{}).get('wrapperOutputReferenceBits')!=64
            or summary.get('completeNewChildRoute',{}).get('directReaderCursorWrites')!=0
            or proof.get('summary',{}).get('parentSource',{}).get('fieldsForwardedToOwnedData')!=len(c['fields'])):
        raise ValueError(f'{LABEL}.recursive:incomplete-current-native-route-or-source-binding')
    result=decode_action(data,source=source,digest=digest,start=start,end=end,
        composition_native=proof,recursive_native=native_validation,depth=depth)
    return {**result,'globalRecursiveStoredSchemaAdmitted':True,'wholeActionByteSpanExact':True,
        'evidenceBoundary':'Exact complete stored Tick parent and recursively certified original children, using separately owned helper/source and complete current union output/return proofs from a fresh full recursive context. Native joins retain their stated context/provider/cache/normal-call/disabled-barrier/buffer/alias conditions. Actual callback cursor equality, execution and enclosing element/list/root admission remain independent.'}
