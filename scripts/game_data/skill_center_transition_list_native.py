"""Transition append fast-path mutation and pre-Start sorting requests.

Resize and sorting internals are opaque. No priority ordering, tie stability,
closed runtime context or lasting live collection identity is inferred.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from scripts.common import check_installed_native_inputs
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols,validate_claims
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data import skill_center_transition_storage_native as storage
from scripts.game_data import skill_center_dispatch_native as dispatch

SCHEMA='endfield.skill-center-transition-list-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-transition-list-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_transition_list_native.json'


def _rules():
    return dict(physicalStateAdderToAppendCallProved=True,appendVersionIncrementBeforeItemsNullGuard=True,
        appendVersionWrapsBits32=True,appendFastCapacityComparisonUnsigned32=True,
        appendSizeStoreBeforeSecondBoundsCheck=True,appendFastStoresOriginalItemAtOldIndex=True,
        appendFastBitmapPreservesItemAndArrayCarriers=True,appendFastMutationSelectorPhysicalReadJoinProved=True,
        resizeCanonicalCalleeIdentityProved=True,resizeEffectsRequired=True,
        startSortRequestPrecedesRunningWriteAndEnterRequests=True,
        sortAllRequestsStateSortForEachExplicitYield=True,stateSortForwardsSameListToCanonicalListSort=True,
        listSortPassesZeroIndexReadCountAndNullComparer=True,
        compareSignedPriorityReturnsMinusOneZeroOrOne=True,compareOtherPriorityReadOnce=True,
        compareThisPriorityRereadOnNonLessBranch=True,normalWin64ReturnsRequired=True,
        validNonoverlappingLayoutRequired=True,bitmapNormalCompletionRequired=True,
        noConcurrentInterferenceForOrdinaryAppendRequired=True,opaqueSortAndEnumerationEffectsRequired=True,
        resizeImplementationProved=False,actualPriorityOrderProved=False,tieStabilityProved=False,
        dynamicDefaultComparerSelectionProved=False,runtimeRgctxProved=False,
        persistentCollectionIdentityProved=False,objectLifetimeProved=False,captureExecutionProved=False)


def _registrations(image,rows):
    expected={
        'start':('Beyond.Gameplay.StateMachine`2','Start',['System.Int32Enum','object'],0),
        'sortAll':('Beyond.Gameplay.StateMachine`2','_SortAllTransitions',['System.Int32Enum','object'],0),
        'stateSort':('Beyond.Gameplay.FSMState`1','SortTransitions',['System.Int32Enum'],0),
        'listSort':('System.Collections.Generic.List`1','Sort',['object'],0),
        'compare':('Beyond.Gameplay.FSMTransition`1','CompareTo',['System.Int32Enum'],1),
        'resize':('System.Collections.Generic.List`1','AddWithResize',['object'],1)}
    _require(len(rows)==len(expected) and {r['id']for r in rows}==set(expected),'transitionList.registration-coverage',list(expected),rows)
    pe=image.pe;md=image.metadata;reg=image.registration
    code=image.mapper.code_registration_summary(pe,image.code_registration);out={}
    for r in rows:
        role=r['id'];owner,name,args,count=expected[role];ti,si,pi=r['tableIndex'],r['methodSpecIndex'],r['pointerIndex']
        _require(all(type(x)is int and x>=0 for x in (ti,si,pi)) and ti<reg['genericMethodTableCount'] and si<reg['methodSpecsCount'] and pi<code['genericMethodPointersCount'],'transitionList.registration-bounds',role,r)
        row=struct.unpack('<iiii',pe.bytes_at_va(int(reg['genericMethodTable'],16)+ti*16,16))
        _require(row[:2]==(si,pi),'transitionList.registration-row',(si,pi),row)
        mi,ci,method_inst=struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+si*12,12))
        _require(0<=mi<len(md.methods) and ci>=0 and method_inst==-1,'transitionList.method-spec','class-only generic method',(mi,ci,method_inst))
        m=md.methods[mi];td=image.named_types[owner]
        _require(td.method_start<=mi<td.method_start+td.method_count and mi==r['methodIndex'] and md.string(m.name_index)==name and len(md.parameters_for(m))==count and not m.flags&16,'transitionList.method-identity',(owner,name,count),r)
        actual_args=[runtime_type_name(pe,md,a.type_pointer_va)for a in image.instantiations.resolve(ci).arguments]
        entry=pe.u64_at_va(int(code['genericMethodPointers'],16)+pi*8)-pe.image_base
        _require(actual_args==args==r['classArguments'] and entry==r['entryRva'],'transitionList.compiled-binding',r,dict(entryRva=entry,classArguments=actual_args))
        if role=='compare':_require(m.slot==4,'transitionList.compare-declared-slot',4,m.slot)
        out[role]=dict(r,entryRva=entry)
    return out


def _semantic_operands(c,grammar):
    op=c['operands'];stride=op['contextStride']
    _require(stride==8,'transitionList.pointer-stride','Win64 pointer stride',stride)
    def v(role,i):return op[grammar[role][i][2]]
    def eq(role,indices,wanted,label):
        got=[v(role,i)for i in indices]
        _require(all(x==wanted for x in got),'transitionList.semantic-'+label,wanted,got)
    for key,indices in [('listVersionOffset',[6]),('listItemsOffset',[8]),('listSizeOffset',[10,33]),('arrayLengthOffset',[14,34]),('arrayDataOffset',[37])]:eq('append',indices,op[key],'append-'+key)
    eq('append',[32],1,'append-size-increment')
    eq('append',[39],op['arrayDataOffset']//stride,'append-bitmap-slot')
    _require(op['arrayDataOffset']%stride==0,'transitionList.array-data-alignment','pointer aligned',op['arrayDataOffset'])
    for role,indices in [('append',[16,21,25]),('stateSort',[7,12,22]),('start',[3,10,31]),('sortAll',[12,17,24,40,45,50,63,69]),('listSort',[4,11,17,31,37])]:eq(role,indices,op['methodInfoClassOffset'],role+'-method-info-class')
    for role,indices in [('append',[17,22,28]),('stateSort',[8,14,23]),('start',[6,12,32]),('sortAll',[13,20,31,41,47,52,64,70]),('listSort',[7,13,21,32,38])]:eq(role,indices,op['rgctxOffset'],role+'-rgctx')
    for role,indices in [('append',[19]),('stateSort',[10]),('start',[8]),('sortAll',[15,43]),('listSort',[9,15])]:eq(role,indices,op['initializerOffset'],role+'-initializer')
    for role,indices,slot,label in [('append',[18,23,29],11,'resize'),('stateSort',[9,15,24],5,'list-sort'),('start',[7,13,33],6,'sort-all'),('sortAll',[14,21,65],32,'enumerator'),('sortAll',[32,53],38,'move-next'),('sortAll',[42,48,71],37,'state-sort'),('listSort',[8,33],14,'count'),('listSort',[14,22,39],49,'sort-range')]:eq(role,indices,slot*stride,role+'-context-'+label)
    eq('stateSort',[3],op['stateTransitionsOffset'],'state-sort-list')
    eq('sortAll',[3],op['dictionaryOffset'],'sort-all-states')
    eq('start',[15],op['blackboardOffset'],'start-blackboard')
    eq('start',[16],op['runningOffset'],'start-running')
    eq('start',[21,23],op['currentOffset'],'start-current')
    eq('start',[19,24],4,'start-enter-slot')
    eq('listSort',[12],op['listSizeOffset'],'list-sort-count')
    eq('listSort',[24],4*stride,'list-sort-fifth-argument')
    eq('compare',[4,5,8],op['transitionPriorityOffset'],'compare-priority')
    eq('compare',[12],(1<<32)-1,'compare-minus-one')
    eq('compare',[10],v('compare',0),'compare-frame-restore')
    # Known push counts and ABI entry homes, rather than build-locked frames.
    frames=[('append',5,57,3,[(0,55),(1,56)],4*stride),
            ('stateSort',2,17,1,[(0,16)],4*stride),('start',2,28,1,[(0,27)],4*stride),
            ('sortAll',2,58,1,[(0,57)],4*stride),('listSort',3,28,1,[(0,26),(1,27)],5*stride)]
    for role,alloc,restore,pushes,saves,minimum in frames:
        frame=v(role,alloc);delta=frame+pushes*stride
        _require(frame>=minimum and frame%(2*stride)==0,'transitionList.semantic-'+role+'-frame','aligned Win64 frame',frame)
        eq(role,[restore],frame,role+'-frame-restore')
        for save,load in saves:eq(role,[load],v(role,save)+delta,role+'-saved-register-'+str(save))
    # Dictionary enumerator sret has 40 bytes copied from temporary+0x28 to
    # the stable loop carrier; this proves the physical value-slot schedule,
    # not Dictionary traversal semantics or the opaque helper's output.
    base=v('sortAll',25);temp=v('sortAll',18)
    eq('sortAll',[23],temp,'enumerator-copy-source-low')
    eq('sortAll',[26],temp+2*stride,'enumerator-copy-source-mid')
    eq('sortAll',[28],temp+4*stride,'enumerator-copy-source-high')
    eq('sortAll',[27],base,'enumerator-copy-target-low')
    eq('sortAll',[30],base+2*stride,'enumerator-copy-target-mid')
    eq('sortAll',[29],base+4*stride,'enumerator-copy-target-high')
    eq('sortAll',[5],base+4*stride,'enumerator-initial-clear')
    eq('sortAll',[8],base,'enumerator-initial-low-clear')
    eq('sortAll',[9],base+2*stride,'enumerator-initial-mid-clear')
    eq('sortAll',[51],base,'enumerator-next-carrier')
    eq('sortAll',[37],base+3*stride,'enumerator-yielded-value-slot')


def _programs(c):
    _require(all(type(x)is int and x>=0 for x in c['operands'].values()),'transitionList.operand-types','nonnegative integer operands',c['operands'])
    grammar={'append': [['48895c24', 'operand', 'appendDisplacement0', 1, ''],
            ['48896c24', 'operand', 'appendDisplacement1', 1, ''], '56', '57', '4156',
            ['4883ec', 'operand', 'appendImmediate5', 1, ''],
            ['ff41', 'operand', 'appendDisplacement6', 1, ''], '498be8',
            ['488b79', 'operand', 'appendDisplacement8', 1, ''], '4c8bf2',
            ['486359', 'operand', 'appendDisplacement10', 1, ''], '488bf1', '4885ff',
            ['0f84', 'relative', '13', 4, ''], ['3b5f', 'operand', 'appendDisplacement14', 1, ''],
            ['72', 'relative', '15', 1, ''], ['498b40', 'operand', 'appendDisplacement16', 1, ''],
            ['488b88', 'operand', 'appendDisplacement17', 4, ''],
            ['488b41', 'operand', 'appendDisplacement18', 1, ''],
            ['488378', 'operand', 'appendDisplacement19', 1, '00'], ['75', 'relative', '20', 1, ''],
            ['498b40', 'operand', 'appendDisplacement21', 1, ''],
            ['488b88', 'operand', 'appendDisplacement22', 4, ''],
            ['488b41', 'operand', 'appendDisplacement23', 1, ''], 'ff10',
            ['488b45', 'operand', 'appendDisplacement25', 1, ''], '498bd6', '488bce',
            ['4c8b80', 'operand', 'appendDisplacement28', 4, ''],
            ['4d8b40', 'operand', 'appendDisplacement29', 1, ''], ['e8', 'relative', '30', 4, ''],
            ['eb', 'relative', '31', 1, ''], ['8d43', 'operand', 'appendDisplacement32', 1, ''],
            ['8941', 'operand', 'appendDisplacement33', 1, ''],
            ['3b5f', 'operand', 'appendDisplacement34', 1, ''], ['73', 'relative', '35', 1, ''],
            ['833d', 'operand', 'appendDisplacement36', 4, '00'],
            ['4c8974df', 'operand', 'appendDisplacement37', 1, ''], ['74', 'relative', '38', 1, ''],
            ['488d43', 'operand', 'appendDisplacement39', 1, ''], '4c8d04c7',
            ['49c1e8', 'operand', 'appendImmediate41', 1, ''],
            ['488d0d', 'operand', 'appendDisplacement42', 4, ''],
            ['4181e0', 'operand', 'appendImmediate43', 4, ''], '418bc0',
            ['48c1e8', 'operand', 'appendImmediate45', 1, ''],
            ['4183e0', 'operand', 'appendImmediate46', 1, ''], '488d14c1', '0f0d0a',
            ['0f1f40', 'operand', 'appendDisplacement49', 1, ''], '488b02', '488bc8', '4c0fabc1',
            'f0480fb10a', ['75', 'relative', '54', 1, ''],
            ['488b5c24', 'operand', 'appendDisplacement55', 1, ''],
            ['488b6c24', 'operand', 'appendDisplacement56', 1, ''],
            ['4883c4', 'operand', 'appendImmediate57', 1, ''], '415e', '5f', '5e', 'c3',
            ['e8', 'relative', '62', 4, ''], 'cc', ['e8', 'relative', '64', 4, ''], 'cc'],
 'compare': [['4883ec', 'operand', 'compareImmediate0', 1, ''], '4c8bc1', '4885d2',
             ['74', 'relative', '3', 1, ''], ['8b4a', 'operand', 'compareDisplacement4', 1, ''],
             ['413948', 'operand', 'compareDisplacement5', 1, ''], ['7c', 'relative', '6', 1, ''],
             '33c0', ['413948', 'operand', 'compareDisplacement8', 1, ''], '0f9fc0',
             ['4883c4', 'operand', 'compareImmediate10', 1, ''], 'c3',
             ['b8', 'operand', 'compareImmediate12', 4, ''], ['eb', 'relative', '13', 1, ''],
             ['e8', 'relative', '14', 4, ''], 'cc'],
 'listSort': [['48895c24', 'operand', 'listSortDisplacement0', 1, ''],
              ['48897424', 'operand', 'listSortDisplacement1', 1, ''], '57',
              ['4883ec', 'operand', 'listSortImmediate3', 1, ''],
              ['488b42', 'operand', 'listSortDisplacement4', 1, ''], '488bda', '488bf9',
              ['488b90', 'operand', 'listSortDisplacement7', 4, ''],
              ['488b42', 'operand', 'listSortDisplacement8', 1, ''],
              ['488378', 'operand', 'listSortDisplacement9', 1, '00'],
              ['0f84', 'relative', '10', 4, ''],
              ['488b43', 'operand', 'listSortDisplacement11', 1, ''],
              ['8b77', 'operand', 'listSortDisplacement12', 1, ''],
              ['488b88', 'operand', 'listSortDisplacement13', 4, ''],
              ['488b81', 'operand', 'listSortDisplacement14', 4, ''],
              ['488378', 'operand', 'listSortDisplacement15', 1, '00'],
              ['0f84', 'relative', '16', 4, ''],
              ['488b43', 'operand', 'listSortDisplacement17', 1, ''], '4533c9', '448bc6', '33d2',
              ['488b88', 'operand', 'listSortDisplacement21', 4, ''],
              ['488b81', 'operand', 'listSortDisplacement22', 4, ''], '488bcf',
              ['48894424', 'operand', 'listSortDisplacement24', 1, ''],
              ['e8', 'relative', '25', 4, ''],
              ['488b5c24', 'operand', 'listSortDisplacement26', 1, ''],
              ['488b7424', 'operand', 'listSortDisplacement27', 1, ''],
              ['4883c4', 'operand', 'listSortImmediate28', 1, ''], '5f', 'c3',
              ['488b43', 'operand', 'listSortDisplacement31', 1, ''],
              ['488b90', 'operand', 'listSortDisplacement32', 4, ''],
              ['488b42', 'operand', 'listSortDisplacement33', 1, ''], 'ff10', '90',
              ['e9', 'relative', '36', 4, ''],
              ['488b43', 'operand', 'listSortDisplacement37', 1, ''],
              ['488b88', 'operand', 'listSortDisplacement38', 4, ''],
              ['488b81', 'operand', 'listSortDisplacement39', 4, ''], 'ff10', '90',
              ['e9', 'relative', '42', 4, '']],
 'sortAll': [['48895c24', 'operand', 'sortAllDisplacement0', 1, ''], '57',
             ['4883ec', 'operand', 'sortAllImmediate2', 1, ''],
             ['488b79', 'operand', 'sortAllDisplacement3', 1, ''], '33c0',
             ['48894424', 'operand', 'sortAllDisplacement5', 1, ''], '0f57c0', '488bda',
             ['0f114424', 'operand', 'sortAllDisplacement8', 1, ''],
             ['0f114424', 'operand', 'sortAllDisplacement9', 1, ''], '4885ff',
             ['0f84', 'relative', '11', 4, ''],
             ['488b42', 'operand', 'sortAllDisplacement12', 1, ''],
             ['488b88', 'operand', 'sortAllDisplacement13', 4, ''],
             ['488b81', 'operand', 'sortAllDisplacement14', 4, ''],
             ['488378', 'operand', 'sortAllDisplacement15', 1, '00'],
             ['0f84', 'relative', '16', 4, ''],
             ['488b43', 'operand', 'sortAllDisplacement17', 1, ''],
             ['488d4c24', 'operand', 'sortAllDisplacement18', 1, ''], '488bd7',
             ['4c8b80', 'operand', 'sortAllDisplacement20', 4, ''],
             ['4d8b80', 'operand', 'sortAllDisplacement21', 4, ''], ['e8', 'relative', '22', 4, ''],
             ['0f104424', 'operand', 'sortAllDisplacement23', 1, ''],
             ['488b43', 'operand', 'sortAllDisplacement24', 1, ''],
             ['488d4c24', 'operand', 'sortAllDisplacement25', 1, ''],
             ['0f104c24', 'operand', 'sortAllDisplacement26', 1, ''],
             ['0f114424', 'operand', 'sortAllDisplacement27', 1, ''],
             ['f20f104424', 'operand', 'sortAllDisplacement28', 1, ''],
             ['f20f114424', 'operand', 'sortAllDisplacement29', 1, ''],
             ['0f114c24', 'operand', 'sortAllDisplacement30', 1, ''],
             ['488b90', 'operand', 'sortAllDisplacement31', 4, ''],
             ['488b92', 'operand', 'sortAllDisplacement32', 4, ''], ['e8', 'relative', '33', 4, ''],
             '84c0', ['74', 'relative', '35', 1, ''],
             ['660f1f4400', 'operand', 'sortAllDisplacement36', 1, ''],
             ['488b7c24', 'operand', 'sortAllDisplacement37', 1, ''], '4885ff',
             ['74', 'relative', '39', 1, ''], ['488b43', 'operand', 'sortAllDisplacement40', 1, ''],
             ['488b90', 'operand', 'sortAllDisplacement41', 4, ''],
             ['488b82', 'operand', 'sortAllDisplacement42', 4, ''],
             ['488378', 'operand', 'sortAllDisplacement43', 1, '00'],
             ['0f84', 'relative', '44', 4, ''],
             ['488b43', 'operand', 'sortAllDisplacement45', 1, ''], '488bcf',
             ['488b90', 'operand', 'sortAllDisplacement47', 4, ''],
             ['488b92', 'operand', 'sortAllDisplacement48', 4, ''], ['e8', 'relative', '49', 4, ''],
             ['488b43', 'operand', 'sortAllDisplacement50', 1, ''],
             ['488d4c24', 'operand', 'sortAllDisplacement51', 1, ''],
             ['488b90', 'operand', 'sortAllDisplacement52', 4, ''],
             ['488b92', 'operand', 'sortAllDisplacement53', 4, ''], ['e8', 'relative', '54', 4, ''],
             '84c0', ['75', 'relative', '56', 1, ''],
             ['488b9c24', 'operand', 'sortAllDisplacement57', 4, ''],
             ['4883c4', 'operand', 'sortAllImmediate58', 1, ''], '5f', 'c3',
             ['e8', 'relative', '61', 4, ''], 'cc',
             ['488b42', 'operand', 'sortAllDisplacement63', 1, ''],
             ['488b88', 'operand', 'sortAllDisplacement64', 4, ''],
             ['488b81', 'operand', 'sortAllDisplacement65', 4, ''], 'ff10', '90',
             ['e9', 'relative', '68', 4, ''], ['488b43', 'operand', 'sortAllDisplacement69', 1, ''],
             ['488b90', 'operand', 'sortAllDisplacement70', 4, ''],
             ['488b82', 'operand', 'sortAllDisplacement71', 4, ''], 'ff10', '90',
             ['e9', 'relative', '74', 4, '']],
 'start': [['48895c24', 'operand', 'startDisplacement0', 1, ''], '57',
           ['4883ec', 'operand', 'startImmediate2', 1, ''],
           ['488b42', 'operand', 'startDisplacement3', 1, ''], '488bd9', '488bfa',
           ['488b88', 'operand', 'startDisplacement6', 4, ''],
           ['488b41', 'operand', 'startDisplacement7', 1, ''],
           ['488378', 'operand', 'startDisplacement8', 1, '00'], ['0f84', 'relative', '9', 4, ''],
           ['488b47', 'operand', 'startDisplacement10', 1, ''], '488bcb',
           ['488b90', 'operand', 'startDisplacement12', 4, ''],
           ['488b52', 'operand', 'startDisplacement13', 1, ''], ['e8', 'relative', '14', 4, ''],
           ['488b53', 'operand', 'startDisplacement15', 1, ''],
           ['c643', 'operand', 'startDisplacement16', 1, '01'], '4885d2',
           ['74', 'relative', '18', 1, ''], ['b9', 'operand', 'startImmediate19', 4, ''],
           ['e8', 'relative', '20', 4, ''], ['48837b', 'operand', 'startDisplacement21', 1, '00'],
           ['74', 'relative', '22', 1, ''], ['488b53', 'operand', 'startDisplacement23', 1, ''],
           ['b9', 'operand', 'startImmediate24', 4, ''], '4533c0', ['e8', 'relative', '26', 4, ''],
           ['488b5c24', 'operand', 'startDisplacement27', 1, ''],
           ['4883c4', 'operand', 'startImmediate28', 1, ''], '5f', 'c3',
           ['488b42', 'operand', 'startDisplacement31', 1, ''],
           ['488b88', 'operand', 'startDisplacement32', 4, ''],
           ['488b41', 'operand', 'startDisplacement33', 1, ''], 'ff10', '90',
           ['e9', 'relative', '36', 4, '']],
 'stateSort': [['48895c24', 'operand', 'stateSortDisplacement0', 1, ''], '57',
               ['4883ec', 'operand', 'stateSortImmediate2', 1, ''],
               ['488b79', 'operand', 'stateSortDisplacement3', 1, ''], '488bda', '4885ff',
               ['74', 'relative', '6', 1, ''],
               ['488b42', 'operand', 'stateSortDisplacement7', 1, ''],
               ['488b90', 'operand', 'stateSortDisplacement8', 4, ''],
               ['488b42', 'operand', 'stateSortDisplacement9', 1, ''],
               ['488378', 'operand', 'stateSortDisplacement10', 1, '00'],
               ['0f84', 'relative', '11', 4, ''],
               ['488b43', 'operand', 'stateSortDisplacement12', 1, ''], '488bcf',
               ['488b90', 'operand', 'stateSortDisplacement14', 4, ''],
               ['488b52', 'operand', 'stateSortDisplacement15', 1, ''],
               ['488b5c24', 'operand', 'stateSortDisplacement16', 1, ''],
               ['4883c4', 'operand', 'stateSortImmediate17', 1, ''], '5f',
               ['e9', 'relative', '19', 4, ''], ['e8', 'relative', '20', 4, ''], 'cc',
               ['488b43', 'operand', 'stateSortDisplacement22', 1, ''],
               ['488b90', 'operand', 'stateSortDisplacement23', 4, ''],
               ['488b42', 'operand', 'stateSortDisplacement24', 1, ''], 'ff10', '90',
               ['e9', 'relative', '27', 4, '']]}
    edges={'append': {13: 62, 15: 32, 20: 25, 31: 55, 35: 64, 38: 55, 54: 50},
 'compare': {3: 14, 6: 12, 13: 10},
 'listSort': {10: 31, 16: 37, 36: 11, 42: 17},
 'sortAll': {11: 61, 16: 63, 35: 57, 39: 61, 44: 69, 56: 37, 68: 17, 74: 45},
 'start': {9: 31, 18: 21, 22: 27, 36: 10},
 'stateSort': {6: 20, 11: 22, 19: 'external', 27: 12}}
    _semantic_operands(c,grammar)
    _require(set(c['programs'])==set(grammar),'transitionList.program-coverage',list(grammar),list(c['programs']))
    for role,patterns in grammar.items():
        p=c['programs'][role];rows=p['instructions'];indices={r['rva']:i for i,r in enumerate(rows)}
        _require(len(rows)==len(patterns) and len(indices)==len(rows),'transitionList.instruction-count',role,len(rows))
        _require(p['entry']==rows[0]['rva'],'transitionList.program-entry',role,p['entry'])
        seen_edges={};seen_refs=set()
        for i,(r,pattern)in enumerate(zip(rows,patterns)):
            raw=bytes.fromhex(r['hex'])
            if isinstance(pattern,str):
                _require(raw.hex()==pattern,'transitionList.opcode-'+role+'-'+str(i),pattern,r);continue
            left,kind,key,n,right=pattern;a=len(bytes.fromhex(left))
            _require(len(raw)==a+n+len(bytes.fromhex(right)) and raw[:a].hex()==left and raw[a+n:].hex()==right,'transitionList.opcode-'+role+'-'+str(i),pattern,r)
            value=int.from_bytes(raw[a:a+n],'little',signed=kind=='relative')
            if kind=='relative':
                target=r['rva']+len(raw)+value;seen_refs.add(key)
                _require(target==p['references'][key],'transitionList.relative-'+role+'-'+key,p['references'][key],target)
                if i in edges[role]:
                    expected=edges[role][i]
                    if expected=='external':
                        _require(target not in indices,'transitionList.external-tail',role,target);seen_edges[i]='external'
                    else:
                        _require(target in indices,'transitionList.internal-edge',role,target);seen_edges[i]=indices[target]
            else:_require(value==c['operands'][key],'transitionList.operand-'+key,c['operands'][key],value)
        _require(seen_edges==edges[role] and seen_refs==set(p['references']),'transitionList.branch-topology',edges[role],seen_edges)
    roles={r['id']:r for r in c['registrations']}
    for role in ('start','sortAll','stateSort','listSort','compare'):_require(c['programs'][role]['entry']==roles[role]['entryRva'],'transitionList.registered-entry',role,c['programs'][role]['entry'])
    for owner,i,target in [('append',30,'resize'),('start',14,'sortAll'),('sortAll',49,'stateSort'),('stateSort',19,'listSort')]:
        _require(c['programs'][owner]['references'][str(i)]==roles[target]['entryRva'],'transitionList.interprocedural-call',target,c['programs'][owner]['references'][str(i)])
    refs=c['programs']['sortAll']['references']
    _require(refs['33']==refs['54'],'transitionList.same-move-next','same physical helper',refs)
    return _rules()


def _validate_dependencies(image,c):
    path=CONTRACTS_DIR/c['dependencies']['storage']
    _require(path==storage.CONTRACT_PATH,'transitionList.storage-path',storage.CONTRACT_PATH,path)
    source,digest=read_reviewed_contract(path,schema=storage.SCHEMA,status='reviewed',label='transitionList.storage')
    _require(source['nativeInputs']==c['nativeInputs'],'transitionList.storage-native-inputs',c['nativeInputs'],source['nativeInputs'])
    _,nested=storage._validate(image,source)
    _require(source['programs']['state']['references']['49']==c['programs']['append']['entry'],'transitionList.state-adder-append-call','validated physical insertion request',c['programs']['append']['entry'])
    reader_path=CONTRACTS_DIR/c['dependencies']['dispatch']
    _require(reader_path==dispatch.CONTRACT_PATH,'transitionList.dispatch-path',dispatch.CONTRACT_PATH,reader_path)
    reader,reader_digest=read_reviewed_contract(reader_path,schema=dispatch.SCHEMA,status='reviewed',label='transitionList.dispatch')
    # storage._validate already authenticates this exact dependency. A bookend
    # before using its fields prevents a time-of-check/time-of-use substitution.
    validated={p:d for p,d in nested}
    _require(validated.get(reader_path)==reader_digest,'transitionList.validated-dispatch-bookend','same validated dependency',reader_path)
    _require(reader['nativeInputs']==c['nativeInputs'],'transitionList.dispatch-native-inputs',c['nativeInputs'],reader['nativeInputs'])
    for key in ('methodInfoClassOffset','rgctxOffset','initializerOffset','listVersionOffset','listSizeOffset','listItemsOffset','arrayLengthOffset','arrayDataOffset','stateTransitionsOffset','dictionaryOffset','runningOffset','blackboardOffset','currentOffset'):
        _require(c['operands'][key]==reader['operands'][key],'transitionList.selector-reader-offset-'+key,reader['operands'][key],c['operands'][key])
    _require(c['operands']['transitionPriorityOffset']==source['operands']['transitionPriorityOffset'],'transitionList.priority-writer-offset',source['operands']['transitionPriorityOffset'],c['operands']['transitionPriorityOffset'])
    _require(c['programs']['start']['references']['26']==reader['operands']['virtualEnumRva'],'transitionList.start-enter-helper',reader['operands']['virtualEnumRva'],c['programs']['start']['references']['26'])
    return [(path,digest),*nested]


def _validate(image,c):
    roles=_registrations(image,c['registrations']);_programs(c)
    image.check_windows(c['codeWindows'],label='transitionList')
    for role,p in c['programs'].items():
        family=image.unwind_index.family(p['entry']);windows=[w for w in c['codeWindows']if w['owner']==role]
        _require([[w['startRva'],w['endRva']]for w in windows]==[r['runtimeTriple'][:2]for r in family['ranges']],'transitionList.complete-family',role,windows)
        covered=[]
        for w in windows:
            selected=[r for r in p['instructions']if w['startRva']<=r['rva']<w['endRva']];cursor=w['startRva'];body=b''
            for r in selected:
                _require(r['rva']==cursor,'transitionList.contiguous-body',cursor,r['rva'])
                raw=bytes.fromhex(r['hex']);body+=raw;cursor+=len(raw);covered.append(r['rva'])
            _require(cursor==w['endRva'] and image.pe.bytes_at_va(image.pe.image_base+w['startRva'],len(body))==body,'transitionList.native-body',role,w)
        _require(covered==[r['rva']for r in p['instructions']],'transitionList.body-coverage',role,covered)
    context_roles={
        'Beyond.Gameplay.StateMachine`2':{6:('Beyond.Gameplay.StateMachine`2','_SortAllTransitions'),32:('System.Collections.Generic.Dictionary`2','GetEnumerator'),37:('Beyond.Gameplay.FSMState`1','SortTransitions'),38:('System.Collections.Generic.Dictionary`2+Enumerator','MoveNext')},
        'Beyond.Gameplay.FSMState`1':{5:('System.Collections.Generic.List`1','Sort')},
        'System.Collections.Generic.List`1':{11:('System.Collections.Generic.List`1','AddWithResize'),14:('System.Collections.Generic.List`1','get_Count'),49:('System.Collections.Generic.List`1','Sort')}}
    _require(len(c['contextClaims'])==3 and {r['typeName']for r in c['contextClaims']}==set(context_roles),'transitionList.context-coverage',list(context_roles),c['contextClaims'])
    symbols=ContextSymbols(image)
    for claim in c['contextClaims']:
        owner=claim['typeName'];expected=context_roles[owner];actual=symbols.context(image.named_types[owner].index,slots=sorted(expected))
        validate_claims(claim,actual,label='transitionList.staticContext')
        _require([(r['relativeSlot'],r['kind'],r['typeName'],r.get('methodName'))for r in actual['entries']]==[(i,3,*v)for i,v in expected.items()],'transitionList.context-role',expected,actual)
    return _rules(),_validate_dependencies(image,c)


def load_skill_center_transition_list(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='transitionList');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        rules,deps=_validate(open_native_image(gate.gameassembly,gate.metadata),c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','transitionList.native-bookend','unchanged native inputs',after.status)
        for source,expected in [(path,digest),*deps]:
            _require(hashlib.sha256(source.read_bytes()).hexdigest().upper()==expected,'transitionList.declaration-bookend',str(source),'changed')
        audit.update(status='validated-conditional-transition-list',detail='',nativeInputs=pins,evidenceBoundary=c['evidenceBoundary'],rules=rules,rows=[dict(id=key,evidence='conditional',rules=rules)for key in ('transitionFastAppend','startSortRequests','transitionPriorityCompare')])
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as e:
        detail=str(e)[:1600];audit.update(status='validation_failed',detail=detail,rules={},rows=[],failures=[dict(check=detail.split(':',1)[0],detail=detail)])
    return audit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('gameassembly','metadata'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_center_transition_list_native.json');a=p.parse_args(argv)
    _require(a.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()),'transitionList.output-root','reports/',a.output)
    r=load_skill_center_transition_list(gameassembly=a.gameassembly,metadata=a.metadata)
    if r['status']=='validated-conditional-transition-list':a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r));return 0 if r['status']=='validated-conditional-transition-list'else 2
if __name__=='__main__':raise SystemExit(main())
