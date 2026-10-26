"""Pooled NPC values read in the owning native gate's current field order."""
from scripts.game_data.string_pool import StringPool,StringPoolDecodeError
from scripts.game_data.codecs.leveldata.memorypack import read_bool,read_f32,read_i32,read_i64,read_u64


class LevelNpcCodecError(ValueError):
    def __init__(self,field,offset=None,expected=None,actual=None):
        self.diagnostic=dict(field=field,offset=offset,expected=expected,actual=actual)
        super().__init__(f'{field}: offset={offset} expected={str(expected)[:180]} actual={str(actual)[:180]}')


class _Reader:
    def __init__(self,strings,layout):
        if not isinstance(strings,StringPool):raise LevelNpcCodecError('matching-StringPool-required',None,'StringPool',type(strings).__name__)
        self.strings,self.layout=strings,layout

    def number(self,data,cursor,field,read):
        value=read(data,cursor)
        if value is None:raise LevelNpcCodecError(field,cursor,'complete current value','invalid or truncated')
        return value

    def member(self,data,cursor,field,count,*,nullable=False):
        actual=data[cursor]if 0<=cursor<len(data)else None
        if actual==255 and nullable:return False,cursor+1
        if actual!=count:raise LevelNpcCodecError(field,cursor,count,actual)
        return True,cursor+1

    def string(self,data,cursor,field):
        index,end=self.number(data,cursor,field,read_i32)
        try:return self.strings.resolve(index),end
        except StringPoolDecodeError as error:raise LevelNpcCodecError(field,cursor,'matching pool index',str(error))from error

    def items(self,data,cursor,field,plan):
        start=cursor;count,cursor=self.number(data,cursor,field+'.count',read_i32);limit=plan['countLimit']
        if count < -1 or count>limit or count>len(data)-cursor:raise LevelNpcCodecError(field,start,f'new collection count -1..{limit}',count)
        values=[]
        for i in range(max(count,0)):
            value,cursor=self.value(data,cursor,f'{field}[{i}]',plan['element']);values.append(value)
        return dict(startOffset=start,endOffset=cursor,count=count,value=None if count==-1 else values),cursor

    def record(self,data,cursor,field,name,*,nullable=False):
        plan=self.layout['records'][name];present,cursor=self.member(data,cursor,field,len(plan),nullable=nullable)
        if not present:return None,cursor
        value={}
        for item in plan:value[item['name']],cursor=self.value(data,cursor,field+'.'+item['name'],item)
        if name==self.layout['tagType']:return value['tagId'],cursor
        return value,cursor

    def ai_dictionary(self,data,cursor,field):
        start=cursor;present,cursor=self.member(data,cursor,field,1,nullable=True)
        if not present:return dict(startOffset=start,endOffset=cursor,count=-1,value=None),cursor
        count,cursor=self.number(data,cursor,field+'.count',read_i32)
        if count not in self.layout['aiDictionaryCounts']:raise LevelNpcCodecError(field,cursor-4,self.layout['aiDictionaryCounts'],count)
        values=[];keys=set()
        for i in range(count):
            key,cursor=self.string(data,cursor,f'{field}[{i}].key')
            if key is None or key in keys:raise LevelNpcCodecError(field,cursor-4,'nonnull unique dictionary key',key)
            keys.add(key);value,cursor=self.record(data,cursor,f'{field}[{i}].value',self.layout['aiType']);values.append(dict(key=key,value=value))
        return dict(startOffset=start,endOffset=cursor,count=count,value=values),cursor

    def value(self,data,cursor,field,plan):
        wire=plan['wire']
        readers=dict(bool=read_bool,i32=read_i32,i64=read_i64,u64=read_u64,f32=read_f32)
        if wire in readers:
            value,end=self.number(data,cursor,field,readers[wire]);return(str(value)if wire=='u64'else value),end
        if wire=='pool':return self.string(data,cursor,field)
        if wire=='vector3':
            vector={}
            for axis in'xyz':vector[axis],cursor=self.number(data,cursor,field+'.'+axis,read_f32)
            return vector,cursor
        if wire=='null':
            present,end=self.member(data,cursor,field,255)
            return None,end
        if wire=='items':return self.items(data,cursor,field,plan)
        if wire=='record':return self.record(data,cursor,field,plan['type'],nullable=plan.get('nullable',False))
        if wire=='ai-dictionary':return self.ai_dictionary(data,cursor,field)
        raise LevelNpcCodecError(field,cursor,'reviewed current native wire',wire)

    def row(self,data,cursor,index=0):
        if not isinstance(data,bytes):raise LevelNpcCodecError('immutable-source-required',cursor,'bytes',type(data).__name__)
        start=cursor;field=f'npcs[{index}]';_,cursor=self.member(data,cursor,field,self.layout['memberCount']);groups={};starts={};ends={}
        for item in self.layout['root']:
            group=item['group'];starts.setdefault(group,cursor);value,cursor=self.value(data,cursor,field+'.'+item['name'],item);groups.setdefault(group,{})[item['name']]=value;ends[group]=cursor
        entity=dict(startOffset=starts['levelEntityData'],endOffset=ends['levelEntityData'],fields=groups.pop('levelEntityData'))
        return dict(indexInCollection=index,startOffset=start,endOffset=cursor,memberCount=self.layout['memberCount'],levelEntityData=entity,**groups),cursor


def decode_npc_runtime_proxy_at(data,cursor,index=0,*,strings,game_root=None,gameassembly=None,metadata=None):
    from scripts.game_data.memorypack.npc_runtime import npc_runtime_decoder
    with npc_runtime_decoder(strings=strings,game_root=game_root,gameassembly=gameassembly,metadata=metadata)as decode:return decode(data,cursor,index)


def decode_npc_runtime_proxy_row(data,*,strings,game_root=None,gameassembly=None,metadata=None):
    row,cursor=decode_npc_runtime_proxy_at(data,0,strings=strings,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
    if cursor!=len(data):raise LevelNpcCodecError('npc-row-eof',cursor,len(data),cursor)
    return row


def decode_npc_runtime_proxy_list(data,offset,*,strings,game_root=None,gameassembly=None,metadata=None):
    from scripts.game_data.memorypack.npc_runtime import npc_runtime_decoder
    with npc_runtime_decoder(strings=strings,game_root=game_root,gameassembly=gameassembly,metadata=metadata)as decode:return decode.collection(data,offset)
