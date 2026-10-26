"""Finite closed Body32/Alpha56 caller joins; no nominal or wire inference.

The closed source owner supplies and replays its internal MethodInfo. Parent
calls, argument copies and physical/lifetime frame receipts remain separate.
"""
from scripts.game_data.memorypack import generated_module_frame_sources as frames
from scripts.game_data.memorypack import generated_field_lifetime_sources as lifetimes


def need(check,condition):
    if not condition:raise ValueError('montageValueParent.'+check)


def selection(scope,read,pins):
    """Return the independently verified nested source and its real context."""
    name=read.get('declaredType');actual=scope.get('managedValueSources',{}).get(str(read.get('memberIndex')), {})
    need('explicit-closed-context-only',read.get('sourceContextMode')=='owned-closed-forwarder'and read.get('context')is None)
    if name=='Beyond.Gameplay.BodyTypeDef':
        from scripts.game_data.memorypack.body_type_closed_value_sources import verify
        event_key='bodyTypeClosedForwarderSource'
    elif name=='Beyond.Gameplay.View.Animation.AlphaBlend':
        from scripts.game_data.memorypack.alpha_blend_closed_value_sources import verify
        event_key='alphaBlendClosedForwarderSource'
    else:raise ValueError('montageValueParent.unsupported-nominal')
    base=verify(actual,pins);proof=actual['proof'];nested=proof['nestedSource'];context=proof['internalContext']
    need('same-owned-closed-source',read.get(event_key)==actual
        and actual.get('sourceTargetRva')==read.get('sourceTargetRva')
        and actual.get('readerMethodDefinition')==nested.get('readerMethodDefinition')
        and proof.get('typedRequest')==nested.get('proof',{}).get('typedRequest'))
    call=read.get('instruction',[])
    need('actual-outer-E8-to-closed-helper',isinstance(call,list)and len(call)==2 and type(call[0])is int
        and isinstance(call[1],str)and len(bytes.fromhex(call[1]))==5 and bytes.fromhex(call[1])[0]==0xe8
        and call[0]+5+int.from_bytes(bytes.fromhex(call[1])[1:],'little',signed=True)==actual['sourceTargetRva']
        and call in scope.get('selectedProgram',[])and call in scope.get('richProgram',{}).get('selectedProgram',[]))
    return actual,nested,context,base


def has_argument_copy(scope,read,stores):
    """Spot the finite local-store instructions so omitted receipts refuse."""
    selected=scope['richProgram']['selectedProgram'];first=selected.index(read['instruction'])
    last=max(selected.index(s['instruction'])for s in stores)
    field_sites={tuple(s['instruction'])for s in stores}
    return any(bytes.fromhex(h).startswith(tuple(bytes.fromhex(p)for p in('0f29','0f11','f30f7f','f20f11')))
        for at,h in selected[first+1:last]if(at,h)not in field_sites)


def require_copies(source,scope,read,pins,setter,hidden,copies,stores,frame_bytes):
    """Replay finite argument slices and rejoin their full positive frames."""
    closed=read.get('sourceContextMode')=='owned-closed-forwarder'
    if closed:actual,nested,context,base=selection(scope,read,pins)
    else:
        # An ordinary Body call has a real outer R8 MethodInfo. Its returned
        # value may be loaded from that exact hidden RSP home before the two
        # argument stores; it does not acquire a fabricated closed context.
        from scripts.game_data.memorypack import body_type_value_sources as body
        actual=scope.get('managedValueSources',{}).get(str(read.get('memberIndex')),{});context=read.get('context')or{}
        need('own-ordinary-Body32-copy-source',read.get('declaredType')==body.TYPE and read.get('managedBytes')==32
            and read.get('sourceContextMode')is None and actual.get('schema')==body.SCHEMA
            and actual.get('status')=='proved-conditional-nominal-managed32-source'and actual.get('nativeInputs')==pins
            and actual.get('actualSourceProved')is True and actual.get('sourceTargetRva')==read.get('sourceTargetRva')
            and actual.get('proof',{}).get('nominal')==setter.get('managedValueLayout')
            and context.get('fullTypeName')==body.TYPE and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
            and context.get('methodName')=='ReadValue'and context.get('register')=='r8'and context.get('typeKind')==17
            and context.get('typeDefinition')==setter['managedValueLayout']['typeDefinition'])
        usage=actual.get('proof',{}).get('typedRequest',{})
        need('real-ordinary-Body32-context-and-source-call',tuple(usage.get(k)for k in
            ('tag','typeName','methodName','classArguments','methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[body.TYPE])
            and all(usage.get(k)==context.get(k)for k in('instructionRva','instructionHex','methodSpec'))
            and actual.get('readerMethodDefinition')==usage.get('methodSpec',[None])[0]
            and[context.get('instructionRva'),context.get('instructionHex')]in scope.get('selectedProgram',[]))
        selected_bytes=setter['program']['selectedBytes'];base=selected_bytes[0][0]-setter['method'][3]
        call=bytes.fromhex(read['instruction'][1])
        need('actual-ordinary-Body32-E8',len(call)==5 and call[0]==0xe8
            and read['instruction'][0]+5+int.from_bytes(call[1:],'little',signed=True)==actual['sourceTargetRva'])
    name=read['declaredType'];width=read['managedBytes'];index=read['memberIndex']
    slices=[(0,16,'xmm0'),(16,16,'xmm1')]
    if name=='Beyond.Gameplay.View.Animation.AlphaBlend':slices += [(32,16,'xmm0'),(48,8,'xmm1')]
    need('once-only-finite-copy-slices',[(c.get('sourceOffset'),c.get('bytes'),c.get('sourceRegister'))for c in copies]==slices)
    rich=scope['richProgram'];selected=rich['selectedProgram'];alias=rich.get('sourceFrameAlias')
    need('same-complete-parent-selected-program',selected==scope.get('selectedProgram'))
    need('one-whole-named-setter-transfer',len(stores)==1 and stores[0].get('sourceOffset')==0 and stores[0].get('storedBytes')==width)
    argument=copies[0].get('displacement')
    need('literal-contiguous-owned-argument',type(argument)is int and argument>=32 and argument+width<=frame_bytes
        and (argument+width<=hidden['displacement']or hidden['displacement']+width<=argument))
    if alias is not None:
        origin=frames.require_descriptor(alias,scope['headerProof'])
        need('same-finite-caller-frame',alias['ownerType']==source.get('wrappedType')
            and alias['memberCount']==scope.get('memberCount')and alias['currentRspBytes']==frame_bytes)
        frames.require_hidden(alias,index,name,width,hidden['displacement'])
        need('same-hidden-RBP-coordinate',hidden.get('frameAddress')==dict(baseRegister='rbp',
            displacement=hidden['displacement']-origin,rspDisplacement=hidden['displacement']))
    else:
        need('only-Body32-RSP-copy',name=='Beyond.Gameplay.BodyTypeDef'and width==32)
    for c in copies:
        offset,size,register=c['sourceOffset'],c['bytes'],c['sourceRegister'];displacement=c.get('displacement');marker=c.get('storeInstruction')
        need('same-closed-nominal-copy',c.get('memberIndex')==index and c.get('nominalTypeName')==name
            and c.get('nominalTypeDefinition')==context['typeDefinition']and displacement==argument+offset
            and marker in selected)
        if alias is not None:
            address=c.get('frameAddress',{});spec=frames.copy_spec(alias,index,name,size,offset,register,address.get('displacement'))
            need('literal-RBP-copy-program',address==dict(baseRegister='rbp',displacement=displacement-origin,rspDisplacement=displacement)
                and marker[1].lower()==spec['instructionHex'].lower()
                and spec['sourceHome']==hidden['displacement']and spec['argumentHome']==argument)
        else:
            need('no-RBP-coordinate-on-RSP-copy',c.get('frameAddress')is None)
            modrm='44'if displacement<128 else'84';disp=displacement.to_bytes(1 if displacement<128 else 4,'little',signed=True).hex()
            if register=='xmm1':modrm=f'{int(modrm,16)+8:02x}'
            need('literal-Body32-RSP-store',marker[1].lower()in[prefix+modrm+'24'+disp for prefix in('0f29','0f11','f30f7f')])
    # Replay every instruction between the actual returned hidden pointer and
    # the named setter: no unproved register clobber or intermediate call.
    first=selected.index(read['instruction']);last=selected.index(stores[0]['instruction']);simd={};seen=[]
    need('copy-after-source-before-named-setter',first<last
        and all(a+len(bytes.fromhex(h))==b for(a,h),(b,_)in zip(selected[first:last],selected[first+1:last+1])))
    by_copy={c['storeInstruction'][0]:c for c in copies}
    source_loads={'0f1000':('xmm0',0,16),'0f104810':('xmm1',16,16),
        '0f104020':('xmm0',32,16),'f20f104830':('xmm1',48,8)}
    if not closed:
        source_loads={}
        for offset,register in((0,'xmm0'),(16,'xmm1')):
            displacement=hidden['displacement']+offset;modrm=0x44 if displacement<128 else 0x84
            if register=='xmm1':modrm+=8
            instruction='0f10'+bytes((modrm,0x24)).hex()+displacement.to_bytes(1 if displacement<128 else 4,'little',signed=True).hex()
            source_loads[instruction]=(register,offset,16)
    if alias is not None:
        delta=argument-origin;argument_lea='488d55'+delta.to_bytes(1,'little',signed=True).hex()
    else:
        argument_lea='488d54'+('24'+argument.to_bytes(1,'little',signed=True).hex())if argument<128 else'488d9424'+argument.to_bytes(4,'little',signed=True).hex()
    setup={'4885db','4885f6','4885ff','4533c0','4533c9','488bcb','488bce','488bcf',argument_lea}
    for site in selected[first+1:last]:
        raw=bytes.fromhex(site[1]);h=raw.hex();c=by_copy.get(site[0])
        if c is not None:
            need('same-live-returned-source-slice',simd.get(c['sourceRegister'])==(c['sourceOffset'],c['bytes']))
            seen.append(c);continue
        if h in source_loads:
            register,offset,size=source_loads[h];need('load-within-own-returned-value',offset+size<=width)
            simd[register]=(offset,size);continue
        need('only-nonclobbering-named-setter-setup',h in setup or(len(raw)==6 and raw[:2]==bytes.fromhex('0f84'))or(len(raw)==2 and raw[0]==0x74))
    call=bytes.fromhex(stores[0]['instruction'][1]);at=stores[0]['instruction'][0]
    need('actual-owned-named-setter-call',seen==copies and len(call)==5 and call[0]==0xe8
        and at+5+int.from_bytes(call[1:],'little',signed=True)==setter['method'][3])
    for path in source['programs']:
        if path['wrapperNull']:continue
        frame=path['frame'];path_selected=path.get('selectedProgram',[])
        need('same-full-positive-copy-fragment',read['instruction']in path_selected and stores[0]['instruction']in path_selected
            and path_selected[path_selected.index(read['instruction']):path_selected.index(stores[0]['instruction'])+1]==selected[first:last+1])
        if alias is not None:
            need('same-positive-frame-alias',frame.get('sourceFrameAlias')==alias
                and all(alias[k]in scope['headerProof'].get('prologue',[])and alias[k]in path_selected for k in('baseAliasInstruction','entryRspAliasInstruction')))
        need('every-physical-copied-home',all([c['displacement']-frame_bytes,c['bytes']]in frame.get('copiedSourceLocalHomes',[])for c in copies))
        rows=[dict(va=hex(base+a),bytes=h,text='')for a,h in path['selectedProgram']]
        hidden_proof=lifetimes.hidden_certificates(rows,base=base,hidden_locals=[hidden],field_stores=stores)
        copy_proof=lifetimes.montage_copy_certificates(rows,base=base,hidden_locals=[hidden],copied_locals=copies,hidden_certificates=hidden_proof)
        if alias is not None or frame.get('hiddenSourceLocalLifetimes'):
            need('same-complete-hidden-source-lifetime',[p for p in frame.get('hiddenSourceLocalLifetimes',[])if p.get('memberIndex')==index]==hidden_proof)
        # RBP NPC argument homes can be reused later only after the separately
        # checked field lifetime. Older RSP copies need no retirement claim.
        if alias is not None or frame.get('copiedSourceLocalLifetimes'):
            need('same-complete-copied-local-lifetime',[p for p in frame.get('copiedSourceLocalLifetimes',[])if p.get('memberIndex')==index]==copy_proof)
    return dict(sourceLocalCopies=copies,argumentLocalDisplacement=argument,completeCopiedLocalFramesProved=True)
