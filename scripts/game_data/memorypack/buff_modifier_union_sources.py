"""Current Heal/Poise union callers and their independent concrete children.

Only selected initialized short/FF paths with initially null outputs are
admitted. Native contexts, base conversions, complete concrete readers and
child grammars are independently composed; no runtime evaluation is inferred.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_selector_union_sources import branch,jump,peek

FAMILIES=('HealProcessorBase','PoiseProcessorBase')
CAPABILITIES={'HealProcessorBase':'buff-heal-processor-union','PoiseProcessorBase':'buff-poise-processor-union'}
LABEL='buffModifierUnionSources'


def need(check,condition,actual=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(actual)[:800])


def program(regions,entry,s,*,profile,tag,ff=False):
    """Complete finite source paths; tag count never comes from payload bytes."""
    heal=profile=='heal-pair-esi32'
    need('finite-profile',heal or profile=='poise-single-edi32')
    need('finite-tag',type(tag)is int and tag in((0,1)if heal else(0,)))
    need('literal-FF',type(ff)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','498bd8','488bfa'if heal else'488bf2')
    g.branch('75',True,1)if heal else g.branch('0f84',False)
    g.take('33f6'if heal else'33ff','488d542438','488bcf'if heal else'488bce','6689742438'if heal else'66897c2438')
    g.call(s['header']);g.take('84c0');branch(g,4,ff)
    child=None
    if ff:
        g.take('488933'if heal else'48893b')
    else:
        g.take('0fb7742438'if heal else'0fb77c2438','6685f6'if heal else'6685ff')
        if heal:
            branch(g,5,tag!=0)
            if tag==1:g.take('6683fe01');branch(g,5,False)
        else:branch(g,5,False)
        g.take('488b0b','4885c9')
        # These two compiler branch layouts both select the just-tested null
        # output. No existing-output/cast/cached-provider path is admitted.
        if peek(g,2)==b'\x0f\x84'or peek(g)==b'\x74':branch(g,4,True)
        else:branch(g,5,False)
        site=g.at;cell=g.relative('488b15')
        g.take('488bcf'if heal else'488bce');g.call(s['packable']);g.take('488903')
        child=dict(instruction=site,cell=cell)
    if peek(g)in(b'\xe9',b'\xeb'):jump(g)
    g.take('488bcb')
    tail=peek(g)!=b'\xe8'
    if not tail:
        g.call(s['barrier'])
        if peek(g)in(b'\xe9',b'\xeb'):jump(g)
    need('owned-restoration-entry',peek(g,3)==bytes.fromhex('488b5c'),
        dict(profile=profile,tag=tag,ff=ff,at=hex(g.at),actual=peek(g,3).hex()))
    g.take('488b5c2430','488b742440','4883c420','5f')
    if tail:
        target=g.relative('e9');need('same-tail-barrier',target==s['barrier'],target)
    else:g.take('c3')
    return dict(selectedBytes=g.seen,profile=profile,initializedFlag=flag,tag=None if ff else tag,
        canonicalFF=ff,childUsage=child,headerTarget=s['header'],childTarget=None if ff else s['packable'],
        barrierTarget=s['barrier'],outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,
        sameReader=True,sameOutput=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rsi','rdi'],concreteGrammarAdmitted=False)


def derive(image,pins,active):
    """Fresh unions, every concrete lifecycle/program, and nominal child joins."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import current_reference_union_sources,generated_reader_sources
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);need('same-active-native-inputs',active['nativeInputs']==pins)
    union=current_reference_union_sources.derive(image,pins,families=FAMILIES)
    routes={row['wrapperName']:row for group in union['families'].values()for row in group['programs']}
    readers=generated_reader_sources.derive_many(image,pins,list(routes));closed={};proofs={}
    references={'Beyond.Blackboard+BlackboardDouble':('skill-blackboard-double','blackboard-double','scalar-payload'),
        'Beyond.Gameplay.AttributeModifierData+AttributeModifier':('skill-root-attribute-modifier','record','skill-root-attribute-modifier')}
    for row in readers['owners']:
        need('complete-concrete-processor',row['status']=='complete-reader-source-proved',row.get('reason'))
        source=row['proof'];route=routes[source['wrapperName']]
        requests={read['memberIndex']:derive_typed_usage_context(image,read['context']['instructionRva'],label=LABEL)
            for read in source['orderedSourceReads']if read['declaredType']in references}
        compiled,pending=compile_member_program(source,pins,wrapper_name=route['wrapperName'],type_name=route['wrappedType'],
            value4={},references=references,reference_children={t:active for t in references},typed_requests=requests)
        need('complete-processor-child-grammars',not pending,pending)
        closed[route['wrapperName']]=dict(tag=route['tag'],wrapperName=route['wrapperName'],typeName=route['wrappedType'],
            memberCount=compiled['memberCount'],orderedReads=compiled['reads'],wholeGrammarAdmitted=True,
            wrapperNullAdmitted=True,generatedWrapperOnly=True)
        proofs[route['wrapperName']]=source
    abi=reference_reader_abi(image,pins);caps={}
    for name,group in union['families'].items():
        children=[]
        for route in group['programs']:
            source=proofs[route['wrapperName']]
            need('actual-abstract-holder',source['lifecycle']['baseHolder'][1:]==[group['typeName'],16])
            children.append(closed[route['wrapperName']])
        need('complete-union-domain',[row['tag']for row in children]==list(range(2 if name=='HealProcessorBase'else 1)))
        caps[CAPABILITIES[name]]=dict(typeName=group['typeName'],routes=children,
            supportedShortTags=[row['tag']for row in children],nullAdmitted=True,nullMarker=255,
            wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
            baseGetterSemanticsProved=group['baseGetterSemanticsAdmitted'],concreteChildGrammarsProved=True,
            extendedTagsAdmitted=False,reservedMarkersAdmitted=False,**abi)
    _publication_gate(image,pins)
    return dict(nativeInputs=pins,capabilities=caps,proof=dict(unions=union,concrete=proofs))


def read_union(reader,native,capability,depth=0):
    """Read only the complete fresh finite program selected by the parent."""
    from scripts.game_data.memorypack.skill_timeline_current_sequence import ATOMIC_KINDS
    from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
    need('union-depth',type(depth)is int and 0<=depth<=64)
    cap=native['capabilities'][capability];start=reader.pos;tag=reader.peek()
    need('whole-ordinary-union',cap['wholeGrammarAdmitted']is True and cap['ordinaryOriginalReadValueAdmitted']is True
        and cap['baseGetterSemanticsProved']is True and cap['concreteChildGrammarsProved']is True
        and cap['nullMarker']==255 and cap['nullAdmitted']is True
        and cap['extendedTagsAdmitted']is False and cap['reservedMarkersAdmitted']is False)
    if tag==255:
        reader.take(1,capability+'.null');reader.records.append(dict(kind=capability,start=start,end=reader.pos,isNull=True));return
    need('finite-union-tag',tag in cap['supportedShortTags'],tag)
    route,=[row for row in cap['routes']if row['tag']==tag]
    reads=route['orderedReads'];need('complete-concrete-program',route['wholeGrammarAdmitted']is True
        and len(reads)==route['memberCount']and[read['memberIndex']for read in reads]==list(range(len(reads))))
    reader.take(1,capability+'.tag');fields=[]
    if reader.peek()==255:
        need('own-wrapper-null',route['wrapperNullAdmitted']is True);reader.take(1,capability+'.wrapper-null')
    else:
        reader.header(route['memberCount'])
        for read in reads:
            at=reader.pos;kind=read['kind'];child=read['childCapability']
            if kind in ATOMIC_KINDS:
                need('atomic-no-child',child is None);reader.take(ATOMIC_KINDS[kind],route['typeName']+'.'+read['fieldName'])
            elif(kind,child)==('blackboard-double','scalar-payload'):
                reader._profile('scalar_payload',child,depth+1)
            elif(kind,child)==('record','skill-root-attribute-modifier'):
                RootChildrenReader(reader).record(child,depth+1)
            else:raise ValueError(LABEL+'.unproved-processor-member:'+str((kind,child)))
            fields.append(dict(fieldName=read['fieldName'],start=at,end=reader.pos))
    reader.records.append(dict(kind=capability,start=start,end=reader.pos,tag=tag,fields=fields,isNull=False))
