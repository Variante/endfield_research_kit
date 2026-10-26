"""Authenticate IFix VM table, callback and lifecycle callers offline.

The VM constructor requests ObjectClone and two typed dictionaries, stores the
incoming instruction table and disposal callback, and requests Cleanner.Start.
ExternMethods stores its input before reading the stored array's length and
requesting an ExternInvoker array. StaticFieldTypes requests an object array
from a nonnull input's length (null otherwise), stores that table first, then
stores the input Types. Neither setter explicitly initializes array elements.

VM static initialization lazily requests Action<string> for the encoded
Console.WriteLine(string) MethodDef, caches it and copies the cache to Info.
_Info checks/reloads Info and forwards its message to an opaque delegate target.
Finalize forwards onDispose, requests Cleanner.Stop, then clears unmanagedCodes
on its normal path. Its local exception-context landing and failure requests
are included; external exception-entry selection and unwinding remain open.

ObjectClone's constructor requests object Type and GetMethod(MemberwiseClone,
Instance|NonPublic), then stores the returned MethodInfo without a result-null
test. Clone null-guards memberwiseClone and tails to MethodBase.Invoke
with the incoming object retained and null R8/R9. Cleanner.Start sets its static start byte before requesting a Cleanner
object when the byte was zero. Stop conditionally requests class preparation
from a native class word, then clears start. Cleanner's static constructor clears
start; its Finalize requests the already-proved NewFieldInfo.Sweep and Start only
when a fresh start byte is nonzero. Its registered constructor is a finite RET
with zero pop immediate, without a pdata function extent. No thread/timer execution is proved.

Complete finite bodies authenticate the caller orders, repeats, branches,
barriers and tails. Deep raw carriers, typed MethodSpec contexts and canonical
Dictionary constructor family membership authenticate stored selections while
preserving runtime sharing. Allocation/defaults, delegate/reflection results,
callback identities, live fields, aliases, class state, GC and execution remain
conditional. Native anchors live in reviewed JSON, with explicit input gates.
Zero-pdata accessors and framework internals are not assigned complete extents.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index, literal_record, usage_method_spec
from scripts.game_data.il2cpp.protocol import runtime_type_name, runtime_type_field_offsets, enum_members, field_defaults
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect, _type, _identity
from scripts.game_data.ifix_vm_reference_helper_rules import _address, _mapped_span
from scripts.game_data.ifix_vm_object_opcode_rules import _carrier as _ordinary_carrier, _method_declaration, _cell_declaration
from scripts.game_data.ifix_vm_call_opcode_rules import _carrier as _compound_carrier
from scripts.game_data.ifix_vm_new_field_rules import _guard_type, _canonical_target


class VmConstructionRuleError(ValueError):
    """A lifecycle/storage claim lacks its selected native witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok: raise VmConstructionRuleError('vm-construction.' + detail)


_METHOD_REFS = {'info': 'stackConstructionRules.methods.logInfo', 'typeFromHandle': 'genericDelegateFactoryRules.methods.getTypeFromHandle',
 'clone':'slotCopyRules.methods.clone','sweep':'newFieldRules.methods.sweep'}
_METHODS = {
 'constructor': ('IFix.Core.VirtualMachine', '.ctor', ['IFix.Core.Instruction**', 'System.Action'], 'void', False),
 'externMethods': ('IFix.Core.VirtualMachine', 'set_ExternMethods', ['System.Reflection.MethodBase[]'], 'void', False),
 'staticFieldTypes': ('IFix.Core.VirtualMachine', 'set_StaticFieldTypes', ['System.Type[]'], 'void', False),
 'staticConstructor': ('IFix.Core.VirtualMachine', '.cctor', [], 'void', True),
 'finalize': ('IFix.Core.VirtualMachine', 'Finalize', [], 'void', False),
 'info': ('IFix.Core.VirtualMachine', '_Info', ['string'], 'void', True),
 'objectCloneCtor': ('IFix.Core.ObjectClone', '.ctor', [], 'void', False),
 'cleanerStart': ('IFix.Core.Cleanner', 'Start', [], 'void', True),
 'cleanerStop': ('IFix.Core.Cleanner', 'Stop', [], 'void', True),
 'cleanerFinalize': ('IFix.Core.Cleanner', 'Finalize', [], 'void', False),
 'cleanerStaticConstructor': ('IFix.Core.Cleanner', '.cctor', [], 'void', True),
 'cleanerCtor': ('IFix.Core.Cleanner', '.ctor', [], 'void', False),
 'clone': ('IFix.Core.ObjectClone', 'Clone', ['object'], 'object', False),
 'sweep': ('IFix.Core.NewFieldInfo', 'Sweep', [], 'void', True),
 'cloneInvoke': ('System.Reflection.MethodBase', 'Invoke', ['object','object[]'], 'object', False),
 'getMethod': ('System.Type', 'GetMethod', ['string', 'System.Reflection.BindingFlags'], 'System.Reflection.MethodInfo', False),
 'typeFromHandle': ('System.Type', 'GetTypeFromHandle', ['System.RuntimeTypeHandle'], 'System.Type', True),
}
_HELPER_REFS = {'typeInitialize':'referenceUpdateRules.helpers.typeInitialize','writeBarrier':'delegateBridgeRules.referenceWriteBarrier',
 'allocateObject':'stackReferenceRules.nullObjectHelper','arrayAllocate':'objectConversionRules.helpers.arrayAllocate',
 'classInitialize':'newFieldRules.helpers.classInitialize','classPrepare':'anonymousStoreyRules.helpers.classInitialize',
 'nullFailure':'referenceUpdateRules.helpers.nullFailure','dictionaryCtor':'virtualDispatchRules.helpers.dictionaryCtorBody',
 'unwindNull':'newFieldRules.helpers.unwindNull','exceptionPropagate':'newFieldRules.helpers.exceptionPropagate'}
_OWN_HELPERS = {'actionInvoke','loggerCtor','loggerInvoke'}
_USAGE_REFS = {'vmType':'stackConstructionRules.usageCells.vmType','objectArray':'objectConversionRules.usageCells.class_objectArray',
 'systemType':'objectConversionRules.usageCells.class_System_Type','newFieldType':'newFieldRules.usageCells.newFieldType'}
_TYPE_CELLS = {'vmType':(1,'IFix.Core.VirtualMachine'),'objectArray':(1,'object[]'),'systemType':(1,'System.Type'),'newFieldType':(1,'IFix.Core.NewFieldInfo'),
 'cleanerType':(1,'IFix.Core.Cleanner'),'objectCloneType':(1,'IFix.Core.ObjectClone'),'externInvokerArray':(1,'IFix.Core.ExternInvoker[]'),
 'calliDictionary':(1,'System.Collections.Generic.Dictionary`2<System.Reflection.MethodBase,IFix.Core.VirtualMachine+CalliInvokerInfo>'),
 'overrideDictionary':(1,'System.Collections.Generic.Dictionary`2<System.Type,System.Collections.Generic.Dictionary`2<System.Reflection.MethodInfo,System.Reflection.MethodInfo>>'),
 'loggerType':(1,'System.Action`1<string>'),'objectHandle':(2,'object')}
_CONTEXTS = {'calliCtor':['System.Reflection.MethodBase','IFix.Core.VirtualMachine+CalliInvokerInfo'],
 'overrideCtor':['System.Type','System.Collections.Generic.Dictionary`2<System.Reflection.MethodInfo,System.Reflection.MethodInfo>']}
_LITERALS = {'cloneName':'MemberwiseClone'}
_NEW_FIELDS = {'IFix.Core.VirtualMachine':{'onDispose':('System.Action',False),'Info':('System.Action`1<string>',True),
 '<>f__mg$cache0':('System.Action`1<string>',True)},'IFix.Core.ObjectClone':{'memberwiseClone':('System.Reflection.MethodInfo',False)},
 'IFix.Core.Cleanner':{'start':('bool',True)}}
_VM_FIELDS = {'objectClone':'IFix.Core.ObjectClone','unmanagedCodes':'IFix.Core.Instruction**','externInvokers':'IFix.Core.ExternInvoker[]',
 'calliInvokerCache':'System.Collections.Generic.Dictionary`2<System.Reflection.MethodBase,IFix.Core.VirtualMachine+CalliInvokerInfo>',
 'externMethods':'System.Reflection.MethodBase[]','overrideCache':'System.Collections.Generic.Dictionary`2<System.Type,System.Collections.Generic.Dictionary`2<System.Reflection.MethodInfo,System.Reflection.MethodInfo>>',
 'staticFieldTypes':'System.Type[]','staticFields':'object[]'}
_EFFECTS = {
 'constructor':'request-ObjectClone-and-two-typed-Dictionary-constructors;store-three-results-with-barriers;store-incoming-unmanagedCodes-and-onDispose;tail-request-Cleanner.Start',
 'externMethods':'store-input-and-barrier;fresh-stored-input-null-guard;read-Int32-length;request-ExternInvoker-array;store-result-and-tail-barrier',
 'staticFieldTypes':'null-input:null-result;otherwise-request-object-array-from-input-length;receiver-null-guard;store-staticFields-and-barrier-before-store-staticFieldTypes-and-tail-barrier',
 'defaults':'no-explicit-array-element-default-initialization-or-cache-clear-in-setters;allocation-and-Dictionary-contents-unobserved',
 'staticConstructor':'nonnull-logger-cache:reuse;null-cache:allocate-Action<string>-and-request-delegate-constructor(null,Console.WriteLine-string-MethodDef);cache-and-barrier;fresh-cache-copy-to-Info-and-tail-barrier',
 'info':'class-init;Info-nonnull-check;class-init-and-fresh-Info-reload;null-reload:nullFailure;otherwise-request-opaque-delegate-target(Info,message,hidden-zero)',
 'finalize':'onDispose-null:unwindNull;otherwise-request-opaque-delegate-target(onDispose);request-Cleanner.Stop;clear-unmanagedCodes-on-normal-return;local-context-landing-propagates-nonnull-context',
 'objectCloneCtor':'GetTypeFromHandle(object);null-Type:nullFailure;GetMethod(MemberwiseClone,Instance|NonPublic);store-returned-MethodInfo-and-tail-barrier-without-result-null-test',
 'cleanerStart':'class-init;start-byte-nonzero:return;otherwise-class-init;start=1;request-Cleanner-object;null-result:nullFailure;normal-return',
 'cleanerStop':'native-class-dword-at224-zero:classPrepare-and-class-reload;otherwise-retain-class;write-start=0;return',
 'cleanerFinalize':'fresh-start-byte-zero:return;otherwise-request-NewFieldInfo.Sweep-and-Cleanner.Start;local-context-landing-propagates-nonnull-context',
 'cleanerStaticConstructor':'write-start=0;return',
 'cleanerCtor':'finite-RET-with-zero-pop-immediate;no-explicit-field-store-or-child-request',
 'clone':'memberwiseClone-null:nullFailure;otherwise-tail-request-MethodBase.Invoke(memberwiseClone,incoming-object,object-array=null,hidden-MethodInfo=null)',
}
_CLAIMS = {'schema':'endfield.ifix-vm-vm-construction-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'methodRefs':_METHOD_REFS,'helperRefs':_HELPER_REFS,'usageRefs':_USAGE_REFS,'effects':_EFFECTS,
 'callLayoutRef':'callOpcodeRules.fieldLayouts','functionLayoutRef':'functionPointerRules.runtimeFields','negativeLayoutRef':'negativeFieldRules.vmFields',
 'cloneFieldRef':'slotCopyRules.objectCloneField','dictionaryMethodRef':'virtualDispatchRules.dictionaryContexts.innerCtor.method',
 'programBoundary':'complete-twelve-IFix-caller-bodies-including-local-landing-null-and-propagation-bytes;one-finite-RET-zero-entry-without-pdata-extent',
 'storageBoundary':'valid-stable-receivers-fields-class-static-buffers-and-input-arrays;repeated-reads-aliases-and-unmodelled-mutation-unobserved',
 'callbackBoundary':'opaque-delegate-request-arguments-only;captured-callback-identity-invocation-and-results-unobserved',
 'allocationBoundary':'typed-allocation-and-constructor-requests-only;defaults-validity-and-capacity-unobserved',
 'contextBoundary':'exact-typed-MethodSpec-and-canonical-Dictionary-MethodDef-family;runtime-sharing-and-constructor-results-unobserved',
 'exceptionBoundary':'local-Finalize-landing-and-helper-requests-only;external-landing-selection-runtime-transfer-and-unwind-unobserved',
 'runtimeBoundary':'class-state-static-storage-GC-logger-thread-timer-and-execution-unobserved',
 'bindingFlags':{'Instance':4,'NonPublic':32},'nativeClassStaticPointerOffset':184,'nativeClassStateWordOffset':224}


def _claims(spec: dict) -> None:
    _need(all(type(spec.get(k)) is type(v) and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/reference/effect/boundary')
    _need(set(spec['methods'])==set(_METHODS)-set(_METHOD_REFS),'owned method set differs')
    _need(set(spec['helpers'])==_OWN_HELPERS and set(spec['programBodies'])=={'info'},'owned helper/program set differs')
    _need(set(spec['usageCells'])==(set(_TYPE_CELLS)|set(_CONTEXTS)|set(_LITERALS)|{'loggerSource'})-set(_USAGE_REFS),'owned cell set differs')
    _need(set(spec['lazyFlags'])==set(_PROGRAMS)-{'clone','cleanerCtor'},'lazy flag set differs')
    _need(set(spec['additionalFields'])==set(_NEW_FIELDS),'additional owner set differs')


def _carrier(image: Any, pointer: int, typ: str) -> None:
    if typ=='System.Reflection.BindingFlags':
        raw=image.pe.bytes_at_va(pointer,16);_need(len(raw)==16 and raw[10]==0x11 and not raw[11]&0x20,'BindingFlags raw value carrier differs')
        _need(runtime_type_name(image.pe,image.metadata,pointer)==typ,'BindingFlags identity differs')
    elif typ=='System.RuntimeTypeHandle':_ordinary_carrier(image,pointer,typ)
    else:_compound_carrier(image,pointer,typ)


def _signature(image: Any, row: dict, identity: tuple) -> Any:
    owner,name,params,returned,static=identity;md=image.metadata
    matches=[m for t in md.types if md.type_full_name(t)==owner for m in md.methods_for(t)if md.string(m.name_index)==name
             and m.parameter_count==len(params) and [_type(image,p.type_index)for p in md.parameters_for(m)]==params]
    _need(len(matches)==1,'named overload differs: '+owner+'.'+name);m=matches[0]
    _need(row.get('type')==owner and row.get('method')==name and ('parameterTypes'not in row or row['parameterTypes']==params),'declared method name/parameters differ: '+name)
    _need(bool(m.flags&16)==static and m.generic_container_index==-1 and _type(image,m.return_type)==returned,'method return/static/generic differs: '+name)
    _method_declaration(row,identity)
    for key in ('returnType','returnTypeName'):
        if key in row:_need(row[key]==returned,'declared method return differs: '+name)
    if 'flags'in row:_need(_address(row['flags'],'method.flags')==m.flags,'declared method flags differ: '+name)
    if 'genericContainerIndex'in row:_need(type(row['genericContainerIndex'])is int and row['genericContainerIndex']==-1,'declared generic container differs: '+name)
    for idx,typ in [(p.type_index,t)for p,t in zip(md.parameters_for(m),params)]+[(m.return_type,returned)]:
        _carrier(image,image.pe.u64_at_va(_rva(image.registration['types'])+idx*8),typ)
    _need(m.token==_rva(row['token']),'method token differs: '+name)
    return m


def _fields(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    md=image.metadata;rows={};layouts=_ref(contract,spec['callLayoutRef']);fn=_ref(contract,spec['functionLayoutRef']);neg=_ref(contract,spec['negativeLayoutRef'])
    for name in ('unmanagedCodes','externInvokers','calliInvokerCache'):rows[name]=layouts['IFix.Core.VirtualMachine']['fields'][name]
    for name in ('externMethods','overrideCache'):rows[name]=fn['IFix.Core.VirtualMachine'][name]
    for name in ('staticFieldTypes','staticFields'):rows[name]=neg['fields'][name]
    rows['objectClone']=_ref(contract,spec['cloneFieldRef']);result={}
    for owner_name,extra in _NEW_FIELDS.items():
        _need(set(spec['additionalFields'][owner_name])==set(extra),'additional fields differ: '+owner_name)
        owners=[t for t in md.types if md.type_full_name(t)==owner_name];_need(len(owners)==1 and not owners[0].bitfield&1,'reference owner differs: '+owner_name)
        owner=owners[0];definitions={md.string(f.name_index):f for f in md.fields_for(owner)};offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index)
        wanted=dict(extra);selected=dict(spec['additionalFields'][owner_name])
        if owner_name=='IFix.Core.VirtualMachine':wanted.update({n:(t,False)for n,t in _VM_FIELDS.items()});selected.update(rows)
        for name,(typ,static)in wanted.items():
            f=definitions.get(name);row=selected[name];offset=row.get('offset')
            _need(f is not None and row.get('type')==typ and type(offset)is int and 0<=offset<256 and offsets.get(name)==offset and _type(image,f.type_index)==typ,'field identity/offset differs: '+name)
            if 'static'in row:_need(row['static']is static,'declared field static kind differs: '+name)
            ptr=image.pe.u64_at_va(_rva(image.registration['types'])+f.type_index*8);_carrier(image,ptr,typ);raw=image.pe.bytes_at_va(ptr,16)
            _need(bool(int.from_bytes(raw[8:10],'little')&16)==static,'raw field static kind differs: '+name)
            if 'rawTypeHex'in row:_need(raw==bytes.fromhex(row['rawTypeHex']),'declared raw field carrier differs: '+name)
            result[name]=offset
    _need(result['Info']==result['start']==0 and result['<>f__mg$cache0']==8,'zero/static-cache offsets differ')
    return result


def _cells(image: Any,spec: dict,contract: dict,targets: dict[str,int]) -> dict[str,int]:
    cells={};md=image.metadata;reg=image.registration;checked=set()
    for role in set(_TYPE_CELLS)|set(_CONTEXTS)|set(_LITERALS)|{'loggerSource'}:
        row=_ref(contract,_USAGE_REFS[role])if role in _USAGE_REFS else spec['usageCells'][role];at=_address(row['cellRva'],role)
        raw=image.pe.bytes_at_va(image.pe.image_base+at,8);decl=row.get('rawHex',row.get('hex'))
        if decl is None:decl=_rva(row['encodedWord']).to_bytes(8,'little').hex()
        _need(raw==bytes.fromhex(decl),'encoded cell bytes differ: '+role);cells[role]=at
        tag=_TYPE_CELLS[role][0]if role in _TYPE_CELLS else 6 if role in _CONTEXTS else 5 if role in _LITERALS else 3
        tags=[row[k]for k in ('usageTag','tag')if k in row]
        _need(tags and all(type(x)is int and x==tag for x in tags),'encoded cell tag differs: '+role)
        if role in _TYPE_CELLS:
            typ=_TYPE_CELLS[role][1];idx=unresolved_usage_index(raw,reg['typesCount'],tag=tag,source='vm-construction.'+role,offset=at)
            ptr=image.pe.u64_at_va(_rva(reg['types'])+idx*8);_carrier(image,ptr,typ);_cell_declaration(row,typ,idx,image.pe.bytes_at_va(ptr,16))
        elif role in _CONTEXTS:
            _need(row.get('classArgs')==_CONTEXTS[role] and row.get('methodArgs')==[],'declared typed context differs: '+role)
            base=_rva(reg['methodSpecs']);rec=usage_method_spec(raw,image.pe.bytes_at_va(base,reg['methodSpecsCount']*12),len(md.methods),reg['genericInstsCount'],source='vm-construction.context',usage_offset=at,records_offset=base)
            method=md.methods[rec['definition']];declared=_ref(contract,spec['dictionaryMethodRef'])
            _need(declared.get('type')=='System.Collections.Generic.Dictionary`2' and declared.get('method')=='.ctor'
                  and type(declared.get('parameterCount'))is int and declared['parameterCount']==0,'declared Dictionary constructor differs')
            _need(md.type_full_name(md.types[method.declaring_type])=='System.Collections.Generic.Dictionary`2'and md.string(method.name_index)=='.ctor'
                  and method.token==_rva(declared['token']) and method.parameter_count==0 and not method.flags&16 and method.generic_container_index==-1
                  and _type(image,method.return_type)=='void','Dictionary constructor definition differs')
            _carrier(image,image.pe.u64_at_va(_rva(reg['types'])+method.return_type*8),'void')
            _need(rec['classInstantiationIndex']>=0 and rec['methodInstantiationIndex']==-1,'context instantiation owners differ')
            args=image.instantiations.resolve(rec['classInstantiationIndex']).arguments
            _need(len(args)==2,'context arity differs')
            for a in args:_guard_type(image,a.type_pointer_va);_need(bytes.fromhex(a.raw_type_record_hex)==image.pe.bytes_at_va(a.type_pointer_va,16),'context carrier snapshot differs')
            _need([runtime_type_name(image.pe,md,a.type_pointer_va)for a in args]==_CONTEXTS[role],'typed context arguments differ')
            if rec['definition']not in checked:_canonical_target(image,rec['definition'],targets['dictionaryCtor']);checked.add(rec['definition'])
        elif role in _LITERALS:
            table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData'];idx=unresolved_usage_index(raw,table.size//8,tag=5,source='vm-construction.literal',offset=at)
            off=table.offset+idx*8;start,size=literal_record(md.buf[off:off+8],pool.size,source='vm-construction.literal',offset=off)
            _need(md.buf[pool.offset+start:pool.offset+start+size]==_LITERALS[role].encode(),'clone literal differs');_cell_declaration(row,_LITERALS[role])
        else:
            idx=unresolved_usage_index(raw,len(md.methods),tag=3,source='vm-construction.source',offset=at);m=md.methods[idx];source=spec['loggerSourceMethod']
            _signature(image,source,('System.Console','WriteLine',['string'],'void',True))
            _need(m.token==_rva(source['token']) and md.type_full_name(md.types[m.declaring_type])=='System.Console'
                  and md.string(m.name_index)=='WriteLine' and m.parameter_count==1 and [_type(image,p.type_index)for p in md.parameters_for(m)]==['string'],'logger MethodDef selection differs')
            _cell_declaration(row,'System.Console.WriteLine')
    for role,row in spec['lazyFlags'].items():
        _need(set(row)=={'rva','identity'}and row['identity']=='anonymous-native-byte','lazy flag declaration differs')
        at=_address(row['rva'],role);_mapped_span(image,at,1,role);cells[role+'Flag']=at
    return cells


def _program(role: str,at: int,targets: dict[str,int],cells: dict[str,int],fields: dict[str,int]) -> bytes:
    p=_Program(at);edges=[]
    for token in _PROGRAMS[role]:
        if isinstance(token,str):p.add(token);continue
        kind,*a=token
        if kind=='label':p.mark(a[0])
        elif kind=='call':p.call(targets[a[0]])
        elif kind=='tail':p.rip('e9',targets[a[0]])
        elif kind=='rip':p.rip(a[0],cells[a[1]],bytes.fromhex(a[2]))
        elif kind=='field':p.add(a[0]);p.add(fields[a[1]].to_bytes(a[2],'little'));p.add(a[3])
        elif kind=='edge':
            prefix=bytes.fromhex(a[0]);width=1 if len(prefix)==1 and prefix!=b'\xe9'else 4;p.add(prefix);edges.append((len(p.raw),width,a[1]));p.add(bytes(width))
        else:_need(False,'unknown finite grammar token')
    for off,width,label in edges:p.raw[off:off+width]=(p.labels[label]-off-width).to_bytes(width,'little',signed=True)
    return bytes(p.raw)


def validate_vm_construction_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    _claims(spec);fields=_fields(image,spec,contract);targets={};bodies={}
    values={r['name']:r['id']for r in enum_members(image.metadata,field_defaults(image.metadata),'System.Reflection.BindingFlags')}
    _need(all(type(values.get(n))is int and type(v)is int and values[n]==v for n,v in spec['bindingFlags'].items()),'named BindingFlags differ')
    for role,identity in _METHODS.items():
        row=dict(_ref(contract,_METHOD_REFS[role])if role in _METHOD_REFS else spec['methods'][role])
        if role=='clone'and 'parameterCount'not in row:row['parameterCount']=len(identity[2])
        if role in spec['programBodies']:
            patch=spec['programBodies'][role];_need(set(patch)=={'bodyBytes','bodySha256'},'complete inherited program declaration differs');row.update(patch)
        if role=='cleanerCtor':
            _need(row.get('entryBoundary')=='finite-ret-zero-entry-without-pdata-function-extent' and 'bodyBytes'not in row
                  and type(row.get('byteCount'))is int and row['byteCount']==3,'finite RET entry declaration differs')
        elif role in _PROGRAMS:_need(type(row.get('bodyBytes'))is int and 0<row['bodyBytes']<=65536,'complete body size differs: '+role)
        elif 'byteCount'in row:_need(type(row['byteCount'])is int and 0<row['byteCount']<=4096,'method window size differs: '+role)
        method=_signature(image,row,identity)
        if role=='cleanerCtor':
            ptr=image.method_pointer_va(method);targets[role]=ptr-image.pe.image_base
            _need(ptr not in extents and targets[role]==_rva(row['rva']),'finite RET entry pointer/pdata boundary differs')
            bodies[role]=image.pe.bytes_at_va(ptr,row['byteCount']);_hash(bodies[role],row,role)
        else:
            targets[role]=_identity(image,row,identity,role,extents,body_required=role in _PROGRAMS)
            if role in _PROGRAMS:bodies[role]=image.pe.bytes_at_va(image.pe.image_base+targets[role],row['bodyBytes'])
    for role in set(_HELPER_REFS)|_OWN_HELPERS:
        row=_ref(contract,_HELPER_REFS[role])if role in _HELPER_REFS else spec['helpers'][role];size=row['byteCount']
        _need(type(size)is int and 0<size<=4096,'helper window differs: '+role)
        if role in _OWN_HELPERS:_need(row.get('effectBoundary')=='opaque-delegate-request-only','request target boundary promoted')
        at=_address(row['rva'],role);_hash(image.pe.bytes_at_va(image.pe.image_base+at,size),row,role);targets[role]=at
    cells=_cells(image,spec,contract,targets)
    for role,raw in bodies.items():_expect(raw,_program(role,targets[role],targets,cells,fields),'complete '+role)
    return dict(status='validated_conditional_vm_construction_rules',evidenceBoundary='conditional',executionBoundary='unobserved',methodCount=13,
                completeMethodCount=12,finiteEntryCount=1,bodyBytes=sum(len(b)for r,b in bodies.items()if r!='cleanerCtor'),
                finiteEntryBytes=len(bodies['cleanerCtor']),effects=spec['effects'],callbackBoundary=spec['callbackBoundary'],exceptionBoundary=spec['exceptionBoundary'])


def validate_selected_vm_construction_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    g=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if g.status!='validated':return dict(status=g.status,detail=g.detail)
    image=NativeImage(g.gameassembly,g.metadata,label='ifix.vm-construction')
    return validate_vm_construction_rules(image,contract['vmConstructionRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))


_PROGRAMS = {'constructor': ('48895c240848896c24104889742418574883ec20',
                 ('rip', '803d', 'constructorFlag', '00'),
                 '498bf0488bea488bd9',
                 ('edge', '75', 'join0'),
                 ('rip', '488d0d', 'cleanerType', ''),
                 ('call', 'typeInitialize'),
                 ('rip', '488d0d', 'calliCtor', ''),
                 ('call', 'typeInitialize'),
                 ('rip', '488d0d', 'overrideCtor', ''),
                 ('call', 'typeInitialize'),
                 ('rip', '488d0d', 'overrideDictionary', ''),
                 ('call', 'typeInitialize'),
                 ('rip', '488d0d', 'calliDictionary', ''),
                 ('call', 'typeInitialize'),
                 ('rip', '488d0d', 'objectCloneType', ''),
                 ('call', 'typeInitialize'),
                 ('rip', 'c605', 'constructorFlag', '01'),
                 ('label', 'join0'),
                 ('rip', '488b0d', 'objectCloneType', ''),
                 ('call', 'allocateObject'),
                 '488bf84885c0',
                 ('edge', '0f84', 'join1'),
                 '33d2488bc8',
                 ('call', 'objectCloneCtor'),
                 ('field', '488d4b', 'objectClone', 1, ''),
                 ('field', '48897b', 'objectClone', 1, ''),
                 ('call', 'writeBarrier'),
                 ('rip', '488b0d', 'calliDictionary', ''),
                 ('call', 'allocateObject'),
                 '488bf84885c0',
                 ('edge', '0f84', 'join1'),
                 ('rip', '488b15', 'calliCtor', ''),
                 '488bc8',
                 ('call', 'dictionaryCtor'),
                 ('field', '488d4b', 'calliInvokerCache', 1, ''),
                 ('field', '48897b', 'calliInvokerCache', 1, ''),
                 ('call', 'writeBarrier'),
                 ('rip', '488b0d', 'overrideDictionary', ''),
                 ('call', 'allocateObject'),
                 '488bf84885c0',
                 ('edge', '74', 'join1'),
                 ('rip', '488b15', 'overrideCtor', ''),
                 '488bc8',
                 ('call', 'dictionaryCtor'),
                 ('field', '488d4b', 'overrideCache', 1, ''),
                 ('field', '48897b', 'overrideCache', 1, ''),
                 ('call', 'writeBarrier'),
                 ('field', '488d4b', 'onDispose', 1, ''),
                 ('field', '48896b', 'unmanagedCodes', 1, ''),
                 ('field', '488973', 'onDispose', 1, ''),
                 ('call', 'writeBarrier'),
                 ('rip', '488b0d', 'cleanerType', ''),
                 ('call', 'classInitialize'),
                 '33c9488b5c2430488b6c2438488b7424404883c4205f',
                 ('tail', 'cleanerStart'),
                 ('label', 'join1'),
                 ('call', 'nullFailure'),
                 'cc'),
 'externMethods': ('48895c2408574883ec20',
                   ('rip', '803d', 'externMethodsFlag', '00'),
                   '488bfa488bd9',
                   ('edge', '75', 'join0'),
                   ('rip', '488d0d', 'externInvokerArray', ''),
                   ('call', 'typeInitialize'),
                   ('rip', 'c605', 'externMethodsFlag', '01'),
                   ('label', 'join0'),
                   ('field', '488d4b', 'externMethods', 1, ''),
                   ('field', '48897b', 'externMethods', 1, ''),
                   ('call', 'writeBarrier'),
                   ('field', '4c8b4b', 'externMethods', 1, ''),
                   '4d85c9',
                   ('edge', '75', 'join1'),
                   ('call', 'nullFailure'),
                   'cc',
                   ('label', 'join1'),
                   '418b5118',
                   ('rip', '488b0d', 'externInvokerArray', ''),
                   ('call', 'arrayAllocate'),
                   ('field', '488d4b', 'externInvokers', 1, ''),
                   ('field', '488943', 'externInvokers', 1, ''),
                   '488b5c24304883c4205f',
                   ('tail', 'writeBarrier')),
 'staticFieldTypes': ('48895c2408574883ec20',
                      ('rip', '803d', 'staticFieldTypesFlag', '00'),
                      '488bfa488bd9',
                      ('edge', '75', 'join0'),
                      ('rip', '488d0d', 'objectArray', ''),
                      ('call', 'typeInitialize'),
                      ('rip', 'c605', 'staticFieldTypesFlag', '01'),
                      ('label', 'join0'),
                      '4885ff',
                      ('edge', '75', 'join1'),
                      '33c0',
                      ('edge', 'eb', 'join2'),
                      ('label', 'join1'),
                      '8b5718',
                      ('rip', '488b0d', 'objectArray', ''),
                      ('call', 'arrayAllocate'),
                      ('label', 'join2'),
                      '4885db',
                      ('edge', '75', 'join3'),
                      ('call', 'nullFailure'),
                      'cc',
                      ('label', 'join3'),
                      ('field', '488d8b', 'staticFields', 4, ''),
                      ('field', '488983', 'staticFields', 4, ''),
                      ('call', 'writeBarrier'),
                      ('field', '488d4b', 'staticFieldTypes', 1, ''),
                      ('field', '48897b', 'staticFieldTypes', 1, ''),
                      '488b5c24304883c4205f',
                      ('tail', 'writeBarrier')),
 'finalize': ('48894c24084883ec48',
              ('rip', '803d', 'finalizeFlag', '00'),
              ('edge', '75', 'join0'),
              ('rip', '488d0d', 'cleanerType', ''),
              ('call', 'typeInitialize'),
              ('rip', 'c605', 'finalizeFlag', '01'),
              ('label', 'join0'),
              '488364242800488d4424504889442430488b442450',
              ('field', '488b48', 'onDispose', 1, ''),
              '4885c9',
              ('edge', '74', 'join2'),
              ('call', 'actionInvoke'),
              ('rip', '488b0d', 'cleanerType', ''),
              ('call', 'classInitialize'),
              '33c9',
              ('call', 'cleanerStop'),
              '488b442450',
              ('field', '48c740', 'unmanagedCodes', 1, '00000000'),
              ('edge', 'eb', 'join1'),
              '488b4c24284885c9',
              ('edge', '75', 'join3'),
              ('label', 'join1'),
              '4883c448c3',
              ('label', 'join2'),
              ('call', 'unwindNull'),
              '90',
              ('label', 'join3'),
              ('call', 'exceptionPropagate'),
              'cc'),
 'info': ('40534883ec20',
          ('rip', '803d', 'infoFlag', '00'),
          '488bd9',
          ('edge', '75', 'join0'),
          ('rip', '488d0d', 'vmType', ''),
          ('call', 'typeInitialize'),
          ('rip', 'c605', 'infoFlag', '01'),
          ('label', 'join0'),
          ('rip', '488b0d', 'vmType', ''),
          ('call', 'classInitialize'),
          ('rip', '488b0d', 'vmType', ''),
          '488b81b800000048833800',
          ('edge', '74', 'join2'),
          ('call', 'classInitialize'),
          ('rip', '488b05', 'vmType', ''),
          '488b88b8000000488b094885c9',
          ('edge', '75', 'join1'),
          ('call', 'nullFailure'),
          'cc',
          ('label', 'join1'),
          '4533c0488bd3',
          ('call', 'loggerInvoke'),
          ('label', 'join2'),
          '4883c4205bc3'),
 'staticConstructor': ('4883ec28',
                       ('rip', '803d', 'staticConstructorFlag', '00'),
                       ('edge', '75', 'join0'),
                       ('rip', '488d0d', 'loggerType', ''),
                       ('call', 'typeInitialize'),
                       ('rip', '488d0d', 'loggerSource', ''),
                       ('call', 'typeInitialize'),
                       ('rip', '488d0d', 'vmType', ''),
                       ('call', 'typeInitialize'),
                       ('rip', 'c605', 'staticConstructorFlag', '01'),
                       ('label', 'join0'),
                       ('rip', '488b0d', 'vmType', ''),
                       '48895c2420488b81b80000004883780800',
                       ('edge', '75', 'join1'),
                       ('rip', '488b0d', 'loggerType', ''),
                       ('call', 'allocateObject'),
                       '488bd84885c0',
                       ('edge', '74', 'join2'),
                       ('rip', '4c8b05', 'loggerSource', ''),
                       '4533c933d2488bc8',
                       ('call', 'loggerCtor'),
                       ('rip', '488b05', 'vmType', ''),
                       '488b88b800000048895908',
                       ('rip', '488b05', 'vmType', ''),
                       '488b88b80000004883c108',
                       ('call', 'writeBarrier'),
                       ('rip', '488b0d', 'vmType', ''),
                       ('label', 'join1'),
                       '488b81b8000000488bc8488b4008488901',
                       ('rip', '488b0d', 'vmType', ''),
                       '488b89b8000000488b5c24204883c428',
                       ('tail', 'writeBarrier'),
                       ('label', 'join2'),
                       ('call', 'nullFailure'),
                       'cc'),
 'objectCloneCtor': ('48895c2408574883ec20',
                     ('rip', '803d', 'objectCloneCtorFlag', '00'),
                     '488bf9',
                     ('edge', '75', 'join0'),
                     ('rip', '488d0d', 'objectHandle', ''),
                     ('call', 'typeInitialize'),
                     ('rip', '488d0d', 'systemType', ''),
                     ('call', 'typeInitialize'),
                     ('rip', '488d0d', 'cloneName', ''),
                     ('call', 'typeInitialize'),
                     ('rip', 'c605', 'objectCloneCtorFlag', '01'),
                     ('label', 'join0'),
                     ('rip', '488b0d', 'systemType', ''),
                     ('rip', '488b1d', 'objectHandle', ''),
                     ('call', 'classInitialize'),
                     '33d2488bcb',
                     ('call', 'typeFromHandle'),
                     '4885c0',
                     ('edge', '75', 'join1'),
                     ('call', 'nullFailure'),
                     'cc',
                     ('label', 'join1'),
                     ('rip', '488b15', 'cloneName', ''),
                     '4533c9488bc8458d4124',
                     ('call', 'getMethod'),
                     ('field', '488d4f', 'memberwiseClone', 1, ''),
                     ('field', '488947', 'memberwiseClone', 1, ''),
                     '488b5c24304883c4205f',
                     ('tail', 'writeBarrier')),
 'clone': ('4883ec28',
           ('field', '488b49', 'memberwiseClone', 1, ''),
           '4885c9',
           ('edge', '75', 'join0'),
           ('call', 'nullFailure'),
           'cc',
           ('label', 'join0'),
           '4533c94533c04883c428',
           ('tail', 'cloneInvoke')),
 'cleanerCtor': ('c20000',),
 'cleanerStart': ('4883ec28',
                  ('rip', '803d', 'cleanerStartFlag', '00'),
                  ('edge', '75', 'join0'),
                  ('rip', '488d0d', 'cleanerType', ''),
                  ('call', 'typeInitialize'),
                  ('rip', 'c605', 'cleanerStartFlag', '01'),
                  ('label', 'join0'),
                  ('rip', '488b0d', 'cleanerType', ''),
                  ('call', 'classInitialize'),
                  ('rip', '488b0d', 'cleanerType', ''),
                  '488b81b8000000803800',
                  ('edge', '75', 'join1'),
                  ('call', 'classInitialize'),
                  ('rip', '488b05', 'cleanerType', ''),
                  '488b88b8000000c60101',
                  ('rip', '488b0d', 'cleanerType', ''),
                  ('call', 'allocateObject'),
                  '4885c0',
                  ('edge', '75', 'join1'),
                  ('call', 'nullFailure'),
                  'cc',
                  ('label', 'join1'),
                  '4883c428c3'),
 'cleanerStop': ('4883ec28',
                 ('rip', '803d', 'cleanerStopFlag', '00'),
                 ('edge', '75', 'join0'),
                 ('rip', '488d0d', 'cleanerType', ''),
                 ('call', 'typeInitialize'),
                 ('rip', 'c605', 'cleanerStopFlag', '01'),
                 ('label', 'join0'),
                 ('rip', '488b05', 'cleanerType', ''),
                 '83b8e000000000',
                 ('edge', '75', 'join1'),
                 '488bc8',
                 ('call', 'classPrepare'),
                 ('rip', '488b05', 'cleanerType', ''),
                 ('label', 'join1'),
                 '488b88b8000000c601004883c428c3'),
 'cleanerFinalize': ('48894c24084883ec48',
                     ('rip', '803d', 'cleanerFinalizeFlag', '00'),
                     ('edge', '75', 'join0'),
                     ('rip', '488d0d', 'cleanerType', ''),
                     ('call', 'typeInitialize'),
                     ('rip', '488d0d', 'newFieldType', ''),
                     ('call', 'typeInitialize'),
                     ('rip', 'c605', 'cleanerFinalizeFlag', '01'),
                     ('label', 'join0'),
                     '488364242800488d4424504889442430',
                     ('rip', '488b0d', 'cleanerType', ''),
                     ('call', 'classInitialize'),
                     ('rip', '488b05', 'cleanerType', ''),
                     '488b88b8000000803900',
                     ('edge', '74', 'join1'),
                     ('rip', '488b0d', 'newFieldType', ''),
                     ('call', 'classInitialize'),
                     '33c9',
                     ('call', 'sweep'),
                     ('rip', '488b0d', 'cleanerType', ''),
                     ('call', 'classInitialize'),
                     '33c9',
                     ('call', 'cleanerStart'),
                     '90',
                     ('label', 'join1'),
                     ('edge', 'eb', 'join2'),
                     '488b4c24284885c9',
                     ('edge', '75', 'join3'),
                     ('label', 'join2'),
                     '4883c448c3',
                     ('label', 'join3'),
                     ('call', 'exceptionPropagate'),
                     'cc'),
 'cleanerStaticConstructor': ('4883ec28',
                              ('rip', '803d', 'cleanerStaticConstructorFlag', '00'),
                              ('edge', '75', 'join0'),
                              ('rip', '488d0d', 'cleanerType', ''),
                              ('call', 'typeInitialize'),
                              ('rip', 'c605', 'cleanerStaticConstructorFlag', '01'),
                              ('label', 'join0'),
                              ('rip', '488b05', 'cleanerType', ''),
                              '488b88b8000000c601004883c428c3')}
