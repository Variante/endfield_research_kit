"""Selected null-Board public GetValue, including shared virtual cast tails.

The raw slot function must be the independently proved concrete scalar cast.
The stored MethodSpec identifies a registration, never a live context. Selected
initialization flags, patch results and ordinary helper effects stay conditions.
"""
from __future__ import annotations
from typing import Callable

MODE='initialized-null-board-getvalue-and-scalar-cast-fallback'
LOCAL_OPS={'480306':'add rax, qword [rsi]'}


def specifications(selector: int, slot: int) -> dict:
    if type(selector) is not int or not 16 <= selector < 128 or type(slot) is not int or not 0 <= slot < 65536:
        raise ValueError('nullGetValue.scalar-cell-or-slot')
    public=['48895C2408','57','4883EC40',None,'488BDA','0F29742430','488BF9',None,
        '0F57F6','33D2',None,'F20F11742468',None,'84C0',None,'4885DB',None,
        None,'488BCF',None,None,'488B5C2450','0F28742430','4883C440','5F','C3']
    prefix=['4053','4883EC20',None,'488BD9',None,'807B'+f'{selector:02X}'+'00',None]
    return {
        'publicNull':{'owner':'public','expected':public,'terminal':'return',
            'branches':{7:('75',True),14:('75',False),16:('74',True),20:('EB',True)},
            'variables':{3:7,10:5,12:5,17:7,19:5},'calls':{12:'patchCheck',19:'getDirectValue'},
            'patchIndexRow':10,'flags':{3:'publicInit'},'globals':{17:('488B15','directUsage')}},
        'directCast':{'owner':'direct','expected':prefix+['B9'+slot.to_bytes(4,'little').hex().upper(),
            '488BD3','4883C420','5B',None],'terminal':'direct-tail',
            'branches':{4:('75',True),6:('75',False)},'variables':{2:7,11:5},'calls':{},
            'flags':{2:'directInit'},'tailTarget':'castThunk'},
        'directKeyed':{'owner':'direct','expected':prefix+[None,None,None,'33D2',None,'0F57C0','4883C420','5B','C3'],
            'terminal':'return','branches':{4:('75',True),6:('75',True)},
            'variables':{2:7,7:7,8:5,9:7,11:5},'calls':{8:'classStorageHelper',11:'directLogError'},
            'flags':{2:'directInit'},'globals':{7:('488B0D','loggerClass'),9:('488B0D','directErrorMessage')}},
        'castFallback':{'owner':'cast','expected':['4053','55','56','4883EC30','0FB7D9','488BF2','488B0A',None,
            '488D4314','48C1E004','480306','4C8B00','488B5008',None,'4C3BC0',None,
            None,'4C3BC0',None,None,'4C3BC0',None,'488BCE','4883C430','5E','5D','5B','49FFE0'],
            'terminal':'indirect-tail','branches':{15:('0F85',True),18:('0F85',True),21:('0F85',True)},
            'variables':{7:5,13:7,16:7,19:7},'calls':{7:'classInitHelper'},'flags':{},
            'comparands':{13:0,16:1,19:2},'globals':{}}}


def _target(row, opcode, *, fail):
    raw=bytes.fromhex(row[1]);prefix=bytes.fromhex(opcode);width=4 if opcode in ('E8','E9') or len(prefix)==2 else 1
    if len(raw)!=len(prefix)+width or not raw.startswith(prefix):fail('null-public-relative-opcode',opcode,row)
    return row[0]+len(raw)+int.from_bytes(raw[-width:],'little',signed=True)


def _program(image, proof, spec, *, fail):
    rows=proof['program'];expected=spec['expected'];windows=proof['codeWindows']
    if len(rows)!=len(expected) or not rows or rows[0][0]!=proof['entryRva']:
        fail('null-public-program-entry-size',[proof['entryRva'],len(expected)],rows)
    image.check_windows(windows,label='blackboardNullGetValue')
    for i,(row,wanted) in enumerate(zip(rows,expected,strict=True)):
        at,h=row;raw=bytes.fromhex(h)
        if not any(w['startRva']<=at<at+len(raw)<=w['endRva'] for w in windows):
            fail('null-public-program-ownership','one complete owned instruction',row)
        image.check_instruction_windows([row],label='blackboardNullGetValue')
        if h not in LOCAL_OPS:
            decoded=image.mapper.decode_x64_subset(raw,image.pe.image_base+at,stop_offset=len(raw))
            if len(decoded)!=1 or 'db ' in decoded[0]['text']:fail('null-public-complete-instruction','one known instruction',row)
        if wanted is not None and h!=wanted:fail('null-public-field-register-instruction',[i,wanted],row)
        if i in spec['branches']:
            opcode,taken=spec['branches'][i];target=_target(row,opcode,fail=fail)
            following=target if taken else at+len(raw)
        elif i+1<len(rows):following=at+len(raw)
        else:continue
        if i+1>=len(rows) or rows[i+1][0]!=following:fail('null-public-selected-edge',following,rows[i+1:i+2])
    last=rows[-1][1]
    if (spec['terminal']=='return' and last!='C3'
            or spec['terminal']=='indirect-tail' and last!='49FFE0'
            or spec['terminal']=='direct-tail' and not last.startswith('E9')):
        fail('null-public-terminal',spec['terminal'],rows[-1])
    return rows


def validate(image,c,consumer,consumer_declaration,*,fail:Callable)->dict:
    if c.get('mode')!=MODE or not consumer.get('selectedConcreteConsumerFieldFlowProved'):
        fail('null-public-scope',MODE,c.get('mode'))
    cast=consumer['records']['castValue'];keyed=consumer['records']['tryKeyed']
    if (not cast['completeSelectedReturnProved'] or cast['sourceLaneBits']!=32 or cast['resultLaneBits']!=64
            or c['methods']['castValue']!=consumer_declaration['records']['castValue']['method']
            or c['methods']['patchCheck']!=consumer_declaration['patchCheckMethod']):
        fail('null-public-independent-cast','actual complete closed Single-to-Double cast and patch definition',cast)
    specs=specifications(keyed['selectorOffset'],c['castSlot'])
    if set(c['programs'])!=set(specs):fail('null-public-program-set',sorted(specs),sorted(c['programs']))
    for role,spec in specs.items():
        proof=c['programs'][role];rows=_program(image,proof,spec,fail=fail)
        for n,method_role in spec['calls'].items():
            if _target(rows[n],'E8',fail=fail)!=c['methods'][method_role][3]:
                fail('null-public-call-identity',c['methods'][method_role],rows[n])
        for n,flag in spec['flags'].items():
            at,h=rows[n];raw=bytes.fromhex(h)
            if len(raw)!=7 or raw[:2]!=bytes.fromhex('803D') or raw[-1]!=0 or at+7+int.from_bytes(raw[2:6],'little',signed=True)!=c['globalCells'][flag]:
                fail('null-public-initialized-flag',[flag,c['globalCells'][flag]],rows[n])
        for n,(prefix,global_role) in spec.get('globals',{}).items():
            at,h=rows[n];raw=bytes.fromhex(h)
            if len(raw)!=7 or not raw.startswith(bytes.fromhex(prefix)) or at+7+int.from_bytes(raw[3:],'little',signed=True)!=c['globalCells'][global_role]:
                fail('null-public-global-source',[global_role,c['globalCells'][global_role]],rows[n])
        for n,ordinal in spec.get('comparands',{}).items():
            at,h=rows[n];raw=bytes.fromhex(h);actual=at+7+int.from_bytes(raw[3:],'little',signed=True)
            if len(raw)!=7 or raw[:3]!=bytes.fromhex('488D05') or actual!=c['castComparands'][ordinal]:
                fail('null-public-shared-cast-comparand',c['castComparands'][ordinal],rows[n])
            if actual==c['methods']['castValue'][3]:fail('null-public-concrete-cast-exclusion','distinct shared-helper special targets',actual)
        if 'tailTarget' in spec and _target(rows[-1],'E9',fail=fail)!=c['entries'][spec['tailTarget']]:
            fail('null-public-direct-tail-identity',c['entries'][spec['tailTarget']],rows[-1])
        if 'patchIndexRow' in spec:
            raw=bytes.fromhex(rows[spec['patchIndexRow']][1])
            if len(raw)!=5 or raw[0]!=0xb9 or int.from_bytes(raw[1:],'little',signed=True)!=c['publicPatchIndex']:
                fail('null-public-patch-index',c['publicPatchIndex'],rows[spec['patchIndexRow']])
    # Both selected direct programs leave entry RDX unread; one replaces it
    # with the scalar for the cast tail, the other explicitly zeros it.
    cast_prefix=consumer_declaration['records']['castValue']['program'][:4]
    if [r[1] for r in cast_prefix]!=['4053','4883EC20','488BD9','33D2']:
        fail('null-public-cast-context-unused','owned cast overwrites incoming RDX before reading it',cast_prefix)
    return {'selectedNullBoardPublicReturnComposed':True,'selectedCompletePrograms':len(specs),
        'conditionalDirectRelation':'Zero selector -> current concrete virtual cast entry -> completed stored Single-to-Double lower lane -> public Double return.',
        'conditionalKeyedRelation':'Nonzero selector -> actual direct LogError call returns ordinarily -> zero Double bits -> public Double return.',
        'storedSingleMissingKeyFallbackPerformed':False,'initializedDirectEntryRdxRead':False,
        'normalConcreteCastEntryRdxRead':False,'liveMethodInfoRequiredBySelectedReturnInstructions':False,
        'castVirtualSlot':c['castSlot'],'castVirtualFunctionCellRelativeToClass':(c['castSlot']+20)*16,
        'castVirtualCompanionCellRelativeToClass':(c['castSlot']+20)*16+8,
        'selectedVirtualFunctionCondition':c['methods']['castValue'],
        'sharedSpecialCasesExcludeConcreteCastProved':True,'allTailsRestoreOwnedFramesBeforeDelegation':True,
        'logErrorCallIdentityAndArgumentProgramProved':True,'actualLogEmissionOrEffectsKnown':False,
        'actualRuntimeClassSlotValueKnown':False,
        'conditions':['Public and direct-entry usage initialization flags are already nonzero.',
            'Public GetValue and the concrete cast patch checks return false ordinarily.',
            'The coherent unchanged scalar is the same instance in all selected programs; incoming Blackboard is null.',
            'The computed class slot function equals the current concrete cast entry; no actual class slot is supplied.',
            'Receiver/class/field/global storage and isolated Win64 frames are valid and stable across ordinary helper returns.',
            'Direct conversion completes; CPU/MXCSR numeric outcomes and logging/helper effects remain unsupplied.'],
        'evidenceBoundary':'conditional','publicGetValueAllNormalSelectionsProved':False,
        'actualNumericResultKnown':False,'runtimeExecutionKnown':False,'providerSelectionProved':False,
        'allDispatchAndFailureEffectsProved':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}
