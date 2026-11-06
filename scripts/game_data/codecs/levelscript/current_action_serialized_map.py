"""ActionSerializedMap under an active current native/pool operation.

The template source owns the exact three typed reference-list callers. Each
element uses the existing source-gated current union reader, including freshly
compiled missing routes. No historical declaration-only map reader is used.
"""
import struct

from scripts.game_data.memorypack.levelscript_current_source import require_current_owner

FIELDS=(('actionList','ActionBase','Beyond.Gameplay.Actions.ActionBase'),
        ('getterList','GetterBase','Beyond.Gameplay.Actions.PureGetter'),
        ('headerList','ActionHeader','Beyond.Gameplay.Actions.ActionHeader'))


def need(check,condition,detail=''):
    if not condition:raise ValueError('currentActionSerializedMap.'+check+':'+str(detail)[:1000])


def decode(data,offset,*,strings,current_owner,budget=None,native_node_decoder=None):
    from scripts.game_data.codecs.levelscript.action_map import decode_reviewed_node
    require_current_owner(current_owner,strings=strings)
    cap=current_owner.require_template(strings=strings)
    need('same-current-template-native-inputs',cap.get('nativeInputs')==current_owner.proof['nativeInputs'])
    lists=cap.get('actionMapLists',{})
    need('three-exact-current-list-sources',set(lists)=={field for field,_,_ in FIELDS})
    for field,_,element in FIELDS:
        source=lists[field]
        need('own-list-count-and-nominal:'+field,source.get('elementType')==element
            and source.get('typeName')=='System.Collections.Generic.List`1<'+element+'>'
            and source.get('headerBytes')==4 and source.get('countLimit')==4096
            and source.get('counts')=='-1-or-nonnegative'
            and source.get('actualCallbackEqualsProvedChildRequired')is True)
    need('literal-complete-map-header',type(offset)is int and 0<=offset<len(data))
    start=offset;marker=data[offset];offset+=1
    if marker==255:return None,offset
    need('own-three-field-map-header',marker==3,dict(offset=start,actual=marker))
    if budget is None:budget={'remaining':65536}
    need('shared-finite-node-budget',type(budget)is dict and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 1<=budget['remaining']<=65536)
    budget['remaining']-=1;result={};counts={};ranges={}
    for field,family,_ in FIELDS:
        at=offset
        need('complete-signed-count:'+field,offset+4<=len(data))
        count=struct.unpack_from('<i',data,offset)[0]
        need('bounded-own-list-count:'+field,-1<=count<=4096,count)
        need('bounded-complete-minimum-node-bytes:'+field,max(count,0)<=len(data)-offset-4
            and max(count,0)<=budget['remaining'])
        offset+=4;budget['remaining']-=max(count,0);values=None if count==-1 else[]
        need('fresh-concrete-action-program-required',count<=0 or callable(native_node_decoder),field)
        for index in range(max(count,0)):
            before=offset
            value,offset=decode_reviewed_node(data,offset,family,strings=strings,
                game_root=current_owner.game_root,current_owner=current_owner,**current_owner.leaves)
            need('complete-forward-current-union-node',type(offset)is int and before<offset<=len(data),
                dict(field=field,index=index,before=before,after=offset))
            # Some maintained reviewed projections normalize booleans/floats.
            # Keep their complete certified wire span beside the named values.
            values.append(dict(value)if isinstance(value,dict)else dict(value=value))
            values[-1]['serializedRawHex']=bytes(data[before:offset]).hex()
            native_value,native_end=native_node_decoder(data,before,family,values[-1])
            need('independent-native-node-extent',native_end==offset,dict(field=field,index=index,
                currentCodecEnd=offset,nativeSourceEnd=native_end))
            values[-1]['currentNativeValue']=native_value
        result[field]=values;counts[field]=count;ranges[field]=[at,offset]
    return dict(sourceOffset=start,endOffset=offset,memberCount=3,fields=result,
        rawListCounts=counts,fieldRanges=ranges,completeCurrentMap=True,
        runtimeExecutionProved=False),offset
