"""Authenticate conditional anonymous-storey loading and Newanon requests.

The loader's normal record loop reads field count/types, constructor ID and
parameter count, calls readSlotInfo, then reads the virtual table and stores
an AnonymousStoreyInfo. readSlotInfo reads an interface count and interface
IDs. Each Type.GetMethods(DeclaredOnly|Public|Instance) result contributes one
file Int32 per returned method, mapped through Dictionary<MethodInfo,int>.
No method count is stored in that interface record. Reflection array length
and order therefore remain required external inputs to nonzero raw framing.

Newanon selects its info with the signed operand. Null Slots requests the
plain storey constructor; other Slots request the wrapper bridge helper.
It copies arguments down one slot in ascending order, performs extra managed
rebasing for tags >= Object except ValueType, inserts the constructed object,
and requests recursive Execute with constructor parameter count plus one.
On normal return it writes the saved constructed object again and commits
the next slot as top. The signed argument loop runs max(parameterCount,0)
times: the conditional net slot delta is 1 minus that value.

The plain constructor allocates unmanaged/managed arrays. Positive field
type IDs write ValueType, use externTypes[id-1] and request CreateInstance;
-2 writes Object with its own field index. Other IDs perform no explicit
field tag/payload write. Array allocator defaults are unobserved. The four
virtual IDs, type ID and VM are stored separately. Finite programs establish
these native requests; storage validity, reflection enumeration, bridge
selection, helper mutation, successful execution and unwinding stay open.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name
from scripts.game_data.il2cpp.context import literal_record, unresolved_usage_index, usage_method_spec
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect, _slice, _type, _identity
from scripts.game_data.ifix_vm_new_field_rules import _dictionary_signature, _guard_type, _canonical_target
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry


class AnonymousStoreyRuleError(ValueError):
    """An anonymous-storey declaration lacks its selected native witness."""


_CLAIMS = {
    'schema': 'endfield.ifix-vm-anonymous-storey-rules.v1', 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
    'loaderBoundary': 'normal-record-loop-valid-reader-arrays-and-helper-returns;outer-count-allocation-and-failure-selection-unresolved',
    'slotRecipe': 'interface-count-and-IDs;GetMethods(22);one-file-method-ID-per-returned-method;dictionary-to-slot;initial-slots-minus-one',
    'framingBoundary': 'interface-method-count-and-order-not-stored;runtime-reflection-array-required;nonzero-raw-framing-unresolved',
    'constructorRecipe': 'allocate-field-arrays;positive-type:ValueType-and-CreateInstance(externTypes[id-1]);minus-two:Object;other:no-explicit-tag-write;store-four-virtual-IDs',
    'newanonRecipe': 'signed-info-index;Slots-null:plain-constructor;otherwise:opaque-bridge-request;ascending-argument-copy-and-managed-rebase;recursive-Execute;restore-constructed-object;commit-top',
    'stackDeltaRecipe': '1-max(signed-CtorParamNum,0)', 'managedClearBoundary': 'no-explicit-consumed-slot-clear-in-selected-Newanon-route',
    'bridgeBoundary': 'caller-request-only;WrappersManager.CreateBridge-slot-1-named;helper-implementation-join-and-runtime-selection-unresolved',
    'storageBoundary': 'valid-stable-arrays-slots-and-normal-nonmutating-helper-return',
    'dictionaryBoundary': 'typed-MethodInfo-int-context-and-canonical-MethodDef-family;runtime-sharing-and-results-unobserved',
    'executionAndAliasBoundary': 'allocation-defaults-Type-results-bridge-aliases-recursive-execution-and-unwind-unobserved',
    'getMethodsRef': 'genericDelegateCatalogRules.virtualMethods.getMethods',
}
_METHODS = {
    'storeyCtor': ('IFix.Core.AnonymousStorey','.ctor',['int','int[]','int','int[]','IFix.Core.VirtualMachine'],'void',False),
    'readSlotInfo': ('IFix.Core.PatchManager','readSlotInfo',['System.IO.BinaryReader','System.Collections.Generic.Dictionary`2<System.Reflection.MethodInfo,int>','System.Type[]','int'],'int[]',True),
    'infoCtor': ('IFix.Core.AnonymousStoreyInfo','.ctor',[],'void',False),
    'exceptionCtor': ('System.Exception','.ctor',['string'],'void',False),
}
_HELPER_REFS = {
    'nullCheck':'negativeFieldRules.helpers.nullCheck','anonymousInfoFetch':'functionPointerRules.helpers.anonymousInfoFetch',
    'allocateStorey':'referenceAddressRules.helpers.allocateObject','subtractSlot':'constrainedTypeOperand.stackEffect.priorPointerHelper',
    'copy':'slotCopyRules.methods.copy','pointerDifference':'arithmeticWindows.stackPointerSubtract',
    'arrayFetch':'initobjTypeOperand.consumerRowFetchHelper','assignmentCheck':'functionPointerRules.helpers.assignmentCheck',
    'managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper','int32Add':'negativeFieldRules.helpers.int32Add',
    'slotMultiply':'arithmeticWindows.signedSlotMultiply','pointerAdd':'arithmeticWindows.pointerAdd',
    'advancePointer':'basicOpcodeRules.helpers.advancePointer','typeInitialize':'referenceUpdateRules.helpers.typeInitialize',
    'readInt32':'exceptionHandler.readMethod','arrayAllocate':'objectConversionRules.helpers.arrayAllocate',
    'getMethodsHelper':'genericDelegateCatalogRules.helperWindows.getMethodsHelper','usageResolve':'objectConversionRules.helpers.usageResolveThunk',
    'allocateInfo':'stackReferenceRules.nullObjectHelper','throwStop':'objectConversionRules.helpers.throwStop',
    'boundsFailure':'referenceUpdateRules.helpers.boundsFailure','nullFailure':'referenceUpdateRules.helpers.nullFailure',
    'writeBarrier':'delegateBridgeRules.referenceWriteBarrier','valueArrayElement':'instanceFieldRules.helpers.valueArrayElement',
    'createInstance':'initobjStackEffect.createInstanceMethod',
    'int32ArrayStore':'referenceAddressRules.helpers.int32ArrayStore','allocateIntArray':'referenceAddressRules.helpers.allocateArray',
    'concatArray':'objectConversionRules.methods.concatArray','execute':'consumer','pushTopCommit':'basicOpcodeRules.sharedWindows.pushTopCommit',
}
_FIELDS = {
    'IFix.Core.AnonymousStorey': {'unmanagedFields':('IFix.Core.Value[]',16),'managedFields':('object[]',24),'typeId':('int',32),
        'virtualMachine':('IFix.Core.VirtualMachine',40),'equalMethodId':('int',48),'finalizeMethodId':('int',52),
        'getHashCodeMethodId':('int',56),'toStringMethodId':('int',60)},
    'IFix.Core.AnonymousStoreyInfo': {'FieldNum':('int',16),'FieldTypes':('int[]',24),'CtorId':('int',32),'CtorParamNum':('int',36),
        'Slots':('int[]',40),'VTable':('int[]',48)},
    'IFix.Core.VirtualMachine': {'anonymousStoreyInfos':('IFix.Core.AnonymousStoreyInfo[]',104),'wrappersManager':('IFix.Core.WrappersManager',144),
        'unmanagedCodes':('IFix.Core.Instruction**',24),'externTypes':('System.Type[]',72)},
}
_TYPE_CELLS = {'anonymousType':'IFix.Core.AnonymousStorey','intArrayType':'int[]','objectArrayType':'object[]',
    'valueArrayType':'IFix.Core.Value[]','exceptionType':'System.Exception','patchManagerType':'IFix.Core.PatchManager','infoType':'IFix.Core.AnonymousStoreyInfo'}
_LITERALS = {'errorPrefix':'can not find slot for ','errorMiddle':' of '}
_USAGE_REFS = {'anonymousType':'functionPointerRules.anonymousStoreyType',
    'intArrayType':'referenceAddressRules.usageCells.intArrayType','objectArrayType':'objectConversionRules.usageCells.class_objectArray'}


def _need(ok: bool, detail: str) -> None:
    if not ok: raise AnonymousStoreyRuleError('anonymousStorey.'+detail)


def _claims(spec: dict) -> None:
    _need(all(spec.get(k)==v for k,v in _CLAIMS.items()) and spec.get('helperRefs')==_HELPER_REFS
        and spec.get('usageRefs')==_USAGE_REFS,'unsupported schema/reference/boundary')
    _need(set(spec['programs'])==set(_PATTERNS),'missing/unknown program')
    _need(set(spec['methods'])==set(_METHODS),'missing/unknown method')


def _named_carrier(image: Any, pointer: int, expected: str, seen: frozenset[int] = frozenset()) -> None:
    """Check nested kinds even where the display name omits nested byref."""
    _need(len(seen)<8 and pointer not in seen,'named carrier: recursive/deep type')
    raw=image.pe.bytes_at_va(pointer,16)
    _need(len(raw)==16 and not raw[11]&0x20,'named carrier: malformed/by-reference type')
    nested=expected.endswith('[]') or expected.endswith('*')
    kind=(0x1d if expected.endswith('[]') else 0x0f) if nested else {
        'int':0x08,'object':0x1c,'IFix.Core.Value':0x11,'IFix.Core.Instruction':0x11,
    }.get(expected,0x12)
    _need(raw[10]==kind,'named carrier: primitive/class/array/pointer kind differs')
    if nested:
        _named_carrier(image,int.from_bytes(raw[:8],'little'),expected[:-2] if expected.endswith('[]') else expected[:-1],seen|{pointer})


def _layout(image: Any, spec: dict) -> None:
    _need(set(spec['fieldLayouts'])==set(_FIELDS),'layout owner set differs')
    for owner,fields in _FIELDS.items():
        types=[t for t in image.metadata.types if image.metadata.type_full_name(t)==owner]
        _need(len(types)==1 and not types[0].bitfield&1,owner+': expected reference-type owner')
        t=types[0];row=spec['fieldLayouts'][owner]
        _need(row['type']==owner and set(row['fields'])==set(fields),owner+': fields differ')
        offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,t.index)
        definitions={image.metadata.string(f.name_index):f for f in image.metadata.fields_for(t)}
        for name,(typ,offset) in fields.items():
            declared=row['fields'][name];_need(name in definitions,owner+'.'+name+': field missing')
            f=definitions[name];pointer=image.pe.u64_at_va(_rva(image.registration['types'])+f.type_index*8);raw=image.pe.bytes_at_va(pointer,16)
            _named_carrier(image,pointer,typ)
            _need(not raw[11]&0x20 and not int.from_bytes(raw[8:10],'little')&0x10 and _type(image,f.type_index)==typ
                and declared=={'type':typ,'offset':offset} and offsets.get(name)==offset,owner+'.'+name+': carrier/layout differs')
    # The inherited field buffers must describe the same stored structure.


def _context(image: Any, row: dict, target: int) -> None:
    reg,md=image.registration,image.metadata;cell=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+cell,8)
    at=_rva(reg['methodSpecs']);record=usage_method_spec(raw,image.pe.bytes_at_va(at,reg['methodSpecsCount']*12),len(md.methods),
        reg['genericInstsCount'],source='anonymousStorey.context',usage_offset=image.pe.image_base+cell,records_offset=at)
    _need(record['classInstantiationIndex']>=0 and record['methodInstantiationIndex']==-1,'dictionary context instantiation differs')
    method=md.methods[record['definition']];identity='ContainsKey' if row['name']=='containsContext' else 'get_Item'
    _need(row.get('identity')==identity and row.get('classArguments')==['System.Reflection.MethodInfo','int']
        and md.type_full_name(md.types[method.declaring_type])=='System.Collections.Generic.Dictionary`2'
        and md.string(method.name_index)==identity,'dictionary named definition differs')
    _dictionary_signature(image,method,identity)
    args=image.instantiations.resolve(record['classInstantiationIndex']).arguments
    for argument in args:_guard_type(image,argument.type_pointer_va)
    _need([runtime_type_name(image.pe,md,x.type_pointer_va) for x in args]==row['classArguments'],'dictionary constructed arguments differ')
    _canonical_target(image,method.index,target)


def _cells(image: Any, spec: dict, targets: dict[str,int], contract: dict) -> dict[str,int]:
    rows={r['name']:r for r in spec['usageCells']};expected=set(_TYPE_CELLS)|set(_LITERALS)|{'containsContext','itemContext','throwContext'}
    _need(len(rows)==len(spec['usageCells']) and set(rows)==expected-set(_USAGE_REFS),'usage set differs');cells={}
    for name,path in _USAGE_REFS.items():
        row=_ref(contract,path)
        rows[name]=dict(row,name=name,identity=row.get('identity',row.get('typeName')),
            rawHex=row.get('rawHex',_rva(row.get('encodedWord','0')).to_bytes(8,'little').hex()))
    for name,row in rows.items():
        at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(raw==bytes.fromhex(row['rawHex']),'stored usage bytes differ: '+name);cells[name]=at
        if name in _TYPE_CELLS:
            _need(row.get('usageTag')==1 and row.get('identity')==_TYPE_CELLS[name],'type usage declaration differs: '+name)
            index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='anonymousStorey.'+name,offset=at)
            _named_carrier(image,image.pe.u64_at_va(_rva(image.registration['types'])+index*8),_TYPE_CELLS[name])
            _need(_type(image,index)==_TYPE_CELLS[name],'type usage carrier differs: '+name)
        elif name in _LITERALS:
            md=image.metadata;table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData']
            _need(row.get('usageTag')==5 and row.get('identity')==_LITERALS[name],'literal declaration differs')
            index=unresolved_usage_index(raw,table.size//8,tag=5,source='anonymousStorey.literal',offset=at);off=table.offset+index*8
            begin,size=literal_record(md.buf[off:off+8],pool.size,source='anonymousStorey.literal',offset=off)
            _need(md.buf[pool.offset+begin:pool.offset+begin+size]==_LITERALS[name].encode(),'literal bytes differ')
        elif name in ('containsContext','itemContext'):
            _need(row.get('usageTag')==6,'dictionary tag differs');_context(image,row,targets['containsMethod' if name=='containsContext' else 'getMethodSlot'])
        else:
            _need(row.get('usageTag')==3 and row.get('identity')=='opaque-runtime-exception-MethodDef-context','exception context boundary differs')
            unresolved_usage_index(raw,len(image.metadata.methods),tag=3,source='anonymousStorey.throw',offset=at)
    _need(set(spec['flags'])=={'slotsFlag','ctorFlag'},'initialization flag set differs')
    cells.update({n:_rva(at) for n,at in spec['flags'].items()});return cells


def _program(name: str, base: int, targets: dict[str,int], cells: dict[str,int]) -> bytes:
    p=_Program(base)
    for token in _PATTERNS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]],bytes.fromhex(args[2]))
        elif kind=='jump':p.rip('e9',targets[args[0]])
        else:_need(False,'unknown finite program token')
    return p.finish()


def validate_anonymous_storey_rules(image: Any,spec: dict,body: bytes,body_rva: int,loader: bytes,loader_rva: int,
                                   opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """The parent authenticates inherited prerequisite groups and complete bodies."""
    _claims(spec);_layout(image,spec);targets={}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);targets[name]=at
        if 'bodyBytes' in row:_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['bodyBytes']),row,name,method=True)
        elif 'byteCount' in row:_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,name)
        elif name not in ('readInt32','createInstance'):_need(False,'inherited body witness missing: '+name)
    _identity(image,_ref(contract,'exceptionHandler.readMethod'),('System.IO.BinaryReader','ReadInt32',[],'int',False),'readInt32',extents,body_required=False)
    _identity(image,_ref(contract,'initobjStackEffect.createInstanceMethod'),('System.Activator','CreateInstance',['System.Type'],'object',True),'createInstance',extents,body_required=False)
    for name,identity in _METHODS.items():targets[name]=_identity(image,spec['methods'][name],identity,name,extents)
    _identity(image,spec['bridgeMethod'],('IFix.Core.WrappersManager','CreateBridge',['int','int[]','int','int[]','int[]','IFix.Core.VirtualMachine'],'IFix.Core.AnonymousStorey',False),
        'CreateBridge',extents,virtual_slot=1)
    get_methods=_ref(contract,_CLAIMS['getMethodsRef'])
    _identity(image,dict(get_methods,virtualSlot=get_methods.get('slot')),('System.Type','GetMethods',['System.Reflection.BindingFlags'],'System.Reflection.MethodInfo[]',False),
        'GetMethods',extents,virtual_slot=132)
    rows={r['name']:r for r in spec['helpers']}
    _need(len(rows)==len(spec['helpers']) and set(rows)=={'bridgeRequest','containsMethod','getMethodSlot','infoArrayStore','classInitialize'},'helper set differs')
    for name,row in rows.items():
        _need(row.get('effectBoundary')=='opaque-callee-request-only','helper result promoted: '+name)
        at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,name);targets[name]=at
    cells=_cells(image,spec,targets,contract)
    for name,row in spec['programs'].items():
        at=_rva(row['rva']);actual=_slice(loader,loader_rva,at,row['byteCount'],name) if name=='loaderRecord' else (
            _slice(body,body_rva,at,row['byteCount'],name) if name=='newanon' else image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']))
        _hash(actual,row,name);_expect(actual,_program(name,at,targets,cells),name)
        if name in ('readSlotInfo','storeyCtor'):
            _need(at==targets[name] and row['byteCount']==spec['methods'][name]['bodyBytes'],'complete finite method boundary differs')
    dispatch=contract['dispatchRules'];extensions=dispatch['extensions']
    selected=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),opcode_ids['Newanon'],
        zero_compare_rva=_rva(extensions['zeroCompare']['rva']),sub_esi_rva=_rva(extensions['subEsi']['rva']),
        entry_rvas={_rva(r['entryRva']) for r in dispatch['entryPoints']})
    _need(selected==_rva(spec['programs']['newanon']['rva']),'Newanon dispatch differs')
    tags={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.ValueType')}
    _need(all(tags.get(k)==v for k,v in {'Object':8,'ValueType':9}.items()),'field tag IDs differ')
    return {'status':'validated_conditional_anonymous_storey_rules','evidenceBoundary':'conditional','executionBoundary':'unobserved',
        'opcode':'Newanon','programCount':len(_PATTERNS),'stackDeltaRecipe':spec['stackDeltaRecipe'],'framingBoundary':spec['framingBoundary'],
        'unresolved':['runtime-interface-GetMethods-count-and-order','outer-anonymous-count-allocation','bridge-helper-implementation-and-live-wrapper-selection',
            'field-buffer-allocation-defaults-and-Type-results','actual-argument-aliases-helper-mutation-and-slot-validity','recursive-Execute-and-unwind-outcome']}


def validate_selected_anonymous_storey_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Fail closed before opening native inputs; selected paths are required."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.anonymousStorey');extents=image.mapper.pdata_function_extents(image.pe)
    at=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    consumer=image.pe.bytes_at_va(image.pe.image_base+at,contract['consumer']['bodyBytes'])
    row=contract['loader'];loadat=_rva(row['rva']);loader=image.pe.bytes_at_va(image.pe.image_base+loadat,row['bodyBytes']);_hash(loader,row,'LoadInternal',method=True)
    ids={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_anonymous_storey_rules(image,contract['anonymousStoreyRules'] if spec is None else spec,consumer,at,loader,loadat,ids,contract,extents)


_PATTERNS = {'newanon': ('488b5f68498bce',
             ('call', 'nullCheck'),
             '49637e04488bcb',
             ('call', 'nullCheck'),
             '488bd7488bcb',
             ('call', 'anonymousInfoFetch'),
             '488bd8488bc8',
             ('call', 'nullCheck'),
             '448b6b244489ac2418040000488bcb',
             ('call', 'nullCheck'),
             '488b442468488bcb483943280f848f000000488b8424f00300004c8bb890000000',
             ('call', 'nullCheck'),
             '448b6b10488bcb',
             ('call', 'nullCheck'),
             '4c8b6318498bce',
             ('call', 'nullCheck'),
             '458b7604488bcb',
             ('call', 'nullCheck'),
             '488b7330488bcb',
             ('call', 'nullCheck'),
             '488b7b28498bcf',
             ('call', 'nullCheck'),
             '488b4424684889442438488b8424f0030000488944243048897c24284889742420458bce4d8bc4418bd5498bcf',
             ('call', 'bridgeRequest'),
             '4c8be0448bac2418040000eb75',
             ('call', 'nullCheck'),
             '448b7b10488bcb',
             ('call', 'nullCheck'),
             '4c8b7318488b7c2450488bcf',
             ('call', 'nullCheck'),
             '8b7704488bcb',
             ('call', 'nullCheck'),
             '488b7b30',
             ('rip', '488b0d', 'anonymousType', ''),
             ('call', 'allocateStorey'),
             '4c8be0488bc8',
             ('call', 'nullCheck'),
             '488b4424684889442430488b8424f0030000488944242848897c2420448bce4d8bc6418bd7498bcc',
             ('call', 'storeyCtor'),
             '488b7c2468448bf74c8b7c2458488bb42408040000498bcf453bf50f8d36010000ba0c000000',
             ('call', 'subtractSlot'),
             '48897c242848897424204c8bc84d8bc7488b942410040000488b8c24f0030000',
             ('call', 'copy'),
             '498bcf',
             ('call', 'nullCheck'),
             '41833f080f8cd0000000498bcf',
             ('call', 'nullCheck'),
             '41833f090f84be000000ba0c000000498bcf',
             ('call', 'subtractSlot'),
             '488bf8498bcf',
             ('call', 'nullCheck'),
             '488b942410040000498bcf',
             ('call', 'pointerDifference'),
             '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d041895704498bcf',
             ('call', 'nullCheck'),
             '49637704488bcf',
             ('call', 'nullCheck'),
             '48637f04488b8c2408040000',
             ('call', 'nullCheck'),
             '488bd7488b8c2408040000',
             ('call', 'arrayFetch'),
             '488bf8488b8c2408040000',
             ('call', 'nullCheck'),
             '488bd7488b8c2408040000',
             ('call', 'assignmentCheck'),
             '488bd64c8bc7488b8c2408040000',
             ('call', 'managedStore'),
             '488b7c2468488bb42408040000ba0c000000498bcf',
             ('call', 'subtractSlot'),
             '4c8bf8ba01000000418bce',
             ('call', 'int32Add'),
             '448bf0e9befeffff',
             ('call', 'nullCheck'),
             '41c70708000000498bcf',
             ('call', 'nullCheck'),
             '488b942410040000498bcf',
             ('call', 'pointerDifference'),
             '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d041895704498bcf',
             ('call', 'nullCheck'),
             '49637f04488bb42408040000488bce',
             ('call', 'nullCheck'),
             '498bd4488bce',
             ('call', 'assignmentCheck'),
             '488bd74d8bc4488bce',
             ('call', 'managedStore'),
             '4c8bb424f0030000498b7e18488bcb',
             ('call', 'nullCheck'),
             '48634b20ba08000000',
             ('call', 'slotMultiply'),
             '488bd0488bcf',
             ('call', 'pointerAdd'),
             '488b38488bcb',
             ('call', 'nullCheck'),
             '8b5b20ba01000000418bcd',
             ('call', 'int32Add'),
             '4c8b6c24684c896c24484c896c244044896c2438895c243089442428488b9c241004000048895c24204c8bce4d8bc7488bd7498bce',
             ('call', 'execute'),
             '498bcf',
             ('call', 'nullCheck'),
             '41c70708000000498bcf',
             ('call', 'nullCheck'),
             '488bd3498bcf',
             ('call', 'pointerDifference'),
             '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d041895704498bcf',
             ('call', 'nullCheck'),
             '49635f04488bce',
             ('call', 'nullCheck'),
             '498bd4488bce',
             ('call', 'assignmentCheck'),
             '488bd34d8bc4488bce',
             ('call', 'managedStore'),
             'be0c000000498bcf8bd6',
             ('call', 'advancePointer'),
             ('jump', 'pushTopCommit')),
 'readSlotInfo': ('48895c241048896c241848897424205741544155415641574883ec30',
                  ('rip', '803d', 'slotsFlag', '00'),
                  '418bd94d8be04c8bea488be9752b',
                  ('rip', '488d0d', 'containsContext', ''),
                  ('call', 'typeInitialize'),
                  ('rip', '488d0d', 'itemContext', ''),
                  ('call', 'typeInitialize'),
                  ('rip', '488d0d', 'intArrayType', ''),
                  ('call', 'typeInitialize'),
                  ('rip', 'c605', 'slotsFlag', '01'),
                  '4885ed0f846402000033d2488bcd',
                  ('call', 'readInt32'),
                  '448bf885c00f8448020000',
                  ('rip', '488b0d', 'intArrayType', ''),
                  '8d5301',
                  ('call', 'arrayAllocate'),
                  '488bd833c94885c00f84320200003b4b187d120f831a0200004863c1834c8320ffffc1ebe94533f64585ff0f8ecd00000033d2488bcd',
                  ('call', 'readInt32'),
                  '4d85e40f84fc010000413b4424180f83e40100004898498b44c42048894424284885c00f84dc01000041b816000000488bd0',
                  ('call', 'getMethodsHelper'),
                  '488bf033ff4885c00f84c00100003b7e187d6d0f83a80100004863c733d2488bcd488b44c6204889442420',
                  ('call', 'readInt32'),
                  '894424604d85ed0f8491010000',
                  ('rip', '4c8b05', 'containsContext', ''),
                  '498bcd488b542420',
                  ('call', 'containsMethod'),
                  '84c07457',
                  ('rip', '4c8b05', 'itemContext', ''),
                  '498bcd488b542420',
                  ('call', 'getMethodSlot'),
                  '3b43180f834f0100008b4c2460ffc74898894c8320eb8e41ffc6453bf70f8c33ffffff488bc3488b5c2468488b6c2470488b7424784883c430415f415e415d415c5fc3',
                  ('rip', '488d0d', 'objectArrayType', ''),
                  ('call', 'usageResolve'),
                  'ba04000000488bc8',
                  ('call', 'arrayAllocate'),
                  '488bd84885c00f84fd000000',
                  ('rip', '488d0d', 'errorPrefix', ''),
                  ('call', 'usageResolve'),
                  '488bd0488bcb',
                  ('call', 'assignmentCheck'),
                  ('rip', '488d0d', 'errorPrefix', ''),
                  ('call', 'usageResolve'),
                  '4c8bc033d2488bcb',
                  ('call', 'managedStore'),
                  '488b542420488bcb',
                  ('call', 'assignmentCheck'),
                  '4c8b442420ba01000000488bcb',
                  ('call', 'managedStore'),
                  ('rip', '488d0d', 'errorMiddle', ''),
                  ('call', 'usageResolve'),
                  '488bd0488bcb',
                  ('call', 'assignmentCheck'),
                  ('rip', '488d0d', 'errorMiddle', ''),
                  ('call', 'usageResolve'),
                  '4c8bc0ba02000000488bcb',
                  ('call', 'managedStore'),
                  '488b542428488bcb',
                  ('call', 'assignmentCheck'),
                  '4c8b442428ba03000000488bcb',
                  ('call', 'managedStore'),
                  '33d2488bcb',
                  ('call', 'concatArray'),
                  ('rip', '488d0d', 'exceptionType', ''),
                  '488bf8',
                  ('call', 'usageResolve'),
                  '488bc8',
                  ('call', 'allocateInfo'),
                  '488bd84885c074334533c0488bd7488bc8',
                  ('call', 'exceptionCtor'),
                  ('rip', '488d0d', 'throwContext', ''),
                  ('call', 'usageResolve'),
                  '488bd0488bcb',
                  ('call', 'throwStop'),
                  'cc',
                  ('call', 'boundsFailure'),
                  'cc33c0e9c1feffff',
                  ('call', 'nullFailure'),
                  'cc'),
 'storeyCtor': ('488bc4488958084889681048897018488978204154415641574883ec20',
                ('rip', '803d', 'ctorFlag', '00'),
                '458be1498bf08bfa488bd9751f',
                ('rip', '488d0d', 'objectArrayType', ''),
                ('call', 'typeInitialize'),
                ('rip', '488d0d', 'valueArrayType', ''),
                ('call', 'typeInitialize'),
                ('rip', 'c605', 'ctorFlag', '01'),
                ('rip', '488b0d', 'valueArrayType', ''),
                '488bd7',
                ('call', 'arrayAllocate'),
                '488d4b1048894310',
                ('call', 'writeBarrier'),
                ('rip', '488b0d', 'objectArrayType', ''),
                '488bd7',
                ('call', 'arrayAllocate'),
                '488d4b1848894318',
                ('call', 'writeBarrier'),
                '33ff4885f60f847f010000488b6c24683b7e180f8df90000000f83650100004863c7837c8620007f464863c7837c8620fe0f85d4000000488b4b104885c90f84460100004863d7',
                ('call', 'valueArrayElement'),
                'c70008000000488b4b104885c90f842b0100004863d7',
                ('call', 'valueArrayElement'),
                '897804e99c000000488b4b104885c90f840e0100004863d7',
                ('call', 'valueArrayElement'),
                'c70009000000488b4b104885c90f84f30000004863d7',
                ('call', 'valueArrayElement'),
                '8978043b7e180f83d90000004c8b73184885ed0f84d20000004c8b45484d85c00f84c50000004863c748634c862048ffc9413b48180f83aa000000498b4cc82033d2',
                ('call', 'createInstance'),
                '4c8bf84d85f60f8498000000488bd0498bce',
                ('call', 'assignmentCheck'),
                '4863d74d8bc7498bce',
                ('call', 'managedStore'),
                'ffc7e9fefeffff488d4b284489632048896b28',
                ('call', 'writeBarrier'),
                '4c8b4c24604d85c9745d41837918007650418b412089433041837918017642418b412489433441837918027634418b412889433841837918037626418b412c488b6c2448488b742450488b7c245889433c488b5c24404883c420415f415e415cc3',
                ('call', 'boundsFailure'),
                'cc',
                ('call', 'nullFailure'),
                'cc'),
 'loaderRecord': ('33ff897c2468904d85ff0f847f200000413b7f180f8dbc010000488b4c24404885c90f84251e000033d2',
                  ('call', 'readInt32'),
                  '448bf8418bd7',
                  ('rip', '488b0d', 'intArrayType', ''),
                  ('call', 'arrayAllocate'),
                  '4c8bf033db90488b4c2440413bdf7d2b4885c90f84cb1d000033d2',
                  ('call', 'readInt32'),
                  '4d85f60f84b61d00004863d3448bc0498bce',
                  ('call', 'int32ArrayStore'),
                  'ffc3ebcb4885c90f84c31d000033d2',
                  ('call', 'readInt32'),
                  '89442448488b4c24404885c90f84a51d000033d2',
                  ('call', 'readInt32'),
                  '448be8488b5c2440',
                  ('rip', '488b0d', 'patchManagerType', ''),
                  '83b9e0000000007505',
                  ('call', 'classInitialize'),
                  '48c744242000000000448b4c24584c8b842480000000488b942498000000488bcb',
                  ('call', 'readSlotInfo'),
                  '4c8be0488b4c24404885c90f84451d000033d2',
                  ('call', 'readInt32'),
                  '8bf08bd0',
                  ('rip', '488b0d', 'intArrayType', ''),
                  ('call', 'allocateIntArray'),
                  '488bf833db66903bde7d30488b4c24404885c90f84061d000033d2',
                  ('call', 'readInt32'),
                  '4885ff0f84f11c00004863d3448bc0488bcf',
                  ('call', 'int32ArrayStore'),
                  'ffc3ebcc',
                  ('rip', '488b0d', 'infoType', ''),
                  ('call', 'allocateInfo'),
                  '488bd84885c00f84d61c000033d2488bc8',
                  ('call', 'infoCtor'),
                  '8b44244889432044897b104c897318488d4b18',
                  ('call', 'writeBarrier'),
                  '44896b244c896328488d4b28',
                  ('call', 'writeBarrier'),
                  '48897b30488d4b30',
                  ('call', 'writeBarrier'),
                  '4c8b7c24504d85ff0f84831c0000488bd3498bcf',
                  ('call', 'assignmentCheck'),
                  '48637c2468488bd74c8bc3498bcf',
                  ('call', 'infoArrayStore'),
                  'ffc7e92cfeffff')}
