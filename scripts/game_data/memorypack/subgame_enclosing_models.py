"""Selected reference/reference dictionary wire loop; runtime storage remains conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def dictionary(regions,entry,s,o,*,count):
 if type(count)is not int or not -1<=count<=4:raise ValueError('subgame.dictionary-count-witness')
 p,b,a,c,t=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed','totalLength'));g=BytesPath(regions,entry);g.take('4c89442418','53','55','56','57','4155','4156','4157','4883ec60','4533ff','498bf9','837a'+b+'04','4d8be8','488bda','4c897c2430','4c8bf1','4c897c2438');g.branch('0f8c',False);g.take('488b43'+p,'486328','89ac24a8000000','8b73'+b,'83c6fc');g.branch('0f88',False);g.take('488343'+p+'04','8343'+a+'04','8343'+c+'04','8973'+b,'486343'+c,'488b4b'+t,'482bc8','483bcd');g.branch('0f8c',False);g.take('83fdff');g.branch('0f84',count==-1)
 if count==-1:g.take('498bcd','4d897d00');g.call(s['barrier'])
 else:
  g.take('4c89a424a0000000','4d397d00');g.branch('0f85',False);g.take('488b4f20','ba03000000','4d8b7610','488b89c0000000');g.call(s['classResolve']);g.take('488bc8');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('488b4f20','488b91c0000000','488b4a20','4c397920');g.branch('0f84',False);g.take('488b4720','4d8bc6','8bd5','488bce','4c8b88c0000000','4d8b4920');g.call(s['constructor']);g.take('498bcd','49897500');g.call(s['barrier']);provider=g.relative('488b0d');g.take('4439b9e0000000');g.branch('0f84',False);g.take('488b4720','488b88c0000000','488b4930');g.call(s['provider']);g.take('488b4f20','4c8bf0','488b89c0000000','488b4938');g.call(s['provider']);g.take('4c8be0','85ed');g.branch('0f8e',count==0)
  if count:
   g.take('660f1f840000000000');loop=g.at
   for i in range(count):
    if g.at!=loop:raise ValueError('subgame.dictionary-loop-entry')
    g.take('488b4f20','488b91c0000000','488b4a40','4883793800');g.branch('0f84',False);g.take('0f57c0','0f11442448','33c0','4889442430','4889442438','4d85f6');g.branch('0f84',False);g.take('b905000000','4c8d4c2430','4c8bc3','498bd6');g.call(s['dispatch']);g.take('4d85e4');g.branch('0f84',False);g.take('b905000000','4c8d4c2438','4c8bc3','498bd4');g.call(s['dispatch']);g.take('498b6d00','488b442438','4c8b6c2430','4889442440','4885ed');g.branch('0f84',False);g.take('488b4720','488b88c0000000','488b4148','4883782000');g.branch('0f84',False);g.take('488b4720','488b88c0000000','488b7148','488b4620','488b88c0000000','488b81c0000000','4883782000');g.branch('0f84',False);g.take('488b4620','498bd5','4c8b442440','488bcd','4c8b88c0000000','498b81c0000000','41b102','4889442420');g.call(s['insert']);g.take('4c8bac24b0000000','41ffc7','443bbc24a8000000');g.branch('0f8c',i+1<count)
  g.take('4c8ba424a0000000');g.jump('eb',1)
 g.take('4883c460','415f','415e','415d','5f','5e','5d','5b','c3');return dict(selectedBytes=g.seen,countWitness=count,headerBytes=4,keyOutput='zeroed same RSP+48 -> R13 -> TryInsert.RDX',valueOutput='zeroed same RSP+56 -> RSP+64 -> TryInsert.R8',sameReader='saved RBX passed to both slot5 callbacks',sameDictionary='fresh typed constructor result stored into original output and passed to TryInsert.RCX',insertMode=2,countInvariant='R15D increments once per two normal callbacks and insert; compared to preserved original signed count at RSP+168.',normalReturn=True,condition='Fresh output, sufficient buffered nonwrapping bounds, initialized coherently inflated string/reference contexts, compatible selected key/value providers and slot5 callbacks; normal successful disjoint allocation, constructor(count,comparer), class/context, insertion and barrier helpers. Runtime constructor/table/storage effects and live provider/default selection excluded.')

def null_ulong_list(regions,entry,s,o):
 p,b,a,c,t=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed','totalLength'));g=BytesPath(regions,entry);g.take('4c89442418','53','55','57','4154','4155','4156','4883ec28','4533ed','4d8be1','837a'+b+'04','4d8bf0','488bda','4c896c2468');g.branch('0f8c',False);g.take('488b43'+p,'8b28','8b7b'+b,'83c7fc');g.branch('0f88',False);g.take('488343'+p+'04','8343'+a+'04','8343'+c+'04','897b'+b,'486343'+c,'488b4b'+t,'482bc8','4863c5','483bc8');g.branch('0f8c',False);g.take('83fdff');g.branch('0f84',True);g.take('498bce','4d892e');g.call(s['barrier']);g.take('4883c428','415e','415d','415c','5f','5d','5b','c3');return dict(selectedBytes=g.seen,wireBytes=4,wireCount=-1,output='same incoming R8 cleared to full zero reference',sameReader=True,normalReturn=True,positiveOrEmptyAdmitted=False)

def root(regions,entry,s,*,new=True,null=False):
 g=BytesPath(regions,entry);g.take('48895c2418','56','4883ec20');g.relative('803d');g.take('00','488bda','488bf1');g.branch('75',True,1);g.take('488d542430','c644243000','488bce');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usage=None
 if null:g.take('488bcb','48c70300000000');g.call(s['barrier'])
 else:
  g.take('48897c2438','48833b00');g.branch('0f84',new)
  if new:
   site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['ctor']);g.take('488bcb','48893b');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb67c2430','4080ff01');g.branch('0f84',True);site=g.at;cell=g.relative('488b15');usage=dict(site=site,cell=cell);g.take('488bce','488b1b');g.call(s['packable']);g.take('4885db');g.branch('74',False,1);g.take('4533c0','488bd0','488bcb');g.call(s['setter']);g.take('488b7c2438');g.jump('eb',1)
 g.take('488b5c2440','4883c420','5e','c3');return dict(selectedBytes=g.seen,new=new,null=null,memberCount=1,allocation=allocation,typedDictionaryUsage=usage,sameReaderAndOutput=True,normalReturn=True)

def union_world(regions,entry,s,*,existing=False,null=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742418','57','4883ec20','33f6','498bd8');g.relative('403835');g.take('488bfa');g.branch('0f85',True);g.take('488d542438','6689742438','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);usage=None;class_usage=None
 if null:g.take('488933')
 else:
  g.take('0fb7542438','85d2');g.branch('0f84',False)
  for _ in range(6):g.take('83ea01');g.branch('0f84',False)
  g.take('83ea01');g.branch('74',False,1);g.take('83fa01');g.branch('74',True,1);g.take('488b0b','4885c9');g.branch('74',not existing,1)
  if existing:
   site=g.at;cell=g.relative('488b15');class_usage=dict(site=site,cell=cell);g.take('488b09');g.call(s['assignable']);g.take('84c0');g.branch('74',True,1)
  site=g.at;cell=g.relative('488b15');usage=dict(site=site,cell=cell);g.take('488bcf');g.call(s['packable']);g.take('488903');g.jump('e9')
 g.take('488bcb');g.call(s['barrier']);g.take('488b5c2430','488b742440','4883c420','5f','c3');return dict(selectedBytes=g.seen,selectedTag=None if null else 8,existingIncompatible=existing,typedWrapperUsage=usage,comparisonTypeUsage=class_usage,sameReaderAndOutput=True,normalReturn=True,scope='Current WorldChallenge tag8 or null only; other positive union tags refused.')

def task(regions,entry,s,*,new=True,null=False):
 g=BytesPath(regions,entry);g.take('48895c2410','4889742418','57','4883ec20');g.relative('803d');g.take('00','488bda','488bf1');g.branch('75',True,1);g.take('488d542430','c644243000','488bce');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None
 if null:g.take('488bcb','48c70300000000');g.call(s['barrier'])
 else:
  g.take('48833b00');g.branch('75',not new,1)
  if new:
   site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['ctor']);g.take('488bcb','48893b');g.call(s['barrier'])
  g.take('807c243001');g.branch('75',False,1);g.take('488b1b','488bce');g.call(s['pool']);g.take('4885db');g.branch('75',True,1);g.take('4533c0','488bd0','488bcb');g.call(s['setter']);g.jump('eb',1)
 g.take('488b5c2438','488b742440','4883c420','5f','c3');return dict(selectedBytes=g.seen,new=new,null=null,memberCount=1,allocation=allocation,sameReaderAndOutput=True,taskIdWireEncoding='one pooled Int32 after positive header',normalReturn=True)
