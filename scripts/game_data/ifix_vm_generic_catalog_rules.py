"""Authenticate the generic delegate factory's lazy catalog recipe.

On a cache miss, a null genericAction field enters initialization. The selected
native calls GetMethods on the GenericDelegate type with Instance|Public|
DeclaredOnly (22), supplies Action/Func name callbacks to the predicate-taking
Where overload, supplies GetParameters().Length callbacks to the two-argument
OrderBy overload, and supplies the resulting sequences to ToArray<MethodInfo>.
The returned references are stored in the named genericAction/genericFunc fields.

The selected metadata separately declares one public instance Action and Func
for each parameter count 0..4, with reciprocal method-generic ordinals. This is
a declaration catalog, not a receipt of reflection results or populated arrays.
Callback materialization, enumeration, comparer results, concurrent static
state, generic sharing and invocation remain unobserved. The parent validates
selected native inputs, the complete Create body and prerequisite selection
rules; this component authenticates its reviewed windows and named call sites.
"""
from __future__ import annotations

import hashlib
import re
import struct
from typing import Any

from scripts.game_data.il2cpp.context import (
    generic_method_candidates, literal_record, method_parameter_owner,
    rip_qword_load_target, unresolved_usage_index, usage_method_spec,
)
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name


class GenericCatalogEvidenceError(ValueError):
    """The catalog recipe or declaration identity lacks its native witness."""


_METHODS = {
    'actionName': ('IFix.Core.GenericDelegateFactory', '<Create>m__0', ('System.Reflection.MethodInfo',), 'bool'),
    'actionCount': ('IFix.Core.GenericDelegateFactory', '<Create>m__1', ('System.Reflection.MethodInfo',), 'int'),
    'funcName': ('IFix.Core.GenericDelegateFactory', '<Create>m__2', ('System.Reflection.MethodInfo',), 'bool'),
    'funcCount': ('IFix.Core.GenericDelegateFactory', '<Create>m__3', ('System.Reflection.MethodInfo',), 'int'),
    'stringEquality': ('System.String', 'Equals', ('string', 'string'), 'bool'),
}
_VIRTUALS = {
    'getMethods': ('System.Type', 'GetMethods', ('System.Reflection.BindingFlags',), 'System.Reflection.MethodInfo[]', 132),
    'getName': ('System.Reflection.MemberInfo', 'get_Name', (), 'string', 8),
}
_FIELDS = {
    'genericAction': 'System.Reflection.MethodInfo[]', 'genericFunc': 'System.Reflection.MethodInfo[]',
    '<>f__am$cache0': 'System.Func`2<System.Reflection.MethodInfo,bool>',
    '<>f__am$cache1': 'System.Func`2<System.Reflection.MethodInfo,int>',
    '<>f__am$cache2': 'System.Func`2<System.Reflection.MethodInfo,bool>',
    '<>f__am$cache3': 'System.Func`2<System.Reflection.MethodInfo,int>',
}
_CONTEXTS = {'whereContext': ('Where', ('System.Reflection.MethodInfo',)),
             'orderContext': ('OrderBy', ('System.Reflection.MethodInfo', 'int')),
             'arrayContext': ('ToArray', ('System.Reflection.MethodInfo',))}
_WITNESSES = {
    'nullCatalog': '4c3920', 'getMethodsArgs': '41b816000000488bd0',
    'actionWhereArgs': '488b5118488bcf', 'funcWhereArgs': '488b5128488bcf',
    'actionOrderArgs': '488b5120488bce', 'funcOrderArgs': '488b5130488bcf',
    'actionStore': '488902', 'funcStore': '48894208',
    'actionNameArgs': 'b908000000488bd3', 'funcNameArgs': 'b908000000488bd3',
    'countArgs': 'b912000000', 'countReturn': '8b40184883c428c3',
}
_EDGES = {
    'getTypeCall': ('call', 'getTypeFromHandle'),
    'getMethodsCall': ('call', 'getMethodsHelper'),
    'actionWhere': ('call', 'whereHelper'), 'funcWhere': ('call', 'whereHelper'),
    'actionOrder': ('call', 'orderByHelper'), 'funcOrder': ('call', 'orderByHelper'),
    'actionArray': ('call', 'toArrayHelper'), 'funcArray': ('call', 'toArrayHelper'),
    'actionNameCall': ('call', 'nameQueryHelper'), 'funcNameCall': ('call', 'nameQueryHelper'),
    'actionEquality': ('jump', 'stringEquality'), 'funcEquality': ('jump', 'stringEquality'),
    'actionCountCall': ('call', 'parameterQueryHelper'), 'funcCountCall': ('call', 'parameterQueryHelper'),
}


def _rva(value: Any) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _named(rows: list[dict], expected: Any, label: str) -> dict[str, dict]:
    mapped = {row.get('name'): row for row in rows}
    if len(mapped) != len(rows) or set(mapped) != set(expected):
        raise GenericCatalogEvidenceError(f'generic-catalog.{label}: missing/duplicate/unknown entries')
    return mapped


def _slice(raw: bytes, base: int, site: int, size: int, label: str) -> bytes:
    offset = site-base
    if size <= 0 or not 0 <= offset <= len(raw)-size:
        raise GenericCatalogEvidenceError(f'generic-catalog.{label}: outside reviewed bytes')
    return raw[offset:offset+size]


def _window(image: Any, row: dict, *, method: bool = False) -> bytes:
    size = row['bodyBytes'] if method else row['byteCount']
    raw = image.pe.bytes_at_va(image.pe.image_base+_rva(row['rva']), size)
    expected = row['bodySha256'] if method else row['sha256']
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != expected.upper() or raw.hex().upper() != row['hex'].upper():
        raise GenericCatalogEvidenceError(f'generic-catalog.{row.get("name", "catalogWindow")}: expectedSha256={expected} actualSha256={actual}')
    return raw


def _type_name(image: Any, index: int) -> str:
    return runtime_type_name(image.pe, image.metadata,
                             image.pe.u64_at_va(_rva(image.registration['types'])+index*8))


def _byref(image: Any, index: int) -> bool:
    pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8)
    return bool(image.pe.bytes_at_va(pointer,16)[11]&0x20)


def _argument_names(image: Any, index: int) -> list[str]:
    args=image.instantiations.resolve(index).arguments
    for arg in args:
        raw=bytes.fromhex(arg.raw_type_record_hex)
        if len(raw)!=16 or raw[11]&0x20:
            raise GenericCatalogEvidenceError('generic-catalog.MethodSpec: by-reference argument carrier differs')
    return [runtime_type_name(image.pe,image.metadata,a.type_pointer_va) for a in args]


def _identity(image: Any, row: dict, expected: tuple, *, virtual: bool = False) -> Any:
    owner, name, params, result = expected[:4]
    if (row.get('type'), row.get('method'), tuple(row.get('parameterTypes', ())), row.get('returnType')) != (owner, name, params, result):
        raise GenericCatalogEvidenceError(f'generic-catalog.{row.get("name")}: unsupported method claim')
    md = image.metadata
    methods = [m for t in md.types if md.type_full_name(t)==owner for m in md.methods_for(t)
               if md.string(m.name_index)==name and tuple(_type_name(image,p.type_index) for p in md.parameters_for(m))==params]
    if len(methods)!=1:
        raise GenericCatalogEvidenceError(f'generic-catalog.{row["name"]}: expected one exact overload, actual={len(methods)}')
    m=methods[0]
    if (m.token!=_rva(row['token']) or m.parameter_count!=len(params) or row.get('parameterCount')!=len(params)
        or _type_name(image,m.return_type)!=result or _byref(image,m.return_type)
        or any(_byref(image,p.type_index) for p in md.parameters_for(m))):
        raise GenericCatalogEvidenceError(f'generic-catalog.{row["name"]}: metadata token/signature differs')
    if bool(m.flags&0x10)==virtual:
        raise GenericCatalogEvidenceError(f'generic-catalog.{row["name"]}: static/instance kind differs')
    if virtual:
        if m.slot!=expected[4] or row.get('slot')!=expected[4]:
            raise GenericCatalogEvidenceError(f'generic-catalog.{row["name"]}: metadata virtual slot differs')
    elif image.method_pointer_va(m)-image.pe.image_base!=_rva(row['rva']):
        raise GenericCatalogEvidenceError(f'generic-catalog.{row["name"]}: registered method pointer differs')
    return m


def _fields(image: Any, rows: dict) -> None:
    if set(rows)!=set(_FIELDS):
        raise GenericCatalogEvidenceError('generic-catalog.fields: unsupported field set')
    md=image.metadata
    owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.GenericDelegateFactory']
    if len(owners)!=1:
        raise GenericCatalogEvidenceError('generic-catalog.fields: ambiguous owner')
    owner=owners[0]
    offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index)
    fields={md.string(f.name_index):f for f in md.fields_for(owner)}
    for name, expected in _FIELDS.items():
        if name not in fields or rows[name].get('offset')!=offsets[name] or rows[name].get('type')!=expected or _type_name(image,fields[name].type_index)!=expected:
            raise GenericCatalogEvidenceError(f'generic-catalog.{name}: named field layout differs')


def _ordinal(image: Any, text: str, method: Any, ordinal: int) -> int:
    match=re.fullmatch(r'MVAR\[(\d+)\]',text)
    if not match:
        raise GenericCatalogEvidenceError('generic-catalog.signature: expected method generic parameter')
    owner=method_parameter_owner(image.metadata.buf,int(match[1]),
                                 [m.generic_container_index for m in image.metadata.methods],source='generic-catalog.signature')
    if (owner['methodIndex'],owner['ordinal'])!=(method.index,ordinal):
        raise GenericCatalogEvidenceError('generic-catalog.signature: reciprocal MVAR owner/ordinal differs')
    return struct.unpack_from('<i',bytes.fromhex(owner['containerRawHex']),4)[0]


def _context_signature(image: Any, method: Any, role: str) -> None:
    if not method.flags&0x10:
        raise GenericCatalogEvidenceError(f'generic-catalog.{role}: LINQ MethodDef must be static')
    if _byref(image,method.return_type) or any(_byref(image,p.type_index) for p in image.metadata.parameters_for(method)):
        raise GenericCatalogEvidenceError(f'generic-catalog.{role}: by-reference LINQ signature differs')
    params=[_type_name(image,p.type_index) for p in image.metadata.parameters_for(method)]
    result=_type_name(image,method.return_type)
    first=re.fullmatch(r'System.Collections.Generic.IEnumerable`1<(MVAR\[\d+\])>',params[0]) if params else None
    if not first:
        raise GenericCatalogEvidenceError(f'generic-catalog.{role}: enumerable generic signature differs')
    arg=first[1];arity=_ordinal(image,arg,method,0)
    if arity!=(2 if role=='orderContext' else 1):
        raise GenericCatalogEvidenceError(f'generic-catalog.{role}: method generic arity differs')
    if role=='whereContext':
        expected=[params[0],f'System.Func`2<{arg},bool>'];expected_result=params[0]
    elif role=='orderContext':
        second=re.fullmatch(r'System.Func`2<MVAR\[\d+\],(MVAR\[\d+\])>',params[1]) if len(params)==2 else None
        if not second:
            raise GenericCatalogEvidenceError('generic-catalog.orderContext: key-selector signature differs')
        _ordinal(image,second[1],method,1)
        expected=[params[0],f'System.Func`2<{arg},{second[1]}>'];expected_result=f'System.Linq.IOrderedEnumerable`1<{arg}>'
    else:
        expected=[params[0]];expected_result=arg+'[]'
    if params!=expected or result!=expected_result or method.parameter_count!=len(expected):
        raise GenericCatalogEvidenceError(f'generic-catalog.{role}: exact LINQ overload signature differs')


def _usage(image: Any, row: dict, raw: bytes, base: int) -> int | None:
    name=row['name'];site=_rva(row['loadRva']);cell=_rva(row['cellRva'])
    if rip_qword_load_target(_slice(raw,base,site,7,name),site,source='generic-catalog.'+name)!=cell:
        raise GenericCatalogEvidenceError(f'generic-catalog.{name}: usage load target differs')
    usage=image.pe.bytes_at_va(image.pe.image_base+cell,8)
    if usage.hex().upper()!=row['rawHex'].upper():
        raise GenericCatalogEvidenceError(f'generic-catalog.{name}: usage cell differs')
    md,pe,reg=image.metadata,image.pe,image.registration
    if name in _CONTEXTS:
        at=_rva(reg['methodSpecs'])
        record=usage_method_spec(usage,pe.bytes_at_va(at,reg['methodSpecsCount']*12),len(md.methods),reg['genericInstsCount'],
                                 source='generic-catalog.'+name,usage_offset=pe.image_base+cell,records_offset=at)
        m=md.methods[record['definition']]
        args=_argument_names(image,record['methodInstantiationIndex'])
        owner,mn=md.type_full_name(md.types[m.declaring_type]),md.string(m.name_index)
        if (owner,mn,tuple(args),record['classInstantiationIndex'])!=('System.Linq.Enumerable',*_CONTEXTS[name],-1):
            raise GenericCatalogEvidenceError(f'generic-catalog.{name}: typed MethodSpec identity differs')
        _context_signature(image,m,name)
        return m.index
    if name=='genericDelegateType':
        idx=unresolved_usage_index(usage,reg['typesCount'],tag=2,source='generic-catalog.type',offset=cell)
        if _byref(image,idx) or _type_name(image,idx)!='IFix.Core.GenericDelegate':
            raise GenericCatalogEvidenceError('generic-catalog.type: type handle differs')
    elif name.endswith('Literal'):
        table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData']
        idx=unresolved_usage_index(usage,table.size//8,tag=5,source='generic-catalog.literal',offset=cell)
        at=table.offset+idx*8;start,size=literal_record(md.buf[at:at+8],pool.size,source='generic-catalog.literal',offset=at)
        expected=b'Action' if name=='actionLiteral' else b'Func'
        if md.buf[pool.offset+start:pool.offset+start+size]!=expected:
            raise GenericCatalogEvidenceError(f'generic-catalog.{name}: string literal differs')
    else:
        names={'actionCallback':'<Create>m__0','actionCountCallback':'<Create>m__1','funcCallback':'<Create>m__2','funcCountCallback':'<Create>m__3'}
        idx=unresolved_usage_index(usage,len(md.methods),tag=3,source='generic-catalog.callback',offset=cell);m=md.methods[idx]
        if (md.type_full_name(md.types[m.declaring_type]),md.string(m.name_index))!=('IFix.Core.GenericDelegateFactory',names[name]):
            raise GenericCatalogEvidenceError(f'generic-catalog.{name}: callback identity differs')
    return None


def _family_targets(image: Any, definitions: dict, helpers: dict) -> None:
    """Join direct bodies to registered MethodDef families, retaining sharing gap."""
    pe,reg=image.pe,image.registration
    specs=pe.bytes_at_va(_rva(reg['methodSpecs']),reg['methodSpecsCount']*12)
    selected={i:d for i,(d,_c,_m) in enumerate(struct.iter_unpack('<iii',specs)) if d in definitions.values()}
    code=image.mapper.code_registration_summary(pe,image.code_registration);at=_rva(reg['genericMethodTable'])
    candidates=generic_method_candidates(pe.bytes_at_va(at,reg['genericMethodTableCount']*16),reg['genericMethodTableCount'],
        reg['methodSpecsCount'],set(selected),code['genericMethodPointersCount'],code['invokerPointersCount'],source='generic-catalog.families',offset=at)
    targets={}
    for row in candidates:
        pointer=pe.u64_at_va(_rva(code['genericMethodPointers'])+row['indices'][0]*8)-pe.image_base
        targets.setdefault(selected[row['methodSpecIndex']],set()).add(pointer)
    for role,helper in (('whereContext','whereHelper'),('orderContext','orderByHelper'),('arrayContext','toArrayHelper')):
        if _rva(helpers[helper]['rva']) not in targets.get(definitions[role],set()):
            raise GenericCatalogEvidenceError(f'generic-catalog.{role}: direct target lacks registered MethodDef-family candidate')


def _catalog(image: Any, rows: list[dict]) -> list[dict]:
    md=image.metadata;owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.GenericDelegate']
    if len(owners)!=1:
        raise GenericCatalogEvidenceError('generic-catalog.declarations: ambiguous owner')
    actual=[];summary=[]
    for m in md.methods_for(owners[0]):
        name=md.string(m.name_index)
        if name not in ('Action','Func') or m.flags&7!=6 or m.flags&0x10:
            continue
        params=[_type_name(image,p.type_index) for p in md.parameters_for(m)];result=_type_name(image,m.return_type)
        if _byref(image,m.return_type) or any(_byref(image,p.type_index) for p in md.parameters_for(m)):
            raise GenericCatalogEvidenceError('generic-catalog.declarations: by-reference declaration differs')
        actual.append({'type':'IFix.Core.GenericDelegate','method':name,'token':hex(m.token),'parameterTypes':params,
                       'returnType':result,'flags':hex(m.flags),'genericContainerIndex':m.generic_container_index})
        count=len(params)+(name=='Func')
        for ordinal,param in enumerate(params):
            if _ordinal(image,param,m,ordinal)!=count:
                raise GenericCatalogEvidenceError('generic-catalog.declarations: method generic arity differs')
        if name=='Func':
            if _ordinal(image,result,m,len(params))!=count:
                raise GenericCatalogEvidenceError('generic-catalog.declarations: method generic arity differs')
        elif result!='void':raise GenericCatalogEvidenceError('generic-catalog.declarations: Action return differs')
        elif not params and m.generic_container_index!=-1:
            raise GenericCatalogEvidenceError('generic-catalog.declarations: zero Action must be nongeneric')
        summary.append({'method':name,'parameterCount':len(params),'genericArgumentCount':count,
                        'evidenceBoundary':'direct','runtimeArrayMembership':'unobserved'})
    if actual!=rows or sorted((r['method'],r['parameterCount']) for r in summary)!=[(name,n) for name in ('Action','Func') for n in range(5)]:
        raise GenericCatalogEvidenceError('generic-catalog.declarations: exact public instance catalog differs')
    return summary


def validate_generic_catalog_rules(image: Any, spec: dict, contract: dict, extents: dict[int,int]) -> dict:
    """Validate recipe and declarations within the parent's selected native gate."""
    if (spec.get('schema')!='endfield.ifix-vm-generic-catalog-rules.v1' or spec.get('evidenceBoundary')!='conditional'
        or spec.get('executionBoundary')!='unobserved' or spec.get('factoryMethodRef')!='delegateConstruction.methodCalls.genericFallback'
        or spec.get('construction')!='GenericDelegate-GetMethods-22-Where-name-OrderBy-parameter-count-ToArray'
        or spec.get('runtimeCatalogBoundary')!='reflection-results-and-enumeration-unobserved'):
        raise GenericCatalogEvidenceError('generic-catalog: unsupported schema/recipe/boundary')
    factory=next(r for r in contract['delegateConstruction']['methodCalls'] if r['role']=='genericFallback')
    base=_rva(factory['rva']);body=image.pe.bytes_at_va(image.pe.image_base+base,factory['bodyBytes'])
    window=spec['catalogWindow'];raw=_window(image,window);start=_rva(window['rva'])
    if _slice(body,base,start,len(raw),'catalogWindow')!=raw:
        raise GenericCatalogEvidenceError('generic-catalog.window: outside Create')
    methods=_named(spec['methods'],_METHODS,'methods');virtuals=_named(spec['virtualMethods'],_VIRTUALS,'virtuals')
    sources=[(base,body)]
    for name,row in methods.items():
        _identity(image,row,_METHODS[name])
        if name!='stringEquality':
            code=_window(image,row,method=True);ptr=image.pe.image_base+_rva(row['rva'])
            if extents.get(ptr)!=ptr+len(code):raise GenericCatalogEvidenceError(f'generic-catalog.{name}: exact callback extent differs')
            sources.append((_rva(row['rva']),code))
    for name,row in virtuals.items():_identity(image,row,_VIRTUALS[name],virtual=True)
    _fields(image,spec['fieldLayouts'])
    helpers=_named(spec['helperWindows'],('getMethodsHelper','nameQueryHelper','whereHelper','orderByHelper','toArrayHelper'),'helpers')
    helper_raw={name:_window(image,row) for name,row in helpers.items()}
    # Class vtable pairs are 16 bytes, following the 20-pair class prefix.
    if helper_raw['getMethodsHelper'][24:41]!=b'\x48\x8b\x03\x4c\x8b\x88'+struct.pack('<i',(132+20)*16)+b'\x4c\x8b\x80'+struct.pack('<i',(132+20)*16+8):
        raise GenericCatalogEvidenceError('generic-catalog.getMethods: class virtual pair differs')
    name_raw=helper_raw['nameQueryHelper']
    if name_raw[24:35]!=b'\x48\x8d\x4b\x14\x48\xc1\xe1\x04\x48\x03\x0f':
        raise GenericCatalogEvidenceError('generic-catalog.getName: slot*16/class-vtable program differs')
    sources.extend((_rva(row['rva']),helper_raw[name]) for name,row in helpers.items())
    def read(site,size,label):
        for at,code in sources:
            if at<=site<=at+len(code)-size:return _slice(code,at,site,size,label)
        raise GenericCatalogEvidenceError(f'generic-catalog.{label}: outside reviewed bytes')
    witnesses=_named(spec['witnesses'],_WITNESSES,'witnesses')
    for name,row in witnesses.items():
        expected=bytes.fromhex(_WITNESSES[name]);actual=read(_rva(row['rva']),len(expected),name)
        if actual!=expected or row.get('hex')!=expected.hex():raise GenericCatalogEvidenceError(f'generic-catalog.{name}: semantic witness differs')
    # Named fields tie callback input and publication instructions to static layout.
    for name,field in (('actionWhereArgs','<>f__am$cache0'),('funcWhereArgs','<>f__am$cache2'),('actionOrderArgs','<>f__am$cache1'),('funcOrderArgs','<>f__am$cache3')):
        if bytes.fromhex(_WITNESSES[name])[3]!=spec['fieldLayouts'][field]['offset']:
            raise GenericCatalogEvidenceError(f'generic-catalog.{name}: static callback field differs')
    if spec['fieldLayouts']['genericAction']['offset']!=0 or spec['fieldLayouts']['genericFunc']['offset']!=8:
        raise GenericCatalogEvidenceError('generic-catalog.publication: static array fields differ')
    # The guard branches over the complete initialization block when non-null.
    guard=_rva(witnesses['nullCatalog']['rva'])+3;branch=read(guard,6,'catalogGuard')
    if branch[:2]!=b'\x0f\x85' or guard+6+int.from_bytes(branch[2:],'little',signed=True)!=start+len(raw):
        raise GenericCatalogEvidenceError('generic-catalog.guard: expected non-null skip target differs')
    cells=_named(spec['usageCells'],('genericDelegateType','actionCallback','actionCountCallback','funcCallback','funcCountCallback',
                                      'whereContext','orderContext','arrayContext','actionLiteral','funcLiteral'),'usageCells')
    definitions={}
    for name,row in cells.items():
        site=_rva(row['loadRva']);code=read(site,7,name)
        result=_usage(image,row,code,site)
        if result is not None:definitions[name]=result
    _family_targets(image,definitions,helpers)
    targets={name:_rva(row['rva']) for name,row in {**methods,**helpers}.items()}
    targets['parameterQueryHelper']=_rva(next(r for r in contract['genericDelegateFactoryRules']['helpers'] if r['name']=='parameterQueryHelper')['rva'])
    targets['getTypeFromHandle']=_rva(next(r for r in contract['genericDelegateFactoryRules']['methods'] if r['name']=='getTypeFromHandle')['rva'])
    edges=_named(spec['controlEdges'],_EDGES,'edges')
    for name,row in edges.items():
        kind,target=_EDGES[name]
        if (row.get('kind'),row.get('target'))!=(kind,target):raise GenericCatalogEvidenceError(f'generic-catalog.{name}: unsupported control claim')
        site=_rva(row['rva']);code=read(site,5,name)
        if code[0]!=(0xe8 if kind=='call' else 0xe9) or site+5+int.from_bytes(code[1:],'little',signed=True)!=targets[target]:
            raise GenericCatalogEvidenceError(f'generic-catalog.{name}: expected named call target differs')
    members={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'System.Reflection.BindingFlags')}
    if {name:members.get(name) for name in ('DeclaredOnly','Instance','Public')}!={'DeclaredOnly':2,'Instance':4,'Public':16}:
        raise GenericCatalogEvidenceError('generic-catalog.flags: BindingFlags values differ')
    catalog=_catalog(image,spec['declaredCatalog'])
    return {'status':'validated_conditional_generic_catalog_recipe','reflectionFlags':['Instance','Public','DeclaredOnly'],
            'filters':['Action','Func'],'orderingKey':'GetParameters().Length','publication':['genericAction','genericFunc'],
            'declaredCatalog':catalog,'evidenceBoundary':'conditional','executionBoundary':'unobserved',
            'unresolved':['runtime-reflection-results-and-array-membership','callback-materialization-and-enumeration',
                          'runtime-comparer-and-concurrent-static-state','exact-generic-sharing-and-invocation']}
