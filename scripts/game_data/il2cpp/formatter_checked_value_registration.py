"""Finite explicit-class-check adapter registration for a plain value Original.

The actual direct constructor is independently selected with Original/object
generic arguments. Its initialized slot12 path returns without stores, calls
or stack changes. The cold indirect base-constructor tail is excluded; live
initialization, provider choice and enclosing native frame remain conditions.
No reference canonical constructor, thunk or value width is substituted.
"""
import hashlib

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

PROFILE='direct-value-adapter-explicit-static-checks.v1'
LABEL='checkedValueRegistration'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def program(regions,entry):
    g=BytesPath(regions,entry)
    def usage(opcode):
        site=g.at;cell=g.relative(opcode);return dict(instruction=site,cell=cell)
    allocation=usage('488b0d');allocate=g.relative('e8');g.take('488bf8','4885c0')
    nonnull=g.relative('75',1);throw=g.relative('e8');g.take('cc')
    need('exact-nonnull-skip-throw-CC',g.at,nonnull)
    constructor=usage('488b15');g.take('488bcf');construct=g.relative('e8')
    system_type=usage('488b0d');key=usage('488b1d');type_check=g.relative('e8')
    g.take('33d2','488bcb');type_from_handle=g.relative('e8')
    provider=usage('488b0d');g.take('488bd8');provider_check=g.relative('e8')
    need('same-actual-static-class-check',type_check,provider_check)
    g.take('4533c0','488bd3','488bcf');register=g.relative('e8')
    return dict(selectedBytes=g.seen,end=g.at,allocation=allocation,constructor=constructor,key=key,
        systemType=system_type,provider=provider,
        actualCalls=dict(allocation=allocate,constructor=construct,typeFromHandle=type_from_handle,registerWrap=register),
        staticClassCheckCalls=dict(systemType=type_check,provider=provider_check),
        excludedNullAllocationThrow=dict(target=throw,terminal='CC'),
        sameAllocatedAdapterToConstructorAndRegistration=True,sameOriginalKeyToRegistration=True,
        constructorCallExecuted=True,allocationNonnullRequired=True,compatibleNormalSourceDisjointHelpersRequired=True,
        systemTypeAndProviderInitializedRequired=True,nativeFrameBoundaryClaimed=False)


def constructor_program(regions,entry):
    """Own the exact bounded initialized path and exclude the cold tail."""
    g=BytesPath(regions,entry)
    g.take('488b4220','488b88c0000000','488b4160','4883782000')
    warm=g.relative('75',1)
    # Inspect and bound the excluded cold arm without admitting its execution.
    cold=g.at;g.take('488b4220','488b88c0000000','488b4160','48ff20')
    need('own-initialized-return-target',g.at,warm);g.take('c3')
    return dict(selectedBytes=g.seen,end=g.at,baseConstructorContextSlot=12,
        baseConstructorInitializedRequired=True,selectedNormalReturnVa=warm,
        excludedColdTailVa=cold,coldBranchAdmitted=False,physicalExtentProved=False,
        selectedPathNoFieldStores=True,selectedPathNoCalls=True,
        normalReturn=True,entryRspRestored=True,allWin64NonvolatilesUnchanged=True)


def derive_constructor(image,original,method,target):
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    ctx=NativeReferenceContext(image);td=ctx.index.types[original];base=image.pe.image_base
    need('plain-nonenumeration-Original',(True,False,'System.ValueType',-1),
        (ctx.is_value_type(original),ctx.is_enum(original),ctx.parent(original),td.generic_container_index))
    entries=GenericEntries(image);rows=entries.observe(method.index,[original,'object'],[])
    need('single-current-nominal-value-registration',1,len(rows));canonical=rows[0]
    need('nonnull-value-canonical-entry',True,type(canonical['pointer'])is int and canonical['pointer']>base)
    need('actual-value-canonical-target',canonical['pointer'],target)
    first=canonical['classInstantiation']['arguments'][0]
    pointer=first['type_pointer_va'];raw=image.pe.bytes_at_va(pointer,16)
    scalar.ordinary(image,pointer,17,LABEL+'.Original')
    need('same-current-Original-type-definition',td.index,int.from_bytes(raw[:8],'little'))
    program_=constructor_program([(target,image.pe.bytes_at_va(target,41))],target)
    end=program_['end'];window=dict(startRva=target-base,endRva=end-base,
        sha256=hashlib.sha256(image.pe.bytes_at_va(target,end-target)).hexdigest().upper(),
        boundary='Exact registered entry through owned initialized RET; physical extent and cold tail execution unproved')
    return canonical,dict(windows=[window]),program_


def _derive(image,original,wrapper,start,helpers):
    from scripts.game_data.il2cpp.formatter_direct_registration import _derive_program
    base=image.pe.image_base;source=program([(base+start,image.pe.bytes_at_va(base+start,256))],base+start)
    return _derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__,value_constructor=True)


def derive(image,original,wrapper,candidates,helpers):
    found={};diagnostics=[]
    for candidate in candidates:
        if not candidate['rawHex'].lower().startswith('488b1d'):continue
        start=candidate['siteRva']-48
        if start<0:continue
        try:
            row=_derive(image,original,wrapper,start,helpers)
            need('exact-selected-key-site',candidate['siteRva'],row['key']['instructionRva']);found[start]=row
        except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:800])
    if len(found)!=1:raise ValueError(LABEL+'.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('explicit-checked-value-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-current-checked-value-declaration',actual,flow)
