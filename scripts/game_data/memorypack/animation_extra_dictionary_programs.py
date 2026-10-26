"""Exact buffered enum/reference dictionary source programs for animation.

The DWORD and byte key carriers use separate actual bodies. This proves
framing and transfers only; nominal enum callbacks and reference children
must be selected and authenticated by the owning component.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('animationExtraDictionaryProgram.'+check)


def symbols(regions,*,key_bytes):
    need('finite-key-carrier',type(key_bytes)is int and key_bytes in(1,4))
    four=key_bytes==4
    patterns=dict(header='4c89642428e8'if four else'c684248000000000e8',
        context='488b4f20e8'if four else'488b4e20e8',
        type='ba15000000488b88c0000000e8',allocate='488bc8e8',constructor='488b92b0000000e8',
        barrier='48892ee8'if four else'49893fe8',keyProvider='488b89b8000000e8',
        valueProvider='488b89c0000000e8',keyDispatch='498bd7e8'if four else'488bd7e8',
        valueDispatch='498bd5e8'if four else'498bd6e8',insert='4d8b4928e8')
    result={}
    for role,h in patterns.items():
        prefix=bytes.fromhex(h);found=[]
        for at,raw in regions:
            position=raw.find(prefix)
            while position>=0:
                end=position+len(prefix)
                need('complete-owned-E8:'+role,end+4<=len(raw))
                found.append(at+end+4+int.from_bytes(raw[end:end+4],'little',signed=True))
                position=raw.find(prefix,position+1)
        need('one-owned-helper:'+role,bool(found)and len(set(found))==1)
        result[role]=found[0]
    return result


def program(regions,entry,offsets,s,*,count,key_bytes):
    need('literal-count-and-key-carrier',type(count)is int and count in(-1,0,1,2,3)
        and type(key_bytes)is int and key_bytes in(1,4))
    need('four-distinct-owned-reader-fields',set(offsets)>=set(('currentPtr','bufferLength','advancedCount','consumed'))
        and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in('currentPtr','bufferLength','advancedCount','consumed'))
        and len({offsets[k]for k in('currentPtr','bufferLength','advancedCount','consumed')})==4)
    o={k:bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed')}
    g=BytesPath(regions,entry);four=key_bytes==4
    if four:
        g.take('4053','56','57','4154','4883ec48');flag=g.relative('803d')+1
        g.take('00','498bf8','488bf2','488bd9');g.branch('0f84',False)
        g.take('4533e4','c644247000','488d542470','4489642420','488bcb','4c89642428')
    else:
        g.take('4053','56','4157','4883ec60');flag=g.relative('803d')+1
        g.take('00','498bf0','4c8bfa','488bd9');g.branch('0f84',False)
        g.take('33c0','4c896c2448','488d942498000000','4889442428','488bcb','c684249800000000','c684248000000000')
    g.call(s['header']);g.take('807c2470ff'if four else'80bc2498000000ff');g.branch('0f84',count==-1)
    keys=[];values=[];inserts=[];edges=[];provider=None
    if count==-1:
        if four:g.take('488bce','4c8926')
        else:g.take('4533ed','498bcf','4d892f')
        g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        if four:
            g.take('48896c2478','4c896c2440','4c89742438','4c897c2430','4c3926');g.branch('75',False,1)
        else:
            g.take('4889ac2488000000','48897c2458','4c89642450','4c89742440','0f29742430','49833f00');g.branch('75',False,1)
        load='488b4f20'if four else'488b4e20'
        g.take(load);g.call(s['context']);g.take('ba15000000','488b88c0000000');g.call(s['type'])
        g.take('488bc8');g.call(s['allocate']);g.take('488be8'if four else'488bf8','4885c0');g.branch('0f84',False)
        g.take(load);g.call(s['context']);g.take('488b88c0000000','488b91b0000000',
            '4c396220'if four else'48837a2000');g.branch('0f84',False)
        g.take(load);g.call(s['context']);g.take('488bcd'if four else'488bcf','488b90c0000000','488b92b0000000')
        g.call(s['constructor']);g.take('488bce','48892e')if four else g.take('498bcf','49893f')
        g.call(s['barrier']);provider=g.relative('488b0d')
        g.take('4439a1e0000000'if four else'83b9e000000000');g.branch('0f84',False)
        g.take(load);g.call(s['context']);g.take('488b88c0000000','488b89b8000000');g.call(s['keyProvider'])
        g.take(load,'4c8bf8'if four else'488bf8');g.call(s['context'])
        g.take('488b88c0000000','488b89c0000000');g.call(s['valueProvider'])
        g.take('837b'+o['bufferLength']+'04','4c8be8'if four else'4c8bf0');g.branch('0f8c',False)
        g.take('488b43'+o['currentPtr'],'448b30'if four else'448b20')
        if not four:g.take('4489a42498000000')
        g.take('8b6b'+o['bufferLength'],'83c5fc');g.branch('0f88',False)
        g.take('488343'+o['currentPtr']+'04','8343'+o['advancedCount']+'04',
            '8343'+o['consumed']+'04','896b'+o['bufferLength'],'418bec'if four else'4533ed',
            '4585f6'if four else'4585e4')
        g.branch('7f',count>0,1)if four else g.branch('0f8e',count==0)
        loop=g.at
        for index in range(count):
            need('same-owned-loop-entry',g.at==loop)
            if four:
                g.take('4489642420','4d85ff');g.branch('0f84',False)
                g.take('4c8d4c2420','4c8bc3','498bd7')
            else:
                g.take('c684248000000000','4885ff');g.branch('0f84',False)
                g.take('4c8d8c2480000000','4c8bc3','488bd7')
            keys.append(g.at);g.call(s['keyDispatch'])
            g.take('4c89642428','4d85ed')if four else g.take('33c0','4889442428','4d85f6')
            g.branch('0f84',False)
            if four:g.take('b905000000')
            g.take('4c8d4c2428','4c8bc3','498bd5'if four else'498bd6')
            values.append(g.at);g.call(s['valueDispatch'])
            if four:
                g.take('8b442420','4c8b26','89442470','488b442428','4889842488000000','4d85e4')
            else:g.take('498b2f','440fb6a42480000000','f20f10742428','4885ed')
            g.branch('74',False,1)
            g.take(load);g.call(s['context']);g.take('488b88c0000000','488b4128','4883782000');g.branch('0f84',False)
            g.take(load);g.call(s['context'])
            if four:g.take('4c8b842488000000','498bcc','8b542470')
            else:g.take('66490f7ef0','410fb6d4','488bcd')
            g.take('4c8b88c0000000','4d8b4928');inserts.append(g.at);g.call(s['insert'])
            g.take('ffc5','41bc00000000','413bee')if four else g.take('41ffc5','443bac2498000000')
            edge=g.at;target=g.relative('0f8c');need('exact-owned-loop-backedge',target==loop);edges.append(edge)
            if index+1<count:g.at=target
            elif four:g.jump('e9')
        if four:g.take('4c8b742438','4c8b6c2440','488b6c2478','4c8b7c2430')
        else:g.take('4c8b742440','4c8b642450','488b7c2458','488bac2488000000','0f28742430')
    if four:g.take('4883c448','415c','5f','5e','5b','c3')
    else:g.take('4c8b6c2448','4883c460','415f','5e','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,initializedFlag=flag,providerTypeCell=provider,
        keyOutputBytes=key_bytes,valueOutputBytes=8,objectMarkerBytes=1,countHeaderBytes=4,
        keyCallbackSites=keys,valueCallbackSites=values,insertSites=inserts,backedgeSites=sorted(set(edges)),
        elementCallbacks=max(count,0),
        countDomain='signed-int32-after-nonnull-object-marker',counter='ebp'if four else'r13d',
        savedCount='immutable R14D'if four else'Int32 stack152; R12D reused only after saving count',
        initiallyNullOutputRequired=True,existingOutputClearProved=False,nominalKeyGrammarAdmitted=False,
        referenceChildGrammarAdmitted=False,normalReturn=True,entryRspRestored=True,wholeOwnerAdmitted=False)


def induction(programs,*,key_bytes,count_limit=4096):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('finite-induction-key-carrier',type(key_bytes)is int and key_bytes in(1,4))
    positive=[p for p in programs if p.get('countWitness')in(0,1,2,3)];one,=[p for p in positive if p['countWitness']==1]
    return prove_induction(positive,initial='418bec'if key_bytes==4 else'4533ed',
        increment='ffc5'if key_bytes==4 else'41ffc5',comparison='413bee'if key_bytes==4 else'443bac2498000000',
        counter='ebp'if key_bytes==4 else'r13d',saved_count=one['savedCount'],max_count=count_limit,
        mode_key='newDictionary',backedge_sites=one['backedgeSites'])
