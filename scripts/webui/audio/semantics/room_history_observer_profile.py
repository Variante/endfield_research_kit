"""Live expanded tone matrices and paired diffusion history in registered RoomVerb."""
from __future__ import annotations
import copy
from scripts.game_data.wwise_room_history_native import load_contract,validate
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def project(base,c,owners,image,selected_inputs):
    if base['schema']!='endfieldCapture.audioRoomInputBuild.v1' or len(base['nativeHooks'])!=53:raise ValueError('room history requires complete input recipe')
    indexed=validate(c,owners['wwise_voice_pipeline_native'],image,selected_inputs);out=copy.deepcopy(base)
    if c['selection']!=dict(blockFrames=base.get('roomInput',{}).get('selection',{}).get('blockFrames',[64,128,256]),prefixWords=4,matrixWords=32):raise ValueError('room history operand selection differs')
    abis={'roomToneKernel':'win64.void_integer5_result.v1','roomDiffusionKernel':'win64.void_integer3_result.v1'}
    for h in c['hooks']:
        k=h['sourceKind']
        if h['index']!=len(out['nativeHooks']) or k!=h['ownerGroup'] or h['abiId']!=abis[k]:raise ValueError('room history hook order/owner/ABI differs')
        for phase in ('memory','resultMemory'):
            if len(h[phase])!=(13 if k=='roomToneKernel' else 19):raise ValueError('room history field count differs')
            fields={f['name']:f for f in h[phase]}
            args={'frames':(1,'argumentU32'),'coefficientPointer':(3,'argument'),'historyPointer':(6,'argument')} if k=='roomToneKernel' else {'frames':(2,'argumentU32'),'input':(1,'argument')}
            for name,(arg,kind) in args.items():
                if fields[name]!=dict(name=name,argIndex=arg,kind=kind,offset=0):raise ValueError('room history typed argument differs')
            if k=='roomToneKernel':
                if fields['samplePointer']!=dict(name='samplePointer',argIndex=0,kind='pointer',offset=0) or fields['coefficientMatrix']!=dict(name='coefficientMatrix',argIndex=3,kind='bytes',offset=0,countField='frames',stride=4,maxBytes=128):raise ValueError('room tone matrix extent or source differs')
                for i in range(4):
                    if fields['historyWord'+str(i)]!=dict(name='historyWord'+str(i),argIndex=6,kind='u32',offset=i*4) or fields['sampleWord'+str(i)]!=dict(name='sampleWord'+str(i),argIndex=0,kind='u32',offset=i*4,pointerOffsets=[0],requireMemory=dict(name='frames',nonzero=True)):raise ValueError('room tone sample/history operand differs')
            else:
                for name,kind,layout in [('length','u32','diffusionLength'),('ringPointer','pointer','diffusionRing'),('ringIndex','u32','diffusionIndex'),('gainBits','u32','diffusionGain')]:
                    if fields[name]!=dict(name=name,argIndex=0,kind=kind,offset=c['layout'][layout]):raise ValueError('room diffusion header differs')
                for i in range(8):
                    if fields['historyWord'+str(i)]!=dict(name='historyWord'+str(i),argIndex=0,kind='ringPairU32',offset=i*4,pointerOffsets=[c['layout']['diffusionRing']],indexField='ringIndex',lengthField='length',requireMemory=dict(name='frames',nonzero=True)):raise ValueError('room paired history read differs')
                for i in range(4):
                    if fields['inputWord'+str(i)]!=dict(name='inputWord'+str(i),argIndex=1,kind='u32',offset=i*4,requireMemory=dict(name='frames',nonzero=True)):raise ValueError('room diffusion input differs')
                if fields['prefix']!=dict(name='prefix',argIndex=1,kind='bytes',offset=0,countField='frames',stride=4,maxBytes=16):raise ValueError('room diffusion output differs')
        out['nativeHooks'].append(dict(name=h['name'],sourceKind=k,module='AkSoundEngine.dll',rva=indexed[k]['entryRva'],abiId=h['abiId'],required=True,memory=copy.deepcopy(h['memory']),resultMemory=copy.deepcopy(h['resultMemory']),readProgram=compile_reads(h['memory']),resultProgram=compile_reads(h['resultMemory'])))
    out.update(schema='endfieldCapture.audioRoomHistoryBuild.v1',observerProfile='audioRoomHistoryPhasesV1',roomHistory=dict(selection=copy.deepcopy(c['selection']),layout=copy.deepcopy(c['layout']),callerReturnRvas={k:[b['returnRva'] for b in c['callBindings'] if b['targetGroup']==k] for k in abis},callerPurposeByReturnRva={b['returnRva']:b['role'] for b in c['callBindings'] if b['targetGroup'] in abis},evidenceBoundary=copy.deepcopy(c['evidenceBoundary'])))
    return out
