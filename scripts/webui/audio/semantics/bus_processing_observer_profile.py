"""Project scoped output-task, effect-consume and floating frame-gain phases."""
from __future__ import annotations
import copy
from scripts.game_data.wwise_bus_processing_native import load_contract, validate
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def validate_biquad_reads(declared, contract, descriptor):
    """Check both phases against the native service ABI and collection layouts."""
    kind=declared['sourceKind'];b=contract['biquadProcessing'];eq=b['eqLayout']
    if kind not in ('biquadProcessing','collectionEqExecute'):return
    expected_abi='win64.void_integer8_result.v1' if kind=='biquadProcessing' else 'win64.void_integer2_result.v1'
    if declared['abiId']!=expected_abi:raise ValueError('biquad/EQ ABI differs')
    for phase in ('memory','resultMemory'):
        fields=declared[phase];expected={}
        def read(name,arg,typ,offset=0,chain=(),**extra):
            expected[name]=dict(argIndex=arg,kind=typ,offset=offset,pointerOffsets=list(chain),**extra)
        if kind=='biquadProcessing':
            for name,arg in [('inputPlane',1),('outputPlane',2),('coefficientPointer',3),('historyPointer',6)]:read(name,arg,'pointer')
            read('frameCountPointer',7,'argument');read('frameCount',7,'u32')
            read('segmentCount',8,'argumentU32');read('bufferCount',9,'argumentU32')
            read('processorMode',5,'u32',int(b['dispatch']['processorModeRva'],16))
            for prefix,count,arg,pointer in [('coefficientWord',5,3,'coefficientPointer'),('historyWord',4,6,'historyPointer')]:
                for i in range(count):read(prefix+str(i),arg,'u32',i*4,(0,),requireMemory=dict(name=pointer,nonzero=True))
            read('prefix',1 if phase=='memory' else 2,'bytes',chain=(0,),countField='frameCount',stride=4,maxBytes=contract['selection']['prefixBytes'])
        else:
            read('instance',0,'argument');read('collection',1,'argument')
            read('collectionCount',1,'u32',eq['collectionCount'])
            read('descriptorPointers',1,'pointer',eq['descriptorPointers']);read('ownerPointers',1,'pointer',eq['ownerPointers'])
            read('descriptor',1,'pointer',chain=(eq['descriptorPointers'],));read('firstCollectionOwner',1,'pointer',chain=(eq['ownerPointers'],))
            for name,typ,offset in [('format','u32',descriptor['formatOffset']),('capacity','u16',descriptor['capacityOffset']),('validFrames','u16',descriptor['validFramesOffset']),('samplePointer','pointer',0),('owner','pointer',contract['layout']['descriptorOwner'])]:
                read(name,1,typ,offset,(eq['descriptorPointers'],0))
            read('outputGainBits',0,'u32',eq['previousOutputGain']);read('parameterPointer',0,'pointer',eq['parameterPointer'])
            read('outputDbBits',0,'u32',eq['outputDb'],(eq['parameterPointer'],));read('includeLfe',0,'u8',eq['includeLfe'],(eq['parameterPointer'],))
            for i in range(3):read('bandEnabled'+str(i),0,'u8',eq['enabledBands']+i)
            read('processorService',5,'pointer',int(eq['processorServiceRva'],16));read('processorVtable',5,'pointer',chain=(int(eq['processorServiceRva'],16),))
            read('processorExecuteTarget',0,'pointerFromField',contract['layout']['effectExecuteSlot'],baseField='processorVtable')
        if {f['name'] for f in fields}!=set(expected):raise ValueError('biquad/EQ read roster differs')
        for f in fields:
            actual={k:v for k,v in f.items() if k!='name'};actual.setdefault('pointerOffsets',[])
            if actual!=expected[f['name']]:raise ValueError('biquad/EQ read differs: '+phase+' '+f['name'])


def project(master, contract, owners, image):
    if master['schema']!='endfieldCapture.audioMasterStageBuild.v1' or len(master['nativeHooks'])!=39:
        raise ValueError('bus processing requires the prepared master-stage recipe')
    indexed=validate(contract, owners['wwise_voice_pipeline_native'], image)
    if contract['taskSampling']['scope']!='sampledRootsAllDescendants' or contract['taskSampling']['rootKeyField']!='taskIndex':
        raise ValueError('bus task sampling declaration differs')
    output=copy.deepcopy(master)
    layout=contract['layout'];descriptor=master['sinkHandoffLayout']
    for declared in contract['addedHooks']:
        if declared['index']!=len(output['nativeHooks']):raise ValueError('bus processing hook order differs')
        fields=declared['memory']
        if len({f['name'] for f in fields})!=len(fields):raise ValueError('bus processing duplicate fields')
        by_name={f['name']:f for f in fields};kind=declared['sourceKind']
        validate_biquad_reads(declared,contract,descriptor)
        if kind=='busOutputTask':
            if by_name['taskIndex']['offset']!=layout['taskIndex']:raise ValueError('bus task index geometry differs')
        elif kind not in ('collectionEqExecute','biquadProcessing'):
            arg=3 if kind=='busEffectConsume' else 0;chain=[] if kind=='sourceFrameGain' else [layout['busInputs']]
            for field,key in [('format','formatOffset'),('capacity','capacityOffset'),('validFrames','validFramesOffset')]:
                if (by_name[field]['argIndex'],by_name[field]['offset'],by_name[field].get('pointerOffsets',[]))!=(arg,descriptor[key],chain):
                    raise ValueError('bus processing descriptor geometry differs: '+field)
            if (by_name['owner']['argIndex'],by_name['owner']['offset'],by_name['owner'].get('pointerOffsets',[]))!=(arg,layout['descriptorOwner'],chain):raise ValueError('bus processing owner geometry differs')
            for name,key in [('previousGainBits','previousGain'),('targetGainBits','targetGain')]:
                if (by_name[name]['argIndex'],by_name[name]['offset'],by_name[name].get('pointerOffsets',[]))!=(arg,layout[key],chain+[layout['descriptorOwner']]):raise ValueError('bus processing retained gain geometry differs')
            if by_name['prefix'].get('pointerOffsets')!=chain+[0]:raise ValueError('bus processing PCM geometry differs')
            if kind=='busEffectConsume':
                for name,base,offset in [('firstEffectVtable','firstEffectObject',0),('firstEffectExecuteTarget','firstEffectVtable',layout['effectExecuteSlot'])]:
                    f=by_name[name]
                    if (f['kind'],f.get('baseField'),f['offset'],f.get('pointerOffsets',[]))!=('pointerFromField',base,offset,[]):raise ValueError('bus effect target geometry differs')
        group=indexed[declared['ownerGroup']]
        output['nativeHooks'].append(dict(name=declared['name'],sourceKind=declared['sourceKind'],module='AkSoundEngine.dll',rva=group['entryRva'],
            abiId=declared['abiId'],required=True,memory=copy.deepcopy(fields),resultMemory=copy.deepcopy(declared['resultMemory']),
            readProgram=compile_reads(fields),resultProgram=compile_reads(declared['resultMemory'])))
    output.update(schema='endfieldCapture.audioBusProcessingBuild.v3',observerProfile='audioBusProcessingPhasesV3',
        busProcessingLayout=copy.deepcopy(contract['layout']),busProcessingSelection=copy.deepcopy(contract['selection']),
        busProcessingReturnSites={k:contract[k] for k in ('gainCallReturnRva','effectConsumeCallReturnRva','taskProcessingCallReturnRva','taskMasterCallReturnRva')},
        busProcessingEvidenceBoundary=copy.deepcopy(contract['evidenceBoundary']),busProcessingTaskScoped=True,
        busProcessingTaskSelection=contract['taskSampling']['scope'],busProcessingTaskKeyField=contract['taskSampling']['rootKeyField'],
        busProcessingCollectionEffect=copy.deepcopy(contract['collectionEffect']),
        busProcessingBiquad=copy.deepcopy(contract['biquadProcessing']),
        busProcessingEffectClasses=[dict(classId=b['classId'],executeRva=indexed[b['executeGroup']]['entryRva'],vtableRva=b['vtableRva']) for b in contract['effectClassBindings']])
    output['busProcessingBiquad']['serviceEntryRva']=indexed[contract['biquadProcessing']['serviceGroup']]['entryRva']
    return output


def validate_addresses(row,facts,fields,layout,descriptor,biquad=None):
    kind=row['hook'].rsplit('.',1)[-1]
    if kind=='collectionEqExecute' and row['phase']!=3:
        addresses={f['name']:row['addresses'][i] for i,f in enumerate(fields) if facts.get(f['name']) is not None}
        eq=biquad['eqLayout'];base=facts.get('descriptor');expected=dict(collectionCount=row['args'][1]+eq['collectionCount'],descriptorPointers=row['args'][1]+eq['descriptorPointers'],ownerPointers=row['args'][1]+eq['ownerPointers'])
        if facts.get('descriptorPointers'):expected['descriptor']=facts['descriptorPointers']
        if facts.get('ownerPointers'):expected['firstCollectionOwner']=facts['ownerPointers']
        if base:expected.update(format=base+descriptor['formatOffset'],capacity=base+descriptor['capacityOffset'],validFrames=base+descriptor['validFramesOffset'],samplePointer=base,owner=base+layout['descriptorOwner'])
        expected['outputGainBits']=row['args'][0]+eq['previousOutputGain']
        expected['parameterPointer']=row['args'][0]+eq['parameterPointer']
        if facts.get('parameterPointer'):expected.update(outputDbBits=facts['parameterPointer']+eq['outputDb'],includeLfe=facts['parameterPointer']+eq['includeLfe'])
        expected.update({f'bandEnabled{i}':row['args'][0]+eq['enabledBands']+i for i in range(3)})
        expected['processorService']=row['moduleBase']+int(eq['processorServiceRva'],16)
        if facts.get('processorService'):expected['processorVtable']=facts['processorService']
        if facts.get('processorVtable'):expected['processorExecuteTarget']=facts['processorVtable']+layout['effectExecuteSlot']
        for name,value in expected.items():
            if name in addresses and addresses[name]!=value:raise ValueError('EQ '+name+' read address differs')
        return
    if kind=='biquadProcessing' and row['phase']!=3:
        addresses={f['name']:row['addresses'][i] for i,f in enumerate(fields) if facts.get(f['name']) is not None}
        expected=dict(inputPlane=row['args'][1],outputPlane=row['args'][2],coefficientPointer=row['args'][3],historyPointer=row['extraArgument'],frameCount=row['sixthArgument'],
            processorMode=row['moduleBase']+int(biquad['dispatch']['processorModeRva'],16))
        for prefix,count,base in [('coefficientWord',5,facts.get('coefficientPointer')),('historyWord',4,facts.get('historyPointer'))]:
            if base:expected.update({prefix+str(i):base+i*4 for i in range(count)})
        plane=facts.get('inputPlane' if row['phase']==1 else 'outputPlane')
        if plane:expected['prefix']=plane
        for name,value in expected.items():
            if name in addresses and addresses[name]!=value:raise ValueError('biquad '+name+' read address differs')
        if row['spanBytes'] and plane is not None and row['spanAddress']!=plane:raise ValueError('biquad PCM prefix address differs')
        return
    if kind not in ('busOutputTask','busPostMixProcessing','busEffectConsume','sourceFrameGain') or row['phase']==3:return
    addresses={f['name']:row['addresses'][i] for i,f in enumerate(fields) if facts.get(f['name']) is not None}
    expected={}
    if kind=='busOutputTask':expected['taskIndex']=row['args'][0]+layout['taskIndex']
    else:
        if kind=='sourceFrameGain':base=row['args'][0]
        else:
            arg=3 if kind=='busEffectConsume' else 0;bus=row['args'][arg]
            expected.update(busInputs=bus+layout['busInputs'],busInputCount=bus+layout['busInputCount'])
            base=facts.get('busInputs')
        if base:
            expected.update(format=base+descriptor['formatOffset'],capacity=base+descriptor['capacityOffset'],validFrames=base+descriptor['validFramesOffset'],samplePointer=base,owner=base+layout['descriptorOwner'])
        if facts.get('owner'):
            expected.update(previousGainBits=facts['owner']+layout['previousGain'],targetGainBits=facts['owner']+layout['targetGain'])
        if facts.get('samplePointer'):expected['prefix']=facts['samplePointer']
        if kind=='busPostMixProcessing':
            for name in ('processingState','processingMode','effectCount','currentControl','previousControl'):expected[name]=row['args'][0]+layout[name]
        if kind=='busEffectConsume':
            expected['inputCollection']=row['args'][1]
            if facts.get('inputCollection'):expected.update(selectedDescriptor=facts['inputCollection'],selectedCount=facts['inputCollection']+layout['collectionCount'])
            for name in ('objectCount','multiObjectMode','skipGainBake','inPlaceMode'):expected[name]=row['args'][0]+layout[name]
            expected.update(previousControl=row['args'][0]+layout['effectPreviousControl'],currentControl=row['args'][0]+layout['effectCurrentControl'],effectObjects=row['args'][0])
            if facts.get('effectObjects'):expected['firstEffectState']=facts['effectObjects']
            if facts.get('firstEffectState'):expected['firstEffectObject']=facts['firstEffectState']+layout['effectObject']
            if facts.get('firstEffectObject'):expected['firstEffectVtable']=facts['firstEffectObject']
            if facts.get('firstEffectVtable'):expected['firstEffectExecuteTarget']=facts['firstEffectVtable']+layout['effectExecuteSlot']
    for name,value in expected.items():
        if name in addresses and addresses[name]!=value:raise ValueError('bus processing '+name+' read address differs')
    if row['spanBytes'] and facts.get('samplePointer') is not None and row['spanAddress']!=facts['samplePointer']:
        raise ValueError('bus processing prefix address differs')
