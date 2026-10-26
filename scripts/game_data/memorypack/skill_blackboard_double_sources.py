"""Concrete current BlackboardDouble lifecycle and complete buffered MC3/FF.

The existing reviewed warm reader owns pooled key4, normalized bool1 and
unchanged Single4. This separate owner adds complete selected existing/new/FF
caller programs, original holder16 versus typed cache24, exact generated
factory/cache/GetValue source and ordinary reference adapter/callback linkage.
The selected Original derives from BlackboardParamBase<float,double>; its
managed inheritance never changes the four serialized Single bytes to Double8.
Normal typed zeroed allocation, coherent initialized contexts and cache/base
references, compatible class casts, disabled collector, stable disjoint buffered
source/frame/objects and ordinary helper ABI remain conditions. Runtime
blackboard evaluation, formatter/default/cache/inflation choice, cold/refill
failures and enclosing owners/physical EOF remain unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillBlackboardDoubleSources'
TYPE='Beyond.Blackboard+BlackboardDouble'
WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardDoubleForMemoryPack'
BASE_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardParamBase_float_double_ForMemoryPack'
BASE='Beyond.Blackboard+BlackboardParamBase`2<float,double>'
CAPABILITY='skill-blackboard-double'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def closed_scalar_argument(raw,kind):
    """Selected closed primitive argument is an undecorated value record."""
    need('closed-base-ordinary-value-argument',True,
        type(kind)is int and kind in(12,13)and len(raw)==16 and raw[10:12]==bytes((kind,128)))


def constructor_program(regions,entry,s,*,value_offset=20):
    """Complete fresh generated constructor; original allocation is nonnull."""
    need('Single-original-slot',20,value_offset)
    g=BytesPath(regions,entry);classes=[];collectors=[]
    g.take('48895c2420','57','4883ec20');ready=flag(g);g.take('488bf9');g.branch('75',True,1)
    def usage(opcode):
        at=g.at;cell=g.relative(opcode);classes.append(dict(instruction=at,cell=cell));return cell
    usage('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
    usage('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
    usage('488b0d');g.take('48896c2438','4889742440','83b9e000000000');g.branch('75',True,1)
    g.take('4533c9','48895f18');collectors.append(g.relative('44390d'))
    bitmap=g.relative('488d2d');g.take('44894b'+bytes((value_offset,)).hex());g.branch('74',True,1)
    collectors.append(g.relative('44390d'));g.take('48895f10');g.branch('74',True,1)
    g.take('488b5f10');concrete=usage('488b35');g.take('4885db');g.branch('75',True,1)
    g.take('488b0b','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
    g.take('48895f18');need('same-concrete-class-cell',concrete,usage('488b35'))
    g.take('488b0b','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1);g.jump('e9')
    collectors.append(flag(g,'833d'));g.branch('74',True,1)
    g.take('488b6c2438','488b742440','488b5c2448','4883c420','5f','c3')
    need('same-constructor-disabled-collector',1,len(set(collectors)))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,classUsages=classes,collectorFlag=collectors[0],
        bitmapCell=bitmap,originalHolderOffset=16,typedCacheOffset=24,originalZeroedSingleOffset=value_offset,
        bothHoldersReferenceSameTypedOriginal=True,normalReturn=True,entryRspRestored=True,wireBytes=0)


def original_constructor_program(regions,entry,*,value_offset=20):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9');at=g.at;cell=g.relative('488b0d')
    g.take('83b9e000000000');g.branch('74',False,1)
    g.take('33c0','8943'+bytes((value_offset,)).hex(),'4883c420','5b','c3')
    return dict(selectedBytes=g.seen,baseClassUsage=dict(instruction=at,cell=cell),zeroSingleOffset=value_offset,
        normalReturn=True,entryRspRestored=True,wireBytes=0)


def instance_setter_program(regions,entry):
    """No-unwind bounded entry; prove the entire disabled selected return."""
    g=BytesPath(regions,entry);one=g.relative('8b05');bitmap=g.relative('4c8d1d')
    g.take('48895118','4c8bd2','4c8bc9','85c0');g.branch('74',True,1)
    g.take('4d895110','85c0');g.branch('74',True,1);g.take('c3')
    return dict(selectedBytes=g.seen,collectorFlag=one,bitmapCell=bitmap,originalHolderOffset=16,typedCacheOffset=24,
        unchangedIncomingOriginal='RDX stored cache24, preserved R10 then stored holder16',
        disabledEaxRemainsZeroAcrossBothStores=True,
        normalReturn=True,physicalExtentProved=False,wireBytes=0)


def factory_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g)
    g.take('488bf9');g.branch('75',True,1)
    at=g.at;cell=g.relative('488b0d');allocation=dict(instruction=at,cell=cell)
    g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('75',True,1)
    g.take('33d2','488bcb');g.call(s['originalConstructor'])
    g.take('4533c0','488bd3','488bcf');g.call(s['instanceSetter'])
    g.take('488b5f10');first=g.at;tc=g.relative('488b15');g.take('488bcb');g.call(s['strictCast'])
    g.take('48894718','488bcb');second=g.at;need('factory-same-typed-class',tc,g.relative('488b15'))
    g.call(s['strictCast']);g.take('488d4f18','488b5c2430','4883c420','5f')
    need('factory-disabled-barrier-tail',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,allocationUsage=allocation,
        concreteClassUsages=[dict(instruction=first,cell=tc),dict(instruction=second,cell=tc)],
        originalHolderOffset=16,typedCacheOffset=24,normalReturnViaBarrier=True,entryRspRestored=True,wireBytes=0)


def strict_cast_program(regions,entry,predicate,*,null=False):
    need('literal-strict-cast-path',True,type(null)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488bfa','488bd9','4885c9');g.branch('74',null,1)
    if null:g.take('488b5c2430','33c0')
    else:
        g.take('488b09');g.call(predicate);g.take('84c0');g.branch('74',False,1)
        g.take('488bc3','488b5c2430')
    g.take('4883c420','5f','c3')
    return dict(selectedBytes=g.seen,originalNull=null,compatibleResult='same incoming RCX reference'if not null else'null',normalReturn=True)


def conversion_program(regions,entry,prepare,getter,s,*,ordinal,cache='coherent'):
    """Actual first optimized interface case, with its own inline cache24 read."""
    need('bounded-interface-ordinal',True,type(ordinal)is int and 0<=ordinal<=8)
    need('finite-conversion-cache-state',True,cache in('coherent','empty','stale'))
    g=BytesPath(regions,entry)
    g.take('4053','55','56','57','4155','4883ec40','498b30','498bf8','0fb7e9','488bda','488bce');g.call(prepare)
    g.take('440fb78630010000','4533ed','410fb7c5','66453be8');g.branch('73',False,1);g.take('488b96b0000000')
    for i in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
        if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7d0','488b86b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c6','4c8b00','488b5808')
    comparison=g.at;need('exact-optimized-GetValue-comparison',getter,g.relative('488d05'))
    g.take('4c89742478','4c89bc2488000000','4c3bc0');g.branch('74',True,1)
    metadata=g.relative('44382d');g.branch('0f84',False)
    g.take('4c396f18');g.branch('0f84',cache=='empty')
    if cache!='empty':g.take('488b4710','48394718');g.branch('0f85',cache=='stale')
    classes=[]
    if cache!='coherent':
        g.take('488b5f10');at=g.at;cell=g.relative('488b15');classes.append(dict(instruction=at,cell=cell))
        g.take('488bcb');g.call(s['cast']);g.take('48894718','488bcb');at=g.at
        need('same-inline-conversion-class',cell,g.relative('488b15'));classes.append(dict(instruction=at,cell=cell))
        g.call(s['cast']);g.take('488d4f18');g.call(s['barrier']);g.take('90');g.jump('e9')
    g.take('488b4718');g.jump('eb',1)
    g.take('4c8bbc2488000000','4c8b742478','4883c440','415d','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,requiredSelector=0,cacheState=cache,
        metadataReadyFlag=metadata,concreteClassUsages=classes,optimizedGetterComparison=comparison,
        originalHolderOffset=16,typedCacheOffset=24,normalReturn=True,entryRspRestored=True,
        sameFullReferenceReturned=True,indirectGetValueCallExecuted=False,nominalInlineGetterSemanticsProved=True,
        runtimeSelectionObserved=False,condition='The exact canonical adapter supplies selector0 and coherent selected nominal interface/MethodInfo; actual selected interface entry pointer equals this owned GetValue comparison. The independently owned inline cache refresh and compatible class source return the same typed original or null. No arbitrary pointer equivalence or live selection inferred.')


def wrapper_dispatch_program(regions,entry,*,prepare,callback,reader):
    """Exact third optimized wrapper case delegates to its actual static body."""
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec70','4d8be9','4d8bf8','488bfa','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','4803c9','488b07','4c8b14c8','488b5cc808','48899c24c0000000')
    excluded=[]
    for i in range(3):
        target=g.relative('488d05')
        if i<2:
            need('preceding-wrapper-case-does-not-match',False,target==callback);excluded.append(target)
        else:need('actual-selected-formatter-pointer',callback,target)
        g.take('4c3bd0');g.branch('0f85',i<2)
    ready=flag(g);g.branch('0f85',True)
    at=g.at;cell=g.relative('488b0d');usage=dict(instruction=at,cell=cell)
    g.take('83b9e000000000');g.branch('75',True,1)
    g.take('4533c0','498bd5','498bcf');call=g.at;g.call(reader);g.jump('eb',1)
    g.take('488b9c24b0000000','4883c470','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,wrapperClassUsage=usage,
        precedingDifferentCallbackTargets=excluded,selectedCallback=callback,actualStaticReader=reader,sourceCall=call,
        staticArguments=dict(rcx='same incoming Reader, R8 preserved R15',rdx='same incoming output, R9 preserved R13',r8='zero unused static context'),
        selectorRequired=5,slotStride=16,vtableBase=320,callbackOffsetForSlotFive=400,methodInfoOffsetForSlotFive=408,
        sameReaderAndOutput=True,normalReturn=True,entryRspRestored=True,physicalCallbackBodyExecuted=False,
        selectedDirectStaticCallProved=True,pointerEqualityBetweenFormatterAndStaticReaderProved=False)


def reader_program(regions,entry,offsets,slots,s,*,new=False,null=False,prepare_empty=False,original_null=False,pool_mode='lookup',formatter=False):
    need('literal-reader-paths',True,all(type(x)is bool for x in(new,null,prepare_empty,original_null,formatter)))
    need('compatible-reader-paths',True,not(new and(prepare_empty or original_null))and not(original_null and not(prepare_empty and null)))
    need('pooled-path',True,pool_mode in('lookup','null','empty'))
    need('exact-stored-slots',dict(blackboardKey=24,useBlackboardKey=16,value=20),slots)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);classes=[];collectors=[]
    g.take('48895c2418','55','56','57','4883ec30');ready=flag(g)
    formatter_class=None
    if formatter:
        g.take('498bf0','488bfa');g.branch('75',True,1)
        at=g.at;cell=g.relative('488b0d');formatter_class=dict(instruction=at,cell=cell)
        g.take('83b9e000000000');g.branch('75',True,1);flag(g);g.branch('75',True,1)
    else:g.take('488bf2','488bf9');g.branch('75',True,1)
    g.take('488b2e','4885ed');g.branch('74',new,1)
    if not new:
        flag(g);g.branch('75',True,1);g.take('48837d1800');g.branch('75',not prepare_empty,1)
        if prepare_empty:
            g.take('48837d1000');g.branch('74',original_null,1)
            if not original_null:
                g.take('488b5d10');at=g.at;cell=g.relative('488b15');classes.append(dict(instruction=at,cell=cell))
                g.take('488bcb');g.call(s['cast']);g.take('48894518','488bcb');at=g.at
                need('same-reader-preparation-class',cell,g.relative('488b15'));classes.append(dict(instruction=at,cell=cell))
                g.call(s['cast']);g.take('488d4d18');g.call(s['barrier'])
    g.take('837f'+rem+'01');g.branch('7d',True,1)
    g.take('488b47'+cur,'0fb628','8b5f'+rem,'83eb01');g.branch('79',True,1)
    g.take('48ff47'+cur,'ff47'+adv,'ff47'+used,'895f'+rem,'4080fdff');g.branch('0f84',null)
    allocation=None;pool_site=None
    if null:
        g.take('33c0'if formatter else'33db','488bce','488906'if formatter else'48891e','488b5c2460','4883c430','5f','5e','5d')
        need('null-tail-barrier',s['barrier'],g.relative('e9'))
    else:
        if formatter:g.take('4c89742450')
        g.take('48833e00');g.branch('75',not new,1)
        if new:
            at=g.at;cell=g.relative('488b0d');allocation=dict(instruction=at,cell=cell)
            g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bce','48891e');g.call(s['barrier'])
        g.take('4080fd03');g.branch('0f85',False)
        if not formatter:g.take('4c89742458')
        flag(g);g.take('4c8b36');g.branch('75',True,1)
        pool_site=g.at;need('same-current-pool-class',s['pool'],g.relative('488b05'))
        g.take('488b88b8000000','48833900');g.branch('0f84',False)
        g.take('837f'+rem+'04');g.branch('7d',True,1)
        g.take('488b47'+cur,'8b18','8b6f'+rem,'83c5fc');g.branch('79',True,1)
        g.take('488347'+cur+'04','8347'+adv+'04','8347'+used+'04','896f'+rem,'83fbfe');g.branch('74',pool_mode=='null',1)
        if pool_mode=='null':g.take('33c0'if formatter else'33db');g.jump('eb',1)
        else:
            g.take('83fbff');g.branch('74',pool_mode=='empty',1)
            if pool_mode=='empty':need('same-current-empty-string',s['empty'],g.relative('488b05'if formatter else'488b1d'));g.jump('eb',1)
            else:
                need('same-lookup-pool-class',s['pool'],g.relative('488b05'))
                g.take('488b88b8000000','488b09'if formatter else'488b29','4885c9'if formatter else'4885ed');g.branch('0f84',False)
                g.take('4533c0','8bd3')
                if not formatter:g.take('488bcd')
                g.call(s['lookup']);g.jump('eb',1)
                if not formatter:g.take('488bd8')
        g.take('4d85f6');g.branch('0f84',False);g.take('4d8b4610','4d85c0');g.branch('0f84',False)
        collectors.append(flag(g,'833d'));g.take('49894018'if formatter else'49895818');g.branch('74',True,1)
        g.take('837f'+rem+'01','488b1e');g.branch('7d',True,1)
        g.take('488b47'+cur,'440fb630','8b6f'+rem,'83ed01');g.branch('79',True,1)
        g.take('48ff47'+cur,'ff47'+adv,'ff47'+used,'896f'+rem,'0f29742420','4885db');g.branch('0f84',False)
        g.take('488b4b10','4885c9');g.branch('0f84',False)
        g.take('4584f6','0f95c0','884110','837f'+rem+'04','488b1e');g.branch('7d',True,1)
        g.take('488b47'+cur,'f30f1030','8b77'+rem,'83c6fc');g.branch('79',True,1)
        g.take('488347'+cur+'04','8347'+adv+'04','8347'+used+'04','8977'+rem,'4885db');g.branch('74',False,1)
        g.take('488b4310','4885c0');g.branch('74',False,1)
        g.take('4c8b742450'if formatter else'4c8b742458','f30f117014','0f28742420','488b5c2460','4883c430','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,
        prepareCacheEmpty=prepare_empty,prepareOriginalNull=original_null,inlineClassUsages=classes,
        wrapperAllocationUsage=allocation,memberCount=None if null else 3,poolMode=None if null else pool_mode,
        formatter=formatter,formatterClassUsage=formatter_class,
        incomingReaderArgument='rdx'if formatter else'rcx',incomingOutputArgument='r8'if formatter else'rdx',
        pooledEntry=pool_site,collectorFlag=collectors[0]if collectors else None,
        directWireBytes=1 if null else 10,boolNormalizedByNonzero=True,SingleBitsUnchanged=True,
        originalHolderOffset=16,typedCacheOffset=24,normalReturn=True,entryRspRestored=True)


def derive(image,pins):
    """Reprove the existing warm declaration and all added concrete boundaries."""
    import struct
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.memorypack import buff_blackboard_double_native as warm,pooled_source_helper
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_fast_barrier
    from scripts.game_data.memorypack.skill_root_buff_input_sources import (
        derived_cached_getter_program,prepare_program,nullable_class_cast_program,compatible_class_program)
    from scripts.game_data.memorypack.pooled_inline_sources import _symbols
    selected_inputs(pins);_publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    reviewed=warm._contract();need('warm-selected-inputs',pins,reviewed['nativeInputs'])
    actual=warm.derive(image,pins);need('fresh-bidirectional-warm-proof',reviewed,actual)
    need('exact-warm-wire',[(n,k,b)for n,k,b in(('blackboardKey','int32-pool-index',4),('useBlackboardKey','byte',1),('value','single-raw',4))],
        [(r['name'],r['encoding'],r['bytes'])for r in actual['wire']])
    need('nominal-reference-lineage',(BASE_WRAPPER,BASE,False),(ctx.parent(WRAPPER),ctx.parent(TYPE),ctx.is_value_type(TYPE)))
    for owner,field,typename,slot,kind in((BASE_WRAPPER,'___instance',BASE,16,21),(WRAPPER,'__realInstance',TYPE,24,18)):
        need('exact-holder-cache:'+field,(owner,typename,slot),ctx.field(owner+'::'+field))
        fd,=[f for f in md.fields_for(ctx.index.types[owner])if md.string(f.name_index)==field]
        scalar.ordinary(image,ctx.type_pointer(fd.type_index),kind,LABEL+'.'+field,reference=True)
    parent_pointer=ctx.type_pointer(ctx.index.types[TYPE].parent_index)
    scalar.ordinary(image,parent_pointer,21,LABEL+'.closedBase',reference=True)
    parent=ContextSymbols(image).type(parent_pointer);need('closed-base-name',BASE,parent['name'])
    need('closed-base-exact-arguments',['float','double'],[a['name']for a in parent['classArguments']])
    for argument,kind in zip(parent['classArguments'],(12,13),strict=True):
        closed_scalar_argument(bytes.fromhex(argument['rawHex']),kind)
    base_td=ctx.index.types[BASE.split('<')[0]]
    field,=[f for f in md.fields_for(base_td)if md.string(f.name_index)=='value']
    raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16);need('base-value-owned-VAR',b'\x13\x00',raw[10:12])
    parameter=type_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),[t.generic_container_index for t in md.types],source=LABEL)
    need('base-value-first-reciprocal-parameter',(base_td.index,0),(parameter['typeIndex'],parameter['ordinal']))
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    pair=derive_pair(image,TYPE,WRAPPER,owned_getter_family=True);mm=methods(image,wrapper)
    sources={name:owned(image,image.method_pointer_va(mm[name]))for name in
        ('.ctor','CreateInstance','GetValue','get___instance','OnDeserialized','Deserialize')}
    for name in sources:
        if name=='Deserialize':continue
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,
            (TYPE,18,True)if name in('GetValue','get___instance')else('void',1,False),[],LABEL+'.'+name)
    def call(body,offset):
        row,=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset]
        raw=bytes.fromhex(row['bytes']);need('exact-owned-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    def after(body,raw):
        return {control_transfer(r)['target']for i,r in enumerate(body['rows'])if i and
            bytes.fromhex(r['bytes'])[:1]==b'\xe8'and bytes.fromhex(body['rows'][i-1]['bytes']).hex()==raw}
    cast,=after(sources['GetValue'],'488bcf');barrier,=after(sources['GetValue'],'488d4b18')
    s=dict(cast=cast,barrier=barrier,allocate=call(sources['.ctor'],81),strictCast=call(sources['CreateInstance'],105),
        originalConstructor=call(sources['CreateInstance'],72),instanceSetter=call(sources['CreateInstance'],86),
        constructor=sources['.ctor']['pointer'])
    need('same-factory-allocator',s['allocate'],call(sources['CreateInstance'],48))
    om,=[m for m in md.methods_for(ctx.index.types[TYPE])if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    need('named-original-constructor',image.method_pointer_va(om),s['originalConstructor'])
    scalar.owned_method_abi(image,ctx,om.index,om.declaring_type,('void',1,False),[],LABEL+'.originalConstructor')
    need('named-instance-setter',image.method_pointer_va(mm['set___instance']),s['instanceSetter'])
    scalar.owned_method_abi(image,ctx,mm['set___instance'].index,wrapper.type_definition,('void',1,False),[(TYPE,18,True)],LABEL+'.instanceSetter')
    for role in('cast','strictCast','originalConstructor'):sources[role]=owned(image,s[role])
    predicates={control_transfer(r)['target']for r in sources['cast']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'}
    need('one-class-cast-predicate',1,len(predicates));s['assignable']=next(iter(predicates))
    sources['assignable']=owned(image,s['assignable'])
    ready,=after(sources['assignable'],'488bcf')
    predicate=compatible_class_program(sources['assignable']['regions'],s['assignable'],ready)
    casts=[nullable_class_cast_program(sources['cast']['regions'],s['cast'],s['assignable'],null=n)for n in(False,True)]
    strict=[strict_cast_program(sources['strictCast']['regions'],s['strictCast'],s['assignable'],null=n)for n in(False,True)]
    pool_fact=pooled_source_helper._contract();pool=pooled_source_helper.validate_on_image(image,base+pool_fact['targetRva'],pins)
    s.update(_symbols(image,pool_fact))
    offsets=scalar.reader_offsets(image,LABEL);slots=actual['fieldOffsets']
    programs=[reader_program(sources['Deserialize']['regions'],sources['Deserialize']['pointer'],offsets,slots,s,**path,pool_mode=mode)
        for path in({},{'new':True},{'null':True},{'new':True,'null':True},{'prepare_empty':True},
            {'prepare_empty':True,'null':True},{'prepare_empty':True,'original_null':True,'null':True})
        for mode in(('lookup',)if path.get('null')else('lookup','null','empty'))]
    getters={name:[derived_cached_getter_program(sources[name]['regions'],sources[name]['pointer'],s,cache=state,cache_offset=24)
        for state in('coherent','empty','stale')]for name in('GetValue','get___instance')}
    prepares=[prepare_program(sources['OnDeserialized']['regions'],sources['OnDeserialized']['pointer'],s,**path)
        for path in({},{'cache_empty':True},{'cache_empty':True,'original_null':True})]
    constructor=constructor_program(sources['.ctor']['regions'],sources['.ctor']['pointer'],s,value_offset=slots['value'])
    original=original_constructor_program(sources['originalConstructor']['regions'],s['originalConstructor'],value_offset=slots['value'])
    factory=factory_program(sources['CreateInstance']['regions'],sources['CreateInstance']['pointer'],s)
    setter_raw=image.pe.bytes_at_va(s['instanceSetter'],256)
    setter=instance_setter_program([(s['instanceSetter'],setter_raw)],s['instanceSetter'])
    setter_window=_window(image,s['instanceSetter'],s['instanceSetter']+256,
        'bounded no-unwind setter observation; selected disabled path through RET, full physical extent unclaimed')
    barrier_windows,barrier_proof,_=_fast_barrier(image,s['barrier'])
    for value in[constructor,setter]+[p for p in programs if p['collectorFlag']is not None]:
        need('same-actual-disabled-collector',base+barrier_proof['disabledFlagRva'],value['collectorFlag'])
    typed=[]
    def typed_class(u,name):
        usage=derive_typed_usage_context(image,u['instruction']-base,label=LABEL+'.class')
        need('exact-owned-class',(1,name),(usage['tag'],usage['typeName']));typed.append(usage)
        return usage
    for name,rows in getters.items():
        for p in rows:
            for u in p['concreteClassUsages']:typed_class(u,TYPE)
    for p in programs:
        for u in p['inlineClassUsages']:typed_class(u,TYPE)
        if p['wrapperAllocationUsage']:typed_class(p['wrapperAllocationUsage'],WRAPPER)
    for p in prepares:
        for u in p['concreteClassUsages']:typed_class(u,TYPE)
    for u,name in zip(constructor['classUsages'],(BASE_WRAPPER,TYPE,BASE,TYPE,TYPE),strict=True):typed_class(u,name)
    typed_class(original['baseClassUsage'],BASE);typed_class(factory['allocationUsage'],TYPE)
    for u in factory['concreteClassUsages']:typed_class(u,TYPE)
    def formatter_proof(selected,selected_pair,selected_wrapper):
        need('same-exact-formatter-pair',(TYPE,WRAPPER),(selected_wrapper.wrapped_type,selected_wrapper.name))
        method=selected_pair['composition']['methods'][1]
        body=owned(selected,base+method[3]);paths=[]
        for path in({},{'new':True},{'null':True},{'new':True,'null':True},{'prepare_empty':True},
                {'prepare_empty':True,'null':True},{'prepare_empty':True,'original_null':True,'null':True}):
            for mode in(('lookup',)if path.get('null')else('lookup','null','empty')):
                program=reader_program(body['regions'],body['pointer'],offsets,slots,s,formatter=True,pool_mode=mode,**path)
                typed_class(program['formatterClassUsage'],WRAPPER)
                for usage in program['inlineClassUsages']:typed_class(usage,TYPE)
                if program['wrapperAllocationUsage']:typed_class(program['wrapperAllocationUsage'],WRAPPER)
                if program['collectorFlag']is not None:need('same-formatter-disabled-collector',base+barrier_proof['disabledFlagRva'],program['collectorFlag'])
                paths.append(program)
        return dict(kind='complete-inline-concrete-formatter',method=method,sourceWindows=body['windows'],programs=paths,
            directlyCallsStaticReader=False,staticReaderPointerEquivalenceProved=False,
            exactOwnNominalGrammarProved=True,sourceReader='incoming RDX',sourceOutput='incoming R8',callbackSelectionConditional=True)
    def conversion_proof(selected,selected_pair,selected_wrapper,body,symbols,ordinal):
        getter=selected.method_pointer_va(methods(selected,selected_wrapper)['GetValue'])
        need('same-selected-concrete-conversion-getter',sources['GetValue']['pointer'],getter)
        paths=[conversion_program(body['regions'],body['pointer'],symbols['conversionPrepare'],getter,s,ordinal=ordinal,cache=state)
            for state in('coherent','empty','stale')]
        for program in paths:
            need('same-concrete-getter-ready-flag',getters['GetValue'][0]['metadataReadyFlag'],program['metadataReadyFlag'])
            for usage in program['concreteClassUsages']:typed_class(usage,TYPE)
        return dict(kind='complete-inline-BlackboardDouble-GetValue',sourceWindows=body['windows'],programs=paths,
            referenceGetterMethod=selected_pair['composition']['methods'][0],interfaceOrdinal=ordinal,
            sameFullReferenceReturned=True,indirectGetValueCallExecuted=False,nominalInlineGetterSemanticsProved=True)
    def wrapper_callback_proof(selected,selected_pair,selected_wrapper,body,symbols):
        callback=base+selected_pair['composition']['methods'][1][3]
        result=wrapper_dispatch_program(body['regions'],body['pointer'],prepare=symbols['prepare'],
            callback=callback,reader=sources['Deserialize']['pointer'])
        typed_class(result['wrapperClassUsage'],WRAPPER)
        return dict(kind='selected-optimized-wrapper-static-call',sourceWindows=body['windows'],program=result,
            exactSelectedFormatter=selected_pair['composition']['methods'][1],
            exactStaticReader=[mm['Deserialize'].index,WRAPPER,'Deserialize',sources['Deserialize']['pointer']-base],
            completeStaticGrammarIndependentlyProved=True)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=formatter_proof,
        conversion_prover=conversion_proof,wrapper_callback_prover=wrapper_callback_proof)
    need('exact-owned-concrete-getter',sources['GetValue']['pointer']-base,adapter['getterMethod'][3])
    reader=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=3,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,orderedReads=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
            ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),('value','single-bits',None))],
        referenceReaderMethodDefinition=reader['referenceReaderMethodDefinition'],referenceReaderTargetRva=reader['referenceReaderTargetRva'],
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,callbackSelectionConditional=True,
        boolNormalizedByNonzero=True,positiveWireBytes=10,nullWireBytes=1,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-blackboard-double-sources.v1',nativeInputs=pins,
        status='validated-conditional-blackboard-double',capabilities={CAPABILITY:cap},
        proof=dict(warm=actual,closedBase=parent,baseValueParameter=parameter,pair=pair,readerPrograms=programs,
            getterPrograms=getters,preparePrograms=prepares,constructor=constructor,originalConstructor=original,
            factory=factory,instanceSetter=setter,instanceSetterWindow=setter_window,typedClassUsages=typed,
            sourceWindows={k:v['windows']for k,v in sources.items()},castPrograms=casts,strictCastPrograms=strict,
            classPredicate=predicate,barrierWindows=barrier_windows,barrierProof=barrier_proof,pooledSource=pool,
            adapter=adapter,referenceReaders=reader),evidenceBoundary=dict(exact='Current complete MC3/FF/new selected reader, pool4/bool1/Single4, typed generic base, constructor/cache24/holder16/GetValue/factory/casts and canonical reference adapter/source joins.',
            conditional=__doc__,structuralOnly='Stored blackboard key/flag/Single configuration; no evaluated blackboard value.',
            unresolved=['runtime formatter/cache/default/inflation choice','cold/refill/error paths','enclosing owners/physical EOF']))))
