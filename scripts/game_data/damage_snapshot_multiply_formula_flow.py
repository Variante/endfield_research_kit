"""Authenticate affine subtype formula on one complete selected owned path."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target

def check_result_records(record, prior_records):
    _require(len(record)==16 and bool(prior_records) and all(len(prior)==16 and record[:8]==prior[:8] and record[10:12]==prior[10:12] for prior in prior_records),'multiply-formula-concrete-result-owner','same selected-image value type definition and ordinary ABI record',[record.hex(),[r.hex() for r in prior_records]])


def check_multiply_rows(rows,pointer,first_end,second_end,offsets,providers):
    selected=rows[:11]+rows[14:]
    forms=[b'\x48\x89\x5c\x24\x08',b'\x48\x89\x6c\x24\x10',b'\x48\x89\x74\x24\x18',b'\x57',b'\x48\x81\xec\x80\x00\x00\x00','ready-byte',
      b'\x49\x8b\xf9',b'\x49\x8b\xe8',b'\x48\x8b\xf2',b'\x48\x8b\xd9','ready-nonzero',
      b'\x0f\x29\x74\x24\x70',b'\x33\xd2',b'\x0f\x29\x7c\x24\x60','patch-id',b'\x44\x0f\x29\x44\x24\x50','patch-call',b'\x84\xc0','patch-excluded',
      b'\x48\x8b\x4b'+bytes([offsets['multiplier']]),b'\x45\x33\xc0',b'\x48\x8b\xd7','multiplier-call',
      b'\x83\x7b'+bytes([offsets['valueSource']])+b'\x00',b'\x0f\x28\xf0','other-source-excluded',
      b'\x4c\x8b\x8c\x24'+struct.pack('<i',offsets['overrideEntryStack']+136),b'\x44\x8b\x43'+bytes([offsets['attributeType']]),b'\x48\x8b\xd6',b'\x48\x8b\xcb',b'\x48\xc7\x44\x24\x20\x00\x00\x00\x00','attribute-call',
      b'\x48\x8b\x4b'+bytes([offsets['addition']]),b'\x45\x33\xc0',b'\x48\x8b\xd7',b'\x44\x0f\x28\xc0','addition-call',
      b'\x48\x8b\x9c\x24'+struct.pack('<i',offsets['serverEntryStack']+136),b'\x0f\x28\xf8',b'\x48\x85\xdb','server-excluded',
      b'\x0f\x57\xc9',b'\xf3\x0f\x5a\xce',b'\xf2\x41\x0f\x59\xc8',b'\x0f\x57\xc0',b'\xf3\x0f\x5a\xc7',b'\xf2\x0f\x58\xc1',b'\x66\x48\x0f\x7e\xc0',
      b'\x44\x0f\x28\x44\x24\x50',b'\x4c\x8d\x9c\x24\x80\x00\x00\x00',b'\x49\x8b\x5b\x10',b'\x49\x8b\x6b\x18',b'\x49\x8b\x73\x20',b'\x0f\x28\x7c\x24\x60',b'\x0f\x28\x74\x24\x70',b'\x49\x8b\xe3',b'\x5f',b'\xc3']
    _require(len(selected)==len(forms),'multiply-formula-selected-length',len(forms),len(selected))
    _require(all(type(offsets[k]) is int and 0<=offsets[k]<128 for k in ('multiplier','valueSource','attributeType','addition')),
             'multiply-formula-field-operands','bounded typed disp8',offsets)
    at=pointer;edges={};calls={};ready=None;patch_id=None
    for n,(row,form) in enumerate(zip(selected,forms)):
        if n==11:at=first_end
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'multiply-formula-contiguity',hex(at),row['va'])
        limit=first_end if n<11 else second_end
        _require(pointer<=at and at+len(raw)<=limit,'multiply-formula-owned-range','selected bytes within actual physical pdata range',row['va'])
        if isinstance(form,bytes):_require(raw==form,'multiply-formula-instruction',form.hex(),raw.hex())
        elif form=='ready-byte':
            _require(len(raw)==7 and raw[:2]==b'\x80\x3d' and raw[-1]==0,'multiply-formula-ready-byte','anonymous RIP byte CMP0',raw.hex());ready=at+7+int.from_bytes(raw[2:6],'little',signed=True)
        elif form=='ready-nonzero':
            _require(len(raw)==2 and raw[0]==0x75 and at+2+int.from_bytes(raw[1:],'little',signed=True)==first_end,'multiply-formula-ready-edge','JNE to exact second extent',raw.hex())
        elif form=='patch-id':
            _require(len(raw)==5 and raw[0]==0xb9,'multiply-formula-patch-id','MOV ECX immediate',raw.hex());patch_id=int.from_bytes(raw[1:],'little')
        elif form.endswith('-call'):
            _require(len(raw)==5 and raw[0]==0xe8,'multiply-formula-call','direct CALL',raw.hex());target=relative_branch_target(raw,at,source='multiplyFormula')
            _require(target==providers[form],'multiply-formula-call-identity',[form,hex(providers[form])],hex(target));calls[form]=hex(target)
        else:
            _require(len(raw)==6 and raw[:2]==b'\x0f\x85','multiply-formula-excluded-condition','JNE outside selected path',raw.hex());edges[form]=at+6+int.from_bytes(raw[2:],'little',signed=True)
        at+=len(raw)
    _require(at==second_end,'multiply-formula-complete-ret-end',hex(second_end),hex(at))
    _require(all(not pointer<=edge<at for edge in edges.values()),'multiply-formula-excluded-targets','outside selected entry-to-RET',edges)
    return {'selectedInstructionCount':len(forms),'selectedRetEnd':at,'metadataReadyByteAddress':ready,'metadataReadyByteCondition':'nonzero selected; initialization path excluded',
            'patchRequestImmediate':patch_id,'actualCalls':calls,'excludedTargets':edges,
            'actualSelectedSource':'stored valueSource Int32 bits zero -> named incoming attacker; no enum member name inferred',
            'floatingOperationOrder':'CVTSS2SD(multiplier Float) then MULSD(destination converted multiplier, source returned attribute Double); CVTSS2SD(addition Float) then ADDSD(destination converted addition, source product); MOVQ low64 to RAX',
            'fieldReceiverOriginEnds':'this RCX -> RBX supplies fields; server argument load subsequently overwrites RBX',
            'providerInternalsAndLiveDamageProved':False,'fullOtherPathsOrRuntimeSubtypeSelectionProved':False}


def check_multiply_formula(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_field,require_ordinary_int32_enum,require_ordinary_double_array,require_ordinary_value_type
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','multiply-formula-fresh-result-layout','fresh sole Double CalcResult layout',consumer_proof.get('claim'))
    body=index.body(spec['type'],spec['method']);selected=NativeReferenceContext(index.image,index=index)
    result_owner,result_method=consumer_proof['symbol'].rsplit('.',1);result_body=index.body(result_owner,result_method)
    result_methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(result_body.pointer,()) if f"{r.get('type')}.{r.get('method')}"==consumer_proof['symbol']]
    _require(bool(result_methods) and all(selected.type_name(m.return_type)==spec['returnType'] for m in result_methods),'multiply-formula-same-result-type',spec['returnType'],[selected.type_name(m.return_type) for m in result_methods])
    _require(not selected.is_value_type(spec['type']) and selected.parent(spec['type'])==spec['baseType'],
             'multiply-formula-this-owner','ordinary subtype with selected CalculationBase parent',[spec['type'],selected.parent(spec['type'])])
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(body.pointer,()) if f"{r.get('type')}.{r.get('method')}"==body.symbol]
    _require(bool(methods) and all(not m.flags&0x10 for m in methods),'multiply-formula-instance-definition','ordinary instance Evaluate',body.symbol)
    result_records=[selected.image.pe.bytes_at_va(selected.type_pointer(m.return_type),16) for m in result_methods]
    for method in methods:
        record=selected.image.pe.bytes_at_va(selected.type_pointer(method.return_type),16)
        check_result_records(record,result_records)
        require_ordinary_value_type(selected,method.return_type,spec['returnType'],'multiply.result')
        require_ordinary_type(selected,_parameter(selected,method,'attacker').type_index,spec['abilityType'],'multiply.attacker',reference_kind=0x12)
        require_ordinary_type(selected,_parameter(selected,method,'blackboard').type_index,spec['blackboardType'],'multiply.blackboard',reference_kind=0x12)
        require_ordinary_double_array(selected,_parameter(selected,method,'attackerOverrideAttributes').type_index,'multiply.override')
        require_ordinary_type(selected,_parameter(selected,method,'argsForServer').type_index,spec['serverType'],'multiply.server',reference_kind=0x12)
    for name,expected in (('this',('register','rcx')),('attacker',('register','rdx')),('blackboard',('register','r9'))):
        _require(index.parameter_location(body.pointer,body.symbol,name)==expected,'multiply-formula-input-register',[name,expected],index.parameter_location(body.pointer,body.symbol,name))
    override=index.parameter_location(body.pointer,body.symbol,'attackerOverrideAttributes');server=index.parameter_location(body.pointer,body.symbol,'argsForServer')
    _require(all(p[0]=='stack' and type(p[1]) is int for p in (override,server)),'multiply-formula-input-stack','explicit named stack offsets',[override,server])
    offsets={'overrideEntryStack':override[1],'serverEntryStack':server[1]}
    td=index.types[spec['type']]
    for key,qualified,expected in (('valueSource',spec['sourceField'],spec['sourceEnum']),('attributeType',spec['attributeField'],spec['attributeEnum'])):
        owner,typ,offset=selected.field(qualified);_require((owner,typ)==(spec['type'],expected),'multiply-formula-enum-field-owner',[spec['type'],expected],[owner,typ])
        fields=[f for f in index.metadata.fields_for(td) if index.metadata.string(f.name_index)==qualified.split('::',1)[1]]
        _require(len(fields)==1,'multiply-formula-enum-field-unique',1,len(fields));require_ordinary_int32_enum(selected,fields[0].type_index,expected,'multiply.'+key);offsets[key]=offset
    for key,qualified in (('multiplier',spec['multiplierField']),('addition',spec['additionField'])):
        owner,typ,offset=selected.field(qualified);_require((owner,typ)==(spec['type'],spec['scalarParameterType']),'multiply-formula-scalar-field-owner',[spec['type'],spec['scalarParameterType']],[owner,typ])
        require_ordinary_field(selected,qualified,typ,'multiply.'+key);offsets[key]=offset
    rows=body.rows;_require(len(rows)>=61,'multiply-formula-body-rows','complete selected program',len(rows))
    providers={name:relative_branch_target(bytes.fromhex(rows[n]['bytes']),int(rows[n]['va'],16),source='multiplyFormulaProvider') for name,n in (('patch-call',19),('multiplier-call',25),('attribute-call',34),('addition-call',39))}
    _check_named_provider(index,providers['patch-call'],spec['patchMethod'],['int'],'bool',is_static=True)
    for name in ('multiplier-call','addition-call'):_check_named_provider(index,providers[name],spec['scalarGetter'],[spec['scalarParameterType'],spec['blackboardType']],'float',is_static=True)
    attr_matches=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(providers['attribute-call'],()) if f"{r.get('type')}.{r.get('method')}"==spec['attributeGetter']]
    _require(bool(attr_matches) and all(not m.flags&0x10 for m in attr_matches),'multiply-formula-attribute-provider','named instance Double provider',hex(providers['attribute-call']))
    for method in attr_matches:
        parameters=index.metadata.parameters_for(method);_require(len(parameters)==3,'multiply-formula-attribute-arity',3,len(parameters))
        require_ordinary_type(selected,method.return_type,'double','multiply.attribute.return')
        require_ordinary_type(selected,parameters[0].type_index,spec['abilityType'],'multiply.attribute.source',reference_kind=0x12)
        require_ordinary_int32_enum(selected,parameters[1].type_index,spec['attributeEnum'],'multiply.attribute.enum')
        require_ordinary_double_array(selected,parameters[2].type_index,'multiply.attribute.array')
    for name,register in (('this','rcx'),('attrSource','rdx'),('attributeType','r8'),('attrArray','r9')):
        _require(index.parameter_location(providers['attribute-call'],spec['attributeGetter'],name)==('register',register),'multiply-formula-attribute-abi',[name,register],index.parameter_location(providers['attribute-call'],spec['attributeGetter'],name))
    _require(body.pointer in index.extents,'multiply-formula-first-extent','exact first owned prefix',hex(body.pointer));first=index.extents[body.pointer]
    _require(first in index.extents,'multiply-formula-second-extent','actual branch-linked physical range',hex(first));second=index.extents[first]
    _require(0<first-body.pointer<=512 and 0<second-first<=4096,'multiply-formula-owned-bounds','bounded branch-linked physical ranges',[body.pointer,first,second])
    proof=check_multiply_rows(rows,body.pointer,first,second,offsets,providers)
    prefix=b''.join(bytes.fromhex(r['bytes']) for r in rows[:11]);tail=b''.join(bytes.fromhex(r['bytes']) for r in rows[14:])
    _require(prefix==index.pe.bytes_at_va(body.pointer,len(prefix)) and tail==index.pe.bytes_at_va(first,second-first),
             'multiply-formula-full-selected-raw-coverage','both complete selected raw partitions',[len(prefix),len(tail)])
    return {**proof,'symbol':body.symbol,'claim':'multiplyAttributeSelectedFloatAffineToCalcResult',
            'selectedPhysicalPdataRanges':[[hex(body.pointer),hex(first)],[hex(first),hex(second)]],
            'commonAttributeEntry':int(rows[30]['va'],16),
            'boundary':'Selected nonzero anonymous entry byte skips the metadata-initialization region, false ordinary IFix continues, stored Int32 valueSource bits zero selects the named incoming attacker and override array, and null ordinary server reference selects arithmetic. Typed owner fields, ordinary Int32 enum storage/parameters, Double-array element/parameter ABI, normal ordinary Float multiplier/addition providers and instance Double attribute provider arguments are checked. Both actual branch-linked physical pdata ranges (same managed unwind family is not inferred), selected raw partitions, every direct call/branch/excluded target and complete restoring RET are authenticated. The exact SSE order is converted Float multiplier times returned Double, then converted Float addition as ADDSD destination plus that product, and low64 bits into the independently authenticated sole-Double CalcResult return. Provider internals, actual enum/member selection data, MXCSR floating state, valid compatible live subtype/objects/frame/storage and normal Win64 noninterference remain conditions; initializer/other source/server/patch paths and actual DamageAction runtime subtype invocation or final damage are not inferred.'}


def check_other_source_bridge(raw,pointer,owned_end,defender_array_entry,main_attribute_entry):
    _require(pointer<owned_end and pointer+16<=owned_end,'multiply-source-bridge-owned-prefix','complete selected 16-byte prefix within actual cold owner',[pointer,owned_end])
    expected=b'\x4c\x8b\x8c\x24'+struct.pack('<i',defender_array_entry+136)+b'\x48\x8b\xf5'
    _require(len(raw)==16 and raw[:11]==expected and raw[11]==0xe9,'multiply-source-bridge-instruction','defender array -> R9/defender RBP -> RSI/direct JMP',raw.hex())
    target=relative_branch_target(raw[11:],pointer+11,source='multiplyOtherSource')
    _require(target==main_attribute_entry,'multiply-source-bridge-common-entry',main_attribute_entry,target)
    return {'selectedPrefixBytes':16,'actualOwnedColdExtentEnd':owned_end,'wholeColdFunctionProved':False,
            'selectedCondition':'stored ordinary Int32 valueSource bits nonzero',
            'sourceTransfer':'incoming defender R8 -> nonvolatile RBP -> full RSI -> common GetAttribute source RDX; RSI attacker origin ends at the bridge write',
            'arrayTransfer':'incoming defenderOverrideAttributes entry stack -> current stack + 136 -> R9',
            'commonAttributeEntry':target,'enumMemberNameOrRuntimeSourceChoiceProved':False}


def check_multiply_defender_bridge(index, main_proof, spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type, require_ordinary_double_array
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(main_proof.get('claim')=='multiplyAttributeSelectedFloatAffineToCalcResult', 'multiply-source-fresh-main', 'fresh full selected affine program', main_proof.get('claim'))
    body=index.body(spec['type'],spec['method']);selected=NativeReferenceContext(index.image,index=index)
    _require(main_proof['symbol']==body.symbol,'multiply-source-same-owner',body.symbol,main_proof['symbol'])
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(body.pointer,()) if f"{r.get('type')}.{r.get('method')}"==body.symbol]
    _require(bool(methods),'multiply-source-methods','named metadata methods',methods)
    for method in methods:
        require_ordinary_type(selected,_parameter(selected,method,'defender').type_index,spec['abilityType'],'multiply.defender',reference_kind=0x12)
        require_ordinary_double_array(selected,_parameter(selected,method,'defenderOverrideAttributes').type_index,'multiply.defenderOverride')
    _require(index.parameter_location(body.pointer,body.symbol,'defender')==('register','r8'),'multiply-source-defender-abi','incoming R8',index.parameter_location(body.pointer,body.symbol,'defender'))
    array=index.parameter_location(body.pointer,body.symbol,'defenderOverrideAttributes')
    _require(array[0]=='stack' and type(array[1]) is int,'multiply-source-array-abi','explicit entry stack',array)
    target=main_proof['excludedTargets']['other-source-excluded']
    _require(target in index.extents,'multiply-source-cold-owner','actual pdata entry',target)
    end=index.extents[target]
    proof=check_other_source_bridge(index.pe.bytes_at_va(target,16),target,end,array[1],main_proof['commonAttributeEntry'])
    return {**proof,'symbol':body.symbol,'claim':'multiplyAttributeNonzeroSourceDefenderBridge',
        'boundary':'Fresh main-program nonzero Int32 source branch reaches the actual cold physical pdata entry. Its complete selected 16-byte prefix replaces RSI with saved ordinary incoming defender and R9 with the named ordinary Double-array override, then jumps exactly to the fresh common attribute-enum load. The common normal provider/arithmetic/RET proof is reused conditionally on caller frame continuity, storage validity, ordinary Win64 returns and noninterference. No enum member name, live source choice, whole cold body or runtime subtype dispatch is inferred.'}
