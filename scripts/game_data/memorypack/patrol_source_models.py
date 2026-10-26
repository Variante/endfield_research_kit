from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
"""Exact current Patrol programs; live/provider selection remains conditional."""


def direct_record(regions,entry,fields,offsets,barrier,*,tail_barrier=False):
    g=BytesPath(regions,entry);b=lambda n:bytes((n,)).hex()
    peek=lambda n=3:bytes(g.bytes.get(g.at+i,-1)for i in range(n))
    def guarded(register):
        raw=peek(1)
        if raw==b'\x74':target=g.relative('74',1)
        else:target=g.relative('0f84')
        if target not in g.bytes:raise ValueError('patrolSource.unowned-null-guard')
        guards.append(target)
    def store(prefix8,prefix32,slot):
        g.take(prefix8+b(slot)if slot<128 else prefix32+slot.to_bytes(4,'little').hex())
    cur,rem,adv,used=(b(offsets[n])for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20');g.relative('803d');g.take('00','488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False);g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',False)
    g.take('48833f00');g.branch('0f84',False);g.take('4080fe'+b(len(fields)));g.branch('0f85',False)
    reader=holder=False;reads=[];guards=[]
    for ordinal,field in enumerate(fields):
        context=None;last=ordinal==len(fields)-1;holder_register='rsi'
        while True:
            raw=peek()
            if raw==b'\x48\x8b\xcb':g.take('488bcb');reader=True
            elif raw==b'\x48\x8b\x37':g.take('488b37');holder=True
            elif raw==b'\x48\x8b\x3f' and last:g.take('488b3f');holder=True;holder_register='rdi'
            elif raw==b'\x48\x8b\x15' and context is None:
                at=g.at;context=dict(instruction=at,cell=g.relative('488b15'))
            else:break
        if not reader or not holder:raise ValueError('patrolSource.entry-reader-holder-setup')
        if bool(context)!=field['typed']:raise ValueError('patrolSource.typed-context-presence')
        site=g.at;g.call(field['target']);reader=False
        g.take('4885ff'if holder_register=='rdi'else'4885f6');guarded(holder_register)
        floating=field['mode']=='single';g.take(('488b47'if holder_register=='rdi'else'488b46')+'10'if floating else('488b4f'if holder_register=='rdi'else'488b4e')+'10')
        g.take('4885c0'if floating else'4885c9');guarded(holder_register)
        if floating:
            if peek()==b'\x48\x8b\x37':g.take('488b37','488bcb');reader=True;holder=True
            store('f30f1140','f30f1180',field['offset'])
        else:
            mode=field['mode'];prefix=('8841','8881')if mode=='bool'else('488941','488981')if mode=='reference'else('8941','8981')
            store(*prefix,field['offset'])
            if mode=='reference':
                slot=field['offset'];g.take('4883c1'+b(slot)if slot<128 else'4883e980'if slot==128 else'4881c1'+slot.to_bytes(4,'little').hex())
                if not(last and tail_barrier):g.call(barrier)
        reads.append(dict(field=field['name'],call=site,target=field['target'],mode=field['mode'],wireBytes=field['wireBytes'],context=context,storeOffset=field['offset']))
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
    if tail_barrier:
        if g.relative('e9')!=barrier:raise ValueError('patrolSource.final-barrier-tail')
    else:g.take('c3')
    if len(set(guards))!=1:raise ValueError('patrolSource.shared-null-failure')
    return dict(selectedBytes=g.seen,reads=reads,memberCount=len(fields),headerWireBytes=1,nonnullExistingWrapper=True,entryReader='rcx->rbx',entryHolder='rdx->rdi',normalReturn=True,condition='Current initialized selected wrapper/source, matching nonnull original, sufficient disjoint Reader/source/storage and ordinary helper/collector/nonvolatile ABI conditions. Null/new/error/default/provider selection, child grammar and full owner are separate.')


def point_record(regions,entry,offsets,slots,packable,barrier):
    g=BytesPath(regions,entry);b=lambda n:bytes((n,)).hex()
    cur,rem,adv,used=(b(offsets[n])for n in('currentPtr','bufferLength','advancedCount','consumed'))
    guards=[]
    def guard(short=False):
        target=g.relative('74',1)if short else g.relative('0f84')
        if target not in g.bytes:raise ValueError('patrolPoint.unowned-null-guard')
        guards.append(target)
    g.take('48895c2418','55','56','57','4883ec20');g.relative('803d');g.take('00','488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False);g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',False)
    g.take('4c89742448','48833f00');g.branch('0f84',False);g.take('4080fe03');g.branch('0f85',False)
    usage=g.at;cell=g.relative('488b15');g.take('488bcb','488b37');site=g.at;g.call(packable)
    g.take('4885f6');guard();g.take('488b4e10','4885c9');guard();g.take('488941'+b(slots['actions']),'4883c1'+b(slots['actions']));g.call(barrier)
    g.take('837b'+rem+'04','488b37');g.branch('0f8c',False);g.take('488b43'+cur,'448b30','8b6b'+rem,'83c5fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','896b'+rem,'4885f6');guard();g.take('488b4610','4885c0');guard();g.take('448970'+b(slots['enterGait']))
    g.take('837b'+rem+'0c','488b3f');g.branch('0f8c',False);g.take('488b43'+cur,'f20f1000','8b6808','f20f11442440','8b73'+rem,'83c6f4');g.branch('0f88',False)
    g.take('488343'+cur+'0c','8343'+adv+'0c','8343'+used+'0c','8973'+rem,'4885ff');guard(True);g.take('488b4710','4885c0');guard(True)
    g.take('4c8b742448','f20f1140'+b(slots['position']),'8968'+b(slots['position']+8),'488b5c2450','4883c420','5f','5e','5d','c3')
    if len(set(guards))!=1:raise ValueError('patrolPoint.shared-null-failure')
    return dict(selectedBytes=g.seen,memberCount=3,headerWireBytes=1,listContext=dict(instruction=usage,cell=cell,call=site),inlineEnumBytes=4,inlineVectorBytes=12,normalReturn=True,condition='Current initialized nonnull wrapper/original, sufficient disjoint Reader/source/storage, exact typed list and Vector3/enum joins, and normal helper/nonvolatile/collector effects. Null/new/refill/error/default/provider and child grammar remain separate.')



def union(regions,entry,s,*,tag=-1,existing=False):
 if type(tag)is not int or tag not in(-1,0,1)or type(existing)is not bool:raise ValueError('patrolUnion.profile')
 g=BytesPath(regions,entry);g.take('48895c2408','4889742418','57','4883ec20');g.relative('803d');g.take('00','498bf0','488bda');g.branch('0f84',False)
 g.take('33ff','488d542438','488bcb','66897c2438');g.call(s['header']);g.take('84c0');g.branch('0f84',tag==-1);child=comparison=None
 if tag==-1:g.take('48893e');g.jump('e9')
 else:
  g.take('0fb77c2438','6685ff');g.branch('74',tag==0,1)
  if tag==1:g.take('6683ff01');g.branch('0f85',False)
  g.take('488b0e','4885c9');g.branch('74'if tag==0 else'0f84',not existing,1 if tag==0 else 4)
  if existing:
   site=g.at;cell=g.relative('488b15');comparison=dict(site=site,cell=cell);g.take('488b09');g.call(s['assignable']);g.take('84c0');g.branch('74',True,1)
  site=g.at;cell=g.relative('488b15');child=dict(site=site,cell=cell);g.take('488bcb');g.call(s['packable'])
  if tag==0:g.take('488906','488bce')
  else:g.take('488bce','488906')
  g.call(s['barrier']);g.jump('eb'if tag==0 else'e9',1 if tag==0 else 4)
 if tag==-1:g.take('488bce');g.call(s['barrier']);g.jump('eb',1)
 g.take('488b5c2430','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,tag=tag,existingIncompatible=existing,comparisonUsage=comparison,childUsage=child,sameReader='incoming RDX retained RBX; same RCX to header/child',sameOutput='incoming R8 retained RSI; complete null or returned ChildWrapper stored unchanged',normalReturn=True,condition='Initialized actual union, selected short tag/null; matching typed context, null or incompatible BaseWrapper output and normal assignability/typed ReadPackable/barrier helpers. Only tags0/1/null admitted; provider/live execution separate.')


def child(regions,entry,s,*,audio=False):
 g=BytesPath(regions,entry);g.take('48895c2418','56','4883ec20');g.relative('803d');g.take('00','488bda','488bf1');g.branch('0f84',False)
 g.take('488b0b','c644243800','4885c9');g.branch('0f85',False);g.take('488d542438','488bce');g.call(s['header']);g.take('84c0');g.branch('0f84',False)
 g.take('48897c2430','48833b00');g.branch('75',False,1);site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('74'if audio else'0f84',False,1 if audio else 4)
 g.take('33d2','488bc8');g.call(s['ctor']);g.take('488bcb','48893b');g.call(s['barrier']);g.take('0fb67c2438','4080ff'+('01'if audio else'03'));g.branch('0f85',False)
 usages=[];reads=[]
 for i in range(1 if audio else 3):
  last=audio or i==2
  if audio:at=g.at;context=g.relative('488b15');usages.append(dict(site=at,cell=context));g.take('488bce','488b1b')
  else:g.take('488b1b'if last else'488b3b','488bce')
  call=g.at;g.call(s['reads'][i]);g.take('4885db'if last else'4885ff');g.branch('74',False,1);g.take('4533c0','8bd0'if audio else'0fb6d0'if last else'488bd0','488bcb'if last else'488bcf');g.call(s['setters'][i]);reads.append(call)
 g.take('488b7c2430','488b5c2440','4883c420','5e','c3')
 return dict(selectedBytes=g.seen,audio=audio,memberCount=1 if audio else 3,allocationUsage=dict(site=site,cell=cell),typedReads=usages,sourceCalls=reads,initialOutputNull=True,normalReturn=True,condition='Initialized fresh typed ChildWrapper output, positive actual header MC1/MC3, normal actual wrapper allocation/constructor and child/setter/barrier effects, disjoint Reader/output. Coherent original/cache relation and each source/setter proved separately; existing-child/prehook routes excluded.')


def cached(regions,entry,s,*,mode='empty'):
 if mode not in('empty','different','coherent'):raise ValueError('patrolGetter.profile')
 g=BytesPath(regions,entry);g.take('4053','4883ec20');g.relative('803d');g.take('00','488bd9');g.branch('74',False,1);g.take('48837b1800');g.branch('0f84',mode=='empty')
 if mode!='empty':g.take('488b4310','48394318');g.branch('0f85',mode=='different')
 usages=[]
 if mode!='coherent':
  at=g.at;cell=g.relative('488b15');usages.append(dict(site=at,cell=cell));g.take('48897c2430','488b7b10','488bcf');g.call(s['cast']);g.take('48894318','488bcf');at=g.at;second=g.relative('488b15');usages.append(dict(site=at,cell=second))
  if cell!=second:raise ValueError('patrolGetter.same-type-cell')
  g.call(s['cast']);g.take('488d4b18');g.call(s['barrier']);g.take('488b7c2430');g.jump('e9')
 g.take('488b4318','4883c420','5b','c3');return dict(selectedBytes=g.seen,mode=mode,classUsages=usages,baseHolder=16,cacheHolder=24,condition='Initialized current wrapper, stable disjoint holders, normal compatible checked casts and barrier; coherent cache returns unchanged original, refresh stores compatible original. Live selection separate.')


def child_factory(regions,entry,s,*,ctor=True):
 g=BytesPath(regions,entry);g.take('4057'if ctor else'48895c2408')
 if not ctor:g.take('57')
 g.take('4883ec20');g.relative('803d');g.take('00','488bf9');g.branch('74'if ctor else'75',not ctor,1)
 if ctor:g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('74'if ctor else'75',not ctor,1)
 g.take('4533c0')
 if ctor:g.take('48895c2430')
 g.take('488bd0','488bcf');g.call(s['baseSetter']);g.take('488b5f10');first=g.relative('488b15');g.take('488bcb');g.call(s['strictCast']);g.take('48894718','488bcb');second=g.relative('488b15');g.call(s['strictCast']);g.take('488d4f18','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier']or cell!=first or cell!=second:raise ValueError('patrolFactory.same-owned-original-type')
 return dict(selectedBytes=g.seen,constructor=ctor,allocationUsage=dict(site=site,cell=cell),sameTypedOriginalInBothHolders=True,condition='Initialized ready BaseWrapper/current typed original, matching typed nonnull zeroed allocation; actual dual-holder setter, successful exact strict casts and disabled collector. Original child constructor is empty/current and every serialized field is overwritten; live activation/default selection separate.')


def scalar_setter(regions,entry,getter,*,slot,boolean=False):
 if type(slot)is not int or not 16<=slot<128 or type(boolean)is not bool:raise ValueError('patrolSetter.profile')
 g=BytesPath(regions,entry);g.take('4053','4883ec20','0fb6da'if boolean else'8bda','33d2');g.call(getter);g.take('4885c0');g.branch('74',False,1);g.take(('8858'if boolean else'8958')+bytes((slot,)).hex(),'4883c420','5b','c3')
 return dict(selectedBytes=g.seen,slot=slot,storedBits=8 if boolean else 32,incomingValuePreserved=True,condition='Actual owning cached getter returns matching nonnull typed original, ordinary Win64 nonvolatile preservation; no signed reinterpretation or Audio Event semantics.')


def reference_setter(regions,entry,getter,barrier,*,slot):
 if type(slot)is not int or not 16<=slot<128:raise ValueError('patrolSetter.reference-profile')
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0');g.branch('74',False,1);g.take('488d48'+bytes((slot,)).hex(),'488958'+bytes((slot,)).hex(),'4883c420','5b')
 if g.relative('e9')!=barrier:raise ValueError('patrolSetter.reference-barrier')
 return dict(selectedBytes=g.seen,slot=slot,incomingReferenceUnchanged=True,condition='Current owning getter returns nonnull matching original; exact full reference stored, normal disabled barrier and Win64 preservation.')



def value32_empty(regions,entry,o,s,*,count=0,new=True):
 if type(count)is not int or count not in(-1,0)or type(new)is not bool:raise ValueError('patrolEmptyList.profile')
 g=BytesPath(regions,entry);b=lambda n:bytes((o[n],)).hex()
 g.take('4053','55','56','4154','4156','4883ec70','837a'+b('bufferLength')+'04','0f57c0','0f11442450','4d8bf1','4d8be0','0f11442460','488bf2');g.branch('0f8c',False)
 g.take('488b46'+b('currentPtr'),'8b28','8b5e'+b('bufferLength'),'83c3fc');g.branch('0f88',False)
 g.take('488346'+b('currentPtr')+'04','8346'+b('advancedCount')+'04','8346'+b('consumed')+'04','895e'+b('bufferLength'),'486346'+b('consumed'),'488b4e'+b('totalLength'),'482bc8','4863c5','483bc8');g.branch('0f8c',False)
 g.take('4889bc24a0000000','83fdff');g.branch('0f84',count==-1);provider=None
 if count==-1:
  g.take('33ff','498bcc','49893c24');g.call(s['barrier']);g.jump('e9')
 else:
  g.take('4c89ac24a8000000','4c89bc24b0000000','49833c2400');g.branch('0f85',not new)
  if new:
   g.take('498b4e20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
   g.take('498b4e20','488b91c0000000','488b4a08','4883792000');g.branch('0f84',False);g.take('85ed');g.branch('0f88',False)
   g.take('498b4620','488b88c0000000','488b7908','488b4720','488b88c0000000');g.branch('0f85',False)
   g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('0f84',False)
   g.take('488b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01','488d4b10','48894310');g.call(s['barrier']);g.take('498bcc','49891c24');g.call(s['barrier'])
  else:
   g.take('498b4620','498b1c24','488b88c0000000','488b4110','4883782000');g.branch('75',True,1)
   g.take('498b4620','488bcb','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
  provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
  g.take('498b4620','488b88c0000000','488b4918');g.call(s['provider']);g.take('33ff','4c8bf8','85ed');g.branch('7f',False,1)
  g.take('4c8bac24a8000000','4c8bbc24b0000000')
 g.take('488bbc24a0000000','4883c470','415e','415c','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,count=count,newList=new,providerClassCell=provider,elementCallbacks=0,headerWireBytes=4,elementWireAdmitted=False,concreteElementFormatterRequired=False,condition='Selected actual closed managed32 ListFormatter/DataPair context, buffered disjoint Reader/output/storage, initialized context/constructor/static empty array and normally returning actual Clear/context/allocation/provider/barrier calls. Count0 provider result is unused; no formatter registration or successful provider lookup is fabricated. Positive DataPair elements stay refused.')
