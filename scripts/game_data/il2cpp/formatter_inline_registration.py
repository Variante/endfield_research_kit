"""Exact alternative eager reference registration with an inlined constructor.

This bounded source stores the typed adapter in RDI, resolves the Original
System.Type key and passes both to the named RegisterWrap. The closed generic
constructor's base MethodInfo context must already be initialized; both actual
inline source and the independent canonical constructor then execute no stores
or calls. No constructor call/pointer alias is asserted for the inline source.
Execution of initialization and the live provider's selection stay unobserved.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

PROFILE='inline-closed-adapter-constructor.v1'
GENERIC='Beyond.MemoryPack.GenericMemoryPackFormatter`2'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError('inlineReferenceRegistration.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def program(regions,entry):
    g=BytesPath(regions,entry)
    def usage(opcode):
        at=g.at;cell=g.relative(opcode);return dict(instruction=at,cell=cell)
    allocation=usage('488b0d');allocate=g.relative('e8');g.take('488bf8','4885c0');g.branch('0f84',False)
    constructor=usage('4c8b05')
    g.take('498b4820','488b91c0000000','488b4a60','4883792000');g.branch('75',True,1)
    system_type=usage('488b0d');key=usage('488b1d');g.take('83b9e000000000');g.branch('75',True,1)
    g.take('33d2','488bcb');type_from_handle=g.relative('e8')
    provider=usage('488b0d');g.take('488bd8','83b9e000000000');g.branch('75',True,1)
    g.take('4533c0','488bd3','488bcf');register=g.relative('e8')
    return dict(selectedBytes=g.seen,end=g.at,allocation=allocation,constructor=constructor,key=key,
        systemType=system_type,provider=provider,actualCalls=dict(allocation=allocate,typeFromHandle=type_from_handle,registerWrap=register),
        adapterValue='same allocation RAX saved RDI then RegisterWrap RCX',originalKey='selected handle RBX then exact Type result RAX saved RBX to RegisterWrap RDX',
        baseConstructorContextSlot=12,baseConstructorInitializedRequired=True,constructorCallExecuted=False,
        allocationNonnullRequired=True,systemTypeAndProviderInitializedRequired=True,normalHelpersRequired=True,
        nativeFrameBoundaryClaimed=False)


def canonical_constructor_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('4883ec28','488b4220','488b88c0000000','488b4160','4883782000');g.branch('0f84',False)
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,baseConstructorContextSlot=12,baseConstructorInitializedRequired=True,
        noFieldStores=True,noCalls=True,normalReturn=True,entryRspRestored=True)


def ordinary_void_return(raw):
    """The value-type marker is independent of modifiers/byref/pinned bits."""
    need('complete-void-type-record',16,len(raw))
    need('ordinary-void-kind',1,raw[10]);need('ordinary-void-modifiers-byref-pinned',0,raw[11]&0x7f)


def _derive(image,original,wrapper,start,helpers):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack.pointer_param import owned
    base=image.pe.image_base;raw=image.pe.bytes_at_va(base+start,256)
    source=program([(base+start,raw)],base+start);ctx=NativeReferenceContext(image)
    usages={name:derive_typed_usage_context(image,source[name]['instruction']-base,label='inlineReferenceRegistration')
        for name in('allocation','constructor','key','systemType','provider')}
    allocation,constructor,key=(usages[k]for k in('allocation','constructor','key'))
    need('nominal-constructor',(6,GENERIC,'.ctor',[original,wrapper],[]),tuple(constructor[k]for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('nominal-adapter',(1,GENERIC+'<'+original+','+wrapper+'>'),(allocation['tag'],allocation['typeName']))
    need('nominal-key',(2,original),(key['tag'],key['typeName']))
    for name,typename in(('systemType','System.Type'),('provider','MemoryPack.MemoryPackFormatterProvider')):
        need('nominal-static-class:'+name,(1,typename),(usages[name]['tag'],usages[name]['typeName']))
    pointer=ctx.type_pointer(allocation['typeIndex']);record=image.pe.bytes_at_va(pointer,16)
    need('adapter-generic-kind',21,record[10]);carrier=int.from_bytes(record[:8],'little')
    instance=image.instantiations.resolve_pointer(image.pe.u64_at_va(carrier+8))
    need('same-closed-constructor-instance',constructor['methodSpec'][1],instance.index)
    need('same-key-type-pointer',instance.arguments[0].type_pointer_va,ctx.type_pointer(key['typeIndex']))
    for name in('typeFromHandle','registerWrap'):
        image.validate_method_row(helpers[name],label='inlineReferenceRegistration')
        need('actual-named-call:'+name,base+helpers[name][3],source['actualCalls'][name])
    for name,owner,method_name,parameters,returned in(
        ('typeFromHandle','System.Type','GetTypeFromHandle',['System.RuntimeTypeHandle'],'System.Type'),
        ('registerWrap','MemoryPack.MemoryPackFormatterProvider','RegisterWrap',['MemoryPack.IMemoryPackFormatter','System.Type'],'void')):
        row=helpers[name];method=image.metadata.methods[row[0]]
        need('static-helper:'+name,True,bool(method.flags&16))
        need('helper-abi:'+name,(owner,method_name,parameters,returned),(row[1],row[2],[ctx.type_name(p.type_index)for p in image.metadata.parameters_for(method)],ctx.type_name(method.return_type)))
    generic=image.named_types[GENERIC];context=ContextSymbols(image).context(generic.index)
    method=image.metadata.methods[constructor['methodSpec'][0]]
    need('exact-closed-constructor-abi',(generic.index,False,0,'void',False),
        (method.declaring_type,bool(method.flags&16),method.parameter_count,ctx.type_name(method.return_type),method.generic_container_index>=0))
    ordinary_void_return(image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16))
    slot,=[row for row in context['entries']if row['relativeSlot']==12]
    need('exact-base-constructor-slot',(3,'MemoryPack.MemoryPackFormatter`1','.ctor',[]),(slot['kind'],slot['typeName'],slot['methodName'],slot['methodArguments']))
    argument,=slot['classArguments'];parameter=argument['parameterOwner']
    need('base-constructor-first-owned-class-argument',(generic.index,0),(parameter['typeIndex'],parameter['ordinal']))
    definition=constructor['methodSpec'][0];canonical=GenericEntries(image).resolve(definition,['object','object'],[])
    body=owned(image,canonical['pointer']);canonical_program=canonical_constructor_program(body['regions'],body['pointer'])
    end=source['end']-base;window=dict(startRva=start,endRva=end,
        sha256=hashlib.sha256(image.pe.bytes_at_va(base+start,end-start)).hexdigest().upper())
    return json.loads(json.dumps(dict(profile=PROFILE,originalType=original,wrapperType=wrapper,window=window,
        allocation=allocation,constructor=constructor,key=key,staticClasses={name:usages[name]for name in('systemType','provider')},
        actualCalls={name:target-base for name,target in source['actualCalls'].items()},helperMethods=helpers,
        sourceProgram=source,canonicalConstructor=canonical,canonicalConstructorWindows=body['windows'],
        canonicalConstructorProgram=canonical_program,genericContext=context,
        condition=__doc__,constructorCallExecuted=False,constructorPointerEqualityClaimed=False)))


def derive(image,original,wrapper,candidates,helpers):
    """Candidate bytes select this exact source profile, never establish it."""
    found={};diagnostics=[]
    for candidate in candidates:
        if not candidate['rawHex'].lower().startswith('488b1d'):continue
        start=candidate['siteRva']-77
        if start<0:continue
        try:
            row=_derive(image,original,wrapper,start,helpers)
            need('exact-selected-key-site',candidate['siteRva'],row['key']['instructionRva'])
            found[start]=row
        except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:400])
    if len(found)!=1:raise ValueError('inlineReferenceRegistration.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('explicit-inline-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-current-inline-declaration',actual,flow)
