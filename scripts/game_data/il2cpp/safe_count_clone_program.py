"""Complete ordinary SafeCount clone equivalence; runtime dispatch stays conditional."""
from scripts.game_data.il2cpp.collection_empty_clone_program import _program,_target
from scripts.game_data.il2cpp.initializer_control import control_transfer

def check_safe_count_clone(canonical,clone,indexed_type_leaf):
    common=['48895c2408','57','4883ec20','48837a3800']
    _program(canonical,common+['488bda','488bf9','7508','488bca',None,'4885ff','7504','33c0','eb19',
        '488b4b38','488b09',None,'33c9','4c8bc7','488bd0',None,'488b5c2430','4883c420','5f','c3'],'safeCount.canonical')
    _program(clone,common+['488bfa','488bd9','7434','4885db','7422','488b4f38','33d2',None,
        '488bd0','33c9','4c8bc3','488b5c2430','4883c420','5f',None,'488b5c2430','33c0','4883c420','5f','c3','488bcf',None,'ebc2'],'safeCount.clone')
    _program(indexed_type_leaf,['488bc1','4863ca','488b0cc8',None],'safeCount.indexedTypeLeaf')
    if _target(clone[11],0xe8)!=int(indexed_type_leaf[0]['va'],16):raise ValueError('safeCount.indexed-type-entry')
    if _target(indexed_type_leaf[3],0xe9)!=_target(canonical[15],0xe8):raise ValueError('safeCount.type-resolution-target')
    if _target(canonical[8],0xe8)!=_target(clone[25],0xe8):raise ValueError('safeCount.context-initializer')
    if _target(canonical[19],0xe8)!=_target(clone[18],0xe9):raise ValueError('safeCount.dispatch-call-tail-target')
    for rows,edges in ((canonical,[(6,9),(10,13),(12,20)]),(clone,[(6,24),(8,19),(26,7)])):
        for branch,target in edges:
            if control_transfer(rows[branch]).get('target')!=int(rows[target]['va'],16):raise ValueError('safeCount.local-control-target')
    return dict(nullCollectionReturnsZero=True,nonNullCollectionAndSlotZeroArgumentsPreserved=True,
        completeProgramsCompared=True,canonicalDispatchVa=canonical[19]['va'],cloneDispatchVa=clone[18]['va'],
        evidenceBoundary='conditional',condition='Matched incoming collection and MethodInfo, stable valid disjoint storage, original ABI-preserving initialization/type-resolution/dispatch calls with no caller return-address observation. Both return the same Int32 from the same slot-zero dispatch. Live generic/interface binding and Count implementation meaning remain separate.')
