"""Original early taps, four-ring late feedback and final wet damping."""
from __future__ import annotations
import copy
from scripts.game_data.wwise_room_wet_native import load_contract,validate
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def expected_reads(kind,l,s):
    def f(name,arg,kind,offset=0,**kw):return dict(name=name,argIndex=arg,kind=kind,offset=offset,**kw)
    if kind=='roomFdnKernel':
        fields=[f('frames',3,'argumentU32')]
        for j in range(4):
            fields.extend(f(name+str(j),0,t,offset) for name,t,offset in [('length','u32',j*l['ringHeaderStride']),('ringPointer','pointer',j*l['ringHeaderStride']+l['ringPointer']),('ringIndex','u32',j*l['ringHeaderStride']+l['ringIndex']),('filterHistory','u32',l['fdnFilterHistory']+j*l['fdnFilterStride']),('b0Word','u32',l['fdnB0']+j*l['fdnFilterStride']),('a1Word','u32',l['fdnA1']+j*l['fdnFilterStride'])])
            fields.extend(f('ring'+str(j)+'Word'+str(k),0,'ringU32',k*4,pointerOffsets=[j*l['ringHeaderStride']+l['ringPointer']],indexField='ringIndex'+str(j),lengthField='length'+str(j),requireMemory=dict(name='frames',nonzero=True)) for k in range(4))
        fields.extend(f('inputWord'+str(j),1,'u32',j*4) for j in range(4));fields.append(f('prefix',2,'bytes',countField='frames',stride=4,maxBytes=16));return fields
    if kind=='roomWetDamping':
        return [f('frames',2,'argumentU32'),f('gainBits',3,'argumentU32'),f('previousInput',0,'u32'),f('previousOutput',0,'u32',4),f('poleBits',0,'u32',8)]+[f('inputWord'+str(j),1,'u32',j*4) for j in range(4)]+[f('prefix',1,'bytes',countField='frames',stride=4,maxBytes=16)]
    return [f('frames',6,'argumentU32'),f('length',0,'u32'),f('ringPointer',0,'pointer',l['ringPointer']),f('ringIndex',0,'u32',l['ringIndex']),f('leftCount',0,'u16',l['earlyLeftCount']),f('rightCount',0,'u16',l['earlyRightCount'])]+[f(label+str(j),arg,'u32',j*4) for label,arg in [('inputWord',1),('leftWord',2),('rightWord',3)] for j in range(4)]+[f('tapProjection',0,'tapHistoryBytes',l['earlyLeftCoefficients'],projectionOffsets=[l['earlyLeftIndices'],l['earlyLeftCount']],maxTaps=s['maxTaps'],prefixWords=s['prefixWords'],countField='frames')]


def project(base,c,owners,image,selected_inputs):
    if base['schema']!='endfieldCapture.audioRoomHistoryBuild.v1' or len(base['nativeHooks'])!=55:raise ValueError('room wet requires complete history recipe')
    indexed=validate(c,owners['wwise_voice_pipeline_native'],image,selected_inputs);out=copy.deepcopy(base)
    l=c['layout'];s=c['selection']
    if s['prefixWords']!=4 or s['maxTaps']!=64 or s['maximumProjectionBytes']!=32+2*s['maxTaps']*32 or s['blockFrames']!=base['roomHistory']['selection']['blockFrames']:raise ValueError('room wet selected extent differs')
    root_fields=[dict(name=name,argIndex=0,kind=kind,offset=l[name]) for name,kind in [('fdnArray','pointer'),('fdnCount','u32'),('earlyObject','pointer'),('earlyEnabled','u8')]]
    if c['rootReads']!=root_fields:raise ValueError('room wet original instance reads differ')
    for h in out['nativeHooks']:
        if h['sourceKind']=='roomVerbExecute':
            for phase,program in [('memory','readProgram'),('resultMemory','resultProgram')]:
                h[phase].extend(copy.deepcopy(c['rootReads']));h[program]=compile_reads(h[phase])
    abis={'roomFdnKernel':'win64.void_integer4_result.v1','roomWetDamping':'win64.void_integer3_float1_result.v1','roomEarlyReflectionKernel':'win64.void_pointer4_u32_result.v1'}
    for h in c['hooks']:
        k=h['sourceKind']
        if h['index']!=len(out['nativeHooks']) or h['ownerGroup']!=k or h['abiId']!=abis[k]:raise ValueError('room wet hook order/owner/ABI differs')
        if h['memory']!=expected_reads(k,l,s) or h['resultMemory']!=expected_reads(k,l,s):raise ValueError('room wet required original read geometry differs: '+k)
        out['nativeHooks'].append(dict(name=h['name'],sourceKind=k,module='AkSoundEngine.dll',rva=indexed[k]['entryRva'],abiId=h['abiId'],required=True,memory=copy.deepcopy(h['memory']),resultMemory=copy.deepcopy(h['resultMemory']),readProgram=compile_reads(h['memory']),resultProgram=compile_reads(h['resultMemory'])))
    out.update(schema='endfieldCapture.audioRoomWetBuild.v1',observerProfile='audioRoomWetPhasesV1',roomWet=dict(selection=copy.deepcopy(c['selection']),layout=copy.deepcopy(c['layout']),callerReturnRvas={k:[b['returnRva'] for b in c['callBindings'] if b['targetGroup']==k] for k in abis},feedbackSumScale=next(b['words'][0] for b in c['constants'] if b['role']=='feedbackSumScale'),evidenceBoundary=copy.deepcopy(c['evidenceBoundary'])))
    return out
