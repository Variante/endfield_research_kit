"""Whole fallback-set MC2 caller with its independent static dictionary."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(key,condition):
    if not condition:raise ValueError('animationFallbackSetProgram.'+key)


def program(regions,entry,s,*,new=False,null=False):
    need('literal-path-selection',type(new)is bool and type(null)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2410','4889742418','57','4883ec20');flag=g.relative('803d');g.take('00','488bda','488bf1');g.branch('75',True,1)
    g.take('488d542430','c644243000','488bce','48c744244800000000');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
    allocation=None;class_load=None;dictionary_context=None;tag_context=None;dictionary_call=None;tag_call=None;field_calls=[]
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier'])
    else:
        g.take('48833b00');g.branch('75',not new,1)
        if new:
            allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bcb','48893b');g.call(s['barrier'])
        g.take('807c243002');g.branch('75',False,1)
        class_load=g.at;g.relative('488b0d');zero=g.at;g.take('48c744244800000000');g.call(s['classReady'])
        dictionary_context=g.at;g.relative('4c8b05');g.take('488d542448','488bce');dictionary_call=g.at;g.call(s['dictionary'])
        g.take('488b0b','4885c9');g.branch('74',False,1)
        g.take('488b542448','4533c0');field_calls.append(g.at);g.call(s['dictionarySetter'])
        tag_context=g.at;g.relative('488b15');g.take('488bce','488b1b');tag_call=g.at;g.call(s['tags'])
        g.take('4885db');g.branch('74',False,1)
        g.take('4533c0','488bd0','488bcb');field_calls.append(g.at);g.call(s['tagSetter']);g.jump('eb',1)
    g.take('488b5c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,new=new,null=null,metadataReadyFlagVa=flag,
        allocationClassInstructionVa=allocation,dictionaryClassInstructionVa=class_load,
        dictionaryContextInstructionVa=dictionary_context,tagContextInstructionVa=tag_context,
        dictionaryCallInstructionVa=dictionary_call,tagCallInstructionVa=tag_call,fieldSetterCallSites=field_calls,
        dictionaryOutputZeroInstructionVa=None if null else zero,dictionaryOutputRspOffset=72,
        dictionaryOutputEntryRspOffset=32,initiallyNullDictionaryOutputProved=not null,
        sameDictionaryOutLocalTransferredToNamedSetter=not null,sameTagListRaxTransferredToNamedSetter=not null,
        serializedMemberCount=2,normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
        frame=dict(entryRspDelta=-40,callShadowRsp=[0,32],headerEntryHome=[8,9],dictionaryOutEntryHome=[32,40],
            originalRbxEntryHome=[16,24],originalRsiEntryHome=[24,32],pushedNonvolatiles=['rdi']),
        childGrammarAdmitted=False)


def class_ready_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28','83b9e000000000');g.branch('74',False,1)
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,sameClassPassedInRcx=True,initializedClassRequired=True,entryRspRestored=True,normalReturn=True)


def setter_program(regions,entry,*,field,barrier):
    need('own-two-reference-fields',field in(24,32))
    g=BytesPath(regions,entry)
    g.take('4883ec28','488b4910','4885c9');g.branch('75',True,1)
    g.take('488951'+bytes((field,)).hex(),'4883c1'+bytes((field,)).hex(),'4883c428')
    need('same-selected-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,holderOffset=16,fieldOffset=field,storedBytes=8,
        incomingValueStoredUnchanged=True,entryRspRestored=True,normalTailBarrier=True)


def initialized_indexer_program(regions,entry):
    """Exact sparse initialized path; the cold target is deliberately unowned."""
    g=BytesPath(regions,entry);g.take('488bc1','4863ca','488b0cc8');g.jump('e9')
    g.take('f6813801000001')
    # Read the exact untaken JE without attributing its cold destination bytes.
    g.take('74','05','488bc1');g.jump('eb',1);g.take('c3')
    return dict(selectedBytes=g.seen,normalReturn=True,result='incoming RCX context[incoming EDX]',
        condition='Incoming index nonnegative/in-range and selected class initialized flag bit one set; readable stable context/class storage.')
