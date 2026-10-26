"""Complete selected default chain, distinct from public GetValue dispatch.

Authenticates actual TryGetDouble and both default callers through their
returns. Default bits, lookup outputs and Boolean selections remain relations
under the stated normal programs, rather than observed game values.
"""
from __future__ import annotations
from typing import Callable
from scripts.game_data.memorypack import closed_scalar_consumers as consumers

MODE = 'normal-try-double-and-double-default-call-chain'


def specifications(cells: dict, limits: list[int]) -> dict:
    key, selector, value = (cells[k] for k in ('blackboardKey','useBlackboardKey','value'))
    if any(type(n) is not int or not 16 <= n < 128 for n in (key,selector,value)) or len(limits) != 3:
        raise ValueError('doubleDefault.closed-cells-and-limits')
    def d(n): return n.to_bytes(4,'little',signed=True).hex().upper()
    prefix = ['48895C2408','4889742410','57','4883EC40','488BF1','0F57C0',None,'498BF8','F20F11442430',
        '488BDA','83B9E000000000',None,'488B81B8000000','488B10','4885D2',None,'817A18'+d(limits[1]),None,
        '83B9E000000000',None,'488B81B8000000','488B10','4885D2',None,'817A18'+d(limits[2]),None,
        '4885DB',None,'807B'+f'{selector:02X}'+'00',None]
    guards = {i:(opcode,False) for i,opcode in [(11,'0F84'),(15,'0F84'),(17,'0F8F'),(19,'74'),
        (23,'0F84'),(25,'0F8F'),(27,'0F84')]}
    suffix = ['F20F1107','488B5C2450','488B742458','4883C440','5F','C3']
    specs = {}
    for role,keyed in [('direct',False),('keyed',True)]:
        middle = (['488B53'+f'{key:02X}','4C8D442430','4533C9','488BCE',None,'F20F10442430',None] if keyed
                  else ['F30F1043'+f'{value:02X}','B001','0F5AC0'])
        branches = {**guards,29:('75',keyed)}
        if keyed: branches[36] = ('EB',True)
        specs['try'+role.title()] = {'method':'tryDouble','expected':prefix+middle+suffix,'branches':branches,
            'variableLengths':{6:7,**({34:5} if keyed else {})},'calls':{34:'numberLookup'} if keyed else {}}
    prefix = ['488BC4','48895808','48897010','57','4883EC50','488BDA','0F2970E8','488BF9','0F57C0',
        '33D2','F20F1140D8',None,'418AF1','0F28F2',None,'84C0',None,'4533C9','4C8D442430','488BD3',
        '488BCF',None,'84C0',None]
    suffix = ['488B5C2460','488B742468','0F28742440','4883C450','5F','C3']
    for role,found in [('found',True),('missing',False)]:
        middle = ['F20F10442430',None] if found else ['0F28C6',None]
        specs['default'+role.title()] = {'method':'getDoubleOrDefault','expected':prefix+middle+suffix,
            'branches':{16:('75',False),23:('75',found),25:('EB',True)},
            'variableLengths':{11:5,14:5,21:5},'patchIndexRow':11,'calls':{14:'patchCheck',21:'tryDouble'}}
    specs['scalarDefault'] = {'method':'getValueOrDefaultInternal',
        'expected':['48895C2408','57','4883EC40','488BDA','0F29742430','488BF9','33D2',None,'0F28F2',None,
            '84C0',None,'4885DB',None,'488364242000','4533C9','0F28D6','488BD7','488BCB',None,None,
            '488B5C2450','0F28742430','4883C440','5F','C3'],
        'branches':{11:('75',False),13:('74',False),20:('EB',True)},
        'variableLengths':{7:5,9:5,19:5},'patchIndexRow':7,'calls':{9:'patchCheck',19:'getDoubleOrDefault'}}
    return specs


def validate(image, c: dict, consumer: dict, composition: dict, *, fail: Callable) -> dict:
    if c.get('mode') != MODE or not consumer.get('selectedConcreteConsumerFieldFlowProved'):
        fail('default-chain-scope', MODE, c.get('mode'))
    fields = consumer['records']; keyed = fields['tryKeyed']; direct = fields['tryDirect']
    if (not composition.get('selectedKeyedConsumerAndManagedLookupComposed')
            or not composition.get('temporaryDisjointFromShadowAndCalleeFrameProved')
            or composition.get('callerStackFrameBytes') != 64 or composition.get('temporaryCallerRspOffset') != 48):
        fail('default-chain-lookup-composition', 'complete current keyed/managed relation and caller frame', composition)
    if c['methods']['numberLookup'] != keyed['lookupMethod'] or c['dispatchLimits'] != keyed['guardSignedDwordAtMostComparedIndices']:
        fail('default-chain-lookup-and-guards', [keyed['lookupMethod'],keyed['guardSignedDwordAtMostComparedIndices']], c)
    cells = {'blackboardKey':keyed['keyOffset'],'useBlackboardKey':keyed['selectorOffset'],'value':direct['valueOffset']}
    specs = specifications(cells,c['dispatchLimits'])
    if set(c['programs']) != set(specs): fail('default-chain-programs',sorted(specs),sorted(c['programs']))
    for role,spec in specs.items():
        proof = c['programs'][role]; method = c['methods'][spec['method']]
        rows = consumers._profile(image,proof,spec['expected'],spec['branches'],fail)
        if rows[0][0] != method[3]: fail('default-chain-entry',method,rows[0])
        for at,callee in spec['calls'].items(): consumers._call(rows[at],c['methods'][callee],fail)
        if 'patchIndexRow' in spec:
            actual = consumers._patch_index(rows[spec['patchIndexRow']],fail)
            if actual != c['patchIndices'][spec['method']]: fail('default-chain-patch-index',c['patchIndices'],actual)
        if spec['method'] == 'tryDouble':
            raw = bytes.fromhex(rows[6][1])
            if len(raw) != 7 or not raw.startswith(bytes.fromhex('488B0D')) or rows[6][0]+7+int.from_bytes(raw[3:],'little',signed=True) != c['dispatchCellRva']:
                fail('default-chain-dispatch-cell',c['dispatchCellRva'],rows[6])
    # The nullable-Board edge is inventoried separately; its helper/INT3 is
    # authenticated without naming an exception or claiming runtime effects.
    null = c['scalarNullBoardTail']
    if len(null) != 2: fail('default-chain-null-board-edge','two complete CALL/INT3 instructions',null)
    windows = c['ownedCodeWindows']['getValueOrDefaultInternal']
    if any(not any(w['startRva'] <= at < at+len(bytes.fromhex(h)) <= w['endRva'] for w in windows) for at,h in null):
        fail('default-chain-null-board-ownership','same actual scalar default owned extent',null)
    image.check_instruction_windows(null)
    raw = bytes.fromhex(null[0][1])
    branch = c['programs']['scalarDefault']['program'][13]
    target = branch[0]+2+int.from_bytes(bytes.fromhex(branch[1])[1:],'little',signed=True)
    if (len(null) != 2 or null[0][0] != target or len(raw) != 5 or raw[0] != 0xe8
            or null[1] != [target+5,'CC']):
        fail('default-chain-null-board-edge','actual JE into helper CALL followed by INT3',null)
    return {'selectedDefaultChainComposed':True,'selectedCompletePrograms':len(specs),
        'scalarFieldCells':cells,'closedGenericTemplateOffsetsUsed':False,
        'tryDoubleArguments':{'receiver':'incoming Blackboard in rsi','scalar':'incoming BlackboardDouble in rbx','output':'incoming double address in rdi'},
        'tryDoubleKeyedLookupRelationInherited':True,'tryDoubleDirectConversionRelationInherited':True,
        'tryDoubleOutputWriteBytes':8,'tryDoublePostLookupAlPreserved':True,
        'defaultCapturedFrom':'incoming xmm2.low64 saved in xmm6 across ordinary returning calls',
        'defaultFoundRelation':'TryGetDouble AL=true -> initialized output slot at caller RSP+48 -> xmm0.low64',
        'defaultMissingRelation':'TryGetDouble AL=false -> original saved default bits in xmm6.low64 -> xmm0.low64',
        'defaultNumericConversionPerformed':False,'normalShowWarningParameterReadBeyondCapture':False,
        'scalarDefaultForwardsOriginalDefaultBits':True,'scalarDefaultForwardsShowWarningFalse':True,
        'scalarDefaultRequiresNonNullBlackboard':True,'scalarNullBoardHelperInt3EdgeProved':True,
        'nullBoardExceptionKindOrEffectsProved':False,
        'conditions':composition['conditions'] + ['Both named default patch checks return false ordinarily.',
            'Default-chain receiver/scalar/output references and isolated frames are valid; TryGetDouble guards complete normally.',
            'Caller default lower Double bits and nonvolatile xmm6 survive all ordinary returning calls.',
            'The scalar default caller receives a nonnull Blackboard; its null branch is outside the normal return relation.',
            'Direct Single-to-Double SIMD conversion completes; actual CPU/MXCSR outcomes are not supplied.'],
        'evidenceBoundary':'conditional','actualDefaultOrLookupValueKnown':False,
        'publicGetValueEndToEndProved':False,'runtimeExecutionKnown':False,'providerSelectionProved':False,
        'allDispatchAndFailureEffectsProved':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}
