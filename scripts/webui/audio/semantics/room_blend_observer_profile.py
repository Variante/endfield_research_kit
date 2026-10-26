"""RoomVerb instance and bounded native blend operands, with six stack values."""
from __future__ import annotations
import copy
import struct
from scripts.game_data.wwise_room_blend_native import load_contract,validate
from scripts.game_data.wwise_bus_processing_native import load_contract as load_bus
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def project(mix,c,owners,image,selected_inputs):
    if mix['schema']!='endfieldCapture.audioMixContributionsBuild.v1' or len(mix['nativeHooks'])!=47:raise ValueError('room blend requires complete contribution recipe')
    indexed=validate(c,owners['wwise_voice_pipeline_native'],image,selected_inputs);out=copy.deepcopy(mix)
    for h in c['hooks']:
        if h['index']!=len(out['nativeHooks']):raise ValueError('room blend hook order differs')
        kind=h['sourceKind']
        if kind not in ('roomVerbExecute','roomVerbBlend') or h['ownerGroup']!=kind:raise ValueError('room blend hook owner differs')
        expected_abi='win64.void_integer2_result.v1' if kind=='roomVerbExecute' else 'win64.void_pointer3_float6_u32_result.v1'
        if h['abiId']!=expected_abi:raise ValueError('room blend native ABI differs')
        for phase in ('memory','resultMemory'):
            fields={f['name']:f for f in h[phase]}
            if kind=='roomVerbBlend':
                mapping={'frames':11,'dryPreviousBits':3,'dryTargetBits':6,'wetAPreviousBits':7,'wetATargetBits':8,'wetBPreviousBits':9,'wetBTargetBits':10}
                for name,arg in mapping.items():
                    if fields[name]!=dict(name=name,argIndex=arg,kind='argumentU32',offset=0):raise ValueError('room blend stack field differs')
                for prefix,arg in [('wetAWord',1),('wetBWord',2)]:
                    for i in range(4):
                        if fields[prefix+str(i)]!=dict(name=prefix+str(i),argIndex=arg,kind='u32',offset=i*4,requireMemory=dict(name='frames',nonzero=True)):raise ValueError('room wet prefix geometry differs')
                expected_prefix=dict(name='prefix',argIndex=0,kind='bytes',offset=0,countField='frames',stride=4,maxBytes=16)
            else:
                expected_fields=[dict(name='instance',argIndex=0,kind='argument',offset=0),dict(name='buffer',argIndex=1,kind='argument',offset=0),
                    dict(name='format',argIndex=1,kind='u32',offset=8),dict(name='capacity',argIndex=1,kind='u16',offset=16),dict(name='validFrames',argIndex=1,kind='u16',offset=18),
                    dict(name='samplePointer',argIndex=1,kind='pointer',offset=0)]
                if any(fields[f['name']]!=f for f in expected_fields):raise ValueError('room instance or descriptor geometry differs')
                if fields['parameterObject']!=dict(name='parameterObject',argIndex=0,kind='pointer',offset=c['layout']['parameterObject']):raise ValueError('room parameter object geometry differs')
                expected_prefix=dict(name='prefix',argIndex=1,kind='bytes',offset=0,pointerOffsets=[0],countField='validFrames',stride=4,maxBytes=16)
            if fields['prefix']!=expected_prefix:raise ValueError('room blend output prefix geometry differs')
        out['nativeHooks'].append(dict(name=h['name'],sourceKind=h['sourceKind'],module='AkSoundEngine.dll',rva=indexed[h['ownerGroup']]['entryRva'],abiId=h['abiId'],required=True,
            memory=copy.deepcopy(h['memory']),resultMemory=copy.deepcopy(h['resultMemory']),readProgram=compile_reads(h['memory']),resultProgram=compile_reads(h['resultMemory'])))
    parameter=bytes.fromhex(next(w['instructionHex'] for w in indexed['roomVerbExecute']['instructionWitnesses'] if w['role']=='parameterObject'))
    if parameter[:3]!=bytes.fromhex('488b81') or len(parameter)!=7 or struct.unpack_from('<i',parameter,3)[0]!=c['layout']['parameterObject']:raise ValueError('room parameter field differs from native read')
    selection=c['selection'];base_selection=mix['busProcessingSelection']
    if any(selection[k]!=base_selection[k] for k in ('format','capacity','validFrames')) or selection['format']!=c['stereoDispatch']['format'] or selection['prefixBytes']!=16:raise ValueError('room selected buffer geometry differs')
    if not selection['blendFrameCounts'] or any(type(n) is not int or n<4 or n>selection['validFrames'] or n&(n-1) for n in selection['blendFrameCounts']):raise ValueError('room blend selected counts differ')
    out.update(schema='endfieldCapture.audioRoomBlendBuild.v1',observerProfile='audioRoomBlendPhasesV1',
        roomBlend=dict(selection=copy.deepcopy(c['selection']),layout=copy.deepcopy(c['layout']),callerReturnRvas=[b['returnRva'] for b in c['callBindings']],
            effectClassId='0x00760003',executeRva=indexed['roomVerbExecute']['entryRva'],
            vtableRva=next(b['vtableRva'] for b in load_bus()['effectClassBindings'] if b['classId']=='0x00760003'),evidenceBoundary=copy.deepcopy(c['evidenceBoundary'])))
    return out
