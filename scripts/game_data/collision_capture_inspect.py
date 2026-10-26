"""Authenticate a saved collision session and decode paired observations.

Source joins use exact stored Model bytes. Mesh names and process-local instance
IDs remain observations and cannot establish a physical Unity asset identity.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import re

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.collision_capture_prepare import ROLES, validate_contract, validate_player, _apis
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.collision_capture_memory import validate_archive

SCHEMA = "endfield.collision-capture-inspection.v18"
from scripts.game_data.collision_capture_queries import EVENT_ROLES as QUERY_EVENT_ROLES
EVENT_ROLES = ROLES[:9] + ("child_colliders", "child_collider", "physics_simulate", "physics_complete", "physics_collider", "contact_header", "contact_pair") + QUERY_EVENT_ROLES + ("ecs_decode","ecs_resource","ecs_terrain_resource","ecs_record_entity","ecs_resource_object","ecs_source_box","ecs_source_mesh","ecs_source_multi","ecs_source_terrain","ecs_source_complex","ecs_owner_after_source")
EVENT_ROLES += ("triangle_geometry_getter","live_mesh_cache","pgs_contact_prepare","tgs_contact_prepare","solver_pair_before_prepare","solver_pair_after_prepare",
                "pgs_contact_solve","pgs_static_solve","pgs_contact4_solve","pgs_static4_solve","pgs_friction_contact_solve","pgs_friction_static_solve","pgs_friction_contact4_solve","pgs_friction_static4_solve","tgs_contact_solve","tgs_contact4_solve","solver_pair_after_solve","tgs_extended_contact_solve")
EVENT_ROLES += ("scene_dynamics_update","pgs_dynamics_update","tgs_dynamics_update","original_island_decision")
EVENT_ROLES += ('geometry_arrays','current_geometry_pose','scene_simulation_generation','task_manager_release','task_atomic_decision','task_worker_run')
EVENT_ROLES += ('body_shape_scene_state',)
EVENT_ROLES += ('pair_prefilter','pair_shader','pair_layer_exclusion','pair_object_exclusion','scene_pair_policy','pair_body_owner','pair_shader_dispatch')
EVENT_ROLES += ('task_dependencies','filter_task_producer','live_body_kinematic','live_body_force','live_body_sleeping','destructible_break','live_body_pair_recheck','native_scene_simulate','native_scene_collide','update_shapes_producer','destructible_load_data','interactive_physics_break','destructible_prepare_attack','destructible_attack_callback','destructible_manager_submit')
EVENT_ROLES += ('solver_task_release','solver_task_atomic','solver_task_run','solver_task_base_release')


def _json(path: Path, limit=64*1024*1024) -> dict:
    if not path.is_file() or path.stat().st_size>limit:
        raise ValueError("missing/oversized JSON:"+str(path))
    value=json.loads(path.read_text("utf-8"))
    if not isinstance(value,dict):
        raise ValueError("JSON root is not an object:"+str(path))
    return value


def _require(value: bool, message: str):
    if not value:
        raise ValueError(message)


def _bytes(text, width, label):
    _require(isinstance(text,str) and len(text)==width*2, "byte width:"+label)
    try: raw=bytes.fromhex(text)
    except ValueError as exc: raise ValueError("invalid hex:"+label) from exc
    _require(len(raw)==width and raw.hex()==text, "noncanonical hex:"+label)
    return raw


def _u64(value):
    return int.from_bytes(_bytes(value,8,"u64"),"little")


def _text(value):
    return _bytes(value,128,"UTF16").decode("utf-16-le").split("\0",1)[0]


def _floats(raw):
    # Preserve every float bit; a nonfinite matrix is an observation, not a
    # usable transform or a reason to replace it with an identity matrix.
    import math
    return [f if math.isfinite(f) else dict(float32BitsHex=raw[n*4:n*4+4].hex(),special="nonfinite")
            for n,f in enumerate(struct.unpack("<"+"f"*(len(raw)//4),raw))]


def _origin(value, *, required=True):
    state,index=value["state"],value["fileIndex"]
    path=_u64(value["pathIdHex"])
    text=_bytes(value["filenameHex"],512,"serialized filename")
    _require(type(state) is int and type(index) is int and -1<=index<1048576,"serialized identity scalars")
    _require(value.get("check")==0,"serialized provenance diagnostic check failed")
    _require(state in ((1,2,4) if required else (0,)),"serialized provenance reader failed/unobserved")
    if state!=1:
        _require(index==-1 and path==0 and not any(text),"absent serialized identity carries values")
        return dict(status="no_serialized_entry" if state==2 else "read_lock_busy" if state==4 else "not_applicable")
    head,zero,tail=text.partition(b"\0")
    _require(index>=0 and bool(head) and bool(zero) and not any(tail),"serialized filename framing")
    filename=head.decode("utf-8")
    cabs=sorted(set(m.lower() for m in re.findall(r"(?<![\w-])CAB-[0-9a-fA-F]{32}(?![\w-])",filename)))
    return dict(status="mapped",fileIndex=index,pathId=str(path),pathIdSigned=str(path if path<1<<63 else path-(1<<64)),
                serializedFilename=filename,cab=cabs[0] if len(cabs)==1 else None,
                boundary="direct: instance-ID map and serialized filename table copied in one native critical-section scope")


def _mesh_join(origin,profile):
    if origin["status"]!="mapped" or not origin["cab"]:
        return dict(status="unjoined",reason="no serialized CAB/PathID observation")
    matches={json.dumps(row["mesh"],sort_keys=True):row for row in profile["target"]["colliderBindings"]
             if row["mesh"]["sourceFile"].lower()==origin["cab"] and str(row["mesh"]["pathId"] & ((1<<64)-1))==origin["pathId"]}
    if len(matches)!=1:
        return dict(status="unjoined",reason="runtime CAB/PathID absent or ambiguous in frozen selected source bindings",matches=len(matches))
    row=next(iter(matches.values()))
    return dict(status="matched_frozen_source",mesh=row["mesh"],meshRawSha256=row["meshRawSha256"],cookedBuffers=row["cookedBuffers"],
                boundary="conditional: exact runtime CAB/PathID agrees with one authenticated frozen selected mesh source; no cooked geometry or contact observation")


def _captured_fields(profile, type_name, raw, formats):
    """Decode captured values using the already authenticated field layout."""
    rows=[row for row in profile["types"] if row["type"]==type_name]
    _require(len(rows)==1 and rows[0]["size"]==len(raw),"captured value layout:"+type_name)
    fields={field["name"]:field for field in rows[0]["fields"]}
    result={}
    for name,fmt in formats.items():
        _require(name in fields,"captured value field:"+type_name+"."+name)
        offset=fields[name]["offset"]
        _require(type(offset) is int and 0<=offset<=len(raw)-struct.calcsize("<"+fmt),
                 "captured value field bounds:"+type_name+"."+name)
        value=struct.unpack_from("<"+fmt,raw,offset)[0]
        if fields[name]["type"]=="bool":
            _require(value in (0,1),"captured bool value:"+type_name+"."+name)
            value=bool(value)
        elif fmt=="Q":
            value=str(value)
        result[name]=value
    return result


def _model_comp(profile, raw):
    return _captured_fields(profile,"Beyond.Gameplay.Core.DynamicScene.ModelCompData",raw,
                            dict(rootGridIndex="I",currentLod="i",asyncInstantiateHandle="I",
                                 status="B",enableState="B",invalid="B",hasLoad="B"))


def _context(profile, raw):
    return _captured_fields(profile,"Beyond.Gameplay.Core.DynamicScene.ElementDealContext",raw,
                            dict(elementId="Q",groupId="Q",gridIndex="i",gridId="I",hotSlot="H",
                                 coldSlot="H",forceSync="B",holdLoad="B",holdUnload="B"))


def validate_native_profile(profile: dict, game_root: Path | None):
    files=profile["files"]
    directory=game_root
    if directory and directory.name=="Endfield_Data": directory=directory.parent
    paths={name: directory/row["relativePath"] if directory else Path(row["path"]) for name,row in files.items()}
    gate=check_installed_native_inputs(files["gameAssembly"]["sha256"],files["metadata"]["sha256"],
                                      gameassembly=paths["gameAssembly"],metadata=paths["metadata"])
    _require(gate.status=="validated","installed_native_inputs:"+gate.status+":"+gate.detail)
    for name,path in paths.items():
        _require(path.stat().st_size==files[name]["bytes"] and sha256_file(path).upper()==files[name]["sha256"].upper(),
                 "selected native file changed:"+name)
    image=open_native_image(paths["gameAssembly"],paths["metadata"])
    methods=validate_contract(image,profile)
    _require(methods==profile["methods"],"saved native method/ABI declarations differ")
    _require(_apis(image,profile["apis"] if profile["schema"]!="endfieldCapture.collisionBuild.v1" else None)==profile["apis"],"saved public C API declarations differ")
    if profile["schema"] in ("endfieldCapture.collisionBuild.v3","endfieldCapture.collisionBuild.v4","endfieldCapture.collisionBuild.v5","endfieldCapture.collisionBuild.v6","endfieldCapture.collisionBuild.v7","endfieldCapture.collisionBuild.v8","endfieldCapture.collisionBuild.v9","endfieldCapture.collisionBuild.v10","endfieldCapture.collisionBuild.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        _require(validate_player(paths["unityPlayer"],profile)==profile["playerMethods"],"saved native player declarations differ")
    if profile["schema"] in ("endfieldCapture.collisionBuild.v6","endfieldCapture.collisionBuild.v7","endfieldCapture.collisionBuild.v8","endfieldCapture.collisionBuild.v9","endfieldCapture.collisionBuild.v10","endfieldCapture.collisionBuild.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_runtime_mesh_native import validate_layout
        from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH
        from scripts.game_data.il2cpp.protocol import load_native_mapper
        pe=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(paths["unityPlayer"])
        _require(profile["contactAttachment"]["nativeInputs"]=={k:v.lower() for k,v in dict(gameAssemblySha256=files['gameAssembly']['sha256'],metadataSha256=files['metadata']['sha256'],unityPlayerSha256=files['unityPlayer']['sha256']).items()},"attachment native inputs differ")
        validate_layout(pe,profile["contactAttachment"],schema="endfield.collision-runtime-shape-native-contract.v1")
        expected=[dict(role="attachment:"+r["role"],rva=r["rva"],expectedBytes=pe.bytes_at_va(pe.image_base+r["rva"],r["bytes"]).hex()) for r in profile["contactAttachment"]["codeWindows"]]
        _require(profile["attachmentPins"]==expected,"attachment runtime pins differ")
    if profile['schema'] in ('endfieldCapture.collisionBuild.v7','endfieldCapture.collisionBuild.v8','endfieldCapture.collisionBuild.v9','endfieldCapture.collisionBuild.v10','endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_query_native import validate_image
        q=profile['queryCapture']
        _require(q['contract']['nativeInputs']==profile['contactAttachment']['nativeInputs'], 'query native inputs differ')
        checked=validate_image(image,pe,q['contract'])
        _require(checked['hooks']==q['hooks'] and checked['pins']==q['pins'], 'saved query ABI/binding pins differ')
    if profile['schema'] in ('endfieldCapture.collisionBuild.v8','endfieldCapture.collisionBuild.v9','endfieldCapture.collisionBuild.v10','endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_ecs_capture_native import load
        checked=load(pe,profile['contactAttachment']['nativeInputs'])
        _require(checked==profile['ecsCapture'],'saved ECS observer declarations differ')
        _require(profile['queryCallerPolicy']=='reviewed-native-callee-and-live-cache','query caller policy differs')
    if profile['schema'] in ('endfieldCapture.collisionBuild.v10','endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_physics_stage_native import validate_image
        stage=profile['stageCapture']
        _require(stage['contract']['nativeInputs']==profile['contactAttachment']['nativeInputs'],'stage native inputs differ')
        _require(validate_image(pe,stage['contract'],cache_layout=stage['cacheLayout'])==stage,'saved stage ABI/hook declarations differ')
    if profile['schema'] in ('endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_solver_dispatch_native import validate_capture
        dispatch=profile['dispatchCapture']
        _require(dispatch['contract']['nativeInputs']==profile['contactAttachment']['nativeInputs'],'dispatch native inputs differ')
        _require(validate_capture(pe,dispatch['contract'])==dispatch,'saved dispatch ABI/hook declarations differ')
    if profile['schema']in ('endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_geometry_state_native import validate
        detail=profile['detailCapture']
        _require(detail['contract']['nativeInputs']==profile['contactAttachment']['nativeInputs'],'detail native inputs differ')
        _require(validate(pe,detail['contract'])==detail,'saved geometry/task declarations differ')
    if profile['schema'] in ('endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_body_state_native import validate as validate_body
        body=profile['bodyCapture']
        _require(body['contract']['nativeInputs']==profile['contactAttachment']['nativeInputs'],'body native inputs differ')
        _require(validate_body(pe,body['contract'])==body,'saved body state declarations differ')
    if profile['schema'] in ('endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_pair_filter_native import load as load_pair, capture_declarations
        contract,gate=load_pair(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
        _require(contract is not None,'pair-filter native gate:'+gate['status'])
        _require(capture_declarations(pe,contract)==profile['pairCapture'],'saved pair filter ABI/read declarations differ')

    if profile['schema'] in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
        from scripts.game_data.collision_pair_step_native import capture_declarations as task_declarations
        from scripts.game_data.collision_live_body_native import load as load_live
        life=profile['lifecycleCapture']
        task=task_declarations(pe,life['task']['contract']);body=load_live(image,pe,profile['contactAttachment']['nativeInputs'])
        expected=dict(task=task,body=body,hooks=sorted(task['hooks']+body['hooks'],key=lambda h:h['kind']),pins=task['pins']+body['pins'])
        if profile['schema'] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_activation_capture_native import load as load_activation
            activation=load_activation(image,profile['contactAttachment']['nativeInputs'],life['activation']['contract'])
            expected.update(activation=activation,hooks=sorted(expected['hooks']+activation['hooks'],key=lambda h:h['kind']),pins=expected['pins']+activation['pins'])
        if profile['schema']=='endfieldCapture.collisionBuild.v17':
            from scripts.game_data.collision_solver_task_native import capture_declarations as solver_declarations
            solver=solver_declarations(pe,life['solver']['contract'])
            expected.update(solver=solver,hooks=sorted(expected['hooks']+solver['hooks'],key=lambda h:h['kind']),pins=expected['pins']+solver['pins'])
        _require(expected==life,'saved lifecycle/body declarations differ')


def inspect(root: Path, *, game_root: Path | None=None) -> dict:
    report=dict(schema=SCHEMA,status="failed",session=str(root.resolve()),observations=[],diagnostics=[])
    try:
        root=root.resolve(strict=True)
        session=_json(root/"session.json")
        profile_path=root/"private/collision-build.json"
        profile=_json(profile_path)
        _require(session["schema"]=="endfieldCapture.collisionSession.v1" and profile["schema"] in ("endfieldCapture.collisionBuild.v1","endfieldCapture.collisionBuild.v2","endfieldCapture.collisionBuild.v3","endfieldCapture.collisionBuild.v4","endfieldCapture.collisionBuild.v5","endfieldCapture.collisionBuild.v6","endfieldCapture.collisionBuild.v7","endfieldCapture.collisionBuild.v8","endfieldCapture.collisionBuild.v9","endfieldCapture.collisionBuild.v10","endfieldCapture.collisionBuild.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') and profile["status"]=="validated",
                 "session/profile schema or preflight status")
        _require(sha256_file(profile_path).lower()==session["profileSha256"].lower(),"frozen profile hash differs")
        runtime=root/"private/EndfieldCollisionCapture.dll"
        _require(sha256_file(runtime).lower()==session["runtimeSha256"].lower(),"staged runtime hash differs")
        config=(root/"private/collision.conf").read_bytes()
        _require(len(config)==40,"bootstrap wire size")
        sid,creation,pid,version,nonce=struct.unpack("<QQII16s",config)
        _require((sid,creation,pid,version)==(session["sessionId"],session["creationTime"],session["pid"],1) and sid>0 and pid>0 and any(nonce),"bootstrap identity differs")
        _require(all((root/name).is_file() for name in ("runtime.ready","capture.complete","host.stopped")) and not (root/"runtime.error").exists(),"session is incomplete or runtime failed")
        _require(not (root/"strict-fatal.txt").exists() or (root/"strict-fatal.txt").stat().st_size==0,"strict transaction recovery occurred")
        for source in profile["sources"]:
            leaf=source["archiveName"]
            _require(Path(leaf).name==leaf,"archive source path escapes")
            path=root/"static-sources"/leaf
            _require(path.stat().st_size==source["bytes"] and sha256_file(path).lower()==source["sha256"].lower(),"frozen source differs:"+leaf)
        validate_native_profile(profile,game_root)
        receipt=_json(root/"receipt.json")
        detail_version=profile['schema']in ('endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17')
        dispatch_version=profile['schema'] in ('endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17')
        stage_version=profile["schema"] in ("endfieldCapture.collisionBuild.v10","endfieldCapture.collisionBuild.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17')
        compact_version=stage_version or profile["schema"]=="endfieldCapture.collisionBuild.v9"
        ecs_version=compact_version or profile["schema"]=="endfieldCapture.collisionBuild.v8"
        query_version=ecs_version or profile["schema"]=="endfieldCapture.collisionBuild.v7"
        contact_version=query_version or profile["schema"]=="endfieldCapture.collisionBuild.v6"
        native_simulation=contact_version or profile["schema"]=="endfieldCapture.collisionBuild.v5"
        memory_version=native_simulation or profile["schema"]=="endfieldCapture.collisionBuild.v4"
        later_version=memory_version or profile["schema"]=="endfieldCapture.collisionBuild.v3"
        child_version=profile["schema"]!="endfieldCapture.collisionBuild.v1"
        pair_version=profile['schema'] in ('endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17')
        _require(receipt["schema"]==("endfieldCapture.collisionReceipt.v17" if profile["schema"]=="endfieldCapture.collisionBuild.v17" else "endfieldCapture.collisionReceipt.v16" if profile["schema"] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else "endfieldCapture.collisionReceipt.v15" if profile["schema"] in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else "endfieldCapture.collisionReceipt.v14" if profile["schema"] in ("endfieldCapture.collisionBuild.v14",'endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else "endfieldCapture.collisionReceipt.v13" if profile["schema"] in ('endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else "endfieldCapture.collisionReceipt.v12" if detail_version else "endfieldCapture.collisionReceipt.v11" if dispatch_version else "endfieldCapture.collisionReceipt.v10" if stage_version else "endfieldCapture.collisionReceipt.v9" if compact_version else "endfieldCapture.collisionReceipt.v8" if ecs_version else "endfieldCapture.collisionReceipt.v7" if query_version else "endfieldCapture.collisionReceipt.v6" if contact_version else "endfieldCapture.collisionReceipt.v5" if native_simulation else "endfieldCapture.collisionReceipt.v4" if memory_version else "endfieldCapture.collisionReceipt.v3" if later_version else "endfieldCapture.collisionReceipt.v2" if child_version else "endfieldCapture.collisionReceipt.v1") and receipt["complete"] is True and receipt["hooksInstalled"] is True and receipt["quiescent"] is True and receipt["writerOk"] is True,"provider completion gates failed")
        for key in ("dropped","unreadable","abandoned","trackingOverflow","activeCallbacks"):
            _require(type(receipt[key]) is int and receipt[key]==0,"provider loss/read/cleanup gate:"+key)
        for key in ("rows","calls","admitted"):
            _require(type(receipt[key]) is int and 0<=receipt[key]<=(profile["ecsCapture"]["contract"]["limits"]["maxRows"] if ecs_version else 200000),"provider count bound:"+key)
        _require(isinstance(receipt["entered"],list) and len(receipt["entered"])==(12+len(profile["queryCapture"]["hooks"])+(len(profile["ecsCapture"]["hooks"]) if ecs_version else 0)+(len(profile["stageCapture"]["hooks"]) if stage_version else 0)+(len(profile["dispatchCapture"]["hooks"]) if dispatch_version else 0)+(len(profile['detailCapture']['hooks']) if detail_version else 0)+(len(profile['pairCapture']['hooks']) if pair_version else 0)+(len(profile['lifecycleCapture']['hooks']) if profile['schema'] in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else 0) if query_version else 12 if contact_version else 11 if later_version else 9) and all(type(n) is int and n>=0 for n in receipt["entered"]),"hook entry census")
        if compact_version:
            q=receipt['eventQueue'];expected=profile['transport']['queueCapacity']
            _require(q['capacity']==expected and type(q['highWater']) is int and 0<=q['highWater']<=expected and
                     q['full']==q['contention']==0,'event transport queue diagnostics')
        for key in ("enableStatus","disableStatus"):
            _require(receipt[key]["stage"]==0 and receipt[key]["pendingRecovery"] is False and receipt[key]["cleanupSucceeded"] is True,"strict transaction gate:"+key)
        journal=root/"events.jsonl"
        _require(journal.stat().st_size<=(4*1024*1024*1024 if ecs_version else 512*1024*1024),"journal exceeds byte bound")
        calls={};stacks={};coverage=Counter();observations=[]
        raw_models={row["rawModelHex"]:row for row in profile["targetModels"]}
        _require(len(raw_models)==len(profile["targetModels"]),"selected source Model bytes are ambiguous")
        count=0
        with journal.open(encoding="utf-8") as handle:
            for count,line in enumerate(handle,1):
                _require(count<=(profile["ecsCapture"]["contract"]["limits"]["maxRows"] if ecs_version else 200000) and len(line)<=8192 and line.endswith("\n"),"journal framing/row bound")
                row=json.loads(line)
                if compact_version:
                    from scripts.game_data.collision_capture_events import expand
                    row=expand(row,profile["transport"]["eventFormat"])
                _require(row["sequence"]==count and (row["flags"] & ~768 == 0 if stage_version and row["kind"]>=48 else row["flags"]==0),"journal sequence/read flags")
                kind,phase,call,thread,parent=(row[k] for k in ("kind","phase","call","thread","parent"))
                _require(all(type(n) is int for n in (kind,phase,call,thread,parent)) and 0<=kind<(103 if profile["schema"]=="endfieldCapture.collisionBuild.v17" else 99 if profile["schema"] in ('endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else 91 if profile["schema"] in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else 84 if profile["schema"] in ("endfieldCapture.collisionBuild.v14",'endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else 77 if profile["schema"] in ('endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else 76 if detail_version else 70 if dispatch_version else 66 if stage_version else 48 if ecs_version else 37 if query_version else 16 if contact_version else 14 if later_version else 11 if child_version else 9) and phase in (0,1) and call>0 and thread>0,"event identity")
                _require(type(row["sequence"]) is int and type(row["qpc"]) is int and row["qpc"]>=0 and type(row["flags"]) is int,"event scalar types")
                _require(isinstance(row["args"],list) and len(row["args"])==8,"argument slots")
                args=[_u64(value) for value in row["args"]]
                model=_bytes(row["model"],96,"Model").hex()
                before=_bytes(row["before"],64,"before")
                after=_bytes(row["after"],128,"after")
                world=_bytes(row["world"],64,"world")
                scene,name=_text(row["sceneUtf16"]),_text(row["nameUtf16"])
                result=_u64(row["result"])
                _require(row["queryState"] in (range(256) if stage_version and kind>=48 else (0,1,2,3,4) if ecs_version and kind>=37 else (0,1,2,4) if kind==13 or kind>=16 else (0,1,2)) and row["active"] in (0,1) and row["enabled"] in (0,1) and row["convex"] in (0,1),"query state")
                stack=stacks.setdefault(thread,[])
                if phase==0:
                    _require(call not in calls and parent==(stack[-1] if stack else 0),"duplicate call or invalid same-thread nesting")
                    calls[call]=row
                    stack.append(call)
                    continue
                _require(call in calls and stack and stack[-1]==call,"unpaired/non-nested return")
                entry=calls[call]
                _require(all(entry[key]==row[key] for key in ("kind","thread","parent","args","model","before","sceneUtf16")) and (kind!=4 or entry["nameUtf16"]==row["nameUtf16"]) and row["qpc"]>=entry["qpc"],"paired input identity differs")
                stack.pop()
                _require("returned" not in entry,"duplicate return")
                entry["returned"]=True
                entry["returnRecord"]=row
                coverage[EVENT_ROLES[kind]]+=1
                if kind in (3,6):_require(result==args[0],"hidden result carrier differs")
                if kind<9:_require(receipt["entered"][kind]>=coverage[EVENT_ROLES[kind]],"hook entry census below paired observations")
                observed=dict(call=call,parentCall=parent,thread=thread,kind=EVENT_ROLES[kind],scene=scene,
                              boundary="query/filter/buffer/guard observation; typed details require query admission" if kind>=16 else
                                       "native finalizer normal return before report dispatch/cleanup" if kind==14 else
                                       "raw pair sampled inside finalized-header observer before dispatch/cleanup" if kind==15 else
                                       "observer-generated sample after original instantiation returned; separately timed reads" if kind>=9 else "paired entry/normal return; separately timed post-setter reads")
                source=raw_models.get(model) if kind!=64 else None
                if source:
                    observed["storedModel"]=dict(source=source["source"],gridOrdinal=source["gridOrdinal"],uniqueId=source["uniqueId"],ordinal=source["ordinal"],guid=source["values"]["Guid"],byteOffset=source["byteOffset"],pathHashHex=source["pathHashHex"])
                elif model!=bytes(96).hex() and kind!=64:
                    observed["sourceGap"]="live Model bytes absent from the frozen target source set"
                if kind in (0,1):
                    observed["modelCompBefore"]=_model_comp(profile,before[32:52] if kind==1 else before[:20])
                    observed["modelCompAfter"]=_model_comp(profile,after[:20])
                if kind==1:
                    observed["elementContext"]=_context(profile,before[:32])
                    observed["runtimeElementId"]=observed["elementContext"]["elementId"]
                    if child_version:
                        original_return_qpc=struct.unpack_from("<Q",after,64)[0]
                        _require(entry["qpc"]<=original_return_qpc<=row["qpc"],"original instantiation return timestamp bound")
                        observed["originalReturnQpc"]=original_return_qpc
                if kind==2:
                    observed["outputPositionRotationScale"]=_floats(after[:36])
                    if source:
                        trans=source["values"]["Trans"]
                        stored=[trans[member][axis] for member in ("Pos","Rot","Scl") for axis in ("X","Y","Z")]
                        observed["storedPositionRotationScale"]=stored
                        observed["outputMatchesStoredTransformBits"]=struct.pack("<9f",*stored)==after[:36]
                if kind==3:observed.update(runtimeUniqueId=args[2],matrixColumnMajor=_floats(after[:64]),matrixAllZero=not any(after[:64]))
                if kind==4:observed.update(registrationName=name,direction=args[2] if args[2]<0x80000000 else args[2]-0x100000000,runtimeUniqueId=result,position=_floats(before[:12]),minPosition=_floats(_bytes(row["args"][4],8,"registration min")),maxPosition=_floats(_bytes(row["args"][5],8,"registration max")))
                if kind==6:observed.update(requestedPathHashHex=f"{args[2]:016X}",handleHex=after[:20].hex())
                if kind in (7,8):
                    observed["queryStatus"]="observed_after_setter_return" if row["queryState"]==1 else "skipped_off_main_thread" if row["queryState"]==2 else "unobserved"
                    if row["queryState"]==1:
                        observed.update(objectInstanceId=row["objectId"],gameObjectInstanceId=row["goId"],transformPointer=row["transform"],worldMatrixColumnMajor=_floats(world),activeInHierarchy=bool(row["active"]))
                        if kind==7:observed.update(parentPointer=row["args"][1],worldPositionStays=bool(args[2]))
                        else:observed.update(enabled=bool(row["enabled"]),meshPointer=row["mesh"],meshInstanceId=row["meshId"],meshName=name,convex=bool(row["convex"]))
                if kind in (9,10):
                    _require(row["queryState"] in (1,2),"child snapshot failed or has invalid state")
                    observed["queryStatus"]="observed_after_instantiation_return" if row["queryState"]==1 else "skipped_off_main_thread"
                    if row["queryState"]==1:
                        _require(_u64(row["go"])>0 and _u64(row["transform"])>0,"child snapshot object/transform missing")
                        observed.update(objectInstanceId=row["objectId"],gameObjectInstanceId=row["goId"],gameObjectPointer=row["go"],transformPointer=row["transform"],worldMatrixColumnMajor=_floats(world),activeInHierarchy=bool(row["active"]))
                    if kind==9:
                        _require(parent in calls and calls[parent]["kind"]==1 and row["model"]==calls[parent]["model"],"child summary lacks selected instantiation parent")
                        component_count,collider_count=struct.unpack_from("<QQ",after)
                        _require(component_count<=profile["childSnapshots"]["maxComponents"] and collider_count<=profile["childSnapshots"]["maxColliders"] and collider_count<=component_count,"child snapshot count bound")
                        if row["queryState"]==2:_require(component_count==collider_count==0,"off-main-thread child counts")
                        observed.update(rootTransformPointer=row["args"][0],rootGameObjectPointer=row["args"][1],componentCount=component_count,colliderCount=collider_count,includeInactive=True)
                    else:
                        _require(parent in calls and calls[parent]["kind"]==9 and row["model"]==calls[parent]["model"] and row["args"][1]==calls[parent]["args"][1],"child collider lacks selected root parent")
                        _require(row["queryState"]==1 and args[5] in (0,1),"child collider query/type state")
                        type_name,zero,tail=before.partition(b"\0")
                        _require(bool(type_name) and bool(zero) and not any(tail),"child collider type text bound")
                        type_name=type_name.decode("ascii")
                        observed.update(colliderPointer=row["args"][0],rootGameObjectPointer=row["args"][1],componentIndex=args[2],enumeratedComponentCount=args[3],colliderOrdinal=args[4],colliderType=type_name,isMeshCollider=bool(args[5]),enabled=bool(row["enabled"]))
                        if args[5]:observed.update(meshPointer=row["mesh"],meshInstanceId=row["meshId"],meshName=name,convex=bool(row["convex"]))
                        if later_version:
                            observed.update(retainedOriginCall=struct.unpack_from("<Q",after,24)[0],enrollmentQpc=struct.unpack_from("<Q",after,32)[0])
                if kind==11:
                    _require(receipt["entered"][9]>=coverage["physics_simulate"],"physics hook census")
                    completed=struct.unpack_from("<I",after,16)[0]
                    original_return=struct.unpack_from("<Q",after)[0]
                    _require(entry["qpc"]<=original_return<=row["qpc"],"physics original return timestamp")
                    _require(args[1]<=0xffffffff,"physics step float32 carrier")
                    _require(args[0]<=0xffffffff,"physics scene uint32 carrier")
                    delta=struct.unpack("<f",struct.pack("<I",args[1]))[0]
                    import math
                    _require(math.isfinite(delta) and delta>0,"physics step was not finite/positive")
                    observed.update(sceneHandle=args[0],stepSeconds=delta,nativeCompletionCount=completed,originalReturnQpc=original_return,
                                    nativeScenePointer=after[8:16].hex(),simulationRole="physics_core" if native_simulation else "physics_simulate",
                                    boundary="conditional: native simulation core normal return; completion is independently witnessed" if native_simulation else "conditional: manual simulation normal return; completion is independently witnessed")
                    if native_simulation:observed["nativeManagerPointer"]=row["args"][2]
                if kind==12:
                    _require(parent in calls and calls[parent]["kind"]==11 and receipt["entered"][10]>=coverage["physics_complete"],"completion lacks admitted simulation parent/census")
                    _require(args[0]>0 and args[1]==_u64(receipt["playerBase"])+profile["physicsSnapshots"]["completionReturnRva"],"completion return-address witness differs")
                    observed.update(nativeScenePointer=row["args"][0],boundary="direct: original native completion function returned at the authenticated simulation-core call site")
                if kind==13:
                    _require(parent in calls and calls[parent]["kind"]==11 and row["queryState"] in (1,4),"later collider lacks simulation parent/state")
                    observed.update(originChildCall=args[2],completedStepOrdinal=args[3],enrollmentQpc=args[4],sceneHandle=args[5],
                                    colliderPointer=row["args"][0],rootGameObjectPointer=row["args"][1],
                                    queryStatus="observed_after_completed_physics_return" if row["queryState"]==1 else "destroyed_or_replaced",
                                    boundary="conditional: separately timed retained-object read after one native completion and outer original normal return")
                    if row["queryState"]==1:
                        observed.update(objectInstanceId=row["objectId"],gameObjectInstanceId=row["goId"],gameObjectPointer=row["go"],transformPointer=row["transform"],worldMatrixColumnMajor=_floats(world),activeInHierarchy=bool(row["active"]),enabled=bool(row["enabled"]),meshPointer=row["mesh"],meshInstanceId=row["meshId"],meshName=name,convex=bool(row["convex"]))
                if later_version and kind in (10,13) and row["queryState"]==1:
                    observed["colliderProvenance"]=_origin(row["colliderOrigin"])
                    observed["meshProvenance"]=_origin(row["meshOrigin"],required=bool(_u64(row["mesh"])))
                    observed["meshSourceJoin"]=_mesh_join(observed["meshProvenance"],profile)
                observations.append(observed)
        _require(not any(stacks.values()) and all(row.get("returned") for row in calls.values()),"open calls at stop")
        _require(set(calls)==set(range(1,len(calls)+1)) and count==receipt["rows"]==receipt["admitted"]==receipt["calls"]*2 and len(calls)==receipt["calls"],"producer/writer counts differ")
        summaries=[row for row in observations if row["kind"]=="child_colliders"]
        samples=[row for row in observations if row["kind"]=="child_collider"]
        if child_version:
            instantiated={row["call"] for row in observations if row["kind"]=="init_instance"}
            _require(len(summaries)==len(instantiated) and {row["parentCall"] for row in summaries}==instantiated,"selected instantiation child summary missing/duplicate")
            for summary in summaries:
                children=[row for row in samples if row["parentCall"]==summary["call"]]
                _require(len(children)==summary["colliderCount"] and sorted(row["colliderOrdinal"] for row in children)==list(range(len(children))),"child collider samples differ from summary count")
                indices=[row["componentIndex"] for row in children]
                _require(len(set(indices))==len(indices) and all(0<=index<summary["componentCount"] for index in indices) and all(row["enumeratedComponentCount"]==summary["componentCount"] for row in children),"child component indices/counts differ")
                original=calls[summary["parentCall"]]["returnRecord"]
                _require(summary["rootTransformPointer"]==original["transform"] and summary["rootGameObjectPointer"]==original["go"],"child summary root differs from instantiation")
                _require(calls[summary["call"]]["qpc"]>=struct.unpack_from("<Q",_bytes(original["after"],128,"instantiation return"),64)[0],"child snapshot precedes original instantiation return")
                if summary["queryStatus"]=="observed_after_instantiation_return":
                    _require(summary["rootTransformPointer"]==summary["transformPointer"] and summary["rootGameObjectPointer"]==summary["gameObjectPointer"],"child summary queried root differs")
        physics_samples=[r for r in observations if r["kind"]=="physics_collider"]
        if later_version:
            physics_steps=[r for r in observations if r['kind']=='physics_simulate']
            markers_by_step=defaultdict(list)
            samples_by_step=defaultdict(list)
            for r in observations:
                if r['kind']=='physics_complete':markers_by_step[r['parentCall']].append(r)
            for r in physics_samples:samples_by_step[r['parentCall']].append(r)
            by_call={r["call"]:r for r in observations}
            retained={r["retainedOriginCall"] for r in samples}
            _require(0 not in retained,"selected child was not retained")
            for child in samples:
                origin=by_call.get(child["retainedOriginCall"],{})
                _require(origin.get("kind")=="child_collider" and origin["call"]<=child["call"] and
                         all(origin[k]==child[k] for k in ("colliderPointer","rootGameObjectPointer","objectInstanceId","enrollmentQpc")) and
                         calls[origin["call"]]["qpc"]<=child["enrollmentQpc"]<=calls[origin["call"]]["returnRecord"]["qpc"],"retained enrollment identity/timestamp differs")
            for step in physics_steps:
                markers=markers_by_step.get(step['call'],[])
                _require(len(markers)==step["nativeCompletionCount"],"physics completion count differs from paired native markers")
                if markers:
                    _require(markers[-1]["nativeScenePointer"]==step["nativeScenePointer"] and all(calls[r["call"]]["returnRecord"]["qpc"]<=step["originalReturnQpc"] for r in markers),"physics marker scene/return timing differs")
                children=samples_by_step.get(step['call'],[])
                _require(not children or len(markers)==1,"later snapshot has no unique completed simulation")
            for sample in physics_samples:
                origin=by_call.get(sample["originChildCall"],{})
                step=by_call[sample["parentCall"]]
                _require(origin.get("kind")=="child_collider" and sample["originChildCall"] in retained and
                         sample["completedStepOrdinal"] in profile["physicsSnapshots"]["completedStepOrdinals"] and
                         all(sample[k]==origin[k] for k in ("colliderPointer","rootGameObjectPointer","enrollmentQpc")) and
                         calls[origin["call"]]["model"]==calls[sample["call"]]["model"] and
                         sample["enrollmentQpc"]<calls[step["call"]]["qpc"] and
                         calls[sample["call"]]["qpc"]>=step["originalReturnQpc"] and sample["sceneHandle"]==step["sceneHandle"],"later collider source/enrollment/physics ordering differs")
                if sample["queryStatus"]=="observed_after_completed_physics_return":
                    _require(all(sample[k]==origin[k] for k in ("objectInstanceId","gameObjectInstanceId","gameObjectPointer","transformPointer")),"retained object identity changed without lifetime gap")
                completed_steps=sum(r["nativeCompletionCount"]==1 and calls[r["call"]]["qpc"]>sample["enrollmentQpc"] and
                                    (r["originalReturnQpc"],r["call"])<=(step["originalReturnQpc"],step["call"])
                                    for r in physics_steps)
                _require(completed_steps==sample["completedStepOrdinal"],"later collider ordinal differs from witnessed completed-step census")
            for origin in retained:
                rows=[r for r in physics_samples if r["originChildCall"]==origin]
                ordinals=profile["physicsSnapshots"]["completedStepOrdinals"]
                _require([r["completedStepOrdinal"] for r in rows]==ordinals[:len(rows)],"later collider ordinals duplicated/out of order")
                _require(not any(r["queryStatus"]=="destroyed_or_replaced" for r in rows[:-1]),"later reads after destroyed/replaced object")
            checkpoint_pending=sum(not any(r["originChildCall"]==origin and (r["completedStepOrdinal"]==profile["physicsSnapshots"]["completedStepOrdinals"][-1] or r["queryStatus"]=="destroyed_or_replaced") for r in physics_samples) for origin in retained)
            pending=sum(not any(r['originChildCall']==origin and r['queryStatus']=='destroyed_or_replaced' for r in physics_samples) for origin in retained) if contact_version else checkpoint_pending
            _require(all(type(receipt[k]) is int and receipt[k]>=0 for k in ("retained","released","pending","pendingAtStop")) and
                     receipt["retained"]==receipt["released"]==len(retained) and receipt["pending"]==0 and receipt["pendingAtStop"]==pending,"retained handle stop accounting differs")
        gaps=[role for role in ROLES[:9] if not coverage[role]]
        hook_coverage=[dict(kind=role,entries=receipt["entered"][n],pairedSelectedCalls=coverage[role],
                            status="observed" if coverage[role] else "entered_outside_selection" if receipt["entered"][n] else "no_entries")
                       for n,role in enumerate(ROLES[:9])]
        report.update(status="validated",observations=observations,coverage=dict(coverage),unobservedHooks=gaps,rows=count,
                      hookCoverage=hook_coverage,
                      pairedGameCalls=sum(coverage[role] for role in ROLES[:9]),pairedObserverSamples=len(summaries)+len(samples),
                      childSnapshotCoverage=dict(summaries=len(summaries),complete=sum(row["queryStatus"]=="observed_after_instantiation_return" for row in summaries),offMainThreadSkipped=sum(row["queryStatus"]=="skipped_off_main_thread" for row in summaries),colliders=len(samples),enabled=child_version),
                      selectedSourceModelsObserved=sum("storedModel" in row and row["kind"]=="init_instance" for row in observations),
                      nativeGate="validated",journalSha256=sha256_file(journal),
                      evidenceBoundary=profile["evidenceBoundary"],
                      remainingGaps=["No selected collider snapshot was captured; parenting observations do not establish child collider state."]*(not coverage["collider_set"] and not any(row["queryStatus"]=="observed_after_instantiation_return" for row in summaries))+
                                    ["Collider destruction/reuse and state at the next physics step remain unobserved.",
                                     "Mesh pointer, instance ID and name do not establish a physical CAB/PathID identity."])
        if later_version:
            report["hookCoverage"]+= [dict(kind=role,entries=receipt["entered"][n],pairedSelectedCalls=coverage[role],
                    nativeRole="physics_core" if native_simulation and n==9 else role,
                    status="observed" if coverage[role] else "entered_outside_selection" if receipt["entered"][n] else "no_entries") for n,role in ((9,"physics_simulate"),(10,"physics_complete"))]
            report["pairedGameCalls"]+=coverage["physics_simulate"]+coverage["physics_complete"]
            report["pairedObserverSamples"]+=len(physics_samples)
            report["physicsSnapshotCoverage"]=dict(retained=len(retained),samples=len(physics_samples),
                    first=sum(r["completedStepOrdinal"]==1 for r in physics_samples),sixtieth=sum(r["completedStepOrdinal"]==60 for r in physics_samples),
                    checkpoints={str(n):sum(r["completedStepOrdinal"]==n for r in physics_samples) for n in profile["physicsSnapshots"]["completedStepOrdinals"]},
                    lifetimeGaps=sum(r["queryStatus"]=="destroyed_or_replaced" for r in physics_samples),pendingAtStop=pending)
            joins=[r for r in samples if r.get("meshSourceJoin",{}).get("status")=="matched_frozen_source"]
            later_joins=[r for r in physics_samples if r.get("meshSourceJoin",{}).get("status")=="matched_frozen_source"]
            recovered={r["originChildCall"] for r in later_joins if all(r.get(k)==by_call[r["originChildCall"]].get(k) for k in ("meshPointer","meshInstanceId"))}
            unresolved=[r for r in samples if r.get("isMeshCollider") and r not in joins and r["retainedOriginCall"] not in recovered]
            report["provenanceCoverage"]=dict(meshSnapshots=sum(r.get("isMeshCollider",False) for r in samples),matchedSelectedMeshSources=len(joins),matchedLaterMeshSources=len(later_joins),recoveredLaterOrigins=len(recovered))
            report["remainingGaps"]=["Some retained colliders did not reach every requested completed physics checkpoint before stop."]*bool(checkpoint_pending)+[
                "Some selected MeshColliders lack a unique native CAB/PathID join to the frozen mesh source."]*bool(unresolved)+[
                "Observed state belongs to separately timed post-instantiation/post-simulation reads; cooked geometry, contact pairs and any unobserved simulation route remain unresolved."]
        if memory_version:
            report["nativeMemory"]=validate_archive(root/"native-memory.bin",receipt["nativeMemory"],profile["nativeMemory"],calls,stage_contract=profile['stageCapture']['contract'] if stage_version else None,detail_contract=profile['detailCapture']['contract'] if detail_version else None)
            if report["nativeMemory"]["limitedSamples"] or report["nativeMemory"]["dropped"] or report["nativeMemory"]["missingRoots"]:
                report["remainingGaps"].append("Native memory traversal reached explicit limits or failed reads; uncaptured windows remain unknown.")
            if not report["nativeMemory"]["blocks"]:
                report["remainingGaps"].append("No native memory windows were captured.")
        if contact_version:
            from scripts.game_data.collision_capture_contacts import decode_contacts
            report['contacts']=decode_contacts(calls,observations,profile,receipt)
            report['hookCoverage'].append(dict(kind='contact_header',entries=receipt['entered'][11],pairedSelectedCalls=coverage['contact_header']))
            report['pairedGameCalls']+=coverage['contact_header']
            report['pairedObserverSamples']+=coverage['contact_pair']
            report['remainingGaps']+=report['contacts']['gaps']
        if query_version:
            from scripts.game_data.collision_capture_queries import decode_queries
            report['queries']=decode_queries(calls,profile,receipt)
            report['remainingGaps']+=report['queries']['gaps']
            report['pairedGameCalls']+=sum(coverage[EVENT_ROLES[h['kind']]] for h in profile['queryCapture']['hooks'])
            report['pairedObserverSamples']+=coverage['query_hit']+coverage['report_stream']
            for hook in profile['queryCapture']['hooks']:
                index=12+profile['queryCapture']['hooks'].index(hook)
                report['hookCoverage'].append(dict(kind=EVENT_ROLES[hook['kind']],entries=receipt['entered'][index],pairedSelectedCalls=coverage[EVENT_ROLES[hook['kind']]]))
        if ecs_version:
            from scripts.game_data.collision_capture_ecs import decode_ecs
            report['ecs']=decode_ecs(calls,profile,report.get('nativeMemory',{}))
            report['remainingGaps']+=report['ecs']['gaps']
            report['pairedGameCalls']+=sum(coverage[EVENT_ROLES[h['kind']]] for h in profile['ecsCapture']['hooks'])
            report['pairedObserverSamples']+=coverage['ecs_owner_after_source']
            for n,hook in enumerate(profile['ecsCapture']['hooks']):
                report['hookCoverage'].append(dict(kind=EVENT_ROLES[hook['kind']],entries=receipt['entered'][12+len(profile['queryCapture']['hooks'])+n],pairedSelectedCalls=coverage[EVENT_ROLES[hook['kind']]]))
        if stage_version:
            from scripts.game_data.collision_capture_stages import decode_stages
            report['physicsStages']=decode_stages(calls,profile,receipt)
            report['remainingGaps']+=report['physicsStages']['gaps']
            report['pairedGameCalls']+=sum(coverage[EVENT_ROLES[h['kind']]] for h in profile['stageCapture']['hooks'])
            report['pairedObserverSamples']+=sum(coverage[EVENT_ROLES[k]] for k in (49,52,53,64))
            start=12+len(profile['queryCapture']['hooks'])+len(profile['ecsCapture']['hooks'])
            for n,hook in enumerate(profile['stageCapture']['hooks']):
                _require(receipt['entered'][start+n]>=coverage[EVENT_ROLES[hook['kind']]],'stage hook census below selected calls:'+hook['role'])
                report['hookCoverage'].append(dict(kind=EVENT_ROLES[hook['kind']],entries=receipt['entered'][start+n],pairedSelectedCalls=coverage[EVENT_ROLES[hook['kind']]]))
        if dispatch_version:
            from scripts.game_data.collision_capture_dispatch import decode_dispatch
            report['physicsDispatch']=decode_dispatch(calls,profile,receipt)
            report['pairedGameCalls']+=sum(coverage[EVENT_ROLES[h['kind']]] for h in profile['dispatchCapture']['hooks'])
            start=12+len(profile['queryCapture']['hooks'])+len(profile['ecsCapture']['hooks'])+len(profile['stageCapture']['hooks'])
            for n,hook in enumerate(profile['dispatchCapture']['hooks']):
                report['hookCoverage'].append(dict(kind=EVENT_ROLES[hook['kind']],entries=receipt['entered'][start+n],pairedSelectedCalls=coverage[EVENT_ROLES[hook['kind']]]))
        if detail_version:
            from scripts.game_data.collision_capture_geometry_state import decode_geometry_state
            report['geometryState']=decode_geometry_state(calls,profile,receipt,report['nativeMemory'])
            report['pairedGameCalls']+=sum(coverage[EVENT_ROLES[h['kind']]] for h in profile['detailCapture']['hooks'])
            report['pairedObserverSamples']+=coverage['geometry_arrays']+coverage['current_geometry_pose']
            start=12+len(profile['queryCapture']['hooks'])+len(profile['ecsCapture']['hooks'])+len(profile['stageCapture']['hooks'])+len(profile['dispatchCapture']['hooks'])
            for n,hook in enumerate(profile['detailCapture']['hooks']):
                selected=coverage[EVENT_ROLES[hook['kind']]]
                if profile['schema']=='endfieldCapture.collisionBuild.v17' and hook['kind'] in (73,74,75):selected+=coverage[EVENT_ROLES[hook['kind']+26]]
                report['hookCoverage'].append(dict(kind=EVENT_ROLES[hook['kind']],entries=receipt['entered'][start+n],pairedSelectedCalls=selected))
        if profile['schema'] in ('endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_capture_body_state import decode_body_states
            report['bodyStates']=decode_body_states(calls,profile,receipt)
            report['pairedObserverSamples']+=coverage['body_shape_scene_state']
        if pair_version:
            from scripts.game_data.collision_capture_pair_filter import decode_pair_filter
            if profile['schema'] in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
                from scripts.game_data.collision_capture_lifecycle import decode_lifecycle
                report['lifecycle']=decode_lifecycle(calls,profile,receipt,report['geometryState'])
            report['pairFiltering']=decode_pair_filter(calls,profile,receipt,task_routes=report.get('lifecycle',{}).get('taskRoutes'))
            report['pairedGameCalls']+=sum(coverage[EVENT_ROLES[h['kind']]] for h in profile['pairCapture']['hooks'])
            report['pairedObserverSamples']+=coverage['scene_pair_policy']+coverage['pair_body_owner']+coverage['live_body_pair_recheck']
            start=12+sum(len(profile[k]['hooks']) for k in ('queryCapture','ecsCapture','stageCapture','dispatchCapture','detailCapture'))
            for n,hook in enumerate(profile['pairCapture']['hooks']):
                report['hookCoverage'].append(dict(kind=EVENT_ROLES[hook['kind']],entries=receipt['entered'][start+n],pairedSelectedCalls=coverage[EVENT_ROLES[hook['kind']]]))
        if profile['schema']=='endfieldCapture.collisionBuild.v17':
            from scripts.game_data.collision_capture_solver_tasks import decode_solver_tasks
            report['solverTasks']=decode_solver_tasks(calls,profile,receipt)
            report['pairedGameCalls']+=sum(coverage[EVENT_ROLES[k]] for k in (99,100,101))
        if profile['schema'] in ('endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            report['pairedGameCalls']+=sum(coverage[EVENT_ROLES[h['kind']]] for h in profile['lifecycleCapture']['hooks'])
            start=12+sum(len(profile[k]['hooks']) for k in ('queryCapture','ecsCapture','stageCapture','dispatchCapture','detailCapture','pairCapture'))
            for n,hook in enumerate(profile['lifecycleCapture']['hooks']):
                report['hookCoverage'].append(dict(kind=EVENT_ROLES[hook['kind']],entries=receipt['entered'][start+n],pairedSelectedCalls=coverage[EVENT_ROLES[hook['kind']]]))
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,struct.error,RuntimeError) as exc:
        report.update(status="failed",observations=[],diagnostics=[dict(check="saved_collision_session",detail=str(exc)[:1600])])
        report.pop("nativeMemory",None)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session",type=Path,required=True)
    parser.add_argument("--game-root",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    report=inspect(args.session,game_root=args.game_root)
    output=args.output or args.session/"collected/collision-inspection.json"
    if report["status"]!="validated":output=output.with_name(output.stem+".failed.json")
    atomic_write_text(output,json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:report[k] for k in ("status","diagnostics","coverage","selectedSourceModelsObserved","childSnapshotCoverage") if k in report}))
    return 0 if report["status"]=="validated" else 1


if __name__=="__main__":
    raise SystemExit(main())
