"""Distinct current GlobalBuffId child, reusing its own reviewed source owner.

The existing nominal GlobalBuffId contract independently authenticates its
managed8 string field, complete MC1/pool4/new/FF wrapper, zero8 constructor,
unchanged RAX getter, exact canonical value adapter and actual Reader/provider
programs. This component composes only that child; neither the same-size BuffId
nor the contract's Param parent supplies an enclosing action. The separate
typed ReadValue binder requires the actual source pointer proved by that owner,
without assigning a registered entry's body to another pointer. Initialized
coherent compatible contexts, canonical selected callbacks, stable disjoint
buffered storage and normal helper/collector effects remain conditions. Runtime
selection, action argument/field transfers and whole-owner/EOF stay unresolved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-global-buff-id-sources.v1'
VALUE='Beyond.Gameplay.Core.GlobalBuffId'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_GlobalBuffIdForMemoryPack'
CAPABILITY='skill-global-buff-id'


def compose(fact,validated,pins):
    """Pure finite shape join; this function grants no native admission."""
    need('global-buff-id-reviewed-shape',('endfield.levelscript-global-buff-id-param-native.v1','exact-current-build',['Param<GlobalBuffId>']),
        (fact.get('schema'),fact.get('status'),fact.get('codecKinds')))
    need('global-buff-id-same-selected-inputs',pins,fact['nativeInputs'])
    need('global-buff-id-own-source-result','proved-current-selected-managed8',validated.get('status'))
    need('global-buff-id-no-runtime-promotion',True,validated.get('runtimeSelectionProved')is False and validated.get('wholeOwnerAdmitted')is False)
    declaration,=[d for d in fact['declarations']if d['typeName']==VALUE]
    need('global-buff-id-own-nominal-wrapper',(WRAPPER,[dict(name='id',typeName='string')]),
        (declaration['wrapperName'],declaration['members']))
    layout=fact['layout']
    need('global-buff-id-own-layout',(8,1,'id','int32-pool-index',5,False),tuple(layout[k]for k in
        ('managedKeyBytes','keyMemberCount','keyName','stringEncoding','serializedPositiveKeyBytes','wholeOwnerAdmitted')))
    cap=dict(typeName=VALUE,wrapperName=WRAPPER,memberCount=1,managedBytes=8,wireBytes=None,
        positiveWireBytes=5,nullWireBytes=1,nullable=True,nullMarker=255,nullReturnsDefaultValue=True,
        wholeGrammarAdmitted=True,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        orderedReads=[dict(fieldName='id',kind='pooled-string')],callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    return cap


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.native_image import read_reviewed_contract
    from scripts.game_data.memorypack.pooled_global_buff_id_sources import validate_components
    _publication_gate(image,pins)
    fact,_=read_reviewed_contract(CONTRACTS_DIR/'levelscript_global_buff_id_param_native.json',
        schema='endfield.levelscript-global-buff-id-param-native.v1',status='exact-current-build',label='skillGlobalBuffId')
    need('global-buff-id-source-selected-inputs',pins,fact['nativeInputs'])
    validated=validate_components(image,fact);cap=compose(fact,validated,pins)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-global-buff-id',nativeInputs=pins,
        typeName=VALUE,wrapperName=WRAPPER,capabilities={CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],
        proof=dict(reviewedNominalSource=fact,validation=validated),
        evidenceBoundary=dict(exact='Own selected GlobalBuffId managed8 layout, MC1/pool4/FF/new wrapper, zero8 constructor/RAX getter and ordinary selected value adapter/actual Reader source.',
            conditional=__doc__,structuralOnly='Stored distinct global buff identifier.',
            unresolved=['actual enclosing argument/field/return transfer','positive collection source','runtime provider/callback selection','whole owner/physical EOF']))))


def derive_read_value(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack.buff_ptr_sources import _typed_context
    _publication_gate(image,pins)
    need('global-buff-id-actual-ReadValue',(6,'MemoryPack.MemoryPackReader','ReadValue',[],[VALUE]),
        tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('global-buff-id-literal-source',True,type(source_target)is int and source_target>image.pe.image_base)
    need('global-buff-id-own-MethodInfo-register',True,
        bytes.fromhex(typed_request.get('instructionHex',''))[:3]==b'\x48\x8b\x15'
        and len(bytes.fromhex(typed_request.get('instructionHex','')))==7)
    child=derive(image,pins)
    need('global-buff-id-own-child-envelope',(SCHEMA,'validated-conditional-global-buff-id',pins,VALUE,WRAPPER),
        tuple(child.get(k)for k in('schema','status','nativeInputs','typeName','wrapperName')))
    fact=child['proof']['reviewedNominalSource']
    cap=compose(fact,child['proof']['validation'],pins)
    need('global-buff-id-source-capability-unchanged',cap,child['capabilities'][CAPABILITY])
    need('global-buff-id-actual-source-not-canonical-alias',image.pe.image_base+fact['symbols']['value'],source_target)
    need('global-buff-id-owned-reader-definition',fact['typedValueUsage']['methodSpec'][0],typed_request['methodSpec'][0])
    context=_typed_context(image,typed_request,VALUE,GenericEntries(image))
    _publication_gate(image,pins)
    return dict(schema='endfield.skill-global-buff-id-read-value.v1',status='proved-conditional-typed-nominal-value-read',
        nativeInputs=pins,typeName=VALUE,wrapperName=WRAPPER,managedBytes=8,readMethod='ReadValue',
        readerMethodDefinition=typed_request['methodSpec'][0],sourceTargetRva=source_target-image.pe.image_base,
        actualSourceProved=True,resultAbi='rax',resultRegister='rax',referenceLaneOffset=0,
        wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(typedRequest=typed_request,typedContext=context,childSource=child,
            actualSourceRva=fact['symbols']['value'],registeredSourceRva=fact['symbols']['registeredValue'],
            actualRegisteredPointerEqualityInferred=False),evidenceBoundary=child['evidenceBoundary'])
