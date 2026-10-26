"""Pure finite Clip raw36 source/local/cached-field compiler composition.

This is not a native gate. Fresh generated caller and nominal source owners
must supply the inputs. Typed hidden36 and literal inline36 are distinct source
profiles; both must reach their actual named field through all36 bytes and
complete parent frames. Marshal40 and the separate MC7 wrapper grant no bytes.
"""
import hashlib
import json

from scripts.game_data.memorypack import skill_animation_clip_raw_sources as raw_source
from scripts.game_data.memorypack.generated_inline_record_components import _coverage,_owned_setter_trace


def need(check,condition):
    if not condition:raise ValueError('skillAnimationClipComponents.'+check)


def _whole(source,scope,read,pins):
    index=read.get('memberIndex');need('literal-member-index',type(index)is int and 0<=index<len(source.get('orderedSourceReads',[])))
    need('complete-current-caller-scope',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==pins and source.get('sourceScope')==scope
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False and scope.get('sourceScopeAdmitted')is True
        and source['orderedSourceReads'][index]==scope.get('events',[])[index]==read
        and read.get('kind')=='value36:'+raw_source.TYPE and read.get('declaredType')==raw_source.TYPE
        and type(read.get('wireBytes'))is int and read['wireBytes']==36 and read.get('actualSourceProved')is True)
    paths=source.get('programs',[])
    need('four-complete-parent-frames',len(paths)==4 and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
        and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    rich=scope.get('richProgram',{})
    need('complete-native-value-flow',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==scope.get('selectedProgram'))
    value=scope.get('valueTypeSources',{}).get(str(index),{});layout=value.get('layout',{})
    need('same-own-physical36-layout',value.get('typeName')==raw_source.TYPE and value.get('actualSourceProved')is True
        and type(value.get('wireBytes'))is int and value['wireBytes']==36 and layout.get('typeName')==raw_source.TYPE
        and layout.get('fields')==[list(f)for f in raw_source.FIELDS]and type(layout.get('typeDefinition'))is int
        and layout.get('boxedBytes')==52 and layout.get('managedPayloadBytes')==layout.get('managedBytes')==36
        and layout.get('marshaledNativeBytes')==40 and layout.get('marshaledSizeUsedForWireWidth')is False
        and layout.get('referenceLaneOffsets')==[]and layout.get('paddingByteRanges')==raw_source.PADDING
        and layout.get('vector3',{}).get('fields')==[[axis,'float',16+4*i]for i,axis in enumerate(('x','y','z'))]
        and layout['vector3'].get('managedBytes')==12)
    return index,rich,value,layout


def _setter(source,scope,read,layout,base):
    from scripts.game_data.memorypack.generated_animation_clip_field_sources import setter_program,direct_setter_program,validate_event
    index=read['memberIndex'];setter=source['setters'][index];validate_event(read,setter)
    getter=setter.get('getter')or{};life=source.get('lifecycle',{})
    need('exact-own-named-field',setter.get('nominalValueLayout')==layout and setter.get('incomingValueStoredUnchanged')is True
        and setter.get('targetField')==source['wrappedType']+'::'+read['fieldName']
        and setter.get('member',{}).get('name')==read['fieldName']and setter['member'].get('declaredType')==raw_source.TYPE
        and setter['method'][1]==source['wrapperName']
        and setter['member'].get('methodIndex')==setter['method'][0]
        and scope.get('richSetters',[])[index]==setter)
    direct=setter.get('profile')=='direct-base-holder-setter'
    if direct:
        holder=setter.get('directHolder',{});leaf=setter.get('directGetValue',{});get_value=life.get('GetValue',{})
        need('exact-own-direct-holder',setter.get('sourceProfile')=='direct-clip36-setter'and not getter
            and life.get('directHolderMode')is True and holder.get('field')==life.get('baseHolder')
            and holder.get('field')==[source['wrapperName'],source['wrappedType'],16]
            and holder.get('inheritedFieldAliasUsed')is False and holder.get('openGenericOffsetUsed')is False
            and setter.get('program',{}).get('holderOffset')==16
            and leaf.get('method')==get_value.get('method')and leaf.get('method',[None,None])[1]==source['wrapperName'])
        at=leaf['method'][3];instructions=leaf.get('program',{}).get('instructions',[])
        need('same-closed-direct-holder-GetValue',instructions==[[at,'488B4110'],[at+4,'C3']]
            and get_value.get('program',{}).get('fullReferenceOutput')is True
            and get_value['program'].get('normalReturnViaGetter')is False
            and[[a-base,h.upper()]for a,h in get_value['program'].get('selectedBytes',[])]==instructions)
    else:
        need('exact-own-cached-field',setter.get('profile')=='cached-getter-value36-setter'
        and setter['method'][1]==getter['method'][1]
        and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
        and getter.get('coherentNonNullSamePointerReturn')is True
        and getter.get('program',{}).get('fullSameReferenceReturned')is True
        and getter['program'].get('entryRspRestored')is True and getter['program'].get('normalReturn')is True)
    windows=setter.get('codeWindows',[]);regions=setter.get('ordinarySourceRegions',[])
    need('whole-owned-named-setter',bool(windows)and len(windows)==len(regions)and len({a for a,h in regions})==len(regions))
    for at,h in regions:
        raw=bytes.fromhex(h);matching=[w for w in windows if w.get('startRva')==at and w.get('endRva',0)-at==len(raw)]
        need('exact-setter-window-bytes',type(at)is int and len(matching)==1
            and hashlib.sha256(raw).hexdigest().upper()==matching[0].get('sha256'))
    args=dict(field=setter['fieldOffset'])
    if not direct:args['getter']=base+getter['method'][3]
    replay=(direct_setter_program if direct else setter_program)([(base+at,bytes.fromhex(h))for at,h in regions],
        base+setter['method'][3],**args)
    need('complete-setter-copy-frame-replayed',json.loads(json.dumps(replay))==setter.get('program'))
    return setter


def _compile_member(source,scope,read,pins):
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    index,rich,value,layout=_whole(source,scope,read,pins);typed=read.get('mode')=='typed-hidden-value'
    positive=[p for p in source['programs']if p['wrapperNull']is False]
    if typed:
        actual=value.get('typedSource',{});base=raw_source.verify(actual,pins);own=actual['proof']
        need('same-actual-typed36-source',value.get('resultAbi')=='hidden-local-to-owned-field'
            and read.get('resultAbi')=='hidden-local'and read.get('nominalHiddenSource')==actual
            and value.get('sourceProgram')==own['actualProgram']and read.get('sourceContextMode')is None
            and layout==dict(own['nominalLayout'],managedBytes=36)and read.get('sourceTargetRva')==actual['targetRva'])
        context=read.get('context',{});raw_source.bind(context,base+actual['targetRva'],actual,base=base)
        need('same-live-caller-typed-context',context.get('instructionRva')==own['typedRequest']['instructionRva']
            and context.get('instructionHex')==own['typedRequest']['instructionHex']and context.get('methodSpec')==own['typedRequest']['methodSpec'])
        site,h=read['instruction'];encoded=bytes.fromhex(h)
        owned={at+i:b for at,h in scope.get('selectedProgram',[])for i,b in enumerate(bytes.fromhex(h))}
        need('actual-owned-source-E8',type(site)is int and len(encoded)==5 and encoded[0]==232
            and site+5+int.from_bytes(encoded[1:],'little',signed=True)==actual['targetRva']
            and all(owned.get(site+i)==b for i,b in enumerate(encoded)))
        usage_at=context['instructionRva'];usage=bytes.fromhex(context['instructionHex'])
        need('actual-owned-source-MethodInfo',type(usage_at)is int and usage_at<site
            and all(owned.get(usage_at+i)==b for i,b in enumerate(usage)))
        locals_=[x for x in rich.get('hiddenSourceLocals',[])if x.get('memberIndex')==index]
        frame_bytes=scope.get('headerProof',{}).get('nullFrameBytes')
        need('whole-36-byte-hidden-local',len(locals_)==1 and type(locals_[0].get('bytes'))is int and locals_[0]['bytes']==36
            and type(locals_[0].get('displacement'))is int and locals_[0]['displacement']>=32
            and locals_[0].get('sourceInstruction')==read['instruction']
            and locals_[0].get('nominalTypeName')==raw_source.TYPE and locals_[0].get('nominalTypeDefinition')==layout['typeDefinition']
            and type(frame_bytes)is int and frame_bytes>=locals_[0]['displacement']+36
            and all(any(type(at)is int and type(width)is int and width==36 and at==locals_[0]['displacement']-frame_bytes
                for at,width in p['frame'].get('hiddenSourceLocalHomes',[]))for p in positive))
    else:
        macro=read.get('inlineSourceProgram',{});site,h=read['instruction'];base=macro.get('guardInstructionVa',0)-site
        need('finite-actual-inline36',read.get('mode')=='buffered-called-advance-clip36'and read.get('context')is None
            and read.get('inlineNominalLayout')==layout and value.get('resultAbi')=='inline-bits-to-owned-field'
            and(scope.get('headerProof',{}).get('readerRegister'),scope.get('headerProof',{}).get('outputRegister'))==('rbx','rdi')
            and bytes.fromhex(h)==bytes((131,123,macro['readerOffsets']['bufferLength'],36))
            and value.get('sourceProgram')==macro)
        selected=scope.get('selectedProgram',[])
        replay=raw_source.capture_program([(base+a,bytes.fromhex(b))for a,b in selected],base+site,macro['readerOffsets'],
            path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope.get('codeWindows',[]),base))
        need('exact-inline36-capture-replayed',json.loads(json.dumps(replay))==macro)
        from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
        advance=read.get('inlineAdvanceSource',{});verify_advance(advance,macro,pins,base)
        need('same-independent-inline36-Advance',value.get('advanceSource')==advance)
        need('whole-preserved-inline-register-frame',all({'xmm6','xmm7'}<=set(p['frame'].get('restoredVectorHomes',{}))
            and 'rbp'in{r for r,home in p['frame'].get('savedHomes',[])}for p in positive))
    setter=_setter(source,scope,read,layout,base);selected=scope.get('selectedProgram',[])
    if not typed:
        transfer=raw_source.inline_program([(base+a,bytes.fromhex(b))for a,b in selected],base+site,macro['readerOffsets'],
            field=setter['fieldOffset'],path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope.get('codeWindows',[]),base))
        need('same-inline36-owned-getter-and-field',transfer.get('getterTargetVa')==base+setter['getter']['method'][3]
            and transfer.get('advanceTargetVa')==macro['advanceTargetVa']and transfer.get('completeSourceBitsStoredUnchanged')is True)
    owned={base+at+i:b for at,h in selected for i,b in enumerate(bytes.fromhex(h))}
    stores=[s for s in rich.get('fieldStores',[])if s.get('memberIndex')==index]
    sources=[s for s in rich.get('sources',[])if s.get('memberIndex')==index]
    need('all-and-only-36-field-bits',len(sources)==1 and sources[0].get('instruction')==read['instruction']
        and _coverage(stores,36,'sourceOffset','storedBytes')
        and sorted((s['sourceOffset'],s['storedBytes'])for s in stores)==[(0,16),(16,16),(32,4)])
    if not typed:need('same-inline36-helper-in-rich-flow',sources[0].get('program')==read['inlineSourceProgram']
        and sources[0].get('actualAdvanceSource')==read['inlineAdvanceSource'])
    prefixes=('0f1181','0f1189','8981')if typed and setter.get('profile')=='direct-base-holder-setter' else\
        ('0f1180','0f1188','8988')if typed else('0f11b0','0f11b8','89a8')
    expected=[_displacement(prefix,setter['fieldOffset']+offset)for prefix,offset in zip(prefixes,(0,16,32),strict=True)]
    for store,encoding in zip(sorted(stores,key=lambda s:s['sourceOffset']),expected,strict=True):
        at,h=store['instruction'];raw=bytes.fromhex(h)
        need('actual-named-36-byte-field-store',type(at)is int and raw.hex()==encoding
            and all(owned.get(base+at+i)==b for i,b in enumerate(raw)))
    return 'animation-clip-raw36'


def compile_member(source,scope,read,pins):
    try:return _compile_member(source,scope,read,pins)
    except(ValueError,KeyError,IndexError,TypeError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        failure=CensusGateError('skillAnimationClipComponents.field',source=source.get('wrapperName','unknown')+'::Deserialize',
            expected='Exact nominal inline/typed raw36 source, full36 local/field coverage, own named setter and all four frames.',
            actual=dict(wrapperName=source.get('wrapperName'),fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:1000]))
        failure.diagnostic.update(validator='skillAnimationClipComponents',nativeInputs=pins,sourceInstruction=read.get('instruction'),
            sourceWindows=source.get('codeWindows',scope.get('codeWindows',[]))[:4])
        failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error
