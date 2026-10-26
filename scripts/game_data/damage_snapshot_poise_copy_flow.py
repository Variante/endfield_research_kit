"""Authenticate Poise carrier low-half replacement, independent of dispatch semantics."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require

def check_copy(rows,pointer,end,source,destination,result_offset,size):
    _require(size==72 and result_offset==32,'poise-copy-layout','reviewed 72-byte span and low field at32',[size,result_offset])
    forms=[]
    for offset in (0,16):
        reg=0x84 if offset==0 else 0x8c
        forms.extend([bytes([0x0f,0x28,reg,0x24])+struct.pack('<i',source+offset),bytes([0x0f,0x29,reg,0x24])+struct.pack('<i',destination+offset)])
    forms.extend([b'\x0f\x28\x84\x24'+struct.pack('<i',source+32),b'\xf2\x0f\x10\xc6',b'\x0f\x29\x84\x24'+struct.pack('<i',source+32),b'\x0f\x29\x84\x24'+struct.pack('<i',destination+32),b'\x0f\x28\x84\x24'+struct.pack('<i',source+48),b'\x0f\x29\x84\x24'+struct.pack('<i',destination+48),b'\xf2\x0f\x10\x8c\x24'+struct.pack('<i',source+64),b'\xf2\x0f\x11\x8c\x24'+struct.pack('<i',destination+64)])
    _require(len(rows)==len(forms),'poise-copy-length',len(forms),len(rows));at=pointer
    for row,expected in zip(rows,forms):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at and raw==expected,'poise-copy-instruction',[hex(at),expected.hex()],[row['va'],raw.hex()]);at+=len(raw)
    _require(at==end,'poise-copy-end',end,at)
    return {'actualOriginalStoreBytes':16,'actualResultLowReplacementBytes':8,'upperEightBytesSource':'original source chunk loaded immediately before reg-reg MOVSD','copiedSpanBytes':72,'exactRawCopyBytes':72,'rawCopyTier':'exact','dispatchTypedReturnProved':False,'conditions':['same valid current frame and disjoint source/destination spans','16-byte aligned MOVAPS addresses','opaque XMM6 low64 preserved to selected copy','no concurrent/intervening storage interference']}


def check_postdispatch(rows,pointer,end):
    from scripts.game_data.il2cpp.context import relative_branch_target
    _require(len(rows)==12,'poise-post-length',12,len(rows));forms=['dispatch',b'\x66\x48\x0f\x6e\xf0','static-pointer',b'\x83\xb9\xe0\x00\x00\x00\x00','ready','excluded-init',b'\x41\x0f\x28\xd6',b'\x0f\x28\xcf',b'\x0f\x28\xc6','opaque-debug',b'\x84\xc0','nonzero-excluded']
    at=pointer;targets={}
    for n,(row,form) in enumerate(zip(rows,forms)):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'poise-post-contiguity',at,row['va'])
        if isinstance(form,bytes):_require(raw==form,'poise-post-instruction',form.hex(),raw.hex())
        elif form in ('dispatch','excluded-init','opaque-debug'):
            _require(len(raw)==5 and raw[0]==0xe8,'poise-post-call','complete direct CALL',raw.hex());targets[form]=relative_branch_target(raw,at,source='poisePost')
        elif form=='static-pointer':_require(len(raw)==7 and raw[:3]==b'\x48\x8b\x0d','poise-post-static','full RIP qword load',raw.hex())
        elif form=='ready':_require(raw==b'\x75\x05','poise-post-ready','JNE skips only exact initializer CALL',raw.hex())
        else:
            _require(len(raw)==6 and raw[:2]==b'\x0f\x85','poise-post-debug-selection','complete JNE',raw.hex());targets[form]=at+6+int.from_bytes(raw[2:],'little',signed=True)
            _require(not pointer<=targets[form]<end,'poise-post-excluded','outside selected fragment',targets[form])
        at+=len(raw)
    _require(at==end,'poise-post-complete-end',end,at)
    return {'actualTargets':targets,'typedDispatchReturnProved':False,'debugBoolTypeProved':False,'selection':'anonymous class dword nonzero skips initializer; opaque debug normal AL low byte zero falls through','resultTransfer':'opaque dispatch normal RAX low64 -> XMM6 low64 -> debug XMM0 and later copy','conditions':['normal opaque dispatch result and ordinary Win64 return','debug preserves nonvolatile XMM6 and caller frame/storage','valid compatible anonymous class storage']}


def copy_ranges(rsp,source,destination,size):
    _require(all(type(v) is int for v in (rsp,source,destination,size)) and size>0,'poise-copy-range-input','integer ranges',[rsp,source,destination,size])
    src=rsp+source;dst=rsp+destination
    valid=0<=rsp<2**64 and all(0<=v and v+size<=2**64 for v in (src,dst))
    return {'source':src,'destination':dst,'nonwrapping':valid,'disjoint':valid and (src+size<=dst or dst+size<=src),'aligned16':valid and src%16==0 and dst%16==0,'liveBackingObserved':False}


def _partition(raw,pointer,lengths):
    rows=[];at=0
    for size in lengths:
        _require(at+size<=len(raw),'poise-fragment-truncated','complete raw instruction',len(raw)-at)
        rows.append({'va':hex(pointer+at),'bytes':raw[at:at+size].hex()});at+=size
    _require(at==len(raw),'poise-fragment-coverage','complete selected bytes',[at,len(raw)])
    return rows


def check_poise_copy(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_value_type
    from scripts.game_data.damage_snapshot_multiply_formula_flow import check_result_records
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','poise-fresh-result','fresh sole Double result layout',consumer_proof.get('claim'))
    selected=NativeReferenceContext(index.image,index=index);owner=spec['packType'];td=index.types[owner]
    _require(selected.is_value_type(owner),'poise-value-owner','selected native value type',owner)
    field_owner,field_type,boxed_field=selected.field(spec['resultField'])
    _require((field_owner,field_type)==(owner,spec['resultType']),'poise-result-field-owner',[owner,spec['resultType']],[field_owner,field_type])
    fields=[f for f in index.metadata.fields_for(td) if index.metadata.string(f.name_index)==spec['resultField'].split('::')[1]]
    _require(len(fields)==1,'poise-result-field-unique',1,len(fields));field=fields[0]
    require_ordinary_value_type(selected,field.type_index,spec['resultType'],'poise.resultField')
    result_owner,result_method=consumer_proof['symbol'].rsplit('.',1);result_body=index.body(result_owner,result_method)
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(result_body.pointer,()) if f"{r.get('type')}.{r.get('method')}"==consumer_proof['symbol']]
    prior=[index.pe.bytes_at_va(selected.type_pointer(m.return_type),16) for m in methods]
    check_result_records(index.pe.bytes_at_va(selected.type_pointer(field.type_index),16),prior)
    header=spec['unboxedHeaderBytes'];_require(header==16,'poise-boxed-adjustment','reviewed value header',header)
    cell=int(index.image.registration['typeDefinitionsSizes'],16)+td.index*8;size_pointer=index.pe.u64_at_va(cell)
    _require(size_pointer!=0,'poise-size-cell','nonzero selected native row',hex(cell))
    size_row=index.pe.bytes_at_va(size_pointer,16);_require(len(size_row)==16,'poise-size-row',16,len(size_row))
    boxed_size=int.from_bytes(size_row[:4],'little');size=boxed_size-header;result_offset=boxed_field-header
    body=index.body(spec['type'],spec['method']);_require(body.pointer in index.extents,'poise-caller-range','actual selected pdata',hex(body.pointer))
    end=index.extents[body.pointer];_require(0<end-body.pointer<=65536,'poise-caller-bound','bounded physical range',end-body.pointer)
    raw=index.pe.bytes_at_va(body.pointer,end-body.pointer);source=spec['anonymousSourceDisp32'];dest=spec['anonymousDestinationDisp32']
    marker=b'\x0f\x28\x84\x24'+struct.pack('<i',source)+b'\x0f\x29\x84\x24'+struct.pack('<i',dest)
    positions=[at for at in range(len(raw)) if raw.startswith(marker,at)]
    matches=[];rejected=[]
    for at in positions:
        if not (at>=54 and at+94<=len(raw)):
            rejected.append({'offset':at,'reason':'incomplete bounded fragment'});continue
        try:
            post=check_postdispatch(_partition(raw[at-54:at],body.pointer+at-54,[5,5,7,7,2,5,4,3,3,5,2,6]),body.pointer+at-54,body.pointer+at)
            copy=check_copy(_partition(raw[at:at+94],body.pointer+at,[8,8,8,8,8,4,8,8,8,8,9,9]),body.pointer+at,body.pointer+at+94,source,dest,result_offset,size)
            matches.append((at,post,copy))
        except ValueError as exc:
            rejected.append({'offset':at,'reason':str(exc)[:256]})
    _require(len(matches)==1,'poise-copy-unique','one complete postdispatch plus copy grammar',{'matchingCount':len(matches),'rejectedCandidates':rejected})
    at,post,copy=matches[0]
    return {**post,**copy,'symbol':body.symbol,'claim':'poiseOpaqueResultLowHalfToTypedPackViewAndCopy',
        'selectedPhysicalPdataRange':[hex(body.pointer),hex(end)],'fragmentEntry':hex(body.pointer+at-54),'fragmentEnd':hex(body.pointer+at+94),
        'selectedValueOwner':owner,'selectedBoxedBytes':boxed_size,'conditionalUnboxedBytes':size,'conditionalResultUnboxedOffset':result_offset,
        'typedFieldViewTier':'conditional','boxedToUnboxedAdjustmentProved':False,'reviewedHeaderAssumptionBytes':header,
        'conditions':post['conditions']+copy['conditions']+['selected live value storage uses the reviewed boxed-to-unboxed header adjustment'],
        'sourceLocalDisp32':source,'destinationLocalDisp32':dest,
        'boundary':'A complete selected raw postdispatch fragment transfers normally returned opaque RAX low64 into XMM6. A nonzero anonymous class dword skips the actual initializer call; an opaque debug target normally returning AL low byte zero selects the complete copy. The actual source chunk is loaded before register-to-register MOVSD replaces only low64; physical MOVAPS stores all sixteen bytes back and to the new buffer, preserving the high eight from that load. Remaining paired vector transfers and scalar tail exactly cover the raw seventy-two-byte span. The selected native boxed size and named calcResult field metadata are authenticated, and the field uses the same concrete selected-image ordinary value definition as the fresh sole-Double consumer result. Subtracting the reviewed header to obtain the unboxed span and the low-eight field view is conditional on that header/storage-layout assumption; no independent boxed-to-unboxed bridge is proved. This is a conditional field view and raw-bit transfer, not a typed dispatch return. Compatible live value layout, valid aligned nonwrapping disjoint storage, same caller frame, ordinary normal returns, XMM6 and storage noninterference remain conditions. Callee internals, Bool debug semantics, actual result production, earlier typed pack initialization, whole Process CFG and final Poise output remain unresolved.'}
