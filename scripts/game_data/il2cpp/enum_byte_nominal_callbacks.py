"""Conditional nominal byte-enum callback from independent complete sources."""
import hashlib
import json

from scripts.game_data.il2cpp import enum_byte_callback_sources as callback_owner
from scripts.game_data.il2cpp import enum_byte_nominal_paths as context_owner
from scripts.game_data.il2cpp import enum_byte_registry_sources as registry_owner
from scripts.game_data.il2cpp.enum_nominal_callback_sources import _nodes

SCHEMA='endfield.enum-byte-nominal-callback-sources.v1'
CAP_SCHEMA='endfield.enum-byte-nominal-callback.v1'
TYPE=context_owner.TYPE
CAPABILITY='enum-byte-callback:'+TYPE
LABEL='enumByteNominalCallbacks'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _regions(regions,windows,base):
    need('complete-exact-region-window-inventory',type(regions)is list and bool(regions)
        and len(regions)==len(windows)and len({at for at,h in regions})==len(regions))
    out=[]
    for at,h in regions:
        raw=bytes.fromhex(h);matches=[w for w in windows if w['startRva']==at and w['endRva']==at+len(raw)]
        need('exact-owned-native-region-hash',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0]['sha256'])
        out.append((base+at,raw))
    return out


def compose(pins,context,registry,callback):
    need('three-independent-current-source-scopes',context.get('schema')==context_owner.SCHEMA
        and context.get('status')=='validated-conditional-original-byte-context-and-selected-code'
        and registry.get('schema')==registry_owner.SCHEMA
        and registry.get('status')=='validated-conditional-byte-registry-roundtrip-source'
        and callback.get('schema')==callback_owner.SCHEMA
        and callback.get('status')=='validated-placeholder-and-dispatch-source-only'
        and all(row.get('nativeInputs')==pins for row in(context,registry,callback)))
    need('own-original-byte-enum-and-selected-code',context.get('typeName')==registry.get('typeName')==TYPE
        and context.get('typeDefinition')==registry.get('typeDefinition')
        and type(context.get('typeDefinition'))is int and context['typeDefinition']>=0
        and context.get('originalContextToSelectedCodeConditional')is True
        and registry.get('sameOriginalNominalTypeAndFormatterRegistryRoundtripConditional')is True
        and callback.get('typeName')=='System.ByteEnum'and type(callback.get('wireBytes'))is int and callback['wireBytes']==1
        and type(context.get('callbackTargetRva'))is int and context['callbackTargetRva']>0
        and context['callbackTargetRva']==callback.get('callbackTargetRva'))
    cp=callback['proof'];selected=context['proof']['selectedCallbackRegistration']
    need('independent-exact-ByteEnum-code-registration',json.loads(json.dumps(selected))==cp['registration']
        and len(selected.get('methodDefinitionIndices',[]))==1)
    definition=selected['methodDefinitionIndices'][0];base=selected['pointer']-context['callbackTargetRva']
    need('explicit-selected-image-base',type(base)is int and base>=0)
    reader=bytes.fromhex(cp['readerParameterHex']);output=bytes.fromhex(cp['outputParameterHex'])
    need('exact-owned-byref-Reader-and-output-VAR-ABI',len(reader)==len(output)==16
        and reader[10:12]==b'\x11\x20'and output[10:12]==b'\x13\x20'
        and int.from_bytes(reader[:8],'little')==cp['readerTypeDefinition']
        and int.from_bytes(output[:8],'little')==cp['outputVariable']['parameterIndex']
        and cp['outputVariable']['typeIndex']==cp['formatterTypeDefinition']and cp['outputVariable']['ordinal']==0
        and cp['formatterMethodDefinition']==definition and cp['namedReaderOffsets']==cp['advanceSource']['readerOffsets'])
    declarations=_nodes(context['proof']['originalContextAndNormalization'],'endfield.enum-inflated-method-class-paths.v1')
    definitions=[r for r in declarations['proof']['intendedPlaceholderDefinitions']if r['methodDefinition']==definition]
    need('same-owned-formatter-method-definition',len(definitions)==1
        and definitions[0]['declaringType']==cp['formatterTypeDefinition']and definitions[0]['parameterCount']==2)
    raw=_regions(cp['callbackRegions'],cp['callbackFamily']['windows'],base)
    programs=[callback_owner.callback_program(raw,selected['pointer'],refill=c)for c in(False,True)]
    need('whole-selected-raw1-callback-replay',json.loads(json.dumps(programs))==cp['callbackPrograms'])
    dispatch=_regions(cp['dispatchRegions'],cp['dispatchFamily']['windows'],base)
    prior=cp['dispatchPrograms'];need('three-actual-byte-dispatch-cases',len(prior)==3)
    actual=[callback_owner.dispatch_program(dispatch,base+callback['sourceTargetRva'],prepare=prior[0]['prepareTarget'],
        callback=selected['pointer'],**case)for case in(dict(),dict(refill=True),dict(indirect=True))]
    need('whole-actual-key-dispatch-replay',json.loads(json.dumps(actual))==prior)
    need('independently-owned-actual-Advance1',cp['advanceSource']['nativeInputs']==pins
        and cp['advanceSource']['completeAdvanceProgramProved']is True
        and cp['advanceSource']['allFourReaderUpdatesProved']is True
        and programs[0]['advanceTarget']==programs[1]['advanceTarget']==base+cp['advanceSource']['targetRva']
        and actual[0]['advanceTarget']==actual[1]['advanceTarget']==programs[0]['advanceTarget'])
    rp=registry['proof'];chain=context['proof']['originalContextAndNormalization']
    need('same-original-nominal-eager-caller',context['proof']['nominalCallerSelections']==rp['nominalCallerSelections'])
    selections=rp['nominalCallerSelections']
    need('one-exact-original-nominal-eager-caller',type(selections)is dict and set(selections)=={TYPE})
    nominal=selections[TYPE];nominal_raw=bytes.fromhex(nominal['nominalRawHex']);usages=nominal['typedUsages']
    need('own-nominal-formatter-constructor-register-requests',len(nominal_raw)==16
        and nominal_raw[10:12]==b'\x11\x80'and int.from_bytes(nominal_raw[:8],'little')==context['typeDefinition']
        and nominal['typeDefinition']==context['typeDefinition']
        and usages['allocation']['typeName']==callback_owner.FORMATTER+'<'+TYPE+'>'
        and usages['constructor']['typeName']==callback_owner.FORMATTER and usages['constructor']['methodName']=='.ctor'
        and usages['constructor']['classArguments']==[TYPE]and usages['constructor']['methodArguments']==[]
        and usages['register']['typeName']=='MemoryPack.MemoryPackFormatterProvider'and usages['register']['methodName']=='Register'
        and usages['register']['classArguments']==[]and usages['register']['methodArguments']==[TYPE]
        and nominal['selectedMacro']['sameAllocatedReferencePreservedInRbx']is True)
    provider=chain['proof']['selectedColdProvider'];method=chain['proof']['providerMethod'][0]
    need('actual-key-VAR-zero-provider-and-original-method-context',rp['keyProviderSlot']['methodSpec'][0]==method
        and rp['providerPrograms'][-1]['actualMethodContextInitializer']==provider['actualMethodContextInitializer']
        and rp['canonicalByteProviderProgram']==provider
        and rp['actualDictionaryRequest']['classArguments'][0]==TYPE)
    receiver=_nodes(chain,'endfield.enum-runtime-type-receiver-paths.v1')
    target=receiver['proof']['typeFromHandlePaths']['hit']['selectedBytes'][0][0]
    need('same-independently-owned-original-TypeFromHandle',rp['providerPrograms'][0]['actualTypeFromHandle']==target
        and rp['registerPrograms'][0]['actualTypeFromHandle']==target)
    need('literal-current-source-and-ABI-identities',type(callback.get('sourceTargetRva'))is int and callback['sourceTargetRva']>0
        and type(registry.get('providerTargetRva'))is int and registry['providerTargetRva']>0
        and cp['outputVariable']['ordinal']==0)
    conditions=[
        'Own ordinary UnmanagedFormatter<the exact original nominal byte enum> is registered and selected, with no intervening replacement.',
        'Actual slot-five callback/MethodInfo retains the original nominal class, Deserialize definition and coherent initialized original contexts.',
        'Both separately proved kind5 normalizers, ByteEnum/System publication and own static ByteEnum registration are selected; loaded metadata agrees.',
        'Source-proved canonical argument and method-key seed/insertion/hit paths select this exact ByteEnum callback row under coherent initialized stable interner/tables.',
        'Own registry insertion/lookup and normal allocation/hash/equality/lock/cleanup/cast/helper effects hold; selected collector barriers are disabled.',
        'The independently proved actual dictionary key provider/dispatcher receives that original nominal MethodInfo/receiver pair; buffered storage is sufficient and disjoint.'
    ]
    capability=dict(schema=CAP_SCHEMA,status='validated-conditional-callback',nativeInputs=pins,typeName=TYPE,
        typeDefinition=context['typeDefinition'],underlyingType='byte',wireBytes=1,callbackTargetRva=context['callbackTargetRva'],
        formatterType=callback_owner.FORMATTER,formatterMethodDefinition=definition,callbackSlot=5,readerByref=True,outputByref=True,
        providerMethodDefinition=method,providerTargetRva=registry['providerTargetRva'],dispatchTargetRva=callback['sourceTargetRva'],
        conditions=conditions,actualRuntimeSelectionObserved=False,unconditionalCallbackSelectionProved=False,
        parentOrCollectionGrammarAdmitted=False,rawBitsPreserved=True,
        evidenceBoundary=dict(exact='Three independent fresh original-context/table, nominal registry/provider and own raw1 callback/actual dispatch source joins.',
            conditional=__doc__,structuralOnly='Raw exact nominal byte bits; declared enum membership is not inferred.',
            unresolved=['actual live registry/cache/MethodInfo state and replacements','enclosing dictionary/record/EOF']))
    return dict(schema=SCHEMA,status='validated-conditional-byte-nominal-callback',nativeInputs=pins,
        capability=capability,proof=dict(originalContextSource=context,nominalRegistrySource=registry,selectedCallbackSource=callback),
        actualRuntimeSelectionObserved=False,wholeOwnerAdmitted=False)


def derive(image,pins,*,typed_request,provider_target,dispatch_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    context=context_owner.derive(image,pins)
    registry=registry_owner.derive(image,pins,typed_request=typed_request,provider_target=provider_target)
    callback=callback_owner.derive_source(image,pins,dispatch_target=dispatch_target)
    result=compose(pins,context,registry,callback)
    _publication_gate(image,pins);return result
