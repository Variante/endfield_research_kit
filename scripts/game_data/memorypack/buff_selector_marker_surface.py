"""Authenticate marker-class surfaces without assigning predicate semantics."""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.core import CONTRACTS_DIR

CONTRACT_PATH=CONTRACTS_DIR/'buff_selector_marker_surface_native.json'
LABEL='buffSelectorMarkerSurface'

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-selector-marker-surface-native-contract.v1',status='exact-current-build',label=LABEL)
    if (len(c['types'])!=2 or any(r['declaredMethods']!=['.ctor'] or r['constructor'][1:3]!=[r['typeName'],'.ctor'] for r in c['types'])):
        raise ValueError(LABEL+'.contract-shape')
    return c

def _validate_image(image,c):
    selected=NativeReferenceContext(image);result=[]
    for row in c['types']:
        owner=selected.index.types.get(row['typeName'])
        if owner is None:raise ValueError(LABEL+'.missing-type:'+row['typeName'])
        methods=list(image.metadata.methods_for(owner));names=[image.metadata.string(m.name_index) for m in methods]
        if names!=row['declaredMethods']:raise ValueError(LABEL+'.method-surface:'+row['typeName'])
        if 'declaredFieldNames' in row:
            fields=[image.metadata.string(f.name_index) for f in image.metadata.fields_for(owner)]
            if fields!=row['declaredFieldNames']:raise ValueError(LABEL+'.field-surface:'+row['typeName'])
        if 'parentTypeName' in row and selected.parent(row['typeName'])!=row['parentTypeName']:
            raise ValueError(LABEL+'.parent-type:'+row['typeName'])
        image.validate_method_row(row['constructor'],label=LABEL)
        method=methods[0]
        if method.flags&0x10 or method.parameter_count!=0 or selected.type_name(method.return_type)!='void':
            raise ValueError(LABEL+'.constructor-signature:'+row['typeName'])
        window=row['constructorWindow'];image.check_windows([window],label=LABEL)
        if (window['startRva']!=row['constructor'][3] or window['endRva']-window['startRva']!=3
                or image.window_bytes(window)!=b'\xc2\x00\x00'):
            raise ValueError(LABEL+'.constructor-program:'+row['typeName'])
        result.append({'typeName':row['typeName'],'declaredMethodNames':names,
            'declaredPredicateMethodPresent':False,'constructorImmediateReturn':True})
    return result

def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    def empty(status,detail):return {'status':status,'detail':detail,'nativeInputs':pins,'typeSurfaces':[],'runtimePredicateKnown':False}
    if gate.status!='validated':return empty(gate.status,gate.detail)
    unity=gate.gameassembly.parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    result=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return empty(after.status,after.detail)
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll changed during validation')
    return {'status':'validated','nativeInputs':pins,'typeSurfaces':result,'runtimePredicateKnown':False,
        'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}
