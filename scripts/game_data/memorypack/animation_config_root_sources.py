"""Current complete AnimationConfig caller, with independent child obligations.

This binds the exact MC15 new/existing caller, named setters and all three
fresh custom-dictionary out-locals. The maintained mask source independently
owns the first-five-field profile. Tail child components must join these actual
typed requests and calls; no wire shape, public selection or EOF is inferred.
"""
import json
from scripts.game_data.memorypack.animation_config_root_programs import FIELDS,program

TYPE='Beyond.Gameplay.View.Animation.AnimationConfigJson'
SCHEMA='endfield.animation-config-root-source.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError('animationConfigRootSource.'+check+':'+str(detail)[:1000])


def verify(actual,pins):
    """Replay the complete retained parent, without supplying child grammars."""
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.generated_member_sources import base_setter_program
    need('exact-fifteen-source',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-animation-config-root-source'
        and actual.get('typeName')==TYPE and actual.get('memberCount')==15
        and actual.get('allFifteenFieldTransfersProved')is True and actual.get('completeSelectedNormalFramesProved')is True
        and actual.get('childGrammarAdmitted')is False and actual.get('wholeOwnerAdmitted')is False
        and actual.get('publicDecoderActivated')is False)
    selected=actual.get('programs',[]);method=actual.get('method',[])
    need('two-complete-ordinary-parent-paths',len(selected)==2 and len(method)==4 and method[2]=='Deserialize'
        and type(selected[0]['selectedBytes'][0][0])is int and type(method[3])is int)
    base=selected[0]['selectedBytes'][0][0]-method[3]
    raw=regions(actual['codeWindows'],actual['sourceRegions'],base,'animation-config-parent')
    byte_map={a+i:b for a,data in raw for i,b in enumerate(data)}
    requests=actual['requests'];setters=actual['setters'];members=actual['members']
    need('all-and-only-owned-named-fields',len(requests)==len(setters)==len(members)==15
        and tuple(r.get('fieldName')for r in requests)==FIELDS and tuple(r.get('fieldName')for r in members)==FIELDS
        and all(r.get('memberIndex')==i for i,r in enumerate(requests))
        and all(r.get('memberIndex')==i for i,r in enumerate(members)))
    symbols={k:base+v for k,v in actual['proof']['symbolRvas'].items()}
    reads=[base+r['sourceTargetRva']for r in requests];targets=[base+r['method'][3]for r in setters]
    replay=[program(raw,base+method[3],symbols,reads,targets,new=new)for new in(False,True)]
    need('complete-parent-bytes-and-frames-replayed',json.loads(json.dumps(replay))==selected
        and all(p.get('normalReturn')is True and p.get('entryRspRestored')is True for p in replay))
    for index,(setter,request,member,event)in enumerate(zip(setters,requests,members,replay[0]['fieldEvents'],strict=True)):
        sr=regions(setter['windows'],setter['sourceRegions'],base,'animation-config-setter-'+str(index))
        need('complete-setter-byte-partition',all(b''.join(bytes.fromhex(r['bytes'])for r in setter['sourceRows']
            if at<=int(r['va'],16)<at+len(raw_bytes))==raw_bytes for at,raw_bytes in sr))
        value=member['declaredType']=='Beyond.Resource.StringPathHash';boolean=member['declaredType']=='bool'
        mode='qword-return'if value else'normalized-byte-return'if boolean else'reference-return'
        parsed=base_setter_program(setter['sourceRows'],holder=16,field=member['fieldOffset'],mode=mode,barrier=symbols['barrier'])
        need('same-whole-named-setter-program',json.loads(json.dumps(parsed))==setter['program']
            and setter.get('field')==[TYPE,member['declaredType'],member['fieldOffset']]
            and setter.get('declaredType')==member['declaredType']and request['typeName']==member['declaredType']
            and request['setterMethod']==setter['method']and setter['method'][1]==actual['wrapperName']
            and setter['method'][2]=='set___'+member['fieldName']+'__'
            and request['sourceInstructionRva']==event['sourceCallInstructionVa']-base
            and request.get('initiallyNullOutputProved')==event.get('initiallyNullOutputProved',False)
            and request.get('outLocal')==event.get('outLocal'))
        usage=request.get('typedRequest')
        if usage is not None:
            encoded=bytes.fromhex(usage.get('instructionHex',''));load=base+usage.get('instructionRva',-base)
            need('same-actual-owned-MethodInfo-load',usage.get('instructionRva')==event['contextInstructionVa']-base
                and len(encoded)==7 and encoded[:3]in(bytes.fromhex('488b15'),bytes.fromhex('4c8b05'))
                and bytes(byte_map.get(load+i,0)for i in range(7))==encoded)
            if index in(6,11,12):
                args=member['declaredType'].split('<',1)[1][:-1].split(',',1)
                need('exact-static-closed-dictionary-context',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
                    (6,'Beyond.SerializeFieldDictionary`2','DeserializeV2',args,[])
                    and request['classTypeUsage']['typeName']==member['declaredType']and request['classTypeUsage']['tag']==1)
            else:
                name='ReadUnmanaged'if value else'ReadPackable'if index in(3,7,10)else'ReadValue'
                need('exact-reader-nominal-request',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
                    (6,'MemoryPack.MemoryPackReader',name,[],[member['declaredType']]))
    return base


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import animation_mask_sources as masks,scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.pointer_param import methods,owned
    from scripts.game_data.memorypack.generated_member_sources import base_setter_program
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    path=CONTRACTS_DIR/'animation_masks_native.json';raw=path.read_bytes();fact=json.loads(raw)
    need('same-reviewed-mask-source',fact.get('schema')=='endfield.animation-masks-native.v1'
        and fact.get('status')=='conditional-current-build'and fact.get('nativeInputs')==pins)
    prefix=masks.validate_components(image,fact);profile=fact['profile']
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    need('exact-current-root-wrapper',wrapper.name==profile['types']['rootWrapper']
        and tuple(m.name for m in wrapper.members)==FIELDS and ctx.is_value_type(TYPE)is False)
    mm=methods(image,wrapper);reader=mm['Deserialize'];primitive_param.reader_abi(image,ctx,reader,wrapper)
    body=owned(image,image.method_pointer_va(reader));setters=[image.method_pointer_va(md.methods[m.method_index])for m in wrapper.members]
    symbols={k:base+v for k,v in profile['symbols'].items()}
    need('same-current-root-construction',symbols['rootConstructor']==image.method_pointer_va(mm['.ctor']))
    reads=[base+r for r in profile['rootReads']]+[None]*10
    programs=[program(body['regions'],body['pointer'],symbols,reads,setters,new=new)for new in(False,True)]
    events=programs[0]['fieldEvents'];need('same-two-parent-field-programs',events==programs[1]['fieldEvents'])
    member_rows=[];setter_proofs=[];requests=[]
    for member,event in zip(wrapper.members,events,strict=True):
        index=event['memberIndex'];field=ctx.field(TYPE+'::'+member.name);method=md.methods[member.method_index]
        value=member.declared_type=='Beyond.Resource.StringPathHash';boolean=member.declared_type=='bool'
        kind=17 if value else 2 if boolean else 21 if '<'in member.declared_type else 18
        scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),
            [(member.declared_type,kind,not(value or boolean))],'animationConfigRoot.setter.'+member.name)
        setter=owned(image,setters[index]);mode='qword-return'if value else'normalized-byte-return'if boolean else'reference-return'
        setter_program=base_setter_program(setter['rows'],holder=16,field=field[2],mode=mode,barrier=symbols['barrier'])
        need('whole-owned-named-setter',setter_program.get('completeOriginalProgram')is True
            and setter_program.get('normalIncomingValueStoredUnchanged')is True and setter_program.get('ordinaryFrameRestored')is True)
        setter_proofs.append(dict(method=[method.index,wrapper.name,md.string(method.name_index),setters[index]-base],
            declaredType=member.declared_type,field=list(field),windows=setter['windows'],program=setter_program,
            sourceRows=setter['rows'],sourceRegions=[[a-base,b.hex()]for a,b in setter['regions']]))
        typed=None;class_type=None
        if 'contextInstructionVa'in event:
            typed=derive_typed_usage_context(image,event['contextInstructionVa']-base,label='animationConfigRoot.'+member.name)
            if index in(6,11,12):
                arguments=member.declared_type.split('<',1)[1][:-1].split(',',1)
                need('exact-current-static-dictionary-request',tuple(typed.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
                    ==(6,'Beyond.SerializeFieldDictionary`2','DeserializeV2',arguments,[]))
                class_type=derive_typed_usage_context(image,event['classInstructionVa']-base,label='animationConfigRoot.class.'+member.name)
                need('same-ready-closed-dictionary-class',class_type.get('tag')==1 and class_type.get('typeName')==member.declared_type,
                    dict(field=member.name,type=class_type.get('typeName')))
            else:
                expected='ReadUnmanaged'if value else'ReadPackable'if member.kind=='list'or index==10 else'ReadValue'
                need('exact-current-reader-field-request',tuple(typed.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
                    ==(6,'MemoryPack.MemoryPackReader',expected,[],[member.declared_type]))
        if index in(8,9):need('same-actual-StringPathHash-source',event['sourceTargetVa']==symbols['hash'])
        if index in(7,10):need('same-actual-packable-reference-source',event['sourceTargetVa']==programs[0]['fieldEvents'][3]['sourceTargetVa'])
        if index==5:need('same-actual-reference-ReadValue-source',event['sourceTargetVa']==events[0]['sourceTargetVa'])
        if boolean:
            source=vector_recorder(image)(event['sourceTargetVa']-base,fragments=True)
            scalar.boolean_source(image,source,scalar.reader_offsets(image,'animationConfigRoot'),member.name)
        requests.append(dict(memberIndex=index,fieldName=member.name,typeName=member.declared_type,
            typedRequest=typed,sourceTargetRva=event['sourceTargetVa']-base,sourceInstructionRva=event['sourceCallInstructionVa']-base,
            classTypeUsage=class_type,initiallyNullOutputProved=event.get('initiallyNullOutputProved',False),
            outLocal=event.get('outLocal'),setterMethod=setter_proofs[-1]['method']))
        member_rows.append(dict(memberIndex=index,fieldName=member.name,declaredType=member.declared_type,fieldOffset=field[2]))
    need('same-actual-two-Boolean-sources',events[13]['sourceTargetVa']==events[14]['sourceTargetVa'])
    if path.read_bytes()!=raw:raise ValueError('animationConfigRoot.mask-declaration-drift')
    _publication_gate(image,pins)
    result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-animation-config-root-source',
        nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,memberCount=15,members=member_rows,requests=requests,
        method=[reader.index,wrapper.name,'Deserialize',body['pointer']-base],codeWindows=body['windows'],
        sourceRegions=[[a-base,b.hex()]for a,b in body['regions']],
        programs=programs,setters=setter_proofs,firstFiveProfile=prefix,
        dictionaryOutputsInitiallyNullProved=True,allFifteenFieldTransfersProved=True,
        completeSelectedNormalFramesProved=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False,
        publicDecoderActivated=False,proof=dict(symbolRvas={k:v-base for k,v in symbols.items()}),evidenceBoundary=__doc__)))
    verify(result,pins);return result
