"""Selected concrete behavior's inherited Entity slot and original Init write.

No runtime allocation, callback selection, object lifetime, or other generic
instantiation is inferred from this closed metadata/native witness.
"""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp import protocol
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields

SCHEMA='endfield.skill-behavior-entity-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-behavior-entity-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_behavior_entity_native.json'
LABEL='skillBehaviorEntity'
CONCRETE='Beyond.Gameplay.AI.CharacterCastSkillBehavior'
GENERIC='Beyond.Gameplay.AI.CharacterAIBehavior`1'
ARGUMENT=CONCRETE+'+CharacterCastSkillBehaviorData'
EMPTY='Beyond.Gameplay.AI.CharacterAIBehavior'
OWNER='Beyond.Gameplay.AI.AIBehavior'
POOL='Beyond.Gameplay.AIClassPool'
CHAIN=[GENERIC+'<'+ARGUMENT+'>',EMPTY,OWNER,POOL,'object']
PRIMITIVES={'bool':1,'byte':1,'sbyte':1,'short':2,'ushort':2,'int':4,'uint':4,'long':8,'ulong':8,'float':4,'double':8}


def _align(value,alignment):
    _require(type(value)is int and type(alignment)is int and value>=0 and alignment>0 and alignment&(alignment-1)==0,
        'behavior-alignment','nonnegative integer/power-of-two alignment',(value,alignment))
    return (value+alignment-1)//alignment*alignment


def _layout_extents(start,fields,size,pointer_bytes):
    """Account for every field and only its necessary natural alignment padding."""
    cursor=start;padding=[]
    for field in sorted(fields,key=lambda r:r['offset']):
        width=field['bytes'];offset=field['offset'];alignment=min(width,pointer_bytes)
        _require(type(width)is int and width in(1,2,4,8)and type(offset)is int,
            'behavior-field-extent','ordinary primitive/enum/reference extent',field)
        expected=_align(cursor,alignment)
        _require(offset==expected and offset+width<=size,'behavior-field-placement',expected,field)
        if expected>cursor:padding.append([cursor,expected])
        cursor=offset+width
    expected_size=_align(cursor,pointer_bytes)
    _require(expected_size==size,'behavior-layout-size',expected_size,size)
    if size>cursor:padding.append([cursor,size])
    return padding


def _relative(raw,rva):
    _require(len(raw)==5 and raw[0]==0xe8,'behavior-relative-call','E8 rel32',raw.hex())
    return rva+5+struct.unpack_from('<i',raw,1)[0]


def _validate(image,contract):
    context=NativeReferenceContext(image);pointer_bytes=struct.calcsize('Q');types={}
    expected_types={CONCRETE,GENERIC,ARGUMENT,EMPTY,OWNER,POOL,'System.Object'}
    for row in contract['types']:
        name=row['name'];td=image.named_types[name]
        actual=dict(index=td.index,parent=context.parent(name),flags=td.flags,bitfield=td.bitfield,fieldCount=td.field_count,genericContainer=td.generic_container_index)
        _require(actual=={k:row[k]for k in actual}and name not in types,'behavior-type-declaration',row,actual)
        _require(not td.flags&0x20 and not td.flags&0x18==0x10 and td.bitfield&0x800,
            'behavior-type-layout','reference class/default native packing',row)
        table=image.registration['typeDefinitionsSizes'];address=image.pe.u64_at_va(int(table,16)+td.index*pointer_bytes)
        _require(address and td.index<image.registration['typeDefinitionsSizesCount'],'behavior-size-row','selected registered type size',row)
        raw=image.pe.bytes_at_va(address,16)
        _require(raw.hex()==row['sizeRowHex']and int.from_bytes(raw[:4],'little')==row['instanceBytes'],
            'behavior-size-bytes',row,raw.hex())
        types[name]=row
    _require(set(types)==expected_types,'behavior-type-coverage',sorted(expected_types),sorted(types))
    owner=CONCRETE
    for expected in CHAIN:
        _require(context.parent(owner)==expected and not context.is_value_type(owner),'behavior-parent-edge',expected,context.parent(owner));owner=expected
    _require(not context.is_value_type(ARGUMENT)and image.named_types[ARGUMENT].generic_container_index<0,
        'behavior-closed-reference-argument','selected nongeneric reference argument',ARGUMENT)
    fields=_validate_fields(image,contract['fields'])
    declared={}
    for name in(POOL,OWNER,EMPTY,CONCRETE):
        td=image.named_types[name];actual=[]
        for field in image.metadata.fields_for(td):
            _require(not context.field_attributes(field.type_index)&0x10,'behavior-instance-fields','no unaccounted static field',name)
            actual.append(image.metadata.string(field.name_index))
        rows=[row for row in fields.values()if row['type']==name]
        _require(sorted(actual)==sorted(row['name']for row in rows),'behavior-complete-fields',actual,rows);declared[name]=rows
    generic_td=image.named_types[GENERIC];members=list(image.metadata.fields_for(generic_td))
    section=image.metadata.sections['genericContainers'];at=section.offset+generic_td.generic_container_index*16
    container=struct.unpack_from('<iiii',image.metadata.buf,at)
    context.require_ordinary_kind(members[0].type_index,0x13)
    _require(container[0:3]==(generic_td.index,1,0)and len(members)==1
        and image.metadata.string(members[0].name_index)=='m_data'and context.type_name(members[0].type_index)==f'VAR[{container[3]}]'
        and not context.field_attributes(members[0].type_index)&0x10,
        'behavior-generic-reference-slot','sole selected type-parameter field',container)
    def width(row):
        kind=row['valueType']
        if kind in PRIMITIVES:return PRIMITIVES[kind]
        if context.is_enum(kind):
            underlying=next((r for r in fields.values()if r['type']==kind and r['name']=='value__'),None)
            _require(underlying is not None and underlying['valueType']in PRIMITIVES,'behavior-enum-extent','validated underlying field',kind)
            return PRIMITIVES[underlying['valueType']]
        _require(kind in image.named_types and not context.is_value_type(kind),'behavior-reference-extent','named reference class',kind)
        return pointer_bytes
    object_size=types['System.Object']['instanceBytes']
    _require(object_size==2*pointer_bytes,'behavior-object-header','selected Win64 object header',object_size)
    extents={};padding={};cursor=object_size
    for name in(POOL,OWNER,EMPTY):
        rows=[dict(field=r['id'],offset=r['offset'],bytes=width(r))for r in declared[name]]
        padding[name]=_layout_extents(cursor,rows,types[name]['instanceBytes'],pointer_bytes);extents[name]=rows;cursor=types[name]['instanceBytes']
    # Only this closed generic parent adds one reference. Its open size/offset row is never used.
    generic_offset=cursor;closed_prefix=cursor+pointer_bytes
    rows=[dict(field=r['id'],offset=r['offset'],bytes=width(r))for r in declared[CONCRETE]]
    padding[CONCRETE]=_layout_extents(closed_prefix,rows,types[CONCRETE]['instanceBytes'],pointer_bytes);extents[CONCRETE]=rows
    layout=dict(concreteType=CONCRETE,ancestorChain=CHAIN,fieldOwner=OWNER,fieldName='m_entity',
        entityOffset=fields['entity']['offset'],entityBytes=width(fields['entity']),
        closedDataOffset=generic_offset,closedDataBytes=pointer_bytes,
        concreteInstanceBytes=types[CONCRETE]['instanceBytes'],fieldExtents=extents,padding=padding)
    _require(fields['entity']['type']==OWNER and fields['entity']['name']=='m_entity' and fields['entity']['ordinaryKind']==0x12 and fields['entity']['valueType']=='Beyond.Gameplay.Core.Entity',
        'behavior-nominal-entity-field','AIBehavior.m_entity:Entity',fields['entity'])
    _require(json.dumps(layout,sort_keys=True)==json.dumps(contract['layout'],sort_keys=True),'behavior-layout-result',contract['layout'],layout)
    methods={}
    expected_methods={'init':(OWNER,'Init'),'ctor':(CONCRETE,'.ctor'),'enter':(CONCRETE,'OnEnter')}
    for row in contract['methods']:
        role=row['id'];index=image.validate_method_row(row['identity'],label=LABEL);method=image.metadata.methods[index]
        actual=dict(returnType=context.type_name(method.return_type),parameters=[dict(name=image.metadata.string(p.name_index),type=context.type_name(p.type_index))for p in image.metadata.parameters_for(method)])
        _require(actual=={k:row[k]for k in actual}and not method.flags&0x10
            and row['identity'][1:3]==list(expected_methods[role])and role not in methods,'behavior-method-nominal',row,actual);methods[role]=row
    _require(set(methods)==set(expected_methods),'behavior-method-coverage',list(expected_methods),list(methods))
    _require([p['type']for p in methods['init']['parameters']]==['Beyond.Gameplay.Core.Entity','Beyond.Gameplay.AI.AIGraph'],
        'behavior-init-entity-argument','this/entity/aiGraph',methods['init'])
    image.check_windows(contract['codeWindows'],label=LABEL);windows={r['owner']:r for r in contract['codeWindows']}
    _require(set(windows)==set(methods),'behavior-window-coverage',list(methods),list(windows))
    for role,row in windows.items():_require(row['startRva']==methods[role]['identity'][3],'behavior-entry',methods[role]['identity'][3],row)
    def checked(row):
        raw=bytes.fromhex(row['hex']);w=windows[row['owner']];rva=row['rva']
        _require(raw and w['startRva']<=rva<rva+len(raw)<=w['endRva']and image.pe.bytes_at_va(image.pe.image_base+rva,len(raw))==raw,
            'behavior-native-span',row,'native/bounds differs');return raw
    spans={r['id']:r for r in contract['spans']}
    _require(set(spans)=={'initCapture','initBridge','initWrite','consumerCapture','consumerLoad','ctorStores'},'behavior-span-coverage','selected capture/write/read/constructor',spans)
    _require(checked(spans['initCapture'])==bytes.fromhex('4c8bd14d8bd8')and checked(spans['consumerCapture'])==bytes.fromhex('488bd9'),
        'behavior-this-capture','RCX this -> preserved selected receiver',spans)
    bridge=checked(spans['initBridge']);capture=checked(spans['initCapture'])
    _require(spans['initBridge']['owner']=='init'and spans['initBridge']['rva']==spans['initCapture']['rva']
      and len(bridge)==19 and bridge[:6]==capture and bridge[6:9]==bytes.fromhex('488b48')
      and bridge[10:13]==bytes.fromhex('4885c9')and bridge[13:15]==bytes.fromhex('0f85')
      and spans['initBridge']['rva']+len(bridge)==spans['initWrite']['rva'],
      'behavior-init-normal-fallthrough','captured receiver/entity unchanged to original write, alternate iFix branch excluded',bridge.hex())
    offset=fields['entity']['offset'];disp=offset.to_bytes(1,'little',signed=True)
    expected=bytes.fromhex('498d4a')+disp+bytes.fromhex('498952')+disp
    write=checked(spans['initWrite']);_require(write[:len(expected)]==expected and len(write)==len(expected)+5,
        'behavior-init-store','LEA this.field; MOV [this.field], entityRDX; barrier',write.hex())
    _require(_relative(write[-5:],spans['initWrite']['rva']+len(expected))==contract['barrierTargetRva'],
        'behavior-write-barrier','selected direct call after actual store',write.hex())
    _require(checked(spans['consumerLoad'])==bytes.fromhex('488b43')+disp,'behavior-concrete-entity-read','load selected inherited field',spans['consumerLoad'])
    ctor=checked(spans['ctorStores']);at=0
    for instruction in contract['constructorWrites']:
        field=fields[instruction['field']];store=instruction['encoding'];value=bytes.fromhex(instruction['valueHex']);width=instruction['bytes']
        _require(field['type']==OWNER,'behavior-ctor-field-owner',OWNER,field['type'])
        if store=='dword':
            _require(width==4 and len(value)==width and field['valueType']=='float','behavior-ctor-float','one Single field',instruction)
            part=bytes.fromhex('c743')+field['offset'].to_bytes(1,'little',signed=True)+value
        else:
            _require(store=='twoBooleans'and width==2 and len(value)==width and field['valueType']=='bool'
                and fields[instruction['nextField']]['offset']==field['offset']+1
                and fields[instruction['nextField']]['valueType']=='bool','behavior-ctor-adjacent-booleans','two declared adjacent bool fields',instruction)
            part=bytes.fromhex('66c743')+field['offset'].to_bytes(1,'little',signed=True)+value
        _require(ctor[at:at+len(part)]==part,'behavior-concrete-ctor-inherited-store',instruction,ctor.hex());at+=len(part)
    _require(at==len(ctor),'behavior-ctor-store-coverage',at,len(ctor))
    rules=dict(inheritedEntityFieldProved=True,initWritesEntityBeforeBarrier=True,concreteNativeReadProved=True,
        selectedConcreteOnly=True,allGenericInstantiationsProved=False,runtimeSelectionProved=False,initializationInvocationProved=False,lifetimeProved=False)
    _require(json.dumps(contract['rules'],sort_keys=True)==json.dumps(rules,sort_keys=True) and len(contract['facts'])==2
        and {r['id']for r in contract['facts']}=={'inheritedEntityLayout','originalInitWrite'}
        and all(json.dumps(r['rules'],sort_keys=True)==json.dumps(rules,sort_keys=True) and json.dumps(r['layout'],sort_keys=True)==json.dumps(layout,sort_keys=True) and r['boundary']
            and r['evidence']=={'inheritedEntityLayout':'direct','originalInitWrite':'conditional'}[r['id']]for r in contract['facts']),
        'behavior-rule-facts',rules,contract['rules'])
    return layout,rules


def load_skill_behavior_entity(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',nativeInputs={},rows=[],rules={},layout={},failures=[],contract=str(path))
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL)
        audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary'])
        pins=contract['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        layout,rules=_validate(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','behavior-native-after','validated',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'behavior-contract-after','unchanged','changed')
        audit.update(status='validated',detail='',nativeInputs=dict(pins),rows=contract['facts'],rules=rules,layout=layout)
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:1200],nativeInputs={},rows=[],rules={},layout={})
        audit['failures'].append(dict(validator=LABEL,source=str(path),check=str(error).split(':',1)[0],detail=str(error)[:1200]))
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv);audit=load_skill_behavior_entity(gameassembly=args.gameassembly,metadata=args.metadata)
    if args.output:
        from scripts.repo_paths import REPO_ROOT
        if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in('reports','scratch','tmp')):parser.error('output must be reports/scratch/tmp')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:audit[k]for k in('status','detail','failures')},indent=2));return int(audit['status']!='validated')
if __name__=='__main__':raise SystemExit(main())
