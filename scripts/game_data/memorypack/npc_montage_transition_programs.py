"""Exact current TransitionOverride MC5/value20 programs; no width inference."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def need(check,condition):
    if not condition:raise ValueError('npcMontageTransition.'+check)


def calls(g,symbols):
    roles={}
    def call(role):
        site=g.at;target=g.relative('e8')
        need('same-call-role:'+role,role not in roles or roles[role]==target)
        need('independent-target:'+role,symbols is None or symbols.get(role)==target)
        roles[role]=target;return site
    return roles,call


def reader(regions,entry,*,new=False,ff=False):
    g=BytesPath(regions,entry);s,call=calls(g,None);reads=[];allocation=None
    g.take('48895c2418','57','4883ec20');ready=flag(g)
    g.take('488bda','488bf9');g.branch('0f84',False)
    g.take('488d542430','c644243000','488bcf');call('header');g.take('84c0');g.branch('0f84',ff)
    if ff:
        g.take('488bcb','48c70300000000');call('barrier');g.take('90');g.jump('e9')
    else:
        g.take('4889742438','48833b00');g.branch('0f84',new)
        if new:
            allocation=dict(site=g.at,cell=g.relative('488b0d'));call('allocate');g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','0f57c0','0f114010','894820','488bcb','488903');call('barrier');g.take('90');g.jump('e9')
        g.take('0fb6742430','4080fe05');g.branch('0f85',False)
        contexts=[]
        for index in range(2):
            if index==0:
                site=g.at;cell=g.relative('488b15');g.take('488bcf','488b33')
            else:
                g.take('488bcf');site=g.at;cell=g.relative('488b15');g.take('488b33')
            contexts.append(dict(site=site,cell=cell));at=call('tag');g.take('4885f6');g.branch('74',False,1)
            g.take('894610'if index==0 else'894614');reads.append(dict(fieldName=('from','to')[index],call=at,kind='tag-raw4'))
        for index,(field,store)in enumerate((('transistionOffset','f30f114618'),('transitionDuration','f30f11461c'),('transitionExitTime','f30f114320'))):
            g.take('488bcf','488b33'if index<2 else'488b1b');at=call('single')
            g.take('4885f6'if index<2 else'4885db');g.branch('74',False,1)
            if index==1:g.take('488b1b','488bcf')
            # The last two reads share the Reader setup before the penultimate store.
            if index==1:
                g.take(store);reads.append(dict(fieldName=field,call=at,kind='float32'))
                at=call('single');g.take('4885db');g.branch('74',False,1)
                g.take('488b742438','f30f114320');reads.append(dict(fieldName='transitionExitTime',call=at,kind='float32'));break
            g.take(store);reads.append(dict(fieldName=field,call=at,kind='float32'))
        if len(reads)==5:g.take('488b5c2440','4883c420','5f','c3')
        return dict(selectedBytes=g.seen,symbols=s,reads=reads,contexts=contexts,allocation=allocation,ready=ready,
            new=new,ff=False,frame=dict(entryRspDelta=-40,shadow=[0,32],header=[48,49],savedRsi=[56,64]),normalReturn=True)
    g.take('488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,symbols=s,reads=[],contexts=[],allocation=allocation,ready=ready,new=new,ff=True,normalReturn=True)


def canonical(regions,entry,*,dispatch=False,canonical_target=None,null=False,create=True):
    g=BytesPath(regions,entry);s,call=calls(g,None)
    if dispatch:
        g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda');call('prepare')
        g.take('488b3b');need('actual-compared-canonical',g.relative('488d0d')==canonical_target)
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False);ready=flag(g);g.branch('0f84',False)
    else:
        g.take('48896c2410','4889742418','57','4883ec20');ready=flag(g)
        g.take('498bf9','498be8','488bf2');g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');call('readNull');g.take('84c0');g.branch('0f85',null)
    type_site=None
    if null:g.take('0f57c0','33c0','0f114500','894510');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');type_site=g.at;type_cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
        g.take('33d2','488bcb');call('typeHandle')
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1)
        g.take('33d2','488bc8');call('creationTest');g.take('84c0');g.branch('75',not create,1)
        if create:g.take('488b4720','488b88c0000000','488b4958');call('activate')
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');call('nonnull')
    if dispatch:g.take('488b5c2430')
    g.take('488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,symbols=s,ready=ready,typeSite=type_site,null=null,create=create,dispatch=dispatch,managedBytes=20,normalReturn=True)


def nonnull(regions,entry,*,wrapper_null=False):
    g=BytesPath(regions,entry);s,call=calls(g,None)
    g.take('48895c2408','4889742410','4c89442418','57','4883ec40');ready=flag(g)
    g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
    site=g.at;g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');call('resolve');g.take('488b88c0000000','488b4920');call('wrapperProvider')
    g.take('4885c0');g.branch('0f84',False)
    g.take('b905000000','4c8d4c2460','4c8bc3','488bd0');call('wrapperInvoke');g.take('488b5c2460','4885db');g.branch('0f84',wrapper_null)
    if wrapper_null:g.take('0f57c0','33c0','0f1106','894610');g.jump('e9')
    else:
        g.take('488b4f20');call('resolve');g.take('ba08000000','488b88c0000000');call('indexed')
        g.take('4c8bc0','488d4c2420','4c8bcb');call('conversion')
        g.take('0f1000','8b4810','0f1106','894e10')
    g.take('488b5c2450','488b742458','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,symbols=s,ready=ready,providerSite=site,wrapperNull=wrapper_null,managedBytes=20,
        frame=dict(entryRspDelta=-72,shadow=[0,32],hidden=[32,52],wrapper=[96,104]),normalReturn=True)


def conversion(regions,entry,*,prepare,ordinal):
    need('literal-interface-ordinal',type(ordinal)is int and 0<=ordinal<=16)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','48897c2418','4156','4883ec40','498b39','488bf1','488bcf','4d8bf1','498bd8');g.call(prepare)
    g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
    for n in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',n==ordinal,1)
        if n<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7','4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1',
        '488b5c2450','488b7c2460','0f1000','8b4010','0f1106','894610','488bc6','488b742458','4883c440','415e','c3')
    return dict(selectedBytes=g.seen,managedBytes=20,copiedSlices=[[0,16],[16,4]],sameHiddenOutputReturned=True,normalReturn=True)


def add(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec40','ff411c','498bf0','4c8b4910','488bfa','48634118','488bd9','4d85c9')
    g.branch('74',False,1);g.take('413b4118');g.branch('0f83',False)
    g.take('8d4801','894b18','413b4118');g.branch('73',False,1)
    g.take('0f1002','488d0480','498d0c81','8b4210','0f114120','894130','488b5c2450','488b742458','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,managedBytes=20,arrayStride=20,arrayDataOffset=32,storedSlices=[[0,16],[16,4]],growthAdmitted=False,normalReturn=True)


def listing(regions,entry,*,count,new=True):
    need('finite-count-witness',type(count)is int and -1<=count<=3)
    g=BytesPath(regions,entry);s,call=calls(g,None);callbacks=[];adds=[];backedge=None;bodies=[];loop=None
    g.take('4c8bdc','53','57','4156','4157','4883ec68','4c8bfa','0f57c0','33c0','498d5310','4533f6','89442450',
        '498bcf','45897310','498bd9','498bf8','0f11442440');call('header');g.take('84c0');g.branch('0f84',count==-1)
    if count==-1:g.take('488bcf','4c8937');call('barrier')
    else:
        g.take('4889ac2490000000','4889b424a0000000','4c89a424a8000000','4c896c2460','8bac2498000000','4c3937');g.branch('0f85',not new)
        if new:
            g.take('488b4b20','33d2','488b89c0000000');call('context');g.take('488bc8');call('allocate');g.take('488bf0','4885c0');g.branch('0f84',False)
            g.take('488b4b20','488b91c0000000','488b4a08','4c397120');g.branch('0f84',False)
            g.take('488b4320','8bd5','488bce','4c8b80c0000000','4d8b4008');call('constructor');g.take('488bcf','488937');call('barrier')
        else:
            g.take('488b4320','488b37','488b88c0000000','488b4110','4c397020');g.branch('0f84',False)
            g.take('ff461c','44897618');g.jump('e9')
        provider_site=g.at;g.relative('488b0d');g.take('4439b1e0000000');g.branch('0f84',False)
        g.take('488b4320','488b88c0000000','488b4918');call('provider');g.take('488bf0','85ed');g.branch('7f',count>0,1)
        for n in range(max(count,0)):
            if loop is None:loop=g.at
            need('same-complete-loop-entry',g.at==loop);start=len(g.seen)
            g.take('33c0','0f57c0','89442450','0f11442440','4885f6');g.branch('74',False,1)
            g.take('4c8d4c2440','4d8bc7','488bd6');callbacks.append(call('dispatch'))
            g.take('0f10442440','4c8b27','448b6c2450','0f11442420','4d85e4');g.branch('74',False,1)
            g.take('488b4320','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
            g.take('488b4320','488d542420','498bcc','0f29442420','44896c2430','4c8b80c0000000','4d8b4030');adds.append(call('Add'))
            g.take('41ffc6','443bf5');bodies.append(g.seen[start:]);g.branch('0f8d',n+1==count)
            if n+1<count:backedge=g.at;g.jump('e9');need('actual-unconditional-backedge',g.at==loop)
        g.take('4c8ba424a8000000','488bb424a0000000','4c8b6c2460','488bac2490000000')
    g.take('4883c468','415f','415e','5f','5b','c3')
    return dict(selectedBytes=g.seen,symbols=s,countWitness=count,newList=new,elementCallbackSites=callbacks,addSites=adds,
        backedge=backedge,loop=loop,loopBodies=bodies,providerSite=provider_site if count>=0 else None,headerBytes=4,managedBytes=20,
        frame=dict(entryRspDelta=-136,shadow=[0,32],argument=[32,52],callbackOutput=[64,84],savedR13=[96,104]),normalReturn=True)


def induction(paths):
    need('all-fresh-and-reused-witnesses',[(p['countWitness'],p['newList'])for p in paths]==[(n,new)for n in(-1,0,1,2,3)for new in(False,True)])
    positive=[p for p in paths if p['countWitness']>0];body=positive[0]['loopBodies'][0]
    need('all-full-unchanged-count-loops',bool(body)and all(p['normalReturn']is True
        and len(p['elementCallbackSites'])==len(p['addSites'])==len(p['loopBodies'])==p['countWitness']
        and all(b==body for b in p['loopBodies'])and p['loop']==positive[0]['loop']for p in positive))
    need('two-and-three-actual-backedge-witnesses',all(p['backedge']is not None for p in positive if p['countWitness']>=2))
    return dict(countRange=[-1,4096],counter='R14D initialized zero and incremented once per element',
        savedCount='EBP loaded once from the header output; full repeated body does not write EBP',
        loopEntry=positive[0]['loop'],backedge=next(p['backedge']for p in positive if p['countWitness']==2),
        identicalBody=body,callbackCountEqualsPositiveCount=True,managedBytesPerElement=20,
        wireWidthInferredFromStride=False,compatibleCanonicalCallbackRequired=True)


def capacity(regions,entry,*,positive):
    need('literal-capacity-case',type(positive)is bool)
    g=BytesPath(regions,entry);s,call=calls(g,None)
    g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
    g.take('498b4820','488b89c0000000');g.branch('75',positive,1)
    if positive:
        g.take('ba01000000');call('context');g.take('488bd3','488bc8');call('arrayAllocate');g.jump('eb',1)
    else:
        g.take('33d2');call('context');g.take('83b8e000000000');g.branch('74',False,1)
        g.take('488b4f20','33d2','488b89c0000000');call('context');g.take('488b88b8000000','488b01')
    g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f');s['barrier']=g.relative('e9')
    return dict(selectedBytes=g.seen,symbolTargets=s,positive=positive,requestedCapacityUnchanged=True,
        arrayContextSlot=1,itemsOffset=16,normalReturnViaBarrier=True)


def provider(regions,entry):
    g=BytesPath(regions,entry);s,call=calls(g,None)
    g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
    type_site=g.at;g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('33d2','488bcb');call('typeHandle');provider_site=g.at;g.relative('488b0d')
    g.take('488bd8','83b9e000000000');g.branch('74',False,1)
    g.take('488bcb');call('backend');g.take('488b4f38','ba01000000','488bd8');call('context')
    g.take('488bd0','488bcb');call('cast');g.take('4885c0');g.branch('0f84',False)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,symbolTargets=s,typeSite=type_site,providerSite=provider_site,
        typeContextSlot=0,formatterContextSlot=1,normalReturn=True)
