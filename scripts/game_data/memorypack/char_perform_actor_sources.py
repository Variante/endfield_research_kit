"""Current initialized Actor13 reader/factory paths; child semantics stay separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def _flag(g):cell=g.relative('803d');g.take('00');return cell

def _setup(g,context):
 seen=set();cells=[]
 for _ in range(3 if context else 2):
  raw=bytes(g.bytes.get(g.at+i,0)for i in range(3)).hex()
  if raw=='488b15'and context and'context'not in seen:cells.append(dict(site=g.at,cell=g.relative('488b15')));seen.add('context')
  elif raw=='488bcd'and'reader'not in seen:g.take('488bcd');seen.add('reader')
  elif raw=='488b1e'and'wrapper'not in seen:g.take('488b1e');seen.add('wrapper')
  else:raise ValueError('actor13.field-source-origins')
 if seen!={'reader','wrapper',*(['context']if context else[])}:raise ValueError('actor13.source-origin-domain')
 return cells

def existing(regions,entry,fields,o):
 if len(fields)!=13 or len({f['name']for f in fields})!=13:raise ValueError('actor13.field-plan')
 g=BytesPath(regions,entry);g.take('48895c2418','55','56','57','4156','4157','4883ec70');_flag(g);imagebase=g.relative('4c8d3d');g.take('488bf2','488be9');g.branch('0f85',True)
 cur,rem,adv,used=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('837d'+rem+'01');g.branch('7d',True,1);g.take('488b45'+cur,'440fb630','8b5d'+rem,'83eb01');g.branch('79',True,1);g.take('48ff45'+cur,'ff45'+adv,'ff45'+used,'895d'+rem,'4180feff');g.branch('0f84',False);g.take('48833e00');g.branch('0f85',True);g.take('4180fe0d');g.branch('0f85',False)
 results=[];prepared=False;collector=None
 for f in fields:
  kind=f['wire'];slot=bytes((f['fieldOffset'],)).hex();start=g.at
  if prepared:
   if kind!='pooledStringIndex':raise ValueError('actor13.float-successor')
   cells=[];prepared=False
  else:cells=_setup(g,kind=='enum32')
  call=g.at;target=g.relative('e8');g.take('4885db');g.branch('74'if kind=='boolByte'and f is fields[-1]else'0f84',False,1 if kind=='boolByte'and f is fields[-1]else 4)
  if kind=='pooledStringIndex':
   g.take('4c8b4310','4d85c0');g.branch('0f84',False);flag=g.relative('833d');g.take('00','498940'+slot);g.branch('74',True,1)
   if collector is not None and flag!=collector:raise ValueError('actor13.collector-identity')
   collector=flag
  elif kind=='float32':
   g.take('488b4310','4885c0');g.branch('0f84',False);g.take('488b1e','488bcd','f30f1140'+slot);prepared=True
  else:
   g.take('488b4b10','4885c9');g.branch('74'if f is fields[-1]else'0f84',False,1 if f is fields[-1]else 4);g.take(('8841'if kind=='boolByte'else'488941'if kind in('int64','uint64')else'8941')+slot)
  results.append(dict(name=f['name'],sourceCall=call,sourceTarget=target,contexts=cells,selectedStart=start,selectedEnd=g.at))
 if prepared:raise ValueError('actor13.dangling-float-setup')
 g.jump('eb',1);g.take('488b9c24b0000000','4883c470','415f','415e','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,fields=results,memberCount=13,reader='incoming RCX saved RBP to every child RCX',wrapper='incoming RDX saved RSI; same wrapper/original guarded before every source return store',collectorCell=collector,imageBase=imagebase,normalReturn=True,condition='Initialized byte flag, MC13, coherent existing nonnull wrapper/original, sufficient nonoverflowing buffered Reader, disabled collector, ordinary noninterfering helpers preserving Win64 ABI. Child source semantics, type/context joins, construction, registry/default/provider selection and new-wrapper paths are separate.')

def factory(regions,entry,s,*,create=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');_flag(g);g.take('488bd9');g.branch('75'if create else'74',create,1);site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('75'if create else'74',create,1);g.take('c7401000000000','488d4b10','48894310','4883c420','5b')
 if g.relative('e9')!=s['barrier']:raise ValueError('actor13.factory-tail-barrier')
 return dict(selectedBytes=g.seen,allocationUsageSite=site,allocationClassCell=cell,originalZeroedFieldOffset=16,originalZeroedBytes=4,holderOffset=16,normalReturnViaBarrier=True,condition='Initialized metadata, normal typed nonnull original allocation with compatible storage, valid disjoint wrapper/frame and normal barrier; allocation effects and runtime execution excluded. Exact inline ActorType0 and full original reference publication are proved.')

"""Complete selected direct-RAX pooled-string routes; helper effects conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def direct_pool(regions,entry,s,o,mode):
 if mode not in ('empty','null','lookup'):raise ValueError('actorPool.mode')
 if {k:o[k]for k in ('currentPtr','bufferLength','advancedCount','consumed')}!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:raise ValueError('actorPool.reader-layout')
 g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d');g.take('00','488bd9');g.branch('0f84',False)
 def pool():
  if g.relative('488b05')!=s['pool']:raise ValueError('actorPool.pool-cell')
  g.take('488b88b8000000')
 pool();g.take('48833900');g.branch('0f84',False);g.take('4889742430','48897c2438','837b3004');g.branch('0f8c',False)
 g.take('488b4350','8b38','8b7330','83c6fc');g.branch('0f88',False);g.take('4883435004','83434004','83434404','897330','488b742430','83ffff');g.branch('74',mode=='empty',1)
 if mode=='empty':
  if g.relative('488b05')!=s['empty']:raise ValueError('actorPool.empty-cell')
 else:
  g.take('83fffe');g.branch('74',mode=='null',1)
  if mode=='null':g.take('488b7c2438','33c0')
  else:
   pool();g.take('488b09','4885c9');g.branch('74',False,1);g.take('4533c0','8bd7','488b7c2438','4883c420','5b')
   if g.relative('e9')!=s['lookup']:raise ValueError('actorPool.lookup-tail')
 if mode=='empty':g.take('488b7c2438')
 if mode!='lookup':g.take('4883c420','5b','c3')
 return dict(mode=mode,selectedBytes=g.seen,initializerCell=flag,wireBytes=4,reader='incoming RCX saved RBX; same buffer, length and both counters advanced4',output='RAX direct original-caller return',lookupArguments=dict(rcx='same initialized pool',edx='unchanged signed Int32 index',r8d=0)if mode=='lookup'else None,normalReturn=True,condition='Initialized metadata and nonnull coherent pool, four contiguous nonoverflowing Reader bytes, disjoint valid stack/Reader and ABI-preserving helpers; index -1 empty, -2 null, or nonnegative in-range lookup respectively. Pool contents, allocation/refill/initialization, pool-absent UTF8 and live helper/runtime effects remain conditional or excluded.')
