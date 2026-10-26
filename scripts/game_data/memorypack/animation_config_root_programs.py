"""Complete selected AnimationConfig MC15 caller and dictionary-local transfers.

This owns caller byte flow only. Exact nominal contexts, child grammars, named
setter bodies, allocation effects and public selection are independent joins.
The selected ready path resets each custom dictionary output before its call;
it never assumes that a reused dictionary implements Clear.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.animation_mask_sources import root_prefix

FIELDS=('_fallbackMontages','avatarBlendProfilePath','bakedBindingPath','boneWeightMasks','controllerPath',
    'extraData','montages','npcMontages','optControllerPath','retargetAnimConfigPath',
    'syncGroupAnimationCurves','syncGroupCurves','timeRefCurves','useRotateDirection','useStateVariables')


def need(check,condition):
    if not condition:raise ValueError('animationConfigRootProgram.'+check)


def program(regions,entry,symbols,reads,setters,*,new=False):
    need('exact-fifteen-owned-calls',isinstance(reads,list)and isinstance(setters,list)
        and len(reads)==len(setters)==15 and all(type(n)is int and n>0 for n in reads[:5]+setters)
        and all(n is None or type(n)is int and n>0 for n in reads[5:]))
    actual_reads=list(reads)
    prefix=root_prefix(regions,entry,symbols,reads[:5],setters[:5],new=new)
    g=BytesPath(regions,prefix['afterPrefix']);events=[]
    def source_call(index):
        at=g.at;target=g.relative('e8')
        need('same-owned-child-call',actual_reads[index]is None or target==actual_reads[index])
        actual_reads[index]=target;return at
    for i,at in enumerate(prefix['readUsageSites']):
        events.append(dict(memberIndex=i,fieldName=FIELDS[i],contextRegister='rdx',contextInstructionVa=at,
            sourceCallInstructionVa=at+13,sourceTargetVa=reads[i],setterTargetVa=setters[i],resultAbi='reference-or-register8'))
    def regular(index):
        context=g.at;g.relative('488b15');g.take('488bcf','488b33');call=source_call(index)
        g.take('4885f6');g.branch('0f84',False);g.take('4533c0','488bd0','488bce');setter=g.at;g.call(setters[index])
        events.append(dict(memberIndex=index,fieldName=FIELDS[index],contextRegister='rdx',contextInstructionVa=context,
            sourceCallInstructionVa=call,sourceTargetVa=actual_reads[index],setterCallInstructionVa=setter,
            setterTargetVa=setters[index],sameWholeRaxToRdx=True,resultAbi='reference-or-register8'))
    def dictionary(index,local,*,short_null=False):
        class_at=g.at;class_cell=g.relative('488b0d');zero=g.at
        slot=bytes((local,)).hex();g.take('48896c24'+slot,'39a9e0000000');g.branch('0f84',False)
        context=g.at;context_cell=g.relative('4c8b05');g.take('488d5424'+slot,'488bcf')
        call=source_call(index);g.take('488b0b','4885c9')
        g.branch('74'if short_null else'0f84',False,1 if short_null else 4)
        load=g.at;g.take('488b5424'+slot,'4533c0');setter=g.at;g.call(setters[index])
        events.append(dict(memberIndex=index,fieldName=FIELDS[index],contextRegister='r8',contextInstructionVa=context,
            contextCellVa=context_cell,sourceCallInstructionVa=call,sourceTargetVa=actual_reads[index],
            classInstructionVa=class_at,classCellVa=class_cell,classStateCheck=dict(register='ebp',knownZero=True,offset=224),
            outLocal=dict(displacement=local,bytes=8,zeroInstructionVa=zero,zeroRegister='rbp',
                zeroOrigin='entry-xor-ebp-ebp',resetImmediatelyBeforeCurrentCall=True),
            resultAbi='static-reader-out-reference8',sourceLocalLoadInstructionVa=load,
            setterCallInstructionVa=setter,setterTargetVa=setters[index],sameWholeLocalToNamedSetter=True,
            initiallyNullOutputProved=True,reusedDictionaryClearAssumed=False))
    regular(5);dictionary(6,104);regular(7);regular(8);regular(9);regular(10)
    dictionary(11,32);dictionary(12,40,short_null=True)
    for index,holder in((13,'rsi'),(14,'rbx')):
        g.take('488b33'if holder=='rsi'else'488b1b','488bcf');call=source_call(index)
        g.take('4885f6'if holder=='rsi'else'4885db');g.branch('74',False,1)
        g.take('4533c0','0fb6d0','488bce'if holder=='rsi'else'488bcb');setter=g.at;g.call(setters[index])
        events.append(dict(memberIndex=index,fieldName=FIELDS[index],sourceCallInstructionVa=call,
            sourceTargetVa=actual_reads[index],setterCallInstructionVa=setter,setterTargetVa=setters[index],
            resultAbi='low-byte-to-named-bool-setter',sourceBoolBitsNormalized=False))
    g.take('488b742458','4883c430','5f','5d','5b','c3')
    selected=prefix['selectedBytes']+g.seen
    need('all-fifteen-source-field-transfers',[r['memberIndex']for r in events]==list(range(15)))
    return dict(selectedBytes=selected,memberCount=15,newWrapper=new,fieldEvents=events,
        prefixSource=prefix,normalReturn=True,entryRspRestored=True,
        savedIntegerNonvolatilesRestored=['rbx','rbp','rsi','rdi'],positiveFrameBytes=72,
        dictionaryLocals=[e['outLocal']for e in events if 'outLocal'in e],
        dictionaryOutputsResetBeforeEachCall=True,otherFieldsOrRuntimeEffectsClaimed=False,
        childGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=__doc__)
