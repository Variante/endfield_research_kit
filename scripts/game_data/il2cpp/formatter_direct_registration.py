"""Exact eager registration with an owned direct closed-constructor call.

The selected bounded program retains the allocated adapter in RDI, calls the
canonical constructor with its actual closed MethodInfo, resolves the Original
Type key, and passes those two values to RegisterWrap. Initialization, normal
helper returns and live provider selection remain explicit conditions.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.formatter_inline_registration import (
    GENERIC, canonical_constructor_program, ordinary_void_return,
)

PROFILE='direct-closed-adapter-constructor.v1'
LABEL='directReferenceRegistration'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def program(regions,entry):
    g=BytesPath(regions,entry)
    def usage(opcode):
        at=g.at;cell=g.relative(opcode);return dict(instruction=at,cell=cell)
    def initialized():
        g.take('83b9e000000000')
        target=g.relative('75',1);cold=g.relative('e8')
        need('exact-warm-join',g.at,target)
        return cold
    allocation=usage('488b0d');g.take('48895c2430');allocate=g.relative('e8')
    g.take('488bf8','4885c0');g.branch('74',False,1)
    constructor=usage('488b15');g.take('488bc8');construct=g.relative('e8')
    system_type=usage('488b0d');key=usage('488b1d');type_init=initialized()
    g.take('33d2','488bcb');type_from_handle=g.relative('e8')
    provider=usage('488b0d');g.take('488bd8');provider_init=initialized()
    g.take('4533c0','488bd3','488bcf');register=g.relative('e8')
    return dict(selectedBytes=g.seen,end=g.at,allocation=allocation,constructor=constructor,key=key,
        systemType=system_type,provider=provider,
        actualCalls=dict(allocation=allocate,constructor=construct,typeFromHandle=type_from_handle,registerWrap=register),
        unselectedClassInitCalls=dict(systemType=type_init,provider=provider_init),
        adapterValue='same allocation RAX saved RDI; same RAX to constructor RCX; retained RDI to RegisterWrap RCX',
        originalKey='selected handle RBX then exact Type result RAX saved RBX to RegisterWrap RDX',
        savedIncomingRbxHomeOffset=48,constructorCallExecuted=True,
        allocationNonnullRequired=True,systemTypeAndProviderInitializedRequired=True,
        normalHelpersRequired=True,nativeFrameBoundaryClaimed=False)


def constructor_abi(owner,static,arity,returned,method_generic):
    need('closed-constructor-abi',(GENERIC,False,0,'void',False),
        (owner,static,arity,returned,method_generic))


def _derive(image,original,wrapper,start,helpers):
    base=image.pe.image_base
    source=program([(base+start,image.pe.bytes_at_va(base+start,256))],base+start)
    return _derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__)


def _derive_program(image,original,wrapper,start,helpers,source,*,profile,condition,value_constructor=False,
        static_roles=('systemType','provider')):
    """Join an already selected finite direct-call program to actual native ABI.

    Each profile replays its own exact byte program before entering this join;
    validation rederives that same profile. No candidate or callable injection
    supplies an ordinary adapter or a canonical constructor pointer by itself.
    """
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack.pointer_param import owned
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    need('literal-value-constructor-selection',bool,type(value_constructor))
    need('explicit-static-class-roles',True,type(static_roles)is tuple and static_roles in(('systemType','provider'),('provider',)))
    if static_roles==('provider',):
        need('single-static-class-explicit-profile','direct-adapter-key-in-rcx-single-static-check.v1',profile)
        need('unobserved-System-Type-initialization-condition',True,source.get('explicitSystemTypeInitializedRequired'))
        need('single-static-class-owned-source-roles',['provider'],source.get('staticRoles'))
        need('no-fabricated-System-Type-class-usage',False,source.get('systemTypeClassUsagePresent'))
    need('owned-direct-constructor-selected',True,source.get('constructorCallExecuted'))
    usages={name:derive_typed_usage_context(image,source[name]['instruction']-base,label=LABEL)
        for name in('allocation','constructor','key',*static_roles)}
    allocation,constructor,key=(usages[k]for k in('allocation','constructor','key'))
    need('nominal-constructor',(6,GENERIC,'.ctor',[original,wrapper],[]),
        tuple(constructor[k]for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('nominal-adapter',(1,GENERIC+'<'+original+','+wrapper+'>'),(allocation['tag'],allocation['typeName']))
    need('nominal-key',(2,original),(key['tag'],key['typeName']))
    static_types={'systemType':'System.Type','provider':'MemoryPack.MemoryPackFormatterProvider'}
    for name in static_roles:
        typename=static_types[name]
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
    generic=image.named_types[GENERIC];context=ContextSymbols(image).context(generic.index)
    slot,=[row for row in context['entries']if row['relativeSlot']==12]
    need('exact-base-constructor-slot',(3,'MemoryPack.MemoryPackFormatter`1','.ctor',[]),
        (slot['kind'],slot['typeName'],slot['methodName'],slot['methodArguments']))
    argument,=slot['classArguments'];parameter=argument['parameterOwner']
    need('base-constructor-first-owned-class-argument',(generic.index,0),(parameter['typeIndex'],parameter['ordinal']))
    entries=GenericEntries(image)
    if value_constructor:
        from scripts.game_data.il2cpp.formatter_checked_value_registration import PROFILE as VALUE_PROFILE,derive_constructor
        need('explicit-value-constructor-profile',VALUE_PROFILE,profile)
        canonical,body,canonical_program=derive_constructor(image,original,method,source['actualCalls']['constructor'])
    else:
        canonical=entries.resolve(method.index,['object','object'],[])
        body=owned(image,canonical['pointer']);canonical_program=canonical_constructor_program(body['regions'],body['pointer'])
    need('actual-direct-canonical-target',canonical['pointer'],source['actualCalls']['constructor'])
    observed=entries.observe(method.index,[original,wrapper],[])
    if value_constructor and observed:
        need('one-actual-closed-value-constructor-row',1,len(observed));closed=observed[0]
    else:closed=entries.resolve(method.index,[original,wrapper],[])if observed else None
    if closed is not None:need('observed-closed-canonical-target',canonical['pointer'],closed['pointer'])
    end=source['end']-base
    return json.loads(json.dumps(dict(profile=profile,originalType=original,wrapperType=wrapper,
        window=dict(startRva=start,endRva=end,sha256=hashlib.sha256(image.pe.bytes_at_va(base+start,end-start)).hexdigest().upper()),
        allocation=allocation,constructor=constructor,key=key,
        staticClasses={name:usages[name]for name in static_roles},
        actualCalls={name:target-base for name,target in source['actualCalls'].items()},helperMethods=helpers,
        sourceProgram=source,canonicalConstructor=canonical,canonicalConstructorWindows=body['windows'],
        canonicalConstructorProgram=canonical_program,genericContext=context,
        closedConstructorObservations=observed,closedConstructor=closed,
        constructorCallExecuted=True,actualConstructorEqualsCanonical=True,
        closedPointerEquivalenceProved=closed is not None,condition=condition)))


def derive(image,original,wrapper,candidates,helpers):
    """Raw key cells select candidates; exact bytes and nominal ABI decide."""
    found={};diagnostics=[]
    for candidate in candidates:
        if not candidate['rawHex'].lower().startswith('488b1d'):continue
        start=candidate['siteRva']-47
        if start<0:continue
        try:
            row=_derive(image,original,wrapper,start,helpers)
            need('exact-selected-key-site',candidate['siteRva'],row['key']['instructionRva'])
            found[start]=row
        except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:600])
    if len(found)!=1:raise ValueError(LABEL+'.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('explicit-direct-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-current-direct-declaration',actual,flow)
