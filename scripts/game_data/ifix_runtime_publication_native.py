"""Authenticate bounded IFix publication bytes; never assert live selector continuity."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract

CONTRACT = CONTRACTS_DIR/'ifix_runtime_publication_native.json'
SCHEMA = 'endfield.ifix-runtime-publication-native-contract.v1'


class PublicationError(ValueError):
    def __init__(self, check, expected, actual, **where):
        def safe(value):
            if isinstance(value,bytes):return value.hex()[:4096]
            if isinstance(value,str):return value[:4096]
            if isinstance(value,(list,tuple)):return [safe(v) for v in value[:32]]
            if isinstance(value,dict):return {str(k):safe(v) for k,v in list(value.items())[:32]}
            if value is None or type(value) in (bool,int,float):return value
            return repr(value)[:4096]
        self.diagnostic = dict(validator='ifix_runtime_publication_native', check=check,
                               expected=safe(expected), actual=safe(actual), **where)
        super().__init__(check)


def need(actual, expected, check, **where):
    if actual != expected:
        raise PublicationError(check, expected, actual, **where)


def rva(value):
    return int(value,16) if isinstance(value,str) else value


def validate_raw(pe, contract):
    """Raw opcodes and independently resolved operands; no disassembler output."""
    base=pe.image_base
    def read(address,size):return pe.bytes_at_va(base+rva(address),size)
    def exact(address,expected,label):
        expected=bytes.fromhex(expected) if isinstance(expected,str) else expected
        need(read(address,len(expected)).hex(),expected.hex(),label,sourceRva=hex(rva(address)))
    def rip(address,prefix,target,size=7):
        prefix=bytes.fromhex(prefix);data=read(address,size)
        need(data[:len(prefix)].hex(),prefix.hex(),'rip-opcode',sourceRva=hex(rva(address)))
        need(rva(address)+size+struct.unpack_from('<i',data,len(prefix))[0],rva(target),'rip-target',sourceRva=hex(rva(address)))
    def relative(address,opcode,target):
        data=read(address,5);need(data[0],opcode,'relative-opcode',sourceRva=hex(rva(address)))
        need(rva(address)+5+struct.unpack_from('<i',data,1)[0],rva(target),'relative-target',sourceRva=hex(rva(address)))
    for window in contract['windows']:
        raw=read(window['rva'],window['byteCount'])
        need(hashlib.sha256(raw).hexdigest(),window['sha256'].lower(),'native-window',window=window['name'],sourceRva=window['rva'])
    roots=contract['rootCells'];init=contract['initialization'];layout=contract['layout']
    need(rva(roots['writer'])!=rva(roots['reader']),True,'distinct-root-cells')
    need([layout['pointerBytes'],layout['entryBytes'],layout['receiverDelta']],[8,16,8],'supported-pair-layout')
    bits=layout['pageBits'];need(type(bits)is int and 0<bits<31,True,'page-bit-domain')
    rip(init['allocatorLoadRva'],'488b05',init['allocatorCellRva'])
    exact(init['argumentRva'],'ba08000000','initializer-element-width')
    exact(init['callRva'],'ffd0','initializer-indirect-call')
    need(rva(init['callRva'])+2,rva(init['writerStoreRva']),'initializer-call-to-store')
    need(rva(init['writerStoreRva'])+7,rva(init['readerStoreRva']),'adjacent-same-RAX-stores')
    rip(init['writerStoreRva'],'488905',roots['writer']);rip(init['readerStoreRva'],'488905',roots['reader'])
    for load in contract['writerRootLoads']:rip(load['rva'],load['prefix'],roots[load['root']])
    for reset in contract['resetStores']:
        rip(reset['rva'],'48c705',roots[reset['root']],11)
        exact(rva(reset['rva'])+7,'00000000','reset-zero')
    registrations=contract['registration']
    for entry in registrations['candidates']:
        at=rva(entry['rva']);rip(at,'488d15',entry['handlerRva']);rip(at+7,'488d0d',entry['nameRva'])
        relative(at+14,0xe8,registrations['callTargetRva']);relative(entry['jumpRva'],0xe9,entry['writerRva'])
        expected=entry['name'].encode('ascii')+b'\0';need(read(entry['nameRva'],len(expected)),expected,'registration-name',sourceRva=entry['nameRva'])
    pub=contract['publication'];setp=pub['set'];clear=pub['clear'];allp=pub['clearAll']
    exact(setp['inputCopiesRva'],'4d8bf0488bf2','set-incoming-carriers')
    exact(setp['zeroRva'],'33db','set-zero-EBX')
    exact(setp['pageIndexRva'],b'\x8b\xe8\xc1\xed'+bytes([bits]),'set-page-index')
    mask=((1<<bits)-1).to_bytes(4,'little')
    exact(setp['slotIndexRva'],b'\x8b\xc7\x25'+mask+b'\x48\x03\xc0','set-slot-index')
    exact(setp['allocateArgumentsRva'],b'\x8d\x53\x10\xb9'+struct.pack('<I',1<<bits),'set-allocation-arguments')
    exact(setp['allocateCallRva'],'ffd0','set-allocation-call')
    exact(setp['allocateResultRva'],'488bd0','set-allocation-result')
    exact(setp['pageFenceRva'],'f0091c24','set-page-fence')
    exact(setp['pageStoreRva'],'488914e8','set-page-store')
    exact(setp['pairStoresRva'],'4c8974c208f0091c24488934c2','set-receiver-fence-function-order')
    exact(clear['zeroRva'],'33c9','clear-zero-ECX')
    exact(clear['pageIndexRva'],b'\x8b\xd0\x48\xc1\xea'+bytes([bits]),'clear-page-index')
    exact(clear['slotIndexRva'],b'\x25'+mask+b'\x48\x03\xc0','clear-slot-index')
    exact(clear['pairStoresRva'],'49890cc0f0090c2449894cc008','clear-function-fence-receiver-order')
    exact(allp['zeroRva'],'4533c9','clear-all-zero-R9D')
    exact(allp['countRva'],b'\x41\xba'+struct.pack('<I',1<<bits),'clear-all-entry-count')
    exact(allp['firstLoopRva'],'4d8bc24c8908488d40104983e80175f3','clear-all-function-loop')
    exact(allp['fenceRva'],'f044090c24','clear-all-middle-fence')
    exact(allp['secondLoopRva'],'4883c0084d8bc24c8908488d40104983e80175f3','clear-all-receiver-loop')
    rip(allp['countReloadRva'],'8b05',allp['pageCountCellRva'],6)
    need(rva(allp['firstLoopRva'])<rva(allp['fenceRva'])<rva(allp['countReloadRva'])<rva(allp['secondLoopRva']),True,'clear-all-static-order')
    for method in contract['methods']:
        rip(method['rootLoadRva'],'488b05',roots['reader'])
        exact(method['tableLoadRva'],bytes.fromhex(method['tablePrefix'])+bytes([method['tableOffset']]),'getter-table-family')
        exact(method['functionLoadRva'],bytes.fromhex(method['functionPrefix'])+struct.pack('<i',method['functionOffset']),'getter-function-slot')
        exact(method['receiverLoadRva'],bytes.fromhex(method['receiverPrefix'])+struct.pack('<i',method['receiverOffset']),'getter-receiver-slot')
        need(method['receiverOffset']-method['functionOffset'],layout['receiverDelta'],'getter-pair-adjacency')


def validate_extents(pe, functions):
    """Select only the reviewed exact .pdata triples; no CFG reconstruction."""
    opt=struct.unpack_from('<I',pe.buf,0x3c)[0]+24
    need(struct.unpack_from('<H',pe.buf,opt)[0],0x20b,'PE32-plus')
    at,size=struct.unpack_from('<II',pe.buf,opt+136)
    need(0<size<=64*1024**2 and size%12==0,True,'exception-directory-bound')
    rows=list(struct.iter_unpack('<III',pe.bytes_at_va(pe.image_base+at,size)))
    for f in functions:
        expected=(rva(f['rva']),rva(f['endRva']),rva(f['unwindRva']))
        found=[row for row in rows if row[0]==expected[0]]
        need(found,[expected],'writer-pdata-extent',function=f['name'])


def validate_stored_map(metadata, contract, indices):
    spec=contract['storedMap'];header=spec['headerPairOffset']
    need(0<=header<=len(metadata)-8,True,'metadata-header-bound')
    offset,size=struct.unpack_from('<II',metadata,header)
    need([offset,size],spec['expectedHeaderPair'],'stored-map-header')
    need(spec['rowBytes'],8,'stored-map-row-width')
    need(size%8==0 and 0<size//8<=spec['maxRows'] and offset+size<=len(metadata),True,'stored-map-range')
    selected={k:[] for k in indices}
    for rowno,(method,patch) in enumerate(struct.iter_unpack('<II',metadata[offset:offset+size])):
        for key,index in indices.items():
            if method==index:selected[key].append((rowno,method,patch))
    result=[];layout=contract['layout']
    for method in contract['methods']:
        key=method['key'];rows=selected[key];need(len(rows),1,'unique-stored-method-map-row',method=key)
        need(type(method['tableOffset']) is int and method['tableOffset']>=0
             and type(method['functionOffset']) is int and 0<=method['functionOffset']<(1<<layout['pageBits'])*layout['entryBytes'],
             True,'stored-map-slot-domain',method=key)
        need(method['tableOffset']%layout['pointerBytes']==method['functionOffset']%layout['entryBytes']==0,True,'stored-map-slot-alignment')
        slot=(method['tableOffset']//layout['pointerBytes'])*(1<<layout['pageBits'])+method['functionOffset']//layout['entryBytes']
        need(rows[0][2],slot,'stored-map-slot-arithmetic',method=key)
        result.append(dict(method=key,methodDefinitionIndex=indices[key],rowIndex=rows[0][0],storedPatchIndex=rows[0][2],computedSlotIndex=slot,runtimeHeaderBaseBindingProved=False))
    return result


def evaluate_publication(image, contract):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    selected=NativeReferenceContext(image);md=image.metadata;indices={}
    validate_raw(image.pe,contract);validate_extents(image.pe,contract['functions'])
    for spec in contract['methods']:
        types=[td for td in md.types if md.type_full_name(td)==spec['type']]
        need(len(types),1,'named-type',method=spec['key'])
        methods=[m for m in md.methods_for(types[0]) if md.string(m.name_index)==spec['method']]
        need(len(methods),1,'named-method',method=spec['key']);method=methods[0]
        actual=[selected.type_name(method.return_type),bool(method.flags&16),[selected.type_name(p.type_index) for p in md.parameters_for(method)]]
        need(actual,[spec['return'],spec['static'],spec['parameters']],'method-signature',method=spec['key'])
        need(image.method_pointer_va(method)-image.pe.image_base,rva(spec['rva']),'method-entry',method=spec['key'])
        indices[spec['key']]=method.index
    return validate_stored_map(md.buf,contract,indices)


def load_ifix_runtime_publication(*,gameassembly=None,metadata=None):
    if (gameassembly is None)!=(metadata is None):raise ValueError('supply both native paths')
    contract,digest=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='ifixRuntimePublication')
    pins=contract['nativeInputs']
    base=dict(schema=SCHEMA,contractSha256=digest,evidenceBoundary=contract['evidenceBoundary'],facts=None,
        storedMethodMapRows=[],conditionalNullPageInference=None,runtimeSelector=None,runtimeFactor=None,
        runtimeContinuityProved=False,allWritersEnumerated=False,runtimeHeaderBaseBindingProved=False)
    def reject(status,check,detail,diagnostic=None):
        return dict(base,status=status,detail=str(detail)[:1500],failures=[diagnostic or dict(validator='ifix_runtime_publication_native',check=check,source=str(CONTRACT),expected=pins,actual=str(detail)[:1500])])
    gate=check_installed_native_inputs(pins['gameAssemblySha256'],pins['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    base['nativeInputs']={k:getattr(gate,a,'') for k,a in (('gameAssemblySha256','gameassembly_sha256'),('metadataSha256','metadata_sha256'))}
    base['nativePaths']={'gameAssembly':str(getattr(gate,'gameassembly',gameassembly)),'metadata':str(getattr(gate,'metadata',metadata))}
    if not gate.validated:return reject(gate.status,'installed_native_inputs',gate.detail)
    try:
        image=open_native_image(gate.gameassembly,gate.metadata)
        for key,raw in (('gameAssemblySha256',image.pe.buf),('metadataSha256',image.metadata.buf)):
            actual=hashlib.sha256(raw).hexdigest()
            if actual.lower()!=pins[key].lower():return reject('mismatched','opened_native_inputs',f'{key}: expected {pins[key]}, actual {actual}')
        rows=evaluate_publication(image,contract)
    except PublicationError as exc:return reject('pendingReview',exc.diagnostic['check'],exc,dict(source=str(CONTRACT),**exc.diagnostic))
    except (OSError,ValueError,RuntimeError,KeyError,IndexError,struct.error) as exc:return reject('pendingReview','publication_evaluation',exc)
    after=check_installed_native_inputs(pins['gameAssemblySha256'],pins['metadataSha256'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if not after.validated:return reject(after.status,'installed_native_inputs_after',after.detail)
    current=hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    if current.lower()!=digest.lower():return reject('pendingReview','contract_changed','reviewed contract changed during evaluation')
    return dict(base,status='validated',detail='',failures=[],facts=contract['facts'],storedMethodMapRows=rows,
        conditionalNullPageInference=contract['conditionalNullPageInference'])


def main(argv=None):
    from scripts.repo_paths import REPO_ROOT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    if (args.gameassembly is None)!=(args.metadata is None):parser.error('supply both native paths')
    output=args.output.resolve()
    if not output.is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('output must be under reports/')
    result=load_ifix_runtime_publication(gameassembly=args.gameassembly,metadata=args.metadata)
    protected=[CONTRACT,Path(__file__),args.gameassembly,args.metadata,*[Path(p) for p in result.get('nativePaths',{}).values()]]
    if any(p is not None and output==Path(p).resolve() for p in protected):parser.error('output aliases a selected input')
    target=output if result['status']=='validated' else output.with_name(output.stem+'.diagnostics.json')
    if any(p is not None and target==Path(p).resolve() for p in protected):parser.error('diagnostic output aliases a selected input')
    atomic_write_text(target,json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'detail':result['detail'],'report':str(target),'runtimeContinuityProved':False}))
    return 0 if result['status']=='validated' else 1


if __name__=='__main__':raise SystemExit(main())
