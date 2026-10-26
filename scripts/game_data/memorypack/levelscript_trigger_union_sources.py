"""Exact three-route TriggerVolume union transport; concrete records separate.

The abstract wrapper has an instance slot-five union reader and no static
Deserialize. Its hot tag and two out-of-line cases require their own source
profile, rather than a guessed jump table or an ordinary-record reader.
"""
import copy
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.current_reference_union_sources import _new_child,_finish

TYPE='Beyond.Gameplay.LevelScriptTriggerVolumeData'
LABEL='storyTriggerVolumeUnion'


def program(regions,entry,symbols,*,tag,ff=False):
    if type(tag)is not int or tag not in(0,1,2)or type(ff)is not bool:
        raise ValueError(LABEL+'.literal-three-route-selection')
    g=BytesPath(regions,entry);s=symbols
    g.take('48895c2408','4889742418','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','498bd8','488bfa');g.branch('0f84',False)
    g.take('33f6','488d542438','488bcf','6689742438');g.call(s['header'])
    g.take('84c0');g.branch('0f84',ff);child=None
    if not ff:
        g.take('0fb7742438','8bc6','83fe01');g.branch('0f85',tag!=1)
        if tag!=1:
            g.take('85c0');g.branch('0f84',tag==0)
            if tag==2:g.take('83f802');g.branch('74',True,1)
        child=_new_child(g,s,'table-rsi')
    _finish(g,s,'table-rsi',ff,child['barrierReceiverPrepared']if child else False)
    return dict(selectedBytes=g.seen,initializedFlag=flag,tag=None if ff else tag,
        canonicalFF=ff,childUsage=child,headerTarget=s['header'],childTarget=None if ff else s['packable'],
        barrierTarget=s['barrier'],outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,
        sameReader=True,sameOutput=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rsi','rdi'],concreteGrammarAdmitted=False,
        condition='Initialized exact three-route union, positive output initially null, matching concrete typed callback, normal ReadPackable/header/disabled-barrier helpers and stable disjoint storage. False header is admitted only for canonical FF; reserved high markers remain refused by the caller profile.')


def _target(body,pattern,label):
    found=[]
    for at,raw in body['regions']:
        offset=raw.find(pattern)
        while offset>=0:
            site=offset+len(pattern)-1
            if raw[site:site+1]!=b'\xe8'or site+5>len(raw):raise ValueError(LABEL+'.owned-E8:'+label)
            found.append(at+site+5+int.from_bytes(raw[site+1:site+5],'little',signed=True))
            offset=raw.find(pattern,offset+1)
    if len(set(found))!=1:raise ValueError(LABEL+'.one-actual-target:'+label+':'+str(found))
    return found[0]


def derive_transport(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack import modelview_packable_sources,reference_adapter_sources
    from scripts.game_data.memorypack.current_reference_union_sources import _lineage
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers=image.memorypack_wrappers;by_name={w.name:w for w in wrappers.values()}
    wrapper,=[w for w in wrappers.values()if w.wrapped_type==TYPE]
    need('abstract-wrapper',128,md.types[wrapper.type_definition].flags&128)
    formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
    formatter,=image.named_type_definitions[formatter_name]
    method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'
        and not m.flags&16 and m.slot==5 and m.parameter_count==2 and ctx.type_name(m.return_type)=='void']
    _vtable(image,formatter.index,5,method.index,LABEL+'.actual-slot5')
    scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.void')
    for parameter,name,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
        need('nominal-instance-byref',(name,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
    entry=image.method_pointer_va(method);body=pointer.owned(image,entry)
    header=_target(body,bytes.fromhex('6689742438e8'),'header')
    barrier=_target(body,bytes.fromhex('488903488bcbe8'),'barrier')
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    need('reference-builds',(pins,pins),(core['nativeInputs'],generic['nativeInputs']))
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    actual_packable=base+core['readPackable']['entryRva']
    header_source=pointer.owned(image,header);offsets=scalar.reader_offsets(image,LABEL)
    headers={marker:enclosing_header(header_source['regions'],header,offsets,marker=marker)for marker in('short','extended','false')}
    symbols=dict(header=header,packable=actual_packable,barrier=barrier);programs=[]
    for tag in(0,1,2):
        source=program(body['regions'],entry,symbols,tag=tag)
        usage=derive_typed_usage_context(image,source['childUsage']['instruction']-base,label=LABEL+'.actualChild')
        argument,=usage['methodArguments'];child=by_name[argument]
        typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
        need('exact-reference-ReadPackable-definition',reference['packableContext']['packableDefinition'],typed['methodDefinition'])
        programs.append(dict(tag=tag,source=source,typedRequest=usage,typedArgument=typed,
            wrapperName=child.name,wrappedType=child.wrapped_type,
            originalLineage=_lineage(ctx,md,child.wrapped_type,TYPE),
            wrapperLineage=_lineage(ctx,md,child.name,wrapper.name),concreteGrammarAdmitted=False))
    need('three-distinct-concrete-children',3,len({p['wrappedType']for p in programs}))
    null=program(body['regions'],entry,symbols,tag=0,ff=True)
    pair=derive_pair(image,TYPE,wrapper.name)
    def forwarder(selected_image,selected_pair,selected_wrapper):
        need('same-operation-forwarder-image',True,selected_image is image)
        face,=selected_pair['composition']['interfaces']
        need('same-union-canonical-pair',(wrapper.name,method.index),(selected_wrapper.name,face['formatterDeserializeMethodIndex']))
        return dict(readerTargetMode='independently-proved-inline',ownedWindows=body['windows'],programs=programs,canonicalFF=null)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
    getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper)
    need('abstract-original-holder',(TYPE,16),(holder['declaredType'],holder['offset']))
    face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
    conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
    for selected in programs:
        child=by_name[selected['wrapperName']];child_holder=_wrapper_holder(ctx,image,child)
        need('inherited-own-original-holder',(TYPE,16),(child_holder['declaredType'],child_holder['offset']))
        td=md.types[child.type_definition];start=section.offset+td.interface_offsets_start*8
        faces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
        matched=[(ordinal,offset)for ordinal,(index,offset)in enumerate(faces)if index==face['interfaceTypeIndex']]
        need('one-inherited-base-interface:'+child.name,1,len(matched));ordinal,offset=matched[0]
        _vtable(image,child.type_definition,offset,getter.index,LABEL+'.inherited-base-getter')
        converted=reference_adapter_sources.conversion(conversion['regions'],conversion_entry,
            base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
        joins.append(dict(wrapperName=child.name,interfaceOrdinal=ordinal,interfaceOffset=offset,
            interfaceTypeIndex=face['interfaceTypeIndex'],baseGetValueMethod=getter.index,holder=child_holder,conversion=converted))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.levelscript-trigger-union-transport.v1',
        status='validated-conditional-trigger-union-transport',nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,
        slot5Method=[method.index,formatter_name,'Deserialize',entry-base],ownedWindows=body['windows'],
        sourceRegions=[dict(start=at,hex=data.hex())for at,data in body['regions']],
        symbolRvas={k:v-base for k,v in symbols.items()},programs=programs,canonicalFF=null,
        headerWindows=header_source['windows'],headerPrograms=headers,referencePackable=reference,
        barrier=_barrier(image,barrier),pair=pair,adapter=adapter,baseHolder=holder,baseGetValue=getter_proof,
        inheritedConversions=joins,admittedRouteTags=[0,1,2],nullUnionMarker=255,
        reservedMarkersRefused=[251,252,253,254],canonicalTagEncoding=True,
        concreteChildGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own three-case compare-chain instance slot5, canonical short/extended/false union header, exact typed concrete wrappers, matching abstract pair/getter and inherited Original conversion.',
            conditional='Initialized metadata, positive union output initially null, actual matching concrete and canonical callbacks, normal helpers/disabled collector and disjoint stable storage.',
            unresolved=['concrete child grammar and root dictionary','live provider/callback selection','runtime trigger evaluation or whole Narrative EOF']))))
