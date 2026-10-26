"""Current named-role supersession of historical anonymous Buff catalogs.

Legacy schemaVersion1 files and their decoders are left untouched. A candidate
names the exact current source methods, field reads and reached normative
consumer for every owner. Admission requires a callable native source projection
and an active, independently validated CurrentSequence operation on the same
selected files. Neither a saved report nor a candidate status is authority.
"""
import json
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA='endfield.buff-catalog-current-roles-native.v1'
SOURCE_ROLES_SCHEMA='endfield.current-catalog-native-source-roles.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_catalog_current_roles_native.json'
READ_KEYS=('memberIndex','fieldName','declaredType','kind','mode','wireBytes','managedBytes','readMethod',
    'instruction','sourceTargetRva','sourceContextMode','context')
CONSUMER_KEYS=('family','currentTag','routeKey','topLevelWrapper','consumerKind','memberCount',
    'actualOrderedReads','capability','capabilityPath','nestedFamily','nestedTag')


def need(check,condition,detail=None):
    if not condition:raise ValueError('catalogCurrentRoles.'+check+':'+str(detail)[:900])


def _identity(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def source_claim(source):
    from scripts.game_data.memorypack.catalog_source_review import _source_windows
    general=source.get('sourceKind')=='complete-general-source'
    need('complete-selected-source',general and source.get('allFourCallerPathsProved')is True
        or not general and source.get('completeSelectedSourceAdmitted')is True and source.get('nativeAttributionProved')is True)
    methods=source.get('sourceMethods',[]);wrapper=source.get('wrapperName');original=source.get('wrappedType')
    need('literal-source-identities',isinstance(wrapper,str)and wrapper and isinstance(original,str)and original
        and isinstance(methods,list)and methods and all(isinstance(m,list)and len(m)==4
            and type(m[0])is int and m[0]>=0 and isinstance(m[1],str)and isinstance(m[2],str)
            and type(m[3])is int and m[3]>0 for m in methods)
        and any(m[1:3]==[wrapper,'Deserialize']for m in methods))
    reads=source.get('orderedSourceReads',[])
    if general:
        need('ordered-named-source-roles',isinstance(reads,list)
            and [r.get('memberIndex')for r in reads]==list(range(len(reads)))
            and all(isinstance(r.get('fieldName'),str)and r['fieldName']and isinstance(r.get('declaredType'),str)
                and r['declaredType']and isinstance(r.get('kind'),str)and r['kind']for r in reads))
    roles=[{k:r[k]for k in READ_KEYS if k in r}for r in reads]
    return dict(wrapperName=wrapper,wrappedType=original,sourceClass='general'if general else'dedicated-domain',
        sourceMethods=methods,codeWindows=_source_windows(source.get('codeWindows')),namedReadRoles=roles,
        maintainedOwner=source.get('maintainedOwner'),
        originalIsValueType=False if general else source.get('genericReferenceReaderApplicable')is False,
        sourceChildGrammarGranted=False)


def consumer_claim(consumer):
    need('closed-current-normative-consumer',consumer.get('routeClosurePresent')is True
        and not consumer.get('missingCapabilities')and not consumer.get('incompleteCapabilities')
        and type(consumer.get('currentTag'))is int and isinstance(consumer.get('family'),str)
        and consumer.get('routeKey')==consumer['family']+':'+str(consumer['currentTag'])
        and consumer.get('historicalTagUsed')is False)
    return{k:consumer[k]for k in CONSUMER_KEYS if k in consumer}


def prepare_candidate(review):
    from scripts.game_data.memorypack.catalog_source_review import SCHEMA as REVIEW_SCHEMA
    need('current-source-review',review.get('schema')==REVIEW_SCHEMA and isinstance(review.get('nativeInputs'),dict)
        and bool(review['nativeInputs'])and isinstance(review.get('catalogs'),list))
    owners={};catalogs=[];held=[]
    for catalog in review['catalogs']:
        if catalog.get('status')!='current-source-and-consumer-review-candidate':
            held.append(dict(contract=catalog['contract'],owners=[dict(wrapperName=o['wrapperName'],
                remainingJoins=o['concreteRemainingJoins'])for o in catalog['exactOwners']if o['concreteRemainingJoins']]))
            continue
        selected=[]
        for owner in catalog['exactOwners']:
            need('no-open-owned-join',owner.get('concreteRemainingJoins')==[])
            source=source_claim(owner['currentSource']);name=source['wrapperName']
            matches=[c for c in owner.get('currentConsumers',[])if c.get('routeClosurePresent')is True]
            need('one-or-more-exact-current-consumers',bool(matches),name)
            matches.sort(key=lambda c:(c.get('consumerKind')!='current-normative-program',
                len(c.get('capabilityPath',[])),c.get('routeKey',''),c.get('capability','')))
            current=consumer_claim(matches[0])
            claim=dict(source=source,consumer=current)
            if name in owners:need('consistent-shared-owner-source',owners[name]['source']==source,name)
            else:owners[name]=claim
            selected.append(name)
        catalogs.append(dict(legacyContract=catalog['contract'],sourceOwners=selected,
            disposition='superseded-by-current-named-source-and-consumer-roles',
            oldAnonymousWindowAttributionClaimed=False,legacyContractModified=False,legacyDecoderActivated=False))
    return json.loads(json.dumps(dict(schema=SCHEMA,status='pending-native-role-validation',nativeInputs=review['nativeInputs'],
        owners=[owners[name]for name in sorted(owners)],catalogs=catalogs,held=held,
        catalogScopeCount=len(review['catalogs']),nativeOperationAuthenticated=False,nativeAdmissionGranted=False,
        nativeValidationRequired=True,catalogsAdmitted=0,
        evidenceBoundary=__doc__)))


def _native_identity(image,pins,claim):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    source=claim['source'];name=source['wrapperName'];base=image.pe.image_base
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==name]
    need('same-actual-wrapper-original',wrapper.wrapped_type==source['wrappedType'],name)
    ctx=NativeReferenceContext(image)
    need('same-reference-value-original-kind',ctx.is_value_type(wrapper.wrapped_type)is source['originalIsValueType'],name)
    for method in source['sourceMethods']:image.validate_method_row(method,label='catalogCurrentRoles.'+name)
    image.check_windows(source['codeWindows'],label='catalogCurrentRoles.'+name)
    roles=source['namedReadRoles']
    if source['sourceClass']=='general':
        need('same-actual-ordered-wrapper-members',[(m.name,m.declared_type)for m in wrapper.members]
            ==[(r['fieldName'],r['declaredType'])for r in roles],name)
    for role in roles:
        instruction=role.get('instruction')
        if instruction:
            image.check_instruction_windows([instruction],label='catalogCurrentRoles.read.'+name)
            at,encoded=instruction;raw=bytes.fromhex(encoded)
            need('read-in-owned-source-window',any(w['startRva']<=at and at+len(raw)<=w['endRva']for w in source['codeWindows']))
            if len(raw)==5 and raw[0]==0xe8:
                need('same-actual-read-call-target',role.get('sourceTargetRva')==at+5+int.from_bytes(raw[1:],'little',signed=True))
        context=role.get('context')
        if context:
            actual=derive_typed_usage_context(image,context['instructionRva'],label='catalogCurrentRoles.context.'+name)
            need('same-actual-typed-read-context',actual['instructionHex']==context['instructionHex']
                and actual.get('methodSpec')==context.get('methodSpec')
                and actual.get('methodName')==context.get('methodName')
                and actual.get('typeName')==context.get('methodOwner'),(name,role['fieldName']))


def _general_roles_from_graph(provenance,pins,requested):
    """Select source semantics from an already validated operation's graph.

    Only requested source objects and their role fields are decoded. Omitted
    instruction traces are neither expanded nor treated as newly replayed code.
    The public operation authenticates this graph before it reaches this helper.
    """
    from scripts.game_data.memorypack.catalog_source_review import SOURCE_SCHEMA,complete_sources
    from scripts.game_data.memorypack.skill_contract_provenance import SCHEMA as PROVENANCE_SCHEMA
    need('validated-semantic-provenance-shape',isinstance(provenance,dict)
        and provenance.get('schema')==PROVENANCE_SCHEMA and provenance.get('nativeAdmissionGranted')is False
        and provenance.get('fullInstructionTracesRetained')is False
        and all(isinstance(provenance.get(k),list)for k in('nodes','nativeCodeWindows','metadataMethods')))
    nodes=provenance['nodes']
    def node(ref,kind):
        need('semantic-node-reference',isinstance(ref,dict)and set(ref)=={'$node'}
            and type(ref['$node'])is int and 0<=ref['$node']<len(nodes))
        value=nodes[ref['$node']];need('semantic-node-kind',isinstance(value,dict)and value.get('kind')==kind)
        if kind=='array':
            need('semantic-array-items',isinstance(value.get('items'),list));return value['items']
        pairs=value.get('members');need('semantic-object-members',isinstance(pairs,list)
            and all(isinstance(p,list)and len(p)==2 and isinstance(p[0],str)for p in pairs)
            and [p[0]for p in pairs]==sorted(set(p[0]for p in pairs)))
        return dict(pairs)
    def decode(value,depth=0,ancestors=()):
        need('bounded-selected-semantic-depth',depth<=128)
        if not isinstance(value,dict):
            need('selected-semantic-scalar',value is None or type(value)in(str,int,float,bool));return value
        if '$node'in value:
            index=value['$node'];need('acyclic-selected-semantic-node',index not in ancestors)
            kind=nodes[index].get('kind')if type(index)is int and 0<=index<len(nodes)else None
            selected=node(value,kind);trail=ancestors+(index,)
            if kind=='array':return[decode(v,depth+1,trail)for v in selected]
            return{k:decode(v,depth+1,trail)for k,v in selected.items()}
        if '$window'in value:
            index=value['$window'];rows=provenance['nativeCodeWindows']
            need('selected-semantic-window',set(value)<={'$window','boundary'}and type(index)is int and 0<=index<len(rows))
            return{k:rows[index][k]for k in('startRva','endRva','sha256')}
        if '$method'in value:
            index=value['$method'];rows=provenance['metadataMethods']
            need('selected-semantic-method',set(value)=={'$method'}and type(index)is int and 0<=index<len(rows))
            return json.loads(json.dumps(rows[index]))
        need('no-omitted-trace-as-source-role',False,value)
    selected={}
    for index,value in enumerate(nodes):
        if not isinstance(value,dict)or value.get('kind')!='object':continue
        raw=value.get('members',[])
        if not isinstance(raw,list)or not all(isinstance(p,list)and len(p)==2 for p in raw):continue
        fields=dict(raw)
        if fields.get('schema')!=SOURCE_SCHEMA or fields.get('wrapperName')not in requested:continue
        fields=node({'$node':index},'object')
        proof={k:decode(fields[k])for k in('schema','nativeInputs','wrapperName','wrappedType',
            'completeSelectedCallerAdmitted','childGrammarAdmitted','method','codeWindows')}
        proof['programs']=[]
        for item in node(fields['programs'],'array'):
            program=node(item,'object');frame=node(program['frame'],'object')
            proof['programs'].append({**{k:decode(program[k])for k in('existing','wrapperNull')},
                'frame':{k:decode(frame[k])for k in('entryRspRestored','allWin64IntegerNonvolatilesRestored')}})
        proof['orderedSourceReads']=[]
        for item in node(fields['orderedSourceReads'],'array'):
            read=node(item,'object');proof['orderedSourceReads'].append({k:decode(read[k])for k in READ_KEYS if k in read})
        for name,source in complete_sources(proof,pins).items():
            claim=source_claim(source)
            need('consistent-native-provenance-source-roles',name not in selected or _identity(selected[name])==_identity(claim),name)
            selected[name]=claim
    return selected


def source_role_prover(*,absent_source_prover=None):
    """Reuse active native source semantics, deriving only absent owned sources.

    The optional fallback is maintained code, not a callback declared by JSON.
    It returns freshly proved source rows under the existing explicit replay
    vocabulary. No saved report can supply the operation provenance argument.
    """
    need('callable-absent-source-prover',absent_source_prover is None or callable(absent_source_prover))
    def prove(image,pins,claims,*,validated_provenance):
        requested={r['wrapperName']:r for r in claims}
        reused=_general_roles_from_graph(validated_provenance,pins,
            {name for name,row in requested.items()if row.get('sourceClass')=='general'})
        missing=[r for r in claims if r['wrapperName']not in reused];fresh={}
        if missing:
            need('fresh-prover-for-absent-owned-sources',callable(absent_source_prover),[r['wrapperName']for r in missing])
            result=absent_source_prover(image,pins,missing)
            need('complete-absent-native-source-replay',isinstance(result,dict)and result.get('nativeInputs')==pins
                and result.get('sourceProgramSemanticsReproved')is True and isinstance(result.get('sources'),list))
            for source in result['sources']:
                row=source_claim(source);name=row['wrapperName']
                need('distinct-absent-source-replay',name not in fresh,name);fresh[name]=row
            need('all-and-only-absent-native-sources',set(fresh)=={r['wrapperName']for r in missing})
        rows={**reused,**fresh}
        return dict(schema=SOURCE_ROLES_SCHEMA,nativeInputs=dict(pins),nativeSourceRoleProjectionProved=True,
            sourceRoles=[rows[r['wrapperName']]for r in claims],activeSemanticProvenanceOwners=sorted(reused),
            freshlyDerivedSourceOwners=sorted(fresh),allSourceProgramsReplayed=False)
    return prove


def validate_on_image(image,pins,candidate,*,source_prover,operation):
    """Validate roles inside one active, independently proved public operation.

    ``source_prover`` is code selected by the maintained native driver, never a
    JSON rule. It projects source roles from the active native graph, freshly
    deriving absent owners. Source flags in the candidate cannot provide the
    gated provenance or select a prover.
    """
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.skill_timeline_current_sequence_native import prepared_current_sequence
    from scripts.game_data.memorypack.catalog_source_review import consumer_index
    need('candidate-schema-and-pins',candidate.get('schema')==SCHEMA and candidate.get('status')in('pending-native-role-validation','exact-current-build')
        and candidate.get('nativeInputs')==pins and bool(pins)
        and candidate.get('nativeAdmissionGranted')is False and candidate.get('nativeValidationRequired')is True)
    catalogs=candidate.get('catalogs',[])
    need('complete-distinct-declared-catalog-scope',isinstance(catalogs,list)and bool(catalogs)
        and candidate.get('held')==[] and type(candidate.get('catalogScopeCount'))is int
        and candidate['catalogScopeCount']==len(catalogs)
        and all(isinstance(c,dict)and isinstance(c.get('legacyContract'),str)and c['legacyContract']for c in catalogs)
        and len({c['legacyContract']for c in catalogs})==len(catalogs))
    need('callable-native-source-prover',callable(source_prover))
    _publication_gate(image,pins);active=prepared_current_sequence(operation);current=active.proof
    need('same-active-native-operation',current.get('status')=='validated'and current.get('nativeInputs')==pins
        and current.get('nativeSources',{}).get('GameAssembly.dll')==str(image.gameassembly.resolve())
        and current.get('nativeSources',{}).get('global-metadata.dat')==str(image.metadata_path.resolve()))
    need('active-public-source-provenance-gate',callable(getattr(active,'source_provenance',None)))
    provenance=active.source_provenance()
    claims=candidate.get('owners',[]);names=[r.get('source',{}).get('wrapperName')for r in claims]
    need('finite-distinct-owned-source-claims',0<len(names)<=1024 and len(names)==len(set(names))and all(isinstance(n,str)and n for n in names))
    replay=source_prover(image,pins,[r['source']for r in claims],validated_provenance=provenance)
    need('complete-native-source-role-projection',isinstance(replay,dict)and replay.get('schema')==SOURCE_ROLES_SCHEMA
        and replay.get('nativeInputs')==pins and replay.get('nativeSourceRoleProjectionProved')is True
        and isinstance(replay.get('sourceRoles'),list)and len(replay['sourceRoles'])==len(names))
    sources={r['wrapperName']:r for r in replay['sourceRoles']}
    reused=replay.get('activeSemanticProvenanceOwners');fresh=replay.get('freshlyDerivedSourceOwners')
    need('all-and-only-requested-source-projections',set(sources)==set(names)
        and isinstance(reused,list)and isinstance(fresh,list)and len(reused)==len(set(reused))and len(fresh)==len(set(fresh))
        and not set(reused)&set(fresh)and set(reused)|set(fresh)==set(names))
    index=consumer_index(current)
    for claim in claims:
        source=claim['source'];name=source['wrapperName']
        need('same-complete-current-source-role',_identity(sources[name])==_identity(source),name)
        _native_identity(image,pins,claim)
        matches=index.get(name,[])+index.get('original:'+source['wrappedType'],[])
        need('same-active-current-consumer-role',any(c.get('routeClosurePresent')is True
            and _identity(consumer_claim(c))==_identity(claim['consumer'])for c in matches),name)
    for catalog in candidate.get('catalogs',[]):
        need('exact-current-supersession-scope',catalog.get('disposition')=='superseded-by-current-named-source-and-consumer-roles'
            and catalog.get('sourceOwners')and set(catalog['sourceOwners'])<=set(names)
            and all(catalog.get(k)is False for k in('oldAnonymousWindowAttributionClaimed','legacyContractModified','legacyDecoderActivated')))
    _publication_gate(image,pins);prepared_current_sequence(active)
    return dict(schema=SCHEMA,status='validated-current-named-catalog-roles',nativeInputs=dict(pins),
        sourceOwners=len(names),catalogsAdmitted=len(candidate['catalogs']),held=candidate['held'],
        nativeSourceRoleProjectionProved=True,activeSemanticProvenanceOwners=reused,freshlyDerivedSourceOwners=fresh,
        activeCurrentConsumerRolesProved=True,legacyContractsModified=0,
        legacyDecodersActivated=0,wholeCorpusEOFClaimed=False,operationScoped=True,evidenceBoundary=__doc__)


def validate_reviewed_on_image(image,pins,*,source_prover,operation):
    from scripts.game_data.il2cpp.native_image import read_reviewed_contract
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label='catalogCurrentRoles')
    return validate_on_image(image,pins,contract,source_prover=source_prover,operation=operation)
