"""Actual selected CharInteract/montage union routes below their raw owners.

These are source and inherited-reference conversions. Concrete wire grammars,
collection/dictionary callbacks and the enclosing owner remain independent.
"""
import json,struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='animationUnionSources'
FAMILIES={
    'char-animation':('Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformActionData',
        ('Beyond.Gameplay.Core.CharInteractPerform.CharAnimActionData',),48),
    'montage':('Beyond.Montage.AnimMontageData',
        ('Beyond.Montage.ClipMontageData','Beyond.Montage.SequenceMontageData'),2),
}


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def montage_program(regions,entry,s,*,tag,existing=False,ff=False):
    need('finite-montage-selection',type(tag)is int and tag in(0,1)and type(existing)is type(ff)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4883ec20');flag=g.relative('803d')+1
    g.take('00','498bd8','488bf2');g.branch('0f84',False)
    g.take('33ff','488d542438','488bce','66897c2438');g.call(s['header']);g.take('84c0');g.branch('0f84',ff)
    usage=None;comparison=None
    if not ff:
        g.take('0fb77c2438','6685ff');g.branch('75',tag==1,1)
        if tag==1:g.take('6683ff01');g.branch('0f85',False)
        g.take('488b0b','4885c9');g.branch('74',not existing,1)
        if existing:
            at=g.at;comparison=dict(instruction=at,cell=g.relative('488b15'))
            g.take('488b09');g.call(s['assignable']);g.take('84c0');g.branch('74',True,1)
        at=g.at;usage=dict(instruction=at,cell=g.relative('488b15'))
        g.take('488bce');g.call(s['packable'])
        if tag==1:g.take('488bcb','488903')
        else:g.take('488903','488bcb')
        g.call(s['barrier'])
        if tag==1:g.jump('e9')
        else:g.jump('eb',1)
    else:
        # Exact FF clears the same output with the entry's whole RDI zero.
        g.take('48893b');g.jump('e9');g.take('488bcb');g.call(s['barrier']);g.jump('eb',1)
    g.take('488b5c2430','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,tag=None if ff else tag,canonicalFF=ff,
        existingIncompatibleWrapper=existing,comparisonTypeUsage=comparison,childUsage=usage,
        sameReader=True,sameOutput=True,outputInitiallyNull=not existing and not ff,
        clearedOutputBytes=8 if ff else 0,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rsi','rdi'],compatibleExistingWrapperAdmitted=False,concreteGrammarAdmitted=False)


def char_animation_program(regions,entry,s,*,tag,count,table,selected,existing=False,ff=False):
    """Selected CharAnim cold branch and its shared output/barrier return."""
    from scripts.game_data.memorypack.skill_selector_union_sources import branch,jump,peek
    need('finite-char-animation-selection',type(tag)is int and 0<=tag<count==48
        and type(existing)is type(ff)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4883ec20');flag=g.relative('803d')+1
    g.take('00','498bd8','488bfa');g.branch('0f84',False)
    g.take('33f6','488d542438','488bcf','6689742438');g.call(s['header']);g.take('84c0');g.branch('0f84',ff)
    usage=None;comparison=None;image_base=None
    if ff:g.take('488933');g.jump('e9')
    else:
        g.take('0fb7742438','83fe'+bytes((count-1,)).hex());g.branch('0f87',False)
        image_base=g.relative('488d15');g.take('8b8cb2'+(table-image_base).to_bytes(4,'little').hex(),'4803ca','ffe1')
        g.at=selected;g.take('488b0b','4885c9');branch(g,4,not existing)
        if existing:
            at=g.at;comparison=dict(instruction=at,cell=g.relative('488b15'))
            g.take('488b09');g.call(s['assignable']);g.take('84c0')
            opcode=peek(g,2);code=4 if opcode[:1]==b'\x74'or opcode==b'\x0f\x84'else 5
            need('owned-incompatible-predicate-branch',opcode[:1]in(b'\x74',b'\x75')or opcode in(b'\x0f\x84',b'\x0f\x85'))
            branch(g,code,code==4)
        at=g.at;usage=dict(instruction=at,cell=g.relative('488b15'))
        g.take('488bcf');g.call(s['packable']);g.take('488903')
        if peek(g)in(b'\xe9',b'\xeb'):jump(g)
    g.take('488bcb');g.call(s['barrier']);g.take('488b5c2430','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,tag=None if ff else tag,entryCount=count,table=table,imageBase=image_base,
        initializedFlag=flag,canonicalFF=ff,existingBaseWrapper=existing,comparisonTypeUsage=comparison,
        childContext=usage,sameReader=True,sameOutput=True,clearedOutputBytes=8 if ff else 0,
        normalReturn=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],
        compatibleExistingWrapperAdmitted=False,concreteGrammarAdmitted=False,
        condition='Exact authenticated selected CharAnim table route, initialized metadata, initially-null or incompatible coherent base wrapper, normal typed child and disabled barrier. Other tags, compatible reuse and enclosing collection remain separate.')


def _owned(image,entry):
    from scripts.game_data.memorypack.buff_ec_profiles_native import family_windows
    base=image.pe.image_base;family,windows=family_windows(image,entry-base)
    return dict(pointer=entry,family=family,windows=windows,
        regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows])


def _target(body,pattern):
    prefix=bytes.fromhex(pattern);found=[]
    for at,raw in body['regions']:
        position=raw.find(prefix)
        while position>=0:
            site=at+position+len(prefix)-1
            found.append(site+5+int.from_bytes(raw[position+len(prefix):position+len(prefix)+4],'little',signed=True))
            position=raw.find(prefix,position+1)
    need('one-owned-helper-sequence:'+pattern,len(set(found))==1)
    return found[0]


def derive(image,pins,*,families=None,all_char_routes=False):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.memorypack import pointer_param as pointer,reference_adapter_sources as reference
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.scalar_param_native import reader_offsets
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    names=list(FAMILIES)if families is None else list(families)
    need('finite-distinct-family-selection',bool(names)and len(names)==len(set(names))and set(names)<=set(FAMILIES))
    need('explicit-complete-Char-family-selection',type(all_char_routes)is bool and(not all_char_routes or'char-animation'in names))
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()}
    by_wrapper={w.name:w for w in wrappers.values()}
    all_wrappers={w.type_definition:w for w in wrappers.values()}
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    model=json.loads((CONTRACTS_DIR/'model_view_state_controller_native.json').read_bytes())
    need('same-current-helper-declarations',core['nativeInputs']==model['nativeInputs']==pins)
    packable=base+core['readPackable']['entryRva'];barrier=base+model['collector']['entryRva']
    collector=_barrier(image,barrier);result={}
    for family in names:
        original,children,count=FAMILIES[family];wrapper=wrappers[original]
        switch=read_union_switch(image,wrapper.name,wrappers=all_wrappers)
        need('exact-current-family-size',switch['entryCount']==count)
        if family=='char-animation'and all_char_routes:
            children=tuple(by_wrapper[r['wrapperName']].wrapped_type for r in switch['entries'])
            need('all-physical-Char-routes-bijective',len(children)==count and len(set(children))==count
                and[r['tag']for r in switch['entries']]==list(range(count)))
        entry=int(switch['dispatcherVa'],16);body=_owned(image,entry)
        header=_target(body,'488d542438488bcf6689742438e8'if family=='char-animation'else'488d542438488bce66897c2438e8')
        assignable=_target(body,'488b09e8')
        symbols=dict(header=header,assignable=assignable,packable=packable,barrier=barrier)
        header_body=_owned(image,header)
        header_programs={mode:enclosing_header(header_body['regions'],header,reader_offsets(image,LABEL),marker=mode)for mode in('short','false')}
        selected=[]
        for child_name in children:
            child=wrappers[child_name];rows=[r for r in switch['entries']if r['wrapperName']==child.name]
            need('one-actual-concrete-route',len(rows)==1);route=rows[0];tag=route['tag'];programs=[]
            for existing in(False,True):
                if family=='char-animation':
                    program=char_animation_program(body['regions'],entry,symbols,tag=tag,count=count,
                        table=int(switch['tableVa'],16),selected=int(route['targetVa'],16),existing=existing)
                    program['childUsage']=program['childContext'];program['comparisonTypeUsage']=program['comparisonTypeUsage']
                else:program=montage_program(body['regions'],entry,symbols,tag=tag,existing=existing)
                usage=derive_typed_usage_context(image,program['childUsage']['instruction']-base,label=LABEL+'.child')
                typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
                need('same-own-method-and-reader-overload',usage['typeName']=='MemoryPack.MemoryPackReader'and usage['classArguments']==[])
                if existing:
                    comparison=derive_typed_usage_context(image,program['comparisonTypeUsage']['instruction']-base,label=LABEL+'.comparison')
                    need('same-actual-typed-comparison',comparison.get('tag')==1 and comparison.get('typeName')==child.name)
                programs.append(dict(source=program,typedRequest=usage,typedArgument=typed))
            selected.append(dict(tag=tag,wrappedType=child_name,wrapperName=child.name,route=route,programs=programs))
        if family=='montage':null=montage_program(body['regions'],entry,symbols,tag=0,ff=True)
        else:
            null=char_animation_program(body['regions'],entry,symbols,tag=0,count=count,
                table=int(switch['tableVa'],16),selected=int(switch['entries'][0]['targetVa'],16),ff=True)
        pair=derive_pair(image,original,wrapper.name)
        def forwarder(selected_image,selected_pair,selected_wrapper):
            face,=selected_pair['composition']['interfaces'];fm=md.methods[face['formatterDeserializeMethodIndex']]
            need('actual-owned-union-slot5',selected_wrapper.name==wrapper.name and image.method_pointer_va(fm)==entry)
            return dict(ownedWindows=body['windows'],programs=selected,canonicalFF=null)
        adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
        getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
        getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper)
        need('own-base-reference-holder',holder['declaredType']==original and holder['offset']==16)
        face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];conversions=[]
        for route in selected:
            child=wrappers[route['wrappedType']];td=md.types[child.type_definition]
            start=section.offset+td.interface_offsets_start*8
            interfaces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
            matches=[(n,offset)for n,(index,offset)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
            need('one-owned-inherited-base-interface',len(matches)==1);ordinal,offset=matches[0]
            _vtable(image,child.type_definition,offset,getter.index,LABEL+'.inheritedGetValue')
            conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=_owned(image,conversion_entry)
            program=reference.conversion(conversion['regions'],conversion_entry,
                base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
            child_holder=_wrapper_holder(ctx,image,child)
            need('derived-wrapper-same-base-holder',child_holder['declaredType']==original and child_holder['offset']==16)
            conversions.append(dict(wrapperName=child.name,interfaceOrdinal=ordinal,interfaceOffset=offset,holder=child_holder,program=program))
        result[family]=dict(typeName=original,wrapperName=wrapper.name,switch=switch,selectedRoutes=selected,canonicalFF=null,
            family=body['family'],codeWindows=body['windows'],actualSourceRegions=[[at-base,raw.hex()]for at,raw in body['regions']],
            headerPrograms=header_programs,headerWindows=header_body['windows'],pair=pair,adapter=adapter,
            baseGetter=getter_proof,baseHolder=holder,derivedBaseConversions=conversions,
            concreteGrammarAdmitted=False,collectionParentAdmitted=False,wholeUnionAdmitted=False)
        if family=='char-animation'and all_char_routes:result[family]['completePhysicalFamilyRequested']=True
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.animation-selected-union-sources.v1',
        status='validated-conditional-selected-animation-union-sources',nativeInputs=pins,families=result,collector=collector,
        concreteGrammarAdmitted=False,containingOwnerAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=__doc__)))
