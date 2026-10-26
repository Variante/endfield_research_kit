"""Finite ordinary NPC string/GameplayTag dictionary with exact callback joins."""
import json

from scripts.game_data.memorypack import char_tag_dictionary_sources as source
from scripts.game_data.memorypack import char_tag_dictionary_programs as paths
from scripts.game_data.memorypack.char_tag_dictionary_codec import TYPE,CAPABILITY,TAG_CAPABILITY
from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions

SCHEMA='endfield.char-tag-dictionary-components.v1'
WIRE='char-string-gameplay-tag-dictionary'


def need(check,condition):
    if not condition:raise ValueError('charTagDictionaryComponents.'+check)


def norm(value):return json.loads(json.dumps(value))


def replay_source(actual,pins):
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_header_program
    need('own-current-ordinary-source',actual.get('schema')==source.SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-char-tag-dictionary-source'and actual.get('typeName')==TYPE
        and actual.get('sourceWitnessClassArguments')==['object',source.VALUE]
        and actual.get('closedPointerEquivalenceProved')is False and actual.get('callbackSelectionConditional')is True
        and all(actual.get(k)is False for k in('keyGrammarAdmitted','valueGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    p=actual['proof'];registration=p['registration'];base=registration['pointer']-actual['dictionaryFormatterTargetRva']
    need('independent-closed-source-registration',registration.get('methodDefinitionIndices')==[actual['dictionaryFormatterMethodDefinition']]
        and len(registration.get('classInstantiation',{}).get('arguments',[]))==2 and base>=2**32)
    key,value=registration['classInstantiation']['arguments'];raw=bytes.fromhex(value['raw_type_record_hex'])
    need('source-witness-own-object-Tag-carriers',bytes.fromhex(key['raw_type_record_hex'])[10:12]==bytes((28,0))
        and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==p['nominalIdentity']['valueTypeDefinition'])
    need('same-independent-parent-identity',source.carrier_shape(p['closedCarrier'],int.from_bytes(raw[:8],'little'))==p['nominalIdentity']
        and tuple(p['typedRequest'].get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[TYPE])
        and p['typedRequest']['methodSpec'][0]==actual['packableReaderMethodDefinition']
        and bytes.fromhex(p['readerParameterRawHex'])[10:12]==bytes((17,32))
        and bytes.fromhex(p['outputParameterRawHex'])[10:12]==bytes((21,32))
        and p.get('contextProof',{}).get('authenticatedSlots')==list(range(10)))
    front=p.get('referenceReader',{});front_source=front.get('source',{})
    need('own-ReadPackable-zero-reference8-return',front.get('status')=='validated-components'
        and front.get('packableContext',{}).get('packableDefinition')==actual['packableReaderMethodDefinition']
        and front_source.get('selectedBytes',[[]])[0][0]==base+actual['packableReaderTargetRva']
        and front_source.get('zeroLocalBits')==64 and front_source.get('returnValue')=='complete same local8 to RAX'
        and front_source.get('entryRspRestored')is True and front.get('wholeOwnerAdmitted')is False)
    owned=regions(p['windows'],p['regions'],base,'NPC-tag-Dictionary');symbols=paths.symbols(owned,base+actual['dictionaryFormatterTargetRva'])
    need('same-actual-source-helper-targets',all(p['symbolRvas'].get(k)==v-base for k,v in symbols.items()))
    programs=[paths.program(owned,base+actual['dictionaryFormatterTargetRva'],symbols,count=n)for n in(-1,0,1,2,3)]
    need('whole-Dictionary-byte-and-count-replay',norm(programs)==p['programs']
        and norm(paths.induction(programs,p['induction']['maxCount']))==p['induction'])
    symbols={k:base+v for k,v in p['symbolRvas'].items()};helpers=p['helpers']
    def raw(role):
        need('same-owned-helper-target:'+role,helpers[role]['entryRva']==p['symbolRvas'][role])
        return regions(helpers[role]['windows'],helpers[role]['regions'],base,'NPC-tag-'+role)
    need('complete-count-header-and-pair-transfer',norm(dictionary_header_program(raw('header'),symbols['header'],p['readerOffsets']))==p['headerProgram']
        and norm(paths.pair_program(raw('keyValue'),symbols['keyValue'],key_dispatch=symbols['keyDispatch'],value_dispatch=symbols['valueDispatch']))==p['pairProgram'])
    ctors=[paths.constructor_program(raw('constructor'),symbols['constructor'],symbols,positive=a,same_comparer=b)
        for a in(False,True)for b in(False,True)]
    need('whole-capacity-comparer-and-DWORD-Add',norm(ctors)==p['constructorPrograms']
        and norm(paths.add_program(raw('Add'),symbols['Add'],symbols['insert']))==p['addProgram'])
    for role in('keyProvider','valueProvider','keyDispatch','valueDispatch'):raw(role)
    return base


def replay_tag(child,transfer,proof,pins,base):
    from scripts.game_data.memorypack.skill_gameplay_tag_value_sources import VALUE,WRAPPER,tag_value_program
    from scripts.game_data.memorypack.skill_gameplay_tag_value_transfer import adapter4_program,nonnull4_program,conversion4_program
    from scripts.game_data.memorypack.pooled_global_buff_id_sources import read_null_program
    need('independent-own-Tag-MC1-value4',child.get('schema')=='endfield.skill-gameplay-tag-value-source.v1'
        and child.get('nativeInputs')==transfer.get('nativeInputs')==pins and child.get('typeName')==transfer.get('typeName')==VALUE
        and child.get('wrapperName')==WRAPPER and child.get('status')=='proved-wrapper-source-requires-value4-adapter'
        and transfer.get('schema')=='endfield.skill-gameplay-tag-value-transfer.v1'
        and transfer.get('status')=='proved-selected-value4-transfer'and transfer.get('managedBytes')==4
        and transfer.get('wireBytes')is None and transfer.get('rawUnmanagedTagGrammarUsed')is False
        and child.get('wholeOwnerAdmitted')is False and transfer.get('positiveCollectionAdmitted')is False)
    layout=child['layout'];need('own-Tag-field-layout',layout.get('managedBytes')==4 and layout.get('typeName')==VALUE
        and layout.get('holder')==[WRAPPER,VALUE,16]and layout.get('fields')==
            {'tagId':dict(typeName='int',kind=8,originalBoxedOffset=16,unboxedOffset=0,wrapperOffset=16,bytes=4)})
    rows=child.get('getter',{}).get('instructions',[])
    need('whole-EAX-getter-and-default4',[(h.upper())for _,h in rows]==['8B4110','C3']
        and all([h.upper()for _,h in child['constructors'][name]['instructions']]==['33C0','894110','C3']for name in('.ctor','CreateInstance'))
        and[h.upper()for _,h in child['setter']['instructions']]==['895110','C3'])
    raw=regions(child['sourceWindows'],proof['wrapperRegions'],base,'NPC-tag-value-wrapper')
    symbols={k:base+v for k,v in child['symbolRvas'].items()}
    programs=[tag_value_program(raw,raw[0][0],symbols,**options)for options in({},{'new':True},{'null':True})]
    need('whole-generated-MC1-and-default4-paths',norm(programs)==child['programs'])
    s={k:base+v for k,v in transfer['symbolRvas'].items()};raws={}
    for role,windows in transfer['sourceWindows'].items():raws[role]=regions(windows,proof['transferRegions'][role],base,'NPC-tag-value-'+role)
    checked={role:[adapter4_program(raws[role],s[role],s,dispatch=role=='dispatch',**options)
        for options in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    checked['nonnull']=[nonnull4_program(raws['nonnull'],s['nonnull'],s,null=n)for n in(False,True)]
    checked['conversion']=conversion4_program(raws['conversion'],s['conversion'],s['prepare'],ordinal=transfer['interfaceOrdinal'])
    checked['readNull']=[read_null_program(raws['readNull'],s['readNull'],s,null=n)for n in(False,True)]
    need('whole-independent-Tag-canonical-paths',norm(checked)==transfer['paths']
        and transfer['registrations']['adapter']['pointer']==s['adapter']
        and transfer['callbackBinding'].get('actualDispatcherComparedAdapterRva')==transfer['symbolRvas']['adapter']
        and transfer['callbackBinding'].get('exactClosedWrapperPointerEqualityInferred')is False)
    return dict(typeName=VALUE,memberCount=1,managedBytes=4,nullable=True,nullMarker=255,positiveWireBytes=5,nullWireBytes=1,
        nullReturnsDefaultValue=True,rawUnmanagedTagGrammarUsed=False,wholeGrammarAdmitted=True,
        canonicalAdapterTargetRva=transfer['symbolRvas']['adapter'])


def compose(actual,pins,string,tag,transfer,tag_proof):
    from scripts.game_data.memorypack.animation_custom_dictionary_components import replay_callback
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack.skill_gameplay_tag_value_transfer import adapter4_program
    base=replay_source(actual,pins);need('same-current-string-callback',replay_callback(string,pins)==base and string.get('typeName')=='string')
    value=replay_tag(tag,transfer,tag_proof,pins,base);p=actual['proof'];s={k:base+v for k,v in transfer['symbolRvas'].items()}
    helpers=p['helpers'];key=helpers['keyDispatch'];kr=regions(key['windows'],key['regions'],base,'NPC-tag-key-dispatch')
    key_program=deserialize_slot(kr,base+key['entryRva'],prepare=s['prepare'],callback=base+string['callbackTargetRva'])
    helper=helpers['valueDispatch'];vr=regions(helper['windows'],helper['regions'],base,'NPC-tag-value-dispatch')
    value_programs=[adapter4_program(vr,base+helper['entryRva'],s,dispatch=True,**options)
        for options in({},{'create':False},{'null':True})]
    need('exact-owned-Tag-type-definition',actual['proof']['nominalIdentity']['valueTypeDefinition']==
        int.from_bytes(bytes.fromhex(transfer['registrations']['adapter']['classInstantiation']['arguments'][0]['raw_type_record_hex'])[:8],'little'))
    cap=dict(typeName=TYPE,keyType='string',valueType=source.VALUE,packableReaderMethodDefinition=actual['packableReaderMethodDefinition'],
        packableReaderTargetRva=actual['packableReaderTargetRva'],dictionaryFormatterMethodDefinition=actual['dictionaryFormatterMethodDefinition'],
        dictionaryFormatterTargetRva=actual['dictionaryFormatterTargetRva'],keyCallbackTargetRva=string['callbackTargetRva'],
        valueCallbackTargetRva=value['canonicalAdapterTargetRva'],headerBytes=4,keyWireBytes=4,managedValueBytes=4,countLimit=4096,nodeLimit=16384,
        countRange=[-1,4096],valueWireProfile='generated-gameplay-tag-MC1',valueCapability=TAG_CAPABILITY,wholeGrammarAdmitted=True,
        positiveCountsAdmitted=True,nullable=True,initiallyNullOutputRequired=True,callbackSelectionConditional=True,
        orderedEntriesPreserved=True,duplicateKeysPreserved=True,rawUnmanagedTagGrammarUsed=False,closedPointerEquivalenceProved=False,
        actualRuntimeSelectionObserved=False,finalMutableDictionaryReconstructed=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        requiredChildCapabilities={TAG_CAPABILITY:value},requiredExternalCapabilities=['byte-payload'])
    from scripts.game_data.memorypack.char_tag_dictionary_codec import require_capability
    require_capability(CAPABILITY,cap)
    return dict(capability=CAPABILITY,capabilities={CAPABILITY:cap,TAG_CAPABILITY:value},requiredExternalCapabilities=['byte-payload']),dict(keyProgram=key_program,valuePrograms=value_programs)


def validate_component(component,pins):
    need('own-current-whole-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-char-tag-dictionary-components'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];joined,dispatch=compose(p['source'],pins,p['string'],p['tag'],p['transfer'],p['tagProof'])
    need('same-complete-capabilities-and-selected-dispatch',all(component.get(k)==v for k,v in joined.items())and p['dispatch']==norm(dispatch))
    return joined


def derive_member(image,pins,*,parent_source,member_index=21):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.char_record_components import _attribute
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_string
    from scripts.game_data.memorypack.skill_gameplay_tag_value_sources import derive as derive_tag
    from scripts.game_data.memorypack.skill_gameplay_tag_value_transfer import derive as derive_transfer
    _publication_gate(image,pins);need('exact-own-parent-field',parent_source.get('wrappedType')==source.PARENT and member_index==21)
    _attribute(image,pins,parent_source);read=parent_source['orderedSourceReads'][member_index]
    need('exact-actual-named-dictionary-field',read.get('fieldName')==source.FIELD and read.get('declaredType')==TYPE)
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='charTagDictionary.actual');base=image.pe.image_base
    actual=source.derive(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'])
    string=derive_string(image,pins);tag=derive_tag(image,pins);transfer=derive_transfer(image,pins,tag)
    def capture(windows):return[[w['startRva'],image.window_bytes(w).hex()]for w in windows]
    proof=dict(wrapperRegions=capture(tag['sourceWindows']),transferRegions={k:capture(w)for k,w in transfer['sourceWindows'].items()})
    joined,dispatch=compose(actual,pins,string,tag,transfer,proof)
    result=norm(dict(schema=SCHEMA,status='validated-conditional-char-tag-dictionary-components',nativeInputs=pins,
        typeName=TYPE,**joined,proof=dict(source=actual,string=string,tag=tag,transfer=transfer,tagProof=proof,dispatch=dispatch),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False))
    validate_component(result,pins);bind_member(parent_source,parent_source['sourceScope'],read,pins,usage,result,CAPABILITY)
    _publication_gate(image,pins);return result


def bind_member(parent,scope,read,pins,usage,component,capability):
    from scripts.game_data.memorypack.char_reference_field_bindings import require_transfer
    selected=validate_component(component,pins);need('same-own-selected-dictionary',capability==CAPABILITY==selected['capability'])
    cap=selected['capabilities'][capability];context=read.get('context',{});raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('finite-actual-NPC-class21-field',parent.get('wrappedType')==source.PARENT and read.get('memberIndex')==21
        and read.get('fieldName')==source.FIELD and read.get('declaredType')==TYPE and read.get('kind')=='reference:'+TYPE
        and len(raw)==16 and raw[10:12]==bytes((21,0))and context.get('register')=='rdx'and context.get('typeKind')==21
        and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'))==('MemoryPack.MemoryPackReader','ReadPackable',TYPE)
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
        and usage==component['proof']['source']['proof']['typedRequest']
        and usage['methodSpec'][0]==cap['packableReaderMethodDefinition']and read.get('sourceTargetRva')==cap['packableReaderTargetRva'])
    encoded=bytes.fromhex(read['instruction'][1]);need('actual-ReadPackable-E8',len(encoded)==5 and encoded[0]==232
        and read['instruction'][0]+5+int.from_bytes(encoded[1:],'little',signed=True)==cap['packableReaderTargetRva'])
    transfer=require_transfer(parent,scope,read,pins)
    return dict(fieldName=source.FIELD,typeName=TYPE,capability=capability,readerMethodDefinition=cap['packableReaderMethodDefinition'],
        sourceTargetRva=cap['packableReaderTargetRva'],parentTransfer=transfer)
