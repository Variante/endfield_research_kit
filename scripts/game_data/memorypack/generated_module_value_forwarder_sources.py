"""Closed Module LangKey/EntityPtr calls, with independent nominal owners.

The actual helper supplies its own ReadValue MethodInfo and returns the same
incoming hidden output after preserving Reader/output across the nested call.
Its byte lemma is width independent. Each nominal source, runtime-storage
boundary and managed result ABI comes freshly from that value's owning gate;
no primitive/vector alias, callback choice or child wire grammar is inferred.
"""
from scripts.game_data.memorypack.generated_vector3_source import forwarder_program

TYPES=('Beyond.LangKey','Beyond.Gameplay.Core.EntityPtr')
SCHEMA='endfield.generated-module-managed-forwarder.v1'
ENTITY_MEMBERS={
    ('Beyond.Gameplay.BeaconPoleControllerData+AltarInfo','altarEntityPtr'),
    ('Beyond.Gameplay.BeaconPoleControllerData+BeaconPoleInfo','beaconPoleEntityPtr'),
    ('Beyond.Gameplay.FogNestControllerData','fogNest'),
    ('Beyond.Gameplay.MatrixRepairControllerData','matrixCenter'),
    ('Beyond.Gameplay.SpecialSightControllerData','specialSight'),
    ('Beyond.Gameplay.RaceData','finalInteractive'),
    ('Beyond.Gameplay.TianshizhuangData','proxyInteractive'),
    ('Beyond.Gameplay.RollingStoneControllerData+LauncherData','templateRollingStone'),
}


def need(check,condition):
    if not condition:raise ValueError('generatedModuleForwarder.'+check)


def owns_closed_member(parent,field,type_name):
    """Explicit regular-frame callers; this selects no source or grammar."""
    return type_name=='Beyond.Gameplay.Core.EntityPtr'and(parent,field)in ENTITY_MEMBERS


def context_shape(context,type_name):
    raw=bytes.fromhex(context.get('argumentRawHex',''))if isinstance(context,dict)else b''
    need('exact-owned-nominal-ReadValue-context',type_name in TYPES and isinstance(context,dict)
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'
        and context.get('fullTypeName')==type_name and context.get('typeKind')==17 and context.get('register')=='r8'
        and len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==context.get('typeDefinition'))


def derive(image,pins,*,source_target,type_name):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_action_sources as actions,pointer_param
    _publication_gate(image,pins);base=image.pe.image_base
    need('literal-finite-selected-entry',type_name in TYPES and type(source_target)is int and source_target>base)
    body=pointer_param.owned(image,source_target);program=forwarder_program(body['regions'],source_target)
    contexts,skipped=actions._contexts(image,body['rows']);need('one-internal-current-context',len(contexts)==1)
    context,=contexts;context_shape(context,type_name)
    need('same-actual-context-instruction',context['instructionRva']==program['contextInstructionVa']-base)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='generatedModuleForwarder.actualMethodInfo')
    need('same-actual-bytes-and-MethodSpec',usage['instructionHex']==context['instructionHex']and usage['methodSpec']==context['methodSpec'])
    if type_name=='Beyond.LangKey':
        from scripts.game_data.memorypack.leveldata_lang_key_value_sources import derive_read_value
        width=16
    else:
        from scripts.game_data.memorypack.leveldata_entity_ptr_value_sources import derive_read_value
        width=40
    nested=derive_read_value(image,pins,typed_request=usage,source_target=program['nestedTargetVa'])
    need('fresh-independent-nominal-nested-source',nested.get('nativeInputs')==pins and nested.get('typeName')==type_name
        and nested.get('managedBytes')==width and nested.get('resultAbi')=='hidden-local'
        and nested.get('actualSourceProved')is True and nested.get('wireGrammarAdmitted')is False
        and nested.get('sourceTargetRva')==program['nestedTargetVa']-base
        and nested.get('readerMethodDefinition')==context['methodSpec'][0])
    _publication_gate(image,pins)
    result=dict(nested);result.update(schema=SCHEMA,status='proved-conditional-owned-Module-ReadValue-forwarder',
        sourceTargetRva=source_target-base,sourceContextMode='owned-closed-forwarder',contextMode='owned-closed-forwarder',
        pointerAliasClaimed=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(nested['proof'],internalContext=context,forwarderProgram=program,nestedSource=nested,
            actualFamily=image.unwind_index.family(source_target-base),actualWindows=body['windows'],
            actualSourceRegions=[[at,raw.hex().upper()]for at,raw in body['regions']],skippedRuntimeCells=skipped),
        evidenceBoundary=dict(exact='Own closed helper MethodInfo load, unchanged Reader/hidden output, nested actual nominal source and complete restored return.',
            conditional=__doc__,unresolved=['live provider/context state','independent wire-child and enclosing frame/field/owner']))
    return result
