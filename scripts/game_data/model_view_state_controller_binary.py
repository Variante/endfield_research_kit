"""One freshly proved ModelView stored-frame operation; runtime activation remains separate."""
import hashlib
from pathlib import Path
from contextlib import contextmanager
from scripts.game_data import model_view_state_controller_native as native
from scripts.game_data.memorypack.modelview import frame
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.string_pool import StringPool


class ModelViewFramingError(ValueError):
    def __init__(self,gate,actual=None):
        self.diagnostics=dict(validator='modelView',gate=gate,actual=actual)
        super().__init__('modelView.'+gate+':'+str(actual)[:1000])


@contextmanager
def model_view_operation(strings,*,game_root=None,gameassembly=None,metadata=None):
    if not isinstance(strings,StringPool):raise ModelViewFramingError('string-pool-required',type(strings).__name__)
    sources=snapshot_complete_reader_inputs();pool=snapshot_string_pool_inputs(Path(strings.root).parent);strings=StringPool(strings.root)
    proof=native.validate(game_root=game_root,gameassembly=gameassembly,metadata=metadata)
    if proof.get('status')!='validated':raise ModelViewFramingError('native-enter',proof)
    active=True
    def decode(data):
        if not active:raise ModelViewFramingError('operation-closed')
        try:
            out=frame(data,proof['layout'],strings)
            out.update(status='exact_current_model_view_frame',schemaMappingId='model-view-state-controller-current21',schemaStatus='conditional_current_build_wire',wholeSchemaExact=True,runtimeMappingId=None,evidenceBoundary=proof['evidenceBoundary'],nativeInputs=proof['nativeInputs'])
            return out
        except ValueError as error:
            failure=ModelViewFramingError('frame',str(error));failure.diagnostics['sourceSha256']=hashlib.sha256(data).hexdigest().upper();raise failure from error
    decode.native_sources=proof['nativeSources'];decode.native_inputs=proof['nativeInputs']
    try:yield decode
    finally:
        active=False;selected=proof['nativeSources'];after=native.validate(gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
        if after.get('status')!='validated':raise ModelViewFramingError('native-exit',after)
        if (proof['layout'],proof['nativeInputs'],proof['nativeSources'])!=(after['layout'],after['nativeInputs'],after['nativeSources']):raise ModelViewFramingError('native-drift')
        changed=snapshot_complete_reader_inputs()
        if sources!=changed:raise ModelViewFramingError('reader-source-drift',reader_input_changes(sources,changed))
        if pool!=snapshot_string_pool_inputs(Path(strings.root).parent):raise ModelViewFramingError('string-pool-drift')
