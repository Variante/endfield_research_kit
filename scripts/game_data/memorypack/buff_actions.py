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
        self._action(depth)
        self.records.append(dict(start=start,end=self.pos,kind='union',tag=self.data[start]))

    def _action(self,depth):
        tag=self.peek()
        if tag==255:self.take(1,'null-union');return
        if tag!=201:raise Unsupported(self.source,self.pos,'supported current union tag',tag,'union-tag')
        self.take(1,'union-tag')
        if self.peek()==255:self.take(1,'null-wrapper');return
        self.header(8)
        self.take(1,'anonymous-nonzero-byte')
        for _ in range(3):self.take(4,'anonymous-scalar32')
        self.take(1,'anonymous-nonzero-byte')
        for _ in range(3):self.sequence(depth)


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
