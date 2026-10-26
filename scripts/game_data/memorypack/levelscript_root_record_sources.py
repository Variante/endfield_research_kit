"""Positive current Narrative root UInt32 dictionaries and exact child joins.

Enemy30 and Lock2/SingleLock18 remain their independently owned finite
profiles. Their LevelData list evidence never supplies a Narrative dictionary
or parent field. This module derives each actual root request separately.
"""
import copy
import json

from scripts.game_data.memorypack import leveldata_enemy_sources as enemy,leveldata_lock_sources as lock
from scripts.game_data.memorypack import uint_reference_dictionary_sources as dictionary

ROOT='Beyond.Gameplay.LevelScriptData'
FIELDS={'enemies':enemy.TYPE,'interactiveLocks':lock.TYPE}
LIMIT=4096


def bind_parent(field,read,component,*,image_base):
    name=field.get('name');typename=FIELDS.get(name)
    declared='System.Collections.Generic.Dictionary`2<uint,'+typename+'>'if typename else None
    usage=component.get('typedRequest',{});cap=component.get('capability',{});spec=usage.get('methodSpec')
    if (typename is None or field.get('typeName')!=declared or read.get('fieldName')!=name
            or type(field.get('offset'))is not int or read.get('storeOffset')!=field['offset']
            or read.get('sourceTarget')!=image_base+component.get('callTargetRva',-1)
            or not isinstance(read.get('typedUsage'),dict)
            or read['typedUsage'].get('instruction')!=image_base+usage.get('instructionRva',-1)
            or(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))!=
                (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[declared])
            or component.get('typeName')!=declared or cap.get('typeName')!=declared or cap.get('valueType')!=typename
            or not isinstance(spec,(tuple,list))or len(spec)!=3
            or type(cap.get('packableReaderMethodDefinition'))is not int
            or cap['packableReaderMethodDefinition']!=spec[0]
            or cap.get('packableReaderTargetRva')!=component['callTargetRva']):
        raise ValueError('currentLevelScriptRootRecords.actual-parent-context-source-store:'+str(name))
    return dict(ownerType=ROOT,fieldName=name,typeName=declared,elementType=typename,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
        fieldOffset=field['offset'],initiallyNullOutputRequired=True,
        actualCallbackEqualsCanonicalRequired=True,actualValueCallbackEqualsProvedChildRequired=True)


def require_record(record,*,type_name,pins):
    source=record.get('source',{});adapter=record.get('adapter',{});pair=record.get('pair',{})
    lifecycle=source.get('lifecycle',{});getter=lifecycle.get('GetValue',{})
    interfaces=pair.get('composition',{}).get('interfaces',[])
    if (source.get('nativeInputs')!=pins or source.get('wrappedType')!=type_name
            or source.get('completeSelectedCallerAdmitted')is not True
            or adapter.get('nativeInputs')!=pins or adapter.get('typeName')!=type_name
            or adapter.get('wrapperName')!=source.get('wrapperName')or adapter.get('pair')!=pair
            or adapter.get('getterMethod')!=getter.get('method')or len(interfaces)!=1
            or interfaces[0].get('formatterDeserializeMethodIndex')!=lifecycle.get('concreteFormatter',{}).get('method',[None])[0]
            or adapter.get('getterReturnedReferenceSemanticsProved')is not False):
        raise ValueError('currentLevelScriptRootRecords.same-fresh-own-record-adapter:'+type_name)
    # The domain source independently proves the whole original getter. The
    # adapter intentionally does not claim those semantics on its own.
    if not(getter.get('program',{}).get('fullReferenceOutput')is True
            or getter.get('ownedCoherentGetter',{}).get('coherentNonNullSamePointerReturn')is True):
        raise ValueError('currentLevelScriptRootRecords.whole-original-reference:'+type_name)


def derive(image,pins,owners,host):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.codecs.leveldata import current_enemy,current_locks
    from scripts.game_data.memorypack.leveldata_lang_key_components import CAP as LANG_CAP
    _publication_gate(image,pins)
    if owners.get('nativeInputs')!=pins or host.get('nativeInputs')!=pins:
        raise ValueError('currentLevelScriptRootRecords.same-current-operation')
    root=owners['owners'][ROOT];sources={};caps={};proofs=host['proofs']
    enemies=proofs['enemies'];locks=proofs['locks']
    if enemies['nativeInputs']!=pins or locks['nativeInputs']!=pins:
        raise ValueError('currentLevelScriptRootRecords.same-native-child-operation')
    current_enemy.validate(enemies['capability'])
    single=locks['capabilities'][lock.SINGLE];language=locks['langKey']['capabilities'][LANG_CAP]
    current_locks.validate(locks['capabilities'][lock.TYPE],single,language)
    require_record(enemies['record'],type_name=enemy.TYPE,pins=pins)
    require_record(locks['records'][lock.TYPE],type_name=lock.TYPE,pins=pins)
    require_record(locks['records'][lock.SINGLE],type_name=lock.SINGLE,pins=pins)
    for field,read in zip(root['fields'],root['program']['orderedReads'],strict=True):
        name=field['name']
        if name not in FIELDS:continue
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-image.pe.image_base,
            label='currentLevelScriptRootRecords.actualRoot')
        collection=dictionary.derive(image,pins,typed_request=usage,call_target=read['sourceTarget'],
            value_type=FIELDS[name],count_limit=LIMIT)
        parent=bind_parent(field,read,collection,image_base=image.pe.image_base)
        records={enemy.TYPE:enemies['capability']}if name=='enemies'else{
            lock.TYPE:locks['capabilities'][lock.TYPE],lock.SINGLE:single,lock.LANG:language}
        caps[name]=dict(typeName=field['typeName'],fieldName=name,elementType=FIELDS[name],
            dictionary=collection['capability'],records=copy.deepcopy(records),parentBinding=parent,
            profileAdmitted=True,finiteChildProfileAdmitted=True,wholeGrammarAdmitted=False,
            initiallyNullOutputRequired=True,actualCallbackEqualsCanonicalRequired=True,
            actualValueCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
            parentFieldAdmitted=False,wholeOwnerAdmitted=False)
        sources[name]=dict(field=field,source=read,typedRequest=usage,collection=collection,parentBinding=parent)
    if set(caps)!=set(FIELDS):raise ValueError('currentLevelScriptRootRecords.two-exact-root-fields')
    from scripts.game_data.codecs.levelscript.current_root_records import validate
    for name,cap in caps.items():validate(name,cap)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.levelscript-current-root-records.v1',
        status='validated-conditional-current-root-records',nativeInputs=pins,capabilities=caps,
        parents=sources,childOwnerJoins=dict(enemies=enemies['record']['adapter'],
            interactiveLocks={name:locks['records'][name]['adapter']for name in(lock.TYPE,lock.SINGLE)}),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own root UInt32/CLASS dictionaries, actual closed ReadPackable requests/targets/stores, bounded unsigned key/reference loop and independently complete Enemy30 or Lock2/SingleLock18 ordinary children.',
            conditional='Initially null dictionary/list outputs, actual matching key/value/source callbacks and coherent typed constructor/Add/provider helpers, compatible existing child wrappers and disabled collector. Child finite resource/float and Enemy object-dictionary restrictions remain intact.',
            unresolved='Live callback/provider selection, any missing closed dictionary pointer equivalence, positive arbitrary Enemy object values and whole Narrative physical EOF/public source receipt.'))))
