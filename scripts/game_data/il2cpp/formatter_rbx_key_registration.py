"""Closed adapter retained in RBX, direct RCX key, ready provider state.

The exact selected caller has no explicit class checks. System.Type and
provider initialization are conditions, never claimed observations.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.formatter_key_receiver_registration import need

PROFILE='direct-adapter-rbx-key-rcx-ready-statics.v1'


def program(regions,entry):
    g=BytesPath(regions,entry)
    def usage(opcode):
        at=g.at;cell=g.relative(opcode);return dict(instruction=at,cell=cell)
    allocation=usage('488b0d');allocate=g.relative('e8')
    g.take('488bd8','4885c0');g.branch('0f84',False)
    constructor=usage('488b15');g.take('488bc8');construct=g.relative('e8')
    key=usage('488b0d');g.take('33d2');type_from_handle=g.relative('e8')
    g.take('4533c0','488bd0','488bcb');register=g.relative('e8')
    return dict(selectedBytes=g.seen,end=g.at,allocation=allocation,constructor=constructor,key=key,
        actualCalls=dict(allocation=allocate,constructor=construct,typeFromHandle=type_from_handle,registerWrap=register),
        staticRoles=[],systemTypeClassUsagePresent=False,providerClassUsagePresent=False,
        sameAllocatedAdapterToConstructorAndRegistration=True,sameOriginalKeyToRegistration=True,
        constructorCallExecuted=True,allocationNonnullRequired=True,
        explicitSystemTypeInitializedRequired=True,explicitProviderInitializedRequired=True,
        systemTypeAndProviderInitializedRequired=True,nativeFrameBoundaryClaimed=False)


def _derive(image,original,wrapper,start,helpers):
    from bisect import bisect_right
    from scripts.game_data.il2cpp.formatter_direct_registration import _derive_program
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_guarded_registration import _reference_original
    ctx=NativeReferenceContext(image);pointer=_reference_original(ctx,original);base=image.pe.image_base
    entries=image.unwind_index.entries;begins=sorted(entries);position=bisect_right(begins,start)-1
    if position<0 or not entries[begins[position]][0]<=start<entries[begins[position]][1]:
        raise ValueError('rbxKeyRegistration.owned-caller')
    from scripts.game_data.memorypack.pointer_param import owned
    caller=owned(image,base+image.unwind_index.resolve(begins[position]))
    source=program(caller['regions'],base+start)
    value=_derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__,static_roles=())
    need('actual-own-reference-key',pointer,ctx.type_pointer(value['key']['typeIndex']))
    value['callerCodeWindows']=caller['windows']
    return value


def derive(image,original,wrapper,candidates,helpers):
    found={};errors=[]
    for c in candidates:
        if not c['rawHex'].lower().startswith('488b0d')or c['siteRva']<39:continue
        start=c['siteRva']-39
        try:
            p=_derive(image,original,wrapper,start,helpers)
            need('same-own-key-site',c['siteRva'],p['key']['instructionRva']);found[start]=p
        except(ValueError,KeyError,IndexError,TypeError)as error:errors.append(str(error)[:500])
    if len(found)!=1:raise ValueError('rbxKeyRegistration.unique-source:'+str((len(found),errors[:3])))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('rbx-key-profile',PROFILE,flow.get('profile'))
    need('same-current-rbx-key-source',_derive(image,flow['originalType'],flow['wrapperType'],
        flow['window']['startRva'],flow['helperMethods']),flow)
