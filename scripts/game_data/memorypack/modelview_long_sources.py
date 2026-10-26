"""Selected signed-long list caller and exact counter loop; helper effects stay conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def list_source(regions,entry,s,*,mode='positive'):
    if mode not in('null','zero','positive'):raise ValueError('modelViewLong.list-mode')
    g=BytesPath(regions,entry);g.take('4053','57','4154','4156','4883ec38');g.relative('803d');g.take('00','498bd9','498bf8','4c8bf2');g.branch('0f84',False);g.take('4533e4','488d542468','498bce','4489642468','4c89642420');g.call(s['header']);g.take('84c0');g.branch('0f84',mode=='null')
    loop=None;callback=None;backedge=None
    if mode=='null':g.take('488bcf','4c8927');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('4889742470','48896c2460','4c896c2478','4c897c2430','8b742468','4c3927');g.branch('0f85',False);g.take('488b4b20','33d2','488b89c0000000');g.call(s['indexed']);g.take('488bc8');g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False);g.take('488b4b20','488b91c0000000','488b4a08','4c396120');g.branch('0f84',False);g.take('488b4320','8bd6','488bcd','4c8b80c0000000','4d8b4008');g.call(s['constructor']);g.take('488bcf','48892f');g.call(s['barrier']);ready=g.relative('488b0d');g.take('4439a1e0000000');g.branch('0f84',False);g.take('488b4320','488b88c0000000','488b4918');g.call(s['provider']);g.take('488be8','458bfc','85f6');g.branch('7f',mode=='positive',1)
        if mode=='positive':
            loop=g.at;g.take('4c89642420','4885ed');g.branch('74',False,1);g.take('4c8d4c2420','4d8bc6','488bd5');callback=g.at;g.call(s['dispatch']);g.take('4c8b27','4c8b6c2420','4d85e4');g.branch('74',False,1);g.take('488b4320','4c8b80c0000000','498b4030','4883782000');g.branch('0f84',False);g.take('488b4320','498bd5','498bcc','4c8b80c0000000','4d8b4030');g.call(s['add']);g.take('41ffc7','41bc00000000','443bfe');fallthrough=g.at+6;g.branch('0f8d',True);edge=BytesPath(regions,fallthrough);backedge=edge.relative('eb',1)
            if backedge!=loop:raise ValueError('modelViewLong.exact-counter-backedge')
        g.take('4c8b6c2478','488b6c2460','4c8b7c2430','488b742470')
    g.take('4883c438','415e','415c','5f','5b','c3')
    return dict(selectedBytes=g.seen,mode=mode,loopEntry=loop,backedge=backedge,callbackSite=callback,wireCountBytes=4,elementBits=64,sameReader=True,sameOutput=True,normalReturn=True,induction='Positive signed N in1..Int32Max is preserved ESI; R15D starts0 and increments once after each one-callback/one-Add body. Exact JGE exits at N; otherwise sole actual JMP returns to same loop entry. Nonvolatile counter/Reader/context and disjoint count/output stack stay stable under normal calls, so exactly N elements are read/appended without counter overflow.',condition='Initialized actual typed List<long> formatter context, matching header/count grammar and same original Reader, initially null output; normal typed allocation/constructor(capacity N), Add64 and callback ABI, coherent new zero-size list with sufficient capacity and disjoint storage. Same Reader R14 and qword output stack+32 reach selected child dispatcher; unchanged result R13 reaches typed Add. Null/zero variants execute no element callback; runtime/default/provider/storage/constructor effects conditional, child/helper grammar separately proved.')


def add64(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','ff411c','498bf0','4c8b4910','488bfa','48634118','488bd9','4d85c9');g.branch('74',False,1);g.take('413b4118');g.branch('73',False,1);g.take('8d4801','894b18','413b4118');g.branch('73',False,1);g.take('498954c120','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,countSlot=24,versionSlot=28,arraySlot=16,elementBits=64,arrayStride=8,incomingValueUnchanged=True,normalReturn=True,condition='Exact typed List<long> fields and ordinary qword argument, nonnull correctly typed items array, nonnegative size smaller than capacity without size overflow and stable disjoint storage. Growth not selected; version may wrap, runtime storage effects conditional.')


def formatter(regions,entry,o,advance):
    g=BytesPath(regions,entry);cur,rem=(bytes((o[n],)).hex()for n in('currentPtr','bufferLength'));g.take('48895c2408','57','4883ec20','837a'+rem+'08','498bf8','488bda');g.branch('0f8c',False);g.take('488b42'+cur,'488b00','ba08000000','488bcb','488907','488b5c2430','4883c420','5f')
    if g.relative('e9')!=advance:raise ValueError('modelViewLong.formatter-advance-tail')
    return dict(selectedBytes=g.seen,wireBytes=8,outputBytes=8,reader='same incoming RDX saved RBX',output='same incoming R8 saved RDI',advanceArgument=8,normalReturnViaAdvance=True,condition='Current closed UnmanagedFormatter<long> slot5, sufficient buffered disjoint Reader/output; complete owned qword copy and same Reader/EDX8 to independently proved Advance tail. Refill/default/runtime selection separate.')


def dispatch(regions,entry,o,s):
    g=BytesPath(regions,entry);cur,rem=(bytes((o[n],)).hex()for n in('currentPtr','bufferLength'));g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf9','498bd8','488bf2');g.call(s['prepare']);g.take('488b06','4c8b9090010000','4c8b8898010000')
    if g.relative('488d05')!=s['callback']:raise ValueError('modelViewLong.dispatch-selected-callback')
    g.take('4c3bd0');g.branch('0f85',False);g.take('837b'+rem+'08');g.branch('0f8c',False);g.take('488b43'+cur,'488b00','ba08000000','488bcb','488907');g.call(s['advance']);g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,slot=5,callback=s['callback'],wireBytes=8,outputBytes=8,sameReader=True,sameOutput=True,normalReturn=True,condition='Prepared current receiver has selected slot5 pointer equal to freshly proved closed UnmanagedFormatter<long> program; sufficient buffered disjoint Reader/output and compatible normal preparation/Advance ABI. Refill/other callbacks/live provider/default selection unproved.')
