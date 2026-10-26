"""Read and authenticate bounded opaque native collision memory windows.

Pointer edges describe values copied from parent windows. They do not establish
allocation extents, object types, PhysX ownership or an atomic memory snapshot.
"""
from __future__ import annotations

import hashlib
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path
import struct

from scripts.common import sha256_file

MAGIC=b"EFCMEM01"
MAGICS={'endfield.native-memory-windows.v1':MAGIC,'endfield.native-memory-windows.v2':b'EFCMEM02','endfield.native-memory-windows.v3':b'EFCMEM03'}
HEADER=struct.Struct("<9Q4I")
LIMITS=((1,"node_limit"),(2,"time_limit"),(4,"session_budget"),(8,"queue_full"),(16,"depth_limit"))


class AddressCoverage:
    """Index address unions only; bytes from other calls are never borrowed."""
    def __init__(self, windows):
        by_call=defaultdict(list);all_ranges=[]
        for window in windows:
            start=int(window['address'],16);end=start+window['bytes']
            if not 65536<=start<end<=0x800000000000:
                raise ValueError('coverage window address/size bound')
            span=(start,end);by_call[window['call']].append(span);all_ranges.append(span)
        self.all=self._merge(all_ranges)
        self.calls={call:self._merge(spans) for call,spans in by_call.items()}

    @staticmethod
    def _merge(spans):
        merged=[]
        for start,end in sorted(spans):
            if merged and start<=merged[-1][1]:
                merged[-1]=(merged[-1][0],max(merged[-1][1],end))
            else:
                merged.append((start,end))
        return merged,[span[0] for span in merged]

    @staticmethod
    def _coverage(index,address,size):
        spans,starts=index;stop=address+size;cursor=address;gaps=[];covered=0
        i=max(0,bisect_right(starts,address)-1)
        for n in range(i,len(spans)):
            start,end=spans[n]
            if start>=stop:break
            low,high=max(start,address),min(end,stop)
            if high<=low:continue
            if cursor<low:gaps.append((cursor,low))
            covered+=high-low;cursor=high
        if cursor<stop:gaps.append((cursor,stop))
        return dict(coveredBytes=covered,complete=covered==size,gapCount=len(gaps),
                    missingRanges=[dict(address=f'{low:016x}',bytes=high-low) for low,high in gaps[:16]],
                    missingRangesLimited=len(gaps)>16)

    def span(self,address,size,call):
        if type(address) is not int or type(size) is not int or not 0<size<=64*1024*1024 or not 65536<=address<0x800000000000-size:
            raise ValueError('coverage requested address/size bound')
        return dict(address=f'{address:016x}',bytes=size,
                    sameCall=self._coverage(self.calls.get(call,([],[])),address,size),
                    anyCall=self._coverage(self.all,address,size),
                    boundary='address-range union only; disjoint callbacks/roles do not supply one typed or consistent byte snapshot')


def validate_policy(policy: dict):
    if policy.get("solverOwnerSpans") not in (None,dict(actorBytes=256,shapeBytes=256)):
        raise ValueError("collision-capture: unsafe solver owner span policy")
    ranges={"windowBytes":(8,4096),"pointerScanBytes":(8,4096),"maxDepth":(1,4),
            "maxNodes":(1,128),"maxMicroseconds":(100,5000),"maxTotalBytes":(4096,128*1024*1024),"maxTotalBlocks":(1,32768)}
    if (policy.get('detailSpanRoots',[]) not in ([],['geometryVertices','geometryIndices']) or policy.get('detailSpanRoots') and policy.get('format')!='endfield.native-memory-windows.v3' or any(type(policy.get(k)) is not int or not lo<=policy[k]<=hi for k,(lo,hi) in ranges.items()) or
            policy.get('reportRoots',[]) not in ([],['contactHeader','contactPair']) or
            policy.get('spanRoots',[]) != (['source','meshIds'] if policy.get('format')=='endfield.native-memory-windows.v3' else []) or
            policy["pointerScanBytes"]>policy["windowBytes"] or policy["pointerScanBytes"]%8 or
            policy.get("roots")!=["collider","sharedMesh"] or policy.get("regionPolicy")!="committed_private_or_mapped_nonexecutable" or
            policy.get("format") not in MAGICS):
        raise ValueError("collision-capture: unsafe native memory window policy")


def _require(condition, message):
    if not condition:
        raise ValueError("native memory: "+message)


def _pointer(value):
    _require(isinstance(value,str) and len(value)==16,"pointer width")
    raw=bytes.fromhex(value)
    _require(raw.hex()==value,"pointer encoding")
    return int.from_bytes(raw,"little")


def validate_archive(path: Path, receipt: dict, policy: dict, calls: dict, *, stage_contract=None, detail_contract=None) -> dict:
    validate_policy(policy)
    _require(receipt.get("schema")==policy['format'] and receipt.get("file")==path.name,"receipt schema/file")
    for key in ("blocks","bytes","admitted","dropped"):
        _require(type(receipt.get(key)) is int and receipt[key]>=0,"receipt scalar:"+key)
    _require(receipt["blocks"]==receipt["admitted"]<=policy["maxTotalBlocks"],"writer/producer block counts")
    _require(path.stat().st_size==receipt["bytes"]<=8+policy["maxTotalBytes"]+HEADER.size*policy["maxTotalBlocks"],"archive size bound")
    before=sha256_file(path)
    _require(before.lower()==receipt["sha256"].lower(),"archive hash differs")
    groups={};summaries=[];missing_roots=[]
    for call,entry in calls.items():
        row=entry["returnRecord"]
        if row['kind']>=48:
            _require(stage_contract is not None,'stage span policy missing')
        roles=[("collider","colliderMemory"),("contactPair" if row["kind"]==15 else "sharedMesh","meshMemory")]
        if "contactMemory" in row:roles.append(("contactHeader","contactMemory"))
        if row['kind']==49:
            roles=[('liveMeshCache','meshMemory'),('getterTriangle','contactMemory')]
        elif row['kind']==64:
            roles=[('solverConstraint','contactMemory')]
            if policy.get('solverOwnerSpans'):roles.extend((('solverActor','colliderMemory'),('solverShape','meshMemory')))
        if policy['format']=='endfield.native-memory-windows.v3':roles.extend((('source','sourceMemory'),('meshIds','meshIdsMemory')))
        if row['kind'] in (50,51) or 54<=row['kind']<=63 or row['kind']==65:
            roles=[('physicsContext' if row['kind'] in (50,51) else 'solverCache','sourceMemory')]
        if row['kind']==70:
            _require(detail_contract is not None and policy.get('detailSpanRoots')==['geometryVertices','geometryIndices'],'geometry array span policy missing')
            roles=[('geometryVertices','sourceMemory'),('geometryIndices','meshIdsMemory')]
        if row['kind']>=48:
            declared={key for _,key in roles}
            for key in {'colliderMemory','meshMemory','contactMemory','sourceMemory','meshIdsMemory'}-declared:
                _require(not _pointer(row[key]['root']) and all(type(v) is int and v==0 for k,v in row[key].items() if k!='root'),'undeclared stage summary:'+key)
        for role,key in roles:
            summary=row[key]
            root=_pointer(summary["root"])
            fields=("startQpc","endQpc","blocks","bytes","examined","rejected","unreadable","limits")
            _require(all(type(summary.get(k)) is int and summary[k]>=0 for k in fields),"summary scalar")
            if not root:
                _require(not any(summary[k] for k in fields),"missing root carries values")
                if row["kind"] in (10,13) and row["queryState"]==1 and (role=="collider" or _pointer(row["mesh"])):
                    missing_roots.append(dict(call=call,role=role))
                continue
            valid=(row["kind"] in (10,13) and row["queryState"]==1 and role in ("collider","sharedMesh") and (role!="sharedMesh" or _pointer(row["mesh"])>0) or
                   row['kind']==37 and role in ('source','meshIds') and root==_pointer(row['args'][0 if role=='source' else 2]) or
                   row["kind"]==14 and row["queryState"]==1 and role=="contactHeader" and root==_pointer(row["args"][1]) or
                   row["kind"]==15 and role=="contactPair" and root==_pointer(row["args"][0]) or
                   row["kind"]==15 and row["queryState"]==1 and role=="collider" and root==_pointer(row["args"][6]) or
                   row["kind"]==30 and row["queryState"]==1 and role=="collider" and root==int.from_bytes(bytes.fromhex(row["queryHex"])[56:64],'little') or
                   row['kind']==49 and row['queryState']==255 and root==_pointer(row['args'][3 if role=='liveMeshCache' else 2]) or
                   row['kind']==70 and role in ('geometryVertices','geometryIndices') and root==struct.unpack_from('<Q',bytes.fromhex(row['before']),16 if role=='geometryVertices' else 24)[0] or
                   row['kind']==64 and role in ('solverActor','solverShape') and row['queryState']==7 and root==struct.unpack_from('<Q',bytes.fromhex(row['queryHex']),24 if role=='solverActor' else 16)[0] or
                   row['kind']==64 and role=='solverConstraint' and root==int.from_bytes(bytes.fromhex(row['before'])[32:40],'little') or
                   role in ('physicsContext','solverCache') and root==_pointer(row['args'][0 if row['kind']==51 else 2]))
            _require(valid,"root lacks live collider/mesh sample or bounded report")
            _require(entry["qpc"]<=summary["startQpc"]<=summary["endQpc"]<=row["qpc"],"summary timestamp bound")
            _require(summary["blocks"]<=summary["examined"]<=policy["maxNodes"] and summary["bytes"]<=policy["windowBytes"]*summary["blocks"] and
                     summary["limits"]<=31 and summary["rejected"]+summary["unreadable"]+summary["blocks"]<=summary["examined"],"summary bounds")
            _require(summary["blocks"] or summary["limits"] or summary["rejected"] or summary["unreadable"],"empty traversal lacks diagnostic")
            _require((call,root) not in groups,"duplicate native root for one sample")
            group=dict(call=call,role=role,root=root,summary=summary,nodes={},bytes=0)
            if role in ('geometryVertices','geometryIndices'):
                size=_pointer(row['args'][6 if role=='geometryVertices' else 7])
                _require(0<size<=detail_contract['limits']['maxArraySpanBytes'] and summary['bytes']<=size,'geometry array span declared bound')
                group['spanBytes']=size
            elif role in ('source','meshIds'):
                count=_pointer(row['args'][1 if role=='source' else 3])
                maximum=65536 if role=='source' else 4096
                _require(0<count*4<=maximum and summary['bytes']<=count*4, 'span declared input bound')
                group['spanBytes']=count*4
            elif role in ('liveMeshCache','getterTriangle','solverConstraint'):
                size=stage_contract['layout']['meshCacheOffset']+8 if role=='liveMeshCache' else 256 if role=='getterTriangle' else min(struct.unpack_from('<H',bytes.fromhex(row['before']),30)[0]*16,stage_contract['limits']['maxConstraintBytes'])
                _require(size>0 and summary['bytes']<=size,'stage span declared bound')
                group['spanBytes']=size
            elif role in ('solverActor','solverShape'):
                size=policy['solverOwnerSpans']['actorBytes' if role=='solverActor' else 'shapeBytes']
                _require(summary['bytes']<=size,'solver owner span declared bound');group['spanBytes']=size
            elif role in ('physicsContext','solverCache'):
                size=stage_contract['limits']['maxContextBytes' if role=='physicsContext' else 'maxSolverCacheBytes']
                _require(summary['bytes']<=size,'stage context declared bound')
                group['spanBytes']=size
            groups[(call,root)]=group
            summaries.append(dict(call=call,role=role,nativeRoot=summary["root"],blocks=summary["blocks"],bytes=summary["bytes"],
                                  limits=[name for bit,name in LIMITS if summary["limits"]&bit],unreadable=summary["unreadable"],rejected=summary["rejected"]))
    windows=[];payload_bytes=0
    with path.open("rb") as handle:
        _require(handle.read(8)==MAGICS[policy['format']],"magic")
        for n in range(receipt["blocks"]):
            raw=handle.read(HEADER.size)
            _require(len(raw)==HEADER.size,"truncated block header")
            call,root,address,parent,offset,qpc,region,region_bytes,allocation,depth,size,protect,kind=HEADER.unpack(raw)
            _require((call,root) in groups,"orphan window")
            group=groups[(call,root)];summary=group["summary"];nodes=group["nodes"]
            _require(summary["startQpc"]<=qpc<=summary["endQpc"] and address not in nodes,"window timing/duplicate")
            exact_span='spanBytes' in group
            byte_buffer=exact_span or policy['format'] in ('endfield.native-memory-windows.v2','endfield.native-memory-windows.v3') and group['role'] in ('contactHeader','contactPair') and bool(parent)
            _require(65536<=address<=0x7fffffffffff and (address%8==0 or byte_buffer) and depth<=policy["maxDepth"] and
                     region<=address<region+region_bytes and (size<=min(policy["windowBytes"],region+region_bytes-address) if exact_span else size==min(policy["windowBytes"],region+region_bytes-address)) and
                     1<=size<=4096 and 0<allocation<=region and protect in (2,4,8) and kind in (0x20000,0x40000),"readable window bounds/protection")
            payload_offset=handle.tell();data=handle.read(size)
            _require(len(data)==size,"truncated payload")
            if not parent:
                _require(not nodes and address==root and offset==depth==0,"root framing")
            elif exact_span:
                _require(parent==root and depth==1 and address==root+offset and offset==group['bytes'], 'span offset/continuity')
            else:
                _require(parent in nodes,"missing parent window")
                ancestor=nodes[parent]
                _require(offset%8==0 and offset+8<=min(len(ancestor["data"]),policy["pointerScanBytes"]) and
                         int.from_bytes(ancestor["data"][offset:offset+8],"little")==address and
                         depth==ancestor["depth"]+1 and qpc>=ancestor["qpc"],"pointer edge differs from parent bytes")
            nodes[address]=dict(data=data,depth=depth,qpc=qpc)
            if exact_span:
                _require(size==min(4096,group['spanBytes']-group['bytes'],region+region_bytes-address), 'exact input chunk size')
            group["bytes"]+=size;payload_bytes+=size
            windows.append(dict(call=call,role=group["role"],root=f"{root:016x}",address=f"{address:016x}",parent=f"{parent:016x}",
                                parentOffset=offset,depth=depth,qpc=qpc,payloadOffset=payload_offset,bytes=size,sha256=hashlib.sha256(data).hexdigest(),
                                regionBase=f"{region:016x}",regionBytes=region_bytes,allocationBase=f"{allocation:016x}",protect=protect,memoryType=kind))
        _require(not handle.read(1),"trailing bytes")
    for group in groups.values():
        _require(len(group["nodes"])==group["summary"]["blocks"] and group["bytes"]==group["summary"]["bytes"],"sample block/byte counts differ")
    _require(receipt["dropped"]==sum(bool(g["summary"]["limits"]&8) for g in groups.values()),"queue loss differs from sample diagnostics")
    _require(payload_bytes<=policy["maxTotalBytes"] and sha256_file(path)==before,"payload bound/archive changed during inspection")
    return dict(schema="endfield.native-memory-inspection.v3" if policy['format']=='endfield.native-memory-windows.v3' else "endfield.native-memory-inspection.v2" if policy['format']=='endfield.native-memory-windows.v2' else "endfield.native-memory-inspection.v1",status="validated",file=path.name,sha256=before,blocks=len(windows),
                payloadBytes=payload_bytes,dropped=receipt["dropped"],samples=summaries,missingRoots=missing_roots,windows=windows,
                limitedSamples=sum(bool(s["limits"] or s["unreadable"] or s["rejected"]) for s in summaries),
                boundary=policy["boundary"])
