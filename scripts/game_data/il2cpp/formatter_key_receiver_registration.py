"""Exact reference registration with Original handle directly in RCX.

The nonnull allocated adapter is retained in RDI and passed unchanged to the
actual closed canonical reference constructor. The own ordinary Original key
is loaded directly into RCX for System.Type.GetTypeFromHandle; its returned
Type is saved in RBX across the provider's explicit class check and supplied
with the retained adapter to RegisterWrap. This source does not load or check
a System.Type class. Coherent initialized System.Type/provider state, normal
compatible helpers and nonaliasing storage remain explicit conditions. No
enclosing frame, runtime provider selection or child wire grammar is admitted.
"""
from scripts.game_data.il2cpp.formatter_guarded_registration import _reference_original
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

PROFILE='direct-adapter-key-in-rcx-single-static-check.v1'
LABEL='keyReceiverReferenceRegistration'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def program(regions,entry):
    g=BytesPath(regions,entry)
    def usage(opcode):
        site=g.at;cell=g.relative(opcode);return dict(instruction=site,cell=cell)
    allocation=usage('488b0d');allocate=g.relative('e8');g.take('488bf8','4885c0');g.branch('74',False,1)
    constructor=usage('488b15');g.take('488bc8');construct=g.relative('e8')
    key=usage('488b0d');g.take('33d2');type_from_handle=g.relative('e8')
    provider=usage('488b0d');g.take('488bd8');provider_check=g.relative('e8')
    g.take('4533c0','488bd3','488bcf');register=g.relative('e8')
    return dict(selectedBytes=g.seen,end=g.at,allocation=allocation,constructor=constructor,key=key,provider=provider,
        actualCalls=dict(allocation=allocate,constructor=construct,typeFromHandle=type_from_handle,registerWrap=register),
        staticClassCheckCalls=dict(provider=provider_check),staticRoles=['provider'],systemTypeClassUsagePresent=False,
        originalKeyPassedDirectlyInRcx=True,sameAllocatedAdapterToConstructorAndRegistration=True,
        sameOriginalKeyToRegistration=True,constructorCallExecuted=True,allocationNonnullRequired=True,
        explicitSystemTypeInitializedRequired=True,systemTypeAndProviderInitializedRequired=True,
        compatibleNormalSourceDisjointHelpersRequired=True,nativeFrameBoundaryClaimed=False)


def _derive(image,original,wrapper,start,helpers):
    from scripts.game_data.il2cpp.formatter_direct_registration import _derive_program
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    context=NativeReferenceContext(image);pointer=_reference_original(context,original);base=image.pe.image_base
    source=program([(base+start,image.pe.bytes_at_va(base+start,256))],base+start)
    result=_derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__,static_roles=('provider',))
    need('actual-key-is-own-reference-record',pointer,context.type_pointer(result['key']['typeIndex']))
    return result


def derive(image,original,wrapper,candidates,helpers):
    found={};diagnostics=[]
    for candidate in candidates:
        if not candidate['rawHex'].lower().startswith('488b0d'):continue
        start=candidate['siteRva']-35
        if start<0:continue
        try:
            row=_derive(image,original,wrapper,start,helpers)
            need('exact-selected-key-site',candidate['siteRva'],row['key']['instructionRva']);found[start]=row
        except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:800])
    if len(found)!=1:raise ValueError(LABEL+'.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('explicit-key-receiver-reference-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-current-key-receiver-declaration',actual,flow)
