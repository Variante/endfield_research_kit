"""Finite BuffPtr constant framing; canonical outer Param is a separate gate."""
from scripts.game_data.memorypack.levelscript_action_buff_param_sources import VALUE,LIST,validate_constant


def read_constant(reader,field,cap,value):
    validate_constant(cap,value)
    if value==LIST:
        count=reader.number('<i',field+'.count')
        if count!=-1:raise ValueError(field+':only-null-Buff-list-source-proved:actual='+str(count))
        return None
    marker=reader.number('<B',field+'.memberCount');uid=0;obj=None
    if marker==1:
        nested=reader.number('<B',field+'.ptr.memberCount')
        if nested==2:
            uid=reader.number('<I',field+'.ptr.cachedUid')
            child=reader.number('<B',field+'.ptr.obj.memberCount')
            if child==1:
                count=reader.number('<i',field+'.ptr.obj.modifiedBBKeys.count')
                if not -1<=count<=cap['objectListMaxCount']:
                    raise ValueError(field+':Buff-modifiedBBKeys-count-limit:actual='+str(count))
                reader.need(max(count,0)*4,field+'.ptr.obj.modifiedBBKeys.elements')
                keys=None if count==-1 else[reader.string(field+'.ptr.obj.modifiedBBKeys['+str(i)+']')for i in range(count)]
                obj=dict(modifiedBBKeys=keys)
            elif child!=255:raise ValueError(field+':Buff-member-count:actual='+str(child))
        elif nested!=255:raise ValueError(field+':ObjectPtr-Buff-member-count:actual='+str(nested))
    elif marker!=255:raise ValueError(field+':BuffPtr-member-count:actual='+str(marker))
    return dict(ptr=dict(cachedUid=uid,obj=obj))
