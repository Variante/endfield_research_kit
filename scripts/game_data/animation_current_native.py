"""Explicit current raw-animation operation with native/source/pool bookends.

The selected families derive their complete owner graphs on the same native
image. Existing public readers retain their default profiles.
"""
from contextlib import contextmanager
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.memorypack import pooled_source_helper

SCHEMA='endfield.current-raw-animation-operation.v1'
FAMILIES={'char-interact','animation-config'}
_PUBLIC_NATIVE_GRANT=object()


class CurrentAnimationOperationError(ValueError):pass


def need(check,condition):
    if not condition:raise CurrentAnimationOperationError('currentAnimation.'+check)


def _gate(pins,root):
    return check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=root.parent/'GameAssembly.dll',metadata=root/'il2cpp_data/Metadata/global-metadata.dat')


def pool_capability(pooled_source,pins):
    """One cap projection from an independently fresh pooled-source result."""
    helpers=pooled_source.get('sourceHelpers',[])
    need('fresh-selected-pooled-source',pooled_source.get('status')=='validated'
        and pooled_source.get('nativeInputs')==pins and pooled_source.get('wireEncoding')=='int32-pool-index'
        and pooled_source.get('emptyIndex')==-1 and pooled_source.get('nullIndex')==-2
        and isinstance(helpers,list)and len(helpers)==1 and type(helpers[0])is int and helpers[0]>0)
    return dict(wholeGrammarAdmitted=True,encoding='int32-pool-index',wireBytes=4,
        emptyIndex=-1,nullIndex=-2,sourceTargetRva=helpers[0],runtimeStringResolutionRequired=True)


def validate_on_image(image,pins,*,families):
    """Fresh semantic proof on the caller's one selected native image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('finite-distinct-families',isinstance(families,(list,tuple))and bool(families)
        and len(families)==len(set(families))and set(families)<=FAMILIES)
    _publication_gate(image,pins);components={};caps={}
    declaration=pooled_source_helper._contract()
    need('same-selected-pool-native-inputs',declaration['nativeInputs']==pins)
    pool=pooled_source_helper.validate_on_image(image,image.pe.image_base+declaration['targetRva'],pins)
    caps['byte-payload']=pool_capability(pool,pins)
    def merge(component):
        incoming=component['capabilities']
        need('coherent-independent-child-capabilities',all(k not in caps or caps[k]==v for k,v in incoming.items()))
        caps.update(incoming)
    if 'char-interact'in families:
        from scripts.game_data.memorypack.char_current_graph_sources import derive as char_source
        component=char_source(image,pins,pooled_capability=caps['byte-payload'])
        need('fresh-complete-Char-parent',component.get('nativeInputs')==pins
            and component.get('status')=='validated-conditional-char-interact-current-components'
            and component.get('wholeOwnerGrammarAdmitted')is True
            and component.get('capabilities',{}).get('char-interact-current',{}).get('allTwentyEightFieldsAdmitted')is True)
        projected={k:component[k]for k in('schema','status','nativeInputs','capability','capabilities',
            'requiredExternalCapabilities','bindings','wholeOwnerGrammarAdmitted')}
        components['char-interact']=projected;merge(projected)
        del component
    if 'animation-config'in families:
        from scripts.game_data.memorypack.animation_config_components import derive_current
        component=derive_current(image,pins,pooled_capability=caps['byte-payload'])
        need('fresh-complete-AnimationConfig-parent',component.get('nativeInputs')==pins
            and component.get('status')=='validated-conditional-animation-config-components'
            and component.get('wholeOwnerGrammarAdmitted')is True
            and component.get('capabilities',{}).get('animation-config-current',{}).get('allFifteenFieldsAdmitted')is True)
        # Native derivation owns the full trace. The active cursor needs only
        # its immutable capability projection, not repeated descendant traces.
        projected={k:component[k]for k in('schema','status','nativeInputs','capability','capabilities',
            'requiredExternalCapabilities','bindings','wholeOwnerGrammarAdmitted')}
        components['animation-config']=projected;merge(projected)
        del component
    for component in components.values():
        need('all-required-child-capabilities',set(component.get('requiredExternalCapabilities',[]))<=set(caps))
    _publication_gate(image,pins)
    return dict(schema=SCHEMA,status='validated-current-raw-animation-sources',nativeInputs=pins,
        families=list(families),capabilities=caps,components=components,poolSource=pool,
        runtimeAnimationProved=False,wholeAnimationConfigAdmitted='animation-config'in components,
        wholeCharInteractAdmitted='char-interact'in components)


class _CurrentAnimationOperation:
    def __init__(self,proof,root,strings,*,_grant=None):
        self._proof=proof;self.game_root=Path(root).resolve();self.strings=strings
        self._grant=_grant;self.active=True;self._exit_validated=False
    def _active(self):
        need('active-public-native-operation',self.active and self._grant is _PUBLIC_NATIVE_GRANT
            and self._proof.get('status')=='validated-current-raw-animation-sources')
    def child(self,name):
        self._active();need('operation-owned-child:'+str(name),name in self._proof['capabilities'])
        return json.loads(json.dumps(self._proof['capabilities'][name]))
    def pool_index(self,index):self._active();return self.strings.resolve(index)
    def char_interact(self,data):
        self._active();need('selected-Char-family','char-interact'in self._proof['families'])
        from scripts.game_data.memorypack.char_current_codec import frame
        need('bytes-like-Char-payload',isinstance(data,(bytes,bytearray,memoryview)))
        return frame(bytes(data),self._proof['components']['char-interact'],operation=self)
    def animation_config(self,data):
        self._active();need('selected-AnimationConfig-family','animation-config'in self._proof['families'])
        from scripts.game_data.memorypack.animation_config_codec import frame
        need('bytes-like-AnimationConfig-payload',isinstance(data,(bytes,bytearray,memoryview)))
        return frame(bytes(data),self._proof['components']['animation-config'],operation=self)
    @property
    def receipt(self):
        need('validated-operation-exit',not self.active and self._exit_validated and self._grant is _PUBLIC_NATIVE_GRANT)
        return dict(schema=SCHEMA,status='validated-current-raw-animation-operation',nativeInputs=dict(self._proof['nativeInputs']),
            families=list(self._proof['families']),capabilities=sorted(self._proof['capabilities']),
            nativeSourcePoolExitBookendsPassed=True,operationScoped=True,runtimeAnimationProved=False,
            wholeAnimationConfigAdmitted=self._proof.get('wholeAnimationConfigAdmitted')is True,
            wholeCharInteractAdmitted=self._proof.get('wholeCharInteractAdmitted')is True)


def prepared_current_animation(operation):
    need('explicit-current-animation-operation',isinstance(operation,_CurrentAnimationOperation))
    operation._active();return operation


@contextmanager
def current_animation(*,game_root,strings,families=('char-interact',)):
    """Opt in once, decode selected files, and accept a receipt only after exit."""
    need('explicit-root-and-current-pool',game_root is not None and strings is not None
        and hasattr(strings,'root')and callable(getattr(strings,'resolve',None)))
    root=Path(game_root).resolve();source_before=snapshot_complete_reader_inputs()
    pool_root=Path(strings.root).parent;pool_before=snapshot_string_pool_inputs(pool_root)
    need('selected-pool-page-set',bool(pool_before.get('files')))
    pins=pooled_source_helper._contract()['nativeInputs'];gate=_gate(pins,root)
    need('selected-native-inputs',gate.status=='validated')
    need('selected-native-paths',Path(gate.gameassembly).resolve()==root.parent/'GameAssembly.dll'
        and Path(gate.metadata).resolve()==root/'il2cpp_data/Metadata/global-metadata.dat')
    need('selected-UnityPlayer',pooled_source_helper.check_unity_input(gate.gameassembly,pins)is None)
    proof=validate_on_image(open_native_image(gate.gameassembly,gate.metadata),pins,families=families)
    operation=_CurrentAnimationOperation(proof,root,strings,_grant=_PUBLIC_NATIVE_GRANT)
    try:yield operation
    finally:
        operation.active=False
        need('native-exit-bookend',_gate(pins,root).status=='validated'
            and pooled_source_helper.check_unity_input(gate.gameassembly,pins)is None)
        after=snapshot_complete_reader_inputs()
        if source_before!=after:
            raise CurrentAnimationOperationError('currentAnimation.reader-source-drift:'+str(reader_input_changes(source_before,after)))
        need('pool-exit-bookend',pool_before==snapshot_string_pool_inputs(pool_root))
        operation._exit_validated=True
