"""BodyTypeDef's own MC3/default32 grammar below any parent transfer.

MC3 stores byte-backed body enum, Int32 custom id and signed pooled-string
index, in order. FF is a one-byte default; managed padding/display name consume
no wire bytes. Complete two-slice setter copy retains both reference lanes
despite one explicit barrier, under its disabled-collector condition.
Parent lifetimes/frames, whole-owner/EOF and runtime helpers remain separate.
"""
from scripts.game_data.memorypack import body_type_value_sources as source

SCHEMA='endfield.body-type-value-components.v1'
CAPABILITY='body-type-def-value'
ORDER=[dict(fieldName='bodyType',kind='enum-byte',childCapability=None),
       dict(fieldName='CustomId',kind='int32',childCapability=None),
       dict(fieldName='CustomName',kind='pooled-string',childCapability='byte-payload')]


def compose(value,pins):
    source.need('same-complete-value-source',value.get('schema')==source.SCHEMA
        and value.get('status')=='proved-conditional-nominal-managed32-source'and value.get('nativeInputs')==pins
        and value.get('typeName')==source.TYPE and value.get('wrapperName')==source.WRAPPER
        and type(value.get('managedBytes'))is int and value['managedBytes']==32 and value.get('resultAbi')=='hidden-local'
        and value.get('wireGrammarAdmitted')is False and value.get('parentFieldAdmitted')is False and value.get('wholeOwnerAdmitted')is False
        and value.get('referenceLaneOffsets')==[8,24]and value.get('paddingByteRanges')==[[1,7],[20,4]])
    proof=value['proof'];nominal=proof['nominal'];pool=proof['pool']
    source.need('own-runtime-and-wire-fields',nominal.get('typeName')==source.TYPE and nominal.get('managedBytes')==32
        and nominal.get('boxedBytes')==48 and nominal.get('fields')==[list(r)for r in source.FIELDS]
        and nominal.get('referenceLaneOffsets')==[8,24]and nominal.get('paddingByteRanges')==[[1,7],[20,4]]
        and nominal.get('serializedFieldNames')==['bodyType','CustomId','CustomName']
        and nominal.get('runtimeOnlyFieldNames')==['m_displayName'])
    source.need('exact-source-pool',pool.get('status')=='validated'and pool.get('nativeInputs')==pins
        and pool.get('wireEncoding')=='int32-pool-index'and pool.get('emptyIndex')==-1 and pool.get('nullIndex')==-2)
    defaults=proof.get('adapterDefaults',[]);null=proof.get('defaultNull',{})
    source.need('both-complete-default32-paths',len(defaults)==2 and all(p.get('defaultZeroBytes')==32
        and p.get('completeOutputSlices')==[[0,16],[16,16]]and all(p.get(k)is True for k in
            ('sameHiddenOutput','entryRspRestored','normalReturn'))for p in defaults)
        and null.get('wireBytes')==1 and null.get('requiredPeekByte')==255 and null.get('headerCalls')==1
        and all(null.get(k)is True for k in('returnsTrue','sameReader','entryRspRestored','normalReturn')))
    roles={'body:bodyReader','value:main32','value:valueDispatcher32','value:notNull32','value:conversion32',
        'value:wrapper::.ctor','value:wrapper::CreateInstance','value:wrapper::GetValue','value:readValue32','value:readNull','value:peek'}
    source.need('own-complete-positive-and-lifecycle-programs',roles<=set(proof.get('ownedPrograms',{}))
        and len(proof.get('positivePrograms',[]))>=16)
    adapter=proof['adapter'];definition=value.get('readerMethodDefinition');target=adapter.get('dispatcherTargetRva')
    source.need('own-value-reader-identity',type(definition)is int and definition>0
        and definition==adapter.get('readerMethodDefinition')and type(target)is int and target>0)
    return dict(typeName=source.TYPE,wrapperName=source.WRAPPER,managedBytes=32,memberCount=3,orderedReads=ORDER,
        referenceLaneOffsets=[8,24],paddingByteRanges=[[1,7],[20,4]],runtimeOnlyFieldNames=['m_displayName'],
        nullable=True,nullMarker=255,nullWireBytes=1,nullReturnsDefaultValue=True,positiveWireBytes=10,wireBytes=None,
        wholeGrammarAdmitted=True,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        valueReaderMethodDefinition=definition,valueDispatcherTargetRva=target,wholeOwnerAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);value=source.derive(image,pins);cap=compose(value,pins);_publication_gate(image,pins)
    return dict(schema=SCHEMA,status='validated-conditional-body-type-value-components',nativeInputs=pins,
        capabilities={CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],proof=dict(source=value),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Own MC3 enum-byte/Int32/pool4 and FF/default32 semantics.',
            conditional=source.__doc__,unresolved=['actual parent field/local/frame','live provider and helper effects','whole owner and EOF']))
