"""Two stored Output fields; its type argument contributes no wire value."""
SCHEMA = 'endfield.levelscript-action-output-capability.v1'
PREFIX = 'Beyond.Gameplay.Actions.ParamOutput`1<'


def validate(cap):
    if not isinstance(cap, dict) or type(cap.get('outputType')) is not str or not cap['outputType']:
        raise ValueError('currentActionOutput.own-runtime-output-type')
    expected = dict(schema=SCHEMA, typeName=PREFIX+cap['outputType']+'>', memberCount=2,
        fieldOrder=['paramTarget', 'path'], paramTargetWireKind='i32', pathEncoding='int32-pool-index',
        nullWireBytes=1, positiveWireBytes=9, sourceReferenceKind=21, referenceOutputBytes=8,
        closedCarrierProved=True, typeArgumentSerialized=False, nullAdmitted=True, positiveAdmitted=True,
        fourPathWrapperSourceProved=True, factoryAndOriginalHolderProved=True,
        actualCallbackEqualsProvedOutputRequired=True, liveFormatterSelectionObserved=False,
        runtimeOutputWritebackProved=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False)
    if any(type(cap.get(key)) is not type(value) or cap.get(key) != value for key, value in expected.items()):
        raise ValueError('currentActionOutput.exact-two-field-owned-source')
    for key in ('readerMethodDefinition', 'sourceTargetRva', 'canonicalCallbackTargetRva'):
        if type(cap.get(key)) is not int or cap[key] <= 0:
            raise ValueError('currentActionOutput.own-reader-and-callback')


def read(reader, field, cap):
    validate(cap)
    count = reader.number('<B', field+'.memberCount')
    if count == 255:
        return None
    if count != 2:
        raise ValueError(field+':output-member-count')
    return dict(paramTarget=reader.number('<i', field+'.paramTarget'), path=reader.string(field+'.path'))
