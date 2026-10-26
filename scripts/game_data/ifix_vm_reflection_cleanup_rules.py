"""Authenticate reflection cleanup capture, iteration and writeback requests.

The complete Invoke producer program is a mandatory prerequisite, including
its result-pushed byte and saved-value writes. The caller constructs an ordered array of native local-home addresses,
copies it after a zero prefix word, and forwards that frame to a wrapper. The
wrapper calls the captured cleanup program with frame+8, rereads the prefix,
and returns if zero or requests exception propagation otherwise. Its observed
failure terminal does not authenticate runtime exception transfer.

The callback reads Call.argumentBase through its captured input and writes a
local cursor. A nonzero result-pushed byte advances it by one descriptor and
initializes the signed Int32 loop index to one; otherwise the index is zero.
Each iteration rereads the invoker count and receiver flag. The upper bound
adds one only for a receiver-bearing non-instantiation call. The comparison
uses wrapping Int32 arithmetic and signed ordering. Admitted iterations
request a null managed-array store at the signed Int64 cursor-to-evaluation
base distance divided by descriptor width, truncated toward zero, then advance
the local cursor and increment the local index. This proves a store request;
incoming tags, array validity, helper mutation, aliases and termination stay
conditional. There is no explicit Call.currentTop write in this callback.

After the loop, a receiver flag, value-receiver byte, saved pointer, saved
object and named DeclaringType/IsValueType query gate select a native writeback
request. The callback prepares Marshal's named class, then follows anonymous
class-word recipes: a nonnull selected function pointer receives object or
unboxed data and the saved pointer; a separate admitted layout path requests
copy(savedPointer, object+header, signed class size). Remaining paths request
errors using stored opaque data. Class words are structural selectors, and
the marshalling, copy, class initialization, query and error results are open.

A detached local entry decrements an Int32 depth at a captured container home
and joins the return epilogue. No ordinary callback branch enters it; its
actual native EH delivery and frame identity remain unobserved. Complete
finite programs authenticate all loops, joins, fallthroughs, argument orders,
capture addresses and request sites. Native declarations live in JSON.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_slice,_identity
from scripts.game_data.ifix_vm_wrapper_dispatch_rules import _raw
from scripts.game_data.ifix_vm_reflection_invoker_rules import _invoke_identity,_layouts,_method_carriers,_INVOKE_PROGRAM,validate_reflection_invoker_rules
from scripts.game_data.ifix_vm_call_opcode_rules import _carrier
from scripts.game_data.ifix_vm_reference_update_rules import _type_pointer
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program


class ReflectionCleanupRuleError(ValueError):
    """A reflection cleanup declaration lacks its selected native witness."""


_CAPTURES=['callInput','cursor','resultPushed','resultSkip','index','managedInput','receiverInput','plainCount','plainIndex',
    'receiverCount','receiverIndex','isInstantiateInput','ordinaryCount','ordinaryIndex','extraReceiver','boundCount','boundIndex',
    'valueReceiver','savedPointer','savedObject','contextContainer']
_HELPER_REFS={'cleanupNormal':'reflectionInvokerRules.helpers.cleanupNormal','cleanupCaptured':'reflectionInvokerRules.helpers.cleanupCaptured',
    'managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper','declaringQuery':'genericDelegateFactoryRules.helpers.returnQueryHelper',
    'valueQuery':'objectConversionRules.helpers.typePredicate','classInitialize':'anonymousStoreyRules.helpers.classInitialize',
    'classPrepare':'chainFieldRules.helpers.classPrepare','exceptionPropagate':'newFieldRules.helpers.exceptionPropagate','unwindNull':'newFieldRules.helpers.unwindNull'}
_VIRTUAL_REFS={'declaringType':'referenceAddressRules.virtualMethods.declaringType','isValueType':'reflectionInvokerRules.virtualMethods.isValueType'}
_VIRTUALS={'declaringType':('System.Reflection.MemberInfo','get_DeclaringType',[],'System.Type',False,9),
    'isValueType':('System.Type','IsValueTypeImpl',[],'bool',False,97)}
_CLAIMS=dict(schema='endfield.ifix-vm-reflection-cleanup-rules.v1',evidenceBoundary='conditional',executionBoundary='unobserved',
    helperRefs=_HELPER_REFS,virtualRefs=_VIRTUAL_REFS,usageRef='objectOpcodeRules.usageCells.cell01',captureOrder=_CAPTURES,
    captureRecipe='ordered-native-home-addresses;copy-after-zero-prefix;wrapper-callback-frame-plus8;prefix-reread-after-callback',
    loopRecipe='cursor=Call.argumentBase;resultPushed:skip-one;index=resultPushed!=0;bound=wrapping-i32(paramCount+(hasThis&&!isInstantiate));signed-comparison;null-managed-store-at-trunc-i64((cursor-Call.evaluationStackBase)/12);cursor-plus12;index-plus1',
    writebackRecipe='hasThis-and-valueReceiver-and-savedPointer-and-savedObject;DeclaringType-slot9;IsValueType-slot97;anonymous-class-function-or-signed-size-copy-request',
    depthRecipe='detached-entry:decrement-Int32-at-captured-context-container-plus24;common-return-join',
    callTopBoundary='no-explicit-Call.currentTop-write-in-callback',
    storageBoundary='valid-stable-Call-invoker-native-homes-captured-addresses-managed-array-and-class-storage;normal-nonmutating-helper-returns;no-unmodelled-alias',
    loopBoundary='signed-Int32-wrapping-counters-and-bound;runtime-counts-capacity-aliases-and-termination-unobserved',
    writebackBoundary='anonymous-class-word-function-layout-and-copy-requests-only;framework-marshalling-and-memory-effects-unobserved',
    exceptionBoundary='failure-request-native-fallthrough-if-returned;detached-entry-and-EH-delivery-frame-identity-unobserved',
    runtimeBoundary='actual-reflection-result-framework-query-class-init-store-copy-error-results-and-execution-unobserved')
_OWN={'nativeCopy','errorFromData','errorFromPair','errorTransfer'}
_DATA={'opaqueDataA','opaqueDataB','opaqueDataC','opaqueDataD'}


def _need(ok: bool,detail: str) -> None:
    if not ok:raise ReflectionCleanupRuleError('reflectionCleanup.'+detail)


def _program(name: str,at: int,targets: dict,cells: dict) -> tuple[bytes,dict]:
    tokens=_PROGRAMS[name];labels={};offset=0
    for token in tokens:
        if isinstance(token,str):offset+=len(bytes.fromhex(token));continue
        kind,*args=token
        if kind=='label':_need(args[0]not in labels,'duplicate finite label');labels[args[0]]=at+offset
        elif kind=='call':offset+=5
        elif kind=='edge':offset+=len(bytes.fromhex(args[0]))+args[2]
        elif kind=='rip':offset+=len(bytes.fromhex(args[0]))+4
        else:_need(False,'unknown finite token')
    out=bytearray()
    for token in tokens:
        if isinstance(token,str):out.extend(bytes.fromhex(token));continue
        kind,*args=token
        if kind=='label':continue
        if kind=='call':prefix=b'\xe8';target=targets[args[0]];width=4
        elif kind=='edge':prefix=bytes.fromhex(args[0]);target=labels[args[1]];width=args[2]
        else:prefix=bytes.fromhex(args[0]);target=cells[args[1]];width=4
        out.extend(prefix+(target-(at+len(out)+len(prefix)+width)).to_bytes(width,'little',signed=True))
    _need(len(out)==offset,'finite extent differs');return bytes(out),labels


def _capture_program(spec: dict) -> bytes:
    homes=spec['captureHomes'];start=spec['captureSourceHome'];frame=spec['framePrefixHome']
    _need(set(homes)==set(_CAPTURES) and all(type(x)is int and 0<=x<65536 for x in list(homes.values())+[start,frame])
        and len(set(homes.values()))==len(homes),'distinct bounded capture homes required')
    prefix=bytes.fromhex(_INVOKE_PROGRAM[0]);depth=7*8+int.from_bytes(prefix[-9:-5],'little')
    _need(homes['receiverInput']==depth+8 and homes['callInput']==depth+24 and homes['isInstantiateInput']==depth+32,
        'capture input homes differ from inherited native ABI')
    out=bytearray()
    for ordinal,name in enumerate(_CAPTURES):
        off=homes[name]
        out.extend(bytes.fromhex('488d4424')+bytes([off])if off<=127 else bytes.fromhex('488d8424')+off.to_bytes(4,'little'))
        out.extend(bytes.fromhex('48898424')+(start+ordinal*8).to_bytes(4,'little'))
    out.extend(bytes.fromhex('48899c24')+frame.to_bytes(4,'little')+bytes.fromhex('488d8c24')+(frame+8).to_bytes(4,'little')+bytes.fromhex('488d8424')+start.to_bytes(4,'little'))
    out.extend(bytes.fromhex('0f10000f11010f1048100f1149100f1040200f1141200f1048300f1149300f1040400f1141400f1048500f1149500f1040600f114160ba800000004803ca0f1040700f1141f00f100c100f11090f104410100f114110488b44102048894120'))
    return bytes(out)


def validate_reflection_cleanup_rules(image: Any,spec: dict,contract: dict,extents: dict) -> dict:
    _need(all(type(spec.get(k))is type(v) and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/claim/boundary')
    _need(set(spec['helpers'])==_OWN and set(spec['opaqueData'])==_DATA,'owned request/data set differs')
    # Captured home names depend on Invoke's producers, not just its ABI and
    # address-array copy. Authenticate the complete finite prerequisite even
    # when this component is called independently of the parent validator.
    validate_reflection_invoker_rules(image,contract['reflectionInvokerRules'],contract,extents)
    at,body,_token=_invoke_identity(image,contract,extents);_layouts(image,contract['reflectionInvokerRules'],contract)
    prefix=bytes.fromhex(_INVOKE_PROGRAM[0]);_expect(body[:len(prefix)],prefix,'Invoke ABI')
    window=spec['captureWindow'];raw=_slice(body,at,_rva(window['rva']),window['byteCount'],'Invoke capture window');_hash(raw,window,'captureWindow');_expect(raw,_capture_program(spec),'captureWindow')
    targets={};rows={}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);where=_rva(row['rva']);count=row['byteCount'];_hash(image.pe.bytes_at_va(image.pe.image_base+where,count),row,name);targets[name]=where;rows[name]=row
    for name,row in spec['helpers'].items():
        _need(row.get('effectBoundary')=='opaque-callee-request-only' and type(row.get('byteCount'))is int and row['byteCount']==16,'opaque request prefix differs')
        where=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+where,16),row,name);targets[name]=where
    for name,identity in _VIRTUALS.items():
        row=_ref(contract,_VIRTUAL_REFS[name]);_identity(image,row,identity[:5],name,extents,virtual_slot=identity[5]);_method_carriers(image,row,identity)
    # Only the common slot/pair-selection prefix is interpreted, not the
    # framework's pointer-identity fast paths or returned Type predicates.
    for name,before,after in [('declaringQuery','48895c240855565741544155415641574883ec50488bfa0fb7d9488b0a','488d431448c1e0044803074c8b00488b5008'),
        ('valueQuery','48895c2408574883ec200fb7d9488bfa488b0a','488d4b1448c1e10448030f488b01488b5108')]:
        p=_Program(targets[name]);p.add(before);p.call(targets['classPrepare']);p.add(after);expected=p.finish()
        _expect(image.pe.bytes_at_va(image.pe.image_base+targets[name],len(expected)),expected,name+' slot pair prefix')
    cells={};row=_ref(contract,spec['usageRef']);cell=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+cell,8)
    _need(row.get('usageTag')==1 and row.get('identity')=='System.Runtime.InteropServices.Marshal' and raw==bytes.fromhex(row['rawHex']),'named Marshal cell differs')
    index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='cleanup.Marshal',offset=cell)
    _carrier(image,_type_pointer(image,index),'System.Runtime.InteropServices.Marshal');cells['marshalType']=cell
    for name,row in spec['opaqueData'].items():
        _need(row.get('evidenceBoundary')=='structuralOnly' and row.get('meaning')=='opaque-error-request-data' and type(row.get('byteCount'))is int and 1<=row['byteCount']<=256,'opaque data boundary differs')
        where=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+where,row['byteCount']),row,name);cells[name]=where
    labels={}
    for name in ('cleanupNormal','cleanupCaptured'):
        raw=_raw(image,dict(rows[name],name=name),extents);expected,selected=_program(name,targets[name],targets,cells);_expect(raw,expected,name);labels[name]=selected
    return dict(status='validated_conditional_reflection_cleanup_rules',evidenceBoundary='conditional',executionBoundary='unobserved',
        captureRecipe=spec['captureRecipe'],loopRecipe=spec['loopRecipe'],writebackRecipe=spec['writebackRecipe'],depthRecipe=spec['depthRecipe'],
        callTopBoundary=spec['callTopBoundary'],storageBoundary=spec['storageBoundary'],loopBoundary=spec['loopBoundary'],writebackBoundary=spec['writebackBoundary'],
        exceptionBoundary=spec['exceptionBoundary'],runtimeBoundary=spec['runtimeBoundary'],captureHomes=spec['captureHomes'],
        unresolved=['live-Call-and-captured-home-storage-aliases','managed-store-query-class-marshalling-copy-and-error-results','loop-termination-and-capacity','detached-entry-and-EH-callback-delivery-frame-identity','actual-execution'])


def validate_selected_reflection_cleanup_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.reflection-cleanup')
    return validate_reflection_cleanup_rules(image,contract['reflectionCleanupRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
_PROGRAMS = {'cleanupNormal': ['40534883ec20488bd94883c108',
                   ('call', 'cleanupCaptured'),
                   '48833b00',
                   ('edge', '75', 'join0', 1),
                   '4883c4205bc3',
                   ('label', 'join0'),
                   '488b0b',
                   ('call', 'exceptionPropagate'),
                   'cc'],
 'cleanupCaptured': ['48895c2410488974241848894c2408574883ec30488bd9488b01488b08488b11488b4308488910488b4310803800',
                     ('edge', '74', 'join0', 1),
                     '488b4308488b084883c10c488908',
                     ('label', 'join0'),
                     '488b4310488b4b1833ff4038388bc7',
                     ('edge', '74', 'join1', 1),
                     'b801000000',
                     ('label', 'join1'),
                     '8901488b4318488b4b208b00890148beabaaaaaaaaaaaa2a0f1f4000',
                     ('label', 'join8'),
                     '488b43208b10488b4330488b08448b411080791400',
                     ('edge', '75', 'join2', 1),
                     '488b4338448900488b43408910',
                     ('edge', 'eb', 'join3', 1),
                     ('label', 'join2'),
                     '488b4348448900488b43508910488b4358488b53488038008b02',
                     ('edge', '74', 'join4', 1),
                     '488b4b388901488b4350488b4b408b008901',
                     ('label', 'join3'),
                     '488b43708938488b4338488b4b788b008901488b4340',
                     ('edge', 'eb', 'join5', 1),
                     ('label', 'join4'),
                     '488b4b608901488b4350488b4b688b008901488b4370c70001000000488b4360488b4b788b008901488b4368',
                     ('label', 'join5'),
                     '488b8b800000008b008901488b4378488b4b708b100311488b83800000003910',
                     ('edge', '7d', 'join6', 1),
                     '488b4328488b084885c9',
                     ('edge', '0f84', 'join7', 4),
                     '488b03488b10488b43084c8b004c2b4208488bc649f7e848d1fa488bc248c1e83f4803d04533c0',
                     ('call', 'managedStore'),
                     '488b4308488b084883c10c488908488b43208b08ffc18908',
                     ('edge', 'e9', 'join8', 4),
                     ('label', 'join6'),
                     '488b4330488b0880791400',
                     ('edge', '0f84', 'join9', 4),
                     '488b8388000000803800',
                     ('edge', '0f84', 'join9', 4),
                     '488b839000000048833800',
                     ('edge', '0f84', 'join9', 4),
                     '488b839800000048833800',
                     ('edge', '0f84', 'join9', 4),
                     '488b4330488b08488b51304885d2',
                     ('edge', '0f84', 'join7', 4),
                     'b909000000',
                     ('call', 'declaringQuery'),
                     '4885c0',
                     ('edge', '0f84', 'join7', 4),
                     'b961000000488bd0',
                     ('call', 'valueQuery'),
                     '84c0',
                     ('edge', '0f84', 'join9', 4),
                     '488b8398000000488b38488b8390000000488b18',
                     ('rip', '488b0d', 'marshalType'),
                     '83b9e000000000',
                     ('edge', '75', 'join10', 1),
                     ('call', 'classInitialize'),
                     ('label', 'join10'),
                     '4885ff',
                     ('edge', '0f84', 'join11', 4),
                     '4885db',
                     ('edge', '0f84', 'join12', 4),
                     '4c8b0f4983797000',
                     ('edge', '74', 'join13', 1),
                     '498b41704883780800',
                     ('edge', '74', 'join13', 1),
                     '4c8b4008488d47104180792a12480f45f8488bd3488bcf41ffd0',
                     ('edge', 'eb', 'join14', 1),
                     ('label', 'join13'),
                     '4183b904010000ff',
                     ('edge', '74', 'join15', 1),
                     '41f6813801000004',
                     ('edge', '75', 'join15', 1),
                     '4180792a0e',
                     ('edge', '74', 'join15', 1),
                     '4d638104010000488d5710488bcb',
                     ('call', 'nativeCopy'),
                     '90',
                     ('label', 'join14'),
                     ('edge', 'eb', 'join9', 1),
                     '488b442440488b88a0000000ff4918',
                     ('label', 'join9'),
                     '488b5c2448488b7424504883c4305fc3',
                     ('label', 'join7'),
                     ('call', 'unwindNull'),
                     '90',
                     ('label', 'join11'),
                     ('rip', '488d0d', 'opaqueDataA'),
                     ('call', 'errorFromData'),
                     '33d2488bc8',
                     ('call', 'errorTransfer'),
                     ('label', 'join12'),
                     ('rip', '488d0d', 'opaqueDataB'),
                     ('call', 'errorFromData'),
                     '33d2488bc8',
                     ('call', 'errorTransfer'),
                     ('label', 'join15'),
                     '4983796000',
                     ('edge', '75', 'join16', 1),
                     '41f6813801000010',
                     ('edge', '75', 'join16', 1),
                     ('rip', '488d15', 'opaqueDataC'),
                     ('rip', '488d0d', 'opaqueDataA'),
                     ('call', 'errorFromPair'),
                     ('edge', 'eb', 'join17', 1),
                     ('label', 'join16'),
                     ('rip', '488d15', 'opaqueDataD'),
                     ('rip', '488d0d', 'opaqueDataA'),
                     ('call', 'errorFromPair'),
                     ('label', 'join17'),
                     '33d2488bc8',
                     ('call', 'errorTransfer'),
                     'cccc']}

