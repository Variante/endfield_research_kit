"""Exact named-parent joins and buffered source programs for atomic DWORDs."""
from __future__ import annotations

import json

from scripts.common import check_installed_native_inputs
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.buff_frontiers_regenerate import _method_row
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.native_image import read_reviewed_contract,open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import buff_ec_profiles_native as ec,buff_profile_source as source
from scripts.game_data.memorypack.wrapper_members import unmanaged_value_sizes_from_image
from scripts.game_data.skill_timeline_routes_regenerate import check_read_setter_transfers

need=source.need


def parent_sources(image,reviewed):
    base=image.pe.image_base;roles=[];targets=set();windows=[]
    for parent in reviewed['parentRoles']:
        method=_method_row(image,[0,parent['ownerType'],'Deserialize',1])
        family,owned,rows=ec.family(image,method[3]);windows.extend(owned)
        source.need('word.parent-decode',not any(r['text'].startswith('db ') for r in rows))
        wrapper=ec.one(list(image.memorypack_wrappers.values()),lambda w:w.name==parent['ownerType'],'word.parent-wrapper')
        contexts=ec.contexts(image,rows)
        selected=[c for c in contexts if c['fullTypeName']==reviewed['typeName']]
        source.need('word.context-count',len(selected)==len(parent['fields']))
        members={m.name:m for m in wrapper.members};field_proofs=[]
        for context,field in zip(selected,parent['fields']):
            member=members[field]
            source.need('word.declared-type',member.declared_type==reviewed['typeName'])
            source.need('word.unmanaged-context',context['methodOwner']=='MemoryPack.MemoryPackReader' and
                context['methodName']=='ReadUnmanaged' and context['typeKind']==0x11 and context['register']=='rdx')
            matches=[]
            for index,row in enumerate(rows):
                flow=control_transfer(row)
                if flow['kind']!='call':continue
                argument=ec.last_write(rows,index,'rdx');reader=ec.last_write(rows,index,'rcx')
                if argument and reader and ec.va(argument)==base+context['instructionRva'] and reader['text']=='mov rcx, rdi':
                    matches.append(row)
            call=ec.one(matches,lambda r:True,'word.typed-consumer-call')
            target=control_transfer(call)['target'];targets.add(target)
            read=dict(memberIndex=list(wrapper.members).index(member),readKind='int32',sourceCallsiteRva=ec.va(call)-base)
            setter=image.metadata.methods[member.method_index]
            setter_target=image.method_pointer_va(setter)
            check_read_setter_transfers([dict(r,va=ec.va(r)) for r in rows],[read],[setter_target],base=base)
            field_proofs.append(dict(fieldName=field,declaredType=member.declared_type,context=context,
                call=ec.site(call,base),targetRva=target-base,
                setter=[setter.index,image.type_name(setter.declaring_type),image.metadata.string(setter.name_index),setter_target-base]))
        roles.append(dict(method=method,family=family,fields=field_proofs))
    source.need('word.unique-actual-helper',len(targets)==1,len(targets))
    return roles,windows,next(iter(targets))


def derive(image,inputs,reviewed):
    base=image.pe.image_base;ctx=NativeReferenceContext(image);name=reviewed['typeName']
    source.need('word.ordinary-value-type',ctx.is_value_type(name) and not ctx.is_enum(name))
    source.need('word.managed-width',unmanaged_value_sizes_from_image(image).get(name)==4)
    roles,windows,target=parent_sources(image,reviewed)
    definitions={f['context']['typeDefinition'] for p in roles for f in p['fields']}
    methods={f['context']['methodSpec'][0] for p in roles for f in p['fields']}
    source.need('word.unique-type-method',len(definitions)==len(methods)==1)
    named=image.named_type_definitions.get(name,())
    source.need('word.unique-type-name',len(named)==1 and named[0].index==next(iter(definitions)))
    family,helper_windows,rows=ec.family(image,target-base)
    offsets=ec.source_offsets(image)
    extra={}
    if reviewed['helperKind']=='inline':program=source.inline_word_program(rows,target,offsets)
    elif reviewed['helperKind']=='advance':
        program,advance=source.advance_word_program(rows,target,offsets)
        af,aw,ar=ec.family(image,advance-base);ap=source.advance_four_program(ar,advance,offsets)
        aby={ec.va(r):r for r in ar};helper_windows+=aw
        extra=dict(advanceTargetRva=advance-base,advanceFamily=af,
            advanceProgram=[ec.site(aby[a],base) for a in ap],advanceArgument=4)
    else:source.need('word.helper-kind',False,reviewed['helperKind'])
    by={ec.va(r):r for r in rows};unique={}
    for w in windows+helper_windows:unique.setdefault((w['startRva'],w['endRva']),w)
    result=dict(reviewed)
    result.update(status='exact-current-build',nativeInputs=dict(inputs),wireBytes=4,resultRegister='eax',
        typeDefinition=next(iter(definitions)),contextTypeKind=0x11,readerMethodDefinition=next(iter(methods)),
        targetRva=target-base,codeWindows=list(unique.values()),proof=dict(parentRoles=roles,
        helperFamily=family,readerOffsets=offsets,selectedProgram=[ec.site(by[a],base) for a in program],**extra))
    return json.loads(json.dumps(result))


def validate_on_image(owner,image,inputs):
    reviewed,_=read_reviewed_contract(owner.CONTRACT_PATH,schema=owner.SCHEMA,status='exact-current-build',label=owner.LABEL)
    source.need('word.native-inputs',reviewed['nativeInputs']==inputs)
    actual=owner.derive(image,inputs,reviewed)
    source.need('word.current-proof',actual==reviewed,ec.first_difference(reviewed,actual))
    return {k:actual[k] for k in ('status','nativeInputs','typeName','typeDefinition','contextTypeKind',
        'readerMethodDefinition','wireBytes','resultRegister','targetRva','evidenceBoundary')} | {'status':'validated'}


def validate_current(owner,*,gameassembly=None,metadata=None):
    if (gameassembly is None)!=(metadata is None):raise ValueError(owner.LABEL+'.native:both-selected-paths-required')
    try:
        reviewed,_=read_reviewed_contract(owner.CONTRACT_PATH,schema=owner.SCHEMA,status='exact-current-build',label=owner.LABEL)
        inputs=reviewed['nativeInputs']
        gate=check_installed_native_inputs(inputs['GameAssembly.dll'],inputs['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
        image=open_native_image(gate.gameassembly,gate.metadata);_publication_gate(image,inputs)
        result=owner.validate_on_image(image,inputs);_publication_gate(image,inputs)
        return result
    except (ValueError,KeyError,IndexError,TypeError,OSError) as error:
        return native_validation_failure(error,label=owner.LABEL,source_path=owner.CONTRACT_PATH)
