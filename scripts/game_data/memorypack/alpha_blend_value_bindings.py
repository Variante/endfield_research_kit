"""Finite AlphaBlend56 complete-parent field/frame and own MC3 wire join.

The exact managed56 transfer preserves runtime-only floats and padding. Its
wire capability comes from the independent Alpha/Beyond curve owner. This
module grants neither a whole montage owner nor runtime provider selection.
"""
import hashlib,json
from scripts.game_data.memorypack import alpha_blend_value_components as owner
from scripts.game_data.memorypack import alpha_blend_value_codec as codec
from scripts.game_data.memorypack import generated_alpha_blend_field_sources as field

TYPE=owner.TYPE
CAPABILITY=codec.CAPABILITY
SCHEMA='endfield.alpha-blend-parent-value-components.v1'


def need(check,condition):
    if not condition:raise ValueError('alphaBlendValueBindings.'+check)


def require_setter(setter):
    """Replay full owned setter regions, including the untaken null edge."""
    method=setter.get('method',[]);program=setter.get('program',{});selected=program.get('selectedBytes',[])
    need('own-setter-method-and-path',len(method)==4 and all(type(method[i])is int for i in(0,3))and bool(selected))
    base=selected[0][0]-method[3];rows=setter.get('ordinarySourceRegions',[]);windows=setter.get('codeWindows',[])
    need('whole-unique-setter-regions',len(rows)==len(windows)>0 and len({a for a,h in rows})==len(rows))
    regions=[]
    for start,h in rows:
        raw=bytes.fromhex(h);matches=[w for w in windows if w.get('startRva')==start and w.get('endRva',0)-start==len(raw)
            and w.get('sha256','').upper()==hashlib.sha256(raw).hexdigest().upper()]
        need('whole-current-setter-window-hash',len(matches)==1);regions.append((base+start,raw))
    family=setter.get('sourceFamily',{})
    need('whole-owned-setter-family',family.get('schema')=='endfield.amd64-unwind-chain-family.v1'
        and family.get('selectedPrimaryRva')==method[3]
        and sorted(tuple(r['runtimeTriple'][:2])for r in family.get('ranges',[]))==sorted((w['startRva'],w['endRva'])for w in windows))
    getter=setter.get('getter');getter_target=base+getter['method'][3]if getter is not None else None
    by={a+i:b for a,raw in regions for i,b in enumerate(raw)}
    last=selected[-2][0];need('actual-terminal-barrier-E9',by.get(last)==0xe9 and selected[-2][1].lower()=='e9')
    barrier=last+5+int.from_bytes(bytes(by[last+i]for i in range(1,5)),'little',signed=True)
    actual=field.setter_program(regions,base+method[3],getter=getter_target,field=setter['fieldOffset'],barrier=barrier)
    need('complete-setter-byte-program-replayed',json.loads(json.dumps(actual))==program)
    if getter is None:
        holder=setter.get('directHolder',{})
        need('actual-literal-declared-holder',holder.get('fieldName')in('__instance','___instance')
            and holder.get('field')==[method[1],setter.get('targetField','').rsplit('::',1)[0],16]
            and holder.get('inheritedFieldAliasUsed')is False and holder.get('openGenericOffsetUsed')is False)
    return actual


def require_transfer(source,scope,read,pins,*,fragment=None):
    index=read.get('memberIndex');context=read.get('context')or{}
    closed=read.get('sourceContextMode')=='owned-closed-forwarder'
    if closed:
        from scripts.game_data.memorypack.montage_value_parent_sources import selection
        _,_,context,_=selection(scope,read,pins)
    need('complete-exact-parent-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==pins and source.get('sourceScope')==scope
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('same-exact-owned-Alpha-member',type(index)is int and 0<=index<len(source.get('orderedSourceReads',[]))
        and source['orderedSourceReads'][index]==read and scope.get('events')==source['orderedSourceReads'])
    setters=source.get('setters',[]);rich_setters=scope.get('richSetters',[])
    need('same-current-setter',index<len(setters)and index<len(rich_setters)and setters[index]==rich_setters[index])
    setter=setters[index];field.validate_event(read,setter);require_setter(setter)
    member=setter['member'];method=setter['method'];layout=setter['managedValueLayout']
    need('same-exact-named-field',method[0]==member.get('methodIndex')and method[1]==member.get('declaringWrapper')
        and method[2]=='set___'+str(read.get('fieldName'))+'__'and member.get('name')==read.get('fieldName')
        and member.get('declaredType')==TYPE and setter.get('targetField','').endswith('::'+str(read.get('fieldName')))
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('childGrammarAdmitted')is False
        and setter.get('factoryAdmitted')is False and layout.get('typeDefinition')==context.get('typeDefinition'))
    rich=scope.get('richProgram',{});selected=rich.get('selectedProgram',[])
    need('complete-source-and-field-program',rich.get('completeSelectedNormalProgram')is True
        and rich.get('childGrammarAdmitted')is False and rich.get('wholeOwnerAdmitted')is False and bool(selected))
    actual=[s for s in rich.get('sources',[])if s.get('memberIndex')==index]
    need('one-exact-hidden56-source',len(actual)==1 and actual[0].get('instruction')==read.get('instruction')
        and actual[0].get('resultAbi')=='hidden-local'and read.get('instruction')in selected)
    stores=[s for s in rich.get('fieldStores',[])if s.get('memberIndex')==index];covered=[]
    for s in stores:
        offset=s.get('sourceOffset');width=s.get('storedBytes')
        need('owned-Alpha-field-source-slice',type(offset)is int and type(width)is int and 0<=offset<offset+width<=56
            and s.get('instruction')in selected)
        covered.extend(range(offset,offset+width))
    need('exact-once-complete56-field-copy',len(covered)==56 and sorted(covered)==list(range(56)))
    hidden=[s for s in rich.get('hiddenSourceLocals',[])if s.get('memberIndex')==index]
    need('own-exact-hidden56-local',len(hidden)==1 and hidden[0].get('bytes')==56
        and type(hidden[0].get('displacement'))is int and 32<=hidden[0]['displacement']<256
        and hidden[0].get('sourceInstruction')==read.get('instruction')
        and hidden[0].get('nominalTypeName')==TYPE and hidden[0].get('nominalTypeDefinition')==layout.get('typeDefinition'))
    paths=source.get('programs',[])
    need('all-four-complete-parent-frames',len(paths)==4 and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
        and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    frame_bytes=scope.get('headerProof',{}).get('nullFrameBytes')
    need('exact-hidden-home-entry-RSP-coordinate',type(frame_bytes)is int and 32<=frame_bytes<4096)
    expected_home=[hidden[0]['displacement']-frame_bytes,56]
    need('hidden56-in-both-positive-frames',all(expected_home in p['frame'].get('hiddenSourceLocalHomes',[])
        for p in paths if not p['wrapperNull']))
    copies=[s for s in rich.get('sourceLocalCopies',[])if s.get('memberIndex')==index]
    from scripts.game_data.memorypack.montage_value_parent_sources import has_argument_copy
    if copies or(closed and has_argument_copy(scope,read,stores)):
        if closed:
            from scripts.game_data.memorypack.montage_value_parent_sources import require_copies
            require_copies(source,scope,read,pins,setter,hidden[0],copies,stores,frame_bytes)
        else:require_argument_copy(source,scope,read,setter,hidden[0],copies,fragment,pins,frame_bytes)
    return dict(memberIndex=index,fieldName=read['fieldName'],typeName=TYPE,managedBytes=56,resultAbi='hidden-local',
        referenceLaneOffsets=[8],paddingByteRanges=[[52,56]],sourceInstruction=read['instruction'],
        setterMethod=method,fieldOffset=setter['fieldOffset'],fieldStores=stores,hiddenSourceLocal=hidden[0],
        completeFieldTransferAndFrameProved=True,wireGrammarAdmitted=False)



def require_argument_copy(source,scope,read,setter,hidden,copies,fragment,pins,frame_bytes):
    from scripts.game_data.memorypack.generated_alpha_blend_transfer_sources import program
    need('explicit-own-CharAnim-copy-fragment',isinstance(fragment,dict)
        and fragment.get('schema')=='endfield.alpha-blend-parent-field-fragment.v1'
        and fragment.get('status')=='proved-conditional-alpha56-parent-field-fragment'
        and fragment.get('nativeInputs')==pins and fragment.get('wrapperName')==source.get('wrapperName')
        and source.get('wrapperName')=='Beyond.MemoryPack.Beyond_Gameplay_Core_CharInteractPerform_CharAnimActionDataForMemoryPack'
        and fragment.get('typeName')==TYPE and fragment.get('managedBytes')==56
        and fragment.get('selectedFieldTransferProved')is True and fragment.get('parentFieldAdmitted')is False
        and fragment.get('parentFrameAdmitted')is False and fragment.get('wholeOwnerAdmitted')is False)
    own=fragment.get('proof',{});actual=scope['managedValueSources'][str(read['memberIndex'])]
    need('same-whole-parent-and-own-field-fragment',own.get('callerMethod')==source.get('method')
        and[(w.get('startRva'),w.get('endRva'),w.get('sha256'))for w in own.get('callerWindows',[])]==
            [(w.get('startRva'),w.get('endRva'),w.get('sha256'))for w in source.get('codeWindows',[])]and own.get('setter')==setter
        and own.get('source')==actual and own.get('typedContext')==read.get('context')
        and own.get('typedRequest')==actual.get('proof',{}).get('typedRequest'))
    regions=own.get('callerRegions',[]);windows=own['callerWindows'];base=setter['program']['selectedBytes'][0][0]-setter['method'][3]
    need('whole-unique-parent-fragment-regions',len(regions)==len(windows)>0 and len({a for a,h in regions})==len(regions))
    for at,h in regions:
        raw=bytes.fromhex(h);need('whole-parent-fragment-window-hash',any(w.get('startRva')==at
            and w.get('endRva',0)-at==len(raw)and w.get('sha256','').upper()==hashlib.sha256(raw).hexdigest().upper()for w in windows))
    header=scope.get('headerProof',{});context=read['context'];selected=scope.get('selectedProgram',[])
    replay=program([(base+a,bytes.fromhex(h))for a,h in regions],base+context['instructionRva'],
        reader=header.get('readerRegister'),output=header.get('outputRegister'),context_cell=context['cellVa'],
        source=base+read['sourceTargetRva'],field=setter['fieldOffset'],barrier=base+actual['proof']['symbolRvas']['barrier'],
        hidden_local=hidden['displacement'],setter=base+setter['method'][3],argument_local=96)
    need('exact-copied-hidden56-fragment-replayed',json.loads(json.dumps(replay))==own.get('sourceProgram')
        and replay['namedSetterSelected']is True and replay['completeSourceBitsTransferredUnchanged']is True)
    owned={base+a+i:b for a,h in selected for i,b in enumerate(bytes.fromhex(h))}
    need('every-fragment-byte-in-complete-rich-parent',all(owned.get(a+i)==b for a,h in replay['selectedBytes']for i,b in enumerate(bytes.fromhex(h))))
    expected=[]
    for c in replay['sourceLocalCopies']:
        expected.append(dict(memberIndex=read['memberIndex'],displacement=c['displacement'],bytes=c['bytes'],
            sourceOffset=c['sourceOffset'],sourceRegister=c['sourceRegister'],
            storeInstruction=[c['instructionVa']-base,next(h for a,h in replay['selectedBytes']if a==c['instructionVa']).upper()],
            nominalTypeName=TYPE,nominalTypeDefinition=read['context']['typeDefinition']))
    need('exact-once56-argument-copy-slices',copies==expected
        and[(c['sourceOffset'],c['bytes'],c['displacement'])for c in copies]==[(0,16,96),(16,16,112),(32,16,128),(48,8,144)])
    need('every-copy-home-in-both-positive-frames',all(all([c['displacement']-frame_bytes,c['bytes']]in p['frame'].get('copiedSourceLocalHomes',[])
        for c in copies)for p in source['programs']if not p['wrapperNull']))
    return replay

def bind(source,scope,read,pins,usage,component,capability):
    need('own-independent-value-wire-component',capability==CAPABILITY
        and component.get('schema')=='endfield.alpha-blend-value-components.v1'
        and component.get('status')=='validated-conditional-alpha-blend-value-components'and component.get('nativeInputs')==pins
        and component.get('requiredExternalCapabilities')==[]and component.get('parentFieldAdmitted')is False
        and component.get('wholeOwnerAdmitted')is False)
    child=component.get('proof',{}).get('transfer',{});composed=owner.compose(pins,child)
    need('own-complete-child-wire-closure',component.get('capabilities')==composed['capabilities']
        and component.get('ownNestedCapabilities')==composed['ownNestedCapabilities'])
    cap=codec.require_capability(component['capabilities'][CAPABILITY]);transfer=require_transfer(source,scope,read,pins,fragment=component.get('proof',{}).get('parentFieldFragment'))
    actual=scope.get('managedValueSources',{}).get(str(read['memberIndex']),{});closed=read.get('sourceContextMode')=='owned-closed-forwarder'
    if closed:
        from scripts.game_data.memorypack.montage_value_parent_sources import selection
        _,actual,context,_=selection(scope,read,pins)
    else:context=read['context']
    argument=bytes.fromhex(context.get('argumentRawHex',''));load=bytes.fromhex(context.get('instructionHex',''))
    call=bytes.fromhex(read.get('instruction',[None,''])[1]);call_rva=read.get('instruction',[None])[0]
    need('literal-own-R8-context-and-E8-source',len(argument)==16 and argument[10:12]==bytes((17,128))
        and int.from_bytes(argument[:8],'little')==context.get('typeDefinition')
        and len(load)==7 and load[:3]==bytes.fromhex('4c8b05')
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
        and(closed or[context.get('instructionRva'),context.get('instructionHex')]in scope.get('selectedProgram',[]))
        and type(call_rva)is int and len(call)==5 and call[0]==0xe8
        and call_rva+5+int.from_bytes(call[1:],'little',signed=True)==read.get('sourceTargetRva'))
    need('same-native-actual-typed56-source',actual.get('schema')=='endfield.alpha-blend-value-transfer.v1'
        and actual.get('nativeInputs')==pins and actual.get('status')=='proved-conditional-alpha-blend-value56-read'
        and actual.get('typeName')==TYPE and actual.get('managedBytes')==56 and actual.get('actualSourceProved')is True
        and actual.get('resultAbi')=='hidden-local'and actual.get('wireGrammarAdmitted')is False
        and actual.get('parentFieldAdmitted')is False and actual.get('wholeOwnerAdmitted')is False
        and actual.get('referenceLaneOffsets')==[8]and actual.get('paddingByteRanges')==[[52,56]]
        and actual.get('sourceTargetRva')==cap.get('valueSourceTargetRva')
        and(closed or actual.get('sourceTargetRva')==read.get('sourceTargetRva'))
        and actual.get('readerMethodDefinition')==context.get('methodSpec',[None])[0]==usage.get('methodSpec',[None])[0]
        and actual.get('proof',{}).get('typedRequest')==usage and context.get('methodSpec')==usage.get('methodSpec')
        and actual['proof']['childSource']['proof']['layout']==child['proof']['childSource']['proof']['layout']
        and actual['proof']['symbolRvas']['dispatch']==cap['valueDispatcherTargetRva']
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE]))
    need('same-parent-source-and-child-MC3',owner.compose(pins,actual)==composed)
    return dict(fieldName=read['fieldName'],typeName=TYPE,capability=capability,
        readerMethodDefinition=actual['readerMethodDefinition'],sourceTargetRva=read['sourceTargetRva'],
        managedValueTransfer=transfer,managedValueCapabilityShape=cap,ordinaryReferenceIdentityClaimed=False)


def derive(image,pins,*,parent_source,member_index):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    _publication_gate(image,pins);scope=parent_source['sourceScope'];read=parent_source['orderedSourceReads'][member_index]
    closed=read.get('sourceContextMode')=='owned-closed-forwarder'
    if closed:
        from scripts.game_data.memorypack.montage_value_parent_sources import selection
        actual,nested,context,_=selection(scope,read,pins)
        usage=derive_typed_usage_context(image,context['instructionRva'],label='alphaBlendValueBindings.internal')
        need('fresh-exact-internal-typed-request',usage==nested['proof']['typedRequest'])
        target=nested['sourceTargetRva']
    else:
        usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='alphaBlendValueBindings')
        target=read['sourceTargetRva']
    component=owner.derive(image,pins,typed_request=usage,source_target=image.pe.image_base+target,count_limit=10000)
    copies=[c for c in scope.get('richProgram',{}).get('sourceLocalCopies',[])if c.get('memberIndex')==member_index]
    if copies and not closed:
        from scripts.game_data.memorypack.generated_alpha_blend_transfer_sources import derive as derive_fragment
        component['proof']['parentFieldFragment']=derive_fragment(image,pins,wrapper_name=parent_source['wrapperName'])
    image.check_windows(parent_source['codeWindows'],label='alphaBlendValueBindings.parent')
    binding=bind(parent_source,scope,read,pins,usage,component,CAPABILITY);_publication_gate(image,pins)
    return dict(schema=SCHEMA,status='validated-conditional-alpha56-parent-value-components',nativeInputs=pins,
        parentWrapper=parent_source['wrapperName'],binding=binding,capabilities=component['capabilities'],
        proof=dict(parentSource=parent_source,childComponent=component),parentFieldAdmitted=True,wholeOwnerAdmitted=False,
        evidenceBoundary='Complete selected initialized parent source/field/local/all four frames joins independently fresh Alpha MC3/default56 and Beyond curve MC3/raw-key-array framing. Runtime callback/provider and helper conditions remain; no whole parent grammar or publication is granted.')
