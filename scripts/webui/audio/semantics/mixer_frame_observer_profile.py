"""Project paired bus mixing, descriptor publication and reset endpoints."""
from __future__ import annotations

import copy
import hashlib
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.webui.audio.semantics.mixer_observer_profile import instruction
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def load_contract():
    value,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_mixer_frame_native.json',
        schema='endfield.wwise-mixer-frame-observer.v5',status='reviewedCurrentBuild',label='wwise-mixer-frame-observer')
    return value


def project(mixer, contract, owners, image):
    if mixer['schema']!='endfieldCapture.audioMixerBuild.v1' or len(mixer['nativeHooks'])!=35:
        raise ValueError('mixer frame declarations require the prepared mixer recipe')
    for owner in owners.values():
        if owner['nativeInputs']!=contract['nativeInputs']:
            raise ValueError('mixer frame selected inputs differ')
    consumers={}
    for body in contract['consumerBodies']:
        length=body['bodyLength']
        if type(length) is not int or not 0<length<=16384 or body['key'] in consumers:
            raise ValueError('mixer consumer extent or identity differs')
        raw=image.bytes_at_va(image.image_base+int(body['rva'],16),length)
        if len(raw)!=length or hashlib.sha256(raw).hexdigest()!=body['bodySha256']:
            raise ValueError('mixer consumer body differs from selected bytes')
        consumers[body['key']]=body
    design=contract['consumerDesign']
    for witness in design['witnesses']:
        body=consumers[witness['body']]
        instruction(body,witness['offset'],witness['instructionHex'],image)
    alignment=design['matrixRowAlignmentFloats']
    if type(alignment) is not int or not 1<=alignment<=128 or alignment&(alignment-1):
        raise ValueError('mixer matrix row alignment differs')
    roles={w['role']:w for w in design['witnesses']}
    if roles['roundOutputChannelsUp']['instructionHex']!='418d76'+bytes([alignment-1]).hex() or roles['paddedMatrixRowStride']['instructionHex']!='83e6'+bytes([(-alignment)&255]).hex():
        raise ValueError('mixer matrix alignment is not native bound')
    for witness in contract['witnesses']:
        group=next(g for g in owners[witness['ownerContract']]['nativeGroups'] if g['key']==witness['ownerGroup'])
        instruction(group['windows'][witness['windowIndex']],witness['bodyOffset'],witness['instructionHex'],image)
    for leaf in contract['resultStorageLeaves']:
        raw=image.bytes_at_va(image.image_base+int(leaf['rva'],16),leaf['bodyLength'])
        if raw!=bytes.fromhex(leaf['bodyHex']) or hashlib.sha256(raw).hexdigest()!=leaf['bodySha256']:
            raise ValueError('mixer anonymous result storage leaf differs from selected bytes')
    pipeline=owners['wwise_voice_pipeline_native'];routing=owners['wwise_voice_routing_native']
    handoff=contract['sinkHandoffLayout']
    for binding in contract['sinkHandoffBindings']:
        value=sum(handoff[name] for name in binding['sumFields']) if 'sumFields' in binding else handoff[binding['field']]
        if type(value) is not int or not 0<=value<1<<(binding['width']*8):raise ValueError('sink handoff field exceeds declared width')
        group=next(g for g in pipeline['nativeGroups'] if g['key']==binding['ownerGroup'])
        encoded=bytes.fromhex(binding['prefixHex'])+value.to_bytes(binding['width'],'little')+bytes.fromhex(binding['suffixHex'])
        instruction(group['windows'][binding['windowIndex']],binding['bodyOffset'],encoded.hex(),image)
    if handoff['formatOffset']!=pipeline['layout']['descriptorChannelConfiguration'] or handoff['validFramesOffset']!=pipeline['layout']['validFrames'] or handoff['renderClientOffset']!=pipeline['layout']['renderClient']:
        raise ValueError('sink handoff descriptor fields differ from owned layout')
    if contract['contextDescriptorOffset']!=pipeline['layout']['contextPcmDescriptor']:
        raise ValueError('mixer frame context descriptor differs from owned layout')
    output=copy.deepcopy(mixer)
    output['schema']='endfieldCapture.audioMixerFrameBuild.v1'
    output['observerProfile']='audioMixerFramePhasesV1'
    for edit in contract['hookEdits']:
        hook=next(h for h in output['nativeHooks'] if h['sourceKind']==edit['ownerGroup'])
        for key in ('abiId','memory','resultMemory'):
            if key in edit:hook[key]=copy.deepcopy(edit[key])
        for key in ('memory','resultMemory'):
            hook[key].extend(copy.deepcopy(edit.get('append'+key[0].upper()+key[1:],[])))
        hook['readProgram']=compile_reads(hook['memory'])
        hook['resultProgram']=compile_reads(hook['resultMemory'])
    for row in contract['addedHooks']:
        if row['index']!=len(output['nativeHooks']):raise ValueError('mixer frame hook order differs')
        group=next(g for g in owners[row['ownerContract']]['nativeGroups'] if g['key']==row['ownerGroup'])
        output['nativeHooks'].append(dict(name=row['name'],sourceKind=row['ownerGroup'],module='AkSoundEngine.dll',rva=group['entryRva'],required=True,
            abiId=row['abiId'],memory=copy.deepcopy(row['memory']),resultMemory=copy.deepcopy(row['resultMemory']),
            readProgram=compile_reads(row['memory']),resultProgram=compile_reads(row['resultMemory'])))
    # Declarations reuse the owning bus layout and the current mixer identity reads.
    bus=next(h for h in output['nativeHooks'] if h['sourceKind']=='busFrameReset')
    expected={'busInputCount':routing['layout']['busInputCount'],'busFirstDescriptor':routing['layout']['busInputs']}
    for phase in ('memory','resultMemory'):
        fields={f['name']:f for f in bus[phase]}
        for name,offset in expected.items():
            if fields[name]['argIndex']!=0 or fields[name]['offset']!=offset or fields[name].get('pointerOffsets'):
                raise ValueError('mixer frame reset reads differ from owned layout')
        for name in ('busSamplePointer','busFormat','busStatus','busCapacity','busValidFrames'):
            if fields[name].get('pointerOffsets')!=[routing['layout']['busInputs']]:
                raise ValueError('mixer frame reset descriptor chain differs')
    publication=output['nativeHooks'][-1]
    source=next(h for h in output['nativeHooks'] if h['sourceKind']=='contextSourceSampleBuffer')
    source_fields={f['name']:f for f in source['resultMemory']}
    for phase in ('memory','resultMemory'):
        for field in publication[phase][:4]:
            if field!=source_fields[field['name']]:raise ValueError('mixer frame publication identity differs')
        fields={f['name']:f for f in publication[phase]}
        head=fields['routeHead']['offset']
        for name,layout in (('routeRows','routeRows'),('routeRowCount','routeRowCount'),('routeBus','routeBus')):
            if fields[name]['argIndex']!=0 or fields[name]['offset']!=routing['layout'][layout] or fields[name].get('pointerOffsets')!=[head]:
                raise ValueError('mixer frame publication route layout differs')
        descriptor=fields['publishedFirstDescriptor']
        if descriptor['offset']!=routing['layout']['publishedDescriptor'] or descriptor.get('pointerOffsets')!=[head,routing['layout']['routeRows']]:
            raise ValueError('mixer frame publication row layout differs')
    selection=contract['stereoPrefixSelection']
    fields={f['name']:f for f in source['resultMemory']}
    for name,parent,value in [('stereoDescriptor','channelConfiguration',selection['channelConfiguration']),('stereoCapacity','stereoDescriptor',None),('stereoValidFrames','stereoCapacity',selection['capacityFrames'])]:
        guard=dict(name=parent,nonzero=True) if value is None else dict(name=parent,equals=value)
        if fields[name].get('requireMemory')!=guard:raise ValueError('stereo prefix layout guard differs')
    for i in range(selection['samplesPerSecondPlane']):
        field=fields['secondPlaneWord'+str(i)]
        if field['argIndex']!=1 or field['kind']!='u32' or field['offset']!=selection['planeStrideBytes']+i*4 or field.get('pointerOffsets')!=[0] or field.get('requireMemory')!=dict(name='stereoValidFrames',equals=selection['validFrames']):
            raise ValueError('stereo prefix read geometry differs')
    if selection['planeStrideBytes']!=selection['capacityFrames']*4 or selection['samplesPerSecondPlane']>selection['validFrames']:
        raise ValueError('stereo prefix stride or extent differs')
    output['mixerFrameEvidenceBoundary']=contract['evidenceBoundary']
    output['mixerFrameUnsampledHookKinds']=contract['unsampledHookKinds']
    output['contextDescriptorOffset']=contract['contextDescriptorOffset']
    output['stereoPrefixSelection']=selection
    sink=next(h for h in output['nativeHooks'] if h['sourceKind']=='sinkInput')
    fields={f['name']:f for f in sink['resultMemory']}
    for name,offset,kind in (('samplePointer',handoff['descriptorOffset'],'pointer'),('channelConfiguration',handoff['descriptorOffset']+handoff['formatOffset'],'u32'),
            ('capacityFrames',handoff['descriptorOffset']+handoff['capacityOffset'],'u16'),('validFrames',handoff['descriptorOffset']+handoff['validFramesOffset'],'u16'),('inputFlags',handoff['inputFlagsOffset'],'u8')):
        field=fields[name]
        if field['argIndex']!=0 or field['offset']!=offset or field['kind']!=kind or field.get('pointerOffsets'):raise ValueError('sink handoff observation differs from owned layout')
    output['sinkHandoffLayout']=copy.deepcopy(handoff)
    output['sinkHandoffEvidenceBoundary']=contract['sinkHandoffBoundary']
    output['mixerConsumerDesign']=copy.deepcopy(design)
    return output


def project_handoff(frame, contract, owners):
    """Extend the authenticated frame recipe with complete sink handoff scopes."""
    if frame['schema']!='endfieldCapture.audioMixerFrameBuild.v1' or len(frame['nativeHooks'])!=37:
        raise ValueError('sink handoff requires the authenticated frame recipe')
    pipeline=owners['wwise_voice_pipeline_native'];layout=contract['sinkHandoffLayout']
    if frame.get('sinkHandoffLayout')!=layout or pipeline['nativeInputs']!=contract['nativeInputs']:
        raise ValueError('sink handoff selected layout or inputs differ')
    output=copy.deepcopy(frame)
    output['schema']='endfieldCapture.audioSinkHandoffBuild.v1'
    output['observerProfile']='audioSinkWriteConsumePhasesV1'
    output['automaticWindow']=False
    output['nativeSelectionScope']='explicitWindowIds'
    output['sinkHandoffUnsampledHookKinds']=['sinkInput','sinkFrameEnd','sinkSubmit']
    fields=[dict(name=name,argIndex=0,offset=offset,kind=kind) for name,offset,kind in
        [('renderClient',pipeline['layout']['renderClient'],'pointer'),
         ('samplePointer',layout['descriptorOffset'],'pointer'),
         ('channelConfiguration',layout['descriptorOffset']+layout['formatOffset'],'u32'),
         ('capacityFrames',layout['descriptorOffset']+layout['capacityOffset'],'u16'),
         ('validFrames',layout['descriptorOffset']+layout['validFramesOffset'],'u16'),
         ('inputFlags',layout['inputFlagsOffset'],'u8'),
         ('resamplerCapacity',layout['resamplerCapacityOffset'],'u16')]]
    group=next(g for g in pipeline['nativeGroups'] if g['key']=='sinkFrameEnd')
    output['nativeHooks'].append(dict(name='AkSoundEngine.sinkFrameEnd',sourceKind='sinkFrameEnd',
        module='AkSoundEngine.dll',rva=group['entryRva'],required=True,abiId='win64.pointer1_result.v1',
        memory=copy.deepcopy(fields),resultMemory=copy.deepcopy(fields),readProgram=compile_reads(fields),resultProgram=compile_reads(fields)))
    sink=next(h for h in output['nativeHooks'] if h['sourceKind']=='sinkInput')
    sink['resultMemory'].append(copy.deepcopy(fields[-1]));sink['resultProgram']=compile_reads(sink['resultMemory'])
    submit=next(h for h in output['nativeHooks'] if h['sourceKind']=='sinkSubmit')
    submit['resultMemory'].append(copy.deepcopy(fields[0]));submit['resultProgram']=compile_reads(submit['resultMemory'])
    output['sinkHandoffEvidenceBoundary']=dict(contract['sinkHandoffBoundary'],
        conditional='Explicit native window IDs retain every sink write/frame-end/submission entry and its paired completion; original caller result register is anonymous. Native descriptor/mode checks and same-thread nesting admit only direct non-ring/non-resampling write/consume intervals. Device HRESULT/copy admission is separate.',
        unresolved='Unobserved writers and allocation lifetime, upstream Event/bus contribution, actual unfiltered consumer input, full filter/matrix equations, resampled/ring/silent branches and audibility.')
    return output
