"""Finite named raw24 camera source-to-parent-field compiler join.

Only the actual InitialParam nominal closed source can select this operation.
Its independent raw24/Advance proof, whole hidden local and owned named setter
are mandatory. The unrelated MC7 wrapper/default and other managed widths do
not supply a field grammar.
"""
from scripts.game_data.memorypack import skill_camera_initial_raw_sources as raw_source


def need(check,condition):
    if not condition:raise ValueError('generatedCameraInitialComponents.'+check)


def _compile_member(source,scope,read,pins):
    index=read['memberIndex'];value=scope.get('valueTypeSources',{}).get(str(index),{})
    typed=value.get('typedSource',{});layout=value.get('layout',{})
    need('same-whole-source-and-nominal',source.get('nativeInputs')==scope.get('nativeInputs')==pins
        and source.get('sourceScope')==scope and type(index)is int
        and source.get('orderedSourceReads',[])[index]==scope.get('events',[])[index]==read
        and read.get('kind')=='value24:'+raw_source.TYPE and read.get('declaredType')==raw_source.TYPE
        and read.get('mode')=='typed-hidden-value'and read.get('resultAbi')=='hidden-local'
        and read.get('wireBytes')==24 and read.get('actualSourceProved')is True
        and value.get('typeName')==raw_source.TYPE and value.get('actualSourceProved')is True
        and value.get('wireBytes')==24 and value.get('resultAbi')=='hidden-local-to-owned-field'
        and read.get('nominalHiddenSource')==typed)
    base=raw_source.verify(typed,pins);own=typed['proof'];nested=own.get('nestedSource',typed)
    need('independent-nominal-layout-and-source',layout==nested['proof']['nominalLayout']
        and value.get('sourceProgram')==own.get('actualProgram')
        and typed.get('targetRva')==read.get('sourceTargetRva'))
    if typed.get('contextMode')=='owned-closed-forwarder':
        need('own-forwarder-not-caller-context',read.get('sourceContextMode')=='owned-closed-forwarder'
            and read.get('context')is None)
    else:
        context=read.get('context',{});raw_source.bind(context,base+typed['targetRva'],typed,base=base)
        need('own-caller-context',read.get('sourceContextMode')is None
            and own['typedRequest']['methodSpec']==context.get('methodSpec')
            and own['typedRequest']['instructionRva']==context.get('instructionRva'))
    at,encoded=read['instruction'];raw=bytes.fromhex(encoded)
    need('actual-owned-source-call',type(at)is int and len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==typed['targetRva'])
    rich=scope.get('richProgram',{});locals_=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
    sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index];setter=source['setters'][index]
    slices=sorted((r.get('sourceOffset'),r.get('storedBytes'))for r in stores)
    named=False
    if slices==[(0,24)]:
        site,h=stores[0]['instruction'];raw=bytes.fromhex(h)
        named=(type(site)is int and len(raw)==5 and raw[0]==232
            and site+5+int.from_bytes(raw[1:],'little',signed=True)==setter.get('method',[None]*4)[3])
    positive=[p for p in source['programs']if not p['wrapperNull']]
    need('whole-hidden24-local-and-field',bool(positive)and rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')and len(locals_)==len(sources)==1
        and locals_[0].get('bytes')==24 and type(locals_[0].get('displacement'))is int
        and 32<=locals_[0]['displacement']<256 and locals_[0].get('sourceInstruction')==read['instruction']
        and sources[0].get('instruction')==read['instruction']and sources[0].get('resultAbi')=='hidden-local'
        and(slices==[(0,16),(16,8)]or named)
        and all(any(type(offset)is int and type(width)is int and width==24
            for offset,width in p['frame'].get('hiddenSourceLocalHomes',[]))for p in positive))
    nominal=bytes.fromhex(setter.get('parameterTypeRecordHex',''));program=setter.get('program',{})
    if setter.get('profile')=='cached-getter-setter'and'closedReferenceCarrier'in setter:
        from scripts.game_data.memorypack.generated_closed_camera_property_components import verify
        from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
        from scripts.game_data.memorypack.generated_vector_member_sources import nonnull
        verify(source,setter,read,layout,base)
        need('same-fresh-closed-property',scope.get('richSetters',[])[index]==setter
            and len(nominal)==16 and nominal[10:12]==bytes((17,128))
            and int.from_bytes(nominal[:8],'little')==layout['typeDefinition']
            and setter.get('nominalValueLayout')==layout and named)
        paths=source.get('programs',[])
        need('four-complete-closed-property-parent-frames',source.get('completeSelectedCallerAdmitted')is True
            and len(paths)==4 and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
            and all(p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
        local=locals_[0];home=local['displacement']-scope['headerProof']['nullFrameBytes']
        copies=[r for r in rich.get('sourceLocalCopies',[])if r.get('memberIndex')==index]
        need('exact-whole-owned-copy-to-setter-local',[(x.get('sourceOffset'),x.get('bytes'),x.get('displacement'))for x in copies]==[(0,16,32),(16,8,48)]
            and all(x.get('nominalTypeName')==raw_source.TYPE and x.get('nominalTypeDefinition')==layout['typeDefinition']
                and x.get('storeInstruction')in scope['selectedProgram']for x in copies)
            and all([home,24]in p['frame'].get('hiddenSourceLocalHomes',[])
                and all([x['displacement']-scope['headerProof']['nullFrameBytes'],x['bytes']]in p['frame'].get('copiedSourceLocalHomes',[])for x in copies)for p in positive))
        selected=scope['selectedProgram'];regions=[(base+a,bytes.fromhex(h))for a,h in selected]
        g=_owned_setter_trace(regions,base+at+5,scope['codeWindows'],base)
        g.take('4885f6');nonnull(g)
        g.take('0f1000','488d542420','4533c0','f20f104810','488bce','0f29442420','f20f114c2430')
        g.call(base+setter['method'][3])
        need('actual-complete-24-local-copy-and-named-call',
            [[a-base,h.upper()]for a,h in(g.seen[-4],g.seen[-3])]==[x['storeInstruction']for x in copies]
            and [g.seen[-2][0]-base,(g.seen[-2][1]+g.seen[-1][1]).upper()]==stores[0]['instruction'])
        return 'camera-initial-raw24'
    need('own-complete-named24-setter',setter.get('profile')=='direct-base-holder-setter'
        and setter.get('storedBytes')==24 and setter.get('member',{}).get('declaredType')==raw_source.TYPE
        and setter.get('targetField')==source['wrappedType']+'::'+read['fieldName']
        and setter.get('incomingValueStoredUnchanged')is True and len(nominal)==16
        and nominal[10:12]==bytes((17,128))and int.from_bytes(nominal[:8],'little')==layout['typeDefinition']
        and program.get('sourceSlices')==[[0,16],[16,8]]
        and program.get('completeSourceBitsStoredUnchanged')is True and program.get('normalFrameAndReturn')is True)
    return 'camera-initial-raw24'


def compile_member(source,scope,read,pins):
    try:return _compile_member(source,scope,read,pins)
    except(ValueError,KeyError,IndexError,TypeError)as error:
        import json
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        failure=CensusGateError('generatedCameraInitialComponents.field',source=source.get('wrapperName','unknown')+'::Deserialize',
            expected='Exact InitialParam raw24/Advance source, coherent nominal request and whole hidden local/named setter/frame.',
            actual=dict(wrapperName=source.get('wrapperName'),fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:1000]))
        failure.diagnostic.update(validator='generatedCameraInitialComponents',nativeInputs=pins,
            sourceInstruction=read.get('instruction'),sourceWindows=source.get('codeWindows',scope.get('codeWindows',[]))[:4])
        failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error
