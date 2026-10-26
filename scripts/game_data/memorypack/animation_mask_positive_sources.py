"""Opt-in positive mask-list source; legacy null/empty/one stays unchanged.

The complete selected loop has a signed exit and a separately owned
backward jump. No list growth or runtime formatter selection is inferred.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.animation-mask-positive-source.v1'
TYPE='System.Collections.Generic.List`1<Beyond.Gameplay.View.Animation.AnimationConfigJson+BoneWeightMaskJsonEntry>'


def need(key,condition):
    if not condition:raise ValueError('animationMaskPositive.'+key)


def list_program(regions,entry,s,*,count,new=True):
    need('finite-count-and-new-mode',type(count)is int and -1<=count<=3 and type(new)is bool)
    g=BytesPath(regions,entry);g.take('4053','57','4156','4157','4883ec58');g.relative('803d');g.take('00','498bd9','498bf8','4c8bf2');g.branch('0f84',False)
    g.take('0f57c0','488d942488000000','4533ff','498bce','4489bc2488000000','0f11442420');g.call(s['collectionHeader']);g.take('84c0');g.branch('0f84',count==-1)
    loops=[];reads=[];adds=[]
    if count==-1:
        g.take('488bcf','4c893f');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('4889b42490000000','4889ac2480000000','4c89642450','0f29742440','8bb42488000000','4c393f');g.branch('0f85',not new)
        if new:
            g.take('488b4b20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('488b4b20','488b91c0000000','488b4a08','4c397920');g.branch('0f84',False);g.take('488b4320','8bd6','488bcd','4c8b80c0000000','4d8b4008');g.call(s['constructor']);g.take('488bcf','48892f');g.call(s['barrier'])
        else:
            g.take('488b4320','488b2f','488b90c0000000','488b4210','4c397820');g.branch('75',True,1);g.take('488b4320','488bcd','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
        provider=g.at;g.relative('488b0d');g.take('4439b9e0000000');g.branch('0f84',False);g.take('488b4320','488b88c0000000','488b4918');g.call(s['provider']);g.take('488be8','85f6');g.branch('7f',count>0,1)
        for index in range(max(count,0)):
            start=g.at;before=len(g.seen)
            g.take('0f57c0','0f11442420','4885ed');g.branch('74',False,1);g.take('4c8d4c2420','4d8bc6','488bd5');reads.append(g.at);g.call(s['dispatch']);g.take('4c8b27','0f28742420','4d85e4');g.branch('74',False,1)
            g.take('488b4320','488b88c0000000','488b4130','4883782000');g.branch('0f84',False);g.take('488b4320','488d542430','498bcc','660f7f742430','4c8b80c0000000','4d8b4030');adds.append(g.at);g.call(s['add']);g.take('41ffc7','443bfe')
            exit_site=g.at;g.branch('0f8d',index+1==count)
            body=g.seen[before:]
            jump=None
            if index+1<count:
                jump=g.at;g.jump('eb',1);need('same-actual-loop-entry',g.at==start)
            loops.append(dict(entryVa=start,exitSite=exit_site,body=body,backJumpVa=jump))
        g.take('4c8b642450','488bac2480000000','0f28742440','488bb42490000000')
    g.take('4883c458','415f','415e','5f','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,elementCallbacks=len(reads),
        callbackSites=reads,addSites=adds,iterations=loops,elementRuntimeBytes=16,
        initialCountRequired=0,capacityAtLeastCountRequired=True,allSourceBitsStored=True,
        fullFrameRestored=True,growthAdmitted=False,elementGrammarAdmitted=False)


def induction(programs,*,count_limit=4096):
    need('bounded-opt-in-count-limit',type(count_limit)is int and 3<=count_limit<=4096)
    paths=[]
    for new in(False,True):
        witnesses={n:[p for p in programs if p.get('newList')is new and p.get('countWitness')==n]for n in range(4)}
        need('one-complete-program-each-witness',all(len(v)==1 for v in witnesses.values()))
        rows={n:v[0]for n,v in witnesses.items()}
        need('zero-no-callback-and-complete-return',rows[0]['elementCallbacks']==0 and rows[0]['selectedBytes'][-1][1]=='c3')
        first=rows[1]['iterations'][0]
        prefix=rows[1]['selectedBytes'][:rows[1]['selectedBytes'].index(first['body'][0])]
        need('literal-zero-counter-and-unchanged-signed-count',sum(h=='4533ff'for a,h in prefix)==1
            and sum(h=='8bb42488000000'for a,h in prefix)==1)
        normalized=lambda v:json.loads(json.dumps(v))
        for count in(1,2,3):
            row=rows[count]
            need('exact-count-read-store-and-return',len(row['iterations'])==row['elementCallbacks']==len(row['addSites'])==count
                and row['selectedBytes'][-1][1]=='c3'and row['growthAdmitted']is False)
            for i,iteration in enumerate(row['iterations']):
                need('identical-owned-iteration-bytes',normalized(iteration['body'])==normalized(first['body'])
                    and iteration['entryVa']==first['entryVa']and iteration['exitSite']==first['exitSite']
                    and iteration['body'][-4][1]=='41ffc7'and iteration['body'][-3][1]=='443bfe'
                    and iteration['body'][-2][1]=='0f8d')
                need('only-final-iteration-takes-signed-exit',(iteration['backJumpVa']is None)==(i+1==count))
        paths.append(dict(newList=new,counter='r15d',savedCount='esi',zeroCountCallbacks=0,
            loopEntryVa=first['entryVa'],signedExitVa=first['exitSite'],body=first['body'],
            positiveWitnesses=[1,2,3],sameOwnedBackJumpVa=rows[2]['iterations'][0]['backJumpVa']))
    return dict(schema=SCHEMA,maxCount=count_limit,nonnegativeCountRange=[0,count_limit],pathProofs=paths,
        noSignedCounterOverflow=True,initialCountRequired=0,capacityAtLeastCountRequired=True,growthAdmitted=False,
        elementGrammarAdmitted=False,parentFieldAdmitted=False,
        invariant='At entry R15D=i and ESI=count. The exact callback/Add16 body increments once; signed JGE exits iff i+1>=count, otherwise the owned jump returns to the same entry. Normal Win64 child ABI preserves the counter/count and copied16 bits.')


def verify_source(component,pins):
    from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions
    need('selected-positive-source-only',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-positive-mask-source'and component.get('typeName')==TYPE
        and component.get('elementGrammarAdmitted')is False and component.get('parentFieldAdmitted')is False)
    proof=component['proof'];base=proof['imageBase'];source=proof['source'];symbols={k:base+v for k,v in proof['symbolRvas'].items()}
    regions=_owned_regions(source['regions'],source['windows'],base=base,label='positive-mask-list')
    replay=[list_program(regions,base+source['entryRva'],symbols,count=-1)]
    replay.extend(list_program(regions,base+source['entryRva'],symbols,count=count,new=new)for new in(False,True)for count in range(4))
    normalized=lambda v:json.loads(json.dumps(v))
    need('exact-all-witnesses-and-induction',normalized(replay)==proof['programs']
        and normalized(induction(replay[1:],count_limit=component['countLimit']))==proof['induction'])
    usage=proof['typedRequest'];reference=proof['reference']
    from scripts.game_data.memorypack.modelview_packable_sources import read_packable
    frontend=proof['referenceSource']
    front_regions=_owned_regions(frontend['regions'],frontend['windows'],base=base,label='positive-mask-ReadPackable')
    front_symbols={k:base+v for k,v in proof['referenceSymbolRvas'].items()}
    need('whole-owned-zero-local-frontend-replay',frontend['entryRva']==proof['sourceTargetRva']
        and normalized(read_packable(front_regions,base+frontend['entryRva'],front_symbols))==reference.get('source'))
    need('exact-closed-ReadPackable-zero-reference-local',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[TYPE])
        and component.get('initiallyNullOutputProved')is True and reference.get('source',{}).get('zeroLocalBits')==64
        and reference['source'].get('formatterSlot')==5 and reference['source'].get('returnValue')=='complete same local8 to RAX'
        and reference['source'].get('callbackArguments',{}).get('output')=='same zero-initialized local8')
    return base


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    """Fresh source/metadata/zero-output proof; no child or enclosing grant."""
    import copy
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.memorypack import animation_mask_sources as legacy,modelview_packable_sources
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    _publication_gate(image,pins);base=image.pe.image_base
    validate_typed_usage_context(image,typed_request,label='animationMaskPositive.actual')
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
    fact=json.loads((CONTRACTS_DIR/'animation_masks_native.json').read_bytes())
    need('same-reviewed-native-inputs',fact.get('nativeInputs')==pins)
    existing=legacy.validate_components(image,fact)
    source=fact['profile']['sources']['list'];symbols={k:base+v for k,v in fact['profile']['symbols'].items()}
    regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in source['windows']]
    programs=[list_program(regions,base+source['entryRva'],symbols,count=-1)]
    programs.extend(list_program(regions,base+source['entryRva'],symbols,count=n,new=new)for new in(False,True)for n in range(4))
    certificate=induction(programs[1:],count_limit=count_limit)
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    need('same-ReadPackable-native-inputs',core.get('nativeInputs')==generic.get('nativeInputs')==pins)
    need('same-owned-ReadPackable-target',call_target==base+core['readPackable']['entryRva']==base+fact['profile']['rootReads'][3])
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    frontend=core['readPackable'];front_symbols=dict(routes['symbolRvas'],backend=frontend['backendForwarder']['entryRva'])
    result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-positive-mask-source',nativeInputs=pins,
        typeName=TYPE,countLimit=count_limit,initiallyNullOutputProved=True,newConstructorCapacityEqualsCountProved=True,
        growthAdmitted=False,elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(imageBase=base,typedRequest=typed_request,sourceTargetRva=call_target-base,
            legacySourceValidation=existing,source=dict(entryRva=source['entryRva'],windows=source['windows'],
                regions=[[a,h.hex().upper()]for a,h in regions]),symbolRvas=fact['profile']['symbols'],
            programs=programs,induction=certificate,reference=reference,referenceSymbolRvas=front_symbols,
            referenceSource=dict(entryRva=frontend['entryRva'],windows=frontend['ownedWindows'],regions=[
                [base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']).hex().upper()]
                for w in frontend['ownedWindows']])))))
    verify_source(result,pins);_publication_gate(image,pins);return result
