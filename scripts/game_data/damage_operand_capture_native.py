"""Authenticate scoped ordinary-entry damage operand observations.

A bounded first-call graph preserves XMM1 on ordinary paths. Exception/resume
paths, the capture backend and runtime values remain separate boundaries.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract

CONTRACT = CONTRACTS_DIR / 'damage_operand_capture_native.json'
SCHEMA = 'endfield.damage-operand-capture-native-contract.v2'


def need(actual, expected, check):
    if actual != expected:
        raise ValueError(f'{check}: expected={expected!r}, actual={actual!r}')


def xmm_destination(raw):
    """Fail-closed instruction vocabulary for the reviewed bounded graph."""
    at=0;rex=0
    while at<len(raw) and (raw[at] in (0x66,0xf2,0xf3) or 0x40<=raw[at]<=0x4f):
        if 0x40<=raw[at]<=0x4f:rex=raw[at]
        at+=1
    need(at<len(raw),True,'prefix-bound');op=raw[at]
    if op==0xf:
        need(at+1<len(raw),True,'opcode-bound');second=raw[at+1]
        if second in (0x10,0x11,0x28,0x58,0x59,0x5c):
            need(at+2<len(raw),True,'modrm-bound');modrm=raw[at+2]
            if second==0x11:return (modrm&7)+(8 if rex&1 else 0) if modrm>>6==3 else None
            return ((modrm>>3)&7)+(8 if rex&4 else 0)
        need(second in (0xb6,0x95) or 0x80<=second<=0x8f,True,'reviewed-two-byte-opcode');return None
    need(op in (0x8b,0x84,0x85,0xa9,0x83,0x80,0x88,0x33,0x8d,0xe8) or 0x70<=op<=0x7f,True,'reviewed-opcode')
    return None


def validate_graph(pe,c):
    g=c['firstCallGraph'];nodes={}
    for n in g['nodes']:
        at=int(n['rva'],16);raw=bytes.fromhex(n['bytes'])
        need(at not in nodes and 0<len(raw)<=15,True,'node-boundaries')
        need(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,'node-bytes:'+n['rva']);nodes[at]=raw
    declared={int(r['callRva'],16):r for r in g['firstCalls']};excluded={int(x,16) for x in g['excludedExceptionDestinations']}
    use=int(g['factorUseRva'],16);need(nodes.get(use),bytes.fromhex(g['factorUseBytes']),'factor-use-node')
    need(nodes[use],bytes.fromhex('f2440f59c1'),'factor-use-operands')
    observed={};seen=set();todo=[(int(g['entryRva'],16),False)]
    while todo:
        at,used=todo.pop();used=used or at==use
        if (at,used) in seen:continue
        seen.add((at,used))
        if at in excluded:continue
        need(at in nodes,True,'missing-successor:'+hex(at));raw=nodes[at]
        need(xmm_destination(raw)!=1,True,'factor-register-clobber:'+hex(at))
        if raw[0]==0xe8:
            need(used,True,'first-call-before-factor-use')
            need(len(raw),5,'call-width');need(at in declared,True,'uncovered-first-call');r=declared[at]
            need(at+5+struct.unpack_from('<i',raw,1)[0],int(r['targetRva'],16),'first-call-target')
            need(at+5,int(r['returnRva'],16),'first-call-return');observed[at]=r;continue
        dest=[at+len(raw)]
        if 0x70<=raw[0]<=0x7f:
            need(len(raw),2,'short-branch-width');dest.append(at+2+struct.unpack_from('<b',raw,1)[0])
        elif raw[:1]==b'\x0f' and 0x80<=raw[1]<=0x8f:
            need(len(raw),6,'near-branch-width');dest.append(at+6+struct.unpack_from('<i',raw,2)[0])
        todo.extend((dst,used) for dst in dest)
    need(set(observed),set(declared),'complete-first-call-set');need(excluded<={at for at,_ in seen},True,'exception-exit-reachability')
    bindings=[]
    for e in c['contextEntries']:
        need(e['context']['factorRegister'],'xmm1','factor-context-register')
        need(e['context']['localPackOffsetFromEntryRsp'],c['joins']['framePackOffset']+8,'entry-pack-offset')
        bindings.extend((int(r,16),int(e['rva'],16)) for r in e['callerReturnRvas'])
    need(sorted(bindings),sorted((int(r['returnRva'],16),int(r['targetRva'],16)) for r in observed.values()),'context-call-bindings')
    for r in g['excludedExceptionWindows']:
        raw=bytes.fromhex(r['bytes']);need(pe.bytes_at_va(pe.image_base+int(r['branchDestinationRva'],16),len(raw)),raw,'excluded-exception-bytes')
    return dict(reachableNodes=len(seen),firstCalls=list(observed.values()),factorUseDominatesFirstCallsInBoundedGraph=True,xmm1PreservedUntilFirstCall=True,exceptionResumePathsIncluded=False,conditions=g['conditions'])


def validate_sites(pe,c):
    read=lambda r,n:pe.bytes_at_va(pe.image_base+int(r,16),n)
    for w in c['windows']:need(hashlib.sha256(read(w['rva'],w['byteCount'])).hexdigest().lower(),w['sha256'].lower(),'window:'+w['name'])
    opt=struct.unpack_from('<I',pe.buf,60)[0]+24;need(struct.unpack_from('<H',pe.buf,opt)[0],0x20b,'PE32-plus')
    at,size=struct.unpack_from('<II',pe.buf,opt+136);need(0<size<=64*1024**2 and size%12==0,True,'pdata-bounds')
    pdata=list(struct.iter_unpack('<III',pe.bytes_at_va(pe.image_base+at,size)))
    for f in c['functions']:
        triple=tuple(int(f[k],16) for k in ['rva','endRva','unwindRva']);need([r for r in pdata if r[0]==triple[0]],[triple],'pdata:'+f['name'])
    for e in c['contextEntries']+c['pairedEntries']:
        b=bytes.fromhex(e['expectedBytes']);need(len(b)>=16,True,'entry-width');need(read(e['rva'],len(b)),b,'entry:'+e['key']);u=e['sourceUnwind']
        if u['kind']=='leaf':
            va=int(e['rva'],16);need([r for r in pdata if r[0]<=va<r[1]],[],'leaf-pdata')
        else:
            b=bytes.fromhex(u['expectedBytes']);need(read(u['rva'],len(b)),b,'entry-unwind');h=b[:4]
            need([h[0]&7,h[0]>>3,h[1],h[2],h[3]],[u['version'],u['flags'],u['prologueBytes'],u['codeSlots'],u['frameByte']],'unwind-header')
    j=c['joins'];pack=j['framePackOffset']
    need(read(j['packArgumentLeaRva'],8),b'\x48\x8d\x8c\x24'+struct.pack('<I',pack),'pack-address')
    defender=next(f for f in c['fields'] if f['field'].endswith('DamagePackData::defender'))
    need(read(j['defenderArgumentLeaRva'],8),b'\x48\x8d\x8c\x24'+struct.pack('<I',pack+defender['offset']-j['boxedHeaderBytes']),'defender-address')
    for n in ['healthReceiverMove','lockResultMove']:need(read(j[n+'Rva'],len(bytes.fromhex(j[n+'Bytes']))),bytes.fromhex(j[n+'Bytes']),n)
    health,raw=c['pairedEntries']
    need([health['key'],health['abiId'],health['nativeAbiDeclaration']['argumentRegisters'],health['nativeAbiDeclaration']['includesMethodInfo']],['healthPredicateEntry','win64.scoped_paired_gp_bool_1.v1',['rcx'],False],'physical-health-abi')
    need([raw['key'],raw['abiId'],raw['nativeAbiDeclaration']['argumentRegisters'],raw['nativeAbiDeclaration']['includesMethodInfo']],['usesRawEntry','win64.scoped_paired_gp_bool_2.v1',['rcx','rdx'],True],'raw-managed-abi')
    for e,k in [(health,'healthCallRva'),(raw,'rawCallRva')]:
        at=int(j[k],16);b=read(j[k],5);need(b[:1],b'\xe8','paired-call')
        need(at+5+struct.unpack_from('<i',b,1)[0],int(e['rva'],16),'paired-target');need(e['callerReturnRvas'],[hex(at+5)],'paired-return')
    need(read(j['rawMethodInfoZeroRva'],2),b'\x33\xd2','raw-method-info')
    damage=next(f for f in c['fields'] if f['field'].endswith('DamagePackData::damageType'))
    need(read(j['damageTypeLoadRva'],7),b'\x8b\x8c\x24'+struct.pack('<I',pack+damage['offset']-j['boxedHeaderBytes']),'damage-type-argument')
    b=read(j['healthEntryRva'],69);need(b[:9],bytes.fromhex('4883ec284885c97432'),'health-entry')
    need(b[47:],bytes.fromhex('83f801740d32c04883c428c3e86092d8faccb001ebf1'),'health-bool-exits')
    data=next(f for f in c['fields'] if f['field'].endswith('AbilitySystem::<data>k__BackingField'))
    need(b[29:36],b'\x48\x8b\x81'+struct.pack('<I',data['offset']),'health-data-consumer');need(health['fields'][0]['offset'],data['offset'],'entry-data-snapshot')
    return validate_graph(pe,c)


def evaluate(image,contract):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    selected=NativeReferenceContext(image);md=image.metadata
    proof=validate_sites(image.pe,contract)
    for spec in contract['methods']:
        types=[t for t in md.types if md.type_full_name(t)==spec['type']]
        need(len(types),1,'unique-type:'+spec['key'])
        methods=[m for m in md.methods_for(types[0]) if md.string(m.name_index)==spec['method']]
        need(len(methods),1,'unique-method:'+spec['key']);m=methods[0]
        need([selected.type_name(m.return_type),bool(m.flags&16),[selected.type_name(p.type_index) for p in md.parameters_for(m)]],
             [spec['return'],spec['static'],spec['parameters']],'signature:'+spec['key'])
        need(image.method_pointer_va(m)-image.pe.image_base,int(spec['rva'],16),'named-entry:'+spec['key'])
    for spec in contract['fields']:
        need(list(selected.field(spec['field'])[1:]),[spec['type'],spec['offset']],'field:'+spec['field'])


    return proof


def load_damage_operand_capture(*,gameassembly=None,metadata=None):
    if (gameassembly is None)!=(metadata is None):raise ValueError('supply both native paths')
    c,digest=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='damageOperandCapture')
    base=dict(schema=SCHEMA,contractSha256=digest,evidenceBoundary=c['evidenceBoundary'],sites=[],contextEntries=[],pairedEntries=[],firstCallProof=None,
              backendValidated=False,wholeProgramIncomingEdgesProved=False,runtimeValues=None)
    def reject(status,check,detail):
        return dict(base,status=status,detail=str(detail)[:1500],failures=[dict(check=check,detail=str(detail)[:1500])])
    pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['gameAssemblySha256'],pins['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    base['nativeInputs']={k:getattr(gate,a,'') for k,a in [('gameAssemblySha256','gameassembly_sha256'),('metadataSha256','metadata_sha256')]}
    if not gate.validated:return reject(gate.status,'installed_native_inputs',gate.detail)
    try:
        image=open_native_image(gate.gameassembly,gate.metadata)
        for key,raw in [('gameAssemblySha256',image.pe.buf),('metadataSha256',image.metadata.buf)]:
            need(hashlib.sha256(raw).hexdigest().lower(),pins[key].lower(),'opened-input:'+key)
        proof=evaluate(image,c)
    except (OSError,ValueError,RuntimeError,KeyError,IndexError,struct.error) as exc:
        return reject('pendingReview','operand-capture-evaluation',exc)
    after=check_installed_native_inputs(pins['gameAssemblySha256'],pins['metadataSha256'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if not after.validated:return reject(after.status,'installed_native_inputs_after',after.detail)
    if hashlib.sha256(CONTRACT.read_bytes()).hexdigest().lower()!=digest.lower():
        return reject('pendingReview','contract_changed','contract changed during evaluation')
    return dict(base,status='validated',detail='',failures=[],sites=c['contextEntries']+c['pairedEntries'],contextEntries=c['contextEntries'],pairedEntries=c['pairedEntries'],firstCallProof=proof,validatedFields=c['fields'],
                backendRequirements=c['backendRequirements'],unresolved=c['unresolved'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path)
    args=parser.parse_args(argv)
    result=load_damage_operand_capture(gameassembly=args.gameassembly,metadata=args.metadata)
    print(json.dumps(result,indent=2));return 0 if result['status']=='validated' else 1


if __name__=='__main__':raise SystemExit(main())
