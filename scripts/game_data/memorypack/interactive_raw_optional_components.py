"""Compile only Variant's independently proved raw Optional field copies.

An Optional's managed size never selects this operation. These six enclosing
fields actually read whole two/eight byte values, including padding. Headered
Optional-reference wrappers have a separate source owner and cannot enter.
"""
import json
from scripts.game_data.memorypack import interactive_value_layouts as layouts
from scripts.game_data.memorypack.interactive_raw_optional_capture_sources import program
from scripts.game_data.memorypack.generated_inline_record_components import _coverage

TYPE='Beyond.Gameplay.Core.InteractiveTemplateVariant'
FIELDS={0:('aoiRadiusType','Beyond.Gameplay.Core.AoiRadiusEnum'),
        3:('delayRecyclePerformTime','float'),4:('delayToRecycleTime','float'),
        6:('facOccDis','float'),7:('factionIndex','Beyond.Gameplay.Core.FactionIndex'),9:('hideInDialog','bool')}


def need(check,condition):
    if not condition:raise ValueError('interactiveRawOptionalComponents.'+check)


def compile_member(owner,scope,read,pins):
    index=read.get('memberIndex');name=read.get('declaredType');macro=read.get('inlineSourceProgram',{})
    need('finite-own-parent-field',owner.get('wrappedType')==TYPE and index in FIELDS
        and (read.get('fieldName'),name)==(FIELDS[index][0],layouts.OPTIONAL+FIELDS[index][1]+'>'))
    width=layouts.RAW[FIELDS[index][1]][1]
    need('same-complete-source-owner',owner.get('nativeInputs')==scope.get('nativeInputs')==pins
        and owner.get('sourceScope')==scope and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read
        and owner.get('completeSelectedCallerAdmitted')is True and owner.get('childGrammarAdmitted')is False
        and read.get('kind')==f'value{width}:'+name and read.get('mode')=='buffered-inline-value'
        and read.get('wireBytes')==macro.get('wireBytes')==width)
    value=scope.get('valueTypeSources',{}).get(str(index),{});layout=value.get('layout',{})
    setter=owner['setters'][index];raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    carrier=bytes.fromhex(layout.get('nominal',{}).get('carrier',{}).get('rawHex',''))
    need('own-closed-value-layout',layout==setter.get('nominalValueLayout')and layout.get('nativeInputs')==pins
        and layout.get('typeName')==name and layout.get('managedBytes')==width and layout.get('referenceLaneOffsets')==[]
        and layout.get('wireGrammarAdmitted')is False and layout.get('openGenericOffsetsUsed')is False
        and len(raw)==len(carrier)==16 and raw[10:12]==carrier[10:12]==bytes((21,128))and raw[:8]==carrier[:8])
    need('native-width-and-source-capture',value.get('typeName')==name and value.get('actualSourceProved')is True
        and value.get('wireBytes')==width and value.get('resultAbi')=='inline-bits-to-owned-field'
        and macro.get('completeSourceBitsCaptured')is True and macro.get('allFourReaderUpdatesProved')is True
        and macro.get('managedLayoutUsedForWidth')is False)
    at,h=read['instruction'];base=macro['guardInstructionVa']-at;selected=scope['selectedProgram']
    need('actual-native-base-and-guard',type(base)is int and base>=0 and bytes.fromhex(h)==bytes((0x83,0x7f,macro['readerOffsets']['bufferLength'],width)))
    native=[(base+a,bytes.fromhex(h))for a,h in selected]
    replay=program(native,macro['guardInstructionVa'],macro['readerOffsets'],reader='rdi',output='rsi')
    need('same-complete-replayed-capture',json.loads(json.dumps(replay))==macro)
    rich=scope.get('richProgram',{});stores=[s for s in rich.get('fieldStores',[])if s.get('memberIndex')==index]
    flow=value.get('sourceProgram',{})
    need('whole-source-bits-and-padding-to-own-field',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==selected and _coverage(stores,width,'sourceOffset','storedBytes')
        and all(flow.get(k)==v for k,v in macro.items())and flow.get('sourceBytes')==macro['selectedBytes']
        and flow.get('fieldStoreProgram')==stores and flow.get('storedBytes')==width
        and flow.get('fullValueBitsStoredUnchanged')is True
        and setter.get('targetField')==TYPE+'::'+read['fieldName']and setter.get('storedBytes')==width
        and setter.get('incomingValueStoredUnchanged')is True
        and setter.get('program',{}).get('normalIncomingValueStoredUnchanged')is True
        and setter.get('program',{}).get('ordinaryFrameRestored')is True)
    return 'interactive-optional-raw'+str(width)
