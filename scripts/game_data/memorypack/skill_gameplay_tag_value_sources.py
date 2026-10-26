"""GameplayTag's generated MC1 record is distinct from its raw4 reader.

The exact List<GameplayTag> canonical value adapter uses this generated wrapper:
MC1 then tagId Int32, or canonical FF/default4. Query's ReadUnmanagedArray<Tag>
instead copies raw4 elements with no per-element header. Both have managed4
storage, which does not select a wire grammar. This owner proves only this
wrapper's named field, exact getter/zero constructor/setter, typed registration,
MC1/new/FF and complete returns. Selected adapter/context/callback and list
count/Add require separate proofs. Ready coherent contexts, normal zeroed typed
allocation/helpers, disjoint buffered storage and disabled collector effects
remain conditions; runtime tag meaning/selection and whole owner/EOF are open.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack import scalar_param_native as scalar

VALUE='Beyond.Gameplay.Core.GameplayTag'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagForMemoryPack'
LABEL='skillGameplayTagValue'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def tag_value_program(regions,entry,s,*,new=False,null=False):
    need('literal-noncontradictory-path',True,type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20');ready=flag(g)
    g.take('488bda','488bf9');g.branch('74',False,1)
    g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
    allocation=None
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('48833b00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','894810','488bcb','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
            allocation=dict(instruction=at,cell=cell,zeroedManagedBytes=4)
        g.take('807c243001');g.branch('0f85',False)
        g.take('488b1b','488bcf');g.call(s['integer']);g.take('4885db');g.branch('74',False,1);g.take('894310')
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,allocation=allocation,
        memberCount=None if null else 1,wireBytes=1 if null else 5,managedBytes=4,
        fieldOrder=[]if null else['tagId'],normalReturn=True,entryRspRestored=True,
        rawUnmanagedElementGrammarInferred=False,originalDefaultValueAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import primitive_param
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_root_value_sources import value_layout
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,selected_inputs,_fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper=_selected_wrapper(image,WRAPPER);need('exact-generated-original',VALUE,wrapper.wrapped_type)
    need('exact-generated-member',[('tagId','int')],[(m.name,m.declared_type)for m in wrapper.members])
    layout=value_layout(image,ctx,VALUE,wrapper,managed_bytes=4,fields={'tagId':('int',8,4)})
    need('wrapper-field-at16',16,layout['fields']['tagId']['wrapperOffset'])
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(VALUE,17,False),[],LABEL+'.getter')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['8B4110','C3'])
    constructors={}
    for name in('.ctor','CreateInstance'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,('void',1,False),[],LABEL+'.'+name)
        constructors[name]=leaf(image,image.method_pointer_va(mm[name]),['33C0','894110','C3'])
    scalar.owned_method_abi(image,ctx,mm['set___tagId__'].index,wrapper.type_definition,('void',1,False),[('int',8,False)],LABEL+'.setter')
    setter=leaf(image,image.method_pointer_va(mm['set___tagId__']),['895110','C3'])
    pair=derive_pair(image,VALUE,WRAPPER);forward=registered_pair(image,pair,wrapper,label=LABEL+'.registration')
    body=owned(image,image.method_pointer_va(mm['Deserialize']));entry=body['pointer'];rows={int(r['va'],16):r for r in body['rows']}
    def call(at):
        row=rows[at];raw=bytes.fromhex(row['bytes']);need('actual-owned-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    new=control_transfer(rows[entry+55])['target'];null=control_transfer(rows[entry+45])['target']
    s=dict(header=call(entry+38),integer=call(entry+78),allocate=call(new+7),barrier=call(new+32))
    need('same-null-barrier',s['barrier'],call(null+10))
    paths=[tag_value_program(body['regions'],entry,s,**p)for p in({},{'new':True},{'null':True})]
    usage=derive_typed_usage_context(image,paths[1]['allocation']['instruction']-base,label=LABEL+'.allocation')
    need('nominal-wrapper-allocation',(1,WRAPPER),(usage['tag'],usage['typeName']))
    scalar.ordinary(image,ctx.type_pointer(usage['typeIndex']),18,LABEL+'.allocation',reference=True)
    offsets=scalar.reader_offsets(image,LABEL);record=vector_recorder(image)
    header=record(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    integer=record(s['integer']-base);scalar.integer_source(image,integer,offsets,LABEL+'.integer')
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-gameplay-tag-value-source.v1',nativeInputs=pins,
        status='proved-wrapper-source-requires-value4-adapter',typeName=VALUE,wrapperName=WRAPPER,
        layout=layout,registeredPair=pair,forwarding=forward,getter=getter,constructors=constructors,setter=setter,
        programs=paths,sourceWindows=body['windows'],allocationUsage=usage,header=header,integerSource=integer,
        barrier=barrier,barrierProof=barrier_proof,symbolRvas={k:v-base for k,v in s.items()},
        positiveCollectionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Current nominal GameplayTag value4 generated wrapper, EAX getter/zero constructors/setter, MC1/tagId Int32 source plus fresh/FF and complete returns; registration/forwarding and exact primitive/header helpers.',
            conditional=__doc__,structuralOnly='Stored tag identifier representation.',unresolved=['selected canonical managed4 adapter/conversion','list count/Add','runtime meaning/selection','whole owner/physical EOF']))))
