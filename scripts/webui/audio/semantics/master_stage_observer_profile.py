"""Observe the admitted master descriptor before and after its gain stage."""
from __future__ import annotations

import copy
import hashlib
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.webui.audio.semantics.mixer_observer_profile import instruction
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def load_contract():
    value,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_master_stage_native.json',schema='endfield.wwise-master-stage-observer.v1',
        status='reviewedCurrentBuild',label='wwise-master-stage-observer')
    return value


def project(consumer, contract, owners, image):
    if consumer['schema']!='endfieldCapture.audioMixerConsumerBuild.v1' or len(consumer['nativeHooks'])!=39:
        raise ValueError('master stage requires prepared consumer observations')
    owner=owners[contract['ownerContract']]
    if owner['nativeInputs']!=contract['nativeInputs']:raise ValueError('master stage selected inputs differ')
    group=next(g for g in owner['nativeGroups'] if g['key']==contract['ownerGroup'])
    groups={g['key']:g for g in owner['nativeGroups']}
    for key in [group['key']]+contract['additionalBodyGroups']:
        for window in groups[key]['windows']:
            raw=image.bytes_at_va(image.image_base+int(window['rva'],16),window['bodyLength'])
            if hashlib.sha256(raw).hexdigest()!=window['bodySha256']:raise ValueError('master stage complete body differs')
    layout=contract['layout']
    for b in contract['bindings']:
        value=layout[b['field']]-layout[b['subtractField']] if 'subtractField' in b else layout[b['field']]
        raw=bytes.fromhex(b['prefixHex'])+value.to_bytes(b['width'],'little')+bytes.fromhex(b['suffixHex'])
        instruction(group['windows'][0],b['offset'],raw.hex(),image)
    for b in contract['bodyInstructions']:
        instruction(groups[b['group']]['windows'][b['windowIndex']],b['offset'],b['instructionHex'],image)
    output=copy.deepcopy(consumer);hook=next(h for h in output['nativeHooks'] if h['sourceKind']=='masterBusOutput')
    base={f['name']:f for f in hook['memory']}
    if base['busInputs']['offset']!=layout['busInputs'] or base['busInputs']['argIndex']!=0:
        raise ValueError('master stage bus descriptor read differs')
    if base['busInputCount']['offset']!=layout['busInputCount'] or base['busInputCount']['argIndex']!=0:
        raise ValueError('master stage bus count read differs')
    fields=contract['appendMemory'];descriptor=output['sinkHandoffLayout']
    for name,key in [('firstInputFormat','formatOffset'),('firstInputCapacity','capacityOffset'),('firstInputValidFrames','validFramesOffset')]:
        f=next(f for f in fields if f['name']==name)
        if f['offset']!=descriptor[key] or f['argIndex']!=0 or f.get('pointerOffsets')!=[layout['busInputs']]:
            raise ValueError('master stage descriptor geometry differs')
    typed={f['name']:f for f in fields}
    for name,key in [('firstInputPreviousGainBits','previousGain'),('firstInputTargetGainBits','targetGain')]:
        f=typed[name]
        if f['offset']!=layout[key] or f['argIndex']!=0 or f['kind']!='u32' or f.get('pointerOffsets')!=[layout['busInputs'],layout['descriptorOwner']]:
            raise ValueError('master stage retained gain geometry differs')
    f=typed['firstInputOwner']
    if f['offset']!=layout['descriptorOwner'] or f['kind']!='pointer' or f['argIndex']!=0 or f.get('pointerOffsets')!=[layout['busInputs']]:
        raise ValueError('master stage input owner geometry differs')
    for name,key,kind in [('outputNodeFormat','nodeFormat','u32'),('outputNodeExtended','nodeExtended','u8'),('outputNodeProcessed','nodeProcessed','u8')]:
        f=typed[name]
        if f['argIndex']!=1 or f['offset']!=layout[key] or f['kind']!=kind or f.get('pointerOffsets'):
            raise ValueError('master stage output mode geometry differs')
    for phase in ('memory','resultMemory'):
        hook[phase]=copy.deepcopy(hook['memory'][:4])+copy.deepcopy(fields)
    hook['readProgram']=compile_reads(hook['memory']);hook['resultProgram']=compile_reads(hook['resultMemory'])
    output.update(schema='endfieldCapture.audioMasterStageBuild.v1',observerProfile='audioMasterStagePhasesV1',
        masterStageSelection=copy.deepcopy(contract['selection']),masterStageLayout=copy.deepcopy(layout),masterStageEvidenceBoundary=copy.deepcopy(contract['evidenceBoundary']))
    return output


def validate_addresses(row, facts, fields, layout, descriptor):
    if not row['hook'].endswith('.masterBusOutput') or row['phase']==3:return
    addresses={f['name']:row['addresses'][i] for i,f in enumerate(fields) if facts.get(f['name']) is not None}
    expected={'busInputs':row['args'][0]+layout['busInputs'],'busInputCount':row['args'][0]+layout['busInputCount']}
    for name,key in [('outputNodeFormat','nodeFormat'),('outputNodeExtended','nodeExtended'),('outputNodeProcessed','nodeProcessed')]:expected[name]=row['args'][1]+layout[key]
    if facts.get('busInputs') is not None:
        for name,key in [('firstInputFormat','formatOffset'),('firstInputCapacity','capacityOffset'),('firstInputValidFrames','validFramesOffset')]:expected[name]=facts['busInputs']+descriptor[key]
        expected['firstInputSamplePointer']=facts['busInputs'];expected['firstInputOwner']=facts['busInputs']+layout['descriptorOwner']
    if facts.get('firstInputOwner') is not None:
        for name,key in [('firstInputPreviousGainBits','previousGain'),('firstInputTargetGainBits','targetGain')]:expected[name]=facts['firstInputOwner']+layout[key]
    for name,value in expected.items():
        if name in addresses and addresses[name]!=value:raise ValueError('master stage '+name+' read address differs')
    if row['spanBytes'] and facts.get('firstInputSamplePointer') is not None and row['spanAddress']!=facts['firstInputSamplePointer']:
        raise ValueError('master stage prefix address differs')
