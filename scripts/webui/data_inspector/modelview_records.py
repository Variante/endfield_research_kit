"""Current ModelView stored graph records, freshly proved for each publication."""
import hashlib
from pathlib import Path
from scripts.source_paths import ExportLayout
from scripts.common import check_installed_native_inputs
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs, snapshot_string_pool_inputs


def _sources(root):
    return {p:hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in sorted(root.glob('*.json'))}


def _publishers():
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in (Path(__file__),Path(__file__).with_name('build_data_inspector.py'))}


def check_after_read(signature,export_root):
    layout=ExportLayout(export_root);pins=signature['nativeInputs'];selected=signature['nativeSources']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
    if gate.status!='validated':raise ValueError('ModelView Data native inputs: '+gate.status+': '+gate.detail)
    unity=check_unity_input(gate.gameassembly,pins)
    if unity:raise ValueError('ModelView Data Unity input: '+str(unity))
    if signature['readerInputs']!=snapshot_complete_reader_inputs():raise ValueError('ModelView Data reader source drift')
    if signature['stringPoolInputs']!=snapshot_string_pool_inputs(layout.json_dir):raise ValueError('ModelView Data string pool drift')
    if signature['publisherSources']!=_publishers():raise ValueError('ModelView Data publisher source drift')
    after={p.relative_to(export_root).as_posix():sha for p,sha in _sources(layout.json_dir/'Interactive/ModelViewStateControllerData').items()}
    if signature['sourceSha256']!=after:raise ValueError('ModelView Data source set or bytes drift')
from scripts.game_data.string_pool import export_string_pool
from scripts.webui.data_inspector.contract import source_descriptor


def current_records(export_root, *, gameassembly=None, metadata=None):
    from scripts.game_data.model_view_state_controller_binary import model_view_operation
    export_root=Path(export_root);layout=ExportLayout(export_root)
    root=layout.json_dir/'Interactive/ModelViewStateControllerData'
    sources=lambda:_sources(root)
    before=sources();records=[];reader_inputs=snapshot_complete_reader_inputs();pool_inputs=snapshot_string_pool_inputs(layout.json_dir);publishers=_publishers()
    with model_view_operation(export_string_pool(layout.json_dir),gameassembly=gameassembly,metadata=metadata)as decode:
        selected=dict(nativeInputs=decode.native_inputs,nativeSources=decode.native_sources,readerInputs=reader_inputs,stringPoolInputs=pool_inputs,publisherSources=publishers)
        for path,digest in before.items():
            data=path.read_bytes()
            if hashlib.sha256(data).hexdigest().upper()!=digest:raise ValueError(f'ModelView source changed while reading: {path}')
            source=source_descriptor(path,export_root=export_root,media_type='application/octet-stream')
            common=dict(id=path.relative_to(export_root).as_posix(),title=path.stem,source=source,tags=['model-view','stored-schema'])
            try:
                value=decode(data)
                if value.get('wholeSchemaExact')is not True or value.get('endOffset')!=len(data)or not isinstance(value.get('storedGraph'),dict):raise ValueError('complete current ModelView stored graph required')
                facts={key:value[key]for key in('modelId','modelAnimatorCount','layerCount','stateCount','behaviorCount','audioBehaviorCount','schemaStatus','evidenceBoundary')if key in value}
                records.append(dict(common,status='named_exact',summary=f"{value.get('stateCount',0)} states; stored fields, runtime selection unobserved",facts=facts,payload=value,payloadKind='reader'))
            except ValueError as error:
                records.append(dict(common,status='unsupported',summary=str(error)[:1000],facts=dict(sourceSha256=digest),diagnostic=str(error)))
    if before!=sources():raise ValueError('ModelView source set or bytes changed during Data publication')
    signature=dict(selected,sourceSha256={p.relative_to(export_root).as_posix():sha for p,sha in before.items()})
    check_after_read(signature,export_root)
    return records,signature
