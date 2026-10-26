"""Own Event/dictionary constructor and explicit object payload-fill paths.

This proves selected source, not a live allocator result. Other class-flag
allocation branches and factory/Activator selection are kept distinct.
"""
import hashlib
import json

from scripts.game_data.memorypack import leveldata_patrol_event_pool_sources as parent_owner
from scripts.game_data.memorypack import leveldata_patrol_event_initialization_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as source
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as helpers
from scripts.game_data.memorypack import leveldata_patrol_pool_dispatch_programs as dispatch
from scripts.game_data.memorypack import leveldata_patrol_event_params_sources as scope
from scripts.game_data.memorypack import leveldata_patrol_event_cleanup_sources as cleanup

SCHEMA='endfield.story-patrol-event-initialization-sources.v1'
INSTANCE_SIZES=tuple(range(64,257,8))


def need(check,condition):
    if not condition:raise ValueError('patrolEventInitializationSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def _metadata(image):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    ctx=NativeReferenceContext(image);result={}
    for key,owner in(('event',scope.EVENT),('blackboard',cleanup.BLACKBOARD),('dictionary',cleanup.DICT)):
        method=source._single_method(ctx,owner,'.ctor',0);pointer=image.method_pointer_va(method)
        result[key]=dict(index=method.index,owner=owner,name='.ctor',parameters=source._parameter_type(ctx,method),
            returns=ctx.type_name(method.return_type),pointerRva=pointer-image.pe.image_base if pointer else None,
            valueType=ctx.is_value_type(owner))
    return result


def require_metadata(m):
    for key,owner in(('event',scope.EVENT),('blackboard',cleanup.BLACKBOARD),('dictionary',cleanup.DICT)):
        d=m[key];need('own-reference-constructor-'+key,(d['owner'],d['name'],d['parameters'],d['returns'],d['valueType'])==(owner,'.ctor',[],'void',False))
    return m


def _replay(p,base,symbols):
    r=lambda n:helpers.regions(p[n],base);e=lambda n:base+p[n]['entryRva'];s={k:base+v for k,v in symbols.items()}
    return dict(objectNew=[programs.object_new_program(r('objectNew'),e('objectNew'),ready=e('ready'),
            allocate=e('rawAllocate'),fill=s['fill'],class_init=e('classInit'),instance_bytes=n,generic_class=g)
            for n in INSTANCE_SIZES for g in(False,True)],
        ready=dispatch.ready_type_program(r('ready'),e('ready')),
        classInit=programs.initialized_class_program(r('classInit'),e('classInit')),
        dictionaryCtor=programs.dictionary_ctor_program(r('dictionaryCtor'),e('dictionaryCtor'),default_comparer=e('comparerFactory')),
        blackboardCtor=programs.blackboard_ctor_program(r('blackboardCtor'),e('blackboardCtor'),
            object_new=e('objectNew'),dictionary_ctor=e('dictionaryCtor'),barrier=s['barrier']),
        eventCtor=programs.event_ctor_program(r('eventCtor'),e('eventCtor'),base_ctor=e('blackboardCtor')))


def _usage_gates(usages,facts,metadata,base):
    for index,kind in enumerate((cleanup.VARIABLE,cleanup.BLACKBOARD)):
        c=usages['class'+str(index)];u=usages['ctor'+str(index)]
        need('own-dictionary-allocation-class-'+str(index),c['tag']==1 and c['typeName']==cleanup.DICT+'<string,'+kind+'>')
        need('own-dictionary-constructor-MethodSpec-'+str(index),u['tag']==6 and u['typeName']==cleanup.DICT
            and u['methodName']=='.ctor'and u['methodSpec'][0]==metadata['dictionary']['index']
            and u['classArguments']==['string',kind]and u['methodArguments']==[])
        row=facts['blackboardCtor']['dictionaries'][index]
        need('actual-dictionary-constructor-sites-'+str(index),c['instructionRva']==row['classSiteVa']-base
            and u['instructionRva']==row['constructorMethodInfoSiteVa']-base)


def _fill_replay(value,pins,base,target):
    from scripts.game_data.il2cpp import byte_fill_sources
    from scripts.game_data.il2cpp.fill_instructions import decode_fill_instructions
    from scripts.game_data.il2cpp.protocol import load_native_mapper
    from scripts.repo_paths import REPO_ROOT
    need('own-object-payload-fill-domain',value['schema']=='endfield.byte-fill-source.v1'and value['nativeInputs']==pins
        and value['entryRva']==target-base and value['maxBytes']==max(INSTANCE_SIZES)-16)
    p=value['proof'];regions=[(a,bytes.fromhex(h))for a,h in p['sourceRegions']]
    need('complete-object-fill-windows',len(regions)==len(p['sourceWindows'])and all(
        w['startRva']==a-base and w['endRva']==a-base+len(raw)and w['sha256']==hashlib.sha256(raw).hexdigest().upper()
        for(a,raw),w in zip(regions,p['sourceWindows'])))
    tables={}
    for table in p['tables']:
        raw=bytes.fromhex(table['rawHex']);need('complete-object-fill-table',table['endRva']-table['startRva']==len(raw)
            and table['sha256']==hashlib.sha256(raw).hexdigest().upper());tables[table['startRva']]=raw
    rep=p['repReachablePrefix'];raw=bytes.fromhex(rep['rawHex']);need('complete-object-fill-rep',
        rep['endRva']-rep['startRva']==len(raw)and rep['sha256']==hashlib.sha256(raw).hexdigest().upper())
    mapper=load_native_mapper(REPO_ROOT/'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py')
    rows=[row for a,b in regions for row in decode_fill_instructions(mapper,b,a)]
    rep_regions=[(base+rep['startRva'],raw)]
    expected=byte_fill_sources.prove(regions,target,rows=rows,table_bytes=tables,rep_regions=rep_regions,
        rep_rows=decode_fill_instructions(mapper,raw,rep_regions[0][0]),image_base=base,max_bytes=value['maxBytes'])
    need('full-own-object-fill-program-replay',norm(expected)==p['program']
        and expected['typedCallerDomainImported']is False and expected['allocationSuccessOrValidCapacityProved']is False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp import byte_fill_sources
    _publication_gate(image,pins);parent=parent_owner.derive(image,pins);base=image.pe.image_base;metadata=require_metadata(_metadata(image))
    p={};p['blackboardCtor']=source._body(image,base+metadata['blackboard']['pointerRva'])
    p['eventCtor']=source._leaf(image,base+metadata['event']['pointerRva'],programs.event_ctor_program,
        base_ctor=base+metadata['blackboard']['pointerRva'])
    p['objectNew']=source._body(image,scope._at_call(p['blackboardCtor'],base,50))
    p['dictionaryCtor']=source._body(image,scope._at_call(p['blackboardCtor'],base,73))
    p['rawAllocate']=source._body(image,scope._at_call(p['objectNew'],base,54))
    p['ready']=source._body(image,scope._at_call(p['objectNew'],base,10))
    p['classInit']=source._body(image,scope._at_call(p['objectNew'],base,964))
    p['comparerFactory']=source._body(image,scope._at_call(p['dictionaryCtor'],base,82))
    symbols=dict(fill=scope._at_call(p['objectNew'],base,132),barrier=scope._at_call(p['blackboardCtor'],base,38))
    symbol_rvas={k:v-base for k,v in symbols.items()};facts=_replay(p,base,symbol_rvas)
    sites={}
    for index,row in enumerate(facts['blackboardCtor']['dictionaries']):
        sites['class'+str(index)]=row['classSiteVa'];sites['ctor'+str(index)]=row['constructorMethodInfoSiteVa']
    usages={k:derive_typed_usage_context(image,at-base,label='patrolEventInitialization.'+k)for k,at in sites.items()}
    _usage_gates(usages,facts,metadata,base)
    fill=byte_fill_sources.derive(image,pins,entry=symbols['fill'],max_bytes=max(INSTANCE_SIZES)-16)
    value=norm(dict(schema=SCHEMA,status='validated-conditional-event-constructor-initialization',nativeInputs=pins,
        proof=dict(imageBase=base,eventPoolSource=parent,metadata=metadata,packets=p,symbolRvas=symbol_rvas,
            programs=facts,usages=usages,byteFill=fill,selectedInstanceBytes=list(INSTANCE_SIZES),
            rawAllocationPrimitiveEffectsProved=False),
        selectedConstructorAndPayloadInitializationProgramsProved=True,
        allocatorZeroStateAssumed=False,actualWritableAllocationCapacityProved=False,
        allObjectAllocationClassFlagBranchesProved=False,actualFactoryOrActivatorConstructorInvocationProved=False,
        runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Actual named Event/base constructors and both separately typed dictionary allocations; header stores and whole payload explicit zero-fill in the selected object allocator branch; ready class helpers preserve the initialized object.',
            conditional='Own selected closed runtime class/MethodInfo and constructor invocation, aligned finite instance size covering all consumed fields, exact normal class-flag predicates, disabled collector/profiling, already initialized class and successful disjoint writable raw allocation. No payload zero-state is assumed from the raw allocator.',
            unresolved=['other object allocation class-flag branches','actual pool factory/Activator selection and invocation of the independently proved constructors','actual allocation capacity/success and live class/pool/callback state','runtime delivery and playback'])))
    validate(value);_publication_gate(image,pins);return value


def validate(value):
    need('own-schema-status',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-event-constructor-initialization')
    p=value['proof'];parent=p['eventPoolSource'];parent_owner.validate(parent);base=p['imageBase'];pins=value['nativeInputs']
    need('same-native-parent',parent['nativeInputs']==pins and parent['proof']['imageBase']==base)
    require_metadata(p['metadata'])
    for packet in p['packets'].values():helpers.verify_packet(packet)
    need('own-named-constructor-targets',all(p['packets'][packet]['entryRva']==p['metadata'][key]['pointerRva']
        for packet,key in(('eventCtor','event'),('blackboardCtor','blackboard'))))
    expected=_replay(p['packets'],base,p['symbolRvas']);need('all-constructor-and-fill-source-replay',norm(expected)==p['programs'])
    _usage_gates(p['usages'],expected,p['metadata'],base)
    _fill_replay(p['byteFill'],pins,base,base+p['symbolRvas']['fill'])
    need('own-size-domain',p['selectedInstanceBytes']==list(INSTANCE_SIZES)and p['rawAllocationPrimitiveEffectsProved']is False)
    ready=parent['proof']['packets']['readyType'];need('same-actual-ready-class-helper',p['packets']['ready']==ready)
    need('same-actual-warm-comparer-source',p['packets']['comparerFactory']==parent['proof']['recyclerSource']['proof']['packets']['factory'])
    need('same-actual-disabled-barrier-target',p['symbolRvas']['barrier']==parent['proof']['recyclerSource']['proof']['clearSource']['proof']['symbolRvas']['barrier'])
    old=parent['proof']['recyclerSource']['proof']['poolSource']['proof']['actualObjectAllocator']
    need('same-actual-retained-object-allocator',p['packets']['objectNew']==old)
    need('exact-selected-initialization-boundary',value['selectedConstructorAndPayloadInitializationProgramsProved']is True
        and all(value[k]is False for k in('allocatorZeroStateAssumed','actualWritableAllocationCapacityProved',
            'allObjectAllocationClassFlagBranchesProved','actualFactoryOrActivatorConstructorInvocationProved','runtimeInvocationObserved','playbackProved')))
    return value
