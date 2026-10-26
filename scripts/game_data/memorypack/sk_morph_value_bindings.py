"""Own actual SkMorph hidden40 source, named setter, full field and frame."""
from scripts.game_data.memorypack import sk_morph_value_components as owner,sk_morph_value_sources as value
from scripts.game_data.memorypack import generated_sk_morph_field_sources as field


def need(check,condition):
    if not condition:raise ValueError('skMorphValueBinding.'+check)


def bind(source,scope,read,pins,usage,child,capability):
    need('own-finite-value-child',capability==owner.CAPABILITY)
    joined=owner.validate_component(child,pins);cap=joined['capabilities'][capability];index=read.get('memberIndex')
    need('complete-current-parent',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==pins and source.get('sourceScope')==scope
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False and type(index)is int and 0<=index<len(source['orderedSourceReads'])
        and source['orderedSourceReads'][index]==read and scope.get('events')==source['orderedSourceReads'])
    setter=source['setters'][index];need('same-fresh-setter',scope['richSetters'][index]==setter)
    field.validate_event(read,setter);nominal=value.validate_layout(setter['managedValueLayout'])
    actual=scope.get('managedValueSources',{}).get(str(index),{});base=owner.replay_value(actual,pins)
    need('own-current-source-to-value-child',actual['typeName']==value.TYPE and actual['sourceTargetRva']==read.get('sourceTargetRva')==cap['valueReaderTargetRva']
        and actual['readerMethodDefinition']==usage.get('methodSpec',[None])[0]==cap['valueReaderMethodDefinition']
        and actual['proof']['typedRequest']==usage and actual['proof']['layout']==nominal==child['proof']['value']['proof']['layout']
        and actual['proof']['symbolRvas']==child['proof']['value']['proof']['symbolRvas'])
    context=read['context'];raw=bytes.fromhex(context.get('instructionHex',''));call_at,call_hex=read['instruction'];call=bytes.fromhex(call_hex)
    need('same-actual-R8-and-E8',len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadValue',[],[value.TYPE])
        and len(call)==5 and call[0]==232 and call_at+5+int.from_bytes(call[1:],'little',signed=True)==read['sourceTargetRva'])
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    setter_raw=regions(setter['codeWindows'],setter['ordinarySourceRegions'],base,'skMorph-parent-setter')
    replay=field.setter_program(setter_raw,base+setter['method'][3],field=setter['fieldOffset'],barrier=base+actual['proof']['symbolRvas']['barrier'])
    need('whole-own-named-setter-replay',owner.normalized(replay)==setter['program']
        and setter['member']['name']==read['fieldName']and setter['member']['declaredType']==value.TYPE
        and setter['method'][0]==setter['member']['methodIndex']and setter['method'][2]=='set___'+read['fieldName']+'__'
        and setter.get('targetField','').endswith('::'+read['fieldName'])and setter.get('incomingValueStoredUnchanged')is True)
    rich=scope['richProgram'];selected=rich['selectedProgram'];sources=[r for r in rich['sources']if r['memberIndex']==index]
    stores=[r for r in rich['fieldStores']if r['memberIndex']==index];hidden=[r for r in rich['hiddenSourceLocals']if r['memberIndex']==index]
    need('whole-actual-source-field-path',rich.get('completeSelectedNormalProgram')is True and selected==scope['selectedProgram']
        and sources==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='hidden-local')]
        and sorted((r['sourceOffset'],r['storedBytes'])for r in stores)==[(0,16),(16,16),(32,8)]
        and all(r['instruction']in selected for r in stores)and read['instruction']in selected
        and len(hidden)==1 and hidden[0]['bytes']==40 and hidden[0]['nominalTypeName']==value.TYPE
        and hidden[0]['nominalTypeDefinition']==nominal['typeDefinition']and hidden[0]['sourceInstruction']==read['instruction'])
    paths=source['programs'];need('all-four-whole-frames',len(paths)==4
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    home=[hidden[0]['displacement']-scope['headerProof']['nullFrameBytes'],40]
    need('actual-owned-hidden40-home',all(home in p['frame'].get('hiddenSourceLocalHomes',[])for p in paths if not p['wrapperNull']))
    transfer=dict(memberIndex=index,fieldName=read['fieldName'],typeName=value.TYPE,managedBytes=40,resultAbi='hidden-local',
        referenceLaneOffsets=[24],paddingByteRanges=value.PADDING,sourceInstruction=read['instruction'],setterMethod=setter['method'],
        fieldOffset=setter['fieldOffset'],fieldStores=stores,hiddenSourceLocal=hidden[0],completeFieldTransferAndFrameProved=True,wireGrammarAdmitted=False)
    return dict(fieldName=read['fieldName'],typeName=value.TYPE,capability=capability,readerMethodDefinition=actual['readerMethodDefinition'],
        sourceTargetRva=actual['sourceTargetRva'],managedValueTransfer=transfer,managedValueCapabilityShape=cap,ordinaryReferenceIdentityClaimed=False)
