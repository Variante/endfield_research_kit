"""Complete stored manual Lua values under a fresh source capability."""
import json
import struct
from scripts.game_data.memorypack import levelscript_manual_action_sources as native


def need(check,condition,detail=''):
    if not condition:raise ValueError('manualLuaValues.'+check+':'+str(detail)[:1200])


def _inline(reader,field):
    at=reader.pos
    need('complete-signed-UTF8-length',at+4<=reader.limit,field)
    count=struct.unpack_from('<i',reader.data,at)[0]
    need('bounded-nullable-UTF8-span',-1<=count<=reader.limit-at-4,(field,count))
    raw=reader.take(4+max(count,0),'source-owned-manual-UTF8:'+field)
    try:value=None if count==-1 else raw[4:].decode('utf-8','strict')
    except UnicodeDecodeError as error:raise ValueError('manualLuaValues.invalid-UTF8:'+field)from error
    return value,dict(wireEncoding='nullable-int32-byte-length-valid-utf8',rawHex=raw.hex(),byteLength=count)


def _record(reader,at,fields,value,mode):
    key=(at,reader.pos)
    need('one-complete-manual-object-span',key not in reader.objects)
    reader.objects[key]=dict(typeName=native.TYPE,fields=fields,value=value,serialization=mode)
    reader.field_count+=len(fields)


def read(reader,cap):
    reader.graph._active()
    need('own-current-full-source',cap.get('schema')==native.SCHEMA and cap.get('nativeInputs')==reader.graph.pins
        and cap.get('status')=='validated-conditional-manual-Lua-action'
        and cap.get('wholeStoredGrammarAdmitted')is True and cap.get('memberCount')==9
        and cap.get('manualMemberCount')==7 and len(cap.get('outerFields',[]))==9
        and len(cap.get('manualFields',[]))==7 and cap.get('manualOriginalFormatterProved')is True
        and cap.get('rootConcreteCallbackAndOriginalGetterProved')is True)
    reader._charge();start=reader.pos
    if reader.peek()==255:
        reader.take(1,'source-owned-null-manual-action-wrapper');return None
    reader.header(9);result={};extents=[]
    reads=next(p['reads']for p in cap['proof']['outerPrograms']if p['existing']and not p['ff'])
    need('complete-source-owned-outer-read-order',len(reads)==9)
    for field,source in zip(cap['outerFields'][:8],reads[:8],strict=True):
        name=field['fieldName'];typ=field['declaredType'];at=reader.pos
        if source['kind']=='pooledString':
            need('own-pooled-UID-field',typ=='string');value=reader._value_string()
        else:
            width=1 if source['kind']=='rawByte'else 4
            need('own-primitive-source-kind',source['kind']in('rawByte','int32'))
            value=reader.layouts.read(typ,reader.take(width,'source-owned-manual-outer-field:'+name))
        result[name]=value;extents.append(dict(fieldName=name,start=at,end=reader.pos))
    at=reader.pos;manual_start=at
    if reader.peek()==255:
        reader.take(1,'source-owned-null-manual-Original');manual=None
    else:
        reader._charge();reader.header(7);manual={};inside=[]
        for field in cap['manualFields']:
            name=field['fieldName'];kind=field['wireKind'];begin=reader.pos
            if kind in('int32','raw-byte'):
                value=reader.layouts.read(field['declaredType'],reader.take(4 if kind=='int32'else 1,'manual-field:'+name))
            elif kind=='utf8':value,_wire=_inline(reader,name)
            elif kind=='pooled-string-Param':
                need('own-independent-String-Param',field['declaredType']==native.PARAM)
                value=reader._parameter(dict(typeName=native.PARAM,proof=cap['paramSource'],capability=cap['paramCapability']))
            elif kind=='serialized-json-Param':
                text,wire=_inline(reader,name)
                def invalid_constant(value):raise ValueError('manualLuaValues.nonstandard-JSON-number:'+value)
                parsed=None if text is None else json.loads(text,parse_constant=invalid_constant,
                    object_pairs_hook=lambda pairs:{'$objectPairs':pairs})
                value=dict(serializedJson=text,jsonSyntax=parsed,wire=wire,runtimeParamObjectProved=False)
            else:raise ValueError('manualLuaValues.unproved-field:'+kind)
            manual[name]=value;inside.append(dict(fieldName=name,start=begin,end=reader.pos))
        _record(reader,manual_start,inside,manual,'manual-Original-seven-fields')
    need('own-whole-Original-assignment-field',cap['outerFields'][8]==dict(fieldName='manualValue',declaredType=native.TYPE))
    result['manualValue']=manual;extents.append(dict(fieldName='manualValue',start=at,end=reader.pos))
    _record(reader,start,extents,result,'generated-wrapper-nine-fields')
    return result
