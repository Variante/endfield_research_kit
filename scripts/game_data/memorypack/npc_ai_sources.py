"""Current AI48 selected source/copy programs; callers prove types and native inputs."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def getter(regions,entry):
 g=BytesPath(regions,entry);g.take('0f104210','488bc1','0f104a20','0f1101','0f104230','0f114910','0f114120','c3')
 return dict(selectedBytes=g.seen,source='incoming RDX wrapper+16',destination='incoming RCX hidden48 output',copiedBytes=48,result='same output pointer',normalReturn=True,condition='Nonnull correctly typed wrapper, disjoint valid output; managed value/reference ownership is separately proved.')

def constructor(regions,entry):
 g=BytesPath(regions,entry);g.take('0f57c0','0f114110','0f114120','0f114130','c3')
 return dict(selectedBytes=g.seen,zeroedBytes=48,firstOffset=16,normalReturn=True)

def reader(regions,entry,s,*,null=False,allocated=False):
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec30');flag=g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f84',False)
 g.take('488d542440','c644244000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
 if null:
  g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742448','48833b00');g.branch('0f84',allocated)
  allocation=None
  if allocated:
   allocation=dict(site=g.at,cell=g.relative('488b0d'));g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False);g.take('0f57c0','488bcb','0f114010','0f114020','0f114030','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb6742440','4080fe06');g.branch('0f85',False)
  g.take('488b33','488bcf');g.call(s['single']);g.take('4885f6');g.branch('0f84',False);g.take('f30f114628','488bcf','488b33');g.call(s['pool']);g.take('4885f6');g.branch('0f84',False);g.take('488d4e10','488901');g.call(s['barrier'])
  g.take('488b33','488bcf');g.call(s['long']);g.take('4885f6');g.branch('74',False,1);g.take('48894620','488bcf','488b33');g.call(s['pool']);g.take('4885f6');g.branch('74',False,1);g.take('488d4e18','48894618');g.call(s['barrier'])
  enum=dict(site=g.at,cell=g.relative('488b15'));g.take('488bcf','488b33');g.call(s['enum']);g.take('4885f6');g.branch('74',False,1);g.take('894638','488d4c2420');vector=dict(site=g.at,cell=g.relative('4c8b05'));g.take('488bd7','488b1b');g.call(s['vector']);g.take('4885db');g.branch('74',False,1)
  g.take('f20f10442420','8b442428','488b742448','f20f11432c','894334')
 g.take('488b5c2450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,initializerFlag=flag,allocation=None if null else allocation,enumContext=None if null else enum,vectorContext=None if null else vector,fieldOrder=[]if null else['floatValue','key','longValue','stringValue','valueType','vector3Value'],wrapperResult='null'if null else'existing or newly zeroed inline48 wrapper',wireMemberCount=None if null else 6,normalFrameAndReturn=True,condition='Initialized metadata, buffered header helper and scalar/pool/Vector3 sources separately proved; normal noninterfering helper/barrier/allocation effects and valid disjoint storage. Null wrapper semantics for the original value require a separate adapter-default proof.')

def dictionary(regions,entry,o,s,*,null=False,count=1):
 if type(count)is not int or count not in(0,1):raise ValueError('npcAI.dictionary-selected-count')
 g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((o[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'));g.take('4053','55','56','57','4155','4156','4881ecb8000000');flag=g.relative('803d');g.take('00','498be8','4c8bf2','488bd9');g.branch('0f84',False)
 g.take('0f57c0','4533ed','837b'+rem+'01','4c89ac24f0000000','0f11442420','0f11442430','0f11442440');g.branch('0f8c',False);g.take('488b43'+cur,'0fb630','8b7b'+rem,'83ef01');g.branch('0f88',False);g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'897b'+rem,'4080feff');g.branch('0f84',null)
 if null:
  g.take('498bce','4d892e');g.call(s['barrier'])
 else:
  g.take('4c89a424f8000000','4c89bc24b0000000','4d392e');g.branch('75',False,1);g.take('488b4d20');g.call(s['context']);g.take('ba15000000','488b88c0000000');g.call(s['type']);g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
  g.take('488b4d20');g.call(s['context']);g.take('488b88c0000000','488b91b0000000','4c396a20');g.branch('0f84',False);g.take('488b4d20');g.call(s['context']);g.take('488bcf','488b90c0000000','488b92b0000000');g.call(s['constructor']);g.take('498bce','49893e');g.call(s['barrier'])
  provider=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False)
  g.take('488b4d20');g.call(s['context']);g.take('488b88c0000000','488b89b8000000');g.call(s['keyProvider']);g.take('488b4d20','4c8bf8');g.call(s['context']);g.take('488b88c0000000','488b89c0000000');g.call(s['valueProvider'])
  g.take('837b'+rem+'04','4c8be0');g.branch('0f8c',False);g.take('488b43'+cur,'8b30','8b7b'+rem,'83c7fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'418bfd','85f6');g.branch('0f8e',count==0)
  if count:
   g.take('4c89ac24f0000000','4d85ff');g.branch('0f84',False);g.take('b905000000','4c8d8c24f0000000','4c8bc3','498bd7');g.call(s['keyDispatch']);g.take('0f57c0','0f11442420','0f11442430','0f11442440','4d85e4');g.branch('0f84',False);g.take('4c8d4c2420','4c8bc3','498bd4');g.call(s['valueDispatch'])
   g.take('0f10442420','4d8b2e','488b8424f0000000','4889842408010000','0f11442450','0f10442430','0f11442460','0f10442440','0f11442470','4d85ed');g.branch('0f84',False);g.take('488b4d20');g.call(s['context']);g.take('488b88c0000000','488b4128','4883782000');g.branch('0f84',False)
   g.take('0f10442450','488b4d20','0f104c2460','0f29842480000000','0f10442470','0f298c2490000000','0f298424a0000000');g.call(s['context']);g.take('488b942408010000','4c8d842480000000','498bcd','4c8b88c0000000','4d8b4928');g.call(s['setItem']);g.take('ffc7','41bd00000000','3bfe');g.branch('0f8c',False)
  g.take('4c8ba424f8000000','4c8bbc24b0000000');g.jump('eb',1)
 g.take('4881c4b8000000','415e','415d','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,initializerFlag=flag,count=None if null else count,headerBytes=1,countBytes=0 if null else 4,valueBytes=48,keyOutput='stack+240',valueOutput='stack+32',setItemValueArgument='stack+128 after three complete 48-byte copies',newDictionary=True,normalFrameAndReturn=True,condition='Matching initialized closed contexts, initially null output, coherent buffered Reader; separately proved matching pooled-string and AI48 callbacks; normal noninterfering context/type/allocation/constructor/provider/barrier/set_Item effects preserving Win64 nonvolatile state. Only FF, new zero and new single-entry paths; other counts, preexisting contents and live/default provider choice remain unproved.')


def adapter(regions,entry,s,*,dispatch=False):
 g=BytesPath(regions,entry)
 if dispatch:
  g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda');g.call(s['prepare']);g.take('488b3b')
  if g.relative('488d0d')!=s['main']:raise ValueError('npcAI.adapter-slot-five-callback')
  g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False);flag=g.relative('803d');g.take('00');g.branch('0f84',False)
 else:
  g.take('48896c2410','4889742418','57','4883ec20');flag=g.relative('803d');g.take('00','498bf9','498be8','488bf2');g.branch('0f84',False)
 g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',False)
 if not dispatch:g.take('48895c2430')
 g.take('488b4720');provider=g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1);g.take('33d2','488bcb');g.call(s['typeFromHandle'])
 if not dispatch:g.take('488b5c2430')
 g.take('4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['isValueType']);g.take('84c0');g.branch('75',False,1);g.take('488b4720','488b88c0000000','488b4958');g.call(s['factory']);g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
 if dispatch:g.take('488b5c2430')
 g.take('488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,dispatch=dispatch,metadataFlag=flag,providerClassCell=provider,reader='incoming R8'if dispatch else'incoming RDX',output48='incoming R9'if dispatch else'incoming R8',nonnullArguments=dict(rcx='same reader',rdx='same output48',r8='factory wrapper reference',r9='closed DeserializeNotNull MethodInfo slot3'),normalReturn=True,condition='Ready matching concrete reference wrapper contexts and original slot5 callback/MethodInfo; ReadIsNull false on MC6 without consuming; normal reflected type is reference wrapper and matching factory returns it; ordinary preparation/provider/allocation helpers. Live receiver/provider selection remains unproved.')


def nonnull(regions,entry,s,*,wrapper_null=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec50');flag=g.relative('803d');g.take('00','498bf9','488bf2','488bd9');g.branch('0f84',False);provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider']);g.take('4885c0');g.branch('0f84',False);g.take('b905000000','4c8d4c2470','4c8bc3','488bd0');g.call(s['wrapperDispatch']);g.take('488b5c2470','4885db');g.branch('0f84',wrapper_null)
 if wrapper_null:g.take('0f57c0','0f1106','0f114610','0f114620');g.jump('e9')
 else:
  g.take('488b4f20');g.call(s['context']);g.take('ba08000000','488b88c0000000');g.call(s['type']);g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion']);g.take('488bce','0f1000','0f104810','0f105020','0f1106','0f114e10','0f115620');g.call(s['barrier'])
 g.take('488b5c2460','488b742468','4883c450','5f','c3')
 return dict(selectedBytes=g.seen,metadataFlag=flag,providerClassCell=provider,wrapperNull=wrapper_null,copiedBytes=48,reader='incoming RCX',output='incoming RDX',wrapperLocal='entry RSP+24 initialized from incoming R8',conversionOutput='stack+32 copied completely to original output',normalReturn=True,condition='Matched closed adapter slots4/8, wrapper slot5 and actual GetValue; normal noninterfering context/provider/preparation/conversion/barrier effects. Runtime provider selection remains conditional.')


def conversion(regions,entry,*,prepare,ordinal):
 if type(ordinal)is not int or not 0<=ordinal<64:raise ValueError('npcAI.interface-ordinal')
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','48897c2418','4156','4883ec50','498b39','488bf1','488bcf','4d8bf1','498bd8');g.call(prepare);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
 for i in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
  if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7','4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1','488b5c2460','488b7c2470','0f1000','0f104810','0f1106','0f104020','488bc6','0f114e10','0f114620','488b742468','4883c450','415e','c3')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,callbackABI=dict(rcx='hidden48 stack output',rdx='same incoming R9 wrapper',r8='matched GetValue MethodInfo'),copiedBytes=48,result='incoming RCX output48',normalReturn=True,condition='Exact concrete wrapper class, coherent interface-offset table and corresponding GetValue vtable; independently checked current ordinal/type/method identity; ordinary class preparation and valid output storage.')


def peek(regions,entry,o):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','8379'+bytes((o['bufferLength'],1)).hex(),'488bd9');g.branch('0f8c',False);g.take('488b43'+bytes((o['currentPtr'],)).hex(),'8038ff','0f94c0','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,consumedBytes=0,returnsHeaderEquals255=True,normalReturn=True,condition='Valid buffered reader with at least one available byte, stable source and frame.')


def read_null(regions,entry,*,peek,header,null=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','c644243000');g.call(peek);g.take('84c0');g.branch('0f85',null)
 if null:g.take('488d542430','488bcb');g.call(header);g.take('b001');g.jump('e9')
 g.take('4883c420','5b','c3')
 return dict(selectedBytes=g.seen,consumedBytes=1 if null else 0,returnsNull=null,normalReturn=True,condition='Independently proved buffered peek and header using same Reader; noninterfering normal callees and valid distinct stack output.')


def forwarder(regions,entry,reader):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag=g.relative('803d');g.take('00','498bd8','488bfa');g.branch('74',False,1);cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1);g.take('4533c0','488bd3','488bcf','488b5c2430','4883c420','5f')
 if g.relative('e9')!=reader:raise ValueError('npcAI.wrapper-forwarded-reader')
 return dict(selectedBytes=g.seen,metadataFlag=flag,wrapperClassCell=cell,reader='incoming RDX',outWrapper='incoming R8',zeroMethodInfo=True,normalTailReturn=True,condition='Initialized exact wrapper class and normal incoming formatter ABI.')


def set_item(regions,entry,insert):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec60','498b4120','498bd9','498bf8','488bf2','488be9','4c8b88c0000000','498b81c0000000','4883782000');g.branch('0f84',False);g.take('488b4320','4c8d442430','0f1007','41b101','488bd6','0f104f10','488b88c0000000','0f29442430','0f104720','488b81c0000000','488bcd','4889442420','0f294c2440','0f29442450');g.call(insert);g.take('488b5c2470','488b6c2478','488bb42480000000','4883c460','5f','c3')
 return dict(selectedBytes=g.seen,key='incoming RDX unchanged',value='all48 incoming R8 bytes copied to stack+48',receiver='incoming RCX unchanged',insertMode=1,normalReturn=True,condition='Matching initialized dictionary generic context; normal TryInsert/helper/storage effects. This is set_Item overwrite mode, never an Add/absence proof.')


def value_provider(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1);provider=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeFromHandle']);root=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1);g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['type']);g.take('488bd0','488bcb');g.call(s['cast']);g.take('4885c0');g.branch('0f84',False);g.take('488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,providerClassCell=provider,rootClassCell=root,typeofContextSlot=0,formatterContextSlot=1,result='same backend result accepted by exact formatter-class cast',normalReturn=True,condition='Initialized GetFormatter<T> method context with current type and MemoryPackFormatter<T> slots; normal type-handle/backend/indexed-type/cast effects returning nonnull matching formatter. No runtime/default provider choice is proved.')
