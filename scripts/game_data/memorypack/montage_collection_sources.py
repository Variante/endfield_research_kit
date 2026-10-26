"""Selected current null/empty collection paths; positive elements always refuse."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
def flag(g,prefix="803d"):
 raw=g.read(7)
 if raw[:2]!=bytes.fromhex(prefix) or raw[-1]!=0:raise ValueError('montageList.flag-width-or-value')
 return g.at+int.from_bytes(raw[2:6],'little',signed=True)



def reference_program(regions,entry,offsets,symbols,*,count=0,new=True):
 if type(count) is not int or count not in (-1,0):raise ValueError('montageList.witness-count')
 g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[n],)).hex() for n in ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('4053','55','4155','4156','4157','4883ec30','837a'+rem+'04','4d8bf9','4d8bf0','48c744242000000000','4c8bea');g.branch('7d',True,1)
 g.take('498b45'+cur,'8b28','896c2468','418b5d'+rem,'83c3fc');g.branch('79',True,1)
 g.take('498345'+cur+'04','418345'+adv+'04','418345'+used+'04','41895d'+rem,'496345'+used,'498b4d'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False);g.take('83fdff','0f95c0','84c0');g.branch('0f84',count==-1)
 collectors=[];calls=[]
 if count==-1:
  collectors.append(flag(g,'833d'));g.take('49c70600000000');g.branch('74',True,1)
 else:
  g.take('4889742460','48897c2470','4c89642478','49833e00');g.relative('488d35');g.take('498b4720');g.branch('74',new,1)
  if new:
   g.take('488b88c0000000','488b01','f6803801000001');g.branch('75',True,1);g.take('488bc8');g.call(symbols['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
   g.take('498b4f20','488b91c0000000','488b4a08','4883792000');g.branch('75',True,1);g.take('498b4720','488b88c0000000','488b7908','85ed');g.branch('0f88',False);g.take('488b4720','488b80c0000000');g.branch('0f84',count==0)
   g.take('488b00','f6803801000001');g.branch('75',True,1);g.take('83b8e000000000');g.branch('75',True,1);g.take('488b4720','488b88c0000000','488b01','f6803801000001');g.branch('75',True,1);collectors.append(flag(g,'833d'));g.take('488b80b8000000','488b08','48894b10');g.branch('74',True,1)
   collectors.append(flag(g,'833d'));g.take('49891e');g.branch('74',True,1)
  else:
   g.take('488b90c0000000','498b1e','488b4210','4883782000');g.branch('75',True,1);g.take('498b4720','488bcb','488b90c0000000','488b5210');g.call(symbols['clear']);g.jump('e9')
  provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1);g.take('498b4720','488b88c0000000','488b4918');g.call(symbols['provider']);g.take('33f6','4c8be0','85ed');g.branch('0f8e',count==0)
  g.take('488b7c2470','4c8b642478','488b742460')
 g.take('4883c430','415f','415e','415d','5d','5b','c3')
 if len(set(collectors))>1:raise ValueError('montageList.shared-disabled-collector')
 return dict(selectedBytes=g.seen,countWitness=count,newList=new,elementCallbackSites=calls,headerBytes=4,callbackAbi=dict(reader='r13',output='rsp+32',receiver='r12',methodInfoSlot=408,callbackSlot=400),growthDelegate=False,arrayReferenceStride=8,initialElementOutput=0,normalReturn=True,disabledCollectorCells=collectors,wholeOwnerAdmitted=False)

def value_program(regions,entry,s,*,null=False,new=False):
 g=BytesPath(regions,entry)
 g.take('4c8bdc','53','57','4156','4157','4883ec68','4c8bfa','0f57c0','33c0','498d5310','4533f6','89442450','498bcf','45897310','498bd9','498bf8','0f11442440');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
 if null:
  g.take('488bcf','4c8937');g.call(s['barrier'])
 else:
  g.take('4889ac2490000000','4889b424a0000000','4c89a424a8000000','4c896c2460','8bac2498000000','4c3937');g.branch('0f85',not new)
  if new:
   g.take('488b4b20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False)
   g.take('488b4b20','488b91c0000000','488b4a08','4c397120');g.branch('0f84',False)
   g.take('488b4320','8bd5','488bce','4c8b80c0000000','4d8b4008');g.call(s['constructor']);g.take('488bcf','488937');g.call(s['barrier'])
  else:
   g.take('488b4320','488b37','488b88c0000000','488b4110','4c397020');g.branch('0f84',False);g.take('ff461c','44897618');g.jump('e9')
  g.relative('488b0d');g.take('4439b1e0000000');g.branch('0f84',False);g.take('488b4320','488b88c0000000','488b4918');g.call(s['provider']);g.take('488bf0','85ed');g.branch('7f',False,1)
  g.take('4c8ba424a8000000','488bb424a0000000','4c8b6c2460','488bac2490000000')
 g.take('4883c468','415f','415e','5f','5b','c3')
 return dict(selectedBytes=g.seen,headerWireBytes=4,count=-1 if null else 0,newList=new,elementCallbacks=0,concreteElementFormatterRequired=False,preLoopProviderNormalReturnRequired=not null,elementWireAdmitted=False,condition='Actual closed ListFormatter<T> selected, coherent initialized typed slots, valid disjoint reader/output/frame, sufficient input and normal context/allocation/constructor/provider/barrier helpers; empty provider result is unused.')
