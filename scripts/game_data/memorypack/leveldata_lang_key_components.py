"""Dedicated two-reference LangKey wire child and explicit managed field binder."""
TYPE='Beyond.LangKey'
CAP='story-lang-key'


def _capability(read_source):
    return dict(typeName=TYPE,managedBytes=16,referenceLaneOffsets=[0,8],memberCount=1,
        keyName='key',keyEncoding='int32-pool-index',positiveWireBytes=5,nullWireBytes=1,
        nullHeaderDefaultValueBytes=16,nonserializedRawText=True,
        nullAdmitted=True,positiveAdmitted=True,wholeGrammarAdmitted=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        readerMethodDefinition=read_source['readerMethodDefinition'],sourceTargetRva=read_source['sourceTargetRva'])


def derive(image,pins,*,typed_request,source_target):
    from scripts.game_data.memorypack.leveldata_lang_key_value_sources import derive_read_value
    from scripts.game_data.codecs.leveldata.current_lang_key import validate
    source=derive_read_value(image,pins,typed_request=typed_request,source_target=source_target)
    # The freshly validated dedicated owner includes both concrete MC1/pool
    # programs and all canonical hidden16/default/GetValue transfer paths.
    # No enclosing source/frame claim is acquired by this child.
    cap=_capability(source);validate(cap)
    return dict(schema='endfield.story-lang-key-component.v1',nativeInputs=pins,capabilities={CAP:cap},
        proof=dict(readSource=source),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Dedicated current LangKey MC1 pooled-key/FF-default and two-reference managed16 source/adapter/GetValue programs.',
            conditional='Matching actual canonical callbacks, initialized coherent contexts, buffered disjoint source/output, disabled collector and normal helper effects. Unserialized rawText is not read from the wire.',
            unresolved=['actual enclosing source/local/field/frame','runtime formatter/provider selection','whole owner/physical EOF']))


def bind_value(source,scope,read,pins,usage,component,capability):
    from scripts.game_data.memorypack.generated_managed_value_components import require_transfer
    from scripts.game_data.codecs.leveldata.current_lang_key import validate
    transfer=require_transfer(source,scope,read,pins);cap=component.get('capabilities',{}).get(capability,{})
    validate(cap);actual=scope.get('managedValueSources',{}).get(str(read['memberIndex']),{})
    setter=source['setters'][read['memberIndex']];layout=setter['managedValueLayout']
    child=component.get('proof',{}).get('readSource',{})
    if (capability!=CAP or component.get('nativeInputs')!=pins or read['declaredType']!=TYPE
            or(transfer['managedBytes'],transfer['resultAbi'],transfer['referenceLaneOffsets'],transfer['paddingByteRanges'])!=(16,'hidden-local',[0,8],[])
            or layout.get('fields')!=[['key','string',16,14],['<rawText>k__BackingField','string',24,14]]
            or actual.get('schema')!='endfield.story-lang-key-value-source.v1'
            or actual.get('wireGrammarAdmitted')is not False or actual.get('referenceLaneOffsets')!=[0,8]
            or setter['program'].get('barrierReferenceLaneOffset')!=0
            or child.get('nativeInputs')!=pins or child.get('schema')!='endfield.story-lang-key-value-source.v1'
            or(child.get('typeName'),child.get('managedBytes'),child.get('resultAbi'),child.get('referenceLaneOffsets'))!=(TYPE,16,'hidden-local',[0,8])
            or child.get('actualSourceProved')is not True or child.get('wireGrammarAdmitted')is not False
            or(cap['readerMethodDefinition'],cap['sourceTargetRva'])!=(usage['methodSpec'][0],read['sourceTargetRva'])
            or(child.get('readerMethodDefinition'),child.get('sourceTargetRva'))!=(cap['readerMethodDefinition'],cap['sourceTargetRva'])):
        raise ValueError('currentLangKey.exact-two-reference-managed-parent')
    return dict(fieldName=read['fieldName'],typeName=TYPE,capability=CAP,
        readerMethodDefinition=cap['readerMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
        managedBytes=16,referenceLaneOffsets=[0,8],wireMemberCount=1,
        positiveWireBytes=5,nullWireBytes=1,nonserializedRawText=True,
        actualCallbackEqualsProvedChildRequired=True,completeFieldTransferAndFrameProved=True)
