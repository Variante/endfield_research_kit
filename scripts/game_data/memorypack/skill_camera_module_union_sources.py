"""Current CameraControlModuleConfig short-tag caller and base conversions.

The thirteen literal compare-chain routes and canonical FF own the complete
initialized normal caller frame. Each positive route starts with a null output,
uses its actual closed ReadPackable wrapper MethodInfo and passes the returned
reference unchanged to the output/barrier. The ordinary abstract-base adapter,
holder16 getter and every concrete inherited-interface conversion are separate
typed joins. Concrete factories/getters/wire grammars, existing-output paths,
reserved markers, live provider selection and enclosing list/owner/EOF remain
unresolved. Stable initialized contexts, compatible helpers, disabled collector
and disjoint valid reader/output storage are conditions, not runtime receipts.
"""
import copy
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.current_reference_union_sources import _finish,_lineage,_new_child
from scripts.game_data.memorypack.skill_selector_union_sources import branch

SCHEMA='endfield.skill-camera-module-union-sources.v1'
TYPE='Beyond.Gameplay.View.CameraControlModuleConfig'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_CameraControlModuleConfigForMemoryPack'
LABEL='skillCameraModuleUnionSources'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:300]+' actual='+str(actual)[:300])


def program(regions,entry,s,*,tag=0,ff=False):
    need('literal-tag',True,type(tag)is int and 0<=tag<13)
    need('literal-FF',bool,type(ff))
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4883ec20','33f6','498bd8')
    flag=g.relative('403835');g.take('488bfa');g.branch('0f85',True)
    g.take('488d542438','6689742438','488bcf');g.call(s['header'])
    g.take('84c0');g.branch('0f84',ff)
    child=None
    if not ff:
        g.take('0fb74c2438','83f906');g.branch('0f87',tag>6)
        if tag>6:
            g.take('83e907');g.branch('0f84',tag==7)
            if tag>7:
                for candidate in range(8,12):
                    g.take('83e901');branch(g,4,tag==candidate)
                    if tag==candidate:break
                if tag==12:g.take('83f901');g.branch('74',True,1)
        else:
            g.branch('0f84',tag==6)
            if tag<6:
                g.take('85c9');g.branch('0f84',tag==0)
                if tag>0:
                    for candidate in range(1,5):
                        g.take('83e901');branch(g,4,tag==candidate)
                        if tag==candidate:break
                    if tag==5:g.take('83f901');g.branch('0f85',False)
        child=_new_child(g,s,'table-rsi')
    _finish(g,s,'table-rsi',ff,child['barrierReceiverPrepared']if child else False)
    return dict(selectedBytes=g.seen,tag=None if ff else tag,canonicalFF=ff,initializedFlag=flag,
        childUsage=child,headerTarget=s['header'],childTarget=None if ff else s['packable'],barrierTarget=s['barrier'],
        outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,sameReader=True,sameOutput=True,
        normalReturn=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],
        concreteGrammarAdmitted=False)


def _call_after(body,prefix):
    pattern=bytes.fromhex(prefix+'e8');found=[]
    for at,raw in body['regions']:
        offset=raw.find(pattern)
        while offset>=0:
            site=at+offset+len(pattern)-1
            found.append(site+5+int.from_bytes(raw[offset+len(pattern):offset+len(pattern)+4],'little',signed=True))
            offset=raw.find(pattern,offset+1)
    need('one-owned-call-after:'+prefix,1,len(found));return found[0]


def _derive(image,pins,*,with_adapter):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import modelview_packable_sources,pointer_param as pointer,reference_adapter_sources as adapters,scalar_param_native as scalar
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    reference=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    collector=json.loads((CONTRACTS_DIR/'model_view_state_controller_native.json').read_bytes())
    for key,declaration in(('packable',core),('reference',reference),('collector',collector)):
        need('selected-dependency:'+key,pins,declaration['nativeInputs'])
    routes=copy.deepcopy(reference['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    helper=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    wrappers={w.name:w for w in image.memorypack_wrappers.values()};wrapper=wrappers[WRAPPER]
    need('nominal-owned-abstract-wrapper',(TYPE,True),(wrapper.wrapped_type,wrapper.abstract))
    fname=WRAPPER+'+'+WRAPPER.rsplit('.',1)[-1]+'Formatter';formatter,=image.named_type_definitions[fname]
    method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'
        and not m.flags&16 and m.slot==5 and m.parameter_count==2 and ctx.type_name(m.return_type)=='void']
    _vtable(image,formatter.index,5,method.index,LABEL+'.slot5')
    scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.void')
    for parameter,name,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',WRAPPER),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
        need('slot5-owned-byrefs',(name,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
    entry=image.method_pointer_va(method);body=pointer.owned(image,entry)
    header=_call_after(body,'488d5424386689742438488bcf')
    packable=base+core['readPackable']['entryRva']
    barrier=base+collector['collector']['entryRva'];barrier_proof=_barrier(image,barrier)
    symbols=dict(header=header,packable=packable,barrier=barrier)
    header_body=pointer.owned(image,header);offsets=scalar.reader_offsets(image,LABEL)
    headers={marker:enclosing_header(header_body['regions'],header,offsets,marker=marker)for marker in('short','false')}
    selected=[]
    for tag in range(13):
        source=program(body['regions'],entry,symbols,tag=tag)
        usage=derive_typed_usage_context(image,source['childUsage']['instruction']-base,label=LABEL+'.child')
        need('one-closed-child-type',1,len(usage.get('methodArguments',[])))
        child=wrappers[usage['methodArguments'][0]]
        need('concrete-child-wrapper',False,child.abstract)
        typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
        need('actual-packable-method-definition',helper['packableContext']['packableDefinition'],typed['methodDefinition'])
        selected.append(dict(tag=tag,wrapperName=child.name,wrappedType=child.wrapped_type,source=source,typedRequest=usage,typedArgument=typed,
            originalLineage=_lineage(ctx,md,child.wrapped_type,TYPE),wrapperLineage=_lineage(ctx,md,child.name,WRAPPER),concreteGrammarAdmitted=False))
    need('thirteen-distinct-closed-child-wrappers',13,len({r['wrapperName']for r in selected}))
    null=program(body['regions'],entry,symbols,ff=True)
    if not with_adapter:
        _publication_gate(image,pins)
        return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-camera-module-callers-only',nativeInputs=pins,
            typeName=TYPE,wrapperName=WRAPPER,capabilities={},programs=selected,canonicalFF=null,
            proof=dict(method=[method.index,fname,'Deserialize',entry-base],ownedWindows=body['windows'],headerWindows=header_body['windows'],
                headerPrograms=headers,referencePackable=helper,barrier=barrier_proof),
            baseAdapterAdmitted=False,concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False,wholeOwnerAdmitted=False,
            evidenceBoundary=dict(exact='Complete selected thirteen-route compare/subtract callers and FF frame with actual typed child requests.',
                conditional=__doc__,structuralOnly='Stored camera module configuration.',
                unresolved=['ordinary base adapter/holder/interface conversion joins','thirteen concrete child grammars/factories/getters',
                    'existing-output alternatives','reserved markers','runtime provider selection','list/parent/EOF']))))
    pair=derive_pair(image,TYPE,WRAPPER)
    def prove_forwarder(selected_image,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces']
        need('owned-base-formatter',(WRAPPER,method.index),(selected_wrapper.name,face['formatterDeserializeMethodIndex']))
        return dict(ownedWindows=body['windows'],slot5Method=method.index,programs=selected,canonicalFF=null)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=prove_forwarder)
    getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
    getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper)
    need('own-abstract-base-holder',(TYPE,16),(holder['declaredType'],holder['offset']))
    face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
    conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
    for selected_child in selected:
        child=wrappers[selected_child['wrapperName']];td=md.types[child.type_definition];child_holder=_wrapper_holder(ctx,image,child)
        need('same-inherited-base-holder',(TYPE,16),(child_holder['declaredType'],child_holder['offset']))
        start=section.offset+td.interface_offsets_start*8
        interfaces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
        found=[(ordinal,offset)for ordinal,(index,offset)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
        need('one-derived-base-interface',1,len(found));ordinal,offset=found[0]
        _vtable(image,child.type_definition,offset,getter.index,LABEL+'.base-getter')
        converted=adapters.conversion(conversion['regions'],conversion_entry,base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
        joins.append(dict(wrapperName=child.name,interfaceOrdinal=ordinal,interfaceOffset=offset,interfaceTypeIndex=face['interfaceTypeIndex'],
            baseGetValueMethod=getter.index,holder=child_holder,conversion=converted))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-camera-module-source',nativeInputs=pins,capabilities={},
        typeName=TYPE,wrapperName=WRAPPER,programs=selected,canonicalFF=null,
        proof=dict(method=[method.index,fname,'Deserialize',entry-base],ownedWindows=body['windows'],headerWindows=header_body['windows'],headerPrograms=headers,
            referencePackable=helper,barrier=barrier_proof,pair=pair,adapter=adapter,baseHolder=holder,baseGetValue=getter_proof,derivedOriginalConversions=joins),
        baseGetterSemanticsAdmitted=True,concreteGetterSemanticsAdmitted=False,concreteFactorySemanticsAdmitted=False,
        concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete selected thirteen-route compare/subtract callers and FF frame, actual typed child requests, base ordinary adapter/holder/interface conversions.',
            conditional=__doc__,structuralOnly='Stored camera module configuration.',
            unresolved=['thirteen concrete child grammars/factories/getters','existing-output alternatives','reserved markers','runtime provider selection','list/parent/EOF']))))


def derive_caller(image,pins):
    """Fresh typed thirteen-route/FF source only; no ordinary adapter admission."""
    return _derive(image,pins,with_adapter=False)


def derive_source(image,pins):
    """Fresh caller plus complete ordinary base adapter and conversions."""
    return _derive(image,pins,with_adapter=True)
