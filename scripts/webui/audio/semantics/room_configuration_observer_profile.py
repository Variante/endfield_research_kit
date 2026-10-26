"""Live original Room parameter object alongside its derived wet state."""
from __future__ import annotations
import copy
from scripts.game_data.wwise_room_configuration_native import load_contract,validate
from scripts.game_data.wwise_room_history_native import load_contract as load_history
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads


def project(base,c,image,selected_inputs):
    if base['schema']!='endfieldCapture.audioRoomWetBuild.v1' or len(base['nativeHooks'])!=58:raise ValueError('Room configuration requires the complete wet recipe')
    checked=validate(c,image,selected_inputs);out=copy.deepcopy(base);p=c['parameterProjection']
    fields=[dict(name='sampleRate',argIndex=0,kind='u32',offset=c['layout']['sampleRate'])]+[dict(name='parameterWord'+str(j),argIndex=0,kind='u32',offset=j*p['wordBytes'],pointerOffsets=[p['instanceOffset']]) for j in range(p['byteExtent']//p['wordBytes'])]
    root=next(h for h in out['nativeHooks'] if h['sourceKind']=='roomVerbExecute')
    for phase,program in [('memory','readProgram'),('resultMemory','resultProgram')]:root[phase].extend(copy.deepcopy(fields));root[program]=compile_reads(root[phase])
    out.update(schema='endfieldCapture.audioRoomConfigurationBuild.v1',observerProfile='audioRoomConfigurationPhasesV1',roomConfiguration=dict(toneStageModes={v['stagePurpose']:v['mode'] for v in c['toneStageSelectors']},parameterProjection=copy.deepcopy(p),parameterVtableRva=checked['parameterVtableRva'],diffusionConfiguration=copy.deepcopy(load_history()['diffusionConfiguration']),evidenceBoundary=copy.deepcopy(c['evidenceBoundary'])))
    return out
