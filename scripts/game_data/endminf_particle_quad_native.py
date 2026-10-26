"""Authenticate selected quad stages and complete size/getter read families.

Evidence and admission boundary
-------------------------------
Exact authenticated windows extend the matrix loader to complete getter/unpack
families and selected non-freeform stages, without certifying live execution.
Public StartSize copies birth arrays; the renderer selects evaluated current
size under another flag. The selected non-freeform helper does not read rotation.
Conditional ordered replay with mathematical weighted curves matches head
corners but fails tails. Isolated Unity curve evaluation reduces that discrepancy
without proving the native curve evaluator or source simulation. In the retained
consolidated recording, observed active sizes, optional velocity multiplier,
flags, calibration and returned job parameters close all retained POSITION
words, including a unique same-Play first-frame native-output/GPU match.
Before/after equality is not atomicity; reciprocal-square-root replay remains
current-CPU conditioned. Other attributes and source curves/simulation remain
unresolved. Keep public-getter failures, capture stalls and missing closing
palettes; observed birth/age values are diagnostics, not renderer inputs, and
new movies inherit no older image scores.
"""
import hashlib
import json
from types import SimpleNamespace
from scripts.game_data import endminf_particle_matrix_native as matrix
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory

CONTRACT=CONTRACTS_DIR/'endminf_particle_quad_native.json'


def load(**selected_paths):
    c=json.loads(CONTRACT.read_bytes())
    if c.get('schema')!='endfield.endminf-particle-quad-native.v1' or c.get('status')!='reviewed':
        raise ValueError('particle-quad.contract: reviewed schema required')
    base,audit=matrix.load(**selected_paths)
    audit=dict(audit,validator='endminf-particle-quad',matrixContract=str(matrix.CONTRACT),contract=str(CONTRACT))
    if base is None:return None,audit
    if c['nativeInputs']!=base.contract['nativeInputs']:
        return None,dict(audit,status='mismatched',detail='quad and authenticated matrix selections differ')
    check='unwind-families'
    try:
        read=lambda r,n:base.pe.bytes_at_va(base.pe.image_base+r,n)
        table,size,raw=read_exception_directory(base.pe)
        index=UnwindChainIndex(raw,read,table_rva=table,image_size=size)
        windows=dict(base.windows)
        for f in c['functions']:
            check='function:'+f['role'];entry=f['entryRva']
            if (f['kind']!='unwindFamily' or index.resolve(entry)!=entry or
                [(a,b-a)for a,b,_ in index.families[entry]]!=[(w['rva'],w['bytes'])for w in f['ranges']]):
                raise ValueError(f'complete unwind family expected={str(f["ranges"])[:220]} actual={str(index.families.get(entry))[:220]}')
            chunks=[]
            for w in f['ranges']:
                if not 0<w['bytes']<=65536:raise ValueError('unbounded window')
                data=read(w['rva'],w['bytes'])
                actual=hashlib.sha256(data).hexdigest()
                if actual!=w['sha256']:raise ValueError(f'window={w["rva"]:#x} expected={w["sha256"]} actual={actual}')
                chunks.append((w['rva'],data))
            windows[f['role']]=chunks
        roles=set()
        for stage in c['stages']:
            check='stage:'+stage['role'];a,b=stage['beginRva'],stage['endRva']
            if stage['role']in roles or not 0<b-a<=4096 or not any(start<=a<b<=start+len(data)for chunks in windows.values()for start,data in chunks):
                raise ValueError('stage escapes authenticated windows or duplicates role')
            roles.add(stage['role'])
        constants={}
        for v in c['fileConstants']:
            check='constant:'+hex(v['instructionRva']);raw=read(v['rva'],v['bytes'])
            if raw.hex()!=v['hex']:raise ValueError(f'operand={v["rva"]:#x} expected={v["hex"]} actual={raw.hex()}')
            constants.update({v['rva']+i:b for i,b in enumerate(raw)})
        audit.update(status='validated',detail='complete size/getter families and bounded quad stages checked',
                     quadFunctionRoles=len(c['functions']),quadStages=len(roles))
        return SimpleNamespace(contract=c,matrix=base,pe=base.pe,windows=windows,constants=constants),audit
    except (ValueError,KeyError,IndexError)as error:
        return None,dict(audit,status='validation_failed',failedCheck=check,detail=str(error)[:700])
