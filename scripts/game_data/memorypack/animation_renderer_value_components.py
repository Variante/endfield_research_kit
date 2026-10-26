"""Own RendererVisibilityEntry MC1, managed8 callback and pooled string array."""
import json
from scripts.game_data.memorypack import animation_renderer_value_sources as source
from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions

SCHEMA='endfield.animation-renderer-value-components.v1'
CAPABILITY='animation-extra-record:'+source.TYPE


def need(check,condition):
    if not condition:raise ValueError('animationRendererComponents.'+check)


def norm(value):return json.loads(json.dumps(value))


def compose(actual,pins):
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import animation_extra_value32_sources as value32,pooled_global_buff_id_sources as neutral,event_args_paths
    from scripts.game_data.memorypack import leveldata_string_array_sources as strings,skill_reference_array_sources as array_sources
    from scripts.game_data.memorypack.pooled_string_list_sources import pooled_string
    from scripts.game_data.memorypack.animation_enemy_shake_value_sources import primitive_program
    from scripts.game_data.animation_current_native import pool_capability
    need('own-native-source',actual.get('schema')==source.SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-renderer-value8-source'and actual.get('typeName')==source.TYPE
        and actual.get('wrapperName')==source.WRAPPER and actual.get('managedBytes')==8
        and actual.get('ordinaryOriginalCallbackAdmitted')is True
        and all(actual.get(k)is False for k in('ordinaryOriginalReadValueAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    p=actual['proof'];layout=p['layout'];pair=p['pair'];faces=pair.get('composition',{}).get('interfaces',[])
    need('own-independent-managed8-reference-layout',layout.get('typeName')==source.TYPE
        and layout.get('fields')==[['rendererNamePrefixes','string[]',16]]and layout.get('boxedBytes')==24
        and layout.get('managedBytes')==8 and layout.get('marshaledNativeBytes')==0xffffffff
        and layout.get('marshaledSizeUsedForManagedWidth')is False and layout.get('referenceLaneOffsets')==[0]
        and layout.get('paddingByteRanges')==[]and layout.get('wireGrammarAdmitted')is False
        and type(layout.get('typeDefinition'))is int and layout['typeDefinition']>=0)
    need('own-pair-wrapper-and-slot5',pair.get('registration',{}).get('originalType')==source.TYPE
        and pair.get('registration',{}).get('wrapperType')==source.WRAPPER and len(faces)==1
        and faces[0].get('originalType')==source.TYPE and faces[0].get('wrapperType')==source.WRAPPER
        and p['forwarding']['readerMethod'][1:3]==[source.WRAPPER,'Deserialize'])
    base=p['registrations']['adapter']['pointer']-p['symbolRvas']['adapter']
    need('selected-native-base',type(base)is int and base>=2**32)
    raw={k:regions(p['sourceWindows'][k],v,base,'renderer-'+k)for k,v in p['sourceRegions'].items()}
    symbols={k:base+v for k,v in p['symbolRvas'].items()}
    def leaf(program,fn,*args):
        selected=program.get('selectedBytes',[]);need('whole-leaf-entry',bool(selected))
        need('whole-own-leaf',norm(fn([(a,bytes.fromhex(h))for a,h in selected],selected[0][0],*args))==program)
    leaf(p['getter'],source.getter_program)
    need('own-registered-QWORD-getter',pair.get('getterEntryProof',{}).get('entryProgram')==p['getter']
        and pair['getterEntryProof']['entryMethod'][0]==faces[0].get('getValueMethodIndex'))
    need('both-own-zero8-factories',len(p.get('zeroLeaves',[]))==2)
    for row,name in zip(p['zeroLeaves'],('.ctor','CreateInstance'),strict=True):
        need('own-named-factory',row['method'][1:3]==[source.WRAPPER,name]);leaf(row['program'],source.zero_program)
    for role,cases in(('adapter',({},dict(create=False),dict(null=True))),('nonnull',({'wrapper_null':False},{'wrapper_null':True}))):
        previous=p['paths'][role];need('complete-own-case-inventory:'+role,len(previous)==len(cases))
        for prior,options in zip(previous,cases,strict=True):
            need('own-helper-symbols',all(symbols.get(k)==v for k,v in prior.get('symbols',{}).items()))
            if role=='nonnull':options=dict(options,ordinal=p['interfaceOrdinal'])
            fn=source.adapter_program if role=='adapter'else source.nonnull_program
            need('whole-own-'+role,norm(fn(raw[role],symbols[role],prior['symbols'],**options))==prior)
    need('whole-own-null-source',norm([value32.read_null_program(raw['readNull'],symbols['readNull'],null=n)for n in(False,True)])==p['paths']['readNull'])
    need('ready-class-helper',norm(neutral.ready_class_init(raw['classReady'],symbols['classReady']))==p['paths']['classReady'])
    callback=base+next(m[3]for m in pair['composition']['methods']if m[0]==faces[0]['formatterDeserializeMethodIndex'])
    need('whole-wrapper-slot5',norm(deserialize_slot(raw['wrapperInvoke'],symbols['wrapperInvoke'],prepare=symbols['prepare'],callback=callback))==p['paths']['wrapperInvocation'])
    for role in('adapter','nonnull','readNull'):
        registration=p['registrations'][role];args=registration.get('classInstantiation',{}).get('arguments',[])
        need('own-canonical-registration',registration.get('pointer')==symbols[role]and len(args)==2)
        carrier=bytes.fromhex(args[0].get('raw_type_record_hex',''))
        need('own-ordinary-kind17',len(carrier)==16 and carrier[10:12]==b'\x11\x80'and int.from_bytes(carrier[:8],'little')==layout['typeDefinition'])
    entry=base+p['forwarding']['readerMethod'][3]
    need('whole-own-MC1-wrapper',norm([source.wrapper_program(raw['wrapper'],entry,**case)for case in({},dict(new=True),dict(null=True))])==p['paths']['wrapper'])
    setter=p['setter'];need('actual-own-named-array-setter',setter['method'][1:3]==[source.WRAPPER,'set___rendererNamePrefixes__']and base+setter['method'][3]==symbols['setter'])
    leaf(setter['program'],source.setter_program,symbols['barrier'])
    primitive_program(raw['header'],symbols['header'],p['readerOffsets'],single=False)
    need('whole-peek',norm(event_args_paths.peek(raw['peek'],symbols['peek'],p['readerOffsets']))==p['peek'])
    array=p['array'];a=array['proof'];cap=array['capability'];request=p['paths']['wrapper'][0]['actualTypedRequest'];usage=a['typedRequest']
    need('own-actual-STRING14-array',array.get('schema')=='endfield.story-pooled-string-array-component.v1'
        and array.get('status')=='validated-conditional-pooled-string-array'and array.get('nativeInputs')==pins
        and array.get('parentFieldAdmitted')is False and array.get('wholeOwnerAdmitted')is False
        and usage.get('instructionRva')==request['instructionVa']-base and usage.get('usageCellRva')==request['cellVa']-base
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadArray',[],['string'])
        and request['sourceTargetVa']==symbols['array']and cap.get('arrayReaderTargetRva')==p['symbolRvas']['array'])
    strings.require_string(bytes.fromhex(a['closedElementRawHex']))
    component=dict(nativeInputs=pins,source=array,capabilities={strings.CAP:cap})
    strings.bind_array(pins,dict(typedRequest=usage,arraySource=array,typeName='string[]',fieldName='rendererNamePrefixes',sourceTargetRva=p['symbolRvas']['array']),component,strings.CAP)
    offsets=p['arrayReaderOffsets']
    need('same-own-reader-fields',all(offsets.get(k)==v for k,v in p['readerOffsets'].items()))
    need('owned-array-total-length',type(offsets['totalLength'])is int and 0<=offsets['totalLength']<128)
    helpers={k:base+v for k,v in a['helperRvas'].items()}
    checked=[array_sources.array_program(raw['array'],symbols['array'],offsets,helpers,count=n,count_limit=3)for n in(-1,0,1,2,3)]
    need('whole-bounded-array-witnesses',norm(checked)==a['arrayPrograms']and norm(array_sources.induction(checked,count_limit=4096))==a['induction'])
    need('whole-array-provider',norm(array_sources.provider_program(raw['arrayProvider'],helpers['provider'],p['arrayProviderSymbols']))==a['provider'])
    string=p['stringCallback'];need('same-independently-owned-pooled-callback',string['entryRva']==a['pooledCallback']['entryRva'])
    need('whole-string-null-empty-lookup',norm([pooled_string(raw['stringCallback'],base+string['entryRva'],string['symbols'],mode=mode)for mode in('lookup','empty','null')])==string['programs'])
    pool=pool_capability(p['pool'],pins)
    own=dict(typeName=source.TYPE,wrapperName=source.WRAPPER,originalTypeDefinition=layout['typeDefinition'],
        memberCount=1,orderedFieldNames=['rendererNamePrefixes'],managedBytes=8,valueStorageKind='value8',
        referenceLaneOffsets=[0],paddingByteRanges=[],wholeGrammarAdmitted=True,nullable=True,nullMarker=255,
        nullWireBytes=1,nullReturnsDefaultValue=True,ordinaryOriginalCallbackAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        canonicalAdapterTargetRva=p['symbolRvas']['adapter'],formatterDeserializeMethodDefinition=faces[0]['formatterDeserializeMethodIndex'],
        stringArrayCapability=cap,requiredChildCapabilities={'byte-payload':pool},actualContainingRouteAdmitted=False,runtimeAnimationProved=False)
    from scripts.game_data.memorypack.animation_renderer_value_codec import require_capability
    require_capability(own)
    return dict(capability=CAPABILITY,capabilities={CAPABILITY:own},requiredExternalCapabilities=['byte-payload'])


def validate_component(component,pins):
    need('own-composed-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-renderer-value-components'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    checked=compose(component['proof']['source'],pins);need('all-and-only-own-capabilities',all(component.get(k)==v for k,v in checked.items()));return checked


def derive(image,pins):
    actual=source.derive(image,pins);checked=compose(actual,pins)
    return dict(schema=SCHEMA,status='validated-conditional-renderer-value-components',nativeInputs=pins,
        **checked,proof=dict(source=actual),parentFieldAdmitted=False,wholeOwnerAdmitted=False)
