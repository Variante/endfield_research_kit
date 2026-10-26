"""Exact selected programs for three animation custom dictionaries.

The reference-Montage and managed16-BeyondCurve bodies are distinct programs.
Each consumes an object marker before a separate signed count. Only a fresh
null output, initialized helper state and sufficient buffered input are used;
provider selection and insertion effects remain independent conditions.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check, condition):
    if not condition:
        raise ValueError('animationCustomDictionaryProgram.' + check)


def _offsets(offsets):
    keys = ('currentPtr', 'bufferLength', 'advancedCount', 'consumed')
    need('four-distinct-owned-reader-fields', all(type(offsets.get(k)) is int
        and 0 <= offsets[k] < 128 for k in keys)
        and len({offsets[k] for k in keys}) == 4)
    return {k: bytes((offsets[k],)).hex() for k in keys}


def _count(count):
    need('finite-source-witness', type(count) is int and -1 <= count <= 3)


def symbols(regions, profile):
    """Select literal E8 targets from the independently replayed argument bytes."""
    need('finite-source-profile', profile in ('reference-Montage', 'string-BeyondCurve', 'int-BeyondCurve'))
    patterns = dict(context='488b4e20e8', type='ba15000000488b88c0000000e8',
        allocate='488bc8e8', constructor='488b92b0000000e8',
        keyProvider='488b89b8000000e8', valueProvider='488b89c0000000e8')
    if profile == 'reference-Montage':
        patterns.update(barrier='4d893424e8', prepare='498b0ee8', insert='4889442420e8')
    else:
        patterns.update(context='498b4f20e8', barrier='49895d00e8', header='0f11442430e8',
            keyDispatch='4c8d4c24204c8bc6488bd3e8', valueDispatch='4c8d4c24304c8bc6488bd5e8',
            insert='4d8b4928e8')
    result = {}
    for role, hex_pattern in patterns.items():
        prefix = bytes.fromhex(hex_pattern); targets = []
        for at, raw in regions:
            position = raw.find(prefix)
            while position >= 0:
                operand = position + len(prefix)
                need('complete-E8-'+role, operand+4 <= len(raw))
                suffix = bytes.fromhex('488bf8' if profile == 'reference-Montage' else '488bd8')
                if role != 'allocate' or raw[operand+4:operand+7] == suffix:
                    targets.append(at+operand+4+int.from_bytes(raw[operand:operand+4], 'little', signed=True))
                position = raw.find(prefix, position+1)
        need('one-actual-helper-'+role, bool(targets) and len(set(targets)) == 1)
        result[role] = targets[0]
    return result


def montage_program(regions, entry, offsets, symbols, *, count):
    """Own reference8 key/value locals, slot5 calls and R13D loop."""
    _count(count); o = _offsets(offsets); s = symbols; g = BytesPath(regions, entry)
    g.take('4053', '55', '56', '57', '4154', '4156', '4883ec58')
    flag = g.relative('803d') + 1
    g.take('00', '498bf0', '4c8be2', '488bd9'); g.branch('75', True, 1)
    g.take('4533f6', '837b'+o['bufferLength']+'01', '4c89b424a8000000', '4c89742430')
    g.branch('7d', True, 1)
    g.take('488b43'+o['currentPtr'], '0fb628', '8b7b'+o['bufferLength'], '83ef01')
    g.branch('79', True, 1)
    g.take('48ff43'+o['currentPtr'], 'ff43'+o['advancedCount'], 'ff43'+o['consumed'],
           '897b'+o['bufferLength'], '4080fdff'); g.branch('0f84', count == -1)
    keys = []; values = []; stores = []; edges = []; gc_flag = None; provider = None
    if count == -1:
        g.take('498bcc', '4d893424'); g.call(s['barrier'])
    else:
        g.take('4d393424'); g.branch('0f85', False)
        g.take('488b4e20'); g.call(s['context'])
        g.take('ba15000000', '488b88c0000000'); g.call(s['type'])
        g.take('488bc8'); g.call(s['allocate']); g.take('488bf8', '4885c0')
        g.branch('0f84', False)
        g.take('488b4e20'); g.call(s['context'])
        g.take('488b88c0000000', '488b81b0000000', '4c397020'); g.branch('75', True, 1)
        g.take('488b4e20'); g.call(s['context'])
        g.take('488bcf', '488b90c0000000', '488b92b0000000'); g.call(s['constructor'])
        gc_flag = g.relative('443935')
        g.take('49893c24'); g.branch('74', True, 1)
        provider = g.relative('488b0d')
        g.take('4c89ac2498000000', '4c897c2450', '4439b1e0000000'); g.branch('75', True, 1)
        for slot, register in (('b8', '4c8bf0'), ('c0', None)):
            g.take('488b4620', 'f6803801000001'); g.branch('75', True, 1)
            g.take('488b88c0000000', '488b89'+slot+'000000')
            g.call(s['keyProvider'] if slot == 'b8' else s['valueProvider'])
            if register: g.take(register)
        g.take('837b'+o['bufferLength']+'04', '4c8bf8'); g.branch('7d', True, 1)
        g.take('488b43'+o['currentPtr'], '8b28', '89ac2490000000',
               '8b7b'+o['bufferLength'], '83c7fc'); g.branch('79', True, 1)
        for code, key in (('488343', 'currentPtr'), ('8343', 'advancedCount'), ('8343', 'consumed')):
            g.take(code+o[key]+'04')
        g.take('897b'+o['bufferLength'], '33ff', '448bef', '85ed'); g.branch('0f8e', count == 0)
        for index in range(count):
            g.take('4889bc24a8000000', '4d85f6'); g.branch('0f84', False)
            g.take('498b0e'); g.call(s['prepare'])
            g.take('4d8b0e', '4c8d8424a8000000', '488bd3', '498bce',
                   '498b8190010000', '4d8b8998010000')
            keys.append(g.at); g.take('ffd0')
            g.take('48897c2430', '4d85ff'); g.branch('0f84', False)
            g.take('498b0f'); g.call(s['prepare'])
            g.take('4d8b0f', '4c8d442430', '488bd3', '498bcf',
                   '498b8190010000', '4d8b8998010000')
            values.append(g.at); g.take('ffd0')
            g.take('488b8424a8000000', '498b2c24', '4889442440',
                   '488b442430', '4889442438', '4885ed'); g.branch('0f84', False)
            g.take('488b4620', 'f6803801000001'); g.branch('75', True, 1)
            g.take('488b80c0000000', '488b4828', '4883792000'); g.branch('75', True, 1)
            g.take('488b4620', 'f6803801000001'); g.branch('75', True, 1)
            g.take('488b80c0000000', '488b7828', '488b4720', '488b88c0000000',
                   '488b81c0000000', '4883782000'); g.branch('75', True, 1)
            g.take('488b4720', '488bcd', '4c8b442438', '488b542440',
                   '4c8b88c0000000', '498b81c0000000', '41b101', '4889442420')
            stores.append(g.at); g.call(s['insert'])
            g.take('41ffc5', 'bf00000000', '443bac2490000000')
            edges.append(g.at); g.branch('0f8c', index+1 < count)
        g.take('4c8bac2498000000', '4c8b7c2450')
    g.take('4883c458', '415e', '415c', '5f', '5e', '5d', '5b', 'c3')
    return _result(g, count, 'reference-Montage', flag, provider, keys, values, stores, edges,
        key_bytes=8, value_bytes=8, gc_flag=gc_flag,
        frame=dict(entryRspDelta=-136, callShadow=[0, 32], insertionMethodInfo=[32, 40],
            valueArgument=[56, 64], keyArgument=[64, 72], valueLocal=[48, 56], keyLocal=[168, 176],
            savedR13=[152, 160], savedR15=[80, 88], countHome=[144, 148],
            pushedNonvolatiles=['rbx', 'rbp', 'rsi', 'rdi', 'r12', 'r14']))


def curve_program(regions, entry, offsets, symbols, *, count, key_kind):
    """Own string/int keys and full16 BeyondCurve hidden-local/argument ABI."""
    _count(count); need('finite-curve-key', key_kind in ('string', 'int'))
    string = key_kind == 'string'; o = _offsets(offsets); s = symbols; g = BytesPath(regions, entry)
    g.take('4053', '56', '4155', '4157', '4883ec78')
    flag = g.relative('803d') + 1
    g.take('00', '4d8bf8', '4c8bea', '488bf1'); g.branch('0f84', False)
    g.take('0f57c0', 'c68424a000000000', '33db', '488d9424a0000000', '488bce',
           '48895c2420' if string else '895c2420', '0f11442430'); g.call(s['header'])
    g.take('80bc24a0000000ff'); g.branch('0f84', count == -1)
    keys = []; values = []; stores = []; edges = []; provider = None
    if count == -1:
        g.take('498bcd', '49895d00'); g.call(s['barrier']); g.take('90'); g.jump('e9')
    else:
        g.take('4889ac24a8000000', '48897c2470', '4c89642468', '4c89742460', '0f29742450',
               '49395d00'); g.branch('75', False, 1)
        g.take('498b4f20'); g.call(s['context'])
        g.take('ba15000000', '488b88c0000000'); g.call(s['type'])
        g.take('488bc8'); g.call(s['allocate']); g.take('488bd8', '4885c0'); g.branch('0f84', False)
        g.take('498b4f20'); g.call(s['context'])
        g.take('488b88c0000000', '488b91b0000000', '48837a2000'); g.branch('0f84', False)
        g.take('498b4f20'); g.call(s['context'])
        g.take('488bcb', '488b90c0000000', '488b92b0000000'); g.call(s['constructor'])
        g.take('498bcd', '49895d00'); g.call(s['barrier'])
        provider = g.relative('488b0d')
        g.take('83b9e000000000'); g.branch('0f84', False)
        g.take('498b4f20'); g.call(s['context'])
        g.take('488b88c0000000', '488b89b8000000'); g.call(s['keyProvider'])
        g.take('498b4f20', '488bd8'); g.call(s['context'])
        g.take('488b88c0000000', '488b89c0000000'); g.call(s['valueProvider'])
        g.take('837e'+o['bufferLength']+'04', '488be8'); g.branch('0f8c', False)
        g.take('488b46'+o['currentPtr'], '448b30', '4489b424a0000000',
               '8b7e'+o['bufferLength'], '83c7fc'); g.branch('0f88', False)
        for code, key in (('488346', 'currentPtr'), ('8346', 'advancedCount'), ('8346', 'consumed')):
            g.take(code+o[key]+'04')
        g.take('897e'+o['bufferLength'], '4533e4', '4585f6'); g.branch('0f8e', count == 0)
        if count and string: g.take('66660f1f840000000000')
        for index in range(count):
            g.take('48c744242000000000' if string else 'c744242000000000', '4885db'); g.branch('0f84', False)
            if string: g.take('b905000000')
            g.take('4c8d4c2420', '4c8bc6', '488bd3'); keys.append(g.at); g.call(s['keyDispatch'])
            g.take('0f57c0', '0f11442430', '4885ed'); g.branch('0f84', False)
            g.take('4c8d4c2430', '4c8bc6', '488bd5'); values.append(g.at); g.call(s['valueDispatch'])
            g.take('498b7d00', '4c8b742420' if string else '448b742420', '0f28742430', '4885ff')
            g.branch('0f84', False)
            g.take('498b4f20'); g.call(s['context'])
            g.take('488b88c0000000', '488b4128', '4883782000'); g.branch('0f84', False)
            g.take('498b4f20', '660f7f742440'); g.call(s['context'])
            g.take('4c8d442440', '498bd6' if string else '418bd6', '488bcf', '4c8b88c0000000', '4d8b4928')
            stores.append(g.at); g.call(s['insert'])
            g.take('41ffc4', '443ba424a0000000'); edges.append(g.at); g.branch('0f8c', index+1 < count)
        g.take('4c8b742460', '4c8b642468', '488b7c2470', '488bac24a8000000', '0f28742450')
    g.take('4883c478', '415f', '415d', '5e', '5b', 'c3')
    return _result(g, count, key_kind+'-BeyondCurve', flag, provider, keys, values, stores, edges,
        key_bytes=8 if string else 4, value_bytes=16, frame=dict(entryRspDelta=-152,
            callShadow=[0, 32], keyLocal=[32, 40 if string else 36], valueLocal=[48, 64],
            valueArgument=[64, 80], savedXmm6=[80, 96], savedR14=[96, 104], savedR12=[104, 112],
            savedRDI=[112, 120], savedRBP=[168, 176], countHome=[160, 164],
            pushedNonvolatiles=['rbx', 'rsi', 'r13', 'r15']))


def _result(g, count, profile, flag, provider, keys, values, stores, edges, *, key_bytes, value_bytes, frame, gc_flag=None):
    return dict(selectedBytes=g.seen, profile=profile, countWitness=count, newDictionary=True,
        metadataReadyFlag=flag, providerClassCell=provider, disabledCollectorFlag=gc_flag,
        nullMarker=255, headerBytes=1, nativePositiveHeaderOneEnforced=False,
        countBytes=0 if count == -1 else 4, initiallyNullOutputRequired=count != -1,
        elementCallbackSites=keys, keyCallbackSites=keys, valueCallbackSites=values,
        insertionCallSites=stores, backedgeSites=edges, keyOutputBytes=key_bytes, valueOutputBytes=value_bytes,
        callbackSlot=5, callbackMethodInfoOffset=408, outputAbi='void-byref-reference8',
        readerRegister='incoming RCX', outputRegister='incoming RDX', methodInfoRegister='incoming R8',
        normalReturn=True, entryRspRestored=True, allWin64IntegerNonvolatilesRestored=True,
        wholeXmm6Restored=value_bytes == 16 and count != -1, frame=frame,
        reusedDictionaryAdmitted=False, wireGrammarAdmitted=False,
        conditions=['Initialized exact metadata/helper contexts and provider class.',
            'Initially null out-reference for a non-FF marker; normal allocation/constructor returns.',
            'Sufficient stable disjoint buffered input, nonwrapping Reader/count arithmetic.',
            'Exact nominal provider receiver/MethodInfo and callback selection remain independent.',
            'Callbacks and insertion preserve Win64 nonvolatiles and live locals; normal insertion returns.'])
