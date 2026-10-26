"""Current GameplayTagQuery value16 wrapper source; its array/adapter stays separate.

MC2 reads the declared QueryType as exact Int32 bits and an independently typed
ReadUnmanagedArray<GameplayTag>. FF clears only the wrapper reference; fresh
allocation zeroes all16 managed bytes. The hidden16 getter copies the complete
value unchanged. Padding/managed width never supplies a serialized width.
Matching initialized contexts, disjoint buffered storage, typed zeroed normal
allocations and compatible helper/barrier effects are conditions. Array count,
bulk element/copy sources and default value16 adapter remain independent, as
do runtime selection and enclosing SkillData/physical EOF.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillRootTagQuery'
VALUE='Beyond.Gameplay.Core.GameplayTagQuery'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagQueryForMemoryPack'
ELEMENT='Beyond.Gameplay.Core.GameplayTag'
ENUM=VALUE+'+QueryType'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def tag_query_program(regions,entry,offsets,s,*,new=False,null=False):
    need('literal-noncontradictory-paths',True,type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2410','48896c2418','4889742420','57','4883ec20');ready=flag(g)
    g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',null)
    allocation=None;array_context=None
    if null:g.take('488bcf','48c70700000000');g.call(s['barrier']);g.jump('eb',1)
    else:
        g.take('4c89742430','48833f00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
            g.take('0f57c0','488bcf','0f114010','488907');g.call(s['barrier']);g.take('90');g.jump('e9')
            allocation=dict(instruction=at,cell=cell,zeroedManagedBytes=16)
        g.take('4080fe02');g.branch('0f85',False)
        g.take('837b'+rem+'04','488b37');g.branch('0f8c',False)
        g.take('488b43'+cur,'448b30','8b6b'+rem,'83c5fc');g.branch('0f88',False)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','896b'+rem,'4885f6');g.branch('74',False,1)
        g.take('44897610','488bcb');at=g.at;cell=g.relative('488b15');array_context=dict(instruction=at,cell=cell)
        g.take('488b3f');g.call(s['array']);g.take('4885ff');g.branch('74',False,1)
        g.take('488d4f18','48894718');g.call(s['barrier']);g.take('4c8b742430')
    g.take('488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,allocation=allocation,
        arrayContext=array_context,managedBytes=16,wireBytes=None,enumWireBytes=0 if null else 4,
        fieldOrder=[]if null else['queryType','tags'],normalReturn=True,entryRspRestored=True,originalDefaultValueAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import primitive_param
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_root_value_sources import value_layout
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_selected_wrapper,_fast_barrier
    from scripts.game_data.levelscript_family_regenerate import Build
    _publication_gate(image,pins);selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper=_selected_wrapper(image,WRAPPER);need('exact-original',VALUE,wrapper.wrapped_type)
    need('exact-member-order',[('queryType',ENUM),('tags',ELEMENT+'[]')],[(m.name,m.declared_type)for m in wrapper.members])
    layout=value_layout(image,ctx,VALUE,wrapper,managed_bytes=16,fields={
        'queryType':(ENUM,17,4),'tags':(ELEMENT+'[]',29,8)})
    need('exact-managed-store-slots',[16,24],[layout['fields'][k]['wrapperOffset']for k in('queryType','tags')])
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(VALUE,17,False),[],LABEL+'.getter')
    scalar.owned_method_abi(image,ctx,mm['.ctor'].index,wrapper.type_definition,('void',1,False),[],LABEL+'.constructor')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['0F104210','488BC1','0F1101','C3'])
    constructor=leaf(image,image.method_pointer_va(mm['.ctor']),['0F57C0','0F114110','C3'])
    pair=derive_pair(image,VALUE,WRAPPER);forward=registered_pair(image,pair,wrapper,label=LABEL+'.registration')
    body=owned(image,image.method_pointer_va(mm['Deserialize']));entry=body['pointer'];rows={int(r['va'],16):r for r in body['rows']}
    def call(at):
        row=rows[at];raw=bytes.fromhex(row['bytes']);need('actual-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    new=control_transfer(rows[entry+100])['target']
    s=dict(array=call(entry+186),barrier=call(entry+204),allocate=call(new+7))
    offsets=scalar.reader_offsets(image,LABEL)
    paths=[tag_query_program(body['regions'],entry,offsets,s,**options)for options in({},{'new':True},{'null':True})]
    allocation=derive_typed_usage_context(image,paths[1]['allocation']['instruction']-base,label=LABEL+'.allocation')
    need('typed-wrapper-allocation',(1,WRAPPER),(allocation['tag'],allocation['typeName']))
    scalar.ordinary(image,ctx.type_pointer(allocation['typeIndex']),18,LABEL+'.allocation',reference=True)
    usage=derive_typed_usage_context(image,paths[0]['arrayContext']['instruction']-base,label=LABEL+'.array')
    bind_typed_read(image,usage,method_name='ReadUnmanagedArray',argument=ELEMENT,kind=17)
    field,=[f for f in image.metadata.fields_for(ctx.index.types[VALUE])if image.metadata.string(f.name_index)=='tags']
    raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
    need('nominal-tags-SZARRAY',b'\x1d\x00',raw[10:12]);element=int.from_bytes(raw[:8],'little')
    actual,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    need('same-declared-array-element',element,actual.type_pointer_va)
    backing=Build(image,pins).derive_enum(dict(typeName=ENUM,backingType='System.Int32',width=4))
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-tag-query-source.v1',nativeInputs=pins,
        status='proved-wrapper-source-requires-array-and-value16-adapter',typeName=VALUE,wrapperName=WRAPPER,
        layout=layout,registeredPair=pair,forwarding=forward,getter=getter,constructor=constructor,programs=paths,
        sourceWindows=body['windows'],allocationUsage=allocation,arrayUsage=usage,enumBacking=backing,
        barrier=barrier,barrierProof=barrier_proof,symbolRvas={k:v-base for k,v in s.items()},
        childGrammarAdmitted=False,positiveCollectionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Current nominal GameplayTagQuery managed16 layout, complete hidden16 getter, zero ctor, registered forwarding, MC2/FF/fresh source and actual declared QueryType/raw4 plus nominal ReadUnmanagedArray<GameplayTag> request.',
            conditional=__doc__,structuralOnly='Stored tag query configuration.',
            unresolved=['actual closed unmanaged array/bulk source','default value16 adapter/conversion and actual caller','runtime selection','whole owner/physical EOF']))))
