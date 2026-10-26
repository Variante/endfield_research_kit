"""Pure current pooled child cursors, reachable only through an active owner.

The owning operation supplies selected native/source/pool capabilities. This
module gives no owner, source provenance or physical-EOF claim by itself.
"""
from scripts.game_data.codecs.levelscript.pooled_interactives import Reader as SparseReader
from scripts.game_data.codecs.levelscript.param_graph import ParamGraphDecodeError

LIMIT=16384


class Reader(SparseReader):
    def __init__(self,data,offset,strings,field,*,condition_cap=None):
        super().__init__(data,offset,strings,field);self.condition_cap=condition_cap
    def condition(self,field):
        if self.condition_cap is None:return super().condition(field)
        from scripts.game_data.codecs.leveldata.current_condition import read,validate_parent
        validate_parent(self.condition_cap,'Beyond.Gameplay.LevelInteractiveData','progressLockCondition')
        return read(self,field,self.condition_cap)
    def count(self,field):
        at=self.offset;count=self.number('<i',field+'.count')
        if not -1<=count<=LIMIT:
            raise ParamGraphDecodeError(f'{field}:count-limit,offset={at},actual={count},limit={LIMIT}')
        return count
    def null_ints(self,field):
        start=self.offset;count=self.count(field)
        if count==-1:return dict(status='null',count=None,values=None,startOffset=start,endOffset=self.offset)
        self.need(count*4,field+'.values')
        values=[self.number('<i',f'{field}[{i}]')for i in range(count)]
        return dict(status='present',count=count,values=values,startOffset=start,endOffset=self.offset)
    def components(self,field):
        start=self.offset;count=self.count(field)
        if count==-1:return dict(status='null',count=None,entries=None,startOffset=start,endOffset=self.offset)
        entries=[];seen=set()
        for i in range(count):
            child=f'{field}[{i}]';key=self.number('<i',child+'.componentType')
            if key in seen:raise ParamGraphDecodeError(f'{child}:duplicate-component-key,offset={self.offset-4},actual={key}')
            seen.add(key);entries.append(dict(componentTypeRaw=key,properties=self.items(child+'.properties',self.key_value)))
        return dict(status='present',count=count,entries=entries,startOffset=start,endOffset=self.offset)


def decode(data,offset,type_name,*,strings,condition_cap=None):
    reader=Reader(data,offset,strings,type_name,condition_cap=condition_cap);start=offset
    if condition_cap is not None:
        from scripts.game_data.codecs.leveldata.current_condition import validate_parent
        validate_parent(condition_cap,'Beyond.Gameplay.LevelInteractiveData','progressLockCondition')
    if type_name=='System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>':
        value=reader.items(type_name,reader.key_value)
        return value,reader.offset
    count=reader.count(type_name)
    if count==-1:return dict(status='null',count=None,values=None,entries=None,
        startOffset=start,endOffset=reader.offset),reader.offset
    values=[];entries=[];seen=set()
    if type_name=='System.Collections.Generic.List`1<ulong>':
        reader.need(count*8,type_name+'.values')
        values=[str(reader.number('<Q',f'{type_name}[{i}]'))for i in range(count)]
    elif type_name=='System.Collections.Generic.Dictionary`2<int,string>':
        for i in range(count):
            key=reader.number('<i',f'{type_name}[{i}].key')
            if key in seen:raise ParamGraphDecodeError(f'{type_name}:duplicate-key,offset={reader.offset-4},actual={key}')
            seen.add(key);value=reader.string(f'{type_name}[{i}].value')
            entries.append(dict(key=key,value=value))
    elif type_name=='System.Collections.Generic.Dictionary`2<uint,Beyond.Gameplay.LevelInteractiveData>':
        for i in range(count):
            key=reader.number('<I',f'interactives[{i}].key')
            if key in seen:raise ParamGraphDecodeError(f'interactives:duplicate-key,offset={reader.offset-4},actual={key}')
            seen.add(key);entries.append(dict(key=key,value=reader.record(f'interactives[{i}].value')))
    else:raise ParamGraphDecodeError('currentLevelScriptCollection:unsupported-closed-type:'+type_name)
    result=dict(status='present',count=count,values=values,entries=entries,startOffset=start,endOffset=reader.offset)
    if condition_cap is not None and type_name=='System.Collections.Generic.Dictionary`2<uint,Beyond.Gameplay.LevelInteractiveData>':
        result['conditionalChildSources']=[dict(typeName=condition_cap['typeName'],admittedRouteTags=condition_cap['admittedRouteTags'],
            countLimit=condition_cap['countLimit'],nodeLimit=condition_cap['nodeLimit'],depthLimit=condition_cap['depthLimit'],
            actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False)]
    return result,reader.offset
