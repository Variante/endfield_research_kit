"""Selected current one-element GameplayTag list transfers; child wire stays separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def list_one(regions,entry,o,s,*,new=True):
 p,b,a,c,t=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed','totalLength'));g=BytesPath(regions,entry);g.take('48895c2420','55','56','57','4155','4156','4883ec20','4533ed','498be9','837a'+b+'04','4d8bf0','488bfa','44896c2458');g.branch('0f8c',False);g.take('488b47'+p,'8b30','8b5f'+b,'83c3fc');g.branch('0f88',False);g.take('488347'+p+'04','8347'+a+'04','8347'+c+'04','895f'+b,'486347'+c,'488b4f'+t,'482bc8','4863c6','483bc8');g.branch('0f8c',False);g.take('83feff');g.branch('0f84',False)
 g.take('4c89642450','4c897c2460','4d392e');g.branch('0f85',not new)
 if new:
  g.take('488b4d20','33d2','488b89c0000000');g.call(s['indexed']);g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False);g.take('488b4d20','488b91c0000000','488b4a08','4c396920');g.branch('0f84',False);g.take('85f6');g.branch('0f88',False);g.take('488b4520','488b88c0000000','4c8b7908','498b4720','488b88c0000000');g.branch('0f85',True);g.take('ba01000000');g.call(s['indexed']);g.take('488bd6','488bc8');g.call(s['arrayAllocate']);g.jump('e9');g.take('488d4b10','48894310');g.call(s['barrier']);g.take('498bce','49891e');g.call(s['barrier'])
 else:
  g.take('488b4520','498b1e','488b88c0000000','488b4110','4c396820');g.branch('75',True,1);g.take('ff431c','44896b18');g.jump('e9')
 class_cell=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False);g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider']);g.take('4c8bf8','458be5','85f6');g.branch('7f',True,1)
 g.take('44896c2458','4d85ff');g.branch('74',False,1);g.take('4c8d4c2458','4c8bc7','498bd7');g.call(s['dispatcher']);g.take('4d8b2e','8b5c2458','4d85ed');g.branch('74',False,1);g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False);g.take('488b4520','8bd3','498bcd','4c8b80c0000000','4d8b4030');g.call(s['add']);g.take('41ffc4','41bd00000000','443be6');g.branch('0f8d',True);g.take('4c8b642450','4c8b7c2460','488b5c2468','4883c420','415e','415d','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,count=1,new=new,headerWireBytes=4,elementWireBytes=None,callbackCount=1,requestedCapacity='unchanged signed count in RSI to array allocator RDX',reader='incoming RDX saved RDI to dispatcher R8',output='incoming R8 saved R14, same list through local->Add RCX',callbackOutput='zeroDWORD frame RSP+88 to dispatcher R9 then unchanged DWORD EDX to typed Add',providerClassCell=class_cell,normalReturn=True,condition='Count exactly one, sufficient nonwrapping buffered Reader, coherent initialized List/array/provider/formatter/Add contexts and compatible nonnull formatter, ordinary noninterfering ABI-preserving helpers. New allocation capacity/initial count and runtime storage effects conditional; positive2+, refill/error/cold contexts excluded.')

def _flag(g):cell=g.relative('803d');g.take('00');return cell

def adapter(regions,entry,s,*,dispatch=False):
 g=BytesPath(regions,entry)
 if dispatch:
  g.take('48895c2408','4889742410','48897c2418','4156','4883ec20','488b0a','4d8bf1','498bf0','488bda');g.call(s['prepare']);g.take('488b3b')
  if g.relative('488d0d')!=s['main']:raise ValueError('tagAdapter.matched-canonical')
  g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
 else:g.take('4889742410','48897c2418','4156','4883ec20');_flag(g);g.take('498bf9','4d8bf0','488bf2');g.branch('0f84',False)
 if dispatch:_flag(g);g.branch('0f84',False)
 g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',False)
 if not dispatch:g.take('48895c2430')
 g.take('488b4720');type_class=g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1);g.take('33d2','488bcb');g.call(s['typeHandle'])
 if not dispatch:g.take('488b5c2430')
 g.take('4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['isValueType']);g.take('84c0');g.branch('75',False,1);g.take('488b4720','488b88c0000000','488b4958');g.call(s['factory']);g.take('488b4f20','4c8bc0','498bd6','4c8b89c0000000','488bce','4d8b4918');g.call(s['notNull'])
 if dispatch:g.take('488b5c2430')
 g.take('488b742438','488b7c2440','4883c420','415e','c3')
 return dict(selectedBytes=g.seen,dispatch=dispatch,typeClassCell=type_class,reader='incoming RDX or dispatcher R8, unchanged RSI to NotNull RCX',output='incoming R8 or dispatcher R9, unchanged R14 to NotNull RDX',factory='same class context VAR1 Activator MethodSpec, result passed R8',contextSlot=3,normalReturn=True,condition='Initialized metadata/type class; nonnull wire marker, reference W class with IsValueType false, compatible normal noninterfering helpers/factory and coherent adapter context; matched slot5 pointer for dispatcher. Factory runtime effects/live selection excluded.')

def not_null(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec20');_flag(g);g.take('498bf9','488bf2','488bd9');g.branch('0f84',False);provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b4920');g.call(s['hotProvider']);g.take('4885c0');g.branch('74',False,1);g.take('b905000000','4c8d4c2440','4c8bc3','488bd0');g.call(s['dispatch']);g.take('488b5c2440','4885db');g.branch('74',False,1);g.take('488b4f20');g.call(s['context']);g.take('ba08000000','488b88c0000000');g.call(s['indexed']);g.take('488bd0','33c9','4c8bc3');g.call(s['conversion']);g.take('488b5c2430','8906','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,providerClassCell=provider,reader='incoming RCX->RBX->slot5 R8',output='incoming RDX->RSI, full DWORD EAX stored through same RSI',wrapper='incoming R8 saved to entry RSP+24, same frame RSP+64 address to slot5 R9, returned wrapper RBX into conversion R8',contexts=dict(provider=4,conversionInterface=8),normalReturn=True,condition='Coherent initialized context, compatible nonnull wrapper formatter/provider and wrapper callback result, ordinary noninterfering helper ABI. All callback/conversion semantics and concrete runtime inflation remain separate.')

def conversion(regions,entry,prepare,*,ordinal):
 if type(ordinal)is not int or not 0<=ordinal<=32:raise ValueError('tagConversion.ordinal')
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b38','498bf0','0fb7e9','488bda','488bcf');g.call(prepare);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
 for i in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
  if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7','4c8b00','488bce','488b5008','488b5c2430','488b6c2438','488b742440','4883c420','5f','49ffe0')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,selector=0,tail='selected interface callback R8, same wrapper receiver RCX, same slot MethodInfo RDX, unchanged callback result EAX to caller',normalReturnViaTail=True,condition='Exact coherent current wrapper interface match at declared ordinal, valid receiver/class/interface records and ordinary preparation/getter ABI; callbacks/runtime records remain conditional.')

def wrapper(regions,entry,s,*,new=True):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20');_flag(g);g.take('488bda','488bf9');g.branch('74',False,1);g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',False);g.take('48833b00');g.branch('0f84',new)
 cell=None
 if new:cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False);g.take('33c9','894810','488bcb','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
 g.take('807c243001');g.branch('0f85',False);g.take('488b1b','488bcf');g.call(s['integer']);g.take('4885db');g.branch('74',False,1);g.take('894310','488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,new=new,allocationClassCell=cell,memberCount=1,field='same full Int32 returned EAX to wrapper holder+16',wireBytes=5,reader='incoming RCX saved RDI to actual header and integer helpers',normalReturn=True,condition='Initialized metadata, positive MC1, valid nonoverflowing buffered Reader, normal disjoint typed allocation/barrier helpers, incoming wrapper null for new or coherent existing wrapper. Header/Int32 source and factory/static/callback joins remain separate.')

def add(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','ff411c','8bda','488b5110','498bf0','48634118','488bf9','4885d2');g.branch('74',False,1);g.take('3b4218');g.branch('73',False,1);g.take('8d4801','894f18','3b4218');g.branch('73',False,1);g.take('895c8220','488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,value='incoming DWORD EDX saved EBX unchanged at same array+32+4*oldCount',count='old signed count RAX→count+1 at+24',versionSlot=28,arrayStride=4,normalReturn=True,condition='Valid coherent List/array, nonnegative current count strictly below capacity, no overflow; storage effects direct, allocation/growth/runtime execution excluded.')


def peek_null(regions,entry,o):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','8379'+bytes((o['bufferLength'],1)).hex(),'488bd9');g.branch('0f8c',False);g.take('488b43'+bytes((o['currentPtr'],)).hex(),'8038ff','0f94c0','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,wireBytes=0,comparison=255,normalReturn=True,condition='At least one buffered input byte, noninterfering valid Reader; returns comparison to FF with no cursor/output writes.')

def read_null_positive(regions,entry,peek):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','c644243000');g.call(peek);g.take('84c0');g.branch('0f85',False);g.take('4883c420','5b','c3')
 return dict(selectedBytes=g.seen,wireBytes=0,returnsFalseForPositive=True,normalReturn=True,condition='Actual independently proved PeekIsNull returns false on non-FF; unchanged Reader, no cursor/output writes, compatible ordinary ABI.')
