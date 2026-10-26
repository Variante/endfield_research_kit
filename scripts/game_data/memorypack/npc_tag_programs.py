"""Selected managed4 GameplayTag adapter programs; runtime sharing stays conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def peek(regions, entry, offsets):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','8379'+bytes((offsets['bufferLength'],1)).hex(),'488bd9');g.branch('0f8c',False)
    g.take('488b43'+bytes((offsets['currentPtr'],)).hex(),'8038ff','0f94c0','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,comparesTo255=True,consumedBytes=0)


def read_null(regions,entry,s,*,null=False):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','c644243000');g.call(s['peek']);g.take('84c0');g.branch('0f85',null)
    if null:
        g.take('488d542430','488bcb');g.call(s['header']);g.take('b001');g.jump('e9')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,null=null,consumedBytes=int(null),normalReturn=True)


def main(regions,entry,s,*,null=False,create=True,dispatch=False):
    g=BytesPath(regions,entry)
    if dispatch:
        g.take('48895c2408','4889742410','48897c2418','4156','4883ec20','488b0a','4d8bf1','498bf0','488bda');g.call(s['prepare'])
        g.take('488b3b')
        if g.relative('488d0d')!=s['main']:raise ValueError('npcTag4.dispatch-exact-adapter')
        g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
    else:
        g.take('4889742410','48897c2418','4156','4883ec20')
    flag=g.relative('803d');g.take('00')
    if not dispatch:g.take('498bf9','4d8bf0','488bf2')
    g.branch('0f84',False)
    g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',null)
    factory_cell=None
    if null:
        g.take('33c0','418906');g.jump('e9')
    else:
        if not dispatch:g.take('48895c2430')
        g.take('488b4720');factory_cell=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
        g.take('33d2','488bcb');g.call(s['typeFromHandle'])
        if not dispatch:g.take('488b5c2430')
        g.take('4885c0');g.branch('74',False,1)
        g.take('33d2','488bc8');g.call(s['isValueType']);g.take('84c0');g.branch('75',not create,1)
        if create:
            g.take('488b4720','488b88c0000000','488b4958');g.call(s['factory'])
        else:g.take('33c0');g.jump('eb',1)
        g.take('488b4f20','4c8bc0','498bd6','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
    if dispatch:g.take('488b5c2430')
    g.take('488b742438','488b7c2440','4883c420','415e','c3')
    return dict(selectedBytes=g.seen,null=null,create=create,dispatch=dispatch,initializedFlagVA=flag,
                factoryTypeClassCellVA=factory_cell,outputBytes=4,sameReaderAndOutput=True,
                nullOutputsDefaultZero32=null,normalReturn=True,wholeOwnerAdmitted=False,
                condition='Ready matching initialized method contexts and classes, exact selected adapter slot5 for dispatch, buffered disjoint Reader/frame/output, normal reflection/factory and NonNull ABI. Runtime sharing/provider selection and child effects are separate.')


def nonnull(regions,entry,s,*,wrapper_null=False):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec20');flag=g.relative('803d');g.take('00','498bf9','488bf2','488bd9');g.branch('0f84',False)
    provider_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b4920');g.call(s['provider'])
    g.take('4885c0');g.branch('74',False,1)
    g.take('b905000000','4c8d4c2440','4c8bc3','488bd0');g.call(s['dispatch'])
    g.take('488b5c2440','4885db');g.branch('74',wrapper_null,1)
    if wrapper_null:g.take('33c0');g.jump('eb',1)
    else:
        g.take('488b4f20');g.call(s['context']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('488bd0','33c9','4c8bc3');g.call(s['conversion'])
    g.take('488b5c2430','8906','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlagVA=flag,providerClassCellVA=provider_class,wrapperNull=wrapper_null,
                originalOutput='incoming RDX in RSI',wrapperTemporary='incoming R8 saved at entry RSP+24; same local supplied at current RSP+64',
                reader='incoming RCX in RBX',wrapperFormatterSlot=5,conversionContextSlot=8,providerContextSlot=4,
                preservesCompleteResultBits=32,nullWrapperDefaultZero32=wrapper_null,normalReturn=True,wholeOwnerAdmitted=False,
                condition='Initialized matching contexts, current wrapper formatter returned normally, matching interface conversion and child programs; runtime receiver/provider/cache/sharing and null failure remain separate.')


def conversion(regions,entry,prepare,*,ordinal):
    if type(ordinal)is not int or not 0<=ordinal<=8:raise ValueError('npcTag4.interface-ordinal')
    g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b38','498bf0','0fb7e9','488bda','488bcf');g.call(prepare)
    g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
    for n in range(ordinal+1):
        g.take('0fb7c8','4803c9','48391cca');g.branch('74',n==ordinal,1)
        if n<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
    g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7','4c8b00','488bce','488b5008','488b5c2430','488b6c2438','488b742440','4883c420','5f','49ffe0')
    return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,interfaceMethodSelector=0,tailReceiver='unchanged incoming R8 wrapper in RSI',
                tailMethodInfo='same selected interface slot',tailTarget='same selected interface slot method pointer',preservesResultBits=32,
                runtimeTargetSelectionProved=False,wholeOwnerAdmitted=False)

"""Current selected new GameplayTag4 list paths; existing/growing lists stay refused."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def tag_list(regions,entry,o,s,*,count):
    if type(count)is not int or not -1<=count<=2:raise ValueError('npcTagList.selected-count')
    g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((o[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('48895c2420','55','56','57','4155','4156','4883ec20','4533ed','498be9','837a'+rem+'04','4d8bf0','488bfa','44896c2458');g.branch('0f8c',False)
    g.take('488b47'+cur,'8b30','8b5f'+rem,'83c3fc');g.branch('0f88',False)
    g.take('488347'+cur+'04','8347'+adv+'04','8347'+used+'04','895f'+rem,'486347'+used,'488b4f'+total,'482bc8','4863c6','483bc8');g.branch('0f8c',False)
    g.take('83feff');g.branch('0f84',count==-1)
    provider_class=None;callbacks=[]
    if count==-1:
        g.take('498bce','4d892e');g.call(s['barrier'])
    else:
        g.take('4c89642450','4c897c2460','4d392e');g.branch('0f85',False)
        g.take('488b4d20','33d2','488b89c0000000');g.call(s['indexed'])
        g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
        g.take('488b4d20','488b91c0000000','488b4a08','4c396920');g.branch('0f84',False)
        g.take('85f6');g.branch('0f88',False)
        g.take('488b4520','488b88c0000000','4c8b7908','498b4720','488b88c0000000');g.branch('0f85',count>0)
        if count:
            g.take('ba01000000');g.call(s['indexed']);g.take('488bd6','488bc8');g.call(s['arrayAllocate']);g.jump('e9')
        else:
            g.take('33d2');g.call(s['indexed']);g.take('4439a8e0000000');g.branch('0f84',False)
            g.take('498b4f20','33d2','488b89c0000000');g.call(s['indexed']);g.take('488b88b8000000','488b01')
        g.take('488d4b10','48894310');g.call(s['barrier'])
        g.take('498bce','49891e');g.call(s['barrier'])
        provider_class=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False)
        g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('4c8bf8','458be5','85f6');g.branch('7f',count>0,1)
        for index in range(count):
            g.take('44896c2458','4d85ff');g.branch('74',False,1)
            g.take('4c8d4c2458','4c8bc7','498bd7');callbacks.append(g.at);g.call(s['dispatch'])
            g.take('4d8b2e','8b5c2458','4d85ed');g.branch('74',False,1)
            g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
            g.take('488b4520','8bd3','498bcd','4c8b80c0000000','4d8b4030');g.call(s['add'])
            g.take('41ffc4','41bd00000000','443be6');g.branch('0f8d',index+1==count)
            if index+1<count:g.jump('eb',1)
        g.take('4c8b642450','4c8b7c2460')
    g.take('488b5c2468','4883c420','415e','415d','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,count=count,wireCountBytes=4,elementOutputBytes=4,elementSourceBytes=None,
                sourceReader='incoming RDX in RDI',listOutput='incoming R8 in R14',elementOutput='current RSP+88',
                outputInitialValue=0,newListOnly=count!=-1,providerContextSlot=3,addContextSlot=6,
                providerClassCellVA=provider_class,elementCallbackSites=callbacks,normalReturn=True,
                wholeOwnerAdmitted=False,childFramingProved=False,
                condition='Initialized coherent typed List<GameplayTag> contexts; valid buffered Reader and initially null list output, count -1/0/1/2, normal fresh zero-count List allocation and matching typed array capacity>=count, current selected GameplayTag4 dispatcher and non-growing Add helper. Existing lists, growth, child framing and runtime provider contents remain separate.')


def add_no_growth(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','ff411c','8bda','488b5110','498bf0','48634118','488bf9','4885d2');g.branch('74',False,1)
    g.take('3b4218');g.branch('73',False,1)
    g.take('8d4801','894f18','3b4218');g.branch('73',False,1)
    g.take('895c8220','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,storedBits=32,arrayStride=4,arrayDataOffset=32,itemsSlot=16,countSlot=24,versionSlot=28,
                sourceValue='unchanged incoming EDX through EBX',normalReturn=True,wholeOwnerAdmitted=False,
                condition='Coherent valid nonnull List and primitive4 array with nonnegative count<capacity and no counter overflow; current typed caller/field layout remains independent. Growth excluded.')

"""Selected initialized GameplayTag wrapper source, independent of adapter selection."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def wrapper(regions,entry,s,*,null=False,created=False):
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20');flag=g.relative('803d');g.take('00','488bda','488bf9');g.branch('74',False,1)
    g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
    allocation=None
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('48833b00');g.branch('0f84',created)
        if created:
            allocation=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','894810','488bcb','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take('807c243001');g.branch('0f85',False)
        g.take('488b1b','488bcf');g.call(s['integer']);g.take('4885db');g.branch('74',False,1);g.take('894310')
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlagVA=flag,allocationClassCellVA=allocation,null=null,created=created,
                memberCount=1,serializedMember='tagId',storedBytes=4,nullWrapper=null,reader='incoming RCX preserved RDI',
                output='incoming RDX preserved RBX',wholeOwnerAdmitted=False,
                condition='Ready current type initialization; matching object-header and Int32 source, normal typed zeroed wrapper allocation and barrier. Adapter/provider selection and owning NPC are separate.')


def capacity_constructor(regions,entry,s,*,positive=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
 g.take('498b4820','488b89c0000000');g.branch('75',positive,1)
 if positive:
  g.take('ba01000000');g.call(s['indexed']);g.take('488bd3','488bc8');g.call(s['arrayAllocate']);g.jump('eb',1)
 else:
  g.take('33d2');g.call(s['indexed']);g.take('83b8e000000000');g.branch('74',False,1)
  g.take('488b4f20','33d2','488b89c0000000');g.call(s['indexed']);g.take('488b88b8000000','488b01')
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('NPC tag constructor collector tail')
 return dict(selectedBytes=g.seen,positiveCapacity=positive,itemsSlot=16,capacity='unchanged positive incoming EDX through EBX'if positive else 0,zeroSizeRequiresFreshAllocation=True,openGenericOffsetsUsed=False,condition='Current closed List<Tag> constructor and reciprocal typed contexts; normal matching typed zeroed allocation, empty-array or capacity array allocation and collector effects. Open generic field-offset placeholders are not a concrete layout.')


def clear(regions,entry):
 g=BytesPath(regions,entry);g.take('ff411c','c7411800000000','c3')
 return dict(selectedBytes=g.seen,countSlot=24,versionSlot=28,normalReturn=True,openGenericOffsetsUsed=False)
