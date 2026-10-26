"""Exact parent null locals and ready-class paths for ExtraData dictionaries."""
import json

from scripts.game_data.memorypack.animation_extra_dictionary_sources import TYPES,validate_event

PREFIX='Beyond.Gameplay.View.Animation.'
PARENTS={
    PREFIX+'CharacterAnimExtraData':(16,22,24),
    PREFIX+'UpperBodyFightExtraData':(16,22,24),
    PREFIX+'EnemyAnimExtraData+EnemyHurtAnimData':(3,6),
}
CHARACTER_FIELDS={
    16:'Beyond.SerializeFieldDictionary`2<Beyond.Gameplay.Core.CharHurtAnim,'+PREFIX+'CharacterAnimExtraData+CharHurtAnimConfig>',
    22:'Beyond.SerializeFieldDictionary`2<string,'+PREFIX+'CharacterAnimExtraData+CharMoveAdditiveAnimConfig>',
    24:'Beyond.SerializeFieldDictionary`2<string,string>',
}
PARENT_FIELDS={PREFIX+'CharacterAnimExtraData':CHARACTER_FIELDS,
    PREFIX+'UpperBodyFightExtraData':CHARACTER_FIELDS,
    PREFIX+'EnemyAnimExtraData+EnemyHurtAnimData':{
        3:'Beyond.SerializeFieldDictionary`2<Beyond.Gameplay.Core.EnemyHurtAnim,'+PREFIX+'EnemyAnimExtraData+EnemyHurtAnimEntry>',
        6:'Beyond.SerializeFieldDictionary`2<Beyond.Gameplay.Core.EnemyHurtShakeIntensity,'+PREFIX+'EnemyAnimExtraData+EnemyHurtShakeIntensityConfig>',
    }}
LABEL='animationExtraStaticParent'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def frame_alias(header,parent_type):
    if parent_type!=PREFIX+'UpperBodyFightExtraData':return None
    address=header.get('headerAddress',{})
    need('exact-UpperBody-header-frame',header.get('nullFrameBytes')==72
        and address.get('baseRegister')=='rbp'and address.get('displacement')==40
        and address.get('entryRspOffset')==16 and address.get('rspDisplacement')==88)
    return dict(profile='animation-upper-extra-static-frame.v1',baseRegister='rbp',entryRspOffset=-24,
        currentRspBytes=72,rspRelativeBaseOffset=48,baseAliasInstruction=address['baseAliasInstruction'])


def parent_setup(image,rows,path,events,header,*,base,parent_type):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec,pointer_param as pointer
    from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
    from scripts.game_data.memorypack.pooled_global_buff_id_sources import ready_class_init
    selected=[e for e in events if e.get('mode')=='typed-static-out-reference']
    need('finite-actual-parent-fields',parent_type in PARENTS
        and tuple(e['memberIndex']for e in selected)==PARENTS[parent_type]
        and all(e['declaredType']==PARENT_FIELDS[parent_type][e['memberIndex']]for e in selected)
        and(header.get('readerRegister'),header.get('outputRegister'))==('rdi','rbx'))
    alias=frame_alias(header,parent_type);zeros=[];guards=[];calls=[]
    for event in selected:
        position=next(i for i,r in enumerate(path)if ec.site(r,base)==event['instruction'])
        argument=ec.last_write(path,position,'rdx');need('actual-reference-out-address',argument is not None)
        raw=ec.raw(argument)
        if alias:
            expected={16:(56,104),22:(-16,32),24:(-8,40)}[event['memberIndex']]
            displacement,home=expected
            need('exact-UpperBody-reference-home',raw==bytes.fromhex('488d55')+displacement.to_bytes(1,'little',signed=True))
            zero_raw=bytes.fromhex('48c745')+displacement.to_bytes(1,'little',signed=True)+b'\0'*4
            candidates=[r for r in path[:position]if ec.raw(r)==zero_raw]
            need('one-actual-UpperBody-null-reset',len(candidates)==1)
            zero=candidates[0];proof=None
            encoding=dict(baseRegister='rbp',displacement=displacement,rspDisplacement=home)
        else:
            need('actual-RSP-reference-out-address',len(raw)==5 and raw[:4]==bytes.fromhex('488d5424'))
            home=raw[4];need('finite-RSP-reference-home',home in(32,40,104))
            candidates=[r for r in path[:position]if ec.raw(r)==bytes.fromhex('48896c24')+bytes((home,))]
            need('actual-RSP-null-reset',bool(candidates));zero=candidates[-1]
            proof=_owned_zero_source(rows,base+header['ordinaryZeroFamily']['entryRva'],[ec.va(zero)],'rbp',base,header['ordinaryZeroFamily'])
            encoding=dict(baseRegister='rsp',displacement=home,rspDisplacement=home)
        zeros.append(dict(memberIndex=event['memberIndex'],instruction=ec.site(zero,base),displacement=home,
            entryRspOffset=home-header['nullFrameBytes'],zeroSource=proof,frameAddress=encoding,
            literalZero=alias is not None))
        context=event['context'];usage_position=next(i for i,r in enumerate(path)if ec.va(r)==base+context['instructionRva'])
        class_load=ec.last_write(path,usage_position,'rcx')
        if alias:
            # The ready-class helper does not write RCX on its selected ready
            # path, so last_write may conservatively stop at its E8. Locate
            # the actual RCX type load in this bounded, exact setup instead.
            start=next(i for i,r in enumerate(path)if r is zero)
            loads=[r for r in path[max(0,start-2):usage_position]if ec.raw(r)[:3]==bytes.fromhex('488b0d')]
            need('one-actual-UpperBody-class-load',len(loads)==1);class_load=loads[0]
        need('actual-owned-class-load',class_load is not None and ec.raw(class_load)[:3]==bytes.fromhex('488b0d'))
        usage=derive_typed_usage_context(image,ec.va(class_load)-base,label=LABEL+'.class')
        need('own-closed-dictionary-class',usage.get('tag')==1 and usage.get('typeName')==event['declaredType']
            and bytes.fromhex(usage.get('typeRawHex',''))[10:12]==bytes((21,0)))
        load_index=next(i for i,r in enumerate(path)if r is class_load)
        between=path[load_index+1:usage_position]
        if alias:
            actual_calls=[r for r in between if ec.raw(r)[:1]==b'\xe8'];need('one-owned-ready-class-call',len(actual_calls)==1)
            call=actual_calls[0];target=control_transfer(call)['target'];body=pointer.owned(image,target)
            program=ready_class_init(body['regions'],target)
            need('ready-class-helper-has-no-effect',program.get('calleeCalls')==0 and program.get('argumentRegistersUnchanged')is True)
            calls.append(dict(load=ec.site(class_load,base),typedRequest=usage,call=ec.site(call,base),
                targetRva=target-base,windows=body['windows'],program=program))
        else:
            comparisons=[(i,r)for i,r in enumerate(path)if load_index<i<usage_position
                and ec.raw(r)==bytes.fromhex('39a9e0000000')]
            need('one-own-ready-class-comparison',len(comparisons)==1);ci,compare=comparisons[0]
            edge=path[ci+1];flow=control_transfer(edge)
            need('actual-selected-ready-class-fallthrough',flow.get('kind')=='conditional'and flow.get('conditionCode')==4
                and ec.va(path[ci+2])==ec.va(edge)+len(ec.raw(edge)))
            zero_proof=_owned_zero_source(rows,base+header['ordinaryZeroFamily']['entryRva'],[ec.va(compare)],'rbp',base,header['ordinaryZeroFamily'])
            guards.append(dict(load=ec.site(class_load,base),typedRequest=usage,comparison=ec.site(compare,base),
                zeroSource=zero_proof,edge=ec.site(edge,base),selectedNextInstruction=ec.site(path[ci+2],base)))
    return json.loads(json.dumps(dict(schema='endfield.animation-extra-static-out-parent.v1',parentType=parent_type,
        initializedZeroLocals=zeros,classGuards=guards,classCalls=calls,sourceFrameAlias=alias,
        initializedClassStateObserved=False,condition='Own ready class path and freshly zeroed reference output homes; normal exact static source and stable disjoint storage. No class initialization slow path or live provider selection is admitted.')))


def validate_setup(setup,events):
    selected=[e for e in events if e.get('mode')=='typed-static-out-reference'];parent=setup.get('parentType')
    need('finite-setup-parent-and-fields',setup.get('schema')=='endfield.animation-extra-static-out-parent.v1'
        and parent in PARENTS and tuple(e['memberIndex']for e in selected)==PARENTS[parent]
        and all(e['declaredType']==PARENT_FIELDS[parent][e['memberIndex']]for e in selected)
        and len(setup.get('initializedZeroLocals',[]))==len(selected)
        and setup.get('initializedClassStateObserved')is False)
    upper=parent==PREFIX+'UpperBodyFightExtraData'
    need('exact-parent-ready-class-profile',len(setup.get('classCalls',[]))==(3 if upper else 0)
        and len(setup.get('classGuards',[]))==(0 if upper else len(selected)))
    expected=[e['declaredType']for e in selected]
    actual=[g['typedRequest']['typeName']for g in setup['classCalls']if upper]or[g['typedRequest']['typeName']for g in setup['classGuards']]
    need('same-nominal-classes-and-event-order',actual==expected)
    return setup


def validate_zero(row,item,base):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    need('same-actual-null-reset',ec.site(row,base)==item['instruction'])
    address=item['frameAddress'];home=item['displacement']
    if item['literalZero']:
        disp=address['displacement']
        need('exact-UpperBody-literal-zero',address['baseRegister']=='rbp'and(disp,home)in((56,104),(-16,32),(-8,40))
            and ec.raw(row)==bytes.fromhex('48c745')+disp.to_bytes(1,'little',signed=True)+b'\0'*4)
    else:
        proof=item.get('zeroSource',{})
        need('own-whole-RBP-zero-reset',address==dict(baseRegister='rsp',displacement=home,rspDisplacement=home)
            and ec.raw(row)==bytes.fromhex('48896c24')+bytes((home,))and proof.get('register')=='rbp'
            and proof.get('value')==0 and proof.get('zeroOnEveryOrdinaryPath')is True and base+item['instruction'][0]in proof.get('sites',[]))
