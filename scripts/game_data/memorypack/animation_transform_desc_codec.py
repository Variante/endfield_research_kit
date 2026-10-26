"""TransformDesc MC4: two raw Vector3 fields and two stored Boolean bytes."""
TYPE='Beyond.Gameplay.TransformDesc'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_TransformDescForMemoryPack'
CAPABILITY='animation-transform-desc'
WIRE='transform-desc-profile'
ORDER=[dict(memberIndex=0,fieldName='pos',kind='unity-vector3-raw12',childCapability=None),
       dict(memberIndex=1,fieldName='rot',kind='unity-vector3-raw12',childCapability=None),
       dict(memberIndex=2,fieldName='usePos',kind='bool-byte',childCapability=None),
       dict(memberIndex=3,fieldName='useRot',kind='bool-byte',childCapability=None)]


def need(check,condition):
    if not condition:raise ValueError('animationTransformDescCodec.'+check)


def require_capability(cap,*,ordinary=False):
    need('own-exact-MC4-wire',cap.get('typeName')==TYPE and cap.get('wrapperName')==WRAPPER
        and cap.get('orderedReads')==ORDER and all(type(cap.get(k))is int and cap[k]==v for k,v in
            (('memberCount',4),('nullMarker',255),('nullWireBytes',1),('positiveWireBytes',27)))
        and cap.get('wireBytes')is None and cap.get('nullable')is True
        and cap.get('wholeGrammarAdmitted')is True and cap.get('directWrapperGrammarAdmitted')is True
        and cap.get('wholeOwnerAdmitted')is False)
    if ordinary:
        need('own-ordinary-reference-identity',all(cap.get(k)is True for k in
            ('ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','callbackSelectionConditional'))
            and all(type(cap.get(k))is int and cap[k]>0 for k in
                ('referenceReaderMethodDefinition','referenceReaderTargetRva','originalTypeDefinition')))
    return cap


def read(reader,capability=CAPABILITY,*,depth=0):
    need('own-capability',capability==CAPABILITY);need('bounded-depth',type(depth)is int and 0<=depth<=64)
    cap=require_capability(reader.operation.child(capability));start=reader.pos;fields=[];null=reader.peek()==255
    if null:reader.take(1,CAPABILITY+'.null')
    else:
        reader.header(4)
        for field in cap['orderedReads']:
            at=reader.pos;reader.take(12 if field['kind']=='unity-vector3-raw12'else 1,CAPABILITY+'.'+field['fieldName'])
            fields.append(dict(fieldName=field['fieldName'],kind=field['kind'],start=at,end=reader.pos))
    row=dict(kind=CAPABILITY,typeName=TYPE,start=start,end=reader.pos,isNull=null,fields=fields,
        containingRouteClaimed=False,runtimeTransformProved=False)
    reader.records.append(row);return row
