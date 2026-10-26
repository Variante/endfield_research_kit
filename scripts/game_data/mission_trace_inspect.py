"""Verify and decode a retained EndfieldCapture mission package without a game.

Run as ``python -m scripts.game_data.mission_trace_inspect --session PATH
--output-dir reports/runtime_capture/inspection``. Optional ``--join-sources``
adds explicit archived questDic-to-missionId assignments, never causal joins.
Use ``--local-files`` for the refactored collector's path/size inventory. That
mode writes ``analysis.json`` and never admits a legacy hashed collection.
Package hashes authenticate consistency with its retained inventory, not its
origin, native ABI, hook execution, or the correctness of server behavior.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
from typing import Any

from scripts.repo_paths import REPO_ROOT
from .mission_trace_invocations import Invocations, InvocationError, PAIRED_ABI


class InspectionError(ValueError):
    """Retained data is unsafe, inconsistent, malformed, or exceeds a bound."""


@dataclass(frozen=True)
class Limits:
    artifacts: int = 20000
    artifact_bytes: int = 16 * 1024**3
    package_bytes: int = 32 * 1024**3
    json_bytes: int = 32 * 1024**2
    journal_bytes: int = 8 * 1024**3
    rows: int = 1000000
    input_line_bytes: int = 32 * 1024
    output_line_bytes: int = 64 * 1024
    output_bytes: int = 2 * 1024**3
    identifiers: int = 65536


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise InspectionError(detail)


def integer(value: Any, label: str, maximum: int = (1 << 64) - 1) -> int:
    require(type(value) is int and 0 <= value <= maximum, f"invalid unsigned integer: {label}")
    return value


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in items:
        require(key not in result, f"duplicate JSON key: {key[:100]}")
        result[key] = value
    return result


def parse_json(data: bytes, label: str) -> Any:
    def finite_float(text: str) -> float:
        value = float(text)
        require(math.isfinite(value), "nonfinite JSON number")
        return value

    try:
        return json.loads(data, object_pairs_hook=pairs,
                          parse_float=finite_float,
                          parse_constant=lambda value: require(False, f"nonfinite JSON number: {value}"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InspectionError(f"invalid JSON: {label}: {str(exc)[:512]}") from exc


def safe_path(root: Path, name: Any, *, existing: bool = True) -> Path:
    require(isinstance(name, str) and 0 < len(name) <= 512, "invalid artifact path")
    parts = name.split("/")
    require(not PurePosixPath(name).is_absolute() and all(part not in ("", ".", "..") for part in parts),
            f"unsafe artifact path: {name}")
    require(not any(char in name for char in '\\:< >"|?*\0'.replace(" ", "")), f"unsafe artifact path: {name}")
    require(all(not part.endswith((".", " ")) and not re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part)
                for part in parts), f"unsafe Windows artifact path: {name}")
    candidate = root.joinpath(*parts)
    resolved = candidate.resolve(strict=existing)
    require(resolved.is_relative_to(root) and resolved != root, f"artifact escaped package: {name}")
    if existing:
        require(resolved.is_file(), f"artifact is not a file: {name}")
    return resolved


def read_bytes(path: Path, limit: int) -> bytes:
    require(path.stat().st_size <= limit, f"input byte budget exceeded: {path.name}")
    with path.open("rb") as source:
        data = source.read(limit + 1)
    require(len(data) <= limit, f"input grew past byte budget: {path.name}")
    return data


def read_object(path: Path, limit: int) -> dict[str, Any]:
    value = parse_json(read_bytes(path, limit), path.name)
    require(isinstance(value, dict), f"expected JSON object: {path.name}")
    return value


def verify_inventory(session: Path, limits: Limits) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    inventory_path = safe_path(session, "collected/inventory.json")
    inventory = read_object(inventory_path, limits.json_bytes)
    require(inventory.get("schema") == "endfieldCapture.collection.v1", "unsupported collection inventory schema")
    require(isinstance(inventory.get("session"), str) and 0 < len(inventory["session"]) <= 127, "invalid inventory session identity")
    artifacts = inventory.get("artifacts")
    require(isinstance(artifacts, list) and 0 < len(artifacts) <= limits.artifacts, "artifact count budget exceeded")
    require(inventory.get("files") == len(artifacts), "inventory file count mismatch")
    result, targets, total = {}, set(), 0
    for row in artifacts:
        require(isinstance(row, dict), "invalid inventory row")
        name = row.get("path")
        path = safe_path(session, name)
        target = str(path).casefold()
        require(name not in result and target not in targets, f"duplicate artifact path or alias: {name}")
        targets.add(target)
        size = integer(row.get("bytes"), f"artifact bytes: {name}", limits.artifact_bytes)
        digest = row.get("sha256")
        require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
                f"invalid artifact SHA256: {name}")
        total += size
        require(total <= limits.package_bytes, "package hash byte budget exceeded")
        before = path.stat()
        require(before.st_size == size, f"artifact size mismatch: {name}")
        actual, length = hashlib.sha256(), 0
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                length += len(block)
                require(length <= size, f"artifact grew while hashing: {name}")
                actual.update(block)
        after = path.stat()
        require(length == size and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                f"artifact changed while hashing: {name}")
        require(actual.hexdigest() == digest, f"artifact SHA256 mismatch: {name}")
        result[name] = {"path": path, "bytes": size, "sha256": digest}
    require(inventory.get("bytes") == total, "inventory total bytes mismatch")
    return result, {"artifacts": len(result), "bytes": total,
                    "sessionId": inventory["session"],
                    "inventorySha256": hashlib.sha256(read_bytes(inventory_path, limits.json_bytes)).hexdigest(),
                    "verifiedAgainstRetainedInventory": True, "inventoryOriginAuthenticated": False}


def bound_object(artifacts: dict[str, dict[str, Any]], name: str, limits: Limits) -> dict[str, Any]:
    require(name in artifacts, f"required artifact is not collection-bound: {name}")
    value = parse_json(bound_bytes(artifacts, name, limits.json_bytes), name)
    require(isinstance(value, dict), f"expected JSON object: {name}")
    return value


def snapshot_local_inventory(session: Path, limits: Limits) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Read the refactored path/size inventory; hashes describe this read only."""
    inventory_path = safe_path(session, "collected/inventory.json")
    inventory_bytes = read_bytes(inventory_path, limits.json_bytes)
    inventory = parse_json(inventory_bytes, "collected/inventory.json")
    require(isinstance(inventory, dict) and inventory.get("schema") == "endfieldCapture.inventory.v1",
            "local-files: unsupported current collection inventory")
    session_id = inventory.get("session")
    require(isinstance(session_id, str) and 0 < len(session_id) <= 127, "local-files: invalid session identity")
    rows = inventory.get("artifacts")
    require(isinstance(rows, list) and 0 < len(rows) <= limits.artifacts and inventory.get("files") == len(rows),
            "local-files: inventory count mismatch")
    artifacts, targets, listed_bytes, total = {}, set(), 0, 0

    def retain(name: str, expected_size: int | None = None) -> None:
        nonlocal total
        path = safe_path(session, name)
        require(name not in artifacts and str(path).casefold() not in targets, f"local-files: duplicate artifact: {name}")
        require(len(artifacts) < limits.artifacts, "local-files: artifact count exceeds budget")
        before = path.stat()
        size = integer(before.st_size, f"local file bytes: {name}", limits.artifact_bytes)
        require(expected_size is None or size == expected_size,
                f"local-files: size differs for {name}: expected {expected_size}, actual {size}")
        total += size
        require(total <= limits.package_bytes, "local-files: snapshot byte budget exceeded")
        digest, length = hashlib.sha256(), 0
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                length += len(block)
                require(length <= size, f"local-files: artifact grew: {name}")
                digest.update(block)
        after = path.stat()
        require(length == size and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                f"local-files: artifact changed: {name}")
        targets.add(str(path).casefold())
        artifacts[name] = {"path": path, "bytes": size, "sha256": digest.hexdigest()}

    for row in rows:
        require(isinstance(row, dict) and set(row) == {"path", "bytes"}, "local-files: requires the current path/size inventory")
        name = row.get("path")
        require(isinstance(name, str) and not name.startswith(("private/", "collected/")),
                "local-files: invalid public inventory path")
        size = integer(row.get("bytes"), f"listed file bytes: {name}", limits.artifact_bytes)
        retain(name, size)
        listed_bytes += size
    require(inventory.get("bytes") == listed_bytes,
            f"local-files: inventory total differs: expected {inventory.get('bytes')}, actual {listed_bytes}")
    for name in ("private/mission-trace-build-manifest.json", "private/mission-trace.activation",
                 "private/runtime.conf", "private/EndfieldCapture.dll"):
        retain(name)
    retained_profile=bound_object(artifacts,"private/mission-trace-build-manifest.json",limits)
    if retained_profile.get('schema')=='audioRuntimeTrace.hooks.v2':
        retain("private/audio-activation.json")
        retain("collected/summary.json")
    require(read_bytes(inventory_path, limits.json_bytes) == inventory_bytes, "local-files: inventory changed during reading")
    return artifacts, {"artifacts": len(artifacts), "bytes": total, "sessionId": session_id,
        "inventorySha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "verifiedAgainstRetainedInventory": False, "inventoryOriginAuthenticated": False,
        "listedPathSizesMatched": True, "hashSource": "offline local-file snapshot, not producer collection hashes",
        "snapshotInputs": [{"path": name, "bytes": row["bytes"], "sha256": row["sha256"]}
                           for name, row in sorted(artifacts.items())]}


def local_source_bindings(artifacts: dict[str, dict[str, Any]], limits: Limits, join_sources: bool):
    names = sorted(name for name in artifacts if name.startswith("source-files/"))
    result = {"status": "selectedExportContext", "nativeValidated": False, "files": len(names),
              "gaps": ["Selected pre-run export copies are source context; omitted sources and export/live-build joins remain unresolved."]}
    assignments = {}
    memberships = 0
    if join_sources:
        prefix = "source-files/export_full/game/Json/MissionRuntimeAsset/"
        for name in names:
            if not name.startswith(prefix) or not name.endswith(".json") or name.endswith("_meta.json"):
                continue
            data = bound_object(artifacts, name, limits)
            mission = data.get("missionId")
            quests = data.get("questDic")
            require(isinstance(mission, str) and re.fullmatch(r"[a-z0-9_]{1,80}", mission) and
                    name == prefix + mission + ".json" and isinstance(quests, dict) and len(quests) <= 4096,
                    f"local-files: invalid source mission membership: {name}")
            for quest, value in quests.items():
                require(isinstance(quest, str) and 0 < len(quest) <= 256 and
                        isinstance(value, dict) and value.get("questId") == quest,
                        f"local-files: invalid source quest membership: {name}")
                memberships += 1
                require(memberships <= limits.identifiers,
                        f"local-files: source membership count exceeds budget: {name}")
                assignments.setdefault(quest, []).append({"missionId": mission, "source": name,
                    "sourceSha256": artifacts[name]["sha256"], "sourcePath": f"questDic[{quest}]",
                    "boundary": "Stored membership in a selected pre-run export copy, not live instance construction."})
    return result, assignments


def bound_bytes(artifacts: dict[str, dict[str, Any]], name: str, limit: int) -> bytes:
    require(name in artifacts, f"required artifact is not collection-bound: {name}")
    row = artifacts[name]
    data = read_bytes(row["path"], limit)
    require(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
            f"bound artifact changed before decoding: {name}")
    return data


def validate_bounded_descriptor(field,fields,hook):
    kind=field['kind'];proof=field.get('rawProof')if kind!=7 else field.get('containerProof')
    require(isinstance(proof,dict)and proof.get('type')==field.get('type'),'bounded read lacks exact selected type proof')
    require(field.get('valueBits')is None and field.get('valueRepresentation')is None,'opaque bounded bytes cannot grant scalar or reference semantics')
    if kind==7:
        require(field.get('readMode')=='boundedContainer'and isinstance(proof.get('elementType'),str)
                and all(proof.get(k)==field.get(k)for k in ('countOffset','versionOffset','storageOffset','arrayLengthOffset','arrayDataOffset','elementStride')),
                'container source-layout binding differs')
        require(all(isinstance(proof.get(k),str)and '::'in proof[k]for k in ('countField','versionField','itemsField')),
                'container named fields missing')
    else:
        require(proof.get('byteCount')==field.get('byteCount')and type(proof.get('offset'))is int and proof['offset']>=0,
                'raw selected span binding differs')
        cells=proof.get('fields');require(isinstance(cells,list)and len(cells)<=16,'raw selected field-span declarations missing')
        if cells:
            require(all(isinstance(c,dict)and isinstance(c.get('field'),str)and isinstance(c.get('type'),str)
                        and type(c.get('offset'))is int and c['offset']>=0 and type(c.get('byteCount'))is int and c['byteCount']>0 for c in cells),'invalid raw selected field extent')
            require(min(c['offset']for c in cells)==proof['offset']
                    and max(c['offset']+c['byteCount']for c in cells)-proof['offset']==proof['byteCount'],'raw selected field range differs')
            for cell in cells:
                representation=cell.get('representationProof')
                if representation is None:continue
                require(isinstance(representation,dict)and representation.get('type')==cell['type']and representation.get('bytes')==cell['byteCount']==8,
                        'raw closed reference field storage differs')
                declared=representation.get('declaredTypeRecordHex','');definition=representation.get('definitionTypeRecordHex','')
                require(all(isinstance(x,str)and re.fullmatch('[0-9a-fA-F]{32}',x)is not None for x in(declared,definition)),
                        'raw closed reference native records missing')
                declared=bytes.fromhex(declared);definition=bytes.fromhex(definition)
                require(declared[10:12]==b'\x15\x00'and not int.from_bytes(declared[8:10],'little')&16
                        and definition[10:12]==b'\x12\x00'and int.from_bytes(definition[:8],'little')==representation.get('definitionTypeIndex')
                        and isinstance(representation.get('argumentTypes'),list)and bool(representation['argumentTypes']),
                        'raw closed reference carrier/definition differs')
        else:
            rep=field.get('argumentRepresentation')or{}
            require(proof.get('unboxedBytes')==proof['byteCount']or rep.get('mode')=='referenceByRef'
                    or isinstance(proof.get('sourceWitness'),dict),'whole raw storage lacks selected size/source proof')
            if kind==6 and proof.get('unboxedBytes')is not None and not field.get('fieldPath'):
                require(rep.get('mode')=='indirectValue'and rep.get('bytes')==proof['unboxedBytes'],
                        'whole raw value argument lacks indirect passing declaration')
        if kind==8:
            n=field['parentFieldIndex'];require(type(n)is int and 0<=n<len(fields),'dependent parent index invalid')
            parent=fields[n]
            require(fields.index(field)>n and parent.get('kind')==7 and parent.get('elementStride')==8
                    and parent.get('containerProof',{}).get('elementType')==field['type']
                    and field.get('offset')==proof['offset']and field.get('parentField')==parent.get('label'),
                    'dependent element nominal/span differs from selected parent')
    rep=field.get('argumentRepresentation')or{}
    if rep.get('mode')=='referenceByRef':
        p=rep.get('nativeArgumentProof')or{};raw=p.get('nativeTypeRecordHex','')
        require(isinstance(raw,str)and re.fullmatch('[0-9a-fA-F]{32}',raw)is not None,'reference byref native record missing')
        raw=bytes.fromhex(raw)
        params=[(n,x)for n,x in enumerate(hook.get('parameters',[]))if x.get('name')==field.get('argumentName')]
        require(kind==6 and field['byteCount']==8 and field['offset']==0 and field['chain0']==field['chain1']==4097
                and raw[10]==18 and raw[11]&0x7f==0x20 and int.from_bytes(raw[:8],'little')==p.get('typeDefinitionIndex')
                and p.get('type')==field['type']and p.get('byref')is True and len(params)==1 and params[0][1].get('type')==field['type']
                and field['arg']==params[0][0]+int(hook.get('receiverIdentity')is not None),'invalid reference byref output ABI')


def program(hook: dict[str, Any]) -> list[list[int]]:
    text = hook.get("readProgram")
    require(isinstance(text, str) and len(text) <= 4096 and (not text or text=='v2:'or text.endswith(";")), "invalid readProgram")
    bounded=text.startswith('v2:')
    if bounded:text=text[3:]
    result = []
    for item in text.split(";")[:-1] if text else []:
        require(re.fullmatch(r"\d+(?:,\d+){4,11}", item) is not None, "invalid readProgram row")
        row=list(map(int,item.split(',')));arg,kind,offset,chain0,chain1=row[:5]
        require(all(n<=0xffffffff for n in row)and arg <= 7 and 1 <= kind <= (8 if bounded else 5) and offset <= 4096 and chain0 <= 4097 and chain1 <= 4097,
                "readProgram bounds exceeded")
        require(chain0 != 4097 or chain1 == 4097, "readProgram second chain lacks first chain")
        require(kind != 4 or (offset == 0 and chain0 == chain1 == 4097), "scalar readProgram has memory path")
        require(len(row)=={6:6,7:12,8:8}.get(kind,5),'invalid readProgram arity')
        if kind==6:require(1<=row[5]<=256,'raw byte read exceeds bound')
        if kind==7:require(all(n<=4096 for n in row[5:10])and 1<=row[11]<=8 and 1<=row[10]<=256//row[11],'container read exceeds bound')
        if kind==8:
            require(row[5]<len(result)and 1<=row[7]<=32 and chain0==chain1==4097,'dependent read parent/span differs')
            parent=result[row[5]]
            require(parent[1]==7 and parent[10]==8 and row[6]<parent[11]and arg==parent[0],'dependent read requires prior reference-slot container')
        result.append(row)
    require(len(result) <= 24, "readProgram field count exceeded")
    return result


def caller_source_families(hook, by_name, profile, image_size):
    """Check retained complete unwind-family framing without reopening natives."""
    families=hook.get('captureCallerSourceWindows')
    if families is None:return None
    require(profile.get('recipeSchema')=='endfield.mission-trace-capture-recipe.v15'
            and isinstance(families,list)and 1<=len(families)<=16,'invalid caller source-family selection')
    from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex
    result=[];names=set()
    for family in families:
        require(isinstance(family,dict)and set(family)=={'callerHook','callerMethodIndex','callerEntryRva','ownership','windows'},'invalid caller source-family shape')
        caller=by_name.get(family['callerHook']);entry=family['callerEntryRva']
        require(caller is not None and caller is not hook and caller.get('observationMode')=='paired'
                and caller['name']not in names and type(entry)is int and entry==int(caller['rva'],16)
                and type(family['callerMethodIndex'])is int and family['callerMethodIndex']==caller.get('methodIndex'),
                'caller source-family metadata/entry mismatch')
        names.add(caller['name']);owner=family['ownership'];windows=family['windows']
        require(isinstance(owner,dict)and owner.get('schema')=='endfield.amd64-unwind-chain-family.v1'
                and type(owner.get('selectedPrimaryRva'))is int and owner.get('selectedPrimaryRva')==entry
                and all(owner.get(k)is True for k in ('completeParentTriplesChecked','allParentChainsTerminated','chainFrameBytesMatched'))
                and all(owner.get(k)is False for k in ('unwindOperationsOrFixedAllocationSemanticsProved','handlerLanguageDataProved','wholeManagedMethodProgramProved','runtimeExecutionKnown')),
                'caller source-family ownership boundary differs')
        ranges=owner.get('ranges');require(isinstance(ranges,list)and isinstance(windows,list)and 1<=len(ranges)==len(windows)<=256,'caller source-family range bounds')
        table=integer(owner.get('tableRva'),'caller unwind table RVA',2**32-1);table_bytes=integer(owner.get('tableBytes'),'caller unwind table bytes',2**32-1)
        require(table>0 and table%4==0 and table_bytes>0 and table_bytes%12==0 and table+table_bytes<=image_size
                and type(owner.get('tableRowsChecked'))is int and owner['tableRowsChecked']==table_bytes//12
                and isinstance(owner.get('tableSha256'),str)and re.fullmatch('[0-9a-fA-F]{64}',owner['tableSha256'])is not None,
                'caller source-family full-table provenance differs')
        triples=[];unwind={};decoded=[];last=0;total=0;table_rows=set()
        for part,window in zip(ranges,windows):
            require(isinstance(part,dict)and isinstance(window,dict)and set(window)=={'startRva','endRva','sha256','rawHex'},'caller family window shape')
            triple=part.get('runtimeTriple');require(isinstance(triple,list)and len(triple)==3 and all(type(n)is int and 0<n<2**32 for n in triple),'caller family runtime triple')
            start,end,info=triple
            require(last<=start<end<=image_size and info%4==0 and type(window['startRva'])is int and type(window['endRva'])is int and window['startRva']==start and window['endRva']==end,'caller family range coordinates/order')
            last=end;raw=window['rawHex']
            require(isinstance(raw,str)and len(raw)==2*(end-start)and re.fullmatch('[0-9a-fA-F]+',raw)is not None,'caller family full window bytes')
            data=bytes.fromhex(raw);total+=len(data);require(total<=1024*1024,'caller family byte budget')
            require(isinstance(window['sha256'],str)and window['sha256'].lower()==hashlib.sha256(data).hexdigest(),'caller family window hash')
            packed=struct.pack('<III',*triple).hex();row=integer(part.get('tableRowRva'),'caller family table row',2**32-1)
            require(part.get('runtimeTripleRawHex','').lower()==packed and type(part.get('codeBytes'))is int and part.get('codeBytes')==len(data)
                    and all(type(part.get(k))is int for k in ('unwindVersion','unwindFlags','frameByte'))
                    and table<=row<row+12<=table+table_bytes and (row-table)%12==0 and row not in table_rows,'caller family exact table-row framing')
            table_rows.add(row);triples.append(tuple(triple));decoded.append((start,end,data))
            record=part.get('unwindRawHex')
            require(isinstance(record,str)and re.fullmatch('(?:[0-9a-fA-F]{2}){4,2048}',record)is not None,'caller family unwind record framing')
            for offset,value in enumerate(bytes.fromhex(record)):
                require(info+offset<image_size and (info+offset not in unwind or unwind[info+offset]==value),'caller family conflicting unwind bytes')
                unwind[info+offset]=value
        def read_unwind(at,count):
            require(type(at)is int and type(count)is int and 0<=count<=4096 and all(at+i in unwind for i in range(count)),'caller family missing unwind bytes')
            return bytes(unwind[at+i]for i in range(count))
        try:
            checked=UnwindChainIndex(b''.join(struct.pack('<III',*t)for t in triples),read_unwind,table_rva=table,image_size=image_size).family(entry)
        except (ValueError,KeyError,IndexError)as exc:raise InspectionError('caller family retained unwind replay: '+str(exc)[:512])from exc
        for actual,claimed in zip(checked['ranges'],ranges):
            require(all(actual[k]==claimed.get(k)for k in ('runtimeTriple','runtimeTripleRawHex','codeBytes','unwindRawHex','unwindVersion','unwindFlags','frameByte','parentChain')),
                    'caller family parent-chain/raw-unwind replay differs')
        require(len(checked['ranges'])==len(ranges),'caller family includes foreign/unowned range')
        # Bind the original contiguous descriptor too, without filling gaps.
        body_end=entry+integer(caller.get('bodyBytes'),'caller primary body bytes',1024*1024);cursor=entry;parts=[]
        for start,end,data in decoded:
            if end<=cursor:continue
            if start!=cursor or cursor>=body_end:break
            stop=min(end,body_end);parts.append(data[:stop-start]);cursor=stop
        require(cursor==body_end and hashlib.sha256(b''.join(parts)).hexdigest()==caller.get('bodySha256'),
                'caller family/original contiguous body hash differs')
        result.append((family,decoded))
    return result


def bindings(artifacts: dict[str, dict[str, Any]], limits: Limits) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    retained_profile = bound_object(artifacts, "private/mission-trace-build-manifest.json", limits)
    from scripts.game_data.mission_trace_audio_links import mission_projection
    profile,combined = mission_projection(retained_profile)
    summary = bound_object(artifacts, "mission-trace/summary.json", limits)
    session = bound_object(artifacts, "session.json", limits)
    require(profile.get("schema") in {"endfieldCapture.missionTraceBuild.v1","endfieldCapture.missionTraceBuild.v2"}, "unsupported retained profile schema")
    bounded_profile=profile.get('schema')=='endfieldCapture.missionTraceBuild.v2'
    require(not bounded_profile or profile.get('recipeSchema')=='endfield.mission-trace-capture-recipe.v15','bounded profile requires recipe v15')
    require(not bounded_profile or profile.get('observerProviders')==['mission-trace']and type(profile.get('providerMask'))is int and profile['providerMask']==128,
            'bounded provider declaration must exactly select mission-trace/128; combined audio not supported by this package gate')
    require(summary.get("schema") in ("endfieldCapture.missionTraceSummary.v1", "endfieldCapture.missionTraceSummary.v2", "endfieldCapture.missionTraceSummary.v3","endfieldCapture.missionTraceSummary.v4","endfieldCapture.missionTraceSummary.v5"),
            "unsupported provider summary schema")
    require(session.get("schema") == "endfieldCapture.session.v1" and profile.get("profile") == "mission-trace" and
            type(session.get("providers"))is int and session.get("providers") == (130 if combined else 128) and session.get("gameBuild") == profile.get("gameBuild"), "session/profile binding mismatch")
    hooks, summary_hooks = profile.get("missionTraceHooks"), summary.get("hooks")
    require(isinstance(hooks, list) and 0 < len(hooks) <= 96 and isinstance(summary_hooks, list), "hook count bounds exceeded")
    require(len(hooks) == len(summary_hooks) == summary.get("hookCount"), "profile/summary hook count mismatch")
    paired_profile = any(PAIRED_ABI.fullmatch(h.get('abiId', '')) for h in hooks if isinstance(h, dict))
    if paired_profile:
        require(summary.get('schema') == ('endfieldCapture.missionTraceSummary.v5'if combined else'endfieldCapture.missionTraceSummary.v4'if bounded_profile else'endfieldCapture.missionTraceSummary.v3') and summary.get('entryOnly') is False
                and summary.get('returnValuesObserved') is True and summary.get('pairedDepthLimit') == 64,
                'paired profile/receipt phase policy mismatch')
        integer(summary.get('pairingFailures'), 'pairing failures')
    else:
        require(not combined and (summary.get('schema') == 'endfieldCapture.missionTraceSummary.v4'if bounded_profile else summary.get('schema')not in{'endfieldCapture.missionTraceSummary.v3','endfieldCapture.missionTraceSummary.v4','endfieldCapture.missionTraceSummary.v5'}), 'paired receipt without paired hooks')
    files = profile.get("files", {})
    require(isinstance(files, dict) and all(isinstance(files.get(key), dict) for key in ("gameAssembly", "metadata")),
            "invalid profile native inputs")
    hashes = []
    for key, receipt in (("gameAssembly", "gameAssemblySha256"), ("metadata", "metadataSha256")):
        digest = files.get(key, {}).get("sha256")
        require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None and summary.get(receipt) == digest,
                f"profile/summary native input binding mismatch: {key}")
        hashes.append(digest)
    layouts=profile.get('readLayouts')
    if layouts is not None:
        require(bounded_profile and isinstance(layouts,dict)and layouts.get('schema')=='endfield.patrol-capture-read-layouts.v1'
                and layouts.get('openGenericOffsetsRead')is False and layouts.get('runtimeSelectionObserved')is False
                and layouts.get('liveContainerContentsObserved')is False and layouts.get('wireGrammarAdmitted')is False,
                'invalid selected raw-layout source boundary')
        pins=layouts.get('nativeInputs')or{}
        require(all(isinstance(pins.get(k),str)and pins[k].lower()==v for k,v in zip(('GameAssembly.dll','global-metadata.dat'),hashes)),
                'raw-layout source/native input mismatch')
    activation = ("schema=missionRuntimeTrace.activation." + ("v2" if any(h.get("captureCallerReturnRvas") for h in hooks) else "v1") + "\ngame_assembly_sha256=" + hashes[0] +
                  "\nmetadata_sha256=" + hashes[1] + "\nhook_count=" + str(len(hooks)) + "\n")
    names, rvas = set(), set()
    for index, (hook, receipt) in enumerate(zip(hooks, summary_hooks)):
        require(isinstance(hook, dict) and isinstance(receipt, dict), "invalid hook descriptor")
        name = hook.get("name")
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.$<>+`-]{1,127}", name) is not None and name not in names, "invalid or repeated hook name")
        names.add(name)
        if hook.get('declaringImage') is not None or hook.get('declaringImageProof') is not None:
            owner=hook.get('declaringImageProof') or {}
            require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                    and isinstance(hook.get('declaringImage'),str)
                    and owner.get('imageName')==hook['declaringImage']
                    and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}\.dll',hook['declaringImage']) is not None
                    and owner.get('methodIndex')==hook.get('methodIndex')
                    and isinstance(hook.get('symbol'),str)
                    and hook.get('symbol')==owner.get('type','')+'.'+hook.get('symbol','').rsplit('.',1)[-1]
                    and all(type(owner.get(k)) is int and owner[k]>=0 for k in ('imageIndex','typeDefinitionIndex','methodIndex','methodStart','methodCount'))
                    and owner['methodStart']<=owner['methodIndex']<owner['methodStart']+owner['methodCount']
                    and hook.get('receiverIdentity') is None
                    and all(p.get('type') in {'bool','int','uint','long','ulong'} for p in hook.get('parameters',[]))
                    and all(not f.get('fieldPath') and f.get('argumentName')!='this' for f in hook.get('fields',[])),
                    'invalid declaring image/method owner binding')
        try:
            rva = int(hook["rva"], 16) if isinstance(hook.get("rva"), str) else integer(hook.get("rva"), "hook RVA")
        except (ValueError, KeyError) as exc:
            raise InspectionError("invalid hook RVA") from exc
        require(0 < rva < 1 << 32 and rva not in rvas, "invalid or repeated hook RVA")
        rvas.add(rva)
        paired = PAIRED_ABI.fullmatch(hook.get('abiId', ''))
        require(hook.get("module") == "GameAssembly.dll" and (hook.get("abiId") == "win64.transparent_entry_snapshot.v1" or paired), "unsupported hook ABI/module")
        if paired:
            proof = hook.get('pairedAbiProof', {})
            if bounded_profile and hook.get('returnType')in{'void','bool'}:
                ordinary=proof.get('ordinaryReturn')or{};raw=ordinary.get('nativeTypeRecordHex','');return_name=hook['returnType']
                require(isinstance(raw,str)and re.fullmatch('[0-9a-fA-F]{32}',raw)is not None,
                        'paired ordinary return native declaration missing')
                require(bytes.fromhex(raw)[10]=={'void':1,'bool':2}[return_name]and bytes.fromhex(raw)[11]&0x7f==0
                        and ordinary.get('type')==return_name and ordinary.get('byref')is False
                        and ordinary.get('bits')==(0 if return_name=='void'else 8)
                        and ordinary.get('register')==('none'if return_name=='void'else'al'),
                        'paired primitive return has byref/ABI decoration')
            scoped=hook['abiId'].startswith('win64.scoped_')
            require((hook.get('captureScope')=='paired-ancestor') == scoped
                    and (not scoped or profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}),
                    'paired scope/ABI binding differs')
            if paired[1]=='int':
                enum=proof.get('enumReturn',{});raw=enum.get('nativeTypeRecordHex','')
                require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                        and isinstance(raw,str) and re.fullmatch('[0-9a-f]{32}',raw) is not None,
                        'invalid enum return native record')
                native=bytes.fromhex(raw)
                require(proof.get('returnStorage')=='int' and enum.get('storageType')=='int'
                        and enum.get('type')==hook.get('returnType')==proof.get('returnType')
                        and enum.get('bits')==32 and enum.get('register')=='eax'
                        and native[10]==17 and native[11]&0x7f==0
                        and int.from_bytes(native[:8],'little')==enum.get('typeDefinitionIndex')
                        and enum.get('type') in profile.get('enumDefinitions',{}), 'invalid Int32 enum return ABI')
                definition = profile['enumDefinitions'][enum['type']]
                require(isinstance(definition, dict) and definition.get('storageType') == 'int'
                        and definition.get('valueBits') == 32 and definition.get('signed') is True
                        and isinstance(definition.get('members'), list) and 0 < len(definition['members']) <= 4096
                        and all(isinstance(m, dict) and isinstance(m.get('name'), str) and 0 < len(m['name']) <= 256
                                and type(m.get('value')) is int and -2**31 <= m['value'] < 2**31
                                for m in definition['members']), 'invalid Int32 enum return definition')
            mixed = hook.get('abiId') == 'win64.paired_double_slot2_void_4.v1'
            single='paired_float_slot1_'in hook.get('abiId','')
            if single:
                inputs=proof.get('scalarInputs',[])
                require(bounded_profile and hook.get('returnType')in{'void','bool'}and len(inputs)==1
                        and [p.get('type')for p in hook.get('parameters',[])]==['float']
                        and hook.get('receiverIdentity')is not None,'invalid Single slot1 input signature')
                input_proof=inputs[0]
                require(input_proof.get('mode')=='scalarRegister'and input_proof.get('type')=='float'
                        and input_proof.get('slot')==1 and input_proof.get('register')=='xmm1'
                        and input_proof.get('bits')==32 and input_proof.get('bytes')==4
                        and scalar_type_record(input_proof,'float',byref=False),'invalid Single slot1 type/ABI')
            if mixed:
                scalar_inputs=proof.get('scalarInputs',[])
                require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v10','endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                        and hook.get('returnType') == 'void' and len(scalar_inputs)==1
                        and hook.get('receiverIdentity') is not None
                        and [p.get('type') for p in hook.get('parameters',[])] == ['string','double'],
                        'invalid mixed scalar input signature')
                input_proof=scalar_inputs[0]
                require(input_proof.get('slot') == 2 and input_proof.get('register') == 'xmm2'
                        and input_proof.get('mode') == 'scalarRegister' and input_proof.get('type') == 'double'
                        and scalar_type_record(input_proof,'double',byref=False),
                        'invalid mixed scalar input native type')
            elif not single:
                require(not proof.get('scalarInputs'),'scalar inputs require typed mixed ABI')
            if int(paired[2]) == 5:
                require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v10','endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'},
                        'fifth paired GP slot requires recipe v10')
            require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v8', 'endfield.mission-trace-capture-recipe.v9', 'endfield.mission-trace-capture-recipe.v10', 'endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'} and hook.get('observationMode') == 'paired'
                    and proof.get('argumentSlots') == int(paired[2]) and proof.get('includesMethodInfo') is True
                    and (proof.get('returnType') == paired[1] and hook.get('returnType') == paired[1]
                         or paired[1]=='int' and proof.get('returnStorage')=='int')
                    and len(hook.get('parameters', [])) + int(hook.get('receiverIdentity') is not None) + 1 == int(paired[2]),
                    'invalid paired ABI provenance')
        if paired and paired[1] in {'float', 'double'}:
            scalar = proof.get('scalarReturn', {})
            bits = 32 if paired[1] == 'float' else 64
            require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v9', 'endfield.mission-trace-capture-recipe.v10', 'endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                    and scalar.get('type') == paired[1] and scalar.get('bits') == bits
                    and scalar.get('register') == 'xmm0' and scalar.get('representation') == 'rawIeee754Bits',
                    'invalid floating return provenance')
            require(scalar_type_record(scalar, paired[1], byref=False), 'invalid floating return type record')
        expected = hook.get("expectedBytes")
        require(isinstance(expected, str) and re.fullmatch(r"(?:[0-9a-f]{2}){16,256}", expected) is not None, "invalid native prefix")
        reads = program(hook)
        require(hook.get('readProgram','').startswith('v2:')==bounded_profile,'profile/readProgram schema differs')
        fields = hook.get("fields")
        require(isinstance(fields, list) and len(fields) == len(reads), "retained typed field metadata missing")
        opaque = hook.get('pairedAbiProof', {}).get('opaqueByRefArguments', [])
        require(isinstance(opaque, list) and len(opaque) <= len(hook.get('parameters', [])),
                'opaque byref argument bounds differ')
        opaque_names = set()
        for witness in opaque:
            require(isinstance(witness, dict), 'invalid opaque byref witness')
            argument = witness.get('argument'); raw = witness.get('nativeTypeRecordHex', '')
            matches = [(n, p) for n, p in enumerate(hook.get('parameters', [])) if p.get('name') == argument]
            require(paired and profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                    and isinstance(argument, str) and argument not in opaque_names and len(matches) == 1
                    and isinstance(raw, str) and re.fullmatch('[0-9a-f]{32}', raw) is not None,
                    'invalid opaque byref parameter binding')
            opaque_names.add(argument)
            n, parameter = matches[0]; native = bytes.fromhex(raw)
            slot = n + int(hook.get('receiverIdentity') is not None)
            require(witness.get('type') == parameter.get('type') and witness.get('mode') == 'opaqueValueByRef'
                    and witness.get('bytes') == 8 and witness.get('byref') is True
                    and witness.get('pointeeRead') is False and native[10] == 17 and native[11] & 0x7f == 0x20
                    and int.from_bytes(native[:8], 'little') == witness.get('typeDefinitionIndex')
                    and type(witness.get('nativeTypeIndex')) is int and witness['nativeTypeIndex'] >= 0
                    and not any(read[0] == slot for read in reads),
                    'opaque byref must forward a declared value pointer without reads')
        if "anonymousEntryProof" in hook or name == "buff.AbilityActionData.DispatchAssignData":
            proof, caller = hook.get("anonymousEntryProof"), hook.get("sourceCaller")
            require(profile.get("recipeSchema") in {"endfield.mission-trace-capture-recipe.v6", "endfield.mission-trace-capture-recipe.v7", "endfield.mission-trace-capture-recipe.v8", "endfield.mission-trace-capture-recipe.v9", "endfield.mission-trace-capture-recipe.v10", "endfield.mission-trace-capture-recipe.v11", "endfield.mission-trace-capture-recipe.v12", "endfield.mission-trace-capture-recipe.v13", "endfield.mission-trace-capture-recipe.v14","endfield.mission-trace-capture-recipe.v15"}
                    and isinstance(proof, dict) and isinstance(caller, dict)
                    and all(isinstance(field, dict) for field in fields)
                    and isinstance(caller.get("returnType"), str)
                    and hook.get("methodIndex") is None and hook.get("returnType") == "unobserved"
                    and proof.get("dataIsCallerReceiver") is True
                    and proof.get("argumentRegisters") == {"action": "rdx", "data": "r8", "environment": "r9"}
                    and isinstance(caller.get("methodIndex"), int)
                    and proof.get("callerMethodIndex") == caller["methodIndex"],
                    "invalid anonymous assignment provenance")
            receiver = hook.get("receiverIdentity")
            require(isinstance(receiver, dict) and receiver.get("arg") == 1
                    and receiver.get("type") == caller.get("returnType"),
                    "invalid anonymous assignment receiver")
            require(isinstance(caller.get("symbol"), str) and caller["symbol"].endswith(".NewAction")
                    and isinstance(caller.get("parameters"), list) and len(caller["parameters"]) == 1
                    and isinstance(caller["parameters"][0], dict), "invalid anonymous assignment caller")
            expected_types = {"suppliedActionIdentity": (1, caller["returnType"]),
                              "suppliedDataIdentity": (2, caller["symbol"].rsplit(".", 1)[0]),
                              "suppliedEnvironmentIdentity": (3, caller["parameters"][0].get("type"))}
            require(len(fields) == 3 and {field.get("label") for field in fields} == set(expected_types)
                    and all((field.get("arg"), field.get("type")) == expected_types[field["label"]]
                            and field.get("valueRepresentation") == "referenceIdentity"
                            and field.get("kind") == 4 and field.get("offset") == 0
                            and field.get("chain0") == field.get("chain1") == 4097
                            and not field.get("fieldPath") and not field.get("argumentRepresentation") for field in fields),
                    "anonymous assignment requires three pure register identities")
        labels = set()
        for field, read in zip(fields, reads):
            require(isinstance(field, dict) and isinstance(field.get("label"), str) and 0 < len(field["label"]) <= 127,
                    "invalid field label")
            require(field["label"] not in labels, "repeated field label")
            labels.add(field["label"])
            keys=['arg','kind','offset','chain0','chain1']+({6:['byteCount'],7:['countOffset','versionOffset','storageOffset','arrayLengthOffset','arrayDataOffset','elementStride','maxCount'],8:['parentFieldIndex','itemIndex','byteCount']}.get(field.get('kind'),[]))
            require([field.get(key)for key in keys]==read, "field/readProgram binding mismatch")
            if field.get('kind',0)>=6:validate_bounded_descriptor(field,fields,hook)
            if field.get('kind')==7:
                source=(layouts or{}).get('containers',{}).get(field['type'])
                require(isinstance(source,dict),'container lacks retained fresh source witness')
                expected={k:v for k,v in source.items()if k!='evidence'}
                expected.update(type=field['type'],sourceWitness=dict(schema=layouts['schema'],type=field['type']))
                require(field['containerProof']==expected,'container descriptor/source witness mismatch')
            witness=(field.get('rawProof')or{}).get('sourceWitness')
            if field.get('readMode')=='virtualCallbackPair':
                source=(layouts or{}).get('callbacks',{}).get(field.get('callbackRole'))
                require(isinstance(source,dict)and source.get('receiverType')==field['type']
                        and source.get('byteCount')==field.get('byteCount')==16
                        and source.get('callbackOffset')==field['offset']and source.get('methodInfoOffset')==field['offset']+8
                        and source.get('liveSelectionObserved')is False and source.get('actualCallbackEffectsProved')is False
                        and witness==dict(schema=layouts['schema'],callbackRole=field['callbackRole'],type=field['type']),
                        'virtual callback descriptor/source witness mismatch')
            elif witness is not None:
                source=(layouts or{}).get('values',{}).get(field['type'])
                require(isinstance(source,dict)and source.get('byteCount')==field.get('byteCount')
                        and witness==dict(schema=layouts['schema'],type=field['type'],byteCount=source['byteCount']),
                        'raw span descriptor/source witness mismatch')
            for cell in (field.get('rawProof')or{}).get('fields',[]):
                witness=cell.get('sourceWitness')
                if witness is None:continue
                source=(layouts or{}).get('values',{}).get(cell['type'])
                require(isinstance(source,dict)and source.get('byteCount')==cell['byteCount']
                        and witness==dict(schema=layouts['schema'],type=cell['type'],byteCount=cell['byteCount']),
                        'raw field storage/source witness mismatch')
            require(isinstance(field.get("type"), str) and len(field["type"]) <= 256, "invalid field type")
            require(field.get("valueBits") in (None, 8, 16, 32, 64), "unsupported field width")
            representation = field.get("valueRepresentation")
            require(representation in (None, "referenceIdentity"), "unsupported value representation")
            if representation == "referenceIdentity":
                require(profile.get("recipeSchema") in {"endfield.mission-trace-capture-recipe.v4", "endfield.mission-trace-capture-recipe.v5", "endfield.mission-trace-capture-recipe.v6", "endfield.mission-trace-capture-recipe.v7", "endfield.mission-trace-capture-recipe.v8", "endfield.mission-trace-capture-recipe.v9", "endfield.mission-trace-capture-recipe.v10", "endfield.mission-trace-capture-recipe.v11", "endfield.mission-trace-capture-recipe.v12", "endfield.mission-trace-capture-recipe.v13", "endfield.mission-trace-capture-recipe.v14","endfield.mission-trace-capture-recipe.v15"}
                        and field.get("valueBits") == 64 and field.get("kind") in (1, 4)
                        and field.get("storageType") == "ulong" and field.get("signed") is False,
                        "invalid reference identity binding")
            argument_representation = field.get('argumentRepresentation') or {}
            if bounded_profile and field.get('argumentName')!='this'and not argument_representation:
                ordinary=field.get('argumentAbi')or{};raw=ordinary.get('nativeTypeRecordHex','')
                matches=[(n,p)for n,p in enumerate(hook.get('parameters',[]))if p.get('name')==field.get('argumentName')]
                require(len(matches)==1 and isinstance(raw,str)and re.fullmatch('[0-9a-fA-F]{32}',raw)is not None,
                        'ordinary bounded argument native declaration missing')
                require(bytes.fromhex(raw)[11]&0x7f==0 and ordinary.get('byref')is False
                        and ordinary.get('argument')==field['argumentName']and ordinary.get('type')==matches[0][1].get('type')
                        and ordinary.get('slot')==field['arg']==matches[0][0]+int(hook.get('receiverIdentity')is not None),
                        'ordinary bounded argument has byref/ABI decoration or wrong slot')
            if argument_representation.get('mode') == 'scalarRegister':
                witness=argument_representation.get('nativeArgumentProof',{})
                input_slot=1 if single else 2;input_type='float'if single else'double'
                require(paired and (mixed or single) and witness==input_proof
                        and field.get('argumentName') == hook['parameters'][input_slot-1]['name'] == witness.get('argument')
                        and field.get('arg') == input_slot and field.get('kind') == 4 and field.get('type') == input_type
                        and field.get('valueBits') == (32 if single else 64) and field.get('offset') == 0
                        and field.get('chain0') == field.get('chain1') == 4097 and not field.get('fieldPath')
                        and field.get('observation') == 'argument-register-bits',
                        'invalid mixed scalar field binding')
            if argument_representation.get('mode') == 'scalarByRef':
                scalar_name = field['type']; bits = {'bool': 8, 'float': 32, 'double': 64}.get(scalar_name)
                witness = argument_representation.get('nativeArgumentProof') or {}
                parameters = hook.get('parameters') or []
                param = [n for n,p in enumerate(parameters) if p.get('name') == field.get('argumentName') and p.get('type') == scalar_name]
                require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v9', 'endfield.mission-trace-capture-recipe.v10', 'endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                        and paired and scalar_name in {'bool','float','double'} and len(param) == 1
                        and field.get('arg') == param[0] + int(hook.get('receiverIdentity') is not None)
                        and field.get('kind') == {'bool': 5, 'float': 2, 'double': 1}.get(scalar_name) and field.get('valueBits') == bits
                        and field.get('offset') == 0 and field.get('chain0') == field.get('chain1') == 4097
                        and not field.get('fieldPath') and field.get('observation') == 'argument-pointee'
                        and witness.get('type') == scalar_name and witness.get('bytes') == bits // 8
                        and witness.get('byref') is True and scalar_type_record(witness, scalar_name, byref=True),
                        'invalid scalar byref argument provenance')
            path = field.get("fieldPath", [])
            require(isinstance(path, list) and len(path) <= 8 and all(isinstance(part, dict) and
                    isinstance(part.get("field"), str) and len(part["field"]) <= 512 for part in path), "invalid typed field path")
        if paired:
            receiver = proof.get('unboxedReceiver')
            if receiver is not None:
                identity = hook.get('receiverIdentity') or {}
                size = receiver.get('unboxedBytes') if isinstance(receiver, dict) else None
                require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                        and isinstance(receiver, dict) and type(size) is int and 1 <= size <= 4096
                        and receiver.get('argument') == 'this' and receiver.get('type') == identity.get('type')
                        and receiver.get('methodIndex') == hook.get('methodIndex')
                        and type(receiver.get('typeDefinitionIndex')) is int and receiver['typeDefinitionIndex'] >= 0
                        and receiver.get('mode') == 'indirectValue' and receiver.get('boxedHeaderBytes') == 16
                        and receiver.get('passing') == proof.get('receiverPassing') == 'normalMethodUnboxedThisPointer'
                        and identity.get('arg') == 0, 'invalid unboxed value receiver proof')
            for field in fields:
                if (proof.get('receiverPassing') == 'normalMethodUnboxedThisPointer'
                        and field.get('arg') == 0 and field.get('fieldPath')
                        and profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}):
                    representation = field.get('argumentRepresentation') or {}
                    cell = field['fieldPath'][0]; offset = cell.get('offset'); width = cell.get('storageBytes')
                    require(receiver is not None and field.get('argumentName') == 'this'
                            and representation.get('mode') == 'indirectValue' and representation.get('bytes') == size
                            and representation.get('nativeArgumentProof') == receiver
                            and type(offset) is int and type(width) is int and 0 <= offset and width > 0
                            and offset + width <= size and cell.get('boxedOffset') == offset + 16,
                            'normal value receiver field lacks unboxed layout binding')
            indirect = proof.get('indirectAggregateArguments', [])
            require(isinstance(indirect,list) and len(indirect) <= 4, 'invalid indirect aggregate proof list')
            names=set()
            for aggregate in indirect:
                raw=aggregate.get('nativeTypeRecordHex','')
                require(profile.get('recipeSchema') in {'endfield.mission-trace-capture-recipe.v10','endfield.mission-trace-capture-recipe.v11','endfield.mission-trace-capture-recipe.v12','endfield.mission-trace-capture-recipe.v13','endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                        and isinstance(raw,str) and re.fullmatch('[0-9a-f]{32}',raw) is not None,
                        'invalid indirect aggregate type record')
                record=bytes.fromhex(raw);size=aggregate.get('unboxedBytes');argument=aggregate.get('argument')
                require(aggregate.get('mode') == 'indirectValue' and type(size) is int
                        and 1 <= size <= 4096 and (size not in {1,2,4,8}or bool(record[11]&0x20))
                        and record[10] == 0x11 and record[11] & 0x7f in {0,0x20}
                        and aggregate.get('byref') is bool(record[11] & 0x20)
                        and isinstance(argument,str) and argument not in names,
                        'invalid indirect aggregate ABI proof')
                names.add(argument)
                require(any(p.get('name') == argument and p.get('type') == aggregate.get('type')
                            for p in hook.get('parameters',[])) and any(
                        f.get('argumentName') == argument and (f.get('fieldPath')or f.get('kind')==6)
                        and (f.get('argumentRepresentation') or {}).get('mode') == 'indirectValue'
                        and (f.get('argumentRepresentation') or {}).get('bytes') == size for f in fields),
                        'indirect aggregate field/parameter binding differs')
            for field in fields:
                if (field.get('argumentRepresentation') or {}).get('mode') == 'indirectValue':
                    require(field.get('argumentName') in names or
                            (field.get('argumentRepresentation') or {}).get('nativeArgumentProof') is not None,
                            'paired indirect field lacks aggregate or native argument proof')
        if paired:
            require(all(p.get('type') not in {'float','double'} or any(
                        f.get('argumentName') == p.get('name') and f.get('type') == p.get('type')
                        and (f.get('argumentRepresentation') or {}).get('mode') in {'scalarByRef','scalarRegister'} for f in fields)
                        for p in hook.get('parameters', [])), 'paired observer has unproved XMM/byref argument')
        require(receipt.get("index") == index and receipt.get("name") == name and receipt.get("rva") == rva and receipt.get("reads") == reads,
                "profile/summary hook binding mismatch")
        integer(receipt.get("calls"), "hook calls")
        activation += f"hook={name}|{rva:x}|{hook['abiId']}|{expected}|{hook['readProgram']}\n"
    by_name={h['name']:h for h in hooks}
    for index,hook in enumerate(hooks):
        scope=hook.get('captureCallerReturnRvas');proofs=hook.get('captureCallerProofs')
        if scope is None and proofs is None:
            require('captureCallerSourceWindows'not in hook,'caller source-family lacks scope/proofs')
            continue
        require(profile.get('recipeSchema')in{'endfield.mission-trace-capture-recipe.v14','endfield.mission-trace-capture-recipe.v15'}
                and hook.get('captureScope')=='paired-ancestor' and isinstance(scope,str)
                and isinstance(proofs,list) and 1<=len(proofs)<=32, 'invalid caller scope shape')
        families=caller_source_families(hook,by_name,profile,integer(summary.get('moduleImageSize'),'module image size',2**32-1))
        used_families=set();returns=[]
        for proof in proofs:
            require(isinstance(proof,dict), 'invalid caller scope proof')
            caller=by_name.get(proof.get('callerHook'));encoded=proof.get('callBytes','')
            require(caller is not None and caller is not hook and caller.get('observationMode')=='paired'
                    and proof.get('callerMethodIndex')==caller.get('methodIndex')
                    and proof.get('callerBodySha256')==caller.get('bodySha256')
                    and re.fullmatch('e8[0-9a-f]{8}',encoded) is not None
                    and type(proof.get('callRva')) is int and type(proof.get('returnRva')) is int
                    and proof['returnRva']==proof['callRva']+5
                    and proof.get('targetRva')==int(hook['rva'],16)
                    and proof['returnRva']+int.from_bytes(bytes.fromhex(encoded)[1:],'little',signed=True)==proof['targetRva'],
                    'invalid caller scope direct-call binding')
            if families is None:
                require(not any(k in proof for k in ('callerSourceFamilyIndex','callerWindowStartRva','callerWindowEndRva','callerWindowSha256'))
                        and int(caller['rva'],16)<=proof['callRva']<proof['returnRva']<=int(caller['rva'],16)+caller['bodyBytes'],
                        'caller contiguous direct-call binding differs')
            else:
                require(set(proof)=={'callerHook','callerMethodIndex','callerBodySha256','callRva','returnRva','callBytes','targetRva',
                        'callerSourceFamilyIndex','callerWindowStartRva','callerWindowEndRva','callerWindowSha256'},'caller source-family proof shape')
                family_index=proof.get('callerSourceFamilyIndex')
                require(type(family_index)is int and 0<=family_index<len(families),'caller source-family index')
                family,windows=families[family_index];used_families.add(family_index)
                require(family['callerHook']==proof['callerHook']and family['callerMethodIndex']==proof['callerMethodIndex'],
                        'caller source-family proof owner differs')
                matches=[(a,b,raw)for a,b,raw in windows if a==proof.get('callerWindowStartRva')and b==proof.get('callerWindowEndRva')
                         and a<=proof['callRva']<proof['returnRva']<=b and hashlib.sha256(raw).hexdigest()==proof.get('callerWindowSha256')]
                require(len(matches)==1,'caller source-family containing window differs')
                start,_,raw=matches[0]
                require(raw[proof['callRva']-start:proof['returnRva']-start].hex()==encoded,'caller source-family exact E8 slice differs')
            returns.append(proof['returnRva'])
        require(families is None or used_families==set(range(len(families))),'caller source-family unused/extra caller')
        require(returns==sorted(set(returns)) and scope==','.join(f'{r:x}' for r in returns),
                'caller scope list/proof differs')
        activation+=f"caller={index}|{scope}\n"
    activation_name = "private/mission-trace.activation"
    require(activation_name in artifacts and bound_bytes(artifacts, activation_name, 128 * 1024) == activation.encode("ascii"),
            "activation/profile binding mismatch")
    config_name = "private/runtime.conf"
    require(config_name in artifacts, "runtime config is not collection-bound")
    config = {}
    for line in bound_bytes(artifacts, config_name, 64 * 1024).decode("utf-8").splitlines():
        require("=" in line, "malformed runtime config")
        key, value = line.split("=", 1)
        require(key not in config, "duplicate runtime config key")
        config[key] = value
    require(config.get("schema") == "endfieldCapture.runtime.v1" and config.get("provider_mask") == ("130"if combined else"128"), "runtime provider binding mismatch")
    portable = lambda value: re.sub(r"/+", "/", value.replace("\\", "/")).rstrip("/").casefold()
    require("session_root" in config and portable(config.get("mission_activation_manifest", "")) ==
            portable(config["session_root"] + "/private/mission-trace.activation"), "runtime activation path binding mismatch")
    if combined:
        require(portable(config.get("activation_manifest",""))==portable(config["session_root"]+"/private/audio-activation.json"),
                "runtime Audio activation path binding mismatch")
    if "session_name" in config:
        require(config["session_name"] == session.get("sessionId"), "runtime session name mismatch")
    if "session_id" in config:
        require(config["session_id"] == str(session.get("numericSessionId")), "runtime numeric session ID mismatch")
    dll = artifacts.get("private/EndfieldCapture.dll")
    if dll and "runtimeSha256" in session:
        require(session["runtimeSha256"] == dll["sha256"] and session.get("runtimeBytes") == dll["bytes"], "staged runtime identity mismatch")
    return profile, summary, hooks


def scalar_type_record(witness, name, *, byref):
    raw = witness.get('nativeTypeRecordHex')
    if not isinstance(raw, str) or re.fullmatch('[0-9a-fA-F]{32}', raw) is None:
        return False
    record = bytes.fromhex(raw)
    return name in {'bool','float','double'} and record[10] == {'bool': 2, 'float': 12, 'double': 13}[name] and record[11] & 0x7f == (0x20 if byref else 0)


PRIMITIVES = {"bool": (8, False), "byte": (8, False), "sbyte": (8, True), "short": (16, True),
              "ushort": (16, False), "int": (32, True), "uint": (32, False), "long": (64, True), "ulong": (64, False)}


def decode_bounded_field(field,observed):
    kind=field['kind'];state=integer(observed.get('state'),'bounded field state',5)
    require(state>0 and (state!=5 or kind==8),'invalid bounded field state')
    raw=integer(observed.get('value'),'bounded source address');count=integer(observed.get('byteCount'),'bounded byte count',256)
    text=observed.get('rawHex')
    require(isinstance(text,str)and re.fullmatch('[0-9a-f]*',text)is not None and len(text)==count*2,'bounded rawHex/full byteCount mismatch')
    result=dict(label=field['label'],type=field['type'],state=state,stateName={1:'exact',2:'unreadable',3:'truncated',4:'observedNull',5:'notApplicable'}[state],
        raw64=raw,byteCount=count,rawHex=text,value=None,fieldPath=field.get('fieldPath',[]),
        read={k:field[k]for k in ('arg','kind','offset','chain0','chain1')},interpretation='Opaque selected physical bytes; no value, ownership or playback inferred.')
    if kind==7:
        keys=('containerAddress','storageBefore','storageAfter','countBefore','countAfter','capacityBefore','capacityAfter','versionBefore','versionAfter','stride','failureCode')
        for k in keys:result[k]=integer(observed.get(k),'container '+k)
        require(result['containerAddress']==raw and result['failureCode']<=3,'invalid container address/failure code')
        if state==1:
            require(raw>0 and result['failureCode']==0 and result['stride']==field['elementStride']
                    and result['countBefore']==result['countAfter']<=field['maxCount']
                    and result['versionBefore']==result['versionAfter']<=0xffffffff
                    and result['storageBefore']==result['storageAfter']
                    and result['capacityBefore']==result['capacityAfter']>=result['countBefore']
                    and count==result['countBefore']*field['elementStride']
                    and (result['storageBefore']>0 or result['countBefore']==result['capacityBefore']==0),
                    'container is incomplete, changed or exceeds declared bounds')
        elif state==4:require(raw==0 and count==0 and all(result[k]==0 for k in keys),'null container carries bytes or invented header state')
        elif state==3:require(count==0 and result['failureCode']==2,'container bound failure carries an admitted prefix')
    else:
        require(observed.get('sourceAddress')==raw,'raw source address differs')
        if state==1:require(raw>0 and count==field['byteCount'],'raw full-span read incomplete')
        if state in {4,5}:require(raw==0 and count==0,'null/inactive span carries bytes')
        if state==4 and kind==6:require(field['chain0']!=4097 or field['offset']>0,'null raw byref pointer is not an absent carrier')
        require(state!=3,'raw spans cannot admit truncated prefixes')
    for k in ('argumentName','argumentRepresentation','argumentAbi','role','observation','readMode','parentFieldIndex','parentField','itemIndex','rawProof','containerProof','callbackRole'):
        if k in field:result[k]=field[k]
    if field.get('readMode')=='virtualCallbackPair'and state==1:
        target,method=struct.unpack('<QQ',bytes.fromhex(text))
        result['callbackPair']=dict(targetAddress=target,methodInfoAddress=method,observed=True,callbackEffectsProved=False)
    return result


def validate_bounded_relations(descriptors,observations):
    for n,(field,value)in enumerate(zip(descriptors,observations)):
        if field['kind']!=8:continue
        parent=observations[field['parentFieldIndex']]
        if parent['state']==4:
            require(value['state']==4,'dependent absent carrier differs from null parent')
            continue
        if parent['state']!=1:
            require(value['state']==2,'dependent read remains valid after failed parent')
            continue
        active=field['itemIndex']<parent['countBefore']
        require((value['state']==5)==(not active),'dependent inactive index state differs from actual captured count')
        if active and value['state']in{1,4}:
            slot=bytes.fromhex(parent['rawHex'])[field['itemIndex']*8:field['itemIndex']*8+8]
            address=int.from_bytes(slot,'little')
            require((value['state']==4 and address==0)or(value['state']==1 and address>0 and value['raw64']==address+field['offset']),
                    'dependent source does not match captured parent reference slot')


def decode_field(field: dict[str, Any], observed: dict[str, Any], enums: dict[str, Any]) -> dict[str, Any]:
    if field['kind']>=6:return decode_bounded_field(field,observed)
    state = integer(observed.get("state"), "field state", 4)
    require(state > 0, "uninitialized observed field")
    raw = integer(observed.get("value"), "raw field value")
    kind = field["kind"]
    if state == 1:
        require(kind != 2 or raw <= 0xFFFFFFFF, "memory u32 observation exceeds physical read width")
        require(kind != 5 or raw <= 0xFF, "memory u8 observation exceeds physical read width")
    decoded = {"label": field["label"], "type": field["type"], "state": state,
               "stateName": {1: "exact", 2: "unreadable", 3: "truncated", 4: "observedNull"}[state], "raw64": raw,
               "read": {key: field[key] for key in ("arg", "kind", "offset", "chain0", "chain1")},
               "fieldPath": field.get("fieldPath", [])}
    for key in ("storageType", "signed", "argumentName", "role", "observation", "argumentRepresentation", "argumentAbi", "valueRepresentation"):
        if key in field:
            decoded[key] = field[key]
    if state == 4:
        require(raw == 0 and "text" not in observed and (kind == 3 or field["chain0"] != 4097 or
                kind in (1, 2, 5) and field['offset'] > 0 and bool(field.get('fieldPath'))), "invalid observed null")
        decoded.update(value=None, interpretation="Observed null string or absent carrier; ownership remains unresolved.")
        return decoded
    if kind == 3:
        text = observed.get("text")
        require(isinstance(text, str), "string observation lacks bounded text")
        units = len(text.encode("utf-16-le", errors="surrogatepass")) // 2
        require(units <= 160, "string observation exceeds UTF16 bound")
        require(raw <= 1024 * 1024, "string length exceeds native sampler bound")
        if state == 1:
            require(units == raw, "exact string length mismatch")
        elif state == 3:
            require(raw > 160 and units == 160, "truncated string length mismatch")
        decoded.update(utf16Length=raw, text=text, value=text if state == 1 else None)
        return decoded
    require("text" not in observed and state != 3, "invalid scalar observation")
    if state == 2:
        decoded.update(value=None)
        return decoded
    name, bits = field["type"], field.get("valueBits")
    definition = enums.get(name)
    primitive = PRIMITIVES.get(name)
    if bits is None:
        decoded.update(value=None, interpretation="No retained scalar width; raw value only.")
        return decoded
    require(bits in (8, 16, 32, 64), "unsupported scalar width")
    masked = raw & ((1 << bits) - 1)
    decoded.update(valueBits=bits, maskedUnsigned=masked)
    if name in {"float", "double"}:
        register_input = (kind==4 and bits=={'float':32,'double':64}[name]
            and (field.get('argumentRepresentation') or {}).get('mode') == 'scalarRegister'
            and scalar_type_record((field.get('argumentRepresentation') or {}).get('nativeArgumentProof',{}),name,byref=False))
        if register_input or (kind, bits) == ((2, 32) if name == "float" else (1, 64)):
            value = struct.unpack("<f" if bits == 32 else "<d", masked.to_bytes(bits // 8, "little"))[0]
            decoded.update(value=value if math.isfinite(value) else None, floatBits=f"0x{masked:0{bits // 4}x}",
                           floatClass="finite" if math.isfinite(value) else ("nan" if math.isnan(value) else "infinity"))
            if register_input:
                proof=field['argumentRepresentation']['nativeArgumentProof']
                decoded['argumentCarrier']=dict(register=proof['register'],bits=bits,representation='positional XMM low bits; not GP register contents')
        else:
            decoded.update(value=None, interpretation="Unsupported float carrier; GP values are not XMM arguments.")
        return decoded
    if definition is not None:
        require(isinstance(definition, dict) and definition.get("valueBits") == bits and type(definition.get("signed")) is bool,
                "invalid retained enum definition")
        signed = definition["signed"]
    elif primitive is not None:
        require(primitive[0] == bits, "primitive width mismatch")
        signed = primitive[1]
    else:
        signed = field.get("signed") if type(field.get("signed")) is bool else None
    value = masked - (1 << bits) if signed and masked & (1 << (bits - 1)) else masked
    decoded.update(value=value, signed=signed)
    if field.get("valueRepresentation") == "referenceIdentity":
        require(bits == 64 and signed is False, "invalid reference identity width/signedness")
        decoded.update(rawPointer=masked, nullReference=masked == 0,
                       interpretation="Same-process managed reference identity only; no pointee fields, stable cross-session identity or ownership inferred.")
    elif name == "bool":
        decoded.update(value=bool(masked), canonicalBool=masked in (0, 1))
    elif definition is not None:
        members = definition.get("members")
        require(isinstance(members, list) and len(members) <= 1024, "enum member budget exceeded")
        require(all(isinstance(member, dict) and type(member.get("value")) is int and isinstance(member.get("name"), str)
                    and len(member["name"]) <= 256 for member in members), "invalid enum members")
        decoded["enumNames"] = [member["name"] for member in members if member["value"] == value]
        decoded["enumSource"] = "retained profile enumDefinitions"
    elif primitive is None:
        decoded["interpretation"] = "Retained width only; enum names or storage signedness may be unavailable."
    return decoded


def source_bindings(session: Path, artifacts: dict[str, dict[str, Any]], limits: Limits, join: bool) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    inventory_name = "static-sources/inventory.json"
    path = session / inventory_name
    result = {"inventoryCollectionBound": inventory_name in artifacts, "copiedEntriesVerified": 0,
              "questAssignmentsRequested": join, "questAssignments": 0,
              "nativeSourceValidationReproved": False, "gaps": []}
    assignments: dict[str, list[dict[str, Any]]] = {}
    if not path.exists():
        result["gaps"].append("No retained static source inventory; source joins remain unresolved.")
        return result, assignments
    inventory = (bound_object(artifacts, inventory_name, limits) if inventory_name in artifacts else
                 read_object(safe_path(session, inventory_name), limits.json_bytes))
    require(inventory.get("schema") == "endfield.mission-source-archive.v1", "unsupported static source inventory")
    if inventory_name not in artifacts:
        result["gaps"].append("Static source inventory is not collection-hashed; its declarations are advisory. Source bytes are checked against collection hashes independently.")
    rows = inventory.get("files")
    require(isinstance(rows, list) and len(rows) <= limits.artifacts, "static source row budget exceeded")
    seen = set()
    for row in rows:
        require(isinstance(row, dict), "invalid source inventory row")
        source_name = row.get("sourceRelativePath")
        safe_path(session, source_name, existing=False)
        require(source_name not in seen, "repeated source inventory path")
        seen.add(source_name)
        if row.get("copied") is not True:
            continue
        name = "static-sources/" + str(row.get("archivedRelativePath", ""))
        safe_path(session, name)
        require(name == "static-sources/files/" + source_name and name in artifacts,
                f"source file is not collection-bound: {source_name}")
        bound = artifacts[name]
        require(row.get("sha256") == bound["sha256"] and row.get("bytes") == bound["bytes"],
                f"source inventory binding mismatch: {source_name}")
        result["copiedEntriesVerified"] += 1
        if not join or not source_name.startswith("game/Json/MissionRuntimeAsset/") or source_name.endswith("_meta.json"):
            continue
        data = bound_object(artifacts, name, limits)
        mission_id, quests = data.get("missionId"), data.get("questDic")
        require(isinstance(mission_id, str) and 0 < len(mission_id) <= 160 and isinstance(quests, dict), "invalid archived mission definition")
        for quest_id, quest in quests.items():
            require(isinstance(quest_id, str) and 0 < len(quest_id) <= 160 and isinstance(quest, dict) and quest.get("questId") == quest_id,
                    "archived quest key/identity mismatch")
            require(result["questAssignments"] < limits.identifiers, "quest assignment budget exceeded")
            assignments.setdefault(quest_id, []).append({"missionId": mission_id, "source": name, "sourceSha256": bound["sha256"],
                                                        "boundary": "explicit archived questDic membership; structuralOnly"})
            result["questAssignments"] += 1
    return result, assignments


def strict_receipt_consistent(receipt: Any, hooks: int) -> bool:
    if not isinstance(receipt, dict):
        return False
    return (all(type(receipt.get(key)) is int and receipt[key] == 0 for key in
                ("status", "failureStage", "rollbackFailureStage", "cleanupFailureStage", "windowsError", "rollbackWindowsError", "cleanupWindowsError",
                 "threadId", "rollbackThreadId", "cleanupThreadId"))
            and receipt.get("hookIndex") == receipt.get("rollbackHookIndex") == (1 << 32) - 1
            and receipt.get("rollbackAttempted") is False and receipt.get("cleanupSucceeded") is True
            and receipt.get("rollbackSucceeded") is True
            and receipt.get("pendingRecovery") is False
            and type(receipt.get("threadsSuspended")) is int and receipt["threadsSuspended"] >= 0
            and receipt.get("threadsResumed") == receipt.get("threadsEnumerated") == receipt["threadsSuspended"]
            and type(receipt.get("contextsChanged")) is int and 0 <= receipt["contextsChanged"] <= receipt["threadsSuspended"]
            and receipt.get("patchesChanged") == hooks)


def strict_preparation_retry_consistent(receipt: Any) -> bool:
    """Only a fully cleaned OpenThread/87 refusal before any suspension is retryable."""
    if not isinstance(receipt, dict):
        return False
    expected = {"status": 13, "failureStage": 3, "windowsError": 87,
                "hookIndex": (1 << 32) - 1, "rollbackHookIndex": (1 << 32) - 1}
    expected.update(dict.fromkeys(("rollbackFailureStage", "rollbackThreadId", "rollbackWindowsError",
                                  "cleanupFailureStage", "cleanupThreadId", "cleanupWindowsError",
                                  "threadsSuspended", "threadsResumed", "contextsChanged", "patchesChanged"), 0))
    return (all(type(receipt.get(key)) is int and receipt[key] == value for key, value in expected.items())
            and all(type(receipt.get(key)) is int and 0 < receipt[key] <= (1 << 32) - 1
                    for key in ("threadId", "threadsEnumerated"))
            and receipt.get("rollbackAttempted") is False and receipt.get("rollbackSucceeded") is True
            and receipt.get("cleanupSucceeded") is True and receipt.get("pendingRecovery") is False)


def strict_enable_history_consistent(summary: dict[str, Any], hooks: int) -> bool:
    if summary.get("schema") == "endfieldCapture.missionTraceSummary.v1":
        return "strictEnableHistory" not in summary and "strictEnableAttempts" not in summary
    attempts, history, final = summary.get("strictEnableAttempts"), summary.get("strictEnableHistory"), summary.get("strictEnable")
    return (type(attempts) is int and 1 <= attempts <= 3 and isinstance(history, list) and len(history) == attempts
            and all(strict_preparation_retry_consistent(receipt) for receipt in history[:-1])
            and isinstance(final, dict) and isinstance(history[-1], dict) and history[-1] == final
            and all(type(history[-1][key]) is type(final[key]) for key in final)
            and strict_receipt_consistent(history[-1], hooks))


def inspect_session(session: Path, output_dir: Path, *, join_sources: bool = False,
                    local_files: bool = False, limits: Limits = Limits()) -> dict[str, Any]:
    session, output_dir = Path(session).resolve(strict=True), Path(output_dir).resolve()
    require(session.is_dir(), "session is not a directory")
    require(any(output_dir.is_relative_to((REPO_ROOT / folder).resolve()) for folder in ("reports", "scratch", "tmp")),
            "output must be under ignored reports/, scratch/, or tmp/")
    require(not output_dir.is_relative_to(session) and not session.is_relative_to(output_dir), "output must be outside original package")
    require(not output_dir.exists() or (output_dir.is_dir() and not any(output_dir.iterdir())), "output directory must be new or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"schema": "endfield.mission-trace-analysis.v1" if local_files else "endfield.mission-trace-inspection.v1", "status": "failed", "session": str(session),
                             "budgets": asdict(limits), "nativeValidationReproved": False, "strictTransitionsReexecuted": False,
                             "boundary": "Entry observations and explicit retained metadata only; no success/return, causal ownership, file execution order, or server criteria inferred.",
                             "gaps": [], "decodedRows": 0}
    partial = output_dir / "decoded.events.partial.jsonl"
    report_name = "analysis.json" if local_files else "inspection.json"
    if local_files:
        report["legacyCaptureAdmission"] = False
        report["boundary"] = "Offline consistency of current raw files, declared fields and explicit synchronous pairs; no producer hash authentication, server policy or omitted-source ownership."
    try:
        artifacts, report["inventory"] = (snapshot_local_inventory if local_files else verify_inventory)(session, limits)
        retained_session = bound_object(artifacts, "session.json", limits)
        require(retained_session.get("sessionId") == report["inventory"]["sessionId"], "collection/session identity mismatch")
        profile, summary, hooks = bindings(artifacts, limits)
        retained_profile=bound_object(artifacts,"private/mission-trace-build-manifest.json",limits)
        combined=retained_profile.get('schema')=='audioRuntimeTrace.hooks.v2'
        require(not combined or local_files,"combined capture requires current local-files inventory mode")
        if summary.get('schema') in {'endfieldCapture.missionTraceSummary.v3','endfieldCapture.missionTraceSummary.v4','endfieldCapture.missionTraceSummary.v5'} and not local_files:
            report['schema'] = 'endfield.mission-trace-inspection.v2'
        report["profileSha256"] = artifacts["private/mission-trace-build-manifest.json"]["sha256"]
        report["providerSummarySha256"] = artifacts["mission-trace/summary.json"]["sha256"]
        report["sources"], assignments = (local_source_bindings(artifacts, limits, join_sources) if local_files
                                          else source_bindings(session, artifacts, limits, join_sources))
        coverage_gaps = profile.get("coverageGaps", [])
        require(isinstance(coverage_gaps, list) and len(coverage_gaps) <= 256 and
                all(isinstance(gap, str) and len(gap) <= 2048 for gap in coverage_gaps), "invalid retained profile coverage gaps")
        report["retainedProfileCoverageGaps"] = coverage_gaps
        enums = profile.get("enumDefinitions", {})
        require(isinstance(enums, dict) and len(enums) <= 256, "enum definition budget exceeded")
        report["gaps"].extend(report["sources"]["gaps"])
        missing_enums = sorted({field["type"] for hook in hooks for field in hook["fields"]
                                if field.get("valueRepresentation") != "referenceIdentity" and field["type"] not in PRIMITIVES and field["type"] not in ("string", "float") and field["type"] not in enums})
        if missing_enums:
            report["gaps"].append("No retained enum definition for: " + ", ".join(missing_enums))
        enable_history = strict_enable_history_consistent(summary, len(hooks))
        strict = enable_history and all(strict_receipt_consistent(summary.get(key), len(hooks)) for key in ("strictEnable", "strictDisable"))
        failure_markers = [name for name in ("runtime.error", "mission-trace/aborted.json", "mission-trace/strict-fatal.txt")
                           if name in artifacts and artifacts[name]["bytes"] > 0]
        report["receiptFacts"] = {"captureCompleteClaim": summary.get("complete"), "healthyClaim": summary.get("healthy"),
                                  "failureReason": summary.get("failureReason"), "nativeInputHashesBoundToProfile": True,
                                  "collectionBoundFailureMarkers": failure_markers,
                                  "strictEnableAttempts": summary.get("strictEnableAttempts"),
                                  "strictEnableHistoryConsistent": enable_history,
                                  "strictTransitionReceiptsConsistent": strict, "strictReceiptProofBoundary": "Retained report consistency only; native transactions are not re-executed or independently observed."}
        journal_name = "mission-trace/events.jsonl"
        require(journal_name in artifacts and artifacts[journal_name]["bytes"] <= limits.journal_bytes, "missing or oversized journal")
        frequency = integer(summary.get("qpcFrequency"), "QPC frequency")
        require(frequency > 0, "zero QPC frequency")
        start_qpc, end_qpc = integer(summary.get("startQpc"), "startQpc"), integer(summary.get("statusQpc"), "statusQpc")
        start_tick, end_tick = integer(summary.get("startTickNs"), "startTickNs"), integer(summary.get("statusTickNs"), "statusTickNs")
        require(end_qpc >= start_qpc and end_tick >= start_tick, "invalid receipt clock bracket")
        base, image_size = integer(summary.get("moduleBase"), "moduleBase"), integer(summary.get("moduleImageSize"), "moduleImageSize", 1 << 32)
        calls, states, threads, sequences = Counter(), Counter(), Counter(), set()
        invocations = Invocations()
        paired_profile = summary.get('returnValuesObserved')is True and summary.get('schema')in{'endfieldCapture.missionTraceSummary.v3','endfieldCapture.missionTraceSummary.v4','endfieldCapture.missionTraceSummary.v5'}
        identifiers: dict[str, Counter[str]] = {"missionId": Counter(), "questId": Counter(), "parentQuestId": Counter()}
        byte_count, input_bytes, qpc_decreases, previous_qpc = 0, 0, 0, None
        journal_digest = hashlib.sha256()
        first_qpc, last_qpc = None, None
        with artifacts[journal_name]["path"].open("rb") as source, partial.open("xb") as destination:
            while line := source.readline(limits.input_line_bytes + 1):
                input_bytes += len(line)
                require(input_bytes <= limits.journal_bytes, "journal byte budget exceeded while decoding")
                journal_digest.update(line)
                require(len(line) <= limits.input_line_bytes and line.endswith(b"\n"), "journal line is oversized or unterminated")
                require(report["decodedRows"] < limits.rows, "journal row budget exceeded")
                row = parse_json(line, "journal row")
                require(isinstance(row, dict) and row.get("schema") == ('endfieldCapture.missionTraceEntry.v3'if summary.get('schema')in{'endfieldCapture.missionTraceSummary.v4','endfieldCapture.missionTraceSummary.v5'}else'endfieldCapture.missionTraceEntry.v2' if paired_profile
                        else 'endfieldCapture.missionTraceEntry.v1'), "unsupported event schema")
                index = integer(row.get("hookIndex"), "hook index", len(hooks) - 1)
                hook = hooks[index]
                report["failedEvent"] = {"journal": journal_name, "row": report["decodedRows"] + 1, "hook": hook["name"],
                                         "hookIndex": index}
                require(row.get("hook") == hook["name"], "event hook binding mismatch")
                sequence = integer(row.get("sequence"), "event sequence")
                require(sequence > 0 and sequence not in sequences, "duplicate or zero event sequence")
                sequences.add(sequence)
                qpc, tick = integer(row.get("qpc"), "event QPC"), integer(row.get("tickNs"), "event tickNs")
                require(start_qpc <= qpc <= end_qpc and start_tick <= tick <= end_tick, "event outside receipt clock bracket")
                thread = integer(row.get("threadId"), "event thread", (1 << 32) - 1)
                require(thread > 0, "zero event thread")
                args = row.get("args")
                require(isinstance(args, list) and len(args) == 8, "invalid event raw arguments")
                for value in args:
                    integer(value, "raw argument")
                mask = integer(row.get("argsReadMask"), "argument read mask", 255)
                typed_abi = PAIRED_ABI.fullmatch(hook.get('abiId', ''))
                if typed_abi:
                    expected_mask = (1 << int(typed_abi[2])) - 1
                    legacy_masks = (15, 255) if profile.get('recipeSchema') in {
                        'endfield.mission-trace-capture-recipe.v8', 'endfield.mission-trace-capture-recipe.v9'} else ()
                    require(mask == expected_mask or mask in legacy_masks,
                            f"paired argument read mask differs: hook={hook['name']}, expected={expected_mask}, actual={mask}")
                else:
                    require(mask in (15, 255), "unsupported argument read mask")
                return_address = integer(row.get("returnAddress"), "return address")
                expected_caller = return_address - base if base <= return_address < base + image_size else 0
                if hook.get('captureCallerReturnRvas'):
                    require(expected_caller in {p['returnRva'] for p in hook['captureCallerProofs']},
                        f"event outside declared caller scope: hook={hook['name']}, actualCallerRva={expected_caller}")
                require(row.get("callerGameAssemblyRva") == expected_caller, "caller address/RVA mismatch")
                fields = row.get("fields")
                paired_return = invocations.observe(row, hook) if paired_profile else None
                require(isinstance(fields, list) and len(fields) == (0 if row.get('phase') == 'unwind' else len(hook["fields"])), "event field count mismatch")
                decoded_fields = []
                for descriptor, observed in zip(hook["fields"], fields):
                    require(isinstance(observed, dict), "invalid observed field")
                    require(mask & (1 << descriptor["arg"]) or observed.get("state") == 2, "field uses unreadable argument")
                    if descriptor["kind"] == 4 and observed.get("state") == 1:
                        require(observed.get("value") == args[descriptor["arg"]], "scalar field/raw argument mismatch")
                    if descriptor["kind"] == 3 and descriptor["chain0"] == 4097 and observed.get("state") == 4:
                        require(args[descriptor["arg"]] == 0, "direct string null/raw argument mismatch")
                    if descriptor['kind']in{6,7}and descriptor['chain0']==4097 and observed.get('state')==1:
                        require(observed.get('value')==args[descriptor['arg']]+descriptor['offset'],'bounded direct source/raw argument mismatch')
                    value = decode_field(descriptor, observed, enums)
                    decoded_fields.append(value)
                    states[value["stateName"]] += 1
                    label = descriptor["label"].split(".")[-1]
                    if label in identifiers and value["state"] == 1 and descriptor["kind"] == 3 and value["value"]:
                        identities = identifiers[label]
                        if value["value"] not in identities:
                            require(sum(len(items) for items in identifiers.values()) < limits.identifiers, "observed identifier budget exceeded")
                        identities[value["value"]] += 1
                validate_bounded_relations(hook['fields']if row.get('phase')!='unwind'else[],decoded_fields)
                decoded = {"schema": "endfield.mission-trace-decoded-entry.v3"if summary.get('schema')in{'endfieldCapture.missionTraceSummary.v4','endfieldCapture.missionTraceSummary.v5'}else"endfield.mission-trace-decoded-entry.v2" if paired_profile else "endfield.mission-trace-decoded-entry.v1", "sequence": sequence, "qpc": qpc, "tickNs": tick,
                           "qpcOffset": qpc - start_qpc, "qpcFrequency": frequency, "secondsFromStart": (qpc - start_qpc) / frequency,
                           "threadId": thread, "hookIndex": index, "hook": hook["name"], "returnAddress": return_address,
                           "callerGameAssemblyRva": expected_caller, "argsReadMask": mask, "rawArgs": args, "fields": decoded_fields}
                if paired_profile:
                    decoded.update({k: row[k] for k in ('invocationId','parentInvocationId','depth','phase','returnValue')})
                    if paired_return is not None:
                        decoded['invocationReceipt'] = paired_return
                receiver = hook.get("receiverIdentity")
                if isinstance(receiver, dict):
                    argument = integer(receiver.get("arg"), "receiver argument", 7)
                    expected_argument = 1 if "anonymousEntryProof" in hooks[index] else 0
                    require(argument == expected_argument and isinstance(receiver.get("type"), str) and len(receiver["type"]) <= 256, "unsupported receiver identity carrier")
                    decoded["receiverIdentity"] = {"rawPointer": args[argument], "type": receiver["type"],
                                                    "boundary": "Observed entry pointer only; object lifetime and causal ownership unresolved."}
                payload = (json.dumps(decoded, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")
                byte_count += len(payload)
                require(len(payload) <= limits.output_line_bytes and byte_count <= limits.output_bytes, "decoded output byte budget exceeded")
                destination.write(payload)
                report["decodedRows"] += 1
                calls[index] += 1
                threads[thread] += 1
                qpc_decreases += int(previous_qpc is not None and qpc < previous_qpc)
                previous_qpc = qpc
                first_qpc = qpc if first_qpc is None else min(first_qpc, qpc)
                last_qpc = qpc if last_qpc is None else max(last_qpc, qpc)
                report.pop("failedEvent", None)
        require(input_bytes == artifacts[journal_name]["bytes"] and journal_digest.hexdigest() == artifacts[journal_name]["sha256"],
                "journal changed before or during decoding")
        require(report["decodedRows"] == integer(summary.get("written"), "written rows") and
                artifacts[journal_name]["bytes"] == integer(summary.get("bytesWritten"), "written bytes"), "journal/summary row or byte count mismatch")
        if paired_profile:
            report['invocations'] = invocations.finish(summary.get('complete') is True)
            if summary.get('complete') is True:
                require(summary.get('pairingFailures') == 0, 'complete receipt has invocation failures')
        accounted = all(summary.get(key) == 0 for key in ("dropped", "unrecorded", "undrainedRecordsAtStop")) and summary.get("finalCountersStable") is True
        for name, state in (("unreadableFields", "unreadable"), ("truncatedFields", "truncated"), ("nullFields", "observedNull")):
            count = integer(summary.get(name), name)
            require((states[state] == count) if accounted else (states[state] <= count or summary.get("finalCountersStable") is not True), f"journal/summary field counter mismatch: {name}")
        attempted, admitted, dropped = (integer(summary.get(key), key) for key in ("attempted", "admitted", "dropped"))
        if summary.get("finalCountersStable") is True:
            require(attempted == admitted + dropped and sum(item["calls"] for item in summary["hooks"]) == attempted, "provider attempted/admitted/hook accounting mismatch")
        require(not sequences or max(sequences) <= attempted, "event sequence exceeds attempted callbacks")
        report["hookCoverage"] = []
        lanes: dict[str, dict[str, Any]] = {}
        for index, hook in enumerate(hooks):
            declared = summary["hooks"][index]["calls"]
            require(calls[index] == declared if accounted else calls[index] <= declared or summary.get("finalCountersStable") is not True, "journal/summary hook calls mismatch")
            lane = hook.get("lane", hook["name"].split(".", 1)[0])
            require(isinstance(lane, str) and len(lane) <= 127, "invalid hook lane")
            coverage = {"index": index, "hook": hook["name"], "lane": lane, "laneSource": "retained profile" if "lane" in hook else "hook-name prefix grouping",
                        "observedRows": calls[index], "receiptCalls": declared, "status": "observed" if calls[index] else "unhit"}
            report["hookCoverage"].append(coverage)
            lane_row = lanes.setdefault(lane, {"hooks": 0, "observedHooks": 0, "rows": 0})
            lane_row["hooks"] += 1
            lane_row["observedHooks"] += int(calls[index] > 0)
            lane_row["rows"] += calls[index]
        contiguous = not sequences or (min(sequences) == 1 and max(sequences) == len(sequences))
        if accounted:
            require(contiguous and attempted == report["decodedRows"] == admitted, "lossless receipt sequence/accounting mismatch")
        if summary.get("complete") is True:
            require(accounted and strict and summary.get("healthy") is True and summary.get("writeComplete") is True and
                    all(summary.get(key) is True for key in ("installed", "hooksEverEnabled", "stopped", "quiescent")) and
                    summary.get("disabledTrampolinesRetainedUntilProcessExit") is True and summary.get("missionFiltered") is False and not failure_markers and
                    all(summary.get(key) is False for key in ("budgetExhausted", "durationBudgetExhausted", "strictPendingRecovery")) and
                    summary.get('returnValuesObserved') is paired_profile and summary.get('entryOnly') is (not paired_profile)
                    and summary.get("failureReason") == "none" and summary.get("firstFailure") is None and
                    summary.get("activeCallbacksAtStop") == 0 and summary.get("strictRecoveryAttempts") == 0 and summary.get("strictRecovery") is None and
                    integer(summary.get("startUtcFileTime100ns"), "UTC session anchor") > 0 and
                    states["unreadable"] == states["truncated"] == 0,
                    "complete provider receipt contradicts retained observations")
            if report["decodedRows"] == 0:
                report['failedGate']={
                    'validator':'mission_trace_inspect','check':'no_selected_hook_observations',
                    'expected':{'selectedHookObservations':'>0'},'actual':{'selectedHookObservations':0},
                    'sourceInputs':{name:{'path':str(artifacts[name]['path']),'bytes':artifacts[name]['bytes'],'sha256':artifacts[name]['sha256']}
                        for name in ('mission-trace/events.jsonl','mission-trace/summary.json')},
                    'hookCoverage':report['hookCoverage'][:96],
                    'runtimeInvocationObserved':False,'playbackProved':False,
                    'boundary':'Selected hooks were not observed. A loss-free complete transport does not establish scenario coverage.'}
                gate=report['failedGate']
                raise InspectionError('mission_trace_inspect.no_selected_hook_observations: expected >0 selected hook observations; actual 0; '
                    +'; '.join(name+'='+value['path']+' sha256='+value['sha256']for name,value in gate['sourceInputs'].items()))
        report.update(status="inspected", decodedBytes=byte_count, fieldStates=dict(states), lanes=lanes,
                      clocks={"qpcFrequency": frequency, "startQpc": start_qpc, "endQpc": end_qpc, "firstEventQpc": first_qpc,
                              "lastEventQpc": last_qpc, "journalQpcDecreases": qpc_decreases, "sequenceContiguous": contiguous,
                              "startTickNs": start_tick, "endTickNs": end_tick,
                              "startUtcFileTime100ns": summary.get("startUtcFileTime100ns"),
                              "boundary": "Preserved per-entry clocks and sequence; cross-thread chronology is not a causal join."},
                      threads=[{"threadId": key, "rows": value} for key, value in sorted(threads.items())],
                      observedIdentifiers={key: [{"id": identity, "rows": count,
                                                  **({"archivedMissionAssignments": assignments.get(identity, [])} if key in ("questId", "parentQuestId") and join_sources else {})}
                                                 for identity, count in sorted(values.items())] for key, values in identifiers.items()})
        report["receiptFacts"]["allJournalRowsAccounted"] = accounted
        if combined:
            from scripts.game_data.mission_trace_audio_links import inspect_links,package_exit
            report['audioLinks']=inspect_links(artifacts,retained_profile,summary,hooks,retained_session,limits)
            package_exit(artifacts,session,report['inventory']['inventorySha256'],limits)
            report['audioLinks']['originalPackageEntryExitMatched']=True
        partial.rename(output_dir / "decoded.events.jsonl")
    except (InspectionError, InvocationError, OSError, UnicodeError, RecursionError, KeyError, TypeError, AttributeError) as exc:
        report["status"] = "failed"
        report["failure"] = str(exc)[:2048]
        report["decodedOutput"] = "decoded.events.partial.jsonl" if partial.exists() else None
        with (output_dir / report_name).open("x", encoding="ascii") as target:
            target.write(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n")
        raise InspectionError(report["failure"]) from exc
    report["decodedOutput"] = "decoded.events.jsonl"
    if local_files:
        report["status"] = "analyzed"
    with (output_dir / report_name).open("x", encoding="ascii") as target:
        target.write(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--join-sources", action="store_true", help="Add explicit assignments from verified archived MissionRuntimeAsset questDic rows.")
    parser.add_argument("--local-files", action="store_true", help="Analyze the current path/size collection and selected source-files context without legacy hash admission.")
    args = parser.parse_args(argv)
    try:
        report = inspect_session(args.session, args.output_dir, join_sources=args.join_sources, local_files=args.local_files)
    except (InspectionError, OSError) as exc:
        print(f"[mission_trace_inspect] failed: {exc}")
        return 1
    observed = sum(row["status"] == "observed" for row in report["hookCoverage"])
    verb = "locally analyzed" if args.local_files else "verified"
    print(f"[mission_trace_inspect] {verb} {report['inventory']['artifacts']} artifacts; decoded {report['decodedRows']} rows; "
          f"observed {observed}/{len(report['hookCoverage'])} hooks; native execution is not re-validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
