"""Own two CharLimbIK raw8 members, with full source/field/frame joins."""
from scripts.game_data.memorypack import char_hand_ik_sources as source

PARENT='Beyond.Gameplay.Core.CharInteractPerform.CharLimbIKActionData'
WIRE='char-hand-ik-raw8'


def need(check,condition):
    if not condition:raise ValueError('charHandIKComponents.'+check)


def compile_member(parent,scope,read,pins):
    index=read.get('memberIndex')
    need('exact-two-owned-HandIK-members',parent.get('wrappedType')==PARENT
        and(index,read.get('fieldName'))in((17,'leftHandParams'),(18,'rightHandParams'))
        and read.get('kind')=='value8:'+source.TYPE and read.get('declaredType')==source.TYPE
        and read.get('wireBytes')==8 and read.get('actualSourceProved')is True and read.get('resultAbi')=='rax')
    need('same-complete-current-parent',parent.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and parent.get('nativeInputs')==scope.get('nativeInputs')==pins and parent.get('sourceScope')==scope
        and parent.get('completeSelectedCallerAdmitted')is True and parent.get('childGrammarAdmitted')is False
        and parent.get('wholeOwnerAdmitted')is False and parent['orderedSourceReads'][index]==scope['events'][index]==read)
    actual=scope.get('primitiveSources',{}).get(str(index),{});source.verify(actual,pins)
    context=read.get('context',{});request=actual['proof']['typedRequest']
    need('own-actual-RDX-MethodSpec-and-carrier',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadUnmanaged'and context.get('fullTypeName')==source.TYPE
        and context.get('typeKind')==17 and context.get('register')=='rdx'
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (request.get('instructionRva'),request.get('instructionHex'),request.get('methodSpec'))
        and context.get('argumentRawHex','').lower()==actual['proof']['closedCarrierHex'].lower()
        and context.get('typeDefinition')==actual['typeDefinition'])
    at,encoded=read['instruction'];raw=bytes.fromhex(encoded)
    need('own-actual-full-QWORD-source-E8',type(at)is int and len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==read.get('sourceTargetRva')==actual['targetRva'])
    setter=parent['setters'][index]
    need('own-whole-nominal-QWORD-field',scope['richSetters'][index]==setter
        and setter.get('targetField')==PARENT+'::'+read['fieldName']and setter.get('storedBytes')==8
        and setter.get('incomingValueStoredUnchanged')is True
        and setter.get('member',{}).get('declaredType')==source.TYPE
        and setter.get('nominalValueLayout')==actual['proof']['layout'])
    rich=scope.get('richProgram',{});stores=[s for s in rich.get('fieldStores',[])if s.get('memberIndex')==index]
    flows=[s for s in rich.get('sources',[])if s.get('memberIndex')==index]
    need('whole-QWORD-through-complete-parent',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')
        and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
        and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
        and stores[0].get('instruction')in scope['selectedProgram'])
    paths=parent.get('programs',[])
    need('all-four-whole-parent-frames',len(paths)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    return WIRE
