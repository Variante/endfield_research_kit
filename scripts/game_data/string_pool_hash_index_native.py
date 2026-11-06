"""Authenticate reviewed SHPI declarations against the explicitly selected pair."""
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR


def load_schema(*,game_root):
    path=CONTRACTS_DIR/'string_pool_hash_index_native.json';before=path.read_bytes();c=json.loads(before)
    if c.get('schema')!='endfield.string-pool-hash-index-native.v1'or c.get('status')!='reviewed':
        raise ValueError('StringPoolHashNative.unsupported-contract')
    root=Path(game_root)if game_root is not None else None;pins=c['nativeInputs']
    options=dict(gameassembly=root.parent/'GameAssembly.dll',metadata=root/'il2cpp_data/Metadata/global-metadata.dat')if root else{}
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],**options)
    if gate.status!='validated':raise ValueError('StringPoolHashNative.selected-pair:'+gate.status+':'+gate.detail)
    unity=gate.metadata.parent.parent.parent.parent/'UnityPlayer.dll'
    if not unity.is_file()or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        raise ValueError('StringPoolHashNative.selected-UnityPlayer:'+str(unity))
    from scripts.game_data.il2cpp.native_image import open_native_image
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    image=open_native_image(gate.gameassembly,gate.metadata);ctx=NativeReferenceContext(image);md=image.metadata
    native=c['nativeHashIndex'];td=ctx.index.types[native['typeName']]
    fields=[]
    for field in md.fields_for(td):
        if not ctx.field_attributes(field.type_index)&16:
            name=md.string(field.name_index);fields.append([name,*ctx.field(native['typeName']+'::'+name)[1:]])
    if fields!=native['fields']:raise ValueError('StringPoolHashNative.own-declared-fields')
    for row in c['methods']:
        image.validate_method_row(row['method']);method=md.methods[row['method'][0]]
        if [ctx.type_name(p.type_index)for p in md.parameters_for(method)]!=row['parameters']or ctx.type_name(method.return_type)!=row['returned']:
            raise ValueError('StringPoolHashNative.own-method-ABI:'+str(row['method'][1:3]))
        image.check_windows(row['codeWindows'])
    exit_gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if exit_gate.status!='validated'or before!=path.read_bytes()or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        raise ValueError('StringPoolHashNative.native-contract-bookend')
    return c,dict(status='validated',nativeInputs=pins,validatedMethods=len(c['methods']),
        evidenceBoundary=c['evidenceBoundary'])
