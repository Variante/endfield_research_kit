"""Pure nominal Int32-enum list checks for explicitly selected domain owners.

There is no default domain. A caller supplies its own exact nominal, keys and
count bound; an independently authenticated callback and list capability must
agree before even the null count is read. Stored bits stay anonymous DWORDs.
"""
import struct


def need(check,condition):
    if not condition:raise ValueError('nominalEnumListCodec.'+check)


def require_capability(cap,element,*,name,count_limit,element_capability):
    need('explicit-domain-parameters',type(name)is str and bool(name)
         and type(count_limit)is int and 0<count_limit<=10000
         and element_capability=='skill-enum-callback:'+name)
    need('own-conditional-list',isinstance(cap,dict)
         and cap.get('schema')=='endfield.nominal-enum-list-sources.v1'
         and cap.get('status')=='validated-conditional-enum-list'
         and cap.get('closedListType')=='System.Collections.Generic.List`1<'+name+'>'
         and cap.get('elementType')==name and cap.get('elementCapability')==element_capability
         and all(cap.get(k)is True for k in('elementValueType','nullable','positiveCountsAdmitted','elementGrammarAdmitted','rawBitsPreserved'))
         and all(type(cap.get(k))is int and cap[k]==v for k,v in
             (('countLimit',count_limit),('headerBytes',4),('signedCountBits',32),('nullCount',-1),('elementWireBytes',4)))
         and cap.get('collectionCounts')==[-1,0]and all(type(n)is int for n in cap['collectionCounts'])
         and all(type(cap.get(k))is int and 0<=cap[k]<1<<32 for k in('elementTypeDefinition','packableReaderMethodDefinition'))
         and type(cap.get('packableReaderTargetRva'))is int and 0<cap['packableReaderTargetRva']<1<<32
         and all(cap.get(k)is False for k in('actualRuntimeSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))
         and type(cap.get('conditions'))is list and bool(cap['conditions'])
         and all(type(c)is str and bool(c)for c in cap['conditions']))
    need('independent-own-nominal-callback',isinstance(element,dict)and element==cap.get('elementCallback')
         and element.get('nativeInputs')==cap.get('nativeInputs')
         and element.get('schema')=='endfield.enum-nominal-callback-sources.v1'
         and element.get('status')=='validated-conditional-callback'
         and element.get('typeName')==name and element.get('typeDefinition')==cap['elementTypeDefinition']
         and type(element.get('wireBytes'))is int and element['wireBytes']==4
         and type(element.get('callbackSlot'))is int and element['callbackSlot']==5
         and element.get('readerByref')is True and element.get('outputByref')is True
         and element.get('formatterType')=='MemoryPack.Formatters.UnmanagedFormatter`1'
         and type(element.get('callbackTargetRva'))is int and 0<element['callbackTargetRva']<1<<32
         and all(element.get(k)is False for k in('actualRuntimeSelectionObserved','unconditionalCallbackSelectionProved','parentOrCollectionGrammarAdmitted'))
         and type(element.get('conditions'))is list and len(element['conditions'])==6
         and all(type(c)is str and bool(c)for c in element['conditions']))
    return cap


def read(reader,*,capability,element_capability,name,count_limit,budget=None,depth=0):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(reader.operation.child(capability),reader.operation.child(element_capability),
        name=name,count_limit=count_limit,element_capability=element_capability)
    need('complete-count',reader.pos+4<=reader.limit)
    count=struct.unpack_from('<i',reader.data,reader.pos)[0]
    need('bounded-signed-count',-1<=count<=count_limit)
    need('complete-element-bytes',reader.pos+4+4*max(0,count)<=reader.limit)
    if budget is None:budget=dict(remaining=16384)
    need('literal-shared-node-budget',type(budget)is dict and set(budget)=={'remaining'}
         and type(budget['remaining'])is int and 1+max(0,count)<=budget['remaining']<=16384)
    start=reader.pos;budget['remaining']-=1+max(0,count)
    reader.take(4,capability+'.count');entries=[]
    for _ in range(max(0,count)):
        at=reader.pos;bits=bytes(reader.data[at:at+4]).hex()
        reader.take(4,capability+'.enum-bits');entries.append(dict(start=at,end=reader.pos,rawHex=bits))
    row=dict(kind=capability,start=start,end=reader.pos,count=count,isNull=count==-1,elementType=name,entries=entries)
    reader.records.append(row)
    return row
