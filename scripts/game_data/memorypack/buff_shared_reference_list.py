"""Selected shared Object list control and instruction representations only.

This validator does not register a stored-action reader or admit any root.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import canonical_json_sha256, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from scripts.game_data.il2cpp.register_rotates import decode_rotate_instructions
from scripts.game_data.il2cpp.reference_list_control import validate_reference_list_control,validate_header_and_loop

LABEL = 'buffSharedReferenceList'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_shared_reference_list_native.json'
SCHEMA = 'endfield.buff-shared-reference-list-native-contract.v2'


def _contract():
    value, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
                                     status='exact-current-build', label=LABEL)
    if (value['methodDefinition'][1:] != ['MemoryPack.Formatters.ListFormatter`1', 'Deserialize']
            or value['classArguments'] != ['object'] or value['methodArguments'] != []
            or value['registeredSharedEntry']['methodDefinitionIndices'] != [value['methodDefinition'][0]]
            or not value['function']['ownedWindows']
            or set(value['headerAndLoopProtocol']['windows'])!={'header','providerAndCount','callback','loopBack','countError'}):
        raise ValueError(LABEL + '.contract-shape')
    return value


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                    metadata: Path | None = None):
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                       gameassembly=gameassembly, metadata=metadata)
    def empty(status, detail):
        return {'status': status, 'detail': detail, 'nativeInputs': pins, 'summary': {},
                'concreteCollectionGrammarProved': False, 'wholeRootAdmitted': False,
                'runtimeExecutionKnown': False}
    if gate.status != 'validated': return empty(gate.status, gate.detail)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return empty('mismatched' if unity.is_file() else 'missing', 'UnityPlayer.dll missing or mismatched')
    image = open_native_image(gate.gameassembly, gate.metadata); base = image.pe.image_base
    definition = contract['methodDefinition']; method = image.metadata.methods[definition[0]]
    if [image.type_name(method.declaring_type), image.metadata.string(method.name_index)] != definition[1:]:
        raise ValueError(LABEL + '.method-definition')
    actual = GenericEntries(image).resolve(definition[0], contract['classArguments'], contract['methodArguments'])
    if canonical_json_sha256(actual) != canonical_json_sha256(contract['registeredSharedEntry']):
        expected=contract['registeredSharedEntry']
        differences=[{'field':key,'expected':str(expected.get(key))[:300],
                      'actual':str(actual.get(key))[:300]} for key in sorted(set(expected)|set(actual))
                     if canonical_json_sha256(expected.get(key))!=canonical_json_sha256(actual.get(key))]
        raise ValueError(LABEL + '.registered-object-entry:' + json.dumps(differences[:8]))
    if actual['pointer'] != base + contract['function']['entryRva']:
        raise ValueError(LABEL + '.entry-pointer')
    directory, size, raw = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(raw, lambda at, n: image.pe.bytes_at_va(base + at, n),
                             table_rva=directory, image_size=size)
    if canonical_json_sha256(unwind.family(contract['function']['entryRva'])) != canonical_json_sha256(contract['unwindFamily']):
        raise ValueError(LABEL + '.complete-unwind-family')
    rows = []
    for window in contract['function']['ownedWindows']:
        data = image.pe.bytes_at_va(base + window['startRva'], window['endRva'] - window['startRva'])
        if data.hex().upper() != window['rawHex'] or hashlib.sha256(data).hexdigest().upper() != window['sha256']:
            raise ValueError(LABEL + '.code-window:' + str(window['startRva']))
        rows.extend(decode_rotate_instructions(image.mapper, data, base + window['startRva']))
    summary = validate_reference_list_control(rows, base, contract['function'], contract['selectedMemoryInstructions'])
    summary['headerAndLoop']=validate_header_and_loop(rows,base,contract['headerAndLoopProtocol'])
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return empty(after.status if after.status != 'validated' else 'mismatched',
                     'native inputs changed during shared-list validation')
    return {'status': 'validated', 'nativeInputs': pins, 'summary': summary,
            'registeredArgument': 'object', 'concreteCollectionGrammarProved': False,
            'wholeRootAdmitted': False, 'runtimeExecutionKnown': False,
            'evidenceBoundary': contract['evidenceBoundary']}
