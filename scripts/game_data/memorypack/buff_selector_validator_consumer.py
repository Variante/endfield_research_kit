"""Current named consumer claims plus complete static control/frame checks."""
from __future__ import annotations
from pathlib import Path
import hashlib
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.body_claims import BodyIndex,check_claim
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack import buff_selector_marker_surface as selected_build

CONTRACT_PATH=CONTRACTS_DIR/'buff_selector_validator_consumer_claims.json'
LABEL='buffSelectorValidatorConsumer'

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-selector-validator-consumer-claims.v1',status='reviewed',label=LABEL)
    if c['controlRequirements']!={'completeOwnedBytePartition':True,'unknownInstructions':0,
            'closedBranchTargets':True,'ordinaryWin64CallFrames':True}:
        raise ValueError(LABEL+'.contract-control-shape')
    return c

def _validate_image(image,c):
    index=BodyIndex(image);spec=c['consumer'];body=index.body(spec['type'],spec['method'])
    selected=NativeReferenceContext(image)
    methods=[m for m in image.metadata.methods_for(index.types[spec['type']])
        if image.metadata.string(m.name_index)==spec['method'] and image.method_pointer_va(m)==body.pointer]
    if len(methods)!=1 or selected.type_name(methods[0].return_type)!=spec['returnType']:
        raise ValueError(LABEL+'.consumer-signature')
    parameters=[selected.type_name(p.type_index) for p in image.metadata.parameters_for(methods[0])]
    if parameters!=spec['parameters']:raise ValueError(LABEL+'.consumer-parameters')
    unique={}
    for row in index.body_with_fragments(body):
        if row['va'] in unique and (unique[row['va']]['bytes'],unique[row['va']]['text'])!=(row['bytes'],row['text']):
            raise ValueError(LABEL+'.overlapping-decode-disagreement')
        unique[row['va']]=row
    rows=sorted(unique.values(),key=lambda r:int(r['va'],16));ranges=[]
    for row in rows:
        a=int(row['va'],16);b=a+len(bytes.fromhex(row['bytes']))
        if ranges and ranges[-1][1]==a:ranges[-1][1]=b
        else:ranges.append([a,b])
    result=check_consumer_control(rows,entry=body.pointer,owned_ranges=ranges)
    reasons=[reason for claim in c['claims'] if (reason:=check_claim(index,body,claim)) is not None]
    if reasons:raise ValueError(LABEL+'.claim-failed:'+str(reasons)[:1200])
    return {'consumer':spec,'claimsProved':len(c['claims']),'methodIndex':methods[0].index,
        'bodyRva':body.pointer-image.pe.image_base,'instructionsChecked':result['instructionsChecked'],
        'ownedRangesChecked':result['ownedRangesChecked'],'callsChecked':len(result['calls']),
        'branchesChecked':len(result['branches']),'returnsChecked':len(result['returns']),
        'returnType':spec['returnType'],'runtimePredicateKnown':False,'runtimeExecutionKnown':False}

def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=selected_build._contract()['nativeInputs']
    def empty(status,detail):return {'status':status,'detail':detail,'nativeInputs':pins,'consumerProof':None,'runtimeExecutionKnown':False}
    g=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if g.status!='validated':return empty(g.status,g.detail)
    unity=g.gameassembly.parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    result=_validate_image(open_native_image(g.gameassembly,g.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=g.gameassembly,metadata=g.metadata)
    if after.status!='validated':return empty(after.status,after.detail)
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll changed during validation')
    return {'status':'validated','nativeInputs':pins,'consumerProof':result,'evidenceBoundary':c['evidenceBoundary'],
        'runtimePredicateKnown':False,'runtimeExecutionKnown':False,'wholeRootAdmitted':False}
