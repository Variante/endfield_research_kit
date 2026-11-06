"""Own a leaf constructor's exact closed ancestor MethodInfo and tail.

The selected registered callee's complete owned body is pinned independently.
Normal constructor effects remain a condition, as for ordinary owned original
constructors. This proves no instantiated fields or wire grammar.
"""
import hashlib
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions, entry):
    g=BytesPath(regions,entry)
    cell=g.relative('488b15');target=g.relative('e9')
    return dict(selectedBytes=g.seen,methodInfoCellVa=cell,tailTargetVa=target,
                sameWholeReceiverRcx=True,stackAndNonvolatilesUnchanged=True,
                incomingReaderArgumentPassed=False,programBytes=12)


def derive(image,pins,*,context,method,original):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.reference_param_profile import _method_row
    def need(check,condition):
        if not condition:raise ValueError('typedConstructorTail.'+check)
    base=image.pe.image_base;pointer=image.method_pointer_va(method)
    raw=image.pe.bytes_at_va(pointer,12);path=program([(pointer,raw)],pointer)
    usage=derive_typed_usage_context(image,pointer-base,label='typedConstructorTail.context')
    args=usage.get('classArguments',[])
    parent=usage['typeName']+'<'+','.join(args)+'>'
    need('own-closed-ancestor',usage.get('tag')==6 and usage.get('methodName')=='.ctor'
         and usage.get('methodArguments')==[] and bool(args)
         and context.parent(original)==parent)
    selected=image.metadata.methods[usage['methodSpec'][0]]
    scalar.owned_method_abi(image,context,selected.index,selected.declaring_type,
                          ('void',1,False),[],'typedConstructorTail.ancestorABI')
    observed=GenericEntries(image).observe(selected.index,args,[])
    need('one-selected-typed-registration',len(observed)==1 and bool(observed[0]['pointer']))
    registration=observed[0]
    need('actual-registered-ancestor-entry',registration['pointer']==path['tailTargetVa'])
    body=members._body(image,registration['pointer'],pins=pins)
    target_method=_method_row(image,selected);target_method[3]=registration['pointer']-base
    return dict(method=_method_row(image,method),codeWindows=[dict(startRva=pointer-base,
        endRva=pointer-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper(),
        boundary='complete closed-ancestor constructor leaf tail; physical extent unproved')],
        typedAncestorTail=dict(program=path,typedRequest=usage,registration=registration,
            targetMethod=target_method,closedAncestorType=parent,foldedAliasesDoNotSupplyIdentity=True,
            identitySource='actual incoming closed MethodInfo and reciprocal metadata ancestor; selected registration proves target only'),
        delegatedConstructor=dict(method=target_method,family=body['family'],codeWindows=body['windows'],
            completeCurrentOwnedBodyPinned=True,normalConstructorReturnRequired=True,runtimeEffectsProved=False),
        completeReachableEntryProgramProved=True,physicalFunctionExtentProved=False,
        normalConstructorReturnRequired=True,runtimeExecutionKnown=False)
