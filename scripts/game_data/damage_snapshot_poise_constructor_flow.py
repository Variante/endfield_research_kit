"""Authenticate complete selected Poise constructor caller transfer."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target

def check_caller(rows,tail,pointer,main_end,tail_pointer,tail_end,buffer,published,patch_target,ctor_target):
    forms=['root',b'\x83\xb9\xe0\x00\x00\x00\x00',b'\x75\x05','excluded-init',b'\x33\xd2','patch-id','patch',b'\x84\xc0','patch-excluded',b'\x0f\x57\xc0',b'\x33\xc0']
    forms += [b'\x0f\x11\x84\x24'+struct.pack('<i',buffer+k) for k in (0,16,32,48)]
    forms += [b'\x48\x89\x84\x24'+struct.pack('<i',buffer+64),b'\x48\x89\x74\x24\x28',b'\x48\x89\x74\x24\x20',b'\x4c\x8b\xcb',b'\x4d\x8b\xc6',b'\x48\x8b\x54\x24\x78',b'\x48\x8d\x8c\x24'+struct.pack('<i',buffer),'ctor',b'\xf2\x0f\x10\x84\x24'+struct.pack('<i',buffer+64)]
    forms += [b'\x0f\x10'+bytes([0x84+reg*8,0x24])+struct.pack('<i',buffer+k) for reg,k in ((1,48),(2,32),(3,16),(4,0))]
    forms+=['tail-jump'];_require(len(rows)==len(forms),'poise-ctor-length',len(forms),len(rows));at=pointer;targets={}
    for row,form in zip(rows,forms):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'poise-ctor-contiguity',at,row['va'])
        if isinstance(form,bytes):_require(raw==form,'poise-ctor-instruction',form.hex(),raw.hex())
        elif form=='root':_require(len(raw)==7 and raw[:3]==b'\x48\x8b\x0d','poise-ctor-root','full RIP qword load',raw.hex())
        elif form=='patch-id':_require(len(raw)==5 and raw[0]==0xb9,'poise-ctor-patch-id','full Int32 immediate',raw.hex())
        elif form=='patch-excluded':
            _require(len(raw)==2 and raw[0]==0x75,'poise-ctor-patch-branch','JNE',raw.hex());targets[form]=at+2+int.from_bytes(raw[1:],'little',signed=True)
            _require(targets[form]==main_end,'poise-ctor-patch-excluded','immediate excluded patched entry',targets[form])
        elif form=='tail-jump':
            _require(len(raw)==2 and raw[0]==0xeb and at+2+int.from_bytes(raw[1:],'little',signed=True)==tail_pointer,'poise-ctor-tail-jump',tail_pointer,raw.hex())
        else:
            _require(len(raw)==5 and raw[0]==0xe8,'poise-ctor-call','full direct CALL',raw.hex());targets[form]=relative_branch_target(raw,at,source='poiseCtor')
            if form in ('patch','ctor'):_require(targets[form]==(patch_target if form=='patch' else ctor_target),'poise-ctor-call-identity',form,targets[form])
        at+=len(raw)
    _require(at==main_end,'poise-ctor-main-end',main_end,at)
    stores=[b'\x0f\x29'+bytes([0x84+reg*8,0x24])+struct.pack('<i',published+k) for reg,k in ((4,0),(3,16),(2,32),(1,48))]+[b'\xf2\x0f\x11\x84\x24'+struct.pack('<i',published+64)]
    _require(len(tail)==len(stores),'poise-ctor-publication-length',len(stores),len(tail));at=tail_pointer
    for row,expected in zip(tail,stores):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at and raw==expected,'poise-ctor-publication',[at,expected.hex()],[row['va'],raw.hex()]);at+=len(raw)
    _require(at==tail_end,'poise-ctor-tail-end',tail_end,at)
    return {'zeroedBytesBeforeConstructor':72,'constructorNormalReturnTransferBytes':72,'actualTargets':targets,'selectedDirectJumpTarget':tail_pointer,'constructorInternalInitializationProved':False,'preCallZeroSurvivesConstructorProved':False,'laterModifierPreservationProved':False}


def require_mask_enum(selected,type_index,expected):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_value_type
    proof=require_ordinary_value_type(selected,type_index,expected,'poise.constructor.mask')
    _require(selected.is_enum(expected),'poise-mask-enum-owner','System.Enum parent',selected.parent(expected))
    td=selected.index.types[expected];fields=[f for f in selected.image.metadata.fields_for(td) if not selected.field_attributes(f.type_index)&0x10]
    _require(len(fields)==1 and selected.image.metadata.string(fields[0].name_index)=='value__','poise-mask-enum-storage','sole instance value__',len(fields))
    raw=selected.image.pe.bytes_at_va(selected.type_pointer(fields[0].type_index),16)
    _require(len(raw)==16 and raw[10]==0x0a and raw[11]&0x7f==0 and selected.type_name(fields[0].type_index)=='long','poise-mask-enum-abi','ordinary signed Int64 underlying',raw.hex())
    _require(selected.field(expected+'::value__')==(expected,'long',16),'poise-mask-enum-layout','boxed Int64 at reviewed header',selected.field(expected+'::value__'))
    return proof


def check_poise_constructor_caller(index,copy_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_poise_copy_flow import _partition
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(copy_proof.get('claim')=='poiseOpaqueResultLowHalfToTypedPackViewAndCopy','poise-ctor-fresh-copy','fresh exact raw copy and conditional typed pack view',copy_proof.get('claim'))
    body=index.body(spec['type'],spec['method']);selected=NativeReferenceContext(index.image,index=index)
    _require(copy_proof['symbol']==body.symbol and copy_proof['selectedValueOwner']==spec['packType'] and copy_proof['conditionalUnboxedBytes']==72,'poise-ctor-same-span','same caller raw72 span and conditional typed view',[body.symbol,copy_proof.get('conditionalUnboxedBytes')])
    buffer=copy_proof['destinationLocalDisp32'];published=copy_proof['sourceLocalDisp32']
    _require(body.pointer in index.extents,'poise-ctor-physical-range','actual pdata',body.pointer);end=index.extents[body.pointer]
    _require(0<end-body.pointer<=65536,'poise-ctor-search-bound','bounded physical range',end-body.pointer)
    raw=index.pe.bytes_at_va(body.pointer,end-body.pointer);marker=b'\x0f\x57\xc0\x33\xc0\x0f\x11\x84\x24'+struct.pack('<i',buffer)
    positions=[at-37 for at in range(len(raw)) if raw.startswith(marker,at) and at>=37];matches=[];rejected=[]
    for at in positions:
        try:
            _require(at+159<=len(raw),'poise-ctor-fragment-bounds','complete raw caller',at)
            rows=_partition(raw[at:at+159],body.pointer+at,[7,7,2,5,2,5,5,2,2,3,2,8,8,8,8,8,5,5,3,3,5,8,5,9,8,8,8,8,2])
            patch=relative_branch_target(bytes.fromhex(rows[6]['bytes']),int(rows[6]['va'],16),source='poiseCtorPatch')
            ctor=relative_branch_target(bytes.fromhex(rows[22]['bytes']),int(rows[22]['va'],16),source='poiseCtorTarget')
            jump=int(rows[-1]['va'],16);jump_raw=bytes.fromhex(rows[-1]['bytes']);target=jump+2+int.from_bytes(jump_raw[1:],'little',signed=True)
            _require(body.pointer<=target and target+41<=end,'poise-ctor-publication-range','complete publication within physical pdata',target)
            tail=_partition(index.pe.bytes_at_va(target,41),target,[8,8,8,8,9])
            proof=check_caller(rows,tail,body.pointer+at,body.pointer+at+159,target,target+41,buffer,published,patch,ctor)
            _check_named_provider(index,patch,spec['patchMethod'],['int'],'bool',is_static=True)
            methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(ctor,()) if f"{r.get('type')}.{r.get('method')}"==spec['packType']+'..ctor']
            _require(bool(methods) and all(not m.flags&0x10 for m in methods),'poise-ctor-named-instance','actual named instance constructor',ctor)
            for method in methods:
                args=index.metadata.parameters_for(method);_require(len(args)==4,'poise-ctor-parameter-count',4,len(args))
                require_ordinary_type(selected,method.return_type,'void','poise.constructor.return')
                for arg,expected in zip(args[:2],[spec['abilityType']]*2):require_ordinary_type(selected,arg.type_index,expected,'poise.constructor.actor',reference_kind=0x12)
                require_mask_enum(selected,args[2].type_index,spec['maskType'])
                require_ordinary_type(selected,args[3].type_index,spec['environmentType'],'poise.constructor.environment',reference_kind=0x12)
            symbol=spec['packType']+'..ctor'
            for name,location in (('this',('register','rcx')),('attacker',('register','rdx')),('defender',('register','r8')),('mask',('register','r9')),('actionEnvironment',('stack',40))):
                _require(index.parameter_location(ctor,symbol,name)==location,'poise-ctor-parameter-abi',[name,location],index.parameter_location(ctor,symbol,name))
            matches.append((at,target,proof))
        except ValueError as exc:rejected.append({'offset':at,'reason':str(exc)[:256]})
    _require(len(matches)==1,'poise-ctor-unique','one complete typed request/transfer',{'matchingCount':len(matches),'rejected':rejected})
    at,target,proof=matches[0]
    return {**proof,'symbol':body.symbol,'claim':'poiseConstructorRequestAndNormalPackTransfer','fragmentEntry':hex(body.pointer+at),'publicationEntry':hex(target),
        'rawTransferTier':'exact','typedPackViewTier':'conditional','boxedToUnboxedAdjustmentProved':False,
        'boundary':'The selected anonymous class guard skips initialization and ordinary IFix Bool false selects complete zero stores over the exact raw seventy-two-byte span. A direct actual named instance constructor request passes the stack value address, anonymous actor carriers, ordinary signed Int64 enum mask and ordinary environment reference in authenticated parameter ABI positions (caller stack slot becomes callee entry slot after the return-address push); their live values and receiver compatibility remain conditions. After normal constructor return, full vector/scalar reloads transfer all pack bytes through a direct branch to complete publication at the fresh later raw copy source. The typed pack field/span interpretation remains conditional on the reviewed boxed-to-unboxed header and live-layout assumption. Constructor internals and output values, pre-call zero survival, caller-frame/live-storage validity, normal-return noninterference, subsequent ApplyPoiseModifier effects and later value preservation remain unresolved or conditional; no full Process path or final Poise result is inferred.'}
