"""Two exact enum32/string dictionary programs with separate callback ABIs.

Nominal enum identity and callbacks are separate obligations. These programs
own every selected new/null path, all four count-reader updates, element
locals, insertion arguments, bounded loop induction and complete frame.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check, condition):
    if not condition:raise ValueError('interactiveEnumDictionary.'+check)


def symbols(regions, *, enum_key):
    patterns=dict(header='4c89642428e8'if enum_key else'44896c2420e8',
        context='488b4f20e8',type='ba15000000488b88c0000000e8',
        allocate='488bc8e8',constructor='488b92b0000000e8',barrier='48892ee8',
        keyProvider='488b89b8000000e8',valueProvider='488b89c0000000e8',
        keyDispatch='498bd7e8',valueDispatch='498bd5e8'if enum_key else'498bd4e8',
        insert='4d8b4928e8')
    result={}
    for role,h in patterns.items():
        prefix=bytes.fromhex(h);found=[]
        for at,raw in regions:
            start=0
            while (p:=raw.find(prefix,start))>=0:
                end=p+len(prefix);need('owned-complete-E8.'+role,end+4<=len(raw))
                found.append(at+end+4+int.from_bytes(raw[end:end+4],'little',signed=True));start=p+1
        need('one-actual-helper.'+role,bool(found)and len(set(found))==1);result[role]=found[0]
    return result


def program(regions,entry,offsets,s,*,count,enum_key):
    need('finite-path',type(count)is int and -1<=count<=3 and type(enum_key)is bool)
    if enum_key:
        from scripts.game_data.memorypack.animation_extra_dictionary_programs import program as enum_reference
        return enum_reference(regions,entry,offsets,s,count=count,key_bytes=4)
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('four-distinct-reader-fields',all(type(offsets.get(k))is int and 0<=offsets[k]<128 for k in keys)
        and len({offsets[k]for k in keys})==4)
    c,r,a,u=(bytes((offsets[k],)).hex()for k in keys)
    g=BytesPath(regions,entry);g.take('4053','56','57','4155','4883ec48')
    flag=g.relative('803d')+1;g.take('00','498bf8','488bf2','488bd9');g.branch('0f84',False)
    g.take('4533ed','c644247000','488d542470','4c896c2428','488bcb','44896c2420')
    g.call(s['header']);g.take('807c2470ff');g.branch('0f84',count==-1)
    keys_at=[];values_at=[];inserts=[];edges=[];provider=None
    def context():g.take('488b4f20');g.call(s['context'])
    if count==-1:
        g.take('488bce','4c892e');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('48896c2478','4c89642440','4c89742438','4c897c2430','4c392e');g.branch('75',False,1)
        context();g.take('ba15000000','488b88c0000000');g.call(s['type']);g.take('488bc8');g.call(s['allocate'])
        g.take('488be8','4885c0');g.branch('0f84',False)
        context();g.take('488b88c0000000','488b91b0000000','4c396a20');g.branch('0f84',False)
        context();g.take('488bcd','488b90c0000000','488b92b0000000');g.call(s['constructor'])
        g.take('488bce','48892e');g.call(s['barrier']);provider=g.relative('488b0d')
        g.take('4439a9e0000000');g.branch('0f84',False)
        context();g.take('488b88c0000000','488b89b8000000');g.call(s['keyProvider'])
        g.take('488b4f20','4c8bf8');g.call(s['context']);g.take('488b88c0000000','488b89c0000000');g.call(s['valueProvider'])
        g.take('837b'+r+'04','4c8be0');g.branch('0f8c',False)
        g.take('488b43'+c,'448b30','8b6b'+r,'83c5fc');g.branch('0f88',False)
        g.take('488343'+c+'04','8343'+a+'04','8343'+u+'04','896b'+r,'418bed','4585f6');g.branch('0f8f',count>0)
        loop=g.at
        for index in range(count):
            need('same-loop-entry',g.at==loop)
            g.take('4c896c2428','4d85ff');g.branch('0f84',False)
            g.take('b905000000','4c8d4c2428','4c8bc3','498bd7');keys_at.append(g.at);g.call(s['keyDispatch'])
            g.take('44896c2420','4d85e4');g.branch('0f84',False)
            g.take('4c8d4c2420','4c8bc3','498bd4');values_at.append(g.at);g.call(s['valueDispatch'])
            g.take('488b442428','4c8b2e','4889842488000000','8b442420','89442470','4d85ed');g.branch('0f84',False)
            context();g.take('488b88c0000000','488b4128','4883782000');g.branch('75',True,1)
            context();g.take('448b442470','498bcd','488b942488000000','4c8b88c0000000','4d8b4928')
            inserts.append(g.at);g.call(s['insert']);g.take('ffc5','41bd00000000','413bee')
            edge=g.at;back=g.relative('0f8c');need('same-loop-backedge',back==loop);edges.append(edge)
            if index+1<count:g.at=back
            else:g.jump('e9')
        g.take('4c8b742438','4c8b642440','488b6c2478','4c8b7c2430')
    g.take('4883c448','415d','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,initializedFlag=flag,providerTypeCell=provider,
        keyOutputBytes=8,valueOutputBytes=4,objectMarkerBytes=1,countHeaderBytes=4,
        keyCallbackSites=keys_at,valueCallbackSites=values_at,insertSites=inserts,backedgeSites=sorted(set(edges)),
        elementCallbacks=max(count,0),counter='ebp',savedCount='immutable R14D',
        initiallyNullOutputRequired=True,entryRspRestored=True,normalReturn=True,
        keyGrammarAdmitted=False,valueGrammarAdmitted=False,wholeOwnerAdmitted=False)


def induction(programs,*,enum_key,count_limit=4096):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    return prove_induction(programs[1:],initial='418bec'if enum_key else'418bed',increment='ffc5',
        comparison='413bee',counter='ebp',saved_count='immutable R14D',max_count=count_limit,
        mode_key='newDictionary',backedge_sites=programs[2]['backedgeSites'])
