"""Authenticate original compiled pair-filter rules on selected native files.

The complete unwind families include cold branches. The scene packet and
indirect call prove the hidden-result ABI. They do not prove a live invocation,
the layer matrix, committed body-core flags or the scene exclusion modes.
"""
from __future__ import annotations

from pathlib import Path

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_body_mode_native import load as load_body_mode
from scripts.game_data.collision_runtime_mesh_native import load_code_layout, validate_code_layout
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory

CONTRACT = CONTRACTS_DIR / 'collision_pair_filter_native.json'
SCHEMA = 'endfield.collision-pair-filter-native.v2'


def validate_program(pe, contract, *, schema=SCHEMA):
    windows = validate_code_layout(pe, contract, schema=schema)
    embedding = contract['layout']['bodyEmbedding']
    if embedding['scb']+embedding['core']+embedding['coreFlags'] != embedding['publicFlags']:
        raise ValueError('pair-filter core/public committed flag coordinates differ')
    table, size, raw = read_exception_directory(pe)
    index = UnwindChainIndex(raw, lambda at, n: pe.bytes_at_va(pe.image_base+at, n),
                             table_rva=table, image_size=size)
    for family in contract['codeFamilies']:
        ranges = [row['runtimeTriple'] for row in index.family(family['rva'])['ranges']]
        if ranges != family['runtimeRanges']:
            raise ValueError('pair-filter complete unwind family differs:'+family['role'])
        recorded = sorted((w['rva'], w['rva']+w['bytes']) for w, _ in windows.values()
                          if w['role'] == family['role'] or w['role'].startswith(family['role']+'_cold_'))
        if recorded != sorted((start, end) for start, end, _ in ranges):
            raise ValueError('pair-filter family has missing/extra code ranges:'+family['role'])
    for row in contract['ruleOperands']:
        raw = windows[row['role']][1]
        at, prefix, width = row['offset'], bytes.fromhex(row['prefix']), row['width']
        if width not in (1, 2, 4) or not prefix or at < 0 or raw[at:at+len(prefix)] != prefix:
            raise ValueError('pair-filter rule instruction differs:'+row['field'])
        start = at+len(prefix)
        if start+width > len(raw):
            raise ValueError('pair-filter clipped rule operand:'+row['field'])
        value = int.from_bytes(raw[start:start+width], 'little', signed=row['signed'])
        if row['invert32']:
            value = ~value & 0xffffffff
        if value != contract['rules'][row['field']]:
            raise ValueError(f"pair-filter rule operand:{row['field']}:expected={contract['rules'][row['field']]},actual={value}")


def capture_declarations(pe, contract):
    """Emit only the reviewed entry ABI; runtime contains no certification path."""
    validate_program(pe, contract)
    expected = ((77,'pair_prefilter',('pointer',)*4+('u32','pointer','bool'),'pointer'),
        (78,'shader',('pointer','u32','pointer','u32','pointer','pointer','pointer','u32'),'pointer'),
        (79,'layer_exclusion',('pointer','i32','i32'),'bool'),
        (80,'object_exclusion',('pointer',)*3,'bool'),
        (83,'shader_dispatch',('pointer',)*4+('u32','bool'),'void'))
    actual = tuple((h['kind'],h['windowRole'],tuple(h['abi']['arguments']),h['abi']['returnMode']) for h in contract['hooks'])
    if actual != expected:
        raise ValueError('pair-filter compiled hook order/ABI differs')
    bounds = dict(maxPairs=(1,8192),maxDispatches=(1,8192),maxShaders=(1,8192),maxLayerChecks=(1,16384),
        maxObjectChecks=(1,16384),maxPolicies=(1,4096),maxOwners=(1,32768),
        sampleEvery=(1,128),initialSamples=(1,256),maxIgnoreKeys=(1,24))
    if set(contract['limits']) != set(bounds) or any(type(contract['limits'][k]) is not int or not lo<=contract['limits'][k]<=hi for k,(lo,hi) in bounds.items()):
        raise ValueError('pair-filter unsafe capture limits')
    if contract['representation'] != dict(sceneOffsetBase='internal_scene',packetBytes=48,coreBytes=64,
        policyBytes=96,matrixBytes=128,ownerKind=82,policyKind=81):
        raise ValueError('pair-filter compiled frame/base representation differs')
    windows = {w['role']:w for w in contract['codeWindows']}
    hooks = []
    for hook in contract['hooks']:
        window = windows[hook['windowRole']];entry = bytes.fromhex(hook['entryHex'])
        if not 5<=len(entry)<=32 or pe.bytes_at_va(pe.image_base+window['rva'],len(entry)) != entry:
            raise ValueError('pair-filter hook entry differs:'+hook['role'])
        hooks.append({**hook,'module':'unityPlayer','rva':window['rva'],'expectedBytes':entry.hex()})
    return dict(contract=contract,hooks=hooks,pins=[dict(module='unityPlayer',rva=w['rva'],
        expectedBytes=pe.bytes_at_va(pe.image_base+w['rva'],w['bytes']).hex()) for w in contract['codeWindows']])


def load(*, gameassembly, metadata, unityplayer):
    contract, gate = load_code_layout(gameassembly=Path(gameassembly), metadata=Path(metadata),
        unityplayer=Path(unityplayer), contract_path=CONTRACT, schema=SCHEMA,
        validator='collision_pair_filter_native', validate=validate_program)
    if contract is None:
        return None, gate
    try:
        mode, mode_gate = load_body_mode(gameassembly=gameassembly, metadata=metadata, unityplayer=unityplayer)
        gate = {**gate, 'bodyModeGate':mode_gate}
        if mode is None:
            return None, {**gate, 'status':mode_gate['status'], 'detail':'named body-mode gate:'+mode_gate['status']}
        getter = next(w for w in mode['codeWindows'] if w['role'] == 'typed_dynamic_flags')
        committed = next(w for w in contract['codeWindows'] if w['role'] == 'public_committed_flags')
        if (mode['nativeInputs'] != contract['nativeInputs'] or
                mode['layout']['mode']['mask'] != contract['layout']['bodyEmbedding']['modeMask'] or
                not getter['rva'] <= committed['rva'] < committed['rva']+committed['bytes'] <= getter['rva']+getter['bytes']):
            raise ValueError('named body-mode input/mask/typed-getter containment differs')
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, StopIteration) as error:
        return None, {**gate, 'status':'failed', 'diagnostics':[dict(check='pair_filter_body_mode',
            detail=str(error)[:1200])]}
    return contract, gate


def evaluate_shader(data0, data1, attribute0, attribute1, *, rules,
                    layer_excluded=None, object_excluded=None):
    """Evaluate supplied operands conditionally; never turn samples into pairs.

    None retains an unavailable matrix/list decision. A tagged or null key
    bypasses the list lookup in the original helper. Excluded paths leave the
    caller's pair-flags output unchanged, represented here by None.
    """
    for data in (data0, data1):
        if len(data) != 4 or any(type(word) is not int or not 0 <= word <= 0xffffffff for word in data):
            raise ValueError('pair-filter requires four u32 filter words')
    if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in (attribute0, attribute1)):
        raise ValueError('pair-filter attribute u32 bound')
    if any(value is not None and type(value) is not bool for value in (layer_excluded, object_excluded)):
        raise ValueError('pair-filter external decisions must be bool or unavailable')
    layer_mask = (1 << rules['layerLowBits'])-1
    layers = [data[rules['layerWord']] & layer_mask for data in (data0, data1)]
    if any(layer >= rules['layerLimit'] for layer in layers):
        layer_excluded = rules['invalidLayerExclusion']
    keys = [(data[rules['keyLowWord']] | data[rules['keyHighWord']] << 32) for data in (data0, data1)]
    if any(not key or key & rules['tagMask'] for key in keys):
        object_excluded = False
    policies = [data[rules['policyWord']] for data in (data0, data1)]
    forced = bool((policies[0] | policies[1]) & rules['forcedExclusionMask'])
    both = all(word & rules['bothExclusionMask'] for word in policies)
    exclusions = dict(forcedShape=forced, bothShapes=both, layer=layer_excluded, object=object_excluded)
    missing = [name for name in ('layer', 'object') if exclusions[name] is None]
    if any(value is True for value in exclusions.values()):
        result, flags = rules['resultExcluded'], None
    elif missing:
        result, flags = None, None
    else:
        result = rules['resultDefault']
        flags = (data0[rules['pairFlagWord']] | data1[rules['pairFlagWord']]) >> rules['pairFlagShift']
        flags &= (1 << rules['pairFlagWidth'])-1
        flags |= rules['triggerPairFlags'] if (attribute0 | attribute1) & rules['triggerAttributeMask'] else rules['defaultPairFlags']
        a, b = (word & ((1 << rules['notificationLowBits'])-1) for word in policies)
        if ((a >> rules['notificationShift'] & b) | (b >> rules['notificationShift'] & a)) & ~rules['notificationClearMask']:
            flags |= rules['notificationPairFlags']
        if (data0[rules['pairFlagWord']] | data1[rules['pairFlagWord']]) & rules['modifierWordMask']:
            flags |= rules['modifierPairFlags']
    return dict(status='conditional_rule_result' if result is not None else 'unresolved_operands',
        result=result, pairFlags=flags, exclusions=exclusions, missingOperands=missing,
        boundary='Supplied operands through authenticated compiled shader rules; no live pair execution, coexistence, upstream eligibility or solver/contact claim.')
