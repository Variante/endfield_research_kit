"""Successful initialized Type-cache formatter transfer; cold/live selections are separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def cache_hit(g,symbols,*,inline):
 # Both paths start with RBX equal to the same nonnull Il2CppType pointer.
 g.take('b201','488bcb');g.call(symbols['classFromType'])
 g.take('4c8d6020' if inline else '4c8d7820');cache=g.relative('488b1d');g.take('488b8b80000000');enter=g.relative('ff15');g.take('90','488b4340','483b4338');g.branch('0f84',False)
 g.take(*(['4533ed','4c8b7348','49ffce','498bcc'] if inline else ['4533e4','488b6b48','48ffcd','498bcf']));g.call(symbols['hash'])
 g.take('488bf8','488b7368','448b7b50' if inline else '448b7350','4923fe' if inline else '4823fd','488d0c7f','443b3cce' if inline else '443b34ce');g.branch('75',True,1)
 g.take('48837b3800');g.branch('0f87',False);g.take('488d047f','833cc600');g.branch('0f85' if inline else '75',False,4 if inline else 1)
 g.take('488b54c608','498bcc' if inline else '498bcf');g.call(symbols['compare']);g.take('85c0');g.branch('0f85' if inline else '75',False,4 if inline else 1)
 g.take('4883ffff');g.branch('0f84' if inline else '74',False,4 if inline else 1)
 g.take('488d0c7f','488d14ce','488b4348','488d0c40','488b4368','488d0cc8','483bd1');g.branch('0f84' if inline else '74',False,4 if inline else 1)
 g.take('488b4a10','488b4370','4c8b34c8' if inline else '488b2cc8','488b8b80000000');leave=g.relative('ff15');g.take('90')
 return dict(cacheGlobalCell=cache,lockImportCell=enter,unlockImportCell=leave,keyFromResolvedClassOffset=32,entryStride=24,entryKeyOffset=8,entryValueIndexOffset=16,valueTableOffset=112,lookup='same first hash/mask probe, non-sentinel entry, no special-key branch, key comparison zero and valid value index',returnedObjectRegister='r14' if inline else 'rbp')


def type_from_handle(regions,entry,symbols):
 g=BytesPath(regions,entry);g.take('48895c2410','55','56','57','4154','4155','4156','4157','4883ec60','488bd9','4885c9');g.branch('0f84',False);type_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 proof=cache_hit(g,symbols,inline=False);g.take('488bc5','488b9c24a8000000','4883c460','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,typeClassCell=type_class,cache=proof,inputType='incoming RCX',result='same cached object in RAX',normalReturn=True)


def provider(regions,entry,symbols):
 g=BytesPath(regions,entry);g.take('48895c2418','55','56','57','4154','4155','4156','4157','4883ec60','488be9','4883793800');g.branch('0f84',False);g.take('488b5d38','488b1b');type_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('0f84',False)
 proof=cache_hit(g,symbols,inline=True);provider_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('803d');flag=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00');g.branch('0f84',False)
 if g.relative('488b0d')!=provider_class:raise ValueError('providerBridge.same-provider-class')
 g.take('83b9e000000000');g.branch('0f84',False);g.take('498bce');g.call(symbols['backend']);g.take('488bd8','ba01000000','488b4d38');g.call(symbols['indexedType']);g.take('4885db');g.branch('74',False,1);g.take('488bd0','488b0b');g.call(symbols['assignable']);g.take('84c0');g.branch('74',False,1)
 g.take('488bc3','488b9c24b0000000','4883c460','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,typeClassCell=type_class,providerClassCell=provider_class,providerInitFlag=flag,cache=proof,typeInput='incoming GetFormatter MethodInfo context slot zero',expectedResultType='same method context slot one',result='unchanged nonnull backend result after compatible-class check',normalReturn=True)


def validate_provider_success(regions,entries,symbols,hot):
 proofs={}
 g=BytesPath(regions['ready'],entries['ready']);g.take('4883ec28','83b9e000000000');g.branch('74',False,1);g.take('4883c428','c3');proofs['ready']=g.seen
 g=BytesPath(regions['indexed'],entries['indexed']);g.take('488bc1','4863ca','488b0cc8')
 if g.relative('e9')!=entries['entry']:raise ValueError('provider.indexed-context-tail')
 proofs['indexed']=g.seen
 g=BytesPath(regions['providerByType'],entries['providerByType']);g.take('4053','4883ec20','803d');flag=g.at+5+int.from_bytes(g.read(4),'little',signed=True);g.take('00','488bd9');g.branch('74',False,1);cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1);g.take('488bcb','4883c420','5b')
 if g.relative('e9')!=symbols['backend'] or flag!=hot['providerInitFlag'] or cell!=hot['providerClassCell']:raise ValueError('provider.shared-backend')
 proofs['providerByType']=g.seen
 g=BytesPath(regions['castObject'],entries['castObject']);g.take('4053','4883ec20','488bd9','4885c9');g.branch('74',False,1);g.take('488b09');g.call(symbols['assignable']);g.take('33c9','84c0','480f44d9','488bc3','4883c420','5b','c3');proofs['castObject']=g.seen
 g=BytesPath(regions['canonical'],entries['canonical']);g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1);g.take('488b5f38');typecell=g.relative('488b0d');g.take('488b1b');g.call(entries['ready']);g.take('33d2','488bcb');g.call(entries['typeFromHandle']);providercell=g.relative('488b0d');g.take('488bd8');g.call(entries['ready']);g.take('488bcb');g.call(entries['providerByType']);g.take('488b4f38','488bd8','488b4908');g.call(entries['entry']);g.take('488bd0','488bcb');g.call(entries['castObject']);g.take('4885c0');g.branch('0f85',True);g.take('488b5c2430','488b742438','4883c420','5f','c3')
 if typecell!=hot['typeClassCell'] or providercell!=hot['providerClassCell'] or symbols['indexedType']!=entries['indexed']:raise ValueError('provider.same-context-and-classes')
 proofs['canonical']=g.seen
 return dict(selectedBytes=proofs,contextTransfer='actual context[index=1] tail-calls the identical entry resolver called by canonical with context[1]',typeTransfer='identical type-context slot zero; proved equal successful initialized cache lookup',providerTransfer='identical provider class, initialization flag, backend and Type argument',resultTransfer='identical expected-class resolver and assignability check; unchanged compatible nonnull backend result',condition='Initialized coherent matching method contexts, first-probe RuntimeType cache hit, normal helper ABI and nonnull compatible formatter; initialization, cache misses/collisions, exceptions and runtime provider selection are not admitted.')
