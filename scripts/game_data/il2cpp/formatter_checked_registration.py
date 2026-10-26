"""Direct closed-adapter registration with two explicit static-class checks.

The exact bounded normal program retains its allocated adapter in RDI, calls
the actual closed constructor with the selected MethodInfo, resolves the exact
Original handle to Type, and passes that pair to RegisterWrap. Both static
checks receive their own nominal class and the same actual helper. Compatible
normal Win64 helpers, nonnull typed allocation and coherent initialized classes
remain conditions. No whole native frame, live initialization, provider state
or stored child grammar follows from this registration path.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

PROFILE='direct-adapter-explicit-static-checks.v1'
LABEL='checkedReferenceRegistration'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def program(regions,entry):
    g=BytesPath(regions,entry)
    def usage(opcode):
        site=g.at;cell=g.relative(opcode);return dict(instruction=site,cell=cell)
    allocation=usage('488b0d');allocate=g.relative('e8')
    g.take('488bf8','4885c0');g.branch('0f84',False)
    constructor=usage('488b15');g.take('488bc8');construct=g.relative('e8')
    system_type=usage('488b0d');key=usage('488b1d');type_check=g.relative('e8')
    g.take('33d2','488bcb');type_from_handle=g.relative('e8')
    provider=usage('488b0d');g.take('488bd8');provider_check=g.relative('e8')
    need('same-actual-static-class-check',type_check,provider_check)
    g.take('4533c0','488bd3','488bcf');register=g.relative('e8')
    return dict(selectedBytes=g.seen,end=g.at,allocation=allocation,constructor=constructor,key=key,
        systemType=system_type,provider=provider,
        actualCalls=dict(allocation=allocate,constructor=construct,typeFromHandle=type_from_handle,registerWrap=register),
        staticClassCheckCalls=dict(systemType=type_check,provider=provider_check),
        adapterValue='same allocation RAX to constructor RCX; retained RDI to RegisterWrap RCX',
        originalKey='selected handle RBX to Type helper; exact Type result RAX saved RBX to RegisterWrap RDX',
        sameAllocatedAdapterToConstructorAndRegistration=True,sameOriginalKeyToRegistration=True,
        constructorCallExecuted=True,allocationNonnullRequired=True,compatibleNormalSourceDisjointHelpersRequired=True,
        systemTypeAndProviderInitializedRequired=True,nativeFrameBoundaryClaimed=False)


def _derive(image,original,wrapper,start,helpers):
    from scripts.game_data.il2cpp.formatter_direct_registration import _derive_program
    base=image.pe.image_base
    source=program([(base+start,image.pe.bytes_at_va(base+start,256))],base+start)
    return _derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__)


def derive(image,original,wrapper,candidates,helpers):
    found={};diagnostics=[]
    for candidate in candidates:
        if not candidate['rawHex'].lower().startswith('488b1d'):continue
        start=candidate['siteRva']-46
        if start<0:continue
        try:
            row=_derive(image,original,wrapper,start,helpers)
            need('exact-selected-key-site',candidate['siteRva'],row['key']['instructionRva']);found[start]=row
        except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:600])
    if len(found)!=1:raise ValueError(LABEL+'.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('explicit-checked-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-current-checked-declaration',actual,flow)
