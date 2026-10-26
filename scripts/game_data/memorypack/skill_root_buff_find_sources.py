"""BuffFindSettings' exact MC3 caller, with independent string/Query holds.

The selected source consumes named buffIdList, raw Int32 CheckType and a typed
hidden16 Query through the same Reader. Each original field store and contained
reference barrier is exact, including fresh wrapper/original allocation and FF.
Its List<string> and Query callback/array grammar stay separate; the selected
Query provider must return nonnull and the fixed callback must independently
own its wire effects. Own holder16 getter, typed factories and complete normal
returns convey stored configuration only. Ready coherent contexts, normal
compatible helpers/constructors and stable disjoint buffered storage remain
conditions; other provider paths, runtime behavior and parent/root/EOF are open.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack import scalar_param_native as scalar

TYPE='Beyond.Gameplay.Core.BuffFindSettings'
QUERY='Beyond.Gameplay.Core.GameplayTagQuery'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffFindSettingsForMemoryPack'
LIST='System.Collections.Generic.List`1<string>'
ENUM=TYPE+'+CheckType'
LABEL='skillRootBuffFind'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def buff_find_program(regions,entry,o,s,*,new=False,null=False):
    need('literal-noncontradictory-path',True,type(new)is bool and type(null)is bool and not(new and null))
    cur,rem,adv,used=(bytes((o[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);g.take('48895c2410','48896c2418','4889742420','57','4883ec30');ready=flag(g)
    g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',null)
    allocation=list_context=query_context=provider_cell=None
    if null:g.take('488bcf','48c70700000000');g.call(s['barrier']);g.jump('eb',1)
    else:
        g.take('4c89742440','48833f00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
            g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bcf','48892f');g.call(s['barrier']);g.take('90');g.jump('e9')
            allocation=dict(instruction=at,cell=cell)
        g.take('4080fe03');g.branch('0f85',False)
        at=g.at;cell=g.relative('488b15');list_context=dict(instruction=at,cell=cell)
        g.take('488bcb','488b37');g.call(s['list']);g.take('4885f6');g.branch('0f84',False)
        g.take('488b4e10','4885c9');g.branch('0f84',False)
        g.take('48894118','4883c118');g.call(s['barrier'])
        g.take('837b'+rem+'04','488b37');g.branch('0f8c',False)
        g.take('488b43'+cur,'448b30','8b6b'+rem,'83c5fc');g.branch('0f88',False)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','896b'+rem,
            '4885f6');g.branch('0f84',False)
        g.take('488b4610','4885c0');g.branch('0f84',False);g.take('44897010')
        at=g.at;cell=g.relative('488b35');query_context=dict(instruction=at,cell=cell)
        g.take('488b3f','48837e3800');g.branch('0f84',False)
        provider_cell=g.relative('488b0d');g.take('0f57c0','0f11442420','83b9e000000000');g.branch('0f84',False)
        g.take('488b4e38','488b09');g.call(s['provider']);g.take('4885c0');g.branch('74',False,1)
        g.take('4c8d4c2420','4c8bc3','488bd0');g.call(s['dispatch'])
        g.take('4885ff');g.branch('74',False,1);g.take('488b4f10','4885c9');g.branch('74',False,1)
        g.take('0f10442420','0f114120','4883c128');g.call(s['barrier']);g.take('4c8b742440')
    g.take('488b5c2448','488b6c2450','488b742458','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,
        memberCount=None if null else 3,allocation=allocation,listContext=list_context,queryContext=query_context,
        providerClassCell=provider_cell,fieldOrder=[]if null else['buffIdList','checkType','tagQuery'],
        enumWireBytes=0 if null else 4,queryManagedBytes=16,queryWireBytes=None,
        queryCallbackSelectorUnusedRequired=True,queryProviderNonNullRequired=True,
        queryReferenceLaneOffset=8,normalReturn=True,entryRspRestored=True)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import primitive_param,buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_root_record_sources import simple_class_constructor_program
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,_fast_barrier
    from scripts.game_data.levelscript_family_regenerate import Build
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    wrapper=_selected_wrapper(image,WRAPPER);need('exact-original',TYPE,wrapper.wrapped_type)
    need('actual-reference-holder',(WRAPPER,TYPE,16),ctx.field(WRAPPER+'::__instance'));need('original-reference',False,ctx.is_value_type(TYPE))
    declarations=[('buffIdList',LIST,21,24),('checkType',ENUM,17,16),('tagQuery',QUERY,17,32)]
    need('exact-generated-members',[(n,t)for n,t,_,_ in declarations],[(m.name,m.declared_type)for m in wrapper.members])
    fields=[]
    for name,typ,kind,offset in declarations:
        need('own-nominal-original-field:'+name,(TYPE,typ,offset),ctx.field(TYPE+'::'+name))
        f,=[f for f in md.fields_for(ctx.index.types[TYPE])if md.string(f.name_index)==name]
        scalar.ordinary(image,ctx.type_pointer(f.type_index),kind,LABEL+'.field.'+name,reference=kind==21)
        fields.append(dict(fieldName=name,typeName=typ,fieldOffset=offset,kind={21:'list'}.get(kind,'enum'if typ==ENUM else'hidden16')))
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(TYPE,18,False),[],LABEL+'.getter')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    pair=derive_pair(image,TYPE,WRAPPER);forward=registered_pair(image,pair,wrapper,label=LABEL+'.registration')
    body=owned(image,image.method_pointer_va(mm['Deserialize']));entry=body['pointer'];rows={int(r['va'],16):r for r in body['rows']}
    def call(at):
        row=rows[at];raw=bytes.fromhex(row['bytes']);need('actual-owned-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    new=control_transfer(rows[entry+100])['target']
    s=dict(list=call(entry+129),barrier=call(entry+164),provider=call(entry+299),dispatch=call(entry+320),
        allocate=call(new+7),constructor=call(new+29))
    offsets=scalar.reader_offsets(image,LABEL);paths=[buff_find_program(body['regions'],entry,offsets,s,**p)for p in({},{'new':True},{'null':True})]
    ctor=owned(image,image.method_pointer_va(mm['.ctor']));need('own-wrapper-constructor',ctor['pointer'],s['constructor'])
    constructor=simple_class_constructor_program(ctor['regions'],ctor['pointer'],fields,holder='rdi')
    need('one-normal-typed-allocator',s['allocate'],constructor['allocate']);need('same-factory-barrier',s['barrier'],constructor['barrier'])
    usages={}
    for role,at,typ in(('wrapperAllocation',paths[1]['allocation']['instruction'],WRAPPER),('originalAllocation',constructor['usageSite'],TYPE)):
        u=derive_typed_usage_context(image,at-base,label=LABEL+'.'+role);need('typed-allocation:'+role,(1,typ),(u['tag'],u['typeName']))
        scalar.ordinary(image,ctx.type_pointer(u['typeIndex']),18,LABEL+'.'+role,reference=True);usages[role]=u
    om,=[m for m in md.methods_for(ctx.index.types[TYPE])if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    need('named-original-constructor',image.method_pointer_va(om),constructor['originalConstructor'])
    scalar.owned_method_abi(image,ctx,om.index,om.declaring_type,('void',1,False),[],LABEL+'.originalCtor')
    contexts={}
    for name,role,method,arg,kind in(('buffIdList','listContext','ReadPackable',LIST,21),('tagQuery','queryContext','ReadValue',QUERY,17)):
        u=derive_typed_usage_context(image,paths[0][role]['instruction']-base,label=LABEL+'.'+name)
        bind_typed_read(image,u,method_name=method,argument=arg,kind=kind,reference=kind==21);contexts[name]=u
    clones=ec.clone_facts(image,pins);need('actual-string-list-reference-source',clones['ReadPackable']['targetRva'],s['list']-base)
    backing=Build(image,pins).derive_enum(dict(typeName=ENUM,backingType='System.Int32',width=4))
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-buff-find-source.v1',nativeInputs=pins,
        status='proved-record-caller-requires-child-joins',typeName=TYPE,wrapperName=WRAPPER,memberCount=3,fields=fields,
        sourceWindows=body['windows'],programs=paths,registeredPair=pair,forwarding=forward,getter=getter,
        constructorWindows=ctor['windows'],constructor=constructor,typedAllocations=usages,contexts=contexts,enumBacking=backing,
        barrier=barrier,barrierProof=barrier_proof,symbolRvas={k:v-base for k,v in s.items()},wholeRecordAdmitted=False,
        evidenceBoundary=dict(exact='Own named MC3/FF/new BuffFindSettings source, direct List reference/enum32/hidden Query16 stores and lane8 barrier, typed ctor/getter/registration and complete returns.',
            conditional=__doc__,structuralOnly='Stored buff-find configuration.',unresolved=['List<string> child grammar','Query16 caller/callback/array grammar','runtime selection','enclosing root/EOF']))))
