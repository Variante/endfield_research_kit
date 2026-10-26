"""Exact positive Char static dictionaries, with distinct UInt32 key flow.

The UInt path extends its independently strict null/zero parser at the actual
count branch. The string/reference body uses the identical owned neutral
slot-five byte program already checked for animation's reference maps. Nominal
contexts, callbacks, construction and parent fields remain separate joins.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import char_perform_dictionary_sources as zero
from scripts.game_data.memorypack import animation_custom_dictionary_programs as reference


def need(check,condition):
    if not condition:raise ValueError('charPositiveDictionary.'+check)


def symbols(regions,*,unsigned):
    patterns=dict(keyDispatch='4c8d4c24204c8bc3498bd7e8',
        valueDispatch='b9050000004c8d4c24284c8bc3498bd4e8',insert='4d8b4928e8')
    if not unsigned:return reference.symbols(regions,'reference-Montage')
    out={}
    for role,encoded in patterns.items():
        pattern=bytes.fromhex(encoded);found=[]
        for at,raw in regions:
            offset=raw.find(pattern)
            while offset>=0:
                operand=offset+len(pattern);need('complete-actual-E8',operand+4<=len(raw))
                found.append(at+operand+4+int.from_bytes(raw[operand:operand+4],'little',signed=True))
                offset=raw.find(pattern,offset+1)
        need('one-owned-'+role,len(set(found))==1);out[role]=found[0]
    return out


def program(regions,entry,offsets,s,*,count,unsigned):
    need('literal-finite-witness',type(count)is int and -1<=count<=3 and type(unsigned)is bool)
    if not unsigned:
        return reference.montage_program(regions,entry,offsets,s,count=count)
    if count==-1:
        result=zero.uint_reference(regions,entry,offsets,s,null=True)
        result.update(countWitness=-1,newDictionary=True,keyCallbackSites=[],valueCallbackSites=[],
            insertionCallSites=[],backedgeSites=[],elementCallbackSites=[],normalReturn=True)
        return result
    empty=zero.uint_reference(regions,entry,offsets,s)
    chunks=empty['selectedBytes'];test=[i for i,(at,h)in enumerate(chunks)if h=='4585f6']
    need('one-exact-saved-count-test',len(test)==1);index,=test
    branch=chunks[index+1];need('exact-positive-count-branch',branch[1]=='0f8f')
    g=BytesPath(regions,branch[0]);g.branch('0f8f',count>0);keys=[];values=[];stores=[];edges=[]
    for ordinal in range(count):
        g.take('44896c2420','4d85ff');g.branch('0f84',False)
        g.take('4c8d4c2420','4c8bc3','498bd7');keys.append(g.at);g.call(s['keyDispatch'])
        g.take('4c896c2428','4d85e4');g.branch('0f84',False)
        g.take('b905000000','4c8d4c2428','4c8bc3','498bd4');values.append(g.at);g.call(s['valueDispatch'])
        g.take('8b442420','4c8b2e','89442470','488b442428','4889842488000000','4d85ed');g.branch('0f84',False)
        g.take('488b4f20');g.call(s['context']);g.take('488b88c0000000','488b4128','4883782000');g.branch('75',True,1)
        g.take('488b4f20');g.call(s['context']);g.take('4c8b842488000000','498bcd','8b542470','4c8b88c0000000','4d8b4928')
        stores.append(g.at);g.call(s['insert'])
        g.take('ffc5','41bd00000000','413bee');edges.append(g.at);g.branch('0f8c',ordinal+1<count)
    if count:g.jump('e9')
    zero._uint_end(g,True)
    return dict(selectedBytes=chunks[:index+1]+g.seen,countWitness=count,newDictionary=True,
        keyCallbackSites=keys,valueCallbackSites=values,elementCallbackSites=keys,insertionCallSites=stores,backedgeSites=edges,
        nullMarker=255,headerBytes=1,countBytes=4,keyOutputBytes=4,valueOutputBytes=8,
        normalReturn=True,entryRspRestored=True,allWin64IntegerNonvolatilesRestored=True,
        initiallyNullOutputRequired=True,reusedDictionaryAdmitted=False,wireGrammarAdmitted=False,
        frame=dict(entryRspDelta=-104,callShadow=[0,32],keyLocal=[32,36],valueLocal=[40,48],
            keyArgument=[112,116],valueArgument=[136,144],savedR15=[48,56],savedR14=[56,64],savedR12=[64,72],
            savedRBP=[120,128],incomingCallerHome=[112,144],pushedNonvolatiles=['rbx','rsi','rdi','r13']))


def induction(programs,*,unsigned,count_limit=4096):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('bounded-positive-dictionary',type(count_limit)is int and 3<=count_limit<=4096)
    if not unsigned:
        from scripts.game_data.memorypack.animation_custom_dictionary_sources import induction as reference_induction
        return reference_induction(programs,count_limit=count_limit)
    rows=[p for p in programs if p['countWitness']>=0]
    need('all-count-witnesses',len(rows)==4 and{p['countWitness']for p in rows}=={0,1,2,3})
    body=next(p for p in rows if p['countWitness']==3);need('one-actual-backedge',len(set(body['backedgeSites']))==1)
    return prove_induction(rows,initial='418bed',increment='ffc5',comparison='413bee',counter='ebp',saved_count='r14d',
        max_count=count_limit,mode_key='newDictionary',backedge_sites=[body['backedgeSites'][0]])


def object_marker_program(regions,entry,offsets):
    """Own buffered byte header, separate from the signed count source."""
    b=lambda name:bytes((offsets[name],)).hex();g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','8379'+b('bufferLength')+'01','488bfa','488bd9')
    g.branch('0f8c',False);g.take('488b43'+b('currentPtr'),'0fb608','880f','8b73'+b('bufferLength'),'83ee01')
    g.branch('0f88',False);g.take('48ff43'+b('currentPtr'),'ff43'+b('advancedCount'),'ff43'+b('consumed'),
        '8973'+b('bufferLength'),'803fff','488b5c2430','488b742438','0f95c0','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=1,returnedAlIsFalseExactlyFor255=True,
        allFourReaderUpdatesProved=True,entryRspRestored=True,normalReturn=True)
