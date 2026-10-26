"""Authenticate IFix's new-field key, default and initialization requests.

The selected storage is a static outer Dictionary<int,Dictionary<string,object>>.
ObjectToIndex uses staticObjectKey for a null owner and requests virtual slot
two, Object.GetHashCode, for other owners. Name supplies the inner string key.
This is hash-keyed storage: no object identity comparison separates colliding
owners, and a mutable Name changes which stored row is requested.

GetValue initializes its outer out-dictionary to null and ignores the outer
TryGetValue Boolean. A null out-dictionary or an unsuccessful inner TryGetValue
requests SetDefaultValue; an inner hit returns its out-value, including null.
SetDefaultValue tests FieldType.IsValueType. True requests Activator.CreateInstance;
false chooses null. Both pass the default to SetValue and return that same default
on normal return. HasInitialize first checks the outer key, then obtains its
dictionary and checks Name. Its true result describes a stored key, not a
successful initializer invocation.

SetValue requests a new inner dictionary only when the outer key is absent.
That branch also adds WeakReference(owner,false) to objList if the owner is
nonnull. The existing-key branch does not refresh its weak reference. It then
requests outer[key][Name] = value through the named generic setter context.
CheckInit returns when MethodId is negative or HasInitialize is true. Otherwise
it builds Call from the static ThreadStackInfo, requests Execute(MethodId,ref
call,0,0), reads Call.GetObject(0), and stores that returned object for the owner.
There is no owner push in this initializer request. BeginForStack builds the
Call's five-word value from ManagedStack and repeated UnmanagedStack Base/Top
reads, and stores the address of Top as topWriteBack. Those reads are not an
atomic snapshot; valid stable storage and normal helper returns are required.

Every native instruction and join in these methods has a finite grammar. Named
layouts authenticate instance/static field carriers, Call's boxed-to-unboxed
offset adjustment, and the unmanaged pointer layout. Dictionary contexts check
their exact overloads, reciprocal VAR ownership/ordinals, out-VAR by-reference
flags and recursively non-byref constructed arguments. Registered MethodDef
families establish the direct shared helper targets, never the runtime sharing
selection. The hash dispatcher, reflection/default creation, class initialization,
allocation, weak-reference construction, dictionary outcomes and execution remain
unobserved. The static constructor requests a ThreadStackInfo and two dictionaries,
stores their returned receivers and sets staticObjectKey to zero. Sweep requests
a ToList snapshot of objList, iterates it, tests the qword at current payload+8
through WeakReference.IsAlive, and requests removal from both dictionaries using
the payload's low Int32 when liveness is false. Its stored landing/unwind paths
are byte-authenticated, but runtime cleanup selection is unobserved. The paired
payload comes from a typed KeyValuePair context and native 16-byte copies; closed
generic field offsets are absent from the stored definition's offset table, so
these word roles remain conditional rather than a recovered generic field layout.
"""
from __future__ import annotations

from pathlib import Path
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.generic_call_projection import project_generic_canonical_entry
from scripts.game_data.il2cpp.context import type_parameter_owner, method_parameter_owner, usage_method_spec, unresolved_usage_index, method_spec_record
from scripts.game_data.il2cpp.protocol import runtime_type_name, runtime_type_field_offsets, runtime_generic_inst_type_pointers
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_update_rules import _rva, _ref, _hash, _expect, _type_pointer, _dictionary_target


class NewFieldRuleError(ValueError):
    """The new-field recipe lacks its selected native witness."""


_METHOD_REFS = {'getValue': 'chainFieldRules.methods.newFieldGet', 'setValue': 'referenceUpdateRules.methods.newFieldSet',
    'executeBridge': 'delegateBridgeRules.methods.executeBridge', 'getObject': 'genericBridgeRules.getObjectMethod',
    'isValueType': 'genericDelegateFactoryRules.methods.isValueType', 'createInstance': 'initobjStackEffect.createInstanceMethod'}
_HELPER_REFS = {'typeInitialize': 'referenceUpdateRules.helpers.typeInitialize', 'nullFailure': 'referenceUpdateRules.helpers.nullFailure',
    'getOuter': 'referenceUpdateRules.helpers.dictionaryItem', 'tryInner': 'genericDelegateFactoryRules.helpers.cacheLookupHelper',
    'setInner': 'genericDelegateFactoryRules.helpers.cacheStoreHelper', 'writeBarrier': 'delegateBridgeRules.referenceWriteBarrier',
    'allocate': 'stackReferenceRules.nullObjectHelper', 'hashClassPrepare': 'chainFieldRules.helpers.classPrepare'}
_OWN_HELPERS = ('classInitialize', 'hashDispatch', 'tryOuter', 'containsOuter', 'containsInner', 'ctorInner', 'add',
    'dictionaryCtor','toList','getEnumerator','moveNext','remove','unwindNull','exceptionPropagate')
_METHODS = {
    'checkInit': ('IFix.Core.NewFieldInfo', 'CheckInit', ['IFix.Core.VirtualMachine', 'object'], 'void', False),
    'getValue': ('IFix.Core.NewFieldInfo', 'GetValue', ['object'], 'object', False),
    'setValue': ('IFix.Core.NewFieldInfo', 'SetValue', ['object', 'object'], 'void', False),
    'objectToIndex': ('IFix.Core.NewFieldInfo', 'ObjectToIndex', ['object'], 'int', False),
    'hasInitialize': ('IFix.Core.NewFieldInfo', 'HasInitialize', ['object'], 'bool', False),
    'setDefault': ('IFix.Core.NewFieldInfo', 'SetDefaultValue', ['object'], 'object', False),
    'beginForStack': ('IFix.Core.Call', 'BeginForStack', ['IFix.Core.ThreadStackInfo'], 'IFix.Core.Call', True),
    'weakCtor': ('System.WeakReference', '.ctor', ['object', 'bool'], 'void', False),
    'executeBridge': ('IFix.Core.VirtualMachine', 'Execute', ['int', 'IFix.Core.Call', 'int', 'int'], 'void', False),
    'getObject': ('IFix.Core.Call', 'GetObject', ['int'], 'object', False),
    'isValueType': ('System.Type', 'get_IsValueType', [], 'bool', False),
    'createInstance': ('System.Activator', 'CreateInstance', ['System.Type'], 'object', True),
    'staticConstructor': ('IFix.Core.NewFieldInfo','.cctor',[],'void',True),
    'sweep': ('IFix.Core.NewFieldInfo','Sweep',[],'void',True),
    'threadCtor': ('IFix.Core.ThreadStackInfo','.ctor',[],'void',False),
    'weakAlive': ('System.WeakReference','get_IsAlive',[],'bool',False),
}
_FIELDS = {'Name': ('string',16,False), 'DeclaringType': ('System.Type',24,False), 'FieldType': ('System.Type',32,False),
    'MethodId': ('int',40,False), 'staticObjectKey': ('int',0,True), 'stack': ('IFix.Core.ThreadStackInfo',8,True),
    'newFieldValues': ('System.Collections.Generic.Dictionary`2<int,System.Collections.Generic.Dictionary`2<string,object>>',16,True),
    'objList': ('System.Collections.Generic.Dictionary`2<int,System.WeakReference>',24,True)}
_STACK_FIELDS = {'IFix.Core.ThreadStackInfo': (False, {'UnmanagedStack': ('IFix.Core.UnmanagedStack*',16), 'ManagedStack': ('object[]',24)}),
    'IFix.Core.UnmanagedStack': (True, {'Base': ('IFix.Core.Value*',16), 'Top': ('IFix.Core.Value*',24)})}
_INNER = 'System.Collections.Generic.Dictionary`2<string,object>'
_CONTEXTS = {
    'ctorInner': ('.ctor', ['string','object'], 'ctorInner'), 'tryInner': ('TryGetValue',['string','object'],'tryInner'),
    'setInner': ('set_Item',['string','object'],'setInner'), 'containsInner': ('ContainsKey',['string','object'],'containsInner'),
    'getOuter': ('get_Item',['int',_INNER],'getOuter'), 'addWeak': ('Add',['int','System.WeakReference'],'add'),
    'addOuter': ('Add',['int',_INNER],'add'), 'containsOuter': ('ContainsKey',['int',_INNER],'containsOuter'),
    'tryOuter': ('TryGetValue',['int',_INNER],'tryOuter'), 'ctorOuter':('.ctor',['int',_INNER],'dictionaryCtor'),
    'ctorWeak':('.ctor',['int','System.WeakReference'],'dictionaryCtor'), 'removeOuter':('Remove',['int',_INNER],'remove'),
    'removeWeak':('Remove',['int','System.WeakReference'],'remove')}
_PAIR='System.Collections.Generic.KeyValuePair`2<int,System.WeakReference>'
_OTHER_CONTEXTS={'toList':('System.Linq.Enumerable','ToList',[],[_PAIR],'toList'),
    'getEnumerator':('System.Collections.Generic.List`1','GetEnumerator',[_PAIR],[],'getEnumerator'),
    'moveNext':('System.Collections.Generic.List`1+Enumerator','MoveNext',[_PAIR],[],'moveNext'),
    'getCurrent':('System.Collections.Generic.List`1+Enumerator','get_Current',[_PAIR],[],None),
    'dispose':('System.Collections.Generic.List`1+Enumerator','Dispose',[_PAIR],[],None),
    'pairKey':('System.Collections.Generic.KeyValuePair`2','get_Key',['int','System.WeakReference'],[],None),
    'pairValue':('System.Collections.Generic.KeyValuePair`2','get_Value',['int','System.WeakReference'],[],None)}
_TYPE_CELLS = {'newFieldType':'IFix.Core.NewFieldInfo', 'innerType':_INNER, 'weakType':'System.WeakReference',
    'threadType':'IFix.Core.ThreadStackInfo','outerType':'System.Collections.Generic.Dictionary`2<int,'+_INNER+'>',
    'weakDictionaryType':'System.Collections.Generic.Dictionary`2<int,System.WeakReference>'}
_CLAIMS = {'schema':'endfield.ifix-vm-new-field-rules.v2','evidenceBoundary':'conditional','executionBoundary':'unobserved',
    'callLayoutRef':'delegateBridgeRules.fieldLayouts.call','callValueBytes':40,'callObjectHeaderBytes':16,
    'keyRecipe':'owner-null:staticObjectKey;owner-nonnull:GetHashCode-slot-2;field-key:Name',
    'getRecipe':'outer-TryGetValue-out-dictionary-null-or-inner-miss:store-and-return-default;inner-hit:return-out-value',
    'setRecipe':'missing-outer-key:add-inner-dictionary;missing-key-and-owner-nonnull:add-WeakReference(owner,false);store-inner[Name]=value',
    'initializationRecipe':'MethodId>=0-and-not-HasInitialize:BeginForStack(static-stack);Execute(MethodId,ref-call,0,0);SetValue(owner,call.GetObject(0))',
    'defaultRecipe':'FieldType.IsValueType?Activator.CreateInstance(FieldType):null;SetValue(owner,default);return-default',
    'aliasBoundary':'hash-key-and-name-identity-only;collisions-mutable-names-and-runtime-aliases-unobserved',
    'stateBoundary':'conditional-static-constructor-and-snapshot-pruning-requests;runtime-state-and-current-layout-unobserved',
    'staticConstructorRecipe':'staticObjectKey=0;construct-and-store-ThreadStackInfo;construct-and-store-outer-and-weak-dictionaries;reference-write-barriers',
    'sweepRecipe':'ToList(objList);GetEnumerator;while-MoveNext:if-not-WeakReference.IsAlive(payload.qword-at-8):Remove-outer-and-weak(payload.int32-at-0)',
    'sweepPayloadBoundary':'typed-KeyValuePair-context-with-native-16-byte-current-copy;closed-generic-field-offsets-and-runtime-enumeration-unobserved',
    'exceptionBoundary':'stored-landing-and-unwind-bytes-authenticated;runtime-unwind-selection-and-cleanup-unobserved',
    'enumerationEntryBoundary':'canonical-pointer-family-only;fourth-registration-word-adjustor-invoker-and-runtime-entry-unobserved',
    'dictionaryBoundary':'stored-typed-context-registered-MethodDef-family-runtime-sharing-unresolved'}


def _need(ok: bool, detail: str) -> None:
    if not ok: raise NewFieldRuleError('newField.' + detail)


def _named(rows: list[dict], names: Any, label: str) -> dict[str, dict]:
    mapped = {row.get('name'): row for row in rows}
    _need(len(mapped) == len(rows) and set(mapped) == set(names), label + ': missing/duplicate/unknown declarations')
    return mapped


def _guard_type(image: Any, pointer: int, depth: int = 0, seen: frozenset[int] = frozenset()) -> None:
    _need(depth <= 8 and pointer not in seen, 'typed argument: recursive/deep carrier')
    raw = image.pe.bytes_at_va(pointer,16)
    _need(len(raw) == 16 and not raw[11] & 0x20, 'typed argument: by-reference/malformed carrier')
    kind = raw[10]
    _need(kind in (0x02,0x08,0x0e,0x1c,0x11,0x12,0x15), 'typed argument: unsupported generic/type kind')
    if kind == 0x15:
        carrier = image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),32)
        _need(len(carrier) == 32 and int.from_bytes(carrier[16:24],'little') == 0, 'typed argument: method-instantiated/malformed generic class')
        definition, inst = struct.unpack_from('<QQ',carrier)
        _need(image.pe.bytes_at_va(definition,16)[10] in (0x11,0x12), 'typed argument: generic definition kind differs')
        _guard_type(image,definition,depth+1,seen|{pointer})
        for argument in runtime_generic_inst_type_pointers(image.pe,inst): _guard_type(image,argument,depth+1,seen|{pointer})


def _type(image: Any, index: int, *, byref: bool = False) -> str:
    pointer = _type_pointer(image,index); raw = image.pe.bytes_at_va(pointer,16)
    _need(bool(raw[11] & 0x20) == byref, 'named signature: by-reference flag differs')
    if raw[10] == 0x15: _guard_type(image,pointer)
    elif raw[10] == 0x0f: _guard_type(image,int.from_bytes(raw[:8],'little'))
    return runtime_type_name(image.pe,image.metadata,pointer)


def _identity(image: Any, row: dict, role: str, extents: dict[int,int]) -> tuple[int,bytes]:
    owner,name,params,returned,static = _METHODS[role]; md=image.metadata
    _need((row.get('type'),row.get('method'),row.get('parameterCount')) == (owner,name,len(params))
          and row.get('parameterTypes') == params, role+': declared identity differs')
    selected=[]
    for t in md.types:
        if md.type_full_name(t) != owner: continue
        for m in md.methods_for(t):
            if md.string(m.name_index) != name or m.parameter_count != len(params): continue
            names=[_type(image,p.type_index,byref=role=='executeBridge' and k==1) for k,p in enumerate(md.parameters_for(m))]
            if names == params: selected.append(m)
    _need(len(selected)==1,role+': expected one named overload'); method=selected[0]
    _need(_type(image,method.return_type)==returned and bool(method.flags&0x10)==static and method.generic_container_index==-1
          and method.token==_rva(row['token']),role+': return/static/generic/token differs')
    for key in ('returnType','returnTypeName'):
        _need(key not in row or row[key]==returned,role+': declared return differs')
    rva=image.method_pointer_va(method)-image.pe.image_base
    _need(rva==_rva(row['rva']),role+': registered pointer differs')
    if 'bodyBytes' in row:
        size=row['bodyBytes'];_need(type(size)is int and 0<size<=65536 and extents.get(image.pe.image_base+rva)==image.pe.image_base+rva+size,role+': exact method extent differs')
        raw=image.pe.bytes_at_va(image.pe.image_base+rva,size);_hash(raw,{'byteCount':size,'sha256':row['bodySha256']},role)
    elif 'entryBytes' in row:
        raw=bytes.fromhex(row['entryBytes']);_expect(image.pe.bytes_at_va(image.pe.image_base+rva,len(raw)),raw,role+'.entry')
    else: raw=b''
    return rva,raw


def _dictionary_signature(image: Any, method: Any, name: str) -> None:
    signatures={'.ctor':([], 'void'), 'TryGetValue':([(0,False),(1,True)],'bool'), 'ContainsKey':([(0,False)],'bool'),
        'Add':([(0,False),(1,False)],'void'),'set_Item':([(0,False),(1,False)],'void'),'get_Item':([(0,False)],1),
        'Remove':([(0,False)],'bool')}
    md=image.metadata; params=md.parameters_for(method); expected,returned=signatures[name]
    # Even the parameterless constructor must be a reciprocal two-VAR owner.
    container=md.types[method.declaring_type].generic_container_index
    offset,size=struct.unpack_from('<II',md.buf,8+14*8)
    _need(0<=container<size//16 and size%16==0 and 128<=offset<=len(md.buf)-size,name+': Dictionary container range differs')
    owner,arity,is_method,start=struct.unpack_from('<iiii',md.buf,offset+container*16)
    _need(owner==method.declaring_type and arity==2 and is_method==0 and start>=0,name+': Dictionary owner/arity differs')
    for ordinal in range(2):
        resolved=type_parameter_owner(md.buf,start+ordinal,[t.generic_container_index for t in md.types],source='newField.dictionary-owner')
        _need(resolved['typeIndex']==owner and resolved['ordinal']==ordinal,name+': Dictionary reciprocal owner differs')
    _need(method.parameter_count==len(params)==len(expected) and not method.flags&0x10 and method.generic_container_index==-1,
          name+': dictionary instance overload differs')
    for index,ordinal,byref in [(p.type_index,ordinal,byref) for p,(ordinal,byref) in zip(params,expected)] + ([(method.return_type,returned,False)] if type(returned)is int else []):
        raw=image.pe.bytes_at_va(_type_pointer(image,index),16)
        _need(raw[10]==0x13 and bool(raw[11]&0x20)==byref,name+': expected VAR/out-VAR carrier')
        owner=type_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),[t.generic_container_index for t in md.types],source='newField.dictionary')
        _need(owner['typeIndex']==method.declaring_type and owner['ordinal']==ordinal
              and struct.unpack_from('<i',bytes.fromhex(owner['containerRawHex']),4)[0]==2,name+': reciprocal VAR owner/ordinal/arity differs')
    if isinstance(returned,str): _need(_type(image,method.return_type)==returned,name+': dictionary return differs')


def _var(image: Any, pointer: int, method: Any, ordinal: int, *, method_owned: bool, arity: int) -> None:
    md=image.metadata;raw=image.pe.bytes_at_va(pointer,16)
    _need(len(raw)==16 and raw[10]==(0x1e if method_owned else 0x13) and not raw[11]&0x20,'enumeration: expected non-byref VAR/MVAR')
    resolver=method_parameter_owner if method_owned else type_parameter_owner
    containers=[m.generic_container_index for m in md.methods] if method_owned else [t.generic_container_index for t in md.types]
    owner=resolver(md.buf,int.from_bytes(raw[:8],'little'),containers,source='newField.enumeration')
    _need(owner['methodIndex' if method_owned else 'typeIndex']==(method.index if method_owned else method.declaring_type)
          and owner['ordinal']==ordinal and struct.unpack_from('<i',bytes.fromhex(owner['containerRawHex']),4)[0]==arity,
          'enumeration: reciprocal owner/ordinal/arity differs')


def _open_generic(image: Any, index: int, name: str, method: Any, *, method_owned: bool) -> None:
    pointer=_type_pointer(image,index);raw=image.pe.bytes_at_va(pointer,16)
    _need(raw[10]==0x15 and not raw[11]&0x20,'enumeration: expected non-byref constructed signature')
    carrier=image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),32);definition,inst=struct.unpack_from('<QQ',carrier)
    _need(int.from_bytes(carrier[16:24],'little')==0,'enumeration: unexpected generic method carrier')
    _guard_type(image,definition)
    _need(runtime_type_name(image.pe,image.metadata,definition)==name,'enumeration: constructed definition differs')
    args=runtime_generic_inst_type_pointers(image.pe,inst)
    _need(len(args)==1,'enumeration: one generic argument required')
    _var(image,args[0],method,0,method_owned=method_owned,arity=1)


def _other_signature(image: Any, method: Any, role: str) -> None:
    md=image.metadata;params=md.parameters_for(method)
    if role=='toList':
        _need(method.parameter_count==len(params)==1 and method.flags&0x10 and method.generic_container_index>=0,
              'ToList: static one-parameter generic overload differs')
        _open_generic(image,params[0].type_index,'System.Collections.Generic.IEnumerable`1',method,method_owned=True)
        _open_generic(image,method.return_type,'System.Collections.Generic.List`1',method,method_owned=True)
        return
    _need(method.parameter_count==len(params)==0 and not method.flags&0x10 and method.generic_container_index==-1,
          role+': enumeration instance zero-parameter overload differs')
    if role=='getEnumerator':
        _open_generic(image,method.return_type,'System.Collections.Generic.List`1+Enumerator',method,method_owned=False)
    elif role in ('getCurrent','pairKey','pairValue'):
        _var(image,_type_pointer(image,method.return_type),method,1 if role=='pairValue'else 0,method_owned=False,
             arity=2 if role.startswith('pair')else 1)
    else:
        _need(_type(image,method.return_type)==('bool'if role=='moveNext'else 'void'),role+': enumeration return differs')
        # Void/Boolean results have no VAR to authenticate their class owner.
        container=md.types[method.declaring_type].generic_container_index
        base,size=struct.unpack_from('<II',md.buf,8+14*8)
        _need(0<=container<size//16 and size%16==0 and 128<=base<=len(md.buf)-size,role+': generic class container range differs')
        owner,arity,is_method,start=struct.unpack_from('<iiii',md.buf,base+container*16)
        _need(owner==method.declaring_type and arity==1 and is_method==0,role+': enumeration class owner differs')
        reciprocal=type_parameter_owner(md.buf,start,[t.generic_container_index for t in md.types],source='newField.enumerator-owner')
        _need(reciprocal['typeIndex']==owner and reciprocal['ordinal']==0,role+': reciprocal enumeration owner differs')


def _canonical_target(image: Any, definition: int, target: int) -> None:
    """Prove canonical pointer membership without following any adjustor word."""
    pe,reg=image.pe,image.registration;code=image.mapper.code_registration_summary(pe,image.code_registration)
    counts=(reg['methodSpecsCount'],reg['genericMethodTableCount'],code['genericMethodPointersCount'],code['invokerPointersCount'])
    _need(all(type(n)is int and 0<=n<=1_000_000 for n in counts),'enumeration: bounded registration counts required')
    spec_count,record_count,pointer_count,invoker_count=counts
    specs=pe.bytes_at_va(_rva(reg['methodSpecs']),spec_count*12)
    selected=set()
    for k,(d,_c,_m)in enumerate(struct.iter_unpack('<iii',specs)):
        if d!=definition:continue
        method_spec_record(specs[k*12:(k+1)*12],len(image.metadata.methods),reg['genericInstsCount'],
            source='newField.enumeration-family',offset=_rva(reg['methodSpecs'])+k*12)
        selected.add(k)
    records=pe.bytes_at_va(_rva(reg['genericMethodTable']),record_count*16)
    pointers=pe.bytes_at_va(_rva(code['genericMethodPointers']),pointer_count*8);found=False
    for spec,slot,_invoker,_fourth in struct.iter_unpack('<iiii',records):
        _need(0<=spec<spec_count,'enumeration: MethodSpec key outside table')
        if spec not in selected:continue
        _need(0<=slot<pointer_count,'enumeration: canonical slot outside table')
        if struct.unpack_from('<Q',pointers,slot*8)[0]!=pe.image_base+target:continue
        project_generic_canonical_entry(records,pointers,record_count=record_count,pointer_count=pointer_count,
            spec_count=spec_count,selected_spec=spec,invoker_count=invoker_count);found=True
    _need(found,'enumeration: direct target lacks canonical MethodDef-family candidate')


def _usage(image: Any, row: dict) -> int | None:
    name=row['name'];cell=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+cell,8)
    _need(raw==bytes.fromhex(row['rawHex']),name+': stored usage bytes differ');md,reg=image.metadata,image.registration
    if name in _TYPE_CELLS:
        _need(row.get('tag')==1 and row.get('identity')==_TYPE_CELLS[name],name+': type usage declaration differs')
        index=unresolved_usage_index(raw,reg['typesCount'],tag=1,source='newField.'+name,offset=cell)
        pointer=_type_pointer(image,index);_guard_type(image,pointer)
        _need(runtime_type_name(image.pe,md,pointer)==_TYPE_CELLS[name],name+': type usage differs');return None
    if name in _CONTEXTS:
        method_name,expected_args,target=_CONTEXTS[name];owner='System.Collections.Generic.Dictionary`2';method_args=[]
    else:owner,method_name,expected_args,method_args,target=_OTHER_CONTEXTS[name]
    _need(row.get('tag')==6 and row.get('type')==owner and row.get('method')==method_name
          and row.get('classArgs')==expected_args and row.get('methodArgs')==method_args and row.get('target')==target,
          name+': typed context declaration differs')
    at=_rva(reg['methodSpecs']);rec=usage_method_spec(raw,image.pe.bytes_at_va(at,reg['methodSpecsCount']*12),len(md.methods),
        reg['genericInstsCount'],source='newField.'+name,usage_offset=image.pe.image_base+cell,records_offset=at)
    method=md.methods[rec['definition']];args=image.instantiations.resolve(rec['classInstantiationIndex']).arguments
    method_arguments=image.instantiations.resolve(rec['methodInstantiationIndex']).arguments
    for arg in (*args,*method_arguments):
        _need(bytes.fromhex(arg.raw_type_record_hex)==image.pe.bytes_at_va(arg.type_pointer_va,16),name+': argument snapshot differs')
        _guard_type(image,arg.type_pointer_va)
    _need((rec['classInstantiationIndex']==-1 if name=='toList'else rec['classInstantiationIndex']>=0)
          and (rec['methodInstantiationIndex']>=0 if name=='toList'else rec['methodInstantiationIndex']==-1)
          and md.type_full_name(md.types[method.declaring_type])==owner
          and md.string(method.name_index)==method_name and [runtime_type_name(image.pe,md,a.type_pointer_va) for a in args]==expected_args,
          name+': stored typed MethodSpec differs')
    _need([runtime_type_name(image.pe,md,a.type_pointer_va) for a in method_arguments]==method_args,name+': stored method instantiation differs')
    if name in _CONTEXTS:_dictionary_signature(image,method,method_name)
    else:_other_signature(image,method,name)
    return rec['definition']


def _layouts(image: Any, spec: dict, contract: dict) -> None:
    md=image.metadata; layout=spec['fieldLayout'];owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.NewFieldInfo']
    _need(layout.get('type')=='IFix.Core.NewFieldInfo' and layout.get('isValueType')is False and len(owners)==1
          and not owners[0].bitfield&1 and set(layout['fields'])==set(_FIELDS),'new-field layout owner/set differs')
    owner=owners[0];definitions={md.string(f.name_index):f for f in md.fields_for(owner)};offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index)
    for name,(typ,offset,static) in _FIELDS.items():
        row=layout['fields'][name];field=definitions[name];raw=image.pe.bytes_at_va(_type_pointer(image,field.type_index),16)
        _need(row=={'type':typ,'offset':offset,'static':static} and offsets[name]==offset and _type(image,field.type_index)==typ
              and bool(int.from_bytes(raw[8:10],'little')&0x10)==static,name+': named instance/static layout differs')
    layouts={r.get('type'):r for r in spec['stackLayouts']}
    _need(len(layouts)==len(spec['stackLayouts']) and set(layouts)==set(_STACK_FIELDS),'stack layout set differs')
    for name,(value,fields) in _STACK_FIELDS.items():
        row=layouts[name];types=[t for t in md.types if md.type_full_name(t)==name]
        _need(len(types)==1 and bool(types[0].bitfield&1)==value and row.get('isValueType')==value and set(row['fields'])==set(fields),name+': layout owner/set differs')
        offsets=runtime_type_field_offsets(md,image.pe,image.registration,types[0].index);definitions={md.string(f.name_index):f for f in md.fields_for(types[0])}
        for field,(typ,offset) in fields.items():
            _need(row['fields'][field]=={'type':typ,'offset':offset} and offsets[field]==offset and _type(image,definitions[field].type_index)==typ,name+'.'+field+': named layout differs')
    call=_ref(contract,spec['callLayoutRef']);types=[t for t in md.types if md.type_full_name(t)=='IFix.Core.Call']
    _need(call.get('type')=='IFix.Core.Call' and call.get('isValueType')is True and len(types)==1 and types[0].bitfield&1,'Call: value owner differs')
    expected={'argumentBase':16,'evaluationStackBase':24,'managedStack':32,'currentTop':40,'topWriteBack':48}
    _need(call.get('fieldOffsets')==runtime_type_field_offsets(md,image.pe,image.registration,types[0].index)==expected,'Call: boxed-to-unboxed offsets differ')


def _hash_virtual(image: Any, row: dict) -> None:
    _need(row=={'type':'System.Object','method':'GetHashCode','parameterTypes':[],'returnType':'int','slot':2},'hash virtual declaration differs')
    md=image.metadata;selected=[m for t in md.types if md.type_full_name(t)=='System.Object' for m in md.methods_for(t)
        if md.string(m.name_index)=='GetHashCode' and m.parameter_count==0]
    _need(len(selected)==1 and selected[0].slot==2 and selected[0].flags&0x40 and not selected[0].flags&0x10
          and selected[0].generic_container_index==-1 and _type(image,selected[0].return_type)=='int','hash virtual slot/signature differs')


_PROGRAMS = {
    'setDefault': {
        'entry': ('48895c24084889742410574883ec20488bf9488bf2488b49204885c9', ('jne8', 'type'), ('call', 'nullFailure'), 'cc'),
        'type': ('33d2', ('call', 'isValueType'), '84c0', ('jne8', 'valueType'), '4533c94533c0488bd6488bcf', ('call', 'setValue'), '33c0', ('jmp8', 'return')),
        'valueType': ('488b4f2033d2', ('call', 'createInstance'), '4533c94c8bc0488bd6488bcf488bd8', ('call', 'setValue'), '488bc3'),
        'return': ('488b5c2430488b7424384883c4205fc3',),
    },
    'sweep': {
        'entry': ('40534881ec800000000f29742470', ('rip', '803d', 'flag', '00'), ('jne8', 'snapshot'), ('rip', '488d0d', 'removeOuter', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'removeWeak', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'toList', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'dispose', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'moveNext', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'getCurrent', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'pairKey', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'pairValue', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'getEnumerator', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'newFieldType', ''), ('call', 'typeInitialize'), ('rip', 'c605', 'flag', '01')),
        'snapshot': (('rip', '488b0d', 'newFieldType', ''), ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '488b88b8000000', ('rip', '488b15', 'toList', ''), '488b4918', ('call', 'toList'), '4885c0', ('je', 'nullExit'), ('rip', '4c8b05', 'getEnumerator', ''), '488bd0488d4c2428', ('call', 'getEnumerator'), '0f104424280f114424480f104c24380f114c2458488364242800488d4424484889442430'),
        'loop': (('rip', '488b15', 'moveNext', ''), '488d4c2448', ('call', 'moveNext'), '84c0', ('je', 'complete'), '0f10742458660f6fc6660f73d80866480f7ec14885c9', ('je', 'currentNullUnwind'), '33d2', ('call', 'weakAlive'), '84c0', ('jne8', 'loop')),
        'remove': (('rip', '488b0d', 'newFieldType', ''), ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '488b88b8000000488b49104885c9', ('je8', 'outerNullUnwind'), ('rip', '4c8b05', 'removeOuter', ''), '660f7ef2', ('call', 'remove'), ('rip', '488b05', 'newFieldType', ''), '488b88b8000000488b49184885c9', ('je8', 'weakNullUnwind'), ('rip', '4c8b05', 'removeWeak', ''), '660f7ef2', ('call', 'remove'), ('jmp', 'loop')),
        'complete': (('jmp8', 'return'),),
        'landing': ('488b4c24284885c9', ('jne8', 'propagate')),
        'return': ('0f287424704881c4800000005bc3',),
        'nullExit': (('call', 'nullFailure'), '90'),
        'weakNullUnwind': (('call', 'unwindNull'), '90'),
        'outerNullUnwind': (('call', 'unwindNull'),),
        'currentNullUnwind': (('call', 'unwindNull'), '90'),
        'propagate': (('call', 'exceptionPropagate'), 'cc'),
    },
    'checkInit': {
        'entry': ('48895c24084889742410574881ec80000000', ('rip', '803d', 'flag', '00'), '498bf8488bf2488bd9', ('jne8', 'check'), ('rip', '488d0d', 'newFieldType', ''), ('call', 'typeInitialize'), ('rip', 'c605', 'flag', '01')),
        'check': ('33c00f57c00f1144243048894424500f11442440394328', ('jl', 'return'), '4533c0488bd7488bcb', ('call', 'hasInitialize'), '84c0', ('jne', 'return'), ('rip', '488b0d', 'newFieldType', ''), ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '4533c0488b88b8000000488b5108488d4c2458', ('call', 'beginForStack'), '0f10000f114424300f1048100f114c2440f20f104020f20f114424504885f6', ('jne8', 'execute'), ('call', 'nullFailure'), 'cc'),
        'execute': ('4883642428004c8d4424308b53284533c98364242000488bce', ('call', 'executeBridge'), '4533c0488d4c243033d2', ('call', 'getObject'), '4533c94c8bc0488bd7488bcb', ('call', 'setValue')),
        'return': ('4c8d9c2480000000498b5b10498b7318498be35fc3',),
    },
    'objectToIndex': {
        'entry': ('40534883ec20', ('rip', '803d', 'flag', '00'), '488bda', ('jne8', 'select'), ('rip', '488d0d', 'newFieldType', ''), ('call', 'typeInitialize'), ('rip', 'c605', 'flag', '01')),
        'select': ('4885db', ('je8', 'static'), 'b902000000488bd34883c4205b', ('tail', 'hashDispatch')),
        'static': (('rip', '488b0d', 'newFieldType', ''), ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '488b80b80000008b004883c4205bc3'),
    },
    'hasInitialize': {
        'entry': ('48895c2408574883ec20', ('rip', '803d', 'flag', '00'), '488bfa488bd9', ('jne8', 'lookup'), ('rip', '488d0d', 'containsOuter', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'containsInner', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'tryOuter', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'newFieldType', ''), ('call', 'typeInitialize'), ('rip', 'c605', 'flag', '01')),
        'lookup': ('4533c0488bd7488bcb', ('call', 'objectToIndex'), ('rip', '488b0d', 'newFieldType', ''), '8bf8', ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '488b88b8000000488b49104885c9', ('je8', 'nullExit'), ('rip', '4c8b05', 'containsOuter', ''), '8bd7', ('call', 'containsOuter'), '84c0', ('je8', 'false'), ('rip', '488b0d', 'newFieldType', ''), '488364243800', ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '488b88b8000000488b49104885c9', ('je8', 'nullExit'), ('rip', '4c8b0d', 'tryOuter', ''), '4c8d4424388bd7', ('call', 'tryOuter'), '488b4c24384885c9', ('je8', 'nullExit'), ('rip', '4c8b05', 'containsInner', ''), '488b5310', ('call', 'containsInner'), '84c0', ('je8', 'false'), 'b001'),
        'return': ('488b5c24304883c4205fc3',),
        'false': ('32c0', ('jmp8', 'return')),
        'nullExit': (('call', 'nullFailure'), 'cc'),
    },
    'getValue': {
        'entry': ('48895c24084889742418574883ec20', ('rip', '803d', 'flag', '00'), '488bfa488bd9', ('jne8', 'lookup'), ('rip', '488d0d', 'tryOuter', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'tryInner', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'newFieldType', ''), ('call', 'typeInitialize'), ('rip', 'c605', 'flag', '01')),
        'lookup': ('4533c0488bd7488bcb', ('call', 'objectToIndex'), ('rip', '488b0d', 'newFieldType', ''), '8bf0488364243800', ('call', 'classInitialize'), ('rip', '488b0d', 'newFieldType', ''), '488b91b8000000488b4a104885c9', ('jne8', 'outer'), ('call', 'nullFailure'), 'cc'),
        'outer': (('rip', '4c8b0d', 'tryOuter', ''), '4c8d4424388bd6', ('call', 'tryOuter'), '488b4c24384885c9', ('je8', 'default'), ('rip', '4c8b0d', 'tryInner', ''), '4c8d442448488b5310488364244800', ('call', 'tryInner'), '84c0', ('je8', 'default'), '488b442448', ('jmp8', 'return')),
        'default': ('4533c0488bd7488bcb', ('call', 'setDefault')),
        'return': ('488b5c2430488b7424404883c4205fc3',),
    },
    'setValue': {
        'entry': ('48895c240848896c2410488974241857415641574883ec20', ('rip', '803d', 'flag', '00'), '4d8bf8488bea4c8bf1', ('jne8', 'lookup'), ('rip', '488d0d', 'addWeak', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'addOuter', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'containsOuter', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'ctorInner', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'getOuter', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'setInner', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'innerType', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'newFieldType', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'weakType', ''), ('call', 'typeInitialize'), ('rip', 'c605', 'flag', '01')),
        'lookup': ('4533c0488bd5498bce', ('call', 'objectToIndex'), ('rip', '488b0d', 'newFieldType', ''), '8bf8', ('call', 'classInitialize'), ('rip', '488b0d', 'newFieldType', ''), '488b91b8000000488b4a104885c9', ('je', 'nullExit'), ('rip', '4c8b05', 'containsOuter', ''), '8bd7', ('call', 'containsOuter'), '84c0', ('jne', 'store'), ('rip', '488b0d', 'newFieldType', ''), ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '488b88b8000000488b7110', ('rip', '488b0d', 'innerType', ''), ('call', 'allocate'), '488bd84885c0', ('je', 'nullExit'), ('rip', '488b15', 'ctorInner', ''), '488bc8', ('call', 'ctorInner'), '4885f6', ('je', 'nullExit'), ('rip', '4c8b0d', 'addOuter', ''), '4c8bc38bd7488bce', ('call', 'add'), '4885ed', ('je8', 'store'), ('rip', '488b0d', 'newFieldType', ''), ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '488b88b8000000488b7118', ('rip', '488b0d', 'weakType', ''), ('call', 'allocate'), '488bd84885c0', ('je', 'nullExit'), '4533c94533c0488bd5488bc8', ('call', 'weakCtor'), '4885f6', ('je8', 'nullExit'), ('rip', '4c8b0d', 'addWeak', ''), '4c8bc38bd7488bce', ('call', 'add')),
        'store': (('rip', '488b0d', 'newFieldType', ''), ('call', 'classInitialize'), ('rip', '488b05', 'newFieldType', ''), '488b88b8000000488b49104885c9', ('je8', 'nullExit'), ('rip', '4c8b05', 'getOuter', ''), '8bd7', ('call', 'getOuter'), '4885c0', ('je8', 'nullExit'), ('rip', '4c8b0d', 'setInner', ''), '4d8bc7498b5610488bc8488b5c2440488b6c2448488b7424504883c420415f415e5f', ('tail', 'setInner')),
        'nullExit': (('call', 'nullFailure'), 'cc'),
    },
    'staticConstructor': {
        'entry': ('40534883ec20', ('rip', '803d', 'flag', '00'), ('jne8', 'initialize'), ('rip', '488d0d', 'ctorWeak', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'ctorOuter', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'weakDictionaryType', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'outerType', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'newFieldType', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'threadType', ''), ('call', 'typeInitialize'), ('rip', 'c605', 'flag', '01')),
        'initialize': (('rip', '488b05', 'newFieldType', ''), '488b88b8000000832100', ('rip', '488b0d', 'threadType', ''), ('call', 'allocate'), '488bd84885c0', ('je', 'nullExit'), '33d2488bc8', ('call', 'threadCtor'), ('rip', '488b0d', 'newFieldType', ''), '488b91b800000048895a08', ('rip', '488b05', 'newFieldType', ''), '488b88b80000004883c108', ('call', 'writeBarrier'), ('rip', '488b0d', 'outerType', ''), ('call', 'allocate'), '488bd84885c0', ('je', 'nullExit'), ('rip', '488b15', 'ctorOuter', ''), '488bc8', ('call', 'dictionaryCtor'), ('rip', '488b0d', 'newFieldType', ''), '488b91b800000048895a10', ('rip', '488b05', 'newFieldType', ''), '488b88b80000004883c110', ('call', 'writeBarrier'), ('rip', '488b0d', 'weakDictionaryType', ''), ('call', 'allocate'), '488bd84885c0', ('je8', 'nullExit'), ('rip', '488b15', 'ctorWeak', ''), '488bc8', ('call', 'dictionaryCtor'), ('rip', '488b0d', 'newFieldType', ''), '488b91b800000048895a18', ('rip', '488b05', 'newFieldType', ''), '488b88b80000004883c1184883c4205b', ('tail', 'writeBarrier')),
        'nullExit': (('call', 'nullFailure'), 'cc'),
    },
    'beginForStack': {
        'entry': ('4883ec280f57c033c04c8bd24c8bc90f11010f114110488941204885d2', ('je8', 'nullExit'), '488b4218488941104883c110', ('call', 'writeBarrier'), '498b42104885c0', ('je8', 'nullExit'), '488b400849894118498b42104885c0', ('je8', 'nullExit'), '488b4008498901498b42104885c0', ('je8', 'nullExit'), '488b0049894108498b42104885c0', ('je8', 'nullExit'), '4883c00849894120498bc14883c428c3'),
        'nullExit': (('call', 'nullFailure'), 'cc'),
    },
}

_NEAR={'je':'0f84','jne':'0f85','jl':'0f8c','jmp':'e9'}
_SHORT={'je8':0x74,'jne8':0x75,'jmp8':0xeb}


def _program(base: int, blocks: dict, targets: dict[str,int], cells: dict[str,int], flag: int = 0) -> tuple[bytes,dict[str,int]]:
    p=_Program(base);near=[];cells=dict(cells,flag=flag)
    for label,tokens in blocks.items():
        p.mark(label)
        for token in tokens:
            if isinstance(token,str):p.add(token);continue
            kind,*args=token
            if kind=='call':p.call(targets[args[0]])
            elif kind=='tail':p.add('e9');p.add((targets[args[0]]-base-len(p.raw)-4).to_bytes(4,'little',signed=True))
            elif kind=='rip':p.rip(args[0],cells[args[1]],bytes.fromhex(args[2]))
            elif kind in _SHORT:p.branch(_SHORT[kind],args[0])
            elif kind in _NEAR:p.add(_NEAR[kind]);near.append((len(p.raw),args[0]));p.add(bytes(4))
            else:_need(False,'unknown finite program token')
    for at,label in near:p.raw[at:at+4]=(p.labels[label]-at-4).to_bytes(4,'little',signed=True)
    return p.finish(),{name:base+at for name,at in p.labels.items()}


def validate_new_field_rules(image: Any, spec: dict, contract: dict, extents: dict[int,int]) -> dict:
    """Validate one gated image after its inherited groups were validated."""
    _need(all(spec.get(k)==v for k,v in _CLAIMS.items()) and spec.get('methodRefs')==_METHOD_REFS and spec.get('helperRefs')==_HELPER_REFS,
          'unsupported schema/reference/boundary')
    _layouts(image,spec,contract);_hash_virtual(image,spec['hashVirtual']);targets={};bodies={}
    methods=_named(spec['methods'],set(_METHODS)-set(_METHOD_REFS),'methods')
    for name in _METHODS:
        row=_ref(contract,_METHOD_REFS[name]) if name in _METHOD_REFS else methods[name]
        targets[name],bodies[name]=_identity(image,row,name,extents)
    for name,row in {**_named(spec['helpers'],_OWN_HELPERS,'helpers'),**{n:_ref(contract,path)for n,path in _HELPER_REFS.items()}}.items():
        targets[name]=_rva(row['rva']);size=row['byteCount']
        _need(type(size)is int and 0<size<=65536,name+': invalid helper window length')
        _hash(image.pe.bytes_at_va(image.pe.image_base+targets[name],size),row,name)
    usages=_named(spec['usageCells'],set(_TYPE_CELLS)|set(_CONTEXTS)|set(_OTHER_CONTEXTS),'usages');cells={}
    for name,row in usages.items():
        cells[name]=_rva(row['cellRva']);definition=_usage(image,row)
        if definition is not None:
            target=_CONTEXTS[name][2]if name in _CONTEXTS else _OTHER_CONTEXTS[name][4]
            if target is not None:
                (_dictionary_target if name in _CONTEXTS else _canonical_target)(image,definition,targets[target])
    _need(set(spec['initializationFlags'])=={'checkInit','getValue','setValue','objectToIndex','hasInitialize','staticConstructor','sweep'},'initialization flag set differs')
    labels={}
    for name,blocks in _PROGRAMS.items():
        program,labels[name]=_program(targets[name],blocks,targets,cells,_rva(spec['initializationFlags'].get(name,0)))
        _expect(bodies[name],program,'newField.'+name+'.full-finite-arguments-and-control')
    # The dispatcher is explicitly opaque after its shared slot-load prefix.
    # Prove the slot pair/hidden MethodInfo forwarding shape, then retain its
    # entire hashed body without asserting fast-path or actual hash outcomes.
    p=_Program(targets['hashDispatch']);p.add('48895c240855565741544155415641574883ec504c8bf20fb7d9488b0a')
    p.call(targets['hashClassPrepare']);p.add('488d431448c1e0044903064c8b00488b5008')
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['hashDispatch'],len(p.raw)),p.finish(),'newField.hashDispatch.slot-selection-prefix')
    return {'status':'validated_conditional_new_field_recipe','evidenceBoundary':'conditional','executionBoundary':'unobserved',
        **{k:spec[k] for k in ('keyRecipe','getRecipe','setRecipe','initializationRecipe','defaultRecipe','aliasBoundary','stateBoundary',
            'staticConstructorRecipe','sweepRecipe','sweepPayloadBoundary','exceptionBoundary')},
        'entryRvas':{n:{k:hex(v)for k,v in rows.items()}for n,rows in labels.items()},
        'unresolved':['runtime-static-storage-and-aliases','hash-dispatch-outcome-and-collisions','mutable-field-names',
            'dictionary-comparer-results-and-exact-generic-sharing','static-initialization-execution-and-storage',
            'closed-generic-current-field-offsets-and-enumeration','weak-reference-liveness-and-removal-results','runtime-unwind-selection-and-cleanup',
            'enumeration-adjustor-table-and-full-generic-entry',
            'allocation-and-weak-reference-outcomes',
            'reflection-and-default-creation-success','initializer-stack-values-and-execution','helper-mutation-and-concurrency','actual-execution']}


def validate_selected_new_field_rules(contract: dict, *, gameassembly: Path, metadata: Path, spec: dict | None = None) -> dict:
    """Fail closed without falling back from the explicit selected native pair."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit GameAssembly and metadata paths are required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'nativeInputs: selected hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.newFields')
    return validate_new_field_rules(image,contract['newFieldRules'] if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
