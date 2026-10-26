"""Selected initialized mask transfers; runtime provider selection stays conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def hash_program(regions,entry,offsets):
 g=BytesPath(regions,entry);cur,rem,adv,used=(bytes([offsets[k]]).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('48895c2408','4889742410','57','4883ec20','8379'+rem+'08','488bf9');g.branch('0f8c',False)
 g.take('488b5f'+cur,'488b1b','8b77'+rem,'83c6f8');g.branch('0f88',False)
 g.take('488347'+cur+'08','8347'+adv+'08','8347'+used+'08','8977'+rem,'488b742438','488bc3','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,valueBytes=8,wireBytes=8,readerOffsets=offsets,condition='Buffered eight bytes; coherent Reader, nonoverflowing counters.')


def peek_program(regions,entry,offsets):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','8379'+bytes([offsets['bufferLength']]).hex()+'01','488bd9');g.branch('0f8c',False)
 g.take('488b43'+bytes([offsets['currentPtr']]).hex(),'8038ff','0f94c0','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,consumedBytes=0,result='first buffered byte equals FF')


def getter_program(regions,entry):
 g=BytesPath(regions,entry);g.take('0f104210','488bc1','0f1101','c3')
 return dict(selectedBytes=g.seen,sourceOffset=16,resultBytes=16,hiddenResult='incoming RCX, returned RAX',wrapper='incoming RDX')


def default_program(regions,entry):
 g=BytesPath(regions,entry);g.take('0f57c0','0f114110','c3');return dict(selectedBytes=g.seen,zeroBytes=16,wrapperOffset=16)


def child_program(regions,entry,s,*,new=False,null=False):
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec20');g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f84',False)
 g.take('488d542430','c644243000','488bcf');g.call(s['objectHeader']);g.take('84c0');g.branch('0f84',null);allocation=None;hash_context=None
 if null:
  g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742438','48833b00');g.branch('0f84',new)
  if new:
   allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False);g.take('0f57c0','488bcb','0f114010','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb6742430','4080fe02');g.branch('0f85',False);g.take('488b33','488bcf');g.call(s['pooled']);g.take('4885f6');g.branch('74',False,1)
  g.take('488d4e18','48894618');g.call(s['barrier']);hash_context=g.at;g.relative('488b15');g.take('488bcf','488b1b');g.call(s['hash']);g.take('4885db');g.branch('74',False,1);g.take('488b742438','48894310')
 g.take('488b5c2440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,new=new,null=null,allocationUsageSite=allocation,hashUsageSite=hash_context,fieldOrder=[]if null else['layerName','maskPath'],wireBytes=1 if null else 13,condition='Initialized metadata; MC2 or FF; normal header/pool/barrier/allocation helpers and stable disjoint wrapper storage. New wrapper zero16 differs from reused remaining bits.')


def forwarder_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','498bd8','488bfa');g.branch('74',False,1);owner=g.at;g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
 g.take('4533c0','488bd3','488bcf','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['child']:raise ValueError('animationMask.forwarder-target')
 return dict(selectedBytes=g.seen,wrapperUsageSite=owner,sameReaderAndOutput=True,condition='Initialized metadata and wrapper class.')


def conversion_program(regions,entry,prepare,*,ordinal):
 if type(ordinal)is not int or not 0<=ordinal<=4:raise ValueError('animationMask.interface-ordinal')
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec30','498b39','488be9','488bcf','498bf1','498bd8');g.call(prepare)
 g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
 for i in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
  if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7','4c8b08','488d4c2420','4c8b4008','488bd6','41ffd1','488b5c2440','488b742450','0f1000','488bc5','0f114500','488b6c2448','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,resultBytes=16,sameHiddenResult=True,condition='Typed matched interface and preceding mismatches; normal prepare/GetValue returns. No interface fallback.')


def list_program(regions,entry,s,*,count,new=True):
 if type(count)is not int or count not in(-1,0,1):raise ValueError('animationMask.list-profile')
 g=BytesPath(regions,entry);g.take('4053','57','4156','4157','4883ec58');g.relative('803d');g.take('00','498bd9','498bf8','4c8bf2');g.branch('0f84',False)
 g.take('0f57c0','488d942488000000','4533ff','498bce','4489bc2488000000','0f11442420');g.call(s['collectionHeader']);g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:
  g.take('488bcf','4c893f');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889b42490000000','4889ac2480000000','4c89642450','0f29742440','8bb42488000000','4c393f');g.branch('0f85',not new)
  if new:
   g.take('488b4b20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
   g.take('488b4b20','488b91c0000000','488b4a08','4c397920');g.branch('0f84',False);g.take('488b4320','8bd6','488bcd','4c8b80c0000000','4d8b4008');g.call(s['constructor']);g.take('488bcf','48892f');g.call(s['barrier'])
  else:
   g.take('488b4320','488b2f','488b90c0000000','488b4210','4c397820');g.branch('75',True,1);g.take('488b4320','488bcd','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
  provider=g.at;g.relative('488b0d');g.take('4439b9e0000000');g.branch('0f84',False);g.take('488b4320','488b88c0000000','488b4918');g.call(s['provider']);g.take('488be8','85f6');g.branch('7f',count==1,1)
  if count:
   g.take('0f57c0','0f11442420','4885ed');g.branch('74',False,1);g.take('4c8d4c2420','4d8bc6','488bd5');g.call(s['dispatch']);g.take('4c8b27','0f28742420','4d85e4');g.branch('74',False,1)
   g.take('488b4320','488b88c0000000','488b4130','4883782000');g.branch('0f84',False);g.take('488b4320','488d542430','498bcc','660f7f742430','4c8b80c0000000','4d8b4030');g.call(s['add']);g.take('41ffc7','443bfe');g.branch('0f8d',True)
  g.take('4c8b642450','488bac2480000000','0f28742440','488bb42490000000')
 g.take('4883c458','415f','415e','5f','5b','c3')
 return dict(selectedBytes=g.seen,count=count,new=new,elementRuntimeBytes=16,elementWireBytes=None,condition='Only null/zero/one; initialized selected contexts and provider; fresh constructor capacity1 or reused count0/capacity>=1; normal typed callbacks. No growth/general loop claim.')


def null_program(regions,entry,s,*,null=False):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','c644243000');g.call(s['peek']);g.take('84c0');g.branch('0f85',null)
 if null:g.take('488d542430','488bcb');g.call(s['objectHeader']);g.take('b001');g.jump('e9')
 g.take('4883c420','5b','c3');return dict(selectedBytes=g.seen,null=null,consumedBytes=int(null))


def adapter_program(regions,entry,s,*,inline=False,null=False,create=False):
 g=BytesPath(regions,entry)
 if inline:
  g.take('48895c2408','48896c2410','4889742418','57','4883ec20','488b0a','498be9','498bf0','488bda');g.call(s['prepare']);g.take('488b3b')
  if g.relative('488d0d')!=s['adapter']:raise ValueError('animationMask.inline-adapter-selection')
  g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False);g.relative('803d');g.take('00');g.branch('0f84',False)
 else:
  g.take('48896c2410','4889742418','57','4883ec20');g.relative('803d');g.take('00','498bf9','498be8','488bf2');g.branch('0f84',False)
 g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',null)
 if null:g.take('0f57c0','0f114500');g.jump('e9')
 else:
  if not inline:g.take('48895c2430')
  g.take('488b4720');type_owner=g.at;g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1);g.take('33d2','488bcb');g.call(s['typeHandle'])
  if not inline:g.take('488b5c2430')
  g.take('4885c0');g.branch('74',False,1);g.take('33d2','488bc8');g.call(s['creationTest']);g.take('84c0');g.branch('75',not create,1)
  if create:g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
  else:g.take('33c0');g.jump('eb',1)
  g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['notNull'])
 if inline:g.take('488b5c2430')
 g.take('488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,inline=inline,null=null,create=create,outputBytes=16,reader='original incoming RDX',condition='Initialized typed adapter; fixed slot5 selected exact adapter in inline form. Normal ReadIsNull/TypeFromHandle/creation-test/activation/NotNull ABIs; no runtime provider/creation selection assertion.')


def not_null_program(regions,entry,s,*,zero=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec30');g.relative('803d');g.take('00','498bf9','488bf2','488bd9');g.branch('0f84',False)
 owner=g.at;g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider']);g.take('4885c0');g.branch('0f84',False)
 g.take('b905000000','4c8d4c2450','4c8bc3','488bd0');g.call(s['ordinaryDispatch']);g.take('488b5c2450','4885db');g.branch('74',zero,1)
 if zero:g.take('0f57c0','0f1106');g.jump('eb',1)
 else:
  g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['context']);g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion']);g.take('488d4e08','0f1000','0f1106');g.call(s['barrier'])
 g.take('488b5c2440','488b742448','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,wrapperNull=zero,wrapperProviderUsageSite=owner,resultBytes=16,referenceLaneOffset=8,condition='Initialized owned context; normal selected wrapper-provider and ordinary slot5 dispatch. Conversion interface returns exact16; sole reference lane+8 gets barrier. No live provider selection.')


def capacity_program(regions,entry,s,*,positive=True):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False);g.take('498b4820','488b89c0000000');g.branch('75',positive,1)
 if positive:g.take('ba01000000');g.call(s['context']);g.take('488bd3','488bc8');g.call(s['arrayAllocate']);g.jump('eb',1)
 else:
  g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('74',False,1);g.take('488b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01')
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('animationMask.capacity-barrier')
 return dict(selectedBytes=g.seen,positiveCapacity=positive,arrayContextSlot=int(positive),itemsOffset=16,condition='New zeroed typed List; typed allocation/ready static empty array and normal barrier. No allocation execution claim.')


def add_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec30','ff411c','498bf0','4c8b4910','488bfa','48634118','488bd9','4d85c9');g.branch('74',False,1);g.take('413b4118');g.branch('0f83',False)
 g.take('8d4801','894b18','413b4118');g.branch('73',False,1);g.take('0f1002','488d4802','4803c9','410f1104c9','488bc8','48c1e104','4883c128','4903c9');g.call(s['barrier']);g.take('488b5c2440','488b742448','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,elementBytes=16,referenceLaneOffset=8,arrayDataOffset=32,arrayStride=16,countOffset=24,condition='Coherent typed List/array; initial count0 and capacity>=1. Exact16 copy, barrier to reference lane+8; no growth.')


def registration_prefix(regions,entry,s):
 g=BytesPath(regions,entry);allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False);constructor=g.at;g.relative('4c8b05')
 g.take('498b4820','488b91c0000000','488b4a60','4883792000');g.branch('75',True,1);type_owner=g.at;g.relative('488b0d');key=g.at;g.relative('488b1d');g.take('83b9e000000000');g.branch('75',True,1);g.take('33d2','488bcb');g.call(s['typeHandle']);provider=g.at;g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('75',True,1);g.take('4533c0','488bd3','488bcf');g.call(s['registerWrap'])
 return dict(selectedBytes=g.seen,allocationUsageSite=allocation,constructorUsageSite=constructor,keyUsageSite=key,typeOwnerUsageSite=type_owner,providerUsageSite=provider,afterRegister=g.at,condition='Owned Init selected initialized base constructor/Type/provider context, normal nonnull allocator and TypeFromHandle and RegisterWrap ABI. Exact allocated formatter RDI and original Type RAX reach RegisterWrap together. Prefix only; no Init execution, dictionary outcome or live provider selection.')


def root_prefix(regions,entry,s,reads,setters,*,new=False):
 if len(reads)!=5 or len(setters)!=5:raise ValueError('animationMask.root-prefix-shape')
 g=BytesPath(regions,entry);g.take('4053','55','57','4883ec30');g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f84',False)
 g.take('33ed','c644245000','488d542450','48896c2468','488bcf','48896c2420','48896c2428');g.call(s['objectHeader']);g.take('84c0');g.branch('0f84',False)
 g.take('4889742458','48392b');g.branch('0f84',new);allocation=None
 if new:
  allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False);g.take('33d2','488bc8');g.call(s['rootConstructor']);g.take('488bcb','488933');g.call(s['barrier']);g.take('90');g.jump('e9')
 g.take('0fb6742450','4080fe0f');g.branch('0f85',False);sites=[]
 for read,setter in zip(reads,setters,strict=True):
  sites.append(g.at);g.relative('488b15');g.take('488bcf','488b33');g.call(read);g.take('4885f6');g.branch('0f84',False);g.take('4533c0','488bd0','488bce');g.call(setter)
 return dict(selectedBytes=g.seen,new=new,allocationUsageSite=allocation,readUsageSites=sites,afterPrefix=g.at,fieldOrder=['_fallbackMontages','avatarBlendProfilePath','bakedBindingPath','boneWeightMasks','controllerPath'],condition='Initialized metadata, MC15 and nonnull typed wrapper with underlying original instance; normal selected reader/setter helpers and stable disjoint storage. New constructor effect explicitly conditional. Prefix only; extraData and all later fields unproved here.')


def root_setter(regions,entry,offset,barrier,*,reference=False):
 d=bytes([offset]).hex();g=BytesPath(regions,entry);g.take('4883ec28')
 if reference:
  g.take('488b4910','4885c9');g.branch('74',False,1);g.take('488951'+d,'4883c1'+d,'4883c428')
  if g.relative('e9')!=barrier:raise ValueError('animationMask.root-setter-barrier')
 else:
  g.take('488b4110','4885c0');g.branch('75',True,1);g.take('488950'+d,'4883c428','c3')
 return dict(selectedBytes=g.seen,wrapperInstanceOffset=16,ownedFieldOffset=offset,source='unchanged incoming RDX',reference=reference,condition='Typed nonnull wrapper/original instance; normal barrier; other fields untouched.')


def root_factory(regions,entry,s,*,create=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bf9');g.branch('75'if create else'74',create,1)
 allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('75'if create else'74',create,1);g.take('33d2','488bcb'if create else'488bc8');g.call(s['originalConstructor']);g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('animationMask.root-factory-barrier')
 return dict(selectedBytes=g.seen,allocationUsageSite=allocation,instanceOffset=16,condition='Initialized metadata; nonnull allocation of typed original class, normal original constructor and barrier. Stored prefix overwrites its five fields; no remaining default/tail-field interpretation.')


def canonical_add_program(regions,entry,store):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec30','ff411c','488bd9','4c8b4910','498bf8','48634918','488bf2','4d85c9');g.branch('75',True,1);g.take('413b4918');g.branch('72',True,1)
 g.take('0f1002','8d4101','488bd1','4c8d442420','894318','498bc9','f30f7f442420');g.call(store);g.take('488b5c2440','488b742448','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,elementBytes=16,condition='Coherent typed List/array; count0 and capacity>=1, exact aligned16 temporary passed to separate array store. No growth.')


def array_store_program(regions,entry,barrier):
 g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1);g.take('410f2800','488d4202','4803c0','48c1e204','0f1104c1','4883c128','4803ca','4883c428')
 if g.relative('e9')!=barrier:raise ValueError('animationMask.array-barrier')
 return dict(selectedBytes=g.seen,arrayDataOffset=32,arrayStride=16,referenceLaneOffset=8,condition='Typed array; nonnegative index below length and aligned16 input, exact128 bits stored and sole reference lane+8 barrier. No allocation or growth.')


def validate_components(image,fact):
 """Recheck all selected bytes, ownership, declarations and static joins per call."""
 import struct
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,derive_typed_usage_context,_vtable
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param,pooled_source_helper,utf8_source_helper,wrapper_members
 from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
 from scripts.game_data.memorypack.reference_instance_sources import validate_instance_context
 from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
 from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 from scripts.game_data.levelscript_family_regenerate import Build
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);profile=fact['profile'];s={k:base+v for k,v in profile['symbols'].items()};sources=profile['sources'];methods=profile['methods'];types=profile['types'];proofs={}
 def need(k,e,a):scalar.need('animationMasks',k,e,a)
 need('supported-counts',[-1,0,1],fact['supportedCounts']);need('entry-field-order',['layerName','maskPath'],fact['fieldOrder']);need('element-wire-bytes',13,fact['elementWireBytes'])
 def capture(role):
  b=sources[role];p=base+b['entryRva'];windows=b['windows'];expected=sorted((w['startRva'],w['endRva'])for w in windows)
  if b['ownership']=='completeUnwindFamily':need(role+'.complete-owned',expected,sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(p-base)['ranges']))
  elif b['ownership']=='closedSelectedLeaf':
   from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
   leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(p,512),p);need(role+'.closed-selected-leaf',expected,[(p-base,max(int(r['va'],16)+len(bytes.fromhex(r['bytes']))for r in leaf['rows'])-base)])
  elif b['ownership']=='boundedSelectedLeaf':need(role+'.bounded-leaf',[(p-base,p-base+34)],expected);need(role+'.leaf-role','clear',role)
  else:raise ValueError('animationMasks.unreviewed-ownership')
  image.check_windows(windows,label='animationMasks.'+role);return [(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows],p
 for role in sources:capture(role)
 for row in methods.values():image.validate_method_row(row,label='animationMasks')
 for symbol,role in dict(child='child',forwarder='forwarder',hash='hash',peek='peek',adapter='adapter',readNull='readNull',notNull='notNull',dispatch='dispatch',ordinaryDispatch='ordinaryDispatch',conversion='conversion',constructor='capacity',clear='clear',add='add',rootConstructor='rootFactory',provider='valueProvider',wrapperProvider='wrapperProvider').items():need(symbol+'.source-target',s[symbol]-base,sources[role]['entryRva'])
 need('original-constructor-target',s['originalConstructor']-base,methods['originalConstructor'][3])
 bindings=dict(child='childRead',getValue='getValue',default='default',create='create',forwarder='childFormatter',root='rootRead',rootFactory='rootFactory',rootCreate='rootCreate',init='init',**{'setter'+str(i):'setter'+str(i)for i in range(5)})
 need('source-method-coverage',bindings,profile['sourceMethods'])
 named=dict(childRead=(types['wrapper'],'Deserialize'),getValue=(types['wrapper'],'GetValue'),default=(types['wrapper'],'.ctor'),create=(types['wrapper'],'CreateInstance'),childFormatter=(types['wrapper']+'+'+types['wrapper'].split('.')[-1]+'Formatter','Deserialize'),rootRead=(types['rootWrapper'],'Deserialize'),rootFactory=(types['rootWrapper'],'.ctor'),rootCreate=(types['rootWrapper'],'CreateInstance'),init=(types['wrapper'],'Init'),originalConstructor=(types['root'],'.ctor'))
 for key,(owner,name)in named.items():need(key+'.named-owner-method',[owner,name],methods[key][1:3])
 for role,key in profile['sourceMethods'].items():need(role+'.named-entry',methods[key][3],sources[role]['entryRva'])
 wrappers={w.name:w for w in wrapper_members.derive_from_image(image).values()};child=wrappers[types['wrapper']];root=wrappers[types['rootWrapper']]
 need('child-wrapper-original',types['entry'],child.wrapped_type);need('child-generated-fields',[('layerName','string'),('maskPath','Beyond.Resource.StringPathHash')],[(m.name,m.declared_type)for m in child.members]);need('child-value-ABI',True,ctx.is_value_type(types['entry']));need('wrapper-reference',False,ctx.is_value_type(types['wrapper']));need('wrapper-instance',(types['wrapper'],types['entry'],16),ctx.field(types['wrapper']+'::__instance'))
 need('root-instance',(types['rootWrapper'],types['root'],16),ctx.field(types['rootWrapper']+'::__instance'));need('root-original',types['root'],root.wrapped_type);need('root-count',15,len(root.members));need('root-first-five',['_fallbackMontages','avatarBlendProfilePath','bakedBindingPath','boneWeightMasks','controllerPath'],[m.name for m in root.members[:5]])
 for name,fields,size in((types['entry'],[('maskPath','Beyond.Resource.StringPathHash',16),('layerName','string',24)],(32,16)),('Beyond.Resource.StringPathHash',[('hash','long',16)],(24,8))):
  td=ctx.index.types[name];actual=[(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16];need(name+'.fields',fields,actual);p=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);need(name+'.managed-size',size,(image.pe.u32_at_va(p),image.pe.u32_at_va(p+4)))
 cs=ContextSymbols(image);adapter=cs.context(ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'].index);lc=cs.context(ctx.index.types['MemoryPack.Formatters.ListFormatter`1'].index);ctorc=cs.context(ctx.index.types['System.Collections.Generic.List`1'].index);a={r['relativeSlot']:r for r in adapter['entries']};provider=cs.context(a[4]['methodSpec'][0],is_method=True);activate=cs.context(a[11]['methodSpec'][0],is_method=True);contexts=[adapter,lc,ctorc,provider,activate];validate_generic_contexts(image,contexts,label='animationMasks');proofs['conversionContext']=validate_conversion_context(image,adapter,entries,fail=need);proofs['instanceContext']=validate_instance_context(image,adapter,[provider,activate],entries,a[3]['methodSpec'][0],fail=need);proofs['listContext']=validate_list_formatter_base_context(image,lc,entries,fail=need);proofs['capacityContext']=validate_capacity_constructor_context(image,lc,ctorc,entries,fail=need)
 for role,name in(('list','Deserialize'),('adapter','Deserialize'),('readNull','ReadIsNull'),('notNull','DeserializeNotNull')):
  td=md.types[(lc if role=='list'else adapter)['definition']];m,=[m for m in md.methods_for(td)if md.string(m.name_index)==name];args=[types['entry']]if role=='list'else[types['entry'],'object'];row=entries.resolve(m.index,args,[]);need(role+'.canonical-registered-entry',sources[role]['entryRva'],row['pointer']-base)
  if name=='Deserialize':_vtable(image,td.index,5,m.index,'animationMasks')
 lslots={r['relativeSlot']:r for r in lc['entries']}
 for role,slot in(('capacity',1),('clear',2),('canonicalAdd',6)):
  row=entries.resolve(lslots[slot]['methodSpec'][0],[types['entry']],[]);need(role+'.same-closed-entry',sources[role]['entryRva'],row['pointer']-base)
 for role in('child','root'):
  m=md.methods[methods[role+'Read'][0]];primitive_param.reader_abi(image,ctx,m,type('Wrapper',(),{'name':types['wrapper'if role=='child'else'rootWrapper']})())
 getter=md.methods[methods['getValue'][0]];scalar.owned_method_abi(image,ctx,getter.index,ctx.index.types[types['wrapper']].index,(types['entry'],17,False),[],'animationMasks.getter')
 for role in('default','create'):
  m=md.methods[methods[role][0]];scalar.owned_method_abi(image,ctx,m.index,ctx.index.types[types['wrapper']].index,('void',1,False),[],'animationMasks.default')
 for key,owner in(('rootFactory',types['rootWrapper']),('rootCreate',types['rootWrapper']),('originalConstructor',types['root'])):
  scalar.owned_method_abi(image,ctx,methods[key][0],ctx.index.types[owner].index,('void',1,False),[],'animationMasks.'+key)
 formatter=md.methods[methods['childFormatter'][0]];need('formatter-instance',0,formatter.flags&16);scalar.ordinary(image,ctx.type_pointer(formatter.return_type),1,'animationMasks.formatter-result');_vtable(image,formatter.declaring_type,5,formatter.index,'animationMasks');parameters=list(md.parameters_for(formatter));need('formatter-arity',2,len(parameters))
 for p,name,kind in zip(parameters,('MemoryPack.MemoryPackReader',types['wrapper']),(17,18),strict=True):
  raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16);need('formatter-byref',(name,kind,32),(ctx.type_name(p.type_index),raw[10],raw[11]))
 for role in('default','create'):proofs[role]=default_program(*capture(role))
 proofs['getter']=getter_program(*capture('getValue'));offsets=scalar.reader_offsets(image,'animationMasks');proofs['hash']=hash_program(*capture('hash'),offsets);proofs['peek']=peek_program(*capture('peek'),offsets)
 proofs['child']=[child_program(*capture('child'),s,new=n)for n in(False,True)]+[child_program(*capture('child'),s,null=True)];proofs['forwarder']=forwarder_program(*capture('forwarder'),s)
 def usage(at):return derive_typed_usage_context(image,at-base,label='animationMasks')
 for p in proofs['child']:
  if p['allocationUsageSite']is not None:need('child-allocation',(1,types['wrapper']),(usage(p['allocationUsageSite'])['tag'],usage(p['allocationUsageSite'])['typeName']))
  if p['hashUsageSite']is not None:
   u=usage(p['hashUsageSite']);need('typed-hash-source',('MemoryPack.MemoryPackReader','ReadUnmanaged',['Beyond.Resource.StringPathHash']),(u['typeName'],u['methodName'],u['methodArguments']))
 u=usage(proofs['forwarder']['wrapperUsageSite']);need('forwarder-wrapper-class',(1,types['wrapper']),(u['tag'],u['typeName']))
 proofs['registration']=registration_prefix(capture('init')[0],base+profile['registrationStartRva'],s)
 p=proofs['registration'];u={k:usage(p[k+'UsageSite'])for k in('allocation','constructor','key','typeOwner','provider')};need('registered-constructor',('Beyond.MemoryPack.GenericMemoryPackFormatter`2','.ctor',[types['entry'],types['wrapper']],[]),(u['constructor']['typeName'],u['constructor']['methodName'],u['constructor']['classArguments'],u['constructor']['methodArguments']));need('original-registration-key',(2,types['entry']),(u['key']['tag'],u['key']['typeName']));need('registration-allocation',(1,'Beyond.MemoryPack.GenericMemoryPackFormatter`2<'+types['entry']+','+types['wrapper']+'>'),(u['allocation']['tag'],u['allocation']['typeName']))
 need('registration-type-owner',(1,'System.Type'),(u['typeOwner']['tag'],u['typeOwner']['typeName']));need('registration-provider-owner',(1,'MemoryPack.MemoryPackFormatterProvider'),(u['provider']['tag'],u['provider']['typeName']));raw=image.pe.bytes_at_va(ctx.type_pointer(u['allocation']['typeIndex']),16);need('adapter-kind',21,raw[10]);instance=image.instantiations.resolve_pointer(image.pe.u64_at_va(int.from_bytes(raw[:8],'little')+8));need('adapter-constructor-instantiation',u['constructor']['methodSpec'][1],instance.index);need('adapter-key-pointer',ctx.type_pointer(u['key']['typeIndex']),instance.arguments[0].type_pointer_va);need('adapter-wrapper-pointer',ctx.type_pointer(ctx.index.types[types['wrapper']].byval_type_index),instance.arguments[1].type_pointer_va)
 td=ctx.index.types[types['wrapper']];section=md.sections['interfaceOffsets'];start=section.offset+td.interface_offsets_start*8;matches=[]
 for ordinal,(idx,off)in enumerate(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8])):
  if ctx.type_name(idx)!='Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1<'+types['entry']+'>':continue
  raw=image.pe.bytes_at_va(ctx.type_pointer(idx),16);need('interface-kind',21,raw[10]);inst=image.instantiations.resolve_pointer(image.pe.u64_at_va(int.from_bytes(raw[:8],'little')+8));need('conversion-original-identity',instance.arguments[0].type_pointer_va,inst.arguments[0].type_pointer_va);_vtable(image,td.index,off,getter.index,'animationMasks');matches.append(ordinal)
 need('conversion-interface-unique',1,len(matches));proofs['conversion']=conversion_program(*capture('conversion'),s['prepare'],ordinal=matches[0]);proofs['ordinaryDispatch']=deserialize_slot(*capture('ordinaryDispatch'),prepare=s['prepare'],callback=s['forwarder'])
 proofs['nullAdapter']=[null_program(*capture('readNull'),s,null=n)for n in(False,True)];proofs['adapter']=[adapter_program(*capture('adapter'),s,null=n,create=c)for n in(False,True)for c in(False,True)];proofs['inlineAdapter']=[adapter_program(*capture('dispatch'),s,inline=True,null=n,create=c)for n in(False,True)for c in(False,True)];proofs['notNull']=[not_null_program(*capture('notNull'),s,zero=n)for n in(False,True)];proofs['list']=[list_program(*capture('list'),s,count=-1)]+[list_program(*capture('list'),s,count=c,new=n)for c in(0,1)for n in(False,True)];proofs['capacity']=[capacity_program(*capture('capacity'),s,positive=p)for p in(False,True)];proofs['add']=add_program(*capture('add'),s);proofs['canonicalAdd']=canonical_add_program(*capture('canonicalAdd'),s['arrayStore']);proofs['arrayStore']=array_store_program(*capture('arrayStore'),s['barrier'])
 g=BytesPath(*capture('clear'));g.take('448b4118','ff411c','c7411800000000','4585c0');g.branch('7e',True,1);g.take('c3');proofs['clear']=dict(selectedBytes=g.seen,initialCount=0)
 reads=[base+r for r in profile['rootReads']];setters=[image.method_pointer_va(md.methods[m.method_index])for m in root.members[:5]];proofs['parent']=[root_prefix(*capture('root'),s,reads,setters,new=n)for n in(False,True)]
 for member,at,target in zip(root.members[:5],proofs['parent'][0]['readUsageSites'],reads,strict=True):
  u=usage(at);need('root-field-context',[member.declared_type],u['methodArguments']);name=u['methodName'];need('root-reader-owner','MemoryPack.MemoryPackReader',u['typeName']);need('root-reader-method','ReadPackable'if member.name=='boneWeightMasks'else'ReadUnmanaged'if member.name.endswith('Path')else'ReadValue',name)
  if name in('ReadPackable','ReadValue'):Build(image,fact['nativeInputs']).prove_named_target(target,'MemoryPack.MemoryPackReader',name,result_abi='reference')
  else:need('same-path-hash-source',s['hash'],target)
 for i,member in enumerate(root.members[:5]):
  field=ctx.field(types['root']+'::'+member.name);method=md.methods[member.method_index];scalar.owned_method_abi(image,ctx,method.index,ctx.index.types[types['rootWrapper']].index,('void',1,False),[(field[1],18 if i==0 else 21 if i==3 else 17,i in(0,3))],'animationMasks.setter'+str(i));need('root-setter-identity',member.method_index,methods['setter'+str(i)][0]);need('root-setter-typed-field',member.declared_type,field[1]);proofs['setter'+str(i)]=root_setter(*capture('setter'+str(i)),field[2],s['barrier'],reference=i in(0,3))
 proofs['rootFactory']=[root_factory(*capture('rootFactory'),s),root_factory(*capture('rootCreate'),s,create=True)]
 for p in proofs['rootFactory']:
  u=usage(p['allocationUsageSite']);need('original-root-allocation',(1,types['root']),(u['tag'],u['typeName']))
 proofs['pooledString']=pooled_source_helper.validate_on_image(image,s['pooled'],fact['nativeInputs']);header=utf8_source_helper._contract();need('collection-source-inputs',fact['nativeInputs'],header['nativeInputs']);need('collection-source-target',s['collectionHeader']-base,header['bodies']['header']['entryRva']);proofs['collectionHeader']=utf8_source_helper._validate_native(image,header);proofs['objectHeader']=primitive_param.object_header_source(image,vector_recorder(image)(s['objectHeader']-base),offsets)
 return dict(selectedPrograms=sum(isinstance(v,(dict,list))for v in proofs.values()),interfaceOrdinal=matches[0],supportedCounts=fact['supportedCounts'],entryRuntimeBytes=16,entryWireBytes=13,boundary=fact['evidenceBoundary'])
