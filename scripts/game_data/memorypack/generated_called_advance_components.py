"""Finite compilation of actual DWORD capture plus complete called Advance.

This pure join replays both current caller bytes and the actual helper's whole
buffered/zero-count programs. Complete outer caller/lifecycle and current named
setter evidence are still mandatory in the shared record compiler. GameplayTag
uses its own independently validated nominal source; it is not an Int32 alias.
"""
import hashlib,json
from scripts.game_data.memorypack import generated_called_advance_sources as source
from scripts.game_data.memorypack.generated_inline_record_components import _cached_scalar_setter,_coverage

LABEL='generatedCalledAdvanceComponents'
def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)
def normalized(value):return json.loads(json.dumps(value))

def verify_advance(cap,macro,pins,base):
    """Replay the actual helper independently of its caller's value kind."""
    offsets=macro['readerOffsets']
    need('same-independent-complete-actual-helper',cap.get('nativeInputs')==pins
        and cap.get('targetRva',-base)+base==macro['advanceTargetVa']and
        cap.get('completeAdvanceProgramProved')is True and cap.get('allFourReaderUpdatesProved')is True
        and cap.get('entryRspRestored')is True and cap.get('allNonvolatilesRestored')is True
        and cap.get('registeredMethodIdentityClaimed')is False and cap.get('childGrammarAdmitted')is False
        and all(cap.get('readerOffsets',{}).get(k)==v for k,v in offsets.items())
        and cap.get('family',{}).get('selectedPrimaryRva')==cap['targetRva'])
    windows=cap.get('codeWindows',[]);regions=cap.get('sourceRegions',[])
    need('all-current-owned-helper-regions',bool(windows)and len(windows)==len(regions)
        and len({a for a,h in regions})==len(regions))
    for at,h in regions:
        raw=bytes.fromhex(h);matches=[w for w in windows if base+w.get('startRva',-base)==at and w.get('endRva',0)-w.get('startRva',0)==len(raw)]
        need('exact-owned-helper-region-hash',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
    actual=[source.advance_program([(a,bytes.fromhex(h))for a,h in regions],macro['advanceTargetVa'],offsets,zero=z)for z in(False,True)]
    need('exact-complete-actual-helper-programs',normalized(actual)==cap.get('programs'))

def _compile_member(owner,scope,read,pins):
    index=read['memberIndex'];kind=read['kind'];macro=read.get('inlineSourceProgram',{});cap=read.get('inlineAdvanceSource',{})
    need('same-source-owned-ordered-event',type(index)is int and 0<=index<len(scope.get('events',[]))and scope['events'][index]==read)
    need('finite-current-called-advance-field',kind in('scalar32','value4:Beyond.Gameplay.Core.GameplayTag','value4:UnityEngine.LayerMask')and read.get('mode')=='buffered-called-advance-scalar'
        and owner.get('nativeInputs')==scope.get('nativeInputs')==cap.get('nativeInputs')==pins and read.get('actualSourceProved')is True
        and type(read.get('wireBytes'))is int and read['wireBytes']==macro.get('wireBytes')==4
        and macro.get('independentAdvanceSourceRequired')is True and macro.get('managedLayoutUsedForWidth')is False)
    instruction,encoded=read['instruction'];offsets=macro.get('readerOffsets',{})
    profile=(scope['headerProof']['readerRegister'],scope['headerProof']['outputRegister'])
    guards={('r15','r14'):bytes((0x41,0x83,0x7f,offsets.get('bufferLength',-1),4)),
        ('rbp','rsi'):bytes((0x83,0x7d,offsets.get('bufferLength',-1),4))}
    need('literal-current-guard',type(instruction)is int and type(macro.get('guardInstructionVa'))is int
        and profile in guards and bytes.fromhex(encoded)==guards[profile])
    base=macro['guardInstructionVa']-instruction;selected=scope.get('selectedProgram',[])
    need('literal-current-native-base',type(base)is int and base>=0 and bool(selected))
    caller=[(base+at,bytes.fromhex(h))for at,h in selected];owned={at+i:b for at,raw in caller for i,b in enumerate(raw)}
    if profile==('rbp','rsi'):
        from scripts.game_data.memorypack.generated_rbp_scalar_capture_sources import program
    else:program=source.program
    replay=program(caller,macro['guardInstructionVa'],offsets,reader=profile[0],output=profile[1])
    need('exact-replayed-caller-capture-and-E8',normalized(replay)==macro and all(owned.get(at+i)==b for at,h in macro['selectedBytes']for i,b in enumerate(bytes.fromhex(h))))
    verify_advance(cap,macro,pins,base)
    proof=scope.get('inlinePrimitiveSources',{}).get(str(index),{})
    need('same-independent-scope-capture-and-helper',proof.get('program')==macro and proof.get('advanceSource')==cap and proof.get('wireBytes')==4)
    rich=scope.get('richProgram',{});flows=[f for f in rich.get('sources',[])if f.get('memberIndex')==index]
    stores=[f for f in rich.get('fieldStores',[])if f.get('memberIndex')==index]
    need('whole-source-to-current-named-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==selected
        and len(flows)==1 and flows[0].get('instruction')==read['instruction']and flows[0].get('mode')==read['mode']
        and flows[0].get('program')==macro and flows[0].get('actualAdvanceSource')==cap and _coverage(stores,4,'sourceOffset','storedBytes'))
    for store in stores:
        at,h=store['instruction'];need('same-actual-owned-field-store',all(owned.get(base+at+i)==b for i,b in enumerate(bytes.fromhex(h))))
    setter=owner['setters'][index]
    need('same-named-whole-field-setter',setter.get('incomingValueStoredUnchanged')is True and setter.get('storedBytes')==4
        and setter.get('member',{}).get('declaredType')==read['declaredType']and setter.get('targetField')==owner['wrappedType']+'::'+read['fieldName'])
    if setter.get('profile')in('inline-coherent-cache-setter','cached-getter-setter'):
        _cached_scalar_setter(owner,setter,dict(read,kind='scalar32'),base)
    else:
        program=setter.get('program',{})
        need('whole-direct-setter-frame',setter.get('profile')=='direct-base-holder-setter'and program.get('completeOriginalProgram')is True
            and program.get('normalIncomingValueStoredUnchanged')is True and program.get('ordinaryFrameRestored')is True)
    if kind in('value4:Beyond.Gameplay.Core.GameplayTag','value4:UnityEngine.LayerMask'):
        nominal=read.get('inlineNamedValueSource',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
        typename,wire={'value4:Beyond.Gameplay.Core.GameplayTag':('Beyond.Gameplay.Core.GameplayTag','gameplay-tag32'),
            'value4:UnityEngine.LayerMask':('UnityEngine.LayerMask','layer-mask-raw4')}[kind]
        need('independent-exact-current-GameplayTag-domain'if typename=='Beyond.Gameplay.Core.GameplayTag'else'independent-exact-current-LayerMask-domain',nominal==proof.get('namedValueSource')and nominal.get('nativeInputs')==pins
            and nominal.get('status')=='validated'and nominal.get('typeName')==read['declaredType']==typename
            and nominal.get('wireBytes')==4 and nominal.get('resultRegister')=='eax'and len(raw)==16 and raw[10:12]==bytes((17,128))
            and int.from_bytes(raw[:8],'little')==nominal.get('typeDefinition'))
        return wire
    return 'scalar32'

def compile_member(owner,scope,read,pins):
    try:return _compile_member(owner,scope,read,pins)
    except(ValueError,KeyError,IndexError,TypeError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        failure=CensusGateError(LABEL+'.field',source=owner.get('wrapperName','unknown')+'::Deserialize',
            expected='Exact complete current DWORD capture/actual Advance replay, whole named setter and independent nominal domain.',
            actual=dict(wrapperName=owner.get('wrapperName'),fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:600]))
        failure.diagnostic.update(validator=LABEL,nativeInputs=pins,sourceInstruction=read.get('instruction'),
            helperCodeWindows=read.get('inlineAdvanceSource',{}).get('codeWindows',[])[:3])
        failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error
