"""AbilitySystemForInt's raw PlungingAttackData source, including padding."""
import json
from scripts.game_data.memorypack import interactive_plunging_layout as nominal
from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
from scripts.game_data.memorypack.generated_inline_record_components import _coverage,_owned_setter_trace
from scripts.game_data.memorypack.generated_float4_capture_sources import program as capture

PARENT='Beyond.Gameplay.Core.AbilitySystemForIntData'
ANCESTOR='Beyond.Gameplay.Core.AbilitySystemData'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_AbilitySystemDataForMemoryPack'


def need(check,condition):
    if not condition:raise ValueError('interactivePlungingComponents.'+check)


def norm(value):return json.loads(json.dumps(value))


def compile_member(owner,scope,read,pins):
    from scripts.game_data.memorypack.generated_reader_sources import constructed_getter_join
    from scripts.game_data.memorypack.generated_vector_member_sources import setter_program
    index=read.get('memberIndex');macro=read.get('inlineSourceProgram',{});advance=read.get('inlineAdvanceSource',{})
    need('finite-own-parent-and-field',owner.get('wrappedType')==PARENT and index==25 and read.get('fieldName')=='plungingAttackData'
        and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
        and owner.get('completeSelectedCallerAdmitted')is True and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read)
    setter=owner['setters'][index];layout=nominal.require_event(read,setter)
    need('own-source-layout',read.get('inlineNominalLayout')==layout)
    at,h=read['instruction'];base=macro.get('guardInstructionVa',-1)-at
    need('actual-buffered-sixteen-byte-operation',type(base)is int and base>=0
        and bytes.fromhex(h)==bytes((0x83,0x7f,macro['readerOffsets']['bufferLength'],16)))
    native=[(base+a,bytes.fromhex(h))for a,h in scope['selectedProgram']]
    replay=capture(native,macro['guardInstructionVa'],macro['readerOffsets'],reader='rdi',output='rbx',
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope['codeWindows'],base))
    need('complete-actual-XMM6-capture',norm(replay)==macro and macro.get('managedLayoutUsedForWidth')is False
        and macro.get('capturedSourceSlices')==[dict(register='xmm6',sourceOffset=0,bytes=16,
            loadInstructionVa=macro['capturedSourceSlices'][0]['loadInstructionVa'],kind='sse')])
    verify_advance(advance,macro,pins,base)
    value=scope.get('valueTypeSources',{}).get(str(index),{});flow=value.get('sourceProgram',{})
    rich=scope.get('richProgram',{});stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    need('whole-stored-value-and-padding',value.get('layout')==layout and value.get('typeName')==nominal.TYPE
        and value.get('actualSourceProved')is True and value.get('wireBytes')==16 and value.get('advanceSource')==advance
        and value.get('resultAbi')=='inline-bits-to-owned-field'
        and rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==scope['selectedProgram']
        and _coverage(stores,16,'sourceOffset','storedBytes')and flow.get('fieldStoreProgram')==stores
        and all(flow.get(k)==v for k,v in macro.items())and flow.get('sourceBytes')==macro['selectedBytes']
        and flow.get('storedBytes')==16 and flow.get('fullValueBitsStoredUnchanged')is True)
    need('both-complete-XMM6-frames',all('xmm6'in p['frame'].get('restoredVectorHomes',{})
        for p in owner['programs']if p['wrapperNull']is False))
    life=owner['lifecycle'];getter=setter.get('getter',{});refresh=getter.get('compatibleRefresh',{})
    joined=constructed_getter_join(life,owner['setters']);matches=[r for r in joined.get('setters',[])if r.get('method')==setter.get('method')]
    need('independent-constructed-ancestor-and-refresh',setter.get('profile')=='cached-getter-setter'
        and setter.get('method',[None,None])[1]==WRAPPER and setter.get('targetField')==ANCESTOR+'::plungingAttackData'
        and getter.get('method',[None,None])[1]==WRAPPER and getter.get('typedCache')==[WRAPPER,ANCESTOR,24]
        and getter.get('baseHolder')==life.get('baseHolder')and getter.get('coherentNonNullSamePointerReturn')is True
        and refresh.get('initializedCompatibleNonNullBaseRequired')is True and refresh.get('emptyOrDifferentCacheAdmitted')is True
        and {p.get('path')for p in refresh.get('programs',[])}=={'empty','different'}
        and joined==owner.get('constructedGetterJoin')and joined.get('inheritedCacheCoherenceAssumed')is False
        and matches==[dict(method=setter['method'],cacheOffset=24,mode='exact-compatible-refresh-from-constructed-base')])
    selected=setter['program']['selectedBytes']
    actual=setter_program([(a,bytes.fromhex(h))for a,h in selected],base+setter['method'][3],
        getter=base+getter['method'][3],field=setter['fieldOffset'],width=16,
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,setter['codeWindows'],base))
    need('complete-actual-setter-byte-replay',norm(actual)==setter['program'])
    return 'interactive-plunging-raw16'
