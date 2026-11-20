"""Bounded normal-attack cache/admission/direct-cast fragments, offline only.

The finite program vocabulary proves selected register and call relations. It
does not select a live AI state, equate separately reloaded receivers, or infer
an unrecorded TryCastSkill result from BeforeCast or nearby commands.
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
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.skill_timing_runtime_native import _validate_fields

SCHEMA='endfield.skill-normal-attack-delivery-native-contract.v2'
CONTRACT_PATH=CONTRACTS_DIR/'skill_normal_attack_delivery_native.json'
RULES=dict(originalPathOnly=True,normalReturnedPathOnly=True,canCastReceiverReloaded=True,
    tryCastReceiverReloaded=True,sameAbilitySystemReceiverProved=False,
    sameIdAndTargetRegistersForwarded=True,canCastFalseSkipsTryCast=True,
    canCastTrueNormalReturnCallsTryCast=True,tryCastBoolForwarded=True,
    aiTargetCallsTryCastDirectly=True,stateTryCastReturnConsumed=False,
    runtimeRequestDeliveryProved=False,unrecordedCallerProved=False)


def need(check,condition):
    if not condition:raise ValueError('skillNormalAttackDelivery.'+check)


def _same(a,b):
    return json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False)


def _decode(raw,rva,*,helper=False):
    """Finite AMD64 framing, GP write set and direct control edges.

    Calls use the explicit ordinary Win64 nonvolatile-register premise. No
    instruction text or contract-supplied write annotation is trusted.
    """
    at=0;rex=0;word=False;prefixes=[];groups=set()
    while at<len(raw)and(raw[at]in(0x66,0xf2,0xf3,0xf0)or 0x40<=raw[at]<=0x4f):
        value=raw[at];prefixes.append(value)
        if 0x40<=value<=0x4f:
            need('single-canonical-rex',not rex);rex=value
        else:
            need('legacy-before-rex',not rex)
            need('finite-legacy-prefix',value in((0x66,0xf2,0xf3,0xf0)if helper else(0x66,0xf2)))
            group=1 if value in(0xf0,0xf2,0xf3)else 3
            need('unique-prefix-group',group not in groups);groups.add(group)
        word|=value==0x66;at+=1
    need('instruction-prefix',at<len(raw));op=raw[at];at+=1;end=rva+len(raw)
    need('finite-prefix-combination',len(groups)<=1 and not(word and rex&8))
    need('finite-prefixed-opcode',not groups or op==0x0f or word and op in(0x89,0xc7))
    if op in(0xe8,0xe9,0xeb)or 0x70<=op<=0x7f:
        width=1 if op==0xeb or 0x70<=op<=0x7f else 4
        need('control-width',at+width==len(raw));target=end+int.from_bytes(raw[at:],'little',signed=True)
        if op==0xe8:return {0,1,2,8,9,10,11},[end],'call',target
        if op in(0xe9,0xeb):return set(),[target],'jump',target
        return set(),[end,target],'branch',target
    if op in(0xc3,0xcc):
        need('terminal-width',at==len(raw));return set(),[],'return'if op==0xc3 else'trap',None
    if op==0x90:need('nop-width',at==len(raw));return set(),[end],'next',None
    if 0x50<=op<=0x5f:
        need('stack-width',at==len(raw));reg=(op&7)+(8 if rex&1 else 0)
        return ({4,reg}if op>=0x58 else{4}),[end],'next',None
    if 0xb0<=op<=0xbf:
        width=1 if op<0xb8 else 8 if rex&8 else 2 if word else 4
        need('immediate-width',at+width==len(raw));reg=(op&7)+(8 if rex&1 else 0)
        if op<0xb8 and not rex and reg>=4:reg-=4
        return {reg},[end],'next',None
    if op in(0x05,0x25,0x3d):
        need('accumulator-width',at+(2 if word else 4)==len(raw))
        return(set()if op==0x3d else{0}),[end],'next',None
    second=None;immediate=0
    if op==0x0f:
        need('second-opcode',at<len(raw));second=raw[at];at+=1
        if 0x80<=second<=0x8f:
            need('near-branch-width',at+4==len(raw));target=end+struct.unpack_from('<i',raw,at)[0]
            return set(),[end,target],'branch',target
        need('finite-second-opcode',second in((0x0d,0x10,0x11,0x14,0x1f,0x28,0x29,0x57,0x58,0x6e,0x73,0x7e,0x7f,0xab,0xb1,0xb7)if helper else(0x10,0x11,0x29,0x57,0x73,0x7e,0xb7)))
        immediate=1 if second==0x73 else 0
    else:
        need('finite-opcode',op in((0x38,0x3b,0x63)if helper else())+(0x88,0x89,0x8b,0x8d,0x39,0x32,0x33,0x85,0x84,0x81,0x83,0xc1,0xc6,0xc7,0xff))
        immediate=1 if op in(0x83,0x80,0xc1,0xc6,0xf6)else(2 if word else 4)if op in(0x69,0x81,0xc7,0xf7)else 0
    need('modrm',at<len(raw));modrm=raw[at];at+=1;mod=modrm>>6;group=(modrm>>3)&7
    reg=group+(8 if rex&4 else 0);rm=(modrm&7)+(8 if rex&1 else 0)
    if helper and second in(0x0d,0x1f):need('helper-hint-memory',mod!=3 and group in ((1,) if second==0x0d else (0,)))
    if helper and second in(0x14,0x28,0x58):need('helper-sse-form',not word and (second==0x58 and 0xf3 in prefixes or second!=0x58 and not groups))
    if helper and second==0x7f:need('helper-movdqa',word and not rex&8)
    if helper and second==0x6e:need('helper-movd',word and not rex&8)
    if helper and 0xf0 in prefixes:need('helper-locked-memory-cmpxchg',second==0xb1 and mod!=3 and bool(rex&8))
    if helper and second==0xb1:need('helper-cmpxchg-lock',0xf0 in prefixes)
    if helper and second==0xab:need('helper-bts-register',mod==3 and not groups and bool(rex&8))
    if second in(0x10,0x11):need('finite-sse-prefix',not word)
    if second in(0x29,0x57,0xb7):need('finite-unprefixed-sse',not groups)
    if second==0x73:need('finite-xmm-shift',word and mod==3 and group==3)
    if second==0x7e:need('finite-movd',word)
    if mod!=3 and modrm&7==4:
        need('sib',at<len(raw));sib=raw[at];at+=1
        if mod==0 and sib&7==5:at+=4
    if mod==0 and modrm&7==5:at+=4
    if mod==1:at+=1
    if mod==2:at+=4
    need('whole-instruction',at+immediate==len(raw))
    writes=set();kind='next'
    if op==0x0f:
        if second in(0xb6,0xb7):writes.add(reg)
        elif second in(0x7e,0xab)and mod==3 and not(second==0x7e and 0xf3 in prefixes):writes.add(rm)
        elif second==0xb1:
            writes.add(0)
            if mod==3:writes.add(rm)
    elif op in(0x8b,0x8d,0x32,0x33,0x03,0x2b,0x63,0x69):writes.add(reg)
    elif op in(0x88,0x89,0xc1,0xc6,0xc7)and mod==3:writes.add(rm)
    elif op in(0x81,0x83,0x80)and group!=7 and mod==3:writes.add(rm)
    elif op==0xff:
        need('finite-ff-group',group==2 and (mod==3 or helper and raw==bytes.fromhex('ff10')))
        writes={0,1,2,8,9,10,11};kind='indirect-call'
    return writes,[end],kind,None


def _graph(rows,*,helper=False):
    nodes={};edges={};decoded={}
    for row in rows:
        at=row['rva'];raw=bytes.fromhex(row['hex']);need('instruction-unique',at not in nodes and 0<len(raw)<=15)
        decoded[at]=_decode(raw,at,helper=helper);nodes[at]=raw;edges[at]=decoded[at][1]
    return nodes,edges,decoded


def _reachable(edges,start,stop=None):
    seen=set();todo=[start]
    while todo:
        at=todo.pop()
        if at in seen or at==stop:continue
        need('owned-control-node',at in edges);seen.add(at);todo.extend(edges[at])
    return seen


def _scope(fact):
    need('schema-status',fact.get('schema')==SCHEMA and fact.get('status')=='reviewed')
    need('rules',_same(fact['rules'],RULES))
    need('bodies',set(fact['programs'])=={'aiTarget','attackId','refresh','stateTry'})
    names={'aiTarget':('Beyond.Gameplay.AI.CharacterAIComponent','TryCastNormalAttack'),'attackId':('Beyond.Gameplay.Core.AbilitySystem','GetNextAttackId'),'refresh':('Beyond.Gameplay.Core.AbilitySystem','RefreshNextSkillRequest'),'stateTry':('Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterAttackState','_TryCastAttack'),'comboRefresh':('Beyond.Gameplay.Core.AbilitySystem+ComboController','RefreshNextSkillRequest'),'getter':('Beyond.Gameplay.Core.AbilitySystem+ComboController','get_nextSkillId'),'lookup':('Beyond.Gameplay.Core.AbilitySystem','_TryGetSkill'),'canCast':('Beyond.Gameplay.Core.AbilitySystem','CanCastSkill'),'tryCast':('Beyond.Gameplay.Core.AbilitySystem','TryCastSkill'),'clear':('Beyond.Gameplay.Core.AbilitySystem','ClearSkillRequest'),'selfTarget':('Beyond.Gameplay.Core.AbilitySystem','get_selfTargetHandle'),'inheritInfo':('Beyond.Gameplay.Core.AbilitySystem','TryGetInheritedSkillCastInfoForNormalAttack')}
    need('method-coverage',fact['methods'].keys()==names.keys())
    for role,pair in names.items():need('method-nominal-'+role,tuple(fact['methods'][role]['identity'][1:3])==pair)


def _semantics(fact):
    _scope(fact);graphs={key:_graph(rows)for key,rows in fact['programs'].items()};m=fact['markers']
    fields={r['id']:r for r in fact['fields']};offset=lambda key:struct.pack('<i',fields[key]['offset']).hex()
    stack=fact['reviewedStack'];need('stack-slots',all(type(v)is int and 0<=v<=255 for v in stack.values()))
    s=lambda key:bytes([stack[key]]).hex()
    operands=fact['reviewedOperands'];types=operands['cacheSkillTypes']
    need('reviewed-operands',type(operands['stringLengthOffset'])is int and 0<=operands['stringLengthOffset']<=127 and type(operands['refreshCommand'])is int and 0<=operands['refreshCommand']<1<<31 and type(types)is list and len(types)==2 and all(type(v)is int and 0<=v<=127 for v in types)and len(set(types))==2)
    def h(role,marker,expected):need('opcode-'+marker,graphs[role][0].get(m[marker])==bytes.fromhex(expected))
    def call(role,marker,target,tail=False):
        at=m[marker];kind='jump'if tail else'call'
        need('call-'+marker,graphs[role][2][at][2:]==(kind,fact['methods'][target]['identity'][3]))
    def sequence(role,marker,values):
        at=m[marker]
        for value in values:
            raw=bytes.fromhex(value);need('sequence-'+marker,graphs[role][0].get(at)==raw);at+=len(raw)
        return at
    def branch(role,at,opcode,target):
        raw=graphs[role][0][at];need('branch-condition',raw.startswith(bytes.fromhex(opcode))and graphs[role][2][at][2:] ==('branch',m[target]))
    def jumphex(opcode,at,target):
        prefix=bytes.fromhex(opcode);width=1 if len(prefix)==1 else 4
        return(prefix+(m[target]-at-len(prefix)-width).to_bytes(width,'little',signed=True)).hex()
    for role,(nodes,edges,decoded)in graphs.items():
        # Refresh is the sole selected cross-method tail transfer.
        for at,values in list(edges.items()):
            for target in values:
                if target not in nodes:
                    need('external-tail',role=='refresh'and decoded[at][2:] ==('jump',fact['methods']['comboRefresh']['identity'][3]));edges[at]=[]
        _reachable(edges,fact['methods'][role]['identity'][3])
    h('aiTarget','aiEntrySave','488bf1')
    need('entry-target-save',sequence('aiTarget','aiEntrySave',['488bf1','488bda'])==m['aiEntrySave']+6)
    h('aiTarget','aiLoadRefresh','488b8e'+offset('componentAbility'))
    call('aiTarget','aiRefreshCall','refresh');call('aiTarget','aiAttackIdCall','attackId');call('aiTarget','aiCanCastCall','canCast');call('aiTarget','aiTryCall','tryCast')
    # Exact adjacent inputs to Refresh, GetNextAttackId and CanCastSkill.
    at=m['aiRefreshCall'];need('refresh-command',graphs['aiTarget'][0][at-5]==b'\xba'+struct.pack('<I',operands['refreshCommand']))
    h('aiTarget','aiIdSave','488bf8');h('aiTarget','aiLoadCanCast','488b8e'+offset('componentAbility'))
    p=m['aiCanCastCall'];expected=['4533e4','41b101','4c89642430','4c8bc3','4488642428','488bd0','c644242001']
    start=p-sum(len(bytes.fromhex(v))for v in expected)
    for value in expected:need('can-cast-argument-flow',graphs['aiTarget'][0].get(start)==bytes.fromhex(value));start+=len(bytes.fromhex(value))
    # RAX (the selected string pointer) must survive until MOV RDX,RAX.
    at=m['aiIdSave'];values=['488bf8','4885c0'];at+=6
    values.append(jumphex('0f84',at,'aiFalse'));at+=6
    values.append('8378'+bytes([operands['stringLengthOffset']]).hex()+'00');at+=4
    values.append(jumphex('0f86',at,'aiFalse'));at+=6
    values+=['488b8e'+offset('componentAbility'),'4885c9'];at+=10
    values.append(jumphex('0f84',at,'aiThrow'))
    need('selected-name-to-admission',sequence('aiTarget','aiIdSave',values)==p-sum(len(bytes.fromhex(v))for v in expected))
    need('can-cast-result-test',graphs['aiTarget'][0][p+5]==bytes.fromhex('84c0'))
    branch('aiTarget',m['aiCanCastBranch'],'0f84','aiFalse');h('aiTarget','aiFalse','32c0')
    h('aiTarget','aiReloadTryCast','488b8e'+offset('componentAbility'))
    setup=['4885c9',jumphex('74',m['aiTrySetup']+3,'aiThrow'),'8b45'+s('aiOptionsTailSource'),'4533c9','0f1045'+s('aiOptionsSource'),'4c89642448','4c8bc3','4488642440','488bd7','8945'+s('aiOptionsTail'),'488d45'+s('aiInherited'),'4889442438','488d45'+s('aiOptions'),'4c89642430','4c89642428','4889442420','0f2945'+s('aiOptions')]
    # The slots above are the finite reviewed frame grammar; validate their
    # declared relationships rather than claiming arbitrary compiler layouts.
    need('try-call-adjacent',sequence('aiTarget','aiTrySetup',setup)==m['aiTryCall'])
    n,e,d=graphs['aiTarget'];entry=fact['methods']['aiTarget']['identity'][3]
    need('selected-call-marker-adjacency',m['aiAttackIdCall']+5==m['aiIdSave']and m['aiCanCastCall']+7==m['aiCanCastBranch']and m['aiAfterCanCast']==m['aiCanCastBranch']+len(n[m['aiCanCastBranch']]))
    at=entry
    while at!=m['aiEntrySave']:
        need('entry-argument-bridge',at in n and at-entry<64 and d[at][2]=='next'and not(d[at][0]&{1,2})and e[at]==[at+len(n[at])]);at+=len(n[at])
    need('ai-entry-role-reachable',m['aiIdSave']in _reachable(e,entry))
    true_nodes=_reachable(e,m['aiAfterCanCast']);normal_returns={at for at in true_nodes if d[at][2]=='return'}
    need('normal-return-present',normal_returns=={m['aiReturn']})
    without_cast=_reachable(e,m['aiAfterCanCast'],m['aiTryCall']);need('cast-dominates-normal-return',not(normal_returns&without_cast))
    false_nodes=_reachable(e,m['aiFalse']);need('false-skips-cast',m['aiTryCall']not in false_nodes)
    need('try-result-epilogue',d[m['aiTryCall']+5][2:]==('jump',m['aiEpilogue']))
    for at in _reachable(e,m['aiEpilogue']):need('bool-result-preserved',0 not in d[at][0])
    # Keep only nodes on a path from saved selected name to the actual call;
    # early-false epilogues restore registers but do not supply the cast.
    reverse={at:[]for at in n}
    for at,targets in e.items():
        for target in targets:reverse[target].append(at)
    ancestors=_reachable(reverse,m['aiTryCall']);between=_reachable(e,m['aiIdSave']+3)&ancestors
    for at in between:need('selected-id-target-this-not-clobbered',not(d[at][0]&{3,6,7}))
    for at in _reachable(e,m['aiEntrySave']+6)&ancestors:need('entry-target-this-not-clobbered',not(d[at][0]&{3,6}))
    for at in true_nodes&ancestors:need('zero-register-preserved',12 not in d[at][0])
    need('try-receiver-reload-on-path',m['aiReloadTryCast']in between)
    need('receiver-reload-dominates-call',m['aiTryCall']not in _reachable(e,m['aiAfterCanCast'],m['aiReloadTryCast']))
    for at in _reachable(e,m['aiReloadTryCast']+len(n[m['aiReloadTryCast']]),m['aiTryCall'])&ancestors:need('reloaded-try-receiver-preserved',1 not in d[at][0])
    h('refresh','refreshForward','488b89'+offset('combo'))
    refresh_rows=graphs['refresh'][2]
    need('refresh-named-tail',sum(value[2:] ==('jump',fact['methods']['comboRefresh']['identity'][3])for value in refresh_rows.values())==1)
    # Cache branch: selected getter result is retained while lookup writes its
    # own local Skill output. Types zero/one alone reach the cached-id return.
    h('attackId','attackCache','488b8f'+offset('combo'));call('attackId','attackLookup','lookup')
    h('attackId','attackReceiverSave','488bf9')
    values=[];at=m['attackCache']
    def add(value):
        nonlocal at
        values.append(value);at+=len(bytes.fromhex(value))
    def addcall(target):
        add('e8'+struct.pack('<i',fact['methods'][target]['identity'][3]-at-5).hex())
    add('488b8f'+offset('combo'));add('4885c9');add(jumphex('74',at,'attackThrow'));add('33d2');addcall('getter')
    add('488bd8');add('4885c0');add(jumphex('74',at,'attackFallback'));add('8378'+bytes([operands['stringLengthOffset']]).hex()+'00');add(jumphex('76',at,'attackFallback'))
    add('4533c9');add('4c8d4424'+s('lookupOut'));add('488bd0');add('488bcf');addcall('lookup');add('84c0');add(jumphex('74',at,'attackFallback'))
    add('488b4424'+s('lookupOut'));add('4885c0');add(jumphex('74',at,'attackThrow'))
    need('complete-cache-lookup-flow',sequence('attackId','attackCache',values)==m['attackType'])
    h('attackId','attackType','83b8'+offset('skillType')+bytes([types[0]]).hex())
    h('attackId','attackTypeOne','83b8'+offset('skillType')+bytes([types[1]]).hex())
    at=m['attackType']+7;branch('attackId',at,'0f85','attackTypeOne')
    branch('attackId',m['attackTypeOne']+7,'0f85','attackFallback')
    h('attackId','attackReturnCached','488bc3')
    need('type-one-joins-cached',graphs['attackId'][2][m['attackTypeOne']+13][2:]==('jump',m['attackReturnCached']))
    # Optional state path is a separate direct invocation, not the admission
    # helper above: the return Boolean is immediately overwritten, then clear.
    h('stateTry','stateIdSave','488be8');call('stateTry','stateIdCall','attackId');call('stateTry','stateTryCall','tryCast');call('stateTry','stateClearCall','clear')
    h('stateTry','stateReloadTry','488bb0'+offset('entityAbility'))
    need('state-discards-result',graphs['stateTry'][0][m['stateDiscardResult']][:3]==bytes.fromhex('488b05')and m['stateDiscardResult']==m['stateTryCall']+5)
    return dict(rules=dict(RULES),callerSites=dict(aiCanCastReturn=m['aiCanCastCall']+5,aiTryCastReturn=m['aiTryCall']+5,stateTryCastReturn=m['stateTryCall']+5),cacheAcceptedSkillTypes=types)



def _helper_semantics(fact):
    """Prove selected source-register relations over finite byte-decoded CFGs."""
    h=fact['helperDelivery'];programs=h['programs'];m=h['markers'];fields={r['id']:r for r in h['fields']}
    need('helper-program-coverage',set(programs)=={'selectedHelper','referenceCarrier','referenceWriter','sharedMapGet'})
    need('helper-field-coverage',set(fields)=={'activeMap','skillId'})
    graphs={k:_graph(v['instructions'],helper=True) for k,v in programs.items()}
    for role,(nodes,edges,decoded) in graphs.items():
        # Every edge must land on a wholly decoded owned instruction. Calls
        # are interprocedural boundaries, never opaque instruction text.
        need('helper-owned-edges',all(t in nodes for targets in edges.values() for t in targets))
        reached=_reachable(edges,programs[role]['entryRva'])
        need('helper-normal-return',any(decoded[a][2]=='return' for a in reached))
    n,e,d=graphs['selectedHelper'];entry=programs['selectedHelper']['entryRva']
    def exact(at,hex_value):need('helper-opcode',n.get(at)==bytes.fromhex(hex_value))
    def sequence(at,values):
        for value in values:exact(at,value);at+=len(bytes.fromhex(value))
        return at
    def target(at,rva):need('helper-direct-call',d[at][2:]==('call',rva))
    def reverse(edges):
        result={a:[] for a in edges}
        for a,targets in edges.items():
            for b in targets:result[b].append(a)
        return result
    back=reverse(e)
    def paths(a,b):return _reachable(e,a)&_reachable(back,b)
    def dominates(a,b):need('helper-dominates',b not in _reachable(e,entry,a))
    oldgraphs={k:_graph(rows)for k,rows in fact['programs'].items()}
    caller=h['sourceCaller'];need('helper-source-owner',caller['owner']=='stateTry')
    old=oldgraphs['stateTry'];at=caller['rva']
    need('helper-source-direct-call',old[2][at][2:]==('call',entry))
    need('helper-source-this-and-MI',old[0].get(at-5)==bytes.fromhex('33d2') and old[0].get(at-3)==bytes.fromhex('488bcb'))
    source_save=caller['thisSaveRva'];need('helper-source-this-save',old[0].get(source_save)==bytes.fromhex('488bd9'))
    oldreverse=reverse(old[1])
    need('helper-source-this-dominates',at not in _reachable(old[1],fact['methods']['stateTry']['identity'][3],source_save))
    for a in _reachable(old[1],source_save+3)&_reachable(oldreverse,at):need('helper-source-this-nonvolatile',3 not in old[2][a][0])
    exact(m['entryThisSave'],'488bd9')
    for a in paths(entry,m['entryThisSave']):
        if a!=m['entryThisSave']:need('helper-entry-this-preserved',1 not in d[a][0])
    # Both direct Try sites must be dominated by the entry save, selected
    # Dictionary return assignment, and their own typed receiver/name loads.
    off=lambda key:struct.pack('<i',fields[key]['offset']).hex()
    oldfields={r['id']:r for r in fact['fields']}
    entity=bytes([oldfields['stateEntity']['offset']]).hex();ability=struct.pack('<i',oldfields['entityAbility']['offset']).hex()
    exact(m['firstIdReceiver'],'488b43'+entity)
    exact(m['secondIdReceiver'],'488b43'+entity)
    for marker in ('firstIdCall','secondIdCall'):target(m[marker],fact['methods']['attackId']['identity'][3])
    # The two receiver reloads independently read the same declared field;
    # equality of values across helper calls remains a stated premise.
    for start,call in ((m['firstIdReceiver'],m['firstIdCall']),(m['secondIdReceiver'],m['secondIdCall'])):
        branch_nodes=paths(start,call)
        loads=[a for a in branch_nodes if n[a]==bytes.fromhex('488b88'+ability)]
        need('helper-getter-typed-receiver',len(loads)==1)
        for a in paths(loads[0]+len(n[loads[0]]),call)-{call}:
            need('helper-getter-receiver-preserved',1 not in d[a][0])
    exact(m['mapLoad'],'488bb9'+off('activeMap'))
    need('helper-map-before-second-id',m['mapLoad'] in paths(m['secondIdReceiver'],m['secondIdCall']))
    for a in paths(m['mapLoad']+len(n[m['mapLoad']]),m['mapGetCall'])-{m['mapGetCall']}:
        need('helper-map-register-preserved',7 not in d[a][0])
    need('helper-id-to-typed-map-adjacency',m['secondIdCall']+5 in n and n[m['secondIdCall']+5]==bytes.fromhex('4885ff'))
    ctx=h['typedActiveMapContext'];need('helper-context-marker',ctx['instructionRva']==m['contextLoad'])
    end=sequence(m['contextLoad'],[ctx['instructionHex'],'488bd0','488bcf'])
    need('helper-map-call-adjacent',end==m['mapGetCall'])
    need('helper-map-call-direct',d[end][2:]==('call',h['typedActiveMapCallTargetRva']))
    for a in paths(m['secondIdCall']+5,m['mapGetCall'])-{m['mapGetCall']}:need('helper-getter-key-not-clobbered',0 not in d[a][0])
    exact(m['selectedSkillSave'],'488bf8');need('helper-map-return-save',end+5==m['selectedSkillSave'])
    # The actual typed method context is separately derived from native bytes.
    need('helper-map-method-context',ctx['typeName']=='System.Collections.Generic.Dictionary`2' and ctx['methodName']=='get_Item'
        and ctx['classArguments']==['string','Beyond.Gameplay.Core.Skill'] and ctx['methodArguments']==[])
    # Preserve volatile R10/R11 by decoding all reachable instructions in the
    # actual carrier callees, not by assuming the ordinary Win64 ABI does so.
    wn,we,wd=graphs['referenceWriter'];writer=programs['referenceWriter']['entryRva']
    for a in _reachable(we,writer):
        need('helper-writer-no-calls',wd[a][2] not in ('call','indirect-call'))
        need('helper-writer-preserves-r10-r11',not wd[a][0]&{10,11})
    cn,ce,cd=graphs['referenceCarrier'];carrier=programs['referenceCarrier']['entryRva']
    calls=[]
    for a in _reachable(ce,carrier):
        if cd[a][2]=='call':
            need('helper-carrier-writer-call',cd[a][3]==writer and a==m['carrierInnerCall']);calls.append(a)
        else:
            need('helper-carrier-no-indirect-call',cd[a][2]!='indirect-call')
            need('helper-carrier-preserves-r10-r11',not cd[a][0]&{10,11})
    need('helper-carrier-one-writer',len(calls)==1)
    gn,ge,gd=graphs['sharedMapGet'];g=h['sharedMapGet'];get_entry=programs['sharedMapGet']['entryRva']
    need('helper-shared-physical-target',h['typedActiveMapCallTargetRva']==get_entry)
    def gexact(at,value):need('helper-shared-map-opcode',gn.get(at)==bytes.fromhex(value))
    def gsequence(at,values):
        for v in values:gexact(at,v);at+=len(bytes.fromhex(v))
        return at
    gexact(g['thisSave'],'488bd9');gexact(g['keySave'],'488bf2')
    need('helper-shared-find-arguments',gsequence(g['mapArguments'],['488b4720','488bd6','488bcb','4c8b80c0000000','4d8b80b0000000'])==g['findEntryCall'])
    need('helper-shared-find-index-call',gd[g['findEntryCall']][2:]==('call',g['findEntryTargetRva']))
    need('helper-shared-slot-layout',g['entryArrayOffset']==24 and g['arrayLengthOffset']==24 and
        g['entryStrideBytes']==24 and g['arrayHeaderBytes']==32 and g['valueOffsetInEntry']==16)
    need('helper-shared-index-next',g['findEntryCall']+5==g['entryIndex'])
    gexact(g['entryIndex'],'4863c8');gexact(g['entryIndex']+3,'85c0')
    branch=gn[g['negativeBranch']];need('helper-shared-negative-index-branch',branch[:2]==b'\x0f\x88' and g['negativeBranch']==g['entryIndex']+5)
    # Negative indices and out-of-array unsigned indices must never reach the
    # selected normal return. Every successful return passes the exact load.
    for a in _reachable(ge,get_entry)&_reachable(reverse(ge),g['thisSave']):need('helper-shared-entry-this-preserved',1 not in gd[a][0])
    for marker in (g['thisSave'],g['keySave']):need('helper-shared-input-dominates',g['findEntryCall'] not in _reachable(ge,get_entry,marker))
    reverse_get=reverse(ge);ancestors=_reachable(reverse_get,g['successReturn'])
    need('helper-shared-negative-rejected',gd[g['negativeBranch']][3] not in ancestors)
    need('helper-shared-index-fallthrough',g['entriesLoad']==g['negativeBranch']+6)
    gexact(g['entriesLoad'],'488b43'+bytes([g['entryArrayOffset']]).hex())
    gexact(g['boundsCompare'],'3b48'+bytes([g['arrayLengthOffset']]).hex())
    gexact(g['boundsBranch'],'73'+gn[g['boundsBranch']][1:].hex())
    need('helper-shared-bounds-rejected',gd[g['boundsBranch']][3] not in ancestors and g['boundsBranch']==g['boundsCompare']+3)
    gexact(g['valueAddress'],'4883c102')
    need('helper-shared-value-address',gsequence(g['valueAddress'],['4883c102','488b742438','488d0c49','488b04c8'])==g['valueLoad']+len(gn[g['valueLoad']]))
    gexact(g['valueLoad'],'488b04c8');gexact(g['successReturn'],'c3')
    for a in _reachable(ge,g['thisSave']+len(gn[g['thisSave']]))&_reachable(reverse_get,g['entriesLoad']):need('helper-shared-this-preserved',3 not in gd[a][0])
    for a in _reachable(ge,g['keySave']+len(gn[g['keySave']]))&_reachable(reverse_get,g['findEntryCall']):need('helper-shared-key-preserved',6 not in gd[a][0])
    for a in _reachable(ge,g['entryIndex']+len(gn[g['entryIndex']]))&_reachable(reverse_get,g['boundsCompare']):need('helper-shared-index-preserved',1 not in gd[a][0])
    for a in _reachable(ge,g['entriesLoad']+len(gn[g['entriesLoad']]))&(_reachable(reverse_get,g['valueLoad'])-{g['valueLoad']}):need('helper-shared-entries-preserved',0 not in gd[a][0])
    for marker in (g['findEntryCall'],g['entryIndex'],g['entriesLoad'],g['boundsCompare'],g['boundsBranch'],g['valueLoad']):
        need('helper-shared-success-dominated',g['successReturn'] not in _reachable(ge,get_entry,marker))
    for a in _reachable(ge,g['valueLoad']+len(gn[g['valueLoad']]))&ancestors:
        need('helper-shared-return-pointer-preserved',0 not in gd[a][0])
    sites=h['castSites'];need('helper-two-cast-sites',len(sites)==2 and len({s['callRva'] for s in sites})==2)
    for site in sites:
        call=site['callRva'];target(call,fact['methods']['tryCast']['identity'][3])
        need('helper-call-return',site['returnRva']==call+5)
        for marker in (m['entryThisSave'],m['selectedSkillSave'],site['receiverReload'],site['nameLoad']):dominates(marker,call)
        for a in paths(m['entryThisSave']+len(n[m['entryThisSave']]),call)-{call}:
            need('helper-this-nonvolatile',3 not in d[a][0])
        for a in paths(m['selectedSkillSave']+len(n[m['selectedSkillSave']]),call)-{call}:
            need('helper-selected-skill-nonvolatile',7 not in d[a][0])
        exact(site['receiverReload'],'488b43'+entity)
        receiver_loads=[a for a in paths(site['receiverReload'],site['nameLoad']) if n[a]==bytes.fromhex('4c8b90'+ability)]
        need('helper-Try-receiver-load',len(receiver_loads)==1)
        exact(site['nameLoad'],'4c8b9f'+off('skillId'))
        target(site['carrierCall'],carrier)
        need('helper-Try-register-setup',sequence(site['argumentSetup'],['4c8bc0','498bd3','498bca'])==call)
        need('helper-carrier-before-args',site['carrierCall']<site['argumentSetup'])
        for a in paths(receiver_loads[0]+len(n[receiver_loads[0]]),site['argumentSetup'])-{site['argumentSetup']}:
            writes=d[a][0]
            if a==site['carrierCall']:writes=writes-{10,11}
            if a==site['nameLoad']:writes=writes-{11}
            need('helper-Try-volatile-carriers',not writes&{10,11})
        need('helper-selected-site-reachable',call in _reachable(e,entry))
    return dict(selectedHelperCallerSites=[s['returnRva'] for s in sites],
        selectedHelperSourceChainProved=True,typedActiveMapGetProved=True,
        selectedSkillIdToTryArgumentProved=True,volatileCarrierPreservationProved=True,
        repeatedGetterResultsOrReloadedReceiversEquated=False,earlierRefreshWinnerProved=False,
        evidenceBoundary=h['evidenceBoundary'])


def _validate_helper(image,fact):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    h=fact['helperDelivery'];fields=_validate_fields(image,h['fields'])
    expected={'activeMap':('Beyond.Gameplay.Core.AbilitySystem','m_activeSkillMap','System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.Core.Skill>',21),
        'skillId':('Beyond.Gameplay.Core.Skill','m_skillId','string',14)}
    need('helper-fields-nominal',fields.keys()==expected.keys())
    for key,values in expected.items():need('helper-field-identity',tuple(fields[key][k]for k in ('type','name','valueType','ordinaryKind'))==values)
    for role,p in h['programs'].items():
        windows=p['windows'];image.check_windows(windows,label='skillNormalAttackDelivery.helper')
        declared=sorted([w['startRva'],w['endRva']]for w in windows)
        need('helper-entry-window',p['entryRva']==declared[0][0])
        if p['ownership']=='unwind-family':
            actual=sorted(r['runtimeTriple'][:2]for r in image.unwind_index.family(p['entryRva'])['ranges'])
            need('helper-complete-family',actual==declared)
        else:
            need('helper-leaf-role',role=='referenceWriter' and p['ownership']=='leaf-ret-int3' and len(windows)==1)
            end=declared[0][1];need('helper-leaf-terminal-ret',p['instructions'][-1]==dict(rva=end-1,hex='c3'))
            padding=(-end)%16;need('helper-leaf-padding',padding>0 and image.pe.bytes_at_va(image.pe.image_base+end,padding)==b'\xcc'*padding)
        rows=p['instructions'];cursor=0
        for start,end in declared:
            at=start
            while cursor<len(rows) and rows[cursor]['rva']<end:
                row=rows[cursor];raw=bytes.fromhex(row['hex']);need('helper-complete-instructions',row['rva']==at and image.pe.bytes_at_va(image.pe.image_base+at,len(raw))==raw)
                _decode(raw,at,helper=True);at+=len(raw);cursor+=1
            need('helper-complete-window',at==end)
        need('helper-complete-program-count',cursor==len(rows))
    context=derive_typed_usage_context(image,h['markers']['contextLoad'],label='skillNormalAttackDelivery.helper')
    need('helper-typed-context',_same(context,h['typedActiveMapContext']))
    from scripts.game_data.il2cpp.context import generic_method_candidates
    reg=image.registration;pe=image.pe;code=image.mapper.code_registration_summary(pe,image.code_registration)
    table=int(reg['genericMethodTable'],16)
    candidates=generic_method_candidates(pe.bytes_at_va(table,reg['genericMethodTableCount']*16),reg['genericMethodTableCount'],
        reg['methodSpecsCount'],{context['methodSpecIndex']},code['genericMethodPointersCount'],code['invokerPointersCount'],
        source='skillNormalAttackDelivery.helper',offset=table)
    # A missing stored MethodSpec table row is an authenticated absence, not
    # a fabricated direct generic registration. The reached shared body is
    # separately framed and its successful reference-slot return is proved.
    result=_helper_semantics(fact)
    result['storedMethodSpecCandidates']=candidates
    result['methodSpecDirectRegistrationClaimed']=False
    result['sharedPhysicalSuccessfulReferenceSlotReturnProved']=True
    return result


def _validate(image,fact):
    _scope(fact);cx=NativeReferenceContext(image);fields=_validate_fields(image,fact['fields']);base=image.pe.image_base
    expected={'componentAbility':('Beyond.Gameplay.AI.CharacterAIComponent','m_abilitySystem','Beyond.Gameplay.Core.AbilitySystem',18),'combo':('Beyond.Gameplay.Core.AbilitySystem','m_comboController','Beyond.Gameplay.Core.AbilitySystem+ComboController',18),'skillType':('Beyond.Gameplay.Core.Skill','<skillType>k__BackingField','Beyond.Gameplay.SkillType',17),'stateEntity':('Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateBase','m_entity','Beyond.Gameplay.Core.Entity',18),'entityAbility':('Beyond.Gameplay.Core.Entity','<abilityCom>k__BackingField','Beyond.Gameplay.Core.AbilitySystem',18)}
    need('field-coverage',fields.keys()==expected.keys())
    for key,values in expected.items():need('field-identity',tuple(fields[key][k]for k in('type','name','valueType','ordinaryKind'))==values)
    for role,row in fact['methods'].items():
        index=image.validate_method_row(row['identity'],label='skillNormalAttackDelivery');method=image.metadata.methods[index]
        need('method-signature',not method.flags&0x10 and cx.type_name(method.return_type)==row['returnType']and [dict(name=image.metadata.string(p.name_index),type=cx.type_name(p.type_index))for p in image.metadata.parameters_for(method)]==row['parameters'])
    image.check_windows(fact['codeWindows'],label='skillNormalAttackDelivery')
    for role,rows in fact['programs'].items():
        actual=sorted(r['runtimeTriple'][:2]for r in image.unwind_index.family(fact['methods'][role]['identity'][3])['ranges'])
        declared=sorted([r['startRva'],r['endRva']]for r in fact['codeWindows']if r['owner']==role)
        need('complete-family',actual==declared)
        cursor=0
        for a,b in declared:
            at=a
            while cursor<len(rows)and rows[cursor]['rva']<b:
                row=rows[cursor];raw=bytes.fromhex(row['hex']);need('complete-program-bytes',row['rva']==at and image.pe.bytes_at_va(base+at,len(raw))==raw);at+=len(raw);cursor+=1
            need('complete-program-range',at==b)
        need('complete-program-count',cursor==len(rows))
    result=_semantics(fact);result['helperDelivery']=_validate_helper(image,fact);return result


def validate_current_native_contract(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema='endfield.skill-normal-attack-delivery-native-audit.v2',status='validation_failed',rules={},rows=[])
    try:
        sources=[Path(__file__),path,Path(__file__).parent/'il2cpp/native_image.py',Path(__file__).parent/'il2cpp/reference_layouts.py',Path(__file__).parent/'il2cpp/formatter_composition.py',Path(__file__).parent/'il2cpp/context.py',Path(__file__).parent/'skill_timing_runtime_native.py',REPO_ROOT/'scripts/common.py',REPO_ROOT/'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py',REPO_ROOT/'tools/endfield-il2cpp/catalog_option_flow_metadata.py']
        def sourcepins():return {str(p.resolve()):dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sources}
        before=sourcepins()
        raw=path.read_bytes();fact=json.loads(raw);_scope(fact);pins=fact['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(gameassembly),metadata=Path(metadata))
        if gate.status!='validated':return dict(audit,status=gate.status,detail=gate.detail)
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),fact)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        source_after=sourcepins();need('source-bookend',after.status=='validated'and raw==path.read_bytes() and before==source_after)
        audit.update(sourceBookends=dict(before=before,after=source_after,matched=True),contractSource=before[str(path.resolve())],sourceDependencies={p:pin['sha256'] for p,pin in before.items()},status='validated',nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'],**result)
        audit['rows']=[dict(id='selectedNormalAttackDirectDelivery',evidence='conditional',**result)]
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:audit.update(status='validation_failed',rules={},rows=[],detail=str(error)[:1600])
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH);parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_normal_attack_delivery_native.json');args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('--output must be below reports/')
    result=validate_current_native_contract(gameassembly=args.gameassembly,metadata=args.metadata,contract_path=args.contract)
    if result['status']=='validated':args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));return 0 if result['status']=='validated'else 2


if __name__=='__main__':raise SystemExit(main())
