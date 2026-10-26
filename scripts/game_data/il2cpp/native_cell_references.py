"""Find selected canonical RIP-relative QWORD references as raw candidates.

This is an overlapping byte-pattern search for REX.W MOV/LEA and MOV imm32
forms. It does not establish instruction/code ownership or discover every
writer: other widths, wider overlaps, aliases and child stores remain open.
Callers must authenticate the selected image and prove each candidate body.

An immutable image may retain a bounded private index of raw byte matches.
Selected matches are decoded afresh; no instruction ownership or native proof
is cached. The index dies with the image and is replaced on any relevant drift.
"""
from __future__ import annotations
from array import array
from bisect import bisect_left, bisect_right
import re
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.integer_addressing import decode_lea_address

_REG=re.compile(rb'(?=([\x48-\x4f][\x89\x8b\x8d][\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}))',re.DOTALL)
_IMM=re.compile(rb'(?=([\x48-\x4b]\xc7\x05.{8}))',re.DOTALL)
_MAX_RAW_SITES=8_000_000
_RELATIVE_BITS=32
_LENGTH_BITS=8
_PATTERN_SHIFT=_RELATIVE_BITS+_LENGTH_BITS
_SECTION_SHIFT=_PATTERN_SHIFT+1
_RELATIVE_MASK=(1<<_RELATIVE_BITS)-1


def _candidate_row(image,body,site,target):
    opcode=body[1]
    if opcode==0x8d:
        decoded=decode_lea_address(body,0,image.image_base+site)
        if decoded is None or decoded[1]!=len(body):raise ValueError('nativeCellReferences.address-encoding')
        facts=decoded[0]['addressOperation'];kind='address'
    elif opcode!=0xc7:
        decoded=decode_memory_move(body,0,image.image_base+site)
        if decoded is None or decoded[1]!=len(body):raise ValueError('nativeCellReferences.move-encoding')
        facts=decoded[0]['memoryOperation'];kind=facts['direction']
        if facts['memoryBytes']!=8:raise ValueError('nativeCellReferences.qword-width')
    else:
        # MOV r/m64, imm32 sign-extends its immediate. It supplies
        # a raw-pattern candidate only; no decoder is substituted.
        value=int.from_bytes(body[7:11],'little',signed=True)&((1<<64)-1)
        facts={'memoryWriteBytes':8,'encodedImmediateBits':32,'immediateWord':value};kind='immediateStore'
    return {'siteRva':site,'cellRva':target,'kind':kind,'rawHex':body.hex(),'facts':facts,
        'instructionBoundaryAndOwnedCodeProved':False}


def _selected_fresh(image,cells):
    """Original scanner, including its lazy attribute access and error order."""
    result=[]
    for section in image.sections:
        if not section['characteristics']&0x20000000:continue
        raw=image.buf[section['rawPointer']:section['rawPointer']+section['rawSize']]
        for pattern in (_REG,_IMM):
            for match in pattern.finditer(raw):
                body=match.group(1);site=section['virtualAddress']+match.start();target=site+len(body)+int.from_bytes(body[3:7],'little',signed=True)
                if target not in cells:continue
                result.append(_candidate_row(image,body,site,target))
    return sorted(result,key=lambda row:(row['siteRva'],row['kind']))


def _raw_key(image,buf):
    sections=getattr(image,'sections',None);base=getattr(image,'image_base',None)
    # Inspect no one-shot iterator before falling back to the original scanner.
    if type(buf) is not bytes or type(sections) not in (list,tuple) or type(base) is not int:return None
    mapping=[]
    try:
        for section in sections:
            flags=section['characteristics']
            if not flags&0x20000000:continue
            pointer,size,va=section['rawPointer'],section['rawSize'],section['virtualAddress']
            if any(type(value) is not int for value in (flags,pointer,size,va)):return None
            start,stop,_=slice(pointer,pointer+size).indices(len(buf))
            if max(0,stop-start)>1<<_RELATIVE_BITS:return None
            mapping.append((pointer,size,va,flags,start,stop))
    except (KeyError,TypeError,OverflowError):return None
    if len(mapping)>=1<<(64-_SECTION_SHIFT):return None
    return base,tuple(mapping),tuple((pattern.pattern,pattern.flags)for pattern in (_REG,_IMM))


class _QwordReferenceIndex:
    """Per-image raw matches only; two packed arrays use 16 bytes per site.

    A temporary sorting permutation costs additional O(site count) memory.
    Oversized/unrepresentable indexes retain only a fallback marker for this
    exact buffer/key, so they never repeat the failed build on every lookup.
    """
    def __init__(self):
        self._buf=self._key=self._index=None
        self._fallback=None
        self._builds=self._hits=self._fresh_calls=0

    def _forget(self):
        self._buf=self._key=self._index=None
        self._fallback=None

    def statistics(self):
        index=self._index
        sites=len(index[0])if index is not None else 0
        return dict(indexBuilt=index is not None,capFallback=self._fallback=='site-cap',
            rawSites=sites,payloadBytes=sites*16,builds=self._builds,hits=self._hits,
            freshCalls=self._fresh_calls,fallbackReason=self._fallback,nativeProofCached=False)

    def _build(self,buf,key):
        targets,origins=array('q'),array('Q')
        patterns=tuple(re.compile(pattern,flags)for pattern,flags in key[2])
        for number,(_,_,va,_,start,stop)in enumerate(key[1]):
            # A section-local view preserves slicing semantics even for regex
            # anchors/lookbehind and avoids copying a large executable section.
            raw=memoryview(buf)[start:stop]
            for pattern_number,pattern in enumerate(patterns):
                for match in pattern.finditer(raw):
                    body=match.group(1);relative=match.start()
                    if body is None or match.start(1)!=relative:
                        self._fallback='unrepresentable-site';return None
                    target=va+relative+len(body)+int.from_bytes(body[3:7],'little',signed=True)
                    if len(targets)>=_MAX_RAW_SITES:
                        self._fallback='site-cap';return None
                    if not -(1<<63)<=target<1<<63 or not 0<len(body)<1<<_LENGTH_BITS:
                        self._fallback='unrepresentable-site';return None
                    targets.append(target)
                    origins.append((number<<_SECTION_SHIFT)|(pattern_number<<_PATTERN_SHIFT)
                        |(relative<<_LENGTH_BITS)|len(body))
        order=sorted(range(len(targets)),key=targets.__getitem__)
        return array('q',(targets[i]for i in order)),array('Q',(origins[i]for i in order))

    def _get(self,buf,key):
        if self._buf is buf and self._key==key:self._hits+=1
        else:
            self._forget();self._builds+=1
            self._buf,self._key=buf,key
            self._index=self._build(buf,key)
        return self._index


def selected_qword_reference_candidates(image,cell_rvas):
    values=tuple(cell_rvas)
    if any(type(v)!=int or v<0 for v in values):raise ValueError('nativeCellReferences.cell-rva-range')
    cells=set(values);buf=getattr(image,'buf',None)
    key=_raw_key(image,buf)
    owner=getattr(image,'_native_cell_raw_index',None)
    if key is None:
        if type(owner)is _QwordReferenceIndex:
            owner._forget();owner._fresh_calls+=1
        return _selected_fresh(image,cells)
    if type(owner)is not _QwordReferenceIndex:
        owner=_QwordReferenceIndex()
        try:image._native_cell_raw_index=owner
        except (AttributeError,TypeError):return _selected_fresh(image,cells)
    index=owner._get(buf,key)
    if index is None:
        owner._fresh_calls+=1
        return _selected_fresh(image,cells)
    targets,origins=index
    selected=[]
    for cell in cells:
        selected.extend(origins[bisect_left(targets,cell):bisect_right(targets,cell)])
    # Restore original section/pattern/offset traversal before the final stable
    # sort, including identical virtual sites from overlapping section maps.
    selected.sort();result=[]
    for origin in selected:
        number=origin>>_SECTION_SHIFT
        relative=(origin>>_LENGTH_BITS)&_RELATIVE_MASK
        length=origin&((1<<_LENGTH_BITS)-1)
        _,_,va,_,start,_=key[1][number]
        body=buf[start+relative:start+relative+length];site=va+relative
        target=site+length+int.from_bytes(body[3:7],'little',signed=True)
        result.append(_candidate_row(image,body,site,target))
    return sorted(result,key=lambda row:(row['siteRva'],row['kind']))
