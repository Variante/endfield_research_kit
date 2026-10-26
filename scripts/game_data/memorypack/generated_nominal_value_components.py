"""Pure caller joins for separately source-proved nominal value returns.

Only explicit nominal domains enter here. An actual typed Reader, complete
source/return ABI, source-owned setter and caller frame supply the value;
managed size and a similarly sized value never supply a stored grammar.
"""
LABEL='generatedNominalValueComponents'
AUDIO_ID='Beyond.Audio.AudioId'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def audio_id(source,scope,read,pins):
    from scripts.game_data.memorypack.nominal_int32_value_sources import bind
    index=read['memberIndex'];proof=scope.get('primitiveSources',{}).get(str(index),{})
    context=read.get('context',{});usage=proof.get('proof',{}).get('typedRequest',{})
    need('exact-AudioId-source',source.get('nativeInputs')==scope.get('nativeInputs')==proof.get('nativeInputs')==pins
        and read.get('kind')=='value4:'+AUDIO_ID and read.get('declaredType')==AUDIO_ID
        and type(read.get('wireBytes'))is int and read['wireBytes']==4
        and type(read.get('sourceTargetRva'))is int and read['sourceTargetRva']>0)
    # Both operands use RVA coordinates here; no absolute pointer identity or
    # equality with the independently proved registered body is inferred.
    bind(context,read['sourceTargetRva'],proof,base=0)
    nominal=bytes.fromhex(context.get('argumentRawHex',''));instruction=bytes.fromhex(context.get('instructionHex',''))
    need('literal-AudioId-owned-context',type(context.get('instructionRva'))is int and context['instructionRva']>=0
        and len(instruction)==7 and instruction[:3]==bytes.fromhex('488B15')
        and len(nominal)==16 and nominal[10:12]==bytes((17,128))
        and int.from_bytes(nominal[:8],'little')==context.get('typeDefinition'))
    need('same-actual-AudioId-request',usage.get('instructionRva')==context.get('instructionRva')
        and usage.get('instructionHex')==context.get('instructionHex')
        and usage.get('methodSpec')==context.get('methodSpec')
        and (usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[AUDIO_ID])
        and proof['proof'].get('argumentRawHex')==context.get('argumentRawHex'))
    at,encoded=read['instruction'];raw=bytes.fromhex(encoded)
    need('actual-AudioId-E8',type(at)is int and len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==read['sourceTargetRva'])
    setters=source.get('setters',[]);setter=setters[index]if index<len(setters)else{}
    need('own-AudioId-incoming-setter',setter.get('incomingValueStoredUnchanged')is True
        and type(setter.get('storedBytes'))is int and setter['storedBytes']==4
        and setter.get('member',{}).get('declaredType')==AUDIO_ID)
    return 'audio-id-raw4'
