"""Current selected warm generated-reader entry and normal-return framing."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def branch(g,short,near,taken):
    if g.bytes.get(g.at)==int(short,16):g.branch(short,taken,1)
    else:g.branch(near,taken,4)


def prefix(regions,entry,s,*,frame,cached=False,nav=False,reverse=False,member_count):
    if frame not in(32,48,64)or not 1<=member_count<255 or nav and(frame!=64 or not cached or reverse):raise ValueError('modelViewReader.scope')
    g=BytesPath(regions,entry);saved=g.read(5)
    if saved not in(bytes.fromhex('48895c2418'),bytes.fromhex('48895c2408'),bytes.fromhex('48895c2410')):raise ValueError('modelViewReader.save-rbx')
    save_rsi=g.bytes.get(g.at)==0x48
    if save_rsi:g.take('4889742418')
    if nav:g.take('48897c2420','55','488bec')
    else:g.take('57')
    g.take('4883ec'+bytes((frame,)).hex());g.relative('803d');g.take('00','488bfa'if reverse else'488bda','488bd9'if reverse else'488bf9')
    if g.bytes.get(g.at)==0x75:g.branch('75',True,1)
    else:g.branch('0f84',False,4)
    slot=frame+24 if cached else frame+16;slot_hex=bytes((slot,)).hex()
    if cached:
        g.take('488b0b','c6451800'if nav else'c64424'+slot_hex+'00','4885c9')
        if g.bytes.get(g.at)==0x74:g.branch('74',False,1)
        else:g.branch('0f85',True,4)
        g.take('33d2');g.call(s['onDeserialized'])
        if g.bytes.get(g.at)==0x90:g.take('90')
        if g.bytes.get(g.at)==0xe9:g.jump('e9',4)
        g.take('488d5518'if nav else'488d5424'+slot_hex)
    else:g.take('488d5424'+slot_hex,'c64424'+slot_hex+'00')
    g.take('488bcb'if reverse else'488bcf');g.call(s['header']);g.take('84c0');branch(g,'74','0f84',False)
    if not save_rsi:g.take('48897424'+bytes((frame+16 if cached else frame+24,)).hex())
    g.take('48833f00'if reverse else'48833b00')
    if g.bytes.get(g.at)==0x75 or g.bytes.get(g.at)==0x0f and g.bytes.get(g.at+1)==0x85:branch(g,'75','0f85',True)
    else:branch(g,'74','0f84',False)
    mc=bytes((member_count,)).hex()
    if g.bytes.get(g.at)!=0x0f:g.take('807d18'+mc if nav else'807c24'+slot_hex+mc)
    else:g.take('0fb67424'+slot_hex,'4080fe'+mc)
    branch(g,'75','0f85',False)
    return dict(selectedBytes=g.seen,end=g.at,reader='rdi'if not reverse else'rbx',holder='rbx'if not reverse else'rdi',frame=frame,savedRbxOffset=saved[-1],savedRsiAtEntry=save_rsi,memberCount=member_count,sameReaderAndOutput=True,headerOutputSlot=24 if nav else slot,condition='Initialized typed generated wrapper and stable nonnull incoming ref output; OnDeserialized is the separately proved exact owned callback and preserves caller Reader/output locals. Current header helper succeeds with the selected stored count. Win64 normal helper ABI, disjoint stable storage and runtime allocator/constructor/barrier effects remain conditional. Null/new/error routes separate.')


def on_deserialized(regions,entry,s,*,cache,path):
    if cache not in(24,32)or path not in('cached','empty-base','refresh'):raise ValueError('modelViewReader.callback-scope')
    g=BytesPath(regions,entry);c=bytes((cache,)).hex();g.take('48895c2408','57','4883ec20','33db','488bf9');g.relative('381d');g.branch('75',True,1);g.take('48395f'+c);g.branch('75',path=='cached',1);cell=None
    if path!='cached':
        g.take('48395f10');g.branch('74',path=='empty-base',1)
        if path=='refresh':
            g.take('488b5f10');cell=g.relative('488b15');g.take('488bcb');g.call(s['cast']);g.take('488947'+c,'488bcb');second=g.relative('488b15');g.call(s['cast']);g.take('488d4f'+c);g.call(s['barrier'])
            if cell!=second:raise ValueError('modelViewReader.callback-class-context')
    g.take('488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,baseSlot=16,cacheSlot=cache,path=path,castClassCell=cell,baseUnchanged=True,normalReturn=True,condition='Initialized exact typed wrapper, stable storage and selected cache/base condition. Compatible cast normally returns same full base reference; disabled collector and ordinary Win64 ABI preserve caller reader/output aliases. Predicate, allocation and runtime storage effects conditional.')


def normal_return(regions,entry,*,frame,saved_rbx,saved_rsi=None,nav=False,setting=False,embedded=False):
    if setting:
        if(frame,saved_rbx,saved_rsi,nav,embedded)!=(128,24,None,False,False):raise ValueError('modelViewReader.setting-return-scope')
    elif frame not in(32,48,64)or saved_rbx not in(8,16,24)or nav and(frame,saved_rbx,saved_rsi,embedded)!=(64,8,96,False):raise ValueError('modelViewReader.return-scope')
    g=BytesPath(regions,entry)
    if g.bytes.get(g.at)in(0xeb,0xe9):g.jump('eb',1)if g.bytes[g.at]==0xeb else g.jump('e9',4)
    if setting:g.take('4c8d9c2480000000','498b5b40','498b6b48','498be3','415f','415e','415c','5f','5e','c3')
    elif embedded:g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    else:
        if nav:g.take('488b5c2450','488b742460','488b7c2468')
        else:
            if g.bytes.get(g.at+2)==0x74:
                if saved_rsi is None:raise ValueError('modelViewReader.unproved-rsi-save')
                g.take('488b7424'+bytes((saved_rsi,)).hex())
            g.take('488b5c24'+bytes((saved_rbx+frame+8,)).hex())
            if g.bytes.get(g.at+2)==0x74:
                if saved_rsi is None:raise ValueError('modelViewReader.unproved-rsi-save')
                g.take('488b7424'+bytes((saved_rsi,)).hex())
        g.take('4883c4'+bytes((frame,)).hex(),'5d'if nav else'5f','c3')
    return dict(selectedBytes=g.seen,normalReturn=True,entryRspRestored=True,noReaderAccess=True,condition='The current ordered-field transfer reaches this exact continuation with the independently proved prologue frame and unchanged saved nonvolatiles; any early RSI restoration is separately checked in its field interval. Only frame restoration and normal RET occur here.')


def inline_prefix(regions,entry,offsets,*,setting=False):
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'));g=BytesPath(regions,entry)
    if setting:
        g.take('48895c2418','48896c2420','56','57','4154','4156','4157','4881ec80000000','33db');image_base=g.relative('4c8d25');g.relative('381d');g.take('4c8bf2','4c8bf9');g.branch('0f85',True,4);g.take('41837f'+rem+'01');g.branch('7d',True,1);g.take('498b47'+cur,'0fb628','418b7f'+rem,'83ef01');g.branch('79',True,1);g.take('49ff47'+cur,'41ff47'+adv,'41ff47'+used,'41897f'+rem,'4080fdff');g.branch('0f84',False,4);g.take('49391e');g.branch('0f85',True,4);g.take('4080fd0b');g.branch('0f85',False,4)
    else:
        image_base=None;g.take('48895c2408','48896c2410','4889742418','57','4883ec20');g.relative('803d');g.take('00','488bfa','488bd9');g.branch('0f84',False,4);g.take('837b'+rem+'01');g.branch('0f8c',False,4);g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False,4);g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('0f84',False,4);g.take('48833f00');g.branch('0f84',False,4);g.take('4080fe07');g.branch('0f85',False,4)
    return dict(selectedBytes=g.seen,end=g.at,reader='r15'if setting else'rbx',holder='r14'if setting else'rdi',memberCount=11 if setting else 7,headerBytes=1,currentPointerDelta=1,bufferLengthDelta=-1,advancedCountDelta=1,consumedDelta=1,nativeImageBase=image_base,condition='Selected initialized metadata/class state, at least one buffered byte with signed nonnegative subtraction, stored exact count and stable nonnull typed wrapper output. Actual refill/error/null/new-wrapper and runtime storage effects remain separate.')

