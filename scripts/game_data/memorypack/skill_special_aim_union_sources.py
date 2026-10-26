"""Own initialized SpecialAim union caller, before concrete sector grammar.

The actual instance formatter reads a union header and admits only short tag
zero or canonical FF. Positive output starts null: the reference-result
ReadPackable<SpecialAimEditSector wrapper> returns a whole reference, which is
stored and barriered before the original frame returns. The existing-output
byref overload is a different path and is not selected. Metadata's inherited
forwardType field and member count do not supply a record grammar. Matching
ready contexts/callbacks, normal disjoint helper effects and disabled collector
remain conditions; concrete children, lists, enclosing actions and execution
are separate obligations.
"""
import copy
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.EnableSpecialAim+SpecialAimShapeEdit'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_EnableSpecialAim_SpecialAimShapeEditForMemoryPack'
CHILD='Beyond.Gameplay.Core.EnableSpecialAim+SpecialAimEditSector'
CHILD_WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_EnableSpecialAim_SpecialAimEditSectorForMemoryPack'


def caller_program(regions,entry,s,*,ff=False):
    """Exact null-output reference-result path; no existing-output alias."""
    if type(ff)is not bool:raise ValueError('specialAimUnion.literal-FF-mode')
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','498bd8','488bf2');g.branch('0f84',False)
    g.take('33ff','488d542438','488bce','66897c2438');g.call(s['header'])
    g.take('84c0');g.branch('0f84',ff);usage=None
    if ff:
        g.take('48893b');g.jump('eb',1)
    else:
        g.take('0fb77c2438','6685ff');g.branch('0f85',False)
        g.take('488b0b','4885c9');g.branch('74',True,1)
        site=g.at;cell=g.relative('488b15');usage=dict(instruction=site,cell=cell)
        g.take('488bce');g.call(s['packable']);g.take('488903')
    g.take('488bcb');g.call(s['barrier']);g.jump('eb',1)
    g.take('488b5c2430','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,canonicalFF=ff,tag=None if ff else 0,
        headerTarget=s['header'],childUsage=usage,childTarget=None if ff else s['packable'],
        barrierTarget=s['barrier'],outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,
        positiveResultBytes=0 if ff else 8,sourceReaderPreserved=True,sameOutput=True,
        normalReturn=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],
        existingOutputByrefPathAdmitted=False,concreteGrammarAdmitted=False)


def derive(image,pins):
    """Reprove exact own formatter, reference clone and inherited conversion."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack import modelview_packable_sources,reference_adapter_sources as adapters
    from scripts.game_data.memorypack.current_reference_union_sources import _header_target,_lineage
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers={w.name:w for w in image.memorypack_wrappers.values()};wrapper=wrappers[WRAPPER];child=wrappers[CHILD_WRAPPER]
    need('SpecialAim-own-nominals',(TYPE,CHILD),(wrapper.wrapped_type,child.wrapped_type))
    formatter_name=WRAPPER+'+'+WRAPPER.rsplit('.',1)[-1]+'Formatter'
    formatter,=image.named_type_definitions[formatter_name]
    fm,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'
        and not m.flags&16 and m.slot==5 and m.parameter_count==2 and ctx.type_name(m.return_type)=='void']
    entry=image.method_pointer_va(fm);body=pointer.owned(image,entry)
    _vtable(image,formatter.index,5,fm.index,'specialAimUnion.slot5')
    scalar.ordinary(image,ctx.type_pointer(fm.return_type),1,'specialAimUnion.void')
    for parameter,name,kind in zip(md.parameters_for(fm),('MemoryPack.MemoryPackReader',WRAPPER),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
        need('SpecialAim-instance-slot5-byrefs',(name,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    model=json.loads((CONTRACTS_DIR/'model_view_state_controller_native.json').read_bytes())
    for name,fact in(('packable',core),('reference',generic),('collector',model)):
        need('SpecialAim-'+name+'-declaration-build',pins,fact['nativeInputs'])
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    packable=base+core['readPackable']['entryRva'];barrier=base+model['collector']['entryRva']
    barrier_proof=_barrier(image,barrier);header=_header_target(body,'pair-edi');hs=pointer.owned(image,header)
    offsets=scalar.reader_offsets(image,'specialAimUnion')
    headers={marker:enclosing_header(hs['regions'],header,offsets,marker=marker)for marker in('short','false')}
    symbols=dict(header=header,packable=packable,barrier=barrier)
    positive=caller_program(body['regions'],entry,symbols);null=caller_program(body['regions'],entry,symbols,ff=True)
    usage=derive_typed_usage_context(image,positive['childUsage']['instruction']-base,label='specialAimUnion.child')
    typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=CHILD_WRAPPER,kind=18,reference=True)
    need('SpecialAim-actual-reference-result-definition',reference['packableContext']['packableDefinition'],typed['methodDefinition'])
    original_lineage=_lineage(ctx,md,CHILD,TYPE);wrapper_lineage=_lineage(ctx,md,CHILD_WRAPPER,WRAPPER)
    pair=derive_pair(image,TYPE,WRAPPER)
    def forwarder(selected_image,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces']
        need('SpecialAim-selected-own-instance-formatter',(WRAPPER,fm.index),(selected_wrapper.name,face['formatterDeserializeMethodIndex']))
        return dict(ownedWindows=body['windows'],slot5Method=fm.index,programs=[positive],canonicalFF=null)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
    getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3'])
    holder=_wrapper_holder(ctx,image,wrapper);child_holder=_wrapper_holder(ctx,image,child)
    need('SpecialAim-own-base-holder',(TYPE,16),(holder['declaredType'],holder['offset']))
    need('SpecialAim-derived-inherited-holder',(TYPE,16),(child_holder['declaredType'],child_holder['offset']))
    need('SpecialAim-abstract-base-wrapper',128,md.types[wrapper.type_definition].flags&128)
    face,=pair['composition']['interfaces'];td=md.types[child.type_definition];section=md.sections['interfaceOffsets']
    start=section.offset+td.interface_offsets_start*8
    interfaces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
    found=[(ordinal,offset)for ordinal,(index,offset)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
    need('SpecialAim-one-derived-base-interface',1,len(found));ordinal,offset=found[0]
    _vtable(image,child.type_definition,offset,getter.index,'specialAimUnion.baseGetter')
    conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
    converted=adapters.conversion(conversion['regions'],conversion_entry,
        base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-special-aim-union-sources.v1',
        status='validated-conditional-special-aim-union-caller',nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,
        childTypeName=CHILD,childWrapperName=CHILD_WRAPPER,slot5Method=[fm.index,formatter_name,'Deserialize',entry-base],
        proof=dict(ownedWindows=body['windows'],positive=positive,canonicalFF=null,headerWindows=hs['windows'],
            headerPrograms=headers,typedRequest=usage,typedArgument=typed,referencePackable=reference,barrier=barrier_proof,
            originalLineage=original_lineage,wrapperLineage=wrapper_lineage,pair=pair,adapter=adapter,
            baseHolder=holder,baseGetValue=getter_proof,derivedHolder=child_holder,
            derivedOriginalConversion=dict(interfaceOrdinal=ordinal,interfaceOffset=offset,program=converted)),
        baseGetterSemanticsAdmitted=True,concreteGetterSemanticsAdmitted=False,concreteFactorySemanticsAdmitted=False,
        concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own initialized tag0/FF union caller, actual closed reference-result ReadPackable, whole returned reference store/barrier/full frame, canonical abstract-base adapter/GetValue and inherited derived interface conversion.',
            conditional=__doc__,structuralOnly='Observed inherited metadata field count is not an ordinary record grammar.',
            unresolved=['concrete sector source/grammar/lifecycle','positive list and enclosing action/root/EOF',
                'existing-output byref overload','runtime callback/provider choice','cold/refill/error paths']))))
