"""Own canonical EnemyShake value8 callback plus its separate MC2 wire."""
import json
from scripts.game_data.memorypack import animation_enemy_shake_value_sources as source

TYPE=source.TYPE
CAPABILITY='animation-extra-record:'+TYPE
SCHEMA='endfield.animation-enemy-shake-value-components.v1'


def need(check,condition):
    if not condition:raise ValueError('animationEnemyShakeComponents.'+check)


def require_capability(cap):
    need('own-MC2-value8-capability',cap.get('typeName')==TYPE and cap.get('wrapperName')==source.WRAPPER
        and cap.get('wholeGrammarAdmitted')is True and cap.get('memberCount')==2
        and cap.get('orderedFieldNames')==['animationSpeed','animationWeight']
        and cap.get('valueStorageKind')=='value8'and cap.get('managedBytes')==8
        and cap.get('referenceLaneOffsets')==cap.get('paddingByteRanges')==[]
        and cap.get('positiveWireBytes')==9 and cap.get('nullWireBytes')==1
        and cap.get('nullMarker')==255 and cap.get('nullReturnsDefaultValue')is True
        and cap.get('ordinaryOriginalCallbackAdmitted')is True and cap.get('ordinaryOriginalReadValueAdmitted')is False
        and type(cap.get('originalTypeDefinition'))is int and cap['originalTypeDefinition']>=0
        and type(cap.get('canonicalAdapterTargetRva'))is int and cap['canonicalAdapterTargetRva']>0
        and type(cap.get('formatterDeserializeMethodDefinition'))is int and cap['formatterDeserializeMethodDefinition']>=0)
    return cap


def compose(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as paths
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    need('own-native-callback-source',actual.get('schema')==source.SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-enemy-shake-canonical-value8'
        and actual.get('typeName')==TYPE and actual.get('wrapperName')==source.WRAPPER and actual.get('managedBytes')==8
        and actual.get('referenceLaneOffsets')==actual.get('paddingByteRanges')==[]
        and actual.get('ordinaryOriginalCallbackAdmitted')is True and actual.get('ordinaryOriginalReadValueAdmitted')is False
        and actual.get('parentFieldAdmitted')is False and actual.get('wholeOwnerAdmitted')is False)
    p=actual['proof'];layout=p['layout'];pair=p['pair'];forward=p['forwarding'];faces=pair['composition']['interfaces']
    need('exact-own-two-Single-layout',layout.get('typeName')==TYPE and layout.get('fields')==source.FIELDS
        and layout.get('managedBytes')==8 and layout.get('boxedBytes')==24
        and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]and type(layout.get('typeDefinition'))is int)
    need('own-eager-pair-and-formatter',pair['registration'].get('originalType')==TYPE
        and pair['registration'].get('wrapperType')==source.WRAPPER and len(faces)==1
        and faces[0].get('originalType')==TYPE and faces[0].get('wrapperType')==source.WRAPPER
        and forward['readerMethod'][1:3]==[source.WRAPPER,'Deserialize'])
    first=p['wrapperPaths'][0]['selectedBytes'][0][0];base=first-forward['readerMethod'][3]
    raw={k:regions(p['sourceWindows'][k],rows,base,'enemyShake-'+k)for k,rows in p['sourceRegions'].items()}
    symbols={k:base+v for k,v in p['symbolRvas'].items()}
    need('three-exact-MC2-wrapper-paths',source.normalized([source.wrapper_program(raw['wrapper'],first,**a)
        for a in({},{'new':True},{'null':True})])==p['wrapperPaths'])
    own=p['getter'];at=own['selectedBytes'][0][0]
    need('own-complete-SSE-value8-getter',source.normalized(source.getter_program([(a,bytes.fromhex(h))for a,h in own['selectedBytes']],at))==own
        and pair.get('getterEntryProof',{}).get('kind')=='owned-selected-getter-entry'
        and pair['getterEntryProof'].get('entryProgram')==own
        and pair['getterEntryProof']['entryMethod'][0]==faces[0]['getValueMethodIndex'])
    need('exact-own-default8-factories',len(p.get('zeroLeaves',[]))==2)
    for row,name in zip(p['zeroLeaves'],('.ctor','CreateInstance'),strict=True):
        method=row['method'];ins=row['program'].get('instructions',[])
        need('same-owned-zero8-leaf',method[1:3]==[source.WRAPPER,name]
            and ins==[[method[3],'33C0'],[method[3]+2,'48894110'],[method[3]+6,'C3']])
    checked=dict(adapter=[paths.adapter_program(raw['adapter'],symbols['adapter'],symbols,**a)for a in({},{'create':False},{'null':True})],
        nonnull=[source.nonnull_program(raw['nonnull'],symbols['nonnull'],symbols,wrapper_null=n)for n in(False,True)],
        readNull=[paths.read_null_program(raw['readNull'],symbols['readNull'],symbols,null=n)for n in(False,True)],
        conversion=paths.conversion_program(raw['conversion'],symbols['conversion'],symbols,ordinal=p['interfaceOrdinal']),
        wrapperInvocation=deserialize_slot(raw['wrapperInvoke'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
            callback=base+next(r[3]for r in pair['composition']['methods']if r[0]==faces[0]['formatterDeserializeMethodIndex'])))
    need('all-canonical-default-interface-paths-replayed',source.normalized(checked)==p['paths'])
    need('same-owned-wrapper-primitives',source.normalized({role:source.primitive_program(raw[role],symbols[role],p['readerOffsets'],single=role=='single')
        for role in('single','header')})==p.get('primitivePaths'))
    for role in('adapter','nonnull','readNull'):
        registration=p['registrations'][role];args=registration.get('classInstantiation',{}).get('arguments',[])
        need('own-selected-canonical-registration:'+role,len(args)==2 and registration.get('pointer')==symbols[role])
        carrier=bytes.fromhex(args[0].get('raw_type_record_hex',''))
        need('same-nominal-value8-carrier',len(carrier)==16 and carrier[10:12]==b'\x11\x80'
            and int.from_bytes(carrier[:8],'little')==layout['typeDefinition'])
    cap=dict(typeName=TYPE,wrapperName=source.WRAPPER,originalTypeDefinition=layout['typeDefinition'],memberCount=2,
        orderedFieldNames=['animationSpeed','animationWeight'],managedBytes=8,valueStorageKind='value8',
        referenceLaneOffsets=[],paddingByteRanges=[],valueFields=source.FIELDS,wholeGrammarAdmitted=True,
        nullable=True,nullMarker=255,nullWireBytes=1,nullReturnsDefaultValue=True,positiveWireBytes=9,
        ordinaryOriginalCallbackAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        canonicalAdapterTargetRva=p['symbolRvas']['adapter'],formatterDeserializeMethodDefinition=faces[0]['formatterDeserializeMethodIndex'],
        actualContainingRouteAdmitted=False,runtimeAnimationProved=False)
    require_capability(cap)
    return dict(capability=CAPABILITY,capabilities={CAPABILITY:cap},requiredExternalCapabilities=[])


def validate_component(component,pins):
    need('native-composed-own-value8',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-animation-enemy-shake-value-components'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    checked=compose(component['proof']['source'],pins)
    need('all-and-only-owned-capabilities',all(component.get(k)==v for k,v in checked.items()))
    return checked


def derive(image,pins):
    actual=source.derive(image,pins);joined=compose(actual,pins)
    return dict(schema=SCHEMA,status='validated-conditional-animation-enemy-shake-value-components',nativeInputs=pins,
        **joined,proof=dict(source=actual),parentFieldAdmitted=False,wholeOwnerAdmitted=False)
