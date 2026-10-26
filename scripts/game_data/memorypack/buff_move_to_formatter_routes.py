"""Authenticate MoveTo/SubSpeed generated wrapper registration and reader routes."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.context import method_parameter_owner
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_package_import_closure
from scripts.game_data.memorypack import generated_formatter_routes as routes

LABEL='buffMoveToFormatterRoutes'
SCHEMA='endfield.buff-move-to-formatter-routes-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_move_to_formatter_routes_native.json'
DEPENDENCY_SCHEMAS={'parent':'endfield.buff-move-to-source-native-contract.v2',
    'subSpeed':'endfield.buff-move-to-subspeed-source-native-contract.v1',
    'lifecycle':'endfield.buff-move-to-lifecycle-native-contract.v1'}

def _fail(check,expected,actual,**scope):
    error=CensusGateError(LABEL+'.'+check,source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1800],actual=str(actual)[:2200])
    error.diagnostic.update(validator=LABEL,check=check,scope=scope)
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (set(c.get('dependencies',{}))!=set(DEPENDENCY_SCHEMAS) or set(c.get('records',{}))!={'moveTo','subSpeed'} or
        any(not isinstance(name,str) or Path(name).name!=name or '/' in name or '\\' in name or not name.endswith('_native.json') for name in c['dependencies'].values())):
        _fail('contract-scope','current parent/subSpeed/lifecycle dependencies and both wrapper routes',c.get('dependencies'))
    return c

def _usage(image,selected,entries,record,row,role,opcode):
    choices=[u for u in record['typedUsages'] if u['instructionRva']==row[0]]
    raw=bytes.fromhex(row[1])
    if len(choices)!=1 or len(raw)!=7 or not row[1].startswith(opcode):
        _fail('typed-route-operand',{'instruction':row,'role':role,'opcode':opcode},choices)
    u=choices[0];cell=row[0]+7+int.from_bytes(raw[3:],'little',signed=True)
    data=image.pe.bytes_at_va(image.pe.image_base+cell,8);encoded=int.from_bytes(data,'little')
    if (u['instructionHex']!=row[1] or u['cellRva']!=cell or data.hex().upper()!=u['usageRawHex'] or encoded>>32 or not encoded&1):
        _fail('typed-route-usage-cell',u,{'cell':cell,'raw':data.hex()})
    tag=encoded>>29;item=(encoded&0x1fffffff)>>1
    if tag!=u['tag'] or item!=u['index']:_fail('typed-route-usage-index',u,[tag,item])
    if role=='closedRegisterMethodInfo':
        if tag!=6 or not 0<=item<len(entries.specs):
            _fail('closed-register-spec-range','bounded actual method usage',[tag,item])
        spec=list(entries.specs[item])
        if (spec!=u['methodSpec'] or spec[:2]!=[record['registerDefinition'][0],-1] or
            entries.arguments(spec[2])[0]!=[record['wrapperTypeName']]):
            _fail('closed-register-wrapper','same owned Register definition and exact wrapper method argument',u)
    else:
        wanted={'formatterClass':record['formatterTypeName'],'providerClass':'MemoryPack.MemoryPackFormatterProvider',
                'wrapperClass':record['wrapperTypeName']}[role]
        if tag!=1 or selected.type_name(item)!=wanted or u['typeName']!=wanted:
            _fail('typed-route-class',wanted,u)

def _register_signature(image,selected,definition):
    if definition[1:]!=['MemoryPack.MemoryPackFormatterProvider','Register']:
        _fail('register-owner','MemoryPackFormatterProvider.Register',definition)
    image.validate_method_row(definition,label=LABEL)
    method=image.metadata.methods[definition[0]];parameters=list(image.metadata.parameters_for(method))
    section=image.metadata.sections['genericContainers'];at=section.offset+method.generic_container_index*16
    if (not method.flags&0x10 or len(parameters)!=1 or selected.type_name(method.return_type)!='void' or
        method.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16):
        _fail('register-signature','static void Register<T>(MemoryPackFormatter<T>)',definition)
    owner,count,is_method,start=struct.unpack_from('<iiii',image.metadata.buf,at)
    identity=method_parameter_owner(image.metadata.buf,start,[m.generic_container_index for m in image.metadata.methods],source=LABEL)
    if ((owner,count,is_method)!=(definition[0],1,1) or identity['methodIndex']!=definition[0] or identity['ordinal']!=0 or
        selected.type_name(parameters[0].type_index)!=f'MemoryPack.MemoryPackFormatter`1<MVAR[{start}]>'):
        _fail('register-owned-parameter','formatter over the sole reciprocal method parameter',identity)

def _reader_signature(image,selected,method_row,wrapper):
    method=image.metadata.methods[method_row[0]];params=list(image.metadata.parameters_for(method))
    if len(params)!=2 or selected.type_name(method.return_type)!='void':_fail('reader-signature','two byrefs and void',method_row)
    raw=[image.pe.bytes_at_va(selected.type_pointer(p.type_index),16) for p in params]
    reader=selected.index.types['MemoryPack.MemoryPackReader'].index
    if (raw[0][10:12]!=b'\x11\x20' or int.from_bytes(raw[0][:8],'little')!=reader or
        raw[1][10:12]!=b'\x12\x20' or int.from_bytes(raw[1][:8],'little')!=wrapper):
        _fail('reader-owned-byrefs',{'reader':reader,'wrapper':wrapper},[r.hex() for r in raw])

def _validate_image(image,c,deps):
    selected=NativeReferenceContext(image);entries=GenericEntries(image);result={}
    for kind,r in c['records'].items():
        old=deps['parent' if kind=='moveTo' else 'subSpeed']['records'][kind]
        if (r['wrapperTypeDefinition'],r['wrapperTypeName'],r['readerMethod'])!=(old['wrapperTypeDefinition'],old['wrapperTypeName'],old['readerMethod']):
            _fail('current-reader-owner',old,r['readerMethod'],record=kind)
        if r['calls']['allocation']!=deps['lifecycle']['calls']['allocation']:_fail('current-allocation-call',deps['lifecycle']['calls']['allocation'],r['calls'])
        if r['calls']['formatterConstructor']!=r['constructorMethod'][3]:
            _fail('actual-created-formatter-constructor',r['constructorMethod'],r['calls'])
        for key in ('initializerMethod','registrarMethod','constructorMethod','deserializeMethod','readerMethod'):
            row=r[key];image.validate_method_row(row,label=LABEL);method=image.metadata.methods[row[0]]
            if selected.type_name(method.return_type)!='void':_fail('method-void',key,row)
            expected={ 'initializerMethod':'.cctor','registrarMethod':'RegisterFormatter','constructorMethod':'.ctor',
                       'deserializeMethod':'Deserialize','readerMethod':'Deserialize'}[key]
            if row[2]!=expected:_fail('route-method-name',expected,row)
        for key in ('initializerMethod','registrarMethod'):
            method=image.metadata.methods[r[key][0]]
            if not method.flags&0x10 or image.metadata.parameters_for(method):_fail('static-zero-parameter',key,r[key])
            if image.type_name(method.declaring_type)!=r['wrapperTypeName']:
                _fail('wrapper-owned-registration-method',r['wrapperTypeName'],r[key])
        for key in ('constructorMethod','deserializeMethod'):
            method=image.metadata.methods[r[key][0]]
            if method.flags&0x10:_fail('instance-formatter-method',key,r[key])
        if image.metadata.parameters_for(image.metadata.methods[r['constructorMethod'][0]]):_fail('formatter-constructor-parameters','none',r['constructorMethod'])
        formatter=image.metadata.methods[r['deserializeMethod'][0]]
        if formatter.slot!=5 or image.type_name(formatter.declaring_type)!=r['formatterTypeName']:
            _fail('formatter-deserialize-slot','actual declaring formatter and virtual slot five',r['deserializeMethod'])
        if (selected.parent(r['formatterTypeName'])!=f"MemoryPack.MemoryPackFormatter`1<{r['wrapperTypeName']}>" or
            image.type_name(image.metadata.methods[r['constructorMethod'][0]].declaring_type)!=r['formatterTypeName']):
            _fail('formatter-closed-wrapper-base',r['wrapperTypeName'],r['formatterTypeName'])
        _reader_signature(image,selected,r['deserializeMethod'],r['wrapperTypeDefinition'])
        _reader_signature(image,selected,r['readerMethod'],r['wrapperTypeDefinition'])
        if not image.metadata.methods[r['readerMethod'][0]].flags&0x10:_fail('static-reader','static current reader',r['readerMethod'])
        _register_signature(image,selected,r['registerDefinition'])
        entry=entries.resolve(r['registerDefinition'][0],[],['object'])
        if entry['pointer']-image.pe.image_base!=r['calls']['register']:_fail('actual-register-entry',r['calls']['register'],entry)
        for key,method_key in (('initializer','initializerMethod'),('firstRegistration','registrarMethod'),('constructorReady','constructorMethod'),('deserialize','deserializeMethod')):
            if r['proofs'][key]['program'][0][0]!=r[method_key][3]:_fail('program-entry',r[method_key],r['proofs'][key]['program'][0])
        use=lambda row,role,opcode:_usage(image,selected,entries,r,row,role,opcode)
        result[kind]={'initializer':routes.initializer_tail(image,r['proofs']['initializer'],r['registrarMethod'][3],fail=_fail),
            'constructorReady':routes.constructor_ready(image,r['proofs']['constructorReady'],fail=_fail),
            'firstWrapperRegistration':routes.first_registration(image,r['proofs']['firstRegistration'],r['calls'],usage=use,fail=_fail),
            'deserializeTail':routes.deserialize_tail(image,r['proofs']['deserialize'],r['readerMethod'][3],usage=use,fail=_fail),
            'wrapperTypeName':r['wrapperTypeName'],'runtimeTypeName':old['runtimeTypeName'],
            'registrationIsForWrapperNotRuntimeOriginal':True,'physicalRegisterDefinitionJoined':True,
            'runtimeOriginalAdapterSelectionProved':False}
    return result

def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c=_contract();native=c['nativeInputs']
    pair=check_installed_native_inputs(native['GameAssembly.dll'],native['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if pair.status!='validated':return {'status':pair.status,'detail':pair.detail,'nativeInputs':native}
    unity=Path(pair.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==native['UnityPlayer.dll']
    if not unity_matches():return {'status':'mismatched' if unity.is_file() else 'missing','detail':'UnityPlayer.dll differs','nativeInputs':native}
    deps={key:read_reviewed_contract(CONTRACTS_DIR/name,schema=DEPENDENCY_SCHEMAS[key],status='exact-current-build',label=LABEL)[0] for key,name in c['dependencies'].items()}
    if any(d['nativeInputs']!=native for d in deps.values()):_fail('dependency-build',native,{k:d['nativeInputs'] for k,d in deps.items()})
    paths={CONTRACT_PATH,*(CONTRACTS_DIR/name for name in c['dependencies'].values()),*_package_import_closure(Path(__file__)),
        NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,Path(pair.gameassembly),Path(pair.metadata),unity}
    sources=[_fingerprint(path) for path in sorted(paths)]
    try:summary=_validate_image(open_native_image(pair.gameassembly,pair.metadata),c,deps)
    except ValueError as error:
        if isinstance(error,CensusGateError):raise
        _fail('native-formatter-route','actual wrapper registration and complete ready caller paths',str(error))
    for row in sources:
        if _fingerprint(Path(row['path']))!=row:_fail('source-drift',row,_fingerprint(Path(row['path'])))
    after=check_installed_native_inputs(native['GameAssembly.dll'],native['global-metadata.dat'],gameassembly=pair.gameassembly,metadata=pair.metadata)
    if after.status!='validated' or not unity_matches():return {'status':after.status if after.status!='validated' else 'mismatched','detail':'native inputs changed','nativeInputs':native}
    return {'status':'validated','nativeInputs':native,'proofSources':sources,'summary':summary,'evidenceBoundary':c['evidenceBoundary'],
        'providerDictionaryEffectsProved':False,'runtimeOriginalAdapterSelectionProved':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True);args=parser.parse_args();report=args.report.resolve()
    if not report.is_relative_to(Path(__file__).resolve().parents[3]/'reports'):parser.error('--report must be inside reports')
    result=validate_current_native_contract(gameassembly=args.gameassembly,metadata=args.metadata)
    if result['status']!='validated':print(json.dumps({'status':result['status'],'detail':result.get('detail'),'reportPreserved':report.as_posix()}));raise SystemExit(1)
    result.update(schema='endfield.buff-move-to-formatter-routes-validation.v1',checkedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'wrapperRoutes':len(result['summary']),'report':report.as_posix()}),flush=True)

if __name__=='__main__':main()
