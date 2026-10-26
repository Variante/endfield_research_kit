"""Pure nominal Query16 closed-helper replay; no wire or native admission."""
import hashlib,json
from scripts.game_data.memorypack.generated_managed_forwarder_sources import TYPE,context_shape
from scripts.game_data.memorypack.generated_vector3_source import forwarder_program

LABEL='generatedManagedForwarderComponents'

def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def _require_source(actual,read,pins,usage):
    """Return only the separately complete nested Query source after exact joins."""
    need('exact-owned-Query-forwarder',read.get('declaredType')==actual.get('typeName')==TYPE
        and read.get('sourceContextMode')==actual.get('sourceContextMode')==actual.get('contextMode')=='owned-closed-forwarder'
        and actual.get('schema')=='endfield.generated-managed-closed-forwarder-source.v1'
        and actual.get('status')=='proved-conditional-owned-Query-ReadValue-forwarder'
        and actual.get('nativeInputs')==pins and actual.get('managedBytes')==read.get('managedBytes')==16
        and actual.get('resultAbi')=='hidden-local'and actual.get('actualSourceProved')is True
        and actual.get('pointerAliasClaimed')is False and actual.get('managedEntryIdentityClaimed')is False
        and actual.get('wireGrammarAdmitted')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False and actual.get('sourceTargetRva')==read.get('sourceTargetRva'))
    proof=actual.get('proof',{});context=proof.get('internalContext',{});context_shape(context,TYPE)
    nested=proof.get('nestedSource',{});program=proof.get('forwarderProgram',{})
    need('exact-internal-Query-ReadValue-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),
        usage.get('classArguments'),usage.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
        and type(context.get('typeDefinition'))is int
        and int.from_bytes(bytes.fromhex(context.get('argumentRawHex',''))[:8],'little')==context['typeDefinition'])
    need('same-independent-internal-request',read.get('context')in(None,context)
        and proof.get('typedRequest')==nested.get('proof',{}).get('typedRequest')==usage
        and (context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec')))
    entry=program.get('selectedBytes',[[None]])[0][0]
    need('literal-forwarder-entry',type(entry)is int and type(actual.get('sourceTargetRva'))is int)
    base=entry-actual['sourceTargetRva'];regions=proof.get('actualSourceRegions',[]);windows=proof.get('actualWindows',[])
    need('complete-owned-forwarder-regions',bool(regions)and len(regions)==len(windows)
        and len({at for at,h in regions})==len(regions))
    for at,h in regions:
        raw=bytes.fromhex(h);matched=[w for w in windows if base+w.get('startRva',-base)==at
            and w.get('endRva',0)-w.get('startRva',0)==len(raw)]
        need('owned-forwarder-window-hash',len(matched)==1
            and hashlib.sha256(raw).hexdigest().upper()==matched[0].get('sha256'))
    replay=forwarder_program([(at,bytes.fromhex(h))for at,h in regions],entry)
    need('complete-actual-forwarder-byte-replay',json.loads(json.dumps(replay))==program
        and program.get('contextInstructionVa')==base+usage.get('instructionRva',-base)
        and program.get('contextCellVa')==context.get('cellVa')
        and all(program.get(key)is True for key in('sameIncomingReaderRdx','sameIncomingOutputRcx',
            'sameOutputReturnedInRax','fullFrameAndNonvolatilesRestored')))
    need('separate-complete-nominal-Query-source',nested.get('status')=='proved-conditional-typed-nominal-value-read'
        and nested.get('nativeInputs')==pins and nested.get('typeName')==TYPE
        and nested.get('managedBytes')==16 and nested.get('resultAbi')=='hidden-local'
        and nested.get('actualSourceProved')is True and nested.get('wireGrammarAdmitted')is False
        and nested.get('sourceTargetRva')==program.get('nestedTargetVa',base)-base
        and nested.get('readerMethodDefinition')==actual.get('readerMethodDefinition')==usage.get('methodSpec',[None])[0])
    return nested


def require_source(actual,read,pins,usage):
    """Retain a bounded attributable failure before a costly aggregate retry."""
    try:return _require_source(actual,read,pins,usage)
    except(ValueError,KeyError,IndexError,TypeError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        failure=CensusGateError(LABEL+'.source',source='scripts/game_data/memorypack/generated_managed_forwarder_components.py',
            expected='exact own Query internal MethodInfo/forwarder bytes, unchanged pointers/full frame and separate nominal nested source',
            actual=dict(typeName=read.get('declaredType'),fieldName=read.get('fieldName'),reason=str(error)[:1200]))
        failure.diagnostic.update(validator=LABEL,failedGate=str(error).split(':',1)[0],memberIndex=read.get('memberIndex'),
            nativeInputs=pins,sourceInstruction=read.get('instruction'),sourceTargetRva=read.get('sourceTargetRva'),
            sourceWindows=actual.get('proof',{}).get('actualWindows',[])[:4])
        failure.args=(json.dumps(failure.diagnostic,sort_keys=True),);raise failure from error
