"""Anonymous current action prefixes: exact supported fixtures and explicit gaps."""
import struct
import unittest

from scripts.game_data.memorypack.buff_actions import FrameError, Reader, Unsupported, event_prefix, sequence_frame


def sequence(*actions,tail=b'\x00\x00'):
    return b'\x03'+struct.pack('<i',len(actions))+b''.join(actions)+tail


def action(*branches):
    return b'\xc9\x08'+bytes(14)+b''.join(branches or [sequence()]*3)


def prefix(seq):
    return b'\x1e'+struct.pack('<i',1)+b'\x02'+bytes(4)+struct.pack('<i',1)+seq


def payload(value):
    return struct.pack('<i',-1 if value is None else len(value))+(value or b'')


def pair(a=b'',b=b'',flag=0):
    return b'\x03'+payload(a)+bytes([flag])+payload(b)


def finder14d(items=(b'wire',None),query_items=(0,0xffffffff)):
    return (b'\x03'+struct.pack('<i',-1 if items is None else len(items))+
            b''.join(payload(v) for v in items or ())+b'\xff'*4+
            b'\x02'+b'\x80'*4+struct.pack('<i',-1 if query_items is None else len(query_items))+
            b''.join(struct.pack('<I',v) for v in query_items or ()))


def tag14d(first=b'\xff',second=b'\xff',last=b'\xff'):
    return b'\xfa\x4d\x01\x09\xfe'+b'\xff'*12+first+b'\x80'+b'\xfe'*4+second+last


def tag42(first=b'\xff',second=b'\xff',bits=0x7fc00000):
    return b'\x42\x0a\xfe'+b'\xff'*12+b'\x80'+struct.pack('<I',bits)+b'\xfe\xff'+first+second


def tag27(first=b'\xff',middle=b'\xff',last=b'\xff'):
    return b'\x27\x0a\xfe'+b'\xff'*12+first+b'\x80\xfe'+middle+b'\xff'+last


def input95(items=(),identifier=b'\xff'):
    return (b'\x03\xfe'+struct.pack('<i',-1 if items is None else len(items))+
            b''.join(items or ())+identifier)


def tag95(items=(),scalar=b'\xff',last=b'\xff'):
    return (b'\x95\x08\xfe'+b'\xff'*12+b'\x80'+scalar+
            struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+last)


def tag74(items=()):
    return (b'\x74\x05\xfe'+b'\xff'*12+struct.pack('<i',-1 if items is None else len(items))+
            b''.join(struct.pack('<I',v) for v in items or ()))


def tag16d(first=b'\xff',second=b'\xff',bits=0xffffffff):
    return b'\xfa\x6d\x01\x08\xfe'+b'\xff'*12+struct.pack('<I',bits)+b'\x80'+first+second


def tag160(nested=b'\xff',first=0xffffffff,second=0x80000000):
    return b'\xfa\x60\x01\x0a\xfe'+b'\xff'*12+b'\xfe\x80'+struct.pack('<I',first)+b'\xff'+struct.pack('<I',second)+nested


def tag89(first=b'',second=b''):
    return b'\x89\x06\xfe'+b'\xff'*12+payload(first)+payload(second)


def tag51(first=b'\xff',second=b'\xff'):
    return b'\x51\x06\xfe'+b'\xff'*12+first+second


def tag03(items=(),scalar=b'\xff',last=255):
    return b'\x03\x09\xfe'+b'\xff'*12+b'\x80'+scalar+b'\xfe'+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+bytes([last])


def tag142(values=(None,b'',b'wire',b'\xff\x00',b'last'),nested=b'\xff',last=0xffffffff):
    return b'\xfa\x42\x01\x0b\xfe'+b'\xff'*12+payload(values[0])+nested+b''.join(payload(v) for v in values[1:])+struct.pack('<I',last)


def option176(nested=b'\xff',scalar=b'\xff'):
    return b'\x02'+nested+scalar


def tag176(items=(),scalar=b'\xff'):
    return (b'\xfa\x76\x01\x07\xfe'+b'\xff'*12+b'\x80'+scalar+
            struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ()))


def tag98(first=None,curve=b'\xff',scalar=b'\xff',last=b'wire'):
    return b'\x98\x09\xfe'+b'\xff'*12+payload(first)+curve+scalar+payload(last)+b'\xff'


def tag140(value=None,first=b'\xff',second=b'\xff'):
    return b'\xfa\x40\x01\x07\xfe'+b'\xff'*12+payload(value)+first+second


def tag13f(value=None,nested=b'\xff',bits=0xffffffff):
    return b'\xfa\x3f\x01\x07\xfe'+b'\xff'*12+payload(value)+nested+struct.pack('<I',bits)


def tag151(nested=b'\xff',first=b'\xff',last=b'\xff'):
    return b'\xfa\x51\x01\x08\xfe'+b'\xff'*12+nested+first+last+b'\x80'


def tag115(nested=b'\xff',first=None,last=b'wire'):
    return (b'\xfa\x15\x01\x10\xfe'+b'\xff'*12+payload(first)+b'\x80'*16+
            b'\xff\xfe'+nested+b'\xff'*8+payload(last)+b'\x80')


def tag2b(nested=b'\xff'):
    return b'\x2b\x05\xfe'+b'\xff'*12+nested


def tag0b(items=(),first=b'\xff',second=b'\xff',last=255):
    return (b'\x0b\x08\xfe'+b'\xff'*12+first+second+
            struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+bytes([last]))


def tagbb(first=b'\xff',second=b'\xff'):
    return b'\xbb\x06\xfe'+b'\xff'*12+first+second


def tag90(first=b'\xff',second=b'\xff',last=b'\xff'):
    return b'\x90\x08\xfe'+b'\xff'*12+first+second+b'\x80'+last


def taga9(profiles=None):
    t,u,c,d,i,a,b,e,f=profiles or (b'\xff',)*9
    return (b'\xa9\x1c\xfe'+b'\xff'*12+b'\x80'+t+b'\xfe\xff'+b'\x80'*4+u+c+
            b'\xff\x80'+d+b'\xfe'+b'\xff'*4+b'\x80'+i+b'\x80'*4+b'\xff'+a+
            b'\x80\xfe\xff'+b+b'\xfe'+e+f)


def query41(items=()):
    return b'\x02'+b'\xff'*4+struct.pack('<i',-1 if items is None else len(items))+b''.join(struct.pack('<I',v) for v in items or ())


def tag41(value=b'wire',query=b'\xff'):
    return b'\x41\x06\xfe'+b'\xff'*12+payload(value)+query


def tag174(first=b'\xff',second=b'\xff',value=b'wire',third=b'\xff',nested=b'\xff',last=255):
    return b'\xfa\x74\x01\x0b\xfe'+b'\xff'*12+first+second+payload(value)+third+b'\x80'*4+nested+bytes([last])


def tag84(nested=b'\xff',bits=0xffffffff):
    return b'\x84\x06\xfe'+b'\xff'*12+nested+struct.pack('<I',bits)


def tag13b(value=b'wire',bits=0xffffffff):
    return b'\xfa\x3b\x01\x06\xfe'+b'\xff'*12+payload(value)+struct.pack('<I',bits)


def tag5e(value=0xffffffff):
    return b'\x5e\x05\xfe'+b'\xff'*12+struct.pack('<I',value)


def tag06(value=0xffffffff):
    return b'\x06\x05\xfe'+b'\xff'*12+struct.pack('<I',value)


def scalar_flag(value=b'wire',last=255):
    return b'\x04'+payload(value)+b'\x80'+b'\xff'*4+bytes([last])


def tag1c(first=b'\xff',child=b'\xff',scalars=None,direction=b'\xff',second=b'\xff'):
    a,b,c,d=scalars or (b'\xff',)*4
    return b'\x1c\x0f\xfe'+b'\xff'*12+first+child+a+direction+b+b'\x80'*4+b'\xfe'+c+second+b'\xff'+d


def tag126(nested=b'\xff'):
    return b'\xfa\x26\x01\x05\xfe'+b'\xff'*12+nested


def tag60(nested=b'\xff',value=0xffffffff):
    return b'\x60\x06\xfe'+b'\xff'*12+struct.pack('<I',value)+nested


def tagd4(first=b'\xff',second=b'\xff',raw=0x7fc00000,last=0xffffffff):
    return b'\xd4\x08\xfe'+b'\xff'*12+first+second+struct.pack('<II',raw,last)


def tag132(first=b'',second=b''):
    return b'\xfa\x32\x01\x06\xfe'+b'\xff'*12+payload(first)+payload(second)


def tag171(first=b'\xff',second=b'\xff',value=b'',third=b'\xff',nested=b'\xff',last=255):
    return b'\xfa\x71\x01\x0d\xfe'+b'\xff'*16+first+second+payload(value)+third+b'\x80'*8+nested+bytes([last])


def tag3f(nested=b'\xff',value=b'wire'):
    return b'\x3f\x07\xfe'+b'\xff'*16+nested+payload(value)


def tag61(nested=b'\xff',value=b'wire'):
    return b'\x61\x0a\xfe'+b'\xff'*12+nested+b'\x80'*4+b'\xff\xfe'+b'\x01'*4+payload(value)


def tagea(items=(),value=b'wire'):
    return (b'\xea\x07\xfe'+b'\xff'*12+b'\x80'+payload(value)+
            struct.pack('<i',-1 if items is None else len(items))+
            (b'' if items is None else b''.join(items)))


def tag35(first=b'\xff',second=b'\xff',curve=b'\xff',direction_value=b'\xff',last=b'\xff'):
    return (b'\x35\x0f\xfe'+b'\xff'*12+first+b'\xfe\x80'+second+curve+
            b'\xff'+direction_value+b'\xfe'+b'\x80'*8+last)


def tag7e(first=b'\xff',second=b'\xff'):
    return b'\x7e\x06\xfe'+b'\xff'*12+first+second


def tag16b(first=b'\xff',second=b'\xff'):
    return b'\xfa\x6b\x01\x06\xfe'+b'\xff'*12+first+second


def curve24(items=()):
    return (b'\x03'+struct.pack('<II',0xffffffff,0x80000000)+
            struct.pack('<i',-1 if items is None else len(items))+
            (b'' if items is None else b''.join(items)))


def envelope24(first=b'\xff',second=b'\xff'):
    return b'\x07'+first+b'\xff'*4+second+b'\x80'*4+b'\xfe\xff'+b'\x01'*4


def impulse24(curve=b'\xff',envelope=b'\xff',value=b''):
    return b'\x12'+b'\xff'*4+b'\xfe'+curve+b'\x80'*44+b'\xff'+payload(value)+b'\x01'*4+envelope


def tag24(impulse=b'\xff',nested=b'\xff',value=b''):
    return b'\x24\x0c\xfe'+b'\xff'*12+payload(value)+b'\x80'+impulse+b'\xfe'*4+bytes(range(12))+b'\xfe\xff'+nested


def tag6a(first=(),second=()):
    def values(items):
        return struct.pack('<i',-1 if items is None else len(items))+(b'' if items is None else b''.join(struct.pack('<I',x) for x in items))
    return b'\x6a\x08\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+b'\xff\x80'+values(first)+values(second)


def tagbd(children=None,nested=None):
    return (b'\xbd\x06\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (sequence() if children is None else children)+(target() if nested is None else nested))


def tagde(assignments=(),points=(),nested=None):
    def items(values):
        return struct.pack('<i',-1 if values is None else len(values))+(b'' if values is None else b''.join(values))
    t=target() if nested is None else nested
    return (b'\xde\x25\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            b'\x00\x80\xff'+items(assignments)+b'\x00\xfe\x80\xff'+bytes(4)+t+
            bytes(range(12))+bytes(4)+bytes(range(12,24))+bytes(range(24,36))+bytes(4)+bytes(range(36,48))+bytes(4)+
            b'\xfe\xff'+items(points)+payload(b'first')+payload(None)+t+
            payload(b'')+payload(b'middle')+payload(b'last')+b'\xff'+bytes(4)+t+t+b'\xfe'+struct.pack('<II',0xffffffff,0x80000000))


def tag145(first=None,second=None):
    return (b'\xfa\x45\x01\x06\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (b'\x03'+payload(b'first')+b'\xff'+bytes.fromhex('FFFFFFFF') if first is None else first)+
            (pair(b'second',b'last',128) if second is None else second))


def tagc4(first=b'first',second=b'second',finder=None,nested=None):
    if finder is None:
        finder=b'\x03'+struct.pack('<i',2)+payload(b'finder')+payload(None)+bytes(4)+b'\x02'+struct.pack('<IiII',0xffffffff,2,1,0xffffffff)
    return (b'\xc4\x08\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            payload(first)+finder+payload(second)+(target() if nested is None else nested))


def tag5a(nested=None,value=b'tail'):
    return (b'\x5a\x06\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (pair(b'first',b'second',128) if nested is None else nested)+payload(value))


def tag48(values=(0,0xffffffff),bits=0x80000000):
    return (b'\x48\x06\xfe'+struct.pack('<IIII',0xffffffff,0x80000000,0x7fc00000,bits)+
            struct.pack('<i',-1 if values is None else len(values))+
            b''.join(struct.pack('<I',value) for value in (values or ())))


def tag88(nested=None):
    return (b'\x88\x05\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (scalar_payload() if nested is None else nested))


def tag7a(value=b'wire',bits=0xffffffff):
    return (b'\x7a\x06\xfe'+struct.pack('<IIII',0xffffffff,0x80000000,0x7fc00000,bits)+payload(value))


def tag0a(value=b'wire',nested=None,t=None):
    return (b'\x0a\x07\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            payload(value)+(scalar_payload() if nested is None else nested)+
            (target() if t is None else t))


def tag76(*items):
    return b'\x76\x05'+bytes(13)+struct.pack('<i',len(items))+b''.join(items)


def tag8a(d=b'\xff',sel=b'\xff',values=(None,None,None,None),extended=False,bits=b'\x01\x00\xc0\x7f'):
    return ((b'\xfa\x8a\x00' if extended else b'\x8a')+b'\x13\xfe'+
            struct.pack('<III',0x01020304,0x80000000,0xffffffff)+d+
            b'\x04\x03\x02\x01'+payload(values[0])+b'\x08\x07\x06\x05\x80'+payload(values[1])+sel+
            b'\x0c\x0b\x0a\x09\x10\x0f\x0e\x0d'+payload(values[2])+b'\x14\x13\x12\x11'+payload(values[3])+
            b'\xfe\xff'+bits)


def post1(items=(),wire=b'\x01'):
    return wire+b'\x01'+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())


def post1_shape():
    a=scalar_payload(b'\xffa',128,b'\x04\x03\x02\x01')
    v=b'\x03'+a+b'\xff'+scalar_payload(None,254,b'\x08\x07\x06\x05')
    return (b'\x12'+a+b'\x0c\x0b\x0a\x09'+v+b'\x10\x0f\x0e\x0d\x14\x13\x12\x11\x80'+
            v+b'\xff\x18\x17\x16\x15\xfe\xff'+a+b'\x1c\x1b\x1a\x19\x20\x1f\x1e\x1d'+
            a+b'\x24\x23\x22\x21'+v+b'\xfe')


def tag14b(t=b'\xff',scalar=b'\xff'):
    return b'\xfa\x4b\x01\x06\xfe'+struct.pack('<III',0x01020304,0x80000000,0xffffffff)+t+scalar


def direction():
    return b'\x08\x01\x00'+bytes(4)+b'\x00\xff'+bytes(4)+b'\xff'+bytes(4)


def target(*,selector=b'\x03\xff'+bytes(8),direction_value=None):
    return (b'\x0d'+(direction() if direction_value is None else direction_value)+
            payload(b'center')+b'\x80'+bytes(4)+b'\xfe'+payload(None)+selector+
            bytes(12)+payload(b'\xff\xfe')+payload(b'group')+bytes(4))


def tag80(first=None,second=None):
    return (b'\x80\x06\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (target() if first is None else first)+
            (target(direction_value=b'\xff') if second is None else second))


def tag16e(value=b'wire',first=None,second=None):
    return (b'\xfa\x6e\x01\x0d\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            b'\x80\xfe'+struct.pack('<II',0x80000001,0xffffffff)+payload(value)+bytes(4)+
            (target(selector=b'\x03\x05\x00'+bytes(8)) if first is None else first)+
            (target(direction_value=b'\xff') if second is None else second)+b'\x80')


def scalar_payload(value=b'value',flag=255,bits=b'\x00\x00\xc0\x7f'):
    return b'\x03'+payload(value)+bytes([flag])+bits


def tag4c(wire=b'\x4c',scalar=b'\xff',first=b'\xff',items=(),last=b'\xff'):
    count=struct.pack('<i',-1 if items is None else len(items))
    return (wire+b'\x0c'+b'\xff'*13+scalar+first+b'\x80\xfe'+b'\xff'*4+b'\x80'+
            count+b''.join(payload(v) for v in (items or ()))+last)


def tag7b(t=None,value=None):
    return (b'\x7b\x07\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (target() if t is None else t)+struct.pack('<I',0x80000001)+
            (scalar_payload(b'key',128,b'\xff\xff\xff\xff') if value is None else value))


def tag_ec(*,nested=None,value=None,key=b'key'):
    return (b'\xec\x0a\xfe'+bytes(16)+(target() if nested is None else nested)+
            b'\x80'+payload(key)+bytes(4)+(scalar_payload() if value is None else value))


def tag50(first=None,second=None):
    return (b'\x50\x07\xfe'+struct.pack('<IIII',0xffffffff,1,0x80000000,14)+
            (scalar_payload(b'\xff\x00',128) if first is None else first)+
            (scalar_payload(None,2,b'\x00\x00\x80\xff') if second is None else second))


def tag11f(first=None,value=None,last=None):
    return (b'\xfa\x1f\x01\x08\x80'+struct.pack('<III',0xffffffff,0x80000000,14)+
            (pair(b'key',b'\xff',254) if first is None else first)+
            (scalar_payload(None) if value is None else value)+b'\xfe'+
            (pair(b'',None) if last is None else last))


def tag_b4(*,finder=None):
    if finder is None:
        finder=(b'\x03'+struct.pack('<i',3)+payload(b'\xff\xfe')+payload(b'')+payload(None)+
                struct.pack('<I',0x80000000)+b'\x02'+struct.pack('<IiII',0xffffffff,2,0,0xffffffff))
    return b'\xb4\x0d\xfe'+bytes(12)+b'\xff'+finder+b'\xff\x80\xff\xff\xfe\x02\xff'


def tag56():
    return (b'\x56\x08\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+payload(b'\xff\x00')+
            struct.pack('<i',3)+b'\x01'+payload(b'a')+b'\xff\x01'+payload(None)+
            struct.pack('<I',0x80000000)+b'\x02'+struct.pack('<IiII',0xffffffff,2,0,0xffffffff))


def tag6d(value=b'value',flag=254):
    return b'\x6d\x06'+bytes([flag])+struct.pack('<IIII',0xffffffff,0x80000000,1,0x7fc00000)+payload(value)

def tag5b(flag=254,bits=0xffffffffffffffff):
    return b'\x5b\x06'+bytes([flag])+struct.pack('<IIIIQ',0xffffffff,0x80000000,1,0x7fc00000,bits)


def tag3c(finder=None,nested=None,value=None):
    if finder is None:
        finder=(b'\x03'+struct.pack('<i',2)+payload(b'\xff\x00')+payload(None)+
                struct.pack('<I',0x80000000)+b'\x02'+struct.pack('<IiII',0xffffffff,2,0,0xffffffff))
    return (b'\x3c\x0a\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+finder+
            struct.pack('<I',0x7fc00000)+(target() if nested is None else nested)+
            struct.pack('<I',0xffffffff)+b'\x80'+(scalar_payload(None) if value is None else value))


def tag119(value=b'wire',nested=None):
    return (b'\xfa\x19\x01\x16\xfe'+struct.pack('<IIIIII',0xffffffff,0x80000000,0x7fc00000,1,2,3)+
            payload(value)+struct.pack('<I',0xffffffff)+b'\xfe\x80\xff'+struct.pack('<I',0x80000000)+
            (target() if nested is None else nested)+struct.pack('<IIII',0xffffffff,0x80000000,0x7fc00000,0xff800000)+
            b'\xfe\x80'+struct.pack('<II',0xffffffff,0x80000000))


def finder3(value=None):
    return b'\x03\x04'+bytes(range(12))+bytes(range(16))+scalar_payload(value)+b'\x80'


def tagc5(tags=None,effect=None,calc=None,nested=None,value=b'wire'):
    return (b'\xc5\x10\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+b'\x80'+payload(value)+
            (effect85() if effect is None else effect)+(b'\x00\x01'+scalar_payload(None) if calc is None else calc)+
            struct.pack('<I',0xffffffff)+(taglist() if tags is None else tags)+struct.pack('<I',0x80000000)+
            b'\xfe\x80\xff'+(target() if nested is None else nested)+b'\x80')


def taglist(items=(b'\x01'+struct.pack('<I',0xffffffff),)):
    return b'\x01'+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())


def tag9b(first=b'first',second=b'second',nested=None):
    return (b'\x9b\x09\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+payload(first)+
            bytes(range(16))+payload(second)+struct.pack('<I',0xffffffff)+(target() if nested is None else nested))


def tag10f(first=254,last=128):
    return b'\xfa\x0f\x01\x05'+bytes([first])+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+bytes([last])

def tag44(value=b'variable-name',nested=None):
    return b'\x44\x06\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+payload(value)+(target() if nested is None else nested)

def tag69(nested=None):
    return b'\x69\x06\xfe'+struct.pack('<IIII',0xffffffff,0x80000000,1,0x7fc00000)+(target() if nested is None else nested)

def tag163(value=b'name',left=None,right=None):
    return (b'\xfa\x63\x01\x08\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+payload(value)+
            struct.pack('<I',0x7fc00000)+(scalar_payload(b'left') if left is None else left)+
            (scalar_payload(b'right-longer') if right is None else right))

def tag136(finder=None,nested=None,value=b'value'):
    if finder is None:
        finder=b'\x03'+struct.pack('<i',2)+payload(b'finder')+payload(None)+bytes(4)+b'\x02'+struct.pack('<IiII',0xffffffff,2,1,0xffffffff)
    return (b'\xfa\x36\x01\x09\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+finder+
            struct.pack('<I',0x7fc00000)+(target() if nested is None else nested)+payload(value)+b'\x80')

def tag78(*,items=(0,0xffffffff,0x80000000),nested=None):
    tail=struct.pack('<i',-1 if items is None else len(items))
    if items:tail+=struct.pack('<'+'I'*len(items),*items)
    return (b'\x78\x09\xfe'+struct.pack('<IIII',0xffffffff,0x80000000,1,0x7fc00000)+
            b'\x80\xff'+(target() if nested is None else nested)+tail)


def tag68(nested=None,flag=254):
    return (b'\x68\x05'+bytes([flag])+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (target() if nested is None else nested))


def tag81(first=b'key',last=b'\xff\x00',nested=None,flag=254):
    return (b'\x81\x09'+bytes([flag])+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            payload(first)+(target() if nested is None else nested)+payload(last)+b'\x80\xff')


def effect85(value=b"fx"):
    return (b'\x55'+
            bytes(4) + bytes(4) + bytes(4) + bytes(1) + bytes(1) + bytes(4) + bytes(4) + bytes(4) +
            bytes(4) + bytes(8) + bytes(4) + scalar_payload(None) + payload(value) + bytes(4) + bytes(1) + bytes(4) +
            bytes(1) + bytes(4) + bytes(4) + bytes(1) + bytes(1) + bytes(4) + bytes(1) + bytes(1) +
            bytes(4) + bytes(1) + bytes(1) + bytes(1) + bytes(1) + bytes(1) + bytes(1) + scalar_payload(None) +
            bytes(4) + bytes(1) + bytes(4) + payload(value) + bytes(4) + bytes(1) + bytes(4) + bytes(4) +
            bytes(4) + bytes(4) + bytes(1) + bytes(12) + b"\x03"+scalar_payload(None)*3 + bytes(4) + bytes(4) + bytes(1) +
            bytes(1) + bytes(4) + bytes(4) + bytes(4) + bytes(1) + bytes(4) + bytes(4) + bytes(12) +
            b"\x03"+scalar_payload(None)*3 + bytes(1) + bytes(12) + b"\x03"+scalar_payload(None)*3 + bytes(1) + bytes(4) + bytes(1) + bytes(1) +
            bytes(1) + bytes(4) + bytes(4) + bytes(1) + bytes(1) + bytes(1) + bytes(1) + bytes(1) +
            bytes(1) + bytes(1) + bytes(1) + bytes(1) + bytes(4) + bytes(1) + bytes(1) + bytes(4) +
            bytes(4) + bytes(4) + bytes(4) + payload(value) + bytes(1))


def damage33(calc=b'\x03\x04'+scalar_payload(None)+bytes(4)+scalar_payload(None)+bytes(4),effect=None,processors=()):
    return (b'\x21\xfe\x80'+calc+scalar_payload(None)+b'\xff'+bytes(4)+bytes(4)+bytes(8)+struct.pack('<i',-1 if processors is None else len(processors))+b''.join(processors or ())+bytes(4)+
            bytes(4)+payload(b'unit')+bytes(4)+(effect85() if effect is None else effect)+b'\xfe'*5+
            b'\x01'+payload(b'sound')+bytes(4)+b'\x80'*6+calc+b'\xff'+bytes.fromhex('0000807f')+b'\xfe'*3)


def tag9a(units=None,env=None):
    return (b'\x9a\x0b\xff'+bytes(12)+b'\xfe'+bytes(4)+
            (struct.pack('<i',1)+damage33() if units is None else units)+target()+
            (b'\x04'+bytes(8)+b'\xfe\xff'+b'\x00\x01'+scalar_payload(None) if env is None else env)+b'\x80'+target())


def taga2(first=b'key',last=b'\xff\x00',targets=None,effect=None):
    targets=(target(),)*4 if targets is None else targets
    return (b'\xa2\x12\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+payload(first)+
            targets[0]+(effect85() if effect is None else effect)+targets[1]+b'\xff'+targets[2]+
            b'\xfe\x80\x01\x00\xff'+payload(last)+targets[3]+b'\x80')


def tag65(t=None,value=None):
    return (b'\x65\x08\xfe'+struct.pack('<IIII',0xffffffff,0x80000000,0x7fc00000,0xdeadbeef)+
            (target() if t is None else t)+b'\x80'+(scalar_payload(b'key') if value is None else value))


def collider16():
    return (b'\x10'+bytes(range(12))+payload(b'one')+payload(None)+payload(b'')+
            bytes(range(12,24))+payload(b'\xff\xfe')+payload(b'longer')+payload(None)+
            struct.pack('<I',0x7fc00000)+payload(b'key')+struct.pack('<I',0xff800000)+payload(b'')+
            bytes(range(24,36))+struct.pack('<I',0xdeadbeef)+b'\xff\x80')


def finder18(shape=None):
    return (b'\x12\x0b\xfe\x80\xff'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            payload(b'\xffkey')+b'\xff\x80'+struct.pack('<I',0xff800000)+(collider16() if shape is None else shape))


def tag7c(t=None,query=None):
    return (b'\x7c\x06\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (target(selector=b'\x03'+finder18()+bytes(8)) if t is None else t)+
            (b'\x02'+struct.pack('<IiIII',0x80000000,3,0,0xffffffff,0x7fc00000) if query is None else query))


def tag96(value=None,key=None,t=None):
    return (b'\x96\x09\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+b'\x80'+
            (scalar_payload(b'scalar') if value is None else value)+
            (pair(b'left',b'right',254) if key is None else key)+
            (target() if t is None else t)+b'\xff')


def tagfe(values=None,targets=None):
    values=(scalar_payload(b'\xffkey'),scalar_payload(None)) if values is None else values
    targets=(target(),target()) if targets is None else targets
    return (b'\xfa\xfe\x00\x14\xfe'+struct.pack('<IIIII',0xffffffff,0x80000000,0x7fc00000,1,0xdeadbeef)+
            b'\x80'+struct.pack('<I',0xffffffff)+values[0]+struct.pack('<I',0x80000000)+values[1]+
            b'\xfe\xff\x80\x00'+targets[0]+targets[1]+b'\xff\x80'+struct.pack('<I',0x7fc00000))


def tag157(t=None,value=None,key=b'\xffkey'):
    return (b'\xfa\x57\x01\x0b\xfe'+struct.pack('<IIII',0xffffffff,0x80000000,0x7fc00000,0xdeadbeef)+
            b'\x80'+payload(key)+struct.pack('<I',0xffffffff)+(target() if t is None else t)+
            b'\xff'+(scalar_payload(None) if value is None else value))


def tag169(assignments=(),strings=(b'key',None,b''),targets=None,d=None,value=None):
    targets=(target(),)*2 if targets is None else targets
    return (b'\xfa\x69\x01\x26\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            payload(b'entity')+payload(None)+bytes(4)+payload(b'path')+targets[0]+(direction() if d is None else d)+
            b'\xfe\x80\x00\xff'+struct.pack('<i',-1 if assignments is None else len(assignments))+
            (b'' if assignments is None else b''.join(assignments))+b'\xfe'+targets[1]+bytes(4)+
            bytes(range(12))+bytes(4)+payload(b'raw')+bytes(range(16))+b'\xff\x80'+payload(b'')+
            b'\xfe\x01'+(scalar_payload(None) if value is None else value)+
            struct.pack('<i',-1 if strings is None else len(strings))+
            (b'' if strings is None else b''.join(payload(s) for s in strings))+b'\x00\x01\x80\xfe\xff\x02\x03\x04\x05')


def tag02(items=(b'\x01'+payload(b'id'),),targets=None,value=None,flag=254):
    targets=(target(),)*3 if targets is None else targets
    return (b'\x02\x0c'+bytes([flag])+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            struct.pack('<i',-1 if items is None else len(items))+(b'' if items is None else b''.join(items))+
            targets[0]+targets[1]+b'\xfe'+(scalar_payload(None) if value is None else value)+targets[2]+b'\x80\xff')


def tag58(single=None,nested=None,value=None,flag=254):
    return (b'\x58\x08'+bytes([flag])+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+
            (b'\x01'+payload(b'id') if single is None else single)+(target() if nested is None else nested)+
            struct.pack('<I',0xffffffff)+(scalar_payload(None) if value is None else value))


def tag57():
    return (b'\x57\x08\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+payload(b'\xff\x00')+
            struct.pack('<i',3)+pair(b'a',b'\xff\x00',254)+b'\xff'+pair(None,b'',128)+
            struct.pack('<I',0x80000000)+b'\x02'+struct.pack('<IiII',0xffffffff,2,0,0xffffffff))


def tag92():
    assignment=b'\x06'+bytes.fromhex('FFFFFFFF')+payload(b'\xff\x00')+bytes.fromhex('0000C07F')+payload(None)+payload(b'')+b'\xfe'
    item=b'\x05\x80'+struct.pack('<i',2)+assignment+b'\xff'+payload(b'\xff\x00')+payload(None)+b'\xfe'
    return (b'\x92\x13\xfe'+bytes(12)+b'\x80\xfe'+b'\x02'+bytes(4)+payload(b'\xff\x00')+
            struct.pack('<i',2)+item+b'\xff'+bytes(4)+payload(b'k')+scalar_payload(None)+b'\x80'+
            struct.pack('<i',3)+payload(b'\xff\x00')+payload(None)+payload(b'')+b'\x00\x01\x80\xfe\xff'+b'\xff')


def tag183(first=(),second=(),scalar1=b'\xff',scalar2=b'\xff',curve=b'\xff',value=None):
    def items(values):
        return struct.pack('<i',-1 if values is None else len(values))+(b'' if values is None else b''.join(values))
    return (b'\xfa\x83\x01\x10'+b'\xff'*13+payload(value)+scalar1+items(first)+b'\xfe'+
            items(second)+scalar2+b'\xff'*12+curve+b'\x80\xfe')


def scalar_pair_flags(first=b'\xff',second=b'\xff'):
    return b'\x06'+b'\xff'*4+first+b'\x80'*4+second+b'\xff\x80'


def taga7(disabled=b'\xff',enabled=b'\xff',query=b'\xff',last=b'\x80',wire=b'\xa7'):
    return wire+b'\x0b'+bytes(13)+b'\xff'+disabled+enabled+query+disabled+enabled+last


def tag19e(first=b'\xff',second=b'\xff',items=(),value=None,last=b'\x00\x80\xff\xfe\x01\x02'):
    return (b'\xfa\x9e\x01\x17'+b'\xff'*13+first+b'\xff'*8+second+b'\x80'*16+
            payload(value)+b'\xff\x80'+payload(b'')+struct.pack('<i',-1 if items is None else len(items))+
            b''.join(payload(v) for v in items or ())+last)


def condition08(value=None):
    return b'\x05\xff'+payload(value)+b'\xff'*8+b'\x80'*4


def group08(items=()):
    return b'\x01'+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())


def tag08(first=(),second=(),vector=b'\xff',scalar=b'\xff',curve=b'\xff',last=b'\xff'*13,wire=b'\x08'):
    first_list=struct.pack('<i',-1 if first is None else len(first))+b''.join(first or ())
    second_list=struct.pack('<i',-1 if second is None else len(second))+b''.join(second or ())
    return (wire+b'\x32'+bytes(13)+vector*2+scalar*4+
            (curve+b'\xff'*4+scalar)*2+b'\x80'*4+scalar+b'\xff'+payload(None)+b'\x80'+
            first_list+curve+b'\xff'+second_list+vector+scalar*6+b'\x80\xff\x00'+curve+vector+last)


def tag120(first=b'\xff',second=b'\xff',value=None):
    return b'\xfa\x20\x01\x08'+bytes(13)+first+second+b'\x80\xff\x00\x7f'+payload(value)


def tag9f(first=b'\xff',second=b'\xff',last=b'\xff',wire=b'\x9f'):
    return wire+b'\x09'+bytes(13)+b'\xff'+b'\x80\xff\x00\x7f'+first+second+last


def tag1b(first=b'\xff',second=b'\xff',direct=b'\xff',scalars=(b'\xff',)*6,wire=b'\x1b'):
    a,b,c,d,e,f=scalars
    return wire+b'\x11'+bytes(13)+first+a+b+b'\x80\xff\x00\x7f'+c+direct+d+b'\xff'+e+b'\x80'+second+b'\x00'+f


def tag87(items=(),wire=b'\x87'):
    return wire+b'\x05'+bytes(13)+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())


def tag52(last=255,wire=b'\x52'):
    return wire+b'\x05\x80'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+bytes([last])


def tag8e(value=b'\xff',wire=b'\x8e'):
    return wire+b'\x05'+bytes(13)+value


def tag125(value=b'\xff',flag=255):
    return b'\xfa\x25\x01\x06'+bytes(13)+bytes([flag])+value


def tag124(last=0xffffffff):
    return b'\xfa\x24\x01\x05\x80'+struct.pack('<IIII',0xffffffff,0x80000000,0x7fc00000,last)


def tag14f(last=0xff):
    return b'\xfa\x4f\x01\x05\x80'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+bytes([last])


def tag71(last=255,extended=False):
    return (b'\xfa\x71\x00' if extended else b'\x71')+b'\x05\x80'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+bytes([last])


def tag70(a=0xffffffff,b=0x80000000,extended=False):
    return (b'\xfa\x70\x00' if extended else b'\x70')+b'\x06\x80'+struct.pack('<IIIII',0xffffffff,0x80000000,0x7fc00000,a,b)


def buff_input16(items=(),value=b'wire'):
    return b'\x03\xff'+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+payload(value)


def target_filter16(query=b'\xff'):
    return b'\x0a\xff\x80'+bytes.fromhex('FFFFFFFF')+b'\xff\x80\x00'+bytes(8)+query+bytes.fromhex('000080FF')


def tag16(items=(),extended=False,first=b'\xff',second=b'\xff',rich=False):
    head=(b'\xfa\x16\x00' if extended else b'\x16')+b'\x1e\xff'+bytes(12)
    return (head+first+second+payload(b'wire')+(target() if rich else b'\xff')+bytes(4)+
            (b'\x02'+bytes(4)+payload(None) if rich else b'\xff')+
            struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+bytes(8)+b'\x80'+
            (target() if rich else b'\xff')+b'\xff\x80'+
            (scalar_payload() if rich else b'\xff')+direction()+b'\xff'+b'\xff\x80\x00\x01'+bytes(4)+b'\xff\x80'+
            (collider16() if rich else b'\xff')+target_filter16(query41((0,0xffffffff)))+bytes.fromhex('FFFFFFFF'))


def tag178(value=b'\xff\x00wire',last=255):
    return b'\xfa\x78\x01\x08\xff'+bytes.fromhex('FFFFFFFF000000800000C07F')+b'\x80\xff'+payload(value)+bytes([last])


def tagc1(first=b'\xff\x00raw',second=b'\x80tail',extended=False):
    return (b'\xfa\xc1\x00' if extended else b'\xc1')+b'\x06\xff'+bytes.fromhex('FFFFFFFF000000800000C07F')+payload(first)+payload(second)


def tag101(value=0xffffffff,last=255):
    return b'\xfa\x01\x01\x06\xff'+bytes.fromhex('FFFFFFFF000000800000C07F')+struct.pack('<I',value)+bytes([last])


def tagc7(first=b'\xff',second=b'\xff',value=None,curve=b'\xff',last=255,extended=False):
    return ((b'\xfa\xc7\x00' if extended else b'\xc7')+b'\x0c\xff'+bytes.fromhex('FFFFFFFF000000800000C07F')+
            b'\xff'*4+first+payload(value)+curve+b'\x00\x00\xc0\x7f'+second+b'\xff'*4+bytes([last]))


def keyword19b(values=(),scalar=b'\xff'):
    return (b'\x03'+struct.pack('<i',-1 if values is None else len(values))+
            b''.join(payload(v) for v in values or ())+b'\xff'*4+scalar)


def tag19b(items=(),paired=b'\xff',first_scalar=b'\xff',last_scalar=b'\xff',first=b'\xff',second=b'\xff'):
    return (b'\xfa\x9b\x01\x0e\xff'+bytes.fromhex('FFFFFFFF000000800000C07F')+b'\x80\xff'+paired+first_scalar+
            struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+
            b'\xff'+last_scalar+first+second+b'\xff'*4)


def tag128(effect=b'\xff',calc=b'\xff',last=b'\xff'):
    return (b'\xfa\x28\x01\x0b\xfe'+b'\xff'*12+b'\x80'+effect+
            b'\xfe'*4+b'\xff'+b'\x80'*4+calc+last)


def tagcf(nested=b'\xff',value=None,raw8=b'\xff'*8):
    return (b'\xcf\x0b\xfe'+b'\xff'*12+b'\x80'*4+b'\xff'+b'\xfe'*4+
            raw8+b'\x80'+nested+payload(value))


def tag2c(first=b'\xff',second=b'\xff',nested=b'\xff',value=None,last=None):
    return (b'\x2c\x0e\xfe'+b'\xff'*12+first+second+b'\x80'+b'\xfe'*4+
            b'\xff'+payload(value)+b'\x80'*4+nested+b'\xfe'+payload(last))


def tag18b(value=0x01020304):
    return b'\xfa\x8b\x01\x05\xfe'+struct.pack('<IIII',0xffffffff,0x80000000,1,value)


def tag07(first=b'\xff',last=b'\xff',extended=False):
    return ((b'\xfa\x07\x00' if extended else b'\x07')+b'\x08\xfe'+
            struct.pack('<III',0xffffffff,0x80000000,1)+first+
            struct.pack('<I',0x01020304)+last+b'\x80')


def tag15b(first=b'\xff',second=b'\xff',seq=b'\xff',integer=b'\xff',last=b'\xff'):
    return (b'\xfa\x5b\x01\x0b\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+
            first+second+b'\x80'+seq+integer+b'\xfe'+last)


def tag144(first=b'\xff',value=None,last=b'\xff',tail=b'\xfe',bits=0x7fc00001):
    return (b'\xfa\x44\x01\x12\xfe'+struct.pack('<III',0xffffffff,0x80000000,1)+
            first+b'\x00\x01\x80\xfe\xff'+payload(value)+
            struct.pack('<IIIII',0xffffffff,0x80000000,1,bits,0x7fffffff)+last+tail)


def tag12a(tags=b'\xff',last=b'\xff',flag=b'\x80'):
    return b'\xfa\x2a\x01\x07\xfe'+b'\xff'*12+flag+tags+last


def weapon_vfx(values=(None,)*9,flags=b'\x00\x01\x7f\x80\xfe\xff\x02\x03\x04'):
    return b'\x12'+flags+b''.join(payload(v) for v in values)


def tag37(nested=b'\xff',extended=False,last=b'\xff'*4,flag=b'\x80'):
    return (b'\xfa\x37\x00' if extended else b'\x37')+b'\x0a\xfe'+b'\xff'*12+b'\x80\xfe\xff'+nested+flag+last


def tag17(pair=b'\xff',extended=False):
    return (b'\xfa\x17\x00' if extended else b'\x17')+b'\x05\xfe'+struct.pack('<III',0x01020304,0x80000000,0xffffffff)+pair


def tagce(first=b'\xff',value=None,last=b'\xff',extended=False,word=b'\x04\x03\x02\x81'):
    return ((b'\xfa\xce\x00' if extended else b'\xce')+b'\x08\xfe'+
            struct.pack('<III',0x01020304,0x80000000,0xffffffff)+first+word+payload(value)+last)


def tag18e(values=(None,)*8):
    assert len(values)==8
    return (b'\xfa\x8e\x01\x12\xfe'+struct.pack('<III',0x01020304,0x80000000,0xffffffff)+
            b''.join(payload(v) for v in values[:4])+b'\x00\x80\xff\x12\x34'+
            payload(values[4])+payload(values[5])+b'\xa5'+payload(values[6])+payload(values[7]))


def tag102(word=b'\x04\x03\x02\x81'):
    return b'\xfa\x02\x01\x05\xfe'+struct.pack('<III',0x01020304,0x80000000,0xffffffff)+word


def tag28(buff_id=b'\xff',value=None,extended=False,word=b'\x04\x03\x02\x81'):
    return ((b'\xfa\x28\x00' if extended else b'\x28')+b'\x07\xfe'+
            struct.pack('<III',0x01020304,0x80000000,0xffffffff)+buff_id+payload(value)+word)


def tag172(first=None,second=None,t=b'\xff',tail=b'\x80'):
    return (b'\xfa\x72\x01\x08\xfe'+struct.pack('<III',0x01020304,0x80000000,0xffffffff)+
            payload(first)+payload(second)+t+tail)


def tag166(items=(),paired=b'\xff',first_scalar=b'\xff',last_scalar=b'\xff',first=b'\xff',second=b'\xff'):
    return (b'\xfa\x66\x01\x0d\xfe'+struct.pack('<III',0x01020304,0x80000000,0xffffffff)+b'\x80\xff'+paired+first_scalar+
            struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+b'\xff'+last_scalar+first+second)

def tag19c(items=(),paired=b'\xff',first_scalar=b'\xff',last_scalar=b'\xff',first=b'\xff',second=b'\xff'):
    return (b'\xfa\x9c\x01\x0d\xfe'+struct.pack('<III',0x01020304,0x80000000,0xffffffff)+b'\x80\xff'+paired+first_scalar+
            struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+b'\xff'+last_scalar+first+second)


def tag15d(items=(),paired=b'\xff',first_scalar=b'\xff',last_scalar=b'\xff',first=b'\xff',second=b'\xff'):
    return (b'\xfa\x5d\x01\x0d\xff'+bytes.fromhex('FFFFFFFF000000800000C07F')+b'\x80\xff'+paired+first_scalar+
            struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+b'\xff'+last_scalar+first+second)


def animator_param(raw4=b'\x00\x00\xc0\x7f',first=b'\xff'*4,flag=b'\xfe',last=b'\xff'*8):
    return b'\x05'+first+flag+raw4+last


def tag14a(first=b'\xff',second=b'\xff',value=None):
    return b'\xfa\x4a\x01\x08\xfe'+b'\xff'*12+b'\x80'+first+second+payload(value)


def tag133(nested=b'\xff',finder=b'\xff',value=None):
    return b'\xfa\x33\x01\x07\xfe'+b'\xff'*12+nested+finder+payload(value)


def tagf4(first=b'\xff'*4,last=b'\xff'*4,extended=False):
    return (b'\xfa\xf4\x00' if extended else b'\xf4')+b'\x06\xfe'+b'\xff'*12+first+last


def tagb9(nested=b'\xff',flag=b'\xff',extended=False):
    return (b'\xfa\xb9\x00' if extended else b'\xb9')+b'\x06\xfe'+b'\xff'*12+flag+nested


def tag186(nested=b'\xff',first=b'\xff'*4,last=b'\xff'*4):
    return b'\xfa\x86\x01\x07\xfe'+b'\xff'*12+nested+first+last


def tag17c(nested=b'\xff',scalar=b'\xff',last_target=b'\xff',last=b'\xff'):
    return (b'\xfa\x7c\x01\x0e\xfe'+b'\xff'*12+nested+b'\xff\xfe\x80\x00'+
            b'\x00\x00\xc0\x7f'+scalar+b'\xfe'+last_target+last)


def subspeedf6(first=b'\xff',value=None,second=b'\xff',curve=b'\xff',last=b'\xff'*4):
    return b'\x05'+first+payload(value)+second+curve+last


def tagf6(overrides=None,wire=b'\xf6'):
    # Independent member-numbered fixture from the selected 46 source calls.
    scalar=scalar_payload(b'expr');vector=b'\x03'+scalar_payload(None)+b'\xff'+scalar_payload(b'')
    sub=subspeedf6(scalar,b'\xff\x00',scalar_payload(None),curve24((bytes(28),)))
    members=[b'\xfe',b'\xff'*4,b'\x80'*4,bytes(4),b'\xff',scalar,b'\x80',bytes(4),
             b'\xff',b'\xfe',b'\x80',b'\x00',b'\xff',b'\xfe',scalar,b'\x80',
             b'\xff'*12,b'\xff'*4,vector,scalar,b'\xfe',b'\xff'*4,b'\xff',b'\xfe',b'\x80',
             scalar,b'\x00\x00\xc0\x7f',b'\xff'*4,b'\xfe',b'\xff',payload(b'wire'),
             scalar,scalar,scalar,curve24((bytes(28),)),b'\xff'*4,b'\x80'*4,
             b'\x00\x00\x80\x7f',b'\xfe',target(),scalar,b'\xff',b'\xfe',b'\x80',sub,sub]
    assert len(members)==46
    for member,value in (overrides or {}).items():members[member-1]=value
    return wire+b'\x2e'+b''.join(members)


def ability_map(items=()):
    return b'\x02'+b'\x80\xfe\xff\x00'+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())


def tagad(items=(),extended=False):
    return (b'\xfa\xad\x00' if extended else b'\xad')+b'\x05\x80'+b'\xfe'*12+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())


def tag198(first=None,second=None,last=b'\xff'):
    return (b'\xfa\x98\x01\x0b\xfe'+struct.pack('<IIIII',0,0x80000000,0xffffffff,0x7fc00001,0x01234567)+
            payload(first)+struct.pack('<II',0xfedcba98,0x80000001)+payload(second)+last)


def tag197(word=0x80000001,last=255):
    return b'\xfa\x97\x01\x06\xfe'+struct.pack('<IIII',0x01234567,0xffffffff,0x7fc00001,word)+bytes([last])


def tag91(shape=b'\xff',last=b'\xff',*,extended=False,bits=0x7fc00001,flags=b'\xff\x00\x80'):
    return ((b'\xfa\x91\x00' if extended else b'\x91')+b'\x0a\xfe'+
            struct.pack('<III',0xffffffff,0x80000000,0x01234567)+
            struct.pack('<I',bits)+flags+shape+last)


def tag184(first=b'\xff',second=b'\xff'):
    return b'\xfa\x84\x01\x06\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00001)+first+second


def tagdf(effect=b'\xff',direction_value=b'\xff',first=b'\xff',second=b'\xff',left=b'\xff',right=b'\xff',*,extended=False,bits=0x7fc00001,last=255):
    return ((b'\xfa\xdf\x00' if extended else b'\xdf')+b'\x0f\xfe'+bytes(12)+effect+
            struct.pack('<I',0xffffffff)+direction_value+first+second+struct.pack('<II',bits,0x80000000)+
            left+struct.pack('<I',bits)+right+bytes([last]))


def tag1f(first=b'\xff',second=b'\xff',third=b'\xff',left=b'\xff',right=b'\xff',nested=b'\xff',*,extended=False,bits=0x7fc00001):
    return ((b'\xfa\x1f\x00' if extended else b'\x1f')+b'\x0f\xfe'+bytes(12)+first+second+left+
            b'\x80'+struct.pack('<II',0xffffffff,bits)+nested+struct.pack('<I',0x80000000)+
            third+right+struct.pack('<I',0xfedcba98))


def tagb7(nested=b'\xff',value=None,*,extended=False,raw=bytes(range(16)),flag=255):
    return ((b'\xfa\xb7\x00' if extended else b'\xb7')+b'\x09\xfe'+
            bytes(12)+raw+bytes([flag])+struct.pack('<I',0x80000000)+nested+payload(value))


class BuffActionsTests(unittest.TestCase):


    def test_b7_fixed_raw16_null_states_and_encodings(self):
        for extended in (False,True):
            shift=2 if extended else 0
            for raw in (bytes(16),b'\xff'*16,bytes(range(16)),b'\x00\x00\xc0\x7f'*4):
                for flag in (0,1,128,255):
                    for value in (None,b''):
                        child=tagb7(value=value,extended=extended,raw=raw,flag=flag)
                        r=Reader(child+b'opaque','b7.bin');r.action(0)
                        self.assertEqual((r.pos,len(child),r.records[-1]['tag']),(41+shift,41+shift,183))
                        span=next(q for q in r.ranges if q['kind']=='anonymous-raw16')
                        self.assertEqual((span['start'],span['end']),(15+shift,31+shift))
                        self.assertEqual(child[span['start']:span['end']],raw)
            for child,tag in ((b'\xff',255),(b'\xb7\xff',183),(b'\xfa\xb7\x00\xff',183)):
                r=Reader(child,'b7-null.bin');r.action(0);self.assertEqual((r.pos,r.records[-1]['tag']),(len(child),tag))

    def test_b7_nested_target_terminal_payload_and_every_cut(self):
        for extended in (False,True):
            for child in (tagb7(extended=extended),tagb7(value=b'\xff\x00\xfa\x80',extended=extended),
                          tagb7(target(),b'longer-tail',extended=extended)):
                r=Reader(child,'b7-full.bin');r.action(0);self.assertEqual(r.pos,len(child))
                for cut in range(len(child)):
                    outcomes=[]
                    for data in (child[:cut],child,child[:cut]+b'\xff'*20):
                        r=Reader(data,'b7-cut.bin',cut)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,cut)
                        self.assertFalse(any(q.get('tag')==183 and q['start']==0 for q in r.records))
                        outcomes.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[1],outcomes[2])
                for tail in (b'\xff',b'other'):
                    for limit in (len(child),len(child+tail)):
                        r=Reader(child+tail,'b7-tail.bin',limit);r.action(0);self.assertEqual(r.pos,len(child))
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_b7_length_words_payload_bounds_raw16_and_headers(self):
        nested=(b'\x0d\xff'+payload(None)+b'\x80'+bytes(4)+b'\xfe'+payload(b'')+
                b'\xff'+bytes(12)+payload(b'A')+payload(b'XYZ')+bytes(4))
        self.assertEqual(len(nested),45)
        for extended in (False,True):
            shift=2 if extended else 0;child=tagb7(nested,b'final',extended=extended)
            for at in tuple(36+shift+k for k in (2,12,29,34))+(81+shift,):
                for count in (-2,2147483647):
                    r=Reader(child[:at]+struct.pack('<i',count)+child[at+4:],'b7-count.bin')
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    d=caught.exception.diagnostic
                    self.assertEqual((d['offset'],d['actual'],d['category'],r.pos),(at,count,'count-bounds',at+4))
                for available in range(4):
                    r=Reader(child,'b7-word.bin',at+available)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(at,at))
            for at,width in ((15+shift,16),(31+shift,1),(32+shift,4)):
                for available in range(width):
                    r=Reader(child,'b7-fixed.bin',at+available)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    d=caught.exception.diagnostic
                    self.assertEqual((d['category'],d['offset'],d['expected'],r.pos),('truncated',at,{'bytes':width},at))
            for at,expected in ((1+shift,9),(36+shift,13)):
                r=Reader(child[:at]+b'\x2a'+child[at+1:],'b7-header.bin')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['offset'],d['expected'],d['actual'],r.pos),(at,expected,42,at))
            at=81+shift
            for available in range(5):
                r=Reader(child,'b7-payload.bin',at+4+available)
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['offset'],d['actual'],d['expected'],r.pos),(at,5,{'minimum':-1,'maximum':available},at+4))

    def test_b7_parent_tail_unknown_nested_and_next_union(self):
        for extended in (False,True):
            child=tagb7(value=b'body',extended=extended);data=sequence(child)
            for missing in (1,2):
                r=Reader(data,'b7-parent.bin',len(data)-missing)
                with self.assertRaises(FrameError) as caught:r.sequence()
                self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(len(data)-missing,len(data)-missing))
            r=Reader(sequence(child,b'\xfa\xa0\x01'),'b7-next.bin')
            with self.assertRaises(Unsupported) as caught:r.sequence()
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],r.pos),(5+len(child),416,5+len(child)))
            self.assertTrue(any(q.get('tag')==183 for q in r.records))
            bad=tagb7(target(selector=b'\x03\x17'+bytes(8)),b'opaque',extended=extended)
            r=Reader(bad,'b7-unknown-target.bin')
            with self.assertRaises(Unsupported) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'nested-profile')
            self.assertFalse(any(q.get('tag')==183 for q in r.records))

    def test_1f_fixed_source_order_null_states_and_encodings(self):
        for extended in (False,True):
            shift=2 if extended else 0
            for bits in (0,0x80000000,0x7fc00001,0xff800000,0xffffffff):
                child=tag1f(extended=extended,bits=bits);r=Reader(child+b'opaque','1f.bin');r.action(0)
                self.assertEqual((r.pos,len(child),r.records[-1]['tag']),(38+shift,38+shift,31))
                self.assertEqual([(v['start'],v['end']) for v in r.ranges if v['kind']=='anonymous-float32-bits'],[(23+shift,27+shift)])
                self.assertEqual((r.ranges[-1]['start'],r.ranges[-1]['end']),(34+shift,38+shift))
            for count in (-1,0):
                seq=b'\x03'+struct.pack('<i',count)+b'\xff\x80'
                child=tag1f(seq,seq,seq,extended=extended);r=Reader(child,'1f-null-array.bin');r.action(0)
                self.assertEqual(r.pos,len(child))
        for data,tag in ((b'\xff',255),(b'\x1f\xff',31),(b'\xfa\x1f\x00\xff',31)):
            r=Reader(data,'1f-null.bin');r.action(0);self.assertEqual((r.pos,r.records[-1]['tag']),(len(data),tag))

    def test_1f_independent_nested_instances_and_every_cut(self):
        first,second,third=sequence(tag197()),sequence(tag197(),b'\xff'),sequence(tag1f())
        left,right,nested=effect85(b'a'),effect85(b'longer'),target()
        for extended in (False,True):
            child=tag1f(first,second,third,left,right,nested,extended=extended)
            start=17 if extended else 15
            seqstarts=[start,start+len(first),start+len(first)+len(second)+len(left)+9+len(nested)+4]
            r=Reader(child,'1f-full.bin');r.action(0);self.assertEqual(r.pos,len(child))
            self.assertEqual([(v['start'],v['end']) for v in r.records if v['kind']=='sequence' and v['start'] in seqstarts],
                             [(q,q+len(seq)) for q,seq in zip(seqstarts,(first,second,third))])
            for cut in range(len(child)):
                outcomes=[]
                for data in (child[:cut],child,child[:cut]+b'\xff'*20):
                    r=Reader(data,'1f-cut.bin',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut)
                    self.assertFalse(any(v.get('tag')==31 and v['start']==0 for v in r.records))
                    outcomes.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[1],outcomes[2])
            for tail in (b'\xff',b'x'*9):
                for limit in (len(child),len(child+tail)):
                    r=Reader(child+tail,'1f-tail.bin',limit);r.action(0);self.assertEqual(r.pos,len(child))
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_1f_three_counts_two_effect_lengths_headers_and_fixed_tails(self):
        seqs=(sequence(tag197()),sequence(tag197(),b'\xff'),sequence(tag197(),tag197()))
        effects=(effect85(b'a'),effect85(b'longer'))
        for extended in (False,True):
            start=17 if extended else 15
            child=tag1f(*seqs,*effects,extended=extended)
            e1=start+len(seqs[0])+len(seqs[1]);s3=e1+len(effects[0])+14;e2=s3+len(seqs[2])
            # Constructed source positions, independent of parser output.
            counts=(start+1,start+len(seqs[0])+1,s3+1,e1+53,e2+53)
            for at in counts:
                for count in (-2,2147483647):
                    data=child[:at]+struct.pack('<i',count)+child[at+4:];r=Reader(data,'1f-count.bin')
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    d=caught.exception.diagnostic
                    self.assertEqual((d['offset'],d['actual'],d['category'],r.pos),(at,count,'count-bounds',at+4))
                for available in range(4):
                    r=Reader(child,'1f-count-cut.bin',at+available)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(at,at))
            for at,expected in ((start-14,15),(start,3),(start+len(seqs[0]),3),(s3,3),(e1,85),(e2,85)):
                r=Reader(child[:at]+b'*'+child[at+1:],'1f-header.bin')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['offset'],d['expected'],d['actual'],r.pos),(at,expected,42,at))
            for at in (e1+len(effects[0])+5,s3-4,len(child)-4):
                for available in range(4):
                    r=Reader(child,'1f-word-cut.bin',at+available)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(at,at))
            for at,seq in zip((start,start+len(seqs[0]),s3),seqs):
                for missing in (1,2):
                    end=at+len(seq)-missing;r=Reader(child,'1f-seq-tail.bin',end)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(end,end))

    def test_1f_each_recursive_sequence_depth_and_unknown_sibling(self):
        for slot in range(3):
            child=tag1f()
            for _ in range(64):
                seqs=[b'\xff']*3;seqs[slot]=sequence(child);child=tag1f(*seqs)
            r=Reader(child,'1f-depth64.bin');r.action(0);self.assertEqual(r.pos,len(child))
            seqs=[b'\xff']*3;seqs[slot]=sequence(child);r=Reader(tag1f(*seqs),'1f-depth65.bin')
            with self.assertRaises(Unsupported) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('depth-limit',65))
        child=tag1f();r=Reader(sequence(child,b'\xfa\xa0\x01'),'1f-next.bin')
        with self.assertRaises(Unsupported) as caught:r.sequence()
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],r.pos),(len(child)+5,416,len(child)+5))
        self.assertTrue(any(v.get('tag')==31 for v in r.records))

    def test_df_source_order_bits_encodings_and_null_states(self):
        for extended in (False,True):
            size=40 if extended else 38
            for bits in (0,0x80000000,0x7fc00001,0xff800000,0xffffffff):
                for last in (0,1,128,255):
                    child=tagdf(extended=extended,bits=bits,last=last)
                    r=Reader(child+b'opaque','df-bits.bin',size);r.action(0)
                    self.assertEqual((r.pos,len(child),r.records[-1]['tag']),(size,size,223))
                    raw=[q for q in r.ranges if q['kind']=='anonymous-float32-bits']
                    shift=2 if extended else 0
                    self.assertEqual([(q['start'],q['end']) for q in raw],[(23+shift,27+shift),(32+shift,36+shift)])
                    self.assertEqual((r.ranges[-1]['start'],r.ranges[-1]['end']),(size-1,size))
        for child,tag in ((b'\xff',255),(b'\xdf\xff',223),(b'\xfa\xdf\x00\xff',223)):
            r=Reader(child,'df-null.bin');r.action(0);self.assertEqual((r.pos,r.records[-1]['tag']),(len(child),tag))

    def test_df_nonnull_instances_all_cuts_and_terminal_byte(self):
        for extended in (False,True):
            for child in (tagdf(extended=extended),tagdf(first=scalar_payload(b'one'),second=scalar_payload(b'longer'),left=target(),right=target(direction_value=b'\xff'),extended=extended),tagdf(effect85(),direction(),scalar_payload(None),scalar_payload(b''),target(),target(),extended=extended)):
                r=Reader(child,'df-full.bin');r.action(0);self.assertEqual(r.pos,len(child))
                for cut in range(len(child)):
                    outcomes=[]
                    for data in (child[:cut],child,child[:cut]+b'\xff'*20):
                        r=Reader(data,'df-cut.bin',cut)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,cut)
                        self.assertFalse(any(q.get('tag')==223 and q['start']==0 for q in r.records))
                        outcomes.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[1],outcomes[2])
                r=Reader(child,'df-final.bin',len(child)-1)
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(len(child)-1,len(child)-1))
                self.assertTrue(any(q['kind']=='anonymous-target-profile' for q in r.records))
                for tail in (b'x',b'\xff'):
                    r=Reader(child+tail,'df-tail.bin');r.action(0);self.assertEqual(r.pos,len(child))
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_df_two_payload_counts_raw_words_and_headers(self):
        first,second=scalar_payload(b'a'),scalar_payload(b'long')
        for extended in (False,True):
            shift=2 if extended else 0
            child=tagdf(first=first,second=second,extended=extended)
            for at in (22+shift,22+shift+len(first)):
                for count in (-2,2147483647):
                    data=child[:at]+struct.pack('<i',count)+child[at+4:];r=Reader(data,'df-length.bin')
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    d=caught.exception.diagnostic
                    self.assertEqual((d['offset'],d['actual'],d['category'],r.pos),(at,count,'count-bounds',at+4))
                for available in range(4):
                    r=Reader(child,'df-length-cut.bin',at+available)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(at,at))
            fixed=tagdf(extended=extended)
            for at in (23+shift,32+shift):
                for available in range(4):
                    r=Reader(fixed,'df-raw4-cut.bin',at+available)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(at,at))
            for at,expected in ((1+shift,15),(21+shift,3),(21+shift+len(first),3)):
                data=child[:at]+b'\x2a'+child[at+1:];r=Reader(data,'df-header.bin')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['offset'],d['expected'],d['actual'],r.pos),(at,expected,42,at))

    def test_df_parent_nullable_counts_tails_and_unknown_sibling(self):
        for extended in (False,True):
            child=tagdf(extended=extended)
            for count in (-1,0,1):
                data=b'\x03'+struct.pack('<i',count)+(child if count==1 else b'')+bytes(2)
                sequence_frame(data)
                for missing in (1,2):
                    r=Reader(data,'df-parent-tail.bin',len(data)-missing)
                    with self.assertRaises(FrameError) as caught:r.sequence()
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(len(data)-missing,len(data)-missing))
            for count in (-2,2147483647):
                with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
                self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('count-bounds',count))
            r=Reader(sequence(child,b'\xfa\xa0\x01'),'df-unknown.bin')
            with self.assertRaises(Unsupported) as caught:r.sequence()
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],r.pos),(len(child)+5,416,len(child)+5))
            self.assertTrue(any(q.get('tag')==223 for q in r.records))

    def test_184_two_independent_sequences_and_distinct_short_tag(self):
        choices=(b'\xff',b'\x03'+struct.pack('<i',-1)+b'\xff\x80',sequence(),sequence(b'\xff'),sequence(tag197(),b'\xff'))
        for first in choices:
            for second in choices:
                child=tag184(first,second);r=Reader(child+b'opaque','184.bin');r.action(0)
                self.assertEqual((r.pos,r.records[-1]['tag']),(len(child),388))
                outer_seqs=[q for q in r.records if q['kind']=='sequence' and q['start'] in (17,17+len(first))]
                self.assertEqual([(q['start'],q['end']) for q in outer_seqs],[(17,17+len(first)),(17+len(first),len(child))])
        self.assertEqual(len(tag184()),19)
        for child,tag in ((b'\xff',255),(b'\xfa\x84\x01\xff',388),(b'\x84\xff',132),(tag84(),132)):
            r=Reader(child,'184-null.bin');r.action(0);self.assertEqual((r.pos,r.records[-1]['tag']),(len(child),tag))

    def test_184_all_cuts_and_required_second_sequence(self):
        for first,second in ((b'\xff',b'\xff'),(sequence(),sequence(b'\xff',tag197())),(sequence(tag184()),sequence(tag197()))):
            child=tag184(first,second)
            for cut in range(len(child)):
                outcomes=[]
                for data in (child[:cut],child,child[:cut]+b'\xff'*30):
                    r=Reader(data,'184-cut.bin',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut)
                    self.assertFalse(any(q.get('tag')==388 and q['start']==0 for q in r.records))
                    outcomes.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[1],outcomes[2])
            r=Reader(child,'184-second.bin',17+len(first))
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(17+len(first),17+len(first)))
            self.assertTrue(any(q['kind']=='sequence' and q['start']==17 for q in r.records))
            for tail in (b'x',b'\xff'):
                r=Reader(child+tail,'184-tail.bin',len(child));r.action(0);self.assertEqual(r.pos,len(child))
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_184_nested_counts_headers_and_sequence_tails(self):
        first,second=sequence(tag197()),sequence(b'\xff',tag197())
        child=tag184(first,second)
        for start,seq in ((17,first),(17+len(first),second)):
            for count in (-2,2147483647):
                data=child[:start+1]+struct.pack('<i',count)+child[start+5:];r=Reader(data,'184-count.bin')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['offset'],d['category'],d['actual'],r.pos),(start+1,'count-bounds',count,start+5))
            for available in range(4):
                r=Reader(child,'184-count-cut.bin',start+1+available)
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(start+1,start+1))
            for missing in (1,2):
                end=start+len(seq);r=Reader(child,'184-seq-tail.bin',end-missing)
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(end-missing,end-missing))
        for at,expected in ((3,6),(17,3),(17+len(first),3)):
            data=child[:at]+b'\x2a'+child[at+1:];r=Reader(data,'184-header.bin')
            with self.assertRaises(FrameError) as caught:r.action(0)
            d=caught.exception.diagnostic
            self.assertEqual((d['offset'],d['expected'],d['actual'],r.pos),(at,expected,42,at))
        r=Reader(tag184(sequence(b'\xfa\xa0\x01')),'184-unknown.bin')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],r.pos),(22,416,22))

    def test_184_depth_counts_and_parent_tail(self):
        # Each Sequence -> action edge raises depth exactly once.
        child=tag184()
        for _ in range(64):child=tag184(sequence(child))
        r=Reader(child,'184-depth64.bin');r.action(0);self.assertEqual(r.pos,len(child))
        r=Reader(tag184(sequence(child)),'184-depth65.bin')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('depth-limit',65))
        for count in (-1,0,1):
            data=b'\x03'+struct.pack('<i',count)+(tag184() if count==1 else b'')+bytes(2)
            sequence_frame(data)
            for missing in (1,2):
                r=Reader(data,'184-parent-tail.bin',len(data)-missing)
                with self.assertRaises(FrameError) as caught:r.sequence()
                self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(len(data)-missing,len(data)-missing))

    def test_91_short_extended_source_order_and_null_states(self):
        for extended in (False,True):
            width=3 if extended else 1
            for bits in (0,0x80000000,0x7fc00001,0xff800000,0xffffffff):
                for flags in (bytes(3),b'\xff'*3,b'\x80\x01\xfe'):
                    child=tag91(extended=extended,bits=bits,flags=flags)
                    r=Reader(child+b'opaque','91-bits.bin',len(child));r.action(0)
                    self.assertEqual((r.pos,r.records[-1]['tag']),(23+width,145))
                    self.assertEqual([(q['start'],q['end']) for q in r.ranges],
                        [(0,width),(width,width+1),(width+1,width+2),
                         (width+2,width+6),(width+6,width+10),(width+10,width+14),
                         (width+14,width+18),(width+18,width+19),(width+19,width+20),
                         (width+20,width+21),(width+21,width+22),(width+22,width+23)])
            null=(b'\xfa\x91\x00' if extended else b'\x91')+b'\xff'
            r=Reader(null,'91-null.bin');r.action(0)
            self.assertEqual((r.pos,r.records[-1]['tag']),(len(null),145))
        r=Reader(b'\xff','91-union-null.bin');r.action(0)
        self.assertEqual((r.pos,r.records[-1]['tag']),(1,255))

    def test_91_nonnull_children_every_cut_and_terminal_target(self):
        for extended in (False,True):
            for shape,last in ((b'\xff',b'\xff'),(collider16(),b'\xff'),(b'\xff',target()),(collider16(),target())):
                child=tag91(shape,last,extended=extended)
                r=Reader(child,'91-full.bin');r.action(0);self.assertEqual(r.pos,len(child))
                self.assertEqual(r.records[-1]['tag'],145)
                for n in range(len(child)):
                    results=[]
                    for data in (child[:n],child,child[:n]+b'\xff'*20):
                        r=Reader(data,'91-cut.bin',n)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,n)
                        self.assertFalse(any(q.get('tag')==145 for q in r.records))
                        results.append((r.pos,caught.exception.diagnostic,r.ranges,r.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])
                # A complete shape is retained when the required target is absent.
                r=Reader(child,'91-target.bin',len(child)-len(last))
                with self.assertRaises(FrameError):r.action(0)
                self.assertTrue(any(q['kind']=='anonymous-collider-shape-profile' for q in r.records))

    def test_91_nested_lengths_headers_and_trailing(self):
        for extended in (False,True):
            width=3 if extended else 1
            child=tag91(collider16(),target(),extended=extended)
            # First collider byte payload follows its header and raw12.
            length_at=width+34
            for count in (-2,2147483647):
                bad=child[:length_at]+struct.pack('<i',count)+child[length_at+4:]
                r=Reader(bad,'91-count.bin')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['offset'],d['actual'],d['category'],r.pos),(length_at,count,'count-bounds',length_at+4))
            for pos,expected in ((width,10),(width+21,16),(width+21+len(collider16()),13)):
                bad=child[:pos]+b'\x2a'+child[pos+1:];r=Reader(bad,'91-header.bin')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['offset'],d['expected'],d['actual'],d['category'],r.pos),(pos,expected,42,'member-count',pos))
            for tail in (b'x',b'\xff'):
                r=Reader(child+tail,'91-tail.bin');r.action(0);self.assertEqual(r.pos,len(child))
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_91_parent_counts_required_tail_and_unknown_sibling(self):
        for extended in (False,True):
            child=tag91(collider16(),target(),extended=extended)
            for count in (-1,0,1):
                data=b'\x03'+struct.pack('<i',count)+(child if count==1 else b'')+bytes(2)
                sequence_frame(data)
                for missing in (1,2):
                    r=Reader(data,'91-parent-tail.bin',len(data)-missing)
                    with self.assertRaises(FrameError) as caught:r.sequence()
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(len(data)-missing,len(data)-missing))
            for count in (-2,2147483647):
                with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
                self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('count-bounds',count))
            r=Reader(sequence(child,b'\xfa\xa0\x01'),'91-unknown.bin')
            with self.assertRaises(Unsupported) as caught:r.sequence()
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],r.pos),(len(child)+5,416,len(child)+5))
            self.assertTrue(any(q.get('tag')==145 for q in r.records))

    def test_197_fixed_source_order_all_bits_and_distinct_alias(self):
        for word in (0,1,0x7fc00000,0x80000000,0xffffffff):
            for last in (0,1,128,255):
                child=tag197(word,last);self.assertEqual(len(child),22)
                r=Reader(child+b'opaque','197.bin',22);r.action(0)
                self.assertEqual((r.pos,r.records[-1]['tag']),(22,407))
                self.assertEqual([(q['start'],q['end']) for q in r.ranges],[(0,3),(3,4),(4,5),(5,9),(9,13),(13,17),(17,21),(21,22)])
        for child,expected in ((b'\xff',255),(b'\xfa\x97\x01\xff',407)):
            r=Reader(child,'197-null.bin');r.action(0);self.assertEqual((r.pos,r.records[-1]['tag']),(len(child),expected))
        r=Reader(b'\x97','197-short.bin')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['actual'],r.pos),(151,0))

    def test_197_every_cut_hard_limits_and_required_last_members(self):
        child=tag197()
        for n in range(len(child)):
            results=[]
            for z in (child[:n],child,child[:n]+b'\xff'*20):
                r=Reader(z,'197-cut.bin',n)
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertLessEqual(r.pos,n);self.assertFalse(r.records)
                results.append((r.pos,caught.exception.diagnostic,r.ranges))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])
        for available in range(4):
            r=Reader(child,'197-word.bin',17+available)
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(17,17))
        r=Reader(child,'197-byte.bin',21)
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(21,21))

    def test_197_header_unknown_union_and_trailing(self):
        for header in (0,5,7,42):
            child=bytearray(tag197());child[3]=header;r=Reader(child,'197-header.bin')
            with self.assertRaises(FrameError) as caught:r.action(0)
            d=caught.exception.diagnostic
            self.assertEqual((d['offset'],d['expected'],d['actual'],d['category'],r.pos),(3,6,header,'member-count',3))
        for tail in (b'x',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(tag197())+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        r=Reader(sequence(tag197(),b'\xfa\xa0\x01'),'197-unknown.bin')
        with self.assertRaises(Unsupported) as caught:r.sequence()
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],r.pos),(27,416,27))
        self.assertTrue(any(q.get('tag')==407 for q in r.records))

    def test_197_parent_counts_tail_and_minimum_guard(self):
        for count in (-1,0,1):
            child=b'\x03'+struct.pack('<i',count)+(tag197() if count==1 else b'')+bytes(2)
            sequence_frame(child)
            for missing in (1,2):
                r=Reader(child,'197-tail.bin',len(child)-missing)
                with self.assertRaises(FrameError) as caught:r.sequence()
                self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(len(child)-missing,len(child)-missing))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+tag197()+bytes(2))
            self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('count-bounds',count))
        with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',1)+bytes(2))
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['offset']),('count-bounds',1))


    def test_198_source_order_independent_payloads_and_terminal_target(self):
        self.assertEqual(len(tag198()),42)
        for first,second in ((None,None),(b'',b''),(b'\xff\xfa',b'\x80'),(None,b'xyz'),(b'abc',None)):
            for last in (b'\xff',target(),target(direction_value=b'\xff')):
                child=tag198(first,second,last);r=Reader(child+b'opaque','198.bin',len(child));r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],408)
                cursor=0
                for q in r.ranges:self.assertEqual(q['start'],cursor);cursor=q['end']
                self.assertEqual(cursor,len(child))
        r=Reader(b'\xfa\x98\x01\xff','198-null.bin');r.action(0);self.assertEqual(r.pos,4)
        r=Reader(b'\x98','198-short.bin')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['category'],r.pos),('truncated',1))
        r=Reader(b'\x98\xff','198-short-wrapper.bin');r.action(0)
        self.assertEqual(r.records[-1]['tag'],152)

    def test_198_every_cut_hard_limit_and_required_terminal_target(self):
        for child in (tag198(),tag198(b'\x80\xff',b'a',target()),tag198(b'',None)):
            for n in range(len(child)):
                results=[]
                for z in (child[:n],child,child[:n]+b'\xff'*20):
                    r=Reader(z,'198-cut.bin',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(q.get('tag')==408 for q in r.records))
                    results.append((r.pos,caught.exception.diagnostic,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])
        child=tag198();r=Reader(child,'198-target.bin',41)
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category'],r.pos),(41,'truncated',41))

    def test_198_independent_lengths_and_wrong_headers(self):
        for first,second in ((None,None),(b'',b''),(b'xyz',b'\xff')):
            child=tag198(first,second)
            for at in (25,37+len(first or b'')):
                for value in (-2,2147483647):
                    bad=bytearray(child);struct.pack_into('<i',bad,at,value);r=Reader(bad,'198-length.bin')
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    d=caught.exception.diagnostic
                    self.assertEqual((d['offset'],d['actual'],d['category'],r.pos),(at,value,'count-bounds',at+4))
                for width in range(4):
                    r=Reader(child,'198-marker.bin',at+width)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertEqual((caught.exception.diagnostic['offset'],r.pos),(at,at))
        for at in (3,41):
            bad=bytearray(tag198());bad[at]=42;r=Reader(bad,'198-header.bin')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category'],r.pos),(at,'member-count',at))

    def test_198_parent_count_tails_unknown_and_trailing(self):
        child=tag198()
        for n in (-1,0,1):
            raw=b'\x03'+struct.pack('<i',n)+(child if n==1 else b'')+bytes(2)
            sequence_frame(raw)
            for missing in (1,2):
                r=Reader(raw,'198-tail.bin',len(raw)-missing)
                with self.assertRaises(FrameError) as caught:r.sequence()
                self.assertEqual(caught.exception.diagnostic['category'],'truncated')
                self.assertEqual(r.pos,len(raw)-missing)
        for n in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',n)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
        for tail in (b'x',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        r=Reader(sequence(child,b'\xfa\xa0\x01'),'198-unknown.bin')
        with self.assertRaises(Unsupported) as caught:r.sequence()
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],r.pos),(47,416,47))
        self.assertTrue(any(q.get('tag')==408 for q in r.records))


    def test_tagad_maps_null_states_and_recursive_source_order(self):
        for extended in (False,True):
            for items in (None,(),(b'\xff',),(ability_map(None),),(ability_map(),),
                          (ability_map((b'\xff',sequence(tagad(None)))),b'\xff')):
                child=tagad(items,extended)
                reader=Reader(child+b'opaque','ad.bin',len(child));reader.action(0)
                self.assertEqual(reader.pos,len(child))
                self.assertEqual(reader.records[-1],dict(start=0,end=len(child),kind='union',tag=173))
                cursor=0
                for r in reader.ranges:self.assertEqual(r['start'],cursor);cursor=r['end']
                self.assertEqual(cursor,len(child))
            for child in ((b'\xfa\xad\x00' if extended else b'\xad')+b'\xff',):
                r=Reader(child,'ad-null.bin');r.action(0);self.assertEqual(r.pos,len(child))

    def test_tagad_every_cut_limit_and_trailing(self):
        for extended in (False,True):
            child=tagad((ability_map((sequence(tagad((b'\xff',))),b'\xff')),),extended)
            wire=sequence(child)
            for n in range(len(wire)):
                results=[]
                for data in (wire[:n],wire,wire[:n]+b'\xff'*(len(wire)-n)):
                    r=Reader(data,'ad-cut.bin',n)
                    with self.assertRaises(FrameError) as caught:r.sequence()
                    self.assertLessEqual(r.pos,n)
                    if n<5+len(child):
                        self.assertFalse(any(v.get('tag')==173 and v['start']==5 for v in r.records))
                    else:
                        self.assertTrue(any(v.get('tag')==173 and v['start']==5 for v in r.records))
                    results.append((r.pos,caught.exception.diagnostic,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])
            with self.assertRaises(FrameError) as caught:sequence_frame(wire+b'x')
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tagad_count_header_guards_and_unknown_child(self):
        for extended in (False,True):
            shift=2 if extended else 0
            good=tagad((ability_map((sequence(b'\xff'),)),),extended)
            # Outer list, map Sequence array, Sequence action array.
            for at in (15+shift,24+shift,29+shift):
                for value in (-2,2147483647):
                    bad=bytearray(good);struct.pack_into('<i',bad,at,value)
                    r=Reader(bad,'ad-count.bin')
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    d=caught.exception.diagnostic
                    self.assertEqual((d['offset'],d['actual'],d['category'],r.pos),(at,value,'count-bounds',at+4))
            for at in (1+shift,19+shift,28+shift):
                bad=bytearray(good);bad[at]=42;r=Reader(bad,'ad-header.bin')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category'],r.pos),(at,'member-count',at))
            child=tagad((ability_map((sequence(b'\xff',b'\xfa\xa0\x01'),)),),extended)
            r=Reader(child,'ad-unknown.bin')
            with self.assertRaises(Unsupported) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],r.pos),(34+shift,416,34+shift))
            self.assertEqual([v.get('tag') for v in r.records],[255])

    def test_tagad_depth_propagates_through_map_sequences(self):
        child=tagad((ability_map((b'\xff',)),))
        r=Reader(child,'ad-depth.bin');r.action(64);self.assertEqual(r.pos,len(child))
        r=Reader(child,'ad-depth.bin')
        with self.assertRaises(Unsupported) as caught:r.action(65)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual'],r.pos),('depth-limit',65,28))
        child=tagad(None)
        for _ in range(66):child=tagad((ability_map((sequence(child),)),))
        r=Reader(child,'ad-recursive.bin')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'depth-limit')
        self.assertFalse(any(v.get('tag')==173 for v in r.records))


    def test_2c_independent_scalars_payloads_and_null_wrappers(self):
        for first,second in ((b'\xff',b'\xff'),(scalar_payload(None),scalar_payload(b'')),
                             (scalar_payload(b'\xff\x00'),scalar_payload())):
            for value,last in ((None,b''),(b'',None),(b'first',b'last')):
                child=tag2c(first,second,target(),value,last)
                row=event_prefix(prefix(sequence(child)),source='2c.bin')
                self.assertEqual(row['status'],'supported-prefix')
                r=next(r for r in row['completedRecords'] if r.get('tag')==44)
                self.assertEqual((r['start'],r['end']),(19,19+len(child)))
        for child in (b'\x2c\xff',b'\xfa\x2c\x00\xff',tag2c(),b'\xfa\x2c\x00'+tag2c()[1:]):
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_2c_every_cut_hard_limits_and_trailing(self):
        raw=sequence(tag2c(scalar_payload(),scalar_payload(None),target(),b'first',b'last'))
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n],source='2c-cut.bin')
        full=prefix(raw)
        for n in range(len(full)):
            row=event_prefix(full,source='2c-limit.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='2c-limit.bin',limit=n))
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_2c_malformed_headers_lengths_and_required_tail(self):
        for missing,offset in ((5,32),(4,33)):
            reader=Reader(tag2c()[:-missing],'2c-tail.bin')
            with self.assertRaises(FrameError) as caught:reader.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],offset)
            self.assertFalse(any(r.get('tag')==44 for r in reader.records))
        for at in (23,33):
            for n in (-2,2147483647):
                child=bytearray(tag2c());struct.pack_into('<i',child,at,n)
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child),source='2c-length.bin')
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']), (at+5,n))
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
        full=prefix(sequence(tag2c(scalar_payload(),scalar_payload(None),target(),b'first',b'last')))
        good=event_prefix(full,source='2c-bad.bin')
        for r in good['ranges']:
            if r['kind'] not in ('member-header','count-i32'):continue
            bad=bytearray(full);at=r['start']
            if r['kind']=='member-header':bad[at]=42
            else:struct.pack_into('<i',bad,at,2147483647)
            row=event_prefix(bad,source='2c-bad.bin')
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row['diagnostic']['offset'],at)

    def test_2c_unknown_child_preserves_only_completed_records(self):
        unknown=b'\x0d\xff'+payload(None)+bytes(6)+payload(None)+b'\x03\x17'
        row=event_prefix(prefix(sequence(tag2c(nested=unknown))),source='2c-target.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['consumedEnd'],19+31+len(unknown)-1)
        self.assertFalse(any(r.get('tag')==44 for r in row['completedRecords']))
        child=tag2c(scalar_payload(),scalar_payload(None),target(),b'first',b'last')
        row=event_prefix(prefix(sequence(child,b'\x59')),source='2c-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['consumedEnd'],19+len(child))
        self.assertTrue(any(r.get('tag')==44 for r in row['completedRecords']))

    def test_14b_target_scalar_null_states_source_order_and_alias(self):
        self.assertEqual(len(tag14b()),19)
        for t in (b'\xff',target(),target(direction_value=b'\xff')):
            for scalar in (b'\xff',scalar_payload(None,128),scalar_payload(b'',254,b'\x04\x03\x02\x01'),scalar_payload(b'\xfeA',255)):
                child=tag14b(t,scalar);r=Reader(child+b'\xaa','14b');r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],331)
                if scalar!=b'\xff':
                    self.assertEqual(r.ranges[-1],dict(start=len(child)-4,end=len(child),kind='anonymous-scalar32'))
                if t!=b'\xff':
                    self.assertIn(dict(start=17,end=17+len(t),kind='anonymous-target-profile'),r.records)
        for value in (b'\xff',b'\xfa\x4b\x01\xff'):
            r=Reader(value+b'\xaa','14b-wrapper');r.action(0);self.assertEqual(r.pos,len(value))
        r=Reader(b'\x4b\xff','14b-short')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],75);self.assertEqual(r.pos,0)

    def test_14b_all_cuts_required_scalar_and_parent_sequence_tails(self):
        for child in (tag14b(),tag14b(target(),scalar_payload(b'wire\xff',128,b'\x04\x03\x02\x01'))):
            for cut in range(len(child)):
                results=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*16):
                    q=Reader(data,'14b-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==331 for v in q.records))
                    results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            parent=prefix(sequence(child))
            for cut in range(len(parent)):
                row=event_prefix(parent,source='14b-parent',limit=cut);self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(parent[:cut]+b'\xff'*(len(parent)-cut),source='14b-parent',limit=cut))
            for tail in (b'\x00',b'\xff'*4):
                r=Reader(child+tail,'14b-end');r.action(0);self.assertEqual(r.pos,len(child))
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        for t in (b'\xff',target()):
            child=tag14b(t);r=Reader(child[:-1],'14b-scalar-required')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],17+len(t));self.assertEqual(r.pos,17+len(t))
            self.assertFalse(any(v.get('tag')==331 for v in r.records))
            child=tag14b(t,scalar_payload(b'x'))
            for k in range(1,5):
                r=Reader(child[:-k],'14b-scalar-dword')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],len(child)-4);self.assertEqual(r.pos,len(child)-4)

    def test_14b_bad_headers_counts_unknown_nested_and_next_child(self):
        child=tag14b(target(),scalar_payload(b'wire'));r=Reader(child,'14b');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                data=bytearray(child);at=span['start']
                if span['kind']=='member-header':data[at]=invalid
                else:struct.pack_into('<i',data,at,invalid)
                q=Reader(data,'14b-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v.get('tag')==331 for v in q.records))
        for count in (-2,2147483647):
            q=Reader(b'\x03'+struct.pack('<i',count)+child+bytes(2),'14b-parent-count')
            with self.assertRaises(FrameError) as caught:q.sequence()
            self.assertEqual(caught.exception.diagnostic['offset'],1);self.assertEqual(q.pos,5)
        for parent in (sequence(child),sequence(),b'\x03'+struct.pack('<i',-1)+bytes(2)):
            q=Reader(parent,'14b-parent');q.sequence();self.assertEqual(q.pos,len(parent))
            for k in (1,2):
                q=Reader(parent[:-k],'14b-parent-tail')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
        q=Reader(tag14b(target(selector=b'\x03\x17'+bytes(8))),'14b-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        row=event_prefix(prefix(sequence(child,b'\xd0')),source='14b-next')
        self.assertEqual(row['diagnostic']['actual'],208);self.assertEqual(row['diagnostic']['offset'],19+len(child))
        self.assertEqual(row['consumedEnd'],19+len(child));self.assertTrue(any(v.get('tag')==331 for v in row['completedRecords']))

    def test_8a_nullable_profiles_payloads_both_encodings_and_raw_terminal(self):
        d=b'\x08\x80\xfe\x04\x03\x02\x01\xff'+target(direction_value=b'\xff')+b'\x08\x07\x06\x05\xff\x0c\x0b\x0a\x09'
        selectors=(b'\xff',b'\x03\xff'+struct.pack('<ii',-1,-1),b'\x03\x00\x00'+bytes(8),b'\x03\xff'+struct.pack('<i',1)+b'\xff'+struct.pack('<i',1)+b'\xff')
        self.assertEqual(len(tag8a()),60);self.assertEqual(len(tag8a(extended=True)),62)
        for extended in (False,True):
            for direction_value in (b'\xff',d):
                for sel in selectors:
                    for values in ((None,b'',b'a\xff',b'\x01\x02\x03'),(b'\x80',None,b'',b'last')):
                        child=tag8a(direction_value,sel,values,extended,b'\x04\x03\x02\x01');q=Reader(child+b'\xaa','8a');q.action(0)
                        self.assertEqual(q.pos,len(child));self.assertEqual(q.records[-1]['tag'],138)
                        self.assertEqual(q.ranges[-1],{'start':len(child)-4,'end':len(child),'kind':'anonymous-float32-bits'})
                        self.assertEqual(child[-6:],b'\xfe\xff\x04\x03\x02\x01')
                        at=(17 if extended else 15)+len(direction_value)
                        self.assertIn({'start':at,'end':at+4,'kind':'anonymous-scalar32'},q.ranges)
                        self.assertEqual(child[at:at+4],b'\x04\x03\x02\x01')
        for raw in (b'\xff',b'\x8a\xff',b'\xfa\x8a\x00\xff'):
            q=Reader(raw+b'\xaa','8a-null');q.action(0);self.assertEqual(q.pos,len(raw))

    def test_8a_all_cuts_required_float_tail_parent_and_trailing(self):
        for extended in (False,True):
            child=tag8a(direction(),b'\x03\xff'+bytes(8),(b'a\xff',b'bc',b'\x80',b'def'),extended)
            for cut in range(len(child)):
                results=[]
                for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                    q=Reader(raw,'8a-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertLessEqual(q.pos,cut);self.assertFalse(any(x.get('tag')==138 for x in q.records))
                    results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for raw in (tag8a(extended=extended),child):
                for k in range(1,7):
                    q=Reader(raw[:-k],'8a-terminal')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    at=len(raw)-4 if k<=4 else len(raw)-k
                    self.assertEqual(caught.exception.diagnostic['offset'],at);self.assertEqual(q.pos,at)
            parent=prefix(sequence(child))
            for cut in range(len(parent)):
                row=event_prefix(parent,source='8a-parent',limit=cut);self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(parent[:cut]+b'\xff'*(len(parent)-cut),source='8a-parent',limit=cut))
            for tail in (b'\x00',b'\xff'*4):
                q=Reader(child+tail,'8a-end');q.action(0);self.assertEqual(q.pos,len(child))
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_8a_bad_headers_counts_unknown_nested_and_parent_boundaries(self):
        child=tag8a(direction(),b'\x03\xff'+bytes(8),(b'a',b'bc',b'def',b'last'));r=Reader(child,'8a');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'8a-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(x.get('tag')==138 for x in q.records))
        q=Reader(tag8a(sel=b'\x03\x17'+bytes(8)),'8a-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        for count in (-2,2147483647):
            q=Reader(b'\x03'+struct.pack('<i',count)+child+bytes(2),'8a-count')
            with self.assertRaises(FrameError) as caught:q.sequence()
            self.assertEqual(caught.exception.diagnostic['offset'],1);self.assertEqual(q.pos,5)
        for parent in (sequence(child),sequence(),b'\x03'+struct.pack('<i',-1)+bytes(2)):
            q=Reader(parent,'8a-parent');q.sequence();self.assertEqual(q.pos,len(parent))
            for k in (1,2):
                q=Reader(parent[:-k],'8a-parent-tail')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
        row=event_prefix(prefix(sequence(child,b'\xd0')),source='8a-next')
        self.assertEqual(row['diagnostic']['actual'],208);self.assertEqual(row['diagnostic']['offset'],19+len(child))
        self.assertEqual(row['consumedEnd'],19+len(child));self.assertTrue(any(x.get('tag')==138 for x in row['completedRecords']))

    def test_18b_fixed_order_raw_dword_bits_and_distinct_short_tag(self):
        for value in (0,1,0xffffffff,0x80000000,0x7fc00001,0x01020304):
            child=tag18b(value);q=Reader(child+b'\xaa','18b');q.action(0)
            self.assertEqual(len(child),21);self.assertEqual(q.pos,21);self.assertEqual(q.records[-1]['tag'],395)
            self.assertEqual([(x['start'],x['end']) for x in q.ranges if x['kind']=='anonymous-scalar32'],[(5,9),(9,13),(13,17),(17,21)])
            self.assertEqual(child[17:21],struct.pack('<I',value))
        for raw in (b'\xff',b'\xfa\x8b\x01\xff'):
            q=Reader(raw+b'\xaa','18b-null');q.action(0);self.assertEqual(q.pos,len(raw))
        q=Reader(b'\x8b'+tag18b()[3:],'18b-short')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],139);self.assertEqual(q.pos,0)

    def test_18b_all_cuts_required_terminal_dword_and_trailing(self):
        child=tag18b()
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'18b-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(x.get('tag')==395 for x in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for k in range(1,5):
            q=Reader(child[:-k],'18b-terminal')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],17);self.assertEqual(q.pos,17)
        for tail in (b'\x00',b'\xff'*4):
            q=Reader(child+tail,'18b-end');q.action(0);self.assertEqual(q.pos,21)
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_18b_bad_header_parent_count_tails_and_unknown_child(self):
        bad=bytearray(tag18b());bad[3]=6;q=Reader(bad,'18b-header')
        with self.assertRaises(FrameError) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],3)
        for count in (-2,2147483647):
            parent=b'\x03'+struct.pack('<i',count)+tag18b()+bytes(2);q=Reader(parent,'18b-count')
            with self.assertRaises(FrameError) as caught:q.sequence()
            self.assertEqual(caught.exception.diagnostic['offset'],1);self.assertEqual(q.pos,5)
        for parent in (sequence(tag18b()),b'\x03'+struct.pack('<i',-1)+bytes(2),sequence()):
            q=Reader(parent,'18b-parent');q.sequence();self.assertEqual(q.pos,len(parent))
            for k in (1,2):
                q=Reader(parent[:-k],'18b-tail')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
        row=event_prefix(prefix(sequence(tag18b(),b'\xd0')),source='18b-next')
        self.assertEqual(row['diagnostic']['actual'],208);self.assertEqual(row['diagnostic']['offset'],40)
        self.assertEqual(row['consumedEnd'],40);self.assertTrue(any(x.get('tag')==395 for x in row['completedRecords']))

    def test_07_short_extended_nullable_profiles_and_source_order(self):
        values=(b'\xff',scalar_payload(None,0,b'\xff'*4),scalar_payload(b'',128,b'\x01\x02\x03\x04'),scalar_payload(b'wire\xff',254))
        for extended in (False,True):
            for first in values:
                for last in (b'\xff',target()):
                    child=tag07(first,last,extended);q=Reader(child+b'\xaa','07');q.action(0)
                    self.assertEqual(q.pos,len(child));self.assertEqual(q.records[-1]['tag'],7)
                    at=(17 if extended else 15)+len(first)
                    self.assertIn({'start':at,'end':at+4,'kind':'anonymous-scalar32'},q.ranges)
                    self.assertEqual(child[at:at+4],b'\x04\x03\x02\x01')
                    self.assertEqual(q.ranges[-1],{'start':len(child)-1,'end':len(child),'kind':'anonymous-byte'})
        self.assertEqual(len(tag07()),22);self.assertEqual(len(tag07(extended=True)),24)
        for raw in (b'\xff',b'\x07\xff',b'\xfa\x07\x00\xff'):
            q=Reader(raw+b'\xaa','07-wrapper');q.action(0);self.assertEqual(q.pos,len(raw))

    def test_07_all_cuts_terminal_byte_and_parent_tails(self):
        for extended in (False,True):
            child=tag07(scalar_payload(b'\xffwire',254,b'\x01\x00\xc0\x7f'),target(),extended)
            for cut in range(len(child)):
                results=[]
                for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                    q=Reader(raw,'07-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertLessEqual(q.pos,cut);self.assertFalse(any(x.get('tag')==7 for x in q.records))
                    results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for last in (b'\xff',target()):
                raw=tag07(last=last,extended=extended);q=Reader(raw[:-1],'07-terminal')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],len(raw)-1);self.assertEqual(q.pos,len(raw)-1)
                self.assertFalse(any(x.get('tag')==7 for x in q.records))
            parent=prefix(sequence(child))
            for cut in range(len(parent)):
                row=event_prefix(parent,source='07-parent',limit=cut);self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(parent[:cut]+b'\xff'*(len(parent)-cut),source='07-parent',limit=cut))
            for tail in (b'\x00',b'\xff'*4):
                q=Reader(child+tail,'07-end');q.action(0);self.assertEqual(q.pos,len(child))
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_07_headers_counts_and_unknown_parent_child(self):
        child=tag07(scalar_payload(b'wire'),target());r=Reader(child,'07-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'07-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(x.get('tag')==7 for x in q.records))
        row=event_prefix(prefix(sequence(child,b'\xd0')),source='07-next')
        self.assertEqual(row['diagnostic']['category'],'union-tag');self.assertEqual(row['diagnostic']['actual'],208)
        self.assertEqual(row['consumedEnd'],19+len(child));self.assertEqual(row['diagnostic']['offset'],19+len(child))
        self.assertTrue(any(x.get('tag')==7 for x in row['completedRecords']))

    def test_15b_independent_scalar_nulls_sequence_states_and_short5b(self):
        values=(b'\xff',scalar_payload(None,0,b'\xff'*4),scalar_payload(b'',128,b'\x01\x02\x03\x04'),scalar_payload(b'wire\xff',254))
        sequences=(b'\xff',b'\x03'+struct.pack('<i',-1)+b'\x80\xfe',sequence(),sequence(b'\xff',tag5b()))
        for i in range(len(values)):
            for seq in sequences:
                child=tag15b(values[i],values[(i+1)%4],seq,values[(i+2)%4],values[(i+3)%4])
                r=Reader(child+b'\xaa','15b');r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],347)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='15b-next')
                self.assertEqual(row['diagnostic']['offset'],19+len(child))
                self.assertTrue(any(x.get('tag')==347 for x in row['completedRecords']))
        self.assertEqual(len(tag15b()),24)
        short=tag5b();q=Reader(short,'15b-short');q.action(0)
        self.assertEqual(q.pos,len(short));self.assertEqual(q.records[-1]['tag'],91)
        for raw in (b'\xff',b'\xfa\x5b\x01\xff'):
            q=Reader(raw+b'\xaa','15b-wrapper');q.action(0);self.assertEqual(q.pos,len(raw))

    def test_15b_all_cuts_required_terminal_scalar_and_parent_trailing(self):
        child=tag15b(scalar_payload(b'first'),scalar_payload(None),sequence(tag5b()),scalar_payload(b'int'),scalar_payload(b'last',128))
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'15b-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(x.get('tag')==347 for x in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for seq in (b'\xff',sequence(),b'\x03'+struct.pack('<i',-1)+bytes(2)):
            body=tag15b(seq=seq);q=Reader(body[:-1],'15b-last-wrapper')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(body)-1)
            self.assertTrue(any(x['kind']=='sequence' for x in q.records))
            self.assertFalse(any(x.get('tag')==347 for x in q.records))
        for value in (None,b'',b'\xffwire'):
            body=tag15b(last=scalar_payload(value));last_dword=len(body)-4
            for k in range(1,5):
                q=Reader(body[:-k],'15b-last-dword')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],last_dword)
        parent=prefix(sequence(child))
        for cut in range(len(parent)):
            row=event_prefix(parent,source='15b-parent',limit=cut);self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(parent[:cut]+b'\xff'*(len(parent)-cut),source='15b-parent',limit=cut))
        for tail in (b'\x00',b'\xff'*4):
            q=Reader(child+tail,'15b-record-end');q.action(0);self.assertEqual(q.pos,len(child))
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_15b_scalar_headers_counts_unknown_sequence_child_and_depth(self):
        child=tag15b(scalar_payload(b'one'),scalar_payload(None),sequence(b'\xff'),scalar_payload(b'int'),scalar_payload(b'last'))
        r=Reader(child,'15b-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'15b-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(x.get('tag')==347 for x in q.records))
        q=Reader(tag15b(seq=sequence(b'\xd0')),'15b-unknown-child')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'union-tag')
        self.assertEqual(caught.exception.diagnostic['actual'],208);self.assertEqual(caught.exception.diagnostic['offset'],25)
        self.assertEqual(q.pos,25);self.assertEqual(len(q.records),2)
        nested=tag15b()
        for _ in range(65):nested=tag15b(seq=sequence(nested))
        q=Reader(nested,'15b-depth')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'depth-limit')
        self.assertEqual(caught.exception.diagnostic['actual'],65);self.assertEqual(caught.exception.diagnostic['offset'],1645)

    def test_144_order_null_profiles_scalar_bits_and_short44_distinction(self):
        asymmetric=(b'\x08\xfe\x80'+struct.pack('<I',0x01020304)+b'\xff'+
                    b'\xff'+struct.pack('<I',0x80000001)+b'\xff'+struct.pack('<I',0x7fffffff))
        for first in (b'\xff',direction(),asymmetric):
            for value in (None,b'',b'\xff\x00wire'):
                for last in (b'\xff',target(),target(direction_value=b'\xff')):
                    for bits in (0x7fc00001,0xff800000,0x80000000):
                        child=tag144(first,value,last,bits=bits);r=Reader(child+b'\xaa','144');r.action(0)
                        self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],324)
                        raw=next(x for x in r.ranges if x['kind']=='anonymous-raw-float32')
                        self.assertEqual(child[raw['start']:raw['end']],struct.pack('<I',bits))
                        row=event_prefix(prefix(sequence(child,b'\x59')),source='144-next')
                        self.assertEqual(row['diagnostic']['offset'],19+len(child))
                        self.assertTrue(any(x.get('tag')==324 for x in row['completedRecords']))
        self.assertEqual(len(tag144()),49)
        short=tag44(None,b'\xff');r=Reader(short,'144-short44');r.action(0)
        self.assertEqual(r.pos,len(short));self.assertEqual(r.records[-1]['tag'],68)
        for raw in (b'\xff',b'\xfa\x44\x01\xff'):
            r=Reader(raw+b'\xaa','144-null');r.action(0);self.assertEqual(r.pos,len(raw))

    def test_144_all_cuts_required_final_byte_and_parent_boundaries(self):
        child=tag144(direction(),b'\xffwire',target())
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'144-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(x.get('tag')==324 for x in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for first in (b'\xff',direction()):
            for value in (None,b''):
                body=tag144(first,value);q=Reader(body[:-1],'144-final-byte')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],len(body)-1)
                self.assertTrue(any(x['kind']=='anonymous-target-profile' for x in q.records))
                self.assertFalse(any(x.get('tag')==324 for x in q.records))
        parent=prefix(sequence(child))
        for cut in range(len(parent)):
            row=event_prefix(parent,source='144-parent',limit=cut);self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(parent[:cut]+b'\xff'*(len(parent)-cut),source='144-parent',limit=cut))
        for tail in (b'\xff',b'\x00'*4):
            q=Reader(child+tail,'144-record-end');q.action(0);self.assertEqual(q.pos,len(child))
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_144_nested_headers_lengths_counts_and_unknown_target(self):
        child=tag144(direction(),b'\x80\xff',target());r=Reader(child,'144-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'144-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(x.get('tag')==324 for x in q.records))
        q=Reader(tag144(direction(),None,target(selector=b'\x03\x17'+bytes(8))),'144-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        self.assertTrue(any(x['kind']=='anonymous-direction-profile' for x in q.records))
        self.assertFalse(any(x.get('tag')==324 for x in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_12a_distinct_tag_wrappers_lists_elements_and_terminal_target(self):
        for tags in (b'\xff',taglist(None),taglist(()),taglist(),taglist((b'\xff',b'\x01'+bytes(4),b'\x01'+b'\xff'*4))):
            for last in (b'\xff',target(),target(direction_value=b'\xff')):
                child=tag12a(tags,last);r=Reader(child+b'\xaa','12a');r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],298)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='12a-next')
                self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
                self.assertTrue(any(v.get('tag')==298 for v in row['completedRecords']))
        # Null element and null target are distinct one-byte wrappers.
        body=tag12a(taglist((b'\xff',)));r=Reader(body,'12a-minimum-reserve');r.action(0)
        self.assertEqual(r.pos,len(body));self.assertEqual(sum(v['kind']=='anonymous-tag-element' for v in r.records),1)
        for raw in (b'\xff',b'\xfa\x2a\x01\xff'):
            r=Reader(raw+b'\xaa','12a-null');r.action(0);self.assertEqual(r.pos,len(raw))
        q=Reader(b'\x2a\xff','12a-short')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],42);self.assertEqual(q.pos,0)

    def test_12a_all_cuts_required_target_and_parent_trailing(self):
        child=tag12a(taglist((b'\xff',b'\x01'+b'\xff'*4,b'\x01'+bytes(4))),target())
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'12a-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==298 for v in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for tags in (b'\xff',taglist(None),taglist(())):
            body=tag12a(tags);q=Reader(body[:-1],'12a-target')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(body)-1)
            self.assertTrue(any(v['kind']=='anonymous-tag-list-profile' for v in q.records))
            self.assertFalse(any(v.get('tag')==298 for v in q.records))
        body=tag12a(taglist((b'\xff',)));q=Reader(body[:-1],'12a-reserve')
        with self.assertRaises(FrameError) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],19);self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
        full=prefix(sequence(child))
        for cut in range(len(full)):
            row=event_prefix(full,source='12a-limit',limit=cut);self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='12a-limit',limit=cut))
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_12a_headers_counts_elements_and_unknown_nested_target(self):
        child=tag12a(taglist((b'\x01'+b'\x80'*4,)),target());r=Reader(child,'12a-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'12a-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at);self.assertFalse(any(v.get('tag')==298 for v in q.records))
        # Erasing an element's header must not silently turn this into a DWORD array.
        q=Reader(tag12a(taglist((b'\x02\x00\x00\x00',))),'12a-raw-array')
        with self.assertRaises(FrameError) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],23);self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        q=Reader(tag12a(taglist(),target(selector=b'\x03\x17'+bytes(8))),'12a-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        self.assertTrue(any(v['kind']=='anonymous-tag-element' for v in q.records));self.assertFalse(any(v.get('tag')==298 for v in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_37_grouped_nine_bytes_then_nine_payloads_and_both_encodings(self):
        cases=((None,)*9,(b'',)*9,(None,b'',b'\xff',b'wire',b'\x00\xfe',b'longer',None,b'x',b'\x80'))
        for ext in (False,True):
            for nested in (b'\xff',*(weapon_vfx(values) for values in cases)):
                for last in (bytes(4),b'\xff'*4,b'\x00\x00\xc0\x7f'):
                    child=tag37(nested,ext,last);r=Reader(child+b'\xaa','37');r.action(0)
                    self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],55)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='37-next')
                    self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
                    self.assertTrue(any(v.get('tag')==55 for v in row['completedRecords']))
            body=tag37(weapon_vfx(cases[-1]),ext);r=Reader(body,'37-order');r.action(0)
            nested_start=20 if ext else 18
            counts=[v for v in r.ranges if v['kind']=='count-i32']
            self.assertEqual(len(counts),9);self.assertEqual(counts[0]['start'],nested_start+10)
            flags=[v for v in r.ranges if nested_start+1<=v['start']<nested_start+10]
            self.assertEqual([v['end']-v['start'] for v in flags],[1]*9)
        for raw in (b'\xff',b'\x37\xff',b'\xfa\x37\x00\xff'):
            r=Reader(raw+b'\xaa','37-null');r.action(0);self.assertEqual(r.pos,len(raw))

    def test_37_all_cuts_and_required_byte_dword_after_null_nested(self):
        for ext in (False,True):
            child=tag37(weapon_vfx((b'x',None,b'',b'\xff\x80',b'wire',None,b'',b'y',None)),ext)
            for cut in range(len(child)):
                results=[]
                for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                    q=Reader(raw,'37-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==55 for v in q.records))
                    results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for nested in (b'\xff',weapon_vfx()):
                body=tag37(nested,ext)
                for missing in range(1,6):
                    q=Reader(body[:-missing],'37-tail')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['offset'],len(body)-(5 if missing==5 else 4))
                    self.assertEqual(caught.exception.diagnostic['expected'],{'bytes':1 if missing==5 else 4})
                    self.assertTrue(any(v['kind']=='anonymous-weapon-vfx-profile' for v in q.records))
                    self.assertFalse(any(v.get('tag')==55 for v in q.records))
            full=prefix(sequence(child))
            for cut in range(len(full)):
                row=event_prefix(full,source='37-limit',limit=cut);self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='37-limit',limit=cut))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_37_headers_all_nine_payload_lengths_and_parent_counts(self):
        for ext in (False,True):
            child=tag37(weapon_vfx((b'x',)*9),ext);r=Reader(child,'37-invalid');r.action(0)
            for span in r.ranges:
                if span['kind'] not in ('member-header','count-i32'):continue
                for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                    bad=bytearray(child);at=span['start']
                    if span['kind']=='member-header':bad[at]=invalid
                    else:struct.pack_into('<i',bad,at,invalid)
                    q=Reader(bad,'37-invalid')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['offset'],at);self.assertFalse(any(v.get('tag')==55 for v in q.records))
            for count in (-2,2147483647):
                with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_17_encodings_and_paired_states(self):
        self.assertEqual(len(tag17()),16);self.assertEqual(len(tag17(extended=True)),18)
        for extended in (False,True):
            for pair in (b'\xff',b'\x03'+payload(None)+b'\x80'+payload(None),
                         b'\x03'+payload(b'')+b'\xff'+payload(b''),b'\x03'+payload(b'\xff\x00')+b'\xfe'+payload(b'\x01\x80\xfa')):
                child=tag17(pair,extended)
                for tail in (b'\x00',b'\xff'):
                    for limit in (len(child),len(child)+1):
                        q=Reader(child+tail,'17',limit);q.action(0)
                        self.assertEqual(q.pos,len(child));self.assertEqual(q.records[-1]['tag'],23)
                        self.assertEqual(q.ranges[0]['start'],0);self.assertEqual(q.ranges[-1]['end'],len(child))
                        self.assertTrue(all(a['end']==b['start'] for a,b in zip(q.ranges,q.ranges[1:])))
            wrapper=(b'\xfa\x17\x00' if extended else b'\x17')+b'\xff'
            q=Reader(wrapper+b'\xa5','17-null');q.action(0);self.assertEqual(q.pos,len(wrapper))

    def test_17_every_cut_and_both_required_lengths(self):
        for extended in (False,True):
            for first,last in ((None,None),(b'',b''),(b'\xff\x00',b'\x01\x80\xfa')):
                pair=b'\x03'+payload(first)+b'\xfe'+payload(last);child=tag17(pair,extended)
                for cut in range(len(child)):
                    outcomes=[]
                    for data in (child[:cut],child,child[:cut]+b'\xff'*32):
                        q=Reader(data,'17-cut',cut)
                        with self.assertRaises(FrameError) as caught:q.action(0)
                        self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==23 for v in q.records))
                        outcomes.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                    self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[0],outcomes[2])
                first_offset=16+2*extended;last_offset=first_offset+5+len(first or b'')
                for offset in (first_offset,last_offset):
                    for count in (-2,2147483647):
                        q=Reader(child[:offset]+struct.pack('<i',count)+child[offset+4:],'17-count')
                        with self.assertRaises(FrameError) as caught:q.action(0)
                        self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                        self.assertEqual(caught.exception.diagnostic['offset'],offset);self.assertEqual(q.pos,offset+4)
                    for nbytes in range(4):
                        q=Reader(child[:offset+nbytes],'17-length-cut')
                        with self.assertRaises(FrameError) as caught:q.action(0)
                        self.assertEqual(caught.exception.diagnostic['offset'],offset);self.assertEqual(q.pos,offset)
                q=Reader(child[:last_offset-1],'17-required-byte')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],last_offset-1);self.assertEqual(q.pos,last_offset-1)

    def test_17_headers_and_required_profile(self):
        for extended in (False,True):
            child=tag17(extended=extended);h=1+2*extended
            for bad in (0,4,6,254):
                q=Reader(child[:h]+bytes([bad])+child[h+1:],'17-header')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],h)
            q=Reader(child[:-1],'17-profile-required')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-1)
            q=Reader(child[:-1]+b'\x02','17-paired-header')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-1)

    def test_17_parent_bounds_tails_and_unknown(self):
        for extended in (False,True):
            child=tag17(extended=extended)
            for parent in (b'\x03'+struct.pack('<i',-1)+b'\x80\xff',b'\x03'+struct.pack('<i',0)+b'\x80\xff',sequence(child)):
                q=Reader(parent,'17-parent');q.sequence();self.assertEqual(q.pos,len(parent))
                for k in (1,2):
                    q=Reader(parent[:-k],'17-parent-tail')
                    with self.assertRaises(FrameError) as caught:q.sequence()
                    self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
            for count in (-2,2147483647):
                q=Reader(b'\x03'+struct.pack('<i',count)+child+bytes(2),'17-parent-count')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(q.pos,5)
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            row=event_prefix(prefix(sequence(child,b'\xd0')),source='17-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],208)
            self.assertEqual(row['consumedEnd'],19+len(child));self.assertTrue(any(v.get('tag')==23 for v in row['completedRecords']))
        q=Reader(b'\x03'+struct.pack('<i',1)+b'\xff\x80','17-reserve2')
        with self.assertRaises(FrameError) as caught:q.sequence()
        self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(q.pos,5)

    def test_ce_both_encodings_nested_states_and_bits(self):
        self.assertEqual(len(tagce()),25);self.assertEqual(len(tagce(extended=True)),27)
        for extended in (False,True):
            for first,value,last in ((b'\xff',None,b'\xff'),(b'\xff',b'',b'\xff'),
                                     (target(),b'\xff\x00\x80',target(direction_value=b'\xff'))):
                for word in (bytes(4),b'\xff'*4,bytes.fromhex('0100C07F'),bytes.fromhex('04030281')):
                    child=tagce(first,value,last,extended,word)
                    for tail in (b'\x00',b'\xff'):
                        for limit in (len(child),len(child)+1):
                            q=Reader(child+tail,'ce',limit);q.action(0)
                            self.assertEqual(q.pos,len(child));self.assertEqual(q.records[-1]['tag'],206)
                            self.assertEqual(q.ranges[0]['start'],0);self.assertEqual(q.ranges[-1]['end'],len(child))
                            self.assertTrue(all(a['end']==b['start'] for a,b in zip(q.ranges,q.ranges[1:])))
            wrapper=(b'\xfa\xce\x00' if extended else b'\xce')+b'\xff'
            q=Reader(wrapper+b'\xa5','ce-null');q.action(0);self.assertEqual(q.pos,len(wrapper))

    def test_ce_all_cuts_and_required_final_target(self):
        for extended in (False,True):
            for first,value,last in ((b'\xff',None,b'\xff'),(b'\xff',b'',b'\xff'),
                                     (target(),b'\xfe\x00',target(direction_value=b'\xff'))):
                child=tagce(first,value,last,extended)
                for cut in range(len(child)):
                    outcomes=[]
                    for data in (child[:cut],child,child[:cut]+b'\xff'*32):
                        q=Reader(data,'ce-cut',cut)
                        with self.assertRaises(FrameError) as caught:q.action(0)
                        self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==206 for v in q.records))
                        outcomes.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                    self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[0],outcomes[2])
                q=Reader(child[:-len(last)],'ce-required-target')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(q.pos,len(child)-len(last));self.assertEqual(caught.exception.diagnostic['offset'],q.pos)

    def test_ce_payload_length_and_header_diagnostics(self):
        for extended in (False,True):
            child=tagce(extended=extended);offset=20+2*extended
            for count in (-2,2147483647):
                q=Reader(child[:offset]+struct.pack('<i',count)+child[offset+4:],'ce-length')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                self.assertEqual(caught.exception.diagnostic['offset'],offset);self.assertEqual(q.pos,offset+4)
            for nbytes in range(4):
                q=Reader(child[:offset+nbytes],'ce-length-cut')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],offset);self.assertEqual(q.pos,offset)
            for bad in (0,7,9,254):
                h=1+2*extended;q=Reader(child[:h]+bytes([bad])+child[h+1:],'ce-header')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],h)

    def test_ce_parent_counts_tails_unknown_and_trailing(self):
        for extended in (False,True):
            child=tagce(extended=extended)
            for parent in (b'\x03'+struct.pack('<i',-1)+b'\x80\xff',b'\x03'+struct.pack('<i',0)+b'\x80\xff',sequence(child)):
                q=Reader(parent,'ce-parent');q.sequence();self.assertEqual(q.pos,len(parent))
                for k in (1,2):
                    q=Reader(parent[:-k],'ce-parent-tail')
                    with self.assertRaises(FrameError) as caught:q.sequence()
                    self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
            for count in (-2,2147483647):
                q=Reader(b'\x03'+struct.pack('<i',count)+child+bytes(2),'ce-parent-count')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(q.pos,5)
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            row=event_prefix(prefix(sequence(child,b'\xd0')),source='ce-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],208)
            self.assertEqual(row['consumedEnd'],19+len(child));self.assertTrue(any(v.get('tag')==206 for v in row['completedRecords']))
        q=Reader(b'\x03'+struct.pack('<i',1)+b'\xff\x80','ce-reserve2')
        with self.assertRaises(FrameError) as caught:q.sequence()
        self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(q.pos,5)

    def test_18e_payload_states_order_and_boundaries(self):
        for values in ((None,)*8,(b'',)*8,tuple(bytes([i,255,128])*i for i in range(8))):
            child=tag18e(values);self.assertEqual(len(child),55+sum(len(v or b'') for v in values))
            for tail in (b'\x00',b'\xff'):
                for limit in (len(child),len(child)+1):
                    q=Reader(child+tail,'18e',limit);q.action(0)
                    self.assertEqual(q.pos,len(child));self.assertEqual(q.records[-1]['tag'],398)
                    self.assertEqual(q.ranges[0]['start'],0);self.assertEqual(q.ranges[-1]['end'],len(child))
                    self.assertTrue(all(a['end']==b['start'] for a,b in zip(q.ranges,q.ranges[1:])))
        for child in (b'\xff',b'\xfa\x8e\x01\xff'):
            q=Reader(child+b'\xa5','18e-null');q.action(0);self.assertEqual(q.pos,len(child))
        q=Reader(b'\x8e\xff','18e-short');q.action(0);self.assertEqual(q.records[-1]['tag'],142)

    def test_18e_every_cut_and_required_terminal_payloads(self):
        for values in ((None,)*8,(b'',)*8,tuple(bytes([i,255,128]) for i in range(8))):
            child=tag18e(values)
            for cut in range(len(child)):
                outcomes=[]
                for data in (child[:cut],child,child[:cut]+b'\xff'*32):
                    q=Reader(data,'18e-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==398 for v in q.records))
                    outcomes.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[0],outcomes[2])
        child=tag18e()
        for offset in (47,51):
            for count_bytes in range(4):
                q=Reader(child[:offset+count_bytes],'18e-length-cut')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],offset);self.assertEqual(q.pos,offset)

    def test_18e_all_payload_length_guards_and_headers(self):
        child=tag18e()
        for offset in (17,21,25,29,38,42,47,51):
            for count in (-2,2147483647):
                q=Reader(child[:offset]+struct.pack('<i',count)+child[offset+4:],'18e-count')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                self.assertEqual(caught.exception.diagnostic['offset'],offset);self.assertEqual(q.pos,offset+4)
                self.assertFalse(any(v.get('tag')==398 for v in q.records))
        for header in (0,17,19,254):
            q=Reader(child[:3]+bytes([header])+child[4:],'18e-header')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],3)

    def test_18e_parent_counts_tails_and_unknown_next(self):
        child=tag18e()
        for parent in (b'\x03'+struct.pack('<i',-1)+b'\x80\xff',b'\x03'+struct.pack('<i',0)+b'\x80\xff',sequence(child)):
            q=Reader(parent,'18e-parent');q.sequence();self.assertEqual(q.pos,len(parent))
            for k in (1,2):
                q=Reader(parent[:-k],'18e-parent-tail')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
        for count in (-2,2147483647):
            q=Reader(b'\x03'+struct.pack('<i',count)+child+bytes(2),'18e-parent-count')
            with self.assertRaises(FrameError) as caught:q.sequence()
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(q.pos,5)
        q=Reader(b'\x03'+struct.pack('<i',1)+b'\xff\x80','18e-reserve2')
        with self.assertRaises(FrameError) as caught:q.sequence()
        self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(q.pos,5)
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        row=event_prefix(prefix(sequence(child,b'\xd0')),source='18e-next')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],208)
        self.assertEqual(row['consumedEnd'],19+len(child));self.assertTrue(any(v.get('tag')==398 for v in row['completedRecords']))

    def test_102_scalar_order_bits_and_wrapper_identity(self):
        for word in (bytes(4),b'\xff'*4,bytes.fromhex('0100C07F'),bytes.fromhex('04030281')):
            child=tag102(word);self.assertEqual(len(child),21)
            for tail in (b'\x00',b'\xff'):
                for limit in (21,22):
                    q=Reader(child+tail,'102',limit);q.action(0)
                    self.assertEqual(q.pos,21);self.assertEqual(q.records[-1]['tag'],258)
                    self.assertEqual([(r['start'],r['end']) for r in q.ranges],[(0,3),(3,4),(4,5),(5,9),(9,13),(13,17),(17,21)])
        for child in (b'\xff',b'\xfa\x02\x01\xff'):
            q=Reader(child+b'\xaa','102-null');q.action(0);self.assertEqual(q.pos,len(child))
        q=Reader(b'\x02\xff','102-short');q.action(0)
        self.assertEqual(q.pos,2);self.assertEqual(q.records[-1]['tag'],2)

    def test_102_all_cuts_and_required_terminal_dword(self):
        child=tag102()
        for cut in range(len(child)):
            outcomes=[]
            for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(data,'102-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==258 for v in q.records))
                outcomes.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[0],outcomes[2])
        for k in range(1,5):
            q=Reader(child[:-k],'102-tail')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'truncated')
            self.assertEqual(caught.exception.diagnostic['offset'],17);self.assertEqual(q.pos,17)
        for bad in (0,4,6,254):
            q=Reader(child[:3]+bytes([bad])+child[4:],'102-header')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],3)
            self.assertFalse(any(v.get('tag')==258 for v in q.records))

    def test_102_parent_counts_tails_and_unknown_next(self):
        child=tag102()
        for parent in (b'\x03'+struct.pack('<i',-1)+b'\x80\xff',
                       b'\x03'+struct.pack('<i',0)+b'\x80\xff',sequence(child)):
            q=Reader(parent,'102-parent');q.sequence();self.assertEqual(q.pos,len(parent))
            for k in (1,2):
                q=Reader(parent[:-k],'102-parent-tail')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['category'],'truncated')
                self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
        for count in (-2,2147483647):
            q=Reader(b'\x03'+struct.pack('<i',count)+child+bytes(2),'102-count')
            with self.assertRaises(FrameError) as caught:q.sequence()
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
            self.assertEqual(caught.exception.diagnostic['offset'],1);self.assertEqual(q.pos,5)
        q=Reader(b'\x03'+struct.pack('<i',1)+b'\xff'+b'\x80','102-reserve2')
        with self.assertRaises(FrameError) as caught:q.sequence()
        self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
        self.assertEqual(caught.exception.diagnostic['offset'],1);self.assertEqual(q.pos,5)
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        row=event_prefix(prefix(sequence(child,b'\xd0')),source='102-next')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],208)
        self.assertEqual(row['consumedEnd'],19+len(child))
        self.assertTrue(any(v.get('tag')==258 for v in row['completedRecords']))

    def test_28_single_buffid_payload_states_and_encodings(self):
        self.assertEqual(len(tag28()),24);self.assertEqual(len(tag28(extended=True)),26)
        for extended in (False,True):
            for buff_id in (b'\xff',b'\x01'+payload(None),b'\x01'+payload(b''),b'\x01'+payload(b'\xff\x80id')):
                for value in (None,b'',b'\x00wire'):
                    child=tag28(buff_id,value,extended)
                    for tail in (b'\x00',b'\xff'):
                        for limit in (len(child),len(child)+1):
                            q=Reader(child+tail,'28',limit);q.action(0)
                            self.assertEqual(q.pos,len(child));self.assertEqual(q.records[-1]['tag'],40)
            child=b'\xfa\x28\x00\xff' if extended else b'\x28\xff'
            q=Reader(child+b'\xaa','28-null');q.action(0);self.assertEqual(q.pos,len(child))
        q=Reader(b'\xff\xaa','28-null-union');q.action(0);self.assertEqual(q.pos,1)

    def test_28_cuts_required_dword_and_payload_after_buffid(self):
        for extended in (False,True):
            for buff_id in (b'\xff',b'\x01'+payload(b'key\xff')):
                child=tag28(buff_id,b'wire',extended)
                for cut in range(len(child)):
                    results=[]
                    for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                        q=Reader(data,'28-cut',cut)
                        with self.assertRaises(FrameError) as caught:q.action(0)
                        self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==40 for v in q.records))
                        results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
                for k in range(1,5):
                    q=Reader(child[:-k],'28-required-dword')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['category'],'truncated')
                    self.assertEqual(caught.exception.diagnostic['offset'],len(child)-4)
                    self.assertEqual(q.pos,len(child)-4)
                    self.assertTrue(any(v['kind']=='anonymous-single-payload' for v in q.records))
                at=(17 if extended else 15)+len(buff_id)
                for k in range(4):
                    q=Reader(child,'28-required-payload',at+k)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['offset'],at);self.assertEqual(q.pos,at)

    def test_28_malformed_headers_counts_and_extended_tag(self):
        for extended in (False,True):
            child=tag28(b'\x01'+payload(b'key'),b'value',extended);r=Reader(child,'28-invalid');r.action(0)
            for span in r.ranges:
                if span['kind'] not in ('member-header','count-i32'):continue
                for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                    data=bytearray(child);at=span['start']
                    if span['kind']=='member-header':data[at]=invalid
                    else:struct.pack_into('<i',data,at,invalid)
                    q=Reader(data,'28-invalid')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['offset'],at)
                    self.assertFalse(any(v.get('tag')==40 for v in q.records))
        q=Reader(b'\xfa\x28\x01\xff','28-other-tag')
        # Extended 0x0128 remains the independently supported union296.
        q.action(0);self.assertEqual(q.records[-1]['tag'],296);self.assertEqual(q.pos,4)

    def test_28_parent_counts_required_tails_and_next_child(self):
        for extended in (False,True):
            child=tag28(b'\x01'+payload(b'key'),None,extended)
            for parent in (b'\x03'+struct.pack('<i',-1)+b'\x80\xff',
                           b'\x03'+struct.pack('<i',0)+b'\x80\xff',sequence(child)):
                q=Reader(parent,'28-parent');q.sequence();self.assertEqual(q.pos,len(parent))
                for k in (1,2):
                    q=Reader(parent[:-k],'28-parent-tail')
                    with self.assertRaises(FrameError) as caught:q.sequence()
                    self.assertEqual(caught.exception.diagnostic['category'],'truncated')
                    self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
            for count in (-2,2147483647):
                q=Reader(b'\x03'+struct.pack('<i',count)+child+b'\x80\xff','28-count')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                self.assertEqual(caught.exception.diagnostic['offset'],1);self.assertEqual(q.pos,5)
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            row=event_prefix(prefix(sequence(child,b'\xd0')),source='28-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],208)
            self.assertEqual(row['consumedEnd'],19+len(child))
            self.assertTrue(any(v.get('tag')==40 for v in row['completedRecords']))

    def test_172_payload_null_empty_nonempty_target_and_terminal_byte(self):
        self.assertEqual(len(tag172()),27)
        for first in (None,b'',b'\xff\x80key'):
            for second in (None,b'',b'wire\x00'):
                for t in (b'\xff',target(),target(direction_value=b'\xff')):
                    child=tag172(first,second,t)
                    for tail in (b'\x00',b'\xff'):
                        for limit in (len(child),len(child)+1):
                            q=Reader(child+tail,'172',limit);q.action(0)
                            self.assertEqual(q.pos,len(child));self.assertEqual(q.records[-1]['tag'],370)
        for child in (b'\xff',b'\xfa\x72\x01\xff'):
            q=Reader(child+b'\xaa','172-null');q.action(0);self.assertEqual(q.pos,len(child))
        q=Reader(b'\x72\xff','172-short')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],114);self.assertEqual(q.pos,0)

    def test_172_cuts_and_required_terminal_byte(self):
        for child in (tag172(),tag172(b'\xff\x00',b'key',target())):
            for cut in range(len(child)):
                results=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    q=Reader(data,'172-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==370 for v in q.records))
                    results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            q=Reader(child[:-1],'172-required-byte')
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'truncated')
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-1)
            self.assertEqual(q.pos,len(child)-1)

    def test_172_malformed_payloads_headers_and_unknown_target(self):
        child=tag172(b'wire',b'value',target());r=Reader(child,'172-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                data=bytearray(child);at=span['start']
                if span['kind']=='member-header':data[at]=invalid
                else:struct.pack_into('<i',data,at,invalid)
                q=Reader(data,'172-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v.get('tag')==370 for v in q.records))
        q=Reader(tag172(t=target(selector=b'\x03\x17'+bytes(8))),'172-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)

    def test_172_parent_counts_tails_and_unknown_next(self):
        child=tag172(b'x',b'',target())
        for parent in (b'\x03'+struct.pack('<i',-1)+b'\x80\xff',
                       b'\x03'+struct.pack('<i',0)+b'\x80\xff',sequence(child)):
            q=Reader(parent,'172-parent');q.sequence();self.assertEqual(q.pos,len(parent))
            for k in (1,2):
                q=Reader(parent[:-k],'172-parent-tail')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['category'],'truncated')
                self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k);self.assertEqual(q.pos,len(parent)-k)
        for count in (-2,2147483647):
            q=Reader(b'\x03'+struct.pack('<i',count)+child+b'\x80\xff','172-count')
            with self.assertRaises(FrameError) as caught:q.sequence()
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
            self.assertEqual(caught.exception.diagnostic['offset'],1);self.assertEqual(q.pos,5)
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        row=event_prefix(prefix(sequence(child,b'\xd0')),source='172-next')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],208)
        self.assertEqual(row['consumedEnd'],19+len(child))
        self.assertTrue(any(v.get('tag')==370 for v in row['completedRecords']))

    def test_166_nullable_lists_end_at_second_target_without_final_dword(self):
        for items in (None,(),(b'\xff',),(keyword19b(None),),(keyword19b((None,b'',b'\xff\x80'),scalar_payload(b'expr')),)):
            for first,second in ((b'\xff',b'\xff'),(target(),b'\xff'),(b'\xff',target()),(target(),target(direction_value=b'\xff'))):
                child=tag166(items,paired=pair(None,b'wire',255),first_scalar=scalar_payload(None),last_scalar=scalar_payload(b''),first=first,second=second)
                r=Reader(child+b'\xaa','166');r.action(0);self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],358)
                row=event_prefix(prefix(sequence(child,tag19b())),source='166-next')
                self.assertEqual(row['status'],'supported-prefix')
                self.assertEqual([v['tag'] for v in row['completedRecords'] if 'tag' in v],[358,411])
        # One null element leaves exactly byte + scalar + two target null wrappers.
        child=tag166((b'\xff',));r=Reader(child,'166-minimum-reserve');r.action(0);self.assertEqual(r.pos,len(child))
        for value in (None,(),(b'\xff',)):
            child=tag166(value);r=Reader(child+b'\xff'*4,'166-end');r.action(0)
            self.assertEqual(r.pos,len(child));self.assertLess(r.pos,r.limit)
        for raw in (b'\xff',b'\xfa\x66\x01\xff'):
            r=Reader(raw+b'\xaa','166-null');r.action(0);self.assertEqual(r.pos,len(raw))
        self.assertEqual(len(tag166()),29)
        r=Reader(b'\x66\xff','166-short')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],102);self.assertEqual(r.pos,0)

    def test_166_all_cuts_required_list_tail_and_parent_trailing(self):
        child=tag166((keyword19b((b'x',),scalar_payload(None)),),paired=pair(b'expr',b''),first=target(),second=target())
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'166-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==358 for v in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for items in (None,(),(b'\xff',)):
            body=tag166(items)
            for cut in range(len(body)-4,len(body)):
                q=Reader(body,'166-required-tail',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                # Positive counts fail at the reserve gate before entering the list.
                self.assertEqual(caught.exception.diagnostic['offset'],21 if items else cut)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds' if items else 'truncated')
                self.assertFalse(any(v.get('tag')==358 for v in q.records))
        full=prefix(sequence(child))
        for cut in range(len(full)):
            row=event_prefix(full,source='166-limit',limit=cut);self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='166-limit',limit=cut))
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_166_nested_headers_counts_and_unknown_target(self):
        child=tag166((keyword19b((None,b'x'),scalar_payload(b'v')),),paired=pair(b'key',None),first=target());r=Reader(child,'166-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'166-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at);self.assertFalse(any(v.get('tag')==358 for v in q.records))
        unknown=target(selector=b'\x03\x17'+bytes(8));q=Reader(tag166(None,second=unknown),'166-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        self.assertFalse(any(v.get('tag')==358 for v in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_166_parent_null_empty_required_tails_and_unknown_next(self):
        for parent in (b'\x03'+struct.pack('<i',-1)+b'\x80\xff',
                       b'\x03'+struct.pack('<i',0)+b'\x80\xff',sequence(tag166())):
            q=Reader(parent,'166-parent');q.sequence();self.assertEqual(q.pos,len(parent))
            for k in (1,2):
                q=Reader(parent[:-k],'166-parent-tail')
                with self.assertRaises(FrameError) as caught:q.sequence()
                self.assertEqual(caught.exception.diagnostic['category'],'truncated')
                self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-k)
                self.assertEqual(q.pos,len(parent)-k)
        row=event_prefix(prefix(sequence(tag166(),b'\xd0')),source='166-next')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],208)
        self.assertEqual(row['consumedEnd'],19+len(tag166()))
        self.assertTrue(any(v.get('tag')==358 for v in row['completedRecords']))

    def test_19c_nullable_lists_end_at_second_target_without_final_dword(self):
        for items in (None,(),(b'\xff',),(keyword19b(None),),(keyword19b((None,b'',b'\xff\x80'),scalar_payload(b'expr')),)):
            for first,second in ((b'\xff',b'\xff'),(target(),b'\xff'),(b'\xff',target()),(target(),target(direction_value=b'\xff'))):
                child=tag19c(items,paired=pair(None,b'wire',255),first_scalar=scalar_payload(None),last_scalar=scalar_payload(b''),first=first,second=second)
                r=Reader(child+b'\xaa','19c');r.action(0);self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],412)
                row=event_prefix(prefix(sequence(child,tag19b())),source='19c-next')
                self.assertEqual(row['status'],'supported-prefix')
                self.assertEqual([v['tag'] for v in row['completedRecords'] if 'tag' in v],[412,411])
        # One null element leaves exactly byte + scalar + two target null wrappers.
        child=tag19c((b'\xff',));r=Reader(child,'19c-minimum-reserve');r.action(0);self.assertEqual(r.pos,len(child))
        for value in (None,(),(b'\xff',)):
            child=tag19c(value);r=Reader(child+b'\xff'*4,'19c-end');r.action(0)
            self.assertEqual(r.pos,len(child));self.assertLess(r.pos,r.limit)
        for raw in (b'\xff',b'\xfa\x9c\x01\xff'):
            r=Reader(raw+b'\xaa','19c-null');r.action(0);self.assertEqual(r.pos,len(raw))
        self.assertEqual(len(tag19c()),29)
        r=Reader(b'\x9c\xff','19c-short')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],156);self.assertEqual(r.pos,0)

    def test_19c_all_cuts_required_list_tail_and_parent_trailing(self):
        child=tag19c((keyword19b((b'x',),scalar_payload(None)),),paired=pair(b'expr',b''),first=target(),second=target())
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'19c-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==412 for v in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for items in (None,(),(b'\xff',)):
            body=tag19c(items)
            for cut in range(len(body)-4,len(body)):
                q=Reader(body,'19c-required-tail',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                # Positive counts fail at the reserve gate before entering the list.
                self.assertEqual(caught.exception.diagnostic['offset'],21 if items else cut)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds' if items else 'truncated')
                self.assertFalse(any(v.get('tag')==412 for v in q.records))
        full=prefix(sequence(child))
        for cut in range(len(full)):
            row=event_prefix(full,source='19c-limit',limit=cut);self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='19c-limit',limit=cut))
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_19c_nested_headers_counts_and_unknown_target(self):
        child=tag19c((keyword19b((None,b'x'),scalar_payload(b'v')),),paired=pair(b'key',None),first=target());r=Reader(child,'19c-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'19c-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at);self.assertFalse(any(v.get('tag')==412 for v in q.records))
        unknown=target(selector=b'\x03\x17'+bytes(8));q=Reader(tag19c(None,second=unknown),'19c-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        self.assertFalse(any(v.get('tag')==412 for v in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_15d_nullable_lists_end_at_second_target_without_final_dword(self):
        for items in (None,(),(b'\xff',),(keyword19b(None),),(keyword19b((None,b'',b'\xff\x80'),scalar_payload(b'expr')),)):
            for first,second in ((b'\xff',b'\xff'),(target(),b'\xff'),(b'\xff',target()),(target(),target(direction_value=b'\xff'))):
                child=tag15d(items,paired=pair(None,b'wire',255),first_scalar=scalar_payload(None),last_scalar=scalar_payload(b''),first=first,second=second)
                r=Reader(child+b'\xaa','15d');r.action(0);self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],349)
                row=event_prefix(prefix(sequence(child,tag19b())),source='15d-next')
                self.assertEqual(row['status'],'supported-prefix')
                self.assertEqual([v['tag'] for v in row['completedRecords'] if 'tag' in v],[349,411])
        # One null element leaves exactly byte + scalar + two target null wrappers.
        child=tag15d((b'\xff',));r=Reader(child,'15d-minimum-reserve');r.action(0);self.assertEqual(r.pos,len(child))
        for value in (None,(),(b'\xff',)):
            child=tag15d(value);r=Reader(child+b'\xff'*4,'15d-end');r.action(0)
            self.assertEqual(r.pos,len(child));self.assertLess(r.pos,r.limit)
        for raw in (b'\xff',b'\xfa\x5d\x01\xff'):
            r=Reader(raw+b'\xaa','15d-null');r.action(0);self.assertEqual(r.pos,len(raw))
        # Short 5D remains the existing union93, not an alias of 349.
        r=Reader(b'\x5d\xff','15d-short');r.action(0);self.assertEqual(r.records[-1]['tag'],93)

    def test_15d_all_cuts_required_list_tail_and_parent_trailing(self):
        child=tag15d((keyword19b((b'x',),scalar_payload(None)),),paired=pair(b'expr',b''),first=target(),second=target())
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'15d-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==349 for v in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for items in (None,(),(b'\xff',)):
            body=tag15d(items)
            for cut in range(len(body)-4,len(body)):
                q=Reader(body,'15d-required-tail',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                # Positive counts fail at the reserve gate before entering the list.
                self.assertEqual(caught.exception.diagnostic['offset'],21 if items else cut)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds' if items else 'truncated')
                self.assertFalse(any(v.get('tag')==349 for v in q.records))
        full=prefix(sequence(child))
        for cut in range(len(full)):
            row=event_prefix(full,source='15d-limit',limit=cut);self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='15d-limit',limit=cut))
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_15d_nested_headers_counts_and_unknown_target(self):
        child=tag15d((keyword19b((None,b'x'),scalar_payload(b'v')),),paired=pair(b'key',None),first=target());r=Reader(child,'15d-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'15d-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at);self.assertFalse(any(v.get('tag')==349 for v in q.records))
        unknown=target(selector=b'\x03\x17'+bytes(8));q=Reader(tag15d(None,second=unknown),'15d-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        self.assertFalse(any(v.get('tag')==349 for v in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_14a_independent_null_objects_payloads_and_distinct_short_tag(self):
        profiles=(b'\xff',animator_param(),animator_param(b'\x00\x00\x80\xff',bytes(4),b'\x00',bytes(8)))
        for first in profiles:
            for second in profiles:
                for value in (None,b'',b'\xff\xfe\x00wire'):
                    child=tag14a(first,second,value);r=Reader(child+b'\xaa','14a');r.action(0)
                    self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],330)
                    nested=[v for v in r.records if v['kind']=='anonymous-animator-param-profile']
                    self.assertEqual([(v['start'],v['end']) for v in nested],[(18,18+len(first)),(18+len(first),18+len(first)+len(second))])
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='14a-next')
                    self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
                    self.assertTrue(any(v.get('tag')==330 for v in row['completedRecords']))
        for raw in (b'\xff',b'\xfa\x4a\x01\xff'):
            r=Reader(raw+b'\xaa','14a-null');r.action(0);self.assertEqual(r.pos,len(raw))
        q=Reader(b'\x4a\xff','14a-short')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],74);self.assertEqual(q.pos,0)

    def test_14a_all_cuts_required_nested_fields_and_terminal_length(self):
        child=tag14a(animator_param(),animator_param(),b'\xff\x80wire')
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'14a-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==330 for v in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for first,second in ((b'\xff',b'\xff'),(animator_param(),b'\xff'),(b'\xff',animator_param()),(animator_param(),animator_param())):
            for value in (None,b''):
                body=tag14a(first,second,value)
                for n in range(1,5):
                    q=Reader(body[:-n],'14a-length')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['expected'],{'bytes':4})
                    self.assertEqual(caught.exception.diagnostic['offset'],len(body)-4)
                    self.assertEqual(sum(v['kind']=='anonymous-animator-param-profile' for v in q.records),2)
                    self.assertFalse(any(v.get('tag')==330 for v in q.records))
        for cut,offset in ((50,50),(53,50),(36,36),(35,32)):
            q=Reader(child,'14a-nested-tail',cut)
            with self.assertRaises(FrameError) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],offset)
            self.assertEqual(sum(v['kind']=='anonymous-animator-param-profile' for v in q.records),int(cut>=36))
        full=prefix(sequence(child))
        for cut in range(len(full)):
            row=event_prefix(full,source='14a-limit',limit=cut)
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='14a-limit',limit=cut))
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_14a_headers_payload_lengths_and_parent_counts(self):
        child=tag14a(animator_param(),animator_param(),b'wire');r=Reader(child,'14a-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'14a-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v.get('tag')==330 for v in q.records))
                self.assertEqual(sum(v['kind']=='anonymous-animator-param-profile' for v in q.records),0 if at<=18 else 1 if at==36 else 2)
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_133_nested_nulls_payload_states_and_distinct_short_tag(self):
        for nested in (b'\xff',target(),target(direction_value=b'\xff')):
            for finder in (b'\xff',finder14d(),finder14d(None,None),finder14d((),())):
                for value in (None,b'',b'\xff\xfe\x00wire'):
                    child=tag133(nested,finder,value);r=Reader(child+b'\xaa','133');r.action(0)
                    self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],307)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='133-next')
                    self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
                    self.assertTrue(any(v.get('tag')==307 for v in row['completedRecords']))
        for raw in (b'\xff',b'\xfa\x33\x01\xff'):
            r=Reader(raw+b'\xaa','133-null');r.action(0);self.assertEqual(r.pos,len(raw))
        q=Reader(b'\x33\xff','133-short')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],51);self.assertEqual(q.pos,0)

    def test_133_all_cuts_and_required_final_payload_length(self):
        child=tag133(target(),finder14d(),b'\xff\x80wire')
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'133-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==307 for v in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for nested,finder in ((b'\xff',b'\xff'),(target(),finder14d())):
            for value in (None,b''):
                body=tag133(nested,finder,value)
                for n in range(1,5):
                    q=Reader(body[:-n],'133-length')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['expected'],{'bytes':4})
                    self.assertEqual(caught.exception.diagnostic['offset'],len(body)-4)
                    self.assertTrue(any(v['kind']=='anonymous-finder-profile' for v in q.records))
                    self.assertFalse(any(v.get('tag')==307 for v in q.records))
        full=prefix(sequence(child))
        for cut in range(len(full)):
            row=event_prefix(full,source='133-limit',limit=cut)
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='133-limit',limit=cut))
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_133_nested_headers_counts_payload_lengths_and_unknown_target(self):
        child=tag133(target(),finder14d(),b'wire');r=Reader(child,'133-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'133-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v.get('tag')==307 for v in q.records))
        unknown=target(selector=b'\x03\x17'+bytes(8));q=Reader(tag133(unknown),'133-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        self.assertFalse(any(v.get('tag')==307 for v in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_f4_both_encodings_and_independent_scalar_bits(self):
        for first,last in ((b'\xff'*4,bytes(4)),(bytes(4),b'\xff'*4),(b'\x80'*4,b'\xfe'*4)):
            for extended in (False,True):
                child=tagf4(first,last,extended);r=Reader(child+b'\xaa','f4');r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(len(child),25 if extended else 23)
                self.assertEqual(r.records[-1]['tag'],244)
                self.assertEqual([v['end']-v['start'] for v in r.ranges[-2:]],[4,4])
                self.assertEqual([v['kind'] for v in r.ranges[-2:]],['anonymous-scalar32']*2)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='f4-next')
                self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
                self.assertTrue(any(v.get('tag')==244 for v in row['completedRecords']))
        for raw in (b'\xff',b'\xf4\xff',b'\xfa\xf4\x00\xff'):
            r=Reader(raw+b'\xaa','f4-null');r.action(0);self.assertEqual(r.pos,len(raw))

    def test_f4_all_cuts_required_scalar_tails_and_parent_boundaries(self):
        for extended in (False,True):
            child=tagf4(extended=extended)
            for cut in range(len(child)):
                results=[]
                for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                    q=Reader(raw,'f4-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==244 for v in q.records))
                    results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for n in range(1,9):
                q=Reader(child[:-n],'f4-required')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['expected'],{'bytes':4})
                self.assertEqual(caught.exception.diagnostic['offset'],len(child)-(4 if n<=4 else 8))
                self.assertFalse(any(v.get('tag')==244 for v in q.records))
            full=prefix(sequence(child))
            for cut in range(len(full)):
                row=event_prefix(full,source='f4-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='f4-limit',limit=cut))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_f4_header_and_parent_count_fail_at_source(self):
        for extended in (False,True):
            child=tagf4(extended=extended);at=3 if extended else 1
            for header in (0,5,7,254):
                bad=bytearray(child);bad[at]=header;q=Reader(bad,'f4-header')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v.get('tag')==244 for v in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+tagf4()+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_b9_encodings_required_byte_and_target_endpoint(self):
        for nested in (b'\xff',target(),target(direction_value=b'\xff')):
            for flag in (b'\x00',b'\xff',b'\xfe',b'\x80'):
                for extended in (False,True):
                    child=tagb9(nested,flag,extended);r=Reader(child+b'\xaa','b9');r.action(0)
                    self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],185)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='b9-next')
                    self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
                    self.assertTrue(any(v.get('tag')==185 for v in row['completedRecords']))
        for raw in (b'\xff',b'\xb9\xff',b'\xfa\xb9\x00\xff'):
            r=Reader(raw+b'\xaa','b9-null');r.action(0);self.assertEqual(r.pos,len(raw))

    def test_b9_all_cuts_and_parent_trailing(self):
        for extended in (False,True):
            child=tagb9(target(),extended=extended)
            for cut in range(len(child)):
                results=[]
                for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                    q=Reader(raw,'b9-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==185 for v in q.records))
                    results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            # Even an FF scalar byte requires a following target header.
            for n in (1,2):
                q=Reader(tagb9(extended=extended)[:-n],'b9-required')
                with self.assertRaises(FrameError):q.action(0)
                self.assertFalse(any(v.get('tag')==185 for v in q.records))
            full=prefix(sequence(child))
            for cut in range(len(full)):
                row=event_prefix(full,source='b9-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='b9-limit',limit=cut))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_b9_nested_header_count_and_unknown_target_boundaries(self):
        child=tagb9(target());r=Reader(child,'b9-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'b9-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v.get('tag')==185 for v in q.records))
        unknown=target(selector=b'\x03\x17'+bytes(8));q=Reader(tagb9(unknown),'b9-target-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        self.assertFalse(any(v.get('tag')==185 for v in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_186_target_nulls_and_two_independent_scalar_tails(self):
        for nested in (b'\xff',target(),target(direction_value=b'\xff')):
            for first,last in ((b'\xff'*4,bytes(4)),(bytes(4),b'\xff'*4),(b'\x80'*4,b'\xfe'*4)):
                child=tag186(nested,first,last);r=Reader(child+b'\xaa','186');r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],390)
                self.assertEqual([v['end']-v['start'] for v in r.ranges[-2:]],[4,4])
                self.assertEqual([v['kind'] for v in r.ranges[-2:]],['anonymous-scalar32']*2)
                row=event_prefix(prefix(sequence(child,b'\x86\xff')),source='186-identity')
                self.assertEqual(row['status'],'supported-prefix')
                self.assertEqual([v['tag'] for v in row['completedRecords'] if 'tag' in v],[390,134])
                row=event_prefix(prefix(sequence(child,b'\x59')),source='186-next')
                self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
        for raw in (b'\xff',b'\xfa\x86\x01\xff'):
            r=Reader(raw+b'\xaa','186-null');r.action(0);self.assertEqual(r.pos,len(raw))

    def test_186_all_cuts_both_dwords_required_and_parent_trailing(self):
        child=tag186(target());r=Reader(child,'186');r.action(0)
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                q=Reader(raw,'186-cut',cut)
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertLessEqual(q.pos,cut);self.assertFalse(any(v.get('tag')==390 for v in q.records))
                results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for nested in (b'\xff',target()):
            for n in range(1,9):
                q=Reader(tag186(nested)[:-n],'186-tail')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['expected'],{'bytes':4})
                self.assertTrue(any(v['kind']=='anonymous-target-profile' for v in q.records))
                self.assertFalse(any(v.get('tag')==390 for v in q.records))
        full=prefix(sequence(child))
        for cut in range(len(full)):
            row=event_prefix(full,source='186-limit',limit=cut)
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='186-limit',limit=cut))
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_186_nested_header_count_and_unknown_target_boundaries(self):
        child=tag186(target());r=Reader(child,'186-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'186-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v.get('tag')==390 for v in q.records))
        unknown=target(selector=b'\x03\x17'+bytes(8));q=Reader(tag186(unknown),'186-target-unknown')
        with self.assertRaises(Unsupported) as caught:q.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
        self.assertFalse(any(v.get('tag')==390 for v in q.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_17c_sequence_nulls_profiles_and_distinct_short_tag(self):
        for nested in (b'\xff',b'\x03'+struct.pack('<i',-1)+b'\xff\xfe',sequence(),
                       sequence(b'\xff'),sequence(tag17c(),b'\x7c\xff')):
            for scalar,nested_target in ((b'\xff',b'\xff'),(scalar_payload(None),target()),
                                         (scalar_payload(b'expr'),target(direction_value=b'\xff'))):
                child=tag17c(nested,scalar,nested_target);r=Reader(child+b'\xaa','17c');r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],380)
                row=event_prefix(prefix(sequence(child,b'\x7c\xff')),source='17c-identity')
                self.assertEqual(row['status'],'supported-prefix')
                self.assertEqual([v['tag'] for v in row['completedRecords'] if 'tag' in v][-2:],[380,124])
                row=event_prefix(prefix(sequence(child,b'\x59')),source='17c-next')
                self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
        for raw in (b'\xff',b'\xfa\x7c\x01\xff'):
            r=Reader(raw+b'\xaa','17c-null');r.action(0);self.assertEqual(r.pos,len(raw))

    def test_17c_all_cuts_final_byte_and_parent_tails(self):
        child=tag17c(sequence(b'\xff',tag17c()),scalar_payload(b'wire'),target())
        for cut in range(len(child)):
            results=[]
            for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                r=Reader(raw,'17c-cut',cut)
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertLessEqual(r.pos,cut)
                self.assertFalse(any(v.get('tag')==380 and v['start']==0 for v in r.records))
                results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for nested_target in (b'\xff',target()):
            r=Reader(tag17c(sequence(b'\xff'),last_target=nested_target,last=b''),'17c-final-byte')
            with self.assertRaises(FrameError):r.action(0)
            self.assertTrue(any(v['kind']=='sequence' for v in r.records))
            self.assertFalse(any(v.get('tag')==380 for v in r.records))
        full=prefix(sequence(child))
        for cut in range(len(full)):
            row=event_prefix(full,source='17c-limit',limit=cut)
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='17c-limit',limit=cut))
        for tail in (b'\x00',b'\xff'):
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
            self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_17c_nested_header_count_and_unknown_child_boundaries(self):
        child=tag17c(sequence(b'\xff',tag17c()),scalar_payload(b'wire'),target())
        r=Reader(child,'17c-invalid');r.action(0)
        for span in r.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                q=Reader(bad,'17c-invalid')
                with self.assertRaises(FrameError) as caught:q.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v.get('tag')==380 and v['start']==0 for v in q.records))
        nested=sequence(b'\xff',b'\x59');r=Reader(tag17c(nested),'17c-child-unknown')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],23);self.assertEqual(r.pos,23)
        self.assertTrue(any(v.get('tag')==255 for v in r.records))
        self.assertFalse(any(v.get('tag')==380 or v['kind']=='sequence' for v in r.records))
        unknown=target(selector=b'\x03\x17'+bytes(8));r=Reader(tag17c(sequence(b'\xff'),last_target=unknown),'17c-target-unknown')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(r.target_depth,0)
        self.assertTrue(any(v['kind']=='sequence' for v in r.records))
        self.assertFalse(any(v.get('tag')==380 for v in r.records))

    def test_17c_recursive_sequence_depth_remains_bounded(self):
        child=tag17c()
        for _ in range(66):child=tag17c(sequence(child))
        row=event_prefix(prefix(sequence(child)),source='17c-depth')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'depth-limit')
        self.assertEqual(row['diagnostic']['actual'],65)
        self.assertFalse(any(v.get('tag')==380 for v in row['completedRecords']))

    def test_f6_profiles_nulls_and_two_independent_subspeed_members(self):
        for wire in (b'\xf6',b'\xfa\xf6\x00'):
            for overrides in ({},{19:b'\xff',35:b'\xff',40:b'\xff',45:b'\xff',46:b'\xff'},
                              {45:b'\xff',46:subspeedf6()}, {45:subspeedf6(),46:b'\xff'}):
                child=tagf6(overrides,wire);r=Reader(child+b'\xaa','f6');r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],246)
                raw12=[v for v in r.ranges if v['kind']=='anonymous-raw12']
                self.assertEqual(len(raw12),1);self.assertEqual(raw12[0]['end']-raw12[0]['start'],12)
                subs=[v for v in r.records if v['kind']=='anonymous-scalar-payload-curve-profile']
                self.assertEqual(len(subs),2);self.assertEqual(subs[0]['end'],subs[1]['start'])
                self.assertEqual(subs[1]['end'],len(child))
                row=event_prefix(prefix(sequence(child,b'\xff')),source='f6-next-null')
                self.assertEqual(row['status'],'supported-prefix')
                row=event_prefix(prefix(sequence(child,b'\x59')),source='f6-next-unknown')
                self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
        for raw in (b'\xff',b'\xf6\xff',b'\xfa\xf6\x00\xff'):
            r=Reader(raw+b'\xaa','f6-null');r.action(0);self.assertEqual(r.pos,len(raw))

    def test_f6_every_cut_and_required_parent_and_subspeed_tails(self):
        for wire in (b'\xf6',b'\xfa\xf6\x00'):
            child=tagf6(wire=wire)
            for cut in range(len(child)):
                results=[]
                for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(raw,'f6-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==246 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            # Removing either entire required final reference is not a nullable encoding.
            for overrides in ({45:b'',46:b'\xff'},{45:b'\xff',46:b''}):
                r=Reader(tagf6(overrides,wire),'f6-missing-ref')
                with self.assertRaises(FrameError):r.action(0)
                self.assertFalse(any(v.get('tag')==246 for v in r.records))
            for n in range(1,5):
                sub=subspeedf6(curve=curve24((bytes(28),)))[:-n]
                r=Reader(tagf6({46:sub},wire),'f6-sub-final-dword')
                with self.assertRaises(FrameError):r.action(0)
                self.assertFalse(any(v.get('tag')==246 for v in r.records))
            full=prefix(sequence(child))
            for cut in range(len(full)):
                row=event_prefix(full,source='f6-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='f6-limit',limit=cut))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_f6_nested_headers_counts_and_unknown_target_fail_closed(self):
        for wire in (b'\xf6',b'\xfa\xf6\x00'):
            child=tagf6(wire=wire);r=Reader(child,'f6-invalid');r.action(0)
            for span in r.ranges:
                if span['kind'] not in ('member-header','count-i32'):continue
                for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                    bad=bytearray(child);at=span['start']
                    if span['kind']=='member-header':bad[at]=invalid
                    else:struct.pack_into('<i',bad,at,invalid)
                    q=Reader(bad,'f6-invalid')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['offset'],at)
                    self.assertFalse(any(v.get('tag')==246 for v in q.records))
            unknown=target(selector=b'\x03\x17'+bytes(8));q=Reader(tagf6({40:unknown},wire),'f6-unknown')
            with self.assertRaises(Unsupported) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
            self.assertFalse(any(v.get('tag')==246 for v in q.records))
            for count in (-2,2147483647):
                with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_ab_shared_field_order_keeps_distinct_action_identity(self):
        for wire in (b'\xab',b'\xfa\xab\x00'):
            for items in (None,(),(b'\xff',keyword19b(None)),(keyword19b((None,b'',b'\xff\x80'),scalar_payload(b'expr')),)):
                body=tag19b(items,paired=pair(None,b'wire',255),first_scalar=scalar_payload(None),last_scalar=scalar_payload(b''),first=target(),second=target(direction_value=b'\xff'))[3:]
                child=wire+body;r=Reader(child+b'\xaa','ab');r.action(0);self.assertEqual(r.pos,len(child))
                self.assertEqual(r.records[-1]['tag'],171)
                row=event_prefix(prefix(sequence(child,tag19b())),source='ab-identity')
                self.assertEqual(row['status'],'supported-prefix')
                self.assertEqual([v['tag'] for v in row['completedRecords'] if 'tag' in v],[171,411])
                row=event_prefix(prefix(sequence(child,b'\x59')),source='ab-next')
                self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
        for raw in (b'\xff',b'\xab\xff',b'\xfa\xab\x00\xff'):
            r=Reader(raw+b'\xaa','ab-null');r.action(0);self.assertEqual(r.pos,len(raw))

    def test_ab_all_cuts_required_tail_and_parent_trailing(self):
        for wire in (b'\xab',b'\xfa\xab\x00'):
            child=wire+tag19b((keyword19b((b'x',),scalar_payload(None)),),paired=pair(b'expr',b''),first=target())[3:]
            for cut in range(len(child)):
                results=[]
                for raw in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(raw,'ab-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==171 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            full=prefix(sequence(child))
            for cut in range(len(full)):
                row=event_prefix(full,source='ab-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='ab-limit',limit=cut))
            for n in range(1,5):
                r=Reader(wire+tag19b(None)[3:-n],'ab-final-dword')
                with self.assertRaises(FrameError):r.action(0)
                self.assertFalse(any(v.get('tag')==171 for v in r.records))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_ab_nested_count_length_header_and_unknown_target_gates(self):
        for wire in (b'\xab',b'\xfa\xab\x00'):
            child=wire+tag19b((keyword19b((None,b'x'),scalar_payload(b'v')),),paired=pair(b'key',None),first=target())[3:]
            r=Reader(child,'ab-invalid');r.action(0)
            for span in r.ranges:
                if span['kind'] not in ('member-header','count-i32'):continue
                for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                    bad=bytearray(child);at=span['start']
                    if span['kind']=='member-header':bad[at]=invalid
                    else:struct.pack_into('<i',bad,at,invalid)
                    q=Reader(bad,'ab-invalid')
                    with self.assertRaises(FrameError) as caught:q.action(0)
                    self.assertEqual(caught.exception.diagnostic['offset'],at)
                    self.assertFalse(any(v.get('tag')==171 for v in q.records))
            unknown=target(selector=b'\x03\x17'+bytes(8))
            q=Reader(wire+tag19b(None,second=unknown)[3:],'ab-unknown')
            with self.assertRaises(Unsupported) as caught:q.action(0)
            self.assertEqual(caught.exception.diagnostic['actual'],23);self.assertEqual(q.target_depth,0)
            self.assertFalse(any(v.get('tag')==171 for v in q.records))
            for count in (-2,2147483647):
                with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+child+bytes(2))
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)

    def test_127_target_profile_nulls_and_distinct_short_action(self):
        base=b'\xfa\x27\x01\x05\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)
        for nested in (b'\xff',target(),target(direction_value=b'\xff'),target(selector=b'\x03\x00\x00'+bytes(8))):
            child=base+nested;r=Reader(child+b'\xaa','127');r.action(0)
            self.assertEqual(r.pos,len(child));self.assertEqual(r.records[-1]['tag'],295)
            row=event_prefix(prefix(sequence(child,tag27())),source='127-short')
            self.assertEqual(row['status'],'supported-prefix')
            self.assertEqual([r['tag'] for r in row['completedRecords'] if 'tag' in r],[295,39])
            row=event_prefix(prefix(sequence(child,b'\x59')),source='127-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
            self.assertTrue(any(r.get('tag')==295 for r in row['completedRecords']))
        for value in (b'\xff',b'\xfa\x27\x01\xff'):
            r=Reader(value+b'\xaa','127-null');r.action(0);self.assertEqual(r.pos,len(value))

    def test_127_all_cuts_limits_and_parent_trailing(self):
        for child in (b'\xff',b'\xfa\x27\x01\xff',b'\xfa\x27\x01\x05'+b'\xff'*13+b'\xff',b'\xfa\x27\x01\x05'+bytes(13)+target()):
            for cut in range(len(child)):
                results=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(data,'127-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==295 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            full=prefix(sequence(child))
            for cut in range(len(full)):
                row=event_prefix(full,source='127-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='127-limit',limit=cut))
            for tail in (b'x',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_127_headers_target_lengths_counts_and_missing_target(self):
        base=b'\xfa\x27\x01\x05'+bytes(13)
        for header in (0,4,6,254):
            r=Reader(base[:3]+bytes([header])+base[4:]+b'\xff','127-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic,dict(source='127-header',offset=3,expected=5,actual=header,category='member-count'))
        r=Reader(base,'127-missing-target')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],17)
        self.assertFalse(any(v.get('tag')==295 for v in r.records))
        for length in (-2,2147483647):
            r=Reader(base+b'\x0d\xff'+struct.pack('<i',length)+bytes(20),'127-target-length')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],19)
            self.assertFalse(any(v.get('tag')==295 for v in r.records))
        for count in (-2,2147483647):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+base+b'\xff'+bytes(2))
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds');self.assertEqual(caught.exception.diagnostic['offset'],1)
        r=Reader(base+target(selector=b'\x03\x17'+bytes(8)),'127-nested-unknown')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'nested-profile')
        self.assertEqual(caught.exception.diagnostic['actual'],23)
        self.assertFalse(any(v.get('tag')==295 for v in r.records));self.assertEqual(r.target_depth,0)

    def test_12b_fixed_record_and_distinct_short_action(self):
        child=b'\xfa\x2b\x01\x04\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)
        reader=Reader(child,'12b.bin');reader.action(0)
        self.assertEqual(reader.pos,17)
        self.assertEqual(reader.records[-1]['tag'],299)
        row=event_prefix(prefix(sequence(child,tag2b())),source='12b-short.bin')
        self.assertEqual(row['status'],'supported-prefix')
        self.assertEqual([r['tag'] for r in row['completedRecords'] if 'tag' in r],[299,43])
        for raw in (b'\xfa\x2b\x01\xff',b'\xff'):
            reader=Reader(raw,'12b-null.bin');reader.action(0);self.assertEqual(reader.pos,len(raw))
        row=event_prefix(prefix(sequence(child,b'\x59')),source='12b-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['consumedEnd'],36)
        self.assertTrue(any(r.get('tag')==299 for r in row['completedRecords']))

    def test_12b_every_cut_hard_limit_and_trailing(self):
        child=b'\xfa\x2b\x01\x04'+b'\xff'*13
        for n in range(len(child)):
            reader=Reader(child[:n],'12b-cut.bin')
            with self.subTest(n=n),self.assertRaises(FrameError):reader.action(0)
            self.assertFalse(any(r.get('tag')==299 for r in reader.records))
        full=prefix(sequence(child))
        for n in range(len(full)):
            row=event_prefix(full,source='12b-limit.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='12b-limit.bin',limit=n))
        with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_12b_wrong_header_parent_count_and_missing_final_dword(self):
        child=b'\xfa\x2b\x01\x04'+bytes(13)
        for header in (0,3,5,254):
            bad=child[:3]+bytes([header])+child[4:]
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='12b-header.bin')
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']), (8,header))
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        for count in (-2,2147483647):
            bad=b'\x03'+struct.pack('<i',count)+child+bytes(2)
            with self.assertRaises(FrameError) as caught:sequence_frame(bad,source='12b-count.bin')
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
            self.assertEqual(caught.exception.diagnostic['offset'],1)
        reader=Reader(child[:-4],'12b-last.bin')
        with self.assertRaises(FrameError) as caught:reader.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],13)
        self.assertFalse(any(r.get('tag')==299 for r in reader.records))

    def test_cf_vector_bits_target_and_required_payload(self):
        for raw8 in (bytes(8),bytes.fromhex('0000C07F000080FF'),b'\xff'*8):
            for value in (None,b'',b'\xff\xfe\x00payload'):
                for nested in (b'\xff',target()):
                    child=tagcf(nested,value,raw8)
                    row=event_prefix(prefix(sequence(child)),source='cf.bin')
                    self.assertEqual(row['status'],'supported-prefix')
                    r=next(r for r in row['completedRecords'] if r.get('tag')==207)
                    self.assertEqual((r['start'],r['end']),(19,19+len(child)))
        for child in (b'\xcf\xff',b'\xfa\xcf\x00'+tagcf()[1:]):
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        reader=Reader(tagcf()[:-4],'cf-required.bin')
        with self.assertRaises(FrameError) as caught:reader.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],34)
        self.assertFalse(any(r.get('tag')==207 for r in reader.records))

    def test_cf_all_cuts_hard_limits_and_trailing(self):
        raw=sequence(tagcf(target(),b'\xff\x00value'))
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n],source='cf-cut.bin')
        full=prefix(raw)
        for n in range(len(full)):
            row=event_prefix(full,source='cf-limit.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='cf-limit.bin',limit=n))
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_cf_malformed_headers_and_payload_lengths(self):
        for count in (-2,2147483647):
            raw=tagcf()[:-4]+struct.pack('<i',count)
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(raw),source='cf-length.bin')
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],
                              caught.exception.diagnostic['category']),(39,count,'count-bounds'))
        good=prefix(sequence(tagcf(target(),b'value')))
        row=event_prefix(good,source='cf-bad.bin')
        for r in row['ranges']:
            if r['kind'] not in ('member-header','count-i32'):continue
            bad=bytearray(good);at=r['start']
            if r['kind']=='member-header':bad[at]=42
            else:struct.pack_into('<i',bad,at,2147483647)
            result=event_prefix(bad,source='cf-bad.bin')
            self.assertEqual(result['status'],'failed')
            self.assertEqual(result['diagnostic']['offset'],at)

    def test_cf_unknown_target_and_later_unknown_action(self):
        unknown=b'\x0d\xff'+payload(None)+bytes(6)+payload(None)+b'\x03\x17'
        row=event_prefix(prefix(sequence(tagcf(unknown))),source='cf-target.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['consumedEnd'],19+33+len(unknown)-1)
        self.assertFalse(any(r.get('tag')==207 for r in row['completedRecords']))
        child=tagcf(target(),b'last')
        row=event_prefix(prefix(sequence(child,b'\x59')),source='cf-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['consumedEnd'],19+len(child))
        self.assertTrue(any(r.get('tag')==207 for r in row['completedRecords']))

    def test_164_fixed_record_null_wrapper_and_no_following_field(self):
        child=b'\xfa\x64\x01\x04\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)
        reader=Reader(child,'164.bin');reader.action(0)
        self.assertEqual(reader.pos,17)
        self.assertEqual(reader.records[-1]['tag'],356)
        self.assertEqual(sequence_frame(sequence(child))[-1]['end'],24)
        for raw in (b'\xfa\x64\x01\xff',b'\xff'):
            reader=Reader(raw,'164-null.bin');reader.action(0);self.assertEqual(reader.pos,len(raw))
        row=event_prefix(prefix(sequence(child,b'\x59')),source='164-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['consumedEnd'],36)
        self.assertTrue(any(r.get('tag')==356 for r in row['completedRecords']))

    def test_164_every_cut_hard_limit_and_trailing(self):
        child=b'\xfa\x64\x01\x04'+b'\xff'*13
        for n in range(len(child)):
            reader=Reader(child[:n],'164-cut.bin')
            with self.subTest(n=n),self.assertRaises(FrameError):reader.action(0)
            self.assertFalse(any(r.get('tag')==356 for r in reader.records))
        full=prefix(sequence(child))
        for n in range(len(full)):
            row=event_prefix(full,source='164-limit.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='164-limit.bin',limit=n))
        with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_164_wrong_header_parent_count_and_distinct_tag(self):
        child=b'\xfa\x64\x01\x04'+bytes(13)
        for header in (0,3,5,254):
            bad=child[:3]+bytes([header])+child[4:]
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='164-header.bin')
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']), (8,header))
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        for count in (-2,2147483647):
            bad=b'\x03'+struct.pack('<i',count)+child+bytes(2)
            with self.assertRaises(FrameError) as caught:sequence_frame(bad,source='164-count.bin')
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
            self.assertEqual(caught.exception.diagnostic['offset'],1)
        # Dropping the high tag byte must not alias the recovered extended action.
        row=event_prefix(prefix(sequence(b'\x64'+child[3:])),source='164-alias.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],100)
        self.assertEqual(row['consumedEnd'],19)

    def test_128_config_calculations_and_terminal_target(self):
        calculations=(b'\xff',b'\x00\xff',b'\x00\x01'+scalar_payload(None),
                      b'\x02\x03\xfe'+scalar_payload(b'')+scalar_payload(),
                      b'\x03\x04'+scalar_payload()+bytes(4)+scalar_payload(None)+bytes(4))
        for effect in (b'\xff',effect85()):
            for calc in calculations:
                child=tag128(effect,calc,target())
                row=event_prefix(prefix(sequence(child)),source='128.bin')
                self.assertEqual(row['status'],'supported-prefix')
                record=next(r for r in row['completedRecords'] if r.get('tag')==296)
                self.assertEqual((record['start'],record['end']),(19,19+len(child)))
        for child in (tag128(),b'\xfa\x28\x01\xff'):
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_128_all_cuts_limits_and_trailing(self):
        raw=sequence(tag128(effect85(),b'\x00\x01'+scalar_payload(),target()))
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):
                sequence_frame(raw[:n],source='128-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='128-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            row=event_prefix(full,source='128-limit.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='128-limit.bin',limit=n))

    def test_128_bad_headers_and_nested_lengths(self):
        raw=prefix(sequence(tag128(effect85(),b'\x00\x01'+scalar_payload(),target())))
        good=event_prefix(raw,source='128-bad.bin')
        for r in good['ranges']:
            if r['kind'] not in ('count-i32','member-header'):continue
            for value in ((-2,2147483647) if r['kind']=='count-i32' else (42,)):
                bad=bytearray(raw);at=r['start']
                if r['kind']=='count-i32':struct.pack_into('<i',bad,at,value)
                else:bad[at]=value
                row=event_prefix(bad,source='128-bad.bin')
                with self.subTest(at=at,value=value):
                    self.assertEqual(row['status'],'failed')
                    self.assertEqual(row['diagnostic']['offset'],at)
                    self.assertEqual(row['diagnostic']['actual'],value)

    def test_128_unknown_children_and_missing_final_target(self):
        reader=Reader(tag128()[:-1],'128-missing.bin')
        with self.assertRaises(FrameError) as caught:reader.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],29)
        self.assertFalse(any(r.get('tag')==296 for r in reader.records))
        unknown=b'\x0d\xff'+payload(None)+bytes(6)+payload(None)+b'\x03\x17'
        for child,offset in ((tag128(calc=b'\x04'),28),
                             (tag128(last=unknown),29+len(unknown)-1)):
            row=event_prefix(prefix(sequence(child)),source='128-unknown.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['consumedEnd'],19+offset)
            self.assertFalse(any(r.get('tag')==296 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(tag128(),b'\x59')),source='128-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['consumedEnd'],49)
        self.assertTrue(any(r.get('tag')==296 for r in row['completedRecords']))

    def test_tag19b_nested_lists_null_empty_payloads_and_tail(self):
        for items in (None,(),(b'\xff',),(keyword19b(None),),(keyword19b(),),(keyword19b((None,b'',b'\xffwire'),scalar_payload()),)):
            child=tag19b(items,pair(None,b'raw',128),scalar_payload(),scalar_payload(None),target(),target())
            r=Reader(child,'19b');r.action(0);self.assertEqual(r.pos,len(child))
            self.assertIn(dict(start=0,end=len(child),kind='union',tag=411),r.records)
            self.assertEqual(sum(v['kind']=='anonymous-keyword-edit-profile' for v in r.records),len(items or ()))
            result=event_prefix(prefix(sequence(child,b'\x59')),source='19b.bin')
            self.assertEqual(result['diagnostic']['offset'],19+len(child))
            self.assertEqual(result['diagnostic']['actual'],89);self.assertFalse(result['wholeSchemaExact'])

    def test_tag19b_all_cuts_hard_limits_wrappers_and_trailing(self):
        for child in (tag19b(None),tag19b((b'\xff',keyword19b((None,b'',b'raw'),scalar_payload()))),b'\xfa\x9b\x01\xff'):
            for cut in range(len(child)):
                values=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(data,'19b-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==411 for v in r.records))
                    values.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(values[0],values[1]);self.assertEqual(values[0],values[2])
            for tail in (b'\xff',b'\x00'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag19b_headers_list_counts_payload_lengths_and_reserves(self):
        child=tag19b((keyword19b((b'raw',)),))
        for offset,expected in ((3,14),(25,3)):
            malformed=bytearray(child);malformed[offset]=expected+1;r=Reader(malformed,'19b-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],offset)
            self.assertEqual(caught.exception.diagnostic['expected'],expected)
        for offset in (21,26,30):
            for count in (-2,0x7fffffff):
                r=Reader(child[:offset]+struct.pack('<i',count)+child[offset+4:],'19b-count')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],offset)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
        r=Reader(tag19b((b'\xff',))[:-1],'19b-outer-reserve')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],21)
        r=Reader(b'\x03'+struct.pack('<i',1)+payload(None)+bytes(4),'19b-inner-reserve')
        with self.assertRaises(FrameError) as caught:r.keyword_edit_profile()
        self.assertEqual(caught.exception.diagnostic['offset'],1)
        self.assertFalse(r.records)

    def test_tag19b_late_unknown_keeps_child_but_requires_final_dword(self):
        element=keyword19b();unknown=b'\x0d\xff'+payload(None)+bytes(6)+payload(None)+b'\x03\x17'
        child=tag19b((element,),second=unknown);r=Reader(child,'19b-unknown')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],28+len(element)+len(unknown)-1)
        self.assertTrue(any(v['kind']=='anonymous-keyword-edit-profile' for v in r.records))
        self.assertFalse(any(v.get('tag')==411 for v in r.records))
        for n in (1,2,3,4):
            child=tag19b(None);r=Reader(child[:-n],'19b-tail')
            with self.assertRaises(FrameError):r.action(0)
            self.assertFalse(any(v.get('tag')==411 for v in r.records))

    def test_tagc7_targets_curve_arrays_and_raw_gameplay_tag(self):
        for curve in (b'\xff',curve24(None),curve24(),curve24((bytes(range(28)),))):
            for first,second in ((b'\xff',target()),(target(),b'\xff'),(b'\xff',b'\xff')):
                for extended in (False,True):
                    child=tagc7(first,second,b'\xff\x00wire',curve,128,extended);r=Reader(child,'c7');r.action(0)
                    self.assertEqual(r.pos,len(child))
                    self.assertIn(dict(start=0,end=len(child),kind='union',tag=199),r.records)
                    self.assertEqual(sum(v['kind']=='anonymous-curve-profile' for v in r.records),1)
                    result=event_prefix(prefix(sequence(child,b'\x59')),source='c7.bin')
                    self.assertEqual(result['diagnostic']['offset'],19+len(child))
                    self.assertEqual(result['diagnostic']['actual'],89);self.assertFalse(result['wholeSchemaExact'])
        for value in (None,b''):
            for last in (0,1,127,128,255):
                child=tagc7(value=value,last=last);r=Reader(child,'c7-null');r.action(0)
                self.assertEqual(r.pos,len(child));self.assertEqual(len(child),35)

    def test_tagc7_all_cuts_limits_null_wrapper_and_trailing(self):
        for child in (tagc7(),tagc7(target(),target(),b'raw',curve24((bytes(28),))),b'\xc7\xff',b'\xfa\xc7\x00\xff'):
            for cut in range(len(child)):
                values=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(data,'c7-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==199 for v in r.records))
                    values.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(values[0],values[1]);self.assertEqual(values[0],values[2])
            for tail in (b'\xff',b'\x00'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tagc7_bad_header_payload_curve_count_and_required_tail(self):
        for header in (0,11,13,254):
            child=bytearray(tagc7());child[1]=header;r=Reader(child,'c7-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],1)
            self.assertEqual(caught.exception.diagnostic['expected'],12)
        child=tagc7(curve=curve24((bytes(28),)))
        for offset in (20,33):
            for count in (-2,0x7fffffff):
                r=Reader(child[:offset]+struct.pack('<i',count)+child[offset+4:],'c7-count')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],offset)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                self.assertFalse(any(v.get('tag')==199 for v in r.records))
        for child in (tagc7(),tagc7(curve=curve24(None)),tagc7(curve=curve24())):
            r=Reader(child[:-1],'c7-tail')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-1)
            self.assertFalse(any(v.get('tag')==199 for v in r.records))

    def test_tagc7_unknown_nested_stops_preserve_completed_curve(self):
        unknown=b'\x0d\xff'+payload(None)+bytes(6)+payload(None)+b'\x03\x17'
        for child,start in ((tagc7(first=unknown),19),(tagc7(second=unknown),29)):
            offset=start+len(unknown)-1
            r=Reader(child,'c7-unknown')
            with self.assertRaises(Unsupported) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],offset)
            self.assertEqual(r.pos,offset)
            self.assertFalse(any(v.get('tag')==199 for v in r.records))
            if start==29:self.assertTrue(any(v['kind']=='anonymous-curve-profile' for v in r.records))

    def test_tag101_fixed_width_arbitrary_values_and_next_unknown(self):
        for value in (0,0x80000000,0x7fc00000,0xffffffff):
            for last in (0,1,127,128,255):
                child=tag101(value,last);r=Reader(child,'101');r.action(0)
                self.assertEqual(r.pos,22);self.assertEqual(len(child),22)
                self.assertIn(dict(start=0,end=22,kind='union',tag=257),r.records)
                result=event_prefix(prefix(sequence(child,b'\x59')),source='101.bin')
                self.assertEqual(result['diagnostic']['offset'],41)
                self.assertEqual(result['diagnostic']['actual'],89);self.assertFalse(result['wholeSchemaExact'])

    def test_tag101_all_cuts_hard_limits_null_wrapper_and_trailing(self):
        for child in (tag101(),b'\xfa\x01\x01\xff'):
            complete=Reader(child,'101-full');complete.action(0);self.assertEqual(complete.pos,len(child))
            for cut in range(len(child)):
                values=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(data,'101-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==257 for v in r.records))
                    values.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(values[0],values[1]);self.assertEqual(values[0],values[2])
            for tail in (b'\xff',b'\x00'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag101_wrong_header_parent_count_alias_and_required_byte(self):
        for header in (0,5,7,254):
            child=bytearray(tag101());child[3]=header;r=Reader(child,'101-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],3)
            self.assertEqual(caught.exception.diagnostic['expected'],6)
        for tag in (b'\x01',b'\xfa\x01\x00'):
            r=Reader(tag+tag101()[3:],'101-alias')
            with self.assertRaises(Unsupported) as caught:r.action(0)
            self.assertEqual(r.pos,0);self.assertEqual(caught.exception.diagnostic['actual'],1)
        for count in (-2,0x7fffffff):
            with self.assertRaises(FrameError) as caught:sequence_frame(b'\x03'+struct.pack('<i',count)+tag101()+b'\x00\x00')
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
            self.assertEqual(caught.exception.diagnostic['offset'],1)
        r=Reader(tag101()[:-1],'101-tail')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],21)
        self.assertFalse(any(v.get('tag')==257 for v in r.records))

    def test_tagc1_independent_payload_null_empty_and_extended(self):
        for first in (None,b'',b'\xff\x00raw'):
            for second in (None,b'',b'\x80tail'):
                for extended in (False,True):
                    child=tagc1(first,second,extended);r=Reader(child,'c1');r.action(0)
                    self.assertEqual(r.pos,len(child))
                    self.assertEqual(len(child),23+2*extended+len(first or b'')+len(second or b''))
                    self.assertIn(dict(start=0,end=len(child),kind='union',tag=193),r.records)
                    rows=[v for v in r.records if v['kind']=='anonymous-byte-payload']
                    self.assertEqual([v['isNull'] for v in rows],[first is None,second is None])
                    result=event_prefix(prefix(sequence(child,b'\x59')),source='c1.bin')
                    self.assertEqual(result['diagnostic']['offset'],19+len(child))
                    self.assertEqual(result['diagnostic']['actual'],89);self.assertFalse(result['wholeSchemaExact'])

    def test_tagc1_all_cuts_limits_wrappers_and_trailing(self):
        for child in (tagc1(),tagc1(None,b''),tagc1(extended=True),b'\xc1\xff',b'\xfa\xc1\x00\xff'):
            for cut in range(len(child)):
                values=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(data,'c1-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==193 for v in r.records))
                    values.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(values[0],values[1]);self.assertEqual(values[0],values[2])
            for tail in (b'\xff',b'\x00'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tagc1_bad_headers_both_lengths_and_required_second_payload(self):
        for header in (0,5,7,254):
            child=bytearray(tagc1());child[1]=header;r=Reader(child,'c1-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],1)
            self.assertEqual(caught.exception.diagnostic['expected'],6)
        for first in (None,b'',b'raw'):
            child=tagc1(first);second=19+len(first or b'')
            for offset in (15,second):
                for length in (-2,0x7fffffff):
                    malformed=child[:offset]+struct.pack('<i',length)+child[offset+4:];r=Reader(malformed,'c1-length')
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertEqual(caught.exception.diagnostic['offset'],offset)
                    self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                    self.assertFalse(any(v.get('tag')==193 for v in r.records))
            r=Reader(child[:second],'c1-second')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],second)
            self.assertFalse(any(v.get('tag')==193 for v in r.records))

    def test_tag178_payload_null_empty_binary_and_arbitrary_final_byte(self):
        for value in (None,b'',b'\xff\x00wire'):
            for last in (0,1,127,128,255):
                child=tag178(value,last);self.assertEqual(len(child),24+len(value or b''))
                r=Reader(child,'178');r.action(0);self.assertEqual(r.pos,len(child))
                self.assertIn(dict(start=0,end=len(child),kind='union',tag=376),r.records)
                payload_row=next(v for v in r.records if v['kind']=='anonymous-byte-payload')
                self.assertEqual(payload_row['isNull'],value is None)
                result=event_prefix(prefix(sequence(child,b'\x59')),source='178.bin')
                self.assertEqual(result['diagnostic']['offset'],19+len(child))
                self.assertEqual(result['diagnostic']['actual'],89);self.assertFalse(result['wholeSchemaExact'])

    def test_tag178_all_cuts_hard_limits_null_wrapper_and_trailing(self):
        for child in (tag178(),tag178(None),b'\xfa\x78\x01\xff'):
            for cut in range(len(child)):
                values=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(data,'178-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==376 for v in r.records))
                    values.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(values[0],values[1]);self.assertEqual(values[0],values[2])
            for tail in (b'\xff',b'\x00'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag178_bad_header_lengths_and_required_last_byte(self):
        for header in (0,7,9,254):
            child=bytearray(tag178());child[3]=header;r=Reader(child,'178-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],3)
            self.assertEqual(caught.exception.diagnostic['expected'],8)
        for length in (-2,0x7fffffff):
            child=tag178()[:19]+struct.pack('<i',length)+bytes(8);r=Reader(child,'178-length')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],19)
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
        for value in (None,b'',b'wire'):
            child=tag178(value);r=Reader(child[:-1],'178-tail')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-1)
            self.assertFalse(any(v.get('tag')==376 for v in r.records))


    def test_tag16_both_encodings_distinct_inputs_and_full_tail(self):
        assignment=b'\x06'+bytes(4)+payload(None)+bytes(4)+payload(b'\xff')+payload(b'')+b'\x80'
        for extended in (False,True):
            for items in (None,(),(b'\xff',buff_input16(None,None),buff_input16((b'\xff',assignment)))):
                child=tag16(items,extended,rich=True)
                r=Reader(child,'16');r.action(0);self.assertEqual(r.pos,len(child))
                self.assertIn(dict(start=0,end=len(child),kind='union',tag=22),r.records)
                result=event_prefix(prefix(sequence(child,b'\x59')),source='16.bin')
                self.assertEqual(result['diagnostic']['offset'],19+len(child))
                self.assertEqual(result['diagnostic']['actual'],89)
                self.assertFalse(result['wholeSchemaExact'])

    def test_tag16_every_cut_hard_limits_null_wrappers_and_trailing(self):
        for child in (tag16((buff_input16((b'\xff',)),),rich=True),tag16(extended=True),b'\x16\xff',b'\xfa\x16\x00\xff'):
            for cut in range(len(child)):
                values=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(data,'16-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut);self.assertFalse(any(v.get('tag')==22 for v in r.records))
                    values.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(values[0],values[1]);self.assertEqual(values[0],values[2])
            for tail in (b'\xff',b'\x00'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag16_profile_headers_counts_and_required_tails(self):
        for body in (b'\x05'+bytes(30),b'\x03\xff'+struct.pack('<i',-2)+bytes(4),
                     b'\x03\xff'+struct.pack('<i',2)+b'\xff'+bytes(4)):
            r=Reader(body,'16-input')
            with self.assertRaises(FrameError):r.buff_input_profile()
            self.assertFalse(any(v['kind']=='anonymous-buff-input-profile' for v in r.records))
        for body in (b'\x02'+bytes(40),target_filter16()[:-1],target_filter16(b'\x02'+bytes(4)+struct.pack('<i',-2))):
            r=Reader(body,'16-filter')
            with self.assertRaises(FrameError):r.target_filter_profile()
        for header in (0,29,31,254):
            child=bytearray(tag16());child[1]=header;r=Reader(child,'16-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
            self.assertEqual(caught.exception.diagnostic['expected'],30)
        # Root list count requires the entire minimum tail, including final DWORD.
        before=b'\x16\x1e\xff'+bytes(12)+b'\xff\xff'+payload(b'')+b'\xff'+bytes(4)+b'\xff'
        r=Reader(before+struct.pack('<i',2)+bytes(32),'16-list')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')

    def test_tag16_unknown_nested_sequence_preserves_completed_predecessor(self):
        first=sequence(b'\xff');second=b'\x03'+struct.pack('<i',1)+b'\x59'+bytes(2)
        child=tag16(first=first,second=second);r=Reader(child,'16-unknown')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],15+len(first)+5)
        self.assertEqual(caught.exception.diagnostic['actual'],89)
        self.assertEqual(len([v for v in r.records if v['kind']=='sequence']),1)
        self.assertFalse(any(v.get('tag')==22 for v in r.records))


    def test_tag159_nested_header4_payloads_and_target(self):
        for value in (None,b'',b'\xff\x00wire'):
            nested=b'\x04'+payload(value)+b'\xff'+bytes.fromhex('FFFFFFFF')+b'\x80'
            for children in ((b'\xff',b'\xff',b'\xff'),(nested,nested,target())):
                child=b'\xfa\x59\x01\x07\xfe'+bytes(12)+b''.join(children)
                r=Reader(child,'159');r.action(0);self.assertEqual(r.pos,len(child))
                self.assertIn(dict(start=0,end=len(child),kind='union',tag=345),r.records)
                result=event_prefix(prefix(sequence(child,b'\x59')),source='159.bin')
                self.assertEqual(result['diagnostic']['offset'],19+len(child))
                self.assertEqual(result['diagnostic']['actual'],89)
                self.assertFalse(result['wholeSchemaExact'])

    def test_tag159_all_cuts_limits_null_wrapper_and_trailing(self):
        nested=b'\x04'+payload(b'\xff\x00wire')+b'\x80'+bytes.fromhex('000080FF')+b'\xff'
        for child in (b'\xfa\x59\x01\xff',b'\xfa\x59\x01\x07\xfe'+bytes(12)+nested+nested+target()):
            for cut in range(len(child)):
                values=[]
                for data in (child,child[:cut],child[:cut]+b'\xff'*20):
                    r=Reader(data,'159-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,cut)
                    self.assertFalse(any(v.get('tag')==345 for v in r.records))
                    values.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(values[0],values[1]);self.assertEqual(values[0],values[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag159_bad_headers_payload_lengths_and_required_target(self):
        common=b'\xfa\x59\x01\x07\x00'+bytes(12)
        for header in (0,3,6,8,254):
            r=Reader(common[:3]+bytes([header])+common[4:]+b'\xff'*3,'159-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
            self.assertEqual(caught.exception.diagnostic['offset'],3)
        for prior in (b'',b'\xff'):
            for length in (-2,0x7fffffff):
                r=Reader(common+prior+b'\x04'+struct.pack('<i',length)+bytes(8),'159-length')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                self.assertEqual(caught.exception.diagnostic['offset'],18+len(prior))
            r=Reader(common+prior+b'\x03'+bytes(12),'159-nested-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['expected'],4)
        r=Reader(common+b'\xff\xff','159-target')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],19)
        self.assertFalse(any(v.get('tag')==345 for v in r.records))


    def test_tag70_both_encodings_fixed_extent_and_raw_terminal_dwords(self):
        for extended in (False,True):
            size=25 if extended else 23
            for a,b in ((0,0),(1,0xffffffff),(0x80000000,0x7fc00000),(0xffffffff,0x80000000)):
                child=tag70(a,b,extended);self.assertEqual(len(child),size)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='70.bin')
                self.assertEqual(row['diagnostic'],dict(source='70.bin',offset=19+size,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=19+size,kind='union',tag=112),row['completedRecords']);self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag70_every_cut_limits_and_trailing(self):
        for child in (tag70(),tag70(0,0,True),b'\x70\xff',b'\xfa\x70\x00\xff'):
            r=Reader(child,'70-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                out=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'70-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==112 for v in r.records))
                    out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag70_bad_member_count_and_both_required_terminal_dwords(self):
        for extended in (False,True):
            child=tag70(0,0,extended);offset=3 if extended else 1
            for header in (0,5,7,254):
                bad=bytearray(child);bad[offset]=header;r=Reader(bad,'70-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic,dict(source='70-header',offset=offset,expected=6,actual=header,category='member-count'))
            for n in range(len(child)-8,len(child)):
                r=Reader(child[:n],'70-last')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['offset'],len(child)-8 if n<len(child)-4 else len(child)-4)
                self.assertFalse(any(v.get('tag')==112 for v in r.records))


    def test_tag71_both_encodings_fixed_extent_and_raw_last_byte(self):
        for extended in (False,True):
            size=18 if extended else 16
            for bits in (0,1,127,128,255):
                child=tag71(bits,extended);self.assertEqual(len(child),size)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='71.bin')
                self.assertEqual(row['diagnostic'],dict(source='71.bin',offset=19+size,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=19+size,kind='union',tag=113),row['completedRecords']);self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag71_every_cut_limits_and_trailing(self):
        for child in (tag71(),tag71(255,True),b'\x71\xff',b'\xfa\x71\x00\xff'):
            r=Reader(child,'71-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                out=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'71-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==113 for v in r.records))
                    out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag71_bad_member_count_and_mandatory_final_byte(self):
        for extended in (False,True):
            child=tag71(255,extended);offset=3 if extended else 1
            for header in (0,4,6,254):
                bad=bytearray(child);bad[offset]=header;r=Reader(bad,'71-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic,dict(source='71-header',offset=offset,expected=5,actual=header,category='member-count'))
            r=Reader(child[:-1],'71-last')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-1)
            self.assertFalse(any(v.get('tag')==113 for v in r.records))


    def test_tag14f_fixed_extent_arbitrary_final_byte(self):
        for bits in (0,1,127,128,255):
            child=tag14f(bits);self.assertEqual(len(child),18)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='14f.bin')
            self.assertEqual(row['diagnostic'],dict(source='14f.bin',offset=37,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=37,kind='union',tag=335),row['completedRecords']);self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag14f_every_cut_hard_limits_and_trailing(self):
        for child in (tag14f(),b'\xfa\x4f\x01\xff'):
            r=Reader(child,'14f-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                out=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'14f-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==335 for v in r.records))
                    out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag14f_bad_member_count_and_missing_last_byte(self):
        for header in (0,4,6,254):
            bad=bytearray(tag14f());bad[3]=header;r=Reader(bad,'14f-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic,dict(source='14f-header',offset=3,expected=5,actual=header,category='member-count'))
        for n in range(17,18):
            r=Reader(tag14f()[:n],'14f-last')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],17)
            self.assertFalse(any(v.get('tag')==335 for v in r.records))


    def test_tag124_fixed_extent_arbitrary_final_dword(self):
        for bits in (0,1,0x80000000,0x7fc00000,0xffffffff):
            child=tag124(bits);self.assertEqual(len(child),21)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='124.bin')
            self.assertEqual(row['diagnostic'],dict(source='124.bin',offset=40,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=40,kind='union',tag=292),row['completedRecords']);self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag124_every_cut_hard_limits_and_trailing(self):
        for child in (tag124(),b'\xfa\x24\x01\xff'):
            r=Reader(child,'124-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                out=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'124-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==292 for v in r.records))
                    out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag124_bad_member_count_and_missing_last_dword(self):
        for header in (0,4,6,254):
            bad=bytearray(tag124());bad[3]=header;r=Reader(bad,'124-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic,dict(source='124-header',offset=3,expected=5,actual=header,category='member-count'))
        for n in range(17,21):
            r=Reader(tag124()[:n],'124-last')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],17)
            self.assertFalse(any(v.get('tag')==292 for v in r.records))


    def test_tag125_byte_then_independent_terminal_scalar(self):
        for flag in (0,1,128,254,255):
            for scalar in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'wire',128,b'\xff'*4)):
                child=tag125(scalar,flag);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='125.bin')
                self.assertEqual(row['diagnostic'],dict(source='125.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=293),row['completedRecords']);self.assertFalse(row['wholeSchemaExact'])
                raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_tag125_every_cut_limits_and_trailing(self):
        for child in (tag125(),tag125(scalar_payload()),tag125(scalar_payload(None)),b'\xfa\x25\x01\xff'):
            r=Reader(child,'125-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                out=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'125-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==293 for v in r.records))
                    out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag125_bad_header_length_and_missing_interposed_byte(self):
        for header in (0,5,7,254):
            bad=bytearray(tag125());bad[3]=header;r=Reader(bad,'125-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic,dict(source='125-header',offset=3,expected=6,actual=header,category='member-count'))
        for value in (b'',b'\x02',b'\x03'+struct.pack('<i',-2),b'\x03'+struct.pack('<i',0x7fffffff),scalar_payload()[:-1]):
            r=Reader(tag125(value),'125-bad')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertGreaterEqual(caught.exception.diagnostic['offset'],18)
            self.assertFalse(any(v.get('tag')==293 for v in r.records))
        r=Reader(tag125()[:17]+b'\xff','125-missing-byte')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],18)


    def test_tag8e_independent_terminal_scalar_extent(self):
        for wire in (b'\x8e',b'\xfa\x8e\x00'):
            for value in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'\xff\x8e\x00',128,b'\xff'*4)):
                child=tag8e(value,wire);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='8e.bin')
                self.assertEqual(row['diagnostic'],dict(source='8e.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=142),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag8e_all_cuts_limits_and_trailing(self):
        for child in (tag8e(scalar_payload()),tag8e(scalar_payload(None),b'\xfa\x8e\x00'),tag8e(),b'\x8e\xff',b'\xfa\x8e\x00\xff'):
            r=Reader(child,'8e-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'8e-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==142 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag8e_malformed_headers_lengths_and_required_final_scalar(self):
        for wire in (b'\x8e',b'\xfa\x8e\x00'):
            for header in (0,4,6,254):
                bad=bytearray(tag8e(wire=wire));bad[len(wire)]=header;r=Reader(bad,'8e-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic,dict(source='8e-header',offset=len(wire),expected=5,actual=header,category='member-count'))
            for value in (b'\x02',b'\x03'+struct.pack('<i',-2),b'\x03'+struct.pack('<i',0x7fffffff),scalar_payload()[:-1],b''):
                r=Reader(tag8e(value,wire),'8e-bad')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['source'],'8e-bad')
                self.assertGreaterEqual(caught.exception.diagnostic['offset'],len(wire)+14)
                self.assertFalse(any(v.get('tag')==142 for v in r.records))

    def test_tag52_fixed_extent_and_arbitrary_terminal_byte(self):
        for wire in (b'\x52',b'\xfa\x52\x00'):
            for last in range(256):
                child=tag52(last,wire);end=19+len(child)
                self.assertEqual(len(child),15+len(wire))
                row=event_prefix(prefix(sequence(child,b'\x59')),source='52.bin')
                self.assertEqual(row['diagnostic'],dict(source='52.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=82),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag52_every_cut_hard_limits_and_trailing(self):
        for child in (tag52(),tag52(wire=b'\xfa\x52\x00'),b'\x52\xff',b'\xfa\x52\x00\xff'):
            r=Reader(child,'52-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'52-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==82 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag52_member_count_and_missing_terminal_byte(self):
        for wire in (b'\x52',b'\xfa\x52\x00'):
            for header in (0,4,6,254):
                bad=bytearray(tag52(wire=wire));bad[len(wire)]=header;r=Reader(bad,'52-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic,dict(source='52-header',offset=len(wire),expected=5,actual=header,category='member-count'))
            child=tag52(wire=wire);r=Reader(child[:-1],'52-final')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-1)
            self.assertFalse(any(v.get('tag')==82 for v in r.records))

    def test_tag87_nullable_list_and_independent_sequences(self):
        for wire in (b'\x87',b'\xfa\x87\x00'):
            for items in (None,(),(b'\xff',),(sequence(),),(b'\x03'+struct.pack('<i',-1)+b'\xff\x80',),(sequence(tag120()),b'\xff',sequence(tag87((sequence(b'\xff'),))))):
                child=tag87(items,wire);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='87.bin')
                self.assertEqual(row['diagnostic'],dict(source='87.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=135),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag87_every_cut_hard_limits_and_trailing(self):
        child=tag87((sequence(tag120(scalar_payload(),scalar_payload(None),b'last')),b'\xff',sequence(tag87((sequence(b'\xff'),)))))
        for child in (child,tag87(None),b'\x87\xff',b'\xfa\x87\x00\xff'):
            r=Reader(child,'87-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'87-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n)
                    self.assertFalse(any(v.get('tag')==135 and v['start']==0 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag87_headers_counts_and_incomplete_children(self):
        for at in (1,19):
            bad=bytearray(tag87((sequence(),)));bad[at]=42;r=Reader(bad,'87-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for good,at in ((tag87(),15),(tag87((sequence(),)),20)):
            for count in (-2,1,0x7fffffff):
                bad=bytearray(good);struct.pack_into('<i',bad,at,count);r=Reader(bad,'87-count')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('87-count',at,count,'count-bounds'))
        for missing in (1,2):
            data=tag87((sequence(b'\xff'),))[:-missing];r=Reader(data,'87-child-tail')
            with self.assertRaises(FrameError):r.action(0)
            self.assertFalse(any(v.get('tag')==135 for v in r.records))
        first=sequence(tag120());child=tag87((first,sequence(b'\x59')))
        row=event_prefix(prefix(sequence(child)),source='87-child-unknown')
        self.assertEqual((row['status'],row['diagnostic']['actual']),('unsupported',89))
        self.assertTrue(any(v.get('tag')==288 for v in row['completedRecords']))
        self.assertFalse(any(v.get('tag')==135 for v in row['completedRecords']))

    def test_tag87_recursive_sequences_keep_depth_gate(self):
        child=tag87()
        for _ in range(33):child=tag87((sequence(child),))
        r=Reader(child,'87-depth')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'depth-limit')
        self.assertFalse(any(v.get('tag')==135 and v['start']==0 for v in r.records))

    def test_tag1b_independent_profiles_and_interleaved_members(self):
        for wire in (b'\x1b',b'\xfa\x1b\x00'):
            for first in (b'\xff',target()):
                for second in (b'\xff',target(direction_value=b'\xff')):
                    for direct in (b'\xff',direction()):
                        for scalars in ((b'\xff',)*6,tuple(scalar_payload(bytes([i])) for i in range(6)),(b'\xff',scalar_payload(None))*3):
                            child=tag1b(first,second,direct,scalars,wire);end=19+len(child)
                            row=event_prefix(prefix(sequence(child,b'\x59')),source='1b.bin')
                            self.assertEqual(row['diagnostic'],dict(source='1b.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                            self.assertIn(dict(start=19,end=end,kind='union',tag=27),row['completedRecords'])
                            self.assertFalse(row['wholeSchemaExact'])
                            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag1b_every_cut_hard_limits_and_trailing(self):
        for child in (tag1b(target(),target(direction_value=b'\xff'),direction(),tuple(scalar_payload(bytes([i])) for i in range(6))),tag1b(),b'\x1b\xff',b'\xfa\x1b\x00\xff'):
            r=Reader(child,'1b-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'1b-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==27 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag1b_headers_lengths_and_incomplete_terminal_profile(self):
        for at in (1,15,16,17,22,23,24,26,28,30):
            bad=bytearray(tag1b());bad[at]=42;r=Reader(bad,'1b-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for slot,at in enumerate((16,17,22,24,26,30)):
            scalars=[b'\xff']*6;scalars[slot]=scalar_payload(None)
            for count in (-2,0x7fffffff):
                bad=bytearray(tag1b(scalars=scalars));struct.pack_into('<i',bad,at+1,count);r=Reader(bad,'1b-length')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('1b-length',at+1,count,'count-bounds'))
        child=tag1b(scalars=(b'\xff',)*5+(scalar_payload(b'last'),))
        for data in (child[:30],child[:-1]):
            r=Reader(data,'1b-final')
            with self.assertRaises(FrameError):r.action(0)
            self.assertFalse(any(v.get('tag')==27 for v in r.records))
            self.assertEqual(sum(v['kind']=='anonymous-scalar-payload' for v in r.records),5)
        bad=bytearray(direction());bad[8]=1
        row=event_prefix(prefix(sequence(tag1b(direct=bad))),source='1b-direction')
        self.assertEqual((row['status'],row['diagnostic']['category']),('failed','member-count'))
        self.assertFalse(any(v.get('tag')==27 for v in row['completedRecords']))

    def test_tag9f_independent_targets_and_terminal_query(self):
        for wire in (b'\x9f',b'\xfa\x9f\x00'):
            for first in (b'\xff',target()):
                for second in (b'\xff',target(direction_value=b'\xff')):
                    for last in (b'\xff',query41(None),query41(),query41((0,0xffffffff))):
                        child=tag9f(first,second,last,wire);end=19+len(child)
                        row=event_prefix(prefix(sequence(child,b'\x59')),source='9f.bin')
                        self.assertEqual(row['diagnostic'],dict(source='9f.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                        self.assertIn(dict(start=19,end=end,kind='union',tag=159),row['completedRecords'])
                        self.assertFalse(row['wholeSchemaExact'])
                        self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag9f_every_cut_hard_limits_and_trailing(self):
        for child in (tag9f(target(),target(direction_value=b'\xff'),query41((0,0xffffffff))),tag9f(),b'\x9f\xff',b'\xfa\x9f\x00\xff'):
            r=Reader(child,'9f-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'9f-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==159 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag9f_headers_query_counts_and_incomplete_parent(self):
        for at in (1,20,21,22):
            bad=bytearray(tag9f());bad[at]=42;r=Reader(bad,'9f-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for count in (-2,1,0x7fffffff):
            bad=bytearray(tag9f(last=query41()));struct.pack_into('<i',bad,27,count);r=Reader(bad,'9f-count')
            with self.assertRaises(FrameError) as caught:r.action(0)
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('9f-count',27,count,'count-bounds'))
        data=tag9f(first=target(),last=query41((123,)))[:-1];r=Reader(data,'9f-last')
        with self.assertRaises(FrameError):r.action(0)
        self.assertFalse(any(v.get('tag')==159 for v in r.records))
        self.assertEqual(sum(v['kind']=='anonymous-target-profile' for v in r.records),2)
        child=tag9f(second=target(selector=b'\x03\x59'))
        row=event_prefix(prefix(sequence(child)),source='9f-unknown')
        self.assertEqual((row['status'],row['diagnostic']['category']),('unsupported','nested-profile'))
        self.assertFalse(any(v.get('tag')==159 for v in row['completedRecords']))

    def test_tag120_independent_scalar_profiles_and_terminal_payload(self):
        for first in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'\xff\xfa')):
            for second in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'other')):
                for value in (None,b'',b'\xff\xfa\x20\x01'):
                    child=tag120(first,second,value);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='120.bin')
                    self.assertEqual(row['diagnostic'],dict(source='120.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=288),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag120_every_cut_hard_limits_and_trailing_bytes(self):
        for child in (tag120(scalar_payload(b'first'),scalar_payload(b'second'),b'terminal'),tag120(),b'\xfa\x20\x01\xff'):
            r=Reader(child,'120-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'120-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==288 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag120_headers_lengths_and_required_parent_remainder(self):
        for at in (3,17,18):
            bad=bytearray(tag120());bad[at]=42;r=Reader(bad,'120-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for child,at in ((tag120(),23),(tag120(scalar_payload(None)),18),(tag120(second=scalar_payload(None)),19)):
            for size in (-2,0x7fffffff):
                bad=bytearray(child);struct.pack_into('<i',bad,at,size);r=Reader(bad,'120-length')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('120-length',at,size,'count-bounds'))
        for data in (tag120()[:19],tag120()[:23],tag120(value=b'last')[:-1]):
            r=Reader(data,'120-tail')
            with self.assertRaises(FrameError):r.action(0)
            self.assertFalse(any(v.get('tag')==288 for v in r.records))
            self.assertEqual(sum(v['kind']=='anonymous-scalar-payload' for v in r.records),2)

    def test_tag08_independent_nested_lists_null_states_and_profiles(self):
        groups=(None,(),(b'\xff',),(group08(None),),(group08(),),(group08((b'\xff',condition08(b'\xff\xfa'))),))
        for wire in (b'\x08',b'\xfa\x08\x00'):
            for first in groups:
                for second in groups:
                    child=tag08(first,second,wire=wire);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='08.bin')
                    self.assertEqual(row['diagnostic'],dict(source='08.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=8),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag08_every_cut_hard_limits_and_trailing(self):
        child=tag08((group08((condition08(b'payload'),b'\xff')),),(group08(None),),b'\x03'+b'\xff'*3,scalar_payload(),curve24((b'\xff'*28,)))
        for child in (child,b'\x08\xff',b'\xfa\x08\x00\xff'):
            r=Reader(child,'08-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'08-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==8 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag08_nested_headers_lengths_counts_and_parent_reservations(self):
        for at in (1,15,16,17,21):
            bad=bytearray(tag08());bad[at]=42;r=Reader(bad,'08-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for at in (44,50):
            for count in (-2,1,0x7fffffff):
                bad=bytearray(tag08());struct.pack_into('<i',bad,at,count);r=Reader(bad,'08-count')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('08-count',at,count,'count-bounds'))
        for method,head,at in (('counted_payload_scalars_profile',b'\x01',1),('byte_payload_scalars_profile',b'\x05\xff',2)):
            for count in (-2,0x7fffffff):
                r=Reader(head+struct.pack('<i',count),'08-inner')
                with self.assertRaises(FrameError) as caught:getattr(r,method)()
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],caught.exception.diagnostic['category']),(at,count,'count-bounds'))
            r=Reader(b'\x2a','08-inner-header')
            with self.assertRaises(FrameError) as caught:getattr(r,method)()
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag08_nested_completion_does_not_replace_parent_tail(self):
        for missing in range(1,14):
            data=tag08(first=None,second=None)[:-missing];r=Reader(data,'08-last')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(data))
            self.assertFalse(any(v.get('tag')==8 for v in r.records))
        data=group08((condition08(b'payload'),condition08()))[:-1];r=Reader(data,'08-child-last')
        with self.assertRaises(FrameError):r.counted_payload_scalars_profile()
        self.assertFalse(any(v['kind']=='anonymous-counted-payload-scalars-profile' for v in r.records))
        self.assertTrue(any(v['kind']=='anonymous-byte-payload-scalars-profile' for v in r.records))

    def test_tag19e_independent_curves_nullable_list_and_six_final_bytes(self):
        for first in (b'\xff',curve24(None),curve24((b'\xff'*28,))):
            for second in (b'\xff',curve24(),curve24((b'\x80'*28,))):
                for items in (None,(),(None,),(b'',b'\xff\xfa')):
                    child=tag19e(first,second,items);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='19e.bin')
                    self.assertEqual(row['diagnostic'],dict(source='19e.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=414),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag19e_every_cut_hard_limits_and_trailing(self):
        for child in (tag19e(curve24((b'\xff'*28,)),curve24(),(None,b'\xfa\xff'),b'payload'),b'\xfa\x9e\x01\xff'):
            r=Reader(child,'19e-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'19e-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==414 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag19e_bad_headers_lengths_list_reservation_and_missing_tail(self):
        for at in (3,17,26):
            bad=bytearray(tag19e());bad[at]=42;r=Reader(bad,'19e-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for at in (43,len(tag19e())-10):
            for count in (-2,0x7fffffff):
                bad=bytearray(tag19e());struct.pack_into('<i',bad,at,count);r=Reader(bad,'19e-count')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('19e-count',at,count,'count-bounds'))
        bad=bytearray(tag19e());at=len(bad)-10;struct.pack_into('<i',bad,at,1)
        r=Reader(bad,'19e-reserve')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'count-bounds'))
        for missing in range(1,7):
            data=tag19e(items=None)[:-missing];r=Reader(data,'19e-last')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(data))
            self.assertFalse(any(v.get('tag')==414 for v in r.records))

    def test_taga7_profiles_null_states_and_terminal_boundary(self):
        for wire in (b'\xa7',b'\xfa\xa7\x00'):
            for disabled in (b'\xff',b'\x01\x00',b'\x01\xff'):
                for enabled in (b'\xff',scalar_pair_flags(),scalar_pair_flags(scalar_payload(None),scalar_payload())):
                    for query in (b'\xff',query41(),query41((0,0xffffffff))):
                        child=taga7(disabled,enabled,query,wire=wire)
                        end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='a7.bin')
                        self.assertEqual(row['diagnostic'],dict(source='a7.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                        self.assertIn(dict(start=19,end=end,kind='union',tag=167),row['completedRecords'])
                        self.assertFalse(row['wholeSchemaExact'])
                        self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_taga7_every_cut_hard_limits_and_trailing(self):
        for child in (taga7(b'\x01\xff',scalar_pair_flags(scalar_payload(),scalar_payload(None)),query41((1,2))),b'\xa7\xff',b'\xfa\xa7\x00\xff'):
            r=Reader(child,'a7-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'a7-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==167 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_taga7_bad_headers_counts_and_missing_final_bytes(self):
        for at in (1,16,17,18,19,20):
            bad=bytearray(taga7());bad[at]=42;r=Reader(bad,'a7-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for count in (-2,0x7fffffff):
            for body,offset in ((b'\x06'+bytes(4)+b'\x03'+struct.pack('<i',count),6),):
                r=Reader(body,'a7-length')
                with self.assertRaises(FrameError) as caught:r.scalar_pair_flags_profile()
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('a7-length',offset,count,'count-bounds'))
        for body,method in ((b'\x01','byte_profile'),(scalar_pair_flags()[:-1],'scalar_pair_flags_profile'),(taga7()[:-1],'action')):
            r=Reader(body,'a7-last')
            with self.assertRaises(FrameError) as caught:
                if method=='action':r.action(0)
                else:getattr(r,method)()
            self.assertEqual(caught.exception.diagnostic['offset'],len(body))
            self.assertFalse(any(v.get('tag')==167 for v in r.records))

    def test_tag150_scalar_and_independent_terminal_byte(self):
        for nested in (b'\xff',scalar_payload(None),scalar_payload(b'\xff\x00')):
            for last in (b'\x00',b'\x80',b'\xff'):
                child=b'\xfa\x50\x01\x06'+b'\xff'*13+nested+last
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='150.bin')
                self.assertEqual(row['diagnostic'],dict(source='150.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=336),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag150_every_cut_hard_limits_and_trailing(self):
        for child in (b'\xfa\x50\x01\x06'+bytes(13)+scalar_payload()+b'\x80',b'\xfa\x50\x01\xff'):
            r=Reader(child,'150-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'150-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==336 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag150_bad_headers_lengths_and_missing_final_byte(self):
        base=b'\xfa\x50\x01\x06'+bytes(13)
        for at in (3,17):
            bad=bytearray(base+b'\xff\x80');bad[at]=42;r=Reader(bad,'150-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for count in (-2,0x7fffffff):
            r=Reader(base+b'\x03'+struct.pack('<i',count),'150-length')
            with self.assertRaises(FrameError) as caught:r.action(0)
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('150-length',18,count,'count-bounds'))
        for nested in (b'\xff',scalar_payload()):
            r=Reader(base+nested,'150-last')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(base+nested))
            self.assertFalse(any(v.get('tag')==336 for v in r.records))
            if nested!=b'\xff':self.assertTrue(any(v['kind']=='anonymous-byte-payload' for v in r.records))

    def test_tag4c_independent_profiles_and_nullable_list(self):
        for wire in (b'\x4c',b'\xfa\x4c\x00'):
            for items in (None,(),(None,),(None,b'',b'\xff\xfa')):
                for scalar,first,last in ((b'\xff',b'\xff',target()),(scalar_payload(),target(),b'\xff'),(scalar_payload(None),target(),target())):
                    child=tag4c(wire,scalar,first,items,last)
                    end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='4c.bin')
                    self.assertEqual(row['diagnostic'],dict(source='4c.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=76),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag4c_every_cut_hard_limits_and_trailing(self):
        for wire in (b'\x4c',b'\xfa\x4c\x00'):
            for child in (tag4c(wire,scalar_payload(),target(),(None,b'key'),target()),wire+b'\xff'):
                r=Reader(child,'4c-cut');r.action(0);self.assertEqual(r.pos,len(child))
                for n in range(len(child)):
                    results=[]
                    for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                        r=Reader(data,'4c-cut',n)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==76 for v in r.records))
                        results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag4c_bad_headers_counts_and_terminal_target(self):
        for wire in (b'\x4c',b'\xfa\x4c\x00'):
            good=tag4c(wire);count_at=len(wire)+23
            for at in (len(wire),len(wire)+14,len(wire)+15,len(good)-1):
                bad=bytearray(good);bad[at]=42;r=Reader(bad,'4c-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
            for count,remaining in ((-2,b'\xff'),(0x7fffffff,b'\xff'),(1,b'\xff'*4)):
                r=Reader(good[:count_at]+struct.pack('<i',count)+remaining,'4c-count')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],caught.exception.diagnostic['category']),(count_at,count,'count-bounds'))
            for count in (-2,0x7fffffff):
                r=Reader(good[:count_at]+struct.pack('<ii',1,count)+b'\xff','4c-element')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],caught.exception.diagnostic['category']),(count_at+4,count,'count-bounds'))
            r=Reader(tag4c(wire,scalar_payload(),target(),(b'keep',),target(selector=b'\x03\x59')),'4c-last')
            with self.assertRaises(Unsupported) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('nested-profile',89))
            self.assertFalse(any(v.get('tag')==76 for v in r.records))
            self.assertTrue(any(v['kind']=='anonymous-byte-payload' for v in r.records))

    def test_tag3a_scalar_and_terminal_payload_independent_nulls(self):
        for wire in (b'\x3a',b'\xfa\x3a\x00'):
            for nested in (b'\xff',scalar_payload(None),scalar_payload(b'\xff\x00')):
                for value in (None,b'',b'\xff\xfa\x3a\x00'):
                    child=wire+b'\x07'+b'\xff'*17+nested+payload(value)
                    end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='3a.bin')
                    self.assertEqual(row['diagnostic'],dict(source='3a.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=58),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag3a_every_cut_hard_limits_and_trailing(self):
        for wire in (b'\x3a',b'\xfa\x3a\x00'):
            for child in (wire+b'\x07'+bytes(17)+scalar_payload()+payload(b'tail'),wire+b'\xff'):
                r=Reader(child,'3a-cut');r.action(0);self.assertEqual(r.pos,len(child))
                for n in range(len(child)):
                    results=[]
                    for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                        r=Reader(data,'3a-cut',n)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==58 for v in r.records))
                        results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag3a_bad_headers_lengths_and_partial_terminal(self):
        for wire in (b'\x3a',b'\xfa\x3a\x00'):
            base=wire+b'\x07'+bytes(17)
            for at in (len(wire),len(base)):
                bad=bytearray(base+b'\xff'+payload(None));bad[at]=42;r=Reader(bad,'3a-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
            for lead in (base+b'\x03',base+b'\xff'):
                for count in (-2,0x7fffffff):
                    r=Reader(lead+struct.pack('<i',count),'3a-length')
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    d=caught.exception.diagnostic
                    self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('3a-length',len(lead),count,'count-bounds'))
            r=Reader(base+scalar_payload()+payload(b'tail')[:-1],'3a-terminal')
            with self.assertRaises(FrameError):r.action(0)
            self.assertFalse(any(v.get('tag')==58 for v in r.records))
            self.assertTrue(any(v['kind']=='anonymous-byte-payload' for v in r.records))

    def test_tag05_terminal_target_encodings_and_nulls(self):
        for wire in (b'\x05',b'\xfa\x05\x00'):
            for nested in (b'\xff',target(),target(direction_value=b'\xff')):
                child=wire+b'\x05'+b'\xff'*13+nested
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='05.bin')
                self.assertEqual(row['diagnostic'],dict(source='05.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=5),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag05_every_cut_hard_limits_and_trailing(self):
        for wire in (b'\x05',b'\xfa\x05\x00'):
            for child in (wire+b'\x05'+bytes(13)+target(),wire+b'\xff'):
                r=Reader(child,'05-cut');r.action(0);self.assertEqual(r.pos,len(child))
                for n in range(len(child)):
                    results=[]
                    for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                        r=Reader(data,'05-cut',n)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==5 for v in r.records))
                        results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag05_bad_headers_lengths_and_unknown_selector(self):
        for wire in (b'\x05',b'\xfa\x05\x00'):
            base=wire+b'\x05'+bytes(13)
            for at in (len(wire),len(base)):
                bad=bytearray(base+b'\xff');bad[at]=42;r=Reader(bad,'05-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
            for count in (-2,0x7fffffff):
                r=Reader(base+b'\x0d\xff'+struct.pack('<i',count),'05-length')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('05-length',len(base)+2,count,'count-bounds'))
            r=Reader(base+target(selector=b'\x03\x59'),'05-selector')
            with self.assertRaises(Unsupported) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('nested-profile',89))
            self.assertFalse(any(v.get('tag')==5 and v.get('kind')=='union' for v in r.records))
            self.assertTrue(any(v['kind']=='anonymous-byte-payload' for v in r.records))

    def test_tag16f_byte_target_and_terminal_scalar(self):
        for t in (b'\xff',target(),target(direction_value=b'\xff')):
            for v in (b'\xff',scalar_payload(None),scalar_payload(b'\xff\x00')):
                child=b'\xfa\x6f\x01\x07'+b'\xff'*13+b'\x80'+t+v
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='16f.bin')
                self.assertEqual(row['diagnostic'],dict(source='16f.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=367),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag16f_every_cut_hard_limits_and_trailing(self):
        for child in (b'\xfa\x6f\x01\x07'+bytes(14)+target()+scalar_payload(),b'\xfa\x6f\x01\xff'):
            r=Reader(child,'16f-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'16f-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==367 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag16f_bad_headers_lengths_and_incomplete_scalar(self):
        base=b'\xfa\x6f\x01\x07'+bytes(14)
        for at in (3,18,19):
            bad=bytearray(base+b'\xff\xff');bad[at]=42;r=Reader(bad,'16f-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for lead,offset in ((base+b'\x0d\xff',20),(base+b'\xff\x03',20)):
            for count in (-2,0x7fffffff):
                r=Reader(lead+struct.pack('<i',count),'16f-length')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('16f-length',offset,count,'count-bounds'))
        r=Reader(base+target()+scalar_payload()[:-1],'16f-incomplete')
        with self.assertRaises(FrameError):r.action(0)
        self.assertFalse(any(v.get('tag')==367 for v in r.records))
        self.assertTrue(any(v['kind']=='anonymous-byte-payload' for v in r.records))
        r=Reader(base+target(selector=b'\x03\x59')+b'\xff','16f-selector')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('nested-profile',89))

    def test_tag15c_terminal_target_and_independent_nulls(self):
        for nested in (b'\xff',target(),target(direction_value=b'\xff')):
            child=b'\xfa\x5c\x01\x05'+b'\xff'*13+nested
            end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='15c.bin')
            self.assertEqual(row['diagnostic'],dict(source='15c.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=348),row['completedRecords'])
            self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag15c_every_cut_hard_limits_and_trailing(self):
        for child in (b'\xfa\x5c\x01\x05'+bytes(13)+target(),b'\xfa\x5c\x01\xff'):
            r=Reader(child,'15c-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'15c-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==348 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag15c_bad_headers_lengths_and_unknown_selector(self):
        base=b'\xfa\x5c\x01\x05'+bytes(13)
        for at in (3,17):
            bad=bytearray(base+b'\xff');bad[at]=42;r=Reader(bad,'15c-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        for count in (-2,0x7fffffff):
            r=Reader(base+b'\x0d\xff'+struct.pack('<i',count),'15c-length')
            with self.assertRaises(FrameError) as caught:r.action(0)
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('15c-length',19,count,'count-bounds'))
        r=Reader(base+target(selector=b'\x03\x59'),'15c-selector')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('nested-profile',89))
        self.assertFalse(any(v.get('tag')==348 for v in r.records))
        self.assertTrue(any(v['kind']=='anonymous-byte-payload' for v in r.records))

    def test_tag2f_sequence_and_independent_target_tail(self):
        for wire in (b'\x2f',b'\xfa\x2f\x00'):
            for seq in (b'\xff',sequence(),b'\x03'+struct.pack('<i',-1)+b'\x80\xfe',sequence(b'\xff',tag5b())):
                for nested in (b'\xff',target()):
                    child=wire+b'\x0a'+b'\xff'*13+seq+b'\xfe'+b'\xff'*4+nested+b'\xff'*8
                    end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='2f.bin')
                    self.assertEqual(row['diagnostic'],dict(source='2f.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=47),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag2f_every_cut_hard_limits_and_trailing(self):
        for wire in (b'\x2f',b'\xfa\x2f\x00'):
            full=wire+b'\x0a'+bytes(13)+sequence(tag5b())+bytes(5)+target()+bytes(8)
            for child in (full,wire+b'\xff'):
                r=Reader(child,'2f-cut');r.action(0);self.assertEqual(r.pos,len(child))
                for n in range(len(child)):
                    results=[]
                    for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                        r=Reader(data,'2f-cut',n)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==47 for v in r.records))
                        results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag2f_bad_nested_count_and_partial_tail(self):
        base=b'\x2f\x0a'+bytes(13)
        for count in (-2,0x7fffffff):
            r=Reader(base+b'\x03'+struct.pack('<i',count)+bytes(20),'2f-count')
            with self.assertRaises(FrameError) as caught:r.action(0)
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('2f-count',16,count,'count-bounds'))
        for at in (1,15):
            bad=bytearray(base+b'\xff'+bytes(5)+b'\xff'+bytes(8));bad[at]=42;r=Reader(bad,'2f-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        r=Reader(base+sequence(b'\x59')+bytes(20),'2f-child')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(20,89))
        nested=sequence(tag5b());head=base+nested+bytes(5)+target()
        for n in range(8):
            r=Reader(head+bytes(n),'2f-tail')
            with self.assertRaises(FrameError):r.action(0)
            self.assertTrue(any(v['kind']=='sequence' and v['start']==15 and v['end']==15+len(nested) for v in r.records))
            self.assertFalse(any(v.get('tag')==47 for v in r.records))

    def test_tag183_independent_lists_profiles_and_final_bytes(self):
        for first in (None,(),(b'\xff',),(target(),b'\xff')):
            for second in (None,(),(b'\xff',target())):
                child=tag183(first,second,scalar_payload(None),scalar_payload(b'wire'),curve24((bytes(28),)))
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='183.bin')
                self.assertEqual(row['diagnostic'],dict(source='183.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=387),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag183_every_cut_hard_limits_and_trailing(self):
        full=tag183((target(),b'\xff'),(target(),),scalar_payload(b'wire'),scalar_payload(None),curve24((bytes(28),)))
        for child in (full,b'\xfa\x83\x01\xff'):
            r=Reader(child,'183-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'183-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==387 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag183_count_reserves_headers_and_partial_second_list(self):
        good=tag183();self.assertEqual(len(good),47)
        for at in (22,27):
            for value in (-2,1,0x7fffffff):
                bad=bytearray(good);struct.pack_into('<i',bad,at,value);r=Reader(bad,'183-count')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('183-count',at,value,'count-bounds'))
                self.assertEqual(r.pos,at+4);self.assertFalse(any(v.get('tag')==387 for v in r.records))
        for at in (3,21,31,44):
            bad=bytearray(good);bad[at]=42;r=Reader(bad,'183-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at,'member-count'))
        first=target();r=Reader(tag183((first,),(target(selector=b'\x03\x59'),)),'183-second')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('nested-profile',89))
        self.assertTrue(any(v['start']==26 and v['end']==26+len(first) for v in r.records))
        self.assertFalse(any(v.get('tag')==387 for v in r.records))

    def test_tag5c_fixed_source_widths_and_encodings(self):
        for wire in (b'\x5c',b'\xfa\x5c\x00'):
            for body in (bytes(25),b'\xff'*25,bytes(range(25))):
                child=wire+b'\x06'+body
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='5c.bin')
                self.assertEqual(row['diagnostic'],dict(source='5c.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=92),row['completedRecords'])
                spans=[v for v in row['ranges'] if 19+len(wire)+1<=v['start']<end]
                self.assertEqual([(v['kind'],v['end']-v['start']) for v in spans],[('anonymous-nonzero-byte',1)]+[('anonymous-scalar32',4)]*4+[('anonymous-scalar64',8)])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag5c_every_cut_hard_limits_and_trailing(self):
        for wire in (b'\x5c',b'\xfa\x5c\x00'):
            for child in (wire+b'\x06'+b'\xff'*25,wire+b'\xff'):
                r=Reader(child,'5c-cut');r.action(0);self.assertEqual(r.pos,len(child))
                for n in range(len(child)):
                    results=[]
                    for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                        r=Reader(data,'5c-cut',n)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==92 for v in r.records))
                        results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag5c_bad_header_and_atomic_qword(self):
        for wire in (b'\x5c',b'\xfa\x5c\x00'):
            for h in (0,5,7,254):
                r=Reader(wire+bytes([h])+bytes(25),'5c-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual(d,dict(source='5c-header',offset=len(wire),expected=6,actual=h,category='member-count'))
            start=len(wire)+18
            for n in range(8):
                r=Reader(wire+b'\x06'+bytes(17+n),'5c-qword')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic,dict(source='5c-qword',offset=start,expected={'bytes':8},actual={'remaining':n},category='truncated'))
                self.assertEqual(r.pos,start);self.assertFalse(r.records)
                self.assertFalse(any(v['kind']=='anonymous-scalar64' for v in r.ranges))

    def test_tag122_nullable_list_and_independent_elements(self):
        elem=b'\x04'+scalar_payload(b'wire')+payload(None)+target()+payload(b'\xff\x00')
        empty=b'\x04\xff'+payload(b'')+b'\xff'+payload(None)
        base=b'\xfa\x22\x01\x05'+b'\xff'*13
        for items in (None,(),(b'\xff',),(elem,empty,b'\xff',elem)):
            child=base+struct.pack('<i',-1 if items is None else len(items))+(b'' if items is None else b''.join(items))
            end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='122.bin')
            self.assertEqual(row['diagnostic'],dict(source='122.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=290),row['completedRecords'])
            profiles=[v for v in row['completedRecords'] if v['kind']=='anonymous-scalar-target-payload']
            self.assertEqual(len(profiles),0 if items is None else len(items))
            self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag122_every_cut_hard_limits_and_trailing(self):
        elem=b'\x04'+scalar_payload(b'wire')+payload(b'key')+target()+payload(None)
        full=b'\xfa\x22\x01\x05'+bytes(13)+struct.pack('<i',2)+b'\xff'+elem
        for child in (full,b'\xfa\x22\x01\xff'):
            r=Reader(child,'122-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'122-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==290 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag122_bad_counts_headers_and_partial_elements(self):
        base=b'\xfa\x22\x01\x05'+bytes(13)
        for value in (-2,2,0x7fffffff):
            r=Reader(base+struct.pack('<i',value)+b'\xff','122-count')
            with self.assertRaises(FrameError) as caught:r.action(0)
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('122-count',17,value,'count-bounds'))
            self.assertEqual(r.pos,21);self.assertFalse(r.records)
        for at in (3,21):
            bad=bytearray(base+struct.pack('<i',1)+b'\xff');bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at+5,'member-count'))
        for lead in (b'\x04\xff',b'\x04\xff'+payload(None)+b'\xff'):
            for value in (-2,0x7fffffff):
                r=Reader(base+struct.pack('<i',1)+lead+struct.pack('<i',value),'122-length')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],caught.exception.diagnostic['category']),(21+len(lead),value,'count-bounds'))
        first=b'\x04\xff'+payload(None)+b'\xff'+payload(None)
        second=b'\x04\xff'+payload(b'key')+target(selector=b'\x03\x59')
        r=Reader(base+struct.pack('<i',2)+first+second,'122-second')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('nested-profile',89))
        self.assertIn(dict(start=21,end=21+len(first),kind='anonymous-scalar-target-payload'),r.records)
        self.assertFalse(any(v.get('tag')==290 for v in r.records))
        self.assertEqual(sum(v['kind']=='anonymous-scalar-target-payload' for v in r.records),1)

    def test_tag135_independent_profiles_and_terminal_payload(self):
        for first in (b'\xff',b'\x01'+payload(None),b'\x01'+payload(b'wire')):
            for nested in (b'\xff',target()):
                for value in (None,b'',b'\xff\x00'):
                    child=b'\xfa\x35\x01\x07'+b'\xff'*13+first+nested+payload(value)
                    end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='135.bin')
                    self.assertEqual(row['diagnostic'],dict(source='135.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=309),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag135_every_cut_hard_limits_and_trailing(self):
        full=b'\xfa\x35\x01\x07'+bytes(13)+b'\x01'+payload(b'id')+target()+payload(b'wire')
        for child in (full,b'\xfa\x35\x01\xff'):
            r=Reader(child,'135-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'135-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==309 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag135_bad_headers_lengths_and_partial_tail(self):
        base=b'\xfa\x35\x01\x07'+bytes(13)
        for lead in (base+b'\x01',base+b'\xff\xff'):
            for value in (-2,2,0x7fffffff):
                r=Reader(lead+struct.pack('<i',value)+b'\xff','135-length')
                with self.assertRaises(FrameError) as caught:r.action(0)
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('135-length',len(lead),value,'count-bounds'))
                self.assertFalse(any(v.get('tag')==309 for v in r.records))
        for at in (3,17):
            bad=bytearray(base+b'\xff\xff'+payload(None));bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']),(at+5,'member-count'))
        first=b'\x01'+payload(b'id')
        child=base+first+target(selector=b'\x03\x59')
        row=event_prefix(prefix(sequence(child)),source='135-unknown')
        self.assertEqual(row['diagnostic']['category'],'nested-profile');self.assertEqual(row['diagnostic']['actual'],89)
        self.assertFalse(any(v.get('tag')==309 for v in row['completedRecords']))
        self.assertTrue(any(v['start']==36 and v['end']==36+len(first) for v in row['completedRecords']))
        r=Reader(base+first+target()+b'\x00','135-tail')
        with self.assertRaises(FrameError):r.action(0)
        self.assertTrue(any(v['start']==17 and v['end']==17+len(first) for v in r.records))
        self.assertFalse(any(v.get('tag')==309 for v in r.records))

    def test_tag18a_two_independent_scalar_profiles(self):
        for first in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'wire')):
            for second in (b'\xff',scalar_payload(None),scalar_payload(b'\xff\x00')):
                child=b'\xfa\x8a\x01\x07'+b'\xff'*17+first+second
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='18a.bin')
                self.assertEqual(row['diagnostic'],dict(source='18a.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=394),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag18a_every_cut_hard_limits_and_trailing(self):
        full=b'\xfa\x8a\x01\x07'+bytes(17)+scalar_payload(b'wire')+scalar_payload(None)
        for child in (full,b'\xfa\x8a\x01\xff'):
            r=Reader(child,'18a-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'18a-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==394 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag18a_bad_headers_lengths_and_partial_second(self):
        base=b'\xfa\x8a\x01\x07'+bytes(17)
        for value in (-2,2,0x7fffffff):
            r=Reader(base+b'\x03'+struct.pack('<i',value)+b'\xff','18a-length')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('18a-length',22,value))
            self.assertEqual(r.pos,26);self.assertFalse(r.records)
        for h in (0,6,8,254):
            r=Reader(base[:3]+bytes([h])+base[4:],'18a-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(3,h))
        first=scalar_payload(b'wire');r=Reader(base+first+b'\x02','18a-second')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(len(base+first),2))
        self.assertFalse(any(v.get('tag')==394 for v in r.records))
        self.assertTrue(any(v['start']==21 and v['end']==21+len(first) for v in r.records))

    def test_tag139_payload_and_terminal_target(self):
        for value in (None,b'',b'wire',b'\xff\x00'):
            for nested in (b'\xff',target(),target(direction_value=b'\xff')):
                child=b'\xfa\x39\x01\x06'+b'\xff'*13+payload(value)+nested
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='139.bin')
                self.assertEqual(row['diagnostic'],dict(source='139.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=313),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag139_every_cut_hard_limits_and_trailing(self):
        full=b'\xfa\x39\x01\x06'+bytes(13)+payload(b'wire')+target()
        for child in (full,b'\xfa\x39\x01\xff'):
            r=Reader(child,'139-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'139-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==313 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag139_bad_length_header_and_partial_target(self):
        base=b'\xfa\x39\x01\x06'+bytes(13)
        for value in (-2,2,0x7fffffff):
            r=Reader(base+struct.pack('<i',value)+b'\xff','139-length')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('139-length',17,value))
            self.assertEqual(r.pos,21);self.assertFalse(r.records)
        for h in (0,5,7,254):
            r=Reader(base[:3]+bytes([h])+base[4:],'139-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(3,h))
        child=base+payload(b'wire')+target(selector=b'\x03\x59')
        row=event_prefix(prefix(sequence(child)),source='139-unknown')
        self.assertEqual(row['diagnostic']['category'],'nested-profile');self.assertEqual(row['diagnostic']['actual'],89)
        self.assertFalse(any(v.get('tag')==313 for v in row['completedRecords']))
        self.assertTrue(any(v['kind']=='anonymous-byte-payload' and v['start']==36 and v['end']==44 for v in row['completedRecords']))

    def test_tag187_assignment_list_and_three_targets(self):
        item=b'\x06'+bytes(4)+payload(None)+b'\xff'*4+payload(b'wire')+payload(b'')+b'\xfe'
        for items in (None,(),(b'\xff',),(item,b'\xff',item)):
            for targets in ((b'\xff',)*3,(target(),b'\xff',target()),(b'\xff',target(),b'\xff')):
                child=b'\xfa\x87\x01\x09'+bytes(13)+struct.pack('<i',-1 if items is None else len(items))+b''.join(items or ())+b'\x80'+b''.join(targets)
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='187.bin')
                self.assertEqual(row['diagnostic'],dict(source='187.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=391),row['completedRecords'])
                self.assertFalse(row['wholeSchemaExact'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag187_every_cut_hard_limits_and_trailing(self):
        item=b'\x06'+bytes(4)+payload(b'wire')+bytes(4)+payload(None)+payload(b'')+b'\xff'
        full=b'\xfa\x87\x01\x09'+bytes(13)+struct.pack('<i',1)+item+b'\x80'+target()+b'\xff'+target()
        for child in (full,b'\xfa\x87\x01\xff'):
            r=Reader(child,'187-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'187-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==391 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag187_count_reserves_tail_and_unknown_third_target(self):
        base=b'\xfa\x87\x01\x09'+bytes(13)
        for n in (-2,1,0x7fffffff):
            r=Reader(base+struct.pack('<i',n)+b'\xff'*4,'187-count')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('187-count',17,n))
            self.assertEqual(r.pos,21);self.assertFalse(r.records)
        for h in (0,8,10,254):
            r=Reader(base[:3]+bytes([h])+base[4:],'187-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(3,h))
        child=base+struct.pack('<i',0)+b'\x80\xff\xff'+target(selector=b'\x03\x59')
        row=event_prefix(prefix(sequence(child)),source='187-unknown')
        self.assertEqual(row['diagnostic']['category'],'nested-profile');self.assertEqual(row['diagnostic']['actual'],89)
        self.assertFalse(any(v.get('tag')==391 for v in row['completedRecords']))
        for start in (41,42):self.assertIn(dict(start=start,end=start+1,kind='anonymous-target-profile'),row['completedRecords'])

    def test_tag188_independent_profiles_and_terminal_target(self):
        for first in (b'\xff',pair(None,b'',255),pair(b'wire',b'\xff\x00',128)):
            for second in (b'\xff',scalar_payload(None),scalar_payload(b'')):
                for third,fourth in ((b'\xff',target()),(target(),b'\xff'),(target(),target())):
                    child=b'\xfa\x88\x01\x08'+b'\xff'*13+first+second+third+fourth
                    end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='188.bin')
                    self.assertEqual(row['diagnostic'],dict(source='188.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=392),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag188_every_cut_hard_limits_and_trailing(self):
        full=b'\xfa\x88\x01\x08'+bytes(13)+pair(b'wire',None)+scalar_payload()+target()+target(direction_value=b'\xff')
        for child in (full,b'\xfa\x88\x01\xff'):
            r=Reader(child,'188-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'188-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==392 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag188_invalid_header_count_and_unknown_final_target(self):
        base=b'\xfa\x88\x01\x08'+bytes(13)
        for value in (0,7,9,254):
            r=Reader(base[:3]+bytes([value])+base[4:]+b'\xff'*4,'188-bounds')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(3,value))
        for value in (-2,0x7fffffff):
            r=Reader(base+b'\x03'+struct.pack('<i',value)+b'\xff'*6,'188-bounds')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('188-bounds',18,value))
            self.assertLessEqual(r.pos,22);self.assertFalse(r.records)
        child=base+b'\xff\xff'+target()+target(selector=b'\x03\x59')
        row=event_prefix(prefix(sequence(child)),source='188-unknown')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertEqual(row['diagnostic']['actual'],89)
        self.assertFalse(any(v.get('tag')==392 for v in row['completedRecords']))
        self.assertIn(dict(start=38,end=38+len(target()),kind='anonymous-target-profile'),row['completedRecords'])

    def test_tag40_direct_nullable_member_one_list(self):
        for values in (None,(),(0,),(0xffffffff,0x80000000,0x7fc00000)):
            items=struct.pack('<i',-1 if values is None else len(values))+b''.join(b'\x01'+struct.pack('<I',v) for v in values or ())
            child=b'\x40\x06\xfe'+b'\xff'*16+items;end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='40.bin')
            self.assertEqual(row['diagnostic'],dict(source='40.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=64),row['completedRecords'])
            self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag40_every_cut_null_extended_hard_limits_and_trailing(self):
        full=b'\x40\x06'+bytes(17)+struct.pack('<i',3)+b'\xff\x01'+b'\xff'*4+b'\x01'+bytes(4)
        for child in (full,b'\xfa\x40\x00'+full[1:],b'\x40\xff',b'\xfa\x40\x00\xff'):
            r=Reader(child,'40-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'40-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==64 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag40_header_and_count_fail_before_elements(self):
        child=b'\x40\x06'+bytes(17)+struct.pack('<i',1)+b'\xff'
        for at,values in ((1,(0,254)),(19,(-2,2,0x7fffffff))):
            for value in values:
                bad=bytearray(child)
                if at==1:bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'40-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('40-bounds',at,value))
                self.assertFalse(r.records)
                self.assertLessEqual(r.pos,23)

        for value in (0,2,254):
            r=Reader(b'\x40\x06'+bytes(17)+struct.pack('<i',1)+bytes([value])+bytes(4),'40-element')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(23,value))
            self.assertFalse(any(v.get('tag')==64 for v in r.records))

    def test_tag77_direct_nullable_dword_list(self):
        for values in (None,(),(0,),(0xffffffff,0x80000000,0x7fc00000)):
            items=struct.pack('<i',-1 if values is None else len(values))+b''.join(struct.pack('<I',v) for v in values or ())
            child=b'\x77\x05\xfe'+b'\xff'*12+items;end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='77.bin')
            self.assertEqual(row['diagnostic'],dict(source='77.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=119),row['completedRecords'])
            self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag77_every_cut_null_extended_hard_limits_and_trailing(self):
        full=b'\x77\x05'+bytes(13)+struct.pack('<iIII',3,0,0xffffffff,0x80000000)
        for child in (full,b'\xfa\x77\x00'+full[1:],b'\x77\xff',b'\xfa\x77\x00\xff'):
            r=Reader(child,'77-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'77-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==119 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag77_header_and_count_fail_before_elements(self):
        child=b'\x77\x05'+bytes(13)+struct.pack('<iII',2,1,2)
        for at,values in ((1,(0,254)),(15,(-2,3,0x7fffffff))):
            for value in values:
                bad=bytearray(child)
                if at==1:bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'77-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('77-bounds',at,value))
                self.assertFalse(r.records)
                self.assertLessEqual(r.pos,19)

    def test_tag6b_three_independent_terminal_payloads(self):
        for first in (None,b'',b'wire'):
            for second in (None,b'',b'\xff\x00'):
                for third in (None,b'',b'last'):
                    child=b'\x6b\x07\xfe'+b'\xff'*12+payload(first)+payload(second)+payload(third)
                    end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='6b.bin')
                    self.assertEqual(row['diagnostic'],dict(source='6b.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=107),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag6b_every_cut_null_extended_hard_limits_and_trailing(self):
        full=b'\x6b\x07'+bytes(13)+payload(b'a')+payload(b'bb')+payload(b'ccc')
        for child in (full,b'\xfa\x6b\x00'+full[1:],b'\x6b\xff',b'\xfa\x6b\x00\xff'):
            r=Reader(child,'6b-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'6b-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==107 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag6b_each_length_is_bounded_and_header_is_exact(self):
        child=b'\x6b\x07'+bytes(13)+payload(b'a')+payload(b'bb')+payload(b'ccc')
        for at,values in ((1,(0,254)),(15,(-2,0x7fffffff)),(20,(-2,0x7fffffff)),(26,(-2,0x7fffffff))):
            for value in values:
                bad=bytearray(child)
                if at==1:bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'6b-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('6b-bounds',at,value))
                self.assertFalse(any(v.get('tag')==107 for v in r.records))
                self.assertEqual(len(r.records),{1:0,15:0,20:1,26:2}[at])

    def test_tag63_direct_terminal_query_boundaries(self):
        for query in (b'\xff',query41(None),query41(),query41((0,0xffffffff,0x80000000))):
            child=b'\x63\x05\xfe'+b'\xff'*12+query;end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='63.bin')
            self.assertEqual(row['diagnostic'],dict(source='63.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=99),row['completedRecords'])
            self.assertIn(dict(start=34,end=end,kind='anonymous-query-profile'),row['completedRecords'])
            self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag63_all_cuts_null_extended_hard_limits_and_trailing(self):
        full=b'\x63\x05'+bytes(13)+query41((0,0xffffffff,0x80000000))
        for child in (full,b'\xfa\x63\x00'+full[1:],b'\x63\xff',b'\xfa\x63\x00\xff'):
            r=Reader(child,'63-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'63-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==99 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag63_bad_headers_counts_and_incomplete_query(self):
        child=b'\x63\x05'+bytes(13)+query41((1,2))
        for at,values in ((1,(0,254)),(15,(0,254)),(20,(-2,0x7fffffff))):
            for value in values:
                bad=bytearray(child)
                if at in (1,15):bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'63-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('63-bounds',at,value))
        r=Reader(child,'63-query',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertFalse(r.records)

    def test_tag86_three_independent_scalars_payload_and_final_byte(self):
        for first in (b'\xff',scalar_payload(None)):
            for middle in (b'\xff',scalar_payload(b'wire')):
                for last in (b'\xff',scalar_payload(b'')):
                    for value in (None,b'',b'\xff\x00'):
                        child=b'\x86\x09\xfe'+b'\xff'*12+first+payload(value)+middle+last+b'\x80'
                        end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='86.bin')
                        self.assertEqual(row['diagnostic'],dict(source='86.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                        self.assertIn(dict(start=19,end=end,kind='union',tag=134),row['completedRecords'])
                        expected=[];at=34
                        for part,skip in ((first,len(payload(value))),(middle,0),(last,0)):
                            expected.append((at,at+len(part)));at+=len(part)+skip
                        actual=[(v['start'],v['end']) for v in row['completedRecords'] if v['kind']=='anonymous-scalar-payload']
                        self.assertEqual(actual,expected)
                        self.assertFalse(row['wholeSchemaExact'])
                        self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag86_all_cuts_extended_null_hard_limits_and_trailing(self):
        full=b'\x86\x09'+bytes(13)+scalar_payload(None)+payload(b'wire')+scalar_payload(b'\xff')+scalar_payload(b'')+b'\xfe'
        for child in (full,b'\xfa\x86\x00'+full[1:],b'\x86\xff',b'\xfa\x86\x00\xff'):
            r=Reader(child,'86-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'86-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==134 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag86_bad_headers_lengths_and_mandatory_byte_after_profiles(self):
        child=b'\x86\x09'+bytes(13)+scalar_payload(None)+payload(b'wire')+scalar_payload(b'\xff')+scalar_payload(b'')+b'\xfe'
        # Independently calculated header and signed-length offsets.
        for at,values in ((1,(0,254)),(15,(0,254)),(33,(0,254)),(44,(0,254)),
                          (16,(-2,0x7fffffff)),(25,(-2,0x7fffffff)),(34,(-2,0x7fffffff)),(45,(-2,0x7fffffff))):
            for value in values:
                bad=bytearray(child)
                if at in (1,15,33,44):bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'86-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('86-bounds',at,value))
        r=Reader(child,'86-tail');r.action(0);completed=[v for v in r.records if v.get('tag')!=134]
        r=Reader(child,'86-tail',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertEqual(r.records,completed)
        self.assertEqual(len([v for v in r.records if v['kind']=='anonymous-scalar-payload']),3)

    def test_tag13a_two_payloads_have_independent_null_and_length_boundaries(self):
        for first in (None,b'',b'\xff\x00'):
            for second in (None,b'',b'wire'):
                child=b'\xfa\x3a\x01\x06\xfe'+b'\xff'*12+payload(first)+payload(second)
                split=36+len(payload(first));end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='13a.bin')
                self.assertEqual(row['diagnostic'],dict(source='13a.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=314),row['completedRecords'])
                self.assertIn(dict(start=36,end=split,kind='anonymous-byte-payload',isNull=first is None),row['completedRecords'])
                self.assertIn(dict(start=split,end=end,kind='anonymous-byte-payload',isNull=second is None),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
                self.assertFalse(row['wholeSchemaExact'])

    def test_tag13a_all_cuts_hard_limits_null_wrapper_and_trailing(self):
        for child in (b'\xfa\x3a\x01\x06'+bytes(13)+payload(b'wire')+payload(b'\xff\x00'),b'\xfa\x3a\x01\xff'):
            r=Reader(child,'13a-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'13a-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==314 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag13a_bad_lengths_headers_and_incomplete_second_payload(self):
        child=b'\xfa\x3a\x01\x06'+bytes(13)+payload(b'wire')+payload(b'\xff\x00')
        for at,values in ((3,(0,254)),(17,(-2,0x7fffffff)),(25,(-2,0x7fffffff))):
            for value in values:
                bad=bytearray(child)
                if at==3:bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'13a-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],caught.exception.diagnostic['category']),('13a-bounds',at,value,'member-count' if at==3 else 'count-bounds'))
        for n in range(25,len(child)):
            r=Reader(child,'13a-second',n)
            with self.assertRaises(FrameError):r.action(0)
            self.assertIn(dict(start=17,end=25,kind='anonymous-byte-payload',isNull=False),r.records)
            self.assertFalse(any(v.get('tag')==314 for v in r.records))

    def test_tag83_scalar32_byte_target_scalar_order(self):
        for bits in (0,0xffffffff,0x80000000,0x7fc00000):
            for first in (b'\xff',target()):
                for last in (b'\xff',scalar_payload(None),scalar_payload(b'wire')):
                    child=b'\x83\x08\xfe'+b'\xff'*12+struct.pack('<I',bits)+b'\x80'+first+last
                    end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='83.bin')
                    self.assertEqual(row['diagnostic'],dict(source='83.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=131),row['completedRecords'])
                    self.assertIn(dict(start=34,end=38,kind='anonymous-scalar32'),row['ranges'])
                    self.assertIn(dict(start=39+len(first),end=end,kind='anonymous-scalar-payload'),row['completedRecords'])
                    self.assertFalse(row['wholeSchemaExact'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag83_all_cuts_extended_null_hard_limits_and_trailing(self):
        full=b'\x83\x08'+bytes(17)+b'\xfe'+target()+scalar_payload(b'wire')
        for child in (full,b'\xfa\x83\x00'+full[1:],b'\x83\xff',b'\xfa\x83\x00\xff'):
            r=Reader(child,'83-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'83-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==131 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag83_nested_count_headers_and_final_scalar_failure(self):
        child=b'\x83\x08'+bytes(17)+b'\xfe'+target()+scalar_payload(b'wire')
        r=Reader(child,'83-bounds');r.action(0)
        for span in [v for v in r.ranges if v['kind'] in ('member-header','count-i32')]:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'83-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('83-bounds',at,value))
        r=Reader(child,'83-final',20+len(target()))
        with self.assertRaises(FrameError):r.action(0)
        completed=list(r.records);self.assertTrue(completed)
        r=Reader(child,'83-final',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertEqual(r.records[:len(completed)],completed)
        self.assertFalse(any(v.get('tag')==131 for v in r.records))
        gap=b'\x83\x08'+bytes(18)+target(selector=b'\x03\x59')+b'\xff'
        r=Reader(gap,'83-gap')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'nested-profile')
        self.assertFalse(any(v.get('tag')==131 for v in r.records))

    def test_tagfc_extended_only_target_then_scalar_exact_end(self):
        for first in (b'\xff',target()):
            for last in (b'\xff',scalar_payload(None),scalar_payload(b'\xff\x00')):
                child=b'\xfa\xfc\x00\x06\xfe'+b'\xff'*12+first+last
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='fc.bin')
                self.assertEqual(row['diagnostic'],dict(source='fc.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=252),row['completedRecords'])
                self.assertIn(dict(start=36+len(first),end=end,kind='anonymous-scalar-payload'),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
                self.assertFalse(row['wholeSchemaExact'])
        for child in (b'\xfc\xff',b'\xfc\x06'+bytes(13)+b'\xff\xff'):
            r=Reader(child,'fc-reserved')
            with self.assertRaises(Unsupported) as caught:r.action(0)
            self.assertEqual((r.pos,caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(0,0,252))
            self.assertEqual(r.records,[])

    def test_tagfc_every_cut_hard_limit_null_wrapper_and_trailing(self):
        full=b'\xfa\xfc\x00\x06'+bytes(13)+target()+scalar_payload(b'wire')
        for child in (full,b'\xfa\xfc\x00\xff'):
            r=Reader(child,'fc-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'fc-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==252 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tagfc_malformed_nested_lengths_and_final_scalar_required(self):
        child=b'\xfa\xfc\x00\x06'+bytes(13)+target()+scalar_payload(b'wire')
        r=Reader(child,'fc-bounds');r.action(0)
        for span in [v for v in r.ranges if v['kind'] in ('member-header','count-i32')]:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'fc-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('fc-bounds',at,value))
        target_end=17+len(target());r=Reader(child,'fc-final',target_end)
        with self.assertRaises(FrameError):r.action(0)
        completed=list(r.records);self.assertTrue(completed)
        r=Reader(child,'fc-final',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertEqual(r.records[:len(completed)],completed)
        self.assertFalse(any(v.get('tag')==252 for v in r.records))
        gap=b'\xfa\xfc\x00\x06'+bytes(13)+target(selector=b'\x03\x59')+b'\xff'
        r=Reader(gap,'fc-gap')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'nested-profile')
        self.assertFalse(any(v.get('tag')==252 for v in r.records))

    def test_tag175_terminal_payload_null_empty_and_arbitrary_bytes(self):
        for value in (None,b'',b'wire',b'\xff\x00\xfe'):
            child=b'\xfa\x75\x01\x05\xfe'+b'\xff'*12+payload(value)
            end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='175.bin')
            self.assertEqual(row['diagnostic'],dict(source='175.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=373),row['completedRecords'])
            self.assertIn(dict(start=36,end=end,kind='anonymous-byte-payload',isNull=value is None),row['completedRecords'])
            self.assertFalse(row['wholeSchemaExact'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag175_all_cuts_hard_limits_null_wrapper_and_trailing(self):
        for child in (b'\xfa\x75\x01\x05\xfe'+b'\xff'*12+payload(b'\xff\x00wire'),b'\xfa\x75\x01\xff'):
            r=Reader(child,'175-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'175-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==373 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag175_malformed_header_and_payload_length_diagnostics(self):
        child=b'\xfa\x75\x01\x05'+bytes(13)+payload(b'wire')
        for at,value,category in ((3,0,'member-count'),(3,254,'member-count'),(17,-2,'count-bounds'),(17,0x7fffffff,'count-bounds')):
            bad=bytearray(child)
            if at==3:bad[at]=value
            else:struct.pack_into('<i',bad,at,value)
            r=Reader(bad,'175-bounds')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],caught.exception.diagnostic['category']),('175-bounds',at,value,category))
            self.assertFalse(any(v.get('tag')==373 for v in r.records))

    def test_tag93_shared_wire_profiles_keep_distinct_union_identity(self):
        child=b'\x93'+tag92()[1:]
        row=event_prefix(prefix(sequence(child,b'\x59')),source='93.bin')
        self.assertEqual(row['diagnostic'],dict(source='93.bin',offset=138,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=138,kind='union',tag=147),row['completedRecords'])
        self.assertFalse(any(v.get('tag')==146 for v in row['completedRecords']))
        for a,b,kind in ((17,28,'anonymous-scalar-bytes-profile'),(32,74,'anonymous-input-profile'),
                         (38,62,'anonymous-assignment-profile'),(84,94,'anonymous-scalar-payload')):
            self.assertIn(dict(start=19+a,end=19+b,kind=kind),row['completedRecords'])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag93_every_cut_hard_limit_extended_null_and_trailing(self):
        full=b'\x93'+tag92()[1:-1]+target()
        for child in (full,b'\xfa\x93\x00'+full[1:],b'\x93\xff',b'\xfa\x93\x00\xff'):
            r=Reader(child,'93-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'93-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==147 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag93_bad_counts_headers_and_mandatory_final_target(self):
        child=b'\x93'+tag92()[1:]
        for at in (22,28,34,43,53,57,63,69,79,85,95,99,105,109):
            for value in (-2,0x7fffffff):
                bad=bytearray(child);struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'93-count')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual'],caught.exception.diagnostic['category']),('93-count',at,value,'count-bounds'))
        for at in (1,17,32,38,84,118):
            bad=bytearray(child);bad[at]=42;r=Reader(bad,'93-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['category']), (at,'member-count'))
        r=Reader(child,'93-final',118)
        with self.assertRaises(FrameError):r.action(0)
        self.assertTrue(any(v['kind']=='anonymous-input-profile' for v in r.records))
        self.assertFalse(any(v.get('tag')==147 for v in r.records))
        gap=child[:-1]+target(selector=b'\x03\x59');r=Reader(gap,'93-gap')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'nested-profile')
        self.assertFalse(any(v.get('tag')==147 for v in r.records))

    def test_tag93_null_lists_empty_lists_and_nested_assignments(self):
        for count in (-1,0):
            for item in (b'\xff',b'\x05\xfe'+struct.pack('<i',count)+payload(None)+payload(b'')+b'\x80'):
                child=(b'\x93\x13'+bytes(15)+b'\xff'+struct.pack('<i',1)+item+bytes(4)+payload(None)+
                       b'\xff\x80'+struct.pack('<i',count)+bytes(5)+b'\xff')
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
            child=(b'\x93\x13'+bytes(15)+b'\xff'+struct.pack('<i',count)+bytes(4)+payload(None)+
                   b'\xff\x80'+struct.pack('<i',count)+bytes(5)+b'\xff')
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag7b_target_scalar_and_payload_keep_source_order(self):
        child=tag7b();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='7b.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=123),row['completedRecords'])
        target_end=19+15+len(target())
        self.assertIn(dict(start=19+15,end=target_end,kind='anonymous-target-profile'),row['completedRecords'])
        self.assertIn(dict(start=target_end,end=target_end+4,kind='anonymous-scalar32'),row['ranges'])
        self.assertEqual(row['ranges'][-1],dict(start=end-4,end=end,kind='anonymous-scalar32'))
        self.assertEqual(row['diagnostic'],dict(source='7b.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag7b_null_extended_truncations_trailing_and_limits(self):
        for child in (tag7b(),b'\xfa\x7b\x00'+tag7b()[1:],b'\x7b\xff',
                      tag7b(b'\xff',b'\xff'),tag7b(value=scalar_payload(None)),tag7b(value=scalar_payload(b''))):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='7b-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='7b-limit',limit=n))

    def test_tag7b_bad_headers_lengths_and_nested_gap(self):
        raw=prefix(sequence(tag7b()));good=event_prefix(raw,source='7b-bounds')
        self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='7b-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
                self.assertEqual(row['diagnostic']['source'],'7b-bounds')
        row=event_prefix(prefix(sequence(tag7b(t=target(selector=b'\x03\x06'+bytes(8))))),source='7b-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==123 for r in row['completedRecords']))

    def test_tag16e_source_segments_targets_and_zero_member_finder(self):
        child=tag16e();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='16e.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=366),row['completedRecords'])
        targets=[r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile']
        first=19+17+2+8+len(payload(b'wire'))+4
        second=first+len(target(selector=b'\x03\x05\x00'+bytes(8)))
        self.assertEqual([(r['start'],r['end']) for r in targets],[(first,second),(second,end-1)])
        finder=next(r for r in row['completedRecords'] if r['kind']=='anonymous-selector-finder-profile')
        self.assertEqual(finder['end']-finder['start'],2)
        self.assertEqual(row['ranges'][-1],dict(start=end-1,end=end,kind='anonymous-nonzero-byte'))
        self.assertEqual(row['diagnostic'],dict(source='16e.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag16e_null_payloads_truncations_trailing_and_limits(self):
        for child in (tag16e(),tag16e(None),tag16e(b''),b'\xfa\x6e\x01\xff',
                      tag16e(first=b'\xff',second=b'\xff'),
                      tag16e(first=target(selector=b'\x03\x05\xff'+bytes(8))),
                      tag16e(first=target(selector=b'\x03\xfa\x05\x00\x00'+bytes(8)))):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='16e-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='16e-limit',limit=n))

    def test_tag16e_bad_headers_counts_and_bounded_nested_gaps(self):
        raw=prefix(sequence(tag16e()));good=event_prefix(raw,source='16e-bounds')
        self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='16e-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
                self.assertEqual(row['diagnostic']['source'],'16e-bounds')
        gap=target(selector=b'\x03\x06'+bytes(8))
        for child in (tag16e(first=gap),tag16e(second=gap)):
            row=event_prefix(prefix(sequence(child)),source='16e-gap')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==366 for r in row['completedRecords']))

    def test_tag80_two_independent_target_ranges_and_unknown_boundary(self):
        child=tag80();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='80.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=128),row['completedRecords'])
        targets=[r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile']
        first=19+15;second=first+len(target())
        self.assertEqual([(r['start'],r['end']) for r in targets],[(first,second),(second,end)])
        self.assertEqual(end-second,len(target(direction_value=b'\xff')))
        self.assertEqual(row['diagnostic'],dict(source='80.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag80_null_extended_truncations_trailing_and_hard_limits(self):
        for child in (tag80(),b'\xfa\x80\x00'+tag80()[1:],b'\x80\xff',
                      tag80(b'\xff',b'\xff'),tag80(first=b'\xff'),tag80(second=b'\xff')):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='80-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='80-limit',limit=n))

    def test_tag80_bad_headers_counts_and_either_nested_gap(self):
        raw=prefix(sequence(tag80()));good=event_prefix(raw,source='80-bounds')
        self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='80-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
                self.assertEqual(row['diagnostic']['source'],'80-bounds')
        gap=target(selector=b'\x03\x11'+bytes(8))
        for child in (tag80(first=gap),tag80(second=gap)):
            row=event_prefix(prefix(sequence(child)),source='80-gap')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==128 for r in row['completedRecords']))

    def test_tagb6_target_then_final_byte_and_unknown_boundary(self):
        child=b'\xb6\x06\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+target()+b'\x80'
        end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='b6.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=182),row['completedRecords'])
        self.assertEqual(row['ranges'][-1],dict(start=end-1,end=end,kind='anonymous-nonzero-byte'))
        self.assertEqual(row['diagnostic'],dict(source='b6.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tagb6_null_extended_truncations_trailing_and_limits(self):
        for child in (b'\xb6\x06'+bytes(13)+target()+b'\xff',
                      b'\xfa\xb6\x00\x06'+bytes(13)+b'\xff\xfe',
                      b'\xb6\xff',b'\xb6\x06'+bytes(13)+b'\xff\x80'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='b6-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='b6-limit',limit=n))

    def test_tagb6_bad_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(b'\xb6\x06'+bytes(13)+target()+b'\x80'))
        good=event_prefix(raw,source='b6-bounds')
        self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='b6-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
                self.assertEqual(row['diagnostic']['source'],'b6-bounds')
        child=b'\xb6\x06'+bytes(13)+target(selector=b'\x03\x11'+bytes(8))+b'\x80'
        row=event_prefix(prefix(sequence(child)),source='b6-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==182 for r in row['completedRecords']))

    def test_tag7c_target_query_and_distinct_collider_ranges(self):
        child=tag7c();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='7c.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=124),row['completedRecords'])
        collider=next(r for r in row['completedRecords'] if r['kind']=='anonymous-collider-shape-profile')
        self.assertEqual(collider['end']-collider['start'],len(collider16()))
        vectors=[r for r in row['ranges'] if r['kind']=='anonymous-raw12' and collider['start']<r['start']<collider['end']]
        self.assertEqual(len(vectors),3);self.assertTrue(all(r['end']-r['start']==12 for r in vectors))
        query=next(r for r in row['completedRecords'] if r['kind']=='anonymous-query-profile')
        self.assertEqual((query['start'],query['end']),(end-21,end))
        self.assertEqual(row['diagnostic'],dict(source='7c.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag7c_nulls_extended_all_truncations_and_limits(self):
        for child in (tag7c(),b'\xfa\x7c\x00'+tag7c()[1:],b'\x7c\xff',tag7c(b'\xff',b'\xff'),
                      tag7c(query=b'\x02'+bytes(4)+struct.pack('<i',-1)),tag7c(query=b'\x02'+bytes(8)),
                      tag7c(t=target(selector=b'\x03'+finder18(b'\xff')+bytes(8))),
                      tag7c(t=target(selector=b'\x03\x12\xff'+bytes(8)))):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='7c-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='7c-limit',limit=n))

    def test_tag7c_bad_headers_lengths_counts_and_unknown_finder(self):
        raw=prefix(sequence(tag7c()));good=event_prefix(raw,source='7c-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='7c-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        for bad_header in (18,3):
            shape=bytes([bad_header])+collider16()[1:]
            row=event_prefix(prefix(sequence(tag7c(t=target(selector=b'\x03'+finder18(shape)+bytes(8))))),source='wrong-shape')
            self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['expected'],16)
        row=event_prefix(prefix(sequence(tag7c(t=target(selector=b'\x03\x11'+bytes(8))))),source='7c-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==124 for r in row['completedRecords']))

    def test_tagfd_exact_fixed_record_and_next_unknown_boundary(self):
        child=b'\xfa\xfd\x00\x04\xfe'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='fd.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',36))
        self.assertEqual(row['completedRecords'],[dict(start=19,end=36,kind='union',tag=253)])
        self.assertEqual(row['ranges'][-5:],[dict(start=22,end=23,kind='member-header'),
            dict(start=23,end=24,kind='anonymous-nonzero-byte'),
            dict(start=24,end=28,kind='anonymous-scalar32'),dict(start=28,end=32,kind='anonymous-scalar32'),
            dict(start=32,end=36,kind='anonymous-scalar32')])
        self.assertEqual(row['diagnostic'],dict(source='fd.bin',offset=36,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[36,39]);self.assertFalse(row['wholeSchemaExact'])

    def test_tagfd_null_all_truncations_trailing_and_hard_limits(self):
        for child in (b'\xfa\xfd\x00\xff',b'\xfa\xfd\x00\x04\x80'+bytes(range(12))):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='fd-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='fd-limit',limit=n))

    def test_tagfd_bad_header_count_and_physical_reserved_encoding(self):
        raw=prefix(sequence(b'\xfa\xfd\x00\x04'+bytes(13)))
        for at in (0,5,14,22):
            bad=bytearray(raw);bad[at]=42
            row=event_prefix(bad,source='fd-header')
            self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        for value in (-2,2147483647):
            bad=bytearray(raw);struct.pack_into('<i',bad,15,value)
            row=event_prefix(bad,source='fd-count')
            self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],15)
        for suffix in (b'',b'\xff',b'\x04'+bytes(13),raw):
            reader=Reader(b'\xfd'+suffix,'physical-fd')
            with self.assertRaises(Unsupported) as caught:reader.action(0)
            self.assertEqual(caught.exception.diagnostic,dict(source='physical-fd',offset=0,expected='supported current union tag',actual=253,category='union-tag'))
            self.assertEqual((reader.pos,reader.ranges,reader.records),(0,[],[]))

    def test_tag96_distinct_member_three_profiles_and_following_boundary(self):
        child=tag96();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='96.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=150),row['completedRecords'])
        nested=[r for r in row['completedRecords'] if r['kind'] in ('anonymous-scalar-payload','anonymous-paired-payload','anonymous-target-profile')]
        self.assertEqual([r['kind'] for r in nested],['anonymous-scalar-payload','anonymous-paired-payload','anonymous-target-profile'])
        self.assertEqual([(r['start'],r['end']) for r in nested[:2]],[(35,51),(51,70)])
        self.assertEqual(row['diagnostic'],dict(source='96.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag96_null_extended_truncation_and_hard_limits(self):
        for child in (tag96(),b'\xfa\x96\x00'+tag96()[1:],b'\x96\xff',tag96(b'\xff',b'\xff',b'\xff'),
                      tag96(scalar_payload(None),pair(None,b'')),tag96(key=pair(b'long-variable-key',b'\xff\xfe'))):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='96-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='96-limit',limit=n))

    def test_tag96_bad_headers_payload_lengths_and_nested_gap(self):
        raw=prefix(sequence(tag96()));good=event_prefix(raw,source='96-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='96-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        row=event_prefix(prefix(sequence(tag96(t=target(selector=b'\x03\xfe'+bytes(8))))),source='96-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==150 for r in row['completedRecords']))

    def test_tagfe_extended_identity_nested_order_and_opaque_tail(self):
        child=tagfe();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='fe.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=254),row['completedRecords'])
        self.assertIn(dict(start=19,end=22,kind='union-tag'),row['ranges'])
        nested=[r for r in row['completedRecords'] if r['kind'] in ('anonymous-scalar-payload','anonymous-target-profile')]
        # Separate source reads survive even when managed argument types repeat.
        scalars=[r for r in nested if r['kind']=='anonymous-scalar-payload']
        self.assertEqual([(r['start'],r['end']) for r in scalars[:2]],
                         [(49,63),(67,77)])
        self.assertEqual(row['diagnostic'],dict(source='fe.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tagfe_nulls_truncations_trailing_and_hard_limits(self):
        for child in (tagfe(),b'\xfa\xfe\x00\xff',tagfe(values=(b'\xff',b'\xff'),targets=(b'\xff',b'\xff')),
                      tagfe(values=(scalar_payload(b'longer-key'),scalar_payload(b'')))):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='fe-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='fe-limit',limit=n))

    def test_tagfe_bad_headers_lengths_and_each_nested_gap(self):
        raw=prefix(sequence(tagfe()));good=event_prefix(raw,source='fe-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='fe-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        gap=target(selector=b'\x03\xfe'+bytes(8))
        for targets in ((gap,target()),(target(),gap)):
            row=event_prefix(prefix(sequence(tagfe(targets=targets))),source='fe-gap')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==254 for r in row['completedRecords']))

    def test_tagfe_physical_reserved_lead_never_selects_extended_profile(self):
        for suffix in (b'',b'\xff',tagfe()[3:],tagfe()):
            reader=Reader(b'\xfe'+suffix,'physical-fe')
            with self.assertRaises(Unsupported) as caught:reader.action(0)
            self.assertEqual(caught.exception.diagnostic,dict(source='physical-fe',offset=0,expected='supported current union tag',actual=254,category='union-tag'))
            self.assertEqual((reader.pos,reader.ranges,reader.records),(0,[],[]))

    def test_tag6e_keeps_identity_with_shared_structural_profile(self):
        child=b'\x6e'+tag65()[1:];end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='6e.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=110),row['completedRecords'])
        self.assertFalse(any(r.get('tag')==101 for r in row['completedRecords']))
        self.assertEqual(row['diagnostic'],dict(source='6e.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag6e_null_extended_truncation_and_hard_limits(self):
        for child in (b'\x6e'+tag65()[1:],b'\xfa\x6e\x00'+tag65()[1:],b'\x6e\xff',
                      b'\x6e'+tag65(b'\xff',b'\xff')[1:],b'\x6e'+tag65(value=scalar_payload(b'long-key'))[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='6e-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='6e-limit',limit=n))

    def test_tag6e_bad_headers_lengths_and_nested_gap(self):
        raw=prefix(sequence(b'\x6e'+tag65()[1:]));good=event_prefix(raw,source='6e-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='6e-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        child=b'\x6e'+tag65(t=target(selector=b'\x03\xfe'+bytes(8)))[1:]
        row=event_prefix(prefix(sequence(child)),source='6e-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==110 for r in row['completedRecords']))

    def test_tag157_extended_record_and_variable_boundaries(self):
        child=tag157();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='157.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=343),row['completedRecords'])
        self.assertIn(dict(start=53,end=133,kind='anonymous-target-profile'),row['completedRecords'])
        self.assertEqual(row['diagnostic'],dict(source='157.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag157_nulls_payload_lengths_and_every_limit(self):
        for child in (tag157(),tag157(b'\xff',b'\xff',None),tag157(key=b''),tag157(value=scalar_payload(b'long-value')),b'\xfa\x57\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='157-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='157-limit',limit=n))

    def test_tag157_bad_headers_lengths_and_nested_boundary(self):
        raw=prefix(sequence(tag157()));good=event_prefix(raw,source='157-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='157-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        row=event_prefix(prefix(sequence(tag157(t=target(selector=b'\x03\xfe'+bytes(8))))),source='157-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==343 for r in row['completedRecords']))
        # A member-eleven header alone does not select the damage action body.
        with self.assertRaises(FrameError):sequence_frame(sequence(b'\xfa\x57\x01'+tag9a()[1:]))

    def test_tag169_extended_record_and_fixed_source_ranges(self):
        child=tag169();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='169.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertIn(dict(start=19,end=end,kind='union',tag=361),row['completedRecords'])
        self.assertEqual(row['diagnostic'],dict(source='169.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertEqual([(r['end']-r['start']) for r in row['ranges'] if r['kind'] in ('anonymous-raw12','anonymous-raw16')],[12,16])
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag169_lists_nulls_and_every_limit(self):
        assignment=b'\x06'+bytes(4)+payload(b'k')+bytes(4)+payload(None)+payload(b'v')+b'\xff'
        for child in (tag169(),tag169((assignment,b'\xff')),tag169(None,None,(b'\xff',)*2,b'\xff',b'\xff'),b'\xfa\x69\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='169-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='169-limit',limit=n))

    def test_tag169_bad_headers_counts_and_nested_boundaries(self):
        raw=prefix(sequence(tag169()));good=event_prefix(raw,source='169-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='169-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        for i in range(2):
            targets=[target()]*2;targets[i]=target(selector=b'\x03\xfe'+bytes(8))
            row=event_prefix(prefix(sequence(tag169(targets=targets))),source='169-gap')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==361 for r in row['completedRecords']))

    def test_tag65_target_scalar_and_unknown_tail(self):
        child=tag65();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='65.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertEqual(row['diagnostic'],dict(source='65.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=end,kind='union',tag=101),row['completedRecords'])
        self.assertIn(dict(start=38,end=118,kind='anonymous-target-profile'),row['completedRecords'])
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag65_nulls_extended_tag_and_every_limit(self):
        for child in (tag65(),tag65(b'\xff',b'\xff'),b'\x65\xff',b'\xfa\x65\x00'+tag65()[1:],
                      tag65(value=scalar_payload(None)),tag65(value=scalar_payload(b'long-variable-payload'))):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='65-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='65-limit',limit=n))

    def test_tag65_malformed_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tag65()));good=event_prefix(raw,source='65-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='65-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        row=event_prefix(prefix(sequence(tag65(t=target(selector=b'\x03\xfe'+bytes(8))))),source='65-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==101 for r in row['completedRecords']))
        # Another member-eight body cannot be selected from the header alone.
        with self.assertRaises(FrameError):sequence_frame(sequence(b'\x65'+tag58()[1:]))

    def test_taga2_four_targets_and_effect_boundaries(self):
        row=event_prefix(prefix(sequence(taga2(),b'\x59')),source='a2.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',731))
        self.assertEqual(row['diagnostic'],dict(source='a2.bin',offset=731,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=731,kind='union',tag=162),row['completedRecords'])
        self.assertEqual([(r['start'],r['end']) for r in row['completedRecords'] if r['kind']=='anonymous-target-profile'],[(41,121),(478,558),(559,639),(650,730)])
        self.assertIn(dict(start=121,end=478,kind='anonymous-effect-configuration-profile'),row['completedRecords'])
        self.assertEqual(row['opaqueRemainderRange'],[731,734]);self.assertFalse(row['wholeSchemaExact'])

    def test_taga2_nulls_extended_tag_truncations_and_limits(self):
        for child in (taga2(),taga2(None,b'',(b'\xff',)*4,b'\xff'),b'\xa2\xff',
                      b'\xfa\xa2\x00'+taga2()[1:],taga2(b'long-variable-payload',None)):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='a2-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='a2-limit',limit=n))

    def test_taga2_bad_headers_and_lengths(self):
        raw=prefix(sequence(taga2()));good=event_prefix(raw,source='a2-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='a2-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)

    def test_taga2_each_target_keeps_unknown_nested_boundary(self):
        for index in range(4):
            targets=[target()]*4;targets[index]=target(selector=b'\x03\xfe'+bytes(8))
            row=event_prefix(prefix(sequence(taga2(targets=targets))),source='a2-gap')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==162 for r in row['completedRecords']))
        # An unrelated action body cannot be selected by replacing its tag/header.
        wrong=b'\xa2\x12'+tag9a()[2:]
        with self.assertRaises(FrameError):sequence_frame(sequence(wrong))

    def test_calculation1_independent_scalars_and_all_cuts(self):
        scalars=(b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'\x00\xff'))
        values=[b'\xff',b'\x01\xff']
        values += [b'\x01\x02'+a+b for a in scalars for b in scalars]
        values += [b'\xfa\x01\x00'+v[1:] for v in values if v[0]==1]
        for value in values:
            r=Reader(value,'calc1',len(value));r.calculation_profile()
            self.assertEqual(r.pos,len(value))
            self.assertEqual(r.records[-1],dict(start=0,end=len(value),kind='anonymous-calculation-profile'))
            for cut in range(len(value)):
                results=[]
                for data in (value,value[:cut],value[:cut]+b'\xff'*20):
                    r=Reader(data,'calc1-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.calculation_profile()
                    self.assertLessEqual(r.pos,cut)
                    self.assertFalse(any(v['kind']=='anonymous-calculation-profile' for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])

    def test_calculation1_missing_second_and_malformed_payloads(self):
        for first in (b'\xff',scalar_payload(None),scalar_payload(b'k')):
            value=b'\x01\x02'+first;r=Reader(value,'calc1-second',len(value))
            with self.assertRaises(FrameError) as caught:r.calculation_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],len(value))
            self.assertFalse(any(v['kind']=='anonymous-calculation-profile' for v in r.records))
        for value,offset in ((b'\x01\x03',1),(b'\x01\x02\x04',2),(b'\x01\x02\xff\x04',3)):
            r=Reader(value,'calc1-header',len(value))
            with self.assertRaises(FrameError) as caught:r.calculation_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],offset)
        for prefix_value in (b'\x01\x02\x03',b'\x01\x02\xff\x03'):
            for count in (-2,2147483647):
                value=prefix_value+struct.pack('<i',count)+b'\xff'*8;r=Reader(value,'calc1-length',len(value))
                with self.assertRaises(FrameError) as caught:r.calculation_profile()
                self.assertEqual(caught.exception.diagnostic['offset'],len(prefix_value))
        for value in (b'\x04',b'\x06',b'\xfa\x01\x01'):
            r=Reader(value,'calc1-unknown',len(value))
            with self.assertRaises(Unsupported) as caught:r.calculation_profile()
            self.assertEqual((r.pos,caught.exception.diagnostic['offset']),(0,0))

    def test_calculation1_parent_tail_and_trailing_sequence(self):
        for calc in (b'\x01\xff',b'\x01\x02\xff\xff',b'\xfa\x01\x00\x02'+scalar_payload(b'left')+scalar_payload(b'right')):
            child=tag9a(struct.pack('<i',1)+damage33(calc,b'\xff'),b'\xff')
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for cut in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:cut])
            full=prefix(raw)
            for cut in range(len(full)):
                row=event_prefix(full,source='calc1-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='calc1-limit',limit=cut))
            for tail in (b'\xff',bytes(8)):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            row=event_prefix(prefix(sequence(child,b'\x59')),source='calc1-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],89)
            self.assertIn(dict(start=19,end=19+len(child),kind='union',tag=154),row['completedRecords'])

    def test_calculation5_variants_raw_bits_and_required_dword(self):
        values=[b'\xff',b'\x05\xff',b'\x05\x04\xff'+b'\xff'*4+b'\xff'+b'\xff'*4]
        for val in (None,b'',b'\x00\xff'):
            values.append(b'\x05\x04\xfe'+struct.pack('<I',0x80000000)+scalar_payload(val)+struct.pack('<I',0x7fc00000))
        values += [b'\xfa\x05\x00'+v[1:] for v in values if v[0]==5]
        for value in values:
            r=Reader(value,'calc5',len(value));r.calculation_profile()
            self.assertEqual(r.pos,len(value))
            self.assertEqual(r.records[-1],dict(start=0,end=len(value),kind='anonymous-calculation-profile'))
            for cut in range(len(value)):
                results=[]
                for data in (value,value[:cut],value[:cut]+b'\xff'*24):
                    r=Reader(data,'calc5-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.calculation_profile()
                    self.assertLessEqual(r.pos,cut)
                    self.assertFalse(any(v['kind']=='anonymous-calculation-profile' for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])

    def test_calculation5_bad_header_payload_and_unknown_union(self):
        for value in (b'\x04',b'\x06',b'\xfa\x05\x01'):
            r=Reader(value,'calc5-unknown',len(value))
            with self.assertRaises(Unsupported) as caught:r.calculation_profile()
            self.assertEqual((r.pos,caught.exception.diagnostic['offset']),(0,0))
        for value,offset in ((b'\x05\x03',1),(b'\x05\x04'+bytes(5)+b'\x04',7),
                             (b'\x05\x04'+bytes(5)+b'\x03'+struct.pack('<i',-2),8),
                             (b'\x05\x04'+bytes(5)+b'\x03'+struct.pack('<i',2147483647),8)):
            r=Reader(value,'calc5-bad',len(value))
            with self.assertRaises(FrameError) as caught:r.calculation_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],offset)
        # Same member count does not justify the tag3 scalar/DWORD/scalar/DWORD order.
        wrong=b'\x05\x04'+scalar_payload(b'x')+bytes(4)+scalar_payload(None)+bytes(4)
        r=Reader(wrong,'calc5-order',len(wrong))
        with self.assertRaises(FrameError):r.calculation_profile()

    def test_calculation5_parent_tail_and_trailing_sequence(self):
        for calc in (b'\x05\xff',b'\x05\x04'+bytes(5)+b'\xff'+bytes(4),
                     b'\xfa\x05\x00\x04\xff'+bytes(4)+scalar_payload(b'k')+b'\xff'*4):
            child=tag9a(struct.pack('<i',1)+damage33(calc,b'\xff'),b'\xff')
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for cut in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:cut])
            full=prefix(raw)
            for cut in range(len(full)):
                row=event_prefix(full,source='calc5-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='calc5-limit',limit=cut))
            for tail in (b'\xff',bytes(8)):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            row=event_prefix(prefix(sequence(child,b'\x59')),source='calc5-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],89)
            self.assertIn(dict(start=19,end=19+len(child),kind='union',tag=154),row['completedRecords'])

    def test_damage_processor_variants_and_modifier_reuse(self):
        modifier=b'\x04'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)+scalar_payload(b'wire')
        values=[b'\xff',b'\x00\xff',b'\x09\xff',b'\x00\x01\xff',b'\x09\x02\xff'+b'\xff'*4]
        for payload_value in (None,b'',b'\x00\xff'):
            values.append(b'\x00\x01'+scalar_payload(payload_value))
        values.append(b'\x09\x02'+modifier+bytes.fromhex('0000807f'))
        values += [b'\xfa'+bytes([v[0],0])+v[1:] for v in values if v[0]!=255]
        for value in values:
            r=Reader(value,'processor',len(value));r.damage_processor_profile()
            self.assertEqual(r.pos,len(value))
            self.assertEqual(r.records[-1]['kind'],'anonymous-damage-processor-profile')
        r=Reader(modifier,'modifier',len(modifier));r.modifier_element_profile()
        wrapped=b'\x02'+struct.pack('<i',1)+modifier+b'\xff'
        a=Reader(wrapped,'modifier',len(wrapped));a.modifier_collection_profile()
        child=next(v for v in a.records if v['kind']=='anonymous-modifier-element-profile')
        self.assertEqual((child['start'],child['end']),(5,5+r.pos))

    def test_damage_processor_lists_and_required_parent_tail(self):
        values=(b'\xff',b'\x00\x01'+scalar_payload(b'key'),b'\x09\x02\xff'+bytes(4))
        for items in (None,(),values):
            child=tag9a(struct.pack('<i',1)+damage33(b'\xff',b'\xff',items),b'\xff')
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='processor-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='processor-limit',limit=n))
            for tail in (b'\xff',b'\x00'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            unknown=event_prefix(prefix(sequence(child,b'\x59')),source='processor-tail')
            self.assertEqual(unknown['status'],'unsupported')
            self.assertEqual(unknown['diagnostic']['actual'],89)

    def test_damage_processor_unknown_header_and_truncation(self):
        values=(b'\x00\x01'+scalar_payload(b'key'),b'\x09\x02\x04'+bytes(12)+scalar_payload(None)+bytes(4),b'\xfa\x09\x00\xff')
        for value in values:
            for cut in range(len(value)):
                for raw in (value,value[:cut],value[:cut]+b'\xff'*16):
                    r=Reader(raw,'processor-cut',cut)
                    with self.assertRaises(FrameError):r.damage_processor_profile()
                    self.assertLessEqual(r.pos,cut)
                    self.assertFalse(any(v['kind']=='anonymous-damage-processor-profile' for v in r.records))
        for value in (b'\x01',b'\xfa\x00\x01'):
            r=Reader(value,'processor-unknown',len(value))
            with self.assertRaises(Unsupported) as caught:r.damage_processor_profile()
            self.assertEqual(r.pos,0);self.assertEqual(caught.exception.diagnostic['offset'],0)
        for value in (b'\x00\x02',b'\x09\x01',b'\x09\x02\x03',b'\x00\x01\x03'+struct.pack('<i',-2),b'\x00\x01\x03'+struct.pack('<i',2147483647)):
            r=Reader(value,'processor-bad',len(value))
            with self.assertRaises(FrameError):r.damage_processor_profile()

    def test_damage_processor_second_count_reserves_42_bytes(self):
        # Minimal unit: both calculation profiles, scalar, effect and sound null.
        head=b'\x21'+bytes(2)+b'\xff\xff'+bytes(1)+bytes(4)+bytes(12)
        tail=bytes(4)+bytes(4)+payload(None)+bytes(4)+b'\xff'+bytes(5)+b'\xff'+bytes(4)+bytes(6)+b'\xff'+bytes(1)+bytes(4)+bytes(3)
        self.assertEqual(len(tail),42)
        good=head+struct.pack('<i',1)+b'\xff'+tail
        r=Reader(good,'processor-count',len(good));r.damage_unit_profile();self.assertEqual(r.pos,len(good))
        for count in (-2,2,2147483647):
            bad=head+struct.pack('<i',count)+b'\xff'+tail
            r=Reader(bad,'processor-count',len(bad))
            with self.assertRaises(FrameError) as caught:r.damage_unit_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],len(head))
        r=Reader(good[:-1],'processor-count',len(good)-1)
        with self.assertRaises(FrameError) as caught:r.damage_unit_profile()
        self.assertEqual(caught.exception.diagnostic['offset'],len(head))
        bad=head+struct.pack('<i',1)+b'\x01'+tail
        r=Reader(bad,'processor-unknown',len(bad))
        with self.assertRaises(Unsupported):r.damage_unit_profile()
        self.assertEqual(r.pos,len(head)+4)
        self.assertFalse(any(v['kind']=='anonymous-damage-unit-profile' for v in r.records))

    def test_tag9a_nested_boundaries_and_unknown_tail(self):
        child=tag9a();row=event_prefix(prefix(sequence(child,b'\x59')),source='9a.bin')
        end=19+len(child)
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',end))
        self.assertEqual(row['diagnostic'],dict(source='9a.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=end,kind='union',tag=154),row['completedRecords'])
        self.assertEqual(sum(r['kind']=='anonymous-damage-unit-profile' for r in row['completedRecords']),1)
        self.assertEqual(sum(r['kind']=='anonymous-effect-configuration-profile' for r in row['completedRecords']),1)
        self.assertEqual(row['opaqueRemainderRange'],[end,end+3]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag9a_truncation_limits_null_and_extended_records(self):
        for child in (tag9a(),tag9a(struct.pack('<i',-1),b'\xff'),tag9a(bytes(4),b'\xff'),
                      tag9a(struct.pack('<i',2)+b'\xff'+damage33(b'\xff',b'\xff')),b'\x9a\xff',
                      b'\xfa\x9a\x00'+tag9a()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='9a-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='9a-limit',limit=n))

    def test_tag9a_bad_headers_and_count_bounds(self):
        raw=prefix(sequence(tag9a()));good=event_prefix(raw,source='9a-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='9a-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)

    def test_tag9a_calculation_variants_and_unclosed_lists(self):
        for calc in (b'\xff',b'\x00\x01'+scalar_payload(None),b'\x02\x03\xfe'+scalar_payload(b'k')*2,
                     b'\x03\x04'+scalar_payload(None)+bytes(4)+scalar_payload(None)+bytes(4),b'\xfa\x00\x00\xff'):
            child=tag9a(struct.pack('<i',1)+damage33(calc));raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
        row=event_prefix(prefix(sequence(tag9a(struct.pack('<i',1)+damage33(b'\x04')))),source='9a-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['actual'],4)
        raw=prefix(sequence(tag9a()));good=event_prefix(raw,source='9a-list')
        # The first/third unit lists and terrain-effect array have no positive
        # element profile; an otherwise bounded positive count must stay unsupported.
        payload_starts={r['start'] for r in good['completedRecords'] if r['kind']=='anonymous-byte-payload'}
        targets=[r for r in good['completedRecords'] if r['kind']=='anonymous-target-profile']
        for span in good['ranges']:
            if span['kind']!='count-i32' or span['start'] in payload_starts or raw[span['start']:span['end']]!=bytes(4):continue
            if any(r['start']<=span['start']<r['end'] for r in targets):continue
            # The second unit list is now independently framed.
            unit=next(r for r in good['completedRecords'] if r['kind']=='anonymous-damage-unit-profile')
            unit_counts=[r for r in good['ranges'] if r['kind']=='count-i32' and unit['start']<=r['start']<unit['end'] and r['start'] not in payload_starts]
            if span['start']==unit_counts[1]['start']:continue
            bad=bytearray(raw);struct.pack_into('<i',bad,span['start'],1)
            row=event_prefix(bad,source='9a-list')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['offset'],span['start'])

    def test_tag02_list_and_three_targets_have_distinct_boundaries(self):
        child=tag02();self.assertEqual(len(child),279)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='02.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',298))
        self.assertEqual(row['diagnostic'],dict(source='02.bin',offset=298,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=298,kind='union',tag=2),row['completedRecords'])
        self.assertEqual([(r['start'],r['end']) for r in row['completedRecords'] if r['kind']=='anonymous-target-profile'],[(45,125),(125,205),(216,296)])
        self.assertEqual(row['opaqueRemainderRange'],[298,301]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag02_null_lists_elements_and_hard_limits(self):
        for child in (tag02(),tag02(None,(b'\xff',)*3,b'\xff'),tag02((),(b'\xff',)*3),
                      tag02((b'\xff',b'\x01'+payload(None),b'\x01'+payload(b''))),
                      b'\x02\xff',b'\xfa\x02\x00\xff',b'\xfa\x02\x00'+tag02()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='02-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='02-limit',limit=n))

    def test_tag02_bad_headers_counts_and_raw_bits(self):
        raw=prefix(sequence(tag02()));good=event_prefix(raw,source='02-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='02-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        for flag in (0,1,128,254,255):
            raw=sequence(tag02(flag=flag));self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_tag02_list_count_and_each_target_are_required(self):
        child=tag02()
        with self.assertRaises(FrameError):sequence_frame(sequence(child[:15]+child[19:]))
        for index in range(3):
            targets=[target()]*3;targets[index]=target(selector=b'\x03\xfe'+bytes(8))
            row=event_prefix(prefix(sequence(tag02(targets=targets))),source='02-gap')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==2 for r in row['completedRecords']))

    def test_tag58_single_target_scalar_boundaries(self):
        child=tag58();self.assertEqual(len(child),116)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='58.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',135))
        self.assertEqual(row['diagnostic'],dict(source='58.bin',offset=135,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=135,kind='union',tag=88),row['completedRecords'])
        self.assertIn(dict(start=41,end=121,kind='anonymous-target-profile'),row['completedRecords'])
        self.assertIn(dict(start=125,end=135,kind='anonymous-scalar-payload'),row['completedRecords'])
        self.assertEqual(row['opaqueRemainderRange'],[135,138]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag58_nulls_truncation_limits_and_trailing(self):
        for child in (tag58(),tag58(b'\xff',b'\xff',b'\xff'),tag58(b'\x01'+payload(None)),
                      tag58(b'\x01'+payload(b''),value=scalar_payload(b'variable-key')),
                      b'\x58\xff',b'\xfa\x58\x00\xff',b'\xfa\x58\x00'+tag58()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='58-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='58-limit',limit=n))

    def test_tag58_bad_headers_lengths_and_raw_bits(self):
        raw=prefix(sequence(tag58()));good=event_prefix(raw,source='58-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='58-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        for flag in (0,1,128,254,255):
            raw=sequence(tag58(flag=flag));self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_tag58_single_value_is_not_list_or_raw_scalar(self):
        for single in (struct.pack('<i',1)+b'\x01'+payload(b'id'),bytes(4)):
            with self.assertRaises(FrameError):sequence_frame(sequence(tag58(single=single)))
        row=event_prefix(prefix(sequence(tag58(nested=target(selector=b'\x03\xfe'+bytes(8))))),source='58-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==88 for r in row['completedRecords']))
        raw=sequence(tag58(),tag56());self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
        with self.assertRaises(FrameError):sequence_frame(sequence(b'\x58'+tag56()[1:]))

    def test_tag81_ordered_payloads_and_target_boundary(self):
        child=tag81();self.assertEqual(len(child),110)
        row=event_prefix(prefix(sequence(child,b'\x82')),source='81.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',129))
        self.assertEqual(row['diagnostic'],dict(source='81.bin',offset=129,expected='supported current union tag',actual=130,category='union-tag'))
        self.assertIn(dict(start=19,end=129,kind='union',tag=129),row['completedRecords'])
        self.assertIn(dict(start=41,end=121,kind='anonymous-target-profile'),row['completedRecords'])
        self.assertIn(dict(start=34,end=41,kind='anonymous-byte-payload',isNull=False),row['completedRecords'])
        self.assertIn(dict(start=121,end=127,kind='anonymous-byte-payload',isNull=False),row['completedRecords'])
        self.assertEqual(row['opaqueRemainderRange'],[129,132]);self.assertFalse(row['wholeSchemaExact'])

    def test_tag81_truncation_limits_and_trailing_bytes(self):
        for child in (tag81(),tag81(None,None,b'\xff'),tag81(b'',b'',b'\xff'),b'\x81\xff',
                      b'\xfa\x81\x00\xff',b'\xfa\x81\x00'+tag81()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='81-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='81-limit',limit=n))

    def test_tag81_malformed_headers_and_payload_lengths(self):
        raw=prefix(sequence(tag81()));good=event_prefix(raw,source='81-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='81-bounds')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        for flag in (0,1,128,254,255):
            raw=sequence(tag81(flag=flag));self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_tag81_nested_gap_and_equal_header_dispatch(self):
        child=tag81(nested=target(selector=b'\x03\xfe'+bytes(8)))
        row=event_prefix(prefix(sequence(child)),source='81-gap')
        self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==129 for r in row['completedRecords']))
        # Both actions have nine members, but their type-selected wire orders differ.
        raw=sequence(tag81(),tag78());self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
        wrong=b'\x81'+tag78()[1:]
        with self.assertRaises(FrameError):sequence_frame(sequence(wrong))

    def test_tag68_target_boundary_and_later_unknown(self):
        child=tag68();self.assertEqual(len(child),95)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='68.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',114))
        self.assertEqual(row['diagnostic'],dict(source='68.bin',offset=114,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=114,kind='union',tag=104),row['completedRecords'])
        self.assertIn(dict(start=34,end=114,kind='anonymous-target-profile'),row['completedRecords'])
        self.assertEqual(row['opaqueRemainderRange'],[114,117])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag68_truncations_limits_trailing_and_nulls(self):
        for child in (tag68(),tag68(b'\xff'),b'\x68\xff',b'\xfa\x68\x00\xff',
                      b'\xfa\x68\x00'+tag68()[1:],tag68(target(selector=b'\xff',direction_value=b'\xff'))):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='68-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='68-limit',limit=n))

    def test_tag68_bad_headers_counts_and_scalar_bits(self):
        raw=prefix(sequence(tag68()));good=event_prefix(raw,source='68-bad')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='68-bad')
                self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at)
        for flag in (0,1,128,254,255):
            raw=sequence(tag68(flag=flag));self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_tag68_preserves_unknown_and_recursive_target_gaps(self):
        for nested in (target(selector=b'\x03\xfe'+bytes(8)),):
            row=event_prefix(prefix(sequence(tag68(nested))),source='68-gap')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==104 for r in row['completedRecords']))

    def test_tag78_scalar_list_boundaries_and_later_unknown(self):
        child=tag78();self.assertEqual(len(child),117)
        row=event_prefix(prefix(sequence(child,b'\x79')),source='78.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',136))
        self.assertEqual(row['diagnostic'],dict(source='78.bin',offset=136,expected='supported current union tag',actual=121,category='union-tag'))
        self.assertIn(dict(start=19,end=136,kind='union',tag=120),row['completedRecords'])
        self.assertIn(dict(start=40,end=120,kind='anonymous-target-profile'),row['completedRecords'])
        self.assertIn(dict(start=120,end=136,kind='anonymous-scalar32-list'),row['completedRecords'])
        self.assertEqual(child[105:117],struct.pack('<III',0,0xffffffff,0x80000000))
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag78_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag78())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='78-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='78-limit.bin',limit=n))

    def test_tag78_bad_count_and_header(self):
        for value in (-2,2147483647):
            bad=bytearray(tag78());struct.pack_into('<i',bad,101,value)
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='78-count.bin')
            self.assertEqual(caught.exception.diagnostic,dict(source='78-count.bin',offset=106,expected={'minimum':-1,'maximum':3},actual=value,category='count-bounds'))
        bad=bytearray(tag78());struct.pack_into('<i',bad,101,2)
        with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        for at,expected in ((1,9),(21,13)):
            bad=bytearray(tag78());bad[at]=0
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='78-header.bin')
            self.assertEqual(caught.exception.diagnostic,dict(source='78-header.bin',offset=at+5,expected=expected,actual=0,category='member-count'))

    def test_tag78_null_empty_and_extended_tag(self):
        for child in (b'\x78\xff',b'\xfa\x78\x00\xff',b'\xfa\x78\x00'+tag78()[1:],
                      tag78(items=None,nested=b'\xff'),tag78(items=(),nested=b'\xff')):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])

    def test_tag78_incomplete_recursive_target_fails_closed(self):
        bad_direction=bytearray(direction());bad_direction[8]=13
        child=tag78(nested=target(direction_value=bad_direction))
        row=event_prefix(prefix(sequence(child)),source='78-gap.bin')
        self.assertEqual(row['status'],'failed')
        self.assertEqual(row['diagnostic']['category'],'member-count')
        self.assertEqual(row['diagnostic']['actual'],0)
        self.assertFalse(any(r['kind']=='union' and r['tag']==120 for r in row['completedRecords']))

    def test_tag3c_nested_boundaries_and_later_unknown(self):
        child=tag3c();self.assertEqual(len(child),150)
        row=event_prefix(prefix(sequence(child,b'\x3d')),source='3c.bin')
        self.assertEqual((row['status'],row['consumedEnd']),('unsupported',169))
        self.assertEqual(row['diagnostic'],dict(source='3c.bin',offset=169,expected='supported current union tag',actual=61,category='union-tag'))
        for kind,a,b in (('union',19,169),('anonymous-finder-profile',34,70),
                         ('anonymous-query-profile',53,70),('anonymous-target-profile',74,154),
                         ('anonymous-scalar-payload',159,169)):
            expected=dict(start=a,end=b,kind=kind)
            if kind=='union':expected['tag']=60
            self.assertIn(expected,row['completedRecords'])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag3c_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag3c())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='3c-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='3c-limit.bin',limit=n))

    def test_tag3c_bad_nested_counts_and_headers(self):
        # Finder list, both payload lengths, query array, final scalar payload.
        for at in (16,20,26,39,141):
            for value in (-2,2147483647):
                bad=bytearray(tag3c());struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='3c-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('3c-count.bin',at+5,value,'count-bounds'))
        for at,expected in ((1,10),(15,3),(34,2),(55,13),(140,3)):
            bad=bytearray(tag3c());bad[at]=0
            with self.subTest(at=at),self.assertRaises(FrameError) as caught:
                sequence_frame(sequence(bad),source='3c-header.bin')
            self.assertEqual(caught.exception.diagnostic,dict(source='3c-header.bin',offset=at+5,expected=expected,actual=0,category='member-count'))

    def test_tag3c_null_and_extended_tag(self):
        for child in (b'\x3c\xff',b'\xfa\x3c\x00\xff',b'\xfa\x3c\x00'+tag3c()[1:],
                      tag3c(b'\xff',b'\xff',b'\xff')):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])

    def test_tag3c_retains_nested_unsupported_boundary(self):
        child=tag3c(nested=target(selector=b'\x03\xff'+struct.pack('<i',1)+b'\x00'+bytes(4)))
        row=event_prefix(prefix(sequence(child)),source='3c-gap.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertEqual(row['diagnostic']['actual'],0)
        self.assertFalse(any(r['kind']=='union' and r['tag']==60 for r in row['completedRecords']))

    def test_tag119_variable_payload_before_target_and_no_final_byte(self):
        for value in (None,b'',b'x',bytes(range(256))):
            child=tag119(value);end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='119.bin')
            self.assertEqual(row['diagnostic'],dict(source='119.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=281),row['completedRecords'])
            self.assertIn(dict(start=end-4,end=end,kind='anonymous-scalar32'),row['ranges'])
            self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag119_null_finder_cuts_limits_and_trailing(self):
        for child in (tag119(),tag119(None),tag119(b''),tag119(nested=b'\xff'),b'\xfa\x19\x01\xff',tag119(nested=target(selector=b'\x03'+finder3()+bytes(8)))):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='119-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='119-limit',limit=n))

    def test_tag119_bad_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tag119(nested=target(selector=b'\x03'+finder3(b'key')+bytes(8)))));good=event_prefix(raw,source='119-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='119-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('119-bounds',at,value))
        row=event_prefix(prefix(sequence(tag119(nested=target(selector=b'\x03\x06'+bytes(8))))),source='119-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==281 for r in row['completedRecords']))

    def test_finder3_raw_spans_payload_and_extended_null(self):
        for raw in (finder3(),finder3(b'abc'),b'\xfa\x03\x00'+finder3()[1:],b'\x03\xff'):
            r=Reader(raw,'finder3');r.selector_finder_profile();self.assertEqual(r.pos,len(raw))
            for n in range(len(raw)):
                r=Reader(raw,'finder3',n)
                with self.assertRaises(FrameError):r.selector_finder_profile()
                self.assertLessEqual(r.pos,n)
        r=Reader(finder3(),'finder3');r.selector_finder_profile()
        self.assertIn(dict(start=2,end=14,kind='anonymous-raw12'),r.ranges)
        self.assertIn(dict(start=14,end=30,kind='anonymous-raw16'),r.ranges)
        for header in (0,3,5):
            with self.assertRaises(FrameError) as caught:Reader(b'\x03'+bytes([header])+finder3()[2:],'finder3').selector_finder_profile()
            self.assertEqual(caught.exception.diagnostic,dict(source='finder3',offset=1,expected=4,actual=header,category='member-count'))
        row=event_prefix(prefix(sequence(b'\x19'+tag119()[3:])),source='119-physical')
        self.assertEqual((row['status'],row['consumedEnd'],row['diagnostic']['actual']),('unsupported',19,25))

    def test_tagc5_tag_list_instances_and_final_byte(self):
        for tags in (b'\xff',taglist(None),taglist(()),taglist(),taglist((b'\xff',b'\x01'+struct.pack('<I',0x80000000)))):
            child=tagc5(tags);end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='c5.bin')
            self.assertEqual(row['diagnostic'],dict(source='c5.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=197),row['completedRecords'])
            lists=[r for r in row['completedRecords'] if r['kind']=='anonymous-tag-list-profile']
            self.assertEqual(len(lists),1);self.assertEqual(lists[0]['end']-lists[0]['start'],len(tags))
            self.assertIn(dict(start=end-1,end=end,kind='anonymous-nonzero-byte'),row['ranges'])
            self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tagc5_null_extended_cuts_limits_and_trailing(self):
        for child in (tagc5(),tagc5(taglist(None),b'\xff',b'\xff',b'\xff',None),tagc5(taglist(()),value=b''),tagc5(nested=b'\xff'),b'\xc5\xff',b'\xfa\xc5\x00'+tagc5()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='c5-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='c5-limit',limit=n))

    def test_tagc5_bad_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tagc5()));good=event_prefix(raw,source='c5-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='c5-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('c5-bounds',at,value))
        row=event_prefix(prefix(sequence(tagc5(nested=target(selector=b'\x03\x06'+bytes(8))))),source='c5-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==197 for r in row['completedRecords']))

    def test_tagc5_unknown_calculation_and_tag_element_header(self):
        row=event_prefix(prefix(sequence(tagc5(calc=b'\x04'))),source='c5-calc')
        self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',4))
        self.assertFalse(any(r.get('tag')==197 for r in row['completedRecords']))
        child=tagc5(taglist((b'\x02'+bytes(4),)))
        row=event_prefix(prefix(sequence(child)),source='c5-element')
        self.assertEqual((row['status'],row['diagnostic']['expected'],row['diagnostic']['actual']),('failed',1,2))
        self.assertEqual(row['diagnostic']['source'],'c5-element')

    def test_tag27_independent_targets_and_paired_payloads(self):
        for first in (b'\xff',target()):
            for middle in (b'\xff',pair(None,b''),pair(b'\xff\x00',None),pair(b'first',b'last',255)):
                for last in (b'\xff',target()):
                    child=tag27(first,middle,last);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='27.bin')
                    self.assertEqual(row['diagnostic'],dict(source='27.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=39),row['completedRecords'])
                    self.assertIn(dict(start=34,end=34+len(first),kind='anonymous-target-profile'),row['completedRecords'])
                    self.assertIn(dict(start=36+len(first),end=end-1-len(last),kind='anonymous-paired-payload'),row['completedRecords'])
                    self.assertIn(dict(start=end-len(last),end=end,kind='anonymous-target-profile'),row['completedRecords'])

    def test_tag95_independent_lists_and_id_payload(self):
        assignment=b'\x06'+bytes(4)+payload(b'a')+bytes(4)+payload(None)+payload(b'b')+b'\xfe'
        for outer in (None,(),(b'\xff',),tuple(input95(items,identifier) for items in (None,(),(b'\xff',assignment,assignment)) for identifier in (b'\xff',b'\x01'+payload(None),b'\x01'+payload(b'ID')))):
            for scalar in (b'\xff',scalar_payload()):
                child=tag95(outer,scalar,target());end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='95.bin')
                self.assertEqual(row['diagnostic'],dict(source='95.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=149),row['completedRecords'])
                profiles=[r for r in row['completedRecords'] if r['kind']=='anonymous-global-input-profile']
                self.assertEqual(len(profiles),len(outer or ()))

    def test_tag74_counted_scalar_bits_and_completion(self):
        for items in (None,(),(0,),(0,0xffffffff,0x80000000,0x7fc00000)):
            child=tag74(items);end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='74.bin')
            self.assertEqual(row['diagnostic'],dict(source='74.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=116),row['completedRecords'])
            self.assertIn(dict(start=34,end=end,kind='anonymous-scalar32-list'),row['completedRecords'])
            spans=[r for r in row['ranges'] if r['kind']=='anonymous-scalar32' and r['start']>=38]
            self.assertEqual([(r['start'],r['end']) for r in spans],[(38+4*i,42+4*i) for i in range(len(items or ()))])

    def test_tag16d_independent_targets_and_raw_scalar(self):
        for first in (b'\xff',target()):
            for second in (b'\xff',target()):
                for bits in (0,0xffffffff,0x80000000,0x7fc00000):
                    child=tag16d(first,second,bits);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='16d.bin')
                    self.assertEqual(row['diagnostic'],dict(source='16d.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=365),row['completedRecords'])
                    self.assertIn(dict(start=41,end=41+len(first),kind='anonymous-target-profile'),row['completedRecords'])
                    self.assertIn(dict(start=41+len(first),end=end,kind='anonymous-target-profile'),row['completedRecords'])

    def test_tag160_separate_scalars_and_final_target(self):
        for nested in (b'\xff',target()):
            for first in (0,0xffffffff,0x80000000,0x7fc00000):
                for second in (0,0xffffffff):
                    child=tag160(nested,first,second);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='160.bin')
                    self.assertEqual(row['diagnostic'],dict(source='160.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=352),row['completedRecords'])
                    self.assertIn(dict(start=47,end=end,kind='anonymous-target-profile'),row['completedRecords'])
                    for at in (38,43):self.assertIn(dict(start=at,end=at+4,kind='anonymous-scalar32'),row['ranges'])

    def test_tag89_independent_payload_lengths_and_null_states(self):
        for first in (None,b'',b'\xff\x00',b'first'):
            for second in (None,b'',b'last\x89\x06'):
                child=tag89(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='89.bin')
                self.assertEqual(row['diagnostic'],dict(source='89.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=137),row['completedRecords'])
                counts=[r['start'] for r in row['ranges'] if r['kind']=='count-i32' and r['start']>=34]
                self.assertEqual(counts,[34,38+len(first or b'')])

    def test_tag51_two_independent_paired_profiles(self):
        for first in (b'\xff',pair(None,b''),pair(b'first',b'\xff',255)):
            for second in (b'\xff',pair(b'',None),pair(b'last',b'\x51\x06',128)):
                child=tag51(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='51.bin')
                self.assertEqual(row['diagnostic'],dict(source='51.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=81),row['completedRecords'])
                profiles=[v for v in row['completedRecords'] if v['kind']=='anonymous-paired-payload']
                self.assertEqual([(v['start'],v['end']) for v in profiles],[(34,34+len(first)),(34+len(first),end)])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag51_every_cut_hard_limits_null_extended_and_trailing(self):
        base=tag51(pair(None,b'wire'),pair(b'last',None))
        for child in (base,tag51(),b'\x51\xff',b'\xfa\x51\x00'+base[1:]):
            r=Reader(child,'51-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'51-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n)
                    self.assertFalse(any(v.get('tag')==81 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag51_bad_independent_lengths_headers_and_second_profile(self):
        first=pair(b'a',b'b');child=tag51(first,pair(b'c',b'd'))
        r=Reader(child,'51-bounds');r.action(0)
        counts=[v['start'] for v in r.ranges if v['kind']=='count-i32']
        headers=[v['start'] for v in r.ranges if v['kind']=='member-header']
        self.assertEqual(len(counts),4);self.assertEqual(len(headers),3)
        for at in counts:
            for value in (-2,0x7fffffff):
                bad=bytearray(child);struct.pack_into('<i',bad,at,value);r=Reader(bad,'51-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('51-bounds',at,value))
        for at in headers:
            bad=bytearray(child);bad[at]=0;r=Reader(bad,'51-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],at)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        r=Reader(child,'51-second',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertIn(dict(start=15,end=15+len(first),kind='anonymous-paired-payload'),r.records)
        self.assertFalse(any(v.get('tag')==81 for v in r.records))

    def test_tag03_independent_list_elements_and_required_byte(self):
        for items in (None,(),(b'\xff',),(b'\x01'+payload(None),b'\x01'+payload(b''),b'\x01'+payload(b'\xff\x03'))):
            for scalar in (b'\xff',scalar_payload(b'wire')):
                child=tag03(items,scalar);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='03.bin')
                self.assertEqual(row['diagnostic'],dict(source='03.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=3),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag03_every_cut_hard_limit_null_extended_and_trailing(self):
        base=tag03((b'\x01'+payload(b'wire'),b'\xff'),scalar_payload(None))
        for child in (base,tag03(None),b'\x03\xff',b'\xfa\x03\x00'+base[1:]):
            r=Reader(child,'03-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'03-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n)
                    self.assertFalse(any(v.get('tag')==3 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag03_bad_counts_headers_and_missing_final_byte(self):
        child=tag03((b'\x01'+payload(b'a'),b'\x01'+payload(b'b')),scalar_payload(b'wire'))
        r=Reader(child,'03-bounds');r.action(0)
        counts=[v['start'] for v in r.ranges if v['kind']=='count-i32']
        self.assertEqual(len(counts),4)
        headers=[v['start'] for v in r.ranges if v['kind']=='member-header']
        self.assertEqual(len(headers),4)
        for at in counts:
            for value in (-2,0x7fffffff):
                bad=bytearray(child);struct.pack_into('<i',bad,at,value);r=Reader(bad,'03-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('03-bounds',at,value))
        for at in headers:
            bad=bytearray(child);bad[at]=0;r=Reader(bad,'03-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],at)
        for last in (0,128,254,255):
            data=tag03(last=last);r=Reader(data,'03-tail');r.action(0);self.assertEqual(r.pos,len(data))
            r=Reader(data[:-1],'03-tail')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'truncated')
            self.assertFalse(any(v.get('tag')==3 for v in r.records))

    def test_tag142_independent_payloads_target_and_final_scalar(self):
        for nested in (b'\xff',target()):
            for values in ((None,)*5,(b'',)*5,(b'a',None,b'',b'\xfa\x42\x01',b'last')):
                child=tag142(values,nested);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='142.bin')
                self.assertEqual(row['diagnostic'],dict(source='142.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=322),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag142_cuts_hard_limits_nulls_and_trailing(self):
        for child in (tag142(),tag142(nested=target()),b'\xfa\x42\x01\xff'):
            r=Reader(child,'142-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'142-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n)
                    self.assertFalse(any(v.get('tag')==322 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag142_malformed_lengths_headers_and_unknown_target(self):
        child=tag142((b'',)*5);r=Reader(child,'142-bounds');r.action(0)
        counts=[v['start'] for v in r.ranges if v['kind']=='count-i32']
        self.assertEqual(len(counts),5)
        for at in counts:
            for value in (-2,0x7fffffff):
                bad=bytearray(child);struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'142-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('142-bounds',at,value))
        for value in (0,5,10,12,254):
            bad=bytearray(child);bad[3]=value;r=Reader(bad,'142-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        gap=tag142(nested=target(selector=b'\x03\x17'))
        r=Reader(gap,'142-gap')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'nested-profile')
        self.assertFalse(any(v.get('tag')==322 for v in r.records))
        self.assertLess(r.pos,len(gap)-sum(len(payload(v)) for v in (b'',b'wire',b'\xff\x00',b'last'))-4)

    def test_tag176_direct_list_and_ordered_option_profiles(self):
        for scalar in (b'\xff',scalar_payload(None),scalar_payload(b'wire')):
            for nested in (b'\xff',sequence(),b'\x03'+struct.pack('<i',-1)+b'\xfe\xff',sequence(tag16d())):
                for items in (None,(),(b'\xff',),(option176(nested,scalar),b'\xff',option176())):
                    child=tag176(items,scalar);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='176.bin')
                    self.assertEqual(row['diagnostic'],dict(source='176.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=374),row['completedRecords'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        child=tag176((option176(sequence(tag16d()),scalar_payload(b'wire')),b'\xff'))
        r=Reader(child,'176-order');r.action(0)
        # Fixed fixture: count follows the one-byte null outer scalar at 19;
        # child member2 starts at 23, sequence at 24, scalar at 55, FF at 69.
        self.assertIn(dict(start=23,end=69,kind='anonymous-sequence-scalar-profile'),r.records)
        self.assertIn(dict(start=69,end=70,kind='anonymous-sequence-scalar-profile'),r.records)
        self.assertIn(dict(start=19,end=70,kind='anonymous-sequence-scalar-list'),r.records)

    def test_tag176_every_cut_hard_limit_null_wrapper_and_trailing(self):
        full=tag176((option176(sequence(tag16d()),scalar_payload(b'wire')),b'\xff'),scalar_payload(None))
        for child in (full,tag176(),b'\xfa\x76\x01\xff'):
            r=Reader(child,'176-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'176-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==374 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag176_bad_headers_counts_and_incomplete_option(self):
        child=tag176((option176(sequence(tag16d()),scalar_payload(b'wire')),b'\xff'))
        # Independent fixed wire offsets: outer, option, sequence, child,
        # scalar headers; direct option count, sequence count, scalar length.
        for at,values in ((3,(0,254)),(23,(0,254)),(24,(0,254)),(32,(0,254)),(55,(0,254)),
                          (19,(-2,0x7fffffff)),(25,(-2,0x7fffffff)),(56,(-2,0x7fffffff))):
            for value in values:
                bad=bytearray(child)
                if at in (19,25,56):struct.pack_into('<i',bad,at,value)
                else:bad[at]=value
                r=Reader(bad,'176-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('176-bounds',at,value))
        r=Reader(child,'176-incomplete',68)
        with self.assertRaises(FrameError):r.action(0)
        self.assertIn(dict(start=24,end=55,kind='sequence'),r.records)
        self.assertFalse(any(v['kind']=='anonymous-sequence-scalar-profile' or v.get('tag')==374 for v in r.records))
        gap=tag176((option176(sequence(b'\x59')),))
        r=Reader(gap,'176-gap')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']), (29,89))
        self.assertFalse(any(v.get('tag')==374 for v in r.records))

    def test_tag176_recursive_options_share_sequence_depth_limit(self):
        child=tag176()
        for _ in range(66):child=tag176((option176(sequence(child)),))
        with self.assertRaises(Unsupported) as caught:sequence_frame(sequence(child),source='176-depth')
        self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['category']),('176-depth','depth-limit'))

    def test_tag98_curve_scalar_and_payloads_have_independent_boundaries(self):
        for curve in (b'\xff',curve24(None),curve24(),curve24((b'\xff'*28,b'\x80'*28))):
            for scalar in (b'\xff',b'\x03'+payload(None)+b'\xfe'+b'\xff'*4):
                for first,last in ((None,b''),(b'wire',None),(b'\xff',b'\x00\xff')):
                    child=tag98(first,curve,scalar,last);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='98.bin')
                    self.assertEqual(row['diagnostic'],dict(source='98.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=152),row['completedRecords'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag98_every_cut_hard_limit_extended_null_wrapper_and_trailing(self):
        full=tag98(b'wire',curve24((b'\xff'*28,)),b'\x03'+payload(b'\xff')+b'\xfe'+b'\x80'*4)
        for child in (full,tag98(),b'\x98\xff',b'\xfa\x98\x00'+full[1:]):
            r=Reader(child,'98-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'98-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==152 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag98_bad_headers_counts_and_tail_failure_preserves_profiles(self):
        child=tag98(b'wire',curve24((b'\xff'*28,)),b'\x03'+payload(None)+b'\xff'+b'\x80'*4)
        r=Reader(child,'98-bounds');r.action(0)
        for span in [v for v in r.ranges if v['kind'] in ('member-header','count-i32')]:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'98-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('98-bounds',at,value))
        r=Reader(child,'98-tail');r.action(0);completed=[v for v in r.records if v.get('tag')!=152]
        r=Reader(child,'98-tail',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertTrue(completed);self.assertEqual(r.records,completed)

    def test_tag140_payload_two_independent_targets_exact_end(self):
        for value in (None,b'',b'wire',b'\xff\x00'):
            for first in (b'\xff',target()):
                for second in (b'\xff',target()):
                    child=tag140(value,first,second);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='140.bin')
                    self.assertEqual(row['diagnostic'],dict(source='140.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=320),row['completedRecords'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag140_every_cut_hard_limit_null_wrapper_and_trailing(self):
        full=tag140(b'wire',target(),target())
        for child in (full,tag140(),b'\xfa\x40\x01\xff'):
            r=Reader(child,'140-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'140-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==320 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag140_bad_headers_counts_and_second_target_failure(self):
        child=tag140(b'wire',target(),target());r=Reader(child,'140-bounds');r.action(0)
        for span in [v for v in r.ranges if v['kind'] in ('member-header','count-i32')]:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'140-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('140-bounds',at,value))
        first_end=len(child)-len(target())
        r=Reader(child,'140-first',first_end)
        with self.assertRaises(FrameError):r.action(0)
        completed=list(r.records);self.assertTrue(completed)
        r=Reader(child,'140-second',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertEqual(r.records[:len(completed)],completed)
        self.assertFalse(any(v.get('tag')==320 for v in r.records))

    def test_tag13f_payload_target_final_dword_exact_end(self):
        for value in (None,b'',b'wire',b'\xff\x00'):
            for nested in (b'\xff',target()):
                for bits in (0,0xffffffff,0x80000000):
                    child=tag13f(value,nested,bits);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='13f.bin')
                    self.assertEqual(row['diagnostic'],dict(source='13f.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=319),row['completedRecords'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag13f_every_cut_hard_limit_null_wrapper_and_trailing(self):
        full=tag13f(b'wire',target())
        for child in (full,tag13f(),b'\xfa\x3f\x01\xff'):
            r=Reader(child,'13f-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'13f-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==319 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag13f_bad_headers_counts_and_final_dword_failure(self):
        child=tag13f(b'wire',target());r=Reader(child,'13f-bounds');r.action(0)
        for span in [v for v in r.ranges if v['kind'] in ('member-header','count-i32')]:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'13f-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('13f-bounds',at,value))
        r=Reader(child,'13f-tail');r.action(0);completed=list(r.records)
        r=Reader(child,'13f-tail',len(child)-1)
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['offset'],len(child)-4)
        self.assertEqual(r.records,[v for v in completed if v.get('tag')!=319])
        self.assertFalse(any(v.get('tag')==319 for v in r.records))

    def test_tag151_sequence_two_scalars_and_byte_have_independent_boundaries(self):
        scalar=b'\x03'+payload(b'wire')+b'\xff'+b'\x80'*4
        for nested in (b'\xff',sequence(),b'\x03'+payload(None)+b'\xff\xfe',sequence(tag2b())):
            for first in (b'\xff',scalar):
                for last in (b'\xff',scalar):
                    child=tag151(nested,first,last);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='151.bin')
                    self.assertEqual(row['diagnostic'],dict(source='151.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=337),row['completedRecords'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        r=Reader(tag151(sequence(b'\x59')),'151-unknown')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['offset']),('union-tag',22))
        self.assertFalse(any(v.get('tag')==337 for v in r.records))

    def test_tag151_every_cut_null_wrapper_trailing_and_depth(self):
        scalar=b'\x03'+payload(None)+b'\xff'+b'\x80'*4
        full=tag151(sequence(tag2b()),scalar,scalar)
        for child in (full,tag151(),b'\xfa\x51\x01\xff'):
            r=Reader(child,'151-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'151-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==337 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        child=tag151()
        for _ in range(66):child=tag151(sequence(child))
        with self.assertRaises(Unsupported) as caught:sequence_frame(sequence(child))
        self.assertEqual(caught.exception.diagnostic['category'],'depth-limit')

    def test_tag151_bad_headers_counts_and_later_scalar_failure(self):
        scalar=b'\x03'+payload(b'wire')+b'\xff'+b'\x80'*4
        child=tag151(sequence(tag2b()),scalar,scalar)
        r=Reader(child,'151-bounds');r.action(0)
        for span in [v for v in r.ranges if v['kind'] in ('member-header','count-i32')]:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'151-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('151-bounds',at,value))
        r=Reader(child,'151-tail',len(child)-3)
        with self.assertRaises(FrameError):r.action(0)
        self.assertTrue(any(v.get('tag')==43 for v in r.records))
        self.assertTrue(any(v['kind']=='sequence' for v in r.records))
        self.assertFalse(any(v.get('tag')==337 for v in r.records))

    def test_tag115_sequence_and_outer_tail_have_independent_boundaries(self):
        for nested in (b'\xff',sequence(),b'\x03'+payload(None)+b'\xff\xfe',sequence(tag2b())):
            for first,last in ((None,b''),(b'wire',None),(b'\xff',b'\x00\xff')):
                child=tag115(nested,first,last);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='115.bin')
                self.assertEqual(row['diagnostic'],dict(source='115.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=277),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        child=tag115(sequence(b'\x59'));r=Reader(child,'115-unknown')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['offset']),('union-tag',44))
        self.assertFalse(any(v.get('tag')==277 for v in r.records))

    def test_tag115_every_cut_null_wrapper_trailing_and_depth(self):
        full=tag115(sequence(tag2b()),b'wire',b'\xff\x00')
        for child in (full,tag115(),b'\xfa\x15\x01\xff'):
            r=Reader(child,'115-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'115-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==277 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        child=tag115()
        for _ in range(66):child=tag115(sequence(child))
        with self.assertRaises(Unsupported) as caught:sequence_frame(sequence(child))
        self.assertEqual(caught.exception.diagnostic['category'],'depth-limit')

    def test_tag115_malformed_headers_counts_and_completed_child_on_tail_failure(self):
        child=tag115(sequence(tag2b()),b'wire',b'\xff\x00')
        r=Reader(child,'115-bounds');r.action(0)
        spans=[v for v in r.ranges if v['kind'] in ('member-header','count-i32')]
        for span in spans:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'115-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('115-bounds',at,value))
        r=Reader(child,'115-tail',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertTrue(any(v.get('tag')==43 for v in r.records))
        self.assertTrue(any(v['kind']=='sequence' for v in r.records))
        self.assertFalse(any(v.get('tag')==277 for v in r.records))

    def test_tag2b_scalar_profile_exact_end_before_unknown_union(self):
        for value in (None,b'',b'wire',b'\xff\x00'):
            for nested in (b'\xff',b'\x03'+payload(value)+b'\xff'+b'\x80'*4):
                child=tag2b(nested);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='2b.bin')
                self.assertEqual(row['diagnostic'],dict(source='2b.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=43),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag2b_every_cut_hard_limit_null_extended_and_trailing(self):
        full=tag2b(b'\x03'+payload(b'wire')+b'\xff'+b'\x80'*4)
        for child in (full,tag2b(),b'\x2b\xff',b'\xfa\x2b\x00'+full[1:]):
            r=Reader(child,'2b-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'2b-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==43 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag2b_invalid_headers_lengths_and_incomplete_scalar(self):
        child=tag2b(b'\x03'+payload(b'wire')+b'\xff'+b'\x80'*4)
        for at in (1,15):
            for value in (0,254):
                bad=bytearray(child);bad[at]=value;r=Reader(bad,'2b-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('2b-header',at,value))
        for value in (-2,0x7fffffff):
            bad=bytearray(child);struct.pack_into('<i',bad,16,value);r=Reader(bad,'2b-length')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('2b-length',16,value))
        r=Reader(child,'2b-incomplete',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertFalse(any(v.get('tag')==43 for v in r.records))
        self.assertLessEqual(r.pos,len(child)-1)

    def test_tag0b_direct_list_null_empty_elements_and_final_byte(self):
        for items in (None,(),(b'\xff',),(b'\x01'+b'\xff'*4,b'\xff',b'\x01'+b'\x80'*4)):
            for first in (b'\xff',pair(None,b'wire',255)):
                for second in (b'\xff',target()):
                    child=tag0b(items,first,second);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='0b.bin')
                    self.assertEqual(row['diagnostic'],dict(source='0b.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=11),row['completedRecords'])
                    self.assertEqual(sum(r['kind']=='anonymous-tag-element' for r in row['completedRecords']),len(items or ()))
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag0b_every_cut_hard_limit_null_extended_trailing(self):
        full=tag0b((b'\x01'+b'\xff'*4,b'\xff'),pair(None,b'wire',255),target())
        for child in (full,tag0b(),b'\x0b\xff',b'\xfa\x0b\x00'+full[1:]):
            r=Reader(child,'0b-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'0b-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==11 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag0b_bad_counts_headers_reserve_and_partial_elements(self):
        child=tag0b((b'\x01'+b'\xff'*4,b'\xff'),pair(None,b'wire',255),target())
        r=Reader(child,'0b-bounds');r.action(0)
        spans=[v for v in r.ranges if v['kind'] in ('member-header','count-i32')]
        self.assertGreater(len(spans),10)
        for span in spans:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'0b-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('0b-bounds',at,value))
        # One byte remaining cannot hold both a null element and required tail.
        bad=tag0b((b'\xff',))[:-1];r=Reader(bad,'0b-reserve')
        with self.assertRaises(FrameError) as caught:r.action(0)
        self.assertEqual((caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),(17,1))
        self.assertFalse(any(v['kind']=='anonymous-tag-element' for v in r.records))
        bad=tag0b((b'\x01'+bytes(4),b'\x01'+bytes(4)))
        r=Reader(bad,'0b-element',len(bad)-3)
        with self.assertRaises(FrameError):r.action(0)
        self.assertEqual(sum(v['kind']=='anonymous-tag-element' for v in r.records),1)
        self.assertFalse(any(v.get('tag')==11 for v in r.records))

    def test_tagbb_two_independent_targets_end_before_next_union(self):
        for first in (b'\xff',target()):
            for second in (b'\xff',target(direction_value=b'\xff')):
                child=tagbb(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='bb.bin')
                self.assertEqual(row['diagnostic'],dict(source='bb.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=187),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tagbb_every_cut_hard_limit_null_extended_trailing(self):
        full=tagbb(target(),target())
        for child in (full,tagbb(),b'\xbb\xff',b'\xfa\xbb\x00'+full[1:]):
            r=Reader(child,'bb-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'bb-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==187 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tagbb_bad_headers_counts_and_partial_second_target(self):
        child=tagbb(target(),target());r=Reader(child,'bb-bounds');r.action(0)
        spans=[v for v in r.ranges if v['kind'] in ('member-header','count-i32')]
        self.assertGreater(len(spans),15)
        for span in spans:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'bb-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('bb-bounds',at,value))
        first=target();gap=tagbb(first,target(selector=b'\x03\x59'));r=Reader(gap,'bb-gap')
        with self.assertRaises(Unsupported):r.action(0)
        self.assertIn(dict(start=15,end=15+len(first),kind='anonymous-target-profile'),r.records)
        self.assertFalse(any(v.get('tag')==187 for v in r.records))

    def test_tag90_independent_int_profiles_and_final_target(self):
        for first in (b'\xff',scalar_payload(None),scalar_payload(b'')):
            for second in (b'\xff',scalar_payload(b'wire',bits=b'\xff'*4)):
                for last in (b'\xff',target()):
                    child=tag90(first,second,last);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='90.bin')
                    self.assertEqual(row['diagnostic'],dict(source='90.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=144),row['completedRecords'])
                    self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag90_every_cut_hard_limit_null_extended_trailing(self):
        full=tag90(scalar_payload(b'first'),scalar_payload(b'second'),target())
        for child in (full,tag90(),b'\x90\xff',b'\xfa\x90\x00'+full[1:]):
            r=Reader(child,'90-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'90-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==144 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag90_bad_headers_lengths_and_unknown_target(self):
        child=tag90(scalar_payload(b'first'),scalar_payload(b'second'),target())
        r=Reader(child,'90-bounds');r.action(0)
        spans=[v for v in r.ranges if v['kind'] in ('member-header','count-i32')]
        self.assertGreater(len(spans),10)
        for span in spans:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'90-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('90-bounds',at,value))
        first=scalar_payload(b'first');second=scalar_payload(b'second')
        gap=tag90(first,second,target(selector=b'\x03\x59'));r=Reader(gap,'90-gap')
        with self.assertRaises(Unsupported):r.action(0)
        self.assertEqual(sum(v.get('kind')=='anonymous-scalar-payload' for v in r.records),2)
        self.assertFalse(any(v.get('tag')==144 for v in r.records))

    def test_tag13c_common_members_end_before_next_union(self):
        for fields in (bytes(13),b'\xff'*13,b'\x80'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)):
            for tag in (b'\xfa\x3c\x01',):
                child=tag+b'\x04'+fields;end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='13c.bin')
                self.assertEqual(row['diagnostic'],dict(source='13c.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=316),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag13c_every_cut_null_extended_bad_header_and_trailing(self):
        for tag in (b'\xfa\x3c\x01',):
            for child in (tag+b'\x04'+b'\xff'*13,tag+b'\xff'):
                r=Reader(child,'13c-cut');r.action(0);self.assertEqual(r.pos,len(child))
                for n in range(len(child)):
                    results=[]
                    for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                        r=Reader(data,'13c-cut',n)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==316 for v in r.records))
                        results.append((caught.exception.diagnostic,r.pos,r.ranges))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            for header in (0,3,5,254):
                r=Reader(tag+bytes([header])+bytes(13),'13c-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic,dict(source='13c-header',offset=len(tag),expected=4,actual=header,category='member-count'))

    def test_tag62_common_members_end_before_next_union(self):
        for fields in (bytes(13),b'\xff'*13,b'\x80'+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)):
            for tag in (b'\x62',b'\xfa\x62\x00'):
                child=tag+b'\x04'+fields;end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='62.bin')
                self.assertEqual(row['diagnostic'],dict(source='62.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=98),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag62_every_cut_null_extended_bad_header_and_trailing(self):
        for tag in (b'\x62',b'\xfa\x62\x00'):
            for child in (tag+b'\x04'+b'\xff'*13,tag+b'\xff'):
                r=Reader(child,'62-cut');r.action(0);self.assertEqual(r.pos,len(child))
                for n in range(len(child)):
                    results=[]
                    for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                        r=Reader(data,'62-cut',n)
                        with self.assertRaises(FrameError) as caught:r.action(0)
                        self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==98 for v in r.records))
                        results.append((caught.exception.diagnostic,r.pos,r.ranges))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            for header in (0,3,5,254):
                r=Reader(tag+bytes([header])+bytes(13),'62-header')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual(caught.exception.diagnostic,dict(source='62-header',offset=len(tag),expected=4,actual=header,category='member-count'))

    def test_taga9_independent_nested_fields_and_final_profile(self):
        profiles=[target(),target(direction_value=b'\xff'),curve24((b'\xff'*28,)),direction(),
                  scalar_flag(None),scalar_payload(None),scalar_payload(b''),scalar_payload(b'wire'),scalar_payload(b'last')]
        cases=[profiles,(b'\xff',)*9]
        for n in range(9):
            case=list(profiles);case[n]=b'\xff';cases.append(case)
        for case in cases:
            child=taga9(case);end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='a9.bin')
            self.assertEqual(row['diagnostic'],dict(source='a9.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=169),row['completedRecords'])
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_taga9_every_cut_hard_limit_extended_null_and_trailing(self):
        full=taga9([target(),target(),curve24((bytes(28),)),direction(),scalar_flag(b'\xff'),
                    scalar_payload(None),scalar_payload(b''),scalar_payload(b'\xff'),scalar_payload(b'last')])
        for child in (full,taga9(),b'\xa9\xff',b'\xfa\xa9\x00'+full[1:]):
            r=Reader(child,'a9-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'a9-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v.get('tag')==169 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_taga9_bad_headers_counts_and_partial_parent(self):
        child=taga9([target(),target(),curve24((bytes(28),)),direction(),scalar_flag(b'impact'),
                     scalar_payload(None),scalar_payload(b''),scalar_payload(b'wire'),scalar_payload(b'last')])
        r=Reader(child,'a9-bounds');r.action(0)
        spans=[v for v in r.ranges if v['kind'] in ('member-header','count-i32')]
        self.assertGreater(len(spans),20)
        for span in spans:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'a9-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('a9-bounds',at,value))
        r=Reader(child,'a9-tail',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertEqual(sum(v.get('kind')=='anonymous-scalar-payload' for v in r.records),3)
        self.assertFalse(any(v.get('tag')==169 for v in r.records))

    def test_tag41_payload_and_independent_query_boundaries(self):
        for value in (None,b'',b'\xff\x41\x06'):
            for query in (b'\xff',query41(None),query41(),query41((0,0xffffffff,0x80000000))):
                child=tag41(value,query);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='41.bin')
                self.assertEqual(row['diagnostic'],dict(source='41.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=65),row['completedRecords'])
                self.assertIn(dict(start=end-len(query),end=end,kind='anonymous-query-profile'),row['completedRecords'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag41_every_cut_hard_limit_null_extended_and_trailing(self):
        base=tag41(None,query41((1,0xffffffff)))
        for child in (base,tag41(),b'\x41\xff',b'\xfa\x41\x00'+base[1:]):
            r=Reader(child,'41-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'41-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n)
                    self.assertFalse(any(v.get('tag')==65 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag41_bad_lengths_headers_and_incomplete_query(self):
        child=tag41(b'a',query41((1,2)));r=Reader(child,'41-bounds');r.action(0)
        spans=[v for v in r.ranges if v['kind'] in ('member-header','count-i32')]
        self.assertEqual(len(spans),4)
        for span in spans:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'41-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('41-bounds',at,value))
        r=Reader(child,'41-query',len(child)-1)
        with self.assertRaises(FrameError):r.action(0)
        self.assertIn(dict(start=15,end=20,kind='anonymous-byte-payload',isNull=False),r.records)
        self.assertFalse(any(v.get('tag')==65 for v in r.records))

    def test_tag174_independent_profiles_and_final_byte(self):
        for first in (b'\xff',scalar_payload(None)):
            for second in (b'\xff',scalar_payload(b'first')):
                for third in (b'\xff',scalar_payload(b'last')):
                    for nested in (b'\xff',target()):
                        child=tag174(first,second,None,third,nested);end=19+len(child)
                        row=event_prefix(prefix(sequence(child,b'\x59')),source='174.bin')
                        self.assertEqual(row['diagnostic'],dict(source='174.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                        self.assertIn(dict(start=19,end=end,kind='union',tag=372),row['completedRecords'])
                        self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag174_every_cut_hard_limit_null_and_trailing(self):
        base=tag174(scalar_payload(b'a'),scalar_payload(None),b'',scalar_payload(b'c'),target())
        for child in (base,tag174(),b'\xfa\x74\x01\xff'):
            r=Reader(child,'174-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'174-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n)
                    self.assertFalse(any(v.get('tag')==372 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag174_bad_counts_headers_unknown_target_and_missing_byte(self):
        child=tag174(scalar_payload(b'a'),scalar_payload(b'b'),b'v',scalar_payload(b'c'),target())
        r=Reader(child,'174-bounds');r.action(0)
        spans=[v for v in r.ranges if v['kind'] in ('member-header','count-i32')]
        for span in spans:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'174-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('174-bounds',at,value))
        gap=tag174(nested=target(selector=b'\x03\x17'));r=Reader(gap,'174-gap')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'nested-profile')
        self.assertLess(r.pos,len(gap)-1)
        self.assertFalse(any(v.get('tag')==372 for v in r.records))
        for last in (0,128,254,255):
            data=tag174(nested=target(),last=last);r=Reader(data,'174-tail');r.action(0)
            self.assertEqual(r.pos,len(data));r=Reader(data,'174-tail',len(data)-1)
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(data)-1)
            self.assertFalse(any(v.get('tag')==372 for v in r.records))

    def test_tag84_target_and_final_scalar_boundary(self):
        for nested in (b'\xff',target(),target(selector=b'\xff',direction_value=b'\xff')):
            for bits in (0,0xffffffff,0x80000000,0x7fc00000):
                child=tag84(nested,bits);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='84.bin')
                self.assertEqual(row['diagnostic'],dict(source='84.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=132),row['completedRecords'])
                self.assertIn(dict(start=end-4,end=end,kind='anonymous-scalar32'),row['ranges'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag84_every_cut_hard_limit_null_extended_and_trailing(self):
        base=tag84(target())
        for child in (base,tag84(),b'\x84\xff',b'\xfa\x84\x00'+base[1:]):
            r=Reader(child,'84-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'84-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n)
                    self.assertFalse(any(v.get('tag')==132 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag84_bad_counts_headers_unknown_target_and_scalar(self):
        child=tag84(target());r=Reader(child,'84-bounds');r.action(0)
        spans=[v for v in r.ranges if v['kind'] in ('member-header','count-i32')]
        for span in spans:
            for value in ((0,254) if span['kind']=='member-header' else (-2,0x7fffffff)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                r=Reader(bad,'84-bounds')
                with self.assertRaises(FrameError) as caught:r.action(0)
                self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('84-bounds',at,value))
        gap=tag84(target(selector=b'\x03\x17'));r=Reader(gap,'84-gap')
        with self.assertRaises(Unsupported) as caught:r.action(0)
        self.assertEqual(caught.exception.diagnostic['category'],'nested-profile')
        self.assertLess(r.pos,len(gap)-4)
        self.assertFalse(any(v.get('tag')==132 for v in r.records))
        for n in range(len(child)-4,len(child)):
            r=Reader(child,'84-tail',n)
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-4)
            self.assertTrue(any(v['start']==15 and v['end']==len(child)-4 for v in r.records))
            self.assertFalse(any(v.get('tag')==132 for v in r.records))

    def test_tag13b_payload_and_required_scalar_boundary(self):
        for value in (None,b'',b'\xff\xfa\x3b\x01'):
            for bits in (0,0xffffffff,0x80000000,0x7fc00000):
                child=tag13b(value,bits);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='13b.bin')
                self.assertEqual(row['diagnostic'],dict(source='13b.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=315),row['completedRecords'])
                self.assertIn(dict(start=end-4,end=end,kind='anonymous-scalar32'),row['ranges'])
                self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))

    def test_tag13b_every_cut_hard_limit_null_and_trailing(self):
        for child in (tag13b(),tag13b(None),b'\xfa\x3b\x01\xff'):
            r=Reader(child,'13b-cut');r.action(0);self.assertEqual(r.pos,len(child))
            for n in range(len(child)):
                results=[]
                for data in (child,child[:n],child[:n]+b'\xff'*(len(child)-n)):
                    r=Reader(data,'13b-cut',n)
                    with self.assertRaises(FrameError) as caught:r.action(0)
                    self.assertLessEqual(r.pos,n)
                    self.assertFalse(any(v.get('tag')==315 for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag13b_bad_length_header_and_incomplete_final_scalar(self):
        child=tag13b()
        for value in (-2,0x7fffffff):
            bad=bytearray(child);struct.pack_into('<i',bad,17,value);r=Reader(bad,'13b-length')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
            self.assertEqual((caught.exception.diagnostic['source'],caught.exception.diagnostic['offset'],caught.exception.diagnostic['actual']),('13b-length',17,value))
        for value in (0,5,7,254):
            bad=bytearray(child);bad[3]=value;r=Reader(bad,'13b-header')
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
            self.assertEqual(caught.exception.diagnostic['offset'],3)
        for n in range(len(child)-4,len(child)):
            r=Reader(child,'13b-tail',n)
            with self.assertRaises(FrameError) as caught:r.action(0)
            self.assertEqual(caught.exception.diagnostic['offset'],len(child)-4)
            self.assertIn(dict(start=17,end=len(child)-4,kind='anonymous-byte-payload',isNull=False),r.records)
            self.assertFalse(any(v.get('tag')==315 for v in r.records))

    def test_tag5e_final_scalar_raw_bits_and_unknown_successor(self):
        for value in (0,0xffffffff,0x80000000,0x7fc00000):
            child=tag5e(value);end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='5e.bin')
            self.assertEqual(row['diagnostic'],dict(source='5e.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=94),row['completedRecords'])
            self.assertIn(dict(start=end-4,end=end,kind='anonymous-scalar32'),row['ranges'])

    def test_tag5e_null_extended_cuts_and_trailing(self):
        for child in (tag5e(),b'\x5e\xff',b'\xfa\x5e\x00'+tag5e()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='5e-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='5e-limit',limit=n))

    def test_tag5e_malformed_headers_counts_and_required_scalar(self):
        raw=prefix(sequence(tag5e()));good=event_prefix(raw,source='5e-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='5e-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('5e-bounds',at,value))
                self.assertFalse(any(r.get('tag')==94 for r in row['completedRecords']))
        for limit in range(34,38):
            row=event_prefix(raw,source='5e-tail',limit=limit)
            self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],34)
            self.assertFalse(any(r.get('tag')==94 for r in row['completedRecords']))

    def test_tag06_final_scalar_raw_bits_and_unknown_successor(self):
        for value in (0,0xffffffff,0x80000000,0x7fc00000):
            child=tag06(value);end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='06.bin')
            self.assertEqual(row['diagnostic'],dict(source='06.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=6),row['completedRecords'])
            self.assertIn(dict(start=end-4,end=end,kind='anonymous-scalar32'),row['ranges'])

    def test_tag06_null_extended_cuts_and_trailing(self):
        for child in (tag06(),b'\x06\xff',b'\xfa\x06\x00'+tag06()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='06-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='06-limit',limit=n))

    def test_tag06_malformed_headers_counts_and_required_scalar(self):
        raw=prefix(sequence(tag06()));good=event_prefix(raw,source='06-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='06-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('06-bounds',at,value))
                self.assertFalse(any(r.get('tag')==6 for r in row['completedRecords']))
        for limit in range(34,38):
            row=event_prefix(raw,source='06-tail',limit=limit)
            self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],34)
            self.assertFalse(any(r.get('tag')==6 for r in row['completedRecords']))

    def test_tag1c_independent_nested_profiles_and_final_scalar(self):
        for child in (b'\xff',scalar_flag(None),scalar_flag(b''),scalar_flag()):
            for mask in range(16):
                scalars=tuple(scalar_payload(bytes([i])) if mask&(1<<i) else b'\xff' for i in range(4))
                action=tag1c(target(),child,scalars,second=target());end=19+len(action)
                row=event_prefix(prefix(sequence(action,b'\x59')),source='1c.bin')
                self.assertEqual(row['diagnostic'],dict(source='1c.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=28),row['completedRecords'])
                at=34+len(target())
                self.assertIn(dict(start=at,end=at+len(child),kind='anonymous-scalar-flag-payload'),row['completedRecords'])
                self.assertIn(dict(start=end-len(scalars[-1]),end=end,kind='anonymous-scalar-payload'),row['completedRecords'])

    def test_tag1c_null_extended_cuts_and_trailing(self):
        direction=b'\x08\xfe\xff'+b'\x80'*4+b'\xfe'+(b'\xff'+b'\x80'*4)*2
        for child in (tag1c(),tag1c(target(),scalar_flag(),(scalar_payload(),)*4,direction,target()),b'\x1c\xff',b'\xfa\x1c\x00'+tag1c()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='1c-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='1c-limit',limit=n))

    def test_tag1c_malformed_profiles_and_unknown_targets(self):
        raw=prefix(sequence(tag1c(target(),scalar_flag(),(scalar_payload(),)*4,second=target())))
        good=event_prefix(raw,source='1c-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='1c-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('1c-bounds',at,value))
                self.assertFalse(any(r.get('tag')==28 for r in row['completedRecords']))
        unknown=target(selector=b'\x03\x17')
        for first,second in ((unknown,target()),(target(),unknown)):
            row=event_prefix(prefix(sequence(tag1c(first,second=second))),source='1c-gap')
            self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
            self.assertFalse(any(r.get('tag')==28 for r in row['completedRecords']))

    def test_scalar_flag_payload_requires_own_final_byte(self):
        child=scalar_flag();raw=prefix(sequence(tag1c(child=child)));at=35
        row=event_prefix(raw,source='1c-child-tail',limit=at+len(child)-1)
        self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],at+len(child)-1)
        self.assertFalse(any(r.get('tag')==28 or r['kind']=='anonymous-scalar-flag-payload' for r in row['completedRecords']))
        for value in (None,b'',b'wire'):
            data=scalar_flag(value)
            for n in range(len(data)):
                r=Reader(data,'child',n)
                with self.assertRaises(FrameError):r.scalar_flag_payload()
                self.assertFalse(any(rec['kind']=='anonymous-scalar-flag-payload' for rec in r.records))

    def test_tag126_final_target_boundary(self):
        for nested in (b'\xff',target()):
            child=tag126(nested);end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='126.bin')
            self.assertEqual(row['diagnostic'],dict(source='126.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=294),row['completedRecords'])
            self.assertIn(dict(start=36,end=end,kind='anonymous-target-profile'),row['completedRecords'])

    def test_tag126_null_extended_cuts_limits_and_trailing(self):
        for child in (tag126(),tag126(target()),b'\xfa\x26\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='126-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='126-limit',limit=n))

    def test_tag126_malformed_counts_headers_and_target_gap(self):
        raw=prefix(sequence(tag126(target())))
        good=event_prefix(raw,source='126-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='126-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('126-bounds',at,value))
                self.assertFalse(any(r.get('tag')==294 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(tag126(target(selector=b'\x03\x17')))),source='126-gap')
        self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
        self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
        self.assertFalse(any(r.get('tag')==294 for r in row['completedRecords']))

    def test_tag60_raw_scalar_and_final_target(self):
        for nested in (b'\xff',target()):
            for value in (0,0xffffffff,0x80000000,0x7fc00000):
                child=tag60(nested,value);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='60.bin')
                self.assertEqual(row['diagnostic'],dict(source='60.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=96),row['completedRecords'])
                self.assertIn(dict(start=34,end=38,kind='anonymous-scalar32'),row['ranges'])
                self.assertIn(dict(start=38,end=end,kind='anonymous-target-profile'),row['completedRecords'])

    def test_tag60_null_extended_cuts_limits_and_trailing(self):
        for child in (tag60(),tag60(target()),b'\x60\xff',b'\xfa\x60\x00'+tag60()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='60-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='60-limit',limit=n))

    def test_tag60_malformed_counts_headers_and_target_gap(self):
        raw=prefix(sequence(tag60(target())))
        good=event_prefix(raw,source='60-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='60-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('60-bounds',at,value))
                self.assertFalse(any(r.get('tag')==96 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(tag60(target(selector=b'\x03\x17')))),source='60-gap')
        self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
        self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
        self.assertFalse(any(r.get('tag')==96 for r in row['completedRecords']))

    def test_tagd4_independent_targets_and_raw_tail(self):
        for first in (b'\xff',target()):
            for second in (b'\xff',target()):
                for bits in (0,0xffffffff,0x80000000,0x7fc00000):
                    child=tagd4(first,second,bits,bits);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='d4.bin')
                    self.assertEqual(row['diagnostic'],dict(source='d4.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=212),row['completedRecords'])
                    self.assertIn(dict(start=34,end=34+len(first),kind='anonymous-target-profile'),row['completedRecords'])
                    self.assertIn(dict(start=34+len(first),end=end-8,kind='anonymous-target-profile'),row['completedRecords'])
                    for at in (end-8,end-4):self.assertIn(dict(start=at,end=at+4,kind='anonymous-scalar32'),row['ranges'])

    def test_tagd4_null_extended_cuts_limits_and_trailing(self):
        for child in (tagd4(),tagd4(target(),target()),b'\xd4\xff',b'\xfa\xd4\x00'+tagd4()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='d4-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='d4-limit',limit=n))

    def test_tagd4_malformed_children_and_required_tail(self):
        child=tagd4(target(),target());raw=prefix(sequence(child));end=19+len(child)
        good=event_prefix(raw,source='d4-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='d4-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('d4-bounds',at,value))
                self.assertFalse(any(r.get('tag')==212 for r in row['completedRecords']))
        for limit in range(end-8,end):
            row=event_prefix(raw,source='d4-tail',limit=limit)
            self.assertEqual(row['status'],'failed')
            self.assertIn(dict(start=34+len(target()),end=end-8,kind='anonymous-target-profile'),row['completedRecords'])
            self.assertFalse(any(r.get('tag')==212 for r in row['completedRecords']))
        unknown=target(selector=b'\x03\x17')
        for first,second in ((unknown,target()),(target(),unknown)):
            child=tagd4(first,second);row=event_prefix(prefix(sequence(child)),source='d4-gap')
            self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
            self.assertLess(row['consumedEnd'],19+len(child)-8)
            self.assertFalse(any(r.get('tag')==212 for r in row['completedRecords']))
            if first!=unknown:self.assertIn(dict(start=34,end=34+len(first),kind='anonymous-target-profile'),row['completedRecords'])

    def test_tag132_independent_payload_lengths_and_null_states(self):
        for first in (None,b'',b'\xff\x00',b'first'):
            for second in (None,b'',b'last\x89\x06'):
                child=tag132(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='132.bin')
                self.assertEqual(row['diagnostic'],dict(source='132.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=306),row['completedRecords'])
                counts=[r['start'] for r in row['ranges'] if r['kind']=='count-i32' and r['start']>=36]
                self.assertEqual(counts,[36,40+len(first or b'')])

    def test_tag132_null_extended_cuts_limits_and_trailing(self):
        for child in (tag132(),tag132(None,None),tag132(b'first',b'last'),b'\xfa\x32\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='132-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='132-limit',limit=n))

    def test_tag132_malformed_headers_lengths_and_incomplete_second(self):
        raw=prefix(sequence(tag132(b'first',b'last')))
        good=event_prefix(raw,source='132-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='132-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('132-bounds',at,value))
                self.assertFalse(any(r.get('tag')==306 for r in row['completedRecords']))
        row=event_prefix(raw,source='132-second',limit=45)
        self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],45)
        self.assertFalse(any(r.get('tag')==306 for r in row['completedRecords']))
        self.assertEqual(row['ranges'],[r for r in good['ranges'] if r['end']<=45])

    def test_tag171_independent_scalar_profiles_and_final_byte(self):
        for first in (b'\xff',scalar_payload(b'a')):
            for second in (b'\xff',scalar_payload(None)):
                for third in (b'\xff',scalar_payload(b'c')):
                    for value in (None,b'',b'raw'):
                        child=tag171(first,second,value,third,target(),128);end=19+len(child)
                        row=event_prefix(prefix(sequence(child,b'\x59')),source='171.bin')
                        self.assertEqual(row['diagnostic'],dict(source='171.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                        self.assertIn(dict(start=19,end=end,kind='union',tag=369),row['completedRecords'])
                        for at,size in ((40,len(first)),(40+len(first),len(second)),(40+len(first)+len(second)+len(payload(value)),len(third))):
                            self.assertIn(dict(start=at,end=at+size,kind='anonymous-scalar-payload'),row['completedRecords'])
                        self.assertIn(dict(start=end-1,end=end,kind='anonymous-nonzero-byte'),row['ranges'])

    def test_tag171_null_cuts_limits_and_trailing(self):
        for child in (tag171(),tag171(scalar_payload(),scalar_payload(None),b'raw',scalar_payload(b'c'),target()),b'\xfa\x71\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='171-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='171-limit',limit=n))

    def test_tag171_malformed_counts_headers_and_unconsumed_tail(self):
        raw=prefix(sequence(tag171(scalar_payload(),scalar_payload(None),b'raw',scalar_payload(b'c'),target())))
        good=event_prefix(raw,source='171-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='171-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('171-bounds',at,value))
                self.assertFalse(any(r.get('tag')==369 for r in row['completedRecords']))
        child=tag171(nested=target(selector=b'\x03\x17'))
        row=event_prefix(prefix(sequence(child)),source='171-gap')
        self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
        self.assertLess(row['consumedEnd'],19+len(child)-1)
        self.assertFalse(any(r.get('tag')==369 for r in row['completedRecords']))
        child=tag171(nested=target());full=prefix(sequence(child));end=19+len(child)
        row=event_prefix(full,source='171-final-byte',limit=end-1)
        self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],end-1)
        self.assertTrue(any(r['kind']=='anonymous-target-profile' for r in row['completedRecords']))
        self.assertFalse(any(r.get('tag')==369 for r in row['completedRecords']))

    def test_tag89_null_extended_cuts_limits_and_trailing(self):
        for child in (tag89(),tag89(None,None),tag89(b'first',b'last'),b'\x89\xff',b'\xfa\x89\x00'+tag89()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='89-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='89-limit',limit=n))

    def test_tag89_malformed_headers_lengths_and_incomplete_second(self):
        raw=prefix(sequence(tag89(b'first',b'last')))
        good=event_prefix(raw,source='89-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='89-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('89-bounds',at,value))
                self.assertFalse(any(r.get('tag')==137 for r in row['completedRecords']))
        row=event_prefix(raw,source='89-second',limit=43)
        self.assertEqual(row['status'],'failed');self.assertEqual(row['diagnostic']['offset'],43)
        self.assertFalse(any(r.get('tag')==137 for r in row['completedRecords']))
        self.assertEqual(row['ranges'],[r for r in good['ranges'] if r['end']<=43])

    def test_tag160_null_cuts_limits_and_trailing(self):
        for child in (tag160(),tag160(target()),b'\xfa\x60\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='160-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='160-limit',limit=n))

    def test_tag160_malformed_counts_headers_and_target_gap(self):
        raw=prefix(sequence(tag160(target())))
        good=event_prefix(raw,source='160-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='160-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('160-bounds',at,value))
                self.assertFalse(any(r.get('tag')==352 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(tag160(target(selector=b'\x03\x17')))),source='160-gap')
        self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
        self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
        self.assertFalse(any(r.get('tag')==352 for r in row['completedRecords']))

    def test_tag16d_null_cuts_limits_and_trailing(self):
        for child in (tag16d(),tag16d(target(),target()),b'\xfa\x6d\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='16d-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='16d-limit',limit=n))

    def test_tag16d_malformed_counts_headers_and_independent_gaps(self):
        raw=prefix(sequence(tag16d(target(),target())))
        good=event_prefix(raw,source='16d-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='16d-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('16d-bounds',at,value))
                self.assertFalse(any(r.get('tag')==365 for r in row['completedRecords']))
        unknown=target(selector=b'\x03\x17')
        for first,second in ((unknown,target()),(target(),unknown)):
            row=event_prefix(prefix(sequence(tag16d(first,second))),source='16d-gap')
            self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
            self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
            self.assertFalse(any(r.get('tag')==365 for r in row['completedRecords']))
            profiles=[r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile']
            self.assertEqual(profiles,[] if first==unknown else [dict(start=41,end=41+len(first),kind='anonymous-target-profile')])

    def test_tag74_null_extended_cuts_limits_and_trailing(self):
        for child in (tag74(),tag74(None),tag74((0,0xffffffff,0x80000000)),b'\x74\xff',b'\xfa\x74\x00'+tag74((1,))[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='74-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='74-limit',limit=n))

    def test_tag74_malformed_counts_headers_and_incomplete_parent(self):
        raw=prefix(sequence(tag74((0,0xffffffff))))
        good=event_prefix(raw,source='74-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='74-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('74-bounds',at,value))
                self.assertFalse(any(r.get('tag')==116 for r in row['completedRecords']))
        row=event_prefix(raw,source='74-short-element',limit=45)
        self.assertEqual(row['status'],'failed')
        self.assertEqual(row['diagnostic']['offset'],34)
        self.assertFalse(any(r['kind']=='anonymous-scalar32-list' for r in row['completedRecords']))

    def test_tag95_null_extended_cuts_limits_and_trailing(self):
        for child in (tag95(),tag95((input95((b'\xff',),b'\x01'+payload(b'ID')),),scalar_payload(),target()),b'\x95\xff',b'\xfa\x95\x00'+tag95()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='95-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='95-limit',limit=n))

    def test_tag95_malformed_counts_headers_and_target_gap(self):
        assignment=b'\x06'+bytes(4)+payload(b'a')+bytes(4)+payload(None)+payload(b'b')+b'\xfe'
        items=(input95((assignment,),b'\x01'+payload(b'ID')),)
        raw=prefix(sequence(tag95(items,scalar_payload(),target())))
        good=event_prefix(raw,source='95-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='95-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('95-bounds',at,value))
                self.assertFalse(any(r.get('tag')==149 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(tag95(items,last=target(selector=b'\x03\x17')))),source='95-gap')
        self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
        self.assertEqual(len([r for r in row['completedRecords'] if r['kind']=='anonymous-global-input-list']),1)
        self.assertFalse(any(r.get('tag')==149 for r in row['completedRecords']))

    def test_tag27_null_extended_cuts_limits_and_trailing(self):
        for child in (tag27(),tag27(target(),pair(b'first',b'last'),target()),b'\x27\xff',b'\xfa\x27\x00'+tag27()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='27-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='27-limit',limit=n))

    def test_tag27_malformed_counts_headers_and_target_gaps(self):
        raw=prefix(sequence(tag27(target(),pair(b'first',b'last'),target())))
        good=event_prefix(raw,source='27-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='27-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('27-bounds',at,value))
        bad_target=target(selector=b'\x03\x17');middle=pair(b'first',None)
        for first,last in ((bad_target,target()),(target(),bad_target)):
            row=event_prefix(prefix(sequence(tag27(first,middle,last))),source='27-gap')
            self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
            self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
            self.assertFalse(any(r.get('tag')==39 for r in row['completedRecords']))
            paired=[r for r in row['completedRecords'] if r['kind']=='anonymous-paired-payload']
            self.assertEqual(paired,[] if first==bad_target else [dict(start=36+len(first),end=36+len(first)+len(middle),kind='anonymous-paired-payload')])

    def test_tag42_independent_targets_and_scalar_bits(self):
        for first in (b'\xff',target(),target(direction_value=b'\xff')):
            for second in (b'\xff',target()):
                for bits in (0,0x80000000,0x7fc00000,0xffffffff):
                    child=tag42(first,second,bits);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='42.bin')
                    self.assertEqual(row['diagnostic'],dict(source='42.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=66),row['completedRecords'])
                    self.assertIn(dict(start=41,end=41+len(first),kind='anonymous-target-profile'),row['completedRecords'])
                    self.assertIn(dict(start=41+len(first),end=end,kind='anonymous-target-profile'),row['completedRecords'])

    def test_tag42_null_extended_cuts_limits_and_trailing(self):
        for child in (tag42(),tag42(target(),target()),b'\x42\xff',b'\xfa\x42\x00'+tag42()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='42-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='42-limit',limit=n))

    def test_tag42_malformed_counts_headers_and_target_gaps(self):
        raw=prefix(sequence(tag42(target(),target())))
        good=event_prefix(raw,source='42-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='42-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('42-bounds',at,value))
        bad_target=target(selector=b'\x03\x17')
        for first,second in ((bad_target,target()),(target(),bad_target)):
            row=event_prefix(prefix(sequence(tag42(first,second))),source='42-gap')
            self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
            self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
            self.assertFalse(any(r.get('tag')==66 for r in row['completedRecords']))
            completed=[r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile']
            self.assertEqual(completed,[] if first==bad_target else [dict(start=41,end=41+len(first),kind='anonymous-target-profile')])

    def test_tag5d_final_scalar_boundary_and_raw_bits(self):
        for bits in (0,1,0x80000000,0xffffffff,0x7fc00000):
            child=b'\x5d\x05\xfe'+bytes(12)+struct.pack('<I',bits)
            for encoded in (child,b'\xfa\x5d\x00'+child[1:],b'\x5d\xff'):
                end=19+len(encoded)
                row=event_prefix(prefix(sequence(encoded,b'\x59')),source='5d.bin')
                self.assertEqual(row['diagnostic'],dict(source='5d.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertEqual(row['completedRecords'],[dict(start=19,end=end,kind='union',tag=93)])
            reader=Reader(child,'5d-final',len(child)-1)
            with self.assertRaises(FrameError) as caught:reader.action(0)
            self.assertEqual(caught.exception.diagnostic,dict(source='5d-final',offset=15,expected={'bytes':4},actual={'remaining':3},category='truncated'))
            self.assertEqual(reader.records,[])

    def test_tag5d_null_extended_cuts_limits_and_trailing(self):
        for child in (b'\x5d\x05'+b'\xff'*17,b'\xfa\x5d\x00\x05'+bytes(17),b'\x5d\xff',b'\xfa\x5d\x00\xff'):
            raw=sequence(child,child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='5d-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='5d-limit',limit=n))

    def test_tag5d_malformed_headers_and_enclosing_counts(self):
        raw=prefix(sequence(b'\x5d\x05'+bytes(17)))
        good=event_prefix(raw,source='5d-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='5d-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('5d-bounds',at,value))
                self.assertFalse(any(r.get('tag')==93 for r in row['completedRecords']))

    def test_tag73_fixed_end_and_independent_adjacent_records(self):
        for flag in (0,1,128,254,255):
            child=b'\x73\x04'+bytes([flag])+struct.pack('<III',0xffffffff,0x80000000,0x7fc00000)
            for encoded in (child,b'\xfa\x73\x00'+child[1:],b'\x73\xff'):
                end=19+len(encoded)
                row=event_prefix(prefix(sequence(encoded,b'\x59')),source='73.bin')
                self.assertEqual(row['diagnostic'],dict(source='73.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertEqual(row['completedRecords'],[dict(start=19,end=end,kind='union',tag=115)])
                raw=sequence(encoded,encoded)
                reader=Reader(raw,'73-pair');reader.sequence()
                self.assertEqual(reader.pos,len(raw))
                self.assertEqual([r for r in reader.records if r['kind']=='union'],[
                    dict(start=5,end=5+len(encoded),kind='union',tag=115),
                    dict(start=5+len(encoded),end=5+2*len(encoded),kind='union',tag=115)])

    def test_tag73_null_extended_cuts_limits_and_trailing(self):
        for child in (b'\x73\x04'+b'\xff'*13,b'\xfa\x73\x00\x04'+bytes(13),b'\x73\xff',b'\xfa\x73\x00\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='73-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='73-limit',limit=n))

    def test_tag73_malformed_headers_and_enclosing_counts(self):
        raw=prefix(sequence(b'\x73\x04'+bytes(13)))
        good=event_prefix(raw,source='73-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='73-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('73-bounds',at,value))
                self.assertFalse(any(r.get('tag')==115 for r in row['completedRecords']))

    def test_tag14d_three_independent_nested_boundaries(self):
        for first in (b'\xff',finder14d(),finder14d(None,None),finder14d((),())):
            for second in (b'\xff',target()):
                for last in (b'\xff',scalar_payload(None),scalar_payload(b'wire',bits=b'\xff'*4)):
                    child=tag14d(first,second,last);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='14d.bin')
                    self.assertEqual(row['diagnostic'],dict(source='14d.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=333),row['completedRecords'])
                    self.assertIn(dict(start=36,end=36+len(first),kind='anonymous-finder-profile'),row['completedRecords'])
                    self.assertIn(dict(start=41+len(first),end=end-len(last),kind='anonymous-target-profile'),row['completedRecords'])
                    self.assertIn(dict(start=end-len(last),end=end,kind='anonymous-scalar-payload'),row['completedRecords'])

    def test_tag14d_null_extended_cuts_limits_and_trailing(self):
        for child in (tag14d(),tag14d(finder14d(),target(),scalar_payload(b'wire')),b'\xfa\x4d\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='14d-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='14d-limit',limit=n))

    def test_tag14d_malformed_nested_counts_headers_and_target_gap(self):
        raw=prefix(sequence(tag14d(finder14d(),target(),scalar_payload(b'wire'))))
        good=event_prefix(raw,source='14d-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='14d-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('14d-bounds',at,value))
        child=tag14d(finder14d(),target(selector=b'\x03\x17'),scalar_payload())
        row=event_prefix(prefix(sequence(child)),source='14d-gap')
        self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
        self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
        self.assertIn(dict(start=36,end=36+len(finder14d()),kind='anonymous-finder-profile'),row['completedRecords'])
        self.assertFalse(any(r.get('tag')==333 or r['kind']=='anonymous-scalar-payload' for r in row['completedRecords']))

    def test_tag3f_independent_nested_and_final_payloads(self):
        for nested in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'\x00\xff',bits=b'\xff'*4)):
            for value in (None,b'',b'\x00\xffwire'):
                child=tag3f(nested,value);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='3f.bin')
                self.assertEqual(row['diagnostic'],dict(source='3f.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=63),row['completedRecords'])
                self.assertIn(dict(start=38,end=38+len(nested),kind='anonymous-scalar-payload'),row['completedRecords'])
                self.assertIn(dict(start=38+len(nested),end=end,kind='anonymous-byte-payload',isNull=value is None),row['completedRecords'])

    def test_tag3f_null_extended_cuts_limits_and_trailing(self):
        for child in (tag3f(),tag3f(scalar_payload(b'raw')),b'\x3f\xff',b'\xfa\x3f\x00'+tag3f()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='3f-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='3f-limit',limit=n))

    def test_tag3f_malformed_independent_counts_and_headers(self):
        raw=prefix(sequence(tag3f(scalar_payload(b'raw'))))
        # Explicit source positions: nested payload count 39, final count 51.
        for at in (39,51):
            for value in (-2,2147483647):
                bad=bytearray(raw);struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='3f-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual'],row['diagnostic']['category']),('3f-bounds',at,value,'count-bounds'))
                self.assertFalse(any(r.get('tag')==63 for r in row['completedRecords']))
        for at in (20,38):
            for value in (0,254):
                bad=bytearray(raw);bad[at]=value
                row=event_prefix(bad,source='3f-header');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['offset'],row['diagnostic']['actual'],row['diagnostic']['category']),(at,value,'member-count'))
                self.assertFalse(any(r.get('tag')==63 for r in row['completedRecords']))

    def test_tag61_target_and_final_payload_boundaries(self):
        for nested in (b'\xff',target(),target(direction_value=b'\xff')):
            for value in (None,b'',b'\x00\xffwire'):
                child=tag61(nested,value);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='61.bin')
                self.assertEqual(row['diagnostic'],dict(source='61.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=97),row['completedRecords'])
                self.assertIn(dict(start=34,end=34+len(nested),kind='anonymous-target-profile'),row['completedRecords'])
                self.assertIn(dict(start=44+len(nested),end=end,kind='anonymous-byte-payload',isNull=value is None),row['completedRecords'])

    def test_tag61_null_extended_cuts_limits_and_trailing(self):
        for child in (tag61(),tag61(target()),b'\x61\xff',b'\xfa\x61\x00'+tag61()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='61-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='61-limit',limit=n))

    def test_tag61_malformed_counts_headers_and_target_gap(self):
        raw=prefix(sequence(tag61(target())))
        good=event_prefix(raw,source='61-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='61-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('61-bounds',at,value))
        child=tag61(target(selector=b'\x03\x17'))
        row=event_prefix(prefix(sequence(child)),source='61-gap')
        self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
        self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
        self.assertFalse(any(r.get('tag')==97 or r['kind']=='anonymous-target-profile' for r in row['completedRecords']))

    def test_tagea_independent_payload_and_target_list(self):
        for value in (None,b'',b'\x00\xffwire'):
            for items in (None,(),(b'\xff',),(target(),b'\xff',target(direction_value=b'\xff'))):
                child=tagea(items,value);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='ea.bin')
                self.assertEqual(row['diagnostic'],dict(source='ea.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=234),row['completedRecords'])
                start=39+len(value or b'')
                self.assertIn(dict(start=start,end=end,kind='anonymous-target-list'),row['completedRecords'])
                cursor=start+4
                for item in items or ():
                    self.assertIn(dict(start=cursor,end=cursor+len(item),kind='anonymous-target-profile'),row['completedRecords'])
                    cursor+=len(item)
                self.assertEqual(cursor,end)

    def test_tagea_null_extended_cuts_limits_and_trailing(self):
        for child in (tagea(),tagea((target(),b'\xff',target())),b'\xea\xff',b'\xfa\xea\x00'+tagea()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='ea-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='ea-limit',limit=n))

    def test_tagea_malformed_counts_headers_and_incomplete_list(self):
        raw=prefix(sequence(tagea((target(),b'\xff',target()))))
        good=event_prefix(raw,source='ea-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='ea-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('ea-bounds',at,value))
        for before in ((),(b'\xff',target())):
            child=tagea(before+(target(selector=b'\x03\x17'),))
            row=event_prefix(prefix(sequence(child)),source='ea-gap')
            self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),('unsupported','nested-profile',23))
            self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
            self.assertFalse(any(r.get('tag')==234 or r['kind']=='anonymous-target-list' for r in row['completedRecords']))
            self.assertEqual(len([r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile']),len(before))

    def test_tag35_independent_targets_and_final_source_boundary(self):
        for first in (b'\xff',target(),target(direction_value=b'\xff')):
            for second in (b'\xff',target(),target(selector=b'\x03\x05\x00'+bytes(8))):
                child=tag35(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='35.bin')
                self.assertEqual(row['diagnostic'],dict(source='35.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=53),row['completedRecords'])
                self.assertIn(dict(start=34,end=34+len(first),kind='anonymous-target-profile'),row['completedRecords'])
                self.assertIn(dict(start=36+len(first),end=36+len(first)+len(second),kind='anonymous-target-profile'),row['completedRecords'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

        child=tag35(curve=curve24((bytes(28),)),direction_value=direction(),last=scalar_payload(b'wire'))
        row=event_prefix(prefix(sequence(child,b'\x59')),source='35-final')
        end=19+len(child)
        self.assertEqual(row['consumedEnd'],end)
        self.assertIn(dict(start=end-14,end=end,kind='anonymous-scalar-payload'),row['completedRecords'])

    def test_tag35_null_extended_cuts_limits_and_trailing(self):
        for child in (tag35(),tag35(target(),target(),curve24((bytes(28),bytes(28))),direction(),scalar_payload(b"wire")),b'\x35\xff',b'\xfa\x35\x00'+tag35()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='35-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='35-limit',limit=n))

    def test_tag35_malformed_counts_headers_and_each_target_gap(self):
        for curve in (b'\xff',curve24(None),curve24(()),curve24((bytes(28),))):
            for last in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'\xff',bits=b'\xff'*4)):
                raw=sequence(tag35(curve=curve,last=last))
                self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
        raw=prefix(sequence(tag35(target(),target(),curve24((bytes(28),bytes(28))),direction(),scalar_payload(b"wire"))))
        good=event_prefix(raw,source='35-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='35-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('35-bounds',at,value))
        for first_gap in (True,False):
            bad=target(selector=b'\x03\x17');good_target=target()
            child=tag35(bad,good_target) if first_gap else tag35(good_target,bad)
            row=event_prefix(prefix(sequence(child)),source='35-gap')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual((row['diagnostic']['category'],row['diagnostic']['actual']),('nested-profile',23))
            self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
            self.assertFalse(any(r.get('tag')==53 for r in row['completedRecords']))
            self.assertEqual(len([r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile']),0 if first_gap else 1)

        for at in (8,13):
            bad=bytearray(direction());bad[at]=13
            child=tag35(direction_value=bad,last=scalar_payload())
            row=event_prefix(prefix(sequence(child)),source='35-direction-gap')
            self.assertEqual((row['status'],row['diagnostic']['category'],row['diagnostic']['actual']),
                             ('failed','member-count',0))
            self.assertEqual(row['consumedEnd'],41+at)
            self.assertFalse(any(r.get('tag')==53 for r in row['completedRecords']))

    def test_tag7e_two_independent_targets(self):
        for first in (b'\xff',target(),target(direction_value=b'\xff')):
            for second in (b'\xff',target(),target(selector=b'\x03\x05\x00'+bytes(8))):
                child=tag7e(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='7e.bin')
                self.assertEqual(row['diagnostic'],dict(source='7e.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=126),row['completedRecords'])
                self.assertEqual([r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile'],
                    [dict(start=34,end=34+len(first),kind='anonymous-target-profile'),dict(start=34+len(first),end=end,kind='anonymous-target-profile')])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag7e_null_extended_cuts_limits_and_trailing(self):
        for child in (tag7e(),tag7e(target(),target()),b'\x7e\xff',b'\xfa\x7e\x00'+tag7e()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='7e-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='7e-limit',limit=n))

    def test_tag7e_malformed_counts_headers_and_each_target_gap(self):
        raw=prefix(sequence(tag7e(target(),target())))
        good=event_prefix(raw,source='7e-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='7e-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('7e-bounds',at,value))
        for first_gap in (True,False):
            bad=target(selector=b'\x03\x17');good_target=target()
            child=tag7e(bad,good_target) if first_gap else tag7e(good_target,bad)
            row=event_prefix(prefix(sequence(child)),source='7e-gap')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual((row['diagnostic']['category'],row['diagnostic']['actual']),('nested-profile',23))
            self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
            self.assertFalse(any(r.get('tag')==126 for r in row['completedRecords']))
            self.assertEqual(len([r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile']),0 if first_gap else 1)

    def test_tag16b_scalar_payload_then_independent_target(self):
        for first in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'\x00\xffwire',bits=b'\xff'*4)):
            for second in (b'\xff',target(),target(direction_value=b'\xff')):
                child=tag16b(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='16b.bin')
                self.assertEqual(row['diagnostic'],dict(source='16b.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=363),row['completedRecords'])
                self.assertIn(dict(start=36,end=36+len(first),kind='anonymous-scalar-payload'),row['completedRecords'])
                self.assertIn(dict(start=36+len(first),end=end,kind='anonymous-target-profile'),row['completedRecords'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag16b_null_truncations_limits_and_trailing(self):
        for child in (tag16b(),tag16b(scalar_payload(b'raw'),target()),b'\xfa\x6b\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='16b-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='16b-limit',limit=n))

    def test_tag16b_malformed_counts_headers_and_unknown_target(self):
        raw=prefix(sequence(tag16b(scalar_payload(b'payload'),target())))
        good=event_prefix(raw,source='16b-bounds');self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='16b-bounds');self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('16b-bounds',at,value))
        child=tag16b(scalar_payload(b'x'),target(selector=b'\x03\x17'))
        row=event_prefix(prefix(sequence(child)),source='16b-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual((row['diagnostic']['category'],row['diagnostic']['actual']),('nested-profile',23))
        self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
        self.assertFalse(any(r.get('tag')==363 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(b'\x6b'+tag16b()[3:])),source='16b-short')
        self.assertEqual((row['diagnostic']['offset'],row['diagnostic']['expected'],row['diagnostic']['actual'],row['diagnostic']['category']),(20,7,6,'member-count'))

    def test_tag24_nested_curve_counts_and_independent_envelope_members(self):
        curves=(b'\xff',curve24(None),curve24(),curve24((bytes(range(28)),)),curve24((b'\xff'*28,b'\x80'*28)))
        for first in curves:
            for second in curves:
                child=tag24(impulse24(first,envelope24(second,first),b'raw\x00\xff'),target(),b'outer')
                end=19+len(child);row=event_prefix(prefix(sequence(child,b'\x59')),source='24.bin')
                self.assertEqual(row['diagnostic'],dict(source='24.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=36),row['completedRecords'])
                actual=[r for r in row['completedRecords'] if r['kind']=='anonymous-curve-profile']
                self.assertEqual([r['end']-r['start'] for r in actual],[len(first),len(second),len(first)])
                raw28=[r for r in row['ranges'] if r['kind']=='anonymous-raw28']
                self.assertTrue(all(r['end']-r['start']==28 for r in raw28))
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag24_null_extended_truncation_hard_limits_and_trailing(self):
        children=(tag24(),tag24(impulse24()),tag24(impulse24(curve24((bytes(range(28)),)),envelope24(curve24(None),curve24()))),b'\x24\xff',b'\xfa\x24\x00'+tag24()[1:])
        for child in children:
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='24-limit',limit=n)
                self.assertEqual(row['status'],'failed');self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='24-limit',limit=n))

    def test_tag24_malformed_all_headers_counts_and_lengths(self):
        c=curve24((bytes(range(28)),));raw=prefix(sequence(tag24(impulse24(c,envelope24(c,c),b'payload'),target(),b'outer')))
        good=event_prefix(raw,source='24-bounds')
        self.assertEqual(good['status'],'supported-prefix')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='24-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('24-bounds',at,value))
        child=tag24(impulse24(c,envelope24(c,c)),b'\x01')
        row=event_prefix(prefix(sequence(child)),source='24-target')
        self.assertEqual(row['status'],'failed')
        self.assertEqual(row['diagnostic']['category'],'member-count')
        self.assertFalse(any(r.get('tag')==36 for r in row['completedRecords']))
        self.assertEqual(row['diagnostic']['offset'],19+len(child)-1)

    def test_tag6a_two_independent_scalar32_lists(self):
        for first in (None,(),(0,),(0xffffffff,0x80000000,0x7fc00000)):
            for second in (None,(),(1,2),(0xffffffff,)):
                child=tag6a(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='6a.bin')
                self.assertEqual(row['diagnostic'],dict(source='6a.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=106),row['completedRecords'])
                lists=[r for r in row['completedRecords'] if r['kind']=='anonymous-scalar32-list']
                split=36+4+4*len(first or ())
                self.assertEqual(lists,[dict(start=36,end=split,kind='anonymous-scalar32-list'),dict(start=split,end=end,kind='anonymous-scalar32-list')])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag6a_null_extended_cuts_limits_and_trailing(self):
        for child in (tag6a(),tag6a(None,None),tag6a((1,2),(0xffffffff,)),b'\x6a\xff',b'\xfa\x6a\x00'+tag6a()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='6a-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='6a-limit',limit=n))

    def test_tag6a_malformed_headers_and_both_list_counts(self):
        raw=prefix(sequence(tag6a((1,2),(3,4))));good=event_prefix(raw,source='6a-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='6a-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('6a-bounds',at,value))
        row=event_prefix(prefix(sequence(b'\x6b'+tag6a()[1:])),source='6a-other')
        self.assertEqual(row['diagnostic'],dict(source='6a-other',offset=20,expected=7,actual=8,category='member-count'))

    def test_tagbd_sequence_then_independent_target(self):
        for children in (b'\xff',b'\x03'+struct.pack('<i',-1)+b'\xfe\xff',sequence(),sequence(b'\xff',tag145()),sequence(tagbd(b'\xff',b'\xff'))):
            for nested in (b'\xff',target()):
                child=tagbd(children,nested);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='bd.bin')
                self.assertEqual(row['diagnostic'],dict(source='bd.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=189),row['completedRecords'])
                self.assertIn(dict(start=34,end=end-len(nested),kind='sequence'),row['completedRecords'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tagbd_null_extended_cuts_limits_and_trailing(self):
        for child in (tagbd(),tagbd(sequence(tag145())),tagbd(b'\xff',b'\xff'),b'\xbd\xff',b'\xfa\xbd\x00'+tagbd()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='bd-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='bd-limit',limit=n))

    def test_tagbd_malformed_counts_and_unknown_child_stop(self):
        raw=prefix(sequence(tagbd(sequence(tag145()))));good=event_prefix(raw,source='bd-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='bd-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('bd-bounds',at,value))
        row=event_prefix(prefix(sequence(tagbd(sequence(b'\x59')))),source='bd-child')
        self.assertEqual(row['diagnostic'],dict(source='bd-child',offset=39,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertFalse(any(r.get('tag')==189 for r in row['completedRecords']))
        self.assertEqual(row['opaqueRemainderRange'][0],39)

    def test_tagbd_recursive_sequence_limit(self):
        child=b'\xff'
        for _ in range(64):child=tagbd(sequence(child),b'\xff')
        self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        raw=sequence(tagbd(sequence(child),b'\xff'))
        with self.assertRaises(Unsupported) as caught:sequence_frame(raw)
        self.assertEqual((caught.exception.diagnostic['category'],caught.exception.diagnostic['actual']),('depth-limit',65))

    def test_tagde_lists_raw_spans_and_final_scalars(self):
        assignment=b'\x06'+bytes(4)+payload(b'key')+bytes(4)+payload(None)+payload(b'val')+b'\xff'
        point=b'\x02'+target()+payload(bytes(range(256)))
        for assignments in (None,(),(b'\xff',assignment)):
            for points in (None,(),(b'\xff',point)):
                child=tagde(assignments,points);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='de.bin')
                self.assertEqual(row['diagnostic'],dict(source='de.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=222),row['completedRecords'])
                spans=[r for r in row['ranges'] if r['kind']=='anonymous-raw12']
                self.assertEqual(len(spans),4)
                self.assertTrue(all(r['end']-r['start']==12 for r in spans))
                self.assertEqual(row['ranges'][-1],dict(start=end-4,end=end,kind='anonymous-scalar32'))
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tagde_null_extended_cuts_limits_and_trailing(self):
        for child in (tagde(),tagde(None,None,b'\xff'),tagde(points=(b'\x02\xff'+payload(None),)),b'\xde\xff',b'\xfa\xde\x00'+tagde()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='de-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='de-limit',limit=n))

    def test_tagde_malformed_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tagde(points=(b'\x02'+target()+payload(b'key'),))))
        good=event_prefix(raw,source='de-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='de-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('de-bounds',at,value))
        row=event_prefix(prefix(sequence(tagde(points=(b'\x02'+target(selector=b'\x03\x06'+bytes(8))+payload(None),)))),source='de-gap')
        self.assertEqual((row['status'],row['diagnostic']['category']),('unsupported','nested-profile'))
        self.assertFalse(any(r.get('tag')==222 for r in row['completedRecords']))

    def test_target_bytes_profile_keeps_payload_after_target(self):
        for raw in (b'\xff',b'\x02\xff'+payload(None),b'\x02'+target()+payload(bytes(range(256)))):
            r=Reader(raw,'target-bytes',len(raw));r.target_bytes_profile()
            self.assertEqual(r.pos,len(raw))
            self.assertEqual(r.records[-1],dict(start=0,end=len(raw),kind='anonymous-target-bytes-profile'))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):Reader(raw,'target-bytes',n).target_bytes_profile()

    def test_tag145_scalar_then_paired_payload_exact_order(self):
        for first in (b'\xff',b'\x03'+payload(None)+b'\x00'+bytes(4),b'\x03'+payload(b'key')+b'\xfe'+bytes.fromhex('FFFFFFFF')):
            for second in (b'\xff',pair(None,None),pair(b'',b''),pair(b'key',bytes(range(256)),255)):
                child=tag145(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='145.bin')
                self.assertEqual(row['diagnostic'],dict(source='145.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=325),row['completedRecords'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag145_null_cuts_limits_and_trailing(self):
        for child in (tag145(),tag145(b'\xff',b'\xff'),b'\xfa\x45\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='145-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='145-limit',limit=n))

    def test_tag145_bad_headers_counts_and_distinct_outer_tag(self):
        raw=prefix(sequence(tag145()));good=event_prefix(raw,source='145-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='145-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('145-bounds',at,value))
        row=event_prefix(prefix(sequence(b'\x45'+tag145()[3:])),source='145-other')
        self.assertEqual(row['diagnostic'],dict(source='145-other',offset=19,expected='supported current union tag',actual=69,category='union-tag'))

    def test_tagc4_two_payloads_separated_by_finder_then_target(self):
        for first in (None,b'',b'first'):
            for second in (None,b'',bytes(range(256))):
                child=tagc4(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='c4.bin')
                self.assertEqual(row['diagnostic'],dict(source='c4.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=196),row['completedRecords'])
                self.assertIn(dict(start=end-len(target()),end=end,kind='anonymous-target-profile'),row['completedRecords'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tagc4_null_extended_cuts_limits_and_trailing(self):
        for child in (tagc4(),tagc4(None,None),tagc4(b'',b''),tagc4(finder=b'\xff'),tagc4(nested=b'\xff'),b'\xc4\xff',b'\xfa\xc4\x00'+tagc4()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='c4-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='c4-limit',limit=n))

    def test_tagc4_bad_headers_counts_and_unknown_target(self):
        raw=prefix(sequence(tagc4()));good=event_prefix(raw,source='c4-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='c4-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('c4-bounds',at,value))
        row=event_prefix(prefix(sequence(tagc4(nested=target(selector=b'\x03\x06'+bytes(8))))),source='c4-gap')
        self.assertEqual((row['status'],row['diagnostic']['category']),('unsupported','nested-profile'))
        self.assertFalse(any(r.get('tag')==196 for r in row['completedRecords']))

    def test_tag5a_paired_payload_then_independent_final_payload(self):
        for first in (None,b'',b'key'):
            for second in (None,b'',b'\xff\x00'):
                for value in (None,b'',bytes(range(256))):
                    nested=pair(first,second,128);child=tag5a(nested,value);end=19+len(child)
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='5a.bin')
                    self.assertEqual(row['diagnostic'],dict(source='5a.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                    self.assertIn(dict(start=19,end=end,kind='union',tag=90),row['completedRecords'])
                    at=34+len(nested)
                    self.assertIn(dict(start=at,end=at+4,kind='count-i32'),row['ranges'])
                    self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag5a_null_extended_cuts_limits_and_trailing(self):
        for child in (tag5a(),tag5a(pair(None,None),None),tag5a(pair(b'',b''),b''),tag5a(b'\xff'),b'\x5a\xff',b'\xfa\x5a\x00'+tag5a()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='5a-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='5a-limit',limit=n))

    def test_tag5a_bad_headers_and_counts(self):
        raw=prefix(sequence(tag5a()));good=event_prefix(raw,source='5a-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='5a-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('5a-bounds',at,value))
        row=event_prefix(prefix(sequence(b'\xc4'+tag5a()[1:])),source='5a-other')
        self.assertEqual(row['diagnostic'],dict(source='5a-other',offset=20,expected=8,actual=6,category='member-count'))

    def test_tag48_final_list_extent_and_raw_bits(self):
        for values in (None,(),(0,),(0xffffffff,0x80000000,0x7fc00000)):
            child=tag48(values);end=19+len(child)
            self.assertEqual(len(child),23+4*len(values or ()))
            row=event_prefix(prefix(sequence(child,b'\x59')),source='48.bin')
            self.assertEqual(row['diagnostic'],dict(source='48.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=72),row['completedRecords'])
            self.assertIn(dict(start=38,end=end,kind='anonymous-scalar32-list'),row['completedRecords'])
            self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag48_null_extended_cuts_limits_and_trailing(self):
        for child in (tag48(),tag48(None),tag48(()),b'\x48\xff',b'\xfa\x48\x00'+tag48()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='48-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='48-limit',limit=n))

    def test_tag48_bad_headers_and_counts(self):
        raw=prefix(sequence(tag48()));good=event_prefix(raw,source='48-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='48-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('48-bounds',at,value))
        row=event_prefix(prefix(sequence(b'\xc4'+tag48()[1:])),source='48-other')
        self.assertEqual(row['diagnostic'],dict(source='48-other',offset=20,expected=8,actual=6,category='member-count'))

    def test_tag88_scalar_payload_is_final_member(self):
        for value in (None,b'',b'x',bytes(range(256))):
            for bits in (bytes(4),b'\xff'*4,b'\x00\x00\xc0\x7f'):
                child=tag88(scalar_payload(value,128,bits));end=19+len(child)
                self.assertEqual(len(child),25+len(value or b''))
                row=event_prefix(prefix(sequence(child,b'\x59')),source='88.bin')
                self.assertEqual(row['diagnostic'],dict(source='88.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=136),row['completedRecords'])
                self.assertEqual(row['ranges'][-1],dict(start=end-4,end=end,kind='anonymous-scalar32'))
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag88_null_extended_cuts_limits_and_trailing(self):
        for child in (tag88(),tag88(scalar_payload(None)),tag88(scalar_payload(b'')),tag88(b'\xff'),b'\x88\xff',b'\xfa\x88\x00'+tag88()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='88-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='88-limit',limit=n))

    def test_tag88_bad_headers_and_counts(self):
        raw=prefix(sequence(tag88()));good=event_prefix(raw,source='88-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='88-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('88-bounds',at,value))
        row=event_prefix(prefix(sequence(b'\x48'+tag88()[1:])),source='88-other')
        self.assertEqual(row['diagnostic'],dict(source='88-other',offset=20,expected=6,actual=5,category='member-count'))

    def test_tag7a_scalar_and_variable_payload_extent(self):
        for value in (None,b'',b'x',bytes(range(256))):
            for bits in (0,0xffffffff,0x80000000,0x7fc00000):
                child=tag7a(value,bits);end=19+len(child)
                self.assertEqual(len(child),23+len(value or b''))
                row=event_prefix(prefix(sequence(child,b'\x59')),source='7a.bin')
                self.assertEqual(row['diagnostic'],dict(source='7a.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=122),row['completedRecords'])
                self.assertIn(dict(start=34,end=38,kind='anonymous-scalar32'),row['ranges'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag7a_null_extended_cuts_limits_and_trailing(self):
        for child in (tag7a(),tag7a(None),tag7a(b''),b'\x7a\xff',b'\xfa\x7a\x00'+tag7a()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='7a-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='7a-limit',limit=n))

    def test_tag7a_bad_headers_and_counts(self):
        raw=prefix(sequence(tag7a()));good=event_prefix(raw,source='7a-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='7a-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('7a-bounds',at,value))
        # The newly supported physical tag requires its own member header.
        row=event_prefix(prefix(sequence(b'\x88'+tag7a()[1:])),source='7a-other')
        self.assertEqual(row['diagnostic'],dict(source='7a-other',offset=20,expected=5,actual=6,category='member-count'))

    def test_tag0a_variable_payload_before_target_and_no_final_byte(self):
        for value in (None,b'',b'x',bytes(range(256))):
            for nested in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'\xff\x00')):
                child=tag0a(value,nested);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='0a.bin')
                self.assertEqual(row['diagnostic'],dict(source='0a.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=10),row['completedRecords'])
                target_start=34+len(payload(value))+len(nested)
                self.assertIn(dict(start=target_start,end=end,kind='anonymous-target-profile'),row['completedRecords'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag0a_null_extended_cuts_limits_and_trailing(self):
        for child in (tag0a(),tag0a(None),tag0a(b''),tag0a(nested=b'\xff'),tag0a(t=b'\xff'),b'\x0a\xff',b'\xfa\x0a\x00'+tag0a()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='0a-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='0a-limit',limit=n))

    def test_tag0a_bad_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tag0a()));good=event_prefix(raw,source='0a-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='0a-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('0a-bounds',at,value))
        row=event_prefix(prefix(sequence(tag0a(t=target(selector=b'\x03\x06'+bytes(8))))),source='0a-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==10 for r in row['completedRecords']))

    def test_tag9b_variable_payload_before_target_and_no_final_byte(self):
        for first in (None,b'',b'x',bytes(range(256))):
            for second in (None,b'',b'\xff\x00'):
                child=tag9b(first,second);end=19+len(child)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='9b.bin')
                self.assertEqual(row['diagnostic'],dict(source='9b.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=155),row['completedRecords'])
                raw_start=34+len(payload(first));target_start=raw_start+16+len(payload(second))+4
                self.assertIn(dict(start=raw_start,end=raw_start+16,kind='anonymous-raw16'),row['ranges'])
                self.assertIn(dict(start=target_start,end=end,kind='anonymous-target-profile'),row['completedRecords'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag9b_null_extended_cuts_limits_and_trailing(self):
        for child in (tag9b(),tag9b(None),tag9b(b''),tag9b(nested=b'\xff'),b'\x9b\xff',b'\xfa\x9b\x00'+tag9b()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='9b-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='9b-limit',limit=n))

    def test_tag9b_bad_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tag9b()));good=event_prefix(raw,source='9b-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='9b-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('9b-bounds',at,value))
        row=event_prefix(prefix(sequence(tag9b(nested=target(selector=b'\x03\x06'+bytes(8))))),source='9b-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==155 for r in row['completedRecords']))

    def test_tag10f_fixed_members_keep_both_byte_values(self):
        for first in (0,1,128,255):
            for last in (0,1,128,255):
                child=tag10f(first,last);self.assertEqual(len(child),18)
                row=event_prefix(prefix(sequence(child,b'\x59')),source='10f.bin')
                self.assertEqual(row['diagnostic'],dict(source='10f.bin',offset=37,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=37,kind='union',tag=271),row['completedRecords'])
                self.assertIn(dict(start=36,end=37,kind='anonymous-nonzero-byte'),row['ranges'])
                self.assertEqual((child[4],child[-1]),(first,last))
                self.assertEqual(row['opaqueRemainderRange'][0],37)

    def test_tag10f_null_cuts_limits_and_trailing(self):
        for child in (tag10f(),b'\xfa\x0f\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='10f-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='10f-limit',limit=n))

    def test_tag10f_bad_headers_and_enclosing_counts(self):
        for header in (0,4,6,254):
            bad=bytearray(tag10f());bad[3]=header
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='10f-header')
            self.assertEqual(caught.exception.diagnostic,dict(source='10f-header',offset=8,expected=5,actual=header,category='member-count'))
        for value in (-2,2147483647):
            bad=bytearray(sequence(tag10f()));struct.pack_into('<i',bad,1,value)
            with self.assertRaises(FrameError) as caught:sequence_frame(bad,source='10f-count')
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('10f-count',1,value,'count-bounds'))
        row=event_prefix(prefix(sequence(b'\x0f'+tag10f()[3:])),source='10f-short')
        self.assertEqual(row['diagnostic']['actual'],15)
        self.assertEqual(row['consumedEnd'],19)

    def test_tag44_variable_payload_before_target_and_no_final_byte(self):
        for value in (None,b'',b'x',bytes(range(256))):
            child=tag44(value);end=19+len(child)
            row=event_prefix(prefix(sequence(child,b'\x59')),source='44.bin')
            self.assertEqual(row['diagnostic'],dict(source='44.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
            self.assertIn(dict(start=19,end=end,kind='union',tag=68),row['completedRecords'])
            self.assertIn(dict(start=34+len(payload(value)),end=end,kind='anonymous-target-profile'),row['completedRecords'])
            self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag44_null_extended_cuts_limits_and_trailing(self):
        for child in (tag44(),tag44(None),tag44(b''),tag44(nested=b'\xff'),b'\x44\xff',b'\xfa\x44\x00'+tag44()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='44-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='44-limit',limit=n))

    def test_tag44_bad_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tag44()));good=event_prefix(raw,source='44-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='44-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('44-bounds',at,value))
        row=event_prefix(prefix(sequence(tag44(nested=target(selector=b'\x03\x06'+bytes(8))))),source='44-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==68 for r in row['completedRecords']))

    def test_tag69_fourth_scalar_precedes_target_and_no_final_byte(self):
        child=tag69();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='69.bin')
        self.assertEqual(row['diagnostic'],dict(source='69.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=end,kind='union',tag=105),row['completedRecords'])
        self.assertIn(dict(start=34,end=38,kind='anonymous-scalar32'),row['ranges'])
        self.assertIn(dict(start=38,end=end,kind='anonymous-target-profile'),row['completedRecords'])
        self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag69_null_extended_cuts_limits_and_trailing(self):
        for child in (tag69(),tag69(b'\xff'),b'\x69\xff',b'\xfa\x69\x00'+tag69()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='69-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='69-limit',limit=n))

    def test_tag69_bad_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tag69()));good=event_prefix(raw,source='69-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='69-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('69-bounds',at,value))
        row=event_prefix(prefix(sequence(tag69(target(selector=b'\x03\x06'+bytes(8))))),source='69-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==105 for r in row['completedRecords']))

    def test_tag163_variable_prefix_and_two_distinct_scalar_payloads(self):
        child=tag163();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='163.bin')
        self.assertEqual(row['diagnostic'],dict(source='163.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=end,kind='union',tag=355),row['completedRecords'])
        records=[r for r in row['completedRecords'] if r['kind']=='anonymous-scalar-payload']
        self.assertEqual(len(records),2)
        self.assertEqual(records[0]['end'],records[1]['start'])
        self.assertEqual(records[1]['end'],end)
        self.assertEqual(records[0]['start'],36+len(payload(b'name'))+4)
        self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag163_null_empty_cuts_limits_and_trailing(self):
        for child in (tag163(),tag163(None),tag163(b''),tag163(left=b'\xff',right=b'\xff'),
                      tag163(left=scalar_payload(None),right=scalar_payload(b'')),b'\xfa\x63\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='163-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='163-limit',limit=n))

    def test_tag163_bad_headers_and_lengths(self):
        raw=prefix(sequence(tag163()));good=event_prefix(raw,source='163-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='163-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('163-bounds',at,value))

    def test_tag136_finder_scalar_target_payload_and_final_byte(self):
        child=tag136();end=19+len(child)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='136.bin')
        self.assertEqual(row['diagnostic'],dict(source='136.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
        self.assertIn(dict(start=19,end=end,kind='union',tag=310),row['completedRecords'])
        finder=next(r for r in row['completedRecords'] if r['kind']=='anonymous-finder-profile')
        target_row=next(r for r in row['completedRecords'] if r['kind']=='anonymous-target-profile')
        self.assertEqual(finder['start'],36)
        self.assertEqual(target_row['start'],finder['end']+4)
        self.assertIn(dict(start=end-1,end=end,kind='anonymous-nonzero-byte'),row['ranges'])
        self.assertEqual(row['opaqueRemainderRange'][0],end)

    def test_tag136_null_variants_cuts_limits_and_trailing(self):
        for child in (tag136(),tag136(value=None),tag136(value=b''),tag136(b'\xff',b'\xff'),b'\xfa\x36\x01\xff'):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='136-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='136-limit',limit=n))

    def test_tag136_bad_headers_counts_and_unknown_nested(self):
        raw=prefix(sequence(tag136()));good=event_prefix(raw,source='136-bounds')
        for span in good['ranges']:
            if span['kind'] not in ('member-header','count-i32'):continue
            for value in ((0,254) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(raw);at=span['start']
                if span['kind']=='member-header':bad[at]=value
                else:struct.pack_into('<i',bad,at,value)
                row=event_prefix(bad,source='136-bounds')
                self.assertEqual(row['status'],'failed')
                self.assertEqual((row['diagnostic']['source'],row['diagnostic']['offset'],row['diagnostic']['actual']),('136-bounds',at,value))
        row=event_prefix(prefix(sequence(tag136(nested=target(selector=b'\x03\x06'+bytes(8))))),source='136-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertFalse(any(r.get('tag')==310 for r in row['completedRecords']))

    def test_tag6d_variable_payload_and_following_unknown(self):
        for value in (None,b'',b'x',bytes(range(256))):
            for flag in (0,1,128,255):
                child=tag6d(value,flag);end=19+len(child)
                self.assertEqual(len(child),23+len(value or b''))
                row=event_prefix(prefix(sequence(child,b'\x59')),source='6d.bin')
                self.assertEqual(row['diagnostic'],dict(source='6d.bin',offset=end,expected='supported current union tag',actual=89,category='union-tag'))
                self.assertIn(dict(start=19,end=end,kind='union',tag=109),row['completedRecords'])
                self.assertEqual(row['opaqueRemainderRange'][0],end)
                self.assertFalse(any(r['kind']=='anonymous-scalar64' for r in row['ranges']))

    def test_tag6d_all_cuts_limits_null_extended_and_trailing(self):
        for child in (tag6d(),tag6d(None),tag6d(b''),b'\x6d\xff',b'\xfa\x6d\x00'+tag6d()[1:]):
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])
            for extra in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+extra)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            full=prefix(raw)
            for n in range(len(full)):
                row=event_prefix(full,source='6d-limit',limit=n)
                self.assertEqual(row['status'],'failed')
                self.assertLessEqual(row['consumedEnd'],n)
                self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='6d-limit',limit=n))

    def test_tag6d_bad_header_and_payload_lengths(self):
        for header in (0,5,7,254):
            bad=bytearray(tag6d());bad[1]=header
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='6d-header')
            self.assertEqual(caught.exception.diagnostic,dict(source='6d-header',offset=6,expected=6,actual=header,category='member-count'))
        for value in (-2147483648,-2,2147483647):
            bad=bytearray(tag6d());struct.pack_into('<i',bad,19,value)
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='6d-length')
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('6d-length',24,value,'count-bounds'))

    def test_tag5b_exact_scalar64_boundary_and_bits(self):
        for flag in (0,1,128,254,255):
            for bits in (0,1,0x8000000000000000,0xffffffffffffffff,0x0102030405060708):
                child=tag5b(flag,bits);self.assertEqual(len(child),27)
                row=event_prefix(prefix(sequence(child,b'\x3d')),source='5b.bin')
                self.assertEqual(row['status'],'unsupported')
                self.assertEqual(row['diagnostic']['actual'],61)
                self.assertEqual(row['consumedEnd'],46)
                self.assertIn(dict(start=19,end=46,kind='union',tag=91),row['completedRecords'])
                self.assertIn(dict(start=38,end=46,kind='anonymous-scalar64'),row['ranges'])
                self.assertEqual(child[19:27],struct.pack('<Q',bits))
                self.assertFalse(row['wholeSchemaExact'])

    def test_tag5b_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag5b())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='5b-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='5b-limit.bin',limit=n))

    def test_tag5b_bad_header_and_enclosing_counts(self):
        bad=bytearray(tag5b());bad[1]=5
        with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='5b-header.bin')
        self.assertEqual(caught.exception.diagnostic,dict(source='5b-header.bin',offset=6,expected=6,actual=5,category='member-count'))
        for value in (-2,2147483647):
            raw=bytearray(sequence(tag5b()));struct.pack_into('<i',raw,1,value)
            with self.assertRaises(FrameError) as caught:sequence_frame(raw,source='5b-count.bin')
            d=caught.exception.diagnostic
            self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),('5b-count.bin',1,value,'count-bounds'))
        raw=bytearray(sequence(tag5b()));struct.pack_into('<i',raw,1,0)
        with self.assertRaises(FrameError) as caught:sequence_frame(raw)
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_tag5b_null_and_extended_tag(self):
        for child in (b'\x5b\xff',b'\xfa\x5b\x00\xff',b'\xfa\x5b\x00'+tag5b()[1:]):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:n])

    def test_tag57_paired_record_boundaries_and_later_unknown(self):
        child=tag57();self.assertEqual(len(child),70)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='57.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],89)
        self.assertEqual(row['consumedEnd'],89)
        self.assertIn(dict(start=19,end=89,kind='union',tag=87),row['completedRecords'])
        spans=[(r['start']-19,r['end']-19) for r in row['completedRecords'] if r['kind']=='anonymous-paired-payload']
        self.assertEqual(spans,[(25,38),(38,39),(39,49)])
        self.assertIn(dict(start=72,end=89,kind='anonymous-query-profile'),row['completedRecords'])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag57_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag57())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='57-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='57-limit.bin',limit=n))

    def test_tag57_bad_counts_and_headers(self):
        for at in (15,21,26,32,40,45,58):
            for value in (-2,2147483647):
                bad=bytearray(tag57());struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='57-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('57-count.bin',at+5,value,'count-bounds'))
        for at in (1,25,39,53):
            bad=bytearray(tag57());bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        # The related tag56 has member-one elements; accepting its header here
        # would silently select the wrong current native element profile.
        bad=bytearray(tag57());bad[25]=1
        with self.assertRaises(FrameError):sequence_frame(sequence(bad))

    def test_tag57_nulls_empty_lists_and_extended_tag(self):
        children=[b'\x57\xff',b'\xfa\x57\x00'+tag57()[1:]]
        for count in (-1,0):
            for key in (None,b''):
                for query in (b'\xff',b'\x02'+bytes(4)+struct.pack('<i',count)):
                    children.append(b'\x57\x08'+bytes(13)+payload(key)+struct.pack('<i',count)+bytes(4)+query)
        for child in children:
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_finder10_zero_members_and_parent_continuation(self):
        for value in (b'\xff',b'\x0a\x00',b'\x0a\xff',b'\xfa\x0a\x00\x00',b'\xfa\x0a\x00\xff'):
            r=Reader(value+b'\xaa','finder10');r.selector_finder_profile()
            self.assertEqual(r.pos,len(value));self.assertEqual(r.records[-1],dict(start=0,end=len(value),kind='anonymous-selector-finder-profile'))
            child=tag_ec(nested=target(selector=b'\x03'+value+bytes(8)))
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            row=event_prefix(prefix(sequence(child,b'\x59')),source='finder10')
            self.assertEqual(row['diagnostic']['offset'],19+len(child));self.assertEqual(row['diagnostic']['actual'],89)
            self.assertFalse(row['wholeSchemaExact'])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_finder10_every_cut_and_hard_limit_mutation(self):
        for value in (b'\x0a\x00',b'\x0a\xff',b'\xfa\x0a\x00\x00',b'\xfa\x0a\x00\xff'):
            for n in range(len(value)):
                out=[]
                for data in (value,value[:n],value[:n]+b'\xff'*(len(value)-n)):
                    r=Reader(data,'finder10-cut',n)
                    with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                    self.assertLessEqual(r.pos,n);self.assertEqual(r.records,[])
                    out.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])

    def test_finder10_wrong_member_count_stops_at_header(self):
        for wire in (b'\x0a',b'\xfa\x0a\x00'):
            for h in (1,3,254):
                r=Reader(wire+bytes([h])+bytes(32),'finder10-header')
                with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='finder10-header',offset=len(wire),expected=0,actual=h,category='member-count'))
                self.assertEqual(r.records,[])

    def test_direction_targets_independent_recursive_boundaries(self):
        leaf=target(direction_value=b'\xff',selector=b'\xff')
        values=(b'\xff',leaf,target(direction_value=direction()[:8]+leaf+bytes(4)+b'\xff'+bytes(4)))
        for first in values:
            for second in values:
                value=direction()[:8]+first+b'\xff'*4+second+b'\x80'*4
                r=Reader(value,'direction-recursive');r.direction_profile();self.assertEqual(r.pos,len(value));self.assertEqual(r.target_depth,0)
                self.assertEqual(r.records[-1],dict(start=0,end=len(value),kind='anonymous-direction-profile'))
                child=tag_ec(nested=target(direction_value=value));raw=sequence(child)
                self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_direction_target_recursion_limit_and_cleanup(self):
        value=target(direction_value=b'\xff',selector=b'\xff')
        for _ in range(63):value=target(direction_value=direction()[:8]+value+bytes(4)+b'\xff'+bytes(4),selector=b'\xff')
        r=Reader(value,'depth64');r.target_profile();self.assertEqual(r.pos,len(value));self.assertEqual(r.target_depth,0)
        value=target(direction_value=direction()[:8]+value+bytes(4)+b'\xff'+bytes(4),selector=b'\xff')
        r=Reader(value,'depth65')
        with self.assertRaises(Unsupported) as caught:r.target_profile()
        self.assertEqual(caught.exception.diagnostic,dict(source='depth65',offset=64*9,expected='target nesting <= 64',actual=65,category='depth-limit'))
        self.assertEqual(r.pos,64*9);self.assertEqual(r.target_depth,0);self.assertEqual(r.records,[])
        r=Reader(b'\xff','null-depth');r.target_depth=64;r.target_profile();self.assertEqual(r.pos,1);self.assertEqual(r.target_depth,64)

    def test_direction_target_all_cuts_lengths_and_unknown_nested(self):
        leaf=target(direction_value=b'\xff',selector=b'\xff');value=direction()[:8]+leaf+bytes(4)+leaf+bytes(4)
        for n in range(len(value)):
            out=[]
            for data in (value,value[:n],value[:n]+b'\xff'*(len(value)-n)):
                r=Reader(data,'recursive-cut',n)
                with self.assertRaises(FrameError) as caught:r.direction_profile()
                self.assertLessEqual(r.pos,n);self.assertEqual(r.target_depth,0)
                self.assertFalse(any(v['kind']=='anonymous-direction-profile' and v['start']==0 for v in r.records))
                out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
            self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
        for count in (-2,0x7fffffff):
            bad=direction()[:8]+b'\x0d\xff'+struct.pack('<i',count);r=Reader(bad,'recursive-length')
            with self.assertRaises(FrameError) as caught:r.direction_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],10);self.assertEqual(caught.exception.diagnostic['actual'],count);self.assertEqual(r.target_depth,0)
        unknown=target(direction_value=b'\xff',selector=b'\x03\x17');r=Reader(direction()[:8]+unknown,'recursive-unknown')
        with self.assertRaises(Unsupported) as caught:r.direction_profile()
        self.assertEqual(caught.exception.diagnostic['category'],'nested-profile');self.assertEqual(r.target_depth,0)
        self.assertFalse(any(v['kind']=='anonymous-target-profile' for v in r.records))

    def test_postprocessor1_nullable_lists_shapes_and_all_byte_cuts(self):
        values=[b'\xff',b'\x01\xff',b'\xfa\x01\x00\xff']
        self.assertEqual(len(post1(None)),6);self.assertEqual(len(post1()),6)
        for wire in (b'\x01',b'\xfa\x01\x00'):
            for items in (None,(),(b'\xff',),(post1_shape(),),(b'\xff',post1_shape(),b'\xff')):
                values.append(post1(items,wire))
        for value in values:
            r=Reader(value+b'\xaa'*8,'post1');r.selector_postprocessor_profile()
            self.assertEqual(r.pos,len(value));self.assertEqual(r.postprocessor_depth,0)
            self.assertEqual(r.records[-1],dict(start=0,end=len(value),kind='anonymous-selector-postprocessor-profile'))
            for cut in range(len(value)):
                results=[]
                for data in (value,value[:cut],value[:cut]+b'\xff'*16):
                    q=Reader(data,'post1-cut',cut)
                    with self.assertRaises(FrameError) as caught:q.selector_postprocessor_profile()
                    self.assertLessEqual(q.pos,cut);self.assertEqual(q.postprocessor_depth,0)
                    self.assertFalse(any(v['kind']=='anonymous-selector-postprocessor-profile' for v in q.records))
                    results.append((caught.exception.diagnostic,q.pos,q.ranges,q.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        r=Reader(post1((post1_shape(),b'\x11')),'post1-partial')
        with self.assertRaises(FrameError):r.selector_postprocessor_profile()
        self.assertEqual(sum(v['kind']=='anonymous-shape-profile' for v in r.records),1)
        self.assertFalse(any(v['kind']=='anonymous-selector-postprocessor-profile' for v in r.records))

    def test_postprocessor1_malformed_counts_headers_and_parent_required_count(self):
        child=post1((post1_shape(),));q=Reader(child,'post1');q.selector_postprocessor_profile()
        for span in q.ranges:
            if span['kind'] not in ('member-header','count-i32'):continue
            for invalid in ((42,) if span['kind']=='member-header' else (-2,2147483647)):
                bad=bytearray(child);at=span['start']
                if span['kind']=='member-header':bad[at]=invalid
                else:struct.pack_into('<i',bad,at,invalid)
                r=Reader(bad,'post1-invalid')
                with self.assertRaises(FrameError) as caught:r.selector_postprocessor_profile()
                self.assertEqual(caught.exception.diagnostic['offset'],at)
                self.assertFalse(any(v['kind']=='anonymous-selector-postprocessor-profile' for v in r.records))
        for count in (-2,2147483647,1):
            r=Reader(b'\x01\x01'+struct.pack('<i',count),'post1-count')
            with self.assertRaises(FrameError) as caught:r.selector_postprocessor_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],2);self.assertEqual(r.pos,6)
        for items in (None,(),(b'\xff',),(post1_shape(),)):
            child=post1(items)
            for validator_count in (-1,0,1):
                parent=b'\x03\xff'+struct.pack('<i',1)+child+struct.pack('<i',validator_count)+b'\xff'*max(0,validator_count)
                r=Reader(parent+b'\xaa','post1-parent');r.selector_profile();self.assertEqual(r.pos,len(parent))
                for cut in range(len(parent)):
                    results=[]
                    for data in (parent,parent[:cut],parent[:cut]+b'\xff'*16):
                        r=Reader(data,'post1-parent-cut',cut)
                        with self.assertRaises(FrameError) as caught:r.selector_profile()
                        results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            parent=b'\x03\xff'+struct.pack('<i',1)+child+bytes(4)
            for k in range(1,5):
                r=Reader(parent[:-k],'post1-parent-tail')
                with self.assertRaises(FrameError) as caught:r.selector_profile()
                self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-4);self.assertEqual(r.pos,len(parent)-4)
                self.assertTrue(any(v['kind']=='anonymous-selector-postprocessor-profile' for v in r.records))
        for count in (-1,0):
            parent=b'\x03\xff'+struct.pack('<i',count)+bytes(4)
            for k in range(1,5):
                r=Reader(parent[:-k],'post1-empty-parent')
                with self.assertRaises(FrameError) as caught:r.selector_profile()
                self.assertEqual(caught.exception.diagnostic['offset'],6);self.assertEqual(r.pos,6)
        r=Reader(b'\x03\xff'+struct.pack('<i',1)+b'\xff','post1-reserve')
        with self.assertRaises(FrameError) as caught:r.selector_profile()
        self.assertEqual(caught.exception.diagnostic['offset'],2);self.assertEqual(r.pos,6)

    def test_postprocessor1_unknown_next_child_and_full_action_tails(self):
        value=post1((post1_shape(),))
        for unknown in (b'\x09',b'\xfa\x01\x01'):
            r=Reader(b'\x03\xff'+struct.pack('<i',2)+value+unknown+bytes(4),'post1-next')
            with self.assertRaises(Unsupported) as caught:r.selector_profile()
            self.assertEqual(r.pos,6+len(value));self.assertEqual(caught.exception.diagnostic['offset'],6+len(value))
            self.assertTrue(any(v['kind']=='anonymous-selector-postprocessor-profile' for v in r.records))
        for value in (post1(None),post1((b'\xff',),b'\xfa\x01\x00'),post1((post1_shape(),))):
            child=tag_ec(nested=target(selector=b'\x03\xff'+struct.pack('<i',1)+value+bytes(4)))
            full=prefix(sequence(child));self.assertEqual(event_prefix(full,source='post1-full')['status'],'supported-prefix')
            for cut in range(len(full)):
                row=event_prefix(full,source='post1-limit',limit=cut);self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='post1-limit',limit=cut))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(sequence(child)+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_postprocessor8_scalar_null_layers_and_bounded_cuts(self):
        values=[b'\xff',b'\x08\xff',b'\xfa\x08\x00\xff']
        for wire in (b'\x08',b'\xfa\x08\x00'):
            for scalar in (b'\xff',scalar_payload(None),scalar_payload(b''),scalar_payload(b'\xff\xfe\x80')):
                values.append(wire+b'\x02'+b'\xff'*4+scalar)
        for value in values:
            r=Reader(value+b'\xaa'*16,'post8');r.selector_postprocessor_profile()
            self.assertEqual(r.pos,len(value));self.assertEqual(r.postprocessor_depth,0)
            self.assertEqual(r.records[-1],dict(start=0,end=len(value),kind='anonymous-selector-postprocessor-profile'))
            for cut in range(len(value)):
                results=[]
                for data in (value,value[:cut],value[:cut]+b'\xff'*16):
                    r=Reader(data,'post8-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.selector_postprocessor_profile()
                    self.assertLessEqual(r.pos,cut);self.assertEqual(r.postprocessor_depth,0)
                    self.assertFalse(any(v['kind']=='anonymous-selector-postprocessor-profile' for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for wire in (b'\x08',b'\xfa\x08\x00'):
            for header in (0,1,3,250,254):
                r=Reader(wire+bytes([header])+bytes(20),'post8-header')
                with self.assertRaises(FrameError) as caught:r.selector_postprocessor_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='post8-header',offset=len(wire),expected=2,actual=header,category='member-count'))
            for length in (-2,2147483647):
                value=wire+b'\x02'+bytes(4)+b'\x03'+struct.pack('<i',length)+bytes(5)
                r=Reader(value,'post8-length')
                with self.assertRaises(FrameError) as caught:r.selector_postprocessor_profile()
                self.assertEqual(caught.exception.diagnostic['offset'],len(wire)+6)
                self.assertFalse(any(v['kind']=='anonymous-selector-postprocessor-profile' for v in r.records))
        for wire in (b'\x09',b'\xfa\x00\x01'):
            r=Reader(wire+bytes(20),'post8-unknown')
            with self.assertRaises(Unsupported):r.selector_postprocessor_profile()
            self.assertEqual(r.pos,0);self.assertEqual(r.records,[])

    def test_postprocessor8_parent_counts_reserve_and_next_element(self):
        for value in (b'\x08\x02'+bytes(4)+b'\xff',b'\x08\x02'+bytes(4)+scalar_payload(b''),b'\x08\xff',b'\xff'):
            for count in (-1,0,1):
                parent=b'\x03\xff'+struct.pack('<i',2)+value+b'\xff'+struct.pack('<i',count)+b'\xff'*max(0,count)
                r=Reader(parent+b'\xaa','post8-parent');r.selector_profile();self.assertEqual(r.pos,len(parent))
                for cut in range(len(parent)):
                    results=[]
                    for data in (parent,parent[:cut],parent[:cut]+b'\xff'*20):
                        r=Reader(data,'post8-parent-cut',cut)
                        with self.assertRaises(FrameError) as caught:r.selector_profile()
                        self.assertFalse(any(v['kind']=='anonymous-selector-profile' for v in r.records))
                        results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                    self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            raw=b'\x03\xff'+struct.pack('<i',2)+value+b'\x09'+bytes(4)
            r=Reader(raw,'post8-next')
            with self.assertRaises(Unsupported) as caught:r.selector_profile()
            self.assertEqual(r.pos,6+len(value));self.assertEqual(caught.exception.diagnostic['offset'],6+len(value))
            for count in (-2,2147483647):
                for offset in (2,6+len(value)):
                    raw=bytearray(b'\x03\xff'+struct.pack('<i',1)+value+bytes(4));struct.pack_into('<i',raw,offset,count)
                    r=Reader(raw,'post8-count')
                    with self.assertRaises(FrameError) as caught:r.selector_profile()
                    self.assertEqual(caught.exception.diagnostic['offset'],offset)
                    self.assertFalse(any(v['kind']=='anonymous-selector-profile' for v in r.records))

    def test_postprocessor8_action_tail_and_trailing_sequence(self):
        for value in (b'\x08\x02'+bytes(4)+scalar_payload(b'x'),b'\xfa\x08\x00\x02'+bytes(4)+b'\xff',b'\x08\xff'):
            child=tag_ec(nested=target(selector=b'\x03\xff'+struct.pack('<i',1)+value+bytes(4)));raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for cut in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:cut])
            full=prefix(raw)
            for cut in range(len(full)):
                row=event_prefix(full,source='post8-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='post8-limit',limit=cut))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            row=event_prefix(prefix(sequence(child,b'\x59')),source='post8-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
            self.assertEqual(row['diagnostic']['actual'],89)

    def test_validator2_two_raw_dwords_nulls_and_bounded_cuts(self):
        for value in (b'\x02\x02'+bytes(8),b'\xfa\x02\x00\x02'+b'\xff'*8,
                      b'\x02\x02'+bytes.fromhex('FFFE800012345678'),
                      b'\x02\xff',b'\xfa\x02\x00\xff',b'\xff'):
            r=Reader(value+b'\xaa'*12,'validator2');r.selector_validator_profile()
            self.assertEqual(r.pos,len(value))
            self.assertEqual(r.records,[dict(start=0,end=len(value),kind='anonymous-selector-validator-profile')])
            for cut in range(len(value)):
                results=[]
                for data in (value,value[:cut],value[:cut]+b'\xff'*16):
                    r=Reader(data,'validator2-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.selector_validator_profile()
                    self.assertLessEqual(r.pos,cut);self.assertEqual(r.records,[])
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for wire in (b'\x02',b'\xfa\x02\x00'):
            for header in (0,1,3,250,254):
                r=Reader(wire+bytes([header])+bytes(16),'validator2-header')
                with self.assertRaises(FrameError) as caught:r.selector_validator_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='validator2-header',offset=len(wire),expected=2,actual=header,category='member-count'))
                self.assertEqual(r.records,[])
            for n in range(4):
                r=Reader(wire+b'\x02'+b'\xff'*4+bytes(n),'validator2-second')
                with self.assertRaises(FrameError):r.selector_validator_profile()
                self.assertEqual(r.records,[])
        for wire in (b'\x03',b'\xfa\x00\x01'):
            r=Reader(wire+bytes(16),'validator2-unknown')
            with self.assertRaises(Unsupported):r.selector_validator_profile()
            self.assertEqual(r.pos,0);self.assertEqual(r.records,[])

    def test_validator2_parent_count_next_element_and_null_layers(self):
        for value in (b'\x02\x02'+bytes(8),b'\xfa\x02\x00\x02'+b'\xff'*8,b'\x02\xff',b'\xff'):
            parent=b'\x03\xff'+bytes(4)+struct.pack('<i',2)+value+b'\xff'
            r=Reader(parent+b'\xaa','validator2-parent');r.selector_profile();self.assertEqual(r.pos,len(parent))
            for cut in range(len(parent)):
                results=[]
                for raw in (parent,parent[:cut],parent[:cut]+b'\xff'*16):
                    r=Reader(raw,'validator2-parent-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.selector_profile()
                    self.assertFalse(any(v['kind']=='anonymous-selector-profile' for v in r.records))
                    results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            r=Reader(parent[:-1]+b'\x03','validator2-next')
            with self.assertRaises(Unsupported) as caught:r.selector_profile()
            self.assertEqual(r.pos,len(parent)-1)
            self.assertEqual(caught.exception.diagnostic['offset'],len(parent)-1)
            self.assertFalse(any(v['kind']=='anonymous-selector-profile' for v in r.records))
            for count in (-2,2147483647):
                raw=b'\x03\xff'+bytes(4)+struct.pack('<i',count)+value
                r=Reader(raw,'validator2-count')
                with self.assertRaises(FrameError) as caught:r.selector_profile()
                self.assertEqual(caught.exception.diagnostic['offset'],6)
                self.assertFalse(any(v['kind']=='anonymous-selector-profile' for v in r.records))

    def test_validator2_action_tail_and_trailing_sequence(self):
        for value in (b'\x02\x02'+bytes(8),b'\xfa\x02\x00\x02'+b'\xff'*8,b'\x02\xff'):
            child=tag_ec(nested=target(selector=b'\x03\xff'+bytes(4)+struct.pack('<i',1)+value));raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for cut in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:cut])
            full=prefix(raw)
            for cut in range(len(full)):
                row=event_prefix(full,source='validator2-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='validator2-limit',limit=cut))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            row=event_prefix(prefix(sequence(child,b'\x59')),source='validator2-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
            self.assertEqual(row['diagnostic']['actual'],89)

    def test_validator1_nested_settings_and_parent_continuation(self):
        for wire in (b'\x01',b'\xfa\x01\x00'):
            for settings in (b'\xff',finder14d(None,None),finder14d((),()),finder14d((None,b'',b'wire'),(0,0xffffffff))):
                for bits in (0,0xffffffff,0x80000000,0x7fc00000):
                    value=wire+b'\x02'+settings+struct.pack('<I',bits)
                    r=Reader(value+b'\xaa','validator1');r.selector_validator_profile();self.assertEqual(r.pos,len(value))
                    self.assertEqual(r.records[-1],dict(start=0,end=len(value),kind='anonymous-selector-validator-profile'))
                    child=tag_ec(nested=target(selector=b'\x03\xff'+bytes(4)+struct.pack('<i',1)+value));raw=sequence(child)
                    self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='validator1');self.assertEqual(row['diagnostic']['offset'],19+len(child))
                    self.assertEqual(row['diagnostic']['actual'],89);self.assertFalse(row['wholeSchemaExact'])
                    for tail in (b'\x00',b'\xff'):
                        with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_validator1_all_cuts_limits_nulls_and_required_dword(self):
        body=finder14d((None,b'wire'),(1,0xffffffff))+bytes(4)
        for value in (b'\x01\x02'+body,b'\xfa\x01\x00\x02'+body,b'\x01\xff',b'\xfa\x01\x00\xff',b'\x01\x02\xff'+bytes(4)):
            r=Reader(value,'validator1');r.selector_validator_profile();self.assertEqual(r.pos,len(value))
            for n in range(len(value)):
                out=[]
                for data in (value,value[:n],value[:n]+b'\xff'*(len(value)-n)):
                    r=Reader(data,'validator1-cut',n)
                    with self.assertRaises(FrameError) as caught:r.selector_validator_profile()
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v['kind']=='anonymous-selector-validator-profile' for v in r.records))
                    out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
        for n in range(4):
            r=Reader(b'\x01\x02\xff'+bytes(n),'validator1-tail')
            with self.assertRaises(FrameError) as caught:r.selector_validator_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],3)
            self.assertFalse(any(v['kind']=='anonymous-selector-validator-profile' for v in r.records))

    def test_validator1_bad_members_nested_counts_and_lengths(self):
        for wire in (b'\x01',b'\xfa\x01\x00'):
            for header in (0,1,3,254):
                r=Reader(wire+bytes([header]),'validator1-header')
                with self.assertRaises(FrameError) as caught:r.selector_validator_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='validator1-header',offset=len(wire),expected=2,actual=header,category='member-count'))
            for n in (-2,0x7fffffff):
                cases=((b'\x03'+struct.pack('<i',n)+bytes(9),len(wire)+2),
                       (b'\x03'+struct.pack('<i',1)+struct.pack('<i',n)+bytes(9),len(wire)+6),
                       (b'\x03'+bytes(8)+b'\x02'+bytes(4)+struct.pack('<i',n)+bytes(4),len(wire)+15))
                for settings,offset in cases:
                    r=Reader(wire+b'\x02'+settings,'validator1-count')
                    with self.assertRaises(FrameError) as caught:r.selector_validator_profile()
                    self.assertEqual(caught.exception.diagnostic['offset'],offset)
                    self.assertEqual(caught.exception.diagnostic['actual'],n)
                    self.assertFalse(any(v['kind']=='anonymous-selector-validator-profile' for v in r.records))

    def test_finder0_zero_header_null_variants_and_no_extra_read(self):
        for value in (b'\x00\x00',b'\xfa\x00\x00\x00',b'\x00\xff',b'\xfa\x00\x00\xff',b'\xff'):
            r=Reader(value+b'\xaa'*12,'finder0');r.selector_finder_profile()
            self.assertEqual(r.pos,len(value))
            self.assertEqual(r.records,[dict(start=0,end=len(value),kind='anonymous-selector-finder-profile')])
            for cut in range(len(value)):
                results=[]
                for data in (value,value[:cut],value[:cut]+b'\xff'*12):
                    r=Reader(data,'finder0-cut',cut)
                    with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                    self.assertLessEqual(r.pos,cut);self.assertEqual(r.records,[])
                    results.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
        for wire in (b'\x00',b'\xfa\x00\x00'):
            for header in (1,2,250,254):
                r=Reader(wire+bytes([header])+bytes(16),'finder0-header')
                with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='finder0-header',offset=len(wire),expected=0,actual=header,category='member-count'))
                self.assertEqual(r.records,[])
        for wire in (b'\x17',b'\xfa\x00\x01'):
            r=Reader(wire+bytes(16),'finder0-unknown')
            with self.assertRaises(Unsupported):r.selector_finder_profile()
            self.assertEqual(r.pos,0);self.assertEqual(r.records,[])

    def test_finder0_parent_counts_required_and_bounded(self):
        for finder in (b'\x00\x00',b'\xfa\x00\x00\x00',b'\x00\xff',b'\xff'):
            for post in (-1,0,1):
                for validator in (-1,0,1):
                    value=b'\x03'+finder+struct.pack('<i',post)+b'\xff'*max(0,post)+struct.pack('<i',validator)+b'\xff'*max(0,validator)
                    r=Reader(value,'finder0-parent');r.selector_profile();self.assertEqual(r.pos,len(value))
                    for cut in range(1+len(finder),len(value)):
                        results=[]
                        for raw in (value,value[:cut],value[:cut]+b'\xff'*16):
                            r=Reader(raw,'finder0-parent-cut',cut)
                            with self.assertRaises(FrameError) as caught:r.selector_profile()
                            self.assertFalse(any(v['kind']=='anonymous-selector-profile' for v in r.records))
                            results.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                        self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
            for offset in (1+len(finder),5+len(finder)):
                for count in (-2,2147483647):
                    value=bytearray(b'\x03'+finder+bytes(8));struct.pack_into('<i',value,offset,count)
                    r=Reader(value,'finder0-count')
                    with self.assertRaises(FrameError) as caught:r.selector_profile()
                    self.assertEqual(caught.exception.diagnostic['offset'],offset)
                    self.assertFalse(any(v['kind']=='anonymous-selector-profile' for v in r.records))

    def test_finder0_action_parent_tail_and_trailing_sequence(self):
        for finder in (b'\x00\x00',b'\xfa\x00\x00\x00',b'\x00\xff'):
            child=tag_ec(nested=target(selector=b'\x03'+finder+bytes(8)));raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for cut in range(len(raw)):
                with self.assertRaises(FrameError):sequence_frame(raw[:cut])
            full=prefix(raw)
            for cut in range(len(full)):
                row=event_prefix(full,source='finder0-limit',limit=cut)
                self.assertEqual(row['status'],'failed')
                self.assertEqual(row,event_prefix(full[:cut]+b'\xff'*(len(full)-cut),source='finder0-limit',limit=cut))
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
            row=event_prefix(prefix(sequence(child,b'\x59')),source='finder0-next')
            self.assertEqual(row['status'],'unsupported');self.assertEqual(row['diagnostic']['offset'],19+len(child))
            self.assertEqual(row['diagnostic']['actual'],89)

    def test_finder1_zero_members_and_parent_continuation(self):
        for wire in (b'\x01',b'\xfa\x01\x00'):
            for header in (b'\x00',b'\xff'):
                value=wire+header;r=Reader(value+b'\xaa','finder1');r.selector_finder_profile()
                self.assertEqual(r.pos,len(value));self.assertEqual(r.records,[dict(start=0,end=len(value),kind='anonymous-selector-finder-profile')])
                child=tag_ec(nested=target(selector=b'\x03'+value+bytes(8)));raw=sequence(child)
                self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
                row=event_prefix(prefix(sequence(child,b'\x59')),source='finder1')
                self.assertEqual(row['diagnostic']['offset'],19+len(child));self.assertEqual(row['diagnostic']['actual'],89)
                self.assertFalse(row['wholeSchemaExact'])
                for tail in (b'\x00',b'\xff'):
                    with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                    self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_finder1_every_cut_hard_limit_and_wrong_member_count(self):
        for value in (b'\x01\x00',b'\xfa\x01\x00\x00',b'\x01\xff',b'\xfa\x01\x00\xff'):
            for n in range(len(value)):
                out=[]
                for data in (value,value[:n],value[:n]+b'\xff'*(len(value)-n)):
                    r=Reader(data,'finder1-cut',n)
                    with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                    self.assertLessEqual(r.pos,n);self.assertEqual(r.records,[])
                    out.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
        for wire in (b'\x01',b'\xfa\x01\x00'):
            for header in (1,2,254):
                r=Reader(wire+bytes([header])+b'\x00'*16,'finder1-header')
                with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='finder1-header',offset=len(wire),expected=0,actual=header,category='member-count'))
                self.assertEqual(r.records,[])

    def test_finder16_independent_members_and_parent_continuation(self):
        shapes=(b'\xff',b'\x02'+scalar_payload(None)+scalar_payload(b'wire',128),b'\x02\xff\xff')
        for wire in (b'\x10',b'\xfa\x10\x00'):
            for v2 in shapes:
                for v3 in (b'\xff',b'\x03'+scalar_payload(b'')+b'\xff'+scalar_payload(None)):
                    value=wire+b'\x09'+scalar_payload(b'a')+v2+v3+scalar_payload(None)+b'\xff'+scalar_payload(b'last')+b'\xff\xff\xff\xff\x80\xff'
                    r=Reader(value+b'\xaa','finder16');r.selector_finder_profile();self.assertEqual(r.pos,len(value))
                    rec=next(v for v in r.records if v['kind']=='anonymous-vector2-payload')
                    self.assertEqual(rec['end']-rec['start'],len(v2))
                    child=tag_ec(nested=target(selector=b'\x03'+value+bytes(8)));raw=sequence(child)
                    self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='finder16');self.assertEqual(row['diagnostic']['offset'],19+len(child))
                    self.assertEqual(row['diagnostic']['actual'],89);self.assertFalse(row['wholeSchemaExact'])
                    for tail in (b'\x00',b'\xff'):
                        with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_finder16_every_cut_hard_limits_and_required_tail(self):
        body=scalar_payload(b'wire')+b'\x02'+scalar_payload(None)+scalar_payload(b'')+b'\x03\xff\xff\xff'+b'\xff'*3+bytes(6)
        for value in (b'\x10\x09'+body,b'\xfa\x10\x00\x09'+body,b'\x10\xff',b'\xfa\x10\x00\xff'):
            r=Reader(value,'finder16');r.selector_finder_profile();self.assertEqual(r.pos,len(value))
            for n in range(len(value)):
                out=[]
                for data in (value,value[:n],value[:n]+b'\xff'*(len(value)-n)):
                    r=Reader(data,'finder16-cut',n)
                    with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v['kind']=='anonymous-selector-finder-profile' for v in r.records))
                    out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])
        for n in (1,2):
            r=Reader(b'\x10\x09'+body[:-n],'finder16-tail')
            with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],2+len(body)-n)

    def test_finder16_headers_and_nested_lengths_fail_closed(self):
        for wire in (b'\x10',b'\xfa\x10\x00'):
            for header in (0,8,10,254):
                r=Reader(wire+bytes([header]),'finder16-header')
                with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='finder16-header',offset=len(wire),expected=9,actual=header,category='member-count'))
            for n in (-2,0x7fffffff):
                value=wire+b'\x09\xff\x02\xff\x03'+struct.pack('<i',n)
                r=Reader(value,'finder16-length')
                with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                self.assertEqual(caught.exception.diagnostic['offset'],len(wire)+5)
                self.assertFalse(any(v['kind'] in ('anonymous-vector2-payload','anonymous-selector-finder-profile') for v in r.records))

    def test_vector2_independent_nulls_headers_and_all_truncations(self):
        for value in (b'\xff',b'\x02\xff\xff',b'\x02'+scalar_payload(None)+scalar_payload(b'wire',255)):
            r=Reader(value+b'\xaa','vector2');r.vector2_payload();self.assertEqual(r.pos,len(value))
            for n in range(len(value)):
                r=Reader(value,'vector2',n)
                with self.assertRaises(FrameError):r.vector2_payload()
                self.assertFalse(any(v['kind']=='anonymous-vector2-payload' for v in r.records))
        for header in (0,1,3,254):
            r=Reader(bytes([header]),'vector2-header')
            with self.assertRaises(FrameError) as caught:r.vector2_payload()
            self.assertEqual(caught.exception.diagnostic,dict(source='vector2-header',offset=0,expected=2,actual=header,category='member-count'))

    def test_finder14_independent_vectors_and_parent_continuation(self):
        vectors=(b'\xff',b'\x03'+b'\xff'*3,b'\x03'+scalar_payload(None)+scalar_payload(b'')+scalar_payload(b'wire',128))
        for wire in (b'\x0e',b'\xfa\x0e\x00'):
            for first in vectors:
                for second in vectors:
                    value=wire+b'\x02'+first+second;r=Reader(value+b'\xaa','finder14');r.selector_finder_profile()
                    self.assertEqual(r.pos,len(value))
                    spans=[v for v in r.records if v['kind']=='anonymous-vector-payload']
                    self.assertEqual([(v['start'],v['end']) for v in spans],[(len(wire)+1,len(wire)+1+len(first)),(len(wire)+1+len(first),len(value))])
                    child=tag_ec(nested=target(selector=b'\x03'+value+bytes(8)));raw=sequence(child)
                    self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
                    row=event_prefix(prefix(sequence(child,b'\x59')),source='finder14')
                    self.assertEqual(row['diagnostic']['offset'],19+len(child));self.assertEqual(row['diagnostic']['actual'],89)
                    for tail in (b'\x00',b'\xff'):
                        with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_finder14_every_cut_and_hard_limits(self):
        v=b'\x03'+scalar_payload(b'wire')+b'\xff'+scalar_payload(None)
        for value in (b'\x0e\x02'+v+v,b'\xfa\x0e\x00\x02'+v+b'\xff',b'\x0e\xff',b'\xfa\x0e\x00\xff'):
            r=Reader(value,'finder14');r.selector_finder_profile();self.assertEqual(r.pos,len(value))
            for n in range(len(value)):
                out=[]
                for data in (value,value[:n],value[:n]+b'\xff'*(len(value)-n)):
                    r=Reader(data,'finder14-cut',n)
                    with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                    self.assertLessEqual(r.pos,n);self.assertFalse(any(v['kind']=='anonymous-selector-finder-profile' for v in r.records))
                    out.append((caught.exception.diagnostic,r.pos,r.ranges,r.records))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])

    def test_finder14_bad_header_lengths_and_second_vector_required(self):
        for wire in (b'\x0e',b'\xfa\x0e\x00'):
            for header in (0,1,3,254):
                r=Reader(wire+bytes([header]),'finder14-header')
                with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='finder14-header',offset=len(wire),expected=2,actual=header,category='member-count'))
            for second in (b'',b'\x02',b'\x03\x03'+struct.pack('<i',-2),b'\x03\x03'+struct.pack('<i',0x7fffffff),b'\x03'+scalar_payload()[:-1]):
                r=Reader(wire+b'\x02\xff'+second,'finder14-bad')
                with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                self.assertGreaterEqual(caught.exception.diagnostic['offset'],len(wire)+2)
                self.assertFalse(any(v['kind']=='anonymous-selector-finder-profile' for v in r.records))

    def test_finder21_zero_members_and_parent_continuation(self):
        for value in (b'\xff',b'\x15\x00',b'\x15\xff',b'\xfa\x15\x00\x00',b'\xfa\x15\x00\xff'):
            r=Reader(value+b'\xaa','finder21');r.selector_finder_profile()
            self.assertEqual(r.pos,len(value));self.assertEqual(r.records[-1],dict(start=0,end=len(value),kind='anonymous-selector-finder-profile'))
            child=tag_ec(nested=target(selector=b'\x03'+value+bytes(8)))
            raw=sequence(child);self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            row=event_prefix(prefix(sequence(child,b'\x59')),source='finder21')
            self.assertEqual(row['diagnostic']['offset'],19+len(child));self.assertEqual(row['diagnostic']['actual'],89)
            self.assertFalse(row['wholeSchemaExact'])
            for tail in (b'\x00',b'\xff'):
                with self.assertRaises(FrameError) as caught:sequence_frame(raw+tail)
                self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_finder21_every_cut_and_hard_limit_mutation(self):
        for value in (b'\x15\x00',b'\x15\xff',b'\xfa\x15\x00\x00',b'\xfa\x15\x00\xff'):
            for n in range(len(value)):
                out=[]
                for data in (value,value[:n],value[:n]+b'\xff'*(len(value)-n)):
                    r=Reader(data,'finder21-cut',n)
                    with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                    self.assertLessEqual(r.pos,n);self.assertEqual(r.records,[])
                    out.append((caught.exception.diagnostic,r.pos,r.ranges))
                self.assertEqual(out[0],out[1]);self.assertEqual(out[0],out[2])

    def test_finder21_wrong_member_count_stops_at_header(self):
        for wire in (b'\x15',b'\xfa\x15\x00'):
            for h in (1,3,254):
                r=Reader(wire+bytes([h])+bytes(32),'finder21-header')
                with self.assertRaises(FrameError) as caught:r.selector_finder_profile()
                self.assertEqual(caught.exception.diagnostic,dict(source='finder21-header',offset=len(wire),expected=0,actual=h,category='member-count'))
                self.assertEqual(r.records,[])

    def test_selector_finder_tag2_zero_members_and_null(self):
        for value in (b'\xff',b'\x02\x00',b'\x02\xff',b'\xfa\x02\x00\x00',b'\xfa\x02\x00\xff'):
            raw=sequence(tag_ec(nested=target(selector=b'\x03'+value+bytes(8))))
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(value=value,n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            with self.assertRaises(FrameError):sequence_frame(raw+b'x')
        for value in (b'\x17',b'\xfa\xff\x00'):
            reader=Reader(value,'finder.bin')
            with self.assertRaises(Unsupported) as caught:reader.selector_finder_profile()
            self.assertEqual(caught.exception.diagnostic['offset'],0)
            self.assertEqual(reader.pos,0)
        for value in (b'\x02\x01',b'\xfa\x02\x00\x03'):
            reader=Reader(value,'finder.bin')
            with self.assertRaises(FrameError) as caught:reader.selector_finder_profile()
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')
        raw=prefix(sequence(tag_ec(nested=target(selector=b'\x03\x02\x00'+bytes(8)))))
        for n in range(len(raw)):
            first=event_prefix(raw,source='finder-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertEqual(first,event_prefix(raw[:n]+b'\xff'*(len(raw)-n),source='finder-limit.bin',limit=n))

    def test_tag92_nested_boundaries_and_later_unknown(self):
        child=tag92();self.assertEqual(len(child),119)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='92.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],89)
        self.assertEqual(row['consumedEnd'],138)
        for a,b,kind in ((0,119,'union'),(17,28,'anonymous-scalar-bytes-profile'),
                         (32,74,'anonymous-input-profile'),(74,75,'anonymous-input-profile'),
                         (38,62,'anonymous-assignment-profile'),(62,63,'anonymous-assignment-profile')):
            expected=dict(start=19+a,end=19+b,kind=kind)
            if kind=='union':expected['tag']=146
            self.assertIn(expected,row['completedRecords'])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag92_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag92())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='92-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='92-limit.bin',limit=n))

    def test_tag92_bad_counts_and_headers(self):
        for at in (22,28,34,43,53,57,63,69,79,85,95,99,105,109):
            for value in (-2,2147483647):
                bad=bytearray(tag92());struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='92-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('92-count.bin',at+5,value,'count-bounds'))
        for at in (1,17,32,38):
            bad=bytearray(tag92());bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag92_null_and_empty_profiles(self):
        children=[b'\x92\xff']
        for count in (-1,0):
            children.append(b'\x92\x13'+bytes(15)+b'\xff'+struct.pack('<i',count)+bytes(4)+payload(None)+
                            b'\xff\x80'+struct.pack('<i',count)+bytes(5)+b'\xff')
            item=b'\x05\xfe'+struct.pack('<i',count)+payload(None)+payload(b'')+b'\x80'
            children.append(b'\x92\x13'+bytes(15)+b'\xff'+struct.pack('<i',1)+item+bytes(4)+payload(None)+
                            b'\xff\x80'+struct.pack('<i',count)+bytes(5)+b'\xff')
        for child in children:
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_tag56_member_one_records_and_later_unknown(self):
        child=tag56();self.assertEqual(len(child),58)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='56.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],89)
        self.assertEqual(row['consumedEnd'],19+58)
        self.assertIn(dict(start=19,end=77,kind='union',tag=86),row['completedRecords'])
        spans=[(r['start']-19,r['end']-19) for r in row['completedRecords'] if r['kind']=='anonymous-single-payload']
        self.assertEqual(spans,[(25,31),(31,32),(32,37)])
        self.assertIn(dict(start=60,end=77,kind='anonymous-query-profile'),row['completedRecords'])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag56_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag56())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='56-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='56-limit.bin',limit=n))

    def test_tag56_bad_counts_and_headers(self):
        good=tag56()
        for at in (15,21,26,33,46):
            for value in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='56-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('56-count.bin',at+5,value,'count-bounds'))
        for at in (1,25,32,41):
            bad=bytearray(good);bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag56_nulls_and_empty_lists(self):
        children=[b'\x56\xff']
        for count in (-1,0):
            for key in (None,b''):
                for query in (b'\xff',b'\x02'+bytes(4)+struct.pack('<i',count)):
                    children.append(b'\x56\x08'+bytes(13)+payload(key)+struct.pack('<i',count)+bytes(4)+query)
        children.append(b'\x56\x08'+bytes(13)+payload(None)+struct.pack('<i',1)+b'\x01'+payload(b'')+bytes(4)+b'\xff')
        for child in children:
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_b4_exact_nested_boundaries_and_later_unknown(self):
        child=tag_b4();self.assertEqual(len(child),63)
        row=event_prefix(prefix(sequence(child,b'\x59')),source='b4.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],89)
        self.assertEqual(row['consumedEnd'],19+63)
        records=row['completedRecords']
        self.assertIn(dict(start=19,end=82,kind='union',tag=180),records)
        self.assertIn(dict(start=19+16,end=19+56,kind='anonymous-finder-profile'),records)
        self.assertIn(dict(start=19+39,end=19+56,kind='anonymous-query-profile'),records)
        self.assertFalse(row['wholeSchemaExact'])

    def test_b4_truncations_trailing_and_anchor_limit(self):
        raw=sequence(tag_b4())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            first=event_prefix(full,source='b4-limit.bin',limit=n)
            self.assertEqual(first['status'],'failed')
            self.assertLessEqual(first['consumedEnd'],n)
            self.assertEqual(first,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='b4-limit.bin',limit=n))

    def test_b4_bad_counts_and_headers(self):
        good=tag_b4()
        for at in (17,21,27,31,44):
            for value in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='b4-count.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('b4-count.bin',at+5,value,'count-bounds'))
        for at in (1,16,39):
            bad=bytearray(good);bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_b4_null_and_empty_nested_collections(self):
        children=[b'\xb4\xff',tag_b4(finder=b'\xff')]
        for count in (-1,0):
            for query in (b'\xff',b'\x02'+bytes(4)+struct.pack('<i',count)):
                children.append(tag_b4(finder=b'\x03'+struct.pack('<i',count)+bytes(4)+query))
        for child in children:
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_normal_nested_ranges_and_explicit_opaque_tail(self):
        raw=sequence(action(sequence(b'\xff'),sequence(),b'\xff'))
        spans=sequence_frame(raw,source='normal.bin')
        self.assertEqual(spans[0]['start'],0)
        self.assertEqual(spans[-1]['end'],len(raw))
        for a,b in zip(spans,spans[1:]):self.assertEqual(a['end'],b['start'])
        data=prefix(raw);report=event_prefix(data+b'opaque',source='normal.bin',limit=len(data))
        self.assertEqual(report['status'],'supported-prefix')
        self.assertEqual(report['opaqueRemainderRange'],[len(data),len(data)+6])
        self.assertFalse(report['wholeSchemaExact'])
        self.assertTrue(any(r['kind']=='union' and r['tag']==201 for r in report['completedRecords']))

    def test_all_truncations_and_trailing_bytes_fail(self):
        raw=sequence(action())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:sequence_frame(raw[:n],source='cut.bin')
            self.assertEqual(caught.exception.diagnostic['source'],'cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'!',source='tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')

    def test_malformed_counts_headers_and_limits(self):
        for n in (-2,2147483647):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:
                sequence_frame(b'\x03'+struct.pack('<i',n)+bytes(2),source='count.bin')
            self.assertEqual(caught.exception.diagnostic['offset'],1)
            self.assertEqual(caught.exception.diagnostic['category'],'count-bounds')
        for raw in (b'\x02'+bytes(6),sequence(b'\xc9\x07'+bytes(14))):
            with self.assertRaises(FrameError):sequence_frame(raw)
        for limit in (-1,True,'1',100):
            with self.subTest(limit=limit),self.assertRaises(FrameError):event_prefix(bytes(5),source='limit.bin',limit=limit)

    def test_nulls_and_nonzero_bytes_are_not_strict_booleans(self):
        for raw in (b'\xff',sequence(b'\xff'),sequence(b'\xc9\xff'),b'\x03'+struct.pack('<i',-1)+b'\xfe\x02',sequence(tail=b'\xff\x80')):
            with self.subTest(raw=raw):self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))

    def test_unknown_union_does_not_borrow_legacy_alias_or_search(self):
        for tag in (0xC0,0x59):
            raw=prefix(sequence(bytes([tag])+action()))
            row=event_prefix(raw,source='unknown.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['actual'],tag)
            self.assertEqual(row['consumedEnd'],19)
            self.assertEqual(row['opaqueRemainderRange'],[19,len(raw)])
            self.assertEqual(row['completedRecords'],[])
            with self.assertRaises(Unsupported):sequence_frame(sequence(bytes([tag])))

    def test_tag76_multiple_pairs_nested_in_ifelse_and_record_bounds(self):
        child=tag76(pair(b'skillId',b'',1),pair(b'',b'example'),pair(None,b'\xff\xfe',255))
        raw=prefix(sequence(action(sequence(child),sequence(),b'\xff')))
        row=event_prefix(raw+b'opaque',source='pair.bin',limit=len(raw))
        self.assertEqual(row['status'],'supported-prefix')
        self.assertEqual(row['opaqueRemainderRange'],[len(raw),len(raw)+6])
        unions=[r for r in row['completedRecords'] if r['kind']=='union']
        self.assertEqual([r['tag'] for r in unions],[118,201])
        records=[r for r in row['completedRecords'] if r['kind']=='anonymous-paired-payload']
        self.assertEqual(len(records),3)
        self.assertTrue(all(unions[0]['start']<r['start']<r['end']<=unions[0]['end'] for r in records))
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(row['ranges'],row['ranges'][1:])))

    def test_tag76_every_truncation_trailing_and_hard_limit(self):
        raw=sequence(tag76(pair(b'a',b'bc'),pair(b'def',b'g')))
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError):sequence_frame(raw[:n],source='pair-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='pair-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            self.assertEqual(event_prefix(full,source='bounded.bin',limit=n),
                event_prefix(full[:n]+b'\xff'*(len(full)-n),source='bounded.bin',limit=n))

    def test_tag76_malformed_counts_lengths_and_headers(self):
        good=bytearray(tag76(pair(b'a',b'bc')))
        for offset in (15,20,26):
            for value in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,offset,value)
                with self.subTest(offset=offset,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='bad-pair.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                    ('bad-pair.bin',offset+5,value,'count-bounds'))
        for offset in (1,19):
            bad=bytearray(good);bad[offset]=4
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad))
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag76_nulls_empty_and_stop_after_complete_record(self):
        for child in (b'\x76\xff',tag76(),tag76(b'\xff'),tag76(pair(None,None)),
                      b'\x76\x05'+bytes(13)+struct.pack('<i',-1)):
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        row=event_prefix(prefix(sequence(tag76(pair()),b'\xed')),source='next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],237)
        self.assertTrue(any(r.get('tag')==118 for r in row['completedRecords']))

    def test_ec_nested_ranges_and_opaque_remainder(self):
        child=tag_ec()
        raw=prefix(sequence(action(sequence(child),sequence(),b'\xff')))
        row=event_prefix(raw+b'opaque',source='ec.bin',limit=len(raw))
        self.assertEqual(row['status'],'supported-prefix')
        self.assertEqual(row['opaqueRemainderRange'],[len(raw),len(raw)+6])
        records=row['completedRecords']
        union=next(r for r in records if r.get('tag')==236)
        self.assertEqual(union['end']-union['start'],len(child))
        for kind in ('direction-profile','target-profile','selector-profile','scalar-payload'):
            record=next(r for r in records if r['kind']=='anonymous-'+kind)
            self.assertTrue(union['start']<record['start']<record['end']<=union['end'])
        self.assertFalse(row['wholeSchemaExact'])
        sequence_frame(sequence(child))  # Includes non-UTF8 bytes and NaN bits.

    def test_ec_every_truncation_trailing_and_hard_limit(self):
        raw=sequence(tag_ec())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:
                sequence_frame(raw[:n],source='ec-cut.bin')
            self.assertEqual(caught.exception.diagnostic['source'],'ec-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='ec-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            bounded=event_prefix(full,source='ec-bound.bin',limit=n)
            self.assertEqual(bounded['status'],'failed')
            self.assertLessEqual(bounded['consumedEnd'],n)
            self.assertEqual(bounded,
                event_prefix(full[:n]+b'\xff'*(len(full)-n),source='ec-bound.bin',limit=n))

    def test_ec_malformed_lengths_and_member_headers(self):
        raw=prefix(sequence(tag_ec()))
        valid=event_prefix(raw,source='ec-bad.bin')
        lengths=[r['start'] for r in valid['ranges'] if r['kind']=='count-i32']
        for at in lengths:
            for n in (-2,2147483647):
                bad=bytearray(raw);struct.pack_into('<i',bad,at,n)
                row=event_prefix(bad,source='ec-bad.bin')
                with self.subTest(at=at,n=n):
                    self.assertEqual(row['status'],'failed')
                    self.assertEqual(row['diagnostic']['offset'],at)
                    self.assertEqual(row['diagnostic']['actual'],n)
                    self.assertEqual(row['diagnostic']['category'],'count-bounds')
        for r in valid['ranges']:
            if r['kind']!='member-header':continue
            bad=bytearray(raw);bad[r['start']]=42
            row=event_prefix(bad,source='ec-header.bin')
            self.assertEqual(row['status'],'failed')
            self.assertEqual(row['diagnostic']['offset'],r['start'])

    def test_ec_null_variants_and_unproven_profiles(self):
        for child in (b'\xec\xff',tag_ec(nested=b'\xff',value=b'\xff',key=None),
                      tag_ec(nested=target(selector=b'\xff',direction_value=b'\xff'))):
            self.assertEqual(sequence_frame(sequence(child))[-1]['end'],len(sequence(child)))
        for nested in (target(selector=b'\x03\x17'+bytes(8)),
                       target(selector=b'\x03\xff'+struct.pack('<ii',1,0))):
            row=event_prefix(prefix(sequence(tag_ec(nested=nested))),source='ec-unsupported.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==236 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(tag_ec(),b'\x59')),source='ec-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],89)
        self.assertTrue(any(r.get('tag')==236 for r in row['completedRecords']))

    def test_tag50_ordered_pair_and_completed_record(self):
        child=tag50()
        raw=prefix(sequence(action(sequence(child),sequence(tag_ec()),b'\xff')))
        row=event_prefix(raw+b'opaque',source='50.bin',limit=len(raw))
        self.assertEqual(row['status'],'supported-prefix')
        union=next(r for r in row['completedRecords'] if r.get('tag')==80)
        self.assertEqual(union['end']-union['start'],len(child))
        items=[r for r in row['completedRecords'] if r['kind']=='anonymous-scalar-payload'
               and union['start']<r['start']<union['end']]
        self.assertEqual([(r['start'],r['end']) for r in items],
                         [(union['start']+19,union['start']+31),(union['start']+31,union['end'])])
        self.assertEqual(row['opaqueRemainderRange'],[len(raw),len(raw)+6])
        self.assertFalse(row['wholeSchemaExact'])

    def test_tag50_all_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag50())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:
                sequence_frame(raw[:n],source='50-cut.bin')
            self.assertEqual(caught.exception.diagnostic['source'],'50-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='50-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            row=event_prefix(full,source='50-bound.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='50-bound.bin',limit=n))

    def test_tag50_malformed_lengths_and_headers(self):
        good=tag50()
        # Independently calculated positions, not derived from parser ranges.
        for at in (20,32):
            for n in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,at,n)
                with self.subTest(at=at,n=n),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='50-length.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('50-length.bin',at+5,n,'count-bounds'))
        for at in (1,19,31):
            bad=bytearray(good);bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='50-header.bin')
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag50_nulls_empty_and_next_unknown(self):
        for child in (b'\x50\xff',tag50(b'\xff',b'\xff'),
                      tag50(scalar_payload(b''),scalar_payload(None)),
                      tag50(b'\xff',scalar_payload()),tag50(scalar_payload(),b'\xff')):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
        child=tag50()
        row=event_prefix(prefix(sequence(child,b'\x59')),source='50-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],89)
        self.assertEqual(row['consumedEnd'],19+len(child))
        self.assertTrue(any(r.get('tag')==80 for r in row['completedRecords']))

    def test_extended_tag_and_member8_record_ranges(self):
        child=tag11f()
        self.assertEqual(len(child),52)
        raw=prefix(sequence(action(sequence(child),b'\xff',sequence())))
        row=event_prefix(raw+b'opaque',source='11f.bin',limit=len(raw))
        self.assertEqual(row['status'],'supported-prefix')
        union=next(r for r in row['completedRecords'] if r.get('tag')==287)
        self.assertEqual(union['end']-union['start'],52)
        tag=next(r for r in row['ranges'] if r['start']==union['start'])
        self.assertEqual(tag,dict(start=union['start'],end=union['start']+3,kind='union-tag'))
        nested=[r for r in row['completedRecords'] if r['kind'] in ('anonymous-paired-payload','anonymous-scalar-payload')
                and union['start']<r['start']<union['end']]
        self.assertEqual([(r['start']-union['start'],r['end']-union['start']) for r in nested],
                         [(17,31),(31,41),(42,52)])
        self.assertEqual(row['opaqueRemainderRange'],[len(raw),len(raw)+6])
        self.assertFalse(row['wholeSchemaExact'])

    def test_extended_tag_truncation_and_unresolved_values(self):
        for wire in (b'\xfa',b'\xfa\x1f'):
            reader=Reader(wire,'tag-cut.bin')
            with self.assertRaises(FrameError) as caught:reader.action(0)
            self.assertEqual(caught.exception.diagnostic['category'],'truncated')
            self.assertEqual(caught.exception.diagnostic['offset'],0)
            self.assertEqual(reader.pos,0)
        for tag in (0,250,255,415,416,65535):
            wire=b'\xfa'+struct.pack('<H',tag)
            row=event_prefix(prefix(sequence(wire+tag11f())),source='unknown-u16.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['actual'],tag)
            self.assertEqual(row['consumedEnd'],19)
            self.assertEqual(row['completedRecords'],[])
        # The selected helper does not impose a minimum u16 value after FA.
        for child in (tag50(),tag_ec(),tag76(),action()):
            expanded=b'\xfa'+struct.pack('<H',child[0])+child[1:]
            row=event_prefix(prefix(sequence(expanded)),source='wide-short.bin')
            self.assertEqual(row['status'],'supported-prefix')
            self.assertTrue(any(r.get('tag')==child[0] for r in row['completedRecords']))
        for lead in (251,252,253,254):
            row=event_prefix(prefix(sequence(bytes([lead]))),source='reserved.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['actual'],lead)

    def test_tag11f_all_truncations_trailing_and_hard_limit(self):
        raw=sequence(tag11f())
        for n in range(len(raw)):
            with self.subTest(n=n),self.assertRaises(FrameError) as caught:
                sequence_frame(raw[:n],source='11f-cut.bin')
            self.assertEqual(caught.exception.diagnostic['source'],'11f-cut.bin')
        with self.assertRaises(FrameError) as caught:sequence_frame(raw+b'x',source='11f-tail.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'trailing-byte')
        full=prefix(raw)
        for n in range(len(full)):
            row=event_prefix(full,source='11f-bound.bin',limit=n)
            self.assertEqual(row['status'],'failed')
            self.assertLessEqual(row['consumedEnd'],n)
            self.assertEqual(row,event_prefix(full[:n]+b'\xff'*(len(full)-n),source='11f-bound.bin',limit=n))

    def test_tag11f_malformed_lengths_and_headers(self):
        good=tag11f()
        for at in (18,26,32,43,48):
            for value in (-2,2147483647):
                bad=bytearray(good);struct.pack_into('<i',bad,at,value)
                with self.subTest(at=at,value=value),self.assertRaises(FrameError) as caught:
                    sequence_frame(sequence(bad),source='11f-length.bin')
                d=caught.exception.diagnostic
                self.assertEqual((d['source'],d['offset'],d['actual'],d['category']),
                                 ('11f-length.bin',at+5,value,'count-bounds'))
        for at in (3,17,31,42):
            bad=bytearray(good);bad[at]=42
            with self.assertRaises(FrameError) as caught:sequence_frame(sequence(bad),source='11f-header.bin')
            self.assertEqual(caught.exception.diagnostic['offset'],at+5)
            self.assertEqual(caught.exception.diagnostic['category'],'member-count')

    def test_tag11f_null_variants_and_later_unknown(self):
        for child in (b'\xfa\x1f\x01\xff',tag11f(b'\xff',b'\xff',b'\xff'),
                      tag11f(pair(None,None),scalar_payload(b''),pair(b'',b''))):
            raw=sequence(child)
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
        child=tag11f()
        row=event_prefix(prefix(sequence(child,b'\xfa\xa0\x01')),source='11f-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],416)
        self.assertEqual(row['consumedEnd'],19+len(child))
        self.assertTrue(any(r.get('tag')==287 for r in row['completedRecords']))

    def test_suffix_cannot_supply_missing_nested_bytes(self):
        raw=prefix(sequence(action()))
        for n in range(1,len(raw)):
            first=event_prefix(raw,source='bounded.bin',limit=n)
            second=event_prefix(raw[:n]+b'\xff'*(len(raw)-n),source='bounded.bin',limit=n)
            self.assertEqual(first,second)

    def test_depth_limit_and_diagnostics(self):
        raw=sequence()
        for _ in range(66):raw=sequence(action(raw,b'\xff',b'\xff'))
        with self.assertRaises(Unsupported) as caught:sequence_frame(raw,source='deep.bin')
        self.assertEqual(caught.exception.diagnostic['category'],'depth-limit')
        row=event_prefix(b'\x1e'+struct.pack('<i',-1),source='map.bin')
        self.assertEqual(row['status'],'failed')
        self.assertEqual(set(row['diagnostic']),{'source','offset','expected','actual','category'})


if __name__=='__main__':unittest.main()
