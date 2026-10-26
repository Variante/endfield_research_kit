"""Exact named BlackboardInt/Vector3 reference requests in generated parents.

The caller supplies an independently authenticated current ReadValue reference
clone fact. This component proves the selected parent method, concrete nominal
CLASS argument, unchanged incoming Reader/context, actual helper target and
unchanged RAX-to-RDX transfer to the named typed setter. Complete parent/setter
families are recorded; parent framing, the child's wire grammar, runtime provider
selection and whole-parent admission remain separate.
"""
import re

from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import buff_ec_profiles_native as ec
from scripts.game_data.memorypack import primitive_param,scalar_param_native as scalar
from scripts.game_data.memorypack.wrapper_members import derive_from_image

LABEL='blackboardReferenceParent'
SELECTIONS={
    'Beyond.Blackboard+BlackboardInt':(
        'Beyond.MemoryPack.Beyond_Blackboard_BlackboardIntForMemoryPack',
        'Beyond.MemoryPack.Beyond_Gameplay_Core_SpawnInteractiveGoldCoin_DataForMemoryPack','count'),
    'Beyond.Blackboard+BlackboardVector3':(
        'Beyond.MemoryPack.Beyond_Blackboard_BlackboardVector3ForMemoryPack',
        'Beyond.MemoryPack.Beyond_Gameplay_Core_JumpToTargetAction_DataForMemoryPack','jumpToPosition'),
}
SAVED=('rbx','rbp','rdi','rsi','r12','r13','r14','r15')


def need(key,expected,actual):scalar.need(LABEL,key,expected,actual)


def _selected_wrapper(wrappers,name):
    selected=[w for w in wrappers.values()if w.name==name]
    need('unique-named-wrapper:'+name,1,len(selected))
    return selected[0]


def reader_register(rows,entry):
    started=False
    for row in rows:
        if ec.va(row)==entry:started=True
        if not started:continue
        if control_transfer(row)['kind']=='call':break
        match=re.fullmatch(r'mov (\w+), rcx',row['text'])
        if match and match[1]in SAVED:return match[1]
    raise ValueError(LABEL+'.reader:no-exact-prologue-save')


def parent_call(rows,context,*,reader,base,target):
    """Exact straight-line RCX/RDX setup reaching the actual reference helper."""
    matches=[]
    for index,row in enumerate(rows):
        transfer=control_transfer(row)
        if transfer['kind']!='call' or transfer['target']!=target:continue
        argument=ec.last_write(rows,index,'rdx');incoming=ec.last_write(rows,index,'rcx')
        if (argument and incoming and ec.va(argument)==base+context['instructionRva']
                and incoming['text']=='mov rcx, '+reader):
            matches.append((index,row,argument,incoming))
    need('one-exact-source-caller',1,len(matches))
    index,call,argument,incoming=matches[0]
    start=min(ec.va(argument),ec.va(incoming))
    setup=[r for r in rows if start<=ec.va(r)<ec.va(call)]
    at=start
    for row in setup:
        need('setup-partition',at,ec.va(row));need('setup-linear','next',control_transfer(row)['kind'])
        need('setup-decoded',False,row['text'].startswith('db '))
        at+=len(ec.raw(row))
    need('setup-call-join',ec.va(call),at)
    return index,dict(sourceCall=ec.site(call,base),readerRegister=reader,
        argumentSetup=[ec.site(r,base)for r in setup],sameIncomingReader=True,
        sameTypedContext=True,sourceTargetRva=target-base)


def reference_transfer(rows,index,*,setter_target,base):
    """The guarded unchanged RAX result becomes RDX of the selected setter."""
    part=rows[index+1:index+7]
    need('complete-reference-transfer',6,len(part))
    test,branch,method_info,move,receiver,call=part
    match=re.fullmatch(r'test (\w+), \1',test['text'])
    need('nonnull-held-wrapper',True,match is not None and match[1]in SAVED)
    need('same-setter-receiver','mov rcx, '+match[1],receiver['text'])
    edge=control_transfer(branch)
    need('nonnull-guard',('conditional',4),(edge['kind'],edge.get('conditionCode')))
    by={ec.va(r):r for r in rows}
    failure=by.get(edge['target']);terminal=by.get(edge['target']+5)
    need('owned-exception-call-and-trap',True,failure is not None and terminal is not None
        and control_transfer(failure)['kind']=='call'and ec.raw(terminal)==b'\xcc')
    need('zero-setter-MethodInfo',bytes.fromhex('4533c0'),ec.raw(method_info))
    need('full-reference-RAX-to-RDX',bytes.fromhex('488bd0'),ec.raw(move))
    transfer=control_transfer(call)
    need('selected-named-setter',('call',setter_target),(transfer['kind'],transfer.get('target')))
    return dict(program=[ec.site(r,base)for r in part],exceptionCallRva=edge['target']-base,
        preservedResultBits=64,methodInfoIsZero=True,sameNonNullReceiver=True,
        valueTransfer='complete incoming helper RAX unchanged into setter RDX')


def derive(image,*,type_name,wrapper_name,parent_wrapper,parent_field,clone_fact):
    need('closed-selection',SELECTIONS.get(type_name),(wrapper_name,parent_wrapper,parent_field))
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers=derive_from_image(image)
    child=_selected_wrapper(wrappers,wrapper_name);parent=_selected_wrapper(wrappers,parent_wrapper)
    need('child-nominal-wrapper',type_name,child.wrapped_type)
    need('ordinary-reference-child',False,ctx.is_value_type(type_name))
    scalar.ordinary(image,ctx.type_pointer(ctx.index.types[type_name].byval_type_index),18,LABEL+'.childType',reference=True)
    member,=[m for m in parent.members if m.name==parent_field]
    need('exact-parent-field-type',type_name,member.declared_type)
    method,=[m for m in md.methods_for(md.types[parent.type_definition])if md.string(m.name_index)=='Deserialize']
    primitive_param.reader_abi(image,ctx,method,parent)
    entry=image.method_pointer_va(method)
    family,windows,rows=ec.family(image,entry-base)
    need('parent-decode',False,any(r['text'].startswith('db ')for r in rows))
    reader=reader_register(rows,entry)
    contexts=[c for c in ec.contexts(image,rows)if c['fullTypeName']==type_name]
    need('unique-closed-parent-context',1,len(contexts));context=contexts[0]
    need('typed-reference-request',('MemoryPack.MemoryPackReader','ReadValue',18,'rdx'),
        tuple(context[k]for k in('methodOwner','methodName','typeKind','register')))
    need('selected-clone-name',['MemoryPack.MemoryPackReader','ReadValue'],clone_fact['equivalentMethod'][1:3])
    image.validate_method_row(clone_fact['equivalentMethod'],label=LABEL+'.referenceClone')
    need('selected-reader-method-definition',clone_fact['equivalentMethod'][0],context['methodSpec'][0])
    spec=context['methodSpec'];need('method-only-instantiation',True,spec[1]==-1 and spec[2]>=0)
    reader_method=md.methods[spec[0]]
    need('reader-instance-no-formal-arguments',(False,0),(bool(reader_method.flags&16),reader_method.parameter_count))
    arguments=image.instantiations.resolve(spec[2]).arguments
    need('one-closed-reference-type',1,len(arguments))
    raw=image.pe.bytes_at_va(arguments[0].type_pointer_va,16)
    need('same-context-type-bytes',context['argumentRawHex'],raw.hex().upper())
    need('ordinary-CLASS-argument-flags',b'\x12\x00',raw[10:12])
    definition=ctx.index.types[type_name].index
    need('actual-closed-TypeDef',definition,int.from_bytes(raw[:8],'little'))
    target=base+clone_fact['targetRva']
    index,call=parent_call(rows,context,reader=reader,base=base,target=target)
    setter=md.methods[member.method_index]
    scalar.owned_method_abi(image,ctx,setter.index,parent.type_definition,('void',1,False),
        [(type_name,18,True)],LABEL+'.namedSetter')
    setter_target=image.method_pointer_va(setter)
    setter_family,setter_windows,_=ec.family(image,setter_target-base)
    transfer=reference_transfer(rows,index,setter_target=setter_target,base=base)
    return dict(typeName=type_name,typeDefinition=definition,contextTypeKind=18,
        referenceReaderMethodDefinition=context['methodSpec'][0],referenceReaderTargetRva=clone_fact['targetRva'],
        parentMethod=[method.index,parent_wrapper,'Deserialize',entry-base],family=family,
        codeWindows=windows,context=context,sourceCall=call['sourceCall'],argumentSetup=call,
        setterMethod=[setter.index,parent_wrapper,md.string(setter.name_index),setter_target-base],
        setterFamily=setter_family,setterWindows=setter_windows,argumentTransfer=transfer,
        wholeParentAdmitted=False,boundary=__doc__)
