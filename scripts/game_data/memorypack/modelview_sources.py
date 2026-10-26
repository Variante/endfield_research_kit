"""Selected ModelView value/source transfers; runtime selection remains conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def audio_id_source(regions,entry,offsets,*,registered=False,advance=None):
    g=BytesPath(regions,entry);b=lambda n:bytes((n,)).hex()
    cur,rem,adv,used=(b(offsets[n])for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408')
    if not registered:g.take('4889742410')
    g.take('57','4883ec20','8379'+rem+'04','488bf9')
    if registered:
        g.branch('7d',True,1);g.take('488b5f'+cur,'ba04000000','488bcf','8b1b');g.call(advance);g.take('8bc3','488b5c2430')
    else:
        g.branch('0f8c',False);g.take('488b5f'+cur,'8b1b','8b77'+rem,'83c6fc');g.branch('0f88',False)
        g.take('488347'+cur+'04','8347'+adv+'04','8347'+used+'04','8977'+rem,'488b742438','8bc3','488b5c2430')
    g.take('4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=4,normalReturn=True,reader='same entry RCX saved RDI',output='unchanged source DWORD in EBX returned EAX',cursor=dict(currentPtr=4,bufferLength=-4,advancedCount=4,consumed=4),condition='Initialized matched typed AudioId context, available signed buffer length >=4, valid disjoint Reader/storage and normal Win64 ABI. Registered path additionally requires the separately proved same Advance(4); refill/live formatter selection remain separate.')


def scalar_result(regions,entry,kind,receiver,setter):
    """Complete selected source-return→named-setter interval, without a call gap."""
    if receiver not in('rsi','rbx','rdi')or kind not in('bool','scalar32','enum','scalar64','float32','string','list','object'):raise ValueError('modelView.scalar-result-scope')
    g=BytesPath(regions,entry);g.take({'rsi':'4885f6','rbx':'4885db','rdi':'4885ff'}[receiver])
    short=g.bytes.get(g.at)==0x74;failure=g.relative('74',1)if short else g.relative('0f84')
    g.take('4533c0')
    if kind=='bool':g.take('8ad0'if g.bytes.get(g.at)==0x8a else'88c2'if g.bytes.get(g.at)==0x88 else'0fb6d0')
    elif kind in('scalar32','enum'):g.take('8bd0')
    elif kind=='float32':g.take('0f28c8')
    else:g.take('488bd0')
    g.take({'rsi':'488bce','rbx':'488bcb','rdi':'488bcf'}[receiver]);g.call(setter)
    return dict(selectedBytes=g.seen,end=g.at,nullTarget=failure,unchangedSourceResult=True,sameNamedSetter=True,condition='Nonnull current typed wrapper and compatible normal named setter preserving Win64 ABI; setter storage/own getter and child wire source are separately proved.')


def vector_result(regions,entry,*,direct,getter=None,setter=None,field=None,frame=False,receiver="rsi"):
    """Exact current hidden12→owned field or declared Vector3 setter transfer."""
    if receiver not in('rsi','rbx','rdi'):raise ValueError('modelView.vector-receiver')
    g=BytesPath(regions,entry);g.take({'rsi':'4885f6','rbx':'4885db','rdi':'4885ff'}[receiver]);first=g.relative('74',1)if g.bytes.get(g.at)==0x74 else g.relative('0f84')
    if direct:
        if type(field)is not int or not 0<=field<116:raise ValueError('modelView.vector-field')
        g.take('33d2','488bce'if receiver=='rsi'else'488bcb');g.call(getter);g.take('4885c0');second=g.relative('74',1)if g.bytes.get(g.at)==0x74 else g.relative('0f84')
        if first!=second:raise ValueError('modelView.vector-null-join')
        g.take('f20f10442420','8b4c2428','f20f1140'+bytes((field,)).hex(),'8948'+bytes((field+8,)).hex())
    else:
        g.take('f20f1000','488d55e0'if frame else'488d542420','8b4008','4533c0','488bce'if receiver=='rsi'else'488bcb','f20f1145e0'if frame else'f20f11442420','8945e8'if frame else'89442428');g.call(setter)
    return dict(selectedBytes=g.seen,end=g.at,nullTarget=first,wireBytes=12,completeValueCopy=True,condition='Separately proved hidden12 source returns same complete output pointer; stable disjoint stack, same saved Reader/typed wrapper and normal compatible actual getter/setter. Direct mode requires current typed original field ownership; runtime/cache/provider/storage effects remain conditional.')
