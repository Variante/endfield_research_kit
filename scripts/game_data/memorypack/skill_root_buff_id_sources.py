"""Exact BuffId managed8 wrapper source, independent of every list/adapter.

The current MC1 body reads a four-byte exported-pool index into the named
buffId string field; FF clears the wrapper byref. Fresh wrapper allocation
zeroes the complete eight-byte managed value. The named getter returns that
unchanged QWORD in RAX and the own constructor zeroes it. Those managed ABI
facts do not imply a serialized width: the positive wire record is header1
plus pool-index4. A default Original and any positive list additionally need
their own selected canonical callback/conversion/count/Add proofs. Matching
initialized contexts, disjoint buffered storage, compatible zeroed allocation
and normal noninterfering helpers remain conditions. Runtime selection and
whole-owner/physical EOF are unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.memorypack.pooled_string_list_sources import flag

LABEL='skillRootBuffId'
VALUE='Beyond.Gameplay.Core.BuffId'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffIdForMemoryPack'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def buff_id_program(regions,entry,offsets,s,*,new=False,null=False):
    need('literal-noncontradictory-paths',True,type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
    g.take('488bf2','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb638','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080ffff');g.branch('74',null,1)
    allocation=None
    if null:g.take('48c70600000000','488bce');g.jump('eb',1)
    else:
        g.take('48833e00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','48894810','488bce','488906');g.call(s['barrier']);g.take('90');g.jump('e9')
            allocation=dict(instruction=at,cell=cell,zeroedManagedBytes=8)
        g.take('4080ff01');g.branch('0f85',False)
        g.take('488b3e','488bcb');g.call(s['pool']);g.take('4885ff');g.branch('74',False,1)
        g.take('488d4f10','488901')
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
    need('same-complete-tail-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,allocation=allocation,
        managedBytes=8,wireBytes=1 if null else 5,fieldOrder=[]if null else['buffId'],
        poolIndexBytes=0 if null else 4,memberCount=None if null else 1,
        normalReturnViaBarrier=True,entryRspRestored=True,originalDefaultValueAdmitted=False)


def derive(image,pins):
    """Reprove the exact current nominal source and every selected full return."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import primitive_param,pooled_source_helper
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_root_value_sources import value_layout
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_selected_wrapper,_fast_barrier
    _publication_gate(image,pins);selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper=_selected_wrapper(image,WRAPPER);need('exact-selected-type',VALUE,wrapper.wrapped_type)
    need('exact-serialized-member',[('buffId','string')],[(m.name,m.declared_type)for m in wrapper.members])
    layout=value_layout(image,ctx,VALUE,wrapper,managed_bytes=8,fields={'buffId':('string',14,8)})
    need('own-field-at-zero',(0,16),(layout['fields']['buffId']['unboxedOffset'],layout['fields']['buffId']['wrapperOffset']))
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(VALUE,17,False),[],LABEL+'.getter')
    scalar.owned_method_abi(image,ctx,mm['.ctor'].index,wrapper.type_definition,('void',1,False),[],LABEL+'.constructor')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    constructor=leaf(image,image.method_pointer_va(mm['.ctor']),['33C0','48894110','C3'])
    pair=derive_pair(image,VALUE,WRAPPER);forward=registered_pair(image,pair,wrapper,label=LABEL+'.registration')
    body=owned(image,image.method_pointer_va(mm['Deserialize']));entry=body['pointer']
    rows={int(r['va'],16):r for r in body['rows']}
    def call(at):
        row=rows[at];raw=bytes.fromhex(row['bytes']);need('owned-direct-E8',(5,232),(len(raw),raw[0]))
        return control_transfer(row)['target']
    allocation=control_transfer(rows[entry+91])['target']
    s=dict(pool=call(entry+113),barrier=control_transfer(rows[entry+150])['target'],allocate=call(allocation+7))
    offsets=scalar.reader_offsets(image,LABEL)
    programs=[buff_id_program(body['regions'],entry,offsets,s,**path)for path in({},{'new':True},{'null':True})]
    usage=derive_typed_usage_context(image,programs[1]['allocation']['instruction']-base,label=LABEL+'.allocation')
    need('typed-wrapper-allocation',(1,WRAPPER),(usage['tag'],usage['typeName']))
    scalar.ordinary(image,ctx.type_pointer(usage['typeIndex']),18,LABEL+'.allocation',reference=True)
    pool=pooled_source_helper.validate_on_image(image,s['pool'],pins)
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-buff-id-source.v1',nativeInputs=pins,
        status='proved-wrapper-source-requires-value8-adapter',typeName=VALUE,wrapperName=WRAPPER,
        layout=layout,registeredPair=pair,forwarding=forward,getter=getter,constructor=constructor,
        programs=programs,sourceWindows=body['windows'],allocationUsage=usage,pooledSource=pool,
        barrier=barrier,barrierProof=barrier_proof,symbolRvas={k:v-base for k,v in s.items()},
        positiveCollectionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Current nominal BuffId value8 layout, RAX getter/zero constructor, registered wrapper forwarding, MC1 pool-index4 and complete fresh/FF wrapper paths.',
            conditional=__doc__,structuralOnly='Stored buff identifier.',
            unresolved=['default Original and selected value8 adapter/conversion','positive list count/loop/Add','runtime selection','whole owner/physical EOF']))))
