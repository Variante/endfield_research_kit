"""Selected ordinary EventParams variable recycling and own Type registry."""
import json

from scripts.game_data.memorypack import leveldata_patrol_event_cleanup_sources as cleanup
from scripts.game_data.memorypack import leveldata_patrol_event_cleanup_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_type_dictionary_programs as table_programs
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_pool_sources as pool
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as source
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as helpers
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_storage_sources as capture

SCHEMA='endfield.story-patrol-event-recycler-sources.v1'
VARIABLE='Beyond.Gameplay.ParamVariable`1'
TYPED_POOL='Beyond.Gameplay.ParamVariablePool`1'
POOL_MANAGER='Beyond.Gameplay.ParamVariablePool'
INTERFACE='Beyond.Gameplay.IParamVariablePool'


def need(check,condition):
    if not condition:raise ValueError('patrolEventRecycler.'+check)


def norm(value):return json.loads(json.dumps(value))


def _method(ctx,owner,name,argc):
    m=source._single_method(ctx,owner,name,argc)
    return dict(index=m.index,owner=owner,name=name,slot=m.slot,parameters=source._parameter_type(ctx,m),
        returns=ctx.type_name(m.return_type),pointerRva=(ctx.image.method_pointer_va(m)-ctx.image.pe.image_base)
            if ctx.image.method_pointer_va(m)else None)


def _metadata(image):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    ctx=NativeReferenceContext(image);cs=ContextSymbols(image);md=image.metadata
    expected=cleanup.DICT+'<System.Type,'+INTERFACE+'>'
    fields=[f for f in md.fields_for(ctx.index.types[POOL_MANAGER])if ctx.type_name(f.type_index)==expected]
    need('one-own-Type-pool-dictionary-field',len(fields)==1)
    name=md.string(fields[0].name_index)
    return dict(poolDefinition=ctx.index.types[TYPED_POOL].index,variableDefinition=ctx.index.types[VARIABLE].index,
        poolContext=cs.context(ctx.index.types[TYPED_POOL].index),variableContext=cs.context(ctx.index.types[VARIABLE].index,slots=[0]),
        poolDictionaryField=list(ctx.field(POOL_MANAGER+'::'+name)),poolDictionaryFieldName=name,
        getType=_method(ctx,VARIABLE,'get_type',0),recycle=_method(ctx,TYPED_POOL,'RecycleFromMainPool',1),
        interfaceRecycle=_method(ctx,INTERFACE,'RecycleFromMainPool',1),
        runtimeHash=_method(ctx,'System.RuntimeType','GetHashCode',0),
        runtimeEquals=_method(ctx,'System.RuntimeType','Equals',1),
        selfGetter=_method(ctx,'System.RuntimeType','get_UnderlyingSystemType',0),
        objectComparerEquals=_method(ctx,'System.Collections.Generic.ObjectEqualityComparer`1','Equals',2))


def require_metadata(m):
    need('own-registry-field',m['poolDictionaryField']==[POOL_MANAGER,cleanup.DICT+'<System.Type,'+INTERFACE+'>',16])
    for key,owner,name,slot,returns,args in(
        ('getType',VARIABLE,'get_type',9,'System.Type',[]),
        ('recycle',TYPED_POOL,'RecycleFromMainPool',5,'void',[cleanup.VARIABLE]),
        ('interfaceRecycle',INTERFACE,'RecycleFromMainPool',1,'void',[cleanup.VARIABLE]),
        ('runtimeHash','System.RuntimeType','GetHashCode',2,'int',[]),
        ('runtimeEquals','System.RuntimeType','Equals',0,'bool',['object']),
        ('selfGetter','System.RuntimeType','get_UnderlyingSystemType',40,'System.Type',[])):
        row=m[key];need('own-method-'+key,(row['owner'],row['name'],row['slot'],row['returns'],row['parameters'])==(owner,name,slot,returns,args))
    c=m['poolContext'];need('own-reciprocal-pool-context',c['definition']==m['poolDefinition']and c['typeName']==TYPED_POOL and c['isMethod']is False)
    entries={r['relativeSlot']:r for r in c['entries']};formal=entries[12]['type']['classArguments'][0]
    owner=formal['parameterOwner'];raw=bytes.fromhex(formal['rawHex'])
    need('own-pool-VAR',raw[10:12]==bytes((19,0))and(owner['typeIndex'],owner['ordinal'])==(m['poolDefinition'],0))
    need('own-typed-variable-class',entries[12]['kind']==2 and entries[12]['type']['definition']['name']==VARIABLE
        and len(entries[12]['type']['classArguments'])==1)
    need('own-typed-singleton',entries[9]['kind']==3 and(entries[9]['typeName'],entries[9]['methodName'])==('Beyond.Singleton`1','get_instance')
        and entries[9]['classArguments'][0]['definition']['name']==TYPED_POOL
        and entries[9]['classArguments'][0]['classArguments']==[formal])
    need('own-typed-Stack-Push-context',entries[14]['kind']==3
        and(entries[14]['typeName'],entries[14]['methodName'])==('System.Collections.Generic.Stack`1','Push')
        and entries[14]['classArguments'][0]==entries[12]['type'])
    v=m['variableContext'];need('only-consumed-getType-class-context',v['definition']==m['variableDefinition']
        and v['typeName']==VARIABLE and v['isMethod']is False and v['selectedSlots']==[0]and len(v['entries'])==1)
    vr=v['entries'][0];vf=vr['type'];vo=vf['parameterOwner']
    need('own-getType-reciprocal-class-VAR',vr['relativeSlot']==0 and vr['kind']==1
        and bytes.fromhex(vf['rawHex'])[10:12]==bytes((19,0))
        and(vo['typeIndex'],vo['ordinal'])==(m['variableDefinition'],0))
    return m


def _replay(p,base,symbols,metadata):
    selected=['unselected']
    def r(name):
        selected[0]=name
        return helpers.regions(p[name],base)
    e=lambda n:base+p[n]['entryRva'];s={k:base+v for k,v in symbols.items()}
    callbacks={k:base+metadata[k]['pointerRva']for k in('runtimeHash','runtimeEquals','selfGetter')}
    try:
        return dict(recycler=[programs.ordinary_variable_recycler_program(r('recycler'),e('recycler'),
                get_type_invoke=e('typeInvoker'),context_type=s['context_type'],type_from_context=s['type_from_context'],
                try_get=e('tryGet'),prepare=s['prepare'],recycle_typed=e('typedRecycleEntity'if mode=='entity-interface'else'typedRecycleScalar'),
                assignable=e('assignable'),singleton=e('singleton'),push=e('push'),mode=mode,misses=n)
                for mode in('first-direct','second-direct','entity-interface')for n in(range(4)if mode=='entity-interface'else(0,))],
            getType=programs.variable_type_program(r('getType'),e('getType'),from_handle=s['from_handle']),
            typeInvoker=programs.variable_type_invoker_program(r('typeInvoker'),e('typeInvoker'),prepare=s['prepare'],callback=e('getType')),
            typedRecycles={name:programs.variable_pool_recycle_program(r(name),e(name),
                type_from_context=s['type_from_context'],assignable=e('assignable'),invoke=e('resetInvoker'),
                singleton=e('singleton'),push=e('push'))for name in('typedRecycleScalar','typedRecycleEntity')},
            resetInvoker=programs.variable_reset_invoker_program(r('resetInvoker'),e('resetInvoker'),prepare=s['prepare'],callback=e('reset')),
            push=programs.stack_push_program(r('push'),e('push')),
            tryGet=[table_programs.try_get_program(r('tryGet'),e('tryGet'),find=e('find'),found=f)for f in(False,True)],
            find=table_programs.find_paths(r('find'),e('find'),hash_invoke=e('hashInvoker'),comparer_getter=e('factoryThunk'),equality_invoke=e('equalityInvoker')),
            factory=source.programs.default_comparer_program(r('factory'),e('factory'),type_from_context=s['type_from_context'],context_type=s['context_type']),
            selfGetter=table_programs.self_type_program(r('selfGetter'),e('selfGetter')),
            runtimeHash=table_programs.runtime_type_hash_program(r('runtimeHash'),e('runtimeHash'),prepare=s['prepare'],self_getter=callbacks['selfGetter']),
            hashInvoker=table_programs.runtime_type_hash_invoker_program(r('hashInvoker'),e('hashInvoker'),prepare=s['prepare'],callback=callbacks['runtimeHash'],self_getter=callbacks['selfGetter']),
            runtimeEquals=table_programs.runtime_type_equals_program(r('runtimeEquals'),e('runtimeEquals')),
            erasedComparer=table_programs.erased_reference_equals_program(r('erasedComparer'),e('erasedComparer'),invoke=e('equalsInvoker')),
            equalityInvoker=table_programs.comparer_equals_invoker_program(r('equalityInvoker'),e('equalityInvoker'),prepare=s['prepare'],callback=e('erasedComparer'),invoke=e('equalsInvoker')),
            equalsInvoker=table_programs.runtime_type_equals_invoker_program(r('equalsInvoker'),e('equalsInvoker'),prepare=s['prepare'],callback=callbacks['runtimeEquals']))
    except (ValueError,KeyError,TypeError) as error:
        raise ValueError("patrolEventRecycler.program."+selected[0]+":"+str(error)) from error


def _usage_gates(usages,progs):
    u=usages['registry'];need('own-warm-manager-context',u['typeName']=='Beyond.Singleton`1'and u['methodName']=='get_instance'
        and u['classArguments']==[POOL_MANAGER]and u['methodArguments']==[])
    u=usages['lookup'];need('own-Type-interface-pool-TryGet',u['typeName']==cleanup.DICT and u['methodName']=='TryGetValue'
        and u['classArguments']==['System.Type',INTERFACE]and u['methodArguments']==[])
    u=usages['interface'];need('own-pool-interface-class',u['typeName']==INTERFACE)
    for key,field in(('registry','registryMethodInfoSiteVa'),('lookup','lookupMethodInfoSiteVa')):
        need('actual-usage-site-'+key,usages[key]['instructionRva']==progs['recycler'][0][field]-progs['imageBase'])


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    _publication_gate(image,pins);clear=cleanup.derive(image,pins);old=pool.derive(image,pins);base=image.pe.image_base
    metadata=require_metadata(_metadata(image));ge=GenericEntries(image);p=dict(recycler=clear['proof']['packets']['recycleVariable'])
    registrations={};types=source.programs.KINDS
    for kind in types:
        registrations[kind]={}
        for key,method in(('getType',metadata['getType']),('recycle',metadata['recycle'])):
            rows=ge.observe(method['index'],[kind],[]);need('own-exact-closed-'+key,len(rows)==1 and rows[0].get('pointer'))
            registrations[kind][key]=rows[0]
    targets={r['getType']['pointer']for r in registrations.values()};need('same-actual-getType-bytes',len(targets)==1)
    p['getType']=source._body(image,targets.pop())
    p['typedRecycleScalar']=source._body(image,registrations['int']['recycle']['pointer'])
    need('Vector-own-registration-same-actual-scalar-program',registrations['UnityEngine.Vector3']['recycle']['pointer']==base+p['typedRecycleScalar']['entryRva'])
    p['typedRecycleEntity']=source._body(image,registrations['Beyond.Gameplay.Core.EntityPtr']['recycle']['pointer'])
    calls=[t for a,t in source._calls(p['typedRecycleScalar'],base)][:5]
    need('five-selected-typed-recycle-calls',len(calls)==5)
    symbols=dict(zip(('type_from_context','assignable','resetInvoker','singleton','push'),calls))
    for key in('assignable','resetInvoker','singleton','push'):p[key]=source._body(image,symbols[key])
    p['reset']=clear['proof']['packets']['variableRecycle']
    p['typeInvoker']=source._body(image,cleanup._call(p['recycler'],base,111))
    p['tryGet']=source._body(image,cleanup._call(p['recycler'],base,264))
    p['find']=source._body(image,cleanup._call(p['tryGet'],base,101))
    p['hashInvoker']=source._body(image,cleanup._call(p['find'],base,81))
    p['factoryThunk']=capture._fixed_prefix(image,cleanup._call(p['find'],base,134),5)
    g=BytesPath(helpers.regions(p['factoryThunk'],base),base+p['factoryThunk']['entryRva'])
    p['factory']=source._body(image,g.relative('e9'))
    p['equalityInvoker']=source._body(image,cleanup._call(p['find'],base,210))
    p['erasedComparer']=capture._prefix(image,base+old['proof']['storageSource']['proof']['strings']['erasedEqualityCandidate']['entryRva'],
        [lambda regions,entry:table_programs.erased_reference_equals_program(regions,entry,
            invoke=base+old['proof']['storageSource']['proof']['strings']['nestedEqualsInvoker']['entryRva'])])
    p['equalsInvoker']=source._body(image,cleanup._call(p['equalityInvoker'],base,98))
    for key,role in(('runtimeHash','runtimeHash'),('runtimeEquals','runtimeEquals'),('selfGetter','selfGetter')):
        method=metadata[role]
        p[key]=(source._leaf(image,base+method['pointerRva'],table_programs.runtime_type_equals_program)if key=='runtimeEquals'
            else source._leaf(image,base+method['pointerRva'],table_programs.self_type_program)if key=='selfGetter'
            else source._body(image,base+method['pointerRva']))
    symbols.update(context_type=cleanup._call(p['recycler'],base,130),prepare=cleanup._call(p['typeInvoker'],base,29),
        from_handle=scope_tail(p['getType'],base))
    symbol_rvas={k:v-base for k,v in symbols.items()};facts=_replay(p,base,symbol_rvas,metadata)
    usages={k:derive_typed_usage_context(image,at-base,label='patrolEventRecycler.'+k)for k,at in(
        ('registry',facts['recycler'][0]['registryMethodInfoSiteVa']),('lookup',facts['recycler'][0]['lookupMethodInfoSiteVa']),
        ('interface',facts['recycler'][-1]['interfaceClassSiteVa']))}
    _usage_gates(usages,dict(facts,imageBase=base))
    erased=ge.observe(metadata['objectComparerEquals']['index'],['System.Type'],[])
    value=norm(dict(schema=SCHEMA,status='validated-conditional-event-ordinary-recycler',nativeInputs=pins,
        proof=dict(imageBase=base,clearSource=clear,poolSource=old,metadata=metadata,packets=p,
            registrations=registrations,closedComparerRegistrationObservations=erased,symbolRvas=symbol_rvas,programs=facts,usages=usages),
        selectedOrdinaryTypedRecyclingEffectsProved=True,ownTypeDictionaryLookupEffectsProved=True,
        canonicalClosedComparerPointerEquivalenceProved=False,liveTypePoolSelectionObserved=False,
        completeEventParamsResetAndDisposalEffectsProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Actual warm registry-hit recycler; own int/Vector3/Entity registrations, slot9 type getter, slot8 base reset and spare Stack.Push; own Type registry chain and RuntimeType hash/reference equality programs.',
            conditional='Canonical corresponding RuntimeType keys and stable handle fields; exact live Type pool registry, typed pool/MethodInfo/vtable contexts; normal ready metadata and disabled collector; spare typed stacks; the actual selected closed System.Type comparer/MethodInfo executes the independently authenticated erased reference equality body, without asserting its comparer subclass or closed pointer equivalence. Other discriminator arms, missing/cold registry and special variables remain separate.',
            unresolved=['EventParams constructor fresh dictionary state and ObjectPool reset/recycle composition','actual pool/class/callback/storage selections and allocation/capacity','runtime event delivery or playback'])))
    validate(value);_publication_gate(image,pins);return value


def scope_tail(packet,base):
    from scripts.game_data.memorypack.leveldata_patrol_event_params_sources import _tail
    return _tail(packet,base)


def validate(value):
    need('own-schema-status',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-event-ordinary-recycler')
    p=value['proof'];base=p['imageBase'];pins=value['nativeInputs'];cleanup.validate(p['clearSource']);pool.validate(p['poolSource'])
    need('same-native-children',p['clearSource']['nativeInputs']==p['poolSource']['nativeInputs']==pins)
    require_metadata(p['metadata'])
    for packet in p['packets'].values():helpers.verify_packet(packet)
    for name in('runtimeHash','runtimeEquals','selfGetter'):
        need('actual-named-callback-packet-'+name,
            p['packets'][name]['entryRva']==p['metadata'][name]['pointerRva'])
    expected=_replay(p['packets'],base,p['symbolRvas'],p['metadata'])
    need('full-recycler-source-replay',norm(expected)==p['programs']);_usage_gates(p['usages'],dict(expected,imageBase=base))
    need('own-three-closed-recyclers',set(p['registrations'])==set(source.programs.KINDS))
    for kind,r in p['registrations'].items():
        for name,method in(('getType',p['metadata']['getType']),('recycle',p['metadata']['recycle'])):
            reg=r[name];target=p['packets']['getType'if name=='getType'else'typedRecycleEntity'if kind=='Beyond.Gameplay.Core.EntityPtr'else'typedRecycleScalar']['entryRva']
            need('own-closed-target-'+kind+name,reg['pointer']==base+target and method['index']in reg['methodDefinitionIndices']
                and reg['classInstantiation']==p['poolSource']['proof']['resets'][kind]['registration']['classInstantiation'])
    need('closed-comparer-observations-never-pointer-alias',isinstance(p['closedComparerRegistrationObservations'],list)
        and value['canonicalClosedComparerPointerEquivalenceProved']is False)
    need('own-actual-parent-recycler',p['packets']['recycler']==p['clearSource']['proof']['packets']['recycleVariable'])
    need('own-actual-base-reset',p['packets']['reset']==p['clearSource']['proof']['packets']['variableRecycle'])
    from_handle=p['clearSource']['proof']['recyclerDescendants'].get(str(p['symbolRvas']['from_handle']))
    need('actual-type-handle-conversion-source-retained',from_handle is not None
        and from_handle['entryRva']==p['symbolRvas']['from_handle'])
    helpers.verify_packet(from_handle)
    need('same-preparation-and-warm-pool-source',p['symbolRvas']['prepare']==p['poolSource']['proof']['storageSource']['proof']['classes']['preparation']['entryRva']
        and p['packets']['singleton']==p['poolSource']['proof']['singleton'])
    need('own-source-only-flags',all(value[k]is True for k in('selectedOrdinaryTypedRecyclingEffectsProved','ownTypeDictionaryLookupEffectsProved'))
        and all(value[k]is False for k in('canonicalClosedComparerPointerEquivalenceProved','liveTypePoolSelectionObserved','completeEventParamsResetAndDisposalEffectsProved','runtimeInvocationObserved','playbackProved')))
    return value
