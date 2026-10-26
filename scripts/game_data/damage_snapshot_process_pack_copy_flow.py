"""Complete unrolled 16-byte value-byte copy; source contents stay anonymous."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require

def check_copy_bytes(raw,pointer,source_disp,dest_disp,size):
    _require(type(size) is int and 128<size<=240 and size%16==0,'process-pack-copy-size','supported bounded full 16-byte compiler copy grammar',size)
    forms=[b'\x48\x8d\x8c\x24'+struct.pack('<i',dest_disp),b'\x48\x8d\x84\x24'+struct.pack('<i',source_disp)]
    segments=[]
    for block in range(size//16):
        register=block%2;offset=block*16
        if block==7:forms.append(b'\x48\x8d\x89\x80\x00\x00\x00')
        local=offset if block<8 else offset-128
        if block==8:forms.append(b'\x48\x8d\x80\x80\x00\x00\x00')
        load=(b'\x0f\x10'+bytes([register*8])) if local==0 else b'\x0f\x10'+bytes([0x40+register*8,local])
        store_local=offset if block<7 else offset-128
        store=(b'\x0f\x11'+bytes([register*8+1])) if store_local==0 else b'\x0f\x11'+bytes([0x41+register*8,store_local&255])
        forms.extend((load,store));segments.append({'sourceRelative':offset,'destRelative':offset,'widthBytes':16,'temporaryXmm':register})
    at=0
    for encoding in forms:
        _require(raw[at:at+len(encoding)]==encoding,'process-pack-copy-instruction',encoding.hex(),raw[at:at+len(encoding)].hex());at+=len(encoding)
    _require(at==len(raw),'process-pack-copy-complete-coverage',at,len(raw))
    return {'selectedEnd':pointer+at,'selectedInstructionCount':len(forms),'copiedBytes':size,'segments':segments,
            'allBytesExactlyCovered':sum(s['widthBytes'] for s in segments)==size,'explicitCallsOrBranches':[],
            'sourceContentsInitializedOrTypedProved':False}

def copy_range_conditions(current_rsp,source_disp,dest_disp,size):
    _require(all(type(v) is int for v in (current_rsp,source_disp,dest_disp,size)) and size>0,
             'process-pack-copy-range-inputs','integer addresses and positive size',[current_rsp,source_disp,dest_disp,size])
    source=current_rsp+source_disp;dest=current_rsp+dest_disp
    valid=0<=current_rsp<1<<64 and all(0<=a and a+size<=1<<64 for a in (source,dest))
    disjoint=valid and (source+size<=dest or dest+size<=source)
    return {'sourceAddress':source,'destAddress':dest,'copiedBytes':size,'validNonwrappingRanges':valid,'sourceDestDisjoint':disjoint,
            'validReadableWritableBackingObserved':False}


def check_process_pack_copy(index,normal_proof,formula_proof,spec):
    _require(normal_proof.get('claim')=='snapshotProcessLocalIndexNormalRequestAndTemporary' and formula_proof.get('claim')=='snapshotNormalSimpleFloatScaleTimesDoubleCarrierToResult',
             'process-pack-copy-fresh-dependencies','fresh normal pack request/typed formula fields',[normal_proof.get('claim'),formula_proof.get('claim')])
    _require(normal_proof['selectedCallee']==formula_proof['symbol'],'process-pack-copy-same-normal','same fresh typed pack consumer',normal_proof['selectedCallee'])
    body=index.body(spec['type'],spec['method'])
    _require(body.symbol==normal_proof['symbol'],'process-pack-copy-same-caller',normal_proof['symbol'],body.symbol)
    owner=formula_proof['checkedValueOwner'];td=index.types[owner];header=spec['unboxedHeaderBytes']
    _require(header==16,'process-pack-copy-header','reviewed Win64 boxed header adjustment',header)
    cell=int(index.image.registration['typeDefinitionsSizes'],16)+td.index*8;size_pointer=index.pe.u64_at_va(cell)
    _require(size_pointer!=0,'process-pack-copy-type-size-cell','nonzero selected type-size row',hex(cell))
    size_raw=index.pe.bytes_at_va(size_pointer,16)
    _require(len(size_raw)==16,'process-pack-copy-size-row','exact selected row',len(size_raw))
    boxed=int.from_bytes(size_raw[:4],'little');size=boxed-header
    _require(128<size<=240 and size%16==0,'process-pack-copy-selected-value-size','supported bounded value copy extent',[owner,boxed,header])
    source=spec['anonymousSourceLocalDisp32'];dest=normal_proof['anonymousPackBufferDisp32']
    _require(body.pointer in index.extents and 0<index.extents[body.pointer]-body.pointer<=65536,
             'process-pack-copy-owned-search','bounded exact selected caller',hex(body.pointer))
    end=index.extents[body.pointer];raw=index.pe.bytes_at_va(body.pointer,end-body.pointer)
    prefix=b'\x48\x8d\x8c\x24'+struct.pack('<i',dest)+b'\x48\x8d\x84\x24'+struct.pack('<i',source)
    positions=[at for at in range(len(raw)) if raw.startswith(prefix,at)];matches=[]
    byte_count=16+sum(6 if offset%128==0 else 8 for offset in range(0,size,16))+14
    for at in positions:
        proof=check_copy_bytes(raw[at:at+byte_count],body.pointer+at,source,dest,size)
        matches.append({'fragmentEntry':hex(body.pointer+at),**proof})
    _require(len(matches)==1,'process-pack-copy-unique-program','one complete selected full-size copy',len(matches))
    field=formula_proof['packAttributesUnboxedOffset']
    _require(type(field) is int and 0<=field and field+8<=size,'process-pack-copy-field-span','whole named pointer view fits exact copied bytes',field)
    segments=[s for s in matches[0]['segments'] if s['destRelative']<=field and field+8<=s['destRelative']+s['widthBytes']]
    _require(len(segments)==1,'process-pack-copy-whole-field-in-segment','one complete selected 16-byte transfer',segments)
    return {**matches[0],'symbol':body.symbol,'claim':'snapshotProcessAnonymousPackBytesCopyToNormalArgument',
            'selectedValueOwner':owner,'selectedBoxedInstanceBytes':boxed,'selectedUnboxedBytes':size,
            'sourceLocalDisp32':source,'destLocalDisp32':dest,'typedConsumerAttributesPointerViewOffset':field,
            'namedPointerViewCopySegment':segments[0],'sourceValueOrArrayContentsProved':False,
            'boundary':'The exact selected owned Process copy contains no calls/branches and transfers all selected unboxed pack-size bytes through complete paired 16-byte MOVUPS loads/stores with both actual base adjustments checked. Its destination displacement matches the fresh normal explicit pack-ref argument; the fresh typed attributes pointer view fits wholly within one complete copied segment. Selected native type-size row and reviewed value header are checked independently. With valid nonwrapping disjoint source/destination storage, the same current-SP/frame and no interference, each destination byte equals the corresponding source byte immediately after this fragment. The source remains an anonymous buffer: its typed initialization, reference/array contents, actual layout/parity and later preservation to the independently entered normal call remain conditions or unresolved. This byte-copy relation does not establish attribute-slot/enum meaning, full Process CFG, all writers, source producer semantics or final damage.'}
