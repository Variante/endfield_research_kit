"""Current concrete generated formatter, holder, getter and factory sources.

Concrete ReadPackable callbacks do not require an unused Original adapter
registration. Their own slot5, ordinary source ABI and exact typed construction
remain independently checked. Reader prefixes and children stay separate.
"""
from __future__ import annotations
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.memorypack import generated_member_sources as members

LABEL='generatedLifecycleSource'


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:700])


def _peek(g,n=1):return bytes(g.bytes[g.at+i]for i in range(n))


def _initialized(g):
    if _peek(g)==b'\x75':g.branch('75',True,1)
    elif _peek(g)==b'\x74':g.branch('74',False,1)
    elif _peek(g,2)==b'\x0f\x85':g.branch('0f85',True)
    else:g.branch('0f84',False)


def _nonnull(g):
    if _peek(g)==b'\x75':g.branch('75',True,1)
    elif _peek(g)==b'\x74':g.branch('74',False,1)
    elif _peek(g,2)==b'\x0f\x85':g.branch('0f85',True)
    else:g.branch('0f84',False)


def factory_program(regions,entry,barrier,*,ctor,original_ctor,base_slot,cache_slot,original_initializers=None,base_ctor=None):
    """Typed cached construction, with an optional exact original constructor."""
    need('factory-role-domain',type(ctor)is bool and type(base_slot)is int and type(cache_slot)is int and
        16<=base_slot<cache_slot<128 and(original_ctor is None or type(original_ctor)is int and original_ctor>0))
    need('owned-original-initializers',original_initializers is None or type(original_initializers)is list)
    need('explicit-base-constructor-role',base_ctor is None or ctor and type(base_ctor)is int and base_ctor>0)
    probe=BytesPath(regions,entry)
    if original_ctor is None and original_initializers:
        from scripts.game_data.memorypack.generated_cached_register_default_sources import program as mixed_register_defaults
        try:return mixed_register_defaults(regions,entry,barrier,ctor=ctor,base_slot=base_slot,cache_slot=cache_slot,initializers=original_initializers)
        except(ValueError,KeyError,IndexError):pass
    if ctor and base_ctor is not None and original_ctor is not None and _peek(probe,5)==bytes.fromhex('48895c2408')and _peek(probe,20)[17:20]==bytes.fromhex('488bd9'):
        from scripts.game_data.memorypack.generated_called_original_factory_sources import program
        return program(regions,entry,barrier,base_ctor=base_ctor,original_ctor=original_ctor,base_slot=base_slot,cache_slot=cache_slot)
    if original_ctor is None and original_initializers and _peek(probe,5)==bytes.fromhex('48895c2408')and _peek(probe,21)[20:21]==b'\xbb'and(
            ctor or any(store.get('bytes')!=4 for store in original_initializers)):
        from scripts.game_data.memorypack.generated_ancestor_scalar_factory_sources import program
        return program(regions,entry,barrier,ctor=ctor,base_slot=base_slot,cache_slot=cache_slot,
            initializers=original_initializers,base_ctor=base_ctor)
    if not ctor and original_ctor is None and original_initializers and _peek(probe,5)==bytes.fromhex('48895c2408')and _peek(probe,21)[20:21]==b'\xbb':
        from scripts.game_data.memorypack.generated_scalar_factory_sources import register_defaults_program
        return register_defaults_program(regions,entry,barrier,base_slot=base_slot,cache_slot=cache_slot,initializers=original_initializers)
    if ctor and base_ctor is not None and _peek(probe,2)==b'\x40\x53':
        need('base-called-original-constructor-not-invoked',original_ctor is None)
        return base_called_factory_program(regions,entry,barrier,base_ctor=base_ctor,base_slot=base_slot,cache_slot=cache_slot,initializers=original_initializers)
    if bytes(probe.bytes.get(entry+i,0)for i in range(20))==bytes.fromhex('48895c2408574883ec20803d')+bytes(probe.bytes.get(entry+i,0)for i in range(12,17))+bytes.fromhex('488bd9'):
        from scripts.game_data.memorypack.generated_inline_cast_factory_sources import literal_class_factory_program
        return literal_class_factory_program(regions,entry,barrier,ctor=ctor,original_ctor=original_ctor,base_slot=base_slot,cache_slot=cache_slot)
    if original_ctor is None and original_initializers is None and(base_slot,cache_slot)==(16,24):
        from scripts.game_data.memorypack.skill_selector_current_sources import factory_program as zero_factory
        return zero_factory(regions,entry,barrier,ctor=ctor)
    g=BytesPath(regions,entry);delayed=_peek(g)==b'\x57'or _peek(g,2)==b'\x40\x57'
    if delayed:g.take('4057'if _peek(g,2)==b'\x40\x57'else'57')
    else:g.take('48895c2408','57')
    g.take('4883ec20');flag=g.relative('803d')+1
    g.take('00','488bf9');_initialized(g);base_usage=None;base_ready=None
    if ctor:
        site=g.at;cell=g.relative('488b0d');base_usage=dict(site=site,cell=cell)
        if _peek(g,2)==b'\x83\xb9':g.take('83b9e000000000');_initialized(g)
        else:base_ready=g.relative('e8')
        if base_ctor is not None:g.take('33d2','488bcf');g.call(base_ctor)
    site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocator=g.relative('e8')
    if original_ctor is not None:g.take('488bd8')
    g.take('4885c0');_nonnull(g)
    if original_ctor is not None:
        g.take('33d2')
        for store in original_initializers or[]:
            width,offset=store['bytes'],store['offset'];need('called-prefix-scalar-default',width in(1,2,4)and 16<=offset<2**31)
            raw=('66'if width==2 else'')+('c6'if width==1 else'c7')+('40'if offset<128 else'80')+offset.to_bytes(1 if offset<128 else 4,'little',signed=True).hex()+store['constantHex'].lower()
            g.take(raw)
        receiver=_peek(g,3)
        need('original-constructor-receiver',receiver in(bytes.fromhex('488bc8'),bytes.fromhex('488bcb')))
        g.take(receiver.hex());g.call(original_ctor)
    inline_writes=None
    if ctor and original_ctor is not None and _peek(g,4)==bytes.fromhex('488d4f')+bytes((cache_slot,)):
        inline_writes=[]
        for slot in(cache_slot,base_slot):
            d=bytes((slot,)).hex();start=g.at;g.take('488d4f'+d,'48895f'+d);g.call(barrier)
            inline_writes.append(dict(offset=slot,bytes=8,sameAllocatedReference=True,programStart=start))
        setter=None
    elif original_initializers is None or original_ctor is not None:
        g.take('4533c0')
        if delayed:g.take('48895c2430')
        g.take('488bd3'if original_ctor is not None else'488bd0','488bcf')
    else:
        expected={};written=set()
        for store in original_initializers:
            width,offset=store['bytes'],store['offset'];need('inlined-original-store-domain',width in(1,2,4) and 16<=offset<2**31)
            span=set(range(offset,offset+width));need('disjoint-inlined-original-initializers',not written&span);written.update(span)
            prefix='66c7'if width==2 else'c6'if width==1 else'c7';modrm='40'if offset<128 else'80'
            raw=prefix+modrm+offset.to_bytes(1 if offset<128 else 4,'little',signed=True).hex()+store['constantHex'].lower()
            need('unique-inlined-original-store',raw not in expected);expected[raw]=store
        arguments={'4533c0','488bd0','488bcf'}
        if delayed:arguments.add('48895c2430')
        while arguments or expected:
            matches=[h for h in list(arguments)+list(expected)if all(g.bytes.get(g.at+i)==b for i,b in enumerate(bytes.fromhex(h)))]
            need('exact-inlined-original-and-holder-arguments',len(matches)==1,(hex(g.at),list(arguments),list(expected)))
            raw=matches[0];g.take(raw)
            if raw in arguments:arguments.remove(raw)
            else:del expected[raw]
    if inline_writes is None:setter=g.relative('e8')
    base=bytes((base_slot,)).hex();cache=bytes((cache_slot,)).hex();g.take('488b5f'+base)
    usages=[];casts=[]
    for i in range(2):
        site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell))
        if i==0:g.take('488bcb')
        casts.append(g.relative('e8'))
        if i==0:g.take('488947'+cache,'488bcb')
    need('same-actual-class-and-cast',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in usages))
    g.take('488d4f'+cache,'488b5c2430','4883c420','5f');need('same-tail-barrier',g.relative('e9')==barrier)
    proof=dict(selectedBytes=g.seen,initializedFlag=flag,constructor=ctor,allocation=allocation,
        baseClassUsage=base_usage,baseReady=base_ready,allocationTarget=allocator,instanceSetter=setter,
        strictCast=casts[0],classUsages=usages,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
        originalConstructorCalled=original_ctor is not None,originalConstructorTarget=original_ctor,
        originalConstructorEffectsProved=False,normalReturnViaBarrier=True,
        condition='Initialized current classes, normal successful typed allocation and exact owned holder setter, compatible same-reference casts and disabled barrier. Optional original constructor has its own metadata/body/call identity; its runtime effects remain unproved.')
    if original_initializers is not None:proof['inlinedOriginalInitializers']=original_initializers
    if inline_writes is not None:proof['inlineHolderWrites']=inline_writes
    if base_ctor is not None:proof['baseConstructorTarget']=base_ctor
    return proof


def base_called_factory_program(regions,entry,barrier,*,base_ctor,base_slot,cache_slot,initializers=None):
    """Owned ancestor wrapper constructor, then fresh Original/holder/casts."""
    need('base-called-explicit-current-roles',type(base_ctor)is int and base_ctor>0 and type(base_slot)is int and
        type(cache_slot)is int and 16<=base_slot<cache_slot<128)
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
    g.take('4053','4883ec20');flag=_direct_flag(g,'803d');g.take('488bd9');_initialized(g)
    site=g.at;cell=g.relative('488b0d');ancestor=dict(site=site,cell=cell);g.take('83b9e000000000');_initialized(g)
    g.take('33d2','488bcb');g.call(base_ctor)
    site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocator=g.relative('e8')
    g.take('4885c0');_nonnull(g)
    if initializers is None:g.take('4533c0','48897c2430','488bd0','488bcb')
    else:
        need('owned-base-called-initializer-list',type(initializers)is list and 0<len(initializers)<=32)
        expected={};covered=set()
        for store in initializers:
            width,offset=store['bytes'],store['offset'];need('base-called-scalar-default-domain',width in(1,2,4)and 16<=offset<2**31)
            span=set(range(offset,offset+width));need('base-called-disjoint-default-stores',not covered&span);covered.update(span)
            raw=('66'if width==2 else'')+('c6'if width==1 else'c7')+('40'if offset<128 else'80')+offset.to_bytes(1 if offset<128 else 4,'little',signed=True).hex()+store['constantHex'].lower()
            expected[raw]=store
        args={'4533c0','48897c2430','488bd0','488bcb'}
        while args or expected:
            matches=[h for h in list(args)+list(expected)if all(g.bytes.get(g.at+i)==b for i,b in enumerate(bytes.fromhex(h)))]
            need('same-every-base-called-default-and-argument',len(matches)==1,(hex(g.at),list(args),list(expected)))
            raw=matches[0];g.take(raw)
            if raw in args:args.remove(raw)
            else:del expected[raw]
    setter=g.relative('e8')
    g.take('488b7b'+b);classes=[];casts=[]
    for index in range(2):
        site=g.at;cell=g.relative('488b15');classes.append(dict(site=site,cell=cell))
        if not index:g.take('488bcf')
        casts.append(g.relative('e8'))
        if not index:g.take('488943'+c,'488bcf')
    need('base-called-same-actual-class-and-cast',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in classes))
    g.take('488d4b'+c,'488b7c2430','4883c420','5b');need('base-called-restored-tail-barrier',g.relative('e9')==barrier)
    result=dict(selectedBytes=g.seen,initializedFlag=flag,constructor=True,allocation=allocation,allocationTarget=allocator,
        baseClassUsage=ancestor,baseReady=None,baseConstructorTarget=base_ctor,instanceSetter=setter,
        strictCast=casts[0],classUsages=classes,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
        originalConstructorCalled=False,originalConstructorTarget=None,originalConstructorEffectsProved=False,normalReturnViaBarrier=True,
        condition='Initialized current ancestor class and exact independently owned ancestor-wrapper zero-context constructor. Fresh typed Original allocation is passed whole to the owned holder setter; two exact same-nominal compatible casts and complete RBX/RDI frame/tail follow. Original constructor effects and runtime outcomes are not inferred.')
    if initializers is not None:result['inlinedOriginalInitializers']=initializers
    return result


def cached_prehook_program(regions,entry,*,cache_slot):
    """Complete initialized hook return with a nonnull own typed cache."""
    need('prehook-owned-cache-slot',type(cache_slot)is int and 16<cache_slot<128)
    g=BytesPath(regions,entry)
    if _peek(g,2)==b'\x40\x53':
        g.take('4053','4883ec20');flag=_direct_flag(g,'803d');g.take('488bd9');_initialized(g)
        g.take('48837b'+bytes((cache_slot,)).hex()+'00');_nonnull(g);g.take('4883c420','5b','c3')
        restored=['rbx']
    else:
        g.take('48895c2408','57','4883ec20','33db','488bf9');flag=g.relative('381d');_nonnull(g)
        g.take('48395f'+bytes((cache_slot,)).hex());_nonnull(g);g.take('488b5c2430','4883c420','5f','c3');restored=['rbx','rdi']
    return dict(selectedBytes=g.seen,initializedFlag=flag,cacheSlot=cache_slot,serializedFieldWrites=0,
        entryRspRestored=True,nonvolatileRegistersRestored=restored,
        condition='Initialized metadata and a compatible nonnull own typed cache. Empty-cache refresh and runtime invocation remain separate.')


def inline_holder_factory_program(regions,entry,barrier,*,original_ctor,base_slot,cache_slot):
    """Actual constructor call, both whole holders, then two exact casts."""
    need('inline-holder-domain',type(original_ctor)is int and original_ctor>0 and type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128)
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag=g.relative('803d')+1;g.take('00','488bd9');_initialized(g);ancestors=[]
    for _ in range(4):
        if _peek(g,2)==b'\x80\x3d':g.relative('803d');g.take('00');_initialized(g)
        site=g.at;cell=g.relative('488b0d');use=dict(site=site,cell=cell)
        if _peek(g,2)==b'\x83\xb9':g.take('83b9e000000000');_initialized(g);ancestors.append(use);continue
        allocation=use;allocator=g.relative('e8');break
    else:raise ValueError(LABEL+'.inline-holder-class-ready-bound')
    g.take('488bf8','4885c0');_nonnull(g);g.take('33d2');receiver=_peek(g,3)
    need('inline-holder-original-receiver',receiver in(bytes.fromhex('488bc8'),bytes.fromhex('488bcf')));g.take(receiver.hex());g.call(original_ctor)
    writes=[]
    for slot in(cache_slot,base_slot):
        b=bytes((slot,)).hex();at=g.at;g.take('488d4b'+b,'48897b'+b);g.call(barrier)
        writes.append(dict(offset=slot,bytes=8,sameAllocatedReference=True,programStart=at))
    b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex();g.take('488b7b'+b);classes=[];casts=[]
    for i in range(2):
        site=g.at;cell=g.relative('488b15');classes.append(dict(site=site,cell=cell))
        if i==0:g.take('488bcf')
        casts.append(g.relative('e8'))
        if i==0:g.take('488943'+c,'488bcf')
    need('inline-holder-original-class-and-cast',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in classes))
    g.take('488d4b'+c,'488b5c2430','4883c420','5f');need('inline-holder-final-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=True,allocation=allocation,allocationTarget=allocator,
        ancestorClassUsages=ancestors,baseClassUsage=None,baseReady=None,instanceSetter=None,inlineHolderWrites=writes,
        strictCast=casts[0],classUsages=classes,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
        originalConstructorCalled=True,originalConstructorTarget=original_ctor,originalConstructorEffectsProved=False,normalReturnViaBarrier=True,
        condition='Initialized current ancestor classes, successful exact original allocation and normal owned original constructor. Both selected compatible wrapper fields receive that whole same reference, then exact compatible casts update the typed cache. All barriers select the disabled path; runtime invocation and constructor effects remain independent.')


def _typed_abi(image,ctx,method,wrapper,result,arguments,label):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,result,arguments,LABEL+'.'+label)
    need('nongeneric-'+label,method.generic_container_index<0)


def _method_row(image,method):
    return[method.index,image.type_name(method.declaring_type),image.metadata.string(method.name_index),
        image.method_pointer_va(method)-image.pe.image_base]


def _body_proof(body):return dict(family=body['family'],codeWindows=body['windows'])


def _class_ancestry(ctx,name):
    from scripts.game_data.memorypack.lock_camera_member_sources import DERIVED_TYPES,original_ancestry
    if name in DERIVED_TYPES:return original_ancestry(ctx,name)
    from scripts.game_data.memorypack import constructed_action_ancestry_sources as constructed
    if name in constructed.TYPES or constructed.has_closed_node_parent(ctx,name):return constructed.original_ancestry(ctx,name)
    result=[]
    while name not in('','object','System.Object'):
        need('bounded-class-ancestry',name not in result and len(result)<32);result.append(name);name=ctx.parent(name)
    return result


def original_leaf_program(data,entry):
    """Exact call-free RCX-relative constant stores and an ordinary return.

    The stop at RET establishes a reachable entry program, never a physical
    function extent. No stack/nonvolatile/argument register is modified.
    """
    need('original-leaf-prefix',type(data)is bytes and 0<len(data)<=128 and type(entry)is int)
    g=BytesPath([(entry,data)],entry);stores=[];zero_context=False;tail=None
    while g.at-entry<len(data):
        first=_peek(g)
        if _peek(g,2)==b'\x33\xd2':
            need('one-explicit-zero-methodinfo',not zero_context);g.take('33d2');zero_context=True;continue
        if first==b'\xe9':
            need('tail-has-explicit-zero-methodinfo',zero_context);tail=g.relative('e9');break
        if first==b'\xc3':g.take('c3');break
        if data[g.at-entry:g.at-entry+3]==b'\xc2\x00\x00':g.take('c20000');break
        start=g.at;width=None
        if first==b'\x66':g.take('66');width=2;need('original-leaf-word-store-opcode',_peek(g)==b'\xc7')
        opcode=g.read(1)[0];need('original-leaf-constant-store-opcode',opcode in(0xc6,0xc7))
        if width is None:width=1 if opcode==0xc6 else 4
        modrm=g.read(1)[0];need('original-leaf-only-owned-RCX-store',modrm in(0x41,0x81))
        displacement=int.from_bytes(g.read(1 if modrm==0x41 else 4),'little',signed=True)
        need('original-leaf-instance-field-offset',16<=displacement<2**31)
        value=g.read(width);stores.append(dict(instructionVa=start,offset=displacement,bytes=width,constantHex=value.hex().upper()))
    else:raise ValueError(LABEL+'.original-leaf-no-return')
    result=dict(selectedBytes=g.seen,stores=stores,programBytes=g.at-entry,normalReturn=tail is None,
        callFree=True,stackUnchanged=True,allNonvolatileRegistersUnchanged=True,physicalFunctionExtentProved=False)
    if tail is not None:result.update(tailTargetVa=tail,explicitZeroMethodInfo=True,sameWholeReceiverRcx=True)
    return result


def _original_constructor(image,ctx,method,original,*,_owners=(),pins=None):
    need('bounded-original-constructor-tail',original not in _owners and len(_owners)<8)
    pointer=image.method_pointer_va(method);base=image.pe.image_base
    if pointer-base in image.unwind_index.entries:
        family,windows=members.ec.family_windows(image,pointer-base)
        return dict(method=_method_row(image,method),family=family,codeWindows=windows,completeCurrentOwnedBodyPinned=True,
            normalConstructorReturnRequired=True,runtimeEffectsProved=False)
    data=image.pe.bytes_at_va(pointer,128);md=image.metadata
    if data[:3]==bytes.fromhex('33d2e9'):
        from scripts.game_data.memorypack import scalar_param_native as scalar
        target=pointer+7+int.from_bytes(data[3:7],'little',signed=True);candidates=[]
        for ancestor in _class_ancestry(ctx,original)[1:]:
            for chosen in md.methods_for(ctx.index.types[ancestor]):
                if md.string(chosen.name_index)=='.ctor'and chosen.parameter_count==0 and image.method_pointer_va(chosen)==target:candidates.append((ancestor,chosen))
        need('unique-owned-ancestor-constructor-tail',len(candidates)==1,[(n,m.index)for n,m in candidates])
        ancestor,chosen=candidates[0];need('nongeneric-owned-ancestor-constructor',chosen.generic_container_index<0)
        scalar.owned_method_abi(image,ctx,chosen.index,chosen.declaring_type,('void',1,False),[],LABEL+'.ancestorCtor')
        delegated=_original_constructor(image,ctx,chosen,ancestor,_owners=(*_owners,original),pins=pins)
        return dict(method=_method_row(image,method),ownedAncestorTail=dict(instructionHex=data[:7].hex().upper(),targetRva=target-base,targetMethod=_method_row(image,chosen),
            sameWholeReceiverRcx=True,methodInfoEdxZero=True,stackAndNonvolatilesUnchanged=True),delegatedConstructor=delegated,
            codeWindows=[dict(startRva=pointer-base,endRva=pointer-base+7,sha256=hashlib.sha256(data[:7]).hexdigest().upper())],
            completeReachableEntryProgramProved=True,physicalFunctionExtentProved=False,normalConstructorReturnRequired=True,runtimeExecutionKnown=False)
    if data[:4]==bytes.fromhex('f30f1015'):
        from scripts.game_data.memorypack.generated_vector_default_sources import derive_original
        need('vector-default-explicit-selected-inputs',isinstance(pins,dict)and bool(pins))
        source=derive_original(image,pins,original_type=original)
        need('same-actual-vector-default-constructor',source['method']==_method_row(image,method))
        return dict(method=source['method'],codeWindows=source['codeWindows'],vectorDefaultSource=source,
            completeReachableEntryProgramProved=True,physicalFunctionExtentProved=False,
            normalConstructorReturnRequired=True,runtimeExecutionKnown=False)
    if data[:6]==bytes.fromhex('0f57d20f57c0'):
        from scripts.game_data.memorypack import char_wet_constructor_sources as char_wet
        if original==char_wet.TYPE:
            need('CharWet-default-explicit-selected-inputs',isinstance(pins,dict)and bool(pins))
            source=char_wet.derive_original(image,pins);char_wet.verify(source,pins)
            need('same-actual-CharWet-default-constructor',source['method']==_method_row(image,method))
            return dict(method=source['method'],codeWindows=source['codeWindows'],charWetDefaultSource=source,
                completeReachableEntryProgramProved=True,physicalFunctionExtentProved=False,
                normalConstructorReturnRequired=True,runtimeExecutionKnown=False)
        from scripts.game_data.memorypack.generated_zero_vector_factory_sources import derive_original
        need('zero-vector-default-explicit-selected-inputs',isinstance(pins,dict)and bool(pins))
        source=derive_original(image,pins,original_type=original)
        need('same-actual-zero-vector-default-constructor',source['method']==_method_row(image,method))
        return dict(method=source['method'],codeWindows=source['codeWindows'],zeroVectorDefaultSource=source,
            completeReachableEntryProgramProved=True,physicalFunctionExtentProved=False,
            normalConstructorReturnRequired=True,runtimeExecutionKnown=False)
    if data[:3]==bytes.fromhex('488b05'):
        from scripts.game_data.memorypack.generated_literal_constructor_sources import derive
        need('literal-default-explicit-selected-inputs',isinstance(pins,dict)and bool(pins))
        return derive(image,pins,context=ctx,method=method,original=original)
    program=original_leaf_program(data,pointer);fields=[];value_subfields=None
    kinds={'bool':(2,1),'byte':(5,1),'sbyte':(4,1),'short':(6,2),'ushort':(7,2),
        'int':(8,4),'uint':(9,4),'long':(10,8),'ulong':(11,8),'float':(12,4),'double':(13,8)}
    from scripts.game_data.memorypack import scalar_param_native as scalar
    for owner in _class_ancestry(ctx,original):
        td=ctx.index.types[owner]
        for field in md.fields_for(td):
            if ctx.field_attributes(field.type_index)&16:continue
            name=md.string(field.name_index);fact=ctx.field(owner+'::'+name);declared=ctx.type_name(field.type_index);backing=declared
            if ctx.is_enum(declared):
                enum=ctx.index.types[declared];backings=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
                need('original-ctor-enum-backing',len(backings)==1 and md.string(backings[0].name_index)=='value__')
                backing=ctx.type_name(backings[0].type_index);need('original-ctor-supported-enum-backing',backing in kinds)
                scalar.ordinary(image,ctx.type_pointer(backings[0].type_index),kinds[backing][0],LABEL+'.ctorEnumBacking')
                scalar.ordinary(image,ctx.type_pointer(field.type_index),17,LABEL+'.ctorEnumField')
            elif backing in kinds:scalar.ordinary(image,ctx.type_pointer(field.type_index),kinds[backing][0],LABEL+'.ctorField')
            if backing in kinds:fields.append(dict(owner=owner,name=name,typeName=declared,offset=fact[2],bytes=kinds[backing][1]))
    from scripts.game_data.memorypack import generated_vector2_constructor_fields as vector2_fields
    if original in vector2_fields.TYPES:
        value_subfields=vector2_fields.derive(image,ctx,original)
        fields.extend(value_subfields['componentFields'])
    joined=[]
    for store in program['stores']:
        owners=[]
        for offset in range(store['offset'],store['offset']+store['bytes']):
            matches=[f for f in fields if f['offset']<=offset<f['offset']+f['bytes']]
            need('original-ctor-byte-owned-by-one-current-field',len(matches)==1,(store,offset,matches))
            if matches[0]not in owners:owners.append(matches[0])
        joined.append(dict(**store,fields=owners))
    length=program['programBytes'];window=dict(startRva=pointer-base,endRva=pointer-base+length,
        sha256=hashlib.sha256(data[:length]).hexdigest().upper(),boundary='complete reachable call-free original-constructor entry program; physical extent unproved')
    result=dict(method=_method_row(image,method),codeWindows=[window],reachableLeaf=program,constantFieldStores=joined,
        completeReachableEntryProgramProved=True,physicalFunctionExtentProved=False,
        normalConstructorReturnRequired=True,runtimeExecutionKnown=False)
    if value_subfields is not None:result['valueSubfieldOwnership']=value_subfields
    if program.get('tailTargetVa')is not None:
        target=program['tailTargetVa'];candidates=[]
        for ancestor in _class_ancestry(ctx,original)[1:]:
            for chosen in md.methods_for(ctx.index.types[ancestor]):
                if md.string(chosen.name_index)=='.ctor'and chosen.parameter_count==0 and image.method_pointer_va(chosen)==target:candidates.append((ancestor,chosen))
        need('unique-owned-initializing-ancestor-tail',len(candidates)==1,[(n,m.index)for n,m in candidates])
        ancestor,chosen=candidates[0];need('nongeneric-initializing-ancestor-constructor',chosen.generic_container_index<0)
        scalar.owned_method_abi(image,ctx,chosen.index,chosen.declaring_type,('void',1,False),[],LABEL+'.initializingAncestorCtor')
        delegated=_original_constructor(image,ctx,chosen,ancestor,_owners=(*_owners,original),pins=pins)
        result.update(ownedAncestorTail=dict(targetRva=target-base,targetMethod=_method_row(image,chosen),sameWholeReceiverRcx=True,methodInfoEdxZero=True,stackAndNonvolatilesUnchanged=True),delegatedConstructor=delegated)
    return result


def _holder_fields(image,ctx,receiver,slots,original_chain):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;result=[]
    for slot in slots:
        fields=[]
        for owner in _class_ancestry(ctx,receiver):
            for field in md.fields_for(ctx.index.types[owner]):
                if ctx.field_attributes(field.type_index)&16:continue
                fact=ctx.field(owner+'::'+md.string(field.name_index))
                if fact[2]!=slot:continue
                scalar.ordinary(image,ctx.type_pointer(field.type_index),18,LABEL+'.holderField',reference=True)
                fields.append(fact)
        need('one-compatible-owned-holder-field',len(fields)==1 and fields[0][1]in original_chain,(slot,fields));result.append(fields[0])
    return result



def _direct_flag(g,prefix='833d'):
 cell=g.relative(prefix)+1;g.take('00');return cell
def _direct_allocation(g,allocate):
 at=g.at;cell=g.relative('488b0d');g.call(allocate);return dict(site=at,cell=cell)
def _direct_constant(g,width):
 site=g.at;g.take('c640'if width==1 else'c740');offset=g.read(1)[0];value=g.read(width)
 need('direct-constant-positive-disp8-field',16<=offset<128)
 return dict(instructionVa=site,offset=offset,bytes=width,constantHex=value.hex().upper())
def constant_tail_factory_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');metadata=_direct_flag(g,'803d');g.take('488bd9');_initialized(g);usage=_direct_allocation(g,s['allocate']);g.take('4885c0');_nonnull(g)
 need('actual-constant-byte-or-dword',_peek(g,2)in(bytes.fromhex('c640'),bytes.fromhex('c740')))
 store=_direct_constant(g,1 if _peek(g,2)==bytes.fromhex('c640')else 4)
 g.take('488d4b10','48894310','4883c420','5b');need('actual-tail',g.relative('e9')==s['barrier'])
 return dict(selectedBytes=g.seen,metadata=metadata,allocation=usage,constantFields=[store],holderOffset=16,sameAllocatedOriginalStored=True,baseHolderOffset=16,typedCacheOffset=None,allocationTarget=s['allocate'],inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],normalReturnViaBarrier=True)
def called_original_factory_program(regions,entry,s):
 """Full current caller with exact Original constructor and restored tail."""
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');metadata=_direct_flag(g,'803d');g.take('488bf9');_initialized(g)
 usage=_direct_allocation(g,s['allocate']);g.take('488bd8','4885c0');_nonnull(g);g.take('33d2')
 if _peek(g,3)==bytes.fromhex('488bc8'):g.take('488bc8')
 else:g.take('488bcb')
 g.call(s['constructor']);g.take('488d4f10','48895f10','488b5c2430','4883c420','5f');need('actual-original-ctor-tail',g.relative('e9')==s['barrier'])
 return dict(selectedBytes=g.seen,metadata=metadata,allocation=usage,baseHolderOffset=16,typedCacheOffset=None,
  allocationTarget=s['allocate'],originalConstructor=True,originalConstructorTarget=s['constructor'],
  inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],normalReturnViaBarrier=True,
  condition='Actual current typed Original allocation and exact named noarg constructor call, full allocated receiver preserved across ordinary Win64 helper effects; complete holder write and restored wrapper frame. Constructor body owned independently, live allocation/execution conditional.')
def constant_guarded_factory_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20');metadata=_direct_flag(g,'803d');g.take('488bf9');_initialized(g);usage=_direct_allocation(g,s['allocate']);g.take('4885c0');_nonnull(g);need('actual-disabled-cell',_direct_flag(g)==s['disabled']);store=_direct_constant(g,1)
 g.take('48894710');g.branch('74',True,1);g.take('488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,metadata=metadata,allocation=usage,constantFields=[store],holderOffset=16,sameAllocatedOriginalStored=True,baseHolderOffset=16,typedCacheOffset=None,allocationTarget=s['allocate'],inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],disabledCollectorCell=s['disabled'],normalReturn=True)
def nested_constant_factory_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');metadata=_direct_flag(g,'803d');g.take('488bf9');_initialized(g);original=_direct_allocation(g,s['allocate']);g.take('488bd8','4885c0');_nonnull(g);first=_direct_constant(g,4)
 child=_direct_allocation(g,s['allocate']);g.take('4885c0');_nonnull(g);second=_direct_constant(g,1);card=g.relative('4c8d0d');site=g.at;g.take('488943');child_slot=g.read(1)[0];need('actual-disabled-cell',g.relative('8b05')==s['disabled']);g.take('85c0');g.branch('74',True,1)
 g.take('48895f10','85c0');g.branch('74',True,1);g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,metadata=metadata,allocation=original,childAllocation=child,constantFields=[dict(object='original',**first),dict(object='child',**second)],
  childReferenceStore=dict(instructionVa=site,offset=child_slot,bytes=8,sameAllocatedChildStored=True),holderOffset=16,sameAllocatedOriginalStored=True,baseHolderOffset=16,typedCacheOffset=None,allocationTarget=s['allocate'],inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],disabledCollectorCell=s['disabled'],deadCollectorAddress=card,normalReturn=True)

def two_list_factory_program(regions,entry,s):
    """Current full default List allocations, exact contexts and wrapper holder."""
    g=BytesPath(regions,entry);g.take('48896c2420','57','4883ec20');metadata=_direct_flag(g,'803d');g.take('488be9');_initialized(g)
    original=_direct_allocation(g,s['allocate']);g.take('488bf8','4885c0');_nonnull(g)
    site=g.at;cell=g.relative('488b0d');first=dict(site=site,cell=cell);g.take('48895c2430');g.call(s['allocate']);g.take('488bd8','4885c0');_nonnull(g)
    g.take('4889742438','33d2');site=g.at;cell=g.relative('488b35');first_context=dict(site=site,cell=cell)
    g.take('488b4e20','488b89c0000000');indexer=g.relative('e8');g.take('83b8e000000000');_nonnull(g)
    g.take('488b4e20','33d2','488b89c0000000');need('same-current-list-class-resolver',g.relative('e8')==indexer)
    dead=g.relative('488d35');g.take('488b88b8000000','488b01','48894310')
    need('actual-inline-list-disabled-cell',g.relative('8b05')==s['disabled']);g.take('85c0');g.branch('74',True,1)
    at=g.at;g.take('48895f');first_slot=g.read(1)[0];g.take('85c0');g.branch('74',True,1)
    second=_direct_allocation(g,s['allocate']);g.take('488bd8','4885c0');_nonnull(g)
    site=g.at;cell=g.relative('488b15');second_context=dict(site=site,cell=cell);g.take('488bc8');list_constructor=g.relative('e8')
    need('same-second-list-disabled-cell',g.relative('8b05')==s['disabled']);at2=g.at;g.take('48895f');second_slot=g.read(1)[0]
    g.take('85c0');g.branch('74',True,1);g.take('48897d10','85c0');g.branch('74',True,1)
    g.take('488b742438','488b5c2430','488b6c2448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadata=metadata,allocation=original,allocationTarget=s['allocate'],baseHolderOffset=16,typedCacheOffset=None,
        inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],sameAllocatedOriginalStored=True,disabledCollectorCell=s['disabled'],
        initializedClassResolver=indexer,actualListConstructor=list_constructor,inlineListItemsOffset=16,deadCollectorAddress=dead,
        listAllocations=[dict(allocation=first,methodContext=first_context,referenceOffset=first_slot,referenceStoreVa=at,inlineInitializer=True),
            dict(allocation=second,methodContext=second_context,referenceOffset=second_slot,referenceStoreVa=at2,inlineInitializer=False)],
        normalReturn=True,nonvolatileRegistersRestored=['rbp','rdi','rbx','rsi'],entryRspRestored=True)


def empty_reference_constructor_program(regions,entry,*,indexer,disabled):
    """Actual called default reference-list initialization, independent of maps."""
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488bf9','488bda','488b4a20','33d2','488b89c0000000');g.call(indexer)
    g.take('83b8e000000000');_nonnull(g);g.take('488b4b20','33d2','488b89c0000000');g.call(indexer)
    need('default-list-current-disabled-cell',_direct_flag(g)==disabled)
    g.take('488b88b8000000','488b01','48894710');g.branch('74',True,1);g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,contextRegister='incoming RDX',receiverRegister='incoming RCX',classContextSlot=0,
        staticReferenceSlot=0,itemsReferenceOffset=16,sameStaticArrayReferenceStored=True,normalReturn=True,entryRspRestored=True,
        nonvolatileRegistersRestored=['rbx','rdi'],registeredNativeEntryIdentityClaimed=False,
        condition='Actual caller supplies its independently checked closed List constructor MethodInfo and same typed List allocation; slot0 selects the initialized matching closed List class and its sole stored static empty array. Disabled collector, stable disjoint storage and normal ordinary helpers are required; no generic native-registration row or child wire grammar is inferred.')


def direct_holder_factory_program(regions,entry,barrier):
    """Complete initialized allocation, whole own holder and restored tail."""
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1;g.take('00','488bd9');_initialized(g)
    site=g.at;cell=g.relative('488b0d');allocator=g.relative('e8');g.take('4885c0');_nonnull(g)
    g.take('488d4b10','48894310','4883c420','5b');need('direct-holder-actual-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,initializedFlag=flag,allocation=dict(site=site,cell=cell),allocationTarget=allocator,
        baseHolderOffset=16,typedCacheOffset=None,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],
        normalReturnViaBarrier=True,entryRspRestored=True,allNonvolatilesRestored=True,originalConstructorInvoked=False,
        condition='Initialized current metadata, normal nonnull exact original allocation, stable disjoint typed holder and disabled reference barrier. No original constructor call, runtime allocation effects or child grammar is inferred.')


def _bind_factory_constant(image,ctx,type_name,store):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;matches=[];widths={2:1,4:1,5:1,6:2,7:2,8:4,9:4,10:8,11:8,12:4,13:8}
    for owner in _class_ancestry(ctx,type_name):
        for field in md.fields_for(ctx.index.types[owner]):
            if ctx.field_attributes(field.type_index)&16:continue
            fact=ctx.field(owner+'::'+md.string(field.name_index))
            declared=ctx.type_name(field.type_index)
            if declared=='UnityEngine.Vector2'and fact[2]<=store['offset']<fact[2]+8:
                from scripts.game_data.memorypack.generated_vector2_factory_constants import bind
                scalar.ordinary(image,ctx.type_pointer(field.type_index),17,LABEL+'.factoryVector2')
                matches.append(bind(image,ctx,fact,store));continue
            if fact[2]!=store['offset']:continue
            raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16);kind=raw[10];declared=ctx.type_name(field.type_index)
            scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,LABEL+'.factoryConstant')
            if store.get('requiresBooleanByteField')is True:
                need('packed-current-Boolean-byte-field',kind==2 and store.get('bytes')==1
                    and store.get('sourceStoreBytes')==2 and store.get('sourceByteIndex')in(0,1)
                    and store.get('sourceStoreOffset')+store['sourceByteIndex']==store['offset'])
            if kind==17 and ctx.is_enum(declared):
                backing,=[f for f in md.fields_for(ctx.index.types[declared])if not ctx.field_attributes(f.type_index)&16]
                need('factory-enum-backing',md.string(backing.name_index)=='value__');kind=image.pe.bytes_at_va(ctx.type_pointer(backing.type_index),16)[10]
                scalar.ordinary(image,ctx.type_pointer(backing.type_index),kind,LABEL+'.factoryEnumBacking')
            need('factory-current-constant-width',kind in widths and widths[kind]==store['bytes'])
            if kind==2:need('factory-boolean-constant',int.from_bytes(bytes.fromhex(store['constantHex']),'little')in(0,1))
            matches.append(dict(field=fact,rawTypeHex=raw.hex().upper(),constantHex=store['constantHex'],bytes=store['bytes']))
    need('one-owned-constant-initializer-field',len(matches)==1,(type_name,store));return matches[0]


def _initialized_indexer(image,pointer):
    from scripts.game_data.memorypack.int_list_sources import initialized_class
    raw=image.pe.bytes_at_va(pointer,15);need('indexed-helper-entry',raw[:10]==bytes.fromhex('488bc14863ca488b0cc8')and raw[10]==0xe9)
    target=pointer+15+int.from_bytes(raw[11:15],'little',signed=True)
    regions=[(pointer,raw),(target,image.pe.bytes_at_va(target,64))];program=initialized_class(regions,pointer,indexed=True)
    selected={at+i for at,h in program['selectedBytes']for i in range(len(bytes.fromhex(h)))};spans=[]
    for at in sorted(selected):
        if spans and spans[-1][1]==at:spans[-1][1]+=1
        else:spans.append([at,at+1])
    base=image.pe.image_base;windows=[dict(startRva=a-base,endRva=b-base,sha256=hashlib.sha256(image.pe.bytes_at_va(a,b-a)).hexdigest().upper(),
        boundary='complete selected initialized indexed-context helper program; physical extent unproved')for a,b in spans]
    return dict(entryRva=pointer-base,selectedClassBranchRva=target-base,codeWindows=windows,program=program,physicalExtentProved=False)


def _bind_default_lists(image,ctx,wrapper,program,disabled):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    base=image.pe.image_base;md=image.metadata;list_owner=ctx.index.types['System.Collections.Generic.List`1']
    class_context=ContextSymbols(image).context(list_owner.index);slot,=[r for r in class_context['entries']if r['relativeSlot']==0]
    need('list-constructor-owned-class-slot',slot['kind']==2 and slot['type']['definition']['name']=='System.Collections.Generic.List`1')
    argument,=slot['type']['classArguments'];need('list-constructor-reciprocal-VAR',(argument['parameterOwner']['typeIndex'],argument['parameterOwner']['ordinal'])==(list_owner.index,0))
    static=[f for f in md.fields_for(list_owner)if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64]
    need('list-one-stored-static-reference',len(static)==1);empty=static[0];raw=image.pe.bytes_at_va(ctx.type_pointer(empty.type_index),16)
    need('list-static-array-same-owned-VAR',raw[10:12]==bytes((29,0))and int.from_bytes(raw[:8],'little')==argument['typePointerVa'])
    result=[]
    for record in program['listAllocations']:
        allocation=derive_typed_usage_context(image,record['allocation']['site']-base,label=LABEL+'.defaultListAllocation')
        method_info=derive_typed_usage_context(image,record['methodContext']['site']-base,label=LABEL+'.defaultListMethodInfo')
        need('exact-current-list-method-context',method_info['tag']==6 and method_info['typeName']=='System.Collections.Generic.List`1'and method_info['methodName']=='.ctor'and len(method_info['classArguments'])==1 and method_info['methodArguments']==[] and method_info['methodSpec'][2]==-1)
        method=md.methods[method_info['methodSpec'][0]];need('owned-default-list-constructor-definition',method.declaring_type==list_owner.index and method.generic_container_index<0)
        scalar.owned_method_abi(image,ctx,method.index,list_owner.index,('void',1,False),[],LABEL+'.defaultListCtor')
        element=method_info['classArguments'][0];list_name='System.Collections.Generic.List`1<'+element+'>'
        need('same-allocated-closed-list',allocation['tag']==1 and allocation['typeName']==list_name)
        allocated_raw=bytes.fromhex(allocation['typeRawHex']);need('reference-list-allocation-kind',allocated_raw[10:12]==bytes((21,0)))
        carrier=int.from_bytes(allocated_raw[:8],'little');inst=image.pe.u64_at_va(carrier+8)
        actual_args=[a.type_pointer_va for a in image.instantiations.resolve_pointer(inst).arguments];expected_args=[a.type_pointer_va for a in image.instantiations.resolve(method_info['methodSpec'][1]).arguments]
        need('same-full-closed-list-type-pointers',actual_args==expected_args and len(actual_args)==1)
        fields=[]
        for owner in _class_ancestry(ctx,wrapper.wrapped_type):
            for field in md.fields_for(ctx.index.types[owner]):
                if ctx.field_attributes(field.type_index)&16:continue
                fact=ctx.field(owner+'::'+md.string(field.name_index))
                if fact[2]!=record['referenceOffset']:continue
                scalar.ordinary(image,ctx.type_pointer(field.type_index),21,LABEL+'.defaultListParentField',reference=True)
                need('same-current-list-parent-field',fact[1]==list_name);fields.append(fact)
        need('one-current-list-parent-field',len(fields)==1)
        result.append(dict(allocation=allocation,constructorMethodInfo=method_info,parentReferenceField=fields[0],sourceProgram=record,
            registeredNativeEntryIdentityClaimed=False,physicalItemsOffsetFromSelectedSource=True,openGenericFieldOffsetsUsed=False))
    helper=members._body(image,program['actualListConstructor'])
    helper_program=empty_reference_constructor_program(helper['regions'],helper['pointer'],indexer=program['initializedClassResolver'],disabled=disabled)
    indexer=_initialized_indexer(image,program['initializedClassResolver'])
    return dict(lists=result,listClassContext=class_context,staticEmptyArrayField=dict(name=md.string(empty.name_index),typeName=ctx.type_name(empty.type_index),rawTypeHex=raw.hex().upper(),soleStoredStaticReference=True),
        actualCalledConstructor=dict(targetRva=helper['pointer']-base,**_body_proof(helper),program=helper_program),initializedContextHelper=indexer,
        registeredNativeEntryIdentityClaimed=False,childWireGrammarAdmitted=False,
        condition='Exact current closed constructor MethodInfos/class VAR identity and actual caller allocation/E8 bodies. Initialized coherent selected class contexts, their initialized sole empty-array static reference and zeroed fresh allocations, stable disjoint storage and disabled collector are required. No registered pointer equality, runtime inflation observation or positive list grammar is inferred.')


def _direct_factory_proof(image,ctx,wrapper,body,barrier,original_ctor,*,direct_factory_prover=None,pins=None):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.modelview_factory_sources import create_instance
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack import generated_direct_value_factory_sources as direct_values
    from scripts.game_data.memorypack.generated_direct_constant_tail_sources import program as direct_constant_tail
    base=image.pe.image_base;original=wrapper.wrapped_type;allocators=[]
    for i,row in enumerate(body['rows'][:-1]):
        raw=members.ec.raw(row)
        if len(raw)!=7 or raw[:3]!=bytes.fromhex('488b0d')or members.ec.raw(body['rows'][i+1])[:1]!=b'\xe8':continue
        try:usage=derive_typed_usage_context(image,members.ec.va(row)-base,label=LABEL+'.directAllocationCandidate')
        except(ValueError,KeyError,IndexError):continue
        if(usage['tag'],usage['typeName'])==(1,original):allocators.append(members.control_transfer(body['rows'][i+1])['target'])
    need('one-current-direct-allocator',len(set(allocators))==1,allocators);allocate=allocators[0]
    disabled=_barrier(image,base+barrier)['result']['disabledFlagRva'];symbols=dict(allocate=allocate,barrier=base+barrier,disabled=base+disabled)
    if direct_factory_prover is not None:
        need('direct-factory-prover-callable',callable(direct_factory_prover))
        supplied=direct_factory_prover(image,ctx,wrapper,body,symbols,original_ctor)
        if supplied is not NotImplemented:
            need('direct-factory-prover-result',isinstance(supplied,dict)and set(supplied)=={'program','originalConstructor','proof'})
            program=supplied['program'];proof=supplied['proof']
            need('direct-factory-owned-complete-proof',isinstance(proof,dict)and
                proof.get('wrapperName')==wrapper.name and proof.get('typeName')==original
                and proof.get('completeSelectedFactoryAdmitted')is True and proof.get('childGrammarAdmitted')is False)
            need('direct-factory-actual-allocation-and-holder',isinstance(program,dict)and
                program.get('allocationTarget')==allocate and program.get('baseHolderOffset')==16
                and program.get('typedCacheOffset')is None and program.get('sameAllocatedOriginalStored')is True
                and program.get('inlineHolderWrites')==[dict(offset=16,bytes=8,sameAllocatedReference=True)])
            need('direct-factory-complete-selected-return',bool(program.get('selectedBytes'))and
                program.get('entryRspRestored')is True and program.get('allNonvolatilesRestored')is True
                and(program.get('normalReturn')is True or program.get('normalReturnViaBarrier')is True))
            return program,dict(childAllocation=None,constantFields=[],defaultLists=None,
                originalConstructor=supplied['originalConstructor'],independentFactory=proof)
    errors=[];programs=[]
    for profile in(direct_holder_factory_program,constant_tail_factory_program,direct_constant_tail,constant_guarded_factory_program,nested_constant_factory_program,two_list_factory_program,
        direct_values.shared_constant_program,direct_values.vector3_one_program):
        try:
            result=profile(body['regions'],body['pointer'],base+barrier)if profile is direct_holder_factory_program else profile(body['regions'],body['pointer'],symbols)
            programs.append(result)
        except(ValueError,KeyError,IndexError)as error:errors.append(str(error))
    constructor_proof=None
    if original_ctor is not None and image.method_pointer_va(original_ctor)in{members.control_transfer(row)['target']for row in body['rows']if members.ec.raw(row)[:1]==b'\xe8'}:
        try:
            scalar.owned_method_abi(image,ctx,original_ctor.index,original_ctor.declaring_type,('void',1,False),[],LABEL+'.directOriginalCtor')
            target=image.method_pointer_va(original_ctor)
            try:
                result=create_instance(body['regions'],body['pointer'],dict(allocate=allocate,constructor=target,barrier=base+barrier),constructor=True)
                result.update(allocation=dict(site=result['allocationInstruction'],cell=result['originalClassCell']),allocationTarget=allocate,
                    baseHolderOffset=16,typedCacheOffset=None,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)])
            except(ValueError,KeyError,IndexError):
                result=called_original_factory_program(body['regions'],body['pointer'],dict(symbols,constructor=target))
            constructor_proof=_original_constructor(image,ctx,original_ctor,original,pins=pins);programs.append(result)
        except(ValueError,KeyError,IndexError)as error:errors.append(str(error))
    need('one-complete-direct-factory-program',len(programs)==1,errors)
    program=programs[0];child=None;child_type=None
    if 'childAllocation'in program:
        child=derive_typed_usage_context(image,program['childAllocation']['site']-base,label=LABEL+'.directChildAllocation');child_type=child['typeName']
        need('current-ordinary-child-class',child['tag']==1 and not ctx.is_value_type(child_type))
        store=program['childReferenceStore'];fields=[]
        for owner in _class_ancestry(ctx,original):
            for field in image.metadata.fields_for(ctx.index.types[owner]):
                if ctx.field_attributes(field.type_index)&16:continue
                fact=ctx.field(owner+'::'+image.metadata.string(field.name_index))
                if fact[2]!=store['offset']:continue
                scalar.ordinary(image,ctx.type_pointer(field.type_index),18,LABEL+'.directChildField',reference=True)
                need('same-current-child-field-type',fact[1]==child_type);fields.append(fact)
        need('one-direct-child-reference-field',len(fields)==1);child=dict(allocation=child,referenceField=fields[0],program=store)
    constants=[_bind_factory_constant(image,ctx,child_type if store.get('object')=='child'else original,store)for store in program.get('constantFields',[])]
    default_lists=_bind_default_lists(image,ctx,wrapper,program,base+disabled)if 'listAllocations'in program else None
    value_initialization=direct_values.bind(image,ctx,original,program,base+barrier)if 'valueInitialization'in program else None
    return program,dict(childAllocation=child,constantFields=constants,defaultLists=default_lists,originalConstructor=constructor_proof,
        **(dict(valueInitialization=value_initialization)if value_initialization is not None else{}))


def _typed_factory_proof(image,pins,ctx,wrapper,body,barrier,original_ctor,prover):
    """Opt-in native typed factory, distinct from a managed allocator/ctor."""
    if prover is None:return None
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    need('typed-factory-callable-only',callable(prover))
    base=image.pe.image_base;disabled=_barrier(image,base+barrier)['result']['disabledFlagRva']
    supplied=prover(image,ctx,wrapper,body,dict(barrier=base+barrier,disabled=base+disabled),original_ctor)
    if supplied is NotImplemented:return None
    need('typed-factory-explicit-result',isinstance(supplied,dict)and set(supplied)=={'program','proof'})
    program=supplied['program'];proof=supplied['proof']
    need('typed-factory-complete-identity',isinstance(proof,dict)and proof.get('nativeInputs')==pins
        and(proof.get('wrapperName'),proof.get('typeName'))==(wrapper.name,wrapper.wrapped_type)
        and proof.get('completeSelectedFactoryAdmitted')is True and proof.get('childGrammarAdmitted')is False
        and proof.get('originalManagedConstructorInvoked')is False and proof.get('opaqueUnityInitializationRequired')is True)
    need('typed-factory-exact-holder-and-return',isinstance(program,dict)
        and program.get('typedFactoryMode')=='scriptable-object-generic'and'allocationTarget'not in program
        and program.get('baseHolderOffset')==16 and program.get('typedCacheOffset')is None
        and program.get('originalReferenceStoredUnchanged')is True
        and program.get('inlineHolderWrites')==[dict(offset=16,bytes=8,sameAllocatedReference=True)]
        and program.get('entryRspRestored')is True and program.get('allNonvolatilesRestored')is True
        and(program.get('normalReturn')is True or program.get('normalReturnViaBarrier')is True)
        and type(program.get('factoryTargetVa'))is int and program['factoryTargetVa']>base)
    site=program.get('factoryUsageInstruction');selected=program.get('selectedBytes',[])
    need('typed-factory-actual-selected-entry',isinstance(site,list)and len(site)==2 and type(site[0])is int
        and bool(selected)and selected[0][0]==body['pointer'])
    usage=derive_typed_usage_context(image,site[0],label=LABEL+'.typedOriginalFactory')
    need('typed-factory-exact-nominal-request',(usage['tag'],usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])==
        (6,'UnityEngine.ScriptableObject','CreateInstance',[],[wrapper.wrapped_type])and usage['instructionHex']==site[1])
    owned={at+i:b for at,raw in body['regions']for i,b in enumerate(raw)}
    need('typed-factory-every-selected-byte-owned',all(owned.get(at+i)==b for at,h in selected for i,b in enumerate(bytes.fromhex(h))))
    chosen={at+i:b for at,h in selected for i,b in enumerate(bytes.fromhex(h))}
    need('typed-factory-actual-owned-MethodSpec-load',all(chosen.get(base+site[0]+i)==b for i,b in enumerate(bytes.fromhex(site[1]))))
    calls=[]
    for at,h in selected:
        raw=bytes.fromhex(h)
        if raw[:1]==b'\xe8'and all(at+i in chosen for i in range(5)):
            target=at+5+int.from_bytes(bytes(chosen[at+i]for i in range(1,5)),'little',signed=True)
            if target==program['factoryTargetVa']:calls.append(at)
    need('typed-factory-actual-selected-call',len(calls)==1)
    return program,usage,dict(childAllocation=None,constantFields=[],defaultLists=None,originalConstructor=None,
        independentFactory=proof,opaqueUnityInitializationRequired=True,originalManagedConstructorInvoked=False)


def _derive_direct_holder(image,pins,wrapper,wrappers,barrier,ctx,mm,reader,*,formatter_prover=None,direct_factory_prover=None,typed_factory_prover=None):
    from scripts.game_data.memorypack import primitive_param
    from scripts.game_data.memorypack.modelview_reference_sources import get_value
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    base=image.pe.image_base;original=wrapper.wrapped_type;md=image.metadata
    primitive_param.reader_abi(image,ctx,reader,wrapper)
    need('direct-holder-no-prehook','OnDeserialized'not in mm)
    owned,=_holder_fields(image,ctx,wrapper.name,[16],_class_ancestry(ctx,original))
    need('exact-direct-holder-original',owned[:2]==(wrapper.name,original))
    method=mm['GetValue'];_typed_abi(image,ctx,method,wrapper,(original,18,True),[],'directGetValue')
    entry=image.method_pointer_va(method);raw=image.pe.bytes_at_va(entry,5);program=get_value([(entry,raw)],entry)
    get_proof=dict(method=_method_row(image,method),program=program,physicalFunctionExtentProved=False,
        reachableEntryWindow=dict(startRva=entry-base,endRva=entry-base+5,sha256=hashlib.sha256(raw).hexdigest().upper(),
            boundary='complete reachable call-free direct holder GetValue entry; physical extent unproved'))
    original_ctors=[m for m in md.methods_for(ctx.index.types[original])if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    need('one-direct-original-constructor',len(original_ctors)<=1);original_ctor=original_ctors[0]if original_ctors else None
    factories=[]
    for name in('.ctor','CreateInstance'):
        method=mm[name];_typed_abi(image,ctx,method,wrapper,('void',1,False),[],'directFactory')
        body=members._body(image,image.method_pointer_va(method),pins=pins)
        typed=_typed_factory_proof(image,pins,ctx,wrapper,body,barrier,original_ctor,typed_factory_prover)
        if typed is None:
            program,initialization=_direct_factory_proof(image,ctx,wrapper,body,barrier,original_ctor,direct_factory_prover=direct_factory_prover,pins=pins)
            usage=derive_typed_usage_context(image,program['allocation']['site']-base,label=LABEL+'.directOriginalAllocation')
            need('exact-direct-allocated-original',(usage['tag'],usage['typeName'])==(1,original));origin=dict(originalAllocation=usage)
        else:program,usage,initialization=typed;origin=dict(originalAllocation=None,originalTypedFactory=usage)
        factories.append(dict(method=_method_row(image,method),**_body_proof(body),program=program,**origin,
            holderSetter=dict(profile='inline-current-wrapper-holder-writes',program=program['inlineHolderWrites'],fields=[owned]),
            castClasses=[],originalConstructor=initialization['originalConstructor'],initialization=initialization))
    modes={f['program'].get('typedFactoryMode')for f in factories}
    need('same-own-factory-selection-mode',len(modes)==1)
    return dict(wrapperName=wrapper.name,wrappedType=original,typeDefinition=wrapper.type_definition,readerMethod=_method_row(image,reader),
        baseHolder=owned,typedCache=None,directHolderMode=True,coherentGetter=None,GetValue=get_proof,coherentPrehook=None,
        concreteFormatter=_concrete_formatter(image,ctx,wrapper,reader,formatter_prover=formatter_prover,pins=pins),factories=factories,
        originalRegistrationRequired=False,readerEntryPrefixAdmitted=False,positiveGrammarAdmitted=False,
        **(dict(typedOriginalFactoryMode='scriptable-object-generic')if modes=={'scriptable-object-generic'}else{}),
        condition='Actual concrete ReadPackable callback and direct original holder. Initialized current classes, compatible existing holder or normal exact typed allocation, stable disjoint storage and disabled barrier. Original adapter/provider selection and child grammar remain independent.')


def _concrete_formatter(image,ctx,wrapper,reader,*,formatter_prover=None,pins=None):
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;base=image.pe.image_base
    formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
    definitions=image.named_type_definitions.get(formatter_name,());need('one-own-concrete-formatter',len(definitions)==1)
    formatter=definitions[0];methods=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
    need('one-own-slot5-method',len(methods)==1);method=methods[0]
    _vtable(image,formatter.index,5,method.index,LABEL)
    need('instance-slot5-void-two-byrefs',not method.flags&16 and method.slot==5 and
        ctx.type_name(method.return_type)=='void'and method.parameter_count==2)
    scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.slot5Return')
    for parameter,type_name,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
        need('exact-slot5-byrefs',ctx.type_name(parameter.type_index)==type_name and raw[10:12]==bytes((kind,32)))
    # This selected initialized formatter program does not enter its metadata
    # initializer. Pin every actual unwind window, then prove the complete warm
    # path directly; decoding the cold RVA table as instructions grants nothing
    # and can fail on its final data bytes before this exact parser is reached.
    if formatter_prover is None:
        pointer=image.method_pointer_va(method)
        family,windows=members.ec.family_windows(image,pointer-base)
        regions=[(base+w['startRva'],image.window_bytes(w))for w in windows]
        first=next((raw for at,raw in regions if at==pointer),b'')
        if first.startswith(bytes.fromhex('4055564883ec48803d')):
            from scripts.game_data.memorypack.generated_large_cached_sources import formatter_source
            owned=dict(pointer=pointer,family=family,windows=windows,regions=regions)
            return _supplied_formatter_proof(image,wrapper,reader,method,owned,formatter_source)
    forward=members._body(image,image.method_pointer_va(method),pins=pins)
    if formatter_prover is not None:
        return _supplied_formatter_proof(image,wrapper,reader,method,forward,formatter_prover)
    if forward['regions'][0][1].startswith(bytes.fromhex('4055564883ec48803d')):
        from scripts.game_data.memorypack.generated_large_cached_sources import formatter_source
        try:return _supplied_formatter_proof(image,wrapper,reader,method,forward,formatter_source)
        except(ValueError,KeyError,IndexError)as error:
            need('formatter-complete-decoded-rows',all(isinstance(row.get('bytes'),str)for row in forward['rows']),
                dict(wrapperName=wrapper.name,method=_method_row(image,method),sourceWindows=forward['windows'],
                    failedProfile=str(error)[:900],required='complete owned instruction/table partition or exact selected formatter tail'))
    calls=[control_transfer(r)['target']for r in forward['rows']if members.ec.raw(r)[:1]==b'\xe8']
    need('bounded-formatter-forwarder-calls',2<=len(calls)<=4)
    forwarding=prove_zero_wrapper_forwarder(forward['rows'],dict(metadataInit=calls[0],classInit=calls[1]),image.method_pointer_va(reader),label=LABEL+'.slot5Forwarder')
    return dict(method=_method_row(image,method),**_body_proof(forward),program=forwarding)


def _supplied_formatter_proof(image,wrapper,reader,method,body,prover):
    """A fresh complete byte parser after the independent slot/ABI gate.

    A supplied owner proves its complete formatter, never merely its name or
    similarity to the static reader. Default callers still use the strict
    forwarder above. This hook does not provide child grammar admission.
    """
    need('formatter-prover-callable',callable(prover))
    program=prover(image,wrapper,reader,method,body)
    need('complete-supplied-formatter-program',isinstance(program,dict)and
        program.get('completeSelectedFormatterAdmitted')is True and
        program.get('childGrammarAdmitted')is False and bool(program.get('programs')))
    return dict(method=_method_row(image,method),**_body_proof(body),program=program,
        proofMode='independent-complete-parser')


def _derive(image,pins,wrapper,wrappers,barrier,getter_cache,*,formatter_prover=None,direct_factory_prover=None,typed_factory_prover=None):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
    from scripts.game_data.memorypack import module_structure_models as holders,subgame_world_models as world
    from scripts.game_data.memorypack.modelview_reference_sources import get_value
    from scripts.game_data.memorypack.reference_param_profile import _getter_windows
    md=image.metadata;base=image.pe.image_base;ctx=NativeReferenceContext(image);original=wrapper.wrapped_type
    need('concrete-nongeneric-reference-wrapper',not wrapper.abstract and not wrapper.wrapped_is_value_type)
    need('one-current-original-definition',len(image.named_type_definitions.get(original,()))==1)
    td=image.named_type_definitions[original][0];need('concrete-reference-original',not td.flags&128 and not ctx.is_value_type(original))
    mm=pointer.methods(image,wrapper);reader=mm['Deserialize']
    if 'get___instance'not in mm:return _derive_direct_holder(image,pins,wrapper,wrappers,barrier,ctx,mm,reader,
        formatter_prover=formatter_prover,direct_factory_prover=direct_factory_prover,typed_factory_prover=typed_factory_prover)
    getter=mm['get___instance']
    primitive_param.reader_abi(image,ctx,reader,wrapper)
    coherent=members._coherent_getter(image,ctx,wrapper,getter,getter_cache,barrier=base+barrier,pins=pins)
    base_holder=coherent['baseHolder'];typed_cache=coherent['typedCache']
    original_chain=_class_ancestry(ctx,original);wrapper_chain=_class_ancestry(ctx,wrapper.name)
    get_method=mm['GetValue'];_typed_abi(image,ctx,get_method,wrapper,(original,18,True),[],'GetValue')
    getter_target=image.method_pointer_va(getter)
    try:
        entry_windows,thunk=_getter_windows(image,md.types[wrapper.type_definition],get_method)
        need('exact-own-GetValue-tail',thunk['kind']=='owned-zero-context-getter-tail'and
            thunk['targetMethod'][0]==getter.index and base+thunk['targetMethod'][3]==getter_target)
        get_program=get_value([(base+thunk['entryMethod'][3],bytes.fromhex(thunk['instructionHex']))],
            image.method_pointer_va(get_method),getter=getter_target)
        get_proof=dict(method=_method_row(image,get_method),entryWindows=entry_windows,entryProof=thunk,program=get_program)
    except(ValueError,KeyError,IndexError):
        inline=members._coherent_getter(image,ctx,wrapper,get_method,getter_cache,barrier=base+barrier,pins=pins)
        get_proof=dict(method=_method_row(image,get_method),ownedCoherentGetter=inline)
    hook=mm['OnDeserialized'];_typed_abi(image,ctx,hook,wrapper,('void',1,False),[],'prehook')
    hook_body=members._body(image,image.method_pointer_va(hook),pins=pins)
    if coherent['program'].get('getterProfile')=='rsi-zero-rbp-image-base-inline-collector':
        from scripts.game_data.memorypack.generated_large_cached_sources import prehook_program
        hook_program=prehook_program(hook_body['regions'],hook_body['pointer'],cache_slot=typed_cache[2],image_base=base)
    else:hook_program=cached_prehook_program(hook_body['regions'],hook_body['pointer'],cache_slot=typed_cache[2])
    original_ctors=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    need('one-current-original-zero-argument-constructor',len(original_ctors)<=1)
    original_ctor=original_ctors[0]if original_ctors else None
    original_constructor=None
    if original_ctor is not None:
        scalar.owned_method_abi(image,ctx,original_ctor.index,td.index,('void',1,False),[],LABEL+'.originalCtor')
        original_constructor=_original_constructor(image,ctx,original_ctor,original,pins=pins)
    factories=[]
    for name in('.ctor','CreateInstance'):
        method=mm[name];_typed_abi(image,ctx,method,wrapper,('void',1,False),[],'factory')
        body=members._body(image,image.method_pointer_va(method),pins=pins);calls={control_transfer(r)['target']for r in body['rows']if members.ec.raw(r)[:1]==b'\xe8'}
        target=image.method_pointer_va(original_ctor)if original_ctor is not None and image.method_pointer_va(original_ctor)in calls else None
        if target is None and original_constructor is not None and 'ownedAncestorTail'in original_constructor:
            ancestor_target=base+original_constructor['ownedAncestorTail']['targetRva']
            if ancestor_target in calls:target=ancestor_target
        initializers=original_constructor.get('reachableLeaf',{}).get('stores')if original_constructor is not None and(target is None or 'ownedAncestorTail'in original_constructor and target==base+original_constructor['ownedAncestorTail']['targetRva'])else None
        base_constructor=None;base_ctor=None
        if name=='.ctor':
            selected=[]
            for owner in wrapper_chain[1:]:
                for candidate in md.methods_for(ctx.index.types[owner]):
                    if md.string(candidate.name_index)=='.ctor'and candidate.parameter_count==0 and image.method_pointer_va(candidate)in calls:selected.append((owner,candidate))
            need('unique-actual-owned-base-wrapper-constructor',len(selected)<=1)
            if selected:
                owner,candidate=selected[0];need('base-wrapper-constructor-nongeneric',candidate.generic_container_index<0)
                scalar.owned_method_abi(image,ctx,candidate.index,candidate.declaring_type,('void',1,False),[],LABEL+'.baseWrapperCtor')
                base_constructor=_original_constructor(image,ctx,candidate,owner,pins=pins);base_ctor=image.method_pointer_va(candidate)
        value_initialization=None
        try:
            from scripts.game_data.memorypack import generated_nested_header_factory_sources as nested_header
            from scripts.game_data.memorypack import generated_default_list_factory_sources as default_list
            if original==nested_header.TYPE:
                program,value_initialization=nested_header.derive_program(image,pins,ctx,wrapper,body,base+barrier,
                    original_chain=original_chain,wrapper_chain=wrapper_chain)
            elif original in default_list.TYPES:
                program,value_initialization=default_list.derive_program(image,pins,ctx,wrapper,body,base+barrier,
                    original_chain=original_chain,wrapper_chain=wrapper_chain)
            elif coherent['program'].get('getterProfile')=='rsi-zero-rbp-image-base-inline-collector':
                from scripts.game_data.memorypack.generated_large_cached_sources import factory_program as large_factory
                from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
                collector=_barrier(image,base+barrier)
                try:
                    program=large_factory(body['regions'],body['pointer'],ctor=name=='.ctor',original_ctor=target,
                        base_slot=base_holder[2],cache_slot=typed_cache[2],image_base=base,
                        disabled=base+collector['result']['disabledFlagRva'],original_initializers=initializers)
                except(ValueError,KeyError,IndexError):
                    from scripts.game_data.memorypack.generated_condition_factory_sources import large_program
                    program=large_program(body['regions'],body['pointer'],ctor=name=='.ctor',original_ctor=target,
                        base_slot=base_holder[2],cache_slot=typed_cache[2],image_base=base,
                        disabled=base+collector['result']['disabledFlagRva'],original_initializers=initializers,base_ctor=base_ctor)
            elif original_constructor is not None and 'zeroVectorDefaultSource'in original_constructor:
                from scripts.game_data.memorypack import generated_zero_vector_factory_sources as zero_vectors
                need('zero-vector-factory-does-not-invoke-Original-or-base-constructor',target is None and base_ctor is None)
                program=zero_vectors.program(body['regions'],body['pointer'],base+barrier,ctor=name=='.ctor',
                    base_slot=base_holder[2],cache_slot=typed_cache[2])
                value_initialization=zero_vectors.bind_initialization(image,pins,original,program,base+barrier)
            elif original_constructor is not None and 'vectorDefaultSource'in original_constructor:
                from scripts.game_data.memorypack import generated_vector_default_sources as vector_defaults
                need('vector-default-factory-does-not-invoke-Original-constructor',target is None)
                arguments=dict(base_slot=base_holder[2],cache_slot=typed_cache[2])
                if name=='.ctor':arguments['base_ctor']=base_ctor
                if 'scalarDefaultInitialization' in original_constructor['vectorDefaultSource']:
                    from scripts.game_data.memorypack.generated_mixed_vector_default_sources import program as mixed_vector_factory
                    program=mixed_vector_factory(body['regions'],body['pointer'],base+barrier,ctor=name=='.ctor',**arguments)
                else:
                    selected=vector_defaults.constructor_program if name=='.ctor'else vector_defaults.factory_program
                    program=selected(body['regions'],body['pointer'],base+barrier,**arguments)
                value_initialization=vector_defaults.bind_initialization(image,pins,original,program,base+barrier)
            else:
                program=factory_program(body['regions'],body['pointer'],base+barrier,ctor=name=='.ctor',original_ctor=target,
                    base_slot=base_holder[2],cache_slot=typed_cache[2],original_initializers=initializers or None,base_ctor=base_ctor)
        except(ValueError,KeyError,IndexError)as error:
            need('only-constructor-inline-holders',name=='.ctor',str(error))
            try:
                if initializers is not None and target is None:
                    from scripts.game_data.memorypack.generated_scalar_factory_sources import constructor_program as scalar_constructor
                    program=scalar_constructor(body['regions'],body['pointer'],base+barrier,base_slot=base_holder[2],cache_slot=typed_cache[2],initializers=initializers)
                else:program=inline_holder_factory_program(body['regions'],body['pointer'],base+barrier,original_ctor=target,base_slot=base_holder[2],cache_slot=typed_cache[2])
            except(ValueError,KeyError,IndexError)as inline_error:
                from scripts.game_data.memorypack import generated_vector_factory_sources as vector_factories
                try:
                    program=vector_factories.constructor_program(body['regions'],body['pointer'],base+barrier,base_slot=base_holder[2],cache_slot=typed_cache[2])
                    value_initialization=vector_factories.bind(image,ctx,original,program,base+barrier)
                except(ValueError,KeyError,IndexError)as vector_error:
                    try:
                        from scripts.game_data.memorypack.generated_inline_cast_factory_sources import constructor_program as inline_cast_constructor
                        program=inline_cast_constructor(body['regions'],body['pointer'],base+barrier,original_ctor=target,base_slot=base_holder[2],cache_slot=typed_cache[2])
                    except(ValueError,KeyError,IndexError)as cast_error:
                        try:
                            from scripts.game_data.memorypack.generated_condition_factory_sources import literal_program
                            program=literal_program(body['regions'],body['pointer'],base+barrier,ctor=name=='.ctor',
                                original_ctor=target,base_slot=base_holder[2],cache_slot=typed_cache[2],base_ctor=base_ctor)
                        except(ValueError,KeyError,IndexError)as literal_error:
                            raise ValueError(LABEL+'.factory-programs:'+str([str(error),str(inline_error),str(vector_error),str(cast_error),str(literal_error)])[:2200])from literal_error
        usage=derive_typed_usage_context(image,program['allocation']['site']-base,label=LABEL+'.originalAllocation')
        need('exact-allocated-original',(usage['tag'],usage['typeName'])==(1,original))
        classes=[]
        for use in program['classUsages']:
            typed=derive_typed_usage_context(image,use['site']-base,label=LABEL+'.castClass')
            need('same-original-cast-class',(typed['tag'],typed['typeName'])==(1,original));classes.append(typed)
        base_class=None
        if program.get('baseClassUsage')is not None:
            base_class=derive_typed_usage_context(image,program['baseClassUsage']['site']-base,label=LABEL+'.ancestorClass')
            need('owned-ancestor-ready-class',base_class['tag']==1 and base_class['typeName']in original_chain+wrapper_chain)
        ancestor_classes=[]
        for use in program.get('ancestorClassUsages',[]):
            typed=derive_typed_usage_context(image,use['site']-base,label=LABEL+'.ancestorClass')
            need('owned-extra-ancestor-ready-class',typed['tag']==1 and typed['typeName']in original_chain+wrapper_chain);ancestor_classes.append(typed)
        if program['instanceSetter']is None:
            slots=[write['offset']for write in program['inlineHolderWrites']]
            need('both-own-inline-holders',slots==[typed_cache[2],base_holder[2]])
            owned_holders=_holder_fields(image,ctx,wrapper.name,slots,original_chain)
            holder_proof=dict(profile='inline-current-wrapper-holder-writes',**_body_proof(body),program=program['inlineHolderWrites'],fields=owned_holders)
        else:
            setters=[]
            for owner in wrapper_chain:
                setters.extend(m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)=='set___instance'and image.method_pointer_va(m)==program['instanceSetter'])
            need('one-owned-holder-setter',len(setters)==1)
            setter=setters[0];parameters=list(md.parameters_for(setter));need('holder-setter-one-parameter',len(parameters)==1)
            declared=ctx.type_name(parameters[0].type_index);need('holder-setter-compatible-original',declared in original_chain)
            scalar.owned_method_abi(image,ctx,setter.index,setter.declaring_type,('void',1,False),[(declared,18,True)],LABEL+'.holder')
            if program.get('factoryProfile')=='rsi-wrapper-rbp-image-base-inline-collector'or(
                    program.get('factoryProfile')=='initialized-ancestor-rsi-inline-collector-factory.v1'and
                    program.get('holderSourceProfile')=='rsi-wrapper-rbp-image-base-inline-collector')or(
                    program.get('factoryProfile')==nested_header.PROFILE and
                    program.get('holderSourceProfile')=='rsi-wrapper-rbp-image-base-inline-collector')or(
                    program.get('factoryProfile')==default_list.PROFILE and
                    program.get('holderSourceProfile')=='rsi-wrapper-rbp-image-base-inline-collector'):
                from scripts.game_data.memorypack.generated_large_cached_sources import holder_source
                holder_body=holder_source(image,pins,program['instanceSetter'],base_slot=base_holder[2],cache_slot=typed_cache[2],barrier=base+barrier)
                stored=holder_body['program']
            else:
                holder_body=members._body(image,program['instanceSetter'])
                try:stored=world.dual_holder(holder_body['regions'],holder_body['pointer'],base+barrier)
                except ValueError:
                    from scripts.game_data.memorypack.modelview_factory_sources import dual_setter
                    _holder_fields(image,ctx,image.type_name(setter.declaring_type),[16,typed_cache[2]],original_chain)
                    stored=dual_setter(holder_body['regions'],holder_body['pointer'],base+barrier,cache=typed_cache[2],owned_cache=True)
                    stored['holderOffsets']=[16,typed_cache[2]]
            owned_holders=_holder_fields(image,ctx,image.type_name(setter.declaring_type),stored['holderOffsets'],original_chain)
            holder_proof=dict(method=_method_row(image,setter),**_body_proof(holder_body),program=stored,fields=owned_holders)
        if program.get('inlineStrictCasts')is not None:
            inline=program['inlineStrictCasts']
            need('actual-two-inline-current-casts',program['strictCast']is None and len(classes)==2 and inline['sameBaseReferenceCached']and inline['successfulPredicateConditional']and inline['runtimePredicateOutcomeObserved']is False)
            strict_cast=dict(mode='owned-inline-factory-class-checks',program=inline,sourceMethod=_method_row(image,method),
                predicateOutcomeConditional=True,externalPredicateSemanticsClaimed=False)
        else:
            cast_body=members._body(image,program['strictCast']);predicates=[]
            for i,row in enumerate(cast_body['rows']):
                if members.ec.raw(row)[:1]==b'\xe8'and i and members.ec.raw(cast_body['rows'][i-1])==bytes.fromhex('488b09'):
                    predicates.append(control_transfer(row)['target'])
            need('one-actual-strict-cast-predicate',len(predicates)==1)
            cast_program=holders.rolling_owned_strict_cast(cast_body['regions'],cast_body['pointer'],predicates[0])
            strict_cast=dict(**_body_proof(cast_body),program=cast_program)
        extra_initialization={}
        if 'inlinedNestedInitialization'in program:
            from scripts.game_data.memorypack.generated_inline_cast_factory_sources import bind_initialization
            extra_initialization['inlinedNestedInitialization']=bind_initialization(image,ctx,wrapper,program)
        factories.append(dict(method=_method_row(image,method),**_body_proof(body),program=program,
            originalAllocation=usage,castClasses=classes,ancestorClass=base_class,ancestorClasses=ancestor_classes,
            originalConstructor=original_constructor if target is not None or initializers or value_initialization is not None else None,
            holderSetter=holder_proof,
            strictCast=strict_cast,**extra_initialization))
        if value_initialization is not None:factories[-1]['valueInitialization']=value_initialization
        if base_constructor is not None:
            need('actual-base-constructor-was-source-proved',program.get('baseConstructorTarget')==base_ctor)
            factories[-1]['baseConstructor']=base_constructor
    formatter_proof=_concrete_formatter(image,ctx,wrapper,reader,formatter_prover=formatter_prover,pins=pins)
    return dict(wrapperName=wrapper.name,wrappedType=original,typeDefinition=wrapper.type_definition,
        readerMethod=_method_row(image,reader),baseHolder=base_holder,typedCache=typed_cache,
        concreteFormatter=formatter_proof,
        coherentGetter=coherent,GetValue=get_proof,coherentPrehook=dict(method=_method_row(image,hook),**_body_proof(hook_body),program=hook_program),
        factories=factories,originalRegistrationRequired=False,readerEntryPrefixAdmitted=False,positiveGrammarAdmitted=False,
        condition='The independent current parent selects this concrete ReadPackable wrapper callback. Initialized coherent compatible classes, successful typed allocation/normal original constructor, compatible same-reference casts and disabled barriers are required. Runtime provider/default/callback selection and original constructor effects remain unobserved.')


def derive_many(image,pins,wrapper_names):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_action_sources import _prepare
    need('bounded-distinct-owners',0<len(wrapper_names)<=512 and len(set(wrapper_names))==len(wrapper_names))
    _publication_gate(image,pins);_,barrier,_=_prepare(image,pins)
    inventory=list(image.memorypack_wrappers.values());wrappers={w.name:w for w in inventory};need('unique-current-wrappers',len(wrappers)==len(inventory))
    cache={};owners=[]
    for name in wrapper_names:
        try:owners.append(dict(status='lifecycle-source-proved',proof=_derive(image,pins,wrappers[name],wrappers,barrier,cache)))
        except(ValueError,KeyError,IndexError,TypeError)as error:owners.append(dict(status='pendingReview',wrapperName=name,reason=str(error)[:2400]))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,owners=owners,wholeOwnerAdmitted=False)))
