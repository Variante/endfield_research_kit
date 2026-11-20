"""Conditional default comparer selection and canonical interface-call closure.

Runtime contexts, conversion/factory results and selected interface pointers
remain explicit premises. Sorting internals and actual comparer identity are
not proved. Only the first comparable CreateComparer branch is interpreted.
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
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,_type_pointer,_vtable
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data import skill_center_transition_list_native as list_native

SCHEMA='endfield.skill-center-default-comparer-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-default-comparer-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_default_comparer_native.json'


def _rules():
    return dict(listNullComparerToCanonicalSortHelperProved=True,
        nullComparerCallsCanonicalDefaultGetter=True,nonNullComparerSkipsDefaultGetter=True,
        nonNullCacheReturnsWithoutFactory=True,nullCacheCallsCanonicalFactory=True,
        factoryResultStoredThenBarrierRequested=True,getterReturnsSavedFactoryResultWithoutCacheReread=True,
        factoryNullResultCanBeStoredAndReturned=True,selectedComparableFactoryBranchProved=True,
        comparableBranchRequestsGenericComparerDefinition=True,comparablePredicateTrueRequired=True,
        runtimeTypeConversionAndFactoryResultsRequired=True,
        sortRequestsComparisonDelegateWithSelectedComparer=True,
        genericComparerCanonicalIdentityProved=True,genericCompareNullOrderingProved=True,
        genericCompareNonNullRequestsComparableSlotZero=True,interfaceFallbackPreservesReceiverOtherAndMethodInfo=True,
        interfaceFallbackReturnBits32Preserved=True,transitionDeclaredComparableInterfaceProved=True,
        canonicalTransitionComparePointerExcludesInlineCases=True,
        actualInterfaceTargetEqualsCanonicalTransitionCompareRequired=True,
        normalWin64ReturnsRequired=True,initializedRuntimeContextRequired=True,
        actualDefaultComparerTypeProved=False,sortComparisonDelegateEffectsProved=False,
        otherFactoryBranchesProved=False,sortAlgorithmProved=False,actualPriorityOrderProved=False,
        tieStabilityProved=False,liveInterfaceTargetProved=False,objectLifetimeProved=False,captureExecutionProved=False)


def _registrations(image,rows):
    expected={
        'range':('System.Collections.Generic.List`1','Sort',['object'],[],3,False),
        'array':('System.Array','Sort',[],['object'],4,True),
        'sortHelper':('System.Collections.Generic.ArraySortHelper`1','Sort',['object'],[],4,False),
        'default':('System.Collections.Generic.Comparer`1','get_Default',['object'],[],0,True),
        'factory':('System.Collections.Generic.Comparer`1','CreateComparer',['object'],[],0,True),
        'genericCompare':('System.Collections.Generic.GenericComparer`1','Compare',['object'],[],2,False)}
    _require(len(rows)==len(expected) and {r['id']for r in rows}==set(expected),'defaultComparer.registration-coverage',list(expected),rows)
    pe=image.pe;md=image.metadata;reg=image.registration;code=image.mapper.code_registration_summary(pe,image.code_registration);out={}
    for r in rows:
        role=r['id'];owner,name,args,margs,count,static=expected[role];ti,si,pi=r['tableIndex'],r['methodSpecIndex'],r['pointerIndex']
        _require(all(type(x)is int and x>=0 for x in (ti,si,pi)) and ti<reg['genericMethodTableCount'] and si<reg['methodSpecsCount'] and pi<code['genericMethodPointersCount'],'defaultComparer.registration-bounds',role,r)
        table=struct.unpack('<iiii',pe.bytes_at_va(int(reg['genericMethodTable'],16)+ti*16,16))
        _require(table[:2]==(si,pi),'defaultComparer.registration-row',(si,pi),table)
        mi,ci,ma=struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+si*12,12))
        _require(0<=mi<len(md.methods),'defaultComparer.method-index','bounded method',mi)
        m=md.methods[mi];td=image.named_types[owner]
        _require(td.method_start<=mi<td.method_start+td.method_count and mi==r['methodIndex'] and md.string(m.name_index)==name and len(md.parameters_for(m))==count and bool(m.flags&16)==static,'defaultComparer.method-identity',(owner,name,count,static),r)
        def arguments(index):return []if index<0 else[runtime_type_name(pe,md,a.type_pointer_va)for a in image.instantiations.resolve(index).arguments]
        actual_args,actual_margs=arguments(ci),arguments(ma);entry=pe.u64_at_va(int(code['genericMethodPointers'],16)+pi*8)-pe.image_base
        _require(actual_args==args==r['classArguments'] and actual_margs==margs==r['methodArguments'] and entry==r['entryRva'],'defaultComparer.compiled-binding',r,dict(entryRva=entry,classArguments=actual_args,methodArguments=actual_margs))
        out[role]=r
    return out


def _semantic(c,g):
    op=c['operands'];stride=op['contextStride'];_require(stride==8,'defaultComparer.pointer-stride','Win64 pointer stride',stride)
    def v(role,i):return op[g[role][i][2]]
    def eq(role,indices,wanted,label):
        got=[v(role,i)for i in indices];_require(all(x==wanted for x in got),'defaultComparer.semantic-'+label,wanted,got)
    for role,indices in [('range',[14]),('sortHelper',[15,21,30,35,49,55,80]),('default',[3,16,24,31]),('factory',[7,21,51]),('genericCompare',[9])]:eq(role,indices,op['methodInfoClassOffset'],role+'-method-info-class')
    for role,indices in [('range',[15]),('sortHelper',[16,23,31,36,51,56,81]),('default',[6,19,27,34]),('factory',[10,25,55]),('genericCompare',[11])]:eq(role,indices,op['rgctxOffset'],role+'-rgctx')
    for role,indices in [('array',[39]),('sortHelper',[33])]:eq(role,indices,op['initializerOffset'],role+'-initializer')
    for role,indices in [('array',[11,26,31,37,41])]:eq(role,indices,op['runtimeMethodContextOffset'],role+'-method-context')
    eq('range',[7],op['listSizeOffset'],'range-list-size');eq('range',[18],op['listItemsOffset'],'range-list-items');eq('range',[20],op['listVersionOffset'],'range-list-version')
    eq('array',[20],op['arrayLengthOffset'],'array-length')
    eq('default',[8,29,36],op['runtimeStaticFieldsOffset'],'default-static-fields')
    eq('default',[20],stride,'default-factory-context-slot')
    eq('array',[29],op['runtimeInitializedOffset'],'array-class-initialized')
    eq('sortHelper',[53],op['runtimeInitializedOffset'],'sort-helper-class-initialized')
    for role,indices,slot,label in [('range',[16],50,'array-sort'),('array',[38,45],3,'sort-helper'),('sortHelper',[32,37,82],5,'comparison-ctor'),('sortHelper',[57],6,'sort-algorithm'),('factory',[12],2,'type-parameter'),('factory',[26],3,'comparable-interface')]:eq(role,indices,slot*stride,role+'-context-'+label)
    for role,indices,slot,label in [('array',[27],1,'sort-helper-type'),('sortHelper',[22],4,'comparison-type'),('sortHelper',[38],3,'comparer-interface-type'),('sortHelper',[50],7,'sort-helper-owner'),('factory',[54],4,'comparer-cast-type'),('genericCompare',[10],1,'comparable-interface')]:eq(role,indices,slot,role+'-resolver-slot-'+label)
    eq('factory',[30],32,'factory-predicate-slot')
    eq('genericCompare',[25],1,'generic-compare-positive-null-order')
    for role,i in [('range',11),('array',24)]:eq(role,[i],1,role+'-nontrivial-count')
    frames=[('range',1,21,1,[],5),('array',5,53,3,[(0,51),(1,52),(13,50)],6),('sortHelper',7,69,3,[(0,65),(1,66),(2,67),(3,68)],5),('default',1,13,1,[(17,39)],4),('factory',3,63,1,[(0,61),(1,62),(15,60)],4),('genericCompare',2,19,1,[(0,18)],4),('interface',6,56,3,[(0,54),(1,52),(2,55)],4)]
    for role,alloc,restore,pushes,saves,outslots in frames:
        frame=v(role,alloc);delta=frame+pushes*stride
        _require(frame>=outslots*stride and frame%(2*stride)==0,'defaultComparer.semantic-'+role+'-frame','aligned outgoing-call frame',frame)
        eq(role,[restore],frame,role+'-frame-restore')
        for saved,loaded in saves:
            # default/factory saves occurring after prologue are already based
            # on the allocated stack; original entry home saves add delta.
            late=(role=='default' and saved==17)or(role=='factory'and saved==15)or(role=='array'and saved==13)
            eq(role,[loaded],v(role,saved)+(0 if late else delta),role+'-restore-'+str(saved))
    range_delta=v('range',1)+stride;eq('range',[13],range_delta+5*stride,'range-incoming-method-info');eq('range',[17],4*stride,'range-outgoing-array-method-info')
    array_delta=v('array',5)+3*stride;eq('array',[6],array_delta+5*stride,'array-incoming-method-info');eq('array',[47],5*stride,'array-outgoing-helper-method-info');eq('array',[48],4*stride,'array-outgoing-comparer')
    helper_delta=v('sortHelper',7)+3*stride;eq('sortHelper',[11,20,87,91,106],helper_delta+5*stride,'helper-incoming-comparer');eq('sortHelper',[12,110],helper_delta+6*stride,'helper-incoming-method-info');eq('sortHelper',[58],4*stride,'helper-outgoing-sort-context')
    eq('interface',[14],op['interfaceCountOffset'],'interface-count');eq('interface',[19,33],op['interfaceTableOffset'],'interface-table');eq('interface',[35],stride,'interface-pair-offset');eq('interface',[42],op['vtableMethodInfoOffset'],'interface-selected-method-info');eq('interface',[38],op['vtablePairBase'],'interface-vtable-base');eq('interface',[39],op['vtableStrideShift'],'interface-vtable-stride')
    _require(op['interfacePairStride']==2*stride and (1<<op['vtableStrideShift'])==2*stride,'defaultComparer.interface-pair-strides','two pointer-sized entries',op)


def _programs(c):
    _require(all(type(x)is int and x>=0 for x in c['operands'].values()),'defaultComparer.operand-types','nonnegative integer operands',c['operands'])
    grammar={'array': [['48895c24', 'operand', 'arrayDisplacement0', 1, ''],
           ['48896c24', 'operand', 'arrayDisplacement1', 1, ''], '56', '57', '4157',
           ['4883ec', 'operand', 'arrayImmediate5', 1, ''],
           ['488b7c24', 'operand', 'arrayDisplacement6', 1, ''], '4d8bf9', '418bd8', '8bf2',
           '488be9', ['48837f', 'operand', 'arrayDisplacement11', 1, '00'],
           ['0f84', 'relative', '12', 4, ''], ['4c897424', 'operand', 'arrayDisplacement13', 1, ''],
           '4885ed', ['0f84', 'relative', '15', 4, ''], '85f6', ['0f88', 'relative', '17', 4, ''],
           '85db', ['0f88', 'relative', '19', 4, ''],
           ['8b45', 'operand', 'arrayDisplacement20', 1, ''], '2bc6', '3bc3',
           ['0f8c', 'relative', '23', 4, ''], ['83fb', 'operand', 'arrayImmediate24', 1, ''],
           ['7e', 'relative', '25', 1, ''], ['488b4f', 'operand', 'arrayDisplacement26', 1, ''],
           ['ba', 'operand', 'arrayImmediate27', 4, ''], ['e8', 'relative', '28', 4, ''],
           ['83b8', 'operand', 'arrayDisplacement29', 4, '00'], ['74', 'relative', '30', 1, ''],
           ['488b4f', 'operand', 'arrayDisplacement31', 1, ''], '488b09',
           ['e8', 'relative', '33', 4, ''], '4c8bf0', '4885c0', ['74', 'relative', '36', 1, ''],
           ['488b4f', 'operand', 'arrayDisplacement37', 1, ''],
           ['488b51', 'operand', 'arrayDisplacement38', 1, ''],
           ['48837a', 'operand', 'arrayDisplacement39', 1, '00'], ['74', 'relative', '40', 1, ''],
           ['488b4f', 'operand', 'arrayDisplacement41', 1, ''], '448bcb', '448bc6', '488bd5',
           ['488b41', 'operand', 'arrayDisplacement45', 1, ''], '498bce',
           ['48894424', 'operand', 'arrayDisplacement47', 1, ''],
           ['4c897c24', 'operand', 'arrayDisplacement48', 1, ''], ['e8', 'relative', '49', 4, ''],
           ['4c8b7424', 'operand', 'arrayDisplacement50', 1, ''],
           ['488b5c24', 'operand', 'arrayDisplacement51', 1, ''],
           ['488b6c24', 'operand', 'arrayDisplacement52', 1, ''],
           ['4883c4', 'operand', 'arrayImmediate53', 1, ''], '415f', '5f', '5e', 'c3', '488bcf',
           ['e8', 'relative', '59', 4, ''], ['e9', 'relative', '60', 4, ''], '488bc8',
           ['e8', 'relative', '62', 4, ''], ['eb', 'relative', '63', 1, ''],
           ['e8', 'relative', '64', 4, ''], 'cc', 'ff12', ['eb', 'relative', '67', 1, ''],
           ['488d0d', 'operand', 'arrayDisplacement68', 4, ''], ['e8', 'relative', '69', 4, ''],
           '488bc8', ['e8', 'relative', '71', 4, ''], '488bd8', '4885c0',
           ['0f84', 'relative', '74', 4, ''], ['488d0d', 'operand', 'arrayDisplacement75', 4, ''],
           ['e8', 'relative', '76', 4, ''], '4533c0', '488bd0', '488bcb',
           ['e8', 'relative', '80', 4, ''], '488bd7',
           ['c743', 'operand', 'arrayDisplacement82', 1, '57000780'], '488bcb',
           ['e8', 'relative', '84', 4, ''], 'cc', '85db', ['78', 'relative', '87', 1, ''],
           ['488d0d', 'operand', 'arrayDisplacement88', 4, ''], ['eb', 'relative', '89', 1, ''],
           ['488d0d', 'operand', 'arrayDisplacement90', 4, ''], ['e8', 'relative', '91', 4, ''],
           '488bd8', ['488d0d', 'operand', 'arrayDisplacement93', 4, ''],
           ['e8', 'relative', '94', 4, ''], '488bc8', ['e8', 'relative', '96', 4, ''], '488bf0',
           '4885c0', ['0f84', 'relative', '99', 4, ''],
           ['488d0d', 'operand', 'arrayDisplacement100', 4, ''], ['e8', 'relative', '101', 4, ''],
           '4533c9', '4c8bc0', '488bd3', '488bce', ['e8', 'relative', '106', 4, ''], '488bd7',
           '488bce', ['e8', 'relative', '109', 4, ''], 'cc',
           ['488d0d', 'operand', 'arrayDisplacement111', 4, ''], ['e8', 'relative', '112', 4, ''],
           '488bc8', ['e8', 'relative', '114', 4, ''], '488bd8', '4885c0',
           ['0f84', 'relative', '117', 4, ''], ['488d0d', 'operand', 'arrayDisplacement118', 4, ''],
           ['e8', 'relative', '119', 4, ''], '4533c0', '488bd0', '488bcb',
           ['e8', 'relative', '123', 4, ''], '488bd7', '488bcb', ['e8', 'relative', '126', 4, ''],
           'cc'],
 'default': ['4057', ['4883ec', 'operand', 'defaultImmediate1', 1, ''], '488bf9',
             ['488b49', 'operand', 'defaultDisplacement3', 1, ''], ['e8', 'relative', '4', 4, ''],
             '33d2', ['488b88', 'operand', 'defaultDisplacement6', 4, ''],
             ['e8', 'relative', '7', 4, ''], ['488b80', 'operand', 'defaultDisplacement8', 4, ''],
             '488b00', ['f0830c24', 'operand', 'defaultImmediate10', 1, ''], '4885c0',
             ['74', 'relative', '12', 1, ''], ['4883c4', 'operand', 'defaultImmediate13', 1, ''],
             '5f', 'c3', ['488b4f', 'operand', 'defaultDisplacement16', 1, ''],
             ['48895c24', 'operand', 'defaultDisplacement17', 1, ''],
             ['e8', 'relative', '18', 4, ''], ['488b88', 'operand', 'defaultDisplacement19', 4, ''],
             ['488b49', 'operand', 'defaultDisplacement20', 1, ''], ['e8', 'relative', '21', 4, ''],
             '488bd8', ['f0830c24', 'operand', 'defaultImmediate23', 1, ''],
             ['488b4f', 'operand', 'defaultDisplacement24', 1, ''], ['e8', 'relative', '25', 4, ''],
             '33d2', ['488b88', 'operand', 'defaultDisplacement27', 4, ''],
             ['e8', 'relative', '28', 4, ''], ['488b88', 'operand', 'defaultDisplacement29', 4, ''],
             '488919', ['488b4f', 'operand', 'defaultDisplacement31', 1, ''],
             ['e8', 'relative', '32', 4, ''], '33d2',
             ['488b88', 'operand', 'defaultDisplacement34', 4, ''], ['e8', 'relative', '35', 4, ''],
             ['488b88', 'operand', 'defaultDisplacement36', 4, ''], ['e8', 'relative', '37', 4, ''],
             '488bc3', ['488b5c24', 'operand', 'defaultDisplacement39', 1, ''],
             ['eb', 'relative', '40', 1, '']],
 'factory': [['48895c24', 'operand', 'factoryDisplacement0', 1, ''],
             ['48897424', 'operand', 'factoryDisplacement1', 1, ''], '57',
             ['4883ec', 'operand', 'factoryImmediate3', 1, ''],
             ['803d', 'operand', 'factoryDisplacement4', 4, '00'], '488bf9',
             ['0f84', 'relative', '6', 4, ''], ['488b4f', 'operand', 'factoryDisplacement7', 1, ''],
             ['e8', 'relative', '8', 4, ''], ['488b0d', 'operand', 'factoryDisplacement9', 4, ''],
             ['488b98', 'operand', 'factoryDisplacement10', 4, ''],
             ['83b9', 'operand', 'factoryDisplacement11', 4, '00'],
             ['488b5b', 'operand', 'factoryDisplacement12', 1, ''],
             ['0f84', 'relative', '13', 4, ''], '33d2',
             ['48896c24', 'operand', 'factoryDisplacement15', 1, ''], '488bcb',
             ['e8', 'relative', '17', 4, ''], ['488b15', 'operand', 'factoryDisplacement18', 4, ''],
             '488bc8', ['e8', 'relative', '20', 4, ''],
             ['488b4f', 'operand', 'factoryDisplacement21', 1, ''], '488bf0',
             ['e8', 'relative', '23', 4, ''], '33d2',
             ['488b88', 'operand', 'factoryDisplacement25', 4, ''],
             ['488b49', 'operand', 'factoryDisplacement26', 1, ''], ['e8', 'relative', '27', 4, ''],
             '4885c0', ['0f84', 'relative', '29', 4, ''],
             ['b9', 'operand', 'factoryImmediate30', 4, ''], '4c8bc6', '488bd0',
             ['e8', 'relative', '33', 4, ''], '84c0', ['0f84', 'relative', '35', 4, ''],
             ['488b0d', 'operand', 'factoryDisplacement36', 4, ''],
             ['488b1d', 'operand', 'factoryDisplacement37', 4, ''],
             ['83b9', 'operand', 'factoryDisplacement38', 4, '00'],
             ['0f84', 'relative', '39', 4, ''], '33d2', '488bcb', ['e8', 'relative', '42', 4, ''],
             ['488b0d', 'operand', 'factoryDisplacement43', 4, ''], '488bd8',
             ['83b9', 'operand', 'factoryDisplacement45', 4, '00'],
             ['0f84', 'relative', '46', 4, ''], '4533c0', '488bd6', '488bcb',
             ['e8', 'relative', '50', 4, ''], ['488b4f', 'operand', 'factoryDisplacement51', 1, ''],
             '488bd8', ['e8', 'relative', '53', 4, ''],
             ['ba', 'operand', 'factoryImmediate54', 4, ''],
             ['488b88', 'operand', 'factoryDisplacement55', 4, ''], ['e8', 'relative', '56', 4, ''],
             '488bd0', '488bcb', ['e8', 'relative', '59', 4, ''],
             ['488b6c24', 'operand', 'factoryDisplacement60', 1, ''],
             ['488b5c24', 'operand', 'factoryDisplacement61', 1, ''],
             ['488b7424', 'operand', 'factoryDisplacement62', 1, ''],
             ['4883c4', 'operand', 'factoryImmediate63', 1, ''], '5f', 'c3',
             ['e8', 'relative', '66', 4, ''], 'cc',
             ['488d0d', 'operand', 'factoryDisplacement68', 4, ''], ['e8', 'relative', '69', 4, ''],
             ['488d0d', 'operand', 'factoryDisplacement70', 4, ''], ['e8', 'relative', '71', 4, ''],
             ['488d0d', 'operand', 'factoryDisplacement72', 4, ''], ['e8', 'relative', '73', 4, ''],
             ['488d0d', 'operand', 'factoryDisplacement74', 4, ''], ['e8', 'relative', '75', 4, ''],
             ['488d0d', 'operand', 'factoryDisplacement76', 4, ''], ['e8', 'relative', '77', 4, ''],
             ['488d0d', 'operand', 'factoryDisplacement78', 4, ''], ['e8', 'relative', '79', 4, ''],
             ['488d0d', 'operand', 'factoryDisplacement80', 4, ''], ['e8', 'relative', '81', 4, ''],
             ['c605', 'operand', 'factoryDisplacement82', 4, '01'], ['e9', 'relative', '83', 4, ''],
             ['e8', 'relative', '84', 4, ''], ['e9', 'relative', '85', 4, ''],
             ['e8', 'relative', '86', 4, ''], ['e9', 'relative', '87', 4, ''],
             ['e8', 'relative', '88', 4, ''], ['e9', 'relative', '89', 4, '']],
 'genericCompare': [['48895c24', 'operand', 'genericCompareDisplacement0', 1, ''], '57',
                    ['4883ec', 'operand', 'genericCompareImmediate2', 1, ''], '498bd8', '488bfa',
                    '4885d2', ['74', 'relative', '6', 1, ''], '4885db',
                    ['74', 'relative', '8', 1, ''],
                    ['498b49', 'operand', 'genericCompareDisplacement9', 1, ''],
                    ['ba', 'operand', 'genericCompareImmediate10', 4, ''],
                    ['488b89', 'operand', 'genericCompareDisplacement11', 4, ''],
                    ['e8', 'relative', '12', 4, ''], '488bd0', '33c9', '4c8bcb', '4c8bc7',
                    ['e8', 'relative', '17', 4, ''],
                    ['488b5c24', 'operand', 'genericCompareDisplacement18', 1, ''],
                    ['4883c4', 'operand', 'genericCompareImmediate19', 1, ''], '5f', 'c3', '48f7db',
                    '1bc0', ['eb', 'relative', '24', 1, ''],
                    ['b8', 'operand', 'genericCompareImmediate25', 4, ''],
                    ['eb', 'relative', '26', 1, '']],
 'interface': [['48895c24', 'operand', 'interfaceDisplacement0', 1, ''],
               ['48896c24', 'operand', 'interfaceDisplacement1', 1, ''],
               ['48897424', 'operand', 'interfaceDisplacement2', 1, ''], '57', '4156', '4157',
               ['4883ec', 'operand', 'interfaceImmediate6', 1, ''], '498b28', '498bf1', '440fb7f9',
               '4d8bf0', '488bcd', '488bfa', ['e8', 'relative', '13', 4, ''],
               ['440fb78d', 'operand', 'interfaceDisplacement14', 4, ''], '33db', '0fb7c3',
               '66413bd9', ['73', 'relative', '18', 1, ''],
               ['488b95', 'operand', 'interfaceDisplacement19', 4, ''], '0fb7c8', '4803c9',
               '48393cca', ['74', 'relative', '23', 1, ''], '66ffc0', '66413bc1',
               ['72', 'relative', '26', 1, ''], '450fb7c7', '488bd7', '498bce',
               ['e8', 'relative', '30', 4, ''], ['eb', 'relative', '31', 1, ''], '0fb7d0',
               ['488b85', 'operand', 'interfaceDisplacement33', 4, ''], '4803d2',
               ['8b44d0', 'operand', 'interfaceDisplacement35', 1, ''], '4103c7', '4898',
               ['4883c0', 'operand', 'interfaceImmediate38', 1, ''],
               ['48c1e0', 'operand', 'interfaceImmediate39', 1, ''], '4803c5', '4c8b08',
               ['4c8b40', 'operand', 'interfaceDisplacement42', 1, ''],
               ['488d05', 'operand', 'interfaceDisplacement43', 4, ''], '4c3bc8',
               ['75', 'relative', '45', 1, ''], '4885f6', ['74', 'relative', '47', 1, ''],
               ['b9', 'operand', 'interfaceImmediate48', 4, ''], '488bd6',
               ['e8', 'relative', '50', 4, ''], '8bd8',
               ['488b6c24', 'operand', 'interfaceDisplacement52', 1, ''], '8bc3',
               ['488b5c24', 'operand', 'interfaceDisplacement54', 1, ''],
               ['488b7424', 'operand', 'interfaceDisplacement55', 1, ''],
               ['4883c4', 'operand', 'interfaceImmediate56', 1, ''], '415f', '415e', '5f', 'c3',
               ['488d05', 'operand', 'interfaceDisplacement61', 4, ''], '4c3bc8',
               ['74', 'relative', '63', 1, ''],
               ['488d05', 'operand', 'interfaceDisplacement64', 4, ''], '4c3bc8',
               ['74', 'relative', '66', 1, ''], '488bd6', '498bce', '41ffd1',
               ['eb', 'relative', '70', 1, ''], '4885f6', ['75', 'relative', '72', 1, ''],
               ['e9', 'relative', '73', 4, ''], '33d2', '33c9', ['e8', 'relative', '76', 4, ''],
               'cc'],
 'range': ['4053', ['4883ec', 'operand', 'rangeImmediate1', 1, ''], '488bd9', '85d2',
           ['78', 'relative', '4', 1, ''], '4585c0', ['0f88', 'relative', '6', 4, ''],
           ['8b41', 'operand', 'rangeDisplacement7', 1, ''], '2bc2', '413bc0',
           ['0f8c', 'relative', '10', 4, ''], ['4183f8', 'operand', 'rangeImmediate11', 1, ''],
           ['7e', 'relative', '12', 1, ''], ['488b4424', 'operand', 'rangeDisplacement13', 1, ''],
           ['488b48', 'operand', 'rangeDisplacement14', 1, ''],
           ['488b81', 'operand', 'rangeDisplacement15', 4, ''],
           ['488b88', 'operand', 'rangeDisplacement16', 4, ''],
           ['48894c24', 'operand', 'rangeDisplacement17', 1, ''],
           ['488b4b', 'operand', 'rangeDisplacement18', 1, ''], ['e8', 'relative', '19', 4, ''],
           ['ff43', 'operand', 'rangeDisplacement20', 1, ''],
           ['4883c4', 'operand', 'rangeImmediate21', 1, ''], '5b', 'c3', '33c9',
           ['e8', 'relative', '25', 4, ''], 'cc', '33d2',
           ['b9', 'operand', 'rangeImmediate28', 4, ''], ['e8', 'relative', '29', 4, ''], 'cc',
           '4533c0', ['ba', 'operand', 'rangeImmediate32', 4, ''],
           ['b9', 'operand', 'rangeImmediate33', 4, ''], ['e8', 'relative', '34', 4, ''], 'cc'],
 'sortHelper': [['48895c24', 'operand', 'sortHelperDisplacement0', 1, ''],
                ['48897424', 'operand', 'sortHelperDisplacement1', 1, ''],
                ['48897c24', 'operand', 'sortHelperDisplacement2', 1, ''],
                ['4c896424', 'operand', 'sortHelperDisplacement3', 1, ''], '4155', '4156', '4157',
                ['4883ec', 'operand', 'sortHelperImmediate7', 1, ''], '458bf9', '458be0', '4c8bea',
                ['488bbc24', 'operand', 'sortHelperDisplacement11', 4, ''],
                ['488b9c24', 'operand', 'sortHelperDisplacement12', 4, ''], '4885ff',
                ['75', 'relative', '14', 1, ''],
                ['488b43', 'operand', 'sortHelperDisplacement15', 1, ''],
                ['488b88', 'operand', 'sortHelperDisplacement16', 4, ''], '488b09',
                ['e8', 'relative', '18', 4, ''], '488bf8',
                ['48898424', 'operand', 'sortHelperDisplacement20', 4, ''],
                ['488b4b', 'operand', 'sortHelperDisplacement21', 1, ''],
                ['ba', 'operand', 'sortHelperImmediate22', 4, ''],
                ['488b89', 'operand', 'sortHelperDisplacement23', 4, ''],
                ['e8', 'relative', '24', 4, ''], '488bc8', ['e8', 'relative', '26', 4, ''],
                '488bf0', '4885c0', ['0f84', 'relative', '29', 4, ''],
                ['488b43', 'operand', 'sortHelperDisplacement30', 1, ''],
                ['488b88', 'operand', 'sortHelperDisplacement31', 4, ''],
                ['488b41', 'operand', 'sortHelperDisplacement32', 1, ''],
                ['488378', 'operand', 'sortHelperDisplacement33', 1, '00'],
                ['0f84', 'relative', '34', 4, ''],
                ['488b43', 'operand', 'sortHelperDisplacement35', 1, ''],
                ['488b88', 'operand', 'sortHelperDisplacement36', 4, ''],
                ['4c8b71', 'operand', 'sortHelperDisplacement37', 1, ''],
                ['ba', 'operand', 'sortHelperImmediate38', 4, ''], ['e8', 'relative', '39', 4, ''],
                '33d2', '4c8bc0', '488bcf', ['e8', 'relative', '43', 4, ''], '4d8bce', '4c8bc0',
                '488bd7', '488bce', ['e8', 'relative', '48', 4, ''],
                ['488b4b', 'operand', 'sortHelperDisplacement49', 1, ''],
                ['ba', 'operand', 'sortHelperImmediate50', 4, ''],
                ['488b89', 'operand', 'sortHelperDisplacement51', 4, ''],
                ['e8', 'relative', '52', 4, ''],
                ['83b8', 'operand', 'sortHelperDisplacement53', 4, '00'],
                ['74', 'relative', '54', 1, ''],
                ['488b43', 'operand', 'sortHelperDisplacement55', 1, ''],
                ['488b88', 'operand', 'sortHelperDisplacement56', 4, ''],
                ['488b41', 'operand', 'sortHelperDisplacement57', 1, ''],
                ['48894424', 'operand', 'sortHelperDisplacement58', 1, ''], '4c8bce', '458bc7',
                '418bd4', '498bcd', ['e8', 'relative', '63', 4, ''], '90',
                ['488b5c24', 'operand', 'sortHelperDisplacement65', 1, ''],
                ['488b7424', 'operand', 'sortHelperDisplacement66', 1, ''],
                ['488b7c24', 'operand', 'sortHelperDisplacement67', 1, ''],
                ['4c8b6424', 'operand', 'sortHelperDisplacement68', 1, ''],
                ['4883c4', 'operand', 'sortHelperImmediate69', 1, ''], '415f', '415e', '415d', 'c3',
                ['e8', 'relative', '74', 4, ''], '90', '488bc8', ['e8', 'relative', '77', 4, ''],
                ['eb', 'relative', '78', 1, ''], 'cc',
                ['488b43', 'operand', 'sortHelperDisplacement80', 1, ''],
                ['488b88', 'operand', 'sortHelperDisplacement81', 4, ''],
                ['488b41', 'operand', 'sortHelperDisplacement82', 1, ''], 'ff10', '90',
                ['e9', 'relative', '85', 4, ''], '33d2',
                ['488b8c24', 'operand', 'sortHelperDisplacement87', 4, ''],
                ['e8', 'relative', '88', 4, ''], '90', ['e9', 'relative', '90', 4, ''],
                ['488b8c24', 'operand', 'sortHelperDisplacement91', 4, ''],
                ['e8', 'relative', '92', 4, ''], 'cc',
                ['488d0d', 'operand', 'sortHelperDisplacement94', 4, ''],
                ['e8', 'relative', '95', 4, ''], '488bc8', ['e8', 'relative', '97', 4, ''],
                '488bd8', '4885c0', ['75', 'relative', '100', 1, ''],
                ['e8', 'relative', '101', 4, ''], 'cc',
                ['488d0d', 'operand', 'sortHelperDisplacement103', 4, ''],
                ['e8', 'relative', '104', 4, ''], '4533c9',
                ['4c8b8424', 'operand', 'sortHelperDisplacement106', 4, ''], '488bd0', '488bcb',
                ['e8', 'relative', '109', 4, ''],
                ['488b9424', 'operand', 'sortHelperDisplacement110', 4, ''], '488bcb',
                ['e8', 'relative', '112', 4, ''], 'cc']}
    edges={'array': {12: 58,
           15: 111,
           17: 86,
           19: 90,
           23: 68,
           25: 50,
           30: 61,
           36: 64,
           40: 66,
           60: 13,
           63: 31,
           67: 41,
           74: 64,
           87: 90,
           89: 91,
           99: 64,
           117: 64},
 'default': {12: 16, 40: 13},
 'factory': {6: 68, 13: 84, 29: 66, 35: 'external', 39: 88, 46: 86, 83: 7, 85: 14, 87: 47, 89: 40},
 'genericCompare': {6: 22, 8: 25, 24: 18, 26: 18},
 'interface': {18: 27,
               23: 32,
               26: 20,
               31: 41,
               45: 61,
               47: 52,
               63: 71,
               66: 46,
               70: 51,
               72: 48,
               73: 74},
 'range': {4: 24, 6: 31, 10: 27, 12: 20},
 'sortHelper': {14: 21, 29: 74, 34: 80, 54: 76, 78: 55, 85: 35, 90: 65, 100: 103}}
    _semantic(c,grammar)
    _require(set(c['programs'])==set(grammar),'defaultComparer.program-coverage',list(grammar),list(c['programs']))
    for role,patterns in grammar.items():
        p=c['programs'][role];rows=p['instructions'];indices={r['rva']:i for i,r in enumerate(rows)}
        _require(len(rows)==len(patterns) and len(indices)==len(rows),'defaultComparer.instruction-count',role,len(rows));_require(p['entry']==rows[0]['rva'],'defaultComparer.program-entry',role,p['entry'])
        seen_edges={};seen_refs=set()
        for i,(r,pattern)in enumerate(zip(rows,patterns)):
            raw=bytes.fromhex(r['hex'])
            if isinstance(pattern,str):_require(raw.hex()==pattern,'defaultComparer.opcode-'+role+'-'+str(i),pattern,r);continue
            left,kind,key,n,right=pattern;a=len(bytes.fromhex(left))
            _require(len(raw)==a+n+len(bytes.fromhex(right)) and raw[:a].hex()==left and raw[a+n:].hex()==right,'defaultComparer.opcode-'+role+'-'+str(i),pattern,r)
            value=int.from_bytes(raw[a:a+n],'little',signed=kind=='relative')
            if kind=='relative':
                target=r['rva']+len(raw)+value;seen_refs.add(key);_require(target==p['references'][key],'defaultComparer.relative-'+role+'-'+key,p['references'][key],target)
                if i in edges[role]:
                    if edges[role][i]=='external':_require(target not in indices,'defaultComparer.external-edge',role,target);seen_edges[i]='external'
                    else:_require(target in indices,'defaultComparer.internal-edge',role,target);seen_edges[i]=indices[target]
            else:_require(value==c['operands'][key],'defaultComparer.operand-'+key,c['operands'][key],value)
        _require(seen_edges==edges[role] and seen_refs==set(p['references']),'defaultComparer.branch-topology',edges[role],seen_edges)
    roles={r['id']:r for r in c['registrations']}
    for role in roles:_require(c['programs'][role]['entry']==roles[role]['entryRva'],'defaultComparer.registered-entry',role,c['programs'][role]['entry'])
    for owner,i,target in [('range',19,'array'),('array',49,'sortHelper'),('sortHelper',18,'default'),('default',21,'factory'),('genericCompare',17,'interface')]:
        _require(c['programs'][owner]['references'][str(i)]==c['programs'][target]['entry'],'defaultComparer.interprocedural-call',target,c['programs'][owner]['references'][str(i)])
    t=c['thunk'];raw=bytes.fromhex(t['hex']);_require(len(raw)==7 and raw[:3]==bytes.fromhex('33d2e9') and t['rva']+len(raw)+int.from_bytes(raw[3:],'little',signed=True)==t['targetRva']==c['programs']['range']['entry'],'defaultComparer.index-zero-thunk','xor edx; jump to selected range body',t)
    return _rules()


def _validate_interface_and_usage(image,c,prior):
    usage=c['factoryUsage'];r=c['programs']['factory']['instructions'][37]
    _require((usage['instructionRva'],usage['instructionHex'].lower())==(r['rva'],r['hex']) and usage['typeName']=='System.Collections.Generic.GenericComparer`1' and usage['tag']==2,'defaultComparer.generic-definition-usage','selected comparable factory branch GenericComparer usage',usage)
    validate_typed_usage_context(image,usage,label='defaultComparer.genericDefinition')
    td=image.named_types['Beyond.Gameplay.FSMTransition`1'];row=c['transitionInterface'];section=image.metadata.sections['interfaceOffsets'];off=section.offset+td.interface_offsets_start*8
    pairs=list(struct.iter_unpack('<ii',image.metadata.buf[off:off+td.interface_offsets_count*8]))
    _require(pairs.count((row['interfaceTypeIndex'],row['interfaceOffset']))==1,'defaultComparer.transition-interface-row','one selected implemented interface',row)
    symbol=ContextSymbols(image).type(_type_pointer(image,row['interfaceTypeIndex'],'defaultComparer.interface'))
    _require(symbol['definition']['name']=='System.IComparable`1' and len(symbol['classArguments'])==1,'defaultComparer.transition-interface-definition','IComparable<T>',symbol)
    argument=symbol['classArguments'][0]
    _require(argument['definition']['name']=='Beyond.Gameplay.FSMTransition`1' and len(argument['classArguments'])==1 and argument['classArguments'][0]['parameterOwner']['typeName']=='Beyond.Gameplay.FSMTransition`1' and argument['classArguments'][0]['parameterOwner']['ordinal']==0,'defaultComparer.transition-interface-argument','FSMTransition own type parameter',argument)
    compared=next(r for r in prior['registrations']if r['id']=='compare')
    _vtable(image,td.index,row['interfaceOffset'],compared['methodIndex'],'defaultComparer.transitionCompare')
    _require(row['interfaceOffset']==4,'defaultComparer.transition-compare-slot','declared CompareTo slot4',row)
    rows=c['programs']['interface']['instructions'];targets=[]
    for i in (43,61,64):
        raw=bytes.fromhex(rows[i]['hex']);targets.append(rows[i]['rva']+len(raw)+int.from_bytes(raw[3:],'little',signed=True))
    _require(compared['entryRva']not in targets,'defaultComparer.canonical-compare-excludes-inline','selected canonical pointer reaches generic fallback',targets)


def _validate_contexts(image,c):
    td=image.named_types['System.Type'];declared=[m for m in image.metadata.methods_for(td)if image.metadata.string(m.name_index)=='IsAssignableFrom']
    _require(len(declared)==1 and declared[0].slot==32 and len(image.metadata.parameters_for(declared[0]))==1,'defaultComparer.assignability-slot','System.Type.IsAssignableFrom slot32 with one argument',[m.slot for m in declared])
    owners=['System.Collections.Generic.Comparer`1','System.Collections.Generic.ArraySortHelper`1','System.Collections.Generic.GenericComparer`1'];_require(len(c['contextClaims'])==3 and {r['typeName']for r in c['contextClaims']}==set(owners),'defaultComparer.context-coverage',owners,c['contextClaims'])
    symbols=ContextSymbols(image)
    for claim in c['contextClaims']:
        actual=symbols.context(image.named_types[claim['typeName']].index,slots=claim.get('selectedSlots'));validate_claims(claim,actual,label='defaultComparer.staticContext')
        indexed={r['relativeSlot']:r for r in actual['entries']};name=claim['typeName']
        methods=({'System.Collections.Generic.Comparer`1':{1:('System.Collections.Generic.Comparer`1','CreateComparer')},'System.Collections.Generic.ArraySortHelper`1':{0:('System.Collections.Generic.Comparer`1','get_Default'),2:('System.Collections.Generic.IComparer`1','Compare'),5:('System.Comparison`1','.ctor'),6:('System.Collections.Generic.ArraySortHelper`1','IntrospectiveSort')},'System.Collections.Generic.GenericComparer`1':{}})[name]
        for slot,wanted in methods.items():
            r=indexed[slot];_require((r['kind'],r['typeName'],r.get('methodName'))==(3,*wanted),'defaultComparer.context-method-role',wanted,r)
        if name=='System.Collections.Generic.GenericComparer`1':
            interface=indexed[1]['type'];_require(interface['definition']['name']=='System.IComparable`1' and interface['classArguments'][0]['parameterOwner']['typeName']==name and interface['classArguments'][0]['parameterOwner']['ordinal']==0,'defaultComparer.generic-comparable-context','IComparable of own T',interface)
        if name=='System.Collections.Generic.Comparer`1':
            interface=indexed[3]['type'];_require(interface['definition']['name']=='System.IComparable`1' and interface['classArguments'][0]['parameterOwner']['typeName']==name and interface['classArguments'][0]['parameterOwner']['ordinal']==0,'defaultComparer.factory-comparable-context','IComparable of own T',interface)


def _validate_dependencies(image,c):
    path=CONTRACTS_DIR/c['dependency'];_require(path==list_native.CONTRACT_PATH,'defaultComparer.dependency-path',list_native.CONTRACT_PATH,path)
    prior,digest=read_reviewed_contract(path,schema=list_native.SCHEMA,status='reviewed',label='defaultComparer.list')
    _require(prior['nativeInputs']==c['nativeInputs'],'defaultComparer.dependency-native-inputs',c['nativeInputs'],prior['nativeInputs'])
    _,nested=list_native._validate(image,prior)
    _require(prior['programs']['listSort']['references']['25']==c['thunk']['rva'],'defaultComparer.list-sort-null-comparer-call','validated prior null-comparer request',c['thunk']['rva'])
    for key in ('methodInfoClassOffset','rgctxOffset','initializerOffset','contextStride','listSizeOffset','listItemsOffset','listVersionOffset','arrayLengthOffset'):_require(c['operands'][key]==prior['operands'][key],'defaultComparer.physical-layout-'+key,prior['operands'][key],c['operands'][key])
    _validate_interface_and_usage(image,c,prior)
    return [(path,digest),*nested]


def _validate(image,c):
    _registrations(image,c['registrations']);_programs(c);image.check_windows(c['codeWindows'],label='defaultComparer')
    for role,p in c['programs'].items():
        windows=[w for w in c['codeWindows']if w['owner']==role];family=image.unwind_index.family(p['entry'])
        _require([[w['startRva'],w['endRva']]for w in windows]==[r['runtimeTriple'][:2]for r in family['ranges']],'defaultComparer.window-family',role,windows)
        for r in p['instructions']:
            raw=bytes.fromhex(r['hex']);_require(any(w['startRva']<=r['rva'] and r['rva']+len(raw)<=w['endRva']for w in windows)and image.pe.bytes_at_va(image.pe.image_base+r['rva'],len(raw))==raw,'defaultComparer.native-instruction',role,r)
        if role!='factory':
            for w in windows:
                cursor=w['startRva']
                for r in p['instructions']:
                    if w['startRva']<=r['rva']<w['endRva']:_require(cursor==r['rva'],'defaultComparer.complete-instruction-coverage',cursor,r['rva']);cursor+=len(bytes.fromhex(r['hex']))
                _require(cursor==w['endRva'],'defaultComparer.complete-range',w['endRva'],cursor)
    t=c['thunk'];_require(image.pe.bytes_at_va(image.pe.image_base+t['rva'],len(bytes.fromhex(t['hex'])))==bytes.fromhex(t['hex']),'defaultComparer.native-thunk',t,'byte drift')
    _validate_contexts(image,c)
    return _rules(),_validate_dependencies(image,c)


def load_skill_center_default_comparer(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='defaultComparer');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        rules,deps=_validate(open_native_image(gate.gameassembly,gate.metadata),c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','defaultComparer.native-bookend','unchanged native inputs',after.status)
        for source,expected in [(path,digest),*deps]:_require(hashlib.sha256(source.read_bytes()).hexdigest().upper()==expected,'defaultComparer.declaration-bookend',str(source),'changed')
        audit.update(status='validated-conditional-default-comparer',detail='',nativeInputs=pins,evidenceBoundary=c['evidenceBoundary'],rules=rules,rows=[dict(id=key,evidence='conditional',rules=rules)for key in ('defaultComparerCacheAndFactory','genericComparerComparableFallback')])
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as e:
        detail=str(e)[:1600];audit.update(status='validation_failed',detail=detail,rules={},rows=[],failures=[dict(check=detail.split(':',1)[0],detail=detail)])
    return audit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('gameassembly','metadata'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_center_default_comparer_native.json');a=p.parse_args(argv)
    _require(a.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()),'defaultComparer.output-root','reports/',a.output)
    r=load_skill_center_default_comparer(gameassembly=a.gameassembly,metadata=a.metadata)
    if r['status']=='validated-conditional-default-comparer':a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r));return 0 if r['status']=='validated-conditional-default-comparer'else 2
if __name__=='__main__':raise SystemExit(main())
