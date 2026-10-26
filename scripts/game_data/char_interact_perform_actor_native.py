"""Authenticate positive actor source facts without admitting their enclosing owner."""
from pathlib import Path
from scripts.common import check_installed_native_inputs,sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.struct_output_sources import check_reader_ref_wrapper_abi

CONTRACT_PATH=CONTRACTS_DIR/'char_interact_perform_actor_native.json'
SCHEMA='endfield.char-interact-perform-actor-source.v1'

def _validate(image,contract):
    def require(condition,check):
        if not condition:raise ValueError('charInteractActor.'+check)
    context=NativeReferenceContext(image);metadata=image.metadata;base=image.pe.image_base
    fields=contract['fields'];owner=context.index.types[contract['typeName']];wrapper=context.index.types[contract['wrapperName']]
    declared={metadata.string(f.name_index):context.field(contract['typeName']+'::'+metadata.string(f.name_index)) for f in metadata.fields_for(owner) if not context.field_attributes(f.type_index)&16}
    require(len(fields)==contract['memberCount']==len(declared) and {f['name'] for f in fields}==set(declared),'field-set')
    require(context.field(contract['wrapperName']+'::__instance')==(contract['wrapperName'],contract['typeName'],16),'typed-holder')
    def fail(*args):raise ValueError('charInteractActor.reader-abi:'+str(args)[:400])
    image.validate_method_row(contract['readerMethod'])
    check_reader_ref_wrapper_abi(image,dict(readerMethod=contract['readerMethod'],wrapperTypeDefinition=wrapper.index),fail=fail)
    windows=contract['codeWindows'];actual=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(contract['readerMethod'][3])['ranges'])
    require(actual==sorted((w['startRva'],w['endRva']) for w in windows),'owned-windows');image.check_windows(windows)
    instructions=[contract['memberCountInstruction']];previous=instructions[0][0]
    widths=dict(enum32=4,uint32=4,int32=4,uint64=8,int64=8,pooledStringIndex=4,boolByte=1,float32=4)
    for field in fields:
        require(declared[field['name']][1:]==(field['type'],field['fieldOffset']),'typed-field:'+field['name'])
        require(widths.get(field['wire'])==field['wireBytes'],'wire-width:'+field['name'])
        call,raw=field['sourceCall'];encoded=bytes.fromhex(raw)
        require(len(encoded)==5 and encoded[0]==0xe8 and call+5+int.from_bytes(encoded[1:],'little',signed=True)==field['sourceTargetRva'],'source-target:'+field['name'])
        require(previous<call<field['returnTransfer'][-1][0],'field-order:'+field['name']);previous=field['returnTransfer'][-1][0]
        instructions.extend([field['sourceCall'],*field['returnTransfer']])
    image.check_instruction_windows(instructions)
    for table in contract['embeddedTables']:
        start,end=table['startRva'],table['endRva'];require(0<end-start<=262144 and (end-start)%4==0,'table-bounds')
        require(any(w['startRva']<=start<end<=w['endRva'] for w in windows),'table-owner')
        require([image.pe.u32_at_va(base+at) for at in range(start,end,4)]==table['targets'],'table-targets')
        image.check_windows([table])

def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None):
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='validated',label='charInteractActor')
    pins=contract['nativeInputs']
    def gate():return check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    before=gate()
    if before.status!='validated':return dict(status=before.status,detail=before.detail,fields=[],wholeOwnerAdmitted=False)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def unity_status():return 'missing' if not unity.is_file() else 'validated' if sha256_file_upper(unity)==pins['UnityPlayer.dll'].upper() else 'mismatched'
    selected=unity_status()
    if selected!='validated':return dict(status=selected,detail='Selected UnityPlayer.dll is '+selected,fields=[],wholeOwnerAdmitted=False)
    _validate(open_native_image(before.gameassembly,before.metadata),contract)
    after=gate();selected=unity_status()
    if after.status!='validated' or selected!='validated':return dict(status=after.status if after.status!='validated' else selected,detail='Selected native inputs changed during actor validation',fields=[],wholeOwnerAdmitted=False)
    return dict(status='validated',fields=contract['fields'],memberCount=contract['memberCount'],evidenceBoundary=contract['evidenceBoundary'],wholeOwnerAdmitted=False)
