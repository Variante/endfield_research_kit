"""Current ordinary runtime case anchoring shared by named policies."""
from scripts.game_data.il2cpp.owned_partition import BranchGrammar


def runtime_case(part,program,origins,*,entry,image_base,fields,enums,case):
    label='levelscriptRuntimeCase';rows=program['rows'];reference=origins['registerOrigins']
    def receiver(at,zero=False):
        if reference[at]['rdi']!=['this'] or zero and reference[at]['rbx']!=['constant:0x0']:
            raise ValueError(label+'.incoming-this-or-zero-bits')
    for table in part['tables']:
        if table['jump'] in program['computedJumpTargets'] and reference[table['load']][table['baseRegister']]!=['constant:'+hex(image_base)]:
            raise ValueError(label+'.selected-image-base')
    mains=[table for table in part['tables'] if table['baseLoad'] is not None]
    if len(mains)!=1:raise ValueError(label+'.unique-runtime-switch')
    main=mains[0];guard=next(i for i,row in enumerate(rows) if int(row['va'],16)==main['guard'])
    if guard<5:raise ValueError(label+'.runtime-switch-prefix')
    prefix=rows[guard-5:guard+1];g=BranchGrammar(prefix,label=label+'.runtimeCase')
    receiver(int(prefix[0]['va'],16));g.take(f'mov ecx, [rdi+{fields["runtimeState"]:#x}]')
    raw=bytes.fromhex(prefix[1]['bytes'])
    if len(raw)!=3 or raw[:2]!=b'\x8d\x41':raise ValueError(label+'.runtime-index-expression')
    bias=-int.from_bytes(raw[2:],'little',signed=True)
    if not 0<bias<=127 or bias!=enums['runtime']['NotLoaded']:raise ValueError(label+'.runtime-index-bias')
    expression=f'lea eax, [rcx-{bias:#x}]'
    g.take(expression,'test eax, eax');g.labels['firstCase']=main['targets'][0];g.branch('je','firstCase')
    g.take(expression,f'cmp eax, {main["maximum"]:#x}');g.finish()
    ordinal=enums['runtime'][case]-bias
    if not 0<=ordinal<=main['maximum']:raise ValueError(label+'.runtime-active-ordinal')
    active=main['targets'][ordinal];receiver(active,True)
    return dict(runtimeStateName=case,runtimeStateValue=enums['runtime'][case],instructionOffset=prefix[0]['offset'],
        indexBias=bias,tableOrdinal=ordinal,caseTargetVa=hex(active))

