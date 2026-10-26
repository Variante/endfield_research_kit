"""Signed Int32 keys and independent Unity Keyframe28 curve values.

Entries preserve their source order and raw keys. Normal insertion is a native
condition; this syntax projection does not reconstruct Dictionary equality,
duplicate-key behavior, final mutable contents or runtime animation.
"""
import struct
from scripts.game_data.memorypack import animation_int_curve_dictionary_sources as source
from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability as curve_capability,read_curve


def need(check,condition):
    if not condition:raise ValueError('animationIntCurveDictionaryCodec.'+check)


def require_capability(cap):
    need('exact-owned-Dictionary',isinstance(cap,dict) and cap.get('typeName')==source.TYPE
        and(cap.get('keyType'),cap.get('valueType'))==('int',source.VALUE)
        and all(type(cap.get(k))is int and cap[k]==v for k,v in
            (('headerBytes',4),('nullCount',-1),('nodeLimit',16384),('managedKeyBytes',4),('keyWireBytes',4),
             ('managedValueBytes',8),('insertBehaviorByte',2)))
        and all(type(cap.get(k))is int and cap[k]>0 for k in ('packableReaderMethodDefinition','packableReaderTargetRva',
            'dictionaryCallbackMethodDefinition','dictionaryCallbackTargetRva','keyCallbackMethodDefinition','keyCallbackTargetRva',
            'valueCallbackMethodDefinition','valueCallbackTargetRva')))
    need('finite-counted-reference-grammar',type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=4096
        and cap.get('countRange')==[-1,cap['countLimit']] and all(type(n)is int for n in cap['countRange'])
        and cap.get('valueWireBytes')is None and all(cap.get(k)is True for k in ('nullable','positiveCountsAdmitted',
            'wholeGrammarAdmitted','actualReadPackableAdmitted','initiallyNullOutputRequired','callbackSelectionConditional',
            'normalInsertionRequired','orderedEntriesPreserved','duplicateKeysPreserved'))
        and all(cap.get(k)is False for k in ('actualRuntimeSelectionObserved','finalMutableDictionaryReconstructed',
            'parentFieldAdmitted','wholeOwnerAdmitted')) and type(cap.get('closedPointerEquivalenceProved'))is bool
        and isinstance(cap.get('conditions'),list) and len(cap['conditions'])==3 and all(isinstance(s,str)and s for s in cap['conditions']))
    need('separate-complete-UnityCurve-child',cap.get('valueCapability')=='skill-animation-curve')
    curve_capability(cap.get('valueCapabilityShape',{}))
    return cap


def read(reader,*,budget=None):
    cap=require_capability(reader.operation.child(source.CAPABILITY))
    need('same-complete-UnityCurve-capability',reader.operation.child(cap['valueCapability'])==cap['valueCapabilityShape'])
    if budget is None:budget=dict(remaining=cap['nodeLimit'])
    need('literal-shared-node-budget',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 0<=budget['remaining']<=cap['nodeLimit'])
    start=reader.pos;need('complete-four-byte-count',start+4<=reader.limit)
    count=struct.unpack_from('<i',reader.data,start)[0]
    need('count-domain-before-consumption',-1<=count<=cap['countLimit'])
    required=1+max(count,0);need('node-budget-before-consumption',required<=budget['remaining']);budget['remaining']-=required
    reader.take(4,source.CAPABILITY+'.count');entries=[]
    for index in range(max(0,count)):
        at=reader.pos;raw=reader.take(4,source.CAPABILITY+'.key');key=struct.unpack('<i',raw)[0];value_start=reader.pos
        read_curve(reader,capability=cap['valueCapability'])
        entries.append(dict(index=index,start=at,end=reader.pos,key=key,keyRawHex=raw.hex(),valueStart=value_start,value=reader.records[-1]))
    result=dict(kind=source.CAPABILITY,typeName=source.TYPE,start=start,end=reader.pos,count=count,isNull=count==-1,
        entries=entries,serializedOrderPreserved=True,duplicateKeysPreserved=True,
        finalMutableDictionaryReconstructed=False,normalNativeInsertionIsCondition=True,
        containingOwnerClaimed=False,runtimeAnimationProved=False)
    reader.records.append(result);return result
