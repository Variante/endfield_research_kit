"""Exact Int32/string static dictionary programs, including inline Int32 reads.

Both directions own their byte programs. Provider selection is conditional;
no reference stride becomes a serialized string width.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('interactiveDictionaryProgram.'+check)


def symbols(regions,*,int_key):
    load='488b4f20'if int_key else'488b4e20'
    patterns=dict(context=load+'e8',type='ba15000000488b88c0000000e8',allocate='488bc8e8',
        constructor='488b92b0000000e8',barrier='49897500e8'if int_key else'49897d00e8',
        keyProvider='488b89b8000000e8',valueProvider='488b89c0000000e8',
        prepare='488b0ee8'if int_key else'498b0ee8',dispatch='498bd4e8',insert='4d8b4928e8')
    result={}
    for name,h in patterns.items():
        prefix=bytes.fromhex(h);found=[]
        for at,raw in regions:
            start=0
            while (p:=raw.find(prefix,start))>=0:
                end=p+len(prefix);need('owned-E8-'+name,end+4<=len(raw))
                found.append(at+end+4+int.from_bytes(raw[end:end+4],'little',signed=True));start=p+1
        need('one-actual-helper-'+name,bool(found)and len(set(found))==1);result[name]=found[0]
    return result


def program(regions,entry,offsets,s,*,count,int_key):
    need('finite-witness-and-direction',type(count)is int and -1<=count<=3 and type(int_key)is bool)
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('four-reader-fields',set(keys)<=set(offsets)and len({offsets[k]for k in keys})==4
        and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
    c,r,a,u=(bytes((offsets[k],)).hex()for k in keys)
    g=BytesPath(regions,entry);g.take('4053','55','56','57','4155','4157','4883ec38')
    flag=g.relative('803d')+1;g.take('00','498bf8'if int_key else'498bf0','4c8bea','488bd9');g.branch('0f84',False)
    g.take('4533ff','837b'+r+'01')
    if int_key:g.take('44897c2470','4c897c2428')
    else:g.take('4c897c2428','44897c2470')
    g.branch('0f8c',False);g.take('488b43'+c,'0fb628','8b'+('73'if int_key else'7b')+r,
        '83'+('ee'if int_key else'ef')+'01');g.branch('0f88',False)
    g.take('48ff43'+c,'ff43'+a,'ff43'+u,'89'+('73'if int_key else'7b')+r,'4080fdff');g.branch('0f84',count==-1)
    load='488b4f20'if int_key else'488b4e20'
    def context():g.take(load);g.call(s['context'])
    def read_int(load_value,save,remaining):
        g.take('837b'+r+'04');g.branch('0f8c',False);g.take('488b43'+c,load_value,save,
            '8b'+remaining+r,'83'+('c5'if remaining=='6b'else'c7')+'fc');g.branch('0f88',False)
        g.take('488343'+c+'04','8343'+a+'04','8343'+u+'04','89'+remaining+r)
    callback_sites=[];inserts=[];edges=[];inline_reads=[];int_targets=[]
    if count==-1:
        g.take('498bcd','4d897d00');g.call(s['barrier'])
    else:
        g.take('4c89642478','4c89742430','4d397d00');g.branch('75',False,1)
        context();g.take('ba15000000','488b88c0000000');g.call(s['type']);g.take('488bc8');g.call(s['allocate'])
        g.take('488bf0'if int_key else'488bf8','4885c0');g.branch('0f84',False)
        context();g.take('488b88c0000000','488b91b0000000','4c397a20');g.branch('0f84',False)
        context();g.take('488bce'if int_key else'488bcf','488b90c0000000','488b92b0000000');g.call(s['constructor'])
        g.take('498bcd','49897500'if int_key else'49897d00');g.call(s['barrier'])
        provider=g.relative('488b0d');g.take('4439b9e0000000');g.branch('0f84',False)
        context();g.take('488b88c0000000','488b89b8000000');g.call(s['keyProvider'])
        if int_key:g.take(load,'488bf0');g.call(s['context'])
        else:g.take(load,'4c8be0');g.call(s['context'])
        g.take('488b88c0000000','488b89c0000000');g.call(s['valueProvider'])
        g.take('837b'+r+'04','4c8be0'if int_key else'4c8bf0');g.branch('0f8c',False)
        g.take('488b43'+c,'448b30'if int_key else'8b28','4489742420'if int_key else'896c2420',
            '8b'+('6b'if int_key else'7b')+r,'83'+('c5'if int_key else'c7')+'fc');g.branch('0f88',False)
        g.take('488343'+c+'04','8343'+a+'04','8343'+u+'04','89'+('6b'if int_key else'7b')+r,
            '4489bc2488000000','4585f6'if int_key else'85ed');g.branch('0f8e',count==0)
        if count:
            int_targets.append(g.relative('488d2d'if int_key else'488d3d'))
            int_targets.append(g.relative('4c8d35'if int_key else'488d2d'))
            if not int_key:g.take('6690')
            loop=g.at
            for index in range(count):
                def integer():
                    g.take('4885f6'if int_key else'4d85f6');g.branch('0f84',False)
                    g.take('488b0e'if int_key else'498b0e');g.call(s['prepare'])
                    g.take('488b06'if int_key else'498b06','4c8b9090010000','4c8b8898010000',
                        '4c3bd5'if int_key else'4c3bd7');g.branch('0f85',False)
                    inline_reads.append(g.at)
                    read_int('8b00','89442470','6b'if int_key else'7b')
                def string():
                    g.take('4c897c2428'if int_key else'4c897c2428','4d85e4');g.branch('0f84',False)
                    g.take('b905000000','4c8d4c2428','4c8bc3','498bd4');callback_sites.append(g.at);g.call(s['dispatch'])
                if int_key:
                    g.take('44897c2470');integer();string()
                    g.take('498b6d00','448b742470','4c8b7c2428','4885ed')
                else:
                    string();g.take('44897c2470');integer()
                    g.take('498b7d00','488b6c2428','448b7c2470','4885ff')
                g.branch('0f84',False)
                context();g.take('488b88c0000000','488b4128','4883782000');g.branch('0f84',False)
                context();g.take('4d8bc7','418bd6','488bcd')if int_key else g.take('458bc7','488bd5','488bcf')
                g.take('4c8b88c0000000','4d8b4928');inserts.append(g.at);g.call(s['insert'])
                g.take('8b842488000000');g.relative('488d2d'if int_key else'488d3d');g.take('ffc0')
                g.relative('4c8d35'if int_key else'488d2d');g.take('41bf00000000','89842488000000','3b442420')
                edge=g.at;back=g.relative('0f8c');need('exact-loop-backedge',back==loop);edges.append(edge)
                if index+1<count:g.at=back
        g.take('4c8b642478','4c8b742430')
    g.take('4883c438','415f','415d','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newDictionary=True,initializedFlag=flag,
        stringCallbackSites=callback_sites,insertSites=inserts,backedgeSites=sorted(set(edges)),
        inlineInt32Sites=inline_reads,intCallbackTargets=int_targets,objectMarkerBytes=1,countHeaderBytes=4,
        keyOutputBytes=4 if int_key else 8,valueOutputBytes=8 if int_key else 4,
        entryRspRestored=True,normalReturn=True,elementCallbacks=max(count,0),
        initiallyNullOutputRequired=True,wholeOwnerAdmitted=False)
