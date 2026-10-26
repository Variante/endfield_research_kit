"""Authenticate bounded geometry/pose reads and task-generation observers."""
import hashlib
import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex

CONTRACT=CONTRACTS_DIR/'collision_geometry_state_native.json'
SCHEMA='endfield.collision-geometry-state-native.v1'
ABIS=(('pointer','f32','pointer','pointer','u32','bool'),('pointer','pointer'),('pointer',),('pointer',))

def validate(pe,c):
    def need(ok,detail):
        if not ok:raise ValueError('collision-geometry-state:'+detail)
    need(c['schema']==SCHEMA and c['status']=='reviewed','schema/status')
    table,size,raw=read_exception_directory(pe)
    chains=UnwindChainIndex(raw,lambda r,n:pe.bytes_at_va(pe.image_base+r,n),table_rva=table,image_size=size)
    windows={};pins=[]
    for w in c['codeWindows']:
        need(w['role'] not in windows and 1<=w['bytes']<=16384,'window identity/bound')
        data=pe.bytes_at_va(pe.image_base+w['rva'],w['bytes'])
        need(hashlib.sha256(data).hexdigest()==w['sha256'],'window hash:'+w['role'])
        if 'runtimeRanges' in w:
            actual=[r['runtimeTriple'] for r in chains.family(w['rva'])['ranges']]
            need(actual==w['runtimeRanges'] and min(a for a,b,u in actual)==w['rva'] and max(b for a,b,u in actual)==w['rva']+w['bytes'],'complete unwind family:'+w['role'])
        else:need(data.hex()==w['leafHex'] and (data[-1:]==b'\xc3' or w['role'] in ('update_task','task_manager_thunk')),'explicit leaf:'+w['role'])
        windows[w['role']]=(w,data);pins.append(dict(module='unityPlayer',rva=w['rva'],expectedBytes=data.hex()))
    checked=set()
    for f in c['fieldOperands']:
        raw=windows[f['role']][1];at=f['offset'];prefix=bytes.fromhex(f['prefix']);n=f['width'];group,name=f['field'].split('.')
        need(n in (1,4) and 0<=at<=len(raw)-len(prefix)-n and raw[at:at+len(prefix)]==prefix,'field instruction:'+f['field'])
        need(int.from_bytes(raw[at+len(prefix):at+len(prefix)+n],'little')==c['layout'][group][name],'field value:'+f['field']);checked.add(f['field'])
    need(checked=={g+'.'+n for g,v in c['layout'].items() for n in v},'layout operand coverage')
    for p in c['probes']:
        raw=windows[p['role']][1];data=bytes.fromhex(p['hex'])
        need(raw[p['offset']:p['offset']+len(data)]==data,'control/forwarding probe:'+p['role'])
    for s in c['vtableSlots']:
        need(pe.u64_at_va(pe.image_base+c['bindings'][s['table']]+s['slot']*8)==pe.image_base+windows[s['role']][0]['rva'],'concrete vtable:'+s['role'])
    release=windows['task_release'][0]['rva'];call=pe.bytes_at_va(pe.image_base+release+20,5)
    need(call[0]==0xe8 and release+25+struct.unpack_from('<i',call,1)[0]==windows['atomic_decrement'][0]['rva'],'original release atomic callee')
    hooks=[]
    need(tuple((h['kind'],h['windowRole']) for h in c['hooks'])==((72,'scene_simulate'),(73,'task_release'),(74,'atomic_decrement'),(75,'task_run')),'hook order')
    for i,h in enumerate(c['hooks']):
        need(tuple(h['abi']['arguments'])==ABIS[i] and h['abi']['returnMode']==('i32' if i==2 else 'void'),'compiled ABI:'+h['role'])
        w,data=windows[h['windowRole']];entry=bytes.fromhex(h['entryHex']);need(5<=len(entry)<=32 and data.startswith(entry),'hook entry:'+h['role'])
        hooks.append(dict(**h,module='unityPlayer',rva=w['rva'],expectedBytes=entry.hex()))
    r=c['representation'];need(r['transformBytes']==28 and r['nativeHitBytes']==56 and r['shapeBufferedPoseOffset']==0,'compiled scalar widths')
    need(r['atomicReturnRva']==release+25 and r['idleSimulationStage']==windows['scene_simulate_guard'][1][21] and
         r['acceptedSimulationStage']==int.from_bytes(windows['scene_simulate'][1][15:19],'little'),'original simulation/dispatch state')
    need(r['transformQuaternionOffset']==0 and r['transformPositionOffset']==16 and r['nativeHitFlagsCandidateOffset']==24 and r['nativeHitFlagsCandidateBytes']==2,'ABI candidate layout')
    bounds=dict(maxArrays=(1,256),maxArraySpanBytes=(4096,524288),maxArrayTotalBytes=(4096,16777216),maxPoses=(1,8192),maxSimulations=(1,4096),maxTaskRecords=(1,8192),maxSceneSlots=(1,64),maxTaskSlots=(1,512),sampleEvery=(1,128))
    need(set(bounds)==set(c['limits']) and all(type(c['limits'][k]) is int and lo<=c['limits'][k]<=hi for k,(lo,hi) in bounds.items()),'unsafe limits')
    return dict(contract=c,hooks=hooks,pins=pins)

def load(pe,native_inputs):
    c,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,label='collision-geometry-state',status='reviewed')
    if {k:v.lower() for k,v in native_inputs.items()}!=c['nativeInputs']:raise ValueError('collision-geometry-state:selected native inputs differ')
    return validate(pe,c)
