"""Named LockCamera inherited properties on two exact closed reference bases.

Compiled accessor effects establish destination offsets; open generic field
offsets remain unused. The actual closed parent carrier and argument own each
declaration. This adapter supplies no constructor, field-layout or wire claim.
"""
from scripts.game_data.memorypack.lock_camera_base_sources import DEFINITION,DERIVED_TYPES

BASE_WRAPPERS=tuple('Beyond.MemoryPack.Beyond_Gameplay_Core_LockCameraAimBaseAction_Beyond_Gameplay_Core_'+
    suffix+'_'+suffix+'Data__LockCameraAimBaseActionDataForMemoryPack'
    for suffix in ('LockCameraAimAction','LockCameraMultiAimAction'))
LABEL='lockCameraMemberSource'


def need(key,value):
    if not value:raise ValueError(LABEL+'.'+key)


def original_ancestry(ctx,type_name):
    """Exact closed parent edge, followed by its ordinary definition ancestors."""
    from scripts.game_data.il2cpp.reference_layouts import closed_generic_reference_pointer_extent
    need('finite-owned-derived-type',type_name in DERIVED_TYPES)
    td=ctx.index.types[type_name]
    closed=closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(td.parent_index))
    need('same-own-closed-reference-edge',closed['definitionTypeIndex']==ctx.index.types[DEFINITION].index
        and closed['argumentTypes']==[type_name]and closed['bytes']==8 and not ctx.is_value_type(type_name))
    result=[type_name,closed['type']];name=ctx.parent(DEFINITION)
    while name not in ('','object','System.Object'):
        need('bounded-ordinary-definition-ancestor',name not in result and len(result)<16 and not ctx.is_value_type(name))
        result.append(name);name=ctx.parent(name)
    need('same-declared-Ability-ancestor',len(result)>2 and result[2]=='Beyond.Gameplay.Core.AbilityAction+AbilityActionData')
    return result


def _setter_from_fresh_effects(effects,member,pins):
    need('fresh-closed-accessor-owner',effects.get('schema')=='endfield.lock-camera-closed-accessor-effects.v1'
        and effects.get('status')=='validated-conditional-closed-accessor-effects'and effects.get('nativeInputs')==pins
        and effects.get('typeName')in DERIVED_TYPES and effects.get('baseWrapperName')==member.declaring_wrapper
        and effects.get('all36NamedAccessorEffectsProved')is True
        and effects.get('openGenericFieldOffsetsUsed')is False and effects.get('nativeClosedMetadataFieldOffsetsAdmitted')is False)
    matches=[a for a in effects['accessors']if a['member']==member.row()]
    need('same-exact-current-declared-property',len(matches)==1)
    actual=matches[0];getter=effects['getter']
    need('same-complete-method-effect',actual['method'][0]==member.method_index
        and actual['method'][1]==member.declaring_wrapper and actual['declaredField']['name']==member.name
        and actual['declaredField']['typeName']==member.declared_type
        and actual['declaredField']['ownerDefinition']==DEFINITION and actual['openGenericFieldOffsetUsed']is False)
    coherent=dict(method=getter['method'],family=getter['family'],codeWindows=getter['codeWindows'],
        program=getter['warmProgram'],baseHolder=effects['baseHolder'],typedCache=effects['closedCacheHolder'],
        coherentNonNullSamePointerReturn=True,refreshAdmitted=True,compatibleRefresh=getter['compatibleRefresh'],
        closedReferenceCarrier=effects['holderCarrier'],closedParent=effects['closedParent'],
        nativeClosedMetadataFieldOffsetsAdmitted=False)
    result=dict(method=actual['method'],member=member.row(),
        targetField=effects['closedParent']['type']+'::'+member.name,
        fieldOffset=actual['actualEffectOffset'],parameterTypeRecordHex=actual['parameterTypeRecordHex'],
        storedBytes=actual['storedBytes'],sourceFamily=actual['family'],codeWindows=actual['codeWindows'],
        profile='cached-getter-setter',program=actual['program'],getter=coherent,
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False,
        closedFieldDeclaration=actual['declaredField'],closedReferenceCarrier=effects['closedParent'],
        fieldOffsetSource='complete actual named compiled property effect',
        nativeClosedMetadataFieldOffsetsAdmitted=False,openGenericFieldOffsetUsed=False)
    if actual.get('nominalValueLayout')is not None:result['nominalValueLayout']=actual['nominalValueLayout']
    return result


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.lock_camera_base_sources import derive_accessors
    need('finite-current-closed-declaring-wrapper',member.declaring_wrapper in BASE_WRAPPERS)
    ctx=NativeReferenceContext(image)
    selected=[w for w in wrappers.values()if w.wrapped_type in DERIVED_TYPES and ctx.parent(w.name)==member.declaring_wrapper]
    need('one-actual-derived-wrapper-for-closed-base',len(selected)==1)
    wrapper=selected[0];key=('lock-camera-closed-accessor-effects',member.declaring_wrapper)
    if key not in getter_cache:getter_cache[key]=derive_accessors(image,pins,type_name=wrapper.wrapped_type)
    effects=getter_cache[key]
    need('same-selected-disabled-reference-barrier',effects['disabledCollector']['actualEntryRva']==barrier)
    return _setter_from_fresh_effects(effects,member,pins)
