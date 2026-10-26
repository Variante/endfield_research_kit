"""Exact stack-retained eager registration with explicit static-class checks.

The selected normal path preserves adapter, Original handle and resolved Type
in distinct stack homes across calls. Each static check receives its actual
nominal class. Compatible normal helpers and source-disjoint storage are
conditions; no live initialization or provider selection is observed.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.formatter_direct_registration import constructor_abi
from scripts.game_data.il2cpp.formatter_inline_registration import GENERIC,canonical_constructor_program,ordinary_void_return

PROFILE='stack-adapter-explicit-static-checks.v1'
LABEL='stackReferenceRegistration'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def program(regions,entry):
    g=BytesPath(regions,entry)
    def usage(opcode):
        at=g.at;cell=g.relative(opcode);return dict(instruction=at,cell=cell)
    allocation=usage('488b0d');allocate=g.relative('e8')
    g.take('4889442420','488b4c2420');check=g.relative('e8')
    constructor=usage('488b15');g.take('488b4c2420');construct=g.relative('e8')
    key=usage('488b05');g.take('4889442428');system_type=usage('488b0d');type_check=g.relative('e8')
    g.take('33d2','488b4c2428');type_from_handle=g.relative('e8');g.take('4889442430')
    provider=usage('488b0d');provider_check=g.relative('e8')
    need('same-static-class-check-entry',type_check,provider_check)
    g.take('4533c0','488b542430','488b4c2420');register=g.relative('e8')
    return dict(selectedBytes=g.seen,end=g.at,allocation=allocation,constructor=constructor,key=key,
        systemType=system_type,provider=provider,
        actualCalls=dict(allocation=allocate,objectCheck=check,constructor=construct,
            typeFromHandle=type_from_handle,registerWrap=register),
        staticClassCheckCalls=dict(systemType=type_check,provider=provider_check),
        stackHomes=dict(adapter=32,originalHandle=40,resolvedType=48),
        sameAllocatedAdapterToConstructorAndRegistration=True,sameOriginalKeyToRegistration=True,
        compatibleNormalSourceDisjointHelpersRequired=True,nativeFrameBoundaryClaimed=False)


def thunk_program(regions,entry):
    g=BytesPath(regions,entry);site=g.at;cell=g.relative('488b15');target=g.relative('e9')
    return dict(selectedBytes=g.seen,end=g.at,contextInstruction=site,contextCell=cell,sharedTarget=target,
        receiverPreserved=True,closedContextLoadedInRdx=True)


def _derive(image,original,wrapper,start,helpers):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.pointer_param import owned
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    source=program([(base+start,image.pe.bytes_at_va(base+start,192))],base+start)
    usages={name:derive_typed_usage_context(image,source[name]['instruction']-base,label=LABEL)
        for name in('allocation','constructor','key','systemType','provider')}
    allocation,constructor,key=(usages[k]for k in('allocation','constructor','key'))
    need('nominal-constructor',(6,GENERIC,'.ctor',[original,wrapper],[]),
        tuple(constructor[k]for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('nominal-adapter',(1,GENERIC+'<'+original+','+wrapper+'>'),(allocation['tag'],allocation['typeName']))
    need('nominal-key',(2,original),(key['tag'],key['typeName']))
    for name,typename in(('systemType','System.Type'),('provider','MemoryPack.MemoryPackFormatterProvider')):
        need('nominal-static-class:'+name,(1,typename),(usages[name]['tag'],usages[name]['typeName']))
    record=image.pe.bytes_at_va(ctx.type_pointer(allocation['typeIndex']),16)
    need('adapter-generic-kind',21,record[10]);carrier=int.from_bytes(record[:8],'little')
    instance=image.instantiations.resolve_pointer(image.pe.u64_at_va(carrier+8))
    need('same-closed-constructor-instance',constructor['methodSpec'][1],instance.index)
    need('closed-adapter-arity',2,len(instance.arguments))
    need('same-key-type-pointer',instance.arguments[0].type_pointer_va,ctx.type_pointer(key['typeIndex']))
    for name,owner,method_name,parameters,returned in(
        ('typeFromHandle','System.Type','GetTypeFromHandle',['System.RuntimeTypeHandle'],'System.Type'),
        ('registerWrap','MemoryPack.MemoryPackFormatterProvider','RegisterWrap',['MemoryPack.IMemoryPackFormatter','System.Type'],'void')):
        row=helpers[name];image.validate_method_row(row,label=LABEL);method=md.methods[row[0]]
        need('actual-named-call:'+name,base+row[3],source['actualCalls'][name])
        need('static-helper:'+name,True,bool(method.flags&16))
        need('helper-abi:'+name,(owner,method_name,parameters,returned),
            (row[1],row[2],[ctx.type_name(p.type_index)for p in md.parameters_for(method)],ctx.type_name(method.return_type)))
    method=md.methods[constructor['methodSpec'][0]]
    constructor_abi(image.type_name(method.declaring_type),bool(method.flags&16),method.parameter_count,
        ctx.type_name(method.return_type),method.generic_container_index>=0)
    ordinary_void_return(image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16))
    thunk_start=source['actualCalls']['constructor'];raw=image.pe.bytes_at_va(thunk_start,32)
    thunk=thunk_program([(thunk_start,raw)],thunk_start)
    actual_context=derive_typed_usage_context(image,thunk['contextInstruction']-base,label=LABEL)
    need('same-actual-thunk-context',tuple(constructor[k]for k in('methodSpecIndex','methodSpec','classArguments','methodArguments')),
        tuple(actual_context[k]for k in('methodSpecIndex','methodSpec','classArguments','methodArguments')))
    canonical=GenericEntries(image).resolve(method.index,['object','object'],[])
    need('actual-thunk-canonical-target',canonical['pointer'],thunk['sharedTarget'])
    body=owned(image,canonical['pointer']);canonical_program=canonical_constructor_program(body['regions'],body['pointer'])
    def window(a,z):return dict(startRva=a-base,endRva=z-base,
        sha256=hashlib.sha256(image.pe.bytes_at_va(a,z-a)).hexdigest().upper())
    return json.loads(json.dumps(dict(profile=PROFILE,originalType=original,wrapperType=wrapper,
        window=window(base+start,source['end']),allocation=allocation,constructor=constructor,key=key,
        staticClasses={name:usages[name]for name in('systemType','provider')},
        actualCalls={name:target-base for name,target in source['actualCalls'].items()},helperMethods=helpers,
        sourceProgram=source,constructorThunk=dict(window=window(thunk_start,thunk['end']),context=actual_context,
            sharedTargetRva=thunk['sharedTarget']-base,program=thunk),
        canonicalConstructor=canonical,canonicalConstructorWindows=body['windows'],
        canonicalConstructorProgram=canonical_program,condition=__doc__)))


def derive(image,original,wrapper,candidates,helpers):
    found={};diagnostics=[]
    for candidate in candidates:
        if not candidate['rawHex'].lower().startswith('488b05'):continue
        start=candidate['siteRva']-44
        if start<0:continue
        try:
            row=_derive(image,original,wrapper,start,helpers)
            need('exact-selected-key-site',candidate['siteRva'],row['key']['instructionRva']);found[start]=row
        except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:600])
    if len(found)!=1:raise ValueError(LABEL+'.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('explicit-stack-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-current-stack-declaration',actual,flow)
