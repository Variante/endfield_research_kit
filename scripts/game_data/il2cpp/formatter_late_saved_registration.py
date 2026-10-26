"""Exact reference registration saving RBX immediately before construction.

The allocated adapter is retained in RDI and passed in RCX to its actual
closed constructor. Saving incoming RBX to its own stack home occurs between
that argument setup and the call. The later Original handle and Type result
use RBX, with both explicit class checks retaining their exact warmed joins.
Normal compatible helpers and coherent initialized classes remain conditions;
this bounded registration program grants no enclosing frame or live selection.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

PROFILE='direct-reference-adapter-late-rbx-save.v1'
LABEL='lateSavedReferenceRegistration'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def program(regions,entry):
    g=BytesPath(regions,entry)
    def usage(opcode):
        site=g.at;cell=g.relative(opcode);return dict(instruction=site,cell=cell)
    def initialized():
        g.take('83b9e000000000');warm=g.relative('75',1);cold=g.relative('e8')
        need('exact-static-warm-join',g.at,warm)
        return cold
    allocation=usage('488b0d');allocate=g.relative('e8')
    g.take('488bf8','4885c0');g.branch('74',False,1)
    constructor=usage('488b15');g.take('488bc8','48895c2430');construct=g.relative('e8')
    system_type=usage('488b0d');key=usage('488b1d');type_init=initialized()
    g.take('33d2','488bcb');type_from_handle=g.relative('e8')
    provider=usage('488b0d');g.take('488bd8');provider_init=initialized()
    g.take('4533c0','488bd3','488bcf');register=g.relative('e8')
    return dict(selectedBytes=g.seen,end=g.at,allocation=allocation,constructor=constructor,key=key,
        systemType=system_type,provider=provider,
        actualCalls=dict(allocation=allocate,constructor=construct,typeFromHandle=type_from_handle,registerWrap=register),
        unselectedClassInitCalls=dict(systemType=type_init,provider=provider_init),
        savedIncomingRbxHomeOffset=48,savedIncomingRbxBeforeConstructor=True,
        sameAllocatedAdapterToConstructorAndRegistration=True,sameOriginalKeyToRegistration=True,
        constructorCallExecuted=True,allocationNonnullRequired=True,
        systemTypeAndProviderInitializedRequired=True,compatibleNormalSourceDisjointHelpersRequired=True,
        nativeFrameBoundaryClaimed=False)


def _derive(image,original,wrapper,start,helpers):
    from scripts.game_data.il2cpp.formatter_direct_registration import _derive_program
    from scripts.game_data.il2cpp.formatter_guarded_registration import _reference_original
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    context=NativeReferenceContext(image);pointer=_reference_original(context,original);base=image.pe.image_base
    source=program([(base+start,image.pe.bytes_at_va(base+start,256))],base+start)
    result=_derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__)
    need('own-ordinary-reference-key',pointer,context.type_pointer(result['key']['typeIndex']))
    return result


def derive(image,original,wrapper,candidates,helpers):
    found={};diagnostics=[]
    for candidate in candidates:
        if not candidate['rawHex'].lower().startswith('488b1d'):continue
        start=candidate['siteRva']-47
        if start<0:continue
        try:
            row=_derive(image,original,wrapper,start,helpers)
            need('exact-selected-key-site',candidate['siteRva'],row['key']['instructionRva']);found[start]=row
        except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:700])
    if len(found)!=1:raise ValueError(LABEL+'.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('explicit-late-save-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-current-late-save-declaration',actual,flow)
