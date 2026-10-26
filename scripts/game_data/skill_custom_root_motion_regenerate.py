"""Re-derive the reviewed CustomRootMotion stored layout on selected native inputs.

The v2 plan records the inlined LayerMask DWORD load and Advance(4), rather
than claiming a formatter call. Only the reviewed names, declared setter
types and wire kinds are reusable. Counts, field drift, ambiguous headers,
undecodable normal-path bytes, changed primitive bodies or unmatched reader
calls refuse publication. Initializer bytes are hashed as pdata windows but
are not interpreted as serialization. This proves stored framing, not live
movement or current source-file cursors. Run with --regenerate [--write].
"""
from __future__ import annotations

if __name__ == '__main__' and not __package__:
    raise SystemExit('Use python -m scripts.game_data.skill_custom_root_motion_regenerate')

import argparse
import copy
import json
import re
import sys
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.buff_frontiers_regenerate import (
    _method_row, _nested_contexts, _read_switch,
)
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.levelscript_two_routes_native import RouteRefused, _window, open_selected_build
from scripts.game_data.memorypack.wrapper_members import derive_from_image

SCHEMA = 'endfield.skill-custom-root-motion-native-contract.v2'
CONTRACT_PATH = CONTRACTS_DIR / 'skill_custom_root_motion_native.json'


def select_reads(rows: list[dict[str, Any]], count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Select calls whose RCX is the saved reader; retain the inline DWORD proof.

    The reviewed code generator saves the reader in RBP. A change in that
    convention is a refusal, not a guessed register substitution.
    """
    headers = [i for i, row in enumerate(rows) if re.fullmatch(r'cmp \w+b, 0x' + f'{count:x}', row['text'])]
    if len(headers) != 1:
        raise RouteRefused(f'header-count={count}:matches={len(headers)}')
    header = rows[headers[0]]
    selected, pending, rcx_reader = [], [], False
    for row in rows[headers[0] + 1:]:
        text = row['text']
        if text.startswith('db '):
            raise RouteRefused(f"normal-path-undecodable={row['va']}")
        pending.append(row)
        if text.startswith('mov rcx,'):
            rcx_reader = text == 'mov rcx, rbp'
        if text.startswith('call '):
            if rcx_reader:
                selected.append({'call': row, 'setup': pending})
            pending, rcx_reader = [], False
        # Exactly the reviewed count plus the raw4 EnsureRemaining slow path.
        if len(selected) == count + 1:
            break
    if len(selected) != count + 1:
        raise RouteRefused(f'reader-call-count:expected={count + 1}:actual={len(selected)}')
    # LayerMask is the sole inline primitive at member 12. Its preceding
    # EnsureRemaining call is not a separate member read.
    ensure, advance = selected[12:14]
    if not any(r['text'] == 'mov edx, 0x4' for r in ensure['setup']):
        raise RouteRefused('layer-mask:missing-EnsureRemaining(4)')
    texts = [r['text'] for r in advance['setup']]
    required = ['mov rbx, [rbp+0x50]', 'mov edx, 0x4', 'mov rcx, rbp', 'mov ebx, [rbx]']
    if not all(t in texts for t in required):
        raise RouteRefused(f'layer-mask:inline-DWORD-or-Advance(4):actual={texts}')
    advance['inline'] = [r for r in ensure['setup'] + advance['setup'] if r['text'] in required]
    del selected[12]
    return header, selected


def check_members(plan: list[dict[str, Any]], members: Any) -> None:
    actual = [m.name for m in members]
    expected = [r['fieldName'] for r in plan]
    if actual != expected:
        raise RouteRefused(f'reviewed-fields:expected={expected}:actual={actual}')
    kinds = {'bool': 'bool-byte', 'int': 'int32', 'string': 'byte-payload',
             'Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority': 'enum-int32',
             'Beyond.Gameplay.Core.MoveCommand+RootMotionCurveMask': 'enum-int32',
             'Beyond.Blackboard+BlackboardDouble': 'scalar-payload',
             'UnityEngine.AnimationCurve': 'curve-profile',
             'Beyond.Gameplay.Core.TargetSettings': 'target-profile', 'UnityEngine.LayerMask': 'raw4'}
    for row, member in zip(plan, members):
        if kinds.get(member.declared_type) != row['kind']:
            raise RouteRefused(f"reviewed-field-type={member.name}:kind={row['kind']}:installed={member.declared_type}")


def prove_primitive(image: Any, target: int, kind: str) -> None:
    """Recognize reader operations, never a build-specific address or digest."""
    if kind=='bool-byte':
        from scripts.game_data.memorypack.scalar_param_native import boolean_source,reader_offsets
        from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
        end=dict(image.mapper.pdata_function_extents(image.pe))[target];base=image.pe.image_base
        raw=image.pe.bytes_at_va(target,end-target);rows=decode_string_source_instructions(image.mapper,raw,target)
        record={'window':{k:v for k,v in _window(image,target,end,'').items() if k!='boundary'},
                'instructions':[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows]}
        boolean_source(image,record,reader_offsets(image,'primitiveBoolean'),'primitiveBoolean');return
    data=image.pe.bytes_at_va(target,96)
    if kind == 'raw4':
        # Advance(n): subtract n from remaining bytes, increment the pointer
        # and both consumed counters. EDX=4 is proved at the parent callsite.
        required=(b'\x48\x63\xfa', b'\x2b\xf7', b'\x48\x01\x7b\x50', b'\x01\x7b\x40', b'\x01\x7b\x44')
        if not all(op in data for op in required):
            raise RouteRefused('primitive-Advance:unreviewed-body')
        return
    rows=image.mapper.decode_x64_subset(data,target,stop_offset=len(data))
    stop=next((i for i,r in enumerate(rows) if r['text']=='ret'),None)
    if stop is None: raise RouteRefused(f'primitive={kind}:no-ret')
    texts=[r['text'] for r in rows[:stop+1]]
    required=['mov esi, [rax]', 'add [rbx+0x50], 0x4', 'add [rbx+0x40], 0x4', 'add [rbx+0x44], 0x4']
    if any(t.startswith('db ') for t in texts) or not all(t in texts for t in required):
        raise RouteRefused(f'primitive={kind}:unreviewed-body')


def regenerate(contract: dict[str, Any], *, opener: Any = open_selected_build) -> dict[str, Any]:
    if contract.get('schema') != SCHEMA:
        raise RouteRefused('schema:v2-inline-source-review-required')
    image, inputs = opener()
    wrapper = contract['dispatcher']['wrapperName']
    wrappers = derive_from_image(image)
    found = [w for w in wrappers.values() if w.name == wrapper]
    if len(found) != 1:
        raise RouteRefused(f'wrapper={wrapper}:matches={len(found)}')
    plan = contract['orderedSourceReads']
    check_members(plan, found[0].members)
    switch = _read_switch(image)
    entries = [e for e in switch['entries'] if e.get('wrapperName') == wrapper]
    if len(entries) != 1:
        raise RouteRefused(f'dispatcher-wrapper={wrapper}:matches={len(entries)}')
    entry = entries[0]
    out = copy.deepcopy(contract)
    base = image.pe.image_base
    dispatcher = out['dispatcher']
    def address(value: Any) -> int:
        return int(value,16) if isinstance(value,str) else value
    table = address(switch['tableVa'])
    target = address(entry['targetVa'])
    cell = address(entry['usageCellVa'])
    import hashlib
    dispatcher.update(switchTableRva=table-base, switchEntryCount=switch['entryCount'],
        switchTableSha256=hashlib.sha256(image.pe.bytes_at_va(table, switch['entryCount']*4)).hexdigest().upper(),
        unionTag=entry['tag'], switchTargetRva=target-base,
        routeWindow=_window(image, target, target+50, 'selected dispatcher route'),
        usageCellRva=cell-base, usageRawHex=image.pe.bytes_at_va(cell,8).hex().upper(),
        registeredTypeIndex=entry['registeredTypeIndex'], wrapperTypeDefinition=entry['typeDefinition'])
    # The dispatch route's length is generator-specific; validate its exact
    # selected bytes at admission, never reuse the old window's digest.
    out['methods'] = [_method_row(image, m) for m in contract['methods']]
    extents = dict(image.mapper.pdata_function_extents(image.pe))
    fragments = BodyIndex(image).chained_fragments
    out['codeWindows'] = []
    for m in out['methods']:
        start=base+m[3]
        if start not in extents: raise RouteRefused(f'pdata={m[3]:#x}')
        out['codeWindows'].append(_window(image,start,extents[start],'complete pdata function extent'))
        for fragment,size in fragments.get(start,()):
            out['codeWindows'].append(_window(image,fragment,fragment+size,'complete chained pdata fragment'))
    start=base+out['methods'][0][3]
    rows=image.mapper.decode_x64_subset(image.pe.bytes_at_va(start,extents[start]-start),start,stop_offset=extents[start]-start)
    header, reads=select_reads(rows,len(plan))
    out['memberCountInstruction']={'rva':int(header['va'],16)-base,'hex':header['bytes'].replace(' ','').upper()}
    owner=image.metadata.types[entry['typeDefinition']]
    setters=image.setter_methods(owner,parameter='typeName',label='skillCustomRootMotionRegenerate')
    if [r[1:] for r in setters] != [r[1:] for r in contract['setterMethods']]:
        raise RouteRefused('setter-types-or-order:review-required')
    out['setterMethods']=setters
    for planrow, read in zip(out['orderedSourceReads'],reads):
        call=read['call']; va=int(call['va'],16); target=int(call['text'].split()[1],16)
        planrow.update(sourceCallsiteRva=va-base,sourceCallHex=call['bytes'].replace(' ','').upper(),sourceTargetRva=target-base)
        planrow['inlineSourceInstructions']=[[int(r['va'],16)-base,r['bytes'].replace(' ','').upper()] for r in read.get('inline',[])]
    # All bool and integer members must share the same concrete primitive.
    for kind in ('bool-byte','int32','enum-int32'):
        targets={r['sourceTargetRva'] for r in out['orderedSourceReads'] if r['kind']==kind}
        if len(targets)!=1: raise RouteRefused(f'primitive-targets={kind}:{sorted(targets)}')
    integer_targets={r['sourceTargetRva'] for r in out['orderedSourceReads'] if r['kind'] in ('int32','enum-int32')}
    if len(integer_targets)!=1: raise RouteRefused('enum-and-int32-primitive-diverge')
    primitives={r['sourceTargetRva']:r['kind'] for r in out['orderedSourceReads'] if r['kind'] in ('bool-byte','int32','raw4')}
    for rva,kind in primitives.items():
        prove_primitive(image,base+rva,kind)
        if base+rva not in extents: raise RouteRefused(f'primitive-pdata={kind}')
        out['codeWindows'].append(_window(image,base+rva,extents[base+rva],f'complete {kind} primitive pdata extent'))
    out['nestedContexts']=[]
    normal=_window(image,int(header['va'],16),int(reads[-1]['call']['va'],16)+5,'reviewed normal-path reads')
    contexts=_nested_contexts(image,normal)
    expected=[c['typeName'] for c in contract['nestedContexts'] if c['typeName']!='UnityEngine.LayerMask']
    if [c['typeName'] for c in contexts]!=expected:
        raise RouteRefused(f'nested-contexts:expected={expected}:actual={[c["typeName"] for c in contexts]}')
    for c in contexts:
        out['nestedContexts'].append({k:c[k] for k in ('instructionRva','instructionHex','usageRawHex','methodSpecIndex','methodSpec','argumentRawHex','typeDefinition','typeName')} | {'cellRva':c['cellVa']-base})
    out['nativeInputs']=inputs
    out['serializedMemberCount']=len(plan)
    out['evidenceBoundary']={
        'exact':'Selected native inputs authenticate the name-resolved dispatcher, 25-member wrapper, complete pdata windows, ordered source calls, inline LayerMask DWORD and Advance(4), setter types and nested generic contexts.',
        'direct':'The normal reader consumes four inherited fields and 21 own fields; member 9 uses the same one-byte primitive as isEnable. Primitive and inline cursor increments are re-proved during regeneration.',
        'structuralOnly':'Stored framing only. Historical reached-source cursors and dependent whole-SkillData/timeline contracts have not been migrated or promoted; runtime movement and provider choice remain separate evidence.'}
    return out


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--regenerate',action='store_true',required=True)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    try:
        result=regenerate(json.loads(CONTRACT_PATH.read_bytes()))
    except (RouteRefused, ValueError, KeyError, StopIteration) as error:
        print(json.dumps({'written':False,'refused':str(error)})); return 1
    if args.write: CONTRACT_PATH.write_bytes((json.dumps(result,indent=2)+'\n').replace('\n','\r\n').encode())
    print(json.dumps({'written':args.write,'memberCount':result['serializedMemberCount']})); return 0


if __name__=='__main__': sys.exit(main())
