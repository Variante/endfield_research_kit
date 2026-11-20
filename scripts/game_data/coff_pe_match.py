"""Relocation-aware AMD64 COFF/bigobj to PE byte matching.

Masked bytes locate candidates only. An exact result additionally authenticates
each relocation against the same-section symbol, a unique relocation-free COFF
section, or a named PE import. Unresolved externals remain conditional.

RVA-to-file mapping is per section, never one image-wide delta: the shipped
GameAssembly.dll puts its AOT managed method bodies in a second executable
section, and protector code in a third, each with a different delta from `.text`.
That is why `read` accepts only a unique raw-backed interval. A scan that hardcodes
`.text`'s delta mislabels the owner of every AOT site and undercounts references, so
a "no references" or "no callers" negative is only as wide as the sections it walked.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct


def require(condition,message):
    if not condition:raise ValueError('coff-pe: '+message)


def bounded(data,offset,size):
    require(type(offset)is int and type(size)is int and 0<=offset<=len(data) and 0<=size<=len(data)-offset,'file interval')
    return data[offset:offset+size]


@dataclass(frozen=True)
class Section:
    index:int
    name:str
    rva:int
    raw:bytes
    characteristics:int
    relocations:tuple


@dataclass(frozen=True)
class Symbol:
    index:int
    name:str
    value:int
    section:int
    kind:int
    storage:int


class CoffObject:
    def __init__(self,data):
        self.data=bytes(data);data=self.data
        require(len(data)>=20,'COFF header')
        self.bigobj=data[:4]==b'\0\0\xff\xff'
        if self.bigobj:
            require(len(data)>=56 and struct.unpack_from('<H',data,4)[0]>=2,'bigobj header')
            machine=struct.unpack_from('<H',data,6)[0];count,pointer,number=struct.unpack_from('<III',data,44)
            header=56;stride=20
        else:
            machine,count,stamp,pointer,number,optional,flags=struct.unpack_from('<HHIIIHH',data)
            require(optional==0,'ordinary COFF optional header not supported');header=20;stride=18
        require(machine==0x8664 and 0<count<=1000000 and number<=10000000,'AMD64 COFF bounds')
        bounded(data,header,count*40);bounded(data,pointer,number*stride)
        table_at=pointer+number*stride;length=struct.unpack('<I',bounded(data,table_at,4))[0]
        self.strings=bounded(data,table_at,length);require(length>=4,'COFF strings')
        def string(offset):
            require(4<=offset<len(self.strings),'COFF string offset');end=self.strings.find(b'\0',offset)
            require(end>=offset,'COFF string terminator');return self.strings[offset:end].decode('utf-8')
        self.symbols={};at=0
        while at<number:
            row=bounded(data,pointer+at*stride,stride);name=row[:8]
            name=string(struct.unpack_from('<I',name,4)[0])if name[:4]==b'\0'*4 else name.rstrip(b'\0').decode('utf-8')
            value,section,kind,storage,aux=struct.unpack_from('<IiHBB'if self.bigobj else'<IHHBB',row,8)
            if not self.bigobj and section in (0xffff,0xfffe):section-=0x10000
            require(section in (-2,-1,0)or 1<=section<=count,'COFF symbol section number')
            require(at+aux<number,'symbol auxiliary bounds')
            self.symbols[at]=Symbol(at,name,value,section,kind,storage);at+=1+aux
        self.sections={}
        for index in range(1,count+1):
            row=bounded(data,header+(index-1)*40,40)
            name=row[:8].rstrip(b'\0').decode('ascii')
            if name.startswith('/')and name[1:].isdigit():name=string(int(name[1:]))
            vs,rva,size,raw_at,reloc_at,line_at,nreloc,nline,flags=struct.unpack_from('<IIIIIIHHI',row,8)
            skip=0
            if flags&0x01000000:
                require(nreloc==0xffff,'relocation overflow marker')
                total=struct.unpack('<I',bounded(data,reloc_at,4))[0];require(total>=1,'relocation overflow count')
                nreloc=total-1;skip=1
            require(nreloc<=10000000,'relocation count')
            reloc=[]
            for j in range(nreloc):
                offset,symbol,kind=struct.unpack('<IIH',bounded(data,reloc_at+(j+skip)*10,10))
                require(symbol in self.symbols,'relocation symbol must not be auxiliary')
                reloc.append((offset,symbol,kind))
            raw=bounded(data,raw_at,size)if size and raw_at else b''
            self.sections[index]=Section(index,name,rva,raw,flags,tuple(reloc))

    def symbol(self,name):
        rows=[row for row in self.symbols.values()if row.name==name]
        require(len(rows)==1,'unique COFF symbol '+name);return rows[0]


class PeImage:
    def __init__(self,data):
        self.data=bytes(data);data=self.data
        require(data[:2]==b'MZ','DOS magic');nt=struct.unpack('<I',bounded(data,60,4))[0]
        require(bounded(data,nt,4)==b'PE\0\0','PE signature')
        machine,count,stamp,sp,sn,optional,flags=struct.unpack('<HHIIIHH',bounded(data,nt+4,20))
        opt=nt+24;require(machine==0x8664 and struct.unpack('<H',bounded(data,opt,2))[0]==0x20b and optional>=240,'PE32+ AMD64')
        self.image_base=struct.unpack('<Q',bounded(data,opt+24,8))[0]
        self.directories=[struct.unpack('<II',bounded(data,opt+112+i*8,8))for i in range(16)]
        self.sections=[]
        for i in range(count):
            row=bounded(data,opt+optional+i*40,40);vs,rva,size,at=struct.unpack_from('<IIII',row,8)
            self.sections.append(Section(i+1,row[:8].rstrip(b'\0').decode('ascii'),rva,bounded(data,at,size),struct.unpack_from('<I',row,36)[0],()))
        self.imports={};rva,size=self.directories[1]
        if rva:
            require(size>=20,'import directory')
            for off in range(0,size,20):
                row=struct.unpack('<IIIII',self.read(rva+off,20))
                if not any(row):break
                original,ts,chain,name,iat=row;dll=self.cstring(name)
                require(original!=0,'bound imports require original lookup table')
                for i in range(1000000):
                    lookup=struct.unpack('<Q',self.read(original+i*8,8))[0]
                    if not lookup:break
                    symbol='#'+str(lookup&0xffff)if lookup>>63 else self.cstring(lookup+2)
                    self.imports[iat+i*8]=dict(dll=dll,name=symbol)
                else:raise ValueError('coff-pe: import thunk limit')

    def read(self,rva,size):
        matches=[section for section in self.sections if section.rva<=rva and rva+size<=section.rva+len(section.raw)]
        require(len(matches)==1,'unique raw-backed PE interval')
        section=matches[0];return section.raw[rva-section.rva:rva-section.rva+size]

    def cstring(self,rva):
        value=bytearray()
        for i in range(65536):
            char=self.read(rva+i,1)
            if char==b'\0':return value.decode('utf-8')
            value+=char
        raise ValueError('coff-pe: PE string limit')

    def import_binding(self,rva,name):
        expected=name.removeprefix('__imp_')
        slot=rva
        if slot not in self.imports:
            try:raw=self.read(rva,6)
            except ValueError:return None
            if raw[:2]!=b'\xff\x25':return None
            slot=rva+6+struct.unpack_from('<i',raw,2)[0]
        actual=self.imports.get(slot)
        return dict(kind='PE-named-import',iatRva=slot,**actual)if actual and actual['name']==expected else None


def relocation_width(kind):
    if kind==1:return 8
    if kind in (2,3,4,5,6,7,8,9,11):return 4
    raise ValueError('coff-pe: unsupported relocation kind '+str(kind))


def _candidate_sections(obj,section,pe):
    variable=set()
    for offset,symbol,kind in section.relocations:
        width=relocation_width(kind);require(offset+width<=len(section.raw),'relocation interval')
        span=set(range(offset,offset+width));require(not(variable&span),'overlapping relocations');variable|=span
    runs=[];start=None
    for i in range(len(section.raw)+1):
        if i<len(section.raw)and i not in variable:
            if start is None:start=i
        elif start is not None:runs.append((start,i));start=None
    require(runs,'nonrelocated anchor required');left,right=max(runs,key=lambda span:span[1]-span[0])
    require(right-left>=8,'at least eight exact anchor bytes required');anchor=section.raw[left:right];result=[]
    for linked in pe.sections:
        if bool(linked.characteristics&0x20000000)!=bool(section.characteristics&0x20000000):continue
        at=linked.raw.find(anchor)
        while at>=0:
            candidate=at-left
            if 0<=candidate and candidate+len(section.raw)<=len(linked.raw):
                raw=linked.raw[candidate:candidate+len(section.raw)]
                if all(raw[a:b]==section.raw[a:b]for a,b in runs):result.append(linked.rva+candidate)
            at=linked.raw.find(anchor,at+1)
    return result


def match_function(obj,pe,name,*,symbol_bindings=None):
    """Return exact or conditional complete-COMDAT candidates for one symbol.

    A function at a nonzero section offset or sharing its section with another
    function value is deliberately unsupported; do not guess its extent.
    """
    symbol_bindings=symbol_bindings or {}
    symbol=obj.symbol(name);require(symbol.section>0 and symbol.kind&0x20 and symbol.value==0,'function must begin complete COFF section')
    section=obj.sections[symbol.section]
    require(all(other.value==0 for other in obj.symbols.values()if other.section==symbol.section and other.kind&0x20),'several functions in one COFF section')
    require(section.raw and section.characteristics&0x20000000,'code section')
    candidates=[]
    for rva in _candidate_sections(obj,section,pe):
        relocations=[];exact=True
        for offset,index,kind in section.relocations:
            target=obj.symbols[index];width=relocation_width(kind);original=section.raw[offset:offset+width];linked=pe.read(rva+offset,width)
            if kind==11:
                # SECREL encodes an output-section-relative value, not an RVA.
                # TLS coalescing/section placement needs an independent binding.
                exact=False
                relocations.append(dict(offset=offset,kind=kind,symbol=target.name,symbolIndex=index,targetRva=None,
                    sectionRelativeTargetOffset=int.from_bytes(linked,'little')-int.from_bytes(original,'little'),
                    proof=None,unresolved='output-section/TLS placement not independently bound'))
                continue
            if 4<=kind<=9:
                addend=int.from_bytes(original,'little',signed=True)
                target_rva=rva+offset+4+(kind-4)+int.from_bytes(linked,'little',signed=True)-addend
            elif kind==1:target_rva=int.from_bytes(linked,'little')-pe.image_base-int.from_bytes(original,'little')
            elif kind==2:target_rva=int.from_bytes(linked,'little')-pe.image_base-int.from_bytes(original,'little')
            else:target_rva=int.from_bytes(linked,'little')-int.from_bytes(original,'little')
            proof=None
            if target.section==symbol.section:
                require(target_rva==rva+target.value,'same-section relocation target mismatch')
                proof=dict(kind='same-COFF-section-symbol',value=target.value)
            elif target.section>0:
                other=obj.sections[target.section]
                if other.raw and not other.relocations:
                    positions=_candidate_sections(obj,other,pe)if len(other.raw)>=8 else []
                    if len(positions)==1 and target_rva==positions[0]+target.value:
                        proof=dict(kind='unique-complete-relocation-free-COFF-section',section=target.section,sectionRva=positions[0])
                    else:
                        section_rva=target_rva-target.value
                        try:equal=pe.read(section_rva,len(other.raw))==other.raw
                        except ValueError:equal=False
                        if equal:proof=dict(kind='complete-relocation-free-data-at-actual-target',section=target.section,
                            sectionRva=section_rva,symbolIdentityProved=False,contentsProved=True)
            else:proof=pe.import_binding(target_rva,target.name)
            if proof is None and target.name in symbol_bindings:
                binding=symbol_bindings[target.name]
                require(type(binding)is dict and type(binding.get('rva'))is int,'explicit cohort binding record')
                require(target_rva==binding['rva'],'bounded cohort relocation target mismatch: '+target.name)
                proof=dict(kind='bounded-cohort-consistent',symbolIdentityProved=False,targetRva=binding['rva'],
                    sourceEvidence=binding.get('evidence','caller-supplied bounded cohort'),candidateStatus=binding.get('candidateStatus'))
            exact=exact and proof is not None and proof.get('symbolIdentityProved',True)
            relocations.append(dict(offset=offset,kind=kind,symbol=target.name,symbolIndex=index,targetRva=target_rva,proof=proof))
        candidates.append(dict(rva=rva,bytes=len(section.raw),status='exact'if exact else'conditional',relocations=relocations))
    return dict(symbol=name,coffSection=symbol.section,sectionBytes=len(section.raw),candidates=candidates,
        unique=len(candidates)==1,exact=len(candidates)==1 and candidates[0]['status']=='exact')


def cohort_bindings(results):
    """Build explicitly conditional target constraints from unique candidates.

    This does not promote the candidates' unknown externals or their provenance.
    Consumers retain the object/input identities used to compute each result.
    """
    bindings={}
    for result in results:
        require(result.get('unique')is True and len(result['candidates'])==1,'unique cohort candidate required')
        name=result['symbol'];candidate=result['candidates'][0]
        binding=dict(rva=candidate['rva'],evidence='unique complete COFF-section nonrelocated bytes; relocation constraints remain bounded',candidateStatus=candidate['status'])
        require(name not in bindings or bindings[name]==binding,'conflicting cohort symbol')
        bindings[name]=binding
    return bindings


def cohort_relocation_consistency(results):
    """Report same nominal SECREL symbol's observed offset consistency only."""
    groups={}
    for result in results:
        require(result.get('unique')is True and len(result['candidates'])==1,'unique cohort candidate required')
        candidate=result['candidates'][0]
        for row in candidate['relocations']:
            if row['kind']!=11:continue
            groups.setdefault(row['symbol'],[]).append(dict(function=result['symbol'],rva=candidate['rva'],
                offset=row['offset'],sectionRelativeTargetOffset=row['sectionRelativeTargetOffset']))
    return [dict(symbol=name,references=rows,consistent=len({row['sectionRelativeTargetOffset']for row in rows})==1,
        independentTlsLayoutProved=False,evidence='same nominal symbol encoded-offset consistency only')for name,rows in sorted(groups.items())]


def archive_members(data):
    """Yield immutable members of a standard Microsoft COFF archive (.lib).

    Linker symbol indexes are not used as provenance; consumers parse the
    selected member's own COFF symbols and retain the archive/member identity.
    """
    data=bytes(data);require(data[:8]==b'!<arch>\n','COFF archive signature')
    at=8;strings=b'';pending=[]
    while at<len(data):
        header=bounded(data,at,60);require(header[58:]==b'`\n','archive member header')
        name=header[:16].rstrip(b' ');size=int(header[48:58].strip());raw=bounded(data,at+60,size)
        if name==b'//':strings=raw
        elif name not in (b'/',b'/SYM64/'):
            pending.append((name,at+60,raw))
        at+=60+size+(size&1)
    require(at==len(data),'archive final alignment')
    for name,offset,raw in pending:
        if name.startswith(b'/')and name[1:].isdigit():
            index=int(name[1:]);require(0<=index<len(strings),'archive long name offset')
            end=strings.find(b'\0',index)
            if end<0:end=strings.find(b'/\n',index)
            require(end>=index,'archive long name terminator');name=strings[index:end]
        else:
            require(not name.startswith(b'#1/'),'BSD archive names unsupported');name=name.rstrip(b'/')
        yield dict(name=name.decode('utf-8'),offset=offset,data=raw)


@contextmanager
def bookended_inputs(paths):
    """Read immutable inputs and refuse any content change before returning."""
    paths=[Path(path).resolve()for path in paths];data={path:path.read_bytes()for path in paths}
    identities=[dict(path=path.as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())for path,raw in data.items()]
    yield data,identities
    for path,raw in data.items():require(path.read_bytes()==raw,'input changed: '+str(path))
