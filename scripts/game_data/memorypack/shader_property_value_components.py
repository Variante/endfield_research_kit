"""Own ShaderPropertyEntry MC4/default24 and canonical callback composition."""
import json
from scripts.game_data.memorypack import shader_property_value_sources as source
from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions

SCHEMA='endfield.shader-property-value-components.v1'
CAPABILITY='animation-extra-record:'+source.TYPE


def need(check,condition):
    if not condition:raise ValueError('shaderPropertyComponents.'+check)


def normalized(value):return json.loads(json.dumps(value))


def enum_program(raw,entry,offsets):
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('four-distinct-reader-fields',len({offsets[k]for k in('currentPtr','bufferLength','advancedCount','consumed')})==4
        and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in('currentPtr','bufferLength','advancedCount','consumed')))
    cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(raw,entry);g.take('48895c2408','4889742410','57','4883ec20','8379'+rem+'04','488bd9')
    g.branch('0f8c',False);g.take('488b43'+cur,'8b30','8b7b'+rem,'83c7fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'488b5c2430','8bc6','488b742438','4883c420','5f','c3')
    return [[a,h]for a,h in g.seen]


def compose(actual,pins):
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as neutral,event_args_paths
    from scripts.game_data.memorypack.animation_enemy_shake_value_sources import primitive_program
    from scripts.game_data.animation_current_native import pool_capability
    need('own-current-canonical-value-source',actual.get('schema')==source.SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-shader-property-canonical-value24'
        and actual.get('typeName')==source.TYPE and actual.get('wrapperName')==source.WRAPPER
        and actual.get('managedBytes')==24 and actual.get('referenceLaneOffsets')==[8]
        and actual.get('paddingByteRanges')==[[20,4]]and actual.get('ordinaryOriginalCallbackAdmitted')is True
        and actual.get('ordinaryOriginalReadValueAdmitted')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False)
    p=actual['proof'];nominal=p['layout'];pair=p['pair'];faces=pair.get('composition',{}).get('interfaces',[])
    need('own-complete-physical-layout',nominal.get('typeName')==source.TYPE and nominal.get('fields')==source.FIELDS
        and type(nominal.get('typeDefinition'))is int and nominal['typeDefinition']>=0
        and nominal.get('boxedBytes')==40 and nominal.get('managedBytes')==24
        and nominal.get('referenceLaneOffsets')==[8]and nominal.get('paddingByteRanges')==[[20,4]]
        and nominal.get('paddingRangeEncoding')=='start,length'and nominal.get('serializedFieldNames')==source.ORDER
        and nominal.get('wireGrammarAdmitted')is False
        and[r.get('typeName')for r in nominal.get('enums',[])]==[source.FIELDS[n][1]for n in(0,1,3)]
        and all(type(r.get('typeDefinition'))is int and r.get('backingType')in('int','uint')and r.get('backingBytes')==4 for r in nominal['enums']))
    need('own-eager-pair-and-direct-wrapper-reader',pair.get('registration',{}).get('originalType')==source.TYPE
        and pair.get('registration',{}).get('wrapperType')==source.WRAPPER and len(faces)==1
        and faces[0].get('originalType')==source.TYPE and faces[0].get('wrapperType')==source.WRAPPER
        and p['forwarding']['readerMethod'][1:3]==[source.WRAPPER,'Deserialize'])
    base=p['registrations']['adapter']['pointer']-p['symbolRvas']['adapter']
    need('selected-native-image-base',type(base)is int and base>=2**32)
    raw={k:regions(p['sourceWindows'][k],rows,base,'shader-property-'+k)for k,rows in p['sourceRegions'].items()}
    symbols={k:base+v for k,v in p['symbolRvas'].items()}
    def replay_leaf(program,fn):
        selected=program.get('selectedBytes',[]);need('exact-own-leaf-entry-and-return',bool(selected))
        need('same-complete-own-leaf',normalized(fn([(a,bytes.fromhex(h))for a,h in selected],selected[0][0]))==program)
    replay_leaf(p['getter'],source.getter_program)
    need('own-registered-full-hidden24-getter',pair.get('getterEntryProof',{}).get('entryProgram')==p['getter']
        and pair['getterEntryProof']['entryMethod'][0]==faces[0].get('getValueMethodIndex'))
    need('both-own-zero24-factories',len(p.get('zeroLeaves',[]))==2)
    for row,name in zip(p['zeroLeaves'],('.ctor','CreateInstance'),strict=True):
        need('exact-own-named-zero24',row['method'][1:3]==[source.WRAPPER,name]);replay_leaf(row['program'],source.zero_program)
    entry=base+p['forwarding']['readerMethod'][3]
    checked=[source.wrapper_program(raw['wrapper'],entry,**case)for case in({},dict(new=True),dict(null=True))]
    need('all-three-complete-MC4-wrapper-paths',normalized(checked)==p['wrapperPaths'])
    for role,cases in(('adapter',({},dict(create=False),dict(null=True))),('nonnull',({'wrapper_null':False},{'wrapper_null':True}))):
        previous=p['paths'][role];need('complete-own-case-inventory:'+role,len(previous)==len(cases))
        for prior,options in zip(previous,cases,strict=True):
            own_symbols=prior.get('symbols',{})
            need('only-own-independently-joined-helper-symbols',all(symbols.get(k)==v for k,v in own_symbols.items()))
            fn=source.adapter_program if role=='adapter'else source.nonnull_program
            need('same-complete-own-'+role,normalized(fn(raw[role],symbols[role],own_symbols,**options))==prior)
    need('whole-interface-hidden24-copy',normalized(source.conversion_program(raw['conversion'],symbols['conversion'],
        ordinal=p['interfaceOrdinal'],prepare=symbols['prepare']))==p['paths']['conversion'])
    need('whole-owned-null-consumption',normalized([neutral.read_null_program(raw['readNull'],symbols['readNull'],symbols,null=n)
        for n in(False,True)])==p['paths']['readNull'])
    need('exact-wrapper-slot5-dispatch',normalized(deserialize_slot(raw['wrapperInvoke'],symbols['wrapperInvoke'],
        prepare=symbols['prepare'],callback=base+next(m[3]for m in pair['composition']['methods']
        if m[0]==faces[0]['formatterDeserializeMethodIndex'])))==p['paths']['wrapperInvocation'])
    for role in('adapter','nonnull','readNull'):
        registration=p['registrations'][role];args=registration.get('classInstantiation',{}).get('arguments',[])
        need('same-own-canonical-registration:'+role,len(args)==2 and registration.get('pointer')==symbols[role])
        carrier=bytes.fromhex(args[0].get('raw_type_record_hex',''))
        need('own-nominal-kind17-value24',len(carrier)==16 and carrier[10:12]==b'\x11\x80'
            and int.from_bytes(carrier[:8],'little')==nominal['typeDefinition'])
    requests=p['requests'];need('all-three-actual-enum-requests',len(requests)==3)
    for request,field in zip(requests,('blendMode','mask','type'),strict=True):
        usage=request['typedRequest'];name=next(t for n,t,o in source.FIELDS if n==field)
        need('own-exact-typed-enum-wire-request',request.get('fieldName')==field
            and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
                ==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[name])
            and request.get('sourceTargetVa')==symbols['enum'])
    selected=enum_program(raw['enum'],symbols['enum'],p['readerOffsets'])
    def bytes_in_order(program,origin=0):
        return[(at-origin+i,b)for at,h in program for i,b in enumerate(bytes.fromhex(h))]
    need('whole-owned-four-byte-enum-reader',bytes_in_order(selected,base)==bytes_in_order(p['enum']['selectedProgram'])
        and p['enum'].get('wireBytes')==4 and p['enum'].get('resultRegister')=='eax'
        and p['enum'].get('targetRva')==p['symbolRvas']['enum'])
    # These independently owned primitive programs supply their exact buffered
    # Reader effects. The pool operation remains an explicit external child.
    primitive_program(raw['header'],symbols['header'],p['readerOffsets'],single=False)
    need('own-peek-program',normalized(event_args_paths.peek(raw['peek'],symbols['peek'],p['readerOffsets']))==p['peek'])
    pool=pool_capability(p['pool'],pins)
    need('same-actual-pooled-name-source',pool['sourceTargetRva']==p['symbolRvas']['pool'])
    if 'actualDispatch'in p['paths']:
        need('actual-complete-value24-dispatch',normalized([source.adapter_program(raw['actualDispatch'],symbols['actualDispatch'],symbols,
            dispatch=True,**case)for case in({},dict(create=False),dict(null=True))])==p['paths']['actualDispatch'])
    cap=dict(typeName=source.TYPE,wrapperName=source.WRAPPER,originalTypeDefinition=nominal['typeDefinition'],
        memberCount=4,orderedFieldNames=source.ORDER,managedBytes=24,valueStorageKind='value24',
        referenceLaneOffsets=[8],paddingByteRanges=[[20,4]],wholeGrammarAdmitted=True,
        nullable=True,nullMarker=255,nullWireBytes=1,nullReturnsDefaultValue=True,positiveWireBytes=17,
        ordinaryOriginalCallbackAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        canonicalAdapterTargetRva=p['symbolRvas']['adapter'],formatterDeserializeMethodDefinition=faces[0]['formatterDeserializeMethodIndex'],
        requiredChildCapabilities={'byte-payload':pool},actualContainingRouteAdmitted=False,runtimeAnimationProved=False)
    from scripts.game_data.memorypack.shader_property_value_codec import require_capability
    require_capability(cap)
    return dict(capability=CAPABILITY,capabilities={CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'])


def validate_component(component,pins):
    need('own-native-composed-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-shader-property-value-components'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    checked=compose(component['proof']['source'],pins)
    need('all-and-only-owned-capabilities',all(component.get(k)==v for k,v in checked.items()))
    return checked


def derive(image,pins,*,dispatch_target=None):
    actual=source.derive(image,pins,dispatch_target=dispatch_target);joined=compose(actual,pins)
    return dict(schema=SCHEMA,status='validated-conditional-shader-property-value-components',nativeInputs=pins,
        **joined,proof=dict(source=actual),parentFieldAdmitted=False,wholeOwnerAdmitted=False)
