"""Anonymous BuffData event-prefix framing; no legacy union-tag aliases."""
import struct


class FrameError(ValueError):
    def __init__(self, source, offset, expected, actual, category='malformed'):
        self.diagnostic=dict(source=source,offset=offset,expected=expected,actual=actual,category=category)
        super().__init__(f'{source}: offset={offset} expected={expected!r} actual={actual!r}')


class Unsupported(FrameError):
    pass


class Reader:
    def __init__(self,data,source,limit=None):
        self.data=data;self.source=source;self.pos=0;self.ranges=[];self.records=[]
        self.postprocessor_depth=0
        self.limit=len(data) if limit is None else limit
        if type(self.limit) is not int or not 0<=self.limit<=len(data):
            raise FrameError(source,0,'limit within file',self.limit)

    def take(self,n,kind):
        if type(n) is not int or n<0 or n>self.limit-self.pos:
            raise FrameError(self.source,self.pos,{'bytes':n},{'remaining':self.limit-self.pos},'truncated')
        start=self.pos;self.pos+=n
        if n:self.ranges.append(dict(start=start,end=self.pos,kind=kind))
        return self.data[start:self.pos]

    def peek(self):
        if self.pos==self.limit:raise FrameError(self.source,self.pos,'one byte','EOF','truncated')
        return self.data[self.pos]

    def header(self,expected):
        actual=self.peek()
        if actual!=expected:raise FrameError(self.source,self.pos,expected,actual,'member-count')
        self.take(1,'member-header')

    def count(self,minimum,reserve=0,nullable=False):
        start=self.pos;n=struct.unpack('<i',self.take(4,'count-i32'))[0]
        if n==-1 and nullable:return n
        maximum=max(0,(self.limit-self.pos-reserve)//minimum)
        if n<0 or n>maximum:
            raise FrameError(self.source,start,{'minimum':-1 if nullable else 0,'maximum':maximum},n,'count-bounds')
        return n

    def sequence(self,depth=0):
        start=self.pos
        self._sequence(depth)
        self.records.append(dict(start=start,end=self.pos,kind='sequence'))

    def _sequence(self,depth):
        if depth>64:raise Unsupported(self.source,self.pos,'nesting <= 64',depth,'depth-limit')
        if self.peek()==255:self.take(1,'null-sequence');return
        self.header(3)
        count=self.count(1,reserve=2,nullable=True)
        for _ in range(max(0,count)):self.action(depth+1)
        self.take(1,'anonymous-nonzero-byte')
        self.take(1,'anonymous-nonzero-byte')

    def action(self,depth):
        start=self.pos
        lead=self.peek();width=3 if lead==250 else 1
        if width>self.limit-self.pos:
            raise FrameError(self.source,self.pos,{'bytes':width},{'remaining':self.limit-self.pos},'truncated')
        tag=struct.unpack_from('<H',self.data,self.pos+1)[0] if lead==250 else lead
        self._action(depth,tag,width)
        self.records.append(dict(start=start,end=self.pos,kind='union',tag=tag))

    def _action(self,depth,tag,width):
        # FA carries an unsigned little-endian tag, not a child-object header.
        # Keep unknown tags at their first byte; never search for a later tag.
        if tag==255 and width==1:self.take(1,'null-union');return
        # FC/FD/FE are authenticated only in their extended encodings.
        if (width==1 and tag>=251) or tag not in (201,118,236,80,287,180,86,146,87,91,60,120,178,104,129,88,2,154,162,101,361,343,110,254,150,253,124,182,128,366,123,109,310,355,105,68,271,155,197,281,10,122,136,72,90,196,325,222,189,106,36,363,126,53,234,97,63,333,115,93,66,39,149,116,365,352,137,369,306,212,96,294,28,6,322,3,81,94,315,132,372,65,169,98,316,144,187,11,43,277,337,319,320,152,374,147,373,252,131,314,134,99,107,119,392,64,391,313,394,309,290,92,387,47,348,367,5,58,76,336,167,414,8,288,159,27,135):raise Unsupported(self.source,self.pos,'supported current union tag',tag,'union-tag')
        self.take(width,'union-tag')
        if self.peek()==255:self.take(1,'null-wrapper');return
        self.header({201:8,118:5,236:10,80:7,287:8,180:13,86:8,146:19,87:8,91:6,60:10,120:9,178:18,104:5,129:9,88:8,2:12,154:11,162:18,101:8,361:38,343:11,110:8,254:20,150:9,253:4,124:6,182:6,128:6,366:13,123:7,109:6,310:9,355:8,105:6,68:6,271:5,155:9,197:16,281:22,10:7,122:6,136:5,72:6,90:6,196:8,325:6,222:37,189:6,106:8,36:12,363:6,126:6,53:15,234:7,97:10,63:7,333:9,115:4,93:5,66:10,39:10,149:8,116:5,365:8,352:10,137:6,369:13,306:6,212:8,96:6,294:5,28:15,6:5,322:11,3:9,81:6,94:5,315:6,132:6,372:11,65:6,169:28,98:4,316:4,144:8,187:6,11:8,43:5,277:16,337:8,319:7,320:7,152:9,374:7,147:19,373:5,252:6,131:8,314:6,134:9,99:5,107:7,119:5,392:8,64:6,391:9,313:6,394:7,309:7,290:5,92:6,387:16,47:10,348:5,367:7,5:5,58:7,76:12,336:6,167:11,414:23,8:50,288:8,159:9,27:17,135:5}[tag])
        self.take(1,'anonymous-nonzero-byte')
        for _ in range(3):self.take(4,'anonymous-scalar32')
        if tag==135:
            for _ in range(max(0,self.count(1,nullable=True))):self.sequence(depth+1)
            return
        if tag==27:
            self.target_profile();self.scalar_payload();self.scalar_payload()
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.direction_profile();self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();return
        if tag==159:
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.target_profile();self.target_profile();self.query_profile();return
        if tag==288:
            self.scalar_payload();self.scalar_payload()
            self.take(4,'anonymous-scalar32');self.byte_payload();return
        if tag==8:
            for _ in range(2):self.vector_payload()
            for _ in range(4):self.scalar_payload()
            for _ in range(2):
                self.curve_profile();self.take(4,'anonymous-scalar32');self.scalar_payload()
            self.take(4,'anonymous-raw4');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.byte_payload();self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=31,nullable=True))):self.counted_payload_scalars_profile()
            self.curve_profile();self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=25,nullable=True))):self.counted_payload_scalars_profile()
            self.vector_payload()
            for _ in range(6):self.scalar_payload()
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.curve_profile();self.vector_payload()
            for _ in range(13):self.take(1,'anonymous-nonzero-byte')
            return
        if tag==414:
            self.curve_profile();self.take(4,'anonymous-scalar32');self.take(4,'anonymous-raw4')
            self.curve_profile();self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(4,'anonymous-raw4')
            self.byte_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            for _ in range(max(0,self.count(4,reserve=6,nullable=True))):self.byte_payload()
            for _ in range(6):self.take(1,'anonymous-nonzero-byte')
            return
        if tag==167:
            self.take(1,'anonymous-nonzero-byte')
            self.byte_profile();self.scalar_pair_flags_profile();self.query_profile()
            self.byte_profile();self.scalar_pair_flags_profile()
            self.take(1,'anonymous-nonzero-byte');return
        if tag==336:
            self.scalar_payload();self.take(1,'anonymous-nonzero-byte');return
        if tag==76:
            self.scalar_payload();self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(4,reserve=1,nullable=True))):self.byte_payload()
            self.target_profile();return
        if tag==367:
            self.take(1,'anonymous-nonzero-byte');self.target_profile();self.scalar_payload()
            return
        if tag==47:
            self.sequence(depth);self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.target_profile();self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32');return
        if tag==387:
            self.byte_payload();self.scalar_payload()
            for _ in range(max(0,self.count(1,reserve=21,nullable=True))):self.target_profile()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=16,nullable=True))):self.target_profile()
            self.scalar_payload()
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.curve_profile();self.take(1,'anonymous-nonzero-byte');self.take(1,'anonymous-nonzero-byte');return
        if tag==290:
            for _ in range(max(0,self.count(1,nullable=True))):self.scalar_target_payload_profile()
            return
        if tag==309:
            self.single_payload();self.target_profile();self.byte_payload();return
        if tag==394:
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.scalar_payload();return
        if tag==313:
            self.byte_payload();self.target_profile();return
        if tag==391:
            for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.assignment_profile()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(3):self.target_profile()
            return
        if tag==64:
            self.take(4,'anonymous-scalar32');self.tag_elements();return
        if tag==392:
            self.paired_payload();self.scalar_payload();self.target_profile();self.target_profile();return
        if tag==119:
            for _ in range(max(0,self.count(4,nullable=True))):self.take(4,'anonymous-scalar32')
            return
        if tag==107:
            for _ in range(3):self.byte_payload()
            return
        if tag==99:self.query_profile();return
        if tag==134:
            self.scalar_payload();self.byte_payload();self.scalar_payload();self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');return
        if tag==131:
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.scalar_payload();return
        if tag==252:self.target_profile();self.scalar_payload();return
        if tag==373:self.byte_payload();return
        if tag==374:
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();start=self.pos
            for _ in range(max(0,self.count(1,nullable=True))):self.sequence_scalar_profile(depth)
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-sequence-scalar-list'));return
        if tag==152:
            self.byte_payload();self.curve_profile();self.scalar_payload()
            self.byte_payload();self.take(1,'anonymous-nonzero-byte');return
        if tag==320:
            self.byte_payload();self.target_profile();self.target_profile();return
        if tag==319:
            self.byte_payload();self.target_profile();self.take(4,'anonymous-scalar32');return
        if tag==337:
            self.sequence(depth);self.scalar_payload();self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');return
        if tag==277:
            self.byte_payload()
            for _ in range(4):self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.sequence(depth)
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(1,'anonymous-nonzero-byte');return
        if tag==43:
            self.scalar_payload();return
        if tag==11:
            self.paired_payload();self.target_profile();self.tag_elements(reserve=1)
            self.take(1,'anonymous-nonzero-byte');return
        if tag==144:
            self.scalar_payload();self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.target_profile();return
        if tag==169:
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile();self.curve_profile()
            self.take(1,'anonymous-nonzero-byte');self.take(1,'anonymous-nonzero-byte')
            self.direction_profile();self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.scalar_flag_payload();self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload();self.scalar_payload();return
        if tag==65:
            self.byte_payload();self.query_profile();return
        if tag==372:
            self.scalar_payload();self.scalar_payload();self.byte_payload();self.scalar_payload()
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');return
        if tag==132:
            self.target_profile();self.take(4,'anonymous-scalar32');return
        if tag==315:
            self.byte_payload();self.take(4,'anonymous-scalar32');return
        if tag==81:
            self.paired_payload();self.paired_payload();return
        if tag==3:
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');start=self.pos
            for _ in range(max(0,self.count(1,reserve=1,nullable=True))):self.single_payload()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-single-payload-list'))
            self.take(1,'anonymous-nonzero-byte');return
        if tag==322:
            self.byte_payload();self.target_profile()
            for _ in range(4):self.byte_payload()
            self.take(4,'anonymous-scalar32');return
        if tag==28:
            self.target_profile();self.scalar_flag_payload();self.scalar_payload()
            self.direction_profile();self.scalar_payload();self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();return
        if tag==294:
            self.target_profile();return
        if tag==96:
            self.take(4,'anonymous-scalar32');self.target_profile();return
        if tag==212:
            self.target_profile();self.target_profile()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if tag==369:
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.scalar_payload()
            self.byte_payload();self.scalar_payload()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.target_profile();self.take(1,'anonymous-nonzero-byte');return
        if tag in (137,306,314):
            self.byte_payload();self.byte_payload();return
        if tag==352:
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile();return
        if tag==365:
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.target_profile();return
        if tag==116:
            start=self.pos
            for _ in range(max(0,self.count(4,nullable=True))):self.take(4,'anonymous-scalar32')
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar32-list'));return
        if tag==149:
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            start=self.pos
            for _ in range(max(0,self.count(1,reserve=1,nullable=True))):self.global_input_profile()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-global-input-list'))
            self.target_profile();return
        if tag==39:
            self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.paired_payload();self.take(1,'anonymous-nonzero-byte');self.target_profile();return
        if tag==66:
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.target_profile();return
        if tag in (93,6,94):self.take(4,'anonymous-scalar32');return
        if tag in (115,98,316):return
        if tag==333:
            self.finder_profile();self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile();self.scalar_payload()
            return
        if tag in (63,58):
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.byte_payload()
            return
        if tag==97:
            self.target_profile();self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.byte_payload()
            return
        if tag==234:
            self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            start=self.pos
            for _ in range(max(0,self.count(1,nullable=True))):self.target_profile()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-target-list'))
            return
        if tag==53:
            self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.curve_profile()
            self.take(1,'anonymous-nonzero-byte');self.direction_profile()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            # The concrete final reader consumes four source bytes, even
            # though its managed wrapper name contains BlackboardDouble.
            self.scalar_payload()
            return
        if tag==126:
            self.target_profile();self.target_profile()
            return
        if tag==363:
            self.scalar_payload();self.target_profile()
            return
        if tag==36:
            self.byte_payload();self.take(1,'anonymous-nonzero-byte')
            self.impulse_profile();self.take(4,'anonymous-scalar32')
            self.take(12,'anonymous-raw12')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.target_profile()
            return
        if tag==106:
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):
                start=self.pos
                for _ in range(max(0,self.count(4,nullable=True))):self.take(4,'anonymous-scalar32')
                self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar32-list'))
            return
        if tag==189:
            self.sequence(depth);self.target_profile()
            return
        if tag==222:
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,nullable=True))):self.assignment_profile()
            for _ in range(4):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(12,'anonymous-raw12');self.take(4,'anonymous-scalar32')
            self.take(12,'anonymous-raw12');self.take(12,'anonymous-raw12')
            self.take(4,'anonymous-scalar32');self.take(12,'anonymous-raw12')
            self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,nullable=True))):self.target_bytes_profile()
            self.byte_payload();self.byte_payload();self.target_profile()
            for _ in range(3):self.byte_payload()
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.target_profile();self.target_profile()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if tag==325:
            self.scalar_payload();self.paired_payload()
            return
        if tag==196:
            self.byte_payload();self.finder_profile();self.byte_payload();self.target_profile()
            return
        if tag==90:
            self.paired_payload();self.byte_payload()
            return
        if tag==136:
            self.scalar_payload()
            return
        if tag==122:
            self.take(4,'anonymous-scalar32');self.byte_payload()
            return
        if tag==10:
            self.byte_payload();self.scalar_payload();self.target_profile()
            return
        if tag==253:return
        if tag==123:
            self.target_profile();self.take(4,'anonymous-scalar32');self.scalar_payload()
            return
        if tag==366:
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(4,'anonymous-scalar32')
            self.target_profile();self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if tag in (128,187):
            self.target_profile();self.target_profile()
            return
        if tag==182:
            self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if tag==124:
            self.target_profile();self.query_profile()
            return
        if tag==150:
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();self.paired_payload()
            self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if tag==254:
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.scalar_payload();self.take(4,'anonymous-scalar32');self.scalar_payload()
            for _ in range(4):self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
            return
        if tag==343:
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            return
        if tag==361:
            self.byte_payload();self.byte_payload();self.take(4,'anonymous-scalar32');self.byte_payload()
            self.target_profile();self.direction_profile()
            for _ in range(4):self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=64,nullable=True))):self.assignment_profile()
            self.take(1,'anonymous-nonzero-byte');self.target_profile();self.take(4,'anonymous-scalar32')
            self.take(12,'anonymous-raw12');self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(16,'anonymous-raw16')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload()
            for _ in range(max(0,self.count(4,reserve=9,nullable=True))):self.byte_payload()
            for _ in range(9):self.take(1,'anonymous-nonzero-byte')
            return
        if tag in (101,110):
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            return
        if tag==162:
            self.byte_payload();self.target_profile();self.effect_configuration_profile();self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            for _ in range(5):self.take(1,'anonymous-nonzero-byte')
            self.byte_payload();self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if tag==154:
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.damage_unit_profile()
            self.target_profile();self.hit_environment_profile()
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            return
        if tag==2:
            for _ in range(max(0,self.count(1,reserve=7,nullable=True))):self.single_payload()
            self.target_profile();self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            return
        if tag==88:
            self.single_payload();self.target_profile()
            self.take(4,'anonymous-scalar32');self.scalar_payload()
            return
        if tag==129:
            self.byte_payload();self.target_profile();self.byte_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            return
        if tag in (104,348,5):
            self.target_profile()
            return
        if tag==178:
            self.direction_profile()
            self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.selector_profile()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(4,'anonymous-scalar32');self.byte_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            return
        if tag in (120,72):
            self.take(4,'anonymous-scalar32')
            if tag==120:
                for _ in range(2):self.take(1,'anonymous-nonzero-byte')
                self.target_profile()
            start=self.pos
            # Conditional list framing plus an independently joined element
            # source reader; not a live generic formatter-selection claim.
            for _ in range(max(0,self.count(4,nullable=True))):self.take(4,'anonymous-scalar32')
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar32-list'))
            return
        if tag==60:
            self.finder_profile()
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload()
            return
        if tag==281:
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile()
            for _ in range(4):self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if tag==197:
            self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.effect_configuration_profile();self.calculation_profile()
            self.take(4,'anonymous-scalar32');self.tag_list_profile();self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if tag==155:
            self.byte_payload();self.take(16,'anonymous-raw16');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.target_profile()
            return
        if tag==271:
            self.take(1,'anonymous-nonzero-byte')
            return
        if tag==68:
            self.byte_payload()
            self.target_profile()
            return
        if tag==105:
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            return
        if tag==355:
            self.byte_payload()
            self.take(4,'anonymous-scalar32')
            self.scalar_payload()
            self.scalar_payload()
            return
        if tag==310:
            self.finder_profile()
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
            return
        if tag==109:
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
            return
        if tag in (91,92):
            self.take(4,'anonymous-scalar32')
            self.take(8,'anonymous-scalar64')
            return
        if tag in (146,147):
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.scalar_bytes_profile()
            for _ in range(max(0,self.count(1,reserve=20,nullable=True))):self.input_profile()
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
            self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(4,reserve=6,nullable=True))):self.byte_payload()
            for _ in range(5):self.take(1,'anonymous-nonzero-byte')
            self.target_profile()
            return
        if tag in (86,87):
            self.byte_payload()
            for _ in range(max(0,self.count(1,reserve=5,nullable=True))):
                if tag==86:self.single_payload()
                else:self.paired_payload()
            self.take(4,'anonymous-scalar32')
            self.query_profile()
            return
        if tag==180:
            self.target_profile()
            self.finder_profile()
            self.target_profile()
            self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload()
            self.target_profile()
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            return
        if tag==287:
            self.paired_payload()
            self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte')
            self.paired_payload()
            return
        if tag==80:
            self.take(4,'anonymous-scalar32')
            for _ in range(2):self.scalar_payload()
            return
        if tag==236:
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            self.take(4,'anonymous-scalar32')
            self.scalar_payload()
            return
        if tag==118:
            start=self.pos
            # Null element is one byte. Bound count before iterating, even
            # though a non-null member-three element needs at least ten bytes.
            for _ in range(max(0,self.count(1,nullable=True))):self.paired_payload()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-paired-payload-list'))
            return
        self.take(1,'anonymous-nonzero-byte')
        for _ in range(3):self.sequence(depth)

    def byte_payload(self):
        start=self.pos
        n=self.count(1,nullable=True)
        # The selected native helper advances by the supplied byte length.
        # Do not substitute standard MemoryPack UTF-16/negative-length layouts
        # or claim decoder parity; even non-UTF8 bytes are structurally valid.
        if n>0:self.take(n,'anonymous-length-prefixed-bytes')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-byte-payload',isNull=n==-1))

    def paired_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-paired-payload')
        else:
            self.header(3)
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-paired-payload'))

    def scalar_flag_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-flag-payload')
        else:
            self.header(4);self.byte_payload();self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-flag-payload'))

    def scalar_target_payload_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-target-payload')
        else:
            self.header(4);self.scalar_payload();self.byte_payload()
            self.target_profile();self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-target-payload'))

    def single_payload(self):
        # A member-one wrapper is a separate serialized byte from its payload
        # length. Neither a value-type name nor an output slot gives its width.
        start=self.pos
        if self.peek()==255:self.take(1,'null-single-payload')
        else:
            self.header(1)
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-single-payload'))

    def null_profile(self,kind):
        actual=self.peek()
        if actual!=255:
            raise Unsupported(self.source,self.pos,'null-only '+kind+' profile',actual,'nested-profile')
        self.take(1,'null-'+kind)

    def scalar_bytes_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-bytes-profile')
        else:
            self.header(2)
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-bytes-profile'))

    def target_bytes_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-target-bytes-profile')
        else:
            self.header(2)
            self.target_profile()
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-target-bytes-profile'))

    def assignment_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-assignment-profile')
        else:
            self.header(6)
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-assignment-profile'))

    def global_input_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-global-input-profile')
        else:
            self.header(3);self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=1,nullable=True))):self.assignment_profile()
            self.single_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-global-input-profile'))

    def input_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-input-profile')
        else:
            self.header(5)
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=9,nullable=True))):self.assignment_profile()
            self.byte_payload()
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-input-profile'))

    def collider_shape_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-collider-shape-profile')
        else:
            self.header(16)
            for _ in range(2):
                self.take(12,'anonymous-raw12')
                for _ in range(3):self.byte_payload()
            for _ in range(2):
                self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(12,'anonymous-raw12');self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-collider-shape-profile'))

    def counted_payload_scalars_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-counted-payload-scalars-profile')
        else:
            self.header(1)
            for _ in range(max(0,self.count(1,nullable=True))):self.byte_payload_scalars_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-counted-payload-scalars-profile'))

    def byte_payload_scalars_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-byte-payload-scalars-profile')
        else:
            self.header(5);self.take(1,'anonymous-byte');self.byte_payload()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.take(4,'anonymous-raw4')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-byte-payload-scalars-profile'))

    def byte_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-byte-profile')
        else:
            self.header(1);self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-byte-profile'))

    def scalar_pair_flags_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-pair-flags-profile')
        else:
            self.header(6)
            for _ in range(2):
                self.take(4,'anonymous-scalar32');self.scalar_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-pair-flags-profile'))

    def query_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-query-profile')
        else:
            self.header(2)
            self.take(4,'anonymous-scalar32')
            # Selected consumer copies and advances count*4 bytes. Bound the
            # multiplication by remaining input; do not emulate native overflow.
            for _ in range(max(0,self.count(4,nullable=True))):
                self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-query-profile'))

    def finder_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-finder-profile')
        else:
            self.header(3)
            for _ in range(max(0,self.count(4,reserve=5,nullable=True))):self.byte_payload()
            self.take(4,'anonymous-scalar32')
            self.query_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-finder-profile'))

    def sequence_scalar_profile(self,depth):
        start=self.pos
        if self.peek()==255:self.take(1,'null-sequence-scalar-profile')
        else:
            self.header(2)
            self.sequence(depth);self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-sequence-scalar-profile'))

    def scalar_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-payload')
        else:
            self.header(3)
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
            # The selected reader advances four bytes, regardless of the
            # managed type name. Preserve bits, including non-finite values.
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-payload'))

    def curve_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-curve-profile')
        else:
            self.header(3)
            for _ in range(2):self.take(4,'anonymous-scalar32')
            for _ in range(max(0,self.count(28,nullable=True))):
                # Native source cursor advances 28; no per-element header.
                self.take(28,'anonymous-raw28')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-curve-profile'))

    def envelope_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-envelope-profile')
        else:
            self.header(7)
            for _ in range(2):
                self.curve_profile();self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-envelope-profile'))

    def impulse_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-impulse-profile')
        else:
            self.header(18);self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.curve_profile()
            # Mixed DWORD and MOVSS source helpers each consume four bytes.
            for _ in range(11):self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.envelope_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-impulse-profile'))

    def direction_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-direction-profile')
        else:
            self.header(8)
            self.take(1,'anonymous-nonzero-byte')
            self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):
                self.null_profile('nested-target')
                self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-direction-profile'))

    def selector_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-selector-profile')
        else:
            self.header(3)
            self.selector_finder_profile()
            for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.selector_postprocessor_profile()
            for _ in range(max(0,self.count(1,nullable=True))):self.selector_validator_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-profile'))

    def selector_finder_profile(self):
        start=self.pos
        tag=self.nested_union_tag((2,3,5,7,8,12,13,18,19),'finder')
        if tag is None:pass
        elif self.peek()==255:self.take(1,'null-nested-finder-wrapper')
        else:
            self.header({2:0,3:4,5:0,7:8,8:0,12:1,13:1,18:11,19:4}[tag])
            if tag==3:
                self.take(12,'anonymous-raw12');self.take(16,'anonymous-raw16')
                self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            elif tag==7:
                for _ in range(3):self.take(1,'anonymous-nonzero-byte')
                for _ in range(2):self.take(4,'anonymous-scalar32')
                self.take(1,'anonymous-nonzero-byte')
                for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.shape_profile()
                self.take(4,'anonymous-scalar32')
            elif tag==12:self.query_profile()
            elif tag==13:self.take(4,'anonymous-scalar32')
            elif tag==18:
                for _ in range(3):self.take(1,'anonymous-nonzero-byte')
                for _ in range(3):self.take(4,'anonymous-scalar32')
                self.byte_payload()
                for _ in range(2):self.take(1,'anonymous-nonzero-byte')
                self.take(4,'anonymous-scalar32');self.collider_shape_profile()
            elif tag==19:
                self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
                self.selection_profile();self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-finder-profile'))

    def nested_union_tag(self,supported,kind):
        lead=self.peek()
        if lead==255:self.take(1,'null-nested-'+kind);return None
        width=3 if lead==250 else 1
        if width>self.limit-self.pos:
            raise FrameError(self.source,self.pos,{'bytes':width},{'remaining':self.limit-self.pos},'truncated')
        tag=struct.unpack_from('<H',self.data,self.pos+1)[0] if lead==250 else lead
        if tag not in supported:
            raise Unsupported(self.source,self.pos,'supported nested-'+kind+' union tag',tag,'nested-profile')
        self.take(width,'nested-'+kind+'-union-tag');return tag

    def selector_validator_profile(self):
        start=self.pos;tag=self.nested_union_tag((4,5,9,10,11),'validator')
        if tag is None:pass
        elif self.peek()==255:self.take(1,'null-nested-validator-wrapper')
        else:
            self.header(3 if tag==4 else 1 if tag==11 else 0)
            if tag==4:
                self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32');self.scalar_payload()
            elif tag==11:self.query_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-validator-profile'))

    def selector_postprocessor_profile(self):
        start=self.pos;tag=self.nested_union_tag((4,7),'postprocessor')
        if tag is None:pass
        elif self.peek()==255:self.take(1,'null-nested-postprocessor-wrapper')
        elif tag==7:
            self.header(6);self.filter_profile()
            for _ in range(2):
                self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
        else:
            # Admit one finite target expansion; a further recursive instance
            # remains a reported gap before its member header is consumed.
            if self.postprocessor_depth:
                raise Unsupported(self.source,self.pos,'postprocessor target depth <= 1',2,'depth-limit')
            self.header(2);self.postprocessor_depth+=1
            try:self.target_profile()
            finally:self.postprocessor_depth-=1
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-postprocessor-profile'))

    def filter_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-filter-profile')
        else:
            self.header(2);self.finder_profile();self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-filter-profile'))

    def vector_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-vector-payload')
        else:
            self.header(3)
            # Three nested scalar payloads, not twelve raw coordinate bytes.
            for _ in range(3):self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-vector-payload'))

    def shape_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-shape-profile')
        else:
            self.header(18)
            self.scalar_payload();self.take(4,'anonymous-scalar32');self.vector_payload()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.vector_payload();self.scalar_payload()
            self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.scalar_payload();self.take(4,'anonymous-scalar32');self.vector_payload()
            self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-shape-profile'))

    def selection_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-selection-profile')
        else:
            self.header(4);self.finder_profile()
            for _ in range(max(0,self.count(1,reserve=5,nullable=True))):self.single_payload()
            self.take(4,'anonymous-scalar32');self.query_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selection-profile'))

    def tag_elements(self,*,reserve=0):
        for _ in range(max(0,self.count(1,reserve=reserve,nullable=True))):
            element=self.pos
            if self.peek()==255:self.take(1,'null-tag-element')
            else:self.header(1);self.take(4,'anonymous-scalar32')
            self.records.append(dict(start=element,end=self.pos,kind='anonymous-tag-element'))

    def tag_list_profile(self):
        # Conditional list count/loop plus separately pinned member-one element;
        # no candidate search or live provider/adapter-selection claim.
        start=self.pos
        if self.peek()==255:self.take(1,'null-tag-list-profile')
        else:
            self.header(1)
            self.tag_elements()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-tag-list-profile'))

    def calculation_profile(self):
        start=self.pos;tag=self.nested_union_tag((0,2,3),'calculation')
        if tag is not None:
            if self.peek()==255:self.take(1,'null-calculation-wrapper')
            else:
                self.header({0:1,2:3,3:4}[tag])
                if tag==2:self.take(1,'anonymous-nonzero-byte')
                self.scalar_payload()
                if tag==3:self.take(4,'anonymous-scalar32')
                if tag in (2,3):self.scalar_payload()
                if tag==3:self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-calculation-profile'))

    def empty_damage_collection(self,kind):
        # Only the selected count/null/empty path is closed; positive element
        # counts remain unsupported rather than guessing their wire widths.
        start=self.pos;n=self.count(1,nullable=True)
        if n>0:raise Unsupported(self.source,start,'null or empty '+kind,n,'nested-profile')

    def hit_sound_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-hit-sound-profile')
        else:self.header(1);self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-hit-sound-profile'))

    def hit_environment_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-hit-environment-profile')
        else:
            self.header(4);self.take(8,'anonymous-scalar64')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.calculation_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-hit-environment-profile'))

    def damage_unit_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-damage-unit-profile')
        else:
            self.header(33)
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.calculation_profile();self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.empty_damage_collection('damage unit list')
            self.take(4,'anonymous-scalar32');self.take(8,'anonymous-scalar64')
            for _ in range(2):self.empty_damage_collection('damage unit list')
            self.take(4,'anonymous-scalar32');self.byte_payload();self.take(4,'anonymous-scalar32')
            self.effect_configuration_profile()
            for _ in range(5):self.take(1,'anonymous-nonzero-byte')
            self.hit_sound_profile();self.take(4,'anonymous-scalar32')
            for _ in range(6):self.take(1,'anonymous-nonzero-byte')
            self.calculation_profile();self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-damage-unit-profile'))

    def effect_configuration_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-effect-configuration-profile')
        else:
            self.header(85)
            # One entry per native source member; inline 8/12-byte reads are
            # raw spans, while vector payloads contain three nested records.
            layout=(
            4,4,4,1,1,4,4,4,4,8,4,'scalar',
            'payload','empty-array',1,4,1,4,4,1,1,4,1,1,
            4,1,1,1,1,1,1,'scalar',4,1,4,'payload',
            4,1,4,4,4,4,1,12,'vector',4,4,1,
            1,4,4,4,1,4,4,12,'vector',1,12,'vector',
            1,4,1,1,1,4,4,1,1,1,1,1,
            1,1,1,1,4,1,1,4,4,4,4,'payload',
            1,
            )
            for op in layout:
                if isinstance(op,int):self.take(op,'anonymous-byte' if op==1 else 'anonymous-raw'+str(op))
                elif op=='payload':self.byte_payload()
                elif op=='scalar':self.scalar_payload()
                elif op=='vector':self.vector_payload()
                else:self.empty_damage_collection('effect array')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-effect-configuration-profile'))

    def target_profile(self):
        # Selected finite profile. Direction targets remain null-only and
        # postprocessor target expansion is explicitly bounded above.
        start=self.pos
        if self.peek()==255:self.take(1,'null-target-profile')
        else:
            self.header(13)
            self.direction_profile()
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            self.selector_profile()
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.byte_payload()
            self.byte_payload()
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-target-profile'))


def sequence_frame(data,*,source='<sequence>'):
    reader=Reader(data,source);reader.sequence()
    if reader.pos!=len(data):raise FrameError(source,reader.pos,'EOF',len(data)-reader.pos,'trailing-byte')
    return reader.ranges


def event_prefix(data,*,source,limit=None):
    reader=Reader(data,source,limit);status='supported-prefix';diagnostic=None
    try:
        reader.header(30)
        count=reader.count(9)
        for _ in range(count):
            start=reader.pos
            reader.header(2);reader.take(4,'anonymous-map-scalar32')
            for _ in range(reader.count(1)):reader.sequence()
            reader.records.append(dict(start=start,end=reader.pos,kind='map'))
    except Unsupported as exc:status='unsupported';diagnostic=exc.diagnostic
    except FrameError as exc:status='failed';diagnostic=exc.diagnostic
    # Atomic scalar spans plus the explicit remainder must tile the whole file.
    # Completed parent records intentionally contain their nested child ranges.
    cursor=0
    for span in reader.ranges:
        if span['start']!=cursor or not cursor<span['end']<=reader.limit:
            raise FrameError(source,cursor,'contiguous bounded scalar ranges',span,'internal-range')
        cursor=span['end']
    if cursor!=reader.pos:raise FrameError(source,cursor,reader.pos,cursor,'internal-range')
    return dict(status=status,diagnostic=diagnostic,consumedEnd=reader.pos,readLimit=reader.limit,ranges=reader.ranges,
                completedRecords=reader.records,
                opaqueRemainderRange=[reader.pos,len(data)],wholeSchemaExact=False,
                evidenceLevel='structural-only',boundary='Forward prefix profile only; no whole-object ownership, field meanings or EOF claim. Opaque remainder is bounded by the authenticated physical file, not a decoded record extent.')
