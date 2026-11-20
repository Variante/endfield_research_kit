"""Selected native request storage for observational combat input snapshots."""
from __future__ import annotations

import hashlib
import struct

from scripts.common import check_installed_native_inputs
from scripts.game_data import skill_request_cache_native as cache
from scripts.game_data.il2cpp.native_image import read_reviewed_contract

SCHEMA = 'endfield.battle-input-capture-read-layouts.v1'
REQUEST = 'System.Nullable`1<' + cache.REQUEST + '>'


def derive_read_layouts(selected):
    contract, digest = read_reviewed_contract(cache.CONTRACT_PATH, schema=cache.SCHEMA,
                                            status='reviewed', label='battleInputCapture')
    pins = contract['nativeInputs']
    image = selected.image
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=image.gameassembly, metadata=image.metadata_path)
    if not gate.validated:
        raise ValueError('battleInputCapture.native: '+gate.status+': '+gate.detail)
    # Share the opened image: do not parse the large selected binary a second time.
    proof = cache._validate(image, contract)
    layout = proof['layout']
    fields = {f['id']: f for f in contract['fields']}
    offsets = {name: layout['outerValueOffset'] + fields[cache.REQUEST+'::'+name]['offset'] - layout['objectHeaderBytes']
               for name in ('nextSkillId', 'remainingTime', 'allowToCastNextSkill', 'modifierInstId', 'skillCastInputData')}
    result = dict(schema=SCHEMA, nativeInputs=dict(pins), openGenericOffsetsRead=False,
                  runtimeSelectionObserved=False, atomicSnapshotProved=False,
                  values={REQUEST: dict(byteCount=layout['requestNullableBytes'],
                      hasValueOffset=layout['outerHasValueOffset'], offsets=offsets,
                      inputHasValueOffset=layout['inputHasValueOffset'],
                      inputValueOffset=layout['inputValueOffset'], inputDataBytes=layout['inputDataBytes'])},
                  proof=dict(ownerSchema=cache.SCHEMA, layout=layout,
                             fields=[fields[cache.REQUEST+'::'+name] for name in offsets],
                             boundary='Selected native construction and clear storage; no live cache selection or atomicity.'))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                          gameassembly=image.gameassembly, metadata=image.metadata_path)
    if not after.validated or hashlib.sha256(cache.CONTRACT_PATH.read_bytes()).hexdigest().upper() != digest:
        raise ValueError('battleInputCapture.inputs changed during layout derivation')
    return result


def validate_read_layouts(value):
    """Check retained declaration consistency; does not reopen or re-prove natives."""
    if (value.get('schema') != SCHEMA or any(value.get(k) is not False for k in
        ('openGenericOffsetsRead','runtimeSelectionObserved','atomicSnapshotProved'))
        or set(value.get('values',{})) != {REQUEST}):
        raise ValueError('battleInputCapture.layout boundary differs')
    proof=value['proof'];layout=proof['layout'];source=value['values'][REQUEST]
    if proof.get('ownerSchema') != cache.SCHEMA:
        raise ValueError('battleInputCapture.layout owner differs')
    fields={f['name']:f for f in proof['fields']}
    expected={name:layout['outerValueOffset']+f['offset']-layout['objectHeaderBytes'] for name,f in fields.items()}
    if (source['offsets']!=expected or source['byteCount']!=layout['requestNullableBytes']
        or source['hasValueOffset']!=layout['outerHasValueOffset']
        or source['inputDataBytes']!=layout['inputDataBytes']
        or source['inputHasValueOffset']!=layout['inputHasValueOffset']
        or source['inputValueOffset']!=layout['inputValueOffset']):
        raise ValueError('battleInputCapture.layout retained geometry differs')
    widths={'nextSkillId':8,'remainingTime':4,'allowToCastNextSkill':1,'modifierInstId':8,
            'skillCastInputData':layout['inputNullableBytes']}
    if (set(expected)!=set(widths) or type(source['byteCount'])is not int or not 1<=source['byteCount']<=256
        or any(type(n)is not int or n<=0 or type(expected[k])is not int or expected[k]<0 or expected[k]+n>source['byteCount'] for k,n in widths.items())
        or any(type(source[k])is not int or source[k]<0 for k in ('hasValueOffset','inputHasValueOffset','inputValueOffset','inputDataBytes'))
        or source['hasValueOffset']>=source['byteCount']
        or source['inputHasValueOffset']>=layout['inputNullableBytes']
        or source['inputValueOffset']+source['inputDataBytes']>layout['inputNullableBytes']):
        raise ValueError('battleInputCapture.layout extent outside capture')
    return True


def decode_request(raw: bytes, source):
    """Decode captured bytes only; pointer fields remain opaque identities."""
    if len(raw) != source['byteCount']:
        raise ValueError('battleInputCapture.request byte count differs')
    flag = raw[source['hasValueOffset']]
    if flag not in (0, 1):
        raise ValueError('battleInputCapture.request hasValue is not Boolean')
    if not flag:
        return dict(present=False, atomicSnapshotProved=False)
    offsets = source['offsets']
    allow = raw[offsets['allowToCastNextSkill']]
    nested = offsets['skillCastInputData']
    present = raw[nested+source['inputHasValueOffset']]
    if allow not in (0, 1) or present not in (0, 1):
        raise ValueError('battleInputCapture.request nested flag is not Boolean')
    time_bits = raw[offsets['remainingTime']:offsets['remainingTime']+4]
    return dict(present=True, nextSkillIdPointer=struct.unpack_from('<Q',raw,offsets['nextSkillId'])[0],
                remainingTimeBits=time_bits.hex(), allowToCastNextSkill=bool(allow),
                modifierInstId=struct.unpack_from('<Q',raw,offsets['modifierInstId'])[0],
                inputDataPresent=bool(present), atomicSnapshotProved=False,
                inputDataHex=raw[nested+source['inputValueOffset']:nested+source['inputValueOffset']+source['inputDataBytes']].hex() if present else None)
