"""Selected null/new-zero dictionary paths; construction/provider effects stay conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def _peek(g,n):return bytes(g.bytes.get(g.at+i,0) for i in range(n)).hex()
def _branch(g,short,long,taken):
 if _peek(g,1)==short:g.branch(short,taken,1)
 else:g.branch(long,taken)
def _flag(g):
 g.take('803d');cell=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00');return cell
def _uint_end(g,full):
 if full:g.take('4c8b742438','4c8b642440','488b6c2478','4c8b7c2430')
 g.take('4883c448','415d','5f','5e','5b','c3')
def uint_reference(regions,entry,o,s,*,null=False):
 g=BytesPath(regions,entry);g.take('4053','56','57','4155','4883ec48');flag=_flag(g);g.take('498bf8','488bf2','488bd9');_branch(g,'74','0f84',False)
 g.take('4533ed','c644247000','488d542470','44896c2420','488bcb','4c896c2428');g.call(s['header']);g.take('807c2470ff');_branch(g,'74','0f84',null)
 if null:
  g.take('488bce','4c892e');g.call(s['barrier']);g.take('90');g.jump('e9');_uint_end(g,False)
 else:
  g.take('48896c2478','4c89642440','4c89742438','4c897c2430','4c392e');_branch(g,'75','0f85',False)
  g.take('488b4f20');g.call(s['context']);g.take('ba15000000','488b88c0000000');g.call(s['type']);g.take('488bc8');g.call(s['allocate']);g.take('488be8','4885c0');_branch(g,'74','0f84',False)
  g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b91b0000000','4c396a20');_branch(g,'74','0f84',False)
  g.take('488b4f20');g.call(s['context']);g.take('488bcd','488b90c0000000','488b92b0000000');g.call(s['constructor']);g.take('488bce','48892e');g.call(s['barrier'])
  owner=g.relative('488b0d');g.take('4439a9e0000000');_branch(g,'74','0f84',False)
  g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b89b8000000');g.call(s['keyProvider']);g.take('488b4f20','4c8bf8');g.call(s['context']);g.take('488b88c0000000','488b89c0000000');g.call(s['valueProvider'])
  g.take('837b'+bytes((o['bufferLength'],4)).hex(),'4c8be0');_branch(g,'7c','0f8c',False)
  g.take('488b43'+bytes((o['currentPtr'],)).hex(),'448b30','8b6b'+bytes((o['bufferLength'],)).hex(),'83c5fc');_branch(g,'78','0f88',False)
  for code,key in [('488343','currentPtr'),('8343','advancedCount'),('8343','consumed')]:g.take(code+bytes((o[key],4)).hex())
  g.take('896b'+bytes((o['bufferLength'],)).hex(),'418bed','4585f6');_branch(g,'7f','0f8f',False);_uint_end(g,True)
 return dict(selectedBytes=g.seen,initializerFlag=flag,bytesConsumed=1 if null else 5,output='null' if null else 'fresh typed constructor result',elementCallbacks=0,providerResultsUsed=False,entryRspRestored=True,wholeOwnerAdmitted=False,condition='Initialized selected native contexts; sufficient contiguous input and nonoverflowing reader counters; source header FF for null or non-FF/zero count for new-zero; incoming output pointer initially null; coherent typed allocation/context/constructor and ordinary noninterfering helper/provider returns preserving Win64 nonvolatile registers. Positive entries, initialized nonempty output contents, live provider choice and owner admission remain unproved.')

def reference_reference(regions,entry,o,s,*,null=False):
 g=BytesPath(regions,entry);g.take('4053','55','56','57','4154','4156','4883ec58');flag=_flag(g);g.take('498bf0','4c8be2','488bd9');_branch(g,'75','0f85',True)
 g.take('4533f6','837b'+bytes((o['bufferLength'],1)).hex(),'4c89b424a8000000','4c89742430');_branch(g,'7d','0f8d',True)
 g.take('488b43'+bytes((o['currentPtr'],)).hex(),'0fb628','8b7b'+bytes((o['bufferLength'],)).hex(),'83ef01');_branch(g,'79','0f89',True)
 for code,key in [('48ff43','currentPtr'),('ff43','advancedCount'),('ff43','consumed')]:g.take(code+bytes((o[key],)).hex())
 g.take('897b'+bytes((o['bufferLength'],)).hex(),'4080fdff');_branch(g,'74','0f84',null)
 if null:
  g.take('498bcc','4d893424');g.call(s['barrier'])
 else:
  g.take('4d393424');_branch(g,'75','0f85',False)
  g.take('488b4e20');g.call(s['context']);g.take('ba15000000','488b88c0000000');g.call(s['type']);g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');_branch(g,'74','0f84',False)
  g.take('488b4e20');g.call(s['context']);g.take('488b88c0000000','488b81b0000000','4c397020');_branch(g,'75','0f85',True)
  g.take('488b4e20');g.call(s['context']);g.take('488bcf','488b90c0000000','488b92b0000000');g.call(s['constructor'])
  collector=g.relative('443935');g.take('49893c24');_branch(g,'74','0f84',True)
  owner=g.relative('488b0d');g.take('4c89ac2498000000','4c897c2450','4439b1e0000000');_branch(g,'75','0f85',True)
  for role,result in [('keyProvider','4c8bf0'),('valueProvider',None)]:
   g.take('488b4620','f6803801000001');_branch(g,'75','0f85',True)
   g.take('488b88c0000000','488b89'+('b8000000' if role=='keyProvider' else 'c0000000'));g.call(s[role])
   if result:g.take(result)
  g.take('837b'+bytes((o['bufferLength'],4)).hex(),'4c8bf8');_branch(g,'7d','0f8d',True)
  g.take('488b43'+bytes((o['currentPtr'],)).hex(),'8b28','89ac2490000000','8b7b'+bytes((o['bufferLength'],)).hex(),'83c7fc');_branch(g,'79','0f89',True)
  for code,key in [('488343','currentPtr'),('8343','advancedCount'),('8343','consumed')]:g.take(code+bytes((o[key],4)).hex())
  g.take('897b'+bytes((o['bufferLength'],)).hex(),'33ff','448bef','85ed');_branch(g,'7e','0f8e',True);g.take('4c8bac2498000000','4c8b7c2450')
 g.take('4883c458','415e','415c','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,initializerFlag=flag,bytesConsumed=1 if null else 5,output='null' if null else 'fresh typed constructor result',elementCallbacks=0,providerResultsUsed=False,entryRspRestored=True,wholeOwnerAdmitted=False,condition='Selected original buffered code, initialized metadata/owner and context slots, absent collector effects, valid disjoint reader/output/storage and count0 or FF input; output initially null; coherent typed allocation/constructor and ordinary context/provider/barrier helpers preserving nonvolatile state. Positive entries and preexisting populated dictionary contents are outside the selected grammar.')
