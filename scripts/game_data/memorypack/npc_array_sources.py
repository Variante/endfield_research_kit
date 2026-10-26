"""Complete selected reference-array reader paths; closed element source is separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def string_array(regions, entry, offsets, symbols, *, count):
    if type(count) is not int or not -1 <= count <= 5:
        raise ValueError('npcStringArray.selected-count')
    g = BytesPath(regions, entry)
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex() for n in ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('48895c2418','48896c2420','56','57','4156','4883ec20','48837a3800','488bfa','488bd9'); g.branch('75',True,1)
    g.take('488b4738','33f6','4889742440','488b38','48397738'); g.branch('75',True,1)
    g.take('837b'+rem+'04'); g.branch('7d',True,1)
    g.take('488b43'+cur,'8b28','448b73'+rem,'4183c6fc'); g.branch('79',True,1)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','448973'+rem,'486343'+used,'488b4b'+total,'482bc8','4863c5','483bc8'); g.branch('0f8c',False)
    g.take('83fdff'); g.branch('0f84',count==-1)
    collectors=[];callbacks=[];provider_cell=None
    if count==-1:
        collectors.append(g.relative('3935')); g.take('4889742440'); g.branch('74',True,1)
    else:
        g.take('85ed'); g.branch('0f84',count==0)
        if count:
            g.take('488b442440','4885c0'); g.branch('74',True,1)
            g.take('488b4738','488b4010','f6803801000001'); g.branch('75',True,1)
            g.take('488bd5','488bc8'); g.call(symbols['arrayAllocate'])
            collectors.append(g.relative('3935')); g.take('4889442440'); g.branch('74',True,1)
            provider_cell=g.relative('488b0d'); g.take('39b1e0000000'); g.branch('75',True,1)
            g.take('488b4f38','488b4918'); g.call(symbols['provider'])
            g.take('4c8bf0','85ed'); g.branch('0f8e',False)
            g.take('6666660f1f840000000000'); loop=g.at
            for index in range(count):
                if g.at!=loop:raise ValueError('npcStringArray.same-loop-entry')
                g.take('488b7c2440','4885ff'); g.branch('0f84',False)
                g.take('4d85f6'); g.branch('0f84',False)
                g.take('3b7718'); g.branch('0f83',False)
                g.take('498b0e'); g.call(symbols['prepare'])
                g.take('4d8b0e','488bd3','8bc6','498bce','4883c004','4c8d04c7','498b8190010000','4d8b8998010000')
                callbacks.append(g.at); g.take('ffd0','ffc6','3bf5'); g.branch('7c',index+1<count,1)
            g.jump('e9')
        else:
            g.take('488b4738','488b5808','48397338'); g.branch('75',True,1)
            g.take('488b4338','488b00','f6803801000001'); g.branch('75',True,1)
            g.take('39b0e0000000'); g.branch('75',True,1)
            g.take('488b4338','488b00','f6803801000001'); g.branch('75',True,1)
            collectors.append(g.relative('3935'))
            g.take('488b80b8000000','488b08','48894c2440'); g.branch('0f84',True)
    g.take('488b442440','488b5c2450','488b6c2458','4883c420','415e','5f','5e','c3')
    return dict(selectedBytes=g.seen,count=count,headerBytes=4,managedElementStride=8,
                arrayDataOffset=32,elementCallbackSites=callbacks,providerClassCellVA=provider_cell,
                disabledCollectorCells=collectors,elementFormatterSlot=5,callbackReceiver='r14',
                callbackReader='same incoming RCX saved RBX',callbackOutput='fresh array +32+8*index',
                callbackMethodInfo='same selected formatter class slot5 MethodInfo',normalReturn=True,
                outputStartsNull=True,wholeOwnerAdmitted=False,childFramingProved=False,
                condition='Ready coherent method contexts and classes, buffered valid disjoint Reader/frame; signed count -1/0/1..5 with enough remaining budget, disabled collector, normal typed fresh array allocation and provider/preparation ABI. Selected element formatter must independently be current pooled-string formatter; runtime provider/cache contents, allocation/empty-array identity and child decoding remain independently conditional.')


"""Current standalone Int32 array source; typed dependencies are independently gated."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def int_array(regions,entry,offsets,symbols,*,count):
 if type(count)is not int or not -1<=count<=5:raise ValueError('EnvTalk.intArray.count')
 g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','48837a3800','488bfa','488bd9');g.branch('0f84',False);g.take('488b4738','488b28','48837d3800');g.branch('0f84',False)
 g.take('837b'+rem+'04');g.branch('0f8c',False);g.take('488b43'+cur,'486338','8b73'+rem,'83c6fc');g.branch('0f88',False)
 g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','8973'+rem,'486343'+used,'488b53'+total,'482bd0','483bd7');g.branch('0f8c',False)
 g.take('83ffff');g.branch('74',count==-1,1)
 if count==-1:g.take('33ff');g.jump('eb',1)
 else:
  g.take('85ff');g.branch('75',count!=0,1)
  if count==0:g.take('488b4d38','488b09');g.call(symbols['empty']);g.take('488bf8')
  else:
   g.take('8d34bd00000000','3b73'+rem);g.branch('0f8f',False);g.take('4c8b4538','33d2','8bcf','4d8b4008');g.call(symbols['allocate']);g.take('488b5538','488bc8','488bf8','488b5210');g.call(symbols['dataReference']);g.take('488b53'+cur,'488bc8','448bc6');g.call(symbols['copy']);g.take('8bd6','488bcb');g.call(symbols['advance']);g.jump('eb',1)
 g.take('488b5c2430','488bc7','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,count=count,headerBytes=4,elementBytes=4,copyBytes=max(0,count)*4,sameReader='entry RCX preserved RBX',newArray='allocator RAX preserved RDI and returned unchanged',copySource='same Reader currentPtr after header',copyTarget='typed allocated array data reference',normalReturn=True,condition='Ready coherent current Int32 method contexts; buffered disjoint valid Reader and signed count -1/0/1..5, sufficient payload, exact independently gated copy/Advance and typed normal empty/allocation/data-reference helpers. Runtime initialization/execution remain conditional; no parent admission.')


def int_empty(regions,entry,s):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','4883793800','488bd9');g.branch('74',False,1);g.take('488b4b38','33d2');g.call(s['indexed']);g.take('83b8e000000000');g.branch('74',False,1);g.take('488b4b38','33d2');g.call(s['indexed']);g.take('488b80b8000000','488b00','4883c420','5b','c3');return dict(selectedBytes=g.seen,contextSlot=0,normalReturn=True,condition='Ready same typed Empty<int> context and initialized class; matching static array exists. Empty object identity and runtime initialization remain conditional.')

def int_allocate(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','4983783800','498bd8','8bf9');g.branch('74',False,1);g.take('488b4b38','33d2');g.call(s['indexed']);g.take('488bd7','488bc8','488b5c2430','4883c420','5f')
 if g.relative('e9')!=s['arrayAllocate']:raise ValueError('npcIntArray.allocate-tail')
 return dict(selectedBytes=g.seen,normalReturn=True,allocationClassContextSlot=0,count='unchanged incoming ECX zero-extended via EDI',condition='Ready typed AllocateUninitializedArray<int> array context and normal exact typed native allocation with requested count. Runtime allocation implementation/contents remain conditional.')

def int_data_reference(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec30','48837a3800','488bda','488bf9');g.branch('74',False,1);g.take('4c8b4338','488d4c2420','488bd7','4d8b00');g.call(s['asSpan']);g.take('488b4338','488b4808','4883793800');g.branch('74',False,1);g.take('488b442420','488b5c2440','4883c430','5f','c3');return dict(selectedBytes=g.seen,normalReturn=True,result='unchanged first QWORD of typed AsSpan<int> output',condition='Ready matching method contexts, disjoint frame/array; AsSpan and Span constructor source independently required.')

def array_as_span(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4983783800','498bf8','488bf2','488bd9');g.branch('74',False,1);g.take('0f57c0','488bd6','0f1103','4c8b4738','488bcb','4d8b4008');g.call(s['spanConstructor']);g.take('488b742438','488bc3','488b5c2430','4883c420','5f','c3');return dict(selectedBytes=g.seen,normalReturn=True,output='entry RCX hidden16 result initialized then passed unchanged to exact Span<int> constructor',array='entry RDX unchanged through RSI',condition='Ready typed context and disjoint valid array/result/frame; exact Span ctor source separately gated.')


def array_span_constructor(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bda','488bf9');g.branch('74',False,1);g.take('4885db');g.branch('74',False,1);g.take('488d4320','488907','8b4318','894708','488b5c2430','4883c420','5f','c3');return dict(selectedBytes=g.seen,normalReturn=True,arrayDataOffset=32,arrayLengthOffset=24,spanPointerOffset=0,spanLengthOffset=8,condition='Initialized metadata, nonnull matching typed array, disjoint valid result; exact output pointer=array+32 and length=stored array length. Runtime construction/inflation remain conditional.')
