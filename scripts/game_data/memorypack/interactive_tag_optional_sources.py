"""Optional<GameplayTag[]> with its actual inlined raw4 bulk-array source.

Count/header and every Reader update are read from the native instructions;
the closed nominal contexts, array-data pointer, bounded copy, bool source,
field transfers, initialized entry/allocation and full frames are independent
joins. No managed stride supplies a wire width or runtime provider selection.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Optional`1<Beyond.Gameplay.Core.GameplayTag[]>'
ELEMENT='Beyond.Gameplay.Core.GameplayTag'
LIMIT=64


def need(check,condition):
    if not condition:raise ValueError('interactiveTagOptional.'+check)


def positive_program(regions,entry,offsets,*,count):
    need('bounded-count',type(count)is int and -1<=count<=LIMIT)
    keys=('currentPtr','bufferLength','advancedCount','consumed','totalLength')
    need('independent-reader-fields',all(type(offsets.get(k))is int and 0<=offsets[k]<128 for k in keys)
        and len({offsets[k]for k in keys})==5)
    c,r,a,u,total=(bytes((offsets[k],)).hex()for k in keys)
    g=BytesPath(regions,entry);symbols={}
    def call(role):
        target=g.relative('e8');need('same-owned-helper.'+role,role not in symbols or symbols[role]==target);symbols[role]=target
    g.take('4080fd02');g.branch('0f85',False)
    g.take('488b37','488bcb');call('boolean');g.take('4885f6');g.branch('0f84',False)
    g.take('884610','4c89742448','4c8b37');context_site=g.at;g.relative('488b3d')
    g.take('48837f3800');g.branch('75',True,1)
    g.take('488b4738','488b28','48837d3800');g.branch('75',True,1)
    g.take('837b'+r+'04');g.branch('7d',True,1)
    g.take('488b43'+c,'8b30','8b7b'+r,'83c7fc');g.branch('79',True,1)
    g.take('488343'+c+'04','8343'+a+'04','8343'+u+'04','897b'+r,
        '486343'+u,'488b4b'+total,'482bc8','4863c6','483bc8');g.branch('0f8c',False)
    g.take('83feff','0f95c0','84c0');g.branch('0f84',count==-1)
    if count==-1:g.take('33f6')
    else:
        g.take('85f6');g.branch('0f84',count==0)
        if count==0:
            g.take('488b4d38','488b09');call('empty');g.take('488bf0');g.jump('eb',1)
        else:
            g.take('4c897c2450','8d3cb500000000','3b7b'+r);g.branch('7e',True,1)
            g.take('488b4538','4c8b7808','49837f3800');g.branch('75',True,1)
            g.take('498b4f38','33d2');call('context')
            g.take('488bd6','488bc8');call('arrayAllocate')
            g.take('488b5538','488bc8','488bf0','488b5210');call('dataReference')
            g.take('488b53'+c,'488bc8','448bc7');call('copy')
            g.take('4c8b7c2450','85ff');g.branch('74',False,1)
            g.take('8b6b'+r,'2bef');g.branch('79',True,1)
            g.take('017b'+a,'4863c7','480143'+c,'017b'+u,'896b'+r);g.jump('eb',1)
    g.take('4d85f6');g.branch('0f84',False)
    disabled=g.relative('833d')+1;g.take('00','49897618');g.branch('74',True,1)
    g.take('4c8b742448','488b5c2458','4883c420','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,countWitness=count,helperTargets=symbols,contextInstructionVa=context_site,
        disabledCollectorFlagVa=disabled,headerBytes=1,booleanBytes=1,arrayCountBytes=4,
        arrayPayloadBytes=max(count,0)*4,elementWireBytes=4,bulkArray=True,callbackExecuted=False,
        fieldOffsets=[16,24],sameBooleanAndArrayReferenceStoredUnchanged=True,
        entryRspRestored=True,normalReturn=True,childGrammarAdmitted=False,runtimeProviderSelectionObserved=False)


def derive(image,pins,wrapper,targets,barrier,disabled_flag):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_action_sources as actions,generated_header_sources as headers
    from scripts.game_data.memorypack import generated_reader_sources as readers,generated_primitive_sources as primitive
    from scripts.game_data.memorypack import generated_lifecycle_sources as life,interactive_value_layouts as layouts,pointer_param as pointer
    from scripts.game_data.memorypack.generated_owned_code_sources import source_family
    from scripts.game_data.memorypack.interactive_value_wrapper_sources import prefix_program
    from scripts.game_data.memorypack.skill_unmanaged_array_context import derive as array_context
    from scripts.game_data.memorypack.skill_gameplay_tag_array_sources import data_reference_program
    from scripts.game_data.memorypack.animation_state_array_sources import empty_program
    from scripts.game_data.memorypack import buff_gameplay_tag_native as atomic
    from scripts.game_data.memory_copy_bounded_native import validate_components as copy_source
    _publication_gate(image,pins);need('finite-own-wrapper',wrapper.wrapped_type==TYPE)
    ctx=NativeReferenceContext(image);base=image.pe.image_base;mm=pointer.methods(image,wrapper)
    layout=layouts.derive(image,pins,TYPE,barrier=base+barrier)
    offsets=actions.ec.source_offsets(image);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    entry=image.method_pointer_va(mm['Deserialize']);family,windows,rows,partition=source_family(image,pins,entry_rva=entry-base,tail_targets=(base+barrier,))
    header,count_row=headers.derive(image,rows,entry,2,offsets,barrier,disabled_flag=disabled_flag,owned_partition=partition)
    regions=[(actions.ec.va(r),actions.ec.raw(r))for r in rows]
    positives=[positive_program(regions,actions.ec.va(count_row),offsets,count=n)for n in range(-1,LIMIT+1)]
    context_sites={p['contextInstructionVa']for p in positives};need('one-actual-array-request',len(context_sites)==1)
    usage=derive_typed_usage_context(image,context_sites.pop()-base,label='interactiveTagOptional.array')
    context=array_context(image,usage,element_type=ELEMENT)
    symbols={}
    for p in positives:
        need('same-own-disabled-collector',p['disabledCollectorFlagVa']==base+disabled_flag)
        for key,target in p['helperTargets'].items():
            need('same-actual-helper-across-counts',key not in symbols or symbols[key]==target);symbols[key]=target
    boolean=primitive.derive(image,symbols['boolean'],'bool',offsets)
    data=pointer.owned(image,symbols['dataReference']);data_proof=data_reference_program(data['regions'],data['pointer'])
    empty=pointer.owned(image,symbols['empty']);empty_proof=empty_program(empty['regions'],empty['pointer'],symbols['context'])
    indexer=life._initialized_indexer(image,symbols['context'])
    copy_path=CONTRACTS_DIR/'memory_copy_bounded_native.json';before=copy_path.read_bytes();copy_fact=json.loads(before)
    need('same-reviewed-copy-build-and-target',copy_fact['nativeInputs']==pins and base+copy_fact['entryRva']==symbols['copy'])
    copy=copy_source(image,copy_fact);need('complete-bounded-copy',copy['maxBytes']>=LIMIT*4)
    element=atomic.validate_on_image(image,pins)
    need('own-exact-raw4-element',element['typeName']==ELEMENT and element['wireBytes']==4 and element['contextTypeKind']==17)
    allocators=[]
    for i,row in enumerate(rows[:-1]):
        if actions.ec.raw(row)[:3]!=bytes.fromhex('488b0d')or len(actions.ec.raw(row))!=7 or actions.ec.raw(rows[i+1])[:1]!=b'\xe8':continue
        u=derive_typed_usage_context(image,actions.ec.va(row)-base,label='interactiveTagOptional.allocation')
        if(u.get('tag'),u.get('typeName'))==(1,wrapper.name):allocators.append(actions.control_transfer(rows[i+1])['target'])
    need('one-exact-wrapper-allocator',len(set(allocators))==1);allocate=allocators[0];programs=[]
    by={actions.ec.va(r):r for r in rows}
    from scripts.game_data.memorypack.generated_vector_member_sources import selected_rows
    for existing,ff in((False,False),(True,False),(False,True),(True,True)):
        prefix=prefix_program(rows,entry,header,base=base,barrier=base+barrier,existing=existing,ff=ff,
            wrapper_name=wrapper.name,allocate=allocate)
        prefix_rows=prefix.pop('selectedRows')
        if prefix['allocation']is not None:
            u=derive_typed_usage_context(image,prefix['allocation']['usageInstruction'][0],label='interactiveTagOptional.selectedAllocation')
            need('same-selected-own-allocation',(u.get('tag'),u.get('typeName'))==(1,wrapper.name));prefix['allocation']['typedRequest']=u
        for positive in [None]if ff else positives:
            path=prefix_rows+([]if ff else selected_rows(rows,positive['selectedBytes']))
            frame=readers.frame_program(path,header_local=header.get('headerLocalDisplacement'),base=base,tail_barrier=base+barrier if ff else None)
            programs.append(dict(**prefix,countWitness=None if ff else positive['countWitness'],frame=frame,
                selectedProgram=[actions.ec.site(r,base)for r in path]))
    formatter=life._concrete_formatter(image,ctx,wrapper,mm['Deserialize'],pins=pins)
    need('copy-contract-bookend',before==copy_path.read_bytes());_publication_gate(image,pins)
    return dict(schema='endfield.interactive-tag-optional-source.v1',nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,
        layout=layout,header=header,codeWindows=windows,programs=programs,positivePrograms=positives,
        arrayContext=context,booleanSource=boolean,dataReferenceSource=dict(windows=data['windows'],program=data_proof),
        emptyArraySource=dict(windows=empty['windows'],program=empty_proof),classContextHelper=indexer,
        boundedCopy=copy,elementSource=element,formatterSource=formatter,
        completeSelectedCallerAdmitted=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False,
        countRange=[-1,LIMIT],runtimeProviderSelectionObserved=False)
