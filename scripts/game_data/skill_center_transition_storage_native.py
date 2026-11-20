"""Canonical AddTransition carrier/storage proof, conditional on opaque helpers.

Validates typed constructor callers, full selected shared machine/state schedules,
and matching executor/condition physical offsets. Runtime contexts, collections,
allocation type, object lifetime and actual selected callbacks remain unresolved.
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
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols, validate_claims
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data import skill_center_transition_construction_native as construction
from scripts.game_data import skill_center_dispatch_native as dispatch

SCHEMA='endfield.skill-center-transition-storage-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-transition-storage-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_transition_storage_native.json'


def _rules():
    return dict(canonicalMachineAdderIdentityProved=True,canonicalStateAdderIdentityProved=True,
        constructionRequestCalleeJoinProved=True,selectedNormalSchedulesProved=True,
        containsAndLookupResultsIndependent=True,statesReloadedBeforeEachDictionaryRequest=True,
        fromLookupResultPassedAsStateReceiver=True,toLookupResultPassedAsTarget=True,
        priorityBits32AndConditionCarrierPreserved=True,transitionWritesFromToPriorityChecker=True,
        stateListReadAfterAllWriteBarriers=True,machineTransitionMapReadAfterStateAdder=True,
        machineSetItemUsesOriginalToId=True,physicalExecutorFromToReadJoinProved=True,
        physicalConditionCheckerReadJoinProved=True,normalWin64ReturnsRequired=True,
        opaqueHelperEffectsRequired=True,staticContextDeclarationsProved=True,
        runtimeRgctxProved=False,allocatorNominalTypeProved=False,dictionaryImplementationProved=False,
        collectionInsertionEffectsProved=False,liveTransitionSelectionProved=False,
        objectLifetimeProved=False,captureWriterAttributed=False)


def _registrations(image,rows):
    expected={
        'machine':('Beyond.Gameplay.StateMachine`2','AddTransition',['System.Int32Enum','object'],4),
        'state':('Beyond.Gameplay.FSMState`1','AddTransition',['System.Int32Enum'],3),
        'contains':('System.Collections.Generic.Dictionary`2','ContainsKey',['System.Int32Enum','object'],1),
        'lookup':('System.Collections.Generic.Dictionary`2','get_Item',['System.Int32Enum','object'],1),
        'setItem':('System.Collections.Generic.Dictionary`2','set_Item',['System.Int32Enum','object'],2)}
    _require(len(rows)==len(expected) and {r['id']for r in rows}==set(expected),'transitionStorage.registration-coverage',list(expected),rows)
    pe=image.pe;md=image.metadata;reg=image.registration
    code=image.mapper.code_registration_summary(pe,image.code_registration);out={}
    for r in rows:
        role=r['id'];owner,name,args,count=expected[role]
        ti,si,pi=r['tableIndex'],r['methodSpecIndex'],r['pointerIndex']
        _require(all(type(x)is int and x>=0 for x in (ti,si,pi)) and ti<reg['genericMethodTableCount'] and si<reg['methodSpecsCount'] and pi<code['genericMethodPointersCount'],'transitionStorage.registration-bounds',role,r)
        table=struct.unpack('<iiii',pe.bytes_at_va(int(reg['genericMethodTable'],16)+ti*16,16))
        _require(table[:2]==(si,pi),'transitionStorage.registration-row',(si,pi),table)
        mi,ci,method_inst=struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+si*12,12))
        _require(0<=mi<len(md.methods) and ci>=0 and method_inst==-1,'transitionStorage.method-spec','class-only generic method',(mi,ci,method_inst))
        m=md.methods[mi];td=image.named_types[owner]
        _require(td.method_start<=mi<td.method_start+td.method_count and mi==r['methodIndex'] and md.string(m.name_index)==name and len(md.parameters_for(m))==count and not m.flags&16,'transitionStorage.method-identity',(owner,name,count),r)
        actual_args=[runtime_type_name(pe,md,a.type_pointer_va)for a in image.instantiations.resolve(ci).arguments]
        entry=pe.u64_at_va(int(code['genericMethodPointers'],16)+pi*8)-pe.image_base
        _require(actual_args==args==r['classArguments'] and entry==r['entryRva'],'transitionStorage.compiled-binding',r,dict(entryRva=entry,classArguments=actual_args))
        out[role]=dict(r,entryRva=entry)
    return out


def _semantic_operands(c,grammar):
    """Prove ABI stack origins, context slots and nonvolatile restore equations."""
    op=c['operands'];stride=op['contextStride']
    _require(stride==8,'transitionStorage.context-stride','Win64 pointer stride',stride)
    def value(role,i):return op[grammar[role][i][2]]
    def equal(role,indices,expected,label):
        actual=[value(role,i)for i in indices]
        _require(all(v==expected for v in actual),'transitionStorage.semantic-'+label,expected,actual)
    class_loads={'machine':[15,20,31,36,47,52,62,67,76,81,94,99,118,124,130,139,149,158],
                 'state':[13,21,39,44,61,67]}
    context_loads={'machine':[16,23,32,39,48,55,63,70,77,85,95,103,119,125,131,140,151,160],
                   'state':[14,22,40,47,62,68]}
    for role in ('machine','state'):
        equal(role,class_loads[role],op['methodInfoClassOffset'],role+'-method-info-class')
        equal(role,context_loads[role],op['rgctxOffset'],role+'-rgctx')
    equal('machine',[18,34,50,65,79,97],op['initializerOffset'],'machine-initializer')
    equal('state',[24,42],op['initializerOffset'],'state-initializer')
    for indices,slot,label in [([17,24,33,40,120,126],26,'contains'),
                              ([49,56,64,71,132],27,'lookup'),
                              ([78,86,141],30,'state-adder'),
                              ([96,104],31,'set-item'),([152,161],29,'diagnostic')]:
        equal('machine',indices,slot*stride,'machine-context-'+label)
    equal('state',[23,63],3*stride,'state-context-constructor')
    equal('state',[41,48,69],4*stride,'state-context-list-add')
    equal('state',[11],2,'state-allocation-context-index')
    # Three explicit pushes in both finite grammars precede local allocation.
    # Win64 entry stack has return address + four home slots. Arguments 5/6
    # therefore originate at +40/+48, independent of this build's frame size.
    for role,restore_indices,minimum in [('machine',[106,107,108],5*stride),
                                        ('state',[52,50,53],4*stride)]:
        frame=value(role,6);delta=frame+3*stride
        _require(frame>=minimum and frame%(2*stride)==0,'transitionStorage.semantic-'+role+'-frame','aligned outgoing-call frame',frame)
        equal(role,[109 if role=='machine' else 54],frame,role+'-frame-restore')
        saved=[value(role,i)for i in (0,1,2)]
        _require(saved==[stride,2*stride,3*stride],'transitionStorage.semantic-'+role+'-save-homes','three distinct Win64 home slots',saved)
        actual=[value(role,i)for i in restore_indices]
        _require(actual==[delta+x for x in saved],'transitionStorage.semantic-'+role+'-register-restores',[delta+x for x in saved],actual)
        equal(role,[14 if role=='machine' else 7],delta+(6 if role=='machine' else 5)*stride,role+'-incoming-method-info')
        if role=='machine':
            equal(role,[83],delta+5*stride,'machine-incoming-condition')
            equal(role,[88],4*stride,'machine-outgoing-state-method-info')


def _programs(c):
    # The opcode/register grammar is code. Addresses, fields and stack operands
    # are declarations; all are authenticated against the selected native pair.
    _require(all(type(v)is int and v>=0 for v in c['operands'].values()),'transitionStorage.operand-types','nonnegative integer physical operands',c['operands'])
    grammar={'machine': [['48895c24', 'operand', 'machineDisplacement0', 1, ''],
             ['48896c24', 'operand', 'machineDisplacement1', 1, ''],
             ['48897424', 'operand', 'machineDisplacement2', 1, ''], '57', '4156', '4157',
             ['4883ec', 'operand', 'machineImmediate6', 1, ''],
             ['488b71', 'operand', 'machineStatesOffset', 1, ''], '458bf9', '418be8', '448bf2',
             '488bf9', '4885f6', ['0f84', 'relative', '13', 4, ''],
             ['488b5c24', 'operand', 'machineDisplacement14', 1, ''],
             ['488b43', 'operand', 'machineDisplacement15', 1, ''],
             ['4c8b90', 'operand', 'machineDisplacement16', 4, ''],
             ['498b82', 'operand', 'machineDisplacement17', 4, ''],
             ['488378', 'operand', 'machineDisplacement18', 1, '00'],
             ['0f84', 'relative', '19', 4, ''],
             ['488b43', 'operand', 'machineDisplacement20', 1, ''], '418bd6', '488bce',
             ['4c8b80', 'operand', 'machineDisplacement23', 4, ''],
             ['4d8b80', 'operand', 'machineDisplacement24', 4, ''], ['e8', 'relative', '25', 4, ''],
             '84c0', ['0f84', 'relative', '27', 4, ''],
             ['488b77', 'operand', 'machineStatesOffset', 1, ''], '4885f6',
             ['0f84', 'relative', '30', 4, ''],
             ['488b43', 'operand', 'machineDisplacement31', 1, ''],
             ['488b90', 'operand', 'machineDisplacement32', 4, ''],
             ['488b82', 'operand', 'machineDisplacement33', 4, ''],
             ['488378', 'operand', 'machineDisplacement34', 1, '00'],
             ['0f84', 'relative', '35', 4, ''],
             ['488b43', 'operand', 'machineDisplacement36', 1, ''], '8bd5', '488bce',
             ['4c8b80', 'operand', 'machineDisplacement39', 4, ''],
             ['4d8b80', 'operand', 'machineDisplacement40', 4, ''], ['e8', 'relative', '41', 4, ''],
             '84c0', ['0f84', 'relative', '43', 4, ''],
             ['488b77', 'operand', 'machineStatesOffset', 1, ''], '4885f6',
             ['0f84', 'relative', '46', 4, ''],
             ['488b43', 'operand', 'machineDisplacement47', 1, ''],
             ['488b90', 'operand', 'machineDisplacement48', 4, ''],
             ['488b82', 'operand', 'machineDisplacement49', 4, ''],
             ['488378', 'operand', 'machineDisplacement50', 1, '00'],
             ['0f84', 'relative', '51', 4, ''],
             ['488b43', 'operand', 'machineDisplacement52', 1, ''], '418bd6', '488bce',
             ['4c8b80', 'operand', 'machineDisplacement55', 4, ''],
             ['4d8b80', 'operand', 'machineDisplacement56', 4, ''], ['e8', 'relative', '57', 4, ''],
             ['488b77', 'operand', 'machineStatesOffset', 1, ''], '4c8bf0', '4885f6',
             ['0f84', 'relative', '61', 4, ''],
             ['488b4b', 'operand', 'machineDisplacement62', 1, ''],
             ['488b91', 'operand', 'machineDisplacement63', 4, ''],
             ['4c8b82', 'operand', 'machineDisplacement64', 4, ''],
             ['498378', 'operand', 'machineDisplacement65', 1, '00'],
             ['0f84', 'relative', '66', 4, ''],
             ['488b43', 'operand', 'machineDisplacement67', 1, ''], '8bd5', '488bce',
             ['4c8b80', 'operand', 'machineDisplacement70', 4, ''],
             ['4d8b80', 'operand', 'machineDisplacement71', 4, ''], ['e8', 'relative', '72', 4, ''],
             '488bf0', '4d85f6', ['0f84', 'relative', '75', 4, ''],
             ['488b4b', 'operand', 'machineDisplacement76', 1, ''],
             ['488b91', 'operand', 'machineDisplacement77', 4, ''],
             ['488b8a', 'operand', 'machineDisplacement78', 4, ''],
             ['488379', 'operand', 'machineDisplacement79', 1, '00'],
             ['0f84', 'relative', '80', 4, ''],
             ['488b43', 'operand', 'machineDisplacement81', 1, ''], '458bc7',
             ['4c8b4c24', 'operand', 'machineDisplacement83', 1, ''], '488bd6',
             ['488b88', 'operand', 'machineDisplacement85', 4, ''],
             ['488b81', 'operand', 'machineDisplacement86', 4, ''], '498bce',
             ['48894424', 'operand', 'machineDisplacement88', 1, ''],
             ['e8', 'relative', '89', 4, ''],
             ['488b7f', 'operand', 'machineTransitionsOffset', 1, ''], '488bf0', '4885ff',
             ['74', 'relative', '93', 1, ''], ['488b4b', 'operand', 'machineDisplacement94', 1, ''],
             ['488b91', 'operand', 'machineDisplacement95', 4, ''],
             ['4c8b82', 'operand', 'machineDisplacement96', 4, ''],
             ['498378', 'operand', 'machineDisplacement97', 1, '00'],
             ['74', 'relative', '98', 1, ''], ['488b43', 'operand', 'machineDisplacement99', 1, ''],
             '4c8bc6', '8bd5', '488bcf', ['4c8b88', 'operand', 'machineDisplacement103', 4, ''],
             ['4d8b89', 'operand', 'machineDisplacement104', 4, ''],
             ['e8', 'relative', '105', 4, ''],
             ['488b5c24', 'operand', 'machineDisplacement106', 1, ''],
             ['488b6c24', 'operand', 'machineDisplacement107', 1, ''],
             ['488b7424', 'operand', 'machineDisplacement108', 1, ''],
             ['4883c4', 'operand', 'machineImmediate109', 1, ''], '415f', '415e', '5f', 'c3',
             ['e8', 'relative', '114', 4, ''], 'cc', '41ff10', ['eb', 'relative', '117', 1, ''],
             ['488b43', 'operand', 'machineDisplacement118', 1, ''],
             ['488b90', 'operand', 'machineDisplacement119', 4, ''],
             ['488b82', 'operand', 'machineDisplacement120', 4, ''], 'ff10', '90',
             ['e9', 'relative', '123', 4, ''],
             ['488b43', 'operand', 'machineDisplacement124', 1, ''],
             ['488b90', 'operand', 'machineDisplacement125', 4, ''],
             ['488b82', 'operand', 'machineDisplacement126', 4, ''], 'ff10', '90',
             ['e9', 'relative', '129', 4, ''],
             ['488b43', 'operand', 'machineDisplacement130', 1, ''],
             ['488b90', 'operand', 'machineDisplacement131', 4, ''],
             ['488b82', 'operand', 'machineDisplacement132', 4, ''], 'ff10', '90',
             ['e9', 'relative', '135', 4, ''], '41ff10', '90', ['e9', 'relative', '138', 4, ''],
             ['488b4b', 'operand', 'machineDisplacement139', 1, ''],
             ['488b91', 'operand', 'machineDisplacement140', 4, ''],
             ['488b8a', 'operand', 'machineDisplacement141', 4, ''], 'ff11', '90',
             ['e9', 'relative', '144', 4, ''],
             ['488b0d', 'operand', 'machineDisplacement145', 4, ''],
             ['83b9', 'operand', 'machineDisplacement146', 4, '00'],
             ['75', 'relative', '147', 1, ''], ['e8', 'relative', '148', 4, ''],
             ['488b43', 'operand', 'machineDisplacement149', 1, ''], '448bc5',
             ['4c8b88', 'operand', 'machineDisplacement151', 4, ''],
             ['4d8b89', 'operand', 'machineDisplacement152', 4, ''],
             ['eb', 'relative', '153', 1, ''],
             ['488b0d', 'operand', 'machineDisplacement154', 4, ''],
             ['83b9', 'operand', 'machineDisplacement155', 4, '00'],
             ['75', 'relative', '156', 1, ''], ['e8', 'relative', '157', 4, ''],
             ['488b43', 'operand', 'machineDisplacement158', 1, ''], '458bc6',
             ['4c8b88', 'operand', 'machineDisplacement160', 4, ''],
             ['4d8b89', 'operand', 'machineDisplacement161', 4, ''],
             ['488b15', 'operand', 'machineDisplacement162', 4, ''],
             ['b1', 'operand', 'machineImmediate163', 1, ''], ['e8', 'relative', '164', 4, ''],
             '90', ['e9', 'relative', '166', 4, '']],
 'state': [['48895c24', 'operand', 'stateDisplacement0', 1, ''],
           ['48896c24', 'operand', 'stateDisplacement1', 1, ''],
           ['48897424', 'operand', 'stateDisplacement2', 1, ''], '57', '4156', '4157',
           ['4883ec', 'operand', 'stateImmediate6', 1, ''],
           ['488b7c24', 'operand', 'stateDisplacement7', 1, ''], '488bf1', '4c8bfa', '498be9',
           ['ba', 'operand', 'stateImmediate11', 4, ''], '458bf0',
           ['488b4f', 'operand', 'stateDisplacement13', 1, ''],
           ['488b89', 'operand', 'stateDisplacement14', 4, ''], ['e8', 'relative', '15', 4, ''],
           '488bc8', ['e8', 'relative', '17', 4, ''], '488bd8', '4885c0',
           ['0f84', 'relative', '20', 4, ''], ['488b47', 'operand', 'stateDisplacement21', 1, ''],
           ['488b88', 'operand', 'stateDisplacement22', 4, ''],
           ['488b41', 'operand', 'stateDisplacement23', 1, ''],
           ['488378', 'operand', 'stateDisplacement24', 1, '00'], ['0f84', 'relative', '25', 4, ''],
           ['488d4b', 'operand', 'transitionFromOffset', 1, ''],
           ['488973', 'operand', 'transitionFromOffset', 1, ''], ['e8', 'relative', '28', 4, ''],
           ['488d4b', 'operand', 'transitionToOffset', 1, ''],
           ['4c897b', 'operand', 'transitionToOffset', 1, ''], ['e8', 'relative', '31', 4, ''],
           ['488d4b', 'operand', 'checkerOffset', 1, ''],
           ['448973', 'operand', 'transitionPriorityOffset', 1, ''],
           ['48896b', 'operand', 'checkerOffset', 1, ''], ['e8', 'relative', '35', 4, ''],
           ['488b76', 'operand', 'stateTransitionsOffset', 1, ''], '4885f6',
           ['74', 'relative', '38', 1, ''], ['488b47', 'operand', 'stateDisplacement39', 1, ''],
           ['488b90', 'operand', 'stateDisplacement40', 4, ''],
           ['488b42', 'operand', 'stateDisplacement41', 1, ''],
           ['488378', 'operand', 'stateDisplacement42', 1, '00'], ['0f84', 'relative', '43', 4, ''],
           ['488b47', 'operand', 'stateDisplacement44', 1, ''], '488bd3', '488bce',
           ['4c8b80', 'operand', 'stateDisplacement47', 4, ''],
           ['4d8b40', 'operand', 'stateDisplacement48', 1, ''], ['e8', 'relative', '49', 4, ''],
           ['488b6c24', 'operand', 'stateDisplacement50', 1, ''], '488bc3',
           ['488b5c24', 'operand', 'stateDisplacement52', 1, ''],
           ['488b7424', 'operand', 'stateDisplacement53', 1, ''],
           ['4883c4', 'operand', 'stateImmediate54', 1, ''], '415f', '415e', '5f', 'c3',
           ['e8', 'relative', '59', 4, ''], 'cc',
           ['488b47', 'operand', 'stateDisplacement61', 1, ''],
           ['488b88', 'operand', 'stateDisplacement62', 4, ''],
           ['488b41', 'operand', 'stateDisplacement63', 1, ''], 'ff10', '90',
           ['e9', 'relative', '66', 4, ''], ['488b47', 'operand', 'stateDisplacement67', 1, ''],
           ['488b90', 'operand', 'stateDisplacement68', 4, ''],
           ['488b42', 'operand', 'stateDisplacement69', 1, ''], 'ff10', '90',
           ['e9', 'relative', '72', 4, '']]}
    edges={'machine': {13: 114,
             19: 118,
             27: 154,
             30: 114,
             35: 124,
             43: 145,
             46: 114,
             51: 130,
             61: 114,
             66: 136,
             75: 114,
             80: 139,
             93: 114,
             98: 116,
             117: 99,
             123: 20,
             129: 36,
             135: 52,
             138: 67,
             144: 81,
             147: 149,
             153: 162,
             156: 158,
             166: 106},
 'state': {20: 59, 25: 61, 38: 59, 43: 67, 66: 26, 72: 44}}
    _semantic_operands(c,grammar)
    _require(set(c['programs'])==set(grammar),'transitionStorage.program-coverage',list(grammar),list(c['programs']))
    for role,patterns in grammar.items():
        p=c['programs'][role];rows=p['instructions'];indices={r['rva']:i for i,r in enumerate(rows)}
        _require(len(rows)==len(patterns) and len(indices)==len(rows),'transitionStorage.instruction-count',role,len(rows))
        _require(p['entry']==rows[0]['rva'],'transitionStorage.program-entry',role,p['entry'])
        seen_edges={};seen_refs=set()
        for i,(r,pattern)in enumerate(zip(rows,patterns)):
            raw=bytes.fromhex(r['hex'])
            if isinstance(pattern,str):
                _require(raw.hex()==pattern,'transitionStorage.opcode-'+role+'-'+str(i),pattern,r)
                continue
            left,kind,key,n,right=pattern;a=len(bytes.fromhex(left))
            _require(len(raw)==a+n+len(bytes.fromhex(right)) and raw[:a].hex()==left and raw[a+n:].hex()==right,'transitionStorage.opcode-'+role+'-'+str(i),pattern,r)
            value=int.from_bytes(raw[a:a+n],'little',signed=kind=='relative')
            if kind=='relative':
                target=r['rva']+len(raw)+value;seen_refs.add(key)
                _require(target==p['references'][key],'transitionStorage.relative-'+role+'-'+key,p['references'][key],target)
                if i in edges[role]:
                    _require(target in indices,'transitionStorage.internal-edge',role,target)
                    seen_edges[i]=indices[target]
            else:_require(value==c['operands'][key],'transitionStorage.operand-'+key,c['operands'][key],value)
        _require(seen_edges==edges[role] and seen_refs==set(p['references']),'transitionStorage.branch-topology',edges[role],seen_edges)
    roles={r['id']:r for r in c['registrations']}
    for role in ('machine','state'):_require(c['programs'][role]['entry']==roles[role]['entryRva'],'transitionStorage.registered-entry',role,c['programs'][role]['entry'])
    p=c['programs']['machine']['references']
    for indices,role in [([25,41],'contains'),([57,72],'lookup'),([89],'state'),([105],'setItem')]:
        for i in indices:_require(p[str(i)]==roles[role]['entryRva'],'transitionStorage.interprocedural-call',role,p[str(i)])
    refs=c['programs']['state']['references']
    _require(refs['28']==refs['31']==refs['35'],'transitionStorage.same-write-barrier','same physical barrier callee',refs)
    return _rules()


def _validate(image,c):
    roles=_registrations(image,c['registrations']);_programs(c)
    image.check_windows(c['codeWindows'],label='transitionStorage')
    for role in ('machine','state'):
        p=c['programs'][role];family=image.unwind_index.family(roles[role]['entryRva'])
        windows=[w for w in c['codeWindows']if w['owner']==role]
        _require([[w['startRva'],w['endRva']]for w in windows]==[r['runtimeTriple'][:2]for r in family['ranges']],'transitionStorage.complete-family',role,windows)
        covered=[]
        for w in windows:
            rows=[r for r in p['instructions']if w['startRva']<=r['rva']<w['endRva']];cursor=w['startRva'];body=b''
            for r in rows:
                _require(r['rva']==cursor,'transitionStorage.contiguous-body',cursor,r['rva'])
                raw=bytes.fromhex(r['hex']);body+=raw;cursor+=len(raw);covered.append(r['rva'])
            _require(cursor==w['endRva'] and image.pe.bytes_at_va(image.pe.image_base+w['startRva'],len(body))==body,'transitionStorage.native-body',role,w)
        _require(covered==[r['rva']for r in p['instructions']],'transitionStorage.body-coverage',role,covered)
    context_roles={
        'Beyond.Gameplay.StateMachine`2':{26:('System.Collections.Generic.Dictionary`2','ContainsKey'),27:('System.Collections.Generic.Dictionary`2','get_Item'),30:('Beyond.Gameplay.FSMState`1','AddTransition'),31:('System.Collections.Generic.Dictionary`2','set_Item')},
        'Beyond.Gameplay.FSMState`1':{0:('System.Collections.Generic.List`1',None),2:('Beyond.Gameplay.FSMTransition`1',None),3:('Beyond.Gameplay.FSMTransition`1','.ctor'),4:('System.Collections.Generic.List`1','Add')}}
    _require(len(c['contextClaims'])==2 and {r['typeName']for r in c['contextClaims']}==set(context_roles),'transitionStorage.context-coverage',list(context_roles),c['contextClaims'])
    symbols=ContextSymbols(image)
    for claim in c['contextClaims']:
        owner=claim['typeName'];expected=context_roles[owner];actual=symbols.context(image.named_types[owner].index,slots=sorted(expected))
        validate_claims(claim,actual,label='transitionStorage.staticContext')
        _require([(r['relativeSlot'],r['typeName'].split('<',1)[0],r.get('methodName'))for r in actual['entries']]==[(i,*v)for i,v in expected.items()],'transitionStorage.context-role',expected,actual)
    return _rules(),_validate_dependencies(image,c,roles)


def _validate_dependencies(image,c,roles):
    dependencies=[]
    for role,module in [('construction',construction),('dispatch',dispatch)]:
        path=CONTRACTS_DIR/c['dependencies'][role]
        _require(path==module.CONTRACT_PATH,'transitionStorage.dependency-path',module.CONTRACT_PATH,path)
        dependency,digest=read_reviewed_contract(path,schema=module.SCHEMA,status='reviewed',label='transitionStorage.'+role)
        _require(dependency['nativeInputs']==c['nativeInputs'],'transitionStorage.dependency-native-inputs',role,dependency['nativeInputs'])
        module._validate(image,dependency);dependencies.append((path,digest,dependency))
    source=dependencies[0][2];reader=dependencies[1][2]
    _require(source['transitionAdderRva']==roles['machine']['entryRva'],'transitionStorage.construction-callee-join',roles['machine']['entryRva'],source['transitionAdderRva'])
    for key in ('transitionFromOffset','transitionToOffset','checkerOffset','stateTransitionsOffset','methodInfoClassOffset','rgctxOffset','initializerOffset'):
        _require(c['operands'][key]==reader['operands'][key],'transitionStorage.writer-reader-offset-'+key,reader['operands'][key],c['operands'][key])
    _require(c['operands']['machineStatesOffset']==reader['operands']['dictionaryOffset'],'transitionStorage.writer-reader-machine-states',reader['operands']['dictionaryOffset'],c['operands']['machineStatesOffset'])
    return [(p,d)for p,d,_ in dependencies]


def load_skill_center_transition_storage(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='transitionStorage');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        rules,deps=_validate(open_native_image(gate.gameassembly,gate.metadata),c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','transitionStorage.native-bookend','unchanged native inputs',after.status)
        for source,expected in [(path,digest),*deps]:
            _require(hashlib.sha256(source.read_bytes()).hexdigest().upper()==expected,'transitionStorage.declaration-bookend',str(source),'changed')
        audit.update(status='validated-conditional-transition-storage',detail='',nativeInputs=pins,evidenceBoundary=c['evidenceBoundary'],rules=rules,rows=[dict(id='constructorRequestToTransitionPhysicalStorage',evidence='conditional',rules=rules)])
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as e:
        detail=str(e)[:1600];audit.update(status='validation_failed',detail=detail,rules={},rows=[],failures=[dict(check=detail.split(':',1)[0],detail=detail)])
    return audit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('gameassembly','metadata'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_center_transition_storage_native.json');a=p.parse_args(argv)
    _require(a.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()),'transitionStorage.output-root','reports/',a.output)
    r=load_skill_center_transition_storage(gameassembly=a.gameassembly,metadata=a.metadata)
    if r['status']=='validated-conditional-transition-storage':a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r));return 0 if r['status']=='validated-conditional-transition-storage'else 2
if __name__=='__main__':raise SystemExit(main())

