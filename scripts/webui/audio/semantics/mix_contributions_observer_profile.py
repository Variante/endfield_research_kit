"""Bounded per-channel original accumulation calls within selected bus tasks."""
from __future__ import annotations
import copy
from scripts.game_data.wwise_mix_contributions_native import load_contract,validate
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def fields(kind,phase,selection):
    result=[dict(name='frames',argIndex=3 if kind=='matrixAccumulateConstant' else 6,kind='argumentU32',offset=0),
            dict(name='coefficientBits',argIndex=2,kind='argumentU32',offset=0)]
    if kind=='matrixAccumulateRamp':result.append(dict(name='stepBits',argIndex=3,kind='argumentU32',offset=0))
    for prefix,arg in [('sourceWord',1),('destinationWord',0)]:
        result.extend(dict(name=prefix+str(i),argIndex=arg,kind='u32',offset=4*i,requireMemory=dict(name='frames',equals=selection['frames'])) for i in range(4))
    result.append(dict(name='prefix',argIndex=1 if phase==1 else 0,kind='bytes',offset=0,countField='frames',stride=4,maxBytes=selection['prefixBytes']))
    return result


def project(bus,contract,image,selected_inputs):
    if bus['schema']!='endfieldCapture.audioBusProcessingBuild.v3' or len(bus['nativeHooks'])!=45:raise ValueError('mix contributions require selected bus recipe')
    indexed=validate(contract,image,selected_inputs)
    if contract['selection']!=dict(frames=512,prefixBytes=16,processorMode=1):raise ValueError('mix contribution selected geometry differs')
    output=copy.deepcopy(bus)
    gate=contract['consumerOutputGate']
    if gate!=dict(field='outputDescriptor',argumentIndex=2):raise ValueError('mix contribution consumer output gate differs')
    consumer=output['nativeHooks'][38]
    if consumer['sourceKind']!='unfilteredMatrixConsumer':raise ValueError('mix contribution original consumer differs')
    for phase,program in [('memory','readProgram'),('resultMemory','resultProgram')]:
        f=next(f for f in consumer[phase] if f['name']==gate['field'])
        if f!=dict(name='outputDescriptor',argIndex=6,kind='pointer',offset=0,requireMemory=dict(name='sourceValidFrames',equals=512)):
            raise ValueError('mix contribution output descriptor ABI differs')
        f.pop('requireMemory');f['requireArgument']=gate['argumentIndex']
        consumer[program]=compile_reads(consumer[phase])
    for h in contract['hooks']:
        kind=h['sourceKind'];constant=kind=='matrixAccumulateConstant'
        if kind not in ('matrixAccumulateConstant','matrixAccumulateRamp') or h['index']!=len(output['nativeHooks']):raise ValueError('mix contribution hook order differs')
        abi='win64.void_pointer2_float_u32_result.v1' if constant else 'win64.void_pointer2_float2_u32_result.v1'
        if h['abiId']!=abi or h['ownerGroup']!=('matrixGainAvxConstant' if constant else 'matrixGainAvxTransition'):raise ValueError('mix contribution floating ABI differs')
        for phase,key in [(1,'memory'),(2,'resultMemory')]:
            if h[key]!=fields(kind,phase,contract['selection']):raise ValueError('mix contribution read geometry differs')
        output['nativeHooks'].append(dict(name=h['name'],sourceKind=kind,module='AkSoundEngine.dll',rva=indexed[h['ownerGroup']]['entryRva'],abiId=abi,
            required=True,memory=copy.deepcopy(h['memory']),resultMemory=copy.deepcopy(h['resultMemory']),readProgram=compile_reads(h['memory']),resultProgram=compile_reads(h['resultMemory'])))
    output.update(schema='endfieldCapture.audioMixContributionsBuild.v1',observerProfile='audioMixContributionsPhasesV1',
        mixContributions=dict(selection=copy.deepcopy(contract['selection']),rampLaneWords=contract['rampLaneWords'][:4],
            callerReturnRvas={h['sourceKind']:next(b['returnRva'] for b in contract['callBindings'] if b['targetGroup']==h['ownerGroup']) for h in contract['hooks']},
            evidenceBoundary=copy.deepcopy(contract['evidenceBoundary'])))
    return output


def validate_addresses(row,facts,declared):
    if row['phase']==3:return
    for i,f in enumerate(declared):
        if facts.get(f['name']) is None or f['kind'] not in ('u32','bytes'):continue
        expected=row['args'][f['argIndex']]+f['offset']
        if row['addresses'][i]!=expected:raise ValueError('mix contribution operand address differs')
    if row['spanBytes'] and row['spanAddress']!=row['args'][1 if row['phase']==1 else 0]:raise ValueError('mix contribution PCM address differs')
