"""Explicit Story Kickable enum list; raw DWORDs, signed count and no owner grant."""
import struct

TYPE='Beyond.Gameplay.KickableObjectType'
CAPABILITY='skill-enum-list:'+TYPE
ELEMENT_CAPABILITY='skill-enum-callback:'+TYPE
COUNT_LIMIT=4096


def need(check,condition):
    if not condition:raise ValueError('currentKickableEnumList.'+check)


def require_capability(cap,element):
    need('own-conditional-list',cap.get('schema')=='endfield.nominal-enum-list-sources.v1'
        and cap.get('status')=='validated-conditional-enum-list'
        and cap.get('closedListType')=='System.Collections.Generic.List`1<'+TYPE+'>'
        and cap.get('elementType')==TYPE and cap.get('elementCapability')==ELEMENT_CAPABILITY
        and cap.get('elementValueType')is True and cap.get('nullable')is True
        and all(cap.get(k)is True for k in('positiveCountsAdmitted','elementGrammarAdmitted','rawBitsPreserved'))
        and all(type(cap.get(k))is int for k in('countLimit','headerBytes','signedCountBits','nullCount','elementWireBytes',
            'elementTypeDefinition','packableReaderMethodDefinition','packableReaderTargetRva'))
        and(cap['countLimit'],cap['headerBytes'],cap['signedCountBits'],cap['nullCount'],cap['elementWireBytes'])==(COUNT_LIMIT,4,32,-1,4)
        and cap.get('collectionCounts')==[-1,0]and all(type(n)is int for n in cap['collectionCounts'])
        and cap['packableReaderMethodDefinition']>=0 and cap['packableReaderTargetRva']>0
        and cap.get('actualRuntimeSelectionObserved')is False and cap.get('parentFieldAdmitted')is False
        and cap.get('wholeOwnerAdmitted')is False and type(cap.get('conditions'))is list and bool(cap['conditions'])
        and all(type(c)is str and c for c in cap['conditions']))
    need('independent-own-nominal-callback',element==cap.get('elementCallback')
        and element.get('nativeInputs')==cap.get('nativeInputs')
        and element.get('schema')=='endfield.enum-nominal-callback-sources.v1'
        and element.get('status')=='validated-conditional-callback'and element.get('typeName')==TYPE
        and element.get('typeDefinition')==cap['elementTypeDefinition']
        and type(element.get('wireBytes'))is int and element['wireBytes']==4
        and type(element.get('callbackSlot'))is int and element['callbackSlot']==5
        and element.get('readerByref')is True and element.get('outputByref')is True
        and element.get('formatterType')=='MemoryPack.Formatters.UnmanagedFormatter`1'
        and type(element.get('callbackTargetRva'))is int and element['callbackTargetRva']>0
        and element.get('actualRuntimeSelectionObserved')is False
        and element.get('unconditionalCallbackSelectionProved')is False
        and element.get('parentOrCollectionGrammarAdmitted')is False
        and type(element.get('conditions'))is list and len(element['conditions'])==6
        and all(type(c)is str and c for c in element['conditions']))
    return cap


def read(reader,*,budget=None,depth=0):
    need('bounded-depth',type(depth)is int and 0<=depth<=64)
    r=reader;cap=require_capability(r.operation.child(CAPABILITY),r.operation.child(ELEMENT_CAPABILITY))
    need('complete-count',r.pos+4<=r.limit)
    count=struct.unpack_from('<i',r.data,r.pos)[0]
    need('bounded-signed-count',-1<=count<=cap['countLimit'])
    need('complete-entry-bytes',r.pos+4+4*max(0,count)<=r.limit)
    if budget is None:budget=[16384]
    need('bounded-node-budget',type(budget)is list and len(budget)==1 and type(budget[0])is int
        and budget[0]>=1+max(0,count))
    budget[0]-=1+max(0,count)
    start=r.pos;r.take(4,CAPABILITY+'.count');entries=[]
    for _ in range(max(0,count)):
        at=r.pos;bits=bytes(r.data[at:at+4]).hex();r.take(4,CAPABILITY+'.enum-bits')
        entries.append(dict(start=at,end=r.pos,rawHex=bits))
    row=dict(kind=CAPABILITY,start=start,end=r.pos,count=count,isNull=count==-1,elementType=TYPE,entries=entries)
    r.records.append(row);return row
