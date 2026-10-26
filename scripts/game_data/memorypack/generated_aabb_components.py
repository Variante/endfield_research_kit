"""Exact Node.bounds raw16 source, local, setter and full caller-frame join."""
import json
from scripts.game_data.memorypack import generated_aabb_field_sources as field,leveldata_aabb_raw_sources as source

WIRE='story-aabb-raw16'


def need(check,condition):
    if not condition:raise ValueError('generatedAabbComponents.'+check)


def norm(value):return json.loads(json.dumps(value))


def compile_member(owner,scope,read,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
    from scripts.game_data.memorypack.generated_vector_member_sources import base_vector_setter_program,setter_program
    index=read.get('memberIndex');context=read.get('context')or{}
    need('same-complete-own-Node-member',field.owns_member(owner.get('wrappedType'),read.get('fieldName'),read.get('declaredType'))
        and owner.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
        and owner.get('completeSelectedCallerAdmitted')is True and owner.get('childGrammarAdmitted')is False
        and owner.get('wholeOwnerAdmitted')is False and type(index)is int and 0<=index<len(owner.get('orderedSourceReads',[]))
        and owner['orderedSourceReads'][index]==read==scope.get('events',[])[index]
        and read.get('kind')=='value16:'+source.TYPE and read.get('mode')=='typed-hidden-value'
        and read.get('actualSourceProved')is True and read.get('resultAbi')=='hidden-local'
        and type(read.get('wireBytes'))is int and read['wireBytes']==16 and read.get('sourceContextMode')is None)
    value=scope.get('valueTypeSources',{}).get(str(index),{});actual=value.get('typedSource',{});p=actual.get('proof',{})
    nominal=value.get('layout',{});program=value.get('sourceProgram',{});selected=program.get('selectedBytes',[])
    need('own-independent-current-AABB-source',actual.get('nativeInputs')==pins and actual.get('schema')==source.SCHEMA
        and value.get('typeName')==source.TYPE and value.get('actualSourceProved')is True and value.get('wireBytes')==16
        and value.get('resultAbi')=='hidden-local-to-owned-field'and program==p.get('actualProgram')and bool(selected)
        and nominal==dict(p.get('nominalLayout',{}),wireReadAdmitted=False)
        and nominal==read.get('nominalValueLayout')and nominal.get('referenceLaneOffsets')==nominal.get('paddingByteRanges')==[])
    base=selected[0][0]-actual['targetRva'];at,encoded=read['instruction'];raw=bytes.fromhex(encoded)
    need('actual-Reader-E8-and-MethodInfo',type(at)is int and len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==actual.get('targetRva')==read.get('sourceTargetRva')
        and all(p.get('typedRequest',{}).get(k)==context.get(k)for k in('instructionRva','instructionHex','methodSpec')))
    source.bind(context,base+actual['targetRva'],actual,base=base)
    raw_regions=regions(p.get('actualWindows',[]),p.get('actualRegions',[]),base,'AABB-actual-raw16')
    replay=source.program(raw_regions,base+actual['targetRva'],p['readerOffsets'],advance=program['advanceTargetVa'])
    need('whole-actual-raw-source-replayed',norm(replay)==program)
    verify_advance(p['advanceSource'],dict(readerOffsets=p['readerOffsets'],advanceTargetVa=program['advanceTargetVa']),pins,base)
    setter=owner['setters'][index];carrier=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('same-own-whole-setter',setter==scope['richSetters'][index]and setter.get('nominalValueLayout')==nominal
        and setter.get('storedBytes')==16 and setter.get('incomingValueStoredUnchanged')is True
        and setter.get('member',{}).get('declaredType')==source.TYPE
        and setter.get('targetField')==field.PARENT+'::'+field.FIELD and setter.get('fieldOffset')==16
        and len(carrier)==16 and carrier[10:12]==bytes((17,128))and int.from_bytes(carrier[:8],'little')==nominal['typeDefinition'])
    method=setter.get('method',[])
    need('own-named-setter-identity',len(method)==4 and method[0]==setter['member'].get('methodIndex')
        and method[1]==setter['member'].get('declaringWrapper')and method[2]=='set___bounds__')
    setter_regions=regions(setter.get('codeWindows',[]),setter.get('ordinarySourceRegions',[]),base,'AABB-own-setter')
    if setter.get('profile')=='direct-base-holder-setter':
        replay=base_vector_setter_program(setter_regions,base+method[3],holder=16,field=16,width=16)
        need('same-own-direct-holder',owner.get('lifecycle',{}).get('baseHolder')==[owner['wrapperName'],field.PARENT,16])
    else:
        getter=setter.get('getter')or{};life=owner.get('lifecycle',{})
        need('own-complete-coherent-cached-getter',setter.get('profile')=='cached-getter-setter'
            and getter.get('method')==life.get('coherentGetter',{}).get('method')
            and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
            and getter.get('coherentNonNullSamePointerReturn')is True
            and all(getter.get('program',{}).get(k)is True for k in('fullSameReferenceReturned','entryRspRestored','normalReturn')))
        replay=setter_program(setter_regions,base+method[3],getter=base+getter['method'][3],field=16,width=16)
    need('complete-own-setter-byte-program',norm(replay)==setter.get('program'))
    rich=scope.get('richProgram',{});local=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
    copy=[r for r in rich.get('sourceLocalCopies',[])if r.get('memberIndex')==index]
    flows=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    need('whole-hidden16-local-copy-and-field-flow',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')and len(local)==len(copy)==len(flows)==1
        and local[0].get('displacement')==32 and local[0].get('bytes')==16
        and local[0].get('sourceInstruction')==flows[0].get('instruction')==read['instruction']
        and local[0].get('nominalTypeName')==source.TYPE and local[0].get('nominalTypeDefinition')==nominal['typeDefinition']
        and copy[0].get('sameOwnedHiddenLocalCopy')is True and copy[0].get('displacement')==32 and copy[0].get('bytes')==16
        and copy[0].get('sourceOffset')==0 and copy[0].get('sourceRegister')=='xmm0'
        and copy[0].get('parentType')==field.PARENT and copy[0].get('fieldName')==field.FIELD
        and len(stores)==1 and stores[0].get('sourceOffset')==0 and stores[0].get('storedBytes')==16
        and stores[0].get('instruction')in rich['selectedProgram'])
    paths=owner.get('programs',[])
    need('all-four-complete-own-parent-frames',len(paths)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p.get('frame',{}).get('entryRspRestored')is True
            and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and all(any(size==16 for home,size in p['frame'].get('hiddenSourceLocalHomes',[]))for p in paths if not p['wrapperNull']))
    return WIRE
