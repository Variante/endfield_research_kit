"""Project reviewed render-client caller roles into the playback recorder."""
from __future__ import annotations

import copy
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads

CONTRACT_PATH=CONTRACTS_DIR/'wwise_device_capture_native.json'
SCHEMA='endfield.wwise-device-observer.v1'


def load_contract():
    value,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='reviewedCurrentBuild',label='wwise-device-observer')
    return value


def project(playback,contract,owner,image):
    if playback['schema']!='endfieldCapture.audioPlaybackBuild.v1' or len(playback['nativeHooks'])!=32 or owner['nativeInputs']!=contract['nativeInputs']:
        raise ValueError('device declarations require the current playback recipe and selected owner')
    identity=owner[contract['identityRole']]
    if identity['interface']!='IAudioRenderClient' or identity['getBufferGroup']!=contract['callerGroup']:
        raise ValueError('device interface/caller group differs')
    group=next(g for g in owner['nativeGroups'] if g['key']==contract['callerGroup'])
    sink=next(h for h in playback['nativeHooks'] if h['sourceKind']==contract['callerGroup'])
    if sink['memory'][0]['name']!='renderClient' or sink['memory'][0]['kind']!='pointer':
        raise ValueError('device discovery requires the declared retained-client first field')
    output=copy.deepcopy(playback);output['schema']='endfieldCapture.audioDeviceBuild.v1';output['observerProfile']='audioDevicePhasesV1'
    for i,row in enumerate(contract['hooks'],32):
        if row['index']!=i:raise ValueError('device hook order differs')
        slot=identity[row['slotField']];caller=int(identity[row['callerField']],16)
        if type(slot) is not int or not 0<slot<256 or slot%8:raise ValueError('device virtual slot is not a bounded pointer offset')
        encoded=b'\xff\x50'+bytes([slot])
        if not any(int(w['rva'],16)<=caller and caller+len(encoded)<int(w['rva'],16)+w['bodyLength'] for w in group['windows']):
            raise ValueError('device call/return outside borrowed complete caller')
        if image.bytes_at_va(image.image_base+caller,len(encoded))!=encoded:
            raise ValueError('device virtual call differs from selected caller bytes')
        before=copy.deepcopy(row['memory']);after=copy.deepcopy(row['resultMemory'])
        for field in before+after:
            if 'offsetFromIdentity' in field:field['offset']=identity[field.pop('offsetFromIdentity')]
        if i==32 and [f['name'] for f in before[:2]]!=['getBufferTarget','releaseBufferTarget']:
            raise ValueError('device discovery target reads differ')
        if i==32 and [f['name'] for f in after[:2]]!=['hresultBits','returnedBuffer']:
            raise ValueError('device GetBuffer result reads differ')
        output['nativeHooks'].append(dict(name=row['name'],module='AkSoundEngine.dll',rva=hex(caller+len(encoded)),
            sourceKind='deviceGetBuffer' if i==32 else 'deviceReleaseBuffer',required=True,abiId=row['abiId'],
            hookBinding=contract['bindingKind'],rvaRole='selectedNativeCallerReturnSite',memory=before,resultMemory=after,
            readProgram=compile_reads(before),resultProgram=compile_reads(after)))
    if len(output['nativeHooks'])!=34:raise ValueError('two logical device methods required')
    output['deviceEvidenceBoundary']=contract['evidenceBoundary']
    for key in ('correlationBoundary','bufferBoundary','lifecycleBoundary'):output['device'+key[0].upper()+key[1:]]=contract[key]
    return output
