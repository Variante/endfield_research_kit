"""Authenticate original body-operation hooks and passive live body fields."""
import hashlib,json,struct
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory

CONTRACT=CONTRACTS_DIR/'collision_live_body_native.json'
SCHEMA='endfield.collision-live-body-native.v2'
ABIS=((86,('pointer','bool'),'void'),(87,('pointer','pointer','i32'),'void'),
      (88,('pointer',),'bool'),(89,('pointer',)*3,'void'))


def validate_windows(images,indexes,contract):
    windows={};pins=[]
    for w in contract['codeWindows']:
        pe=images[w['module']]
        if w['role'] in windows or not 1<=w['bytes']<=4096:
            raise ValueError('live-body window identity/bounds:'+w['role'])
        raw=pe.bytes_at_va(pe.image_base+w['rva'],w['bytes'])
        if hashlib.sha256(raw).hexdigest()!=w['sha256']:
            raise ValueError('live-body window hash:'+w['role'])
        windows[w['role']]=(w,raw);pins.append(dict(module=w['module'],rva=w['rva'],expectedBytes=raw.hex()))
    covered=set()
    for family in contract['codeFamilies']:
        actual=[r['runtimeTriple'] for r in indexes[family['module']].family(family['rva'])['ranges']]
        if actual!=family['runtimeRanges']:
            raise ValueError('live-body complete unwind family:'+family['role'])
        for n,(start,end,_) in enumerate(actual):
            role=family['role']+(f'_part_{n}' if n else '')
            window=windows.get(role)
            if (role in covered or window is None or window[0]['module']!=family['module'] or
                    (window[0]['rva'],window[0]['bytes'])!=(start,end-start)):
                raise ValueError('live-body family extent:'+role)
            covered.add(role)
    if set(windows)-covered!={'sleep_getter','sleep_forward'}:
        raise ValueError('live-body family/leaf coverage')
    for role,(window,raw) in windows.items():
        if role in covered:continue
        if raw.hex()!=window.get('leafHex'):
            raise ValueError('live-body explicit leaf:'+role)
        covered.add(role)
    return windows,pins


def load(image,player,native_inputs):
    c,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,label='collision-live-body',status='reviewed')
    if c['nativeInputs']!={k:v.lower() for k,v in native_inputs.items()}:
        raise ValueError('live-body selected native inputs differ')
    if tuple((f['role'],f['module']) for f in c['codeFamilies'])!=(
            ('set_kinematic','unityPlayer'),('add_force','unityPlayer'),
            ('sleeping','unityPlayer'),('destructible_break','gameAssembly')):
        raise ValueError('live-body function family identity/order')
    from scripts.game_data.collision_body_mode_native import CONTRACT as MODE,validate_route
    from scripts.game_data.collision_runtime_mesh_native import validate_layout
    mode=json.loads(MODE.read_text('utf-8'))
    if mode['nativeInputs']!=c['nativeInputs']:raise ValueError('live-body mode inputs differ')
    validate_layout(player,mode,schema=mode['schema']);validate_route(image,player,mode)
    images=dict(gameAssembly=image.pe,unityPlayer=player)
    indexes={}
    for name,pe in images.items():
        table,size,raw=read_exception_directory(pe)
        indexes[name]=UnwindChainIndex(raw,lambda a,n,p=pe:p.bytes_at_va(p.image_base+a,n),table_rva=table,image_size=size)
    windows,pins=validate_windows(images,indexes,c)
    md=image.metadata;t=next(t for t in md.types if md.type_full_name(t)=='UnityEngine.Object')
    offsets=runtime_type_field_offsets(md,image.pe,image.registration,t.index)
    managed=c['layout']['managed'];rigid=c['layout']['rigidbody']
    if offsets['m_CachedPtr']!=managed['cachedPtr'] or rigid['actor']!=mode['layout']['mode']['actorOffset'] or rigid['cachedKinematic']!=mode['layout']['mode']['cachedOffset']:
        raise ValueError('live-body managed/component coordinates')
    identity=c['instanceIdConsumer'];image.validate_method_row([identity['index'],identity['type'],identity['method'],identity['rva']],label='live-body-identity')
    raw=image.pe.bytes_at_va(image.pe.image_base+identity['rva'],identity['bodyBytes'])
    if hashlib.sha256(raw).hexdigest()!=identity['bodySha256']:raise ValueError('live-body InstanceID consumer')
    if (raw[20:23]!=bytes.fromhex('488b05') or identity['rva']+27+struct.unpack_from('<i',raw,23)[0]!=managed['identityClassCellRva'] or
        raw[27:29]!=bytes.fromhex('83b8') or int.from_bytes(raw[29:33],'little')!=managed['classInitialized'] or
        raw[36:39]!=bytes.fromhex('488b88') or int.from_bytes(raw[39:43],'little')!=managed['classStatics'] or
        raw[68:71]!=bytes.fromhex('486301') or raw[71:74]!=bytes.fromhex('8b0418')):
        raise ValueError('live-body InstanceID offset consumer operands')
    getter=c['sleepGetter'];leaf=bytes.fromhex(getter['leafHex'])
    expected=b'\x83\xb9'+int(c['layout']['actor']['sleepState']).to_bytes(4,'little')+b'\0\x0f\x95\xc0\xc3'
    if leaf!=expected or player.bytes_at_va(player.image_base+getter['rva'],len(leaf))!=leaf or player.u64_at_va(player.image_base+getter['vtableRva']+getter['slot']*8)!=player.image_base+getter['rva']:
        raise ValueError('live-body original sleeping getter')
    forward=c['sleepForward'];w,raw=windows['sleep_forward'];wrapper=windows['sleeping']
    if (w['rva']!=forward['rva'] or raw[7:10]!=bytes.fromhex('488b41') or raw[10]!=rigid['actor'] or
            raw[11:17]!=bytes.fromhex('488bc8488b10') or raw[17:20]!=bytes.fromhex('48ffa2') or
            int.from_bytes(raw[20:24],'little')!=getter['slot']*8 or raw[24:]!=bytes.fromhex('c332c0ebfb')):
        raise ValueError('live-body registered sleeping virtual route')
    at=forward['wrapperCallOffset'];code=wrapper[1]
    if code[at]!=0xe8 or wrapper[0]['rva']+at+5+struct.unpack_from('<i',code,at+1)[0]!=w['rva']:
        raise ValueError('live-body registered sleeping callee')
    if c['kinematicMask']!=mode['layout']['mode']['mask']:raise ValueError('live-body compiled kinematic mask')
    registration=mode['layout']['registration']
    for b in c['bindings']:
        name=player.c_string_at_va(player.u64_at_va(player.image_base+registration['nameTableRva']+b['slot']*8))
        if name!=b['name'] or player.u64_at_va(player.image_base+registration['functionTableRva']+b['slot']*8)!=player.image_base+b['functionRva']:
            raise ValueError('live-body compiled registration:'+b['role'])
        image.validate_method_row(b['managedMethod'],label='live-body')
        raw=image.pe.bytes_at_va(image.pe.image_base+b['cacheLoadRva'],7)
        if raw.hex()!=b['cacheLoadHex'] or raw[:3]!=bytes.fromhex('488b05') or b['cacheLoadRva']+7+struct.unpack_from('<i',raw,3)[0]!=b['cacheCellRva']:
            raise ValueError('live-body cached binding:'+b['role'])
    hooks=[]
    if tuple((h['kind'],tuple(h['abi']['arguments']),h['abi']['returnMode']) for h in c['hooks'])!=ABIS:
        raise ValueError('live-body compiled observer ABI/order')
    for h in c['hooks']:
        w,raw=windows[h['role']];entry=bytes.fromhex(h['entryHex'])
        if h['rva']!=w['rva'] or h['module']!=w['module'] or not 5<=len(entry)<=32 or not raw.startswith(entry):
            raise ValueError('live-body hook entry:'+h['role'])
        if h['module']=='gameAssembly':image.validate_method_row(h['method'],label='live-body-break')
        hooks.append(dict(**h,expectedBytes=entry.hex()))
    bounds=dict(maxBodyEvents=(1,16384),maxBreakEvents=(1,1024),initialSamples=(1,256),sampleEvery=(1,128),boostSteps=(1,240),maxBodyRoots=(1,128),maxBodyRechecks=(1,16384))
    if set(c['limits'])!=set(bounds) or any(type(c['limits'][k]) is not int or not lo<=c['limits'][k]<=hi for k,(lo,hi) in bounds.items()):
        raise ValueError('live-body unsafe limits')
    return dict(contract=c,hooks=hooks,pins=pins)
