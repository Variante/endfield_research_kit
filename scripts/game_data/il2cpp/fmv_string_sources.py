"""Selected bounded original FMV string programs; runtime choices remain conditional."""


from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


from scripts.game_data.il2cpp.inline_copy_sources import prove_inline_copy


def forwarding(regions,entry,*,arity,prepare,initialize,tail):
 if arity not in (1,2):raise ValueError('fmvFormat.arity')
 proofs=[]
 for context_ready in (False,True):
  for class_ready in (False,True):
   g=BytesPath(regions,entry)
   g.take('48895c2408')
   if arity==1:g.take('4889742410','57','4883ec20','4983783800','498bd8','488bfa','488bf1')
   else:g.take('48896c2410','4889742418','57','4883ec20','4983793800','498bd9','498bf8','488bf2','488be9')
   g.branch('74',not context_ready,1)
   if not context_ready:g.take('488bcb');g.call(prepare);g.jump('eb',1)
   source=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',not class_ready,1)
   if not class_ready:g.call(initialize);g.jump('eb',1)
   if arity==1:g.take('4c8b4338','488bd7','488bce','4d8b00','488b5c2430','488b742438')
   else:g.take('4c8b4b38','4c8bc7','488bd6','488bcd','4d8b09','488b5c2430','488b6c2438','488b742440')
   g.take('4883c420','5f')
   if g.relative('e9')!=tail:raise ValueError('fmvFormat.tail')
   proofs.append(dict(contextReady=context_ready,classReady=class_ready,sourceTypeCell=source,selectedBytes=g.seen))
 # The four selected paths cover every byte, including both helper returns.
 actual={at+i for p in proofs for at,raw in p['selectedBytes'] for i in range(len(bytes.fromhex(raw)))}
 expected={at+i for at,raw in regions for i in range(len(raw))}
 if actual!=expected:raise ValueError('fmvFormat.complete-owned-coverage')
 return dict(paths=proofs,arity=arity,contextSlot=0,contextOffset=56,
  forwardedArguments=['incoming RCX format','incoming RDX value']+(['incoming R8 value'] if arity==2 else []),
  condition='Actual current owned thunk; initialized valid closed generic MethodInfo and static ZString class, normal context/class initialization helpers preserving Win64 nonvolatile registers and stable storage. Slot zero is forwarded to the selected tail; helper effects, live initialized slot contents, format parsing, builder effects, exceptions and final naming semantics remain separate.')


def parse_token(regions,entry,*,length,start,index):
 if any(type(n) is not int for n in (length,start,index)) or index not in (0,1) or not 0<=start<start+3<=length<1<<31:raise ValueError('fmvParser.bounded-token')
 g=BytesPath(regions,entry);g.take('4053','56','57','4883ec40','418bd8','488bfa','488bf1','4885d2');g.branch('0f84',False)
 g.take('48896c2460','ffc3','48636a10','4c89642468','4c896c2470','4c89742438','4c897c2430','3bdd');g.branch('74',False,1)
 g.take('48634a10','8bc3','483bc1');g.branch('0f8d',False);g.take('4863c3','0fb7544214','b830000000','6683fa39');g.branch('76',True,1)
 g.take('663bc2');g.branch('77',False,1)
 g.take('4c635710','4c8d4f14','4c63c3','4533db','458bf3','4f8d0c41','478d34b6','0fb7c2','ffc3','458d76e8','49ffc0','4d8d4902','468d3470','3bdd');g.branch('74',False,1)
 g.take('8bc3','493bc2');g.branch('0f8d',False);g.take('410fb711','8d42d0','6683f809');g.branch('0f86',False)
 g.take('4183fe10');g.branch('0f8d',False);g.take('3bdd');g.branch('7d',False,1)
 g.take('48634f10','4c8d4f14','4f8d0c41','8bc3','483bc1');g.branch('0f8d',False)
 g.take('410fb711','6683fa20');g.branch('0f84',False);g.take('458bfb','6683fa2c');g.branch('0f84',False)
 g.take('3bdd');g.branch('7d',False,1);g.take('48634f10','4c8d4714','4c63cb','4f8d0448','8bc3','483bc1');g.branch('0f8d',False)
 g.take('410fb710','6683fa20');g.branch('0f84',False);g.take('0f57c0','6683fa3a');g.branch('74',False,1)
 g.take('6683fa7d');g.branch('0f85',False)
 g.take('44895e04','ffc3','4c8b6c2470','488bc6','4c8b642468','488b6c2460','448936','4c8b742438','44897e1c','4c8b7c2430','895e18','0f114608','4883c440','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,result=dict(index=index,padding4=0,formatSpanPointer=0,formatSpanLength=0,lastIndex=start+3,alignment=0),outputOffsets=dict(index=0,formatSpan=8,lastIndex=24,alignment=28),returnIsIncomingOutput=True,
  condition='Stable nonnull managed string with stated length and exact three UTF16 units {0} or {1} at incoming start; disjoint valid 32-byte output and Win64 frame, no integer overflow. Only this bounded token path is proved; alignment, format spans, multiple digits, malformed inputs and other branches remain excluded.')


def constant_value(get_regions,get_entry,try_regions,try_entry,*,source_slot,constant_slot,barrier,source=0):
 if type(source)is not int or source!=0:raise ValueError('fmvSource.constant-only')
 if any(type(n)is not int or not 0<n<128 for n in (source_slot,constant_slot))or source_slot==constant_slot:raise ValueError('fmvSource.owned-slots')
 src=bytes((source_slot,)).hex();value=bytes((constant_slot,)).hex()
 g=BytesPath(get_regions,get_entry)
 g.take('48895c2410','48896c2418','4889742420','57','4883ec20','4983793800','498bf9','410fb6f0','488bea','488bd9');g.branch('74',False,1)
 g.take('48c744243000000000','4885db');g.branch('74',False,1)
 g.take('488b4738','488b4808','4883792000');g.branch('74',False,1)
 g.take('837b'+src+'ff');g.branch('74',False,1)
 g.take('837b'+src+'fe');g.branch('74',False,1)
 g.take('4c8b4f38','488d542430','440fb6c6','488bcb','4d8b4910');g.call(try_entry)
 h=BytesPath(try_regions,try_entry)
 h.take('48895c2418','4889542410','56','57','4154','4156','4157','4881ecd0000000','498bf1','450fb6f0','488bfa','488bd9','4983793800');h.branch('0f84',False)
 h.take('33c0','4889842418010000','4889842400010000','0f57c0','0f118424a0000000','0f118424b0000000','48898424c0000000','4885db');h.branch('0f84',False)
 h.take('488b4638','488b4808','4883792000');h.branch('0f84',False)
 h.take('837b'+src+'00');h.branch('75',False,1)
 h.take('488b43'+value,'488907','488bcf');h.call(barrier)
 h.take('b001','488b9c2410010000','4881c4d0000000','415f','415e','415c','5f','5e','c3')
 g.take('84c0');g.branch('74',False,1)
 g.take('488b442430','488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
 return dict(getValueBytes=g.seen,tryGetValueBytes=h.seen,sourceSlot=source_slot,constantSlot=constant_slot,
  methodContextOffset=56,getterReadySlot=1,tryGetValueSlot=2,outLocalOffsetFromAllocatedGetValueRsp=48,
  selectedParamReadSlots=[source_slot,constant_slot],inactiveFields=['idRef','path','getter','context','m_pathRuntime','setter','m_variableBind'],
  transfer='TryGetValue writes the same incoming Param constant reference to the GetValue local and returns true; GetValue returns that exact reference, including null.',
  condition='Initialized valid closed reference-valued Param<T>/GetValue/TryGetValue MethodInfo contexts; source is exactly zero; nonnull matching typed Param and disjoint caller/out/frame storage; selected ordinary noninterfering ABI-preserving barrier returns normally. Generic slots are separately authenticated; no runtime provider/cache selection, active reference/path/getter source, exception or cold initialization is admitted.')


def zero_alignment(regions,entry,rows,*,context_class,type_context,copy_entry,copy_finish,copy_target,invoker,formatter,char_count=128,index=0,capacity=256):
 if any(type(n)is not int for n in (char_count,index,capacity))or not 0<=char_count<=128 or not 0<=index<=capacity<=0x7fffffff or char_count>capacity-index:raise ValueError('fmvZeroAlign.character-capacity-bound')
 g=BytesPath(regions,entry)
 g.take('4c894c2420','55','56','57','4154','4155','4156','4157','4881ecc0000000','488d6c2430','4c8bbdf8000000','4d8be1','48899dd0000000','418bf8','0f29b580000000','488bf2','4c8be9','49837f3800');g.branch('0f84',False)
 g.take('498b4f38','4533f6','4489b5e0000000','44897510','85ff');g.branch('0f8f',False)
 g.take('33d2','f7df');g.call(context_class)
 g.take('4439b0e0000000');g.branch('0f84',False)
 g.take('498b4f38','33d2');g.call(context_class)
 g.take('498b5d00','4d636508','488b88b8000000');invoke_context=g.relative('488b05')
 g.take('48894500','488b11','48895520','4c397038');g.branch('0f84',False)
 g.take('4885db');g.branch('0f84',False)
 g.take('443b6318');g.branch('0f87',False)
 g.take('8b4318','498d4c2410','488d0c4b','4489750c','412bc4','48894d00','894508','0f287500','0f297500','4885d2');g.branch('0f84',False)
 g.take('498b4738','488b4810','4c397120');g.branch('0f84',False)
 g.take('488b4500','488b9de8000000','4c8b4228','488b4a40','48894520','8b450c','0f1003','89452c','488b4218')
 if g.relative('488d15')!=invoker:raise ValueError('fmvZeroAlign.selected-invoker')
 g.take('660f73de08','660f7e7528','0f287520','0f294570','660f7f7540','483bc2');g.branch('0f85',False)
 g.take('488b4110')
 if g.relative('488d0d')!=formatter:raise ValueError('fmvZeroAlign.selected-formatter')
 g.take('0f294530','0f297520','483bc1');g.branch('0f85',False)
 g.take('4885f6');g.branch('0f84',False)
 string_class=g.relative('488b05');g.take('483906');g.branch('0f85',False)
 fast_flag=g.relative('443835');g.take('8b4610','8985e0000000');g.branch('0f84',False)
 span_method=g.relative('488b05');g.take('488d5e14','448b6610','48895d50','48894500','488b4820','0f297560');g.call(type_context)
 g.take('660f73de08','66480f7ef0','443be0');g.branch('0f87',False)
 g.take('488b4d00','488b4920');g.call(type_context)
 g.take('488b88c0000000','488b4930','4883793800');g.branch('0f84',False)
 g.take('488b4d60','478d0424','488bd1','418bc0','482bd3','483bd0');g.branch('0f82',False)
 g.take('488bd3','418bc0','482bd1','483bd0');g.branch('0f82',False)
 if g.at!=copy_entry:raise ValueError('fmvZeroAlign.copy-entry')
 copy=prove_inline_copy(rows,copy_entry,copy_finish,source='rbx',copy_target=copy_target,spill=('rbp',0x50))
 if copy['maxBytes']!=256 or copy['completeCases']!=516:raise ValueError('fmvZeroAlign.complete-copy-bound')
 g.at=copy_finish;g.take('41b601','488b9de8000000','4584f6');g.branch('0f84',False)
 g.take('8b8de0000000','8bdf','41014d08','2bd9','85ff');g.branch('0f8f',False)
 g.take('488b9dd0000000','0f28b580000000','488da590000000','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,copy=copy,cells=dict(arraySpanContext=invoke_context,stringClass=string_class,fastFlag=fast_flag,spanMethod=span_method),
  builderFields=dict(buffer=0,index=8),stringFields=dict(length=16,characters=20),arrayFields=dict(length=24,characters=32),formatterCacheStaticField=0,
  sourcePointerSpill=['rbp',80],maxStringChars=128,alignment=0,charsWritten='original input String.length',indexAfter='original builder.index + original input String.length',
  bufferEffect='Exact original input UTF16 chars copied to buffer[original index : original index + length]; no padding or formatting-span contents consumed on selected original string fast path.',
  condition='Zero alignment; nonnull exact System.String; valid initialized typed contexts; stable selected cache delegate whose invoker and method pointer equal the two actual compared targets. Fast string-span flag is nonzero; helper returns compatible declaring/context classes; all ready checks succeed. Disjoint source/destination and valid nonwrapping storage, char length0..128 and sufficient existing buffer capacity. Ordinary type/context helpers preserve nonvolatile registers and memory. Complete bounded-copy dependency required for calls above32bytes. No live/default formatter selection, growth/retry, custom delegate, null string, positive alignment or wider string is admitted.')



def fixed_format(regions,entry,*,arity,text,substring,parser,internal,parser_regions):
 if (arity,text)not in ((1,'Narrative/Cutscene/{0}'),(2,'{0}/{1}'),(2,'{0}/{1}.usm')):raise ValueError('fmvFormat.fixed-literal-only')
 g=BytesPath(regions,entry);operations=[];cells=[]
 if arity==1:
  g.take('48897c2420','4154','4156','4157','4881ec90000000','4983793800','4d8bf1','4d8be0','488bfa','4c8bf9');g.branch('0f84',False)
  g.take('48899c24b0000000','4889ac24b8000000','4889b424c0000000','4885ff');g.branch('0f84',False);g.take('33ed','8bdd','6690')
 else:
  g.take('4057','4154','4155','4156','4157','4881ec90000000','4c8bbc24e0000000','4d8be1','4d8be8','488bfa','4c8bf1','49837f3800');g.branch('0f84',False)
  g.take('48899c24c0000000','4889ac24c8000000','4889b424d0000000','4885ff');g.branch('0f84',False);g.take('33ed','8bdd')
 pos=segment=0;loop=g.at
 while True:
  if g.at!=loop:raise ValueError('fmvFormat.loop-back')
  g.take('3b5f10');g.branch('0f8d',pos>=len(text))
  if pos>=len(text):break
  g.take('48634f10','8bc3','483bc1');g.branch('0f8d',False)
  g.take('4863c3','0fb74c4714','6683f97b');g.branch('74',text[pos]=='{',1)
  if text[pos]!='{':
   if text[pos]=='}':raise ValueError('fmvFormat.unsupported-closing-brace')
   g.take('6683f97d');g.branch('0f84',False);g.take('ffc3');g.jump('eb',1);pos+=1;continue
  token=text[pos:pos+3]
  if token not in ('{0}','{1}'):raise ValueError('fmvFormat.bounded-token')
  value=int(token[1]);g.take('8b4710','ffc8','3bd8');g.branch('0f84',False)
  g.take('3b5f10');g.branch('74',False,1)
  g.take('48634710','8d4b01','483bc8');g.branch('0f8d',False)
  g.take('4863c3','66837c47167b');g.branch('0f84',False)
  cells.append(('builderClass',g.relative('488b0d')));g.take('8bf3','2bf5','83b9e000000000');g.branch('0f84',False)
  g.take('448bce','448bc5','488bd7','498bcf'if arity==1 else'498bce');g.call(substring)
  operations.append(dict(kind='literal',start=segment,count=pos-segment,text=text[segment:pos]))
  g.take('448bc3','488d4c2450','488bd7');g.call(parser)
  parsed=parse_token(parser_regions,parser,length=len(text),start=pos,index=value)
  if arity==1:
   g.take('488bc8','0f1000','8b6818','0f11442430','0f10c8','8d5dff','0f11442430','0f104010','660f7ec8','0f11442440','85c0');g.branch('0f85',False)
   g.take('488b7118');cells.append(('builderClass',g.relative('488b0d')));g.take('48c1ee20','0f114c2430','0f11442440','3981e0000000');g.branch('0f84',False)
   g.take('498b4638','4c8d4c2430','0f10442438','448bc6','498bd4','488b08');cells.append(('spanProvider',g.relative('488b05')))
   g.take('48894c2428','498bcf','0f29442430','4889442420');g.call(internal);g.jump('e9')
  else:
   g.take('0f1000','8b6818','0f10c8','0f11442430','8d5dff','660f7ec9','0f11442430','0f104010','0f11442440','85c9');g.branch('75',value!=0,1)
   if value==0:
    cells.append(('builderClass',g.relative('488b0d')));g.take('488b7018','48c1ee20','0f114c2430','83b9e000000000','0f11442440');g.branch('0f84',False)
    g.take('498b4738','498bd5','488b08');cells.append(('spanProvider',g.relative('488b05')))
   else:
    g.take('83f901');cells.append(('builderClass',g.relative('488b0d')));g.branch('0f85',False)
    g.take('488b7018','48c1ee20','83b9e000000000','0f114c2430','0f11442440');g.branch('0f84',False)
    g.take('498b4738','498bd4','488b4808');cells.append(('spanProvider',g.relative('488b05')));g.jump('eb',1)
   g.take('0f10442438','48894c2428','4c8d4c2430','448bc6','4889442420','498bce','0f29442430');g.call(internal);g.jump('e9')
  operations.append(dict(kind='argument',index=value,contextSlot=value,alignment=parsed['result']['alignment'],formatSpan=[0,0],parser=parsed));segment=pos+3;pos=segment;g.take('ffc3');g.jump('eb',1)
 g.take('8b5f10','2bdd','85db');g.branch('7e',len(text)==segment,1)
 if len(text)>segment:
  cells.append(('builderClass',g.relative('488b0d')));g.take('83b9e000000000');g.branch('0f84',False)if arity==1 else g.branch('74',False,1)
  g.take('448bcb','448bc5','488bd7','498bcf'if arity==1 else'498bce');g.call(substring);operations.append(dict(kind='literal',start=segment,count=len(text)-segment,text=text[segment:]))
 if arity==1:g.take('488bb424c0000000','488bac24b8000000','488b9c24b0000000','488bbc24c8000000','4881c490000000','415f','415e','415c','c3')
 else:g.take('488bb424d0000000','488bac24c8000000','488b9c24c0000000','4881c490000000','415f','415e','415d','415c','5f','c3')
 return dict(selectedBytes=g.seen,operations=operations,cells=cells,template=text,arity=arity,restoredFrame=True,
  condition='Exact selected literal, valid initialized closed string MethodInfo slots and builder class, nonnull stable managed format and values, ordinary noninterfering ABI-preserving substring/parser/zeroalignment callees with independently authenticated effects. Only these three literals, no escape/alignment/format/custom string path; no final String construction or owner admission.')


def append_string(regions,entry,rows,*,substring,type_context,copy_entry,copy_finish,copy_target,length,start=0,count=None,index=0,capacity=256):
 count=length if count is None else count
 if type(substring)is not bool or any(type(n)is not int for n in (length,start,count,index,capacity))or not 0<=start<=length<=0x7fffffff or not 0<=count<=128 or count>length-start or not 0<=index<=capacity<=0x7fffffff or count>capacity-index or not substring and(start!=0 or count!=length):raise ValueError('fmvAppend.bounded-selected-source')
 g=BytesPath(regions,entry);cells=[]
 def flag():
  raw=g.read(7)
  if raw[:2]!=b'\x80\x3d'or raw[-1]!=0:raise ValueError('fmvAppend.initializer-flag')
  cells.append(('initializedFlag',g.at-1+int.from_bytes(raw[2:6],'little',signed=True)))
 if substring:
  g.take('48895c2418','55','56','57','4883ec50');flag();g.take('418bf1','4963e8','488bda','488bf9');g.branch('0f84',False)
  g.take('4885db');g.branch('0f84',False);flag();g.branch('0f84',False)
  g.take('3b6b10');g.branch('0f87',False);g.take('8b4310','2bc5','3bf0');g.branch('0f87',False)
  cells.append(('builderClass',g.relative('488b0d')));g.take('488d1c6b','4883c314','48895c2430','83b9e000000000');g.branch('0f84',False);flag();g.branch('0f84',False)
  g.take('488b07','4885c0');g.branch('0f84',False)
  g.take('8b4018','2b4708','4c89742470','4c897c2478','3bc6');g.branch('0f8c',False)
  cells.append(('arraySpanContext',g.relative('4c8b3d')));g.take('488b2f','4c637708','49837f3800');g.branch('0f84',False)
  g.take('0f29742440','4885ed');g.branch('0f84',False)
  g.take('443b7518');g.branch('0f87',False)
  g.take('8b4518','488d4d20','4a8d0c71','c744242c00000000','412bc6','48894c2420','89442428','0f28742420');cells.append(('spanCopyContext',g.relative('488b2d')))
  g.take('0f29742420','488b4d20');g.call(type_context)
  g.take('660f73de08','660f7ef0','3bf0');g.branch('0f87',False)
  g.take('488b4d20');g.call(type_context)
  g.take('488b88c0000000','488b4930','4883793800');g.branch('0f84',False)
  g.take('488b4c2420','448d0436','488bd1','418bc0','482bd3','483bd0');g.branch('0f82',False)
  g.take('488bd3','418bc0','482bd1','483bd0');g.branch('0f82',False)
 else:
  g.take('4053','57','4157','4883ec50');flag();g.take('488bfa','488bd9');g.branch('0f84',False);flag();g.branch('0f84',False)
  g.take('4533ff','0f29742440','4885ff');g.branch('0f84',False)
  g.take('488d4714','44897c242c','4889442420','8b4710','89442428','0f28742420');cells.append(('builderClass',g.relative('488b0d')))
  g.take('0f29742430','4439b9e0000000');g.branch('0f84',False);cells.append(('initializedFlag',g.relative('44383d')));g.branch('0f84',False)
  g.take('488b03','4885c0');g.branch('0f84',False)
  g.take('8b4018','2b4308','48896c2470','4889742478','660f73de08','660f7ef6','4c89b42480000000','3bc6');g.branch('0f8c',False)
  cells.append(('arraySpanContext',g.relative('4c8b35')));g.take('488b3b','48636b08','4d397e38');g.branch('0f84',False)
  g.take('4885ff');g.branch('0f84',False)
  g.take('3b6f18');g.branch('0f87',False)
  g.take('8b4718','488d4d10','488d0c4f','44897c242c','2bc5','48894c2420','89442428','0f28742420');cells.append(('spanCopyContext',g.relative('488b3d')))
  g.take('0f29742420','488b4f20');g.call(type_context)
  g.take('660f73de08','660f7ef0','3bf0');g.branch('0f87',False)
  g.take('488b4f20');g.call(type_context)
  g.take('4863fe','488b88c0000000','488b4930','4c397938');g.branch('0f84',False)
  g.take('488b4c2420','448d043f','4c8b4c2430','488bd1','492bd1','418bc0','483bd0');g.branch('0f82',False)
  g.take('498bd1','418bc0','482bd1','483bd0');g.branch('0f82',False)
 if g.at!=copy_entry:raise ValueError('fmvAppend.copy-entry')
 copy=prove_inline_copy(rows,copy_entry,copy_finish,source='rbx'if substring else'r9',copy_target=copy_target,spill=('rsp',0x30))
 if copy['maxBytes']!=256 or copy['completeCases']!=516:raise ValueError('fmvAppend.complete-copy-bound')
 g.at=copy_finish
 if substring:g.take('017708','0f28742440','4c8b742470','4c8b7c2478','488b9c2480000000','4883c450','5f','5e','5d','c3')
 else:g.take('017308','488b742478','488b6c2470','4c8bb42480000000','0f28742440','4883c450','415f','5f','5b','c3')
 return dict(selectedBytes=g.seen,copy=copy,cells=cells,substring=substring,maxCopiedChars=128,sourceChars='input String[start:start+count]'if substring else'full input String',sourcePointerSpill=['rsp',48],builderFields=dict(buffer=0,index=8),indexAfter='original index + count',
  condition='Nonnull stable managed String and compatible existing char[] buffer, initialized typed source/class/span contexts and flags, valid nonwrapping disjoint source/destination/frame, count0..128 inside string bounds and sufficient existing capacity. Ordinary class/context helper effects preserve memory/nonvolatile registers; independent bounded-copy gate required for calls above32bytes. No growth, null inputs, invalid bounds, larger copies or live allocation/provider selection.')


def cached_builder(regions,entry):
 g=BytesPath(regions,entry);tls=[];classes=[]
 g.take('4053','57','4883ec28');raw=g.read(7)
 if raw[:2]!=b'\x80\x3d'or raw[-1]!=0:raise ValueError('fmvBuilder.initializer')
 g.take('0fb6fa','488bd9');g.branch('75',True,1)
 g.take('4889742448','4084ff');g.branch('0f84',False)
 classes.append(g.relative('488b05'));g.take('83b8e000000000');g.branch('75',True,1)
 tls_index=g.relative('488b0d');g.take('4863b010010000','8b09');tls.append(g.relative('ff15'))
 g.take('488bf8','4885c0');g.branch('75',True,1)
 g.take('488b4710','488b4060','488b0cf0','80790800');g.branch('0f85',False)
 classes.append(g.relative('488b05'));g.take('40b601','48896c2440','4c89742420','83b8e000000000');g.branch('75',True,1)
 if g.relative('488b0d')!=tls_index:raise ValueError('fmvBuilder.TLS-index-cell')
 g.take('4863a810010000','8b09');tls.append(g.relative('ff15'));g.take('488bf8','4885c0');g.branch('75',True,1)
 g.take('488b4710','488b4060','488b0ce8','488b39','4885ff');g.branch('75',True,1)
 classes.append(g.relative('488b05'));g.take('83b8e000000000');g.branch('75',True,1)
 if g.relative('488b0d')!=tls_index:raise ValueError('fmvBuilder.TLS-index-cell')
 g.take('4c63b010010000','8b09');tls.append(g.relative('ff15'));g.take('488be8','4885c0');g.branch('75',True,1)
 g.take('488b4510','488b6c2440','488b4060','4a8b0cf0','4c8b742420','40887108');g.jump('eb',1)
 barrier=g.read(7)
 if barrier[:2]!=b'\x83\x3d'or barrier[-1]!=0:raise ValueError('fmvBuilder.barrier-flag')
 g.take('48893b');g.branch('74',True,1)
 g.take('4088730c','488b742448','c7430800000000','4883c428','5f','5b','c3')
 if len(set(classes))!=1 or len(set(tls))!=1:raise ValueError('fmvBuilder.same-class-TLS-import')
 return dict(selectedBytes=g.seen,sourceClassCell=classes[0],tlsIndexCell=tls_index,tlsImportCell=tls[0],fields=dict(buffer=0,index=8,usesThreadStaticBuffer=12),indexAfter=0,usesThreadStaticBufferAfter=True,
  condition='Incoming DL is true; current class/metadata initialized, stable same-thread TLS calls return nonnull compatible contexts for this class, scratch-buffer-used flag0 and cached scratch buffer is nonnull valid char[] with required capacity; barrier flag0. Fields and scratch flag updated exactly. TLS/import live binding, cold allocation, reentrancy, concurrent mutation and pool branch are not admitted.')


def final_string(regions,entry,rows,*,allocate,copy_entry,copy_finish,copy_target,count,start=0,array_length=256):
 if any(type(n)is not int for n in (count,start,array_length))or not 1<=count<=128 or not 0<=start<=array_length-count<=0x7fffffff-count:raise ValueError('fmvFinalString.positive-bounded-source')
 g=BytesPath(regions,entry);g.take('48895c2410','48896c2418','4889742420','57','4883ec20','4863ea','418bf8','488bd9','4885c9');g.branch('0f84',False)
 g.take('85d2');g.branch('0f88',False);g.take('4585c0');g.branch('0f88',False)
 g.take('8b4118','412bc0','3be8');g.branch('0f8f',False);g.take('4585c0');g.branch('0f84',False)
 g.take('418bc8');g.call(allocate);g.take('488bf0','4885c0');g.branch('0f84',False)
 g.take('837b1800','488d4814');g.branch('0f84',False);g.branch('0f86',False)
 g.take('4883c320','4c8d0c6b','488bd1','448d043f','492bd1','418bc0','483bd0');g.branch('0f82',False)
 g.take('498bd1','418bc0','482bd1','483bd0');g.branch('0f82',False)
 if g.at!=copy_entry:raise ValueError('fmvFinalString.copy-entry')
 copy=prove_inline_copy(rows,copy_entry,copy_finish,source='r9',copy_target=copy_target)
 if copy['maxBytes']!=256 or copy['completeCases']!=516:raise ValueError('fmvFinalString.complete-copy-bound')
 g.at=copy_finish;g.take('488bc6','488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,copy=copy,maxChars=128,arrayDataOffset=32,stringDataOffset=20,allocationChars='incoming count',returnedReference='unchanged nonnull allocation result',contents='exact input char[] slice[start:start+count]',
  condition='Positive count1..128 and nonnull stable compatible char[] with valid signed bounds and disjoint frame. Current allocation target returns normal compatible nonnull disjoint String with requested length and valid character storage; complete bounded-copy dependency required above32bytes. No zero-length String.Empty path, allocation internals, overlap, invalid/larger source or runtime execution receipt.')



def cached_string(regions,entry,*,mode,count):
 if type(mode)is not int or mode not in (0,3)or type(count)is not int or not 1<=count<=128:raise ValueError('fmvStringAllocation.selected-cache-domain')
 g=BytesPath(regions,entry);cells={}
 g.take('4157','4883ec50','4c63f9','85c9');g.branch('75',True,1)
 g.take('48897c2438','4a8d3c7d1a000000','418bc7','483bc7');g.branch('0f87',False)
 cells['stringClass']=g.relative('488b05');g.take('48895c2460','48896c2448','33ed');raw=g.read(7)
 if raw[:2]!=b'\x83\x3d'or raw[-1]!=1:raise ValueError('fmvStringAllocation.mode-guard')
 cells['mode']=g.at-1+int.from_bytes(raw[2:6],'little',signed=True)
 g.take('4889742440','8bf5','4889442470','b803000000','0f44f0','4c89642430');image_base=g.relative('4c8d25')
 g.take('4881ff00080000');g.branch('0f87',False)
 cells['lockFlag']=g.relative('392d');g.branch('74',True,1)
 g.take('498b8cfc');cells['requestSizeClassTable']=image_base+int.from_bytes(g.read(4),'little',signed=True)
 g.take('8bc6','48c1e005','4a8b8420');cells['freeListTable']=image_base+int.from_bytes(g.read(4),'little',signed=True)
 g.take('488b1cc8','488d14c8','4885db');g.branch('74',False,1)
 g.take('85f6');g.branch('74',mode==0,1)
 if mode==3:g.take('83fe03');g.branch('74',True,1)
 g.take('488b03','488902','48c1e104');cells['cacheAccounting']=g.relative('48010d')
 if g.relative('392d')!=cells['lockFlag']:raise ValueError('fmvStringAllocation.stable-lock-flag')
 g.branch('0f84',True)
 g.take('488b442470','488903','48896b08');cells['allocationCounter']=g.relative('f048ff05')
 raw=g.read(7)
 if raw[:2]!=b'\xf6\x05'or raw[-1]!=0x80:raise ValueError('fmvStringAllocation.profiler-guard')
 cells['profiler']=g.at-1+int.from_bytes(raw[2:6],'little',signed=True)
 g.take('4c8b642430','488b742440','44897b10','6642896c7b14','488b6c2448');g.branch('74',True,1)
 g.take('488b7c2438','488bc3','488b5c2460','4883c450','415f','c3')
 return dict(selectedBytes=g.seen,cells=cells,imageBase=image_base,mode=mode,charCount=count,requestedBlockBytes='26 + 2 * count',maxChars=128,
  stores=dict(classHeader=0,monitorZero=8,length=16,zeroWordAfterCharacters='20 + 2 * count'),returnedReference='same selected nonnull cached block',
  condition='Positive count1..128; runtime mode maps to0or3, lock flag0, selected free-list head is nonnull and identifies a disjoint adequately sized valid managed block; all class/cache/global cells and table addresses are valid stable disjoint storage. Selected class global equals initialized System.String class, profiler-mask0x80 clear. Exact class/length/terminator stores and free-list pop are proved; live allocator/provider/class binding, zero/wider counts, cold allocation, synchronization and collector behavior remain unproved.')



def format_result(regions,entry,*,arity,construct,append,string,cleanup):
 if type(arity)is not int or arity not in (1,2):raise ValueError('fmvFormatResult.arity')
 g=BytesPath(regions,entry);classes=[]
 if arity==1:
  g.take('4889542410','48894c2408','53','56','57','4156','4883ec78','498bf8','488bf2','4c8bf1','4983783800');g.branch('0f84',False)
  g.take('0f57c0','0f11442458','33db','48899c24b0000000')
 else:
  g.take('4c89442418','4889542410','48894c2408','53','56','57','4156','4157','4883ec70','498bf9','498bf0','4c8bf2','4c8bf9','4983793800');g.branch('0f84',False)
  g.take('0f57c0','0f11442460','33db','48899c24b8000000')
 classes.append(g.relative('488b0d'));g.take('3999e0000000');g.branch('0f84',False)
 g.take('b201','488d4c2458'if arity==1 else'488d4c2460');g.call(construct)
 if arity==1:g.take('48895c2448','488d442458','4889442450')
 else:g.take('48895c2450','488d442460','4889442458')
 classes.append(g.relative('488b0d'));g.take('83b9e000000000');g.branch('0f84',False)
 if arity==1:g.take('4c8b4f38','4d8b09','4c8bc6','498bd6','488d4c2458')
 else:g.take('488b4738','488b08','48894c2420','4c8bce','4d8bc6','498bd7','488d4c2460')
 g.call(append)
 g.take('448b442460'if arity==1 else'448b442468','4585c0');g.branch('0f84',False)
 g.take('4533c9','33d2','488b4c2458'if arity==1 else'488b4c2460');g.call(string)
 g.take('488bd8','48899c24b0000000'if arity==1 else'48899c24b8000000','488d4c2450'if arity==1 else'488d4c2458');g.call(cleanup)
 g.take('488bc3','4883c478'if arity==1 else'4883c470')
 if arity==2:g.take('415f')
 g.take('415e','5f','5e','5b','c3')
 if len(set(classes))!=1:raise ValueError('fmvFormatResult.same-builder-class')
 return dict(selectedBytes=g.seen,builderClassCell=classes[0],arity=arity,builderStackOffset=88 if arity==1 else 96,contextSlot=0,stringArguments=dict(source='constructed builder.buffer',start=0,count='builder.index after AppendFormat'),returnedReference='exact positive String.Ctor result across ordinary cleanup',
  condition='Ready valid closed string MethodInfo and builder class; current constructor/AppendFormat/positive String.Ctor helper components independently proved and selected with matched disjoint stack/value storage; final index1..128. Cleanup returns normally, preserves Win64 nonvolatile registers and does not interfere with disjoint returned String. No cold/exception/empty-result paths or live cache/allocator selection.')



def array_data(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1);g.take('488d4210','488d0441','4883c428','c3')
 return dict(selectedBytes=g.seen,returnedPointer='incoming RCX + 32',condition='Incoming EDX is zero, compatible valid nonnull char[] with length>0 at+24 and disjoint Win64 frame; invalid bounds/array type/live invocation are separate.')


def char_copy(regions,entry,rows,*,copy_target):
 g=BytesPath(regions,entry);g.take('4883ec28','478d0c00','4c8bc1','4c2bc2','418bc1','4c3bc0');g.branch('0f82',False)
 g.take('4c8bc2','418bc1','4c2bc1','4c3bc0');g.branch('0f82',False)
 proof=prove_inline_copy(rows,g.at,0,source='rdx',copy_target=copy_target,count_register='r9',stack_release=40)
 return dict(selectedBytes=g.seen,copy=proof,charCountBound=128,byteCount='2 * incoming R8D char count',source='incoming RDX',destination='incoming RCX',
  condition='Nonnull valid stable char-aligned source/destination with disjoint nonwrapping storage and count0..128; copy helper bounded dependency authenticated separately. Whole selected normal returns restore original stack/nonvolatiles; larger/overlapping/unselected runtime paths are excluded.')


def concat(regions,entry,*,type_handle,append,allocate,array_data,char_copy,dispose):
 g=BytesPath(regions,entry);classes=[];handles=[];imports=[]
 g.take('48895c2408','4889742410','57','4154','4155','4156','4157','4883ec50','498bf8','4c8bea','4c8bf1','4983783800');g.branch('75',True,1)
 g.take('0f57c0','0f11442428','4533ff','4c89bc2490000000');classes.append(g.relative('488b0d'));g.take('4439b9e0000000');g.branch('75',True,1)
 initialized=g.relative('44383d');g.branch('75',True,1)
 classes.append(g.relative('488b0d'));g.take('4439b9e0000000');g.branch('75',True,1)
 classes.append(g.relative('488b05'));g.take('4863b010010000');tls_index=g.relative('488b0d');g.take('8b09');imports.append(g.relative('ff15'))
 g.take('488bd8','4885c0');g.branch('75',True,1)
 g.take('488b4310','488b4060','488b0cf0','44387908');g.branch('0f85',False)
 g.take('41b401');classes.append(g.relative('488b05'));g.take('4439b8e0000000');g.branch('75',True,1)
 g.take('4863b010010000')
 if g.relative('488b0d')!=tls_index:raise ValueError('fmvConcat.TLS-index')
 g.take('8b09');imports.append(g.relative('ff15'));g.take('488bd8','4885c0');g.branch('75',True,1)
 g.take('488b4310','488b4060','488b0cf0','488b19','4885db');g.branch('75',True,1)
 classes.append(g.relative('488b05'));g.take('4439b8e0000000');g.branch('75',True,1)
 g.take('4c63b810010000')
 if g.relative('488b0d')!=tls_index:raise ValueError('fmvConcat.TLS-index')
 g.take('8b09');imports.append(g.relative('ff15'));g.take('488bf0','4885c0');g.branch('75',True,1)
 g.take('488b4610','488b4060','4a8b0cf8','44886108','4533ff');g.jump('eb',1)
 g.take('48895c2428');barrier=g.read(7)
 if barrier[:2]!=b'\x83\x3d'or barrier[-1]!=0:raise ValueError('fmvConcat.barrier-flag')
 g.branch('74',True,1)
 g.take('44897c2430','4488642434','4c897c2438','488d442428','4889442440')
 for n in (0,1):
  g.take('488b5f38','488b1b'if n==0 else'488b5b18');type_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
  g.take('33d2','488bcb');g.call(type_handle);g.take('488bd8','33d2');handles.append(g.relative('488b0d'));g.call(type_handle)
  g.take('483bd8');g.branch('0f84',True)
  g.take('4d85f6'if n==0 else'4d85ed');g.branch('74',False,1)
  classes.append(g.relative('488b0d'));g.take('83b9e000000000');g.branch('75',True,1)
  g.take('498bd6'if n==0 else'498bd5','488d4c2428');g.call(append)
 classes.append(g.relative('488b0d'));g.take('83b9e000000000');g.branch('75',True,1)
 g.take('8b7c2430','85ff');g.branch('74',False,1)
 g.take('488b742428','4885f6');g.branch('0f84',False)
 g.take('85ff');g.branch('0f88',False)
 g.take('397e18');g.branch('0f88',False)
 g.take('8bcf');g.call(allocate);g.take('488bd8','4885c0');g.branch('0f84',False)
 g.take('837e1800');g.branch('74',False,1)
 g.take('33d2','488bce');g.call(array_data);g.take('4c8bf8','4533c9','448bc7','498bd7','488d4b14');g.call(char_copy);g.jump('eb',1)
 g.take('48899c2490000000');classes.append(g.relative('488b0d'));g.take('83b9e000000000');g.branch('75',True,1)
 g.take('488d4c2428');g.call(dispose);g.jump('eb',1)
 g.take('488bc3','4c8d5c2450','498b5b30','498b7338','498be3','415f','415e','415d','415c','5f','c3')
 if len(set(classes))!=1 or len(set(imports))!=1 or len(set(handles))!=1:raise ValueError('fmvConcat.same-class-TLS-string-handle')
 return dict(selectedBytes=g.seen,builderClassCell=classes[0],typeClassCell=type_class,stringTypeHandleCell=handles[0],tlsIndexCell=tls_index,tlsImportCell=imports[0],initializedFlagCell=initialized,
  builderStackOffset=40,bufferOffset=0,indexOffset=8,usedFlagOffset=12,initialIndex=0,argumentOrder=[0,1],contextTypeHandleSlots=[0,3],allocationChars='String0.length + String1.length',result='Exact original first string UTF16 chars followed by original second string UTF16 chars; unchanged fresh String result across normal Dispose.',
  condition='Ready valid closed string,string MethodInfo; initialized builder/type classes and metadata, stable same-thread nonnull TLS contexts with scratch-used0 and existing sufficient char[] buffer, barrier flag0. Type.GetTypeFromHandle called with the two actual closed String type handles and the same current String type cell; selected equalities true. Inputs nonnull stable String, each length0..128 with sum1..128. Independently proved append/allocator/array-data/char-copy components and normal noninterfering Dispose preserve output/nonvolatile registers. No live cache/TLS/provider/default/type-equality inference, empty/cold/growth/custom type or owner/playback claim.')


def ordinary_concat(regions,entry,rows,*,allocate,copy_target,copy_entries,copy_finishes,left=10,right=2):
 if any(type(n)is not int for n in (left,right))or not 1<=left<=128 or not 1<=right<=128 or left+right>128 or len(copy_entries)!=2 or len(copy_finishes)!=2:raise ValueError('fmvRootConcat.positive-bounded-strings')
 g=BytesPath(regions,entry);g.take('4053','57','4883ec28','488bfa','488bd9','4885c9');g.branch('0f84',False)
 g.take('83791000');g.branch('0f86',False);g.take('4885d2');g.branch('0f84',False);g.take('837a1000');g.branch('0f86',False)
 g.take('4889742448','4c89742458','48896c2440','4c637110','8b4a10','4103ce');g.call(allocate)
 g.take('488bf0','8b4310','4885f6');g.branch('0f84',False);g.take('3b4610');g.branch('0f8f',False)
 g.take('448d0400','4c8d4e14','498bc1','488d5314','482bc2','493bc0');g.branch('0f82',False)
 g.take('488bca','492bc9','493bc8');g.branch('0f82',False)
 if g.at!=copy_entries[0]:raise ValueError('fmvRootConcat.first-copy-join')
 first=prove_inline_copy(rows,g.at,copy_finishes[0],source='rdx',destination_register='r9',copy_target=copy_target);g.at=copy_finishes[0]
 g.take('8b4610','412bc6','394710');g.branch('0f8f',False)
 g.take('8b4710','498d4e0a','488d0c4e','4c8d4f14','448d0400','488bc1','492bc1','493bc0');g.branch('0f82',False)
 g.take('498bd1','482bd1','493bd0');g.branch('0f82',False)
 if g.at!=copy_entries[1]:raise ValueError('fmvRootConcat.second-copy-join')
 second=prove_inline_copy(rows,g.at,copy_finishes[1],source='r9',copy_target=copy_target);g.at=copy_finishes[1]
 g.take('488b6c2440','488bc6','488b742448','4c8b742458','4883c428','5f','5b','c3')
 return dict(selectedBytes=g.seen,copies=[first,second],maxResultChars=128,allocationChars='left.length + right.length',result='exact original left UTF16 chars then original right UTF16 chars in fresh allocated String',
  condition='Both inputs nonnull stable String, positive lengths with sum<=128; independently authenticated cached String allocator returns compatible requested-length storage. Original input/output/frame/globals disjoint and nonwrapping; complete bounded-copy dependency for larger calls. No empty/null/overlap/cold/larger String, runtime class/cache/allocator binding or caller/source admission.')


def video_root(regions,entry,*,concat,receiver_present=False):
 if type(receiver_present)is not bool:raise ValueError('fmvRoot.selected-hook-domain')
 g=BytesPath(regions,entry);hooks=g.relative('488b05');raw=g.read(7)
 if raw[:2]!=b'\xc6\x05'or raw[-1]!=1:raise ValueError('fmvRoot.initialized-flag-store')
 g.take('488b4878','4885c9');g.branch('74',not receiver_present,1)
 if receiver_present:g.take('488b8130b80000','4885c0');g.branch('74',True,1)
 platform=g.relative('488b05');prefix=g.relative('488b0d');g.take('4533c0','488bd0');g.call(concat)
 owner=g.relative('488b0d');g.take('488b91b8000000','48894228')
 return dict(selectedBytes=g.seen,hookTableCell=hooks,platformLiteralCell=platform,prefixLiteralCell=prefix,sourceTypeCell=owner,staticStorageOffset=184,videoPathFieldOffset=40,storedValue='ordinary String.Concat(prefix literal, PC platform literal)',
  condition='Selected current VFSDefine initializer has reached this owned block with valid initialized metadata/static storage; hook table valid and selected receiver absent or selected callback absent. Literal cells initialized to separately authenticated values and ordinary bounded Concat proof selected; later initialized field read remains stable/noninterfered. Hook/runtime/global contents, preceding/cold/other initializer paths and live execution are not inferred.')


def _flag(g):
 raw=g.read(7)
 if raw[:2]!=b'\x80\x3d'or raw[-1]!=0:raise ValueError('fmvConsumer.initializer-flag')
 return g.at-1+int.from_bytes(raw[2:6],'little',signed=True)


def action_tail(regions,entry,*,wait,movie_slot,get,initialize,play,pause=None,allocate=None,callback=None):
 if type(wait)is not bool or type(movie_slot)is not int or not 16<=movie_slot<0x80000000:raise ValueError('fmvConsumer.action-tail-selection')
 g=BytesPath(regions,entry)
 if wait:g.take('488bcb');g.call(pause)
 method_info=g.relative('4c8b0d');g.take('41b001','488b8b'+movie_slot.to_bytes(4,'little').hex())
 if wait:g.take('33d2')
 g.call(get)
 if wait:
  callback_type=g.relative('488b0d');g.take('488be8');g.call(allocate);g.take('488bf0','4885c0');g.branch('75',True,1)
  callback_method=g.relative('4c8b05');g.take('4533c9','488bd3','488bce');g.call(callback);action_type=g.relative('488b0d');g.call(initialize);g.take('488bd6','488bcd')
 else:
  action_type=g.relative('488b0d');g.take('488bd8');g.call(initialize);g.take('33d2','488bcb');g.jump('eb',1)
 g.take('4c8bcf','48c744242000000000','4533c0');g.call(play)
 g.take('488b5c2450','488b6c2458','488b742460','0f28742430','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,methodInfoCell=method_info,actionTypeCell=action_type,wait=wait,movieSlot=movie_slot,transfer='same GetValue<string> result passed in RCX to GameAction.PlayFmv',condition='Selected action tail reached with valid Action/Param/storage, current constant-source GetValue proof and initialized typed context; wait selects one of both complete tails. Ordinary pause/initializer/allocation/callback construction returns normally without source/String interference and preserves nonvolatile registers. No activation/prior action fields/provider/live playback claim.')


def play_name_probe(regions,entry,*,initialize,gender,subpath,check):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4156','4157','4883ec40','33db','498bf1');initialized=g.relative('381d');g.take('4d8bf0','488bea','488bf9');g.branch('75',True,1)
 hooks=g.relative('488b05');g.take('488b4828','4885c9');g.branch('74',True,1)
 source_class=g.relative('488b0d');g.take('48895c2438','48895c2430');g.call(initialize)
 g.take('4533c0','488bd7','33c9');g.call(gender);g.take('33d2','488bc8','4c8bf8');g.call(subpath)
 g.take('4533c0','488d542430','488bc8');g.call(check)
 return dict(selectedBytes=g.seen,initializedFlagCell=initialized,hookTableCell=hooks,sourceTypeCell=source_class,gender=0,transfer='incoming RCX string -> GetGenderedFMVId(0,string) -> GetCSVideoAssetSubPath(result) -> CheckCanPlay(result,out local)',condition='Initialized original PlayFmv path with absent selected iFix receiver and stable inputs; normal noninterfering initialization and independently proved naming/check helpers. Stops at name probe; queue/PlayParam/callback ownership, execution/activation/order/playback remain separate.')


def do_play_name(regions,entry,*,initialize,gender,play):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec30');_flag(g);g.take('498be9','498bd8','488bfa','488bf1');g.branch('75',True,1)
 hooks=g.relative('488b05');g.take('488b4828','4885c9');g.branch('74',True,1)
 source_class=g.relative('488b0d');g.call(initialize);g.take('4533c0','488bd6','33c9');g.call(gender)
 manager_class=g.relative('488b0d');g.take('488bf0');g.call(initialize)
 if g.relative('488b0d')!=manager_class:raise ValueError('fmvConsumer.same-manager-class')
 g.take('488b91b8000000','488b4a78','4885c9');g.branch('75',True,1)
 g.take('48c744242800000000','4c8bcb','4c8bc7','48c744242000000000','488bd6');g.call(play)
 g.take('488b5c2440','488b6c2448','488b742450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,hookTableCell=hooks,sourceTypeCell=source_class,managerTypeCell=manager_class,managerStaticSlot=120,transfer='incoming RCX string -> GetGenderedFMVId(0,string), exact result in RDX to selected direct manager target',condition='Initialized original path with absent selected iFix receiver and compatible nonnull selected manager; ordinary initialization/gender/direct manager calls preserve nonvolatile registers and disjoint storage. Actual target/typed declarations separately gated; no live manager binding or playback/activation/order receipt.')


def exists(regions,entry,*,initialize,subpath,resolve):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');_flag(g);g.take('488bfa','488bd9');g.branch('75',True,1)
 hooks=g.relative('488b05');g.take('488b4808','4885c9');g.branch('74',True,1)
 source=g.relative('488b0d');g.take('48c744244000000000');g.call(initialize);g.take('33d2','488bcb');g.call(subpath);g.take('4533c0','488d542440','488bc8');g.call(resolve)
 g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,hookTableCell=hooks,sourceTypeCell=source,transfer='incoming id -> GetCSVideoAssetSubPath -> TryGetVideoPlayFullPath with disjoint local out string; resolver AL returned unchanged',condition='Initialized original path, absent selected iFix receiver, valid stable String/stack; normal noninterfering initializer and independently gated subpath/resolver. File existence/live VFS result remains conditional.')


def check_can_play(regions,entry,*,ends,resolve):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20');_flag(g);g.take('498bf0','488bfa','488bd9');g.branch('75',True,1)
 hooks=g.relative('488b05');g.take('488b4840','4885c9');g.branch('74',True,1)
 g.take('4885db');g.branch('75',True,1)
 suffix=g.relative('488b15');g.take('4533c9','4533c0','488bcb');g.call(ends);g.take('84c0');g.branch('75',False,1)
 g.take('4533c0','488bd7','488bcb');g.call(resolve);g.take('84c0','0f95c0');g.jump('eb',1)
 g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,hookTableCell=hooks,suffixLiteralCell=suffix,transfer='same incoming subpath and out pointer -> TryGetVideoPlayFullPath; AL normalized bool',condition='Initialized original path, absent selected iFix receiver, nonnull stable subpath; selected ordinary EndsWith test for authenticated .mp4 literal is false. Typed EndsWith and resolver independently gated. mp4/error/live VFS/playback paths excluded.')


def resolve_path(regions,entry,*,asset,singleton,resolve):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec60');_flag(g);g.take('498bf8','488bf2','488bd9');g.branch('75',True,1)
 hooks=g.relative('488b05');g.take('488b4840','4885c9');g.branch('0f85',False)
 g.take('0f57c0','c684248800000000','33d2','488bcb','0f11442430','0f11442440','0f11442450');g.call(asset)
 source=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('75',True,1)
 g.take('33c9');g.call(singleton);g.take('4885c0');g.branch('75',True,1)
 g.take('488d4c2430','48c744242800000000','48894c2420','4c8d8c2488000000','488bc8','4c8bc6','488bd3');g.call(resolve)
 g.take('488b5c2470','488b742478','4883c460','5f','c3')
 return dict(selectedBytes=g.seen,hookTableCell=hooks,sourceTypeCell=source,transfer='incoming subpath -> GetVideoAssetPath; same result in RDX and unchanged incoming out string pointer in R8 to selected VFS resolver',condition='Initialized original path with absent selected iFix receiver, compatible nonnull selected VFS singleton and stable disjoint source/output/frame; ordinary independently gated asset-name/helper calls. Actual singleton/VFS bindings, physical full path/result and playback are not inferred.')


def flag(g):
 raw=g.read(7)
 if raw[:2]!=b'\x80\x3d' or raw[-1]!=0:raise ValueError('fmvName.initializer-flag')
 return g.at+int.from_bytes(raw[2:6],'little',signed=True)

def gender_id(regions,entry,s,*,query_gender=False,female=False,exists=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20');flag(g);g.take('498bd8','488bf2','8bf9');g.branch('75',True,1)
 hooks=g.relative('488b05');g.take('488b4808','4885c9');g.branch('74',True,1)
 g.take('85ff');g.branch('75',not query_gender,1)
 if query_gender:g.relative('488b0d');g.call(s['typeInit']);g.take('33c9');g.call(s['gender']);g.take('8bf8')
 male=g.relative('488b1d');g.take('83ff02');female_cell=g.relative('480f441d');g.relative('488b0d');g.call(s['typeInit']);concat_context=g.relative('4c8b05');g.take('488bd6','488bcb');g.call(s['concat']);g.relative('488b0d');g.take('488bd8');g.call(s['typeInit']);g.take('33d2','488bcb');g.call(s['exists']);g.take('84c0','480f44de','488bc3','488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,hookTable=hooks,literalCells=dict(male=male,female=female_cell),concatContextCell=concat_context,result=('female-prefix' if female else 'male-prefix')+' plus input id' if exists else 'unchanged input id',queriedNarrativeGender=query_gender,condition='Initialized metadata, absent selected iFix receiver, valid stable references, effective gender equals the selected witness, ordinary type initialization/concatenation/existence helpers preserving Win64 nonvolatile registers; existence result equals selected witness.')

def cutscene_subpath(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag(g);g.take('488bfa','488bd9');g.branch('75',True,1);hooks=g.relative('488b05');g.take('488b08','4885c9');g.branch('74',True,1);context=g.relative('4c8b05');g.take('488bd3');literal=g.relative('488b0d');g.call(s['format']);g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,hookTable=hooks,formatContextCell=context,formatLiteralCell=literal,inputToFormat='unchanged incoming RCX -> RDX',condition='Initialized metadata, absent selected iFix receiver and normal correctly typed formatting helper with stable references.')

def video_asset_path(regions,entry,s,*,has_suffix=False):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag(g);g.take('488bfa','488bd9');g.branch('75',True,1);hooks=g.relative('488b05');g.take('488b4840','4885c9');g.branch('0f85',False);g.take('4885db');g.branch('74',False,1);suffix=g.relative('488b15');g.take('4533c9','4533c0','488bcb');g.call(s['endsWith']);g.take('84c0');source_type=g.relative('488b05');g.branch('0f85',has_suffix)
 g.take('83b8e000000000');g.branch('75',True,1)
 g.take('488b80b8000000' if has_suffix else '488b90b8000000');literal=g.relative('488b0d');g.take('488b5028' if has_suffix else '488b5228')
 if has_suffix:g.jump('e9')
 context=g.relative('4c8b0d');g.take('4c8bc3');g.call(s['format']);g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,hookTable=hooks,suffixCell=suffix,formatLiteralCell=literal,formatContextCell=context,sourceTypeCell=source_type,storedBasePathOffset=40,hasSuffix=has_suffix,inputToFormat='unchanged incoming RCX -> R8; static base path -> RDX',condition='Initialized metadata and selected static source class; absent selected iFix receiver, nonnull input, normal EndsWith/typed formatting helpers preserving nonvolatile registers; comparison result equals selected witness.')

