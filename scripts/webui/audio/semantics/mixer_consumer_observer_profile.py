"""Project the original unfiltered matrix consumer's bounded input/output reads."""
from __future__ import annotations

import copy
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def project(handoff, contract):
    if handoff['schema']!='endfieldCapture.audioSinkHandoffBuild.v1' or len(handoff['nativeHooks'])!=38:
        raise ValueError('matrix consumer requires the prepared handoff recipe')
    design=contract['consumerDesign']; row=contract['consumerHook']
    if design['argumentCount']!=8 or design['returnKind']!='void' or row['index']!=38 or row['abiId']!='win64.void_integer8_result.v1':
        raise ValueError('matrix consumer ABI differs')
    body=next(b for b in contract['consumerBodies'] if b['key']==row['bodyKey'])
    layout=handoff['sinkHandoffLayout']; fields={f['name']:f for f in row['memory']}
    offsets={'Capacity':layout['capacityOffset'],'ValidFrames':layout['validFramesOffset'],
        'Format':layout['formatOffset'],'SamplePointer':0}
    for domain,arg in (('source',3),('output',6)):
        for suffix,offset in offsets.items():
            f=fields[domain+suffix]
            if f['argIndex']!=arg or f['offset']!=offset or f.get('pointerOffsets')!=[0]:
                raise ValueError('matrix consumer descriptor geometry differs from native layout')
    cohort=fields['cohortCount']
    witness=next(w for w in design['witnesses'] if w['role']=='cohortCount')
    if cohort['offset']!=bytes.fromhex(witness['instructionHex'])[-1] or cohort['argIndex']!=0 or cohort['kind']!='u32':
        raise ValueError('matrix consumer cohort displacement differs from native read')
    # The preceding frame projection authenticates the complete consumer bodies.
    output=copy.deepcopy(handoff)
    output['schema']='endfieldCapture.audioMixerConsumerBuild.v1'
    output['observerProfile']='audioMixerConsumerPhasesV1'
    output['nativeHooks'].append(dict(name=row['name'],sourceKind=row['sourceKind'],module='AkSoundEngine.dll',
        rva=body['rva'],required=True,abiId=row['abiId'],memory=copy.deepcopy(row['memory']),resultMemory=copy.deepcopy(row['resultMemory']),
        readProgram=compile_reads(row['memory']),resultProgram=compile_reads(row['resultMemory'])))
    output['mixerConsumerSelection']=copy.deepcopy(row['selection'])
    output['mixerConsumerSelection'].update(descriptorOffsets=offsets,cohortCountOffset=cohort['offset'],matrixRowAlignmentFloats=design['matrixRowAlignmentFloats'])
    output['mixerConsumerInputBoundary']=design['inputBoundary']
    output['mixerConsumerEvidenceBoundary']=row['evidenceBoundary']
    return output
