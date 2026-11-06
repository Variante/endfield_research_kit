"""Exact shared Optional-reference hidden16 read and compatible provider paths.

These byte programs own no nominal layout or wire grammar. Their caller must
independently bind the actual closed request, registered wrapper/interface,
selected canonical comparison, GetValue transfer, child parser and helpers.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('interactiveManagedOptionalProgram.'+check)


def inline_setter(regions,entry,*,field,disabled):
    """Own the complete disabled-collector path of a direct holder setter."""
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-own-field-and-collector',type(field)is int and 16<=field<2**31
        and type(disabled)is int and disabled>0)
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488b5910','4885db');g.branch('74',False,1)
    flag=g.relative('833d')+1;need('same-actual-disabled-collector',flag==disabled)
    g.take('00','0f1002',_displacement('0f1143',field))
    edge=g.at;fall=edge+2
    lane=bytes.fromhex(_displacement('4c8d43',field+8))
    need('own-unselected-reference-lane-address',all(g.bytes.get(fall+i)==b for i,b in enumerate(lane)))
    g.branch('74',True,1);g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,storedBytes=16,managedBytes=16,referenceLaneOffsets=[8],
        barrierReferenceLaneOffset=8,holderOffset=16,wholeInputBitsStoredUnchanged=True,
        disabledCollectorRequired=True,inlineDisabledCollectorFlagVa=flag,
        unselectedBarrierLaneAddressInstruction=[fall,lane.hex().upper()],activeCollectorAdmitted=False,
        entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,normalReturnViaBarrier=False)


def provider(regions,entry):
    g=BytesPath(regions,entry);s={};classes=[]
    def call(role):
        target=g.relative('e8');need('same-helper.'+role,role not in s or s[role]==target);s[role]=target
    def ready():g.take('83b9e000000000');g.branch('0f84',False)
    def cls():classes.append(dict(instructionVa=g.at,cellVa=g.relative('488b0d')))
    g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('0f84',False)
    cls();g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('4885db');g.branch('0f84',False);ready();g.take('488bcb');call('typeHandle')
    g.take('488bd8');cls();ready();flag=g.relative('803d')+1;g.take('00');g.branch('0f84',False)
    cls();ready();g.take('488bcb');call('backend')
    g.take('488b4f38','ba01000000','488bd8');call('indexed')
    g.take('4885db');g.branch('74',False,1)
    g.take('488b0b','488bd0');call('assignable');g.take('84c0');g.branch('74',False,1)
    g.take('488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,helperTargets=s,classUsages=classes,providerReadyFlagVa=flag,
        requestedTypeContextSlot=0,resultFormatterTypeContextSlot=1,sameRequestedTypePassedToBackend=True,
        sameNonNullCompatibleBackendReturned=True,entryRspRestored=True,normalReturn=True,
        resultClassPredicateOutcomeObserved=False,wireGrammarAdmitted=False)


def read(regions,entry,*,ordinal,ff=False,create=True,wrapper_null=False):
    need('finite-explicit-path',type(ordinal)is int and 0<=ordinal<=16
        and all(type(v)is bool for v in(ff,create,wrapper_null)))
    g=BytesPath(regions,entry);s={};classes=[];flags=[];interface_calls=[]
    def call(role):
        target=g.relative('e8');need('same-helper.'+role,role not in s or s[role]==target);s[role]=target
    def flag():
        flags.append(g.relative('803d')+1);g.take('00');g.branch('75',True,1)
    def cls():classes.append(dict(instructionVa=g.at,cellVa=g.relative('488b0d')))
    g.take('4053','56','57','4883ec30','4983783800','498bd8','488bfa','488bf1');g.branch('75',True,1)
    g.take('0f57c0','0f1106');cls();g.take('83b9e000000000');g.branch('75',True,1)
    g.take('488b4b38','48896c2458','4c89742468','488b09');call('provider')
    g.take('488bd8','4885c0');g.branch('0f84',False);g.take('488b08');call('prepare')
    g.take('488b0b','488b8190010000','488ba998010000');canonical=g.relative('488d0d')
    g.take('483bc1');g.branch('0f85',False);flag()
    g.take('837f3001','c644245000');g.branch('7d',True,1)
    g.take('488b4750','8038ff');g.branch('75',not ff,1)
    if ff:
        g.take('488d542450','488bcf');call('header');g.take('0f57c0','0f1106');g.jump('e9')
    else:
        g.take('488b4520');cls();g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('75',True,1)
        g.take('4885db');g.branch('0f84',False)
        g.take('83b9e000000000');g.branch('75',True,1)
        g.take('488bcb');call('typeHandle');g.take('4885c0');g.branch('0f84',False)
        g.take('b944000000','488bd0');call('typeFlags');g.take('33db','a980000000');g.branch('76',create,1)
        if create:
            g.take('488b4520','488b88c0000000','488b4958');call('activate')
        else:g.take('8bc3');g.jump('eb',1)
        ready=g.relative('381d');flags.append(ready)
        g.take('488b5520','4889442450','4c8b82c0000000','498b6818');g.branch('75',True,1)
        cls();g.take('3999e0000000');g.branch('75',True,1)
        g.take('488b4d20');call('context');g.take('488b88c0000000','488b4920');call('wrapperProvider')
        g.take('4885c0');g.branch('0f84',False)
        g.take('b905000000','4c8d4c2450','4c8bc7','488bd0');call('wrapperInvoke')
        g.take('4c8b742450','4d85f6');g.branch('0f84',wrapper_null)
        if wrapper_null:g.take('0f57c0','0f1106');g.jump('e9')
        else:
            g.take('488b4d20');call('context');g.take('ba08000000','488b88c0000000');call('indexed')
            g.take('498b2e','488bf8','488bcd');call('prepare')
            g.take('0fb79530010000','663bda');g.branch('73',False,1)
            g.take('488b8db0000000','6666660f1f840000000000');loop=g.at
            for i in range(ordinal+1):
                g.take('0fb7c3','4803c0','48393cc1');g.branch('74',i==ordinal,1)
                if i<ordinal:
                    g.take('66ffc3','663bda');g.branch('72',True,1);need('same-interface-loop',g.at==loop)
            g.take('488b85b0000000','0fb7cb','4803c9','486344c808','4883c014','48c1e004','4803c5');g.jump('eb',1)
            g.take('4c8b08','488d4c2420','4c8b4008','498bd6');interface_calls.append(g.at);g.take('41ffd1')
            disabled=g.relative('833d')+1;g.take('00','0f1000','0f1106');g.branch('74',True,1)
    g.take('4c8b742468','488bc6','488b6c2458','4883c430','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,helperTargets=s,classUsages=classes,readyFlagVas=flags,
        comparedCanonicalTargetVa=canonical,ff=ff,createWrapper=None if ff else create,
        wrapperNull=None if ff else wrapper_null,managedBytes=16,hiddenGetterLocal=[32,16],
        initializedWrapperLocal=[80,8],interfaceOrdinal=ordinal,interfaceGetValueSlot=0,
        interfaceGetValueCallSites=interface_calls,completeOutputBitsCopied=not(ff or wrapper_null),
        completeOutputDefaultZeroed=ff or wrapper_null,
        disabledCollectorFlagVa=None if ff or wrapper_null else disabled,
        sameHiddenOutputReturnedInRax=True,entryRspRestored=True,allNonvolatilesRestored=True,
        normalReturn=True,wireGrammarAdmitted=False,providerSelectionObserved=False)
