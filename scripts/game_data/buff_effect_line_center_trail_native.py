"""Current-build conditional EffectLineCenter forwarding into trail components.

The entry prefix joins the current EffectInstance.m_data reference to its
12-byte centerOffset copy and the subsequent Start call. Static MethodSpec
cells select VFXTrailPointsTool consistently for query and enumeration; these
cells do not prove initialized generic runtime objects or an observed call.
Complete Start and _IsCenterOffset grammars establish their ordinary guards.
Point deformation, renderer submission, parent ExecuteInternal/configuration
lifetime joins, and actual execution remain unresolved.
"""
from __future__ import annotations
import hashlib
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.context import unresolved_usage_index, method_spec_record
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.sse_lanes import decode_lane_transfer_instructions
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar

SCHEMA = 'endfield.buff-effect-line-center-trail-native-contract.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_effect_line_center_trail_native.json'
LABEL = 'buffEffectLineCenterTrail'
TRAIL = 'HG.Rendering.Runtime.VFXTrailPointsTool'


def _fail(check: str, expected: Any, actual: Any) -> None:
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} '
                     f'expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _contract() -> dict:
    result, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
        status='exact-current-build', label=LABEL)
    if (result.get('scope') != 'conditional-trail-forwarding-and-start-guards'
            or set(result.get('programs', {})) != {'forwarding','start','zeroPredicate'}
            or len(result.get('fields', [])) != 4):
        _fail('contract-shape', 'four typed fields and three bounded programs', result.get('scope'))
    return result


def _forwarding(rows: list[dict], pointers: dict, offsets: dict) -> dict:
    g = ProgramGrammar(rows, label=LABEL+'.forwarding')
    data, center, target = (offsets[k] for k in ('data','cfgCenter','trailCenter'))
    g.take('mov [rsp+0x8], rbx','push rsi','push rdi','push r14',
        'sub rsp, 0xa0','mov rbx, rcx','xor edx, edx')
    g.pattern(r'mov ecx, 0x[0-9a-f]+'); g.call(pointers['isPatched'])
    g.take('test al, al'); patch = g.branch('jne')
    g.take(f'mov rdi, [rbx+0x{data:x}]','test rdi, rdi'); g.branch('je')
    g.take(f'movsd xmm0, [rdi+0x{center:x}]','movaps xmm4, xmm0','xorps xmm1, xmm1',
        'subss xmm4, xmm1','movaps xmm2, xmm0','shufps xmm2, xmm2, 0x55',
        'movsd [rsp+0x40], xmm0','subss xmm2, xmm1',
        f'movss xmm3, [rdi+0x{center+8:x}]','subss xmm3, xmm1',
        'mulss xmm3, xmm3','mulss xmm2, xmm2','mulss xmm4, xmm4',
        'addss xmm4, xmm2','addss xmm3, xmm4')
    epsilon = g.pattern(r'movss xmm0, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    if not bytes.fromhex(epsilon['bytes']).startswith(b'\xf3\x0f\x10\x05'):
        g.fail('epsilon-width','32-bit scalar float load',epsilon)
    g.take('comiss xmm0, xmm3'); early = g.branch('ja')
    g.take('xor edx, edx','mov rcx, rbx'); g.call(pointers['effectObject'])
    g.take('mov rdi, rax'); g.pattern(r'mov rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('cmp [rcx+0xe0], 0x0'); g.branch('jne','object-ready'); g.call(pointers['classInit'])
    g.mark('object-ready'); g.take('xor r8d, r8d','xor edx, edx','mov rcx, rdi')
    g.call(pointers['objectInequality']); g.take('test al, al'); absent = g.branch('je')
    g.pattern(r'mov rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('cmp [rcx+0xe0], 0x0'); g.branch('jne','pool-ready'); g.call(pointers['classInit'])
    g.mark('pool-ready'); allocation_context = g.pattern(r'mov rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.call(pointers['allocate']); g.take('mov r14, rax','mov [rsp+0xd0], rax',
        'xor edx, edx','mov rcx, rbx'); g.call(pointers['effectObject'])
    g.take('test rax, rax'); g.branch('je')
    query_context = g.pattern(r'mov r9, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('mov r8, r14','mov dl, 0x1','mov rcx, rax'); query = g.call(pointers['query'])
    g.take('test r14, r14'); g.branch('je')
    enumerator_context = g.pattern(r'mov r8, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('mov rdx, r14','lea rcx, [rsp+0x40]'); enumerator = g.call(pointers['getEnumerator'])
    g.take('movups xmm0, [rsp+0x40]','movups [rsp+0x60], xmm0',
        'movsd xmm1, [rsp+0x50]','movsd [rsp+0x70], xmm1',
        'xor esi, esi','mov [rsp+0x40], rsi','lea rax, [rsp+0x60]','mov [rsp+0x48], rax')
    g.mark('move-next')
    next_context = g.pattern(r'mov rdx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('lea rcx, [rsp+0x60]'); next_call = g.call(pointers['moveNext'])
    g.take('test al, al'); g.branch('je','loop-exit')
    g.take('mov rcx, [rsp+0x70]',f'mov rax, [rbx+0x{data:x}]','test rax, rax'); g.branch('je')
    z = g.take(f'mov edx, [rax+0x{center+8:x}]')
    if bytes.fromhex(z['bytes'])[0] != 0x8b: g.fail('source-z-width','32-bit scalar copy',z)
    g.take('test rcx, rcx'); g.branch('je')
    g.take(f'movsd xmm0, [rax+0x{center:x}]',f'movsd [rcx+0x{target:x}], xmm0')
    z = g.take(f'mov [rcx+0x{target+8:x}], edx')
    if bytes.fromhex(z['bytes'])[0] != 0x89: g.fail('destination-z-width','32-bit scalar copy',z)
    g.take('xor edx, edx'); start = g.call(pointers['start']); g.branch('jmp','move-next')
    g.mark('loop-exit'); g.finish(prefix=True)
    if early['target'] != absent['target']:
        g.fail('common-early-exit','same offset/object early-exit target',{'offset':early,'object':absent})
    return {'instructionsChecked':g.cursor,'entryPrefixChecked':True,'completeCallerChecked':False,
        'thisReceiver':'incoming instance RCX preserved in RBX',
        'configuration':'fresh current EffectInstance.m_data reload in each successful iteration',
        'copyBytes':12,'sourceField':'Beyond.Gameplay.EffectActionCfg::centerOffset',
        'destinationField':TRAIL+'::centerOffset','allComponentsCopiedBeforeStart':True,
        'includeInactive':True,'loopEnumeratorCurrentOffset':16,
        'enumeratorValueCopyBytes':24,'configurationReferencesAcrossCallsEquated':False,
        'startCall':start,'queryCall':query,'enumeratorCall':enumerator,'moveNextCall':next_call,
        'epsilonLoad':epsilon,'epsilonEarlyExitPredicate':'ordered epsilon > squared float32 displacement',
        'patchBranch':patch,'contexts':{'allocate':allocation_context,'query':query_context,
            'getEnumerator':enumerator_context,'moveNext':next_context},
        'selection':'ordinary IFix-false prefix; guards take checked continuation; providers return compatible nonnull objects and MoveNext selects a valid current component',
        'genericRuntimeInitializationProved':False,'componentQueryObserved':False}


def _start(rows: list[dict], pointers: dict, erosion_offset: int) -> dict:
    g = ProgramGrammar(rows,label=LABEL+'.start')
    g.take('push rbx','sub rsp, 0x20','mov rbx, rcx','xor edx, edx')
    g.pattern(r'mov ecx, 0x[0-9a-f]+'); g.call(pointers['isPatched'])
    g.take('test al, al'); g.branch('jne','patch')
    erosion = g.take(f'cmp [rbx+0x{erosion_offset:x}], al')
    if bytes.fromhex(erosion['bytes'])[0] != 0x38: g.fail('erosion-byte-width','byte CMP',erosion)
    g.branch('jne','epilogue'); g.take('xor edx, edx','mov rcx, rbx')
    apply = g.call(pointers['applyOffset'])
    g.take('xor edx, edx','mov rcx, rbx','add rsp, 0x20','pop rbx')
    tail = g.branch('jmp')
    if tail['target'] != pointers['applyPoints']: g.fail('points-tail-call',pointers['applyPoints'],tail)
    g.mark('patch'); g.take('xor edx, edx'); g.pattern(r'mov ecx, 0x[0-9a-f]+')
    g.call(pointers['getPatch']); g.take('test rax, rax'); g.branch('jne','invoke-patch')
    g.call(pointers['fatal']); g.take('int3')
    g.mark('invoke-patch'); g.take('xor r8d, r8d','mov rdx, rbx','mov rcx, rax')
    g.call(pointers['invokeVoid'])
    g.mark('epilogue'); g.take('add rsp, 0x20','pop rbx','ret'); g.finish()
    return {'completeProgramChecked':True,'instructionsChecked':len(rows),
        'ordinaryErosionNonzeroReturnsWithoutPointCalls':True,
        'ordinaryErosionZeroCalls':['same receiver _ApplyCenterOffset','same receiver tail ApplyPoints'],
        'applyOffsetCall':apply,'applyPointsTailCall':tail,'runtimeExecutionObserved':False}


def _parity(g: ProgramGrammar, label: str) -> None:
    row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'],16)
    if len(raw) != 2 or raw[0] != 0x7a:
        g.fail('unordered-predicate','complete short JP',row)
    target = at+2+int.from_bytes(raw[1:],'little',signed=True)
    if row['text'] != f'jp 0x{target:x}': g.fail('unordered-decoding',hex(target),row)
    g.edges.append((target,label,row))


def _zero_predicate(rows: list[dict], pointers: dict, center_offset: int) -> dict:
    g = ProgramGrammar(rows,label=LABEL+'.zeroPredicate')
    g.take('push rbx','sub rsp, 0x20','mov rbx, rcx','xor edx, edx')
    g.pattern(r'mov ecx, 0x[0-9a-f]+'); g.call(pointers['isPatched'])
    g.take('test al, al'); g.branch('jne','patch')
    for component in range(3):
        g.take(f'movss xmm0, [rbx+0x{center_offset+component*4:x}]')
        if component == 0: g.take('xorps xmm1, xmm1')
        g.take('ucomiss xmm0, xmm1'); _parity(g,'nonzero'); g.branch('jne','nonzero')
    g.take('add rsp, 0x20','pop rbx','ret')
    g.mark('nonzero'); g.take('mov al, 0x1','add rsp, 0x20','pop rbx','ret')
    g.mark('patch'); g.take('xor edx, edx'); g.pattern(r'mov ecx, 0x[0-9a-f]+')
    g.call(pointers['getPatch']); g.take('test rax, rax'); g.branch('jne','invoke-patch')
    g.call(pointers['fatal']); g.take('int3')
    g.mark('invoke-patch'); g.take('xor r8d, r8d','mov rdx, rbx','mov rcx, rax','add rsp, 0x20','pop rbx')
    tail = g.branch('jmp')
    if tail['target'] != pointers['invokeBool']: g.fail('bool-patch-tail',pointers['invokeBool'],tail)
    g.finish()
    return {'completeProgramChecked':True,'instructionsChecked':len(rows),
        'ordinaryFalse':'all three components compare equal to zero, including negative zero',
        'ordinaryTrue':'any component is nonzero or unordered (NaN)',
        'usesEpsilon':False,'falseReturnAlPreservedFromIsPatched':True,'runtimeExecutionObserved':False}


def _validate_image(image: Any, contract: dict) -> dict:
    index = BodyIndex(image); selected = NativeReferenceContext(image,index=index); base = image.pe.image_base
    if selected.parent('Beyond.Gameplay.BattleNormalEffect') != 'Beyond.Gameplay.EffectInstance':
        _fail('receiver-ancestry','immediate EffectInstance parent',selected.parent('Beyond.Gameplay.BattleNormalEffect'))
    offsets = {}
    expected_fields = {'data':('Beyond.Gameplay.EffectInstance::m_data','Beyond.Gameplay.EffectActionCfg'),
        'cfgCenter':('Beyond.Gameplay.EffectActionCfg::centerOffset','UnityEngine.Vector3'),
        'trailCenter':(TRAIL+'::centerOffset','UnityEngine.Vector3'),
        'erosion':(TRAIL+'::isErosionLine','bool')}
    for field in contract['fields']:
        if (field['role'] not in expected_fields
                or (field['field'],field['type']) != expected_fields[field['role']]
                or field['role'] in offsets):
            _fail('field-role',expected_fields,field)
        actual = selected.field(field['field'])
        if actual != (field['owner'],field['type'],field['offset']): _fail('field:'+field['field'],field,actual)
        offsets[field['role']] = field['offset']
    vector = selected.index.types.get('UnityEngine.Vector3')
    if vector is None or vector.generic_container_index>=0 or not selected.is_value_type('UnityEngine.Vector3'):
        _fail('vector-value','nongeneric selected Vector3 value',None)
    vector_fields = [f for f in image.metadata.fields_for(vector) if not selected.field_attributes(f.type_index)&0x10]
    if len(vector_fields)!=3 or [selected.field('UnityEngine.Vector3::'+c) for c in ('x','y','z')] != [('UnityEngine.Vector3','float',16),('UnityEngine.Vector3','float',20),('UnityEngine.Vector3','float',24)]:
        _fail('vector-components','three consecutive float32 components',vector_fields)
    size_pointer = image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+vector.index*8)
    if image.pe.u32_at_va(size_pointer)!=28: _fail('vector-size','12 unboxed bytes',image.pe.u32_at_va(size_pointer))
    for declaration in contract['declarations']:
        method = image.metadata.methods[declaration['methodIndex']]
        actual = {'methodIndex':method.index,'type':image.type_name(method.declaring_type),
            'method':image.metadata.string(method.name_index),'flags':method.flags,
            'returnType':selected.type_name(method.return_type),
            'returnNativeTypeHex':image.pe.bytes_at_va(selected.type_pointer(method.return_type),16).hex().upper(),
            'parameters':[{'name':image.metadata.string(p.name_index),'type':selected.type_name(p.type_index),
                'nativeTypeHex':image.pe.bytes_at_va(selected.type_pointer(p.type_index),16).hex().upper()}
                for p in image.metadata.parameters_for(method)]}
        if actual != declaration: _fail('declaration:'+declaration['method'],declaration,actual)
    for role in ('forwarding','start','zeroPredicate'):
        declaration = next(d for d in contract['declarations'] if d['methodIndex']==contract['programs'][role]['method'][0])
        method = image.metadata.methods[declaration['methodIndex']]
        if (declaration['flags'] & 0x10 or declaration['parameters'] or method.generic_container_index>=0
                or declaration['returnType'] != ('bool' if role=='zeroPredicate' else 'void')):
            _fail('instance-abi:'+role,'nongeneric no-argument instance program',declaration)
    programs = {}
    for role,spec in contract['programs'].items():
        image.validate_method_row(spec['method'],label=LABEL)
        window = spec['window']; pointer = base+window['startRva']
        if pointer != base+spec['method'][3] or index.extents.get(pointer) != base+window['endRva']:
            _fail('owned-primary:'+role,spec['method'],window)
        image.check_windows([window],label=LABEL)
        programs[role] = decode_lane_transfer_instructions(image.mapper,image.window_bytes(window),pointer)
    pointers = {role:base+rva for role,rva in contract['callTargets'].items()}
    for role,name in contract['namedCallTargets'].items():
        if index.names_of(pointers[role]) != [name]: _fail('named-call:'+role,[name],index.names_of(pointers[role]))
    forwarding = _forwarding(programs['forwarding'],pointers,offsets)
    start = _start(programs['start'],pointers,offsets['erosion'])
    zero = _zero_predicate(programs['zeroPredicate'],pointers,offsets['trailCenter'])
    contexts = []
    expected_contexts = {'allocate':('Beyond.PoolCore.ListPool`1','Allocate',[TRAIL],[]),
        'query':('UnityEngine.GameObject','GetComponentsInChildren',[],[TRAIL]),
        'getEnumerator':('System.Collections.Generic.List`1','GetEnumerator',[TRAIL],[]),
        'moveNext':('System.Collections.Generic.List`1+Enumerator','MoveNext',[TRAIL],[])}
    if set(contract['genericContexts']) != set(expected_contexts):
        _fail('generic-context-roles',list(expected_contexts),list(contract['genericContexts']))
    for role,spec in contract['genericContexts'].items():
        expected_type,expected_method,expected_class,expected_method_args = expected_contexts[role]
        if (spec['definition'][1:] != [expected_type,expected_method]
                or spec['classArguments'] != expected_class or spec['methodArguments'] != expected_method_args):
            _fail('context-role:'+role,expected_contexts[role],spec)
        row = forwarding['contexts'][role]; raw = bytes.fromhex(row['bytes']); at = int(row['va'],16)
        if len(raw)!=7 or raw[:3] not in (b'\x48\x8b\x0d',b'\x48\x8b\x15',b'\x4c\x8b\x05',b'\x4c\x8b\x0d'):
            _fail('context-load:'+role,'complete RIP-relative qword load',row)
        cell = at+7+int.from_bytes(raw[3:],'little',signed=True)
        word = image.pe.bytes_at_va(cell,8)
        si = unresolved_usage_index(word,image.registration['methodSpecsCount'],tag=6,source=str(image.gameassembly),offset=cell)
        record_at = int(image.registration['methodSpecs'],16)+si*12
        record = image.pe.bytes_at_va(record_at,12)
        definition,ci,mi = method_spec_record(record,len(image.metadata.methods),image.registration['genericInstsCount'],source=str(image.gameassembly),offset=record_at)
        method = image.metadata.methods[definition]
        actual = [definition,image.type_name(method.declaring_type),image.metadata.string(method.name_index)]
        def args(identity):
            return [runtime_type_name(image.pe,image.metadata,a.type_pointer_va) for a in image.instantiations.resolve(identity).arguments]
        if (si != spec['methodSpecIndex'] or actual != spec['definition']
                or args(ci) != spec['classArguments'] or args(mi) != spec['methodArguments']):
            _fail('typed-context:'+role,spec,{'methodSpecIndex':si,'definition':actual,'classArguments':args(ci),'methodArguments':args(mi)})
        contexts.append({'role':role,'cellRva':cell-base,'usageRawHex':word.hex().upper(),
            'definition':actual,'classArguments':args(ci),'methodArguments':args(mi),
            'methodSpecIndex':si,'methodSpecRawHex':record.hex().upper()})
    epsilon = forwarding['epsilonLoad']; raw = bytes.fromhex(epsilon['bytes']); at = int(epsilon['va'],16)
    cell = at+8+int.from_bytes(raw[4:],'little',signed=True)
    actual = image.pe.bytes_at_va(cell,4).hex().upper()
    if actual != contract['epsilon']['rawHex'] or cell-base != contract['epsilon']['rva']:
        _fail('epsilon-literal',contract['epsilon'],{'rva':cell-base,'rawHex':actual})
    return {'fields':contract['fields'],'forwarding':forwarding,'start':start,'zeroPredicate':zero,
        'staticTypedContexts':contexts,'epsilon':{'rva':cell-base,'rawHex':actual,'float32':struct.unpack('<f',bytes.fromhex(actual))[0]},
        'conditionalTrailOffsetCopyProved':True,'ordinaryStartGuardsProved':True,
        'ordinaryExactZeroPredicateProved':True,'parentExecutionConfigurationJoinProved':False,
        'pointDeformationProved':False,'rendererSubmissionProved':False,'runtimeExecutionObserved':False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status != 'validated': return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity = Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():
        if not unity.is_file(): return False
        with unity.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches(): return {'status':'mismatched','detail':'Selected UnityPlayer missing or different','nativeInputs':pins}
    result = _validate_image(open_native_image(gate.gameassembly,gate.metadata),contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():
        return {'status':'mismatched','detail':'Selected native inputs changed during trail validation','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**result,'evidenceBoundary':contract['evidenceBoundary']}
