"""Typed original DialogBranch selection and its selected generic reader calls."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.list_item_program import check_list_item_program
from scripts.game_data.il2cpp.owned_consumer_instructions import read_owned_consumer_instructions
from scripts.game_data.il2cpp.original_field_return import check_original_field_return
from scripts.game_data.il2cpp.dialog_branch_program import check_dialog_branch_program
from scripts.game_data.il2cpp.safe_count_clone_program import check_safe_count_clone

def check_dialog_branch_selection(index,body,spec):
    image=index.image;md=image.metadata;ctx=NativeReferenceContext(image);base=image.pe.image_base;generic=GenericEntries(image)
    def need(check,expected,actual):
        if actual!=expected:raise ValueError(f'dialogBranchSelection.{check}: {body.symbol}; source={image.gameassembly}; expected={str(expected)[:320]}; actual={str(actual)[:420]}')
    need('profile',{'conditionsField','resultField','resultGetter','activateMethod'},set(spec) if isinstance(spec,dict) else None)
    need('named-profile',True,all(isinstance(v,str) and v for v in spec.values()))
    branch_data,list_type,conditions=ctx.field(spec['conditionsField']);condition_type,result_type,result=ctx.field(spec['resultField'])
    need('typed-condition-list',f'System.Collections.Generic.List`1<{condition_type}>',list_type)
    need('result-enum',True,ctx.is_enum(result_type));need('result-word','int',ctx.field(result_type+'::value__')[1])
    need('result-members',[0,1,2],[index.enum_member_id(result_type,n) for n in ('False','True','Undecided')])
    aliases=[r for r in index.names_by_pointer.get(body.pointer,()) if r['type']+'.'+r['method']==body.symbol]
    need('unique-caller',1,len(aliases));method=md.methods[aliases[0]['methodIndex']];params=list(md.parameters_for(method))
    need('caller-ABI',(0,-1,'int',1),(method.flags&16,method.generic_container_index,ctx.type_name(method.return_type),len(params)))
    need('branch-data-parameter',branch_data,ctx.type_name(params[0].type_index));ctx.require_ordinary_kind(params[0].type_index,0x12);ctx.require_ordinary_kind(method.return_type,8)
    def selected_method(symbol):
        pointers=index.pointers_by_name.get(symbol,set());need('unique-selected-method:'+symbol,1,len(pointers));pointer=next(iter(pointers))
        declarations=[r for r in index.names_by_pointer[pointer] if r['type']+'.'+r['method']==symbol];need('selected-declaration:'+symbol,1,len(declarations))
        return pointer,md.methods[declarations[0]['methodIndex']]
    getter_pointer,getter=selected_method(spec['resultGetter']);need('getter-owner',condition_type,image.type_name(getter.declaring_type))
    need('getter-ABI',(0,0,result_type),(getter.flags&16,getter.parameter_count,ctx.type_name(getter.return_type)));ctx.require_ordinary_kind(getter.return_type,0x11)
    getter_body=index.body(condition_type,md.string(getter.name_index),parameters=[]);need('getter-pointer',getter_pointer,getter_body.pointer)
    original_getter=check_original_field_return(index,getter_body,result,4)
    activate_pointer,activate=selected_method(spec['activateMethod']);need('activate-owner',condition_type,image.type_name(activate.declaring_type))
    need('activate-ABI',(0,'void'),(activate.flags&16,ctx.type_name(activate.return_type)));ctx.require_ordinary_kind(activate.return_type,1)
    def owned(pointer):
        rows=[];ranges=[]
        for p in image.unwind_index.family(pointer-base)['ranges']:
            a,b=p['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,b-a);decoded=decode_type_data_initialization_instructions(image.mapper,raw,base+a)
            need('complete-owned-byte-coverage',raw,b''.join(bytes.fromhex(r['bytes']) for r in decoded));rows+=decoded;ranges.append((base+a,base+b))
        return rows,ranges
    rows,ranges=owned(body.pointer);program=check_dialog_branch_program(rows,entry=body.pointer,ranges=ranges,conditions=conditions,result=result)
    calls=program['selectedCalls'];need('activate-target',activate_pointer,calls['activate'])
    count_context=derive_typed_usage_context(image,int(program['countContext']['va'],16)-base,label='dialogBranch.count')
    need('count-context',['Beyond.CollectionExtensions','SafeCount',[],[condition_type]],[count_context.get(k) for k in ('typeName','methodName','classArguments','methodArguments')])
    definition=count_context['methodSpec'][0];count_method=md.methods[definition];parameters=list(md.parameters_for(count_method))
    need('count-ABI',(16,'int',1),(count_method.flags&16,ctx.type_name(count_method.return_type),len(parameters)));ctx.require_ordinary_kind(count_method.return_type,8);ctx.require_ordinary_kind(parameters[0].type_index,0x15)
    selected=image.instantiations.resolve(count_context['methodSpec'][2]);need('count-argument-arity',1,len(selected.arguments))
    need('ordinary-condition-reference',b'\x12\0',image.pe.bytes_at_va(selected.arguments[0].type_pointer_va,16)[10:12])
    symbols=ContextSymbols(image).context(definition,is_method=True);entries=symbols['entries'];need('count-context-arity',2,len(entries))
    interface,count=entries;need('count-interface',(2,0,'System.Collections.Generic.ICollection`1'),(interface['kind'],interface['relativeSlot'],interface['type']['definition']['name']))
    argument=interface['type']['classArguments'];need('interface-argument-arity',1,len(argument));need('interface-parameter-owner',(definition,0),(argument[0].get('parameterOwner',{}).get('methodIndex'),argument[0].get('parameterOwner',{}).get('ordinal')))
    need('interface-count-context',(3,'System.Collections.Generic.ICollection`1','get_Count',argument,[]),(count['kind'],count.get('typeName'),count.get('methodName'),count.get('classArguments'),count.get('methodArguments')))
    declared_count=md.methods[count['methodSpec'][0]];need('interface-count-ABI',(0,0,0,'int'),(declared_count.slot,declared_count.flags&16,declared_count.parameter_count,ctx.type_name(declared_count.return_type)));ctx.require_ordinary_kind(declared_count.return_type,8)
    canonical=generic.observe(definition,[],['object']);need('canonical-count-arity',1,len(canonical));need('canonical-count-adjustor',-1,canonical[0]['registration']['indices'][-1])
    canonical_rows,_=owned(canonical[0]['pointer']);clone_rows,_=owned(calls['count']);need('count-clone-shape',27,len(clone_rows))
    leaf=control_transfer(clone_rows[11]).get('target');need('count-indexed-helper',True,type(leaf) is int)
    leaf_rows=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(leaf,15),leaf)
    count_proof=check_safe_count_clone(canonical_rows,clone_rows,leaf_rows)
    item_context=derive_typed_usage_context(image,int(program['itemContext']['va'],16)-base,label='dialogBranch.item')
    need('item-context',['System.Collections.Generic.List`1','get_Item',[condition_type],[]],[item_context.get(k) for k in ('typeName','methodName','classArguments','methodArguments')])
    selected=image.instantiations.resolve(item_context['methodSpec'][1]);need('item-argument-arity',1,len(selected.arguments));need('item-reference-argument',b'\x12\0',image.pe.bytes_at_va(selected.arguments[0].type_pointer_va,16)[10:12])
    declaration=md.methods[item_context['methodSpec'][0]];parameters=list(md.parameters_for(declaration));need('item-ABI',(0,1,'int'),(declaration.flags&16,len(parameters),ctx.type_name(parameters[0].type_index) if len(parameters)==1 else None));ctx.require_ordinary_kind(parameters[0].type_index,8)
    returned=ContextSymbols(image).type(ctx.type_pointer(declaration.return_type));need('item-return-owner',(declaration.declaring_type,0),(returned.get('parameterOwner',{}).get('typeIndex'),returned.get('parameterOwner',{}).get('ordinal')));need('ordinary-item-return',b'\x13\0',bytes.fromhex(returned['rawHex'])[10:12])
    registration=generic.resolve(declaration.index,['object'],[]);need('item-entry',(calls['item'],-1),(registration['pointer'],registration['registration']['indices'][-1]))
    code,owned_ranges,_=read_owned_consumer_instructions(image.mapper,image.pe,calls['item']);item_proof=check_list_item_program(code,entry=calls['item'],owned_ranges=owned_ranges,element_kind='reference')
    return dict(program=program,countProof=count_proof,countContext=count_context,countSymbols=symbols,itemProof=item_proof,itemContext=item_context,originalGetter=original_getter,
        evidenceBoundary='conditional',condition=program['condition']+' The count clone matches its registered canonical body and declared ICollection.Count context; live interface/generic binding remains conditional.')
