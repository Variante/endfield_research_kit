"""Bounded per-image raw instruction rows; never caches native proof results."""
from collections import OrderedDict
import copy
from types import CodeType, FunctionType

MAX_ENTRIES=512
MAX_ROWS=32768
MAX_RAW_BYTES=4*1024*1024


def _copy_raw_rows(value,memo=None):
    """Fast exact builtin row copies, with standard exotic-type fallback.

    Native parser leaves are immutable and normally absent from the memo.
    Once an exotic deepcopy hook runs, scalar memo substitutions remain
    observable exactly as in deepcopy. Tuples and subclasses use that fallback.
    """
    atomic=(str,bytes,int,float,bool,type(None))
    if memo is None:memo={}
    exotic=bool(memo)
    def clone(item):
        nonlocal exotic
        kind=type(item)
        if kind in atomic:
            if exotic and id(item)in memo:return memo[id(item)]
            return item
        identity=id(item)
        if identity in memo:return memo[identity]
        if kind is list:
            result=[];memo[identity]=result
            result.extend(clone(child)for child in item)
            copy._keep_alive(item,memo)
            return result
        if kind is dict:
            result={};memo[identity]=result
            for key,child in item.items():result[clone(key)]=clone(child)
            copy._keep_alive(item,memo)
            return result
        exotic=True
        return copy.deepcopy(item,memo)
    return clone(value)


def _names(code):
    result=set(code.co_names)
    for value in code.co_consts:
        if isinstance(value,CodeType):result.update(_names(value))
    return result


class _DecoderIdentity:
    """Observe implementation references, including nested fallback functions."""
    def __init__(self,decoder,mapper):
        self.decoder=decoder;self.mapper=mapper;self.bindings=[];self.functions=[]
        pending=[decoder];seen=set()
        for name in ('decode_one_x64','decode_x64_subset'):
            value=getattr(mapper,name,None);self.bindings.append((mapper,name,value,False))
            if isinstance(value,FunctionType):pending.append(value)
        while pending:
            function=pending.pop()
            if not isinstance(function,FunctionType)or id(function)in seen:continue
            seen.add(id(function));self.functions.append((function,function.__code__,function.__defaults__,function.__kwdefaults__))
            for name in sorted(_names(function.__code__)):
                value=function.__globals__.get(name)
                if isinstance(value,FunctionType):
                    self.bindings.append((function.__globals__,name,value,True));pending.append(value)

    def current(self,decoder,mapper):
        if decoder is not self.decoder or mapper is not self.mapper:return False
        for function,code,defaults,kwdefaults in self.functions:
            if function.__code__ is not code or function.__defaults__ is not defaults or function.__kwdefaults__ is not kwdefaults:return False
        for owner,name,value,mapping in self.bindings:
            actual=owner.get(name)if mapping else getattr(owner,name,None)
            if actual is not value:return False
        return True


def _call(lane,decoder,mapper,raw,start,kwargs):
    return decoder(mapper,raw,start,**kwargs)if lane=='string-source'else decoder(raw,start,**kwargs)


class _RawInstructionIndex:
    def __init__(self,image):
        self.image=image;self.pe=image.pe;self.buffer=image.pe.buf;self.mapper=image.mapper
        self.entries=OrderedDict();self.guards={};self.rows=0;self.raw_bytes=0
        self.hits=self.misses=self.bypasses=self.evictions=0

    def statistics(self):
        return dict(hits=self.hits,misses=self.misses,bypasses=self.bypasses,evictions=self.evictions,
            entries=len(self.entries),rows=self.rows,rawBytes=self.raw_bytes)

    def decode(self,lane,decoder,raw,start,kwargs):
        guard=self.guards.get(lane)
        if guard is None:self.guards[lane]=guard=_DecoderIdentity(decoder,self.mapper)
        elif not guard.current(decoder,self.mapper):
            # Never reuse stale rows after a decoder override. A fresh index on
            # another opened image may accept that image's own implementation.
            self.bypasses+=1;return _call(lane,decoder,self.mapper,raw,start,kwargs)
        key=(lane,start,raw)
        previous=self.entries.get(key)
        if previous is not None:
            self.hits+=1;self.entries.move_to_end(key);return _copy_raw_rows(previous)
        self.misses+=1;rows=_call(lane,decoder,self.mapper,raw,start,kwargs)
        if not guard.current(decoder,self.mapper):
            self.bypasses+=1;return rows
        if type(rows)is not list or len(rows)>MAX_ROWS or len(raw)>MAX_RAW_BYTES:
            self.bypasses+=1;return rows
        while self.entries and(len(self.entries)>=MAX_ENTRIES or self.rows+len(rows)>MAX_ROWS
                or self.raw_bytes+len(raw)>MAX_RAW_BYTES):
            old_key,old_rows=self.entries.popitem(last=False)
            self.rows-=len(old_rows);self.raw_bytes-=len(old_key[2]);self.evictions+=1
        stored=_copy_raw_rows(rows);self.entries[key]=stored
        self.rows+=len(stored);self.raw_bytes+=len(raw)
        return rows


def decode_image_rows(image,lane,decoder,raw,start,*,stop_offset=None):
    """Share only exact raw parses, with independent mutable rows per caller.

    Ownership/unwind selection, byte-window hashing, source and publication
    gates remain at every caller. The lanes are deliberately distinct.
    """
    from scripts.game_data.il2cpp.native_image import NativeImage
    if lane not in ('string-source','mapper-subset'):raise ValueError('rawInstructionIndex.unknown-lane')
    kwargs={}if stop_offset is None else {'stop_offset':stop_offset}
    # These are exactly the only two invocation shapes cached by this helper.
    selected=(lane=='string-source'and stop_offset is None or lane=='mapper-subset'and type(stop_offset)is int and stop_offset==len(raw))
    if(type(image)is not NativeImage or type(getattr(image.pe,'buf',None))is not bytes
            or type(raw)is not bytes or type(start)is not int or not selected):
        return _call(lane,decoder,image.mapper,raw,start,kwargs)
    index=getattr(image,'_raw_instruction_index',None)
    if index is None:image._raw_instruction_index=index=_RawInstructionIndex(image)
    if(index.image is not image or index.pe is not image.pe or index.buffer is not image.pe.buf
            or index.mapper is not image.mapper):
        return _call(lane,decoder,image.mapper,raw,start,kwargs)
    return index.decode(lane,decoder,raw,start,kwargs)
