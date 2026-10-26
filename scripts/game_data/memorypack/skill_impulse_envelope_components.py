"""Own Envelope value32 transfer joined to two actual Unity Curve readers.

The actual hidden32 source/adapter/default and wrapper MC7 precede this wire
composition. Each curve has an independent complete custom-formatter grammar,
including its actual ordinary Reader identity and bounded key induction.
Parent local/store/frame, enclosing action and live callback choice remain
separate. Managed width is never consumed as a serialized width.
"""
import json
from scripts.game_data.memorypack.skill_impulse_envelope_sources import TYPE,WRAPPER,CURVE,MEMBERS
from scripts.game_data.memorypack.skill_impulse_envelope_codec import CAPABILITY,ORDER
from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability as require_curve
from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value

LABEL='skillImpulseEnvelopeComponents'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def compose(pins,transfer,curve):
    need('own-complete-actual-value-source',transfer.get('schema')=='endfield.impulse-envelope-value-transfer.v1'
        and transfer.get('status')=='proved-conditional-envelope-value32-read'
        and transfer.get('nativeInputs')==pins and transfer.get('typeName')==TYPE and transfer.get('wrapperName')==WRAPPER
        and type(transfer.get('managedBytes'))is int and transfer['managedBytes']==32
        and transfer.get('resultAbi')=='hidden-local'and transfer.get('actualSourceProved')is True
        and transfer.get('referenceLaneOffsets')==[0,8]and transfer.get('wireGrammarAdmitted')is False
        and transfer.get('parentFieldAdmitted')is False)
    child=transfer.get('proof',{}).get('childSource',{});layout=child.get('layout',{})
    need('own-current-wrapper-and-managed-layout',child.get('schema')=='endfield.impulse-envelope-wrapper-source.v1'
        and child.get('status')=='proved-envelope-wrapper-source-requires-value-and-curve-joins'
        and child.get('nativeInputs')==pins and child.get('typeName')==TYPE and child.get('wrapperName')==WRAPPER
        and child.get('childGrammarAdmitted')is False and child.get('originalDefaultValueAdmitted')is False
        and layout.get('typeName')==TYPE and layout.get('managedBytes')==32
        and layout.get('referenceLaneOffsets')==[0,8]and layout.get('paddingByteRanges')==[[30,32]])
    expected={'m_AttackShape':(CURVE,0,8),'m_DecayShape':(CURVE,8,8),
        'm_AttackTime':('float',16,4),'m_SustainTime':('float',20,4),'m_DecayTime':('float',24,4),
        'm_ScaleWithImpact':('bool',28,1),'m_HoldForever':('bool',29,1)}
    need('own-named-reference-float-Boolean-storage',set(layout.get('fields',{}))==set(expected)
        and all((layout['fields'][name].get('typeName'),layout['fields'][name].get('unboxedOffset'),
            layout['fields'][name].get('bytes'))==value for name,value in expected.items()))
    need('independent-complete-Unity-curve',curve.get('schema')=='endfield.skill-animation-curve-sources.v1'
        and curve.get('status')=='validated-conditional-unity-animation-curve'
        and curve.get('nativeInputs')==pins and curve.get('wholeSkillDataAdmitted')is False)
    curve_cap=require_curve(curve.get('capabilities',{}).get('skill-animation-curve',{}))
    requests=child.get('requests',{});symbols=child.get('symbolRvas',{});readers=child.get('referenceReaders',{})
    need('exact-two-own-Curve-requests',set(requests)=={'attack','decay'}
        and symbols.get('curve')==curve_cap['referenceReaderTargetRva']==readers.get('referenceReaderTargetRva')
        and curve_cap['referenceReaderMethodDefinition']==readers.get('referenceReaderMethodDefinition'))
    bindings={}
    for role,field in(('attack','m_AttackShape'),('decay','m_DecayShape')):
        bindings[role]=bind_read_value(pins,dict(fieldName=field,typeName=CURVE,typedRequest=requests[role],
            sourceTargetRva=symbols['curve']),dict(nativeInputs=pins,capabilities={'curve-profile':curve_cap}),'curve-profile')
    for key,kind,width,result in(('singleSource','float32',4,'xmm0-low32'),('booleanSource','bool',1,'al-normalized')):
        primitive=child.get(key,{})
        need('own-complete-'+key,primitive.get('kind')==kind and primitive.get('wireBytes')==width
            and primitive.get('resultRegister')==result and primitive.get('boolNormalized')is(kind=='bool')
            and all(primitive.get(k)is True for k in('completeBufferedProgram','entryRspRestored','nonvolatilesRestored'))
            and primitive.get('targetRva')==symbols.get('single'if kind=='float32'else'boolean'))
    definition=transfer.get('readerMethodDefinition');target=transfer.get('sourceTargetRva')
    dispatch=transfer.get('proof',{}).get('symbolRvas',{}).get('dispatch')
    need('literal-own-value-reader-identities',all(type(n)is int and n>0 for n in(definition,target,dispatch)))
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=7,managedBytes=32,referenceLaneOffsets=[0,8],
        paddingByteRanges=[[30,32]],nullable=True,nullMarker=255,nullWireBytes=1,wireBytes=None,positiveWireBytes=None,
        nullReturnsDefaultValue=True,wholeGrammarAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,actualValueReadValueAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
        orderedReads=ORDER,valueReaderMethodDefinition=definition,valueSourceTargetRva=target,
        valueDispatcherTargetRva=dispatch,callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    return dict(capabilities={CAPABILITY:cap,'curve-profile':curve_cap},bindings=bindings,
        requiredExternalCapabilities=['curve-profile'],requiredExternalCapabilityIdentities={'curve-profile':{
            k:curve_cap[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}})


def derive(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    from scripts.game_data.memorypack.skill_impulse_envelope_transfer import derive as transfer_source
    from scripts.game_data.memorypack.skill_animation_curve_sources import derive as curve_source
    transfer=transfer_source(image,pins,typed_request=typed_request,source_target=source_target)
    curve=curve_source(image,pins);selected=compose(pins,transfer,curve);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.impulse-envelope-components.v1',
        status='validated-conditional-impulse-envelope-components',nativeInputs=pins,**selected,
        proof=dict(transfer=transfer,curve=curve),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own current Envelope value32 Reader/adapter/default/wrapper MC7 and both actual Curve reader joins to the complete Unity custom formatter/key induction.',
            conditional=__doc__,structuralOnly='Stored impulse envelope configuration.',
            unresolved=['actual parent local/whole-field/frame','enclosing action/Skill/EOF','live provider/callback choice','camera response']))))
