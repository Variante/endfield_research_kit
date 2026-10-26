"""Observed stereo input, optional input-processing return and circular history."""
from __future__ import annotations
import copy
import math
import struct
from scripts.game_data.wwise_room_input_native import load_contract,validate
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def project(base,c,owners,image,selected_inputs):
    if base['schema']!='endfieldCapture.audioRoomBlendBuild.v1' or len(base['nativeHooks'])!=49:raise ValueError('room input requires complete room blend recipe')
    indexed=validate(c,owners['wwise_voice_pipeline_native'],image,selected_inputs);out=copy.deepcopy(base)
    abis={'roomInputPreparation':'win64.void_integer5_result.v1','roomInputFold':'win64.void_integer4_float2_result.v1','roomDelayCopy':'win64.void_integer4_result.v1','roomDelaySwap':'win64.void_integer3_result.v1'}
    if any(c['selection'][k]!=base['roomBlend']['selection'][k] for k in ('format','capacity','validFrames','prefixBytes')):raise ValueError('room input selected geometry differs')
    if c['selection']['stereoFoldCoefficientBits']!=struct.unpack('<I',struct.pack('<f',math.sqrt(.5)))[0] or any(type(n) is not int or n<4 or n>256 or n%4 for n in c['selection']['blockFrames']):raise ValueError('room input stereo normalization or block extent differs')
    for h in c['hooks']:
        kind=h['sourceKind']
        if h['index']!=len(out['nativeHooks']) or kind!=h['ownerGroup'] or h['abiId']!=abis[kind]:raise ValueError('room input hook order/owner/ABI differs')
        for phase in ('memory','resultMemory'):
            fields={f['name']:f for f in h[phase]}
            mapping={'roomInputPreparation':{'instance':(0,'argument'),'buffer':(1,'argument'),'output':(2,'argument'),'frames':(3,'argumentU32'),'frameOffset':(6,'argumentU32')},
                'roomInputFold':{'buffer':(0,'argument'),'output':(3,'argument'),'frames':(1,'argumentU32'),'frameOffset':(2,'argumentU32'),'centerGainBits':(6,'argumentU32'),'lfeGainBits':(7,'argumentU32')},
                'roomDelayCopy':{'input':(1,'argument'),'output':(2,'argument'),'frames':(3,'argumentU32')},'roomDelaySwap':{'input':(1,'argument'),'output':(1,'argument'),'frames':(2,'argumentU32')}}[kind]
            for name,(arg,field_kind) in mapping.items():
                if fields[name]!=dict(name=name,argIndex=arg,kind=field_kind,offset=0):raise ValueError('room input typed argument field differs')
            prefix=dict(name='prefix',argIndex=2 if kind in ('roomInputPreparation','roomDelayCopy') else 3 if kind=='roomInputFold' else 1,kind='bytes',offset=0,countField='frames',stride=4,maxBytes=16)
            if fields['prefix']!=prefix:raise ValueError('room input output prefix differs')
            if kind in ('roomInputPreparation','roomInputFold'):
                arg=1 if kind=='roomInputPreparation' else 0
                for name,field_kind,offset in [('format','u32',8),('capacity','u16',16),('validFrames','u16',18)]:
                    if fields[name]!=dict(name=name,argIndex=arg,kind=field_kind,offset=offset):raise ValueError('room input descriptor header differs')
                if kind=='roomInputPreparation':
                    for name,layout in [('copyDelayLength','initialCopyDelay'),('swapDelayLength','initialSwapDelay')]:
                        if fields[name]!=dict(name=name,argIndex=0,kind='u32',offset=c['layout'][layout]):raise ValueError('room delay branch snapshot differs')
                    if fields['toneEnabled']!=dict(name='toneEnabled',argIndex=0,kind='u8',offset=c['layout']['toneEnabled'],pointerOffsets=[c['layout']['parameterObject']]) or fields['toneSlotCount']!=dict(name='toneSlotCount',argIndex=0,kind='u8',offset=c['layout']['toneSlotCount']):raise ValueError('room optional tone branch snapshot differs')
            if kind=='roomInputFold':
                if fields['samplePointer']!=dict(name='samplePointer',argIndex=0,kind='pointer',offset=0):raise ValueError('room fold sample pointer differs')
                for plane,offset in [('leftWord',0),('rightWord',c['selection']['capacity']*4)]:
                    for i in range(4):
                        name=plane+str(i)
                        if fields[name]!=dict(name=name,argIndex=0,kind='indexedU32',offset=offset+i*4,pointerOffsets=[0],indexField='frameOffset',requireMemory=dict(name='frames',nonzero=True)):raise ValueError('room fold indexed plane differs')
            elif kind.startswith('roomDelay'):
                for name,field_kind,offset in [('length','u32',c['layout']['ringLength']),('ringPointer','pointer',c['layout']['ringPointer']),('ringIndex','u32',c['layout']['ringIndex'])]:
                    if fields[name]!=dict(name=name,argIndex=0,kind=field_kind,offset=offset):raise ValueError('room circular header differs')
                for i in range(4):
                    name='historyWord'+str(i)
                    if fields[name]!=dict(name=name,argIndex=0,kind='ringU32',offset=i*4,pointerOffsets=[c['layout']['ringPointer']],indexField='ringIndex',lengthField='length',requireMemory=dict(name='frames',nonzero=True)):raise ValueError('room circular history read differs')
                    name='inputWord'+str(i)
                    if fields[name]!=dict(name=name,argIndex=1,kind='u32',offset=i*4,requireMemory=dict(name='frames',nonzero=True)):raise ValueError('room circular incoming sample read differs')
        out['nativeHooks'].append(dict(name=h['name'],sourceKind=kind,module='AkSoundEngine.dll',rva=indexed[kind]['entryRva'],abiId=h['abiId'],required=True,
            memory=copy.deepcopy(h['memory']),resultMemory=copy.deepcopy(h['resultMemory']),readProgram=compile_reads(h['memory']),resultProgram=compile_reads(h['resultMemory'])))
    out.update(schema='endfieldCapture.audioRoomInputBuild.v1',observerProfile='audioRoomInputPhasesV1',roomInput=dict(selection=copy.deepcopy(c['selection']),layout=copy.deepcopy(c['layout']),
        callerReturnRvas={k:[b['returnRva'] for b in c['callBindings'] if b['targetGroup']==k] for k in abis},evidenceBoundary=copy.deepcopy(c['evidenceBoundary'])))
    return out
