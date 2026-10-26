"""Typed closed-Data receiver flow and guarded AI blackboard lookup selection.

The selected prefix and five lookup blocks are proved from complete owned
instruction spans. Getter/conversion/write regions elsewhere in the body remain
outside this proof. Static MethodSpec contexts are not live MethodInfo objects.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any

from .instance_string_field_calls import _at, _raw, _require, _branch, _call, _disp, _owner, _type, _instance_field_type
from .reference_layouts import NativeReferenceContext, single_reference_generic_field
from .context import method_spec_usage_index
from .generic_entries import GenericEntries
from .protocol import runtime_type_name

MODE='closed-data-ai-blackboard-selector-and-null-fallback-lookups'


def validate_program(rows: list[dict], *, fields: dict, methods: dict, enum_members: dict) -> dict:
    """Prove the prefix, three selector edges and all five owned lookup calls."""
    raw=[_raw(r) for r in rows];by={_at(r):i for i,r in enumerate(rows)}
    _require(len(by)==len(rows) and bool(rows), 'ai-body-rows', 'unique owned instruction entries', len(rows))
    for a,b in zip(rows,rows[1:]):
        _require(_at(a)+len(_raw(a))==_at(b), 'ai-body-contiguity', a,b)
    guard=[i for i,r in enumerate(rows) if len(raw[i])==5 and raw[i][0]==0xe8 and _call(r)==methods['guard']]
    _require(len(guard)==1,'ai-guard','one assembly-owned patch guard',guard)
    g=guard[0]
    _require(raw[g+1]==b'\x84\xc0','ai-guard-result','TEST AL',rows[g+1])
    patch=_branch(rows[g+2],opcode=b'\x0f\x85')
    cursor=g+3
    prefix_start=cursor
    alias=[i for i,b in enumerate(raw[:g]) if b==b'\x48\x8b\xf9']
    input_alias=[i for i,b in enumerate(raw[:g]) if b==b'\x48\x8b\xda']
    _require(len(alias)==len(input_alias)==1, 'ai-entry-aliases', 'RDI=incoming RCX, RBX=incoming RDX', [alias,input_alias])
    _require(all((r.get('write') or {}).get('register') not in ('rcx','ecx','cx','cl','ch')
                 and not r['text'].startswith(('call ','j')) for r in rows[:alias[0]]),
             'ai-incoming-this','incoming RCX retained until its saved alias',rows[:alias[0]])
    _require(all((r.get('write') or {}).get('register') not in ('rdx','edx','dx','dl','dh')
                 and not r['text'].startswith(('call ','j')) for r in rows[:input_alias[0]]),
             'ai-incoming-handle','incoming RDX retained until its saved alias',rows[:input_alias[0]])
    for i in range(alias[0]+1,g+3):
        _require((rows[i].get('write') or {}).get('register') not in ('rdi','edi','di','dil'),
                 'ai-this-alias-preserved','RDI remains this before target call',rows[i])
    for i in range(input_alias[0]+1,g+3):
        _require((rows[i].get('write') or {}).get('register') not in ('rbx','ebx','bx','bl','bh'),
                 'ai-input-alias-preserved','RBX retains the input handle before target call',rows[i])

    def take(expected):
        nonlocal cursor
        actual=raw[cursor]
        _require(actual==expected,'ai-selected-instruction',expected.hex(),rows[cursor])
        _require(not rows[cursor]['text'].startswith('db '),'ai-selected-boundary','decoded complete instruction',rows[cursor])
        row=rows[cursor];cursor+=1;return row

    def edge(opcode,target=None):
        nonlocal cursor
        row=rows[cursor];cursor+=1
        return _branch(row,opcode=opcode,target=target)

    def call(expected=None):
        nonlocal cursor
        row=rows[cursor];cursor+=1;target=_call(row)
        if expected is not None:_require(target==expected,'ai-direct-callee',hex(expected),row)
        return row

    data=fields['data'];key=fields['key']
    take(_disp(b'\x48\x8b\x57',data));take(b'\x48\x85\xd2');failure=edge(b'\x0f\x84')
    take(_disp(b'\x48\x8b\x52',fields['target']));take(b'\x45\x33\xc9')
    take(b'\x4c\x8b\xc3');take(b'\x48\x8b\xcf');target_call=call(methods['target'])
    take(b'\x48\x85\xc0');early_return=edge(b'\x0f\x84')
    take(_disp(b'\x48\x8b\x40',fields['entity']));take(b'\x48\x85\xc0');edge(b'\x0f\x84',failure)
    expected=b'\x48\x8b\x88'+fields['enemyAI'].to_bytes(4,'little',signed=True)
    take(expected);take(b'\x48\x85\xc9');null_ai=edge(b'\x74')
    take(b'\x45\x33\xc0');take(b'\x33\xd2');parent_call=call(methods['parentBlackboard'])
    take(b'\x48\x8b\xd8');join=edge(b'\xeb')
    _require(_at(rows[cursor])==null_ai,'ai-null-component-edge','XOR EBX reached by null EnemyAI component',hex(null_ai))
    take(b'\x33\xdb');_require(_at(rows[cursor])==join,'ai-blackboard-join','same blackboard/null join',hex(join))
    init=raw[cursor]
    _require(len(init)==7 and init[:3]==b'\x48\x8b\x0d','ai-init-cell','RIP-relative class cell',rows[cursor]);cursor+=1
    call() # No class-initializer behavior is inferred; its ordinary ABI is conditional.
    take(b'\x45\x33\xc0');take(b'\x33\xd2');take(b'\x48\x8b\xcb');eq_call=call(methods['nullEquality'])
    take(b'\x84\xc0');edge(b'\x0f\x85',early_return)
    take(_disp(b'\x48\x8b\x4f',data));take(b'\x48\x85\xc9');edge(b'\x0f\x84',failure)
    take(_disp(b'\x8b\x49',fields['selector']));take(b'\x85\xc9');float_entry=edge(b'\x0f\x84')
    sub=raw[cursor];_require(len(sub)==3 and sub[:2]==b'\x83\xe9','ai-selector-sub','SUB ECX, sign-extended imm8',rows[cursor]);cursor+=1
    string_entry=edge(b'\x0f\x84')
    cmp=raw[cursor];_require(len(cmp)==3 and cmp[:2]==b'\x83\xf9','ai-selector-cmp','CMP ECX, sign-extended imm8',rows[cursor]);cursor+=1
    no_value_return=edge(b'\x0f\x85')
    subtract=int.from_bytes(sub[2:],'little',signed=True);compare=int.from_bytes(cmp[2:],'little',signed=True)
    actual={'Float':0,'String':subtract&0xffffffff,'Vector3':(subtract+compare)&0xffffffff}
    _require(actual=={k:v&0xffffffff for k,v in enum_members.items()},'ai-enum-selector',enum_members,actual)
    selector_end=cursor
    _require(all(not r['text'].startswith('db ') for r in rows[:selector_end]),
             'ai-prefix-decoded','all selected entry/prefix instruction boundaries supported',None)
    lookups=[]

    def context_row():
        nonlocal cursor
        row=rows[cursor];b=raw[cursor];cursor+=1
        _require(len(b)==7 and b[:3]==b'\x4c\x8b\x05','ai-lookup-context','complete RIP-relative R8 load',row)
        return row

    def lookup(route,expected_type,*,vector=False,last=False):
        nonlocal cursor
        start=cursor
        if vector:
            take(_disp(b'\x48\x8b\x47',data));take(b'\x48\x8b\xcb');ctx=context_row()
            take(_disp(b'\x48\x8b\x50',key))
        else:
            take(_disp(b'\x48\x8b\x57',data));take(b'\x48\x85\xd2');edge(b'\x0f\x84',failure)
            ctx=context_row();take(b'\x48\x8b\xcb');take(_disp(b'\x48\x8b\x52',key))
        c=call(methods['lookup']);take(b'\x48\x8b\xd8' if vector or last else b'\x48\x8b\xf0')
        take(b'\x48\x85\xc0')
        nonnull_jump=None
        if route=='Float' and not last:
            nonnull_jump=edge(b'\x0f\x85')
            _require(nonnull_jump in by and nonnull_jump>_at(rows[cursor]),
                     'ai-fallback-success','owned forward nonnull edge',hex(nonnull_jump))
        else:
            edge(b'\x0f\x84',no_value_return)
        lookups.append({'route':route,'staticMethodArgument':expected_type,'startVa':_at(rows[start]),
            'endVa':_at(rows[cursor]),'callVa':_at(c),'contextLoadVa':_at(ctx),
            'sourceKeyField': 'aiBBKey','receiverOrigin':'GetParentBlackboard return after false Unity null equality',
            'sourceKeyReloaded':True,'nonnullJumpVa':nonnull_jump,'fallbackOnNull':route=='Float' and not last})

    vector_entry=_at(rows[cursor]);lookup('Vector3','UnityEngine.Vector3',vector=True)
    _require(string_entry in by and float_entry in by,'ai-route-entries','owned String/Float instruction boundaries',[string_entry,float_entry])
    cursor=by[string_entry];lookup('String','string')
    cursor=by[float_entry]
    for n,name in enumerate(('float','int','bool')):lookup('Float',name,last=n==2)
    for item in lookups:
        _require(all(not r['text'].startswith('db ') for r in rows[by[item['startVa']]:by[item['endVa']]]),
                 'ai-lookup-decoded','complete selected lookup fragment',item)
    first,last=lookups[-3]['startVa'],lookups[-1]['endVa']
    _require(all(item['nonnullJumpVa'] is None or not first<=item['nonnullJumpVa']<last for item in lookups),
             'ai-fallback-success-exits','nonnull earlier lookup skips later lookup blocks',lookups)
    early=validate_early_return(rows,early_return,expected_value=False)
    no_value=validate_early_return(rows,no_value_return,expected_value=True)
    _require(early_return!=no_value_return and early['epilogueVa']==no_value['epilogueVa'],
             'ai-return-leaves','distinct false/true leaves using the same matched epilogue',[early,no_value])
    return {'lookups':lookups,'selectorEntries':{'Float':float_entry,'String':string_entry,'Vector3':vector_entry},
        'targetCallVa':_at(target_call),'parentBlackboardCallVa':_at(parent_call),'nullEqualityCallVa':_at(eq_call),
        'prefixStartVa':_at(rows[prefix_start]),'prefixEndVa':_at(rows[selector_end]),
        'earlyReturnVa':early_return,'earlyReturn':early,'noValueReturnVa':no_value_return,
        'noValueReturn':no_value,'failureVa':failure,'patchEntryVa':patch,
        'patchResultCondition':False,'parentBlackboardInitArgument':False,'unityNullEqualityResultCondition':False,
        'floatFallbackOrder':['float','int','bool'],'completeGetterOrWriteFlowProved':False,
        'runtimeExecutionKnown':False,'liveGenericContextSelected':False}


def validate_early_return(rows,entry,*,expected_value):
    """Decode the selected two-byte return leaf and match its saved-register frame.

    The legacy decoder splits XOR AL,AL into two db rows. This byte profile
    independently recognizes its complete two-byte instruction; it does not
    treat either db row as a decoded instruction or extend the getter profile.
    """
    raw=[_raw(r) for r in rows];by={_at(r):i for i,r in enumerate(rows)}
    _require(entry in by,'ai-early-return-owner','owned instruction entry',hex(entry))
    i=by[entry];body=b''.join(raw);offset=entry-_at(rows[0])
    expected=b'\xb0\x01' if expected_value else b'\x32\xc0'
    _require(body[offset:offset+2]==expected and entry+2 in by,
             'ai-early-return-value',expected.hex(),body[offset:offset+2].hex())
    epilogue=_branch(rows[by[entry+2]],opcode=b'\xeb')
    _require(epilogue in by and epilogue>entry,'ai-return-epilogue-owner','owned forward epilogue',hex(epilogue))
    j=by[epilogue]
    _require(raw[0]==b'\x48\x8b\xc4' and raw[5]==b'\x55' and
             len(raw[6])==7 and raw[6][:3]==b'\x48\x8d\xa8',
             'ai-return-prologue','saved entry RSP, nonvolatile stores and PUSH RBP',raw[:7])
    reserve=raw[7]
    _require(len(reserve)==7 and reserve[:3]==b'\x48\x81\xec',
             'ai-return-frame-reserve','SUB RSP,imm32',rows[7])
    size=int.from_bytes(reserve[3:],'little',signed=True)
    _require(0<size<=65536 and size%16==0,'ai-return-frame-size','bounded aligned frame reserve',size)
    expected=[b'\x4c\x8d\x9c\x24'+size.to_bytes(4,'little'),]
    for k,save,restore in ((1,b'\x48\x89\x58',b'\x49\x8b\x5b'),
                           (2,b'\x48\x89\x70',b'\x49\x8b\x73'),
                           (3,b'\x48\x89\x78',b'\x49\x8b\x7b'),
                           (4,b'\x4c\x89\x70',b'\x4d\x8b\x73')):
        _require(len(raw[k])==4 and raw[k][:3]==save and raw[k][3]<120,
                 'ai-return-register-save','owned nonvolatile save to entry RSP',rows[k])
        expected.append(restore+bytes([raw[k][3]+8]))
    expected.extend((b'\x49\x8b\xe3',b'\x5d',b'\xc3'))
    _require(raw[j:]==expected and all(not r['text'].startswith('db ') for r in rows[j:]),
             'ai-return-epilogue','matched restores, MOV RSP,R11, POP RBP, plain RET',rows[j:])
    return {'returnValue':expected_value,'entryVa':entry,'epilogueVa':epilogue,
            'completeLeafAndMatchedEpilogueProved':True,
            'condition':'selected path with a coherent unchanged frame and successful valid-memory restores'}


def _method(image, spec):
    owner=_owner(image,spec['type'],assembly=spec['image'])
    methods=[m for m in image.metadata.methods_for(owner) if image.metadata.string(m.name_index)==spec['method']]
    candidates=[{'methodIndex':m.index,'genericContainerIndex':m.generic_container_index,'flags':m.flags} for m in methods]
    if 'genericArity' in spec:
        methods=[m for m in methods if _generic_arity(image.metadata,m)==spec['genericArity']]
    _require(len(methods)==1,'ai-method-owner','one assembly/signature-owned method',
             {'selector':spec,'namedCandidates':candidates,'selected':[m.index for m in methods]})
    return methods[0]


def _generic_arity(metadata,method):
    if method.generic_container_index<0:return 0
    section=metadata.sections['genericContainers'];at=section.offset+method.generic_container_index*16
    _require(section.offset<=at<=section.offset+section.size-16,'ai-generic-container','owned metadata container',at)
    owner,count,is_method,parameter=struct.unpack_from('<iiii',metadata.buf,at)
    _require(owner==method.index and is_method==1 and 0<count<=64 and parameter>=0,
             'ai-generic-owner','method-owned bounded generic parameter list',[owner,count,is_method,parameter])
    return count


def _field(context, qualified, expected_type):
    owner,t,offset=context.field(qualified)
    td=_owner(context.image,owner)
    name=qualified.partition('::')[2]
    field=[f for f in context.image.metadata.fields_for(td) if context.image.metadata.string(f.name_index)==name]
    _require(len(field)==1 and _instance_field_type(context.image,field[0].type_index)==(0x12,expected_type,False),
             'ai-field-reference','unique instance class reference',qualified)
    _require(t==expected_type,'ai-field-type',expected_type,t)
    return offset


def _ancestor(context,name,owner):
    seen=set()
    while name not in ('','object','System.Object'):
        _owner(context.image,name)
        if name==owner:return
        _require(name not in seen and len(seen)<64,'ai-ancestry','bounded unambiguous non-generic ancestry',name)
        seen.add(name);name=context.parent(name)
    _require(False,'ai-inherited-owner',owner,seen)


def prove(index, claim):
    image=index.image
    _require(claim.get('mode')==MODE,'ai-claim-mode',MODE,claim.get('mode'))
    owner=_owner(image,claim['type'])
    current=[m for m in image.metadata.methods_for(owner) if image.metadata.string(m.name_index)==claim['method']]
    _require(len(current)==1,'ai-caller-definition','one selected caller definition',len(current));method=current[0]
    _require(not method.flags&0x10 and method.generic_container_index<0 and _type(image,method.return_type)==(2,'bool',False),
             'ai-caller-ABI','instance, nongeneric, direct Boolean return',method.index)
    ptr=image.method_pointer_va(method)
    _require(ptr in index.extents and not index.chained_fragments.get(ptr),'ai-caller-unwind','exact primary body with no unowned fragments',hex(ptr))
    size=index.extents[ptr]-ptr;_require(0<size<=8192,'ai-body-bound','bounded positive primary body',size)
    rows=index._decode(ptr,size)
    _require(sum(len(_raw(r)) for r in rows)==size,'ai-full-byte-coverage',size,len(rows))
    context=NativeReferenceContext(image,index=index)
    for name in (claim['type'],claim['dataType'],claim['enumType'],'Beyond.Gameplay.Core.AbilityAction`1',
                 'Beyond.Gameplay.Core.AbilityAction'):_owner(image,name)
    parent=context.parent(claim['type'])
    _require(parent=='Beyond.Gameplay.Core.AbilityAction`1<'+claim['dataType']+'>','ai-closed-parent','exact Data argument',parent)
    layout=single_reference_generic_field(context,owner=parent,field=claim['dataField'],witness=claim['type'])
    data_td=_owner(image,claim['dataType'])
    for name,kind,typename in ((claim['targetField'],0x12,'Beyond.Gameplay.Core.TargetSettings'),
                               (claim['selectorField'],0x11,claim['enumType']),(claim['keyField'],0x0e,'string')):
        fields=[f for f in image.metadata.fields_for(data_td) if image.metadata.string(f.name_index)==name]
        _require(len(fields)==1 and _instance_field_type(image,fields[0].type_index)==(kind,typename,False),
                 'ai-declared-data-field',[name,kind,typename],[f.type_index for f in fields])
    enum=_owner(image,claim['enumType']);backing=next(f for f in image.metadata.fields_for(enum) if image.metadata.string(f.name_index)=='value__')
    _require(_instance_field_type(image,backing.type_index)==(8,'int',False),'ai-enum-backing','Int32',backing.type_index)
    members={n:index.enum_member_id(claim['enumType'],n) for n in ('Float','String','Vector3')}
    selected={n:_method(image,spec) for n,spec in claim['methods'].items()}
    guard=selected['guard'];gp=list(image.metadata.parameters_for(guard))
    _require(guard.flags&0x10 and guard.generic_container_index<0 and _type(image,guard.return_type)==(2,'bool',False)
             and [_type(image,p.type_index) for p in gp]==[(8,'int',False)],
             'ai-patch-signature','nongeneric static Boolean IsPatched(Int32)',guard.index)
    target=selected['target'];params=list(image.metadata.parameters_for(target));caller_params=list(image.metadata.parameters_for(method))
    _require(target.flags&0x10 and _type(image,target.return_type)==(0x12,'Beyond.Gameplay.Core.AbilitySystem',False)
             and len(params)==3 and len(caller_params)==1
             and [_type(image,p.type_index) for p in params[:2]]==[(0x12,'Beyond.Gameplay.Core.AbilityAction',False),(0x12,'Beyond.Gameplay.Core.TargetSettings',False)]
             and _type(image,params[2].type_index)==_type(image,caller_params[0].type_index),
             'ai-target-ABI','same input handle and typed action/TargetSettings arguments',target.index)
    entity_owner,_,entity_name=claim['entityField'].partition('::')
    _owner(image,entity_owner);_ancestor(context,'Beyond.Gameplay.Core.AbilitySystem',entity_owner)
    entity_offset=_field(context,claim['entityField'],'Beyond.Gameplay.Core.Entity')
    _ancestor(context,'Beyond.Gameplay.Core.Entity',claim['enemyAIField'].partition('::')[0])
    ai_offset=_field(context,claim['enemyAIField'],'Beyond.Gameplay.AI.EnemyAIComponent')
    _owner(image,'Beyond.Gameplay.AI.EnemyAIComponent');_owner(image,'Beyond.Gameplay.AI.AIComponent')
    _ancestor(context,'Beyond.Gameplay.AI.EnemyAIComponent','Beyond.Gameplay.AI.AIComponent')
    _ancestor(context,'NodeCanvas.Framework.AssetBlackboard','UnityEngine.Object')
    parent_bb=selected['parentBlackboard'];pp=list(image.metadata.parameters_for(parent_bb))
    _ancestor(context,'Beyond.Gameplay.AI.EnemyAIComponent',image.type_name(parent_bb.declaring_type))
    _require(not parent_bb.flags&0x10 and _type(image,parent_bb.return_type)==(0x12,'NodeCanvas.Framework.AssetBlackboard',False)
             and len(pp)==1 and _type(image,pp[0].type_index)==(2,'bool',False),
             'ai-parent-blackboard-ABI','instance AssetBlackboard GetParentBlackboard(Boolean)',parent_bb.index)
    eq=selected['nullEquality'];ep=list(image.metadata.parameters_for(eq))
    _require(eq.flags&0x10 and _type(image,eq.return_type)==(2,'bool',False)
             and [_type(image,p.type_index) for p in ep]==[(0x12,'UnityEngine.Object',False)]*2,
             'ai-null-equality-ABI','static Boolean Unity Object equality',eq.index)
    lookup=selected['lookup'];lp=list(image.metadata.parameters_for(lookup))
    _require(lookup.flags&0x10 and lookup.generic_container_index>=0
             and _type(image,lookup.return_type)[0]==0x15 and not _type(image,lookup.return_type)[2]
             and _type(image,lookup.return_type)[1].startswith('NodeCanvas.Framework.Variable`1<MVAR[')
             and [_type(image,p.type_index) for p in lp]==[(0x12,'NodeCanvas.Framework.IBlackboard',False),(0x0e,'string',False)],
             'ai-lookup-ABI','static generic lookup, IBlackboard and String inputs',lookup.index)
    entries=GenericEntries(image)
    physical={t:entries.resolve(lookup.index,[],[t]) for t in ('UnityEngine.Vector3','float','int','bool')}
    _require(len({p['pointer'] for p in physical.values()})==1,'ai-shared-lookup-entry',
             'one physical lookup definition for independently registered value-type contexts',physical)
    fields={'data':layout['fieldOffset'],'target':index.field_offset(claim['dataType']+'::'+claim['targetField']),
        'selector':index.field_offset(claim['dataType']+'::'+claim['selectorField']),
        'key':index.field_offset(claim['dataType']+'::'+claim['keyField']),'entity':entity_offset,'enemyAI':ai_offset}
    pointers={n:image.method_pointer_va(m) for n,m in selected.items() if n!='lookup'};pointers['lookup']=next(iter(physical.values()))['pointer']
    result=validate_program(rows,fields=fields,methods=pointers,enum_members=members)
    for item in result['lookups']:
        raw=image.pe.bytes_at_va(item['contextLoadVa'],7)
        cell=item['contextLoadVa']+7+struct.unpack_from('<i',raw,3)[0];usage=image.pe.bytes_at_va(cell,8)
        si=method_spec_usage_index(usage,image.registration['methodSpecsCount'],source=str(image.gameassembly),offset=cell)
        spec=struct.unpack('<iii',image.pe.bytes_at_va(int(image.registration['methodSpecs'],16)+si*12,12))
        args=[runtime_type_name(image.pe,image.metadata,a.type_pointer_va) for a in image.instantiations.resolve(spec[2]).arguments]
        registrations=[r for r in struct.iter_unpack('<iiii',entries.table) if r[0]==si]
        arg=item['staticMethodArgument']
        if arg=='string' and registrations:
            physical[arg]=entries.resolve(lookup.index,[],[arg])
            _require(physical[arg]['pointer']==pointers['lookup'],'ai-string-physical-entry',
                     'same exact caller target',physical[arg]['pointer'])
        direct=physical.get(arg)
        validate_static_lookup_context(spec,args,method_index=lookup.index,expected_arg=arg,
            spec_index=si,registered_spec_index=direct['methodSpecIndex'] if direct else None,
            direct_registration_absent=not registrations)
        item.update(contextCellRva=cell-image.pe.image_base,usageRawHex=usage.hex().upper(),methodSpecIndex=si,
                    liveContextObserved=False,directInstantiationRegistrationProved=direct is not None,
                    methodSpecRegistrationRows=len(registrations),
                    entryEvidence='exact own instantiation registration' if direct else
                        'exact caller target and static String MethodSpec; independent compiled String registration absent')
    result.update(method=[method.index,claim['type'],claim['method'],ptr-image.pe.image_base],
        codeWindow={'startRva':ptr-image.pe.image_base,'endRva':ptr+size-image.pe.image_base,
            'sha256':hashlib.sha256(image.pe.bytes_at_va(ptr,size)).hexdigest().upper()},
        closedDataLayout=layout,selectorEnumMembers=members,nativeCallerLookupSelectionProved=True,
        allFiveIndependentInstantiationRegistrationsProved=all(r['directInstantiationRegistrationProved'] for r in result['lookups']),
        evidenceBoundary='conditional',condition='coherent instances, ordinary Win64 calls, false patch check and the recorded selected branch/helper results')
    return result


def validate_static_lookup_context(spec,args,*,method_index,expected_arg,spec_index,registered_spec_index,
                                   direct_registration_absent=False):
    _require(len(spec)==3 and spec[0]==method_index and spec[1]==-1 and spec[2]>=0
             and args==[expected_arg] and (spec_index==registered_spec_index or
                 expected_arg=='string' and registered_spec_index is None and direct_registration_absent),
             'ai-static-lookup-context','exact usage->MethodSpec->registered method argument',[spec_index,spec,args])
