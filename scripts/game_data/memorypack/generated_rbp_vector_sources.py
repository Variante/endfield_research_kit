"""Exact RBP-local three-Vector3 transfer, separate from nominal child source.

The caller independently proves each current Vector3 source and named setter,
and the header's frame alias. No arbitrary RBP memory or value width follows.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedRbpVectorSource'
TYPE='UnityEngine.Vector3'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def program(regions,entry,*,events,setters,header,base,path):
    address=header.get('headerAddress',{})
    need('exact-owned-RBP-header-frame',address.get('baseRegister')=='rbp'
        and address.get('displacement')==16 and address.get('entryRspOffset')==8
        and address.get('rspDisplacement')==header.get('headerLocalDisplacement')==80
        and header.get('nullFrameBytes')==72 and address.get('baseAliasInstruction')in header.get('prologue',[])
        and(header.get('readerRegister'),header.get('outputRegister'))==('rsi','rbx'))
    alias_site,alias_hex=address['baseAliasInstruction']
    alias=BytesPath(regions,base+alias_site);alias.take('488bec')
    need('same-actual-RBP-frame-alias-bytes',alias_hex.upper()=='488BEC')
    need('exact-three-nominal-source-setter-pairs',len(events)==len(setters)==3 and all(
        e.get('memberIndex')==n and e.get('kind')=='value12:'+TYPE and e.get('declaredType')==TYPE
        and e.get('mode')=='typed-hidden-value'and e.get('resultAbi')=='hidden-local'
        and e.get('sourceContextMode')=='owned-closed-forwarder'and e.get('context')is None
        and e.get('wireBytes')==s.get('storedBytes')==12 and e.get('actualSourceProved')is True
        for n,(e,s)in enumerate(zip(events,setters))))
    g=BytesPath(regions,entry);g.take('807d1003');g.branch('0f85',False)
    sources=[];stores=[];hidden=[];copies=[];calls=[];nulls=[]
    for n,(event,setter)in enumerate(zip(events,setters)):
        last=n==2;g.take('488b1b'if last else'488b3b','488d4df0','488bd6')
        at=g.at;g.call(base+event['sourceTargetRva'])
        need('same-owned-source-instruction',event['instruction']==[at-base,'E8'+(base+event['sourceTargetRva']-at-5).to_bytes(4,'little',signed=True).hex().upper()])
        sources.append(dict(memberIndex=n,instruction=event['instruction'],resultAbi='hidden-local'))
        calls.append(event['instruction']);hidden.append(dict(memberIndex=n,displacement=48,bytes=12,
            sourceInstruction=event['instruction'],frameAddress=dict(baseRegister='rbp',displacement=-16,rspDisplacement=48)))
        g.take('4885db'if last else'4885ff')
        null=g.relative('0f84'if n==0 else'74',4 if n==0 else 1)
        exit=BytesPath(regions,null);exit.relative('e8');exit.take('cc')
        nulls.append([null-base,bytes(exit.bytes[null+i]for i in range(5)).hex().upper()])
        g.take('f20f1000','488d55e0','8b4008','4533c0','488bcb'if last else'488bcf')
        low=g.at;g.take('f20f1145e0');high=g.at;g.take('8945e8')
        copies.extend([dict(memberIndex=n,displacement=32,bytes=8,storeInstruction=[low-base,'F20F1145E0'],sourceOffset=0,
            nominalTypeName=TYPE,frameAddress=dict(baseRegister='rbp',displacement=-32,rspDisplacement=32)),
            dict(memberIndex=n,displacement=40,bytes=4,storeInstruction=[high-base,'8945E8'],sourceOffset=8,
            nominalTypeName=TYPE,frameAddress=dict(baseRegister='rbp',displacement=-24,rspDisplacement=40))])
        at=g.at;g.call(base+setter['method'][3]);instruction=[at-base,'E8'+(base+setter['method'][3]-at-5).to_bytes(4,'little',signed=True).hex().upper()]
        stores.append(dict(memberIndex=n,instruction=instruction,sourceOffset=0,storedBytes=12));calls.append(instruction)
    g.jump('eb',1);g.take('488b5c2458','488b742460','488b7c2468','4883c440','5d','c3')
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    selected_bytes=[(at+i,value)for at,raw in g.seen for i,value in enumerate(bytes.fromhex(raw))]
    selected_rows=[(ec.va(row)+i,value)for row in path for i,value in enumerate(ec.raw(row))]
    need('exact-all-and-only-selected-caller-instructions',selected_rows==selected_bytes)
    return dict(selectedProgram=[ec.site(row,base)for row in path],selectedBytes=g.seen,sources=sources,fieldStores=stores,
        calls=calls,ownedNullCalls=nulls,sourceLocalReferences=[],sourceLocalValues=[],hiddenSourceLocals=hidden,
        sourceLocalCopies=copies,sourceFrameAlias=dict(profile='rbp-frame-three-Vector3.v1',
            baseAliasInstruction=address['baseAliasInstruction'],baseRegister='rbp',entryRspOffset=-8,
            currentRspBytes=72,rspRelativeBaseOffset=64,hiddenLocalBytes=12,hiddenLocalDisplacement=48,
            argumentLocalDisplacement=32,storedSourceSlices=[[0,8],[8,4]]),
        completeSelectedNormalProgram=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False,
        condition='Exact owned RBP frame alias and three independently nominal Vector3 sources/setters; normal compatible ABI-preserving calls, nonnull current wrappers and disjoint stable buffered storage. No helper/provider execution or enclosing child grammar is inferred.')
