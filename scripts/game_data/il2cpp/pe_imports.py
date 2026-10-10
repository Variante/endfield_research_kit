"""Exact bounded PE32+ x64 selected import declaration joins.

Walk actual null-terminated lookup tables, rather than estimating descriptor
ownership from address proximity. On-disk declarations establish no live IAT
binding, loaded DLL identity, ABI signature or imported implementation effects.
Following the Microsoft PE format, fail closed on bound or lookup-differing
IAT entries, overlapping descriptors, reserved lookup bits and missing
terminators.
"""
from __future__ import annotations
import hashlib,struct


def _file(image,offset,size):
    if offset<0 or size<0 or offset+size>len(image.buf):
        raise ValueError(f'peImports.header-range: offset={offset} bytes={size}')
    return image.buf[offset:offset+size]


def _u(image,offset,size):return int.from_bytes(_file(image,offset,size),'little')


def _directory(image,index):
    if _file(image,0,2)!=b'MZ':raise ValueError('peImports.dos-signature')
    pe=_u(image,0x3c,4)
    if pe<64:raise ValueError('peImports.pe-header-overlap')
    if _file(image,pe,4)!=b'PE\0\0' or _u(image,pe+4,2)!=0x8664:
        raise ValueError('peImports.pe-x64-signature')
    size=_u(image,pe+20,2);optional=pe+24
    _file(image,optional,size)
    if size<112 or _u(image,optional,2)!=0x20b:raise ValueError('peImports.optional-pe32plus')
    count=_u(image,optional+108,4)
    if count>(size-112)//8:raise ValueError('peImports.directory-count-exceeds-header')
    if count<=index or size<112+(index+1)*8:raise ValueError('peImports.directory-unavailable')
    if _u(image,optional+24,8)!=image.image_base:raise ValueError('peImports.image-base-mismatch')
    offset=optional+112+index*8
    rva,length=struct.unpack('<II',_file(image,offset,8))
    return rva,length,{'fileOffset':offset,'rawHex':_file(image,offset,8).hex(' ')}


def _read(image,rva,size):
    if rva<0 or size<0 or rva+size>1<<32:raise ValueError('peImports.rva-range')
    raw=image.bytes_at_va(image.image_base+rva,size)
    if len(raw)!=size:raise ValueError('peImports.short-rva-read')
    return raw


def _string(image,rva,limit):
    raw=bytearray()
    for at in range(limit):
        byte=_read(image,rva+at,1);raw+=byte
        if byte==b'\0':
            try:value=bytes(raw[:-1]).decode('ascii')
            except UnicodeDecodeError as error:raise ValueError('peImports.non-ascii-name') from error
            if not value:raise ValueError('peImports.empty-name')
            return value,bytes(raw)
    raise ValueError('peImports.unterminated-name')


def resolve_named_import_slots(image,wanted,*,descriptor_limit=256,thunk_limit=4096):
    """Resolve selected named slots only after proving unique actual ownership.

    Explicit original lookup tables and unbound on-disk IAT entries are required
    for selected imports. Ordinal imports are structurally walked but cannot
    yield a selected name. Every descriptor's table extent uses its actual null
    terminator; all selected slots must lie inside the declared IAT directory.
    """
    wanted=sorted(set(wanted))
    if any(type(v)!=int or not 0<=v<1<<32 or v%8 for v in wanted):
        raise ValueError('peImports.selected-slot-range-or-alignment')
    if (type(descriptor_limit)!=int or type(thunk_limit)!=int or
            not 0<descriptor_limit<=4096 or not 0<thunk_limit<=65536):raise ValueError('peImports.limits')
    directory,size,directory_header=_directory(image,1);iat,iat_size,iat_header=_directory(image,12)
    if not directory or not 20<=size<=1<<20 or directory+size>1<<32:
        raise ValueError('peImports.import-directory-range')
    if not iat or not 8<=iat_size<=1<<24 or iat+iat_size>1<<32:
        raise ValueError('peImports.iat-directory-range')
    matches={v:[] for v in wanted};descriptors=[];terminated=False
    for n in range(min(size//20,descriptor_limit)):
        rva=directory+n*20;raw=_read(image,rva,20)
        if raw==b'\0'*20:terminated=True;break
        original,stamp,forwarder,name,first=struct.unpack('<IIIII',raw)
        if not original or not name or not first or original%8 or first%8:
            raise ValueError('peImports.descriptor-required-fields')
        entries=[];lookup_terminated=False
        for slot in range(thunk_limit):
            lookup_raw=_read(image,original+slot*8,8);value=int.from_bytes(lookup_raw,'little')
            if not value:lookup_terminated=True;break
            if value&(1<<63):
                if value&~((1<<63)|0xffff):raise ValueError('peImports.ordinal-reserved-bits')
            elif value>>31:raise ValueError('peImports.name-rva-reserved-bits')
            entries.append(value)
        if not lookup_terminated:raise ValueError('peImports.lookup-terminator-missing')
        extent=8*(len(entries)+1)
        if not iat<=first or first+extent>iat+iat_size:raise ValueError('peImports.lookup-iat-extent')
        if _read(image,first+len(entries)*8,8)!=b'\0'*8:raise ValueError('peImports.iat-terminator-mismatch')
        descriptors.append((first,first+extent,rva))
        for selected in wanted:
            if not first<=selected<first+len(entries)*8:continue
            index=(selected-first)//8;value=entries[index]
            if value&(1<<63):raise ValueError('peImports.selected-ordinal-has-no-name')
            current=_read(image,selected,8)
            if stamp or int.from_bytes(current,'little')!=value:
                raise ValueError('peImports.selected-bound-or-different-iat')
            dll,dll_raw=_string(image,name,512);hint_raw=_read(image,value,2)
            symbol,symbol_raw=_string(image,value+2,2048)
            lookup_bytes=_read(image,original,extent)
            matches[selected].append({'slotRva':selected,'descriptorRva':rva,'descriptorHex':raw.hex(' '),
                'libraryNameRva':name,'libraryName':dll,'libraryNameHex':dll_raw.hex(' '),
                'originalThunkRva':original,'firstThunkRva':first,'thunkIndex':index,'actualThunkCount':len(entries),
                'terminatedLookupBytes':extent,'terminatedLookupSha256':hashlib.sha256(lookup_bytes).hexdigest().upper(),
                'lookupEntryRva':original+index*8,'lookupEntryHex':value.to_bytes(8,'little').hex(' '),
                'iatEntryHex':current.hex(' '),'hintNameRva':value,'hint':int.from_bytes(hint_raw,'little'),
                'hintHex':hint_raw.hex(' '),'symbolName':symbol,'symbolNameHex':symbol_raw.hex(' '),
                'onDiskUnboundIatEqualsLookupProved':True,'liveIatValueOrCalleeSelected':False})
    if not terminated:raise ValueError('peImports.descriptor-terminator-missing')
    for a,b,descriptor in descriptors:
        if any(other!=descriptor and max(a,c)<min(b,d) for c,d,other in descriptors):
            raise ValueError('peImports.overlapping-iat-descriptors')
    for selected,rows in matches.items():
        if len(rows)!=1:raise ValueError(f'peImports.selected-slot-ownership: slot={selected} matches={len(rows)}')
    return {'selectedImports':[matches[v][0] for v in wanted],
        'importDirectoryRva':directory,'importDirectoryBytes':size,'importDirectoryHeader':directory_header,
        'iatDirectoryRva':iat,'iatDirectoryBytes':iat_size,'iatDirectoryHeader':iat_header,
        'walkedDescriptors':len(descriptors),'descriptorNullTerminatorRva':rva,
        'actualTerminatedTableOwnershipChecked':True,'completeImportSymbolCatalogProved':False,
        'liveIatValueOrCalleeSelected':False}
