"""Exact Quaternion raw16 source, local and whole named-field compiler join.

This is a finite ReadUnmanaged<Quaternion> branch. A managed16 reference value,
Vector3 source, inline input or matching width cannot supply this operation.
Fresh native source owners establish the bytes; this pure join checks their
actual request, complete source, local, setter and all enclosing normal frames.
"""
from scripts.game_data.memorypack import leveldata_quaternion_value_sources as quaternion


def need(check,condition):
    if not condition:raise ValueError('generatedHiddenQuaternionComponents.'+check)


def _compile_member(source,scope,read,pins):
    index=read['memberIndex'];value=scope.get('valueTypeSources',{}).get(str(index),{})
    typed=value.get('typedSource',{});actual=typed;closed=read.get('sourceContextMode')=='owned-closed-forwarder'
    context=read.get('context',{});closed_base=None
    if closed:
        from scripts.game_data.memorypack import leveldata_quaternion_forwarder_sources as forwarder
        need('exact-closed-Quaternion-member',read.get('context')is None
            and forwarder.owns_member(source.get('wrappedType'),read.get('fieldName'),read.get('declaredType')))
        closed_base=forwarder.verify(typed,pins);actual=typed['proof']['nestedSource'];context=typed['proof']['internalContext']
    else:need('ordinary-Quaternion-context-mode',read.get('sourceContextMode')is None and isinstance(context,dict))
    proof=actual.get('proof',{});program=value.get('sourceProgram',{})
    layout=value.get('layout',{});request=proof.get('typedRequest',{});selected=program.get('selectedBytes',[])
    need('same-source-and-nominal',source.get('nativeInputs')==scope.get('nativeInputs')==typed.get('nativeInputs')==pins
        and source.get('sourceScope')==scope and read==source.get('orderedSourceReads',[])[index]
        and read.get('kind')=='value16:'+quaternion.TYPE and read.get('declaredType')==quaternion.TYPE
        and read.get('mode')=='typed-hidden-value'and read.get('resultAbi')=='hidden-local'
        and read.get('actualSourceProved')is True
        and type(read.get('wireBytes'))is int and read['wireBytes']==16
        and value.get('typeName')==quaternion.TYPE and value.get('actualSourceProved')is True
        and value.get('wireBytes')==16 and value.get('resultAbi')=='hidden-local-to-owned-field'
        and layout.get('typeName')==quaternion.TYPE and layout.get('managedBytes')==16
        and layout.get('wireReadAdmitted')is False and layout.get('typeDefinition')==typed.get('typeDefinition')
        and layout.get('fields')==[[axis,'float',16+4*i]for i,axis in enumerate('xyzw')]
        and program==proof.get('actualProgram')and bool(selected))
    base=selected[0][0]-actual['targetRva'];at,encoded=read['instruction'];raw=bytes.fromhex(encoded)
    need('same-closed-helper-and-nested-image-base',not closed or base==closed_base)
    need('actual-source-call',type(at)is int and len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==typed['targetRva']==read.get('sourceTargetRva')
        and request.get('instructionRva')==context.get('instructionRva')
        and request.get('instructionHex')==context.get('instructionHex')
        and request.get('methodSpec')==context.get('methodSpec'))
    quaternion.bind(context,base+actual['targetRva'],actual,base=base)
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    replay=quaternion.program([(a,bytes.fromhex(h))for a,h in selected],base+actual['targetRva'],proof['readerOffsets'],
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,proof.get('actualWindows',[]),base))
    replay['selectedBytes']=[[a,h]for a,h in replay['selectedBytes']]
    need('complete-owned-hidden16-source',replay==program)
    rich=scope.get('richProgram',{});locals_=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
    sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    need('complete-local-and-field-transfer',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')and len(locals_)==len(sources)==len(stores)==1
        and locals_[0].get('bytes')==16 and type(locals_[0].get('displacement'))is int
        and 32<=locals_[0]['displacement']<256 and locals_[0].get('sourceInstruction')==read['instruction']
        and sources[0].get('instruction')==read['instruction']and sources[0].get('resultAbi')=='hidden-local'
        and stores[0].get('sourceOffset')==0 and stores[0].get('storedBytes')==16
        and all(any(type(offset)is int and type(width)is int and width==16
            for offset,width in p['frame'].get('hiddenSourceLocalHomes',[]))for p in source['programs']if not p['wrapperNull']))
    setter=source['setters'][index];nominal=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('own-ordinary-Quaternion-setter',setter.get('storedBytes')==16 and setter.get('member',{}).get('declaredType')==quaternion.TYPE
        and setter.get('targetField')==source['wrappedType']+'::'+read['fieldName']
        and setter.get('incomingValueStoredUnchanged')is True
        and len(nominal)==16 and nominal[10:12]==bytes((17,128))
        and int.from_bytes(nominal[:8],'little')==layout['typeDefinition'])
    if setter.get('profile')=='cached-getter-setter':
        from scripts.game_data.memorypack.generated_hidden_vector_components import cached_setter
        cached_setter(source,scope,read,setter,pins,type_name=quaternion.TYPE,width=16)
    else:
        need('own-direct-Quaternion-setter',setter.get('profile')=='direct-base-holder-setter'
        and setter.get('program',{}).get('sourceSlices')==[[0,16]]
        and setter['program'].get('completeSourceBitsStoredUnchanged')is True
        and setter['program'].get('normalFrameAndReturn')is True)
    return 'unity-quaternion-raw16'


def compile_member(source,scope,read,pins):
    """Preserve a bounded, attributable refusal before a full owner retry."""
    try:return _compile_member(source,scope,read,pins)
    except ValueError as error:
        import json
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        index=read.get('memberIndex');setters=source.get('setters',[])
        setter=setters[index]if type(index)is int and 0<=index<len(setters)else{}
        diagnostic=CensusGateError('generatedHiddenQuaternionComponents.hidden-field',
            source='scripts/game_data/memorypack/generated_hidden_quaternion_components.py',
            expected='own Quaternion source/context, hidden16 local/field/frame transfer and independently replayed direct or coherent cached setter',
            actual=dict(reason=str(error)[:1400],setterProfile=setter.get('profile'),
                storedBytes=setter.get('storedBytes'),setterMethod=setter.get('method')))
        diagnostic.diagnostic.update(validator='generatedHiddenQuaternionComponents',failedGate=str(error).split(':',1)[0],
            wrapperName=source.get('wrapperName'),typeName=source.get('wrappedType'),
            fieldName=read.get('fieldName'),memberIndex=index,nativeInputs=pins,
            sourceWindows=source.get('codeWindows',[])[:8],setterWindows=setter.get('codeWindows',[])[:8])
        diagnostic.args=(json.dumps(diagnostic.diagnostic,sort_keys=True),)
        raise diagnostic from error
