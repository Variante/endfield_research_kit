"""Pure bounded transfer proof for the current mixed NPC source family.

The caller supplies authenticated declarations, slots, owned rows and callees.
This component deliberately does not prove child framing, setters, factories or
provider selection. Unsupported field/source/transfer variants fail closed.
"""
import re
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar


def mixed_transfers(rows, fields, symbols, *, array_source=None):
    g = ProgramGrammar(rows, label='npcMixedTransfers')
    reads = []
    nulls = []
    def branch(kind):
        row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
        code = {'je': 4, 'jne': 5, 'jge': 13}[kind]
        rel = raw[1:] if len(raw) == 2 and raw[0] == 0x70 + code else raw[2:] if len(raw) == 6 and raw[:2] == bytes((15, 128 + code)) else None
        if rel is None: g.fail('branch-predicate', kind, row)
        target = at + len(raw) + int.from_bytes(rel, 'little', signed=True)
        if row['text'] not in (f'{kind} {target:#x}', f'jcc {target:#x}'): g.fail('branch-text', kind, row)
        return target
    def null(reg):
        g.take(f'test {reg}, {reg}'); nulls.append(branch('je'))
    def call():
        row = g.rows[g.cursor]; raw = bytes.fromhex(row['bytes'])
        if len(raw) != 5 or raw[0] != 232: g.fail('source', 'direct E8 call', row)
        target = int(row['va'], 16) + 5 + int.from_bytes(raw[1:], 'little', signed=True)
        g.call(target); return row, target
    def context(reg):
        if g.rows[g.cursor]['text'].startswith(f'mov {reg}, [rip'):
            return g.pattern(r'mov '+reg+r', \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    def buffered(width, receiver):
        g.take(f'cmp dword [rdi+0x30], {width:#x}', f'mov {receiver}, [rsi]')
        ready = branch('jge'); g.take('xor r8d, r8d', f'mov edx, {width:#x}', 'mov rcx, rdi')
        g.call(symbols['refill'])
        if ready != int(g.rows[g.cursor]['va'], 16): g.fail('buffered-join', ready, g.rows[g.cursor])
    for i, field in enumerate(fields):
        start = g.cursor; inline = field['mode']; offset = field['offset']; source_context = None
        if inline == 'outref-dictionary':
            class_context = context('rcx'); g.take('mov [rbp+0x58], r13', 'cmp dword [rcx+0xe0], 0x0')
            ready = branch('jne'); g.call(symbols['classInit'])
            if ready != int(g.rows[g.cursor]['va'],16): g.fail('dictionary-ready', ready, g.rows[g.cursor])
            source_context = context('r8'); g.take('lea rdx, [rbp+0x58]', 'mov rcx, rdi'); source, target = call()
            g.take('mov rcx, [rsi]', 'mov rbx, [rbp+0x58]'); null('rcx'); g.take('xor edx, edx'); g.call(symbols['getter']); null('rax')
            g.take(f'lea rcx, [rax+{offset:#x}]', f'mov [rax+{offset:#x}], rbx'); g.call(symbols['barrier'])
            reads.append(dict(field=field['name'], mode=inline, sourceCall=source, target=target, contextLoad=source_context, classContextLoad=class_context, startVA=int(g.rows[start]['va'],16), endVA=int(g.rows[g.cursor-1]['va'],16)+len(bytes.fromhex(g.rows[g.cursor-1]['bytes']))))
            continue
        if inline == 'int32-array':
            if array_source is None: g.fail('array-source', 'independent selected array-source function', None)
            paths = [array_source(count=n) for n in range(-1, 6)]
            ends = {p['selectedBytes'][-1][0]+len(bytes.fromhex(p['selectedBytes'][-1][1])) for p in paths}
            if len(ends) != 1: g.fail('array-rejoin', 'one final setter end', sorted(ends))
            end = ends.pop()
            if any(p['selectedBytes'][0][0] != int(g.rows[g.cursor]['va'],16) for p in paths): g.fail('array-start', 'current next source', paths)
            while g.cursor < len(g.rows) and int(g.rows[g.cursor]['va'],16) < end: g.row()
            if g.cursor == 0 or int(g.rows[g.cursor-1]['va'],16)+len(bytes.fromhex(g.rows[g.cursor-1]['bytes'])) != end: g.fail('array-end', 'current original instruction boundary', end)
            reads.append(dict(field=field['name'],mode=inline,sourcePaths=paths,startVA=int(g.rows[start]['va'],16),endVA=end))
            continue
        if inline == 'vector12':
            buffered(12, 'rbx'); g.take('mov rax, [rdi+0x50]', 'mov edx, 0xc', 'mov rcx, rdi', 'movsd xmm6, [rax]', 'mov r14d, [rax+0x8]')
            source, target = call()
            if target != symbols['advance']: g.fail('vector-advance', symbols['advance'], target)
            null('rbx'); g.take('mov rax, [rbx+0x10]'); null('rax')
            g.take(f'movsd [rax+{offset:#x}], xmm6')
            if i == 12: g.take('mov rcx, rdi')
            g.take(f'mov [rax+{offset+8:#x}], r14d')
        else:
            raw4 = inline == 'inline4'
            hidden16 = inline == 'hidden16'
            if raw4:
                buffered(4, 'r14'); g.take('mov rbx, [rdi+0x50]', 'mov edx, 0x4', 'mov rcx, rdi', 'mov ebx, [rbx]')
                source, target = call()
                if target != symbols['advance']: g.fail('inline-advance', symbols['advance'], target)
                receiver = 'r14'
            elif hidden16:
                source_context = context('r8'); local = field.get('hiddenLocal', -32)
                if local not in (-32, -48): g.fail('hidden-output-local', [-32,-48], local)
                g.take(f'lea rcx, [rbp-{(-local):#x}]', 'mov rbx, [rsi]', 'mov rdx, rdi')
                source, target = call(); receiver = 'rbx'
            else:
                for _ in range(3):
                    text = g.rows[g.cursor]['text']
                    if text == 'mov rcx, rdi': g.take(text)
                    elif text == 'mov rbx, [rsi]': g.take(text)
                    elif text.startswith('mov rdx, [rip'): source_context = context('rdx')
                    else: break
                setup = [row['text'] for row in g.rows[start:g.cursor]]
                wanted = ['mov rbx, [rsi]'] + ([] if i == 13 else ['mov rcx, rdi'])
                if sorted(t for t in setup if not t.startswith('mov rdx, [rip')) != sorted(wanted): g.fail('entry-arguments', wanted, setup)
                source, target = call(); receiver = 'rbx'
            if field['transfer'] == 'direct':
                null(receiver); g.take('mov rcx, [rbx+0x10]'); null('rcx')
                reg = {'bool':'al','scalar64':'rax','enum':'eax'}[field['kind']]
                g.take(f'mov [rcx+{offset:#x}], {reg}')
            elif field['transfer'] == 'setter':
                null(receiver)
                if hidden16:
                    g.take(f'movaps xmm0, [rbp-{(-local):#x}]', 'lea rdx, [rbp-0x20]', 'xor r8d, r8d', 'movdqa [rbp-0x20], xmm0', 'mov rcx, rbx')
                else:
                    g.take('xor r8d, r8d')
                    move = 'mov edx, ebx' if raw4 else {'bool':'movzx edx, al','scalar32':'mov edx, eax','enum':'mov edx, eax','float32':'movaps xmm1, xmm0'}.get(field['kind'], 'mov rdx, rax')
                    g.take(move, f'mov rcx, {receiver}')
                g.call(field['setter'])
            elif field['transfer'] == 'getter-store':
                save = 'rdi' if i == len(fields)-1 else 'r14'
                if not raw4:
                    g.take(f'movzx {save}d, al' if field['kind'] == 'bool' else f'mov {save}d, eax' if field['kind'] in ('scalar32','enum') else f'mov {save}, rax')
                null(receiver); g.take('xor edx, edx', f'mov rcx, {receiver}'); g.call(symbols['getter']); null('rax')
                if i == len(fields)-1: g.take('movaps xmm6, [rsp+0x70]')
                reg = 'ebx' if raw4 else save+'b' if field['kind'] == 'bool' else save+'d' if field['kind'] in ('scalar32','enum') else save
                if field['reference']: g.take(f'lea rcx, [rax+{offset:#x}]')
                g.take(f'mov [rax+{offset:#x}], {reg}')
                if field['reference']: g.call(symbols['barrier'])
            else: g.fail('transfer-kind', ['direct','setter','getter-store'], field)
        reads.append(dict(field=field['name'],mode=inline,sourceCall=source,target=target,contextLoad=source_context,startVA=int(g.rows[start]['va'],16),endVA=int(g.rows[g.cursor-1]['va'],16)+len(bytes.fromhex(g.rows[g.cursor-1]['bytes']))))
    g.finish()
    if len(set(nulls)) != 1: g.fail('null-target', 'one caller null failure', nulls)
    return dict(fieldTransfers=reads, nullExitVA=nulls[0],completeSelectedFieldTransfers=True,childFramingProved=False,readerHolderOriginsProved=False,settersGettersAndInitializationProved=False)

"""Selected initialized parent-inlined unmanaged Int32 array transfers.

Closed contexts, header/copy/advance sources, setter ownership and caller entry
origins remain separate proof obligations. This bounded component never selects
a live runtime MethodInfo or admits an NPC owner.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def selected_array(regions, entry, symbols, *, count):
    if type(count) is not int or not -1 <= count <= 5:
        raise ValueError('npcIntArray.selected-count')
    g = BytesPath(regions, entry)
    usage = g.relative('488b1d')
    g.take('4c8b26', '4c396b38'); g.branch('75', True, 1)
    g.take('488b4338', '488b18', '4c396b38'); g.branch('75', True, 1)
    g.take('488d5548', '44896d48', '488bcf'); g.call(symbols['header'])
    g.take('84c0'); g.branch('0f84', count == -1)
    if count == -1:
        g.take('4d8bf5')
    else:
        g.take('448b7548', '4585f6'); g.branch('0f84', count == 0)
        if count:
            g.take('468d3cb500000000', '443b7f30'); g.branch('7e', True, 1)
            g.take('488b4338', '4c8b6808', '49837d3800'); g.branch('75', True, 1)
            g.take('498b4d38', '33d2'); g.call(symbols['indexedClass'])
            g.take('498bd6', '488bc8'); g.call(symbols['arrayAllocate'])
            g.take('4c8bf0', '488b4338', '4c8b6810', '49837d3800'); g.branch('75', True, 1)
            g.take('498b4538', '488b08', '4883793800'); g.branch('75', True, 1)
            initialized = g.relative('803d'); g.take('00'); g.branch('75', True, 1)
            g.take('4d85f6'); g.branch('74', False, 1)
            g.take('498d5e20'); g.jump('eb', 1)
            g.take('498b4538', '488b4808', '4883793800'); g.branch('75', True, 1)
            g.take('488b5750', '488bcb', '458bc7'); g.call(symbols['copyForwarder'])
            g.take('418bd7', '488bcf'); g.call(symbols['advance'])
            g.take('4533ed'); g.jump('eb', 1)
        else:
            initialized = None
            g.take('488b4338', '488b18', '4c396b38'); g.branch('75', True, 1)
            g.take('488b4b38', '33d2'); g.call(symbols['indexedClass'])
            g.take('4439a8e0000000'); g.branch('75', True, 1)
            g.take('488b4b38', '33d2'); g.call(symbols['indexedClass'])
            g.take('488b88b8000000', '4c8b31'); g.jump('eb', 1)
    g.take('4d85e4'); g.branch('0f84', False)
    g.take('4533c0', '498bd6', '498bcc'); g.call(symbols['setter'])
    return dict(selectedBytes=g.seen, count=count, usageCellVA=usage,
                initializedFlagVA=initialized if count != -1 else None,
                headerBytes=4, elementBytes=4, copyBytes=max(0, count)*4,
                arrayDataOffset=32, sameReaderRegister='rdi', setterReceiver='original holder dereference saved R12',
                selectedTypedContextSlots=dict(readUnmanagedArrayDangerous=0,dangerousArrayEmpty=0,dangerousArrayAllocate=1,dangerousArrayDataReference=2),
                wholeOwnerAdmitted=False, calleeEffectsProved=False,
                condition='Selected initialized context blocks and optional metadata flag ready, R13 zero on entry, buffered valid disjoint Reader/frame, count -1/0/1..5, matching original Int32 array contexts, normal header/indexed-class/typed-allocation/setter ABI, exact independently proved copy-forwarder and Advance effects. Empty-array identity and live MethodInfo/provider selection remain separate.')

"""Initialized NPC root header/origin paths; all runtime selections explicit."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def root_prefix(regions, entry, symbols, *, allocated=False, null=False):
    g = BytesPath(regions, entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','488bec','4881ec80000000','4533ed')
    image_base = g.relative('4c8d3d')
    init = g.relative('44382d')
    g.take('488bf2','488bf9'); g.branch('0f85',True)
    g.take('4c8b36','4c896d58','4d85f6'); g.branch('0f84',allocated)
    if not allocated:
        cache_init = g.relative('44382d'); g.branch('0f85',True)
        g.take('4d396e20'); g.branch('75',True,1)
    else:
        cache_init = None
    g.take('837f3001'); g.branch('7d',True,1)
    g.take('488b4750','440fb630','8b5f30','83eb01'); g.branch('79',True,1)
    g.take('48ff4750','ff4740','ff4744','895f30','4180feff'); g.branch('0f84',null)
    if null:
        g.take('488bce','4c892e'); g.call(symbols['barrier']); g.jump('eb',1)
        g.take('488b9c24c0000000','4881c480000000','415f','415e','415d','415c','5f','5e','5d','c3')
        allocation_cell = None
    else:
        g.take('0f29742470','4c392e'); g.branch('75',not allocated,1)
        allocation_cell = None
        if allocated:
            allocation_cell = g.relative('488b0d'); g.call(symbols['allocate'])
            g.take('488bd8','4885c0'); g.branch('0f84',False)
            g.take('33d2','488bc8'); g.call(symbols['constructor'])
            g.take('488bce','48891e'); g.call(symbols['barrier'])
        g.take('4180fe79'); g.branch('0f85',False)
    return dict(selectedBytes=g.seen,imageBaseVA=image_base,initializedFlagVA=init,
                cacheInitializedFlagVA=cache_init,allocationTypeCellVA=allocation_cell,
                sourceReaderRegister='rdi',wrapperOutputRegister='rsi',zeroRegister='r13',
                headerBytes=1,expectedMemberCount=None if null else 121,null=null,allocated=allocated,
                nextInstructionVA=g.at,returnsNormally=null,wholeOwnerAdmitted=False,
                condition='Initialized metadata and buffered disjoint Reader/output/frame; header FF or121, nonwrapping pointer/counters, normal ABI-preserving barrier/allocation/constructor calls. Existing path requires nonnull wrapper and nonnull RuntimeProxy cache; base/cache coherence and any cache refresh remain independent. Allocated path requires null incoming wrapper and normal typed constructor effects independently established. Cold initialization/refill/fallback/mismatched-count paths are excluded.')

"""Initialized inherited NPC setter paths with explicit cache refresh selection."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def _branch(g, code, taken):
    first = g.bytes[g.at]
    g.branch(('0f'+f'{0x80+code:02x}') if first == 15 else f'{0x70+code:02x}', taken, 4 if first == 15 else 1)


def _disp(prefix, field):
    if type(field) is not int or not 16 <= field < 0x80000000:
        raise ValueError('npcSetter.owned-field-offset')
    raw = bytearray.fromhex(prefix)
    raw[-1] = (raw[-1] & 63) | (64 if field < 128 else 128)
    return (raw + field.to_bytes(1 if field < 128 else 4, 'little', signed=True)).hex()


def selected_setter(regions, entry, field, mode, symbols, *, refresh='coherent'):
    if refresh not in ('coherent','empty','different') or mode not in ('bool','int32','uint64','reference','value4','value16','float'):
        raise ValueError('npcSetter.selected-profile')
    g = BytesPath(regions, entry)
    if mode == 'float':
        g.take('4883ec38'); flag = g.relative('803d'); g.take('00','0f29742420','0f28f1','48895c2440','488bd9')
    elif mode == 'value4':
        g.take('4053','4883ec20'); flag = g.relative('803d'); g.take('00','8bda','48897c2438','488bf9')
    else:
        g.take('4057','4883ec20'); flag = g.relative('803d'); g.take('00')
        g.take('0fb6fa' if mode == 'bool' else '8bfa' if mode == 'int32' else '488bfa','48895c2430','488bd9')
    _branch(g,4,False)
    holder = 'rdi' if mode == 'value4' else 'rbx'
    h = '7f' if holder == 'rdi' else '7b'
    g.take('4883'+h+'1800'); _branch(g,4,refresh=='empty')
    if refresh != 'empty':
        g.take('488b47'+'10' if holder=='rdi' else '488b4310','48394718' if holder=='rdi' else '48394318')
        _branch(g,5,refresh=='different')
    cast_cells = []
    if refresh != 'coherent':
        saved = 'rdi' if mode == 'float' else 'rsi'
        if mode == 'float':
            g.take('48897c2430','488b7b10','4885ff')
        elif mode == 'value4':
            g.take('4889742430','488b7710','4885f6')
        else:
            g.take('4889742438','488b7310','4885f6')
        _branch(g,4,False)
        cast_cells.append(g.relative('488b15')); g.take('488b0f' if saved=='rdi' else '488b0e')
        g.call(symbols['assignable']); g.take('84c0'); _branch(g,4,False)
        g.take('488bc7' if saved=='rdi' else '488bc6','48894718' if holder=='rdi' else '48894318')
        cast_cells.append(g.relative('488b15')); g.take('488b0f' if saved=='rdi' else '488b0e')
        g.call(symbols['assignable']); g.take('488d4f18' if holder=='rdi' else '488d4b18'); g.call(symbols['barrier'])
        g.take('488b7c2430' if mode=='float' else '488b742430' if mode=='value4' else '488b742438')
        g.jump('eb' if g.bytes[g.at]==235 else 'e9',1 if g.bytes[g.at]==235 else 4)
        if len(set(cast_cells)) != 1: raise ValueError('npcSetter.refresh-class-cell-identity')
    reference = mode in ('reference','value16')
    g.take('488b4b18' if reference else '488b4718' if holder=='rdi' else '488b4318')
    g.take('488b7c2438' if mode=='value4' else '488b5c2440' if mode=='float' else '488b5c2430')
    g.take('4885c9' if reference else '4885c0'); _branch(g,4,False)
    if mode=='value16':
        g.take('0f1007',_disp('0f1141',field))
    else:
        g.take(_disp(dict(reference='488979',uint64='488978',int32='8978',bool='408878',value4='8958',float='f30f1170')[mode],field))
    if reference:
        g.take('4883c1'+bytes((field,)).hex() if field<128 else '4881c1'+field.to_bytes(4,'little').hex(),'4883c420','5f')
        if g.relative('e9') != symbols['barrier']: raise ValueError('npcSetter.reference-barrier-tail')
    elif mode=='float':
        g.take('0f28742420','4883c438','c3')
    else:
        g.take('4883c420','5b' if mode=='value4' else '5f','c3')
    return dict(selectedBytes=g.seen,mode=mode,fieldOffset=field,baseSlot=16,cacheSlot=24,
                initializedFlagVA=flag,refresh=refresh,castClassCellVAs=cast_cells,
                unchangedIncomingArgumentStored=True,ownedFieldProved=False,wholeOwnerAdmitted=False,
                condition='Initialized metadata, stable compatible original object/base reference, coherent nonnull cache or selected successful compatible refresh; normal ABI-preserving assignability and collector calls, predicate success and initialized runtime class layout remain conditional. Cold initialization, incompatible/null original and exceptional paths are not admitted.')

"""Current root cached getter, including successful ordinary refresh paths."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def getter(regions, entry, symbols, *, refresh='coherent'):
    if refresh not in ('coherent','empty','different'):
        raise ValueError('npcRootGetter.refresh')
    g = BytesPath(regions, entry)
    g.take('4053','4883ec20'); flag = g.relative('803d'); g.take('00','488bd9'); g.branch('74',False,1)
    g.take('48837b2000'); g.branch('0f84',refresh=='empty')
    if refresh != 'empty':
        g.take('488b4310','48394320'); g.branch('0f85',refresh=='different')
    cells = []
    if refresh != 'coherent':
        cells.append(g.relative('488b15')); g.take('48897c2430','488b7b10','488bcf'); g.call(symbols['cast'])
        g.take('48894320','488bcf'); cells.append(g.relative('488b15')); g.call(symbols['cast'])
        g.take('488d4b20'); g.call(symbols['barrier']); g.take('488b7c2430'); g.jump('e9')
        if len(set(cells)) != 1:
            raise ValueError('npcRootGetter.same-typed-cast-cell')
    g.take('488b4320','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,refresh=refresh,initializedFlagVA=flag,castClassCellVAs=cells,
                baseSlot=16,cacheSlot=32,normalReturn=True,wholeOwnerAdmitted=False,
                condition='Initialized metadata and stable wrapper/base/cache; coherent nonnull cache or normal compatible cast and collector effects. Runtime cast predicate, execution and typed object/class binding remain separate.')

"""Same-reference compatible cast shell; the assignability outcome stays conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def compatible_cast(regions, entry, assignable, *, null=False):
    g = BytesPath(regions, entry)
    g.take('4053','4883ec20','488bd9','4885c9'); g.branch('74',null,1)
    if null:
        g.take('33c0')
    else:
        g.take('488b09'); g.call(assignable)
        g.take('33c9','84c0','480f44d9','488bc3')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,null=null,conditionalUnchangedCompatibleReference=True,
                predicateOutcomeProved=False,wholeOwnerAdmitted=False)

"""Current initialized NPC root constructor path; inherited cache24 remains distinct."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def constructor(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20');g.relative('803d');g.take('00','488bd9');g.branch('0f84',False)
    baseclass=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('33d2','488bcb');g.call(s['baseConstructor'])
    rootclass=g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
    emptyclass=g.relative('488b0d');g.take('488b91b8000000','488b0a','48898858020000','488d8858020000');g.call(s['barrier'])
    envclass=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
    g.take('c6402001','488d8f68020000','48898768020000','4889742430');g.call(s['barrier'])
    g.take('33d2','c6879802000001','488bcf');g.call(s['originalBaseConstructor'])
    g.take('488d4b20','48897b20');g.call(s['barrier']);g.take('488d4b10','48897b10');g.call(s['barrier'])
    g.take('488b7b10');castclass=g.relative('488b35');g.take('4885ff');g.branch('0f84',False)
    g.take('488b0f','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
    g.take('48897b20');secondclass=g.relative('488b35');g.take('488b0f','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
    if castclass!=secondclass or rootclass!=castclass:raise ValueError('NPC constructor exact original class join')
    g.take('488d4b20','488b742430','488b5c2438','4883c420','5f')
    if g.relative('e9')!=s['barrier']:raise ValueError('NPC constructor final barrier tail')
    return dict(selectedBytes=g.seen,classCells=dict(baseWrapper=baseclass,rootOriginal=rootclass,staticString=emptyclass,envTalkOriginal=envclass),
                baseSlot=16,rootCacheSlot=32,inheritedCache24Rebound=False,rootAndBaseSameReference=True,
                condition='Initialized coherent class/static inputs, normal exact typed base-wrapper constructor and original LevelNpc constructor, fresh zeroed original/EnvTalk allocations, collector helpers and two successful compatible assignability predicates. Base constructor cache24 is deliberately not assumed to alias the fresh RuntimeProxy original; exact inherited setter refresh is independently required.')

"""Initialized current NPC bool setter with a coherent or refreshed root cache."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def bool_setter(regions,entry,s,*,refresh='coherent'):
    if refresh not in('coherent','empty','different'):raise ValueError('NPC root bool refresh')
    g=BytesPath(regions,entry);g.take('4055','4883ec50','48895c2468','0fb6ea','4889742470','488bf1','48897c2448','33ff');flag=g.relative('40383d');g.take('4c89742440');g.relative('4c8d35');g.branch('0f85',True)
    g.take('48397e20');g.branch('74',refresh=='empty',1)
    if refresh!='empty':g.take('488b4610','48394620');g.branch('74',refresh=='coherent',1)
    cells=[]
    if refresh!='coherent':
        g.take('488b5e10','4885db');g.branch('75',True,1)
        cells.append(g.relative('488b15'));g.take('488b0b');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
        g.take('488bfb','48897e20');cells.append(g.relative('488b15'));g.take('488b0b');g.call(s['assignable'])
        barrier=g.relative('833d');g.take('00');g.branch('74',True,1)
        if len(set(cells))!=1:raise ValueError('NPC root bool same class cells')
    else:barrier=None
    g.take('488b4620','4c8b742440','488b7c2448','488b742470','488b5c2468','4885c0');g.branch('74',False,1)
    g.take('4088a820020000','4883c450','5d','c3')
    return dict(selectedBytes=g.seen,refresh=refresh,metadataFlagVA=flag,barrierFlagVA=barrier,castClassCellVAs=cells,
                baseSlot=16,rootCacheSlot=32,fieldOffset=544,valueBytes=1,source='unchanged incoming DL preserved BPL',normalReturn=True,
                condition='Ready metadata; coherent nonnull root cache or nonnull base reference with two normal compatible assignability calls. Refreshed cache path selects disabled write-barrier flag. Cold metadata/reflection, predicate outcomes and enabled collector effects remain unproved.')

"""Selected disabled-collector inherited entity string field store."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def entity_string_setter(regions,entry,*,field):
    if field!=48:raise ValueError('NPC entity string owned field')
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488b5910','4885db');g.branch('74',False,1)
    flag=g.relative('833d');g.take('00','48895330');g.branch('74',True,1)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,collectorFlagVA=flag,fieldOffset=field,instanceSlot=16,
                unchangedIncomingReferenceStored=True,normalReturn=True,condition='Valid wrapper and matching nonnull original; selected collector flag zero. Enabled collector and null-object failure paths excluded.')


def normal_return(regions,entry):
 g=BytesPath(regions,entry);g.take('488b9c24c0000000','4881c480000000','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,restoresFrame=True,restoresWin64NonvolatileGprs=True,normalReturn=True,condition='Same matched root prefix frame and normally returned field/callee programs; preceding field transfer separately restores XMM6.')
