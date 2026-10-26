"""Compile the own Color capture/spill/Advance and complete field transfer.

The finite caller program owns sixteen raw input bytes. Independent current
rgba layout, named setter, coherent holder and complete frame retain their own
gates. Neither a Quaternion source nor another managed16 value can select it.
"""
import json

from scripts.game_data.memorypack import generated_color_capture_sources as capture
from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
from scripts.game_data.memorypack.generated_vector_member_sources import setter_program
from scripts.game_data.memorypack.unity_color_sources import TYPE

LABEL='generatedColorComponents'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def normalized(value):return json.loads(json.dumps(value))


def _compile_member(owner,scope,read,pins):
    index=read['memberIndex'];macro=read.get('inlineSourceProgram',{});advance=read.get('inlineAdvanceSource',{})
    value=scope.get('valueTypeSources',{}).get(str(index),{});layout=value.get('layout',{})
    need('same-owned-current-Color-event',type(index)is int and 0<=index<len(scope.get('events',[]))
        and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
        and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read
        and read.get('kind')=='value16:'+TYPE and read.get('declaredType')==TYPE
        and read.get('mode')=='buffered-called-advance-color16'and read.get('actualSourceProved')is True
        and type(read.get('wireBytes'))is int and read['wireBytes']==16)
    need('own-independent-rgba-layout',value.get('typeName')==TYPE and value.get('actualSourceProved')is True
        and value.get('wireBytes')==16 and value.get('resultAbi')=='inline-bits-to-owned-field'
        and layout==read.get('inlineNominalLayout')and layout.get('typeName')==TYPE
        and type(layout.get('typeDefinition'))is int and layout['typeDefinition']>=0
        and layout.get('fields')==[[axis,'float',16+4*i]for i,axis in enumerate('rgba')]
        and layout.get('managedBytes')==16 and layout.get('boxedBytes')==32
        and layout.get('referenceLaneOffsets')==[]and layout.get('paddingByteRanges')==[]
        and layout.get('wireReadAdmitted')is False and layout.get('managedSizeUsedForWireWidth')is False)
    instruction,encoded=read['instruction'];offsets=macro['readerOffsets'];base=macro['guardInstructionVa']-instruction
    selected=scope.get('selectedProgram',[]);header=scope['headerProof']
    need('literal-owned-current-Color-guard',type(base)is int and base>=0 and type(instruction)is int
        and bytes.fromhex(encoded)==bytes((131,127,offsets['bufferLength'],16))and bool(selected))
    regions=[(base+at,bytes.fromhex(h))for at,h in selected];owned={a+i:b for a,raw in regions for i,b in enumerate(raw)}
    replay=capture.program(regions,macro['guardInstructionVa'],offsets,reader=header['readerRegister'],output=header['outputRegister'],
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope.get('codeWindows',[]),base))
    need('actual-capture-and-spill-before-owned-Advance',normalized(replay)==macro
        and macro.get('wireBytes')==16 and macro.get('completeSourceBitsCaptured')is True
        and macro.get('completeSourceBitsSpilledBeforeAdvance')is True
        and macro.get('independentAdvanceSourceRequired')is True and macro.get('managedLayoutUsedForWidth')is False)
    verify_advance(advance,macro,pins,base)
    rich=scope.get('richProgram',{});sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    locals_=[r for r in rich.get('sourceLocalValues',[])if r.get('memberIndex')==index]
    flow=value.get('sourceProgram',{})
    need('whole-Color-source-and-field',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==selected and len(sources)==len(stores)==len(locals_)==1
        and sources[0].get('instruction')==read['instruction']and sources[0].get('mode')==read['mode']
        and sources[0].get('wireBytes')==16 and sources[0].get('program')==macro
        and sources[0].get('actualAdvanceSource')==advance and value.get('advanceSource')==advance
        and all(flow.get(k)==v for k,v in macro.items())and flow.get('sourceBytes')==macro['selectedBytes']
        and flow.get('storedBytes')==16 and flow.get('fullValueBitsStoredUnchanged')is True
        and flow.get('fieldStoreProgram')==stores and stores[0].get('sourceOffset')==0 and stores[0].get('storedBytes')==16)
    local=locals_[0];spill=macro['sourceLocalValues'][0];store=stores[0];setter=owner['setters'][index]
    need('exact-stack16-local-lifetime',local.get('displacement')==spill['displacement']==32
        and local.get('bytes')==local.get('fieldBytes')==spill['bytes']==16
        and local.get('storeInstruction')==[spill['storeInstructionVa']-base,'0F11442420'])
    site,h=store['instruction'];field=setter['fieldOffset']
    need('actual-whole-field-store-and-local-reload',type(field)is int and 16<=field<128
        and bytes.fromhex(h)==bytes((15,17,64,field))
        and all(owned.get(base+site+i)==b for i,b in enumerate(bytes.fromhex(h)))
        and any(at==site-8 and bytes.fromhex(raw)==bytes.fromhex('0f10442420')for at,raw in selected)
        and any(at==site-3 and bytes.fromhex(raw)==bytes.fromhex('488bcf')for at,raw in selected))
    positive=[p for p in owner['programs']if p.get('wrapperNull')is False]
    need('every-positive-complete-local-frame',len(positive)==2
        and {p.get('existing')for p in positive}=={False,True}
        and all(p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True
            and any(type(at)is int and width==16 for at,width in p['frame'].get('sourceValueLocalHomes',[]))
            and any(all(l.get(k)==v for k,v in local.items())and l.get('fieldStores')==stores
                and l.get('liveThroughInstruction')==store['instruction']for l in p['frame'].get('sourceValueLocalLifetimes',[]))for p in positive))
    program=setter.get('program',{});getter=setter.get('getter',{});life=owner.get('lifecycle',{})
    nominal=bytes.fromhex(setter.get('parameterTypeRecordHex',''));method=setter.get('method',[]);get_method=getter.get('method',[])
    need('own-current-complete-Color-setter',setter.get('profile')=='cached-getter-setter'
        and setter==scope.get('richSetters',[])[index]and setter.get('nominalValueLayout')==layout
        and setter.get('storedBytes')==16 and setter.get('member',{}).get('declaredType')==TYPE
        and setter.get('targetField')==owner['wrappedType']+'::'+read['fieldName']
        and setter.get('incomingValueStoredUnchanged')is True and len(nominal)==16
        and nominal[10:12]==bytes((17,128))and int.from_bytes(nominal[:8],'little')==layout['typeDefinition']
        and program.get('storedBytes')==16 and program.get('fullValueStoredUnchanged')is True and program.get('normalFrameAndReturn')is True
        and len(method)==len(get_method)==4 and method[1]==get_method[1]==owner['wrapperName'])
    need('same-own-coherent-Color-holder',getter.get('method')==life.get('coherentGetter',{}).get('method')
        and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
        and isinstance(life.get('typedCache'),list)and len(life['typedCache'])==3
        and life['typedCache'][:2]==[owner['wrapperName'],owner['wrappedType']]
        and getter.get('coherentNonNullSamePointerReturn')is True
        and all(getter.get('program',{}).get(k)is True for k in('fullSameReferenceReturned','entryRspRestored','normalReturn')))
    selected_setter=program.get('selectedBytes',[])
    need('same-owned-setter-entry',bool(selected_setter)and selected_setter[0][0]==base+method[3])
    replay=setter_program([(a,bytes.fromhex(raw))for a,raw in selected_setter],base+method[3],
        getter=base+get_method[3],field=field,width=16,
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,setter.get('codeWindows',[]),base))
    need('whole-named16-setter-replayed',normalized(replay)==program)
    return 'unity-color-raw16'


def compile_member(owner,scope,read,pins):
    try:return _compile_member(owner,scope,read,pins)
    except(ValueError,KeyError,IndexError,TypeError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        failure=CensusGateError(LABEL+'.field',source=owner.get('wrapperName','unknown')+'::Deserialize',
            expected='Own Color rgba/capture/spill/actual Advance, whole field/setter and every positive local frame.',
            actual=dict(wrapperName=owner.get('wrapperName'),fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:1000]))
        failure.diagnostic.update(validator=LABEL,nativeInputs=pins,sourceInstruction=read.get('instruction'),
            helperCodeWindows=read.get('inlineAdvanceSource',{}).get('codeWindows',[])[:3])
        failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error
