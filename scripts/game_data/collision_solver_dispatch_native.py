"""Authenticate CPU solver selection, scene dispatch and island-work gates.

Evidence and admission boundary
-------------------------------
Exact selected unwind families and operands distinguish the named rigid-body
solver task from actual CPU dynamics. The CPU simulation-controller factory
installs an empty delegated task slot; the scene separately dispatches its held
dynamics context. Constructor solver-type selection chooses PGS or TGS factories.
Both CPU update bodies copy accurate-island active count and return before task
allocation on zero. Body, kinematic, articulation, contact-manager and constraint
counts are separate. Task names or a shared run-wrapper return address do not
identify an executed backend, branch or task generation; live operands need
original-call observations rather than later checkpoint counts.
"""
import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import load_layout, validate_layout
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots

CONTRACT = CONTRACTS_DIR / 'collision_solver_dispatch_native.json'
SCHEMA = 'endfield.collision-solver-dispatch-native.v2'
ARGUMENTS = (('pointer',)*2, *(('pointer',)*5+('u32','pointer','u32','u32','pointer','pointer','f32','pointer','u32'),)*2, ('pointer',))


def load(*, gameassembly, metadata, unityplayer):
    return load_layout(gameassembly=gameassembly, metadata=metadata, unityplayer=unityplayer,
                       contract_path=CONTRACT, schema=SCHEMA, validator='collision_solver_dispatch_native')


def validate_capture(pe, contract):
    validate_layout(pe, contract, schema=SCHEMA)
    windows={w['role']:w for w in contract['codeWindows']}
    hooks=contract['hooks'];pins=[];result=[]
    if tuple((h['kind'],h['windowRole']) for h in hooks)!=((66,'scene_update'),(67,'pgs_update'),(68,'tgs_update'),(69,'flush_thunk')):raise ValueError('dispatch hook order')
    for n,h in enumerate(hooks):
        if tuple(h['abi']['arguments'])!=ARGUMENTS[n] or h['abi']['returnMode']!=('pointer' if n==3 else 'void'):
            raise ValueError('dispatch compiled ABI:'+h['role'])
        w=windows[h['windowRole']];entry=bytes.fromhex(h['entryHex'])
        if not 5<=len(entry)<=32 or pe.bytes_at_va(pe.image_base+w['rva'],len(entry))!=entry:
            raise ValueError('dispatch hook entry:'+h['role'])
        result.append(dict(**h,module='unityPlayer',rva=w['rva'],expectedBytes=entry.hex()))
    for w in windows.values():pins.append(dict(module='unityPlayer',rva=w['rva'],expectedBytes=pe.bytes_at_va(pe.image_base+w['rva'],w['bytes']).hex()))
    slot=contract['flushImport']['selectedImports'][0]['slotRva']
    if resolve_named_import_slots(pe,[slot])!=contract['flushImport'] or contract['flushImport']['selectedImports'][0]['symbolName']!='InterlockedFlushSList':
        raise ValueError('dispatch flush import binding declaration')
    if tuple((s['backend'],s['kind'],s['windowRole']) for s in contract['decisionSites'])!=(('pgs',67,'pgs_update'),('tgs',68,'tgs_update')):
        raise ValueError('dispatch decision site order')
    for site in contract['decisionSites']:
        call=pe.bytes_at_va(pe.image_base+site['callRva'],5)
        if call[0]!=0xe8 or site['callRva']+5+struct.unpack_from('<i',call,1)[0]!=windows['flush_thunk']['rva']:
            raise ValueError('dispatch original decision callee:'+site['backend'])
        allocation=pe.bytes_at_va(pe.image_base+site['allocationRva'],7)
        if allocation!=b'\x48\x81\xec'+struct.pack('<I',site['allocationBytes']):raise ValueError('dispatch stack allocation:'+site['backend'])
        bias=0
        if site.get('framePointerLeaRva'):
            lea=pe.bytes_at_va(pe.image_base+site['framePointerLeaRva'],5)
            if lea.hex()!=site['framePointerLeaHex'] or lea[:4]!=b'\x48\x8d\x6c\x24':raise ValueError('dispatch frame pointer:'+site['backend'])
            bias=site['allocationBytes']+int.from_bytes(lea[4:],'little',signed=True)
        if bias!=site['framePointerFromStack'] or site['countFromReturnSlot']!=bias+site['storeDisplacement']+8 or not 8<=site['countFromReturnSlot']<=512:
            raise ValueError('dispatch original count return-slot derivation:'+site['backend'])
        store=bytes.fromhex(site['storePrefix'])+struct.pack('<I',site['storeDisplacement'])
        if pe.bytes_at_va(pe.image_base+site['storeRva'],len(store))!=store:raise ValueError('dispatch count store:'+site['backend'])
        branch=pe.bytes_at_va(pe.image_base+site['compareRva'],13)
        if branch.hex()!=site['branchHex'] or branch[7:9]!=b'\x0f\x84' or struct.unpack_from('<I',branch,3)[0]!=site['storeDisplacement'] or site['compareRva']+13+struct.unpack_from('<i',branch,9)[0]!=site['zeroReturnRva']:
            raise ValueError('dispatch original count compare/branch:'+site['backend'])
        if site['returnRva']!=site['callRva']+5 or site['poolOffset']!=contract['layout']['context'][site['backend']+'PoolOffset']:
            raise ValueError('dispatch original call/pool:'+site['backend'])
    limits=contract['limits'];bounds=dict(maxSceneUpdates=(1,4096),maxDynamicsUpdates=(1,8192),maxDecisions=(1,8192),sampleEvery=(1,128))
    if set(limits)!=set(bounds) or any(type(limits[k]) is not int or not lo<=limits[k]<=hi for k,(lo,hi) in bounds.items()):raise ValueError('dispatch sample bounds')
    return dict(contract=contract,hooks=result,pins=pins)


def load_capture(pe, native_inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,label='collision-dispatch',status='reviewed')
    if {k:v.lower() for k,v in native_inputs.items()}!=contract['nativeInputs']:raise ValueError('dispatch selected inputs differ')
    return validate_capture(pe,contract)
