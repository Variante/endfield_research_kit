"""Finite list constants joined to independently owned Param wire sources.

This owner supplies no canonical outer Param identity. The dedicated component
joins that separately to its actual closed reference carrier and adapter.
"""
import json

from scripts.game_data.contracts import CONTRACTS_DIR

FLOAT='System.Collections.Generic.List`1<float>'
VECTOR='System.Collections.Generic.List`1<UnityEngine.Vector3>'
TYPES=(FLOAT,VECTOR)
CAP_SCHEMA='endfield.actionmap-numeric-vector-list-constant.v1'
LIMIT=4096


def need(check,condition):
    if not condition:raise ValueError('actionNumericVectorList.'+check)


def specification(value):
    need('finite-own-list-domain',value in TYPES)
    return dict(schema=CAP_SCHEMA,typeName=value,countLimit=LIMIT,countRange=[-1,LIMIT],
        wireCountBytes=4,elementWireBytes=4 if value==FLOAT else 12,
        elementType='float' if value==FLOAT else 'UnityEngine.Vector3',
        elementEncoding='float32-bits' if value==FLOAT else 'raw-xyz-Single',
        finiteFloatProfile=value==VECTOR,positiveCountsAdmitted=True,
        constantSourceAdmitted=True,liveCallbackSelectionObserved=False)


def validate_constant(cap,value):
    expected=specification(value)
    need('exact-own-list-constant-capability',isinstance(cap,dict) and set(cap)==set(expected)
         and all(type(cap.get(k)) is type(v) and cap[k]==v for k,v in expected.items())
         and all(type(n) is int for n in cap['countRange']))
    return cap


def _contract(name,pins,captures):
    path=CONTRACTS_DIR/name;raw=path.read_bytes();fact=json.loads(raw)
    selected=fact.get('nativeInputs',{})
    need('exact-selected-reviewed-source',fact.get('status')=='exact-current-build'
         and {'GameAssembly.dll','global-metadata.dat'}<=set(selected)
         and set(selected)<={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
         and all(pins.get(k)==v for k,v in selected.items()))
    captures[path]=raw
    return fact


def derive_wire(image,pins,*,value_type):
    need('finite-own-list-domain',value_type in TYPES)
    captures={}
    if value_type==FLOAT:
        from scripts.game_data import levelscript_numeric_list_param_native as owner,levelscript_int_list_native as integers
        from scripts.game_data.memorypack import numeric_list_sources
        from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
        fact=_contract('levelscript_numeric_list_param_native.json',pins,captures)
        need('own-numeric-Param-source-schema',fact['schema']==owner.SCHEMA)
        row,=[r for r in fact['components'] if r['elementType']=='float']
        need('own-float-list-Param',row['codecKind']=='Param<List<float>>')
        dependency=_contract('levelscript_int_list_native.json',pins,captures)
        integers._validate_native(image,dependency)
        actual=numeric_list_sources.derive(image,pins,row,dependency)
        validate_claims(row['proof'],actual,label='actionNumericVectorList.Float.source')
        validate_claims(actual,row['proof'],label='actionNumericVectorList.Float.declaration')
        child=actual['child']
        need('own-float-bits-list-source',child['positiveCountAdmitted'] is True
             and child['wireCountBytes']==4 and child['wireElementBytes']==4
             and child['numericConversion'] is False and child['callback']['elementType']=='float'
             and child['callback']['wireBytes']==4 and child['callback']['preservedBits']==32
             and child['countInduction']['maxCount']>=LIMIT)
        result=dict(reviewedSource=fact,actualSource=actual,listSource=dependency)
    else:
        from scripts.game_data.memorypack import levelscript_positive_vector3_list_sources as vectors
        actual=vectors.derive(image,pins)
        vectors.validate(actual,pins)
        result=dict(actualSource=actual)
    need('all-selected-source-contract-bookends',all(p.read_bytes()==raw for p,raw in captures.items()))
    cap=specification(value_type);validate_constant(cap,value_type)
    return dict(**result,constantCapability=cap)
