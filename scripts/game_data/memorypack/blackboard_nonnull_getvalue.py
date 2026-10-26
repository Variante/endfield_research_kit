"""Compose complete nonnull public returns with the matching concrete Try arm.

The lookup owner supplies a complete conditional loop and authenticated frame
write ledger. No runtime class function, receiver contents or log effect is
supplied by these selected programs.
"""
from __future__ import annotations
from typing import Callable
from scripts.game_data.memorypack import closed_scalar_consumers as consumers

MODE='initialized-nonnull-board-public-and-matching-try-returns'


def specifications(cells:dict,limits:list,slot:int)->dict:
    key,selector,value=(cells[k] for k in ('blackboardKey','useBlackboardKey','value'))
    if (any(type(n)is not int or not 16<=n<128 for n in (key,selector,value)) or len(limits)!=3
            or type(slot)is not int or not 0<=slot<65536):raise ValueError('nonnullGetValue.cells-and-slot')
    def d(n):return n.to_bytes(4,'little',signed=True).hex().upper()
    public=['48895C2408','57','4883EC40',None,'488BDA','0F29742430','488BF9',None,
        '0F57F6','33D2',None,'F20F11742468',None,'84C0',None,'4885DB',None,
        '4C8D4C2468','4C8BC3','488BD7',None,'84C0',None]
    suffix=['488B5C2450','0F28742430','4883C440','5F','C3']
    specs={}
    for role,found in [('publicFound',True),('publicMissing',False)]:
        middle=['F20F10442468',None] if found else ['488B7F'+f'{key:02X}','33D2','488BCB',None,
            None,'488BD8',None,None,'4C8BCB',None,'4C8BC7','48894C2420','B103',None,'0F57C0',None]
        specs[role]={'owner':'public','expected':public+middle+suffix,
            'branches':{7:('75',True),14:('75',False),16:('74',False),22:('75',found),24 if found else 38:('EB',True)},
            'variables':{3:7,10:5,12:5,20:5,**({26:5,27:7,29:5,30:7,32:7,36:5} if not found else {})},
            'calls':{12:'patchCheck',20:'tryThunk',**({26:'dumpToString',29:'classStorageHelper',36:'missingLogger'} if not found else {})},
            'flagRow':3,'patchIndexRow':10,'globals':{} if found else {
                27:('488B0D','loggerClass'),30:('488B0D','loggerContext'),32:('488B15','loggerFormat')}}
    prefix=['48895C2408','4889742418','57','4883EC30','488B0A','498BF1','498BF8','488BDA',None,
        '488B03','4C8B90'+d((slot+20)*16),'4C8B88'+d((slot+20)*16+8),None,'4C3BD0',None,None,
        '83B9E000000000',None,'488B81B8000000','488B10','4885D2',None,'817A18'+d(limits[0]),None,
        '4885FF',None,'83B9E000000000','0F57C0','F20F11442448',None,'488B81B8000000','488B10',
        '4885D2',None,'817A18'+d(limits[1]),None,'83B9E000000000',None,'488B81B8000000','488B10',
        '4885D2',None,'817A18'+d(limits[2]),None,'807B'+f'{selector:02X}'+'00',None]
    guards={n:(opcode,False) for n,opcode in [(14,'0F85'),(17,'0F84'),(21,'0F84'),(23,'0F8F'),
        (25,'0F84'),(29,'0F84'),(33,'0F84'),(35,'0F8F'),(37,'0F84'),(41,'0F84'),(43,'0F8F')]}
    suffix=['F20F1106','488B5C2440','488B742450','4883C430','5F','C3']
    for role,keyed in [('thunkDirect',False),('thunkKeyed',True)]:
        middle=['488B53'+f'{key:02X}','4C8D442448','4533C9','488BCF',None,'F20F10442448',None] if keyed else [
            'F30F1043'+f'{value:02X}','B001','0F5AC0']
        specs[role]={'owner':'try','expected':prefix+middle+suffix,
            'branches':{**guards,45:('75',keyed),**({52:('EB',True)} if keyed else {})},
            'variables':{8:5,12:7,15:7,**({50:5} if keyed else {})},
            'calls':{8:'classInitHelper',**({50:'numberLookup'} if keyed else {})},'globals':{15:('488B0D','dispatch')},
            'tryComparandRow':12}
    return specs


def validate(image,c,consumer,lookup,composition,*,fail:Callable)->dict:
    if c.get('mode')!=MODE or not consumer.get('selectedConcreteConsumerFieldFlowProved'):
        fail('nonnull-public-scope',MODE,c.get('mode'))
    fields=consumer['records'];keyed=fields['tryKeyed'];direct=fields['tryDirect']
    if (not lookup.get('completeSelectedManagedLookupCfgProved') or not lookup.get('arbitraryLoopProved')
            or not lookup.get('allSelectedReturnsRestoreSavedRegistersAndFrame')
            or not composition.get('selectedKeyedConsumerAndManagedLookupComposed')
            or not composition.get('calleeRestoresCallerOutputAliasAndFrameProved')
            or c['methods']['numberLookup']!=keyed['lookupMethod'] or c['methods']['numberLookup']!=composition['actualLookupMethod']
            or c['dispatchLimits']!=keyed['guardSignedDwordAtMostComparedIndices']):
        fail('nonnull-public-independent-lookup','same complete current managed loop, actual callee and frame ledger',lookup)
    cells={'blackboardKey':keyed['keyOffset'],'useBlackboardKey':keyed['selectorOffset'],'value':direct['valueOffset']}
    specs=specifications(cells,c['dispatchLimits'],c['trySlot'])
    if set(c['programs'])!=set(specs):fail('nonnull-public-program-set',sorted(specs),sorted(c['programs']))
    for role,spec in specs.items():
        proof=c['programs'][role];rows=consumers._profile(image,proof,spec['expected'],spec['branches'],fail)
        if rows[0][0]!=c['entries'][spec['owner']]:fail('nonnull-public-entry',c['entries'][spec['owner']],rows[0])
        for n,method in spec['calls'].items():consumers._call(rows[n],c['methods'][method],fail)
        if 'flagRow' in spec:
            at,h=rows[spec['flagRow']];raw=bytes.fromhex(h)
            if (len(raw)!=7 or raw[:2]!=bytes.fromhex('803D') or raw[-1]!=0
                    or at+7+int.from_bytes(raw[2:6],'little',signed=True)!=c['globalCells']['publicInit']):
                fail('nonnull-public-initialized-flag',c['globalCells']['publicInit'],rows[spec['flagRow']])
            if consumers._patch_index(rows[spec['patchIndexRow']],fail)!=c['publicPatchIndex']:
                fail('nonnull-public-patch-index',c['publicPatchIndex'],rows[spec['patchIndexRow']])
        for n,(prefix,name) in spec['globals'].items():
            at,h=rows[n];raw=bytes.fromhex(h)
            if len(raw)!=7 or not raw.startswith(bytes.fromhex(prefix)) or at+7+int.from_bytes(raw[3:],'little',signed=True)!=c['globalCells'][name]:
                fail('nonnull-public-global-cell',[prefix,name,c['globalCells'][name]],rows[n])
        if 'tryComparandRow' in spec:
            at,h=rows[spec['tryComparandRow']];raw=bytes.fromhex(h)
            if len(raw)!=7 or raw[:3]!=bytes.fromhex('488D05') or at+7+int.from_bytes(raw[3:],'little',signed=True)!=c['methods']['tryValue'][3]:
                fail('nonnull-public-concrete-try-comparand',c['methods']['tryValue'],rows[spec['tryComparandRow']])
    # The helper's Double temporary occupies unused incoming home space.
    # Its saved RBX/RSI bracket, rather than overlap, those eight bytes.
    public_frame=64;helper_frame=48;helper_delta=-(8+8+helper_frame)
    public_output=104;temporary=72
    writes=[{'kind':'helper-private-frame','publicRspStart':helper_delta,'bytes':helper_frame},
        {'kind':'helper-push-and-return','publicRspStart':helper_delta+helper_frame,'bytes':16},
        {'kind':'helper-saved-rbx','publicRspStart':helper_delta+64,'bytes':8},
        {'kind':'helper-temporary','publicRspStart':helper_delta+temporary,'bytes':8},
        {'kind':'helper-saved-rsi','publicRspStart':helper_delta+80,'bytes':8}]
    if (composition['calleeRspRelativeToCallerRsp']!=-176 or composition['calleeStackAllocationBytes']!=144
            or lookup['outputWriteBytes']!=8 or lookup['numericConversionPerformed'] is not False):
        fail('nonnull-public-lookup-frame','proved selected lookup allocation and exact Double outputs',composition)
    for write in composition['calleeNonOutputWrites']:
        a=write['callerRspRelativeStart'];b=a+write['bytes']
        if not (-176<=a<b<=-32 or 0<=a<b<=32) or a<temporary+8 and temporary<b:
            fail('nonnull-public-lookup-temporary-overlap',[temporary,temporary+8],write)
    for write in writes:
        a=write['publicRspStart'];b=a+write['bytes']
        if a<public_output+8 and public_output<b:fail('nonnull-public-output-frame-overlap',[public_output,public_output+8],write)
    return {'selectedNonNullBoardPublicReturnComposed':True,'selectedCompletePrograms':len(specs),'scalarFieldCells':cells,
        'actualLookupMethod':c['methods']['numberLookup'],'tryVirtualSlot':c['trySlot'],
        'tryVirtualFunctionCellRelativeToClass':(c['trySlot']+20)*16,'tryVirtualCompanionCellRelativeToClass':(c['trySlot']+20)*16+8,
        'virtualFunctionCondition':c['methods']['tryValue'],'matchingConcreteTryInlinedFieldFlowProved':True,
        'publicStackAllocationBytes':public_frame,'publicOutputRspOffset':public_output,'helperStackAllocationBytes':helper_frame,
        'helperRspRelativeToPublicRsp':helper_delta,'helperTemporaryRspOffset':temporary,'helperTemporaryUsesIncomingHomeSpace':True,
        'helperFrameWrites':writes,'lookupAndHelperTemporariesSeparatedFromPublicOutputProved':True,
        'helperPostLookupAlPreserved':True,'allSelectedFramesAndSavedRegistersRestored':True,
        'conditionalDirectRelation':'Stored Single completes conversion to lower Double; helper writes public output and returns AL=true; public returns those same eight output bytes.',
        'conditionalKeyedFoundRelation':'Managed lookup first matching numeric Double -> helper temporary -> public output with AL=true -> public Double return.',
        'conditionalKeyedMissingRelation':'Managed lookup exhausted -> temporary/public output zero with AL=false -> actual dump/logger argument program -> public Double explicitly zero.',
        'storedSingleMissingKeyFallbackPerformed':False,'missingDumpAndLogArgumentProgramProved':True,
        'actualLogEmissionOrEffectsKnown':False,'actualRuntimeClassSlotValueKnown':False,'liveLoggerContextOrMutationEffectsProved':False,
        'conditions':composition['conditions']+['Public usage initialization flag is already nonzero and public IsPatched returns false ordinarily.',
            'Incoming Blackboard is nonnull; the helper class slot function equals current concrete Try; its stored guards take their normal fallthroughs.',
            'Private frames and supplied Win64 home spaces are valid and isolated; class/global/string/context storage is valid and stable across ordinary helpers.',
            'The missing-value dump, class helper and actual physical registered logger return ordinarily with compatible context and preserve active frames/referents; their effects are unsupplied.',
            'Direct SIMD conversion completes; CPU/MXCSR outcomes and actual receiver/list/value selection are not observed.'],
        'evidenceBoundary':'conditional','publicGetValueAllNormalSelectionsProved':False,'actualNumericResultKnown':False,
        'runtimeExecutionKnown':False,'providerSelectionProved':False,'allDispatchAndFailureEffectsProved':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False}
