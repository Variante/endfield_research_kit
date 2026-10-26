"""IFix-local finite opcode selection and the selected default request route.

Only position-bound CMP ECX,R13D=0 and SUB ECX,ESI=12 extend the existing
immediate comparison/subtraction grammar. Reviewed entry boundaries terminate
the walk; an unknown instruction at any other point fails closed. Enum members
that reach the default route are a conditional family, not missing bodies to
invent. The first StackSpace header is handled before this ordinary loop.
Default requests Code.ToString, boxing the authored operand, String.Concat,
and NotImplementedException/throwRuntimeException. Message results, throwing,
runtime state and actual entry are unobserved; normal return reaches PC advance.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import literal_record, unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_slice,_hash,_expect,_type,_identity
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES


class DispatchRuleError(ValueError):
    """A selected switch/default declaration lacks its finite native witness."""


def _need(ok: bool,label: str) -> None:
    if not ok:raise DispatchRuleError('ifix-dispatch.'+label)


def resolve_selected_dispatch_entry(body: bytes,body_rva: int,start_rva: int,opcode_id: int,*,
                                   zero_compare_rva: int,sub_esi_rva: int,entry_rvas: set[int]) -> int:
    """Walk the reviewed switch only; never treat an arbitrary unknown as an entry."""
    _need(type(opcode_id) is int and 0<=opcode_id<=0x7fffffff,'opcode outside selected positive Int32 domain')
    pc,value,flags,seen=start_rva,opcode_id,None,set()
    for _ in range(64):
        _need(pc not in seen,'repeated dispatcher PC');seen.add(pc)
        if pc in entry_rvas:return pc
        raw=_slice(body,body_rva,pc,3,'dispatch')
        if raw==bytes.fromhex('413bcd'):
            _need(pc==zero_compare_rva,'register-zero comparison at unknown site');immediate,size,subtract=0,3,False
        elif raw[:2]==bytes.fromhex('2bce'):
            _need(pc==sub_esi_rva,'slot-width subtraction at unknown site');immediate,size,subtract=12,2,True
        elif raw[:2] in (bytes.fromhex('83f9'),bytes.fromhex('83e9'),bytes.fromhex('81f9'),bytes.fromhex('81e9')):
            width=1 if raw[0]==0x83 else 4
            immediate=int.from_bytes(_slice(body,body_rva,pc+2,width,'dispatch.immediate'),'little',signed=True)
            size,subtract=2+width,raw[1]==0xe9
        else:
            near=raw[:2] in (bytes.fromhex('0f84'),bytes.fromhex('0f85'),bytes.fromhex('0f8f'),bytes.fromhex('0f8e'))
            short=raw[0] in (0x74,0x75,0x7f,0x7e)
            _need((near or short) and flags is not None,f'unknown dispatch instruction rva={pc:#x} bytes={raw.hex()}')
            equal,greater=flags;condition=raw[1] if near else raw[0]
            selected={0x84:equal,0x85:not equal,0x8f:greater,0x8e:not greater,0x74:equal,0x75:not equal,0x7f:greater,0x7e:not greater}[condition]
            size=6 if near else 2;disp=int.from_bytes(_slice(body,body_rva,pc+(2 if near else 1),4 if near else 1,'dispatch.branch'),'little',signed=True)
            pc=pc+size+disp if selected else pc+size;continue
        flags=(value==immediate,value>immediate)
        if subtract:value=((value-immediate+0x80000000)&0xffffffff)-0x80000000
        pc+=size
    _need(False,'dispatcher step bound exceeded')


_METHODS={
    'enumToString':('System.Enum','ToString',[],'string',False),
    'concat':('System.String','Concat',['object','object','object'],'string',True),
    'notImplementedCtor':('System.NotImplementedException','.ctor',['string'],'void',False),
}
_CELL_NAMES={'codeType':(1,'IFix.Core.Code'),'intType':(1,'int'),'spaceLiteral':(5,' '),
             'notImplementedType':(1,'System.NotImplementedException')}
_BLOCKS={
    'default':('4c8d442470',('rip','488b15','codeType'),'488d8c24f0020000',('call','typeCarrier'),
        '33d2488d8c24f0020000',('call','enumToString'),'488bd8498bce',('call','nullCheck'),
        '418b4e04898c2420010000488d942420010000',('rip','488b0d','intType'),('call','boxOperand'),
        '4533c94c8bc0',('rip','488b15','spaceLiteral'),'488bcb',('call','concat'),('jump','exceptionMessage')),
    'exceptionMessage':('488bf8',('rip','488b0d','notImplementedType'),('call','allocateObject'),
        '488bd8488bc8',('call','nullCheck'),'4533c0488bd7488bcb',('call','notImplementedCtor'),
        '488b8c24f0030000488bd341b0014533c9',('call','runtimeException'),('jump','defaultPcJoin')),
    'defaultPcJoin':(('jump','pcAdvance'),),
}
_HELPER_REFS={'typeCarrier':'instanceFieldRules.helpers.typeCarrier','nullCheck':'negativeFieldRules.helpers.nullCheck'}
_TAIL_REFS={'zeroRegister':'basicOpcodeRules.sharedWindows.zeroRegister','slotWidth':'basicOpcodeRules.sharedWindows.slotWidth',
            'loopState':'basicOpcodeRules.sharedWindows.loopState','pcAdvance':'basicOpcodeRules.sharedWindows.pcAdvance'}


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int]) -> bytes:
    p=_Program(at)
    for token in _BLOCKS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='jump':p.rip('e9',targets[args[0]])
        else:_need(False,'unknown default program token')
    return p.finish()


def validate_dispatch_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,
                            extents: dict[int,int]) -> dict:
    """Validate switch selection and default requests in one authenticated image."""
    _need(spec.get('schema')=='endfield.ifix-vm-dispatch-rules.v1' and spec.get('evidenceBoundary')=='conditional'
          and spec.get('executionBoundary')=='unobserved' and spec.get('scope')=='ordinary-Execute-loop-after-entry-header'
          and spec.get('defaultBoundary')=='request-only-message-throwing-and-runtime-state-unobserved'
          and spec.get('methodRefs')=={'runtimeException':'delegateConstruction.methodCalls.nullFallbackException'}
          and spec.get('helperRefs')==_HELPER_REFS and spec.get('tailRefs')==_TAIL_REFS,'unsupported schema/reference/boundary')
    members={x['name']:x['id'] for x in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    _need(members==opcode_ids,'actual enum differs from selected opcode layout')
    targets={}
    for name,path in {**_HELPER_REFS,**_TAIL_REFS}.items():
        row=_ref(contract,path);at=_rva(row['rva'])
        raw=_slice(body,body_rva,at,row['byteCount'],name) if name in _TAIL_REFS else image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount'])
        _hash(raw,row,name);targets[name]=at
    _expect(_slice(body,body_rva,targets['zeroRegister'],3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister')
    _expect(_slice(body,body_rva,targets['slotWidth'],5,'slotWidth'),bytes.fromhex('be0c000000'),'slotWidth')
    extensions=spec['extensions'];_need(set(extensions)=={'zeroCompare','subEsi'},'unknown switch extension')
    for name,shape in {'zeroCompare':'413bcd','subEsi':'2bce'}.items():
        row=extensions[name];raw=_slice(body,body_rva,_rva(row['rva']),row['byteCount'],name);_hash(raw,row,name);_expect(raw,bytes.fromhex(shape),name)
    entries=spec['entryPoints'];mapped={row['opcode']:row for row in entries}
    _need(len(entries)==len(mapped) and set(mapped)==set(opcode_ids),'missing/duplicate/unknown enum entry')
    reviewed=set()
    for name,row in mapped.items():
        _need(row['opcodeId']==opcode_ids[name],'enum ID differs: '+name)
        window=row['window'];at=_rva(window['rva']);_need(at==_rva(row['entryRva']),'entry witness not at entry: '+name)
        raw=_slice(body,body_rva,at,window['byteCount'],'entry.'+name)
        _hash(raw,window,'entry.'+name)
        head=_slice(body,body_rva,at,3,'entry-head.'+name)
        _need(head not in (bytes.fromhex('413bcd'),) and head[:2] not in
              tuple(bytes.fromhex(x) for x in ('2bce','83f9','83e9','81f9','81e9','0f84','0f85','0f8f','0f8e'))
              and head[0] not in (0x74,0x75,0x7f,0x7e),'entry stops inside dispatcher: '+name)
        reviewed.add(at)
    start=_rva(contract['basicOpcodeRules']['dispatchStartRva'])
    for name,row in mapped.items():
        entry=resolve_selected_dispatch_entry(body,body_rva,start,row['opcodeId'],zero_compare_rva=_rva(extensions['zeroCompare']['rva']),
            sub_esi_rva=_rva(extensions['subEsi']['rva']),entry_rvas=reviewed)
        _need(entry==_rva(row['entryRva']),'selected enum route differs: '+name)
    methods={row['name']:row for row in spec['methods']};_need(len(methods)==len(spec['methods']) and set(methods)==set(_METHODS),'default method set differs')
    for name,identity in _METHODS.items():targets[name]=_identity(image,methods[name],identity,name,extents)
    targets['runtimeException']=_identity(image,_ref(contract,'delegateConstruction.methodCalls.nullFallbackException'),
        ('IFix.Core.VirtualMachine','throwRuntimeException',['System.Exception','bool'],'void',False),'runtimeException',extents)
    helpers={row['name']:row for row in spec['helpers']};_need(len(helpers)==len(spec['helpers']) and set(helpers)=={'boxOperand','allocateObject'},'default helper set differs')
    for name,row in helpers.items():
        _need(row.get('effectBoundary')=='opaque-callee-request-only','helper outcome promoted: '+name)
        at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,name);targets[name]=at
    rows={row['name']:row for row in spec['usageCells']};_need(len(rows)==len(spec['usageCells']) and set(rows)==set(_CELL_NAMES),'default cell set differs');cells={}
    for name,(tag,identity) in _CELL_NAMES.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(row.get('usageTag')==tag and row.get('identity')==identity and raw==bytes.fromhex(row['rawHex']),'stored default usage differs: '+name);cells[name]=at
        if tag==1:
            index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='ifix-dispatch.'+name,offset=at)
            _need(_type(image,index)==identity,'raw non-byref default carrier differs: '+name)
        else:
            md=image.metadata;table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData'];idx=unresolved_usage_index(raw,table.size//8,tag=5,source='ifix-dispatch.literal',offset=at)
            off=table.offset+idx*8;begin,size=literal_record(md.buf[off:off+8],pool.size,source='ifix-dispatch.literal',offset=off)
            _need(md.buf[pool.offset+begin:pool.offset+begin+size]==b' ','stored concat separator differs')
    blocks={row['name']:row for row in spec['blocks']};_need(len(blocks)==len(spec['blocks']) and set(blocks)==set(_BLOCKS),'default block set differs')
    targets.update({name:_rva(row['rva']) for name,row in blocks.items()})
    for name,row in blocks.items():
        raw=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(raw,row,name);_expect(raw,_program(name,targets[name],targets,cells),'default.'+name)
    defaults=sorted(name for name,row in mapped.items() if _rva(row['entryRva'])==targets['default'])
    _need(defaults==sorted(spec['defaultOpcodes']),'default enum family differs')
    return {'status':'validated_conditional_ifix_dispatch','evidenceBoundary':'conditional','executionBoundary':'unobserved',
      'ordinaryLoopEnumCount':len(entries),'distinctEntryCount':len(reviewed),'defaultOpcodes':defaults,'defaultOpcodeCount':len(defaults),
      'scope':spec['scope'],'defaultBoundary':spec['defaultBoundary'],
      'unresolved':['actual-loop-entry-and-PC-values','Enum.ToString-boxing-Concat-and-exception-message-results',
                    'throwRuntimeException-control-outcome','runtime-helper-alias-mutation','actual-execution']}


def validate_selected_dispatch_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Explicit selected-input gate; no game-root fallback or native execution."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'native input hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.dispatch');extents=image.mapper.pdata_function_extents(image.pe)
    base=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    body=image.pe.bytes_at_va(image.pe.image_base+base,contract['consumer']['bodyBytes'])
    ids={x['name']:x['id'] for x in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_dispatch_rules(image,contract['dispatchRules'] if spec is None else spec,body,base,ids,contract,extents)
