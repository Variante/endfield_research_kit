"""Current checkpoint ParamVariable effects and selected blackboard callees.

Only the three independently requested value types are selected. Registration
rows authenticate their own closed methods without identifying a live vtable.
Table creation, string callback effects and nonselected observer paths remain
named obligations instead of being inferred from a generic method name.
"""
import hashlib
import json

from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as parent_owner
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_programs as programs

SCHEMA='endfield.story-patrol-checkpoint-callee-sources.v1'
VARIABLE='Beyond.Gameplay.ParamVariable`1'
BASE_VARIABLE='Beyond.Gameplay.ParamVariable'
BLACKBOARD='Beyond.Gameplay.ParamBlackboard'
DICT='System.Collections.Generic.Dictionary`2'
ROLES=(('int','setId','getId'),('UnityEngine.Vector3','setPosition','getPosition'),
    ('Beyond.Gameplay.Core.EntityPtr','setEntity','getEntity'))


def need(check,condition):
    if not condition:raise ValueError('patrolCheckpointCalleeSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def _calls(packet,base):
    cells={base+at+i:b for at,h in packet['regions']for i,b in enumerate(bytes.fromhex(h))}
    result=[]
    # Instruction boundaries come from the owned decoder; bytes are checked
    # against their authenticated full regions, never searched for E8 bytes.
    for row in packet.get('rows',[]):
        raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
        need('decoded-row-matches-owned-bytes',bytes(cells[at+i]for i in range(len(raw)))==raw)
        if len(raw)==5 and raw[0]==232:
            result.append((at,at+5+int.from_bytes(raw[1:],'little',signed=True)))
    return result


def _body(image,at):
    from scripts.game_data.memorypack.pointer_param import owned
    value=parent_owner.packet(image,at);value['rows']=owned(image,at)['rows'];return value


def _leaf(image,at,parser,**kwargs):
    """Exact selected registered prefix through RET or a proved external tail."""
    base=image.pe.image_base;prefix=image.pe.bytes_at_va(at,128)
    result=parser([(at,prefix)],at,**kwargs)
    spans=[(p,len(bytes.fromhex(h)))for p,h in result['selectedBytes']]
    need('contiguous-complete-selected-leaf-prefix',spans and spans[0][0]==at
        and all(a+n==b for(a,n),(b,_)in zip(spans,spans[1:])))
    length=sum(n for _,n in spans);raw=image.pe.bytes_at_va(at,length)
    return dict(entryRva=at-base,windows=[dict(startRva=at-base,endRva=at-base+length,
        sha256=hashlib.sha256(raw).hexdigest().upper())],regions=[[at-base,raw.hex().upper()]],
        physicalFunctionExtentProved=False)


def _single_method(ctx,owner,name,parameters):
    md=ctx.image.metadata
    methods=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name
        and len(md.parameters_for(m))==parameters]
    need('one-own-declared-method-'+owner+'.'+name,len(methods)==1);return methods[0]


def _parameter_type(ctx,method):
    return [ctx.type_name(p.type_index)for p in ctx.image.metadata.parameters_for(method)]


def _registered(ge,method,kind):
    rows=ge.observe(method.index,[kind],[])
    need('one-own-closed-nonnull-registration',len(rows)==1 and type(rows[0].get('pointer'))is int and rows[0]['pointer']>0)
    return rows[0]


def require_nominal(nominal):
    """Pure reciprocal generic and nongeneric named field gates."""
    need('own-nominal-owners',nominal['variableType']==VARIABLE and nominal['baseVariableType']==BASE_VARIABLE
        and nominal['variableParent']==BASE_VARIABLE and nominal['blackboardType']==BLACKBOARD)
    need('own-blackboard-reference-table',nominal['tableField']==[BLACKBOARD,
        DICT+'<string,'+BASE_VARIABLE+'>',40])
    need('own-base-named-fields',nominal['baseFields']=={
        'key':[BASE_VARIABLE,'string',24],
        'observerCounter':[BASE_VARIABLE,'int',48],
        'secondObserver':[BASE_VARIABLE,'System.Action`2<'+BASE_VARIABLE+','+BASE_VARIABLE+'>',136]})
    field=nominal['valueField'];raw=bytes.fromhex(field['rawHex']);owner=field.get('parameterOwner',{})
    need('own-value-field-reciprocal-VAR',field['name'].startswith('VAR[')and len(raw)==16 and raw[10]==19 and raw[11]==0
        and(owner.get('typeIndex'),owner.get('typeName'),owner.get('ordinal'))==
        (nominal['variableDefinition'],VARIABLE,0))
    for name,slot,returns,args in(('SetValue',17,'void',[field['name']]),('get_value',14,field['name'],[]),
            ('set_value',15,'void',[field['name']])):
        m=nominal['methods'][name]
        need('own-value-method-signature-'+name,(m['owner'],m['name'],m['slot'],m['returns'],m['parameters'])==
            (VARIABLE,name,slot,returns,args))
        for symbol in m['valueSymbols']:
            r=bytes.fromhex(symbol['rawHex'])
            need('same-method-and-field-reciprocal-VAR',len(r)==16 and r[:8]==raw[:8]and r[10:]==raw[10:]
                and symbol.get('parameterOwner')==owner)
    context=nominal['variableContext'];need('own-selected-class-context',context['definition']==nominal['variableDefinition']and context['isMethod']is False)
    for index,method in((2,'SetValue'),(7,'get_value'),(8,'set_value')):
        slot=next(r for r in context['entries']if r['relativeSlot']==index)
        need('own-class-method-slot-'+method,slot['kind']==3 and slot['typeName']==VARIABLE and slot['methodName']==method
            and slot['methodSpec'][0]==nominal['methods'][method]['index']and slot['methodArguments']==[]
            and len(slot['classArguments'])==1 and slot['classArguments'][0].get('parameterOwner')==owner)
    return nominal


def _nominal(image,ctx):
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    md=image.metadata;symbols=ContextSymbols(image);td=ctx.index.types[VARIABLE]
    fields=[f for f in md.fields_for(td)if md.string(f.name_index)=='m_value']
    need('sole-own-declared-value-field',len(fields)==1 and len(md.fields_for(td))==1)
    value=symbols.type(ctx.type_pointer(fields[0].type_index));methods={}
    for name,n in(('SetValue',1),('get_value',0),('set_value',1)):
        method=_single_method(ctx,VARIABLE,name,n);parameters=md.parameters_for(method)
        values=[symbols.type(ctx.type_pointer(p.type_index))for p in parameters]
        if name=='get_value':values=[symbols.type(ctx.type_pointer(method.return_type))]
        methods[name]=dict(index=method.index,owner=VARIABLE,name=name,slot=method.slot,
            returns=ctx.type_name(method.return_type),parameters=_parameter_type(ctx,method),valueSymbols=values)
    result=dict(variableType=VARIABLE,baseVariableType=BASE_VARIABLE,variableParent=ctx.parent(VARIABLE),
        variableDefinition=td.index,blackboardType=BLACKBOARD,tableField=list(ctx.field(BLACKBOARD+'::variableDict')),
        baseFields={name:list(ctx.field(BASE_VARIABLE+'::'+field))for name,field in
            (('key','<key>k__BackingField'),('observerCounter','m_onPropertyChangedEventCounter'),('secondObserver','raiseOnBBVariableChangedEvent'))},
        valueField=value,methods=methods,variableContext=symbols.context(td.index,slots=[0,1,2,3,4,5,6,7,8]))
    return require_nominal(result)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    _publication_gate(image,pins);parent=parent_owner.derive(image,pins);base=image.pe.image_base
    ctx=NativeReferenceContext(image);ge=GenericEntries(image);nominal=_nominal(image,ctx);values={};creates={}
    for kind,set_role,get_role in ROLES:
        methods={};put_parent=parent['proof']['helpers'][set_role];read_parent=parent['proof']['helpers'][get_role]
        invoker=_body(image,base+put_parent['symbolRvas']['invoke']);prepare=_calls(invoker,base)[0][1]
        for name in('get_value','SetValue','set_value'):
            method=image.metadata.methods[nominal['methods'][name]['index']];registration=_registered(ge,method,kind)
            at=registration['pointer']
            if name=='get_value':packet=_leaf(image,at,programs.getter_program,kind=kind)
            elif name=='set_value'and kind=='int':
                packet=_leaf(image,at,programs.property_set_program,kind=kind,invoke=base+invoker['entryRva'])
            else:packet=_body(image,at)
            arg=registration['classInstantiation']['arguments'][0]
            methods[name]=dict(registration=registration,classArgument=ContextSymbols(image).type(arg['type_pointer_va']),
                packet=packet,canonicalMethodBodyUniquenessClaimed=False,
                actualRuntimeCallbackSelected=False)
        put=methods['SetValue']['packet'];get=methods['get_value']['packet'];prop=methods['set_value']['packet']
        value_programs=dict(getter=programs.getter_program(parent_owner.regions(get,base),base+get['entryRva'],kind=kind),
            setter=programs.set_value_program(parent_owner.regions(put,base),base+put['entryRva'],kind=kind),
            property=programs.property_set_program(parent_owner.regions(prop,base),base+prop['entryRva'],kind=kind,invoke=base+invoker['entryRva']),
            invokers={str(slot):programs.virtual_set_program(parent_owner.regions(invoker,base),base+invoker['entryRva'],kind=kind,
                prepare=prepare,callback=methods[name]['registration']['pointer'],slot=slot)for slot,name in((15,'set_value'),(17,'SetValue'))})
        values[kind]=dict(setRole=set_role,getRole=get_role,methods=methods,invoker=invoker,prepareTargetRva=prepare-base,programs=value_programs)
        create_context=next(s for s in parent['proof']['contexts'][set_role]['entries']if s['relativeSlot']==0)
        at=base+put_parent['symbolRvas']['getOrCreate'];create=_body(image,at);calls=_calls(create,base)
        definition=create_context['methodSpec'][0];context=ContextSymbols(image).context(definition,is_method=True)
        symbols=dict(lookup=base+read_parent['symbolRvas']['lookup'],
            type_from_context=base+read_parent['symbolRvas']['typeFromContext'],assignable=base+read_parent['symbolRvas']['assignable'])
        if kind.endswith('EntityPtr'):
            extra=dict(zip(('allocate','barrier','invoke','set_item'),[target for _,target in calls[1:5]]))
        else:extra=dict(new_value=calls[1][1])
        paths=[programs.get_or_create_program(parent_owner.regions(create,base),at,kind=kind,found=hit,**symbols,**extra)for hit in(False,True)]
        new=None
        if'new_value'in extra:
            own=_body(image,extra['new_value']);targets=[t for _,t in _calls(own,base)[:4]]
            need('four-own-NewParamVariable-calls',len(targets)==4)
            new=dict(packet=own,symbolRvas={k:v-base for k,v in zip(('allocate','barrier','invoke','set_item'),targets)},
                program=programs.new_variable_program(parent_owner.regions(own,base),base+own['entryRva'],kind=kind,
                    **dict(zip(('allocate','barrier','invoke','set_item'),targets))))
        creates[kind]=dict(packet=create,context=context,parentContextSlot=create_context,
            symbolRvas={k:v-base for k,v in{**symbols,**extra}.items()},programs=paths,newVariable=new)
    lookup_target={parent['proof']['helpers'][r]['symbolRvas']['lookup']for _,_,r in ROLES}
    need('same-own-typed-dictionary-source',len(lookup_target)==1);lookup=_body(image,base+next(iter(lookup_target)))
    find=_body(image,_calls(lookup,base)[0][1]);targets=[target for _,target in _calls(find,base)[:3]]
    need('own-three-default-string-chain-callees',len(targets)==3)
    symbols=dict(zip(('hash_invoke','comparer_getter','equality_invoke'),targets))
    paths,induction=programs.find_string_paths(parent_owner.regions(find,base),base+find['entryRva'],**symbols)
    dictionary=dict(lookup=lookup,find=find,symbolRvas={k:v-base for k,v in symbols.items()},
        lookupPrograms=[programs.try_get_program(parent_owner.regions(lookup,base),base+lookup['entryRva'],find=base+find['entryRva'],found=f)for f in(False,True)],
        findPrograms=paths,induction=induction)
    value=norm(dict(schema=SCHEMA,status='validated-conditional-checkpoint-callee-selected-programs',nativeInputs=pins,
        proof=dict(imageBase=base,parent=parent,nominal=nominal,values=values,creates=creates,dictionary=dictionary),
        selectedParamVariableGetAndNoObserverSetEffectsProved=True,selectedPropertySetterAndInvokerTransfersProved=True,
        selectedGetOrCreateHitAndMissTransfersProved=True,selectedStringDictionaryChainAndOutputTransfersProved=True,
        completeBlackboardStorageEffectsProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Own closed registrations, reciprocal VAR declarations and named nongeneric fields; complete selected 4/12/40 getter/store frames; distinct property slot15 and SetValue slot17 invokers; compatible-hit/miss creation calls and own string-reference lookup chain induction/output transfers.',
            conditional='Same selected closed runtime class/MethodInfo and callbacks, original replacement context absent, nonpositive observer counter and null second observer, disabled collector, ready own contexts, stable valid disjoint dictionary/value/frame storage and normal stated callee ABI. Live state is not observed.',
            unresolved=['pool allocation/reuse effects and complete created-instance initialization','selected string hash/equality and comparer factory effects','dictionary insertion/update and table growth effects','nonselected observer/event/replacement/cold/error branches','actual callback/table selection, checkpoint activation and playback'])))
    validate(value);_publication_gate(image,pins);return value


def validate(value):
    need('schema-status',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-checkpoint-callee-selected-programs')
    p=value['proof'];base=p['imageBase'];parent_owner.validate(p['parent']);require_nominal(p['nominal'])
    need('same-parent-native-inputs',p['parent']['nativeInputs']==value['nativeInputs'])
    need('finite-three-selected-values',set(p['values'])==set(p['creates'])==set(programs.KINDS))
    for kind,set_role,get_role in ROLES:
        own=p['values'][kind];need('same-parent-roles',(own['setRole'],own['getRole'])==(set_role,get_role))
        invoker=own['invoker'];parent_owner.verify_packet(invoker)
        need('same-actual-parent-invoker',invoker['entryRva']==p['parent']['proof']['helpers'][set_role]['symbolRvas']['invoke'])
        methods=own['methods'];need('exact-three-methods',set(methods)=={'get_value','SetValue','set_value'})
        for name,v in methods.items():
            parent_owner.verify_packet(v['packet']);registration=v['registration'];args=registration['classInstantiation']['arguments']
            need('own-method-registration-and-closed-argument',len(args)==1 and registration['methodInstantiation']['index']==-1
                and p['nominal']['methods'][name]['index']in registration['methodDefinitionIndices']
                and registration['pointer']==base+v['packet']['entryRva']
                and v['canonicalMethodBodyUniquenessClaimed']is False and v['actualRuntimeCallbackSelected']is False)
            arg=v['classArgument'];raw=bytes.fromhex(arg['rawHex']);expected_kind=8 if kind=='int'else 17
            need('own-exact-closed-kind-and-argument-bytes',arg['name']==kind and len(raw)==16
                and raw[10]==expected_kind and raw[11]==128 and arg['typePointerVa']==args[0]['type_pointer_va']
                and arg['rawHex']==args[0]['raw_type_record_hex'])
            need('own-exact-method-class-type-argument',registration['classInstantiation']==methods['SetValue']['registration']['classInstantiation'])
        expected=dict(getter=programs.getter_program(parent_owner.regions(methods['get_value']['packet'],base),methods['get_value']['registration']['pointer'],kind=kind),
            setter=programs.set_value_program(parent_owner.regions(methods['SetValue']['packet'],base),methods['SetValue']['registration']['pointer'],kind=kind),
            property=programs.property_set_program(parent_owner.regions(methods['set_value']['packet'],base),methods['set_value']['registration']['pointer'],kind=kind,invoke=base+invoker['entryRva']),
            invokers={str(slot):programs.virtual_set_program(parent_owner.regions(invoker,base),base+invoker['entryRva'],kind=kind,
                prepare=base+own['prepareTargetRva'],callback=methods[name]['registration']['pointer'],slot=slot)for slot,name in((15,'set_value'),(17,'SetValue'))})
        need('full-value-program-replay',norm(expected)==own['programs'])
        create=p['creates'][kind];parent_owner.verify_packet(create['packet'])
        need('same-actual-parent-creation',create['packet']['entryRva']==p['parent']['proof']['helpers'][set_role]['symbolRvas']['getOrCreate'])
        need('own-formal-GetOrCreate-method-context',create['context']['definition']==create['parentContextSlot']['methodSpec'][0]
            and(create['context']['typeName'],create['context']['methodName'])==(BLACKBOARD,'GetParamVariableOrNewOne'))
        symbols={k:base+v for k,v in create['symbolRvas'].items()}
        expected=[programs.get_or_create_program(parent_owner.regions(create['packet'],base),base+create['packet']['entryRva'],kind=kind,found=f,**symbols)for f in(False,True)]
        need('full-create-program-replay',norm(expected)==create['programs'])
        new=create['newVariable']
        if kind.endswith('EntityPtr'):need('entity-creation-own-inline-only',new is None)
        else:
            parent_owner.verify_packet(new['packet']);need('same-NewParamVariable-target',new['packet']['entryRva']==create['symbolRvas']['new_value'])
            expected=programs.new_variable_program(parent_owner.regions(new['packet'],base),base+new['packet']['entryRva'],kind=kind,
                **{k:base+v for k,v in new['symbolRvas'].items()})
            need('full-NewParamVariable-program-replay',norm(expected)==new['program'])
    d=p['dictionary'];parent_owner.verify_packet(d['lookup']);parent_owner.verify_packet(d['find'])
    need('same-actual-typed-dictionary-source',all(d['lookup']['entryRva']==p['parent']['proof']['helpers'][r]['symbolRvas']['lookup']for _,_,r in ROLES))
    expected=[programs.try_get_program(parent_owner.regions(d['lookup'],base),base+d['lookup']['entryRva'],find=base+d['find']['entryRva'],found=f)for f in(False,True)]
    need('full-lookup-program-replay',norm(expected)==d['lookupPrograms'])
    paths,induction=programs.find_string_paths(parent_owner.regions(d['find'],base),base+d['find']['entryRva'],**{k:base+v for k,v in d['symbolRvas'].items()})
    need('full-string-chain-and-induction-replay',norm(paths)==d['findPrograms']and norm(induction)==d['induction'])
    need('no-unproved-storage-runtime-grant',all(value[k]is False for k in('completeBlackboardStorageEffectsProved','runtimeInvocationObserved','playbackProved')))
    return value
