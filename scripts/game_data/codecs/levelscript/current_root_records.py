"""Current positive root dictionaries; no historical child codec fallback."""
import struct

from scripts.game_data.memorypack import levelscript_root_record_sources as source
from scripts.game_data.memorypack import uint_reference_dictionary_sources as dictionary
from scripts.game_data.codecs.leveldata import current_enemy,current_locks
from scripts.game_data.codecs.leveldata.current_owner import Reader


def validate(field,cap):
    typename=source.FIELDS.get(field);declared='System.Collections.Generic.Dictionary`2<uint,'+typename+'>'if typename else None
    if (not isinstance(cap,dict)or typename is None or(cap.get('fieldName'),cap.get('typeName'),cap.get('elementType'))!=(field,declared,typename)
            or any(cap.get(k)is not True for k in('profileAdmitted','finiteChildProfileAdmitted','initiallyNullOutputRequired',
                'actualCallbackEqualsCanonicalRequired','actualValueCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))):
        raise ValueError('currentRootRecords.exact-finite-current-root:'+str(field))
    selected=cap.get('dictionary',{});parent=cap.get('parentBinding',{})
    expected=dictionary.capability(type_name=declared,value_type=typename,count_limit=source.LIMIT,
        reader_definition=selected.get('packableReaderMethodDefinition'),reader_target=selected.get('packableReaderTargetRva'),
        closed_pointer_equivalence=selected.get('closedPointerEquivalenceProved'))
    if selected!=expected:raise ValueError('currentRootRecords.exact-owned-UInt32-source')
    wanted=dict(ownerType=source.ROOT,fieldName=field,typeName=declared,elementType=typename,
        readerMethodDefinition=selected['packableReaderMethodDefinition'],sourceTargetRva=selected['packableReaderTargetRva'],
        fieldOffset=parent.get('fieldOffset'),initiallyNullOutputRequired=True,
        actualCallbackEqualsCanonicalRequired=True,actualValueCallbackEqualsProvedChildRequired=True)
    if parent!=wanted or type(parent.get('fieldOffset'))is not int or not 16<=parent['fieldOffset']<4096:
        raise ValueError('currentRootRecords.exact-own-root-parent')
    records=cap.get('records',{})
    if field=='enemies':
        if set(records)!={source.enemy.TYPE}:raise ValueError('currentRootRecords.exact-Enemy-child-set')
        current_enemy.validate(records[source.enemy.TYPE])
    else:
        if set(records)!={source.lock.TYPE,source.lock.SINGLE,source.lock.LANG}:raise ValueError('currentRootRecords.exact-Lock-child-set')
        current_locks.validate(records[source.lock.TYPE],records[source.lock.SINGLE],records[source.lock.LANG])


def conditional_sources(field,cap):
    validate(field,cap);selected=cap['dictionary']
    rows=[dict(typeName=cap['typeName'],countLimit=selected['countLimit'],sourceWitnessClassArguments=['uint','object'],
        initiallyNullOutputRequired=True,actualCallbackEqualsCanonicalRequired=True,
        actualKeyCallbackEqualsProvedUInt32Required=True,actualValueCallbackEqualsProvedChildRequired=True,
        typedConstructorAndHelperCompatibilityRequired=True,closedPointerEquivalenceProved=selected['closedPointerEquivalenceProved'],
        actualCallbackSelectionObserved=False,providerFactorySelectionObserved=False)]
    if field=='enemies':
        child=cap['records'][source.enemy.TYPE];opaque=child['childCapabilities'][source.enemy.dictionary.CAP]
        rows.append(dict(typeName=opaque['typeName'],allowedCounts=[-1,0],sourceWitnessClassArguments=['object','object'],
            actualCallbackEqualsCanonicalRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
            closedPointerEquivalenceProved=False,positiveObjectValuesAdmitted=False,runtimeEnemyActivationProved=False))
    else:
        rows.append(dict(typeName=source.lock.LANG,managedBytes=16,referenceLaneOffsets=[0,8],rawTextSerialized=False,
            actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
    return rows


def decode(data,offset,field,*,strings,capability):
    validate(field,capability)
    if type(offset)is not int or not 0<=offset<=len(data)-4:raise ValueError('currentRootRecords.truncated-count:'+field)
    count=struct.unpack_from('<i',data,offset)[0]
    if not -1<=count<=source.LIMIT:raise ValueError('currentRootRecords.count-domain:'+field+':'+str(count))
    reader=Reader(data,strings,dict(records=capability['records'],collections={}));reader.offset=offset+4
    reader.need(max(count,0)*5,field+'.minimum-entries');rows=[];seen=set()
    for index in range(max(count,0)):
        key=reader.number('<I',field+'['+str(index)+'].key')
        if key in seen:raise ValueError('currentRootRecords.duplicate-UInt32-key:'+field+':'+str(key))
        seen.add(key);path=field+'['+str(key)+']'
        if field=='enemies':value=current_enemy.read(reader,path,capability['records'][source.enemy.TYPE])
        else:value=current_locks.read(reader,path,capability['records'][source.lock.TYPE],
            capability['records'][source.lock.SINGLE],capability['records'][source.lock.LANG])
        rows.append(dict(key=key,value=value))
    return dict(startOffset=offset,endOffset=reader.offset,status='null'if count==-1 else'present',
        count=None if count==-1 else count,entries=None if count==-1 else rows,parseStatus='decoded',
        conditionalChildSources=conditional_sources(field,capability)),reader.offset
