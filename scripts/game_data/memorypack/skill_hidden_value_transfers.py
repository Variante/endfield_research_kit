"""Selected hidden-value dispatcher shapes with independently supplied types.

These byte programs prove argument, interface and result-buffer transfers only.
Their caller must prove the exact closed nominal value, canonical adapter
registration, actual compared pointer, owned wrapper/interface/GetValue ABI and
the child wire source separately. Managed16 never selects a wire grammar.
Initialized matching contexts/callbacks, normal compatible helpers, disjoint
buffered storage and the selected disabled collector path are conditions.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.memorypack.pooled_string_list_sources import flag

LABEL='skillHiddenValueTransfers'


def inline16_program(regions,entry,s,offsets,*,ordinal,null=False,create=True,wrapper_null=False):
    """Exact fixed-slot5 inline header/class/interface/copy16 source shape."""
    scalar.need(LABEL,'literal-path-switches',True,all(type(x)is bool for x in(null,create,wrapper_null)))
    scalar.need(LABEL,'independent-null-paths',False,null and wrapper_null)
    scalar.need(LABEL,'bounded-owned-interface-ordinal',True,type(ordinal)is int and 0<=ordinal<=16)
    cur,rem=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength'))
    g=BytesPath(regions,entry)
    g.take('66894c2408','53','55','56','57','4883ec38','488b0a','498be9','498bf8','488bda')
    g.call(s['prepare']);g.take('488b03','4c8b9090010000','488bb098010000')
    scalar.need(LABEL,'independent-canonical-adapter-pointer',s['adapter'],g.relative('488d05'))
    g.take('4c3bd0');g.branch('0f85',False)
    metadata=flag(g);g.branch('75',True,1)
    g.take('837f'+rem+'01','c644246000');g.branch('7d',True,1)
    g.take('488b47'+cur,'8038ff');g.branch('75',not null,1)
    cells={};getter=None;collector=None
    if null:
        g.take('488d542460','488bcf');g.call(s['header'])
        g.take('0f57c0','0f114500')
    else:
        g.take('488b4620');cells['type']=g.relative('488b0d')
        g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('75',True,1)
        g.take('4885db');g.branch('0f84',False)
        g.take('83b9e000000000');g.branch('75',True,1)
        g.take('488bcb');g.call(s['typeObject']);g.take('4885c0');g.branch('0f84',False)
        g.take('b944000000','4c89742430','488bd0');g.call(s['creationTest'])
        g.take('33db','a980000000');g.branch('76',create,1)
        if create:
            g.take('488b4620','488b88c0000000','488b4958');g.call(s['activate'])
        else:g.take('8bc3');g.jump('eb',1)
        cells['nonnullFlag']=g.relative('381d')
        g.take('488b4e20','4889442468','488b91c0000000','4c8b7218');g.branch('75',True,1)
        cells['provider']=g.relative('488b0d');g.take('3999e0000000');g.branch('75',True,1)
        g.take('498b4e20');g.call(s['resolve'])
        g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
        g.take('4885c0');g.branch('0f84',False)
        g.take('b905000000','4c8d4c2468','4c8bc7','488bd0');g.call(s['wrapperInvoke'])
        g.take('488b742468','4885f6');g.branch('75',not wrapper_null,1)
        if wrapper_null:g.take('0f57c0','0f114500')
        else:
            g.take('498b4e20');g.call(s['resolve'])
            g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
            g.take('4c8b36','488bf8','498bce');g.call(s['prepare'])
            g.take('410fb79630010000','663bda');g.branch('73',False,1)
            g.take('498b8eb0000000','660f1f840000000000')
            for i in range(ordinal+1):
                g.take('0fb7c3','4803c0','48393cc1');g.branch('0f84',i==ordinal)
                if i<ordinal:g.take('66ffc3','663bda');g.branch('72',True,1)
            g.take('498b86b0000000','0fb7cb','4803c9','486344c808','4883c014','48c1e004','4903c6')
            g.jump('e9')
            g.take('4c8b08','488d4c2420','4c8b4008','488bd6')
            getter=g.at;g.take('41ffd1');collector=flag(g,'833d')
            g.take('0f1000','0f114500');g.branch('0f84',True)
        g.take('4c8b742430')
    g.take('4883c438','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=metadata,staticCells=cells,
        null=null,wrapperNull=None if null else wrapper_null,create=None if null else create,
        consumedBytes=1 if null else None,managedOutputBytes=16,wireBytes=None,
        normalReturn=True,entryRspRestored=True,rcxSelectorRead=False,
        actualFixedSlot=5,callbackOffset=400,companionOffset=408,
        incomingReader='r8 preserved rdi',incomingOutput='r9 preserved rbp',
        wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        interfaceOrdinal=ordinal,getValueMethodSlot=0,hiddenGetterCall=getter,
        hiddenGetterArguments=dict(rcx='local16 output',rdx='returned wrapper',r8='selected GetValue MethodInfo'),
        copyFromReturnedPointer=True,completeCopiedBytes=0 if null or wrapper_null else 16,
        defaultZeroBytes=16 if null or wrapper_null else 0,
        disabledCollectorCell=collector,childWireGrammarAdmitted=False)
