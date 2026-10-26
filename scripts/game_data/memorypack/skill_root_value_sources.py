"""Nominal current Skill root values, keeping wire and managed ABIs separate.

DataPair's wrapper reads MC4 as Boolean, pooled key, raw Double and pooled value
string. Its declared storage is reordered and occupies managed32 with padding;
the selected getter copies two complete XMM chunks to a hidden result buffer.
Neither those chunks nor a list's element stride supply a wire width. The FF
wrapper branch clears the wrapper byref; a default original value additionally
requires the independently proved concrete value adapter/conversion path.

These routines currently return source components and explicit outstanding
adapter/list joins. No enclosing root, positive collection or live formatter
selection is admitted from a wrapper name, managed size or source hash alone.
Initialized matching typed contexts, normal compatible Win64 helpers/barriers,
disjoint sufficiently buffered storage and selected callbacks remain conditions.
"""
from __future__ import annotations

import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import scalar_param_native as scalar, primitive_param, pooled_source_helper
from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
from scripts.game_data.memorypack.reference_param_profile import derive_pair
from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,selected_inputs,_fast_barrier
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.pooled_string_list_sources import flag

LABEL='skillRootValueSources'
DATA_PAIR='Beyond.Blackboard+DataPair'
DATA_PAIR_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_DataPairForMemoryPack'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def double_program(regions,entry,offsets):
    """The actual buffered eight-byte Double helper, including full return."""
    g=BytesPath(regions,entry)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','57','4883ec30','8379'+rem+'08','488bd9','0f29742420');g.branch('0f8c',False)
    g.take('488b43'+cur,'f20f1030','8b7b'+rem,'83c7f8');g.branch('0f88',False)
    g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,
        '488b5c2440','0f28c6','0f28742420','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=8,resultRegister='xmm0.low64',
        exactBitTransfer=True,normalReturn=True,readerCounterStores=4,entryRspRestored=True)


def data_pair_program(regions,entry,offsets,slots,symbols,*,new=False,null=False):
    """Actual MC4/FF, existing/new wrapper source and complete barrier tail."""
    need('data-pair-path-booleans',True,type(new)is bool and type(null)is bool and not(new and null))
    need('data-pair-storage-fields',{'isDynamic','key','valueDouble','valueStr'},set(slots))
    g=BytesPath(regions,entry)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20')
    ready=flag(g);g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',null)
    allocation=None
    if null:
        g.take('48c70700000000','488bcf');g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('0f84',new)
        if new:
            usage=g.at;cell=g.relative('488b0d');g.call(symbols['allocate'])
            g.take('4885c0');g.branch('0f84',False)
            g.take('0f57c0','488bcf','0f114010','0f114020','488907');g.call(symbols['barrier'])
            g.take('90');g.jump('e9');allocation=dict(usage=usage,cell=cell,zeroedValueBytes=32)
        g.take('4080fe04');g.branch('0f85',False)
        g.take('488b37','488bcb');g.call(symbols['boolean']);g.take('4885f6');g.branch('74',False,1)
        g.take('8846'+bytes((slots['isDynamic'],)).hex(),'488bcb','488b37');g.call(symbols['pool'])
        g.take('4885f6');g.branch('74',False,1)
        g.take('488d4e'+bytes((slots['key'],)).hex(),'488901');g.call(symbols['barrier'])
        g.take('488b37','488bcb');g.call(symbols['double']);g.take('4885f6');g.branch('74',False,1)
        g.take('488b3f','488bcb','f20f1146'+bytes((slots['valueDouble'],)).hex());g.call(symbols['pool'])
        g.take('4885ff');g.branch('74',False,1)
        g.take('488947'+bytes((slots['valueStr'],)).hex(),'488d4f'+bytes((slots['valueStr'],)).hex())
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
    need('data-pair-normal-tail-barrier',symbols['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,wrapperNull=null,newWrapper=new,
        allocation=allocation,memberCount=None if null else 4,wireOrder=[]if null else[
            dict(field='isDynamic',kind='boolean',wireBytes=1),dict(field='key',kind='pooled-string',wireBytes=4),
            dict(field='valueDouble',kind='double-bits',wireBytes=8),dict(field='valueStr',kind='pooled-string',wireBytes=4)],
        directWireBytes=1 if null else 18,normalReturnViaBarrier=True,
        nullOutput='wrapper reference itself'if null else None,
        originalDefaultValueAdmitted=False)


def value_layout(image,ctx,name,wrapper,*,managed_bytes,fields):
    """Own the padded value's actual boxed layout and wrapper-contained storage."""
    md=image.metadata;td=ctx.index.types[name]
    need('original-is-value',True,ctx.is_value_type(name));need('original-not-enum',False,ctx.is_enum(name))
    holder=ctx.field(wrapper.name+'::__instance')
    need('value-wrapper-holder',(wrapper.name,name,16),holder)
    declared=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    need('value-instance-field-inventory',set(fields),{md.string(f.name_index)for f in declared})
    rows={};occupied=[]
    for f in declared:
        field=md.string(f.name_index);typename,kind,width=fields[field];layout=ctx.field(name+'::'+field)
        need('value-field-type:'+field,typename,layout[1]);scalar.ordinary(image,ctx.type_pointer(f.type_index),kind,
            LABEL+'.valueField.'+field,reference=kind in(14,18,21,29))
        unboxed=layout[2]-16;slot=holder[2]+unboxed
        need('value-field-within-managed-layout:'+field,True,0<=unboxed and unboxed+width<=managed_bytes)
        occupied.extend(range(unboxed,unboxed+width));rows[field]=dict(typeName=typename,kind=kind,
            originalBoxedOffset=layout[2],unboxedOffset=unboxed,wrapperOffset=slot,bytes=width)
    need('value-fields-disjoint',len(occupied),len(set(occupied)))
    sizes={}
    for definition in(td,md.types[wrapper.type_definition]):
        need('value-size-row-index',True,0<=definition.index<int(image.registration['typeDefinitionsSizesCount']))
        address=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
        need('value-size-row-present',True,address>0)
        raw=image.pe.bytes_at_va(address,16);sizes[image.type_name(definition.index)]=dict(rawHex=raw.hex().upper(),instanceBytes=int.from_bytes(raw[:4],'little'))
    need('boxed-value-size',16+managed_bytes,sizes[name]['instanceBytes'])
    need('wrapper-contains-full-value',True,sizes[wrapper.name]['instanceBytes']>=holder[2]+managed_bytes)
    return dict(typeName=name,managedBytes=managed_bytes,holder=holder,fields=rows,sizeRows=sizes)


def derive_data_pair(image,pins):
    """Fresh child source only; the positive value-list adapter join stays open."""
    selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper=_selected_wrapper(image,DATA_PAIR_WRAPPER)
    need('selected-data-pair-type',DATA_PAIR,wrapper.wrapped_type)
    need('data-pair-serialized-members',[
        ('isDynamic','bool'),('key','string'),('valueDouble','double'),('valueStr','string')],
        [(m.name,m.declared_type)for m in wrapper.members])
    layout=value_layout(image,ctx,DATA_PAIR,wrapper,managed_bytes=32,fields={
        'isDynamic':('bool',2,1),'key':('string',14,8),
        'valueDouble':('double',13,8),'valueStr':('string',14,8)})
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    pair=derive_pair(image,DATA_PAIR,wrapper.name);registration=registered_pair(image,pair,wrapper,label=LABEL+'.DataPair')
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(DATA_PAIR,17,False),[],LABEL+'.dataPairGetter')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['0F104210','488BC1','0F104A20','0F1101','0F114910','C3'])
    source=owned(image,image.method_pointer_va(mm['Deserialize']));by={int(r['va'],16):r for r in source['rows']}
    entry=source['pointer']
    def call(offset):
        row=by[entry+offset];flow=control_transfer(row)
        need('data-pair-direct-source',(5,'call'),(len(bytes.fromhex(row['bytes'])),flow['kind']))
        return flow['target']
    allocation_branch=control_transfer(by[entry+95])['target']
    allocation=by[allocation_branch];need('data-pair-allocator-usage-load',b'\x48\x8b\x0d',bytes.fromhex(allocation['bytes'])[:3])
    allocation_call=by[allocation_branch+7]
    symbols=dict(boolean=call(117),pool=call(136),double=call(164),barrier=call(153),
        allocate=control_transfer(allocation_call)['target'])
    need('data-pair-same-pooled-helper',symbols['pool'],call(185))
    slots={name:field['wrapperOffset']for name,field in layout['fields'].items()};offsets=scalar.reader_offsets(image,LABEL)
    programs=[data_pair_program(source['regions'],entry,offsets,slots,symbols,**option)
        for option in({},{'new':True},{'null':True})]
    usage=derive_typed_usage_context(image,programs[1]['allocation']['usage']-base,label=LABEL+'.DataPairAllocation')
    need('exact-data-pair-wrapper-allocation',(1,wrapper.name),(usage['tag'],usage['typeName']))
    scalar.ordinary(image,ctx.type_pointer(usage['typeIndex']),18,LABEL+'.DataPairAllocation',reference=True)
    record=vector_recorder(image);boolean=record(symbols['boolean']-base)
    scalar.boolean_source(image,boolean,offsets,LABEL+'.DataPairBoolean')
    pool=pooled_source_helper.validate_on_image(image,symbols['pool'],pins)
    double=owned(image,symbols['double']);double_proof=double_program(double['regions'],double['pointer'],offsets)
    barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier'])
    return json.loads(json.dumps(dict(schema='endfield.skill-root-data-pair-source.v1',nativeInputs=pins,
        status='proved-wrapper-source-requires-value-adapter-join',typeName=DATA_PAIR,wrapperName=wrapper.name,
        layout=layout,registeredPair=pair,forwarding=registration,getter=getter,sourceWindows=source['windows'],
        programs=programs,allocationUsage=usage,booleanSource=boolean,pooledSource=pool,
        doubleWindows=double['windows'],doubleProgram=double_proof,barrier=barrier,barrierProof=barrier_proof,
        requiredJoins=['actual closed DataPair value32 canonical adapter/dispatcher/conversion',
            'positive value-list callback and managed32 index/store induction'],
        positiveCollectionAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Own DataPair managed32 field storage, hidden getter copy32, registered wrapper forwarding, MC4 Boolean/pool/Double/pool source including new/FF wrapper paths and complete selected tails.',
            conditional='Matching initialized selected callbacks/contexts, normal compatible noninterfering helper/barrier effects and stable buffered storage.',
            unresolved=['actual value32 adapter/conversion and positive-list composition','runtime selection','whole root/EOF']))))
