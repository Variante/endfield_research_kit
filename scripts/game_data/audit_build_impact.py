"""Inventory script exposure to selected-build drift without executing builders.

This static audit parses maintained Python, maps imports and literal contract
references, compares reviewed native-input pins with the selected files, and
reports fixed union-tag checks and native-address/hash literals for review.
Matching pins establish build identity only, not validated native semantics.
Dependency reachability means potential impact: an optional fail-closed lane
can be unavailable while its enclosing builder still works. No contract is
repinned, no audited target script is executed, and no generated page data is published.
"""
from __future__ import annotations

if __name__ == '__main__' and not __package__:
    raise SystemExit('Use python -m scripts.game_data.audit_build_impact')

import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.repo_paths import REPO_ROOT

_PIN_NAMES = {
    'gameassemblydll': 'GameAssembly.dll', 'gameassemblysha256': 'GameAssembly.dll',
    'gameassembly': 'GameAssembly.dll', 'globalmetadatadat': 'global-metadata.dat',
    'globalmetadatasha256': 'global-metadata.dat', 'metadatasha256': 'global-metadata.dat',
    'metadata': 'global-metadata.dat', 'unityplayerdll': 'UnityPlayer.dll',
    'unityplayersha256': 'UnityPlayer.dll', 'unityplayer': 'UnityPlayer.dll',
    'aksoundenginesha256': 'AkSoundEngine.dll', 'aksoundenginedll': 'AkSoundEngine.dll',
    'baselibdll': 'baselib.dll',
}
_SHA = re.compile(r'[a-fA-F0-9]{64}\Z')
_SCRIPT_SUFFIXES = {'.py', '.bat', '.ps1', '.cjs', '.mjs', '.sh'}


def selected_inputs() -> dict[str, Any]:
    gate = check_installed_native_inputs()
    result = {'status': gate.status, 'detail': gate.detail, 'files': {}}
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return result
    for name, path in [('GameAssembly.dll', gate.gameassembly), ('global-metadata.dat', gate.metadata),
                       *[(n, gate.gameassembly.parent / n) for n in
                         ('UnityPlayer.dll', 'AkSoundEngine.dll', 'baselib.dll')]]:
        if not path.is_file() and name in ('AkSoundEngine.dll','baselib.dll'):
            path=gate.metadata.parents[2] / 'Plugins' / 'x86_64' / name
        if path.is_file():
            with path.open('rb') as stream:
                result['files'][name] = hashlib.file_digest(stream, 'sha256').hexdigest().upper()
    return result


def native_pins(value: Any, path: str = '$') -> list[dict[str, str]]:
    """Recognize explicit native-file hash keys, including source/sources shapes."""
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            name = _PIN_NAMES.get(re.sub('[^a-z0-9]', '', key.lower()))
            digest = child.get('sha256') if isinstance(child, dict) else child
            if name and isinstance(digest, str) and _SHA.fullmatch(digest):
                result.append({'file': name, 'sha256': digest.upper(), 'path': path+'.'+key})
            result.extend(native_pins(child, path+'.'+key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(native_pins(child, f'{path}[{index}]'))
    return result


def strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def function_facts(tree: ast.Module, filename: str) -> dict[str, Any]:
    """Static top-level calls, including explicit local/relative import aliases."""
    module = filename.removesuffix('.py').replace('\\', '/').replace('/', '.').removesuffix('.__init__')
    package = module.split('.') if filename.endswith('__init__.py') else module.split('.')[:-1]

    def imports(nodes):
        aliases = {}
        for node in nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split('.')[0]
                    aliases[alias.asname or name] = alias.name if alias.asname else name
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = package[:len(package) - node.level + 1]
                    base = '.'.join(parts + ([node.module] if node.module else []))
                else:
                    base = node.module or ''
                for alias in node.names:
                    aliases[alias.asname or alias.name] = base + '.' + alias.name
        return aliases

    functions = {f.name: f for f in tree.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
    global_aliases = imports(tree.body)
    result = {}
    for name, function in functions.items():
        aliases = {
            'check_installed_native_inputs': 'scripts.common.check_installed_native_inputs',
            **global_aliases,
            **{n: module + '.' + n for n in functions},
            **imports(ast.walk(function)),
        }

        def dotted(node):
            if isinstance(node, ast.Name):
                return aliases.get(node.id, node.id)
            if isinstance(node, ast.Attribute):
                owner = dotted(node.value)
                return owner + '.' + node.attr if owner else ''
            return ''

        calls = sorted({dotted(n.func) for n in ast.walk(function) if isinstance(n, ast.Call)} - {''})
        cached = next((d.lineno for d in function.decorator_list
                       if isinstance(d, ast.Call) and dotted(d.func) in ('lru_cache', 'functools.lru_cache')), None)
        result[module + '.' + name] = {'function': name, 'line': cached, 'calls': calls}
    return result


def cached_native_gate_functions(functions: dict[str, Any]) -> list[dict[str, Any]]:
    reverse: dict[str,set[str]]={}
    for caller,row in functions.items():
        for target in row['calls']:reverse.setdefault(target,set()).add(caller)
    seed='scripts.common.check_installed_native_inputs';gated={seed};queue=[seed]
    while queue:
        for caller in reverse.get(queue.pop(),()):
            if caller not in gated:gated.add(caller);queue.append(caller)
    return [{'symbol':name,'function':row['function'],'line':row['line'],'directGate':seed in row['calls']}
            for name,row in sorted(functions.items()) if row['line'] is not None and name in gated]


def python_facts(source: str, filename: str) -> dict[str, Any]:
    out: dict[str, Any] = {'imports': [], 'strings': [], 'fixedTagChecks': [], 'unequalComparisonChains': [],
                           'nativeAddressLiterals': [], 'hex64Literals': [], 'cachedNativeGateFunctions': []}
    try:
        tree = ast.parse(source, filename=filename)
        compile(tree, filename, 'exec', dont_inherit=True)
    except SyntaxError as exc:
        return {**out, 'parseError': {'line': exc.lineno, 'detail': exc.msg}}
    out['functions']=function_facts(tree,filename)
    out['cachedNativeGateFunctions']=cached_native_gate_functions(out['functions'])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out['imports'].extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            out['imports'].append(node.module)
            out['imports'].extend(node.module+'.'+a.name for a in node.names if a.name != '*')
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                out['strings'].append(node.value)
                if _SHA.fullmatch(node.value):
                    out['hex64Literals'].append({'line': node.lineno, 'value': node.value.upper()})
                if re.fullmatch(r'0x[0-9a-fA-F]+', node.value) and 6442450944 < int(node.value,16) < 8589934592:
                    out['nativeAddressLiterals'].append({'line': node.lineno, 'value': node.value})
            elif type(node.value) is int and 6442450944 < node.value < 8589934592:
                out['nativeAddressLiterals'].append({'line': node.lineno, 'value': hex(node.value)})
        elif isinstance(node, ast.Compare):
            if len(node.ops)>1 and any(isinstance(op,ast.NotEq) for op in node.ops):
                out['unequalComparisonChains'].append({'line':node.lineno,'expression':ast.get_source_segment(source,node)})
            left = node.left
            is_tag = (isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant)
                      and left.slice.value == 'tag') or (
                isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute)
                and left.func.attr == 'get' and left.args
                and isinstance(left.args[0], ast.Constant) and left.args[0].value == 'tag')
            if is_tag:
                for item in node.comparators:
                    if isinstance(item, ast.Constant) and type(item.value) is int:
                        out['fixedTagChecks'].append({'line': node.lineno, 'value': item.value,
                                                     'expression': ast.get_source_segment(source, node)})
    return out


def code_windows(value: Any, path: str = '$') -> list[dict[str, Any]]:
    result = []
    if isinstance(value, dict):
        if {'startRva', 'endRva', 'sha256'} <= value.keys():
            def integer(v):
                return int(v,0) if isinstance(v,str) else v
            start,end = integer(value['startRva']),integer(value['endRva'])
            if type(start) is int and type(end) is int and 0 <= start < end and _SHA.fullmatch(str(value['sha256'])):
                result.append({'path':path,'startRva':start,'endRva':end,'sha256':value['sha256'].upper()})
        for key, child in value.items():
            result.extend(code_windows(child,path+'.'+key))
    elif isinstance(value,list):
        for index,child in enumerate(value):
            result.extend(code_windows(child,f'{path}[{index}]'))
    return result


def pin_status(pins: list[dict[str, str]], selected: dict[str, Any]) -> str:
    if not pins:
        return 'no-recognized-native-pins'
    if selected['status'] != NATIVE_EVIDENCE_VALIDATED:
        return 'selected-inputs-unavailable'
    if any(p['file'] in selected['files'] and p['sha256'] != selected['files'][p['file']] for p in pins):
        return 'mismatched'
    if any(p['file'] not in selected['files'] for p in pins):
        return 'missing-selected-file'
    return 'matching-pins-not-semantic-validation'


def fixed_tag_drift(root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join only single-route shape checks to an exact current registry wrapper.

    A current wrapper rank proves the fixed comparison would refuse that rank;
    it does not establish that the rest of this contract can be regenerated.
    Multi-route/local-variable contexts remain review candidates.
    """
    registry=next((r for r in rows if r['path']=='scripts/game_data/contracts/levelscript_union_tags.json'),None)
    if not registry or registry['nativePinStatus']!='matching-pins-not-semantic-validation':
        return []
    catalog=json.loads((root/registry['path']).read_bytes())
    result=[]
    by_path={r['path']:r for r in rows}
    for row in rows:
        checks=row['facts'].get('fixedTagChecks',[])
        if not checks:
            continue
        raw=(root/row['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest().upper()!=row['sha256']:
            continue
        tree=ast.parse(raw,filename=row['path'])
        functions=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_contract']
        candidates=[]
        for dependency in row['dependencies']:
            if not dependency.endswith('.json'):
                continue
            candidate=json.loads((root/dependency).read_bytes())
            route=candidate.get('route') if isinstance(candidate,dict) else None
            if isinstance(route,dict) and route.get('wrapperName') and route.get('family'):
                candidates.append((by_path[dependency],route))
        if len(candidates)!=1:
            continue
        contract,route=candidates[0]
        family={'GetterBase':'PureGetter'}.get(route['family'],route['family'])
        matches=[r for r in catalog.get('families',{}).get(family,[]) if r.get('wrapperName')==route['wrapperName']]
        if len(matches)!=1:
            continue
        current=matches[0]
        for check in checks:
            expression=check['expression']
            if (not any(f.lineno<=check['line']<=f.end_lineno for f in functions)
                    or not re.match(r'''route(?:\[['"]tag['"]\]|\.get\(['"]tag['"]\))\s*!=''',expression)
                    or check['value']==current['tag']):
                continue
            result.append({'source':row['path'],'line':check['line'],'sourceSha256':row['sha256'],
                           'validator':'_contract','check':'fixed-union-tag','contract':contract['path'],
                           'wrapper':route['wrapperName'],'expected':check['value'],'actual':current['tag'],
                           'reviewedMemberCount':route.get('serializedMemberCount'),
                           'selectedMemberCount':current['memberCount']})
    return result


def audit(root: Path, paths: list[str], selected: dict[str, Any], read_window: Any = None,
          previous: dict[str, Any] | None = None):
    previous=previous or {}
    cached={r['path']:r for r in previous.get('files',[])} if previous.get('schema') in ('endfield.script-build-impact.v2','endfield.script-build-impact.v3','endfield.script-build-impact.v4','endfield.script-build-impact.v5') else {}
    paths = sorted(set(paths))
    modules = {p[:-3].replace('/', '.'): p for p in paths if p.endswith('.py')}
    modules.update({k.removesuffix('.__init__'): v for k,v in list(modules.items()) if k.endswith('.__init__')})
    basenames: dict[str, list[str]] = {}
    symbols: dict[str, list[str]] = {}
    for p in paths:
        basenames.setdefault(Path(p).name, []).append(p)
        symbols.setdefault(Path(p).stem, []).append(p)
    rows = []
    for p in paths:
        raw = (root / p).read_bytes()
        digest = hashlib.sha256(raw).hexdigest().upper()
        row: dict[str, Any] = {'path': p, 'sha256': digest, 'suffix': Path(p).suffix}
        old=cached.get(p)
        try:
            text = raw.decode('utf-8-sig')
            if old and old['sha256']==digest and (not p.endswith('.py') or previous.get('schema')=='endfield.script-build-impact.v5'):
                facts=old['facts']
                row['reusedStaticFacts']=True
            elif p.endswith('.py'):
                facts = python_facts(text, p)
            elif p.endswith('.json'):
                try:
                    value = json.loads(text)
                    methods=value.get('methods',[]) if isinstance(value,dict) else []
                    formatter=bool(methods) and all(isinstance(m,list) and len(m)>=3 and
                        isinstance(m[1],str) and m[1].startswith(('Beyond.MemoryPack.','MemoryPack.')) for m in methods)
                    facts = {'strings': list(strings(value)), 'pins': native_pins(value),
                             'codeWindows':code_windows(value),
                             'windowOwner':'GameAssembly.dll' if formatter else 'unresolved',
                             'schema': value.get('schema', value.get('schemaVersion')) if isinstance(value, dict) else None}
                except ValueError as exc:
                    facts = {'strings': [], 'parseError': {'detail': str(exc)}}
            else:
                facts = {'strings': re.findall(r'[\w./\\-]+\.json', text),
                         'imports': re.findall(r'python\s+-m\s+([\w.]+)', text)}
        except UnicodeError as exc:
            facts = {'strings': [], 'parseError': {'detail': str(exc)}}
        if 'strings' in facts:
            facts['literalReferences']=[s for s in facts.pop('strings') if s.endswith('.json') or re.fullmatch(r'[a-z][a-z0-9_]*',s)]
        row['facts'] = facts
        row['dependencies'] = sorted({modules[name] for name in facts.get('imports', []) if name in modules})
        for literal in facts.get('literalReferences', []):
            # Exact file names and exact module stems only. A literal name can
            # be an optional reference, so dependency impact remains potential.
            name = literal.replace('\\', '/').rsplit('/', 1)[-1]
            candidates = basenames.get(name, []) if name.endswith('.json') else symbols.get(literal, [])
            if not name.endswith('.json'):
                candidates = [p for p in candidates if p.endswith('.py')] or candidates
            if len(candidates) == 1 and candidates[0] != p:
                row['dependencies'].append(candidates[0])
        row['dependencies'] = sorted(set(row['dependencies']))
        row['nativePinStatus'] = pin_status(facts.get('pins', []), selected)
        # Older formatter-window contracts have no nativeInputs of their own;
        # their enclosing reader gates the build. Check these exact byte pins
        # only, reusing already-classified nativeInputs for other contracts.
        row['codeWindowStatus'] = 'not-checked'
        if (facts.get('codeWindows') and facts.get('windowOwner')=='GameAssembly.dll'
                and row['nativePinStatus']=='no-recognized-native-pins'
                and selected['status']==NATIVE_EVIDENCE_VALIDATED and read_window):
            failures=[]
            reusable=(old and old['sha256']==digest and previous.get('selectedInputs')==selected
                      and old['codeWindowStatus'] in ('mismatched','matching-bytes-not-semantic-validation'))
            for window in (() if reusable else facts['codeWindows']):
                try:
                    raw=read_window(window['startRva'],window['endRva']-window['startRva'])
                    actual=hashlib.sha256(raw).hexdigest().upper()
                    if actual!=window['sha256']:
                        failures.append({**window,'actualSha256':actual})
                except (ValueError,IndexError) as exc:
                    failures.append({**window,'error':str(exc)})
            if reusable:
                failures=old.get('codeWindowFailures',[])
                row['reusedWindowChecks']=True
            row['codeWindowStatus']='mismatched' if failures else 'matching-bytes-not-semantic-validation'
            row['codeWindowFailures']=failures
        rows.append(row)
    functions={name:info for row in rows for name,info in row['facts'].get('functions',{}).items()}
    cached_gates={info['symbol']:info for info in cached_native_gate_functions(functions)}
    for row in rows:
        if row['suffix']=='.py':
            row['facts']['cachedNativeGateFunctions']=[cached_gates[name] for name in row['facts'].get('functions',{}) if name in cached_gates]
    affected = {r['path']: {r['path']} if r['nativePinStatus'] in
                ('mismatched', 'missing-selected-file', 'selected-inputs-unavailable') or r['codeWindowStatus']=='mismatched' else set() for r in rows}
    changed = True
    while changed:
        changed = False
        for row in rows:
            found = set().union(*(affected[d] for d in row['dependencies']))
            new = found - affected[row['path']]
            if new:
                affected[row['path']].update(new)
                changed = True
    for row in rows:
        row['potentiallyAffectedContracts'] = sorted(affected[row['path']])
    tag_drift=fixed_tag_drift(root,rows)
    return {'schema': 'endfield.script-build-impact.v5', 'selectedInputs': selected,
            'scope': 'Tracked scripts/ files plus root and tools script entry points; explicitly includes untracked maintained additions. Submodule internals and ignored local tests are excluded.',
            'evidenceBoundary': 'Static dependency and pin drift only; matching hashes and absence of findings do not certify functional compatibility. Literal references may be optional; dynamic/generated references may be absent.',
            'counts': {'files': len(rows), 'pythonFiles': sum(r['suffix']=='.py' for r in rows),
                       'jsonFiles': sum(r['suffix']=='.json' for r in rows),
                       'pinStatuses': dict(Counter(r['nativePinStatus'] for r in rows if r['suffix']=='.json')),
                       'potentiallyAffectedScripts': sum(r['suffix']!='.json' and bool(r['potentiallyAffectedContracts']) for r in rows),
                       'fixedTagCheckScripts': sum(bool(r['facts'].get('fixedTagChecks')) for r in rows),
                       'confirmedFixedTagDriftScripts':len({r['source'] for r in tag_drift}),
                       'unequalComparisonChainScripts':sum(bool(r['facts'].get('unequalComparisonChains')) for r in rows),
                       'cachedNativeGateScripts':sum(bool(r['facts'].get('cachedNativeGateFunctions')) for r in rows),
                       'nativeAddressLiteralScripts': sum(bool(r['facts'].get('nativeAddressLiterals')) for r in rows),
                       'codeWindowStatuses':dict(Counter(r['codeWindowStatus'] for r in rows if r['facts'].get('codeWindows'))),
                       'reusedStaticFiles':sum(bool(r.get('reusedStaticFacts')) for r in rows),
                       'reusedWindowFiles':sum(bool(r.get('reusedWindowChecks')) for r in rows),
                       'parseErrors': sum('parseError' in r['facts'] for r in rows)},
            'fixedTagDrift':tag_drift,'files': rows}


def markdown_summary(report: dict[str, Any]) -> str:
    counts=report['counts'];rows=report['files']
    blocked=[r for r in rows if r['nativePinStatus']=='mismatched' or r['codeWindowStatus']=='mismatched']
    families=Counter(Path(r['path']).stem.split('_',1)[0] for r in blocked)
    lines=['# Script game-update impact audit','',report['scope'],'',report['evidenceBoundary'],'',
           f"Checked {counts['pythonFiles']} Python files and {counts['jsonFiles']} JSON sources across {counts['files']} maintained files. Compile/parse errors: {counts['parseErrors']}.",
           '', '| Native input disposition | JSON files |','| --- | ---: |']
    lines += [f'| {key} | {count} |' for key,count in counts['pinStatuses'].items()]
    lines += ['', '| Code-window disposition | Files |','| --- | ---: |']
    lines += [f'| {key} | {count} |' for key,count in counts['codeWindowStatuses'].items()]
    lines += ['',f"Potential dependency exposure: {counts['potentiallyAffectedScripts']} scripts. Optional gated lanes can make this much broader than actual builder failure.",
              '', '| Confirmed stale JSON family (filename prefix) | Files |','| --- | ---: |']
    lines += [f'| {key} | {count} |' for key,count in families.most_common()]
    lines += ['',f"Fixed numeric tag checks occur in {counts['fixedTagCheckScripts']} scripts; these are review candidates, not automatic defects.",
              f"Exact current-wrapper joins confirm stale fixed comparisons in {counts['confirmedFixedTagDriftScripts']} scripts; their other claims still require independent regeneration.",
              f"Chained comparisons containing != occur in {counts['unequalComparisonChainScripts']} scripts; review them for identity gates that require all values to agree.",
              f"Native gates are reachable through explicit top-level calls/imports inside result caches in {counts['cachedNativeGateScripts']} scripts; review their keys and keep current input gates outside cached derivation. Dynamic calls and object methods need separate review.",
              '', '| Embedded native VA candidates | Literals |','| --- | ---: |']
    lines += [f"| {r['path']} | {len(r['facts']['nativeAddressLiterals'])} |" for r in rows if r['facts'].get('nativeAddressLiterals')]
    lines += ['',f"Reused static files: {counts['reusedStaticFiles']}; reused byte-window checks: {counts['reusedWindowFiles']}.",
              '', 'The adjacent JSON contains every audited path, source fingerprint, direct dependencies, potential stale dependencies, explicit pins, byte mismatches and source lines. Matching pins/bytes do not replace an owning native validator. Claims contracts and other pinless sources still need their own checks.','']
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', type=Path, default=REPO_ROOT / 'reports/game_data/script_build_impact.json')
    parser.add_argument('--check-code-windows', action='store_true', help='Check pinless formatter-window contracts against selected native bytes')
    parser.add_argument('--previous-report', type=Path, help='Reuse static facts and byte checks only while their source/native hashes match')
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if not any(output.is_relative_to(REPO_ROOT / folder) for folder in ('reports', 'scratch', 'tmp')):
        parser.error('--output must be under reports/, scratch/ or tmp/')
    tracked = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                                      cwd=REPO_ROOT, text=True).splitlines()
    paths = [p for p in tracked if ((p.startswith('scripts/') and Path(p).suffix in _SCRIPT_SUFFIXES | {'.json'})
             or (('/' not in p or p.startswith('tools/')) and Path(p).suffix in _SCRIPT_SUFFIXES))
             and (REPO_ROOT / p).is_file()]
    selected=selected_inputs()
    read_window=None
    if args.check_code_windows and selected['status']==NATIVE_EVIDENCE_VALIDATED:
        image=None
        def read_window(rva, size):
            nonlocal image
            if image is None:
                gate=check_installed_native_inputs(selected['files']['GameAssembly.dll'],selected['files']['global-metadata.dat'])
                if gate.status!=NATIVE_EVIDENCE_VALIDATED:
                    parser.exit(1,f'selected-native-inputs:{gate.status}:{gate.detail}\n')
                image=open_native_image(gate.gameassembly,gate.metadata)
            return image.pe.bytes_at_va(image.pe.image_base+rva,size)
    previous=json.loads(args.previous_report.read_bytes()) if args.previous_report else None
    result = audit(REPO_ROOT, paths, selected,read_window,previous)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    output.with_suffix('.md').write_text(markdown_summary(result),encoding='utf-8')
    print(json.dumps({'counts': result['counts'], 'report': str(output)}))
    return int(bool(result['counts']['parseErrors']))


if __name__ == '__main__':
    raise SystemExit(main())
