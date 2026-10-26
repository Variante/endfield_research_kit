"""Actual current ParamKeyValue/ParamValue formatter bodies.

Generated slot-five callbacks inline their readers. They are proved directly;
no alias to a shorter static Deserialize or historical component is assumed.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def formatter_deserialize_declaration(image,ctx):
    """Select and authenticate the ordinary formatter's slot-five declaration."""
    import struct
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;owner=ctx.index.types['MemoryPack.MemoryPackFormatter`1']
    need=lambda k,e,a:scalar.need('currentParamValue.formatter',k,e,a)
    matches=[m for m in md.methods_for(owner)if md.string(m.name_index)=='Deserialize'
        and m.slot==5 and not m.flags&16 and m.parameter_count==2
        and ctx.type_name(m.return_type)=='void']
    need('one-instance-slot5-void-two-byref-declaration',1,len(matches))
    method,=matches;scalar.ordinary(image,ctx.type_pointer(method.return_type),1,'currentParamValue.formatter.void')
    parameters=list(md.parameters_for(method));need('parameter-count',2,len(parameters))
    reader=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
    need('same-reader-byref',(ctx.index.types['MemoryPack.MemoryPackReader'].index,b'\x11\x20'),
        (int.from_bytes(reader[:8],'little'),reader[10:12]))
    section=md.sections['genericContainers'];at=section.offset+owner.generic_container_index*16
    need('bounded-owner-container',True,owner.generic_container_index>=0
        and section.offset<=at<=section.offset+section.size-16)
    definition,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
    need('one-owned-class-parameter',(owner.index,1,0),(definition,count,is_method))
    identity=type_parameter_owner(md.buf,start,[t.generic_container_index for t in md.types],
        source='currentParamValue.formatter')
    need('reciprocal-class-parameter',(owner.index,0),(identity['typeIndex'],identity['ordinal']))
    output=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16)
    need('same-owner-var-byref',(start,b'\x13\x20'),
        (int.from_bytes(output[:8],'little'),output[10:12]))
    return dict(methodDefinition=method.index,formatterSlot=5,readerByrefRawHex=reader.hex(),
        outputByrefRawHex=output.hex(),ownedTypeParameter=identity)


def flag(g,prefix='803d'):
    cell=g.relative(prefix)+1;g.take('00');return cell


def key_value_program(regions,entry,o,s,*,mode='lookup',null=False,new=True):
    if mode not in('null','empty','lookup')or type(null)is not bool or type(new)is not bool:
        raise ValueError('currentParamKV.profile')
    cur,rem,adv,used=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);alloc=None;context=None;pool=None;collector=[]
    g.take('48895c2418','55','56','57','4883ec20');ready=flag(g)
    g.take('498bf8','488bda');g.branch('75',True,1)
    wrapper_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
    reader_ready=flag(g);g.branch('75',True,1)
    g.take('837b'+rem+'01');g.branch('7d',True,1)
    g.take('488b43'+cur,'0fb628','8b73'+rem,'83ee01');g.branch('79',True,1)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'8973'+rem,'4080fdff')
    g.branch('0f84',null)
    if null:
        g.take('33c0','488bcf','488907');g.call(s['barrier'])
    else:
        g.take('48833f00');g.branch('75',not new,1)
        if new:
            site=g.at;cell=g.relative('488b0d')
            if cell!=wrapper_class:raise ValueError('currentParamKV.same-wrapper-class')
            alloc=dict(site=site,cell=cell)
            g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bcf','488937');g.call(s['barrier'])
        g.take('4080fd02');g.branch('0f85',False)
        pool_ready=flag(g);g.take('488b2f');g.branch('75',True,1)
        pool=g.relative('488b05')
        if pool!=s['pool']:raise ValueError('currentParamKV.pool-class')
        g.take('488b88b8000000','48833900');g.branch('0f84',False)
        g.take('4c89742440','837b'+rem+'04');g.branch('7d',True,1)
        g.take('488b43'+cur,'8b30','448b73'+rem,'4183c6fc');g.branch('79',True,1)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','448973'+rem,
            '4c8b742440','83fefe');g.branch('74',mode=='null',1)
        if mode=='null':g.take('33c0');g.jump('eb',1)
        else:
            g.take('83feff');g.branch('74',mode=='empty',1)
            if mode=='empty':
                if g.relative('488b05')!=s['empty']:raise ValueError('currentParamKV.empty-string')
                g.jump('eb',1)
            else:
                if g.relative('488b05')!=pool:raise ValueError('currentParamKV.same-pool')
                g.take('488b88b8000000','488b09','4885c9');g.branch('0f84',False)
                g.take('4533c0','8bd6');g.call(s['lookup']);g.jump('eb',1)
        g.take('4885ed');g.branch('0f84',False)
        g.take('4c8b4510','4d85c0');g.branch('0f84',False)
        collector.append(flag(g,'833d'));g.relative('488d35');g.take('49894010')
        g.branch('74',True,1)
        site=g.at;cell=g.relative('488b15');context=dict(site=site,cell=cell)
        g.take('488bcb','488b3f');call=g.at;g.call(s['valueReader'])
        g.take('4885ff');g.branch('0f84',False)
        g.take('4c8b4710','4d85c0');g.branch('74',False,1)
        collector.append(flag(g,'833d'));g.take('49894018');g.branch('74',True,1)
    g.take('488b5c2450','4883c420','5f','5e','5d','c3')
    if len(set(collector))>1:raise ValueError('currentParamKV.same-disabled-collector')
    return dict(selectedBytes=g.seen,readerTargetMode='independently-proved-inline',
        null=null,newWrapper=new,mode=None if null else mode,memberCount=None if null else 2,
        entryReader='rdx',entryOutput='r8',sameReader=True,headerBytes=1,
        allocation=alloc,wrapperClassCell=wrapper_class,readerReadyFlag=reader_ready,
        formatterReadyFlag=ready,typedValueRequest=context,
        valueReadCall=None if null else call,poolClassCell=pool,
        keyFieldOffset=None if null else 16,valueFieldOffset=None if null else 24,
        pooledKeyBytes=0 if null else 4,normalReturn=True,childGrammarAdmitted=False,
        condition='Initialized generated formatter/static reader metadata, buffered disjoint input/output, compatible existing wrapper or normal exact typed zeroed allocation plus independently proved constructor; matched nonnull pool and normal lookup, typed ParamValue child, disabled collector. No cold/refill/live provider/default-selection or child grammar inferred.')


def reference_constructor(regions,entry,s):
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20');ready=flag(g)
    g.take('488bf9');g.branch('75',True,1)
    site=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
    g.take('4885c0');g.branch('74',False,1)
    collector=flag(g,'833d');g.take('48894710');g.branch('74',True,1)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,readyFlag=ready,allocation=dict(site=site,cell=cell),
        collectorDisabledFlag=collector,originalHolder=16,
        result='same normal zeroed typed original allocator reference stored unchanged into wrapper+16',
        normalReturn=True)


def value_program(regions,entry,o,s,*,count=1,null=False,new=True):
    if type(count)is not int or count not in(-1,0,1)or type(null)is not bool or type(new)is not bool:
        raise ValueError('currentParamValue.profile')
    cur,rem,adv,used,total=(bytes((o[k],)).hex()for k in
        ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g=BytesPath(regions,entry);allocation=context=None;collectors=[]
    g.take('4053','55','56','57','4883ec28');ready=flag(g)
    g.take('498bf0','488bda');g.branch('75',True,1)
    wrapper_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
    reader_ready=flag(g);g.branch('75',True,1)
    g.take('837b'+rem+'01');g.branch('7d',True,1)
    g.take('488b43'+cur,'0fb628','8b7b'+rem,'83ef01');g.branch('79',True,1)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'897b'+rem,'4080fdff')
    g.branch('0f84',null)
    if null:
        g.take('33ff','488bce','48893e','4883c428','5f','5e','5d','5b')
        if g.relative('e9')!=s['barrier']:raise ValueError('currentParamValue.null-barrier-tail')
    else:
        g.take('4c89742450','48833e00');g.branch('75',not new,1)
        if new:
            site=g.at;cell=g.relative('488b0d')
            if cell!=wrapper_class:raise ValueError('currentParamValue.same-wrapper-class')
            allocation=dict(site=site,cell=cell)
            g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bce','48893e');g.call(s['barrier'])
        g.take('4080fd02');g.branch('0f85',False)
        g.take('837b'+rem+'04','488b3e');g.branch('7d',True,1)
        g.take('488b43'+cur,'448b30','8b6b'+rem,'83c5fc');g.branch('79',True,1)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','896b'+rem,
            '4885ff');g.branch('0f84',False)
        g.take('488b4710','4885c0');g.branch('0f84',False)
        g.take('44897010','4c897c2420','4c8b3e')
        site=g.at;context=dict(site=site,cell=g.relative('488b35'))
        g.take('48837e3800');g.branch('75',True,1)
        g.take('488b4638','33ff','48897c2458','488b28','48397d38')
        g.branch('75',True,1)
        g.take('837b'+rem+'04');g.branch('7d',True,1)
        g.take('488b43'+cur,'8b30','448b73'+rem,'4183c6fc');g.branch('79',True,1)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','448973'+rem,
            '486343'+used,'488b4b'+total,'482bc8','4863c6','483bc8')
        g.branch('0f8c',False);g.relative('4c8d35');g.take('83feff')
        g.branch('0f84',count==-1)
        if count==-1:
            g.take('488d4c2458','48897c2458');g.call(s['barrier'])
        else:
            g.take('85f6');g.branch('0f84',count==0)
            if count:
                g.take('488b442458','4885c0');g.branch('74',True,1)
                g.take('488b4538','488b4010','f6803801000001');g.branch('75',True,1)
                g.take('488bd6','488bc8');g.call(s['arrayAllocate'])
                collectors.append(g.relative('393d'));g.take('4889442458');g.branch('74',True,1)
                provider_class=g.relative('488b0d');g.take('39b9e0000000');g.branch('75',True,1)
                g.take('488b4d38','488b4918');g.call(s['provider'])
                g.take('488be8','85f6');g.branch('0f8e',False)
                g.take('6666660f1f840000000000');loop=g.at
                g.take('488b4c2458','4885c9');g.branch('0f84',False)
                g.take('4885ed');g.branch('0f84',False)
                g.take('3b7918');g.branch('0f83',False)
                g.take('448bcf','4c8bc3','4983c102','488bd5','49c1e104','4c03c9')
                child_call=g.at;g.call(s['atomDispatch'])
                g.take('ffc7','3bfe')
                if g.relative('7c',1)!=loop:raise ValueError('currentParamValue.exact-array-backedge')
                g.jump('e9')
            else:
                g.take('488b4538','488b5808','48397b38');g.branch('75',True,1)
                g.take('488b4b38','33d2');g.call(s['indexed'])
                g.take('39b8e0000000');g.branch('75',True,1)
                g.take('488b4b38','33d2');g.call(s['indexed'])
                collectors.append(g.relative('393d'))
                g.take('488b88b8000000','488b01','4889442458');g.branch('74',True,1)
        g.take('4d85ff');g.branch('0f84',False)
        g.take('4d8b4710','4d85c0');g.branch('0f84',False)
        collectors.append(flag(g,'833d'))
        g.take('488b442458','49894018');g.branch('74',True,1)
        g.take('4c8b7c2420','4c8b742450','4883c428','5f','5e','5d','5b','c3')
    if len(set(collectors))>1:raise ValueError('currentParamValue.same-disabled-collector')
    return dict(selectedBytes=g.seen,readerTargetMode='independently-proved-inline',
        null=null,newWrapper=new,allocation=allocation,wrapperClassCell=wrapper_class,
        formatterReadyFlag=ready,readerReadyFlag=reader_ready,memberCount=None if null else 2,
        arrayContext=context,arrayCountProfile=None if null else'null'if count==-1 else
        'zero'if count==0 else'all-positive-Int32',
        headerBytes=1,enumWireBytes=0 if null else 4,arrayHeaderBytes=0 if null else 4,
        atomCall=None if null or count<1 else child_call,
        atomProviderClassCell=None if null or count<1 else provider_class,
        elementManagedStride=16,normalReturn=True,childGrammarAdmitted=False,
        countInvariant='Array output starts null. EDI starts0 and only INC EDI writes it after one exact child dispatch into array+32+i*16. ESI count is immutable and exact signed JL returns to the same loop head. Normally allocated exact typed array has count elements; all-positive bounded count needs no reuse/growth path.',
        condition='Initialized generated and closed Reader/ReadArray/ArrayFormatter contexts, compatible wrappers or normal typed zeroed allocation/constructor, ready exact array element class, normal array allocation and matching provider/hidden16 callback, buffered disjoint stable input/storage and disabled collector. Element wire grammar, cold/refill/default/runtime selection are independent.')


def atom_program(regions,entry,o,s,*,mode='lookup',null=False,new=True):
    if mode not in('null','empty','lookup')or type(null)is not bool or type(new)is not bool:
        raise ValueError('currentParamAtom.profile')
    cur,rem,adv,used=(bytes((o[k],)).hex()for k in
        ('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);allocation=None
    g.take('48895c2418','55','56','57','4883ec20');ready=flag(g)
    g.take('498bf8','488bda');g.branch('75',True,1)
    wrapper_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
    reader_ready=flag(g);g.branch('75',True,1)
    g.take('837b'+rem+'01');g.branch('7d',True,1)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('79',True,1)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff')
    g.branch('75',not null,1)
    if null:
        g.take('33c0','488bcf','488907','488b5c2450','4883c420','5f','5e','5d')
        if g.relative('e9')!=s['barrier']:raise ValueError('currentParamAtom.null-barrier-tail')
    else:
        g.take('4c89742440','48833f00');g.branch('75',not new,1)
        if new:
            site=g.at;cell=g.relative('488b0d')
            if cell!=wrapper_class:raise ValueError('currentParamAtom.same-wrapper-class')
            allocation=dict(site=site,cell=cell);g.call(s['allocate'])
            g.take('4885c0');g.branch('0f84',False)
            g.take('0f57c0','488bcf','0f114010','488907');g.call(s['barrier'])
        g.take('4080fe02');g.branch('0f85',False)
        g.take('837b'+rem+'08','488b37');g.branch('7d',True,1)
        g.take('488b43'+cur,'4c8b30','8b6b'+rem,'83c5f8');g.branch('79',True,1)
        g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','896b'+rem,'4885f6')
        g.branch('0f84',False);pool_ready=flag(g)
        g.take('4c897610','488b37');g.branch('75',True,1)
        pool=g.relative('488b05')
        if pool!=s['pool']:raise ValueError('currentParamAtom.pool-class')
        g.take('488b88b8000000','48833900');g.branch('0f84',False)
        g.take('837b'+rem+'04');g.branch('7d',True,1)
        g.take('488b43'+cur,'8b38','8b6b'+rem,'83c5fc');g.branch('79',True,1)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','896b'+rem,'83fffe')
        g.branch('74',mode=='null',1)
        if mode=='null':g.take('33c0');g.jump('eb',1)
        else:
            g.take('83ffff');g.branch('74',mode=='empty',1)
            if mode=='empty':
                if g.relative('488b05')!=s['empty']:raise ValueError('currentParamAtom.empty-string')
                g.jump('eb',1)
            else:
                if g.relative('488b05')!=pool:raise ValueError('currentParamAtom.same-pool')
                g.take('488b88b8000000','488b09','4885c9');g.branch('0f84',False)
                g.take('4533c0','8bd7');g.call(s['lookup'])
                g.jump('eb',1)
        g.take('4885f6');g.branch('0f84',False)
        collector=flag(g,'833d');g.take('48894618');g.branch('74',True,1)
        g.take('4c8b742440','488b5c2450','4883c420','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,readerTargetMode='independently-proved-inline',
        null=null,newWrapper=new,allocation=allocation,wrapperClassCell=wrapper_class,
        formatterReadyFlag=ready,readerReadyFlag=reader_ready,memberCount=None if null else 2,
        mode=None if null else mode,headerBytes=1,wireBytes=1 if null else 13,
        rawBits=0 if null else 64,pooledStringBytes=0 if null else 4,
        managedValueBytes=16,normalReturn=True,
        condition='Initialized generated formatter/static reader and StringPool; compatible wrapper or normal exact typed allocation cleared16 bytes, disjoint stable buffered Reader/output; pool sentinel -2/-1/nonnegative and normal lookup, disabled collector. FF clears wrapper reference; independently proved hidden16 conversion supplies default zero16. No runtime provider/default selection.')


def atom_static_program(regions,entry,o,s,*,mode='lookup',null=False,new=True):
    """Independently prove the actual static reader reached by the fast slot."""
    if mode not in('null','empty','lookup')or type(null)is not bool or type(new)is not bool:
        raise ValueError('currentParamAtom.static-profile')
    if o!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:
        raise ValueError('currentParamAtom.static-reader-layout')
    g=BytesPath(regions,entry);allocation=None
    g.take('48895c2418','55','56','57','4883ec20');ready=flag(g)
    g.take('488bfa','488bd9');g.branch('75',True,1)
    g.take('837b3001');g.branch('7d',True,1)
    g.take('488b4350','0fb628','8b7330','83ee01');g.branch('79',True,1)
    g.take('48ff4350','ff4340','ff4344','897330','4080fdff');g.branch('75',not null,1)
    if null:
        g.take('33db','488bcf','48891f','488b5c2450','4883c420','5f','5e','5d')
        if g.relative('e9')!=s['barrier']:raise ValueError('currentParamAtom.static-null-barrier')
    else:
        g.take('48833f00');g.branch('75',not new,1)
        if new:
            allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(s['allocate'])
            g.take('4885c0');g.branch('0f84',False)
            g.take('0f57c0','488bcf','0f114010','488907');g.call(s['barrier'])
        g.take('4080fd02');g.branch('0f85',False)
        g.take('4c89742448','837b3008','488b37');g.branch('7d',True,1)
        g.take('488b4350','4c8b30','8b6b30','83c5f8');g.branch('79',True,1)
        g.take('4883435008','83434008','83434408','896b30','4885f6');g.branch('0f84',False)
        pool_ready=flag(g);g.take('4c897610','488b37');g.branch('75',True,1)
        if g.relative('488b05')!=s['pool']:raise ValueError('currentParamAtom.static-pool-class')
        g.take('488b88b8000000','48833900');g.branch('0f84',False)
        g.take('837b3004');g.branch('7d',True,1)
        g.take('488b4350','8b38','8b6b30','83c5fc');g.branch('79',True,1)
        g.take('4883435004','83434004','83434404','896b30','83fffe');g.branch('74',mode=='null',1)
        if mode=='null':g.take('33db');g.jump('eb',1)
        else:
            g.take('83ffff');g.branch('74',mode=='empty',1)
            if mode=='empty':
                if g.relative('488b1d')!=s['empty']:raise ValueError('currentParamAtom.static-empty-string')
                g.jump('eb',1)
            else:
                if g.relative('488b05')!=s['pool']:raise ValueError('currentParamAtom.static-same-pool')
                g.take('488b88b8000000','488b19','4885db');g.branch('0f84',False)
                g.take('4533c0','8bd7','488bcb');g.call(s['lookup']);g.jump('eb',1);g.take('488bd8')
        g.take('4885f6');g.branch('0f84',False)
        collector=flag(g,'833d');g.take('48895e18');g.branch('74',True,1)
        g.take('4c8b742448','488b5c2450','4883c420','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,null=null,newWrapper=None if null else new,
        typedAllocation=allocation,metadataReadyFlag=ready,wireBytes=1 if null else 13,
        managedValueBytes=16,normalReturn=True,entryFrameRestored=True,
        reader='incoming RCX saved RBX',wrapperOutput='incoming RDX saved RDI',
        liveFormatterSelectionObserved=False)


def atom_wrapper_invoke_program(regions,entry,*,prepare,callback,reader):
    """Own the selected exact fast comparison and its actual static-reader E8."""
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec70',
        '4d8be9','4d8bf8','488bfa','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','4803c9','488b07','4c8b14c8','488b5cc808','48899c24c0000000')
    excluded=g.relative('488d05')
    if excluded==callback:raise ValueError('currentParamAtom.unproved-first-inline-target')
    g.take('4c3bd0');g.branch('0f85',True)
    if g.relative('488d05')!=callback:raise ValueError('currentParamAtom.exact-second-inline-target')
    g.take('4c3bd0');g.branch('0f85',False)
    ready=flag(g);g.branch('0f85',True)
    usage=dict(instruction=g.at,cell=g.relative('488b0d'))
    g.take('83b9e000000000');g.branch('75',True,1)
    g.take('4533c0','498bd5','498bcf');site=g.at;g.call(reader);g.jump('e9')
    g.take('488b9c24b0000000','4883c470','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,selectedCallback=callback,excludedFirstCallback=excluded,
        actualStaticReader=reader,sourceCall=site,metadataReadyFlag=ready,wrapperUsage=usage,
        slot=5,callbackReceiverUnused=True,sameReaderAndWrapperOutput=True,
        readerArguments=dict(rcx='incoming R8 reader',rdx='incoming R9 wrapper output',r8='zero MethodInfo'),
        normalReturn=True,entryFrameRestored=True,liveCallbackSelectionObserved=False)


def _body_target(body,text,*,before=False):
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    i=next(i for i,r in enumerate(body['rows'])if r['text']==text)
    rows=list(reversed(body['rows'][:i]))if before else body['rows'][i+1:]
    return next(control_transfer(r)['target']for r in rows if control_transfer(r)['kind']=='call')


def derive_key_value_callback(image,pair,wrapper):
    """Exact current inline callback, ctor, field getter and child request."""
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_source_helper,pooled_inline_sources
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    ctx=NativeReferenceContext(image);base=image.pe.image_base;md=image.metadata
    def need(k,e,a):scalar.need('currentParamKV',k,e,a)
    need('closed-pair','Beyond.Gameplay.ParamKeyValue',wrapper.wrapped_type)
    need('reference-kind',False,ctx.is_value_type(wrapper.wrapped_type))
    need('members',[('key','string'),('value','Beyond.Gameplay.ParamValue')],
        [(m.name,m.declared_type)for m in wrapper.members])
    fields=[list(ctx.field(wrapper.wrapped_type+'::'+m.name))for m in wrapper.members]
    need('field-layout',[[wrapper.wrapped_type,'string',16],
        [wrapper.wrapped_type,'Beyond.Gameplay.ParamValue',24]],fields)
    need('original-holder',(wrapper.name,wrapper.wrapped_type,16),ctx.field(wrapper.name+'::__instance'))
    mm=methods(image,wrapper);formatter=md.methods[pair['composition']['methods'][1][0]]
    source=owned(image,image.method_pointer_va(formatter));ctor=owned(image,image.method_pointer_va(mm['.ctor']))
    pool_fact=pooled_source_helper._contract()
    pool_symbols=pooled_inline_sources._symbols(image,pool_fact)
    symbols=dict(pool_symbols,allocate=_body_target(source,'mov rsi, rax',before=True),
        constructor=image.method_pointer_va(mm['.ctor']),
        barrier=_body_target(source,'mov [rdi], rsi'),
        valueReader=_body_target(source,'mov rdi, [rdi]'))
    offsets=scalar.reader_offsets(image,'currentParamKV')
    programs=[key_value_program(source['regions'],source['pointer'],offsets,symbols,
        null=n,new=c,mode=mode)for n in(False,True)for c in(False,True)for mode in('null','empty','lookup')]
    constructor=reference_constructor(ctor['regions'],ctor['pointer'],symbols)
    allocations=[]
    for role,site,expected in(('original',constructor['allocation']['site'],wrapper.wrapped_type),
        ('wrapper',next(p['allocation']['site']for p in programs if p['allocation']),wrapper.name)):
        usage=derive_typed_usage_context(image,site-base,label='currentParamKV.'+role)
        need('typed-allocation:'+role,(1,expected),(usage['tag'],usage['typeName']))
        allocations.append(usage)
    read=next(p for p in programs if p['typedValueRequest'])
    usage=derive_typed_usage_context(image,read['typedValueRequest']['site']-base,label='currentParamKV.value')
    need('typed-value',('MemoryPack.MemoryPackReader','ReadValue',['Beyond.Gameplay.ParamValue']),
        (usage['typeName'],usage['methodName'],usage['methodArguments']))
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    return json.loads(json.dumps(dict(readerTargetMode='independently-proved-inline',
        typeName=wrapper.wrapped_type,wrapperName=wrapper.name,fields=fields,
        formatterMethod=pair['composition']['methods'][1],sourceWindows=source['windows'],
        staticReaderMethod=[mm['Deserialize'].index,wrapper.name,'Deserialize',image.method_pointer_va(mm['Deserialize'])-base],
        staticReaderEquivalenceClaimed=False,programs=programs,constructor=constructor,
        constructorWindows=ctor['windows'],typedAllocations=allocations,
        getter=getter,getterReturnedReferenceSemanticsProved=True,
        typedValueRequest=usage,valueReaderTargetRva=symbols['valueReader']-base,
        pooledSymbols={k:v-base for k,v in pool_symbols.items()},childGrammarAdmitted=False)))


def derive_key_value(image,pins):
    import json
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols,validate_claims
    from scripts.game_data.memorypack import pooled_source_helper,levelscript_interactive_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
    base=image.pe.image_base;name='Beyond.Gameplay.ParamKeyValue'
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==name]
    pair=derive_pair(image,name);pool=pooled_source_helper._contract()
    scalar.need('currentParamKV','pool-build',pins,pool['nativeInputs'])
    pool_proof=pooled_source_helper.validate_on_image(image,base+pool['targetRva'],pins)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=derive_key_value_callback)
    callback=adapter['pairForwarder']
    fact=json.loads((CONTRACTS_DIR/'levelscript_interactive_native.json').read_bytes())
    scalar.need('currentParamKV','reference-source-build',pins,fact['nativeInputs'])
    symbols={k:base+v for k,v in fact['symbols'].items()}
    scalar.need('currentParamKV','actual-reference-source',symbols['readValue']if 'readValue'in symbols else
        base+fact['sources']['readValue']['entryRva'],base+callback['valueReaderTargetRva'])
    source=owned(image,base+callback['valueReaderTargetRva'])
    reference=levelscript_interactive_sources.read_value_reference_program(source['regions'],source['pointer'],symbols)
    contexts=fact['methodContexts'];fresh=ContextSymbols(image)
    for c in contexts:validate_claims(c,fresh.context(c['definition'],is_method=True),label='currentParamKV.reference-context')
    context=validate_read_value_context(image,*contexts,GenericEntries(image),
        fail=lambda k,e,a:scalar.need('currentParamKV',k,e,a))
    return json.loads(json.dumps(dict(typeName=name,profile=pair,adapter=adapter,
        pool=pool_proof,referenceSource=reference,referenceWindows=source['windows'],
        referenceContext=context,childGrammarAdmitted=False,wholeOwnerAdmitted=False)))


def derive_value_callback(image,pair,wrapper):
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    ctx=NativeReferenceContext(image);base=image.pe.image_base;md=image.metadata
    def need(k,e,a):scalar.need('currentParamValue',k,e,a)
    need('nominal','Beyond.Gameplay.ParamValue',wrapper.wrapped_type)
    need('members',[('type','Beyond.GEnums.ParamRealType'),('valueArray','Beyond.Gameplay.ParamValueAtom[]')],
        [(m.name,m.declared_type)for m in wrapper.members])
    fields=[list(ctx.field(wrapper.wrapped_type+'::'+m.name))for m in wrapper.members]
    need('original-field-layout',[[wrapper.wrapped_type,'Beyond.GEnums.ParamRealType',16],
        [wrapper.wrapped_type,'Beyond.Gameplay.ParamValueAtom[]',24]],fields)
    need('enum-int32-backing','int',ctx.field('Beyond.GEnums.ParamRealType::value__')[1])
    need('reference-kind',False,ctx.is_value_type(wrapper.wrapped_type))
    need('wrapper-holder',(wrapper.name,wrapper.wrapped_type,16),ctx.field(wrapper.name+'::__instance'))
    mm=methods(image,wrapper);m=md.methods[pair['composition']['methods'][1][0]]
    source=owned(image,image.method_pointer_va(m));ctor=owned(image,image.method_pointer_va(mm['.ctor']))
    symbols=dict(allocate=_body_target(source,'mov rdi, rax',before=True),
        constructor=ctor['pointer'],barrier=_body_target(source,'mov [rsi], rdi'),
        arrayAllocate=_body_target(source,'mov rdx, rsi'),
        provider=_body_target(source,'mov rcx, [rcx+0x18]'),
        atomDispatch=_body_target(source,'shl r9, 0x4'),
        indexed=_body_target(source,'mov rcx, [rbx+0x38]'))
    offsets=scalar.reader_offsets(image,'currentParamValue')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[value_program(source['regions'],source['pointer'],offsets,symbols,
        count=n,null=z,new=c)for z in(False,True)for c in(False,True)for n in(-1,0,1)]
    constructor=reference_constructor(ctor['regions'],ctor['pointer'],symbols)
    allocations=[]
    for role,site,expected in(('original',constructor['allocation']['site'],wrapper.wrapped_type),
        ('wrapper',next(p['allocation']['site']for p in programs if p['allocation']),wrapper.name)):
        usage=derive_typed_usage_context(image,site-base,label='currentParamValue.'+role)
        need('typed-allocation:'+role,(1,expected),(usage['tag'],usage['typeName']));allocations.append(usage)
    array=next(p for p in programs if p['arrayContext'])
    usage=derive_typed_usage_context(image,array['arrayContext']['site']-base,label='currentParamValue.array')
    need('typed-array',('MemoryPack.MemoryPackReader','ReadArray',[],['Beyond.Gameplay.ParamValueAtom']),
        tuple(usage[k]for k in('typeName','methodName','classArguments','methodArguments')))
    field,=[f for f in md.fields_for(ctx.index.types[wrapper.wrapped_type])if md.string(f.name_index)=='valueArray']
    raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
    need('SZARRAY-field',b'\x1d\x00',raw[10:12]);element_pointer=int.from_bytes(raw[:8],'little')
    element_raw=image.pe.bytes_at_va(element_pointer,16)
    need('exact-Atom-value-element',(b'\x11\x80',ctx.index.types['Beyond.Gameplay.ParamValueAtom'].index),
        (element_raw[10:12],int.from_bytes(element_raw[:8],'little')))
    symbols_ctx=ContextSymbols(image);first=symbols_ctx.context(usage['methodSpec'][0],is_method=True)
    second=symbols_ctx.context(first['entries'][0]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[first,second],label='currentParamValue.array')
    deserialize=formatter_deserialize_declaration(image,ctx)
    array_context=validate_read_array_context(image,[first,second],usage,GenericEntries(image),element_pointer,
        deserialize['methodDefinition'],fail=need)
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    return json.loads(json.dumps(dict(readerTargetMode='independently-proved-inline',
        typeName=wrapper.wrapped_type,wrapperName=wrapper.name,fields=fields,
        formatterMethod=pair['composition']['methods'][1],sourceWindows=source['windows'],
        staticReaderEquivalenceClaimed=False,programs=programs,constructor=constructor,
        constructorWindows=ctor['windows'],typedAllocations=allocations,
        getter=getter,getterReturnedReferenceSemanticsProved=True,
        typedArrayRequest=usage,arrayContext=array_context,declaredArrayContexts=[first,second],
        formatterDeserializeDeclaration=deserialize,
        atomDispatchTargetRva=symbols['atomDispatch']-base,
        symbolRvas={k:v-base for k,v in symbols.items()},childGrammarAdmitted=False)))


def derive_atom(image,pins,dispatch_target):
    """Own nominal Atom16, actual source, hidden output and exact array child."""
    import json,struct
    from scripts.game_data.il2cpp.formatter_composition import (
        derive_typed_usage_context,validate_registered_formatter_composition,_vtable)
    from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_source_helper,pooled_inline_sources,primitive_param
    from scripts.game_data.memorypack.buff_ptr_sources import _adapter_context
    from scripts.game_data.memorypack.skill_hidden_value_transfers import inline16_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    ctx=NativeReferenceContext(image);base=image.pe.image_base;md=image.metadata;entries=GenericEntries(image)
    def need(k,e,a):scalar.need('currentParamAtom',k,e,a)
    original='Beyond.Gameplay.ParamValueAtom';wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==original]
    need('value-kind',True,ctx.is_value_type(original))
    need('members',[('valueBit64','long'),('valueString','string')],[(m.name,m.declared_type)for m in wrapper.members])
    need('fields',[(original,'long',16),(original,'string',24)],
        [ctx.field(original+'::'+m.name)for m in wrapper.members])
    need('value-holder',(wrapper.name,original,16),ctx.field(wrapper.name+'::__instance'))
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+ctx.index.types[original].index*8)
    need('boxed-size32',32,image.pe.u32_at_va(size))
    pair=derive_pair(image,original)
    validate_eager_wrap_registration(image,pair['registration'],label='currentParamAtom.pair')
    validate_registered_formatter_composition(image,pair['composition'],label='currentParamAtom.pair')
    mm=methods(image,wrapper);face,=pair['composition']['interfaces'];fm=md.methods[face['formatterDeserializeMethodIndex']]
    _vtable(image,fm.declaring_type,5,fm.index,'currentParamAtom.callback')
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(original,17,False),[],'currentParamAtom.getter')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['0F104210','488BC1','0F1101','C3'])
    constructors={n:leaf(image,image.method_pointer_va(mm[n]),['0F57C0','0F114110','C3'])for n in('.ctor','CreateInstance')}
    td=md.types[face['wrapperDefinition']];section=md.sections['interfaceOffsets'];start=section.offset+td.interface_offsets_start*8
    faces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
    ordinal=faces.index((face['interfaceTypeIndex'],face['interfaceOffset']))
    source=owned(image,image.method_pointer_va(fm));dispatch=owned(image,dispatch_target)
    pool_fact=pooled_source_helper._contract();need('pool-build',pins,pool_fact['nativeInputs'])
    pool_proof=pooled_source_helper.validate_on_image(image,base+pool_fact['targetRva'],pins)
    ps=pooled_inline_sources._symbols(image,pool_fact)
    source_symbols=dict(ps,allocate=_body_target(source,'test rax, rax',before=True),
        barrier=_body_target(source,'movups [rax+0x10], xmm0'))
    offsets=scalar.reader_offsets(image,'currentParamAtom')
    programs=[atom_program(source['regions'],source['pointer'],offsets,source_symbols,
        mode=m,null=n,new=c)for n in(False,True)for c in(False,True)for m in('null','empty','lookup')]
    allocation=next(p['allocation']for p in programs if p['allocation'])
    usage=derive_typed_usage_context(image,allocation['site']-base,label='currentParamAtom.allocate')
    need('typed-wrapper-allocation',(1,wrapper.name),(usage['tag'],usage['typeName']))
    def call(offset):
        raw=image.pe.bytes_at_va(dispatch_target+offset,5);need('exact-E8',0xe8,raw[0])
        return dispatch_target+offset+5+int.from_bytes(raw[1:],'little',signed=True)
    symbols={k:call(n)for k,n in dict(prepare=25,header=135,typeObject=225,
        creationTest=252,activate=285,resolve=361,wrapperProvider=377,wrapperInvoke=407,indexed=464).items()}
    load=image.pe.bytes_at_va(dispatch_target+47,7);need('canonical-compare-LEA','488d05',load[:3].hex())
    symbols['adapter']=dispatch_target+54+int.from_bytes(load[3:],'little',signed=True)
    atd=ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2']
    definition,=[m for m in md.methods_for(atd)if md.string(m.name_index)=='Deserialize']
    canonical=entries.resolve(definition.index,[original,'object'],[])
    need('exact-canonical-Atom16-entry',canonical['pointer'],symbols['adapter'])
    context,context_proof=_adapter_context(image,entries)
    # This dispatcher calls TryReadObjectHeader (one byte), independently of
    # the UTF-8 helper's four-byte collection header. Prove its actual source.
    header=vector_recorder(image)(symbols['header']-base)
    primitive_param.object_header_source(image,header,offsets)
    paths=[inline16_program(dispatch['regions'],dispatch['pointer'],symbols,offsets,
        ordinal=ordinal,null=n,create=c,wrapper_null=w)for n,c,w in
        ((True,True,False),(False,True,False),(False,False,False),(False,True,True))]
    invocation=owned(image,symbols['wrapperInvoke'])
    static=owned(image,image.method_pointer_va(mm['Deserialize']))
    primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    static_programs=[atom_static_program(static['regions'],static['pointer'],offsets,source_symbols,
        mode=m,null=n,new=c)for n in(False,True)for c in(False,True)for m in('null','empty','lookup')]
    allocation=next(p['typedAllocation']for p in static_programs if p['typedAllocation'])
    static_allocation=derive_typed_usage_context(image,allocation['instruction']-base,label='currentParamAtom.static-allocate')
    need('static-typed-wrapper-allocation',(1,wrapper.name),(static_allocation['tag'],static_allocation['typeName']))
    invoke=atom_wrapper_invoke_program(invocation['regions'],invocation['pointer'],
        prepare=symbols['prepare'],callback=image.method_pointer_va(fm),reader=static['pointer'])
    invoked_type=derive_typed_usage_context(image,invoke['wrapperUsage']['instruction']-base,label='currentParamAtom.fast-invoke')
    need('inline-invoke-wrapper-type',(1,wrapper.name),(invoked_type['tag'],invoked_type['typeName']))
    return json.loads(json.dumps(dict(typeName=original,profile=pair,boxedBytes=32,managedBytes=16,
        fields=[list(ctx.field(original+'::'+m.name))for m in wrapper.members],
        getter=getter,constructors=constructors,interfaceOrdinal=ordinal,
        callbackMethod=pair['composition']['methods'][1],callbackWindows=source['windows'],
        callbackPrograms=programs,typedAllocation=usage,pool=pool_proof,
        dispatchWindows=dispatch['windows'],dispatchPrograms=paths,
        symbolRvas={k:v-base for k,v in symbols.items()},canonicalAdapter=canonical,
        adapterContext=context,adapterContextProof=context_proof,
        headerSource=header,headerProof=dict(wireBytes=1,ffReturnsFalse=True,
            sameReaderAndOutput=True,actualSourceTargetRva=symbols['header']-base),
        wrapperInvoke=invoke,wrapperInvokeWindows=invocation['windows'],invokedWrapperType=invoked_type,
        staticReaderWindows=static['windows'],staticReaderPrograms=static_programs,staticTypedAllocation=static_allocation,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))


def derive(image,pins):
    import json
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    key=derive_key_value(image,pins)
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type=='Beyond.Gameplay.ParamValue']
    pair=derive_pair(image,wrapper.wrapped_type)
    value=derive_adapter(image,pins,pair,wrapper,forwarder_prover=derive_value_callback)
    atom=derive_atom(image,pins,image.pe.image_base+value['pairForwarder']['atomDispatchTargetRva'])
    return json.loads(json.dumps(dict(nativeInputs=pins,keyValue=key,value=value,atom=atom,
        admittedTypes=['Beyond.Gameplay.ParamKeyValue','Beyond.Gameplay.ParamValue','Beyond.Gameplay.ParamValueAtom'],
        stringEncoding='int32-pool-index',nullIndex=-2,emptyIndex=-1,
        arrayCounts='all-signed-nonnegative-or-minus1',parserArrayCountLimit=16384,
        wholeOwnerAdmitted=False,runtimeSelectionObserved=False)))
