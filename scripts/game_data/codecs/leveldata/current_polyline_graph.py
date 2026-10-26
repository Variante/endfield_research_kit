"""Bounded pure cursor for the selected positive Polyline graph."""
from scripts.game_data.memorypack import leveldata_polyline_graph_sources as source
from scripts.game_data.memorypack.leveldata_polyline_graph_components import key,WIRE,LIST_WIRE


def need(check,condition):
    if not condition:raise ValueError('currentPolylineGraph.'+check)


def wire(typ):
    if typ=='float':return 'float32-bits'
    if typ=='bool':return 'bool-byte'
    if typ=='UnityEngine.Vector3':return 'unity-vector3-raw12'
    if typ=='Beyond.AABB':return 'story-aabb-raw16'
    if typ in(source.TREE,source.NODE):return WIRE
    if typ.startswith('System.Collections.Generic.List`1<'):return LIST_WIRE
    raise ValueError('currentPolylineGraph.unowned-wire:'+typ)


def validate(cap):
    need('exact-selected-graph',cap.get('schema')==source.SCHEMA and cap.get('typeName')==source.TYPE
        and type(cap.get('memberCount'))is int and cap['memberCount']==12
        and all(cap.get(k)is True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','wholeGrammarAdmitted',
            'finiteFloatProfile','actualCallbackEqualsProvedChildRequired','positiveBvhNodesAdmitted',
            'positiveConvexPolygonsAdmitted','positiveTreeAdmitted','recursiveTypeGrammarDischarged'))
        and cap.get('liveFormatterSelectionObserved')is False
        and set(cap.get('programs',{}))==set(source.PLANS)
        and set(cap.get('records',{}))=={key(t)for t in source.PLANS}
        and set(cap.get('collections',{}))=={key(source.LIST(t))for t in('int',source.VECTOR,source.NODE,source.LIST(source.VECTOR))}
        and cap.get('recursiveTypeGrammar')==dict(types=[source.NODE],nullMarker=255,positiveHeaderBytes=1,
            positiveNodeBoundsWireBytes=16,depthLimit=64,nodeBudget=16384)
        and all(type(cap.get('recursiveTypeGrammar',{}).get(k))is int for k in
            ('nullMarker','positiveHeaderBytes','positiveNodeBoundsWireBytes','depthLimit','nodeBudget'))
        and cap.get('program')==cap['programs'][source.TYPE])
    for name,plan in source.PLANS.items():
        own=cap['records'][key(name)];program=cap['programs'][name]
        need('exact-own-record-cap',own.get('typeName')==name and type(own.get('memberCount'))is int and own['memberCount']==len(plan)
            and all(own.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
                'recursiveTypeGrammarAssumption','actualCallbackEqualsProvedChildRequired'))
            and own.get('liveFormatterSelectionObserved')is False
            and all(type(own.get(k))is int and own[k]>0 for k in('referenceReaderMethodDefinition',
                'referenceReaderTargetRva','originalTypeDefinition','canonicalAdapterTargetRva',
                'canonicalAdapterMethodDefinition','formatterDeserializeMethodDefinition')))
        need('exact-own-program-order',type(program.get('memberCount'))is int and program['memberCount']==len(plan)
            and all(type(r.get('memberIndex'))is int for r in program.get('reads',[]))
            and[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]==[
                (i,n,wire(t),key(t)if t in(source.TREE,source.NODE)or t.startswith('System.Collections.Generic.List`1<')else None)
                for i,(n,t)in enumerate(plan)])
        expected=[(n,t,key(t))for n,t in plan if t in(source.TREE,source.NODE)or t.startswith('System.Collections.Generic.List`1<')]
        bindings=program.get('childBindings',[])
        need('exact-own-program-bindings',[(b.get('fieldName'),b.get('typeName'),b.get('capability'))for b in bindings]==expected
            and program.get('requiredCapabilities')==sorted({k for n,t,k in expected}))
        for b in bindings:
            child=cap['records'][b['capability']]if b['typeName']in(source.TREE,source.NODE)else cap['collections'][b['capability']]
            prefix='reference'if b['typeName']in(source.TREE,source.NODE)else'packable'
            need('same-own-child-reader-identity',child.get('typeName')==b['typeName']
                and all(type(b.get(k))is int and b[k]>0 for k in('readerMethodDefinition','sourceTargetRva'))
                and(b['readerMethodDefinition'],b['sourceTargetRva'])==
                    (child.get(prefix+'ReaderMethodDefinition'),child.get(prefix+'ReaderTargetRva')))
            callback_keys=('canonicalAdapterTargetRva','canonicalAdapterMethodDefinition')if prefix=='reference'else(
                ('elementCallbackTargetRva','elementCallbackMethodDefinition')if child.get('elementCapability')is not None else())
            need('same-own-child-callback-identity',all(type(b.get(k))is int and b[k]==child.get(k)for k in callback_keys))
    for capability,own in cap['collections'].items():
        element=own.get('elementType');name=source.LIST(element)if isinstance(element,str)else None
        need('exact-positive-collection',element in('int',source.VECTOR,source.NODE,source.LIST(source.VECTOR))
            and own.get('typeName')==name and capability==key(name)and type(own.get('countLimit'))is int
            and own['countLimit']==source.LIMIT and own.get('countRange')==[-1,source.LIMIT]
            and all(type(n)is int for n in own.get('countRange',[]))
            and all(type(own.get(k))is int and own[k]>0 for k in('packableReaderMethodDefinition','packableReaderTargetRva'))
            and isinstance(own.get('sourceMethodSpec'),list)and len(own['sourceMethodSpec'])==3
            and all(type(n)is int for n in own['sourceMethodSpec'])and own['sourceMethodSpec'][0]==own['packableReaderMethodDefinition']
            and all(own.get(k)is True for k in('nullable','positiveCountsAdmitted','wholeGrammarAdmitted','actualCallbackEqualsProvedChildRequired'))
            and own.get('liveFormatterSelectionObserved')is False
            and own.get('elementWireBytes')==(4 if element=='int'else 8 if element==source.VECTOR else None)
            and own.get('elementCapability')==(key(element)if element in(source.NODE,source.LIST(source.VECTOR))else None))
        if element in(source.NODE,source.LIST(source.VECTOR)):
            child=cap['records'][key(element)]if element==source.NODE else cap['collections'][key(element)]
            keys=('canonicalAdapterTargetRva','canonicalAdapterMethodDefinition')if element==source.NODE else(
                'canonicalFormatterTargetRva','canonicalFormatterMethodDefinition')
            need('same-independent-list-element-callback',all(type(own.get(k))is int and own[k]>0 for k in
                ('elementCallbackTargetRva','elementCallbackMethodDefinition'))
                and(own['elementCallbackTargetRva'],own['elementCallbackMethodDefinition'])==(child.get(keys[0]),child.get(keys[1])))
            carrier=own.get('elementCarrier',{});raw=bytes.fromhex(carrier.get('rawHex',''))
            need('same-independent-list-element-carrier',carrier.get('name')==element and len(raw)==16
                and raw[10:12]==bytes((18,0)if element==source.NODE else(21,0)))
            if element==source.NODE:need('same-own-Node-type-definition',int.from_bytes(raw[:8],'little')==child['originalTypeDefinition'])
            else:need('same-complete-inner-Vector2-list-carrier',carrier==child.get('closedCarrier'))
        elif element==source.VECTOR:
            need('explicit-own-inner-list-callback',all(type(own.get(k))is int and own[k]>0 for k in
                ('canonicalFormatterTargetRva','canonicalFormatterMethodDefinition'))
                and own.get('closedCarrier',{}).get('name')==name)
    root=cap['records'][key(source.TYPE)]
    need('same-outer-reference-identity',(cap.get('referenceReaderMethodDefinition'),cap.get('referenceReaderTargetRva'))==
        (root['referenceReaderMethodDefinition'],root['referenceReaderTargetRva']))


def read(reader,field,cap):
    validate(cap);budget={'remaining':16384}
    def consume(path):
        if budget['remaining']<=0:reader.refuse(path,'polyline-node-budget',budget['remaining'])
        budget['remaining']-=1
    def vector(path,axes):return [reader.single(path+'.'+axis)for axis in axes]
    def record(name,path,depth):
        if depth>=64:reader.refuse(path,'polyline-depth-limit',depth)
        consume(path);start=reader.offset;marker=reader.number('<B',path+'.memberCount')
        if marker==255:return None
        plan=source.PLANS[name]
        if marker!=len(plan):reader.refuse(path,'polyline-member-count',marker)
        result=dict(startOffset=start,recordType=name,memberCount=len(plan));ranges={}
        for name,typ in plan:
            at=reader.offset;p=path+'.'+name
            if typ=='float':value=reader.single(p)
            elif typ=='bool':value=reader.boolean(p)
            elif typ=='UnityEngine.Vector3':value=dict(zip('xyz',vector(p,'xyz')))
            elif typ=='Beyond.AABB':value=dict(min=vector(p+'.min','xy'),max=vector(p+'.max','xy'))
            elif typ in(source.TREE,source.NODE):value=record(typ,p,depth+1)
            else:value=collection(typ,p,depth+1)
            result[name]=value;ranges[name]=[at,reader.offset]
        result.update(endOffset=reader.offset,fieldRanges=ranges);return result
    def collection(name,path,depth):
        if depth>=64:reader.refuse(path,'polyline-depth-limit',depth)
        consume(path);start=reader.offset;count=reader.number('<i',path+'.count')
        if not -1<=count<=source.LIMIT:reader.refuse(path,'polyline-count-limit',count)
        element=cap['collections'][key(name)]['elementType'];minimum=4 if element=='int'else 8 if element==source.VECTOR else 4 if element==source.LIST(source.VECTOR)else 1
        reader.need(max(count,0)*minimum,path+'.elements');rows=[]
        for i in range(max(count,0)):
            p=path+f'[{i}]'
            if element=='int':consume(p);value=reader.number('<i',p)
            elif element==source.VECTOR:consume(p);value=vector(p,'xy')
            elif element==source.NODE:value=record(source.NODE,p,depth+1)
            else:value=collection(source.LIST(source.VECTOR),p,depth+1)
            rows.append(value)
        return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
    return record(source.TYPE,field,0)
