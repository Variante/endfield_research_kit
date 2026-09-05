"""Fail-closed selected-build marker2 anonymous four-byte read evidence."""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.game_data import streaming_native as base
from scripts.game_data import streaming_marker17_native as dependency

SCHEMA = 'endfield.streaming-marker2-native-contract.v1'
DEFAULT_CONTRACT = Path(__file__).with_name('streaming_marker2_native.json')
CONTRACT_SHA256 = 'C3381F058BFBCB1AF9019FDC1C53B066EBC8CFC1138E38CDF1A16B2B1F2C828A'
DEPENDENCY_SHA256 = '34E915707F363B55F572D867C1CC3C1B28A76D66D132EB0E212377A730DD2891'
BASE_SHA256 = '436F51D0C6C0BF0009D2EBF439C8BEC1A13E94404E983E5ADD0E09A604A82E60'
EXPECTED_INPUTS = {
    'gameAssemblySha256':'C24495E51B406F03B03890C4788EE618AE022C991405BE5D5B8B787CB775AE89',
    'metadataSha256':'0076743397ACADF03D3B0064343A963C7C88863B8160526D397E4B3EFB96F02E',
    'unityPlayerSha256':'BEE7BE52370ADDDD67BA61E4937CA51B7F272656841D187E95E505496DA798D1',
}
EXPECTED_RANGES = {
    'selector6Slot1WholeCountConsumer':(0xE3B9A0,229),
    'selector6FullCountKeyLiteral':(0x1AA8188,12),
    'selector6Slot1Assignment':(0x383777,54),
    'slot1DispatcherCompleteHotBodySupersedes220BFragment':(0x6DD80,276),
    'slot1DispatcherColdIndirectBranch':(0xEB400C,11),
    'marker2Slot1SelectedEntryWholeBody':(0x1BC230,61),
}
BASE_ROLES = sorted([
    'defaultConstructorContextBasePrefix','registrationNativeFunctionVtableAddress',
    'descriptorConstructor','publishTenCallbacks','callbackAssignment','inlineCallbackMove',
    'callbackReset','inlineCallbackCloneLeaf','inlineCallbackMoveLeaf','inlineCallbackVtable',
    'marker2Slot1DispatchEntry','slot1RowField3ContextScope','parallelScopeCallbackBridgeA',
    'rootMarkerRecordAllocator','rootMarkerByteCopy','record32GrowInsert','record32RelocateLeaf',
    'record32Publish','streamingField2RowConsumer',
    'keyIndexLookupWrapper','keyIndexMapInit','keyIndexMapResize','keyIndexMapAllocateEmptySlots',
    'keyIndexMapRehashPreservingRows','keyIndexMapInsert','keyIndexMapInsertThunk',
    'keyIndexMapFind','keyIndexMapEndIterator','keyIndexMapIteratorEquality','keyIndexMapInitialEmptySlot',
])
PROFILE = {
    'family':'streaming','rootMarker':2,'rawSelector':6,'key':[9,2,0],
    'packedKey':0x09020000,'marker':2,'slot':1,'readWidth':4,
    'projection':'anonymous-u32','allowedWordValues':'all-u32-bit-patterns',
    'keyMultiplicityPolicy':'unique in complete nested key vector',
    'markerBinding':'independent authenticated same-element join; native does not inspect marker2',
    'contextBinding':'conditional default slot1 callback with certified second-root row.field3 at context+0x80; paired-root witness required',
    'extentStatus':'read-window-only; no serialized sizeof or native EOF proof',
    'runtimeReceipt':'unresolved','targetOwnedBytes':0,'evidenceLevel':'structural-only',
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def _validate_ranges(image: bytes, rows: list[dict[str, Any]], expected: dict[str, tuple[int,int]]) -> list[dict[str, Any]]:
    failures=[]
    def require(gate,wanted,actual):
        if wanted!=actual:failures.append(dict(gate=gate,expected=wanted,actual=actual))
    require('range_role_catalog',sorted(expected),sorted(r.get('role','') for r in rows))
    require('range_unique_rva_size',len(rows),len({(r.get('rva'),r.get('size')) for r in rows}))
    for row in rows:
        role=str(row.get('role','unknown'))
        try:
            rva,size=row['rva'],row['size']
            if type(rva) is not int or type(size) is not int:raise ValueError('RVA and size must be integers, not bool')
            require(role+'.identity',expected.get(role),(rva,size))
            offset,body=base._bounded_pe_range(image,rva,size)
            require(role+'.file_offset',row['fileOffset'],offset)
            require(role+'.body_sha256',row['bodySha256'],sha256(body))
            entry=bytes.fromhex(row['entryBytesHex'])
            if not entry or len(entry)>size:raise ValueError('entry bytes must be nonempty and fit selected span')
            require(role+'.entry_bytes',entry.hex().upper(),body[:len(entry)].hex().upper())
        except (KeyError,TypeError,ValueError) as exc:
            failures.append(dict(gate=role+'.bounded_range',expected='positive contiguous mapped PE span',actual=str(exc),
                                 rva=row.get('rva'),size=row.get('size'),fileOffset=row.get('fileOffset')))
    return failures

def validate_marker2_native_contract(*, game_root: Path, contract_path: Path=DEFAULT_CONTRACT) -> dict[str,Any]:
    failures=[]
    result=dict(status='validation_failed',profile=None,consumerReview=None,evidenceBoundary=None,validationFailures=failures)
    def require(gate,wanted,actual):
        if wanted!=actual:failures.append(dict(gate=gate,expected=wanted,actual=actual))
    try:
        raw=Path(contract_path).read_bytes()
        result['contractSha256']=sha256(raw)
        require('contract_sha256',CONTRACT_SHA256,sha256(raw))
        if failures:return result
        doc=json.loads(raw)
        require('schema',SCHEMA,doc.get('schema'))
        require('contract_status','validated-conditional-static',doc.get('status'))
        require('native_inputs',EXPECTED_INPUTS,doc.get('nativeInputs'))
        require('profile',PROFILE,doc.get('profile'))
        require('dependency_sha256',DEPENDENCY_SHA256,doc['dependency']['sha256'])
        require('dependency_schema','endfield.streaming-marker17-native-contract.v2',doc['dependency']['schema'])
        require('dependency_roles',[],doc['dependency']['requiredUnityPlayerRoles'])
        require('dependency_registration',{'selector':6,'reusedEvidence':['descriptorConstructorSpan','publicationSpan']},doc['dependency']['registration'])
        require('base_sha256',BASE_SHA256,doc['baseContract']['sha256'])
        require('base_schema','endfield.streaming-field2-native-contract.v8',doc['baseContract']['schema'])
        require('base_roles',BASE_ROLES,doc['baseContract']['requiredUnityPlayerRoles'])
        depraw=dependency.DEFAULT_CONTRACT.read_bytes();baseraw=base.DEFAULT_CONTRACT.read_bytes()
        require('installed_dependency_contract_sha256',DEPENDENCY_SHA256,sha256(depraw))
        require('installed_base_contract_sha256',BASE_SHA256,sha256(baseraw))
        if failures:return result
        depdoc=json.loads(depraw);basedoc=json.loads(baseraw)
        role_list=[r['role'] for r in basedoc['unityPlayerRanges']]
        require('base_role_catalog_unique',len(role_list),len(set(role_list)))
        require('base_required_roles_missing',[],sorted(set(BASE_ROLES)-set(role_list)))
        selected=[r for r in depdoc['selectedDefaultSlot3'] if r.get('selector')==6]
        require('selector6_registration_count',1,len(selected))
        if len(selected)==1:
            require('selector6_registration_evidence_missing',[],sorted(set(doc['dependency']['registration']['reusedEvidence'])-selected[0].keys()))
        if failures:return result
        gate=dependency.validate_marker17_native_contract(game_root=Path(game_root))
        require('dependency_native_gate','validated',gate.get('status'))
        require('dependency_native_contract_sha256',DEPENDENCY_SHA256,gate.get('contractSha256'))
        require('dependency_native_inputs',EXPECTED_INPUTS,gate.get('nativeInputs'))
        if failures:
            result['dependencyValidationFailures']=gate.get('validationFailures',[])[:5]
            return result
        image=(Path(game_root).parent/'UnityPlayer.dll').read_bytes()
        require('unity_image_read_sha256',EXPECTED_INPUTS['unityPlayerSha256'],sha256(image))
        if failures:return result
        failures.extend(_validate_ranges(image,doc['unityPlayerRanges'],EXPECTED_RANGES))
        for role in ('selector6FullCountKeyLiteral',):
            rva,size=EXPECTED_RANGES[role]
            try:
                _,literal=base._bounded_pe_range(image,rva,size)
                require(role+'.exact_key',struct.pack('<3I',9,2,0).hex().upper(),literal.hex().upper())
            except ValueError as exc:
                failures.append(dict(gate=role+'.key_range',expected='bounded12-byte key',actual=str(exc)))
        if not failures:
            result.update(status='validated',profile=doc['profile'],consumerReview=doc['consumerReview'],
                evidenceBoundary=doc['evidenceBoundary'],nativeInputs=dict(EXPECTED_INPUTS),
                nativeMappingId=doc['nativeMappingId'],dependencyContractSha256=DEPENDENCY_SHA256,baseContractSha256=BASE_SHA256)
    except (OSError,UnicodeError,json.JSONDecodeError,KeyError,TypeError,ValueError,struct.error) as exc:
        failures.append(dict(gate='marker2_contract_inputs',expected='readable complete pinned evidence',actual=f'{type(exc).__name__}: {exc}'))
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--game-root',type=Path,required=True)
    parser.add_argument('--contract',type=Path,default=DEFAULT_CONTRACT)
    args=parser.parse_args()
    print(json.dumps(validate_marker2_native_contract(game_root=args.game_root,contract_path=args.contract),indent=2))
