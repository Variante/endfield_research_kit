"""Prepare the bounded EndfieldCapture collision observer without attaching.

Native declarations are reviewed versioned data. Generated profiles and C++
headers go under reports; preparation never launches or opens a game process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.pe_exports import resolve_named_exports
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, load_native_mapper
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH
from scripts.game_data.mission_trace_capture_prepare import SelectedMethods
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.collision_capture_memory import validate_policy

CONTRACT = CONTRACTS_DIR / "collision_capture_native.json"
SCHEMA = "endfield.collision-capture-native.v17"
ROLES = ("init_model", "init_instance", "model_transform", "grid_matrix", "register_scene",
         "collider_enable", "prefab_request", "parent", "collider_set", "world_matrix",
         "component_transform", "component_go", "instance_id", "object_name", "mesh", "convex", "active", "enabled", "main_thread",
         "child_components", "array_length", "array_value", "cached_ptr", "physics_simulate")
ARGUMENTS = (("pointer",)*4, ("pointer",)*5, ("pointer","u64","pointer","pointer","pointer","pointer"),
             ("pointer","pointer","u32","pointer"), ("pointer","pointer","i32","pointer","u64","u64","pointer"),
             ("pointer","u64","bool","pointer"), ("pointer","u8","u64","bool","u8","u32","pointer"),
             ("pointer","pointer","bool","pointer"), ("pointer","bool","pointer"), ("pointer",)*3,
             *(("pointer",)*2,)*8, ("pointer",), ("pointer","pointer","bool","pointer"),
             ("pointer","pointer"), ("pointer","i32","pointer"), ("pointer","pointer"), ("u32","f32","pointer"))
RETURNS = ("void","void","void","pointer","u32","void","pointer","void","void","pointer",
           "pointer","pointer","i32","pointer","pointer","bool","bool","bool","bool","pointer","i32","pointer","pointer","void")
LEGACY_APIS = ("il2cpp_object_get_class", "il2cpp_class_get_name", "il2cpp_class_get_namespace", "il2cpp_class_get_parent")
APIS = LEGACY_APIS + ("il2cpp_class_get_image", "il2cpp_class_from_name", "il2cpp_class_get_type",
                      "il2cpp_type_get_object", "il2cpp_gchandle_new", "il2cpp_gchandle_free", "il2cpp_gchandle_get_target")
API_ARGUMENTS = (("pointer",),)*5 + (("pointer",)*3, ("pointer",), ("pointer",), ("pointer","bool"), ("u32",), ("u32",))
API_RETURNS = ("pointer",)*8 + ("u32","void","pointer")


def _selected(image):
    # Signature/layout helpers need no global body scan or generic dispatch table.
    selected = SelectedMethods.__new__(SelectedMethods)
    selected.image, selected._type_names = image, {}
    selected.index = SimpleNamespace(types={image.metadata.type_full_name(t): t for t in image.metadata.types})
    return selected


def validate_contract(image, contract: dict) -> list[dict]:
    if contract['schema'] in (SCHEMA,'endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') and (
            contract.get('lifecycleObserver')!='collision_pair_step_native.json' or
            contract.get('liveBodyObserver')!='collision_live_body_native.json'):
        raise ValueError('collision-capture: task lifecycle/live body observer differs')
    if contract['schema'] in (SCHEMA,'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') and contract.get('pairObserver')!='collision_pair_filter_native.json':
        raise ValueError('collision-capture: pair filter observer differs')
    if contract['schema'] in (SCHEMA,'endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') and contract.get('bodyObserver')!='collision_body_state_native.json':
        raise ValueError('collision-capture: body state observer differs')
    if contract['schema'] in (SCHEMA,'endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') and (
            contract.get('detailObserver')!='collision_geometry_state_native.json' or
            contract['nativeMemory'].get('detailSpanRoots')!=['geometryVertices','geometryIndices']):
        raise ValueError('collision-capture: geometry state observer/span declarations differ')
    if contract['schema'] in (SCHEMA,"endfield.collision-capture-native.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v17') and contract.get('dispatchObserver')!='collision_solver_dispatch_native.json':
        raise ValueError('collision-capture: dynamics dispatch observer differs')
    if contract['schema'] in (SCHEMA,"endfield.collision-capture-native.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16',"endfield.collision-capture-native.v10","endfieldCapture.collisionBuild.v11",'endfieldCapture.collisionBuild.v10','endfieldCapture.collisionBuild.v17') and contract.get('stageObserver')!='collision_physics_stage_native.json':
        raise ValueError('collision-capture: physics-stage observer differs')
    if contract['schema'] in (SCHEMA,"endfield.collision-capture-native.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16',"endfield.collision-capture-native.v10","endfieldCapture.collisionBuild.v11","endfield.collision-capture-native.v9","endfieldCapture.collisionBuild.v10",'endfieldCapture.collisionBuild.v9','endfield.collision-capture-native.v8','endfieldCapture.collisionBuild.v8','endfieldCapture.collisionBuild.v17') and (
            contract.get('ecsObserver') not in (None,'collision_ecs_capture_native.json') or
            contract.get('queryCallerPolicy')!='reviewed-native-callee-and-live-cache'):
        raise ValueError('collision-capture: current ECS observer/query caller policy differs')
    if contract['schema'] in (SCHEMA,"endfield.collision-capture-native.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16',"endfield.collision-capture-native.v10","endfieldCapture.collisionBuild.v11","endfield.collision-capture-native.v9","endfieldCapture.collisionBuild.v10",'endfieldCapture.collisionBuild.v9','endfieldCapture.collisionBuild.v17'):
        transport=contract.get('transport',{})
        bounds=dict(queueCapacity=(4096,32768),batchRows=(1,4096),maxBatchBytes=(8192,4194304),flushMillis=(250,2000))
        if (transport.get('eventFormat')!='endfield.collision-event-json.v2' or
                any(type(transport.get(k)) is not int or not lo<=transport[k]<=hi for k,(lo,hi) in bounds.items()) or
                transport['queueCapacity']&(transport['queueCapacity']-1) or transport['batchRows']>transport['queueCapacity']):
            raise ValueError('collision-capture: compiled transport bounds/format differ')
    if contract['schema'] in (SCHEMA,'endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') and contract.get('activationObserver')!='collision_activation_capture_native.json':
        raise ValueError('collision-capture: activation observer differs')
    rows = contract["methods"]
    if contract['schema'] in (SCHEMA,'endfieldCapture.collisionBuild.v17') and contract.get('solverTaskObserver')!='collision_solver_task_native.json':
        raise ValueError('collision-capture: selected solver task observer differs')
    legacy=contract["schema"] in ("endfield.collision-capture-native.v1","endfieldCapture.collisionBuild.v1")
    child_legacy=contract["schema"] in ("endfield.collision-capture-native.v2","endfieldCapture.collisionBuild.v2")
    native_simulation=contract["schema"] in (SCHEMA,"endfield.collision-capture-native.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16',"endfield.collision-capture-native.v10","endfieldCapture.collisionBuild.v11","endfield.collision-capture-native.v9","endfieldCapture.collisionBuild.v10","endfieldCapture.collisionBuild.v9","endfield.collision-capture-native.v8","endfieldCapture.collisionBuild.v8","endfield.collision-capture-native.v7","endfieldCapture.collisionBuild.v7","endfield.collision-capture-native.v6","endfieldCapture.collisionBuild.v6","endfield.collision-capture-native.v5","endfieldCapture.collisionBuild.v5",'endfieldCapture.collisionBuild.v17')
    if tuple(row["role"] for row in rows) != (ROLES[:19] if legacy else ROLES[:22] if child_legacy else ROLES):
        raise ValueError("collision-capture: hook/query role order differs")
    for n,row in enumerate(rows):
        abi=row["abi"]
        expected_hidden=64 if row["role"] in ("grid_matrix","world_matrix") else 20 if row["role"]=="prefab_request" else 0
        if (tuple(abi["arguments"]),abi["returnMode"],abi["hiddenReturnBytes"],row["hook"]) != (ARGUMENTS[n],RETURNS[n],expected_hidden,n<9 or row["role"]=="physics_simulate" and not native_simulation):
            raise ValueError("collision-capture:"+row["role"]+": compiled machine ABI declaration differs")
    if not legacy:
        limits=contract["childSnapshots"]
        if (type(limits["maxComponents"]) is not int or type(limits["maxColliders"]) is not int or
                not 1<=limits["maxColliders"]<=min(limits["maxComponents"],256) or
                not limits["maxComponents"]<=4096 or limits["includeInactive"] is not True or
                limits["componentType"]!="UnityEngine.Component"):
            raise ValueError("collision-capture: unsafe child snapshot bounds/type")
    selected = _selected(image)
    layouts = {row["type"]:row for row in contract["types"]}
    if not legacy and not child_legacy:
        scene=layouts.get("UnityEngine.PhysicsScene",{})
        if scene.get("size")!=4 or scene.get("fields")!=[dict(name="m_Handle",type="int",offset=0)]:
            raise ValueError("collision-capture: compiled PhysicsScene value carrier differs")
    for suffix, size, fields in (
            ("FBDynamicSceneModel",32,{"__p":0}),
            ("Struct",32,{"<bb_pos>k__BackingField":0,"<bb>k__BackingField":8}),
            ("ByteBuffer",24,{"_buffer":0,"_pos":16}),
            ("ByteData",16,{"_buffer":0,"_length":8}),
            ("ElementDealContext",32,{"elementId":0}),
            ("ModelCompData",20,{"rootGridIndex":0,"asyncInstantiateHandle":8}),
            ("FAssetProxyHandle",20,{"m_untrackedHandle":0}),
            ("String",None,{"_stringLength":16,"_firstChar":20})):
        candidates=[row for name,row in layouts.items() if name.endswith("."+suffix)]
        if len(candidates)!=1 or candidates[0]["size"]!=size or any({f["name"]:f["offset"] for f in candidates[0]["fields"]}.get(name)!=at for name,at in fields.items()):
            raise ValueError("collision-capture:compiled bounded reader layout differs:"+suffix)
    hook_pointers = {image.pe.image_base+r["rva"] for r in rows if r["hook"]}
    aliases = {pointer:[] for pointer in hook_pointers}
    for method in image.metadata.methods:
        pointer = image.method_pointer_va(method)
        if pointer in aliases:
            aliases[pointer].append(method.index)
    result = []
    for n, row in enumerate(rows):
        label = "collision-capture:" + row["role"]
        image.validate_method_row([row["index"], row["type"], row["method"], row["rva"]], label=label)
        method = image.metadata.methods[row["index"]]
        parameters = list(image.metadata.parameters_for(method))
        actual = [dict(name=image.metadata.string(p.name_index), type=selected.type_name(p.type_index)) for p in parameters]
        byref = [bool(image.pe.bytes_at_va(image.pe.u64_at_va(int(image.registration["types"],16)+p.type_index*8),16)[11] & 0x20) for p in parameters]
        if (actual, selected.type_name(method.return_type), bool(method.flags & 16), byref) != (row["parameters"], row["returnType"], row["static"], row["parameterByRef"]):
            raise ValueError(label + ": selected metadata signature/byref drift")
        if not 16 <= row["bodyBytes"] <= 4096:
            raise ValueError(label + ": unbounded body")
        raw = image.pe.bytes_at_va(image.pe.image_base+row["rva"], row["bodyBytes"])
        if hashlib.sha256(raw).hexdigest().lower() != row["bodySha256"].lower():
            raise ValueError(label + ": native body hash differs")
        for probe in row["abiEntryProbes"]:
            at, expected = probe["offset"], bytes.fromhex(probe["bytes"])
            if not expected or at < 0 or raw[at:at+len(expected)] != expected:
                raise ValueError(label + ": entry argument witness differs")
        if row["hook"]:
            if aliases[image.pe.image_base+row["rva"]] != [row["index"]]:
                raise ValueError(label + ": folded/ambiguous native hook")
        result.append({**row, "expectedBytes": raw.hex()})
    for row in contract["types"]:
        td = selected.index.types.get(row["type"])
        if td is None or td.index != row["index"] or selected.is_value_type(row["type"]) != row["value"]:
            raise ValueError("collision-capture:type identity drift:" + row["type"])
        if row["value"] and selected.value_size(row["type"]) != row["size"]:
            raise ValueError("collision-capture:unboxed size drift:" + row["type"])
        fields = {image.metadata.string(f.name_index): f for f in image.metadata.fields_for(td)}
        offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, td.index)
        for field in row["fields"]:
            f = fields.get(field["name"])
            if f is None or selected.type_name(f.type_index) != field["type"] or offsets[field["name"]] - (16 if row["value"] else 0) != field["offset"]:
                raise ValueError("collision-capture:field layout drift:" + row["type"] + "::" + field["name"])
    return result


def _apis(image, declarations=None) -> list[dict]:
    # Current declarations authenticate typed public entries and implementation
    # windows. Older saved profiles contain only the four closed pointer getters.
    result = []
    names=LEGACY_APIS if declarations is None else APIS[:len(declarations)]
    if declarations is not None and (len(declarations) not in (10,11) or tuple(row["role"] for row in declarations)!=names):
        raise ValueError("collision-capture: public API declaration order differs")
    exports = {row["symbolName"]:row for row in resolve_named_exports(image.pe, names)["selectedExports"]}
    if set(exports) != set(names):
        raise ValueError("collision-capture:public C API selection differs")
    # The provider indexes these slots by operation, not export-name sorting.
    for n,name in enumerate(names):
        row = exports[name]
        if row["isForwarder"]:
            raise ValueError("collision-capture:forwarded C API:" + row["symbolName"])
        if declarations is not None:
            declared=declarations[n]
            abi=declared["abi"]
            if (tuple(abi["arguments"]),abi["returnMode"])!=(API_ARGUMENTS[n],API_RETURNS[n]):
                raise ValueError("collision-capture: compiled public API ABI differs:"+name)
            if declared["rva"]!=row["targetRva"] or not 1<=declared["bodyBytes"]<=4096:
                raise ValueError("collision-capture: public API entry differs:"+name)
            raw=image.pe.bytes_at_va(image.pe.image_base+row["targetRva"],declared["bodyBytes"])
            if hashlib.sha256(raw).hexdigest().lower()!=declared["bodySha256"].lower():
                raise ValueError("collision-capture: public API body differs:"+name)
            for probe in declared["abiEntryProbes"]:
                at,expected=probe["offset"],bytes.fromhex(probe["bytes"])
                if not expected or at<0 or raw[at:at+len(expected)]!=expected:
                    raise ValueError("collision-capture: public API argument witness differs:"+name)
            windows=[]
            for window in declared.get("codeWindows",[]):
                if not 1<=window["bodyBytes"]<=4096:
                    raise ValueError("collision-capture: public API implementation bound:"+name)
                body=image.pe.bytes_at_va(image.pe.image_base+window["rva"],window["bodyBytes"])
                if hashlib.sha256(body).hexdigest().lower()!=window["sha256"].lower():
                    raise ValueError("collision-capture: public API implementation differs:"+name)
                windows.append({**window,"expectedBytes":body.hex()})
            result.append({**declared,"expectedBytes":raw.hex(),**(dict(codeWindows=windows) if windows else {})})
            continue
        raw = image.pe.bytes_at_va(image.pe.image_base+row["targetRva"], 16)
        matched = re.match(rb"\x48\x8b(?:\x01|\x41[\x00-\x7f]|\x81....)\xc3", raw, re.DOTALL)
        if matched is None:
            raise ValueError("collision-capture:C API is not a closed RCX/RAX pointer getter:" + row["symbolName"])
        result.append(dict(role=row["symbolName"], rva=row["targetRva"], expectedBytes=matched[0].hex()))
    return result


def validate_player(path: Path, contract: dict) -> list[dict]:
    """Authenticate native provenance readers and the physics completion witness."""
    policy=contract["runtimeProvenance"]
    sizes=dict(entryBytes=40,maxFiles=1048576,maxFilenameBytes=512,stringTagOffset=32,
               stringLengthOffset=16,stringInlineRemainingOffset=24,stringInlineCapacity=24,
               identityBytes=16,identityFileIndexOffset=0,identityPathIdOffset=8)
    if any(type(policy.get(k)) is not int or policy[k]!=v for k,v in sizes.items()):
        raise ValueError("collision-capture: compiled serialized identity/string bounds differ")
    if policy.get("lockMode")!="try_critical_section_nonblocking":
        raise ValueError("collision-capture: compiled critical-section lock policy differs")
    steps=contract["physicsSnapshots"]
    legacy=contract["schema"] in ("endfield.collision-capture-native.v3","endfieldCapture.collisionBuild.v3")
    native_simulation=contract["schema"] in (SCHEMA,"endfield.collision-capture-native.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16',"endfield.collision-capture-native.v10","endfieldCapture.collisionBuild.v11","endfield.collision-capture-native.v9","endfieldCapture.collisionBuild.v10","endfieldCapture.collisionBuild.v9","endfield.collision-capture-native.v8","endfieldCapture.collisionBuild.v8","endfield.collision-capture-native.v7","endfieldCapture.collisionBuild.v7","endfield.collision-capture-native.v6","endfieldCapture.collisionBuild.v6","endfield.collision-capture-native.v5","endfieldCapture.collisionBuild.v5",'endfieldCapture.collisionBuild.v17')
    contact_version=contract["schema"] in (SCHEMA,"endfield.collision-capture-native.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16',"endfield.collision-capture-native.v10","endfieldCapture.collisionBuild.v11","endfield.collision-capture-native.v9","endfieldCapture.collisionBuild.v10","endfieldCapture.collisionBuild.v9","endfield.collision-capture-native.v8","endfieldCapture.collisionBuild.v8","endfield.collision-capture-native.v7","endfieldCapture.collisionBuild.v7","endfield.collision-capture-native.v6","endfieldCapture.collisionBuild.v6",'endfieldCapture.collisionBuild.v17')
    if contact_version:
        p=contract["contactCapture"]
        if (p.get("role")!="contact_finalize" or p.get("headerBytes")!=48 or p.get("pairBytes")!=64 or
                p.get("maxPairsPerHeader")!=128 or p.get("maxPairSamples")!=2048 or
                p.get("maxUnselectedSamples")!=128 or
                p.get("retainUntilStop") is not True or p.get("removedFlagsMask")!=3):
            raise ValueError("collision-capture: compiled contact bounds/removal policy differs")
        if contract['nativeMemory'].get('reportRoots')!=['contactHeader','contactPair'] or contract['nativeMemory'].get('format')!=('endfield.native-memory-windows.v3' if contract['schema'] in (SCHEMA,"endfield.collision-capture-native.v11","endfieldCapture.collisionBuild.v12","endfieldCapture.collisionBuild.v13",'endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16',"endfield.collision-capture-native.v10","endfieldCapture.collisionBuild.v11","endfield.collision-capture-native.v9","endfieldCapture.collisionBuild.v10",'endfieldCapture.collisionBuild.v9','endfield.collision-capture-native.v8','endfieldCapture.collisionBuild.v8','endfieldCapture.collisionBuild.v17') else 'endfield.native-memory-windows.v2'):
            raise ValueError('collision-capture: contact archive root policy differs')
    if native_simulation and steps.get("simulationRole")!="physics_core":
        raise ValueError("collision-capture: native simulation hook selection differs")
    ordinals=steps["completedStepOrdinals"]
    if (steps["maxRetainedColliders"]!=64 or steps["completionRole"]!="physics_complete" or
            not isinstance(ordinals,list) or not 1<=len(ordinals)<=4 or
            any(type(n) is not int or not 1<=n<=3600 for n in ordinals) or ordinals!=sorted(set(ordinals)) or
            legacy and ordinals!=[1,60]):
        raise ValueError("collision-capture: compiled retained collider/physics policy differs")
    if not legacy:
        validate_policy(contract["nativeMemory"])
    rows=contract["playerMethods"]
    hook_roles={r["role"] for r in rows if r.get("hook")}
    if ([r["role"] for r in rows[:3]]!=["read_lock","serialized_identity","physics_complete"] or
            len({r["role"] for r in rows})!=len(rows) or
            hook_roles!=({"physics_core","physics_complete","contact_finalize"} if contact_version else {"physics_core","physics_complete"} if native_simulation else {"physics_complete"})):
        raise ValueError("collision-capture: player query/hook order differs")
    for n,row in enumerate(rows):
        if contact_version and row["role"]=="contact_finalize":
            if row["abi"]!={"arguments":["pointer"]*4+["u32"],"returnMode":"void","hiddenReturnBytes":0}:
                raise ValueError("collision-capture:UnityPlayer:contact_finalize: compiled native ABI differs")
        if n<3 or native_simulation and row["role"]=="physics_core":
            expected=(("pointer",),("pointer","i32","pointer"),("pointer",))[n] if n<3 else ("pointer","u32","f32")
            if tuple(row["abi"]["arguments"])!=expected or row["abi"]["returnMode"]!=("bool" if n==1 else "void"):
                raise ValueError("collision-capture:UnityPlayer:"+row["role"]+": compiled native ABI differs")
    pe=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(path)
    result=[]
    for n,row in enumerate(rows):
        label="collision-capture:UnityPlayer:"+row["role"]
        if not 1<=row["bodyBytes"]<=4096:
            raise ValueError(label+": native window bound")
        raw=pe.bytes_at_va(pe.image_base+row["rva"],row["bodyBytes"])
        if hashlib.sha256(raw).hexdigest()!=row["bodySha256"].lower():
            raise ValueError(label+": body hash differs")
        for probe in row["abiEntryProbes"]:
            at,b=probe["offset"],bytes.fromhex(probe["bytes"])
            if not b or at<0 or raw[at:at+len(b)]!=b:
                raise ValueError(label+": ABI witness differs")
        result.append({**row,"expectedBytes":raw.hex()})
    by_role={r["role"]:r for r in rows}
    witness_fields=set()
    for witness in policy["fieldWitnesses"]:
        row=by_role[witness["role"]];raw=bytes.fromhex(next(r["expectedBytes"] for r in result if r["role"]==row["role"]))
        at,prefix=witness["instructionOffset"],bytes.fromhex(witness["prefix"])
        mode=witness["encoding"];width=1 if mode=="disp8" else 4
        if mode not in ("disp8","disp32","rip32") or at<0 or not prefix or raw[at:at+len(prefix)]!=prefix or at+len(prefix)+width>len(raw):
            raise ValueError("collision-capture: manager field instruction witness differs:"+witness["field"])
        value=int.from_bytes(raw[at+len(prefix):at+len(prefix)+width],"little",signed=mode=="rip32")
        if mode=="rip32":value+=row["rva"]+at+len(prefix)+width
        if value!=policy[witness["field"]]:
            raise ValueError("collision-capture: manager field differs from native operand:"+witness["field"])
        witness_fields.add(witness["field"])
    if witness_fields!={"singletonRva","vtableRva","lockOffset","mapOffset","filesOffset","countOffset"}:
        raise ValueError("collision-capture: incomplete manager field witnesses")
    imports=resolve_named_import_slots(pe,[policy["readLockImportRva"],policy["releaseLockImportRva"]])["selectedImports"]
    expected={policy["readLockImportRva"]:"EnterCriticalSection",policy["releaseLockImportRva"]:"LeaveCriticalSection"}
    if any(r["libraryName"].lower()!="kernel32.dll" or r["symbolName"]!=expected[r["slotRva"]] for r in imports):
        raise ValueError("collision-capture: manager critical-section import identity differs")
    acquire=bytes.fromhex(result[0]["expectedBytes"])
    if acquire[:3]!=b"\x48\xff\x25" or rows[0]["rva"]+7+int.from_bytes(acquire[3:],"little",signed=True)!=policy["readLockImportRva"]:
        raise ValueError("collision-capture: read lock import tail target differs")
    # Prove the code's file-index getter really is the constructed manager's
    # virtual slot, and the completion return site calls the selected marker.
    table=pe.image_base+policy["vtableRva"]
    filename=next(r for r in rows if r["role"]=="filename_consumer")
    if pe.u64_at_va(table+32)!=pe.image_base+filename["rva"]:
        raise ValueError("collision-capture: filename virtual dispatch differs")
    site=pe.image_base+steps["completionReturnRva"]
    call=pe.bytes_at_va(site-5,5)
    if call[0]!=0xe8 or site+int.from_bytes(call[1:],"little",signed=True)!=pe.image_base+rows[2]["rva"]:
        raise ValueError("collision-capture: physics completion call site differs")
    if native_simulation:
        core=by_role[steps["simulationRole"]]
        if not core["rva"]<=steps["completionReturnRva"]-5<steps["completionReturnRva"]<=core["rva"]+core["bodyBytes"]:
            raise ValueError("collision-capture: completion call lies outside native simulation body")
    if contact_version:
        target=by_role[p["role"]]
        for site in p["returnRvas"]:
            raw=pe.bytes_at_va(pe.image_base+site-5,5)
            if raw[0]!=0xe8 or site+int.from_bytes(raw[1:],"little",signed=True)!=target["rva"]:
                raise ValueError("collision-capture: contact finalization call site differs")
        for witness in p["fieldWitnesses"]:
            raw=bytes.fromhex(next(r["expectedBytes"] for r in result if r["role"]==witness["role"]))
            at=witness["offset"];expected=bytes.fromhex(witness["bytes"])
            if raw[at:at+len(expected)]!=expected:
                raise ValueError("collision-capture: contact field witness differs:"+witness["field"])
            value=p
            for part in witness['path'].split('.'):
                value=value[int(part)] if isinstance(value,list) else value[part]
            operand=0 if witness.get('implicitZero') else expected[witness['operandOffset']]
            if value!=operand:
                raise ValueError("collision-capture: contact field differs from native operand:"+witness['field'])
    return result


def prepare(game_root: Path, plan_path: Path) -> dict:
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="collision-capture", status="reviewed")
    inputs = contract["nativeInputs"]
    directory = game_root.resolve()
    if directory.name == "Endfield_Data":
        directory = directory.parent
    paths = dict(executable=directory/"Endfield.exe", gameAssembly=directory/"GameAssembly.dll",
                 metadata=directory/"Endfield_Data/il2cpp_data/Metadata/global-metadata.dat", unityPlayer=directory/"UnityPlayer.dll")
    gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["metadataSha256"], gameassembly=paths["gameAssembly"], metadata=paths["metadata"])
    if gate.status != "validated":
        raise ValueError("collision-capture:installed_native_inputs:" + gate.status + ":" + gate.detail)
    if sha256_file(paths["unityPlayer"]).upper() != inputs["unityPlayerSha256"].upper():
        raise ValueError("collision-capture:UnityPlayer differs")
    image = open_native_image(paths["gameAssembly"], paths["metadata"])
    methods = validate_contract(image, contract)
    from scripts.game_data.collision_runtime_mesh_native import load_layout
    attachment,attachment_gate=load_layout(gameassembly=paths["gameAssembly"],metadata=paths["metadata"],unityplayer=paths["unityPlayer"],
        contract_path=CONTRACTS_DIR/"collision_runtime_shape_native.json",schema="endfield.collision-runtime-shape-native-contract.v1",validator="collision_contact_attachment")
    if attachment is None:
        raise ValueError("collision-capture: attachment native gate:"+str(attachment_gate))
    from scripts.game_data import collision_query_native
    query_capture=collision_query_native.load(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'],image=image)
    from scripts.game_data import collision_ecs_capture_native
    pe=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(paths["unityPlayer"])
    ecs_capture=collision_ecs_capture_native.load(pe, inputs)
    from scripts.game_data import collision_physics_stage_native
    stage_capture=collision_physics_stage_native.load(pe, inputs)
    from scripts.game_data import collision_solver_dispatch_native
    dispatch_capture=collision_solver_dispatch_native.load_capture(pe, inputs)
    from scripts.game_data import collision_geometry_state_native
    detail_capture=collision_geometry_state_native.load(pe,inputs)
    from scripts.game_data import collision_body_state_native
    body_capture=collision_body_state_native.load(pe,inputs)
    from scripts.game_data import collision_pair_filter_native
    pair_contract,pair_gate=collision_pair_filter_native.load(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
    if pair_contract is None:
        raise ValueError('collision-capture: pair-filter native gate:'+str(pair_gate))
    pair_capture=collision_pair_filter_native.capture_declarations(pe,pair_contract)
    from scripts.game_data import collision_pair_step_native,collision_live_body_native
    step_contract,step_gate=collision_pair_step_native.load(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
    if step_contract is None:raise ValueError('collision-capture: task lifecycle native gate:'+str(step_gate))
    task_capture=collision_pair_step_native.capture_declarations(pe,step_contract)
    live_body_capture=collision_live_body_native.load(image,pe,inputs)
    from scripts.game_data import collision_activation_capture_native
    activation_capture=collision_activation_capture_native.load(image,inputs)
    from scripts.game_data import collision_solver_task_native
    solver_contract,solver_gate=collision_solver_task_native.load(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer'])
    if solver_contract is None:raise ValueError('collision-capture: solver task native gate:'+str(solver_gate))
    solver_capture=collision_solver_task_native.capture_declarations(pe,solver_contract)
    lifecycle_capture=dict(solver=solver_capture,activation=activation_capture,task=task_capture,body=live_body_capture,hooks=sorted(task_capture['hooks']+live_body_capture['hooks']+activation_capture['hooks']+solver_capture['hooks'],key=lambda h:h['kind']),pins=task_capture['pins']+live_body_capture['pins']+activation_capture['pins']+solver_capture['pins'])
    if pair_contract['layout']['scene']['publicDelta']!=body_capture['contract']['layout']['scene']['publicDelta']:
        raise ValueError('collision-capture: body/pair scene address domains differ')
    plan = json.loads(plan_path.read_text("utf-8"))
    if plan["schema"] != "endfield.collision-live-capture-plan.v1" or {k:v.upper() for k,v in plan["nativeInputs"].items()} != {k:v.upper() for k,v in inputs.items()}:
        raise ValueError("collision-capture:selected source plan/native inputs differ")
    for row in plan["sources"]:
        path = REPO_ROOT / row["path"]
        if sha256_file(path).lower() != row["sha256"].lower():
            raise ValueError("collision-capture:source receipt changed:" + row["path"])
    model_receipt = next(row for row in plan["sources"] if "dynamic_model_current" in row["path"])
    models = json.loads((REPO_ROOT/model_receipt["path"]).read_text("utf-8"))
    target_models = [row for row in models["models"] if row["pathHashHex"] == plan["firstTarget"]["pathHashHex"]]
    raw_sources = {row["virtualPath"]:row for row in models["files"]}
    archived = [dict(path=str((REPO_ROOT/row["path"]).resolve()),sha256=row["sha256"]) for row in plan["sources"]]
    archived += [dict(path=str(CONTRACT),sha256=digest),dict(path=str(plan_path.resolve()),sha256=sha256_file(plan_path))]
    archived.append(dict(path=str(CONTRACTS_DIR/"collision_runtime_shape_native.json"),sha256=sha256_file(CONTRACTS_DIR/"collision_runtime_shape_native.json")))
    archived.append(dict(path=str(collision_query_native.CONTRACT),sha256=query_capture['contractSha256']))
    for name in ("collision_ecs_capture_native.json","ecs_collision_native.json","streaming_collision_native.json","streaming_marker17_native.json","collision_runtime_mesh_native.json"):
        path=CONTRACTS_DIR/name
        archived.append(dict(path=str(path),sha256=sha256_file(path)))
    archived.append(dict(path=str(collision_physics_stage_native.CONTRACT),sha256=sha256_file(collision_physics_stage_native.CONTRACT)))
    archived.append(dict(path=str(collision_solver_dispatch_native.CONTRACT),sha256=sha256_file(collision_solver_dispatch_native.CONTRACT)))
    archived.append(dict(path=str(collision_geometry_state_native.CONTRACT),sha256=sha256_file(collision_geometry_state_native.CONTRACT)))
    archived.append(dict(path=str(collision_body_state_native.CONTRACT),sha256=sha256_file(collision_body_state_native.CONTRACT)))
    archived.append(dict(path=str(collision_pair_filter_native.CONTRACT),sha256=sha256_file(collision_pair_filter_native.CONTRACT)))
    from scripts.game_data.collision_body_mode_native import CONTRACT as BODY_MODE_CONTRACT
    archived.append(dict(path=str(BODY_MODE_CONTRACT),sha256=sha256_file(BODY_MODE_CONTRACT)))
    for path in (collision_pair_step_native.CONTRACT,collision_live_body_native.CONTRACT,collision_activation_capture_native.CONTRACT,collision_solver_task_native.CONTRACT):
        archived.append(dict(path=str(path),sha256=sha256_file(path)))
    visited = set()
    for model in target_models:
        source = raw_sources[model["source"]]
        raw_path = (REPO_ROOT/source["path"]).resolve()
        if sha256_file(raw_path).upper() != source["sha256"].upper():
            raise ValueError("collision-capture:target Model source changed:"+model["source"])
        raw = raw_path.read_bytes()
        at = model["byteOffset"]
        if not 0 <= at <= len(raw)-96 or int.from_bytes(raw[at+64:at+72],"little") != int(model["pathHashHex"],16):
            raise ValueError("collision-capture:target Model framing differs")
        model["rawModelHex"] = raw[at:at+96].hex()
        if raw_path not in visited:
            visited.add(raw_path);archived.append(dict(path=str(raw_path),sha256=source["sha256"]))
    if not target_models or not any(row["source"]==plan["firstTarget"]["source"] and row["ordinal"]==plan["firstTarget"]["ordinal"] for row in target_models):
        raise ValueError("collision-capture:first selected source Model is absent")
    for n,row in enumerate(archived):
        path=Path(row["path"])
        row.update(bytes=path.stat().st_size,archiveName=f"{n:02d}-{path.name}")
    files = {key: dict(relativePath=path.relative_to(directory).as_posix(), bytes=path.stat().st_size, sha256=sha256_file(path), path=str(path)) for key,path in paths.items()}
    # Recheck gates after analysis to reject an input changing during preparation.
    for key, row in files.items():
        expected = inputs.get(key+"Sha256")
        if expected and row["sha256"].upper() != expected.upper():
            raise ValueError("collision-capture:input changed:" + key)
    for row in archived:
        if sha256_file(Path(row["path"])).lower()!=row["sha256"].lower():
            raise ValueError("collision-capture:source changed during preparation:"+row["archiveName"])
    pe=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(paths["unityPlayer"])
    attachment_pins=[dict(role="attachment:"+r["role"],rva=r["rva"],expectedBytes=pe.bytes_at_va(pe.image_base+r["rva"],r["bytes"]).hex()) for r in attachment["codeWindows"]]
    return dict(schema="endfieldCapture.collisionBuild.v17", status="validated", offlineOnly=True,
                profile="collision", processName="Endfield.exe", files=files, methods=methods, apis=_apis(image,contract["publicApis"]),
                childSnapshots=contract["childSnapshots"],transport=contract["transport"],queryCallerPolicy=contract["queryCallerPolicy"],stageObserver=contract['stageObserver'],
                contactCapture=contract["contactCapture"],contactAttachment=attachment,attachmentPins=attachment_pins,queryCapture=query_capture,ecsCapture=ecs_capture,stageCapture=stage_capture,dispatchCapture=dispatch_capture,detailCapture=detail_capture,
                dispatchObserver=contract['dispatchObserver'],detailObserver=contract['detailObserver'],bodyObserver=contract['bodyObserver'],bodyCapture=body_capture,
                pairObserver=contract['pairObserver'],pairCapture=pair_capture,lifecycleCapture=lifecycle_capture,lifecycleObserver=contract['lifecycleObserver'],liveBodyObserver=contract['liveBodyObserver'],activationObserver=contract['activationObserver'],solverTaskObserver=contract['solverTaskObserver'],
                playerMethods=validate_player(paths["unityPlayer"],contract),runtimeProvenance=contract["runtimeProvenance"],physicsSnapshots=contract["physicsSnapshots"],nativeMemory=contract["nativeMemory"],
                types=contract["types"], contractSha256=digest, sourcePlan=dict(path=str(plan_path.resolve()),sha256=sha256_file(plan_path)),
                target=plan["firstTarget"], targetModels=target_models, sources=archived, evidenceBoundary=contract["evidenceBoundary"])


def header(profile: dict, profile_path: Path) -> str:
    lines = ["#pragma once", "#include <array>", "#include <cstdint>", "namespace collision_capture::build {",
             "struct Pin { const char* role; std::uint32_t rva; const char* bytes; };", "inline constexpr Pin pins[] = {"]
    for row in [*profile["methods"], *profile["apis"]]:
        lines.append('{"'+row["role"]+'", '+str(row["rva"])+', "'+row["expectedBytes"]+'"},')
    for row in profile["apis"]:
        for n,window in enumerate(row.get("codeWindows",[])):
            lines.append('{"'+row["role"]+':implementation-'+str(n)+'", '+str(window["rva"])+', "'+window["expectedBytes"]+'"},')
    lines += ["};","inline constexpr Pin player_pins[] = {"]
    for row in profile["playerMethods"]:
        lines.append('{"'+row["role"]+'", '+str(row["rva"])+', "'+row["expectedBytes"]+'"},')
    for row in profile.get("attachmentPins",[]):
        lines.append('{"'+row["role"]+'", '+str(row["rva"])+', "'+row["expectedBytes"]+'"},')
    player_indices={row["role"]:n for n,row in enumerate(profile["playerMethods"])}
    lines += ["};",f"inline constexpr unsigned method_count = {len(profile['methods'])};",f"inline constexpr unsigned query_count = {len(profile['methods'])-10};",f"inline constexpr unsigned api_count = {len(profile['apis'])};",
              f"inline constexpr unsigned physics_core_index = {player_indices['physics_core']};",f"inline constexpr unsigned physics_complete_index = {player_indices['physics_complete']};",
              f"inline constexpr std::uint64_t max_components = {profile['childSnapshots']['maxComponents']};",f"inline constexpr std::uint64_t max_colliders = {profile['childSnapshots']['maxColliders']};",
              "struct File { const wchar_t* path; std::uint64_t bytes; const char* sha256; };", "inline constexpr File files[] = {"]
    for row in profile["files"].values():
        lines.append('{L'+json.dumps(row["path"].replace("\\", "/"))+', '+str(row["bytes"])+', "'+row["sha256"]+'"},')
    lines += ["};","struct Source { const wchar_t* path; const wchar_t* name; std::uint64_t bytes; const char* sha256; };", "inline constexpr Source sources[] = {"]
    for row in profile["sources"]:
        lines.append('{L'+json.dumps(row["path"].replace("\\","/"))+', L'+json.dumps(row["archiveName"])+', '+str(row["bytes"])+', "'+row["sha256"]+'"},')
    target_hash = int(profile["target"]["pathHashHex"],16)
    lines += ["};", f"inline constexpr std::uint64_t target_hash = 0x{target_hash:016x}ULL;"]
    capture=profile.get('queryCapture')
    if capture:
        lines += ['struct ExtraPin { bool player; std::uint32_t rva; const char* bytes; };','inline constexpr ExtraPin extra_hooks[] = {']
        for row in capture['hooks']:
            lines.append('{'+('true' if row['module']=='unityPlayer' else 'false')+', '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
        lines += ['};','inline constexpr ExtraPin extra_pins[] = {']
        for row in capture['pins']:
            lines.append('{'+('true' if row['module']=='unityPlayer' else 'false')+', '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
        lines += ['};',f'inline constexpr std::array<unsigned,{len(capture["hooks"])}> extra_kinds = {{'+','.join(str(h['kind']) for h in capture['hooks'])+'};',
                  'struct QueryBinding { std::uint32_t cache, caller, target; };','inline constexpr QueryBinding query_bindings[] = {']
        for b in capture['contract']['bindings']:
            lines.append('{'+','.join(str(b[k]) for k in ('cacheCellRva','returnRva','functionRva'))+'},')
        lines.append('};')
        for name,value in capture['contract']['limits'].items():
            lines.append(f'inline constexpr unsigned query_{name} = {value};')
        for family in ('reportLayout','arrayLayout','conversionInput'):
            for name,value in capture['contract'][family].items():
                lines.append(f'inline constexpr unsigned query_{family}_{name} = {value};')
        for ti in capture['contract']['types']:
            prefix='hit' if ti['type']=='UnityEngine.RaycastHit' else 'proxy' if ti['type']=='UnityEngine.ECSColliderResultProxy' else 'movement' if ti['type'].endswith('MovementComponent') else None
            if prefix:
                for field in ti['fields']:
                    lines.append(f"inline constexpr unsigned query_{prefix}_{field['name']} = {field['offset']};")
    for name,key in (('event_queue_capacity','queueCapacity'),('writer_batch_rows','batchRows'),('writer_max_batch_bytes','maxBatchBytes'),('writer_flush_millis','flushMillis')):
        lines.append(f'inline constexpr unsigned {name} = {profile["transport"][key]};')
    ec=profile['ecsCapture']
    stage=profile['stageCapture']
    lines += ['inline constexpr ExtraPin stage_hooks[] = {']
    for row in stage['hooks']:
        lines.append('{true, '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
    lines += ['};','inline constexpr ExtraPin stage_pins[] = {']
    for row in stage['pins']:
        lines.append('{true, '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
    lines += ['};',f'inline constexpr std::array<unsigned,{len(stage["hooks"])}> stage_kinds = {{'+','.join(str(h['kind']) for h in stage['hooks'])+'};']
    for family in ('limits','layout'):
        for name,value in stage['contract'][family].items():
            lines.append(f'inline constexpr unsigned stage_{name} = {value};')
    dc=profile['dispatchCapture']
    for family in ('hooks','pins'):
        lines+=['inline constexpr ExtraPin dispatch_'+family+'[] = {']
        for row in dc[family]:lines.append('{true, '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
        lines+=['};']
    lines+=[f'inline constexpr std::array<unsigned,{len(dc["hooks"])}> dispatch_kinds = {{'+','.join(str(h['kind']) for h in dc['hooks'])+'};']
    for group,fields in dc['contract']['layout'].items():
        for name,value in fields.items():lines.append(f'inline constexpr {"std::int32_t" if value<0 else "unsigned"} dispatch_{group}_{name} = {value};')
    for name,value in dc['contract']['limits'].items():lines.append(f'inline constexpr unsigned dispatch_{name} = {value};')
    for site in dc['contract']['decisionSites']:
        for name in ('returnRva','countFromReturnSlot'):lines.append(f'inline constexpr unsigned dispatch_{site["backend"]}_{name} = {site[name]};')
    lines.append(f'inline constexpr unsigned dispatch_flush_iat = {dc["contract"]["flushImport"]["selectedImports"][0]["slotRva"]};')
    lines.append('inline constexpr std::array<unsigned,6> dispatch_population_offsets = {'+','.join(str(dc['contract']['layout']['accurateIsland'][name]) for name in ('activeIslands','rigidBodies','kinematics','articulations','contactManagers','constraints'))+'};')
    detail=profile['detailCapture']
    for family in ('hooks','pins'):
        lines+=['inline constexpr ExtraPin detail_'+family+'[] = {']
        for row in detail[family]:lines.append('{true, '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
        lines+=['};']
    lines+=[f'inline constexpr std::array<unsigned,{len(detail["hooks"])}> detail_kinds = {{'+','.join(str(h['kind']) for h in detail['hooks'])+'};']
    for group,fields in detail['contract']['layout'].items():
        for name,value in fields.items():lines.append(f'inline constexpr unsigned detail_{group}_{name} = {value};')
    for group in ('bindings','representation','limits'):
        for name,value in detail['contract'][group].items():
            if type(value) is int:lines.append(f'inline constexpr unsigned detail_{name} = {value};')
    for name,value in stage['cacheLayout']['layout']['triangle'].items():lines.append(f'inline constexpr unsigned detail_triangle_{name} = {value};')
    body=profile['bodyCapture']['contract']
    lines+=['inline constexpr ExtraPin body_pins[] = {']
    for row in profile['bodyCapture']['pins']:lines.append('{true, '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
    lines+=['};']
    for group,fields in body['layout'].items():
        for name,value in fields.items():lines.append(f'inline constexpr auto body_{group}_{name} = {value};')
    for name,value in body['limits'].items():lines.append(f'inline constexpr unsigned body_{name} = {value};')
    pair=profile['pairCapture']
    for family in ('hooks','pins'):
        lines+=['inline constexpr ExtraPin pair_'+family+'[] = {']
        for row in pair[family]:lines.append('{true, '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
        lines+=['};']
    lines+=[f'inline constexpr std::array<unsigned,{len(pair["hooks"])}> pair_kinds = {{'+','.join(str(h['kind']) for h in pair['hooks'])+'};']
    for group,fields in pair['contract']['layout'].items():
        for name,value in fields.items():lines.append(f'inline constexpr {"std::int32_t" if value<0 else "unsigned"} pair_{group}_{name} = {value};')
    for group in ('limits','rules','representation'):
        for name,value in pair['contract'][group].items():
            if type(value) is int:lines.append(f'inline constexpr unsigned pair_{name} = {value};')
    life=profile['lifecycleCapture']
    for family in ('hooks','pins'):
        lines+=['inline constexpr ExtraPin life_'+family+'[] = {']
        for row in life[family]:lines.append('{'+('true' if row['module']=='unityPlayer' else 'false')+', '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
        lines+=['};']
    lines+=[f'inline constexpr std::array<unsigned,{len(life["hooks"])}> life_kinds = {{'+','.join(str(h['kind']) for h in life['hooks'])+'};']
    for group,fields in life['task']['contract']['layout'].items():
        for name,value in fields.items():lines.append(f'inline constexpr unsigned life_{group}_{name} = {value};')
    lines+=['struct TaskType {unsigned vtable,ownerKind,sceneOffset;};','inline constexpr TaskType life_task_types[] = {']
    for task in life['task']['contract']['taskTypes']:
        offset=life['task']['contract']['layout']['scene'][task['sceneField']] if 'sceneField' in task else 0
        if task['ownerKind']=='publicScene':offset+=life['task']['contract']['publicSceneDelta']
        lines.append('{'+str(task['vtableRva'])+','+str(2 if task['ownerKind']=='nphaseCore' else 3 if task['ownerKind']=='publicScene' else 1)+','+str(offset)+'},')
    lines+=['};']
    seed_role=1+next(i for i,t in enumerate(life['task']['contract']['taskTypes']) if t['role']==life['task']['contract']['simulationSeedRole'])
    lines.append(f'inline constexpr unsigned life_simulationSeedRole = {seed_role};')
    solver=life['solver']['contract']
    lines+=['struct SolverTaskType {unsigned vtable,role;};','inline constexpr SolverTaskType solver_task_types[] = {']
    for t in solver['taskTypes']:lines.append('{'+str(t['vtableRva'])+','+str(t['role'])+'},')
    lines+=['};']
    for group,fields in solver['layout'].items():
        for name,value in fields.items():lines.append(f'inline constexpr unsigned solver_{group}_{name} = {value};')
    for name,value in solver['limits'].items():lines.append(f'inline constexpr unsigned solver_{name} = {value};')
    for name,value in life['task']['contract']['limits'].items():lines.append(f'inline constexpr unsigned life_{name} = {value};')
    for group,fields in life['body']['contract']['layout'].items():
        for name,value in fields.items():lines.append(f'inline constexpr unsigned live_{group}_{name} = {value};')
    lines.append(f'inline constexpr unsigned live_kinematicMask = {life["body"]["contract"]["kinematicMask"]};')
    for binding in life['body']['contract']['bindings']:lines.append(f'inline constexpr unsigned live_{binding["role"]}_function = {binding["functionRva"]};')
    for name,value in life['body']['contract']['limits'].items():lines.append(f'inline constexpr unsigned live_{name} = {value};')
    for binding in life['body']['contract']['bindings']:lines.append(f'inline constexpr unsigned live_{binding["role"]}_cache = {binding["cacheCellRva"]};')
    for group,fields in life['activation']['layout'].items():
        for name,value in fields.items():lines.append(f'inline constexpr unsigned activation_{group}_{name} = {value};')
    for name,value in life['activation']['contract']['limits'].items():lines.append(f'inline constexpr unsigned activation_{name} = {value};')
    lines += ['inline constexpr ExtraPin ecs_hooks[] = {']
    for row in ec['hooks']:
        lines.append('{true, '+str(row['rva'])+', "'+row['expectedBytes']+'"},')
    lines += ['};',f'inline constexpr std::array<unsigned,{len(ec["hooks"])}> ecs_kinds = {{'+','.join(str(h['kind']) for h in ec['hooks'])+'};']
    for name,value in ec['contract']['limits'].items():
        lines.append(f'inline constexpr unsigned ecs_{name} = {value};')
    for family in ('actor','userdata','registry'):
        for name,value in ec['contract']['layout'][family].items():
            lines.append(f'inline constexpr unsigned ecs_{family}_{name} = {value};')
    lines += [f'inline constexpr unsigned ecs_shapeTaggedUserdata = {ec["contract"]["layout"]["shapeTaggedUserdata"]};',
              f'inline constexpr unsigned ecs_registry_singleton = {ec["contract"]["registry"]["singletonRva"]};']
    for name,key in (("singleton_rva","singletonRva"),("vtable_rva","vtableRva"),("lock_offset","lockOffset"),
                     ("map_offset","mapOffset"),("files_offset","filesOffset"),("count_offset","countOffset"),
                     ("acquire_iat_rva","readLockImportRva"),("release_iat_rva","releaseLockImportRva")):
        lines.append(f"inline constexpr std::uint32_t {name} = {profile['runtimeProvenance'][key]};")
    lines.append(f"inline constexpr std::uint32_t completion_return_rva = {profile['physicsSnapshots']['completionReturnRva']};")
    contact=profile['contactCapture'];attachment=profile['contactAttachment']['layout']
    lines.append(f"inline constexpr unsigned contact_finalize_index = {player_indices['contact_finalize']};")
    lines.append("inline constexpr std::array<std::uint32_t,2> contact_return_rvas = {"+','.join(map(str,contact['returnRvas']))+"};")
    for family in ('header','pair'):
        for field,value in contact[family].items():
            for suffix,at in enumerate(value) if isinstance(value,list) else [('',value)]:
                lines.append(f"inline constexpr unsigned contact_{family}_{field}{suffix} = {at};")
    for name,value in dict(contact_max_pairs=contact['maxPairsPerHeader'],contact_max_samples=contact['maxPairSamples'],
            contact_max_unselected=contact['maxUnselectedSamples'],
            contact_collider_vtable=attachment['collider']['vtableRva'],contact_collider_shape=attachment['collider']['shape'],
            contact_shape_vtable=attachment['shape']['vtableRva'],contact_shape_actor=attachment['shape']['actor']).items():
        lines.append(f"inline constexpr std::uint32_t {name} = {value};")
    for name,value in profile['nativeMemory']['solverOwnerSpans'].items():lines.append(f'inline constexpr unsigned solver_owner_{name} = {value};')
    ordinals=profile['physicsSnapshots']['completedStepOrdinals']
    lines.append(f"inline constexpr std::array<std::uint64_t,{len(ordinals)}> completed_step_ordinals = {{"+','.join(map(str,ordinals))+"};")
    for name,key in (("window_bytes","windowBytes"),("pointer_scan_bytes","pointerScanBytes"),("max_depth","maxDepth"),
                     ("max_nodes","maxNodes"),("max_microseconds","maxMicroseconds"),("max_total_bytes","maxTotalBytes"),("max_total_blocks","maxTotalBlocks")):
        lines.append(f"inline constexpr std::uint32_t memory_{name} = {profile['nativeMemory'][key]};")
    for name, t, field in [("manager_offset","DynamicSceneSystemBase","manager"),("scene_name_offset","DynamicStreamingScene","m_currentMapId")]:
        row = next(ti for ti in profile["types"] if ti["type"].endswith("."+t))
        offset = next(f["offset"] for f in row["fields"] if f["name"]==field)
        lines.append(f"inline constexpr std::uint32_t {name} = {offset};")
    lines += ["inline constexpr const wchar_t* profile_path = L"+json.dumps(str(profile_path).replace("\\","/"))+";",
              'inline constexpr const char* profile_sha256 = "'+sha256_file(profile_path)+'";', "}"]
    return "\n".join(lines)+"\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=REPO_ROOT/"reports/assets/collision_live_capture_plan.json")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT/"reports/runtime_capture/collision")
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    # Emitted files are artifacts; never route them into a tracked source folder.
    if not any(output.is_relative_to(REPO_ROOT / root) for root in ("reports", "tmp", "scratch")):
        parser.error("--output-dir must stay under reports/, tmp/ or scratch/")
    try:
        profile = prepare(args.game_root, args.plan)
        atomic_write_text(output/"collision-build.json",json.dumps(profile,ensure_ascii=False,indent=2)+"\n")
        atomic_write_text(output/"collision_build.h", header(profile, output/"collision-build.json"))
        report = dict(schema="endfield.collision-capture-preflight.v17", status="validated", hooks=12+len(profile['queryCapture']['hooks'])+len(profile['ecsCapture']['hooks'])+len(profile['stageCapture']['hooks'])+len(profile['dispatchCapture']['hooks'])+len(profile['detailCapture']['hooks'])+len(profile['pairCapture']['hooks'])+len(profile['lifecycleCapture']['hooks']), queries=len(profile["methods"])-10, publicApis=len(profile["apis"]), playerWindows=len(profile["playerMethods"]), offlineOnly=True, profile=str(output/"collision-build.json"), profileSha256=sha256_file(output/"collision-build.json"))
        atomic_write_text(output/"preflight.json", json.dumps(report,indent=2)+"\n")
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        report = dict(schema="endfield.collision-capture-preflight.v2", status="failed", offlineOnly=True, diagnostic=str(exc)[:1600])
        atomic_write_text(output/"preflight.failed.json", json.dumps(report,indent=2)+"\n")
        print(json.dumps(report)); return 1
    print(json.dumps(report)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
