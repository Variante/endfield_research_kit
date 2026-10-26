"""Authenticate the reviewed CPP character-shadow observation layout.

Selected native bytes establish declarations and static operands only. The
contract does not establish a live call, camera identity or matrix ownership.
Callers select all three native files explicitly; drift produces no rows.


Evidence and admission boundary
-------------------------------
Exact selected GameAssembly/metadata/UnityPlayer checks authenticate native camera
fields, unboxed settings, ABIs, caller and windows; missing/mismatched inputs
withhold declarations. The CPP camera is opaque, not a managed Camera pointer.
This loader does not observe cache updates, fit execution or uploads. Live
admission separately needs original fit results, scoped matrix/quaternion
intermediates and MXCSR, camera/frame identities and byte joins. Generic math
need not be globally hooked when retained parent operands bound the operations.

GetBounds reads a per-camera cache: retain dictionary/fallback identity,
sphere/renderer and camera snapshots at its earlier update, not merely later
GetMatrices getters. Exact caster/receiver replay does not prove cache inputs.
Sphere/renderer-info arrays contain inline values; use unboxed offsets and native
element sizes, keeping element and Transform/Renderer addresses separate.
Fixtures must be independently declared, rather than reproduce observer offsets.
A missing similarly named managed fit call cannot exclude the separate CPP fit.
A direct HGCamera.BeforeCullingCPP getter stack is not a caster-matrix writer.

An upload join needs buffer width, constant offset, Map generation, original
Unmap completion and exact used slice; allocation size is not shader-used range.
An upload caller is not the earlier arithmetic writer. Valid cache snapshots
remain usable without optional entry calls and do not alone justify recapture.
Corrected inline snapshots reproduce sphere unions and first getter matrices;
that does not admit an independent source pose's fit. TransformPoint may differ
from exported-matrix multiplication by a world-coordinate float32 step.
Same-schema actor timeline links lack pose fields: only before/after rows carry
them. Observed orthonormal camera inversion and explicit scalar-SSE float32
boundaries are arithmetic controls, not proof of earlier field writers, source
uploads, image parity or exclusive cache ownership.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage, native_validation_failure
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets

SCHEMA='endfield.character-shadow-cpp-native-contract.v1'
DEFAULT_CONTRACT=CONTRACTS_DIR/'character_shadow_cpp_native.json'


def load_character_shadow_cpp_contract(gameassembly:Path,metadata:Path,player:Path,*,contract_path=DEFAULT_CONTRACT):
    contract_path=Path(contract_path);contract=json.loads(contract_path.read_bytes());inputs=contract['nativeInputs']
    if contract.get('schema')!=SCHEMA or contract.get('status')!='reviewed':
        raise ValueError('characterShadowCpp.contract:unsupported-schema-or-status')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    audit=dict(status=gate.status,detail=gate.detail,evidenceBoundary='conditional',liveCoverageCertified=False)
    if gate.status!='validated':return None,audit
    player=Path(player)
    if not player.is_file():return None,dict(audit,status='missing',detail='Selected UnityPlayer.dll missing')
    with player.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest.upper()!=inputs['unityPlayerSha256'].upper():
        return None,dict(audit,status='mismatched',detail='Selected UnityPlayer.dll hash differs')
    try:
        image=NativeImage(Path(gameassembly),Path(metadata),label='characterShadowCpp')
        pe=image.mapper.PeImage(player)
        for role,row in contract['functions'].items():
            if pe.bytes_at_va(pe.image_base+row['rva'],16).hex()!=row['prefix']:
                raise ValueError('characterShadowCpp.native:entry-prefix='+role)
            for window in row['codeWindows']:
                raw=pe.bytes_at_va(pe.image_base+window['rva'],window['bytes'])
                if hashlib.sha256(raw).hexdigest().upper()!=window['sha256'].upper():
                    raise ValueError('characterShadowCpp.native:code-window='+role)
        caller=contract['caller'];call=pe.bytes_at_va(pe.image_base+caller['callRva'],5)
        if call[:1]!=b'\xe8' or caller['callRva']+5+int.from_bytes(call[1:],'little',signed=True)!=contract['functions']['fit']['rva']:
            raise ValueError('characterShadowCpp.native:fit-caller-target')
        settings=contract['settings'];types=image.named_type_definitions.get(settings['type'],())
        if len(types)!=1:raise ValueError('characterShadowCpp.native:settings-type-identity')
        definition=types[0];offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,definition.index)
        expected={k:v+settings['objectHeaderBytes'] for k,v in settings['unboxedFields'].items()}
        actual={k:offsets.get(k) for k in expected}
        if actual!=expected:raise ValueError(f'characterShadowCpp.native:settings-fields expected={expected!r} actual={actual!r}')
        # The native shared input is a stored value projection. Require the
        # value-type size itself, rather than treating a boxed extent as stride.
        if not definition.bitfield&1:raise ValueError('characterShadowCpp.native:settings-value-type')
        pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
        actual_size=image.pe.u32_at_va(pointer)-settings['objectHeaderBytes']
        if actual_size!=settings['unboxedBytes']:
            raise ValueError(f'characterShadowCpp.native:settings-size expected={settings["unboxedBytes"]} actual={actual_size}')
    except (ValueError,KeyError,IndexError) as error:
        return None,native_validation_failure(error,label='characterShadowCpp',source_path=contract_path)
    return contract,dict(audit,status='validated',detail='Selected static CPP entries, caller and settings layout validated',functions=len(contract['functions']))
