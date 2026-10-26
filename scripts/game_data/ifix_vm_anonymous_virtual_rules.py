"""Authenticate plain AnonymousStorey virtual callers and result readers.

The four virtual callers compare their saved method ID with Int32 -1. Equals
then uses receiver pointer equality; GetHashCode shifts the low32 receiver
word and performs a wrapping Int32 multiply; ToString tail-requests the named
System.Object.ToString; Finalize returns. Other IDs, including other negative
values, take the patched caller paths rather than that specific fallback.

Each patched path requests Begin, copies the returned five-word Call, pushes
the saved receiver, optionally pushes Equals' saved argument, and requests
Execute with the reread ID, the authored argument count and zero refCount and
hidden argument. On normal return Equals reads GetBoolean(0), GetHashCode
reads GetInt32(0), ToString forwards a stored typed GetAsType<string> context,
and Finalize returns without an explicit result reader. These are conditional
requests; recursive execution, changed stack state and helper mutation remain
unobserved. Primitive readers compute argumentBase+signedOffset*12, null-check
that descriptor and read Value1 without reading Type or clearing managed slots.

The inherited complete shared GetAsType program prepares its supplied context if needed,
requests GetObject with the signed offset, saves the returned reference, queries
the supplied method context's first type entry, and tail-requests a reference
cast. The stored MethodSpec has a reciprocal one-parameter method-generic
declaration and a non-byref string argument. Static MethodDef-family membership
authenticates the selected direct body; it does not select exact runtime
sharing or establish cast success. GetObject's saved-reference/physical-clear
semantics stay in their existing owning group.

Finalize includes a detached prefix-home propagation path. A nearby separate
complete frame program reads a pointer from an incoming RDX frame home, reads
the qword at that pointer, and writes it to another frame home, returning zero.
No ordinary Finalize branch requests that frame program. Actual EH delivery,
frame association, error transfer and interpretation of that word are open.
Complete finite programs preserve all request arguments, branch joins and
native fallthroughs. Addresses, hashes and changing inventories live in JSON.

The separate ObjectEquals, ObjectGetHashCode and ObjectToString entries
provide finite base-operation programs. ObjectEquals compares the incoming
receiver and object pointers; ObjectGetHashCode shifts the low32 receiver
word and multiplies modulo Int32 width. ObjectToString zeroes the hidden
MethodInfo register and tail-requests the canonical System.Object.ToString.
These registered entries have no selected pdata extent; the proof ends at
their return or unconditional tail and excludes adjacent bytes. Framework
ToString outcomes and actual invocation remain unobserved.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import usage_method_spec
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_identity,_type
from scripts.game_data.ifix_vm_call_opcode_rules import _carrier
from scripts.game_data.ifix_vm_stack_construction_rules import _signature
from scripts.game_data.ifix_vm_call_push_rules import _layout as _call_layout
from scripts.game_data.ifix_vm_new_field_rules import _var,_canonical_target
from scripts.game_data.ifix_vm_generic_bridge_rules import _identity as _bridge_identity,_context_type_leaf
from scripts.game_data.ifix_vm_wrapper_dispatch_rules import _raw
from scripts.game_data.ifix_vm_generic_reference_get_rules import _program as _reference_program
from scripts.game_data.ifix_vm_generic_bridge_rules import _body
from scripts.game_data.ifix_vm_call_scalar_rules import _generic_definition,_program as _scalar_program


class AnonymousVirtualRuleError(ValueError):
    """A plain anonymous virtual caller lacks its selected native witness."""


_METHODS={'Equals':('IFix.Core.AnonymousStorey','Equals',['object'],'bool',False),
    'GetHashCode':('IFix.Core.AnonymousStorey','GetHashCode',[],'int',False),
    'ToString':('IFix.Core.AnonymousStorey','ToString',[],'string',False),
    'Finalize':('IFix.Core.AnonymousStorey','Finalize',[],'void',False),
    'objectToString':('System.Object','ToString',[],'string',False)}
_METHOD_REFS={'begin':'delegateBridgeRules.methods.begin','pushObject':'delegateBridgeRules.methods.pushObject',
    'executeBridge':'delegateBridgeRules.methods.executeBridge','getObject':'genericBridgeRules.getObjectMethod',
    'getBoolean':'callScalarRules.methods.GetBoolean','getInt32':'callScalarRules.methods.GetInt32'}
_READERS={'getBoolean':('IFix.Core.Call','GetBoolean',['int'],'bool',False),'getInt32':('IFix.Core.Call','GetInt32',['int'],'int',False)}
_LEAVES={'ObjectEquals':('IFix.Core.AnonymousStorey','ObjectEquals',['object'],'bool',False),
    'ObjectGetHashCode':('IFix.Core.AnonymousStorey','ObjectGetHashCode',[],'int',False),
    'ObjectToString':('IFix.Core.AnonymousStorey','ObjectToString',[],'string',False)}
_HELPER_REFS={'nullFailure':'referenceUpdateRules.helpers.nullFailure','metadataInitialize':'referenceUpdateRules.helpers.typeInitialize',
    'unwindNull':'newFieldRules.helpers.unwindNull','exceptionPropagate':'newFieldRules.helpers.exceptionPropagate',
    'contextPrepare':'genericBridgeRules.helpers.contextPrepare','contextType':'genericBridgeRules.helpers.contextType','referenceCast':'genericBridgeRules.helpers.referenceCast'}
_CLAIMS=dict(schema='endfield.ifix-vm-anonymous-virtual-rules.v2',evidenceBoundary='conditional',executionBoundary='unobserved',
    methodRefs=_METHOD_REFS,helperRefs=_HELPER_REFS,fieldLayoutRef='anonymousStoreyRules.fieldLayouts',slotBytes=12,
    genericDefinitionRef='callScalarRules.genericDefinition',genericProgramRef='genericReferenceGetRules.candidateProgram',
    fallbackRecipe='ID==-1:Equals-pointer-equality;GetHashCode-low32-receiver-shift3-wrapping-multiply;ToString-System.Object.ToString-tail-request;Finalize-return',
    patchedRecipe='Begin-copy-five-words;push-saved-receiver-and-optional-Equals-argument;Execute-reread-ID-argsCount-2-or1-refCount0-hidden0;normal-result-reader-or-Finalize-return',
    primitiveRecipe='argumentBase+signedOffset*12;descriptor-null-check;GetBoolean:Value1!=0;GetInt32:Value1;no-Type-read-or-managed-clear',
    stringRecipe='stored-GetAsType<string>-context;complete-shared-body-GetObject-offset-context-type-and-reference-cast-requests',
    genericBoundary='stored-typed-MethodSpec-and-registered-MethodDef-family;exact-runtime-sharing-context-resolution-and-cast-result-unobserved',
    finalizeRecipe='ordinary-return-or-detached-prefix-home-propagation;separate-incoming-RDX-frame-word-read-write-and-literal-zero-return',
    leafRecipe='ObjectEquals:incoming-pointer-equality;ObjectGetHashCode:low32-receiver-shift3-wrapping-multiply;ObjectToString:zero-hidden-MethodInfo-tail-System.Object.ToString',
    leafBoundary='exact-registered-finite-entry-through-return-or-tail-without-selected-pdata-function-extent;adjacent-bytes-excluded',
    storageBoundary='valid-stable-receiver-Call-Value-and-managed-storage;normal-native-ABI-nonmutating-helper-returns;overlap-and-live-contents-unobserved',
    exceptionBoundary='native-failure-requests-and-terminals;detached-frame-entry-association-EH-delivery-transfer-and-unwind-unobserved',
    runtimeBoundary='method-ID-validity-thread-stack-Begin-Push-Execute-result-read-query-cast-and-framework-ToString-outcomes-unobserved')
_FIELDS={'unmanagedFields':'IFix.Core.Value[]','managedFields':'object[]','typeId':'int','virtualMachine':'IFix.Core.VirtualMachine',
    'equalMethodId':'int','finalizeMethodId':'int','getHashCodeMethodId':'int','toStringMethodId':'int'}


def _need(ok: bool,detail: str) -> None:
    if not ok:raise AnonymousVirtualRuleError('anonymousVirtual.'+detail)


def _program(name: str,at: int,targets: dict,cells: dict) -> bytes:
    tokens=_PROGRAMS[name];labels={};offset=0
    for token in tokens:
        if isinstance(token,str):offset+=len(bytes.fromhex(token));continue
        kind,*args=token
        if kind=='label':_need(args[0]not in labels,'duplicate finite label');labels[args[0]]=at+offset
        elif kind=='call':offset+=5
        elif kind=='tail':offset+=5
        elif kind=='edge':offset+=len(bytes.fromhex(args[0]))+args[2]
        elif kind=='rip':offset+=len(bytes.fromhex(args[0]))+4+len(bytes.fromhex(args[2]))
        else:_need(False,'unknown finite token')
    out=bytearray()
    for token in tokens:
        if isinstance(token,str):out.extend(bytes.fromhex(token));continue
        kind,*args=token
        if kind=='label':continue
        suffix=b''
        if kind in ('call','tail'):prefix=b'\xe8'if kind=='call'else b'\xe9';target=targets[args[0]];width=4
        elif kind=='edge':prefix=bytes.fromhex(args[0]);target=labels[args[1]];width=args[2]
        else:prefix=bytes.fromhex(args[0]);target=cells[args[1]];width=4;suffix=bytes.fromhex(args[2])
        out.extend(prefix+(target-(at+len(out)+len(prefix)+width+len(suffix))).to_bytes(width,'little',signed=True)+suffix)
    _need(len(out)==offset,'finite extent differs');return bytes(out)


def _layout(image: Any,spec: dict,contract: dict) -> None:
    md=image.metadata;name='IFix.Core.AnonymousStorey';owners=[t for t in md.types if md.type_full_name(t)==name]
    _need(len(owners)==1 and not owners[0].bitfield&1,'reference AnonymousStorey owner required');owner=owners[0];row=_ref(contract,spec['fieldLayoutRef'])[name]
    fields={md.string(f.name_index):f for f in md.fields_for(owner)};offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index)
    _need(set(fields)==set(_FIELDS) and set(row['fields'])==set(_FIELDS) and row['type']==name,'complete anonymous field set differs')
    expected={'unmanagedFields':16,'managedFields':24,'typeId':32,'virtualMachine':40,'equalMethodId':48,'finalizeMethodId':52,'getHashCodeMethodId':56,'toStringMethodId':60}
    for field,typ in _FIELDS.items():
        f=fields[field];pointer=image.pe.u64_at_va(_rva(image.registration['types'])+f.type_index*8);_carrier(image,pointer,typ)
        _need(_type(image,f.type_index)==typ and not int.from_bytes(image.pe.bytes_at_va(pointer,16)[8:10],'little')&16
            and row['fields'][field]=={'type':typ,'offset':expected[field]} and offsets.get(field)==expected[field],'anonymous field carrier/layout differs: '+field)
    _call_layout(image,{'callLayoutRef':'delegateBridgeRules.fieldLayouts.call'},contract)
    values=[t for t in md.types if md.type_full_name(t)=='IFix.Core.Value'];_need(len(values)==1 and values[0].bitfield&1,'Value value-type owner differs')
    fs=[f for f in md.fields_for(values[0])if md.string(f.name_index)=='Value1'];_need(len(fs)==1 and _type(image,fs[0].type_index)=='int'
        and runtime_type_field_offsets(md,image.pe,image.registration,values[0].index).get('Value1')==20,'Value1 int/offset differs')
    pointer=image.pe.u64_at_va(_rva(image.registration['types'])+fs[0].type_index*8);_carrier(image,pointer,'int');_need(not int.from_bytes(image.pe.bytes_at_va(pointer,16)[8:10],'little')&16,'Value1 is static')


def _context(image: Any,spec: dict,targets: dict,contract: dict) -> int:
    row=spec['stringContext'];md=image.metadata;reg=image.registration;cell=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+cell,8)
    _need(row.get('usageTag')==6 and row.get('identity')=='IFix.Core.Call.GetAsType<string>' and raw==bytes.fromhex(row['rawHex']),'string MethodSpec usage differs')
    where=_rva(reg['methodSpecs']);record=usage_method_spec(raw,image.pe.bytes_at_va(where,reg['methodSpecsCount']*12),len(md.methods),reg['genericInstsCount'],source='anonymousVirtual.string',usage_offset=cell,records_offset=where)
    declaration=_ref(contract,spec['genericDefinitionRef']);_generic_definition(image,declaration);method=md.methods[record['definition']]
    _need(record['classInstantiationIndex']==-1 and record['methodInstantiationIndex']>=0 and declaration.get('type')=='IFix.Core.Call'
        and declaration.get('method')=='GetAsType' and declaration.get('parameterCount')==1 and declaration.get('parameterTypes')==['int']
        and method.index==declaration['methodIndex']
        and method.token==_rva(declaration['token']) and md.type_full_name(md.types[method.declaring_type])=='IFix.Core.Call'
        and md.string(method.name_index)=='GetAsType' and method.parameter_count==1 and not method.flags&16 and method.generic_container_index>=0,'generic GetAsType declaration differs')
    params=md.parameters_for(method);_need(len(params)==1 and _type(image,params[0].type_index)=='int','generic offset argument differs');_carrier(image,image.pe.u64_at_va(_rva(reg['types'])+params[0].type_index*8),'int')
    _var(image,image.pe.u64_at_va(_rva(reg['types'])+method.return_type*8),method,0,method_owned=True,arity=1)
    args=image.instantiations.resolve(record['methodInstantiationIndex']).arguments
    _need(len(args)==1 and len(bytes.fromhex(args[0].raw_type_record_hex))==16 and not bytes.fromhex(args[0].raw_type_record_hex)[11]&0x20
        and bytes.fromhex(args[0].raw_type_record_hex)==image.pe.bytes_at_va(args[0].type_pointer_va,16),'string instantiation is byref/malformed')
    _carrier(image,args[0].type_pointer_va,'string');_canonical_target(image,method.index,targets['getAsString']);return cell


def validate_anonymous_virtual_rules(image: Any,spec: dict,contract: dict,extents: dict) -> dict:
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items())and set(spec['methods'])==set(_METHODS)and set(spec['leafMethods'])==set(_LEAVES)
        and set(spec['helpers'])=={'finalizeFrame'},'unsupported schema/claim/catalog/boundary');_layout(image,spec,contract);targets={};rows={}
    for name,identity in _METHODS.items():
        row=spec['methods'][name];targets[name]=_identity(image,row,identity,name,extents);_signature(image,identity);rows[name]=row
    for name,identity in _LEAVES.items():
        row=spec['leafMethods'][name]
        _need(row.get('entryBoundary')==spec['leafBoundary']and 'bodyBytes'not in row and 'bodySha256'not in row,'finite leaf boundary differs: '+name)
        targets[name]=_identity(image,row,identity,name,extents);_signature(image,identity);rows[name]=row
        _need(image.pe.image_base+targets[name]not in extents,'leaf has selected pdata function extent: '+name)
    for name,path in _METHOD_REFS.items():
        row=_ref(contract,path)
        if name in _READERS:targets[name]=_identity(image,row,_READERS[name],name,extents);_signature(image,_READERS[name]);rows[name]=row
        else:targets[name],_raw_body=_bridge_identity(image,row,name,extents)
        md=image.metadata;method=next(m for t in md.types if md.type_full_name(t)==row['type']for m in md.methods_for(t)if m.token==_rva(row['token']))
        for ordinal,(p,typ)in enumerate(zip(md.parameters_for(method),row['parameterTypes'])):_carrier(image,image.pe.u64_at_va(_rva(image.registration['types'])+p.type_index*8),typ,byref=name=='executeBridge'and ordinal==1)
        _carrier(image,image.pe.u64_at_va(_rva(image.registration['types'])+method.return_type*8),row.get('returnTypeName',row.get('returnType')))
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);targets[name]=_rva(row['rva'])
        if name=='contextType':_context_type_leaf(image,row,extents)
        else:_hash(image.pe.bytes_at_va(image.pe.image_base+targets[name],row.get('byteCount',row.get('bodyBytes'))),row,name,method='bodyBytes'in row)
    for name,row in spec['helpers'].items():
        _need(row.get('name')==name,'helper label differs');targets[name]=_rva(row['rva']);_raw(image,row,extents);rows[name]=row
    targets['getAsString'],generic_body=_body(image,_ref(contract,spec['genericProgramRef']),extents,'inherited GetAsType reference program')
    _expect(generic_body,_reference_program(targets['getAsString'],targets),'inherited GetAsType reference program')
    for name,identity in _READERS.items():
        row=rows[name];_expect(image.pe.bytes_at_va(image.pe.image_base+targets[name],row['bodyBytes']),_scalar_program(identity[1],targets[name],targets),name)
    cells={'stringContext':_context(image,spec,targets,contract)};flag=spec['lazyFlag'];where=_rva(flag['rva']);section=flag['section']
    _need(flag.get('byteCount')==1 and flag.get('storage')=='unbacked-PE-virtual-tail-runtime-state-unobserved' and 'hex'not in flag and 'sha256'not in flag,
        'lazy flag runtime boundary differs')
    selected=[s for s in image.pe.sections if s['name']==section['name'] and s['virtualAddress']<=where<s['virtualAddress']+s['virtualSize']]
    _need(len(selected)==1 and selected[0]==section and where>=section['virtualAddress']+section['rawSize'],'lazy flag is not unbacked virtual tail');cells['lazyFlag']=where
    for name in _PROGRAMS:
        row=rows[name];count=row.get('bodyBytes',row.get('byteCount'));_expect(image.pe.bytes_at_va(image.pe.image_base+targets[name],count),_program(name,targets[name],targets,cells),name)
    return dict(status='validated_conditional_anonymous_virtual_rules',evidenceBoundary='conditional',executionBoundary='unobserved',
        fallbackRecipe=spec['fallbackRecipe'],patchedRecipe=spec['patchedRecipe'],primitiveRecipe=spec['primitiveRecipe'],stringRecipe=spec['stringRecipe'],
        genericBoundary=spec['genericBoundary'],finalizeRecipe=spec['finalizeRecipe'],leafRecipe=spec['leafRecipe'],leafBoundary=spec['leafBoundary'],storageBoundary=spec['storageBoundary'],exceptionBoundary=spec['exceptionBoundary'],runtimeBoundary=spec['runtimeBoundary'],
        unresolved=['runtime-receiver-method-ID-and-thread-stack-selection','Begin-Push-Execute-and-result-query-cast-outcomes','exact-GetAsType-runtime-sharing','Finalize-detached-entry-frame-association-EH-delivery-and-transfer','live-storage-overlap-and-execution'])


def validate_selected_anonymous_virtual_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.anonymous-virtual')
    return validate_anonymous_virtual_rules(image,contract['anonymousVirtualRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
_PROGRAMS = {'Equals': ['48895c2408574881ec80000000837930ff488bfa488bd9',
            ('edge', '0f84', 'join1', 4),
            '33d2488d4c2458',
            ('call', 'begin'),
            '4533c0488d4c2430488bd30f10000f1048100f11442430f20f104020f20f114424500f114c2440',
            ('call', 'pushObject'),
            '4533c0488d4c2430488bd7',
            ('call', 'pushObject'),
            '488b4b284885c9',
            ('edge', '75', 'join0', 1),
            ('call', 'nullFailure'),
            'cc',
            ('label', 'join0'),
            '4883642428004c8d4424308b533041b9020000008364242000',
            ('call', 'executeBridge'),
            '4533c0488d4c243033d2',
            ('call', 'getBoolean'),
            ('edge', 'eb', 'join2', 1),
            ('label', 'join1'),
            '483bdf0f94c0',
            ('label', 'join2'),
            '488b9c24900000004881c4800000005fc3'],
 'GetHashCode': ['40534881ec80000000837938ff488bd9',
                 ('edge', '74', 'join1', 1),
                 '33d2488d4c2458',
                 ('call', 'begin'),
                 '4533c0488d4c2430488bd30f10000f1048100f11442430f20f104020f20f114424500f114c2440',
                 ('call', 'pushObject'),
                 '488b4b284885c9',
                 ('edge', '75', 'join0', 1),
                 ('call', 'nullFailure'),
                 'cc',
                 ('label', 'join0'),
                 '4883642428004c8d4424308b533841b9010000008364242000',
                 ('call', 'executeBridge'),
                 '4533c0488d4c243033d2',
                 ('call', 'getInt32'),
                 ('edge', 'eb', 'join2', 1),
                 ('label', 'join1'),
                 'c1eb0369c3b179379e',
                 ('label', 'join2'),
                 '4881c4800000005bc3'],
 'ToString': ['40534881ec80000000',
              ('rip', '803d', 'lazyFlag', '00'),
              '488bd9',
              ('edge', '75', 'join0', 1),
              ('rip', '488d0d', 'stringContext', ''),
              ('call', 'metadataInitialize'),
              ('rip', 'c605', 'lazyFlag', '01'),
              ('label', 'join0'),
              '33d2837b3cff',
              ('edge', '74', 'join2', 1),
              '488d4c2458',
              ('call', 'begin'),
              '4533c0488d4c2430488bd30f10000f1048100f11442430f20f104020f20f114424500f114c2440',
              ('call', 'pushObject'),
              '488b4b284885c9',
              ('edge', '75', 'join1', 1),
              ('call', 'nullFailure'),
              'cc',
              ('label', 'join1'),
              '4883642428004c8d4424308b533c41b9010000008364242000',
              ('call', 'executeBridge'),
              ('rip', '4c8b05', 'stringContext', ''),
              '488d4c243033d2',
              ('call', 'getAsString'),
              '4881c4800000005bc3',
              ('label', 'join2'),
              '488bcb4881c4800000005b',
              ('tail', 'objectToString')],
 'Finalize': ['4c8bdc49894b084881eca80000004983639000498d430849894398498b4308837834ff',
              ('edge', '74', 'join0', 1),
              '33d2498d4bc8',
              ('call', 'begin'),
              '0f10000f114424480f1048100f114c2458f20f104020f20f114424684533c0488b9424b0000000488d4c2448',
              ('call', 'pushObject'),
              '488b8424b0000000488b48284885c9',
              ('edge', '74', 'join3', 1),
              '488364242800836424200041b9010000004c8d4424488b5034',
              ('call', 'executeBridge'),
              '90',
              ('label', 'join0'),
              ('edge', 'eb', 'join1', 1),
              '488b4c24384885c9',
              ('edge', '75', 'join2', 1),
              ('label', 'join1'),
              '4881c4a8000000c3',
              ('label', 'join2'),
              ('call', 'exceptionPropagate'),
              '90',
              ('label', 'join3'),
              ('call', 'unwindNull'),
              '90cc'],
 'finalizeFrame': ['4889542410554883ec30488bea488b4530488b0848894d3848b800000000000000004883c4305dc3cc'],
 'ObjectEquals': ['483bca0f94c0c3'],
 'ObjectGetHashCode': ['c1e90369c1b179379ec3'],
 'ObjectToString': ['33d2',('tail','objectToString')]}
