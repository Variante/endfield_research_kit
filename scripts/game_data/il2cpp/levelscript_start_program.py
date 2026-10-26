"""Current ordinary Active-case start policy."""
from scripts.game_data.il2cpp.levelscript_runtime_program import runtime_case
from scripts.game_data.il2cpp.owned_partition import BranchGrammar


def check_levelscript_start_program(part,program,origins,*,entry,image_base,fields,enums,pointers):
    label='levelscriptStartProgram';rows=program['rows'];by_at={int(row['va'],16):row for row in rows}
    reference=origins['registerOrigins']
    def receiver(at,zero=False):
        if reference[at]['rdi']!=['this'] or zero and reference[at]['rbx']!=['constant:0x0']:
            raise ValueError(label+'.incoming-this-or-zero-bits')
    gate=runtime_case(part,program,origins,entry=entry,image_base=image_base,fields=fields,enums=enums,case='Active')
    active=int(gate['caseTargetVa'],16)
    position=next(i for i,row in enumerate(rows) if int(row['va'],16)==active)
    first=BranchGrammar(rows[position:position+2],label=label+'.publicActive')
    first.take(f'cmp dword [rdi+{fields["state"]:#x}], {enums["state"]["Active"]:#x}')
    done=first.branch('je')['target'];first.finish();receiver(done,True)
    position=next(i for i,row in enumerate(rows) if int(row['va'],16)==done)
    g=BranchGrammar(rows[position:],label=label+'.policy');g.take(f'cmp [rdi+{fields["done"]:#x}], bl')
    g.branch('jne','exit');start_calls=[]
    def call(pointer):
        row=g.call(pointer)
        if reference[int(row['va'],16)]['rcx']!=['this']:raise ValueError(label+'.callee-receiver')
        return row
    g.take('xor edx, edx','mov rcx, rdi');start_calls.append(call(pointers['get_startType']))
    g.take(f'cmp eax, {enums["start"]["Never"]:#x}');never=g.branch('je','exit')
    g.take('xor edx, edx','mov rcx, rdi');start_calls.append(call(pointers['get_startType']))
    if enums['start']['ByEnterStartShape']!=0:raise ValueError(label+'.zero-tested-start-member')
    g.take('xor edx, edx','mov rcx, rdi','test eax, eax');area_branch=g.branch('je','area')
    start_calls.append(call(pointers['get_startType']));g.take(f'cmp eax, {enums["start"]["SameWithActive"]:#x}')
    same=g.branch('je','preStart');manual=g.take(f'cmp [rdi+{fields["manual"]:#x}], bl')
    receiver(int(manual['va'],16),True);g.branch('je','exit')
    g.take(f'mov [rdi+{fields["manual"]:#x}], bl');g.branch('jmp','preStart')
    g.mark('area');area=call(pointers['UpdateWithinStartArea']);g.take('test al, al');g.branch('je','exit')
    g.mark('preStart');g.take('xor r8d, r8d',f'mov edx, {enums["runtime"]["PreStart"]:#x}','mov rcx, rdi')
    setter=call(pointers['set_runtimeState']);g.mark('exit');g.finish(prefix=True)
    gates={name:dict(callOffset=start_calls[i]['offset'],comparedValue=enums['start'][name],branchTargetVa=hex(branch['target']))
        for i,(name,branch) in enumerate((('Never',never),('ByEnterStartShape',area_branch),('SameWithActive',same)))}
    gates['Never']['branchesAwayFromPreStart']=True;gates['ByEnterStartShape']['branchTargetIsStartAreaCheck']=True
    gates['SameWithActive']['branchTargetIsCommonPreStart']=True
    return dict(runtimeStateGate=gate,
        activeStateGate=dict(instructionOffset=active-entry,comparedValue=enums['state']['Active'],branchTargetVa=hex(done),branchTargetIsDoneCheck=True),
        doneGate=dict(instructionOffset=done-entry,doneResultTested=True,notDoneFallsThroughToStartPolicy=True),startTypeGates=gates,
        startAreaGate=dict(callOffset=area['offset'],resultTested=True,trueFallsThroughToCommonPreStart=True),
        preStartTransition=dict(commonTargetVa=hex(g.labels['preStart']),setterCallOffset=setter['offset'],
            runtimeStateValue=enums['runtime']['PreStart'],setterReceivesValue=True),
        evidenceBoundary='conditional',condition=program['condition']+' Typed original getter/area/setter implementations, ordinary Win64 callees and stable disjoint storage are conditions; IFix replacements and live state remain separate.')

