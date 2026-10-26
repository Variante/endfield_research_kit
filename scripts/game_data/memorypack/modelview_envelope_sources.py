"""Selected current Envelope32 adapter paths; typed runtime selection is conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def main(regions,entry,s,*,null=False,dispatch=False):
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2410','48896c2418','4889742420','66894c2408','57','4883ec20','488b0a','498be9','498bf0','488bda');g.call(s['prepare']);g.take('488b03','4c8b9090010000','488bb898010000')
        if g.relative('488d05')!=s['main']:raise ValueError('modelViewEnvelope.matched-main')
        g.take('4c3bd0');g.branch('0f85',False)
    else:g.take('48896c2418','4889742420','57','4883ec20')
    g.relative('803d');g.take('00')
    if not dispatch:g.take('498bf9','498be8','488bf2')
    g.branch('0f84',False);g.take('488bce','c64424'+('30'if dispatch else'38')+'00');g.call(s['peek']);g.take('84c0');g.branch('0f85',null)
    if null:g.take('488d5424'+('30'if dispatch else'38'),'488bce');g.call(s['header']);g.take('0f57c0','0f114500','0f114510');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');type_cell=g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeHandle']);
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1);g.take('b944000000','488bd0');g.call(s['typeFlags']);g.take('a980000000');g.branch('77',False,1);g.take('488b4720','488b88c0000000','488b4958');g.call(s['factory']);g.take('488b4f20','4c8bc0','488bd5','4c8b89c0000000','488bce','4d8b4918');g.call(s['notNull'])
    if dispatch:g.take('488b5c2438')
    g.take('488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,null=null,dispatch=dispatch,normalReturn=True,outputBytes=32,reader='incoming RDX preserved RSI',output='incoming R8 preserved RBP; same pointer to child NotNull or exact zero32',condition='Initialized coherent current Envelope32/object adapter context and ready Type class; buffered disjoint Reader/output, same Peek/header semantics, normal TypeHandle/nonabstract flags/factory/helper returns with Win64 preservation. Factory returns exact typed wrapper reference; runtime/default selection, allocation/storage effects conditional. Child wire/conversion/provider separately proved.')


def not_null(regions,entry,s,*,wrapper_null=False):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec40');g.relative('803d');g.take('00','498bf9','488bf2','488bd9');g.branch('0f84',False);cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b4920');g.call(s['hotProvider']);g.take('4885c0');g.branch('0f84',False);g.take('b905000000','4c8d4c2460','4c8bc3','488bd0');g.call(s['wrapperDispatch']);g.take('488b5c2460','4885db');g.branch('0f84',wrapper_null)
    if wrapper_null:g.take('0f57c0','0f1106','0f114610');g.jump('e9')
    else:
        g.take('488b4f20');g.call(s['context']);g.take('ba08000000','488b88c0000000');g.call(s['indexed']);g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion']);g.take('488bce','0f1000','0f104810','0f1106','0f114e10');g.call(s['barrier'])
    g.take('488b5c2450','488b742458','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,wrapperNull=wrapper_null,providerClassCell=cell,normalReturn=True,outputBytes=32,sameReaderAndOutput=True,condition='Initialized matching Envelope32/Wrapper inflated context, same ordinary slot5 callback Reader and wrapper-ref temporary, compatible provider success and noninterfering Win64 helpers, disabled collector. Positive conversion uses actual current helper (no incoming RDX selector inference) with hidden32 result; complete getter/output transfer and typed context separately proved; live/default/runtime/storage effects conditional.')


def conversion(regions,entry,prepare,*,ordinal):
    if type(ordinal)is not int or not 0<=ordinal<=12:raise ValueError('modelViewEnvelope.interface-ordinal')
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','48897c2418','4156','4883ec40','498b39','488bf1','488bcf','4d8bf1','498bd8');g.call(prepare);g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
    for i in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==ordinal,1)
        if i<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7','4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1','488b5c2450','488b7c2460','0f1000','0f104810','488bc6','0f1106','0f114e10','488b742458','4883c440','415e','c3')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,selector=0,selectorInlined=True,outputBytes=32,sameWrapper=True,normalReturn=True,condition='Current exact inflated interface and matching getter at its actual interface offset, ready compatible wrapper class, stable disjoint hidden32 stack/output; prepare and getter normal Win64 ABI. Incoming RDX selector is unused by this constant-zero-slot program. GetValue typed hidden32 and child field/source joins independently checked; live/runtime/default/interface selection remains conditional.')


def typed_provider(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1);typeClass=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('33d2','488bcb');g.call(s['typeHandle']);providerClass=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1);g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed']);g.take('4885db');g.branch('0f84',False);g.take('488b0b','488bd0');g.call(s['assignable']);g.take('84c0');g.branch('0f84',False);g.take('488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassCell=typeClass,providerClassCell=providerClass,methodContext='Incoming MethodInfo savedRDI, own slot0 T to TypeFromHandle and own slot1 MemoryPackFormatter<T> to indexed expected class',output='Same nonnull backend result savedRBX, actual class[RBX] RCX and indexed expected class RDX to current assignable predicate, true branch returns unchanged fullref8 RBX through RAX with full restored frame',normalReturn=True,condition='Initialized own coherent method context and Type/provider classes, successful selected Type/backend lookup, compatible nonnull formatter and normal helpers preserving ABI. Runtime cache population/inflation/default selection and allocation/storage effects remain conditional; no reader/wire consumption in this helper.')
