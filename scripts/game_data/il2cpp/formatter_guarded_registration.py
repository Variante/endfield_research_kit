"""Exact guarded reference-adapter registration with explicit static checks.

The selected normal program skips only its owned null-allocation throw/CC,
retains the allocated adapter in RDI, and calls the actual closed constructor
with RCX=RDI. Its nominal Original is an ordinary, nongeneric reference class;
the actual key pointer must be that class's own by-value type record. The
existing reference constructor proof independently binds the canonical entry,
closed MethodInfo and slot12 context before the same adapter/key reach
RegisterWrap. No value constructor or value-width inference is substituted.

Exact bytes and typed argument flow are proved on the selected path.
Compatible normal helper returns, coherent initialized static classes and
live provider selection remain conditional. Whole native frame, runtime
allocation/initialization and child grammar remain unresolved here.
"""
from scripts.game_data.il2cpp.formatter_checked_value_registration import program as _source_program

PROFILE='direct-reference-adapter-nonnull-skip-static-checks.v1'
LABEL='guardedReferenceRegistration'


def need(check,expected,actual):
    if type(expected)is not type(actual)or expected!=actual:
        raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+' actual='+str(actual)[:240])


def _reference_original(context,original):
    definition=context.index.types[original]
    need('nongeneric-reference-class',(-1,False,False,0),
        (definition.generic_container_index,context.is_value_type(original),context.is_enum(original),definition.flags&0x20))
    pointer=context.type_pointer(definition.byval_type_index)
    raw=context.image.pe.bytes_at_va(pointer,16)
    need('ordinary-reference-type-record',(16,18,0),(len(raw),raw[10]if len(raw)>10 else None,raw[11]if len(raw)>11 else None))
    need('own-current-reference-definition',definition.index,int.from_bytes(raw[:8],'little'))
    need('own-current-reference-name',original,context.type_name(definition.byval_type_index))
    return pointer


def _derive(image,original,wrapper,start,helpers):
    from scripts.game_data.il2cpp.formatter_direct_registration import _derive_program
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    context=NativeReferenceContext(image);pointer=_reference_original(context,original)
    base=image.pe.image_base
    source=_source_program([(base+start,image.pe.bytes_at_va(base+start,256))],base+start)
    result=_derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__)
    need('actual-key-is-own-reference-record',pointer,context.type_pointer(result['key']['typeIndex']))
    return result


def derive(image,original,wrapper,candidates,helpers):
    """Raw exact key cells select candidates; bytes and nominal ABI decide."""
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
    need('explicit-guarded-reference-profile',PROFILE,flow.get('profile'))
    actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
    need('exact-current-guarded-reference-declaration',actual,flow)
