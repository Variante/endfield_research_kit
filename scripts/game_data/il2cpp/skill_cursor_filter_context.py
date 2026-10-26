"""Current byte filters for cursor observation, with no terminal-schema claims.

Called by the existing target-set context command. Historical corpus/receipt
validators retain their stricter schema and reject this observation-only context.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import struct
import subprocess

from scripts.common import check_installed_native_inputs
from scripts.game_data.dynamic_stream_area_corpus import DEFAULT_CLI, _verify_build_fingerprints, _verify_fingerprints
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.skill-cursor-filter-context.v1'
CONTRACT_SCHEMA = 'endfield.skill-cursor-capture-target-set.v2'


def require(value, detail):
    if not value:
        raise ValueError('skill-cursor-filter: ' + detail)


def validate_targets(contract):
    require(contract.get('schema') == CONTRACT_SCHEMA and contract.get('status') == 'reviewed-observation-filters', 'contract shape differs')
    rows = contract.get('targets')
    limit = contract.get('captureMaxSourceBytes')
    require(limit == 131072 and isinstance(rows, list) and 0 < len(rows) <= 64, 'target bounds differ')
    for row in rows:
        require(re.fullmatch(r'Data/Json/SkillData/[^/]+[.]json', row.get('virtualPath', '')) and
                type(row.get('length')) is int and 0 < row['length'] <= limit and
                re.fullmatch('[A-F0-9]{64}', row.get('logicalSha256', '')) and
                row.get('role') in ('captureFilter', 'comparisonFilter'), 'invalid target row')
    require([r['virtualPath'] for r in rows] == sorted({r['virtualPath'] for r in rows}) and
            len({r['logicalSha256'] for r in rows}) == len(rows), 'duplicate or unordered filters')
    return rows


def validate_observer(image, declaration):
    require(declaration.get('schema') == 'endfieldCapture.skillDataCursorNative.v1', 'observer schema differs')
    for row in declaration['methods'].values():
        image.validate_method_row([row['index'], row['owner'], row['name'], row['rva']], label='skill-cursor-filter')
        raw = bytes.fromhex(row['prologue'])
        require(image.pe.bytes_at_va(image.pe.image_base + row['rva'], len(raw)) == raw, 'named observer entry differs')
    for row in declaration['readers'].values():
        raw = bytes.fromhex(row['prologue'])
        require(image.pe.bytes_at_va(image.pe.image_base + row['rva'], len(raw)) == raw, 'shared reader entry differs')
    fields = declaration['fieldCallsites']
    inline = declaration['inlineFields']
    require(sorted([r['fieldIndex'] for r in fields] + [r['fieldIndex'] for r in inline]) == list(range(declaration['memberCount'])), 'field coverage differs')
    for rows in (fields, declaration['actionGroupChildCallsites']):
        for row in rows:
            raw = image.pe.bytes_at_va(image.pe.image_base + row['callRva'], 5)
            target = row['callRva'] + 5 + struct.unpack_from('<i', raw, 1)[0] if raw[0] == 0xe8 else None
            require(target == declaration['readers'][row['reader']]['rva'], 'observer call target differs')
    return dict(memberCount=declaration['memberCount'], directFields=len(fields),
                unobservedFields=inline, childCallsites=len(declaration['actionGroupChildCallsites']))


def validate_stream(rows, targets):
    expected = {r['virtualPath']: r for r in targets}
    seen = set()
    for row in rows:
        path = row.get('fileName')
        require(path in expected and path not in seen and row.get('blockTypeValue') == 19, 'unexpected, duplicate or wrong-block stream source')
        seen.add(path)
        raw = base64.b64decode(row['dataBase64'], validate=True)
        wanted = expected[path]
        require(row.get('length') == len(raw) == wanted['length'] and
                hashlib.sha256(raw).hexdigest().upper() == wanted['logicalSha256'], 'current source identity differs: ' + path)
    require(seen == set(expected), 'one or more selected sources are missing')


def audit(contract, outer_path):
    targets = validate_targets(contract)
    outer = json.loads(outer_path.read_bytes())
    require(outer.get('format') == 'animestudio-vfs-boundary-audit', 'outer audit shape differs')
    _verify_fingerprints(outer.get('sourceFingerprints'), 'source')
    _, cli = _verify_build_fingerprints(outer.get('buildFingerprints'), DEFAULT_CLI)
    require(cli['matchesOuterAudit'], 'stream CLI differs from selected outer audit')
    pins = contract['nativeInputs']
    # Resolve the explicitly selected audit build, rather than a module-global game root.
    files = {r['path'].replace('\\', '/').rsplit('/', 1)[-1]: r['path'] for r in outer['buildFingerprints']}
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                        gameassembly=files['GameAssembly.dll'], metadata=files['global-metadata.dat'])
    require(gate.status == 'validated', 'selected native inputs: ' + gate.status + ': ' + gate.detail)
    path = (REPO_ROOT / contract['observerDeclaration']).resolve()
    require(path == REPO_ROOT / 'tools/EndfieldCapture/config/skilldata-cursor-native.json', 'observer owner differs')
    declaration = json.loads(path.read_bytes())
    for key, native in (('GameAssembly.dll', 'GameAssembly.dll'), ('Endfield_Data/il2cpp_data/Metadata/global-metadata.dat', 'global-metadata.dat')):
        require(declaration['nativeInputs'][key]['sha256'].upper() == pins[native].upper(), 'observer selects a different build')
    image = open_native_image(gate.gameassembly, gate.metadata)
    native = validate_observer(image, declaration)
    command = [str(DEFAULT_CLI), 'stream', '--streaming-assets', outer['primaryAssets'],
               '--fallback-assets', outer['fallbackAssets'], '--block-type', 'json-data', '--verify-md5']
    for row in targets:
        command += ['--file-regex', '^' + re.escape(row['virtualPath']) + '$']
    try:
        process = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=120)
    except subprocess.SubprocessError as exc:
        raise ValueError('skill-cursor-filter: target stream did not finish') from exc
    require(process.returncode == 0, 'target stream failed: ' + process.stderr[-1000:])
    validate_stream([json.loads(line) for line in process.stdout.splitlines()], targets)
    _verify_fingerprints(outer.get('sourceFingerprints'), 'source')
    _, final_cli = _verify_build_fingerprints(outer.get('buildFingerprints'), DEFAULT_CLI)
    require(final_cli['matchesOuterAudit'], 'stream CLI changed during selection')
    sources = [dict(sourceLength=r['length'], sourceSha256=r['logicalSha256']) for r in targets]
    binding = ';'.join(f"{r['sourceLength']}:{r['sourceSha256']}" for r in sources).encode('ascii')
    return dict(schema=SCHEMA, status='native-only-observation-filters', observationOnly=True,
                publicationEligible=False, inputSetSha256=outer['inputSetSha256'],
                nativeInputs=pins, nativeValidation=native, captureTargetSet=targets,
                targetSources=sources, targetSetBindingSha256=hashlib.sha256(binding).hexdigest().upper(),
                captureMaxSourceBytes=contract['captureMaxSourceBytes'],
                outerAudit=dict(path=str(outer_path.resolve()), fullAuditPassed=outer['summary']['fullAuditPassed']),
                evidenceBoundary='Current named observer and MD5-verified selected VFS bytes only. This is a sparse logical-path filter set, not the complete ambiguous corpus or a positive-control/terminal selection. Unobserved members remain gaps; historical 48-field receipt/corpus validators cannot publish this context.')
