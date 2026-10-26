"""Actual EventParams Clear/reset source, with ordinary recycler effects separate.

Dictionary enumeration and full byte clearing are independently authenticated.
The selected recycler, constructor and live callback/storage conditions do not
become facts merely because their caller and typed argument are proved here.
"""
import hashlib
import json

from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as source
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as helpers
from scripts.game_data.memorypack import leveldata_patrol_event_params_sources as scope
from scripts.game_data.memorypack import leveldata_patrol_event_cleanup_programs as programs

SCHEMA='endfield.story-patrol-event-cleanup-sources.v1'
BLACKBOARD='Beyond.Gameplay.ParamBlackboard'
VARIABLE='Beyond.Gameplay.ParamVariable'
DICT='System.Collections.Generic.Dictionary`2'
COUNT_LIMIT=4096
BUCKET_LIMIT=8192


def need(check,condition):
    if not condition:raise ValueError('patrolEventCleanupSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def _call(packet,base,offset):return scope._at_call(packet,base,offset)


def _named(ctx,owner,name):
    m=source._single_method(ctx,owner,name,0)
    return dict(index=m.index,owner=owner,name=name,slot=m.slot,
        parameters=source._parameter_type(ctx,m),returns=ctx.type_name(m.return_type),
        pointerRva=ctx.image.method_pointer_va(m)-ctx.image.pe.image_base)


def _metadata(image):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    ctx=NativeReferenceContext(image)
    return dict(eventParent=ctx.type_name(ctx.index.types[scope.EVENT].parent_index),
        blackboardParent=ctx.type_name(ctx.index.types[BLACKBOARD].parent_index),
        fields={n:list(ctx.field(BLACKBOARD+'::'+n))for n in('variableDict','subBlackboardRefDict')},
        methods={n:_named(ctx,BLACKBOARD,n)for n in('Clear','_ClearVariables','OnAllocate')},
        reusableRecycle=_named(ctx,'Beyond.ReusableObject','OnRecycle'),
        variableRecycle=_named(ctx,VARIABLE,'OnRecycle'))


def require_metadata(value):
    need('own-base-hierarchy',value['eventParent']==BLACKBOARD and value['blackboardParent']=='Beyond.ReusableObject')
    need('own-two-blackboard-dictionaries',value['fields']==dict(
        variableDict=[BLACKBOARD,DICT+'<string,'+VARIABLE+'>',40],
        subBlackboardRefDict=[BLACKBOARD,DICT+'<string,'+BLACKBOARD+'>',48]))
    for key,slot in(('Clear',10),('_ClearVariables',65535),('OnAllocate',7)):
        m=value['methods'][key]
        need('own-method-'+key,(m['owner'],m['name'],m['slot'],m['parameters'],m['returns'])==(BLACKBOARD,key,slot,[],'void'))
    for key,owner in(('reusableRecycle','Beyond.ReusableObject'),('variableRecycle',VARIABLE)):
        m=value[key];need('own-reset-method-'+key,
            (m['owner'],m['name'],m['slot'],m['parameters'],m['returns'])==(owner,'OnRecycle',8,[],'void'))
    return value


def _replay(p,base,symbols):
    r=lambda n:helpers.regions(p[n],base)
    e=lambda n:base+p[n]['entryRva']
    s={k:base+v for k,v in symbols.items()}
    return dict(clear=programs.blackboard_clear_program(r('clear'),e('clear'),
            clear_variables=e('clearVariables'),clear_dictionary=e('dictionaryClear')),
        variables=programs.clear_variable_paths(r('clearVariables'),e('clearVariables'),barrier=s['barrier'],
            move_next=e('moveNext'),assignable=e('assignable'),recycle=e('recycleVariable'),
            clear_dictionary=e('dictionaryClear'),count_limit=COUNT_LIMIT),
        moveNext=programs.dictionary_enumerator_paths(r('moveNext'),e('moveNext'),
            context_type=s['context_type'],count_limit=COUNT_LIMIT),
        dictionaryClear=[programs.dictionary_clear_program(r('dictionaryClear'),e('dictionaryClear'),
            fill=s['fill'],positive=v)for v in(False,True)],
        notAssignable=[programs.ordinary_not_assignable_program(r('assignable'),e('assignable'),
            prepare=s['prepare'],shallower=v)for v in(False,True)],
        blackboardAllocate=programs.blackboard_allocate_program(r('blackboardAllocate'),e('blackboardAllocate'),barrier=s['barrier']),
        reusableRecycle=programs.reusable_recycle_program(r('reusableRecycle'),e('reusableRecycle')),
        variableRecycle=programs.variable_recycle_reset_program(r('variableRecycle'),e('variableRecycle')))


def _require_usages(usages,progs,packets,base):
    expected=(('moveNext',DICT+'+Enumerator','MoveNext',['string',VARIABLE]),
        ('variableClear',DICT,'Clear',['string',VARIABLE]),('subdictionaryClear',DICT,'Clear',['string',BLACKBOARD]))
    for key,owner,name,args in expected:
        u=usages[key]
        need('own-closed-context-'+key,u['typeName']==owner and u['methodName']==name
            and u['classArguments']==args and u['methodArguments']==[]and len(u['methodSpec'])==3)
    last=progs['variables']['witnesses'][-1]
    for key,expected_name,site in(
        ('excludedGlobal','Beyond.Gameplay.ParamVariableFromGlobalVar',last['excludedGlobalVariableClassSiteVa']),
        ('excludedMap','Beyond.Gameplay.ParamVariableFromMapVar',last['excludedMapVariableClassSiteVa'])):
        u=usages[key];need('own-excluded-ordinary-class-'+key,u['typeName']==expected_name and u['instructionRva']==site-base)
    sites=dict(moveNext=last['moveNextMethodInfoSiteVa'],variableClear=last['dictionaryClearMethodInfoSiteVa'],
        subdictionaryClear=progs['clear']['subdictionaryMethodInfoSiteVa'])
    for key,at in sites.items():need('same-actual-context-site-'+key,usages[key]['instructionRva']==at-base)


def _validate_fill(fill,pins,base,target):
    from scripts.game_data.il2cpp import byte_fill_sources
    from scripts.game_data.il2cpp.fill_instructions import decode_fill_instructions
    from scripts.game_data.il2cpp.protocol import load_native_mapper
    from scripts.repo_paths import REPO_ROOT
    need('own-neutral-fill-domain',fill['schema']=='endfield.byte-fill-source.v1'and fill['nativeInputs']==pins
        and fill['entryRva']==target-base and fill['maxBytes']==max(BUCKET_LIMIT*4,COUNT_LIMIT*24))
    p=fill['proof'];regions=[(a,bytes.fromhex(h))for a,h in p['sourceRegions']]
    need('full-fill-windows',len(regions)==len(p['sourceWindows'])and all(
        w['startRva']==a-base and w['endRva']==a-base+len(raw)and w['sha256']==hashlib.sha256(raw).hexdigest().upper()
        for(a,raw),w in zip(regions,p['sourceWindows'])))
    rep=p['repReachablePrefix'];rep_raw=bytes.fromhex(rep['rawHex'])
    need('full-rep-prefix',rep['endRva']-rep['startRva']==len(rep_raw)
        and rep['sha256']==hashlib.sha256(rep_raw).hexdigest().upper())
    tables={}
    for t in p['tables']:
        raw=bytes.fromhex(t['rawHex']);need('full-fill-table',t['endRva']-t['startRva']==len(raw)
            and t['sha256']==hashlib.sha256(raw).hexdigest().upper());tables[t['startRva']]=raw
    mapper=load_native_mapper(REPO_ROOT/'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py')
    rows=[r for a,raw in regions for r in decode_fill_instructions(mapper,raw,a)]
    rep_regions=[(base+rep['startRva'],rep_raw)]
    result=byte_fill_sources.prove(regions,target,rows=rows,table_bytes=tables,rep_regions=rep_regions,
        rep_rows=decode_fill_instructions(mapper,rep_raw,rep_regions[0][0]),image_base=base,max_bytes=fill['maxBytes'])
    need('full-fill-program-replay',norm(result)==p['program'])
    need('no-typed-domain-or-capacity-promotion',result['typedCallerDomainImported']is False
        and result['allocationSuccessOrValidCapacityProved']is False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp import byte_fill_sources
    _publication_gate(image,pins);parent=scope.derive(image,pins);base=image.pe.image_base
    metadata=require_metadata(_metadata(image));p={}
    for key,m in(('clear',metadata['methods']['Clear']),('clearVariables',metadata['methods']['_ClearVariables']),
        ('blackboardAllocate',metadata['methods']['OnAllocate']),('reusableRecycle',metadata['reusableRecycle']),
        ('variableRecycle',metadata['variableRecycle'])):
        p[key]=source._body(image,base+m['pointerRva'])
    # Sites below are independently consumed by the complete byte programs.
    p['moveNext']=source._body(image,_call(p['clearVariables'],base,412))
    p['assignable']=source._body(image,_call(p['clearVariables'],base,459))
    p['recycleVariable']=source._body(image,_call(p['clearVariables'],base,2501))
    p['dictionaryClear']=source._body(image,_call(p['clearVariables'],base,2547))
    symbols=dict(barrier=_call(p['clearVariables'],base,291),
        context_type=_call(p['moveNext'],base,142),prepare=_call(p['assignable'],base,109),
        fill=_call(p['dictionaryClear'],base,246))
    symbol_rvas={k:v-base for k,v in symbols.items()};facts=_replay(p,base,symbol_rvas)
    last=facts['variables']['witnesses'][-1];sites=dict(moveNext=last['moveNextMethodInfoSiteVa'],
        variableClear=last['dictionaryClearMethodInfoSiteVa'],subdictionaryClear=facts['clear']['subdictionaryMethodInfoSiteVa'],
        excludedGlobal=last['excludedGlobalVariableClassSiteVa'],excludedMap=last['excludedMapVariableClassSiteVa'])
    usages={k:derive_typed_usage_context(image,at-base,label='patrolEventCleanup.'+k)for k,at in sites.items()}
    _require_usages(usages,facts,p,base)
    fill=byte_fill_sources.derive(image,pins,entry=symbols['fill'],max_bytes=max(BUCKET_LIMIT*4,COUNT_LIMIT*24))
    # Retain exact actual descendants for the separate typed recycler join.
    descendants={}
    for at,target in source._calls(p['recycleVariable'],base):
        if target not in descendants:
            try:descendants[target-base]=source._body(image,target)
            except(ValueError,KeyError,RuntimeError):
                from scripts.game_data.memorypack.leveldata_patrol_checkpoint_storage_sources import _fixed_prefix
                descendants[target-base]=_fixed_prefix(image,target,256)
    value=norm(dict(schema=SCHEMA,status='validated-conditional-event-cleanup-callers',nativeInputs=pins,
        proof=dict(imageBase=base,scopeSource=parent,metadata=metadata,packets=p,symbolRvas=symbol_rvas,
            programs=facts,usages=usages,byteFill=fill,recyclerDescendants=descendants),
        countLimit=COUNT_LIMIT,bucketLengthLimit=BUCKET_LIMIT,selectedClearAndEnumerationProgramsProved=True,
        completeDictionaryClearByteEffectsProved=True,ordinaryValueRecyclerEffectsProved=False,
        completeEventParamsResetAndDisposalEffectsProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Actual named slot10 Clear and _ClearVariables; own closed dictionary/enumerator contexts; count/entry/frame loops; full buckets and used entries byte-fill; base reset/recycle stores.',
            conditional='Warm metadata, original replacement selection, both dictionaries nonnull, valid stable one-dimensional zero-based arrays with own4/24 component sizes; count within4096 and bucket length within8192; disabled collector; ordinary values outside GlobalVar/MapVar; selected normal recycler preserves the enumerated dictionary.',
            unresolved=['ordinary typed variable recycler/registry/pool callback effects','constructor state and selected EventParams ObjectPool reset/recycle effects','actual allocation/capacity and live pool/callback/storage selection','runtime event delivery and playback'])))
    validate(value);_publication_gate(image,pins);return value


def validate(value):
    need('own-schema-status',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-event-cleanup-callers')
    p=value['proof'];scope.validate(p['scopeSource']);base=p['imageBase'];pins=value['nativeInputs']
    need('same-fresh-scope',p['scopeSource']['nativeInputs']==pins and p['scopeSource']['proof']['imageBase']==base)
    require_metadata(p['metadata'])
    for packet in list(p['packets'].values())+list(p['recyclerDescendants'].values()):helpers.verify_packet(packet)
    packets=p['packets'];m=p['metadata'];s={k:base+v for k,v in p['symbolRvas'].items()}
    for key,method in(('clear',m['methods']['Clear']),('clearVariables',m['methods']['_ClearVariables']),
        ('blackboardAllocate',m['methods']['OnAllocate']),('reusableRecycle',m['reusableRecycle']),('variableRecycle',m['variableRecycle'])):
        need('own-method-entry-'+key,packets[key]['entryRva']==method['pointerRva'])
    expected=_replay(packets,base,p['symbolRvas']);need('full-cleanup-program-replay',norm(expected)==p['programs'])
    _require_usages(p['usages'],expected,packets,base)
    _validate_fill(p['byteFill'],pins,base,s['fill'])
    need('bounded-own-table-domain',value['countLimit']==COUNT_LIMIT and value['bucketLengthLimit']==BUCKET_LIMIT)
    need('no-callee-or-runtime-promotion',all(value[k]is True for k in('selectedClearAndEnumerationProgramsProved','completeDictionaryClearByteEffectsProved'))
        and all(value[k]is False for k in('ordinaryValueRecyclerEffectsProved','completeEventParamsResetAndDisposalEffectsProved','runtimeInvocationObserved','playbackProved')))
    return value
