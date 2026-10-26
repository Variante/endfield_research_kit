"""Join a full Char source's unchanged RAX reference to its named field."""


def need(check,condition):
    if not condition:raise ValueError('charReferenceFieldBindings.'+check)


def require_transfer(parent,scope,read,pins):
    index=read.get('memberIndex')
    need('complete-own-Char-source',parent.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and parent.get('nativeInputs')==scope.get('nativeInputs')==pins and parent.get('sourceScope')==scope
        and parent.get('completeSelectedCallerAdmitted')is True and parent.get('childGrammarAdmitted')is False
        and parent.get('wholeOwnerAdmitted')is False and type(index)is int and index>=0
        and index<len(parent.get('orderedSourceReads',[]))and parent['orderedSourceReads'][index]==scope['events'][index]==read
        and read.get('kind')=='reference:'+str(read.get('declaredType')))
    setter=parent['setters'][index];member=setter.get('member',{})
    need('same-owned-whole-reference-setter',setter.get('incomingValueStoredUnchanged')is True
        and setter.get('storedBytes')==8 and member.get('name')==read.get('fieldName')
        and member.get('declaredType')==read.get('declaredType')
        and setter.get('targetField','').endswith('::'+read['fieldName']))
    paths=parent.get('programs',[])
    need('all-four-complete-caller-frames',len(paths)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    selected=scope.get('selectedProgram',[])
    if 'richProgram'in scope:
        rich=scope['richProgram'];flows=[s for s in rich.get('sources',[])if s.get('memberIndex')==index]
        stores=[s for s in rich.get('fieldStores',[])if s.get('memberIndex')==index]
        need('whole-rich-reference-flow',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==selected
            and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
            and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
            and stores[0].get('instruction')in selected and scope['richSetters'][index]==setter)
        transfer=stores[0]
    else:
        transfers=[s for s in scope.get('setterTransfers',[])if s.get('memberIndex')==index]
        need('one-whole-ordinary-reference-flow',len(transfers)==1);transfer,=transfers
        receiver=transfer.get('receiver');receivers={'rbx':'488bcb','rsi':'488bce','rdi':'488bcf'}
        need('actual-RAX-RDX-named-call-transfer',transfer.get('sourceCall')==read['instruction']and transfer.get('returnAbi')=='rax'
            and receiver in receivers and transfer.get('transfer',[0,''])[1].lower()=='488bd0'
            and transfer.get('setterTargetRva')==setter['method'][3]
            and all(transfer.get(k)in selected for k in('sourceCall','transfer','setterCall','wrapperLoad')))
        at=selected.index(transfer['transfer'])
        need('complete-owned-reference-call-arguments',at>0 and at+2<len(selected)
            and selected[at-1][1].lower()=='4533c0'and selected[at+1][1].lower()==receivers[receiver]
            and selected[at+2]==transfer['setterCall'])
        call_at,encoded=transfer['setterCall'];raw=bytes.fromhex(encoded)
        need('actual-owned-named-setter-E8',len(raw)==5 and raw[0]==232
            and call_at+5+int.from_bytes(raw[1:],'little',signed=True)==setter['method'][3])
    need('same-complete-program-in-both-positive-frames',all(all(site in p.get('selectedProgram',[])for site in selected)
        for p in paths if not p['wrapperNull']))
    return dict(memberIndex=index,fieldName=read['fieldName'],typeName=read['declaredType'],storedBytes=8,
        sourceInstruction=read['instruction'],setterMethod=setter['method'],fieldOffset=setter['fieldOffset'],
        transfer=transfer,allFourParentFramesProved=True,wholeReferenceStoredUnchanged=True,childGrammarAdmitted=False)
