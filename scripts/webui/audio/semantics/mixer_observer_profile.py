"""Project stored playback identity and paired output conversion from owned bytes."""
from __future__ import annotations

import copy
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads

SCHEMA = 'endfield.wwise-mixer-observer.v2'
CONTRACT_PATH = CONTRACTS_DIR/'wwise_mixer_capture_native.json'


def load_contract():
    value,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='reviewedCurrentBuild',label='wwise-mixer-observer')
    return value


def instruction(window, offset, encoded, image):
    raw=bytes.fromhex(encoded)
    if type(offset) is not int or not 0<=offset<=window['bodyLength']-len(raw):
        raise ValueError('mixer witness exceeds borrowed complete body')
    if image.bytes_at_va(image.image_base+int(window['rva'],16)+offset,len(raw))!=raw:
        raise ValueError('mixer witness differs from selected bytes')
    return raw


def project(device, contract, owners, image):
    if device['schema']!='endfieldCapture.audioDeviceBuild.v1' or len(device['nativeHooks'])!=34:
        raise ValueError('mixer declarations require the prepared device recipe')
    for owner in owners.values():
        if owner['nativeInputs']!=contract['nativeInputs']:raise ValueError('mixer owner selected inputs differ')
    identity=contract['storedOwnerIdentity']
    blob_hook=next(h for h in device['nativeHooks'] if h.get('sourceKind')==identity['blobProjectionHook'])
    blob_fields={f['name']:f for f in blob_hook['memory']}
    owner=owners[identity['ownerContract']]
    transport=next(t for t in owner['ownerTransports'] if t['key']==identity['ownerTransport'])
    window=transport[identity['endpoint']]['windows'][identity['windowIndex']]
    for key in ('retainedBlob','retainedSource'):
        binding=identity[key]
        raw=instruction(window,binding['bodyOffset'],binding['instructionHex'],image)
        registers=(1,2,8,9)
        if len(raw)!=3 or raw[1]!=0x8b or raw[2]>>6!=3 or ((raw[2]&7)+(8 if raw[0]&1 else 0))!=registers[binding['argumentIndex']]:
            raise ValueError('mixer retained argument register differs')
    for field in identity['fields']:
        raw=instruction(window,field['storeBodyOffset'],field['storeInstructionHex'],image)
        if len(raw)<6 or int.from_bytes(raw[-4:],'little')!=field['offset']:
            raise ValueError('mixer stored owner displacement differs')
        if 'loadInstructionHex' in field:
            load=instruction(window,field['loadBodyOffset'],field['loadInstructionHex'],image)
            source_field=blob_fields[field['sourceBlobField']]
            if source_field['argIndex']!=identity['blobProjectionArgumentIndex'] or source_field['kind']!=field['kind'] or source_field.get('pointerOffsets') or source_field['offset']!=load[-1]:
                raise ValueError('mixer owner load differs from the queued blob field projection')
    for witness in contract['abiWitnesses']:
        group=next(g for g in owners[witness['ownerContract']]['nativeGroups'] if g['key']==witness['ownerGroup'])
        instruction(group['windows'][witness['windowIndex']],witness['bodyOffset'],witness['instructionHex'],image)
    output=copy.deepcopy(device)
    output['schema']='endfieldCapture.audioMixerBuild.v1'
    output['observerProfile']='audioMixerPhasesV1'
    for edit in contract['hookEdits']:
        hook=next(h for h in output['nativeHooks'] if h['sourceKind']==edit['ownerGroup'])
        for key in ('memory','resultMemory','abiId'):
            if key in edit:hook[key]=copy.deepcopy(edit[key])
        for key in ('memory','resultMemory'):
            hook[key].extend(copy.deepcopy(edit.get('append'+key[0].upper()+key[1:],[])))
            hook['resultProgram' if key=='resultMemory' else 'readProgram']=compile_reads(hook[key]) if hook[key] else ''
    sample=next(h for h in output['nativeHooks'] if h['sourceKind']=='contextSourceSampleBuffer')
    primary=next(f for f in sample['resultMemory'] if f['name']=='primaryOwner')
    for declaration in identity['fields']:
        field=next(f for f in sample['resultMemory'] if f['name']==declaration['name'])
        if (field['offset']!=declaration['offset'] or field['kind']!=declaration['kind'] or
                field.get('pointerOffsets')!=[primary['offset']] or field['argIndex']!=primary['argIndex'] or
                field.get('requireMemory')!=dict(name='primaryOwner',nonzero=True)):
            raise ValueError('mixer owner capture reads differ from borrowed storage bindings')
    for row in contract['addedHooks']:
        if row['index']!=len(output['nativeHooks']):raise ValueError('mixer added hook order differs')
        group=next(g for g in owners[row['ownerContract']]['nativeGroups'] if g['key']==row['ownerGroup'])
        output['nativeHooks'].append(dict(name=row['name'],sourceKind=row['ownerGroup'],module='AkSoundEngine.dll',rva=group['entryRva'],required=True,
            abiId=row['abiId'],memory=copy.deepcopy(row['memory']),resultMemory=copy.deepcopy(row['resultMemory']),
            readProgram=compile_reads(row['memory']),resultProgram=compile_reads(row['resultMemory'])))
    output['storedOwnerIdentity']={f['name']:dict(offset=f['offset'],kind=f['kind']) for f in identity['fields']}
    output['mixerEvidenceBoundary']=contract['evidenceBoundary']
    output['mixerSamplingBoundary']=contract['samplingBoundary']
    return output
