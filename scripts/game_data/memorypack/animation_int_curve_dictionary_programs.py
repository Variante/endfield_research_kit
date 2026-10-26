"""Own Int32/reference Dictionary formatter program for animation curves.

The signed count itself is the four-byte header. This body owns its distinct
inline capacity/default-comparer constructor and key callback comparison; it
does not borrow a different word32 dictionary profile or select a live provider.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check, condition):
    if not condition:
        raise ValueError('animationIntCurveDictionaryProgram.'+check)


def symbols(regions):
    patterns = dict(indexed='ba03000000488b6d10488b89c0000000e8', allocate='488bc8e8',
        defaultComparer='488b4910e8', barrier='4d893c24e8', keyProvider='488b4930e8',
        valueProvider='488b4938e8', prepare='498b0ee8',
        valueDispatch='4c8d4c24384c8bc3498bd5e8', insert='4889442420e8', initialize='4d8b4008e8')
    result = {}
    for name, pattern in patterns.items():
        prefix = bytes.fromhex(pattern); targets = []
        for at, raw in regions:
            position = raw.find(prefix)
            while position >= 0:
                operand = position+len(prefix)
                need('complete-helper-E8:'+name, operand+4 <= len(raw))
                if name != 'allocate' or raw[operand+4:operand+7] == bytes.fromhex('488bf8'):
                    targets.append(at+operand+4+int.from_bytes(raw[operand:operand+4], 'little', signed=True))
                position = raw.find(prefix, position+1)
        need('unique-actual-helper:'+name, bool(targets) and len(set(targets)) == 1)
        result[name] = targets[0]
    return result


def program(regions, entry, offsets, s, *, count, key_callback, same_comparer=False):
    need('finite-count-and-comparer', type(count) is int and -1 <= count <= 3 and type(same_comparer) is bool)
    need('literal-nominal-int-callback', type(key_callback) is int and key_callback > 0)
    keys = ('currentPtr','bufferLength','advancedCount','consumed','totalLength')
    need('five-distinct-reader-fields', len({offsets.get(k) for k in keys}) == 5
        and all(type(offsets.get(k)) is int and 0 <= offsets[k] < 128 for k in keys))
    o = {k:bytes((offsets[k],)).hex() for k in keys}; g = BytesPath(regions, entry)
    g.take('4c89442418','53','55','56','57','4154','4155','4157','4883ec60','4533ff','498bf1',
           '837a'+o['bufferLength']+'04','4d8be0','488bda','4c897c2440','488be9','4489bc24a8000000','4c897c2438')
    g.branch('0f8c',False)
    g.take('488b43'+o['currentPtr'],'4c6328','44896c2430','8b7b'+o['bufferLength'],'83c7fc');g.branch('0f88',False)
    for code,key in (('488343','currentPtr'),('8343','advancedCount'),('8343','consumed')):g.take(code+o[key]+'04')
    g.take('897b'+o['bufferLength'],'486343'+o['consumed'],'488b4b'+o['totalLength'],'482bc8','493bcd')
    g.branch('0f8c',False);g.take('4183fdff');g.branch('0f84',count == -1)
    callback_sites=[];insert_sites=[];backedges=[];provider=None;first=None;second=None
    if count == -1:
        g.take('498bcc','4d893c24');g.call(s['barrier'])
    else:
        g.take('4c89b424a0000000','4d393c24');g.branch('0f85',False)
        g.take('488b4e20','ba03000000','488b6d10','488b89c0000000');g.call(s['indexed'])
        g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
        g.take('488b4e20','488b91c0000000','488b4a20','4c397920');g.branch('0f84',False)
        g.take('488b4620','488b88c0000000','4c8b7120','4585ed');g.branch('0f88',False)
        g.branch('0f8f',count > 0)
        if count > 0:
            g.take('498b4620','488b88c0000000','488b4108','4c397820');g.branch('0f84',False)
            g.take('498b4620','418bd5','488bcf','4c8b80c0000000','4d8b4008');g.call(s['initialize']);g.jump('e9')
        g.take('498b4620','488b88c0000000','488b4910');g.call(s['defaultComparer'])
        g.take('483be8');g.branch('74',same_comparer,1)
        if not same_comparer:
            g.take('488d4f30','48896f30');g.call(s['barrier'])
        g.take('498bcc','49893c24');g.call(s['barrier']);provider=g.relative('488b0d')
        g.take('4439b9e0000000');g.branch('0f84',False)
        g.take('488b4620','488b88c0000000','488b4930');g.call(s['keyProvider'])
        g.take('488b4e20','4c8bf0','488b89c0000000','488b4938');g.call(s['valueProvider'])
        g.take('4c8be8','44397c2430');g.branch('0f8e',count == 0)
        if count:
            first=g.relative('488d3d');second=g.relative('488d2d')
            need('actual-first-compared-Int32-callback',first == key_callback)
            g.take('660f1f840000000000')
        for index in range(count):
            g.take('488b4620','488b88c0000000','488b4940','4883793800');g.branch('0f84',False)
            g.take('0f57c0','0f11442448','33c0','898424a8000000','4889442438','4d85f6');g.branch('0f84',False)
            g.take('498b0e');g.call(s['prepare'])
            g.take('498b06','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False)
            g.take('837b'+o['bufferLength']+'04');g.branch('0f8c',False)
            g.take('488b43'+o['currentPtr'],'8b00','898424a8000000','8b7b'+o['bufferLength'],'83c7fc')
            g.branch('0f88',False)
            for code,key in (('488343','currentPtr'),('8343','advancedCount'),('8343','consumed')):g.take(code+o[key]+'04')
            g.take('897b'+o['bufferLength'],'4d85ed');g.branch('0f84',False)
            g.take('b905000000','4c8d4c2438','4c8bc3','498bd5');callback_sites.append(g.at);g.call(s['valueDispatch'])
            g.take('498b2c24','448bbc24a8000000','4c8b642438','4885ed');g.branch('0f84',False)
            g.take('488b4620','488b88c0000000','488b4148','4883782000');g.branch('0f84',False)
            g.take('488b4620','488b88c0000000','488b7948','488b4720','488b88c0000000',
                   '488b81c0000000','4883782000');g.branch('0f84',False)
            g.take('488b4720','4d8bc4','418bd7','488bcd','4c8b88c0000000','498b81c0000000','41b102','4889442420')
            insert_sites.append(g.at);g.call(s['insert'])
            g.take('4c8b7c2440')
            need('same-first-callback-after-insertion',g.relative('488d3d') == first)
            g.take('4c8ba424b0000000')
            need('same-second-excluded-callback-after-insertion',g.relative('488d2d') == second)
            g.take('41ffc7','4c897c2440','443b7c2430');backedges.append(g.at);g.branch('0f8c',index+1 < count)
        g.take('4c8bb424a0000000')
    g.take('4883c460','415f','415d','415c','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,sameComparer=same_comparer,
        headerBytes=4,nullCount=-1,keyWireBytes=4,valueManagedBytes=8,providerClassCell=provider,
        firstComparedCallback=first,secondExcludedCallback=second,elementCallbackSites=callback_sites,
        valueCallbackSites=callback_sites,insertionCallSites=insert_sites,backedgeSites=backedges,
        counter='r15d',counterHomeOffset=64,savedCountOffset=48,initiallyNullOutputRequired=True,
        nullOutputBytes=8 if count == -1 else 0,normalReturn=True,entryRspRestored=True,
        allNonvolatilesRestored=True,wireGrammarAdmitted=False,reusedDictionaryAdmitted=False,
        frame=dict(entryRspDelta=-152,shadow=[0,32],insertionMethodInfo=[32,40],countHome=[48,52],
            valueLocal=[56,64],counterHome=[64,72],unusedPairZero=[72,88],keyLocal=[168,172],
            savedR14=[160,168],savedOutputArgument=[176,184],
            pushed=['rbx','rbp','rsi','rdi','r12','r13','r15']),
        condition='Actual nominal Int32 key callback matches the first compared pointer; exact selected typed formatter/Dictionary contexts and metadata are initialized. Fresh typed allocation, capacity/default-comparer and insertion effects return normally; stable disjoint buffered Reader/locals and normal callback ABI. R15 is a temporary key then restored from the owned counter home before each increment. Value source, live callback/provider choice and actual outer field/frame remain independent.')


def induction(programs, *, count_limit=4096):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('bounded-count-domain', type(count_limit) is int and 3 <= count_limit <= 4096)
    certificates=[]
    for same in (False,True):
        selected=[p for p in programs if p['sameComparer'] == same and p['countWitness'] >= 0]
        one,=[p for p in selected if p['countWitness'] == 1]
        certificates.append(prove_induction(selected,initial='4533ff',increment='41ffc7',comparison='443b7c2430',
            counter='r15d',saved_count='RSP+48',max_count=count_limit,mode_key='newDictionary',
            backedge_sites=one['backedgeSites']))
    return dict(countLimit=count_limit,comparerProfiles=[False,True],certificates=certificates,
        counterHomeOffset=64,countHomeOffset=48,actualKeyTemporaryRestoredBeforeIncrement=True,
        completeCallerOwnsEveryCounterHomeLoadStore=True,normalNoninterferingChildABIRequired=True)
