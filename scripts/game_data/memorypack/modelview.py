"""Pure bounded ModelView stored framing; the owning facade authenticates its layout."""
import math,struct


def frame(data,layout,strings):
    offset=0
    def take(n,path):
        nonlocal offset
        if n<0 or offset+n>len(data):raise ValueError(f'{path}:truncated@{offset}')
        value=data[offset:offset+n];offset+=n;return value
    def scalar(fmt,path):return struct.unpack('<'+fmt,take(struct.calcsize(fmt),path))[0]
    def read(kind,path,depth=0):
        nonlocal offset
        if depth>32:raise ValueError(f'{path}:nesting-limit')
        start=offset
        if isinstance(kind,list):
            count=scalar('i',path+'.count')
            if count==-1:return None
            if count<0 or count>len(data)-offset:raise ValueError(f'{path}:invalid-count={count}')
            return [read(kind[1],f'{path}[{i}]',depth+1)for i in range(count)]
        if kind in('long','int'):kind={'long':'i64','int':'i32'}[kind]
        if kind in('bool','i32','u32','i64','float'):
            value=scalar({'bool':'B','i32':'i','u32':'I','i64':'q','float':'f'}[kind],path)
            if kind=='bool'and value not in(0,1):raise ValueError(f'{path}:invalid-bool={value}')
            if kind=='float'and not math.isfinite(value):raise ValueError(f'{path}:nonfinite-float')
            return bool(value)if kind=='bool'else value
        if kind=='string':return strings.resolve(scalar('i',path+'.poolIndex'))
        if kind in('vector3','raw16'):return take(12 if kind=='vector3'else 16,path).hex()
        if kind==layout['unionBase']:
            tag=scalar('B',path+'.tag')
            if tag==255:return None
            if str(tag)not in layout['union']:raise ValueError(f'{path}:unsupported-union-tag={tag}')
            row=read(layout['union'][str(tag)],path,depth+1)
            if row is None:raise ValueError(f'{path}:null-positive-union-payload')
            row.update(sourceOffset=start,unionTag=tag,unionTagHex=f'0x{tag:04x}',unionTagEncoding='memorypack-u8',byteLength=offset-start)
            return row
        if kind==layout['curve']:
            marker=scalar('B',path+'.memberCount')
            if marker==255:return None
            if marker!=3:raise ValueError(f'{path}:curve-member-count={marker}:expected=3')
            pre=read('i32',path+'.preWrapMode');post=read('i32',path+'.postWrapMode');count=scalar('i',path+'.keys.count')
            if count < -1 or count>(len(data)-offset)//28:raise ValueError(f'{path}:invalid-key-count={count}')
            keys=[take(28,f'{path}.keys[{i}]').hex()for i in range(max(0,count))]
            return dict(preWrapMode=pre,postWrapMode=post,keys=None if count==-1 else keys)
        fields=layout['records'].get(kind)
        if fields is None:raise ValueError(f'{path}:unsupported-record={kind}')
        marker=scalar('B',path+'.memberCount')
        if marker==255:return None
        if marker!=len(fields):raise ValueError(f'{path}:member-count={marker}:expected={len(fields)}')
        row={name:read(wire,path+'.'+name,depth+1)for name,wire in fields}
        row.update(sourceOffset=start,memberCount=marker,endOffset=offset,byteLength=offset-start)
        return row
    root=read(layout['root'],'ModelView')
    if root is None:raise ValueError('ModelView:null-root')
    if offset!=len(data):raise ValueError(f'ModelView:trailing-bytes@{offset}')
    audio=[];layers=states=behaviors=0;models=root['modelAnimatorDatas']or[]
    for mi,model in enumerate(models):
        if model is None:raise ValueError(f'ModelView.modelAnimatorDatas[{mi}]:null-owner')
        for li,layer in enumerate(model['layerFsmDatas']or[]):
            if layer is None:raise ValueError(f'ModelView.layers[{li}]:null-owner')
            layers+=1
            for si,state in enumerate(layer['stateDatas']or[]):
                if state is None:raise ValueError(f'ModelView.states[{si}]:null-owner')
                states+=1
                for bi,row in enumerate(state['behaviors']or[]):
                    behaviors+=1
                    if row is None or str(row['unionTag'])not in layout['audioKinds']:continue
                    row=dict(row)
                    row.update(behaviorKind=layout['audioKinds'][str(row['unionTag'])],behaviorType=row.pop('type'),modelAnimatorIndex=mi,modelAnimatorName=model['modelName']or'',layerIndex=li,layerFsmIndex=layer['index'],layerName=layer['layerName']or'',stateIndex=si,stateName=state['stateName']or'',stateType=state['stateType'],behaviorIndex=bi,modelId=root['modelId']or'')
                    if 'behaviourType'in row:row['rtpcBehaviourType']=row.pop('behaviourType')
                    audio.append(row)
    return dict(storedGraph=root,bytesConsumed=offset,memberCount=root['memberCount'],modelId=root['modelId']or'',preTickAnimator=root['preTickAnimator'],modelAnimatorCount=len(models),layerCount=layers,stateCount=states,behaviorCount=behaviors,audioBehaviorCount=len(audio),audioBehaviors=audio,endOffset=offset)
