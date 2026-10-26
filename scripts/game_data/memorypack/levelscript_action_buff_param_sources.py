"""Independent BuffPtr constants and their exact ordinary Param reference join.

The value owns the complete hidden16, nested ObjectPtr and concrete Buff MC1
source. The distinct list owns only its actual null return; no element or
positive-count effect is borrowed from the value's managed width.
"""
import json

from scripts.game_data.contracts import CONTRACTS_DIR

VALUE='Beyond.Gameplay.Core.BuffPtr'
LIST='System.Collections.Generic.List`1<'+VALUE+'>'
TYPES=(VALUE,LIST)
SCHEMA='endfield.actionmap-buff-param-constant.v1'


def need(check,condition):
    if not condition:raise ValueError('actionBuffParam.'+check)


def specification(value):
    need('finite-own-Buff-domain',value in TYPES)
    result=dict(schema=SCHEMA,valueType=value,constantSourceProved=True,
        fullParamSourceProved=True,actualCallbackEqualsProvedChildRequired=True,
        liveFormatterSelectionObserved=False,runtimeValueEvaluationAdmitted=False,wholeOwnerAdmitted=False)
    if value==LIST:
        result.update(wireKind='null-buff-list',collectionCounts=[-1],wireCountBytes=4,
            positiveElementsAdmitted=False,elementCallbacks=0,typedListContextRead=False)
    else:
        result.update(wireKind='buff-pointer-record',managedValueBytes=16,constantMemberCount=1,
            nestedMemberCount=2,uidEncoding='uint32',objectType='Beyond.Gameplay.Core.Buff',
            constantNullAdmitted=True,nestedNullAdmitted=True,objectNullAdmitted=True,
            positiveObjectAdmitted=True,objectMemberCount=1,objectField='modifiedBBKeys',
            objectEncoding='pooled-string-list',objectListMaxCount=10000)
    return result


def validate_constant(cap,value):
    expected=specification(value)
    need('exact-own-Buff-constant-capability',isinstance(cap,dict) and set(cap)==set(expected)
        and all(type(cap.get(k))is type(v)and cap[k]==v for k,v in expected.items())
        and (value!=LIST or all(type(n)is int for n in cap['collectionCounts'])))
    return cap


def derive_wire(image,pins,*,value_type):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reference_join
    need('finite-own-Buff-domain',value_type in TYPES);_publication_gate(image,pins)
    if value_type==LIST:
        from scripts.game_data.memorypack import levelscript_action_param_sources as source
        actual=source.derive(image,pins,codec_kind='Param<List<BuffPtr>>')
        reference=actual['proof']['reference'];parent=actual['proof']['source']
        need('own-null-list-Param-source',actual['capability']['valueType']==LIST
            and actual['capability']['collectionCounts']==[-1]
            and actual['capability']['positiveElementsAdmitted']is False
            and actual['proof']['nullListProgram']['elementCallbacks']==0
            and actual['proof']['nullListProgram']['typedListContextRead']is False)
        proof=dict(actualSource=actual,positiveListSourceAdmitted=False,
            positiveListElementsAndContextEffectsProved=False)
    else:
        from scripts.game_data import levelscript_buff_ptr_param_native as owner
        from scripts.game_data.memorypack import buff_ptr_param,pooled_source_helper
        from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
        paths=[owner.DEFAULT_CONTRACT,pooled_source_helper.CONTRACT_PATH,
            CONTRACTS_DIR/'levelscript_pooled_string_list_native.json']
        captures={path:path.read_bytes()for path in paths};fact=owner._contract(owner.DEFAULT_CONTRACT)
        need('selected-reviewed-Buff-Param-source',fact['nativeInputs']==pins)
        actual=buff_ptr_param.derive(image,pins,fact['profile'])
        validate_claims(fact['proof'],actual,label='actionBuffParam.source')
        validate_claims(actual,fact['proof'],label='actionBuffParam.declaration')
        validate_claims(fact['evidenceBoundary'],actual['evidenceBoundary'],label='actionBuffParam.boundary')
        validate_claims(actual['evidenceBoundary'],fact['evidenceBoundary'],label='actionBuffParam.boundary-declaration')
        parent=actual['parent'];reference=_reference_join(image,pins,VALUE)
        need('own-positive-Buff-object-source',actual['buffObject']['typeName']=='Beyond.Gameplay.Core.Buff'
            and actual['buffObject']['positiveAdmitted']is True and actual['buffObject']['memberCount']==1
            and actual['buffObject']['listMaxCount']==10000)
        need('all-own-Buff-source-contract-bookends',all(path.read_bytes()==raw for path,raw in captures.items()))
        proof=dict(reviewedSource=fact,actualSource=actual)
    getter=parent['ownedMethods']['GetValue']
    need('same-owned-complete-Param-reference-getter',getter['methodIndex']==reference['getterMethodDefinition']
        and getter['pointerRva']==reference['getter']['entryRva'])
    cap=specification(value_type);validate_constant(cap,value_type);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,proof=proof,constantCapability=cap,
        canonicalReference=reference,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
