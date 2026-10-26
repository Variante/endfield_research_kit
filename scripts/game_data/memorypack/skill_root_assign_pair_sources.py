"""Exact AssignPair managed40 wrapper source, independent of every collection.

The selected MC6 path reads enum32, pooled input key, raw Single, pooled string,
pooled target key and Boolean. Reordered original storage occupies managed40;
its hidden getter copies16+16+8. That storage is never a wire-width inference.
FF clears the wrapper reference; default original output requires the separate
selected canonical value adapter and conversion proof. Matching initialized
typed contexts, stable buffered disjoint storage and normal noninterfering
allocation/barrier helpers remain conditions. Runtime formatter selection,
unselected refill/error paths and all enclosing callers/EOF remain unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillRootAssignPair'
VALUE='Beyond.Blackboard+AssignPair'
WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_AssignPairForMemoryPack'
ENUM='Beyond.Blackboard+DataPair+ValueType'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def branch(g,near,short,taken):
    if g.bytes.get(g.at)==bytes.fromhex(short)[0]:return g.branch(short,taken,1)
    return g.branch(near,taken)


def assign_pair_program(regions,entry,offsets,slots,s,*,new=False,null=False):
    if type(new)is not bool or type(null)is not bool or new and null:raise ValueError('assignPair.path')
    g=BytesPath(regions,entry)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
    g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',null)
    allocation=None;context=None
    if null:
        g.take('488bcf','48c70700000000');g.call(s['barrier']);g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
            g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','0f57c0','0f114010','0f114020','48894830','488bcf','488907')
            g.call(s['barrier']);g.take('90');g.jump('e9');allocation=dict(instruction=at,cell=cell,zeroedManagedBytes=40)
        g.take('4080fe06');g.branch('0f85',False)
        at=g.at;cell=g.relative('488b15');context=dict(instruction=at,cell=cell)
        g.take('488bcb','488b37');g.call(s['integer']);g.take('4885f6');branch(g,'0f84','74',False)
        g.take('8946'+bytes((slots['directValueType'],)).hex(),'488bcb','488b37');g.call(s['pool'])
        g.take('4885f6');branch(g,'0f84','74',False)
        slot=bytes((slots['inputValueKey'],)).hex();g.take('488d4e'+slot,'488946'+slot);g.call(s['barrier'])
        g.take('488b37','488bcb');g.call(s['single']);g.take('4885f6');branch(g,'0f84','74',False)
        g.take('f30f1146'+bytes((slots['numericValue'],)).hex(),'488bcb','488b37');g.call(s['pool'])
        g.take('4885f6');branch(g,'0f84','74',False)
        slot=bytes((slots['stringValue'],)).hex();g.take('488d4e'+slot,'488946'+slot);g.call(s['barrier'])
        g.take('488b37','488bcb');g.call(s['pool']);g.take('4885f6');branch(g,'0f84','74',False)
        g.take('488d4e'+bytes((slots['targetKey'],)).hex(),'488901');g.call(s['barrier'])
        g.take('488b3f','488bcb');g.call(s['boolean']);g.take('4885ff');branch(g,'0f84','74',False)
        g.take('8847'+bytes((slots['useDirectValue'],)).hex())
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,
        allocation=allocation,enumContext=context,managedBytes=40,wireBytes=1 if null else 22,
        fieldWireBytes=[]if null else[4,4,4,4,4,1],normalReturn=True,
        originalDefaultValueAdmitted=False)


def derive(image,pins):
    """Fresh exact nominal field/source/getter proof; no parent admission."""
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import primitive_param,pooled_source_helper
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_selected_wrapper,_fast_barrier
    from scripts.game_data.memorypack.skill_root_value_sources import value_layout
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.levelscript_family_regenerate import Build
    selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper=_selected_wrapper(image,WRAPPER);need('exact-selected-value',VALUE,wrapper.wrapped_type)
    need('exact-ordered-members',[
        ('directValueType',ENUM),('inputValueKey','string'),('numericValue','float'),
        ('stringValue','string'),('targetKey','string'),('useDirectValue','bool')],
        [(m.name,m.declared_type)for m in wrapper.members])
    layout=value_layout(image,ctx,VALUE,wrapper,managed_bytes=40,fields={
        'targetKey':('string',14,8),'inputValueKey':('string',14,8),
        'useDirectValue':('bool',2,1),'directValueType':(ENUM,17,4),
        'numericValue':('float',12,4),'stringValue':('string',14,8)})
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    pair=derive_pair(image,VALUE,wrapper.name);forward=registered_pair(image,pair,wrapper,label=LABEL+'.registration')
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(VALUE,17,False),[],LABEL+'.getter')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),[
        '0F104210','488BC1','0F104A20','0F1101','F20F104230','0F114910','F20F114120','C3'])
    body=owned(image,image.method_pointer_va(mm['Deserialize']));entry=body['pointer']
    rows={int(r['va'],16):r for r in body['rows']}
    def call(at):
        row=rows[at];raw=bytes.fromhex(row['bytes'])
        need('exact-direct-call',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    new=control_transfer(rows[entry+95])['target']
    symbols={name:call(entry+offset)for name,offset in dict(integer=124,pool=147,barrier=169,single=180,boolean=258).items()}
    symbols['allocate']=call(new+7)
    need('same-second-pool',symbols['pool'],call(entry+201));need('same-third-pool',symbols['pool'],call(entry+230))
    offsets=scalar.reader_offsets(image,LABEL);slots={name:f['wrapperOffset']for name,f in layout['fields'].items()}
    programs=[assign_pair_program(body['regions'],entry,offsets,slots,symbols,**path)
        for path in({},{'new':True},{'null':True})]
    allocation=derive_typed_usage_context(image,programs[1]['allocation']['instruction']-base,label=LABEL+'.allocation')
    need('exact-wrapper-allocation',(1,WRAPPER),(allocation['tag'],allocation['typeName']))
    scalar.ordinary(image,ctx.type_pointer(allocation['typeIndex']),18,LABEL+'.allocation',reference=True)
    usage=derive_typed_usage_context(image,programs[0]['enumContext']['instruction']-base,label=LABEL+'.enum')
    bind_typed_read(image,usage,method_name='ReadUnmanaged',argument=ENUM,kind=17)
    backing=Build(image,pins).derive_enum(dict(typeName=ENUM,backingType='System.Int32',width=4))
    record=vector_recorder(image);integer=record(symbols['integer']-base)
    scalar.integer_source(image,integer,offsets,LABEL+'.integer')
    single=record(symbols['single']-base);primitive_param.single_source(image,single,offsets)
    boolean=record(symbols['boolean']-base);scalar.boolean_source(image,boolean,offsets,LABEL+'.boolean')
    pool=pooled_source_helper.validate_on_image(image,symbols['pool'],pins)
    barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier'])
    return json.loads(json.dumps(dict(schema='endfield.skill-root-assign-pair-source.v1',nativeInputs=pins,
        status='proved-wrapper-source-requires-value40-adapter',typeName=VALUE,wrapperName=WRAPPER,
        layout=layout,registeredPair=pair,forwarding=forward,getter=getter,programs=programs,
        sourceWindows=body['windows'],allocationUsage=allocation,enumUsage=usage,enumBacking=backing,
        integerSource=integer,singleSource=single,booleanSource=boolean,pooledSource=pool,
        barrier=barrier,barrierProof=barrier_proof,symbolRvas={k:v-base for k,v in symbols.items()},
        positiveCollectionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Exact nominal AssignPair managed40 layout, hidden getter copy40, typed eager registration/forwarding, MC6 enum/pool/Single/pool/pool/Boolean and fresh/FF wrapper complete source returns.',
            conditional=__doc__,structuralOnly='Serialized blackboard assignment configuration.',
            unresolved=['selected value40 adapter/conversion and actual parent callback','positive collection count/loop/Add','runtime selection','whole owner/physical EOF']))))
