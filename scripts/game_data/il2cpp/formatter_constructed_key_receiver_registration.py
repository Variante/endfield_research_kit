"""Exact RCX-key eager registration for a proved closed reference carrier.

The instruction program is shared with the ordinary CLASS profile. This
separate gate requires the selected GENERICINST reference key and reciprocal
definition/arguments. It grants neither heap layout nor a child wire grammar.
"""
from scripts.game_data.il2cpp.formatter_key_receiver_registration import program
from scripts.game_data.il2cpp.formatter_constructed_guarded_registration import require_carrier

PROFILE='direct-constructed-adapter-key-in-rcx-single-static-check.v1'
LABEL='constructedKeyReceiverRegistration'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def _derive(image,original,wrapper,start,helpers):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.formatter_direct_registration import _derive_program
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
    base=image.pe.image_base;context=NativeReferenceContext(image)
    source=program([(base+start,image.pe.bytes_at_va(base+start,256))],base+start)
    usage=derive_typed_usage_context(image,source['key']['instruction']-base,label=LABEL)
    need('own-actual-Type-key',(2,original),(usage['tag'],usage['typeName']))
    pointer=context.type_pointer(usage['typeIndex']);raw=image.pe.bytes_at_va(pointer,16)
    carrier=closed_generic_reference_pointer_extent(context,pointer);require_carrier(original,raw,carrier)
    result=_derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__,static_roles=('provider',))
    need('same-selected-key-pointer',pointer,context.type_pointer(result['key']['typeIndex']))
    result.update(constructedReferenceKey=carrier,constructedHeapLayoutAdmitted=False)
    return result


def derive(image,original,wrapper,candidates,helpers):
    found={};diagnostics=[]
    for candidate in candidates:
        if not candidate['rawHex'].lower().startswith('488b0d'):continue
        start=candidate['siteRva']-35
        if start<0:continue
        try:
            result=_derive(image,original,wrapper,start,helpers)
            need('actual-key-site',candidate['siteRva'],result['key']['instructionRva']);found[start]=result
        except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:900])
    if len(found)!=1:raise ValueError(LABEL+'.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
    return next(iter(found.values()))


def validate(image,flow,*,label):
    need('explicit-constructed-key-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-selected-declaration',actual,flow)
