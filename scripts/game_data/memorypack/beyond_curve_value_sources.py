"""Conditional Beyond FAnimationCurve value framing and actual typed source.

This composes independently derived concrete MC3/raw-key-array framing and
managed16 canonical callback/conversion. It is separate from Unity curves.
Positive key counts are bounded by the current proved copy component. No
enclosing record, runtime provider selection or curve evaluation is admitted.
"""

def derive(image,pins,*,typed_request,source_target,count_limit=8):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.beyond_curve_sources import derive as derive_wrapper
    from scripts.game_data.memorypack.managed_value16_read_sources import derive as derive_read
    _publication_gate(image,pins)
    if typed_request.get('methodArguments')!=['Beyond.FAnimationCurve']:
        raise ValueError('beyondCurveValue.exact-typed-request')
    child=derive_wrapper(image,pins,count_limit=count_limit)
    source=derive_read(image,pins,typed_request=typed_request,source_target=source_target,reference_lane=0,
        wrapper_name=child['wrapperName'])
    if source['typeName']!=child['typeName']or source['nativeInputs']!=child['nativeInputs']or source['wrapperName']!=child['wrapperName']:
        raise ValueError('beyondCurveValue.same-current-child-and-source')
    _publication_gate(image,pins)
    return dict(schema='endfield.beyond-curve-value-source.v1',status='proved-conditional-beyond-curve-value',nativeInputs=pins,
        typeName=child['typeName'],wrapperName=child['wrapperName'],managedBytes=16,referenceLaneOffset=0,
        readMethod='ReadValue',readerMethodDefinition=source['readerMethodDefinition'],sourceTargetRva=source['sourceTargetRva'],
        actualSourceProved=True,resultAbi='hidden-local',nullMarker=255,serializedMemberCount=3,
        nullAdmitted=True,positiveAdmitted=True,keyCountLimit=count_limit,
        wireProgram=dict(null=dict(headerBytes=1,marker=255,output='default zero16'),
            positive=dict(headerBytes=1,memberCount=3,fields=[
                dict(name='keys',kind='raw-array',signedCountBytes=4,nullCount=-1,emptyCount=0,positiveCountLimit=count_limit,
                    elementBytes=32,elementHeaders=False,order=['time','value','inTangent','outTangent','tangentMode','weightedMode','inWeight','outWeight']),
                dict(name='postWrapMode',kind='enum32-bits',bytes=4),dict(name='preWrapMode',kind='enum32-bits',bytes=4)])),
        providerSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(wrapper=child,typedSource=source),
        evidenceBoundary=dict(exact='Actual typed Reader and complete matched canonical managed16 source compose the independently proved concrete MC3/FF wrapper, interface/GetValue16 conversion and bounded raw FKeyframe array32.',
            conditional=source['evidenceBoundary']['conditional']+' '+child['evidenceBoundary']['conditional'],
            structuralOnly='Stored key fields and wrap enum bits; no curve evaluation or runtime effect.',
            unresolved=['live provider/default/override/inflation selection','keys above bounded current copy limit','enclosing parent framing/field/EOF','cold/refill/error paths']))
