"""Selected coherent current ModelView holders and exact owning stores."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def coherent_getter(regions,entry,*,base_slot,cache_slot,mode):
    if not(16<=base_slot<cache_slot<128)or mode not in('rbx','rdi'):raise ValueError('modelViewGetter.scope')
    b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
    if mode=='rdi':g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bf9');g.branch('75',True,1);g.take('48837f'+c+'00');g.branch('74',False,1);g.take('488b47'+b,'483947'+c);g.branch('74',True,1);g.take('488b47'+c,'488b5c2430','4883c420','5f','c3')
    else:
        g.take('4053','4883ec20');g.relative('803d');g.take('00','488bd9');g.branch('74',False,1);g.take('48837b'+c+'00');g.branch('74',False,1)if g.bytes.get(g.at)==0x74 else g.branch('0f84',False);g.take('488b43'+b,'483943'+c);g.branch('75',False,1)if g.bytes.get(g.at)==0x75 else g.branch('0f85',False);g.take('488b43'+c,'4883c420','5b','c3')
    return dict(selectedBytes=g.seen,baseSlot=base_slot,cacheSlot=cache_slot,normalReturn=True,output='Same nonnull full reference in coherent base/cache slots is returned unchanged RAX',condition='Initialized current wrapper with coherent nonnull compatible typed base/cache holders and stable storage. Refresh/cast/constructor/collector effects and live provider selection remain conditional.')


def base_setter(regions,entry,*,holder,field,kind):
    if not(16<=holder<128 and 16<=field<128)or kind not in('bool','dword','single','qword'):raise ValueError('modelViewBaseSetter.scope')
    g=BytesPath(regions,entry);h=bytes((holder,)).hex();f=bytes((field,)).hex();g.take('4883ec28','488b41'+h,'4885c0');positive=g.bytes.get(g.at)==0x75
    if positive:g.branch('75',True,1)
    else:g.branch('74',False,1)
    g.take(('8850'if kind=='bool'else'8950'if kind=='dword'else'f30f1148'if kind=='single'else'488950')+f,'4883c428','c3')
    return dict(selectedBytes=g.seen,holder=holder,field=field,kind=kind,unchangedArgumentStored=True,normalReturn=True,condition='Current declared ordinary setter ABI and typed holder/field; stable compatible nonnull original. Null/error and helper/runtime effects separate.')


def qword_setter(regions,entry,*,getter,field):
    if not 16<=field<128:raise ValueError('modelViewQwordSetter.scope')
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0');g.branch('74',False,1);g.take('488958'+bytes((field,)).hex(),'4883c420','5b','c3')
    return dict(selectedBytes=g.seen,field=field,storedBytes=8,unchangedArgumentStored=True,normalReturn=True,condition='Current typed getter normally returns coherent nonnull original; incoming scalar64 preserved RBX across its ordinary ABI. Null/helper/storage effects separate.')


def vector_setter(regions,entry,*,getter,field,copy_mode):
    if not 16<=field<116 or copy_mode not in('rax','rcx'):raise ValueError('modelViewVectorSetter.scope')
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter)
    if copy_mode=='rcx':g.take('488bc8')
    g.take('4885c0');positive=g.bytes.get(g.at)==0x75;g.branch('75'if positive else'74',positive,1);f=bytes((field,)).hex();z=bytes((field+8,)).hex();g.take('f20f1003')
    if copy_mode=='rcx':g.take('f20f1140'+f,'8b4308','8941'+z)
    else:g.take('8b4b08','f20f1140'+f,'8948'+z)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,field=field,storedBytes=12,completeValueCopy=True,normalReturn=True,condition='Current ordinary Vector3 ABI passes stable disjoint twelve-byte input through RDX/RBX, actual typed getter returns coherent nonnull original; normal helper ABI preserves RBX. Null/error/refresh/storage effects remain conditional.')
