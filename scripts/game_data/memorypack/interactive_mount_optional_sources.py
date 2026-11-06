"""Optional mount arrays with the actual inlined ReadArray front and slot5.

The separately owned byref array source supplies count/element obligations.
This owner proves the closed outer request, its slot0 context, initially null
local, actual byref call and unchanged array/boolean field transfers, plus
new/reused/FF entry paths and frames at both actual entry ABIs.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Optional`1<Beyond.Gameplay.View.NameMountPointDef[]>'


def need(check,condition):
    if not condition:raise ValueError('interactiveMountOptional.'+check)


def positive_program(regions,entry,*,formatter=False):
    need('literal-entry-ABI',type(formatter)is bool)
    g=BytesPath(regions,entry);g.take('4080fe02'if formatter else'4080fd02');g.branch('0f85',False)
    g.take('488b37','488bcb');boolean=g.relative('e8');g.take('4885f6');g.branch('0f84',False)
    g.take('884610','488b37');context_site=g.at;g.relative('488b3d')
    g.take('48837f3800');g.branch('75',True,1)
    local=56 if formatter else 48;d=bytes((local,)).hex()
    g.take('4c8b4738','488d5424'+d);zero=g.at;g.take('48c74424'+d+'00000000','488bcb','4d8b00')
    call_site=g.at;byref=g.relative('e8');g.take('4885f6');g.branch('0f84',False)
    disabled=g.relative('833d')+1;g.take('00','488b4424'+d,'48894618');g.branch('0f84',True)
    g.take('488b5c24'+('30'if formatter else'38'),'488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,booleanTargetVa=boolean,arrayContextInstructionVa=context_site,
        arrayByrefCallInstructionVa=call_site,arrayByrefTargetVa=byref,disabledCollectorFlagVa=disabled,
        localDisplacement=local,localZeroInstructionVa=zero,localZeroBytes='48C74424'+d.upper()+'00000000',
        arrayInitiallyNull=True,arrayContextSlot=0,arrayReferenceBytes=8,fieldOffsets=[16,24],
        sameBooleanAndArrayReferenceStoredUnchanged=True,entryRspRestored=True,normalReturn=True,
        childGrammarAdmitted=False,formatterEntry=formatter)


def _complete(image,pins,wrapper,targets,barrier,disabled_flag,*,formatter_method=None,body=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,generated_action_sources as actions
    from scripts.game_data.memorypack import generated_header_sources as headers,generated_reader_sources as readers
    from scripts.game_data.memorypack import generated_primitive_sources as primitive,interactive_value_layouts as layouts
    from scripts.game_data.memorypack.interactive_mount_array_sources import derive_inlined_front
    from scripts.game_data.memorypack.generated_owned_code_sources import source_family
    from scripts.game_data.memorypack.generated_vector_member_sources import selected_rows
    from scripts.game_data.memorypack.interactive_value_wrapper_sources import prefix_program
    _publication_gate(image,pins);need('finite-own-wrapper',wrapper.wrapped_type==TYPE)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);mm=pointer.methods(image,wrapper)
    is_formatter=formatter_method is not None
    entry=image.method_pointer_va(formatter_method if is_formatter else mm['Deserialize'])
    family,windows,rows,partition=source_family(image,pins,entry_rva=entry-base,tail_targets=(base+barrier,))
    if is_formatter:need('same-fresh-actual-slot5-windows',body['windows']==windows and body['pointer']==entry)
    layout=layouts.derive(image,pins,TYPE,barrier=base+barrier);offsets=actions.ec.source_offsets(image)
    header,count=headers.derive(image,rows,entry,2,offsets,barrier,disabled_flag=disabled_flag,
        owned_partition=partition,argument_registers=('rdx','r8')if is_formatter else('rcx','rdx'))
    regions=[(actions.ec.va(r),actions.ec.raw(r))for r in rows]
    positive=positive_program(regions,actions.ec.va(count),formatter=is_formatter)
    need('same-exact-disabled-collector',positive['disabledCollectorFlagVa']==base+disabled_flag)
    boolean=primitive.derive(image,positive['booleanTargetVa'],'bool',offsets)
    usage=derive_typed_usage_context(image,positive['arrayContextInstructionVa']-base,label='interactiveMountOptional.ReadArray')
    array=derive_inlined_front(image,pins,typed_request=usage,call_target=positive['arrayByrefTargetVa'])
    need('own-independent-inner-array-source',array['schema']=='endfield.interactive-mount-point-byref-array-source.v1'
        and array['nativeInputs']==pins and array['resultAbi']=='void-byref-reference8'
        and array['arrayReaderTargetRva']==positive['arrayByrefTargetVa']-base and array['initiallyNullArrayRequired']is True)
    allocators=[]
    for i,row in enumerate(rows[:-1]):
        if len(actions.ec.raw(row))!=7 or actions.ec.raw(row)[:3]!=bytes.fromhex('488b0d')or actions.ec.raw(rows[i+1])[:1]!=b'\xe8':continue
        u=derive_typed_usage_context(image,actions.ec.va(row)-base,label='interactiveMountOptional.allocation')
        if(u.get('tag'),u.get('typeName'))==(1,wrapper.name):allocators.append(actions.control_transfer(rows[i+1])['target'])
    need('one-current-wrapper-allocator',len(set(allocators))==1);allocate=allocators[0];programs=[]
    for existing,ff in((False,False),(True,False),(False,True),(True,True)):
        prefix=prefix_program(rows,entry,header,base=base,barrier=base+barrier,existing=existing,ff=ff,
            wrapper_name=wrapper.name,allocate=allocate)
        for guard in prefix['initializedGuards']:
            if guard['kind']=='wrapper-class-ready':
                u=derive_typed_usage_context(image,guard['instruction'][0],label='interactiveMountOptional.classReady')
                need('same-own-ready-wrapper',(u.get('tag'),u.get('typeName'))==(1,wrapper.name));guard['typedRequest']=u
        if prefix['allocation']is not None:
            u=derive_typed_usage_context(image,prefix['allocation']['usageInstruction'][0],label='interactiveMountOptional.selectedAllocation')
            need('same-selected-wrapper',(u.get('tag'),u.get('typeName'))==(1,wrapper.name));prefix['allocation']['typedRequest']=u
        path=prefix.pop('selectedRows')+([]if ff else selected_rows(rows,positive['selectedBytes']))
        locals_=[]if ff else[dict(displacement=positive['localDisplacement'],bytes=8,
            zeroInstruction=[positive['localZeroInstructionVa']-base,positive['localZeroBytes']])]
        frame=readers.frame_program(path,base=base,header_local=header.get('headerLocalDisplacement'),
            source_locals=locals_,tail_barrier=base+barrier if ff else None)
        programs.append(dict(**prefix,frame=frame,selectedProgram=[actions.ec.site(r,base)for r in path]))
    _publication_gate(image,pins)
    return dict(schema='endfield.interactive-mount-optional-source.v1',nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,
        layout=layout,header=header,codeWindows=windows,positiveProgram=positive,programs=programs,
        booleanSource=boolean,arraySource=array,completeSelectedCallerAdmitted=True,childGrammarAdmitted=False,
        wholeOwnerAdmitted=False,formatterEntry=is_formatter,runtimeProviderSelectionObserved=False)


def derive(image,pins,wrapper,targets,barrier,disabled_flag):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_lifecycle_sources as life,pointer_param as pointer
    result=_complete(image,pins,wrapper,targets,barrier,disabled_flag)
    def formatter_source(image,wrapper,reader,method,body):
        proof=_complete(image,pins,wrapper,targets,barrier,disabled_flag,formatter_method=method,body=body)
        return dict(completeSelectedFormatterAdmitted=True,childGrammarAdmitted=False,
            programs=proof['programs'],inlineMountOptionalSource=proof)
    result['formatterSource']=life._concrete_formatter(image,NativeReferenceContext(image),wrapper,
        pointer.methods(image,wrapper)['Deserialize'],formatter_prover=formatter_source,pins=pins)
    return result
