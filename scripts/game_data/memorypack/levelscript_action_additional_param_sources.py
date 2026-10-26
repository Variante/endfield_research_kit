"""Own complete Quaternion and PosRot-list Param sources on a selected image.

Constant, caller and ordinary canonical reference proofs stay separate. A
failed generated caller is pending; neither a layout nor a retained packet
is accepted as its replacement.
"""
import json

from scripts.game_data.codecs.levelscript.current_action_additional_param import SCHEMA,QUATERNION,POSROT_LIST,validate_constant


def need(check,condition,detail=None):
    if not condition:raise ValueError('actionAdditionalParam.'+check+(':'+str(detail)[:1800]if detail is not None else''))


def _quaternion(image,pins):
    from scripts.game_data.memorypack.levelscript_quaternion_param_sources import derive_parent
    source=derive_parent(image,pins)
    return dict(wrapperSource=source),dict(wireKind='quaternion-raw16',wireBytes=16,fieldOrder=['x','y','z','w'])


def _posrot(image,pins):
    from scripts.game_data import levelscript_pos_rot_native as owner
    from scripts.game_data.memorypack.levelscript_posrot_list_param_sources import derive_parent
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader
    path=owner.DEFAULT_CONTRACT;raw=path.read_bytes();fact=json.loads(raw)
    need('own-reviewed-PosRot-native-build',fact.get('schema')==owner.SCHEMA
        and fact.get('status')=='exact-current-build'and fact.get('nativeInputs')==pins
        and fact.get('layout')==dict(stringEncoding='int32-pool-index',parentMemberCount=4,childMemberCount=2,
            positiveChildWireBytes=25,defaultChildWireBytes=1,managedValueBytes=24,
            listCount='signed-int32;-1=null',tail=['Int32 idRef','Int32 paramSource','pooled path']))
    owner._validate_native(image,fact)
    parent=derive_parent(image,pins)
    actual=parent['typedRead']
    contexts=[c for c in fact['usageContexts']if c.get('methodName')=='ReadPackable'and c.get('methodArguments')==[POSROT_LIST]]
    need('one-own-current-PosRot-typed-source',len(contexts)==1 and actual==contexts[0])
    reader=_reader(image,pins)
    need('same-owned-PosRot-ReadPackable-definition',actual['methodSpec'][0]==reader['packableContext']['packableDefinition'])
    need('all-four-own-PosRot-Param-paths',len(parent['programs'])==4
        and {(p['existing'],p['wrapperNull'])for p in parent['programs']}=={(False,False),(True,False),(False,True),(True,True)})
    need('own-PosRot-contract-exit',path.read_bytes()==raw)
    return dict(reviewedSource=fact,currentParent=parent,packableReferenceSource=reader),dict(wireKind='posrot-list',
        countLimit=4096,elementMemberCount=2,nullElementMarker=255,elementPositiveWireBytes=25,
        elementDefaultBytes=24,fieldOrder=['eulerAngles','position'])


def derive_wire(image,pins,*,value_type):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('finite-independent-value-domain',value_type in(QUATERNION,POSROT_LIST))
    _publication_gate(image,pins)
    proof,spec=_quaternion(image,pins)if value_type==QUATERNION else _posrot(image,pins)
    cap=dict(schema=SCHEMA,valueType=value_type,**spec,constantSourceProved=True,fullParamSourceProved=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        runtimeValueEvaluationAdmitted=False,wholeOwnerAdmitted=False)
    validate_constant(cap,value_type);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,constantCapability=cap,proof=proof,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
