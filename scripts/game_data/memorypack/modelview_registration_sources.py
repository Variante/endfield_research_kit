"""Selected lazy generated key/delegate and concrete adapter registration paths."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def lazy_key(regions,entry,s):
    g=BytesPath(regions,entry);key=g.relative('488b05');g.take('48898424');original=g.read(4).hex();g.take('33d2','488b8c24',original);g.call(s['typeHandle']);g.take('48898424');resolved=g.read(4).hex();delegate=g.relative('488b0d');g.call(s['allocate']);g.take('48898424');obj=g.read(4).hex();g.take('488b8c24',obj);g.call(s['objectCheck']);g.take('4533c9');callback=g.relative('4c8b05');g.take('33d2','488b8c24',obj);g.call(s['delegateConstructor']);g.take('488b8c24');dictionary=g.read(4).hex();g.call(s['objectCheck']);setter=g.relative('4c8b0d');g.take('4c8b8424',obj,'488b9424',resolved,'488b8c24',dictionary);g.call(s['dictionaryAdd'])
    slots=[int.from_bytes(bytes.fromhex(q),'little')for q in(original,resolved,obj,dictionary)]
    if len(set(slots))!=4 or any(q<32 or q%8 for q in slots):raise ValueError('modelViewLazy.overlapping-stack')
    return dict(selectedBytes=g.seen,end=g.at,keyCell=key,delegateClassCell=delegate,callbackCell=callback,addContextCell=setter,slots=slots,keyAndCallbackTransferredTogether=True,condition='Initialized current metadata cells and ordinary normally returning allocation/check/Type/delegate/dictionary helpers with stable disjoint stack. Actual method and concrete generic contexts independently checked. Dictionary construction/storage/execution and runtime lazy/provider selection remain conditional.')


def lazy_init(regions,entry,s,*,mode='standard'):
    if mode not in('standard','array','inline'):raise ValueError('modelViewLazy.init-mode')
    g=BytesPath(regions,entry);inline=mode=='inline';extra=mode=='array'
    g.take('488bc4','53','57','4881ec88000000')if inline else g.take('48895c2408','57','4883ec20')
    g.relative('803d');g.take('00');g.branch('0f85'if inline else'75',True,4 if inline else 1);allocation=g.at;adapter=g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0')
    if inline or extra:g.branch('0f84',False)
    else:g.branch('75',True,1)
    constructor=g.at;ctor=g.relative('4c8b05'if inline else'488b15')
    if inline:g.take('498b4820','488b91c0000000','488b4a60','4883792000');g.branch('75',True,1)
    else:g.take('488bc8'if extra else'488bcf');g.call(s['constructor'])
    first=g.relative('488b0d');key_at=g.at;key=g.relative('488b1d')
    if inline:g.take('83b9e000000000');g.branch('75',True,1)
    else:g.call(s['classInit'])
    g.take('33d2','488bcb');g.call(s['typeHandle']);second=g.relative('488b0d');g.take('488bd8')
    if inline:g.take('83b9e000000000');g.branch('75',True,1)
    else:g.call(s['classInit'])
    g.take('4533c0','488bd3','488bcf');g.call(s['registerWrap']);list_sites=None
    if extra:
        a=g.at;g.relative('488b0d');g.call(s['arrayAllocate']);g.take('488bd8','4885c0');g.branch('74',False,1);c=g.at;g.relative('488b15');g.take('488bc8');g.call(s['arrayConstructor']);r=g.at;g.relative('488b15');g.take('488bcb');g.call(s['arrayRegister']);list_sites=dict(allocation=a,constructor=c,registration=r)
    if inline:g.take('b001','4881c488000000','5f','5b','c3')
    else:g.take('488b5c2430','b001','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,allocationInstruction=allocation,constructorInstruction=constructor,keyInstruction=key_at,adapterCell=adapter,constructorCell=ctor,keyCell=key,readyClassCells=[first,second],extraArraySites=list_sites,constructorContextInlined=inline,normalReturn=True,booleanResult=True,adapterAndKeyTransferredTogether=True,condition='Initialized callback and coherent typed usages; allocation returns concrete nonnull adapter and actual constructor/type/class helpers normally preserve Win64 nonvolatiles. Inlined variant selects ready matching base-constructor context. Same adapter RDI and resolved Type RBX reach RegisterWrap. Construction/storage/helper effects, lazy execution/default/provider selection conditional.')
