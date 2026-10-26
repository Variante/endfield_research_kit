"""Prepare the reviewed Audio playback manifest without starting a capture."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.wwise_codec_factory_native import load_validated_codec_contract
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.repo_paths import REPO_ROOT
from scripts.webui.audio.semantics import playback_observer_profile as profile
from scripts.webui.audio.semantics import device_observer_profile as device_profile
from scripts.webui.audio.semantics import mixer_observer_profile as mixer_profile
from scripts.webui.audio.semantics import mixer_frame_observer_profile as frame_profile
from scripts.webui.audio.semantics import mixer_consumer_observer_profile as consumer_profile
from scripts.webui.audio.semantics import master_stage_observer_profile as master_profile
from scripts.webui.audio.semantics import bus_processing_observer_profile as bus_profile
from scripts.webui.audio.semantics import mix_contributions_observer_profile as contributions_profile
from scripts.webui.audio.semantics import room_blend_observer_profile as room_profile
from scripts.webui.audio.semantics import room_input_observer_profile as input_profile
from scripts.webui.audio.semantics import room_history_observer_profile as history_profile
from scripts.webui.audio.semantics import room_wet_observer_profile as wet_profile
from scripts.webui.audio.semantics import room_configuration_observer_profile as configuration_profile
from scripts.webui.story_recovery import prepare_endfield_source_owner as source


def prepare(game_root, output, *, device=False, mixer=False, mixer_frame=False, sink_handoff=False, mixer_consumer=False, master_stage=False, bus_processing=False, mix_contributions=False,room_blend=False,room_input=False,room_history=False,room_wet=False,room_configuration=False):
    root=Path(game_root).resolve();output=Path(output).resolve()
    room_wet=room_wet or room_configuration
    room_history=room_history or room_wet
    room_input=room_input or room_history
    room_blend=room_blend or room_input
    mix_contributions=mix_contributions or room_blend
    bus_processing=bus_processing or mix_contributions
    master_stage=master_stage or bus_processing
    mixer_consumer=mixer_consumer or master_stage
    if REPO_ROOT/'reports' not in output.parents:
        raise ValueError('playback declarations must be written under reports/')
    base,audit=source.prepare(root,REPO_ROOT/'reports/audio/playback_source_basis.json',REPO_ROOT/'reports/audio/playback_source_basis_gate.json')
    if base is None:
        raise ValueError('source/owner declaration gate failed: '+audit.get('detail',audit['status']))
    _,gate=load_validated_codec_contract(gameassembly=root/'GameAssembly.dll',metadata=root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',
        ak_sound_engine=root/'Endfield_Data/Plugins/x86_64/AkSoundEngine.dll',include_inheritance=True,include_sink_negotiation=True)
    if gate['status']!='validated':
        raise ValueError('playback native gate failed: '+gate.get('detail',gate['status']))
    contract=profile.load_contract()
    owners={name:json.loads((CONTRACTS_DIR/(name+'.json')).read_bytes()) for name in {r['ownerContract'] for r in contract['hooks']}|{r['ownerContract'] for r in contract['lineageArguments']}}
    if contract['nativeInputs'] != owners['wwise_codec_factory_native']['nativeInputs']:
        raise ValueError('playback recipe selected inputs differ')
    image=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(root/'Endfield_Data/Plugins/x86_64/AkSoundEngine.dll')
    profile.validate_lineage_arguments(contract,owners,image)
    profile.validate_field_arguments(contract,owners,image)
    manifest=profile.project(base,contract,owners)
    if device or mixer or mixer_frame or sink_handoff or mixer_consumer:
        observer=device_profile.load_contract()
        if observer['nativeInputs']!=contract['nativeInputs']:raise ValueError('device observer selected inputs differ')
        manifest=device_profile.project(manifest,observer,owners[observer['ownerContract']],image)
    if mixer or mixer_frame or sink_handoff or mixer_consumer:
        observer=mixer_profile.load_contract()
        if observer['nativeInputs']!=contract['nativeInputs']:raise ValueError('mixer observer selected inputs differ')
        manifest=mixer_profile.project(manifest,observer,owners,image)
    if mixer_frame or sink_handoff or mixer_consumer:
        observer=frame_profile.load_contract()
        if observer['nativeInputs']!=contract['nativeInputs']:raise ValueError('mixer frame observer selected inputs differ')
        manifest=frame_profile.project(manifest,observer,owners,image)
        if sink_handoff or mixer_consumer:manifest=frame_profile.project_handoff(manifest,observer,owners)
        if mixer_consumer:manifest=consumer_profile.project(manifest,observer)
        if master_stage:manifest=master_profile.project(manifest,master_profile.load_contract(),owners,image)
        if bus_processing:manifest=bus_profile.project(manifest,bus_profile.load_contract(),owners,image)
        if mix_contributions:manifest=contributions_profile.project(manifest,contributions_profile.load_contract(),image,contract['nativeInputs'])
        if room_blend:manifest=room_profile.project(manifest,room_profile.load_contract(),owners,image,contract['nativeInputs'])
        if room_input:manifest=input_profile.project(manifest,input_profile.load_contract(),owners,image,contract['nativeInputs'])
        if room_history:manifest=history_profile.project(manifest,history_profile.load_contract(),owners,image,contract['nativeInputs'])
        if room_wet:manifest=wet_profile.project(manifest,wet_profile.load_contract(),owners,image,contract['nativeInputs'])
        if room_configuration:manifest=configuration_profile.project(manifest,configuration_profile.load_contract(),image,contract['nativeInputs'])
    output.parent.mkdir(parents=True,exist_ok=True)
    staged=output.with_suffix('.tmp');staged.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');staged.replace(output)
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-root',type=Path,required=True)
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--device',action='store_true',help='add observed render-client HRESULT and pre-release buffer phases')
    modes.add_argument('--mixer',action='store_true',help='add current owner serial, actual mixer rows and paired output conversion to device phases')
    modes.add_argument('--mixer-frame',action='store_true',help='add paired bus mixing/publication/reset and retain every source sample/release endpoint')
    modes.add_argument('--sink-handoff',action='store_true',help='observe every sink write/frame-end/submission inside manually selected native windows')
    modes.add_argument('--mixer-consumer',action='store_true',help='add original unfiltered consumer PCM/gain/matrix and initial/returned output in manual windows')
    modes.add_argument('--master-stage',action='store_true',help='add first master input/gain, mode and before/after PCM to locate the remaining output transform')
    modes.add_argument('--bus-processing',action='store_true',help='observe complete output-task descendants, post-mix/effect transitions and floating frame-gain calls')
    modes.add_argument('--mix-contributions',action='store_true',help='add original per-channel constant/ramp AVX accumulation operands to selected bus tasks')
    modes.add_argument('--room-input',action='store_true',help='observe original stereo fold and circular history inside RoomVerb')
    modes.add_argument('--room-history',action='store_true',help='observe live expanded tone matrices and paired diffusion history')
    modes.add_argument('--room-configuration',action='store_true',help='add complete stored Room settings and sample rate to the accepted wet recipe')
    modes.add_argument('--room-wet',action='store_true',help='observe complete early-tap prefixes, four-ring feedback and final wet damping')
    modes.add_argument('--room-blend',action='store_true',help='add actual RoomVerb instance and original three-buffer blend operands and phases')
    p.add_argument('--output',type=Path);args=p.parse_args()
    if args.room_input:args.output=args.output or REPO_ROOT/'reports/audio/room_input_capture_manifest.json'
    if args.room_history:args.output=args.output or REPO_ROOT/'reports/audio/room_history_capture_manifest.json'
    if args.room_wet:args.output=args.output or REPO_ROOT/'reports/audio/room_wet_capture_manifest.json'
    if args.room_configuration:args.output=args.output or REPO_ROOT/'reports/audio/room_configuration_capture_manifest.json'
    if args.room_blend:args.output=args.output or REPO_ROOT/'reports/audio/room_blend_capture_manifest.json'
    if args.mix_contributions:args.output=args.output or REPO_ROOT/'reports/audio/mix_contributions_capture_manifest.json'
    args.output=args.output or REPO_ROOT/('reports/audio/bus_processing_capture_manifest.json' if args.bus_processing else 'reports/audio/master_stage_capture_manifest.json' if args.master_stage else 'reports/audio/mixer_consumer_capture_manifest.json' if args.mixer_consumer else 'reports/audio/sink_handoff_capture_manifest.json' if args.sink_handoff else 'reports/audio/mixer_frame_capture_manifest.json' if args.mixer_frame else 'reports/audio/mixer_capture_manifest.json' if args.mixer else 'reports/audio/device_capture_manifest.json' if args.device else 'reports/audio/playback_capture_manifest.json')
    try:manifest=prepare(args.game_root,args.output,device=args.device,mixer=args.mixer,mixer_frame=args.mixer_frame,sink_handoff=args.sink_handoff,mixer_consumer=args.mixer_consumer,master_stage=args.master_stage,bus_processing=args.bus_processing,mix_contributions=args.mix_contributions,room_blend=args.room_blend,room_input=args.room_input,room_history=args.room_history,room_wet=args.room_wet,room_configuration=args.room_configuration)
    except (OSError,ValueError,KeyError,TypeError,StopIteration) as error:
        print('Audio playback declarations withheld: '+str(error));return 2
    print(f"Audio playback declarations: {len(manifest['nativeHooks'])} native + 2 managed hooks -> {args.output}")
    return 0


if __name__=='__main__':raise SystemExit(main())
