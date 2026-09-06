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
        if tag not in (201,118,236,80):raise Unsupported(self.source,self.pos,'supported current union tag',tag,'union-tag')
        self.take(1,'union-tag')
        if self.peek()==255:self.take(1,'null-wrapper');return
        self.header({201:8,118:5,236:10,80:7}[tag])
        self.take(1,'anonymous-nonzero-byte')
        for _ in range(3):self.take(4,'anonymous-scalar32')
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

    def null_profile(self,kind):
        actual=self.peek()
        if actual!=255:
            raise Unsupported(self.source,self.pos,'null-only '+kind+' profile',actual,'nested-profile')
        self.take(1,'null-'+kind)

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
            self.null_profile('nested-finder')
            for _ in range(2):
                at=self.pos
                n=self.count(1,nullable=True)
                if n!=0:
                    raise Unsupported(self.source,at,'empty-only nested collection',n,'nested-profile')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-profile'))

    def target_profile(self):
        # Selected finite profile. Non-null recursive targets and nonempty
        # selector collections remain unsupported, never signature-scanned.
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
