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


def effect85():
    return (b'\x55'+
            bytes(4) + bytes(4) + bytes(4) + bytes(1) + bytes(1) + bytes(4) + bytes(4) + bytes(4) +
            bytes(4) + bytes(8) + bytes(4) + scalar_payload(None) + payload(b"fx") + bytes(4) + bytes(1) + bytes(4) +
            bytes(1) + bytes(4) + bytes(4) + bytes(1) + bytes(1) + bytes(4) + bytes(1) + bytes(1) +
            bytes(4) + bytes(1) + bytes(1) + bytes(1) + bytes(1) + bytes(1) + bytes(1) + scalar_payload(None) +
            bytes(4) + bytes(1) + bytes(4) + payload(b"fx") + bytes(4) + bytes(1) + bytes(4) + bytes(4) +
            bytes(4) + bytes(4) + bytes(1) + bytes(12) + b"\x03"+scalar_payload(None)*3 + bytes(4) + bytes(4) + bytes(1) +
            bytes(1) + bytes(4) + bytes(4) + bytes(4) + bytes(1) + bytes(4) + bytes(4) + bytes(12) +
            b"\x03"+scalar_payload(None)*3 + bytes(1) + bytes(12) + b"\x03"+scalar_payload(None)*3 + bytes(1) + bytes(4) + bytes(1) + bytes(1) +
            bytes(1) + bytes(4) + bytes(4) + bytes(1) + bytes(1) + bytes(1) + bytes(1) + bytes(1) +
            bytes(1) + bytes(1) + bytes(1) + bytes(1) + bytes(4) + bytes(1) + bytes(1) + bytes(4) +
            bytes(4) + bytes(4) + bytes(4) + payload(b"fx") + bytes(1))


def damage33(calc=b'\x03\x04'+scalar_payload(None)+bytes(4)+scalar_payload(None)+bytes(4),effect=None):
    return (b'\x21\xfe\x80'+calc+scalar_payload(None)+b'\xff'+bytes(4)+bytes(4)+bytes(8)+bytes(8)+
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


class BuffActionsTests(unittest.TestCase):
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
        # The three unit lists and terrain-effect array have no positive element
        # profile; an otherwise bounded positive count must stay unsupported.
        payload_starts={r['start'] for r in good['completedRecords'] if r['kind']=='anonymous-byte-payload'}
        targets=[r for r in good['completedRecords'] if r['kind']=='anonymous-target-profile']
        for span in good['ranges']:
            if span['kind']!='count-i32' or span['start'] in payload_starts or raw[span['start']:span['end']]!=bytes(4):continue
            if any(r['start']<=span['start']<r['end'] for r in targets):continue
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
        for nested in (target(selector=b'\x03\xfe'+bytes(8)),
                       target(direction_value=direction().replace(b'\xff',b'\x0d',1))):
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

    def test_tag78_recursive_target_remains_unsupported(self):
        bad_direction=bytearray(direction());bad_direction[8]=13
        child=tag78(nested=target(direction_value=bad_direction))
        row=event_prefix(prefix(sequence(child)),source='78-gap.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['category'],'nested-profile')
        self.assertEqual(row['diagnostic']['actual'],13)
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
            bad=target(selector=b'\x03\x10');good_target=target()
            child=tag7e(bad,good_target) if first_gap else tag7e(good_target,bad)
            row=event_prefix(prefix(sequence(child)),source='7e-gap')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual((row['diagnostic']['category'],row['diagnostic']['actual']),('nested-profile',16))
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
        child=tag16b(scalar_payload(b'x'),target(selector=b'\x03\x10'))
        row=event_prefix(prefix(sequence(child)),source='16b-gap')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual((row['diagnostic']['category'],row['diagnostic']['actual']),('nested-profile',16))
        self.assertEqual(row['consumedEnd'],row['diagnostic']['offset'])
        self.assertFalse(any(r.get('tag')==363 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(b'\x6b'+tag16b()[3:])),source='16b-short')
        self.assertEqual((row['diagnostic']['offset'],row['diagnostic']['actual'],row['diagnostic']['category']),(19,107,'union-tag'))

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
        self.assertEqual(row['diagnostic'],dict(source='6a-other',offset=19,expected='supported current union tag',actual=107,category='union-tag'))

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
        row=event_prefix(prefix(sequence(tagbd(sequence(b'\x27')))),source='bd-child')
        self.assertEqual(row['diagnostic'],dict(source='bd-child',offset=39,expected='supported current union tag',actual=39,category='union-tag'))
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
        row=event_prefix(prefix(sequence(child,b'\x5c')),source='57.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],92)
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

    def test_selector_finder_tag2_zero_members_and_null(self):
        for value in (b'\xff',b'\x02\x00',b'\x02\xff',b'\xfa\x02\x00\x00',b'\xfa\x02\x00\xff'):
            raw=sequence(tag_ec(nested=target(selector=b'\x03'+value+bytes(8))))
            self.assertEqual(sequence_frame(raw)[-1]['end'],len(raw))
            for n in range(len(raw)):
                with self.subTest(value=value,n=n),self.assertRaises(FrameError):sequence_frame(raw[:n])
            with self.assertRaises(FrameError):sequence_frame(raw+b'x')
        for value in (b'\x01',b'\xfa\xff\x00'):
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
        row=event_prefix(prefix(sequence(child,b'\x51')),source='b4.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],81)
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
        for tag in (0xC0,0x40,0x71):
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
        for nested in (target(selector=b'\x03\x00'+bytes(8)),
                       target(selector=b'\x03\xff'+struct.pack('<ii',1,0)),
                       target(direction_value=direction().replace(b'\xff',b'\x0d',1))):
            row=event_prefix(prefix(sequence(tag_ec(nested=nested))),source='ec-unsupported.bin')
            self.assertEqual(row['status'],'unsupported')
            self.assertEqual(row['diagnostic']['category'],'nested-profile')
            self.assertFalse(any(r.get('tag')==236 for r in row['completedRecords']))
        row=event_prefix(prefix(sequence(tag_ec(),b'\x51')),source='ec-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],81)
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
        row=event_prefix(prefix(sequence(child,b'\x51')),source='50-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],81)
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
        for tag in (0,250,255,288,415,416,65535):
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
        row=event_prefix(prefix(sequence(child,b'\xfa\x20\x01')),source='11f-next.bin')
        self.assertEqual(row['status'],'unsupported')
        self.assertEqual(row['diagnostic']['actual'],288)
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
