"""Own the current Timeline/ForceSync zero-original factory programs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPES=frozenset(('Beyond.Gameplay.Core.TimelineAction+TimelineActionData',
                 'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData'))


def program(regions,entry,s,*,constructor):
    if type(constructor)is not bool:raise ValueError('buffTimelineFactory.literal-profile')
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20')if constructor else g.take('4053','4883ec20')
    ready=g.relative('803d')+1;g.take('00','488bf9'if constructor else'488bd9');g.branch('75',True,1)
    site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0')
    g.branch('74',False,1)if constructor else g.branch('75',True,1)
    if constructor:
        disabled=g.relative('833d')+1;g.take('00','48894710')
        if disabled!=s['disabled']:raise ValueError('buffTimelineFactory.same-disabled-collector')
        g.branch('74',True,1);g.take('488b5c2438','4883c420','5f','c3')
    else:
        g.take('488d4b10','48894310','4883c420','5b')
        if g.relative('e9')!=s['barrier']:raise ValueError('buffTimelineFactory.same-tail-barrier')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,allocation=dict(site=site,cell=cell),
        allocationTarget=s['allocate'],baseHolderOffset=16,typedCacheOffset=None,
        sameAllocatedOriginalStored=True,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],
        entryRspRestored=True,allNonvolatilesRestored=True,
        normalReturn=constructor,normalReturnViaBarrier=not constructor,
        originalConstructorCalled=False,allocationConditional='Normal fresh zeroed allocation of the exact typed Original; initialized metadata and disabled collector.')


def prove(image,ctx,wrapper,body,symbols,original_ctor):
    if wrapper.wrapped_type not in TYPES:return NotImplemented
    from scripts.game_data.memorypack.pointer_param import methods
    methods_=methods(image,wrapper)
    constructor=body['pointer']==image.method_pointer_va(methods_['.ctor'])
    if not constructor and body['pointer']!=image.method_pointer_va(methods_['CreateInstance']):
        raise ValueError('buffTimelineFactory.actual-owned-method')
    actual=program(body['regions'],body['pointer'],symbols,constructor=constructor)
    return dict(program=actual,originalConstructor=None,
        proof=dict(wrapperName=wrapper.name,typeName=wrapper.wrapped_type,
            completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,
            sourceWindows=body['windows'],originalConstructorCalled=False))
