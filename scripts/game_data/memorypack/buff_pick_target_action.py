"""Named PickTarget storage and its independently owned BlackboardInt child.

Selected ordinary native paths prove Reader-to-field transfers. They do not
observe formatter choice, evaluate the index, or select a gameplay target.
The recursive TargetSettings decoder keeps its own evidence and depth limit.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Callable
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_actions import Reader,SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import setter_output_sources as setters
from scripts.game_data.memorypack import buffered_owned_sources as buffered
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import inherited_reference_sources as inherited
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack import buff_timeline_read_value as read_value
from scripts.game_data.memorypack import struct_output_sources as structs
from scripts.game_data.memorypack.wrapper_members import derive_from_image

LABEL='buffPickTargetAction'
SCHEMA='endfield.buff-pick-target-action-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_pick_target_action_native.json'
FIELD_NAMES=('isEnable','priorityLevel','priorityOffset','serverActionIndex','contextKey','index','target')
INTEGER_NAMES=('blackboardKey','useBlackboardKey','value')

def _fail(check,expected,actual):
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL);error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (set(c['records'])!={'pickTarget','integer'}
        or tuple(m['fieldName'] for m in c['records']['pickTarget']['members'])!=FIELD_NAMES
        or tuple(m['fieldName'] for m in c['records']['integer']['members'])!=INTEGER_NAMES
        or [m['kind'] for m in c['records']['pickTarget']['members']]!=['byte','scalar32','scalar32','scalar32','byte-payload','integer','target']
        or [m['kind'] for m in c['records']['integer']['members']]!=['byte-payload','byte','scalar32']):
        _fail('contract-shape','seven PickTarget and three distinct BlackboardInt members',c.get('records'))
    return c

def supported_tags():return frozenset((_contract()['unionTag'],))

def _patterns(image,window,rows,patterns):
    references._program(image,window,rows,_fail)
    expected=patterns.copy()
    for i,pattern in enumerate(expected):
        if pattern=='jne32':
            raw=bytes.fromhex(rows[i][1])
            if len(raw)!=6 or raw[:2]!=b'\x0f\x85':_fail('nonzero-branch','complete JNE rel32',rows[i])
            expected[i]=rows[i][1]
    inherited._program(image,rows,expected,fail=_fail)

def validate_integer_stores(image,record,layout,string_helpers):
    """Three closed int/int base fields, source results and actual setters."""
    s=layout['instanceOffset'];key,flag,value=[layout['fieldOffsets'][n] for n in INTEGER_NAMES]
    hx=lambda x:f'{x:02X}'
    patterns=[
      ['488B3E','488BCB','call','4885FF','je32',f'488B4F{hx(s)}','4885C9','je32',f'488941{hx(key)}',f'4883C1{hx(key)}','call'],
      ['488B3E','488BCB','call','4885FF','je32',f'488B4F{hx(s)}','4885C9','je32',f'8841{hx(flag)}'],
      ['488BCB','488B3E','call','4885FF','je8',f'488B4F{hx(s)}','4885C9','je8',f'8941{hx(value)}']]
    setter_patterns=[
      ['4883EC28',f'488B49{hx(s)}','4885C9','je8',f'488951{hx(key)}',f'4883C1{hx(key)}','4883C428','tail'],
      ['4883EC28',f'488B41{hx(s)}','4885C0','je8',f'8850{hx(flag)}','4883C428','C3'],
      ['4883EC28',f'488B41{hx(s)}','4885C0','je8',f'8950{hx(value)}','4883C428','C3']]
    previous=None;failures=[]
    for i,m in enumerate(record['members']):
        rows=m['sourceProgram'];_patterns(image,record['window'],rows,patterns[i])
        if previous is not None and rows[0][0]!=previous:_fail('integer-member-order',previous,rows[0])
        previous=rows[-1][0]+len(bytes.fromhex(rows[-1][1]));named.check_call(image,m['sourceCall'],label=LABEL,fail=_fail)
        if rows[2][0]!=m['sourceCall']['rva']:_fail('integer-read-position',rows[2],m['sourceCall'])
        helpers=string_helpers if i==0 else [layout['primitiveTargets']['byte' if i==1 else 'int']]
        if m['sourceCall']['targetRva'] not in helpers:_fail('integer-primitive-identity',helpers,m['sourceCall'])
        failures.extend(inherited._target(row) for row,pattern in zip(rows,patterns[i],strict=True) if pattern in ('je8','je32'))
        sp=m['setterProgram'];wanted=setter_patterns[i].copy()
        if i==0:
            raw=bytes.fromhex(sp[-1][1])
            if len(raw)!=5 or raw[0]!=0xE9:_fail('integer-reference-barrier-tail','complete E9',sp[-1])
            wanted[-1]=sp[-1][1]
            if inherited._target(sp[-1])!=layout['barrierTarget']:_fail('integer-setter-barrier',layout['barrierTarget'],sp[-1])
            inherited._call(rows[-1],layout['barrierTarget'],fail=_fail)
        _patterns(image,m['setterWindow'],sp,wanted)
        if sp[0][0]!=m['setterMethod'][3]:_fail('integer-setter-entry',m['setterMethod'],sp[0])
    if len(set(failures))!=1 or record['window']['startRva']<=failures[0]<record['window']['endRva']:
        _fail('integer-nonnull-exit','one external null failure',failures)
    return {'namedFields':3,'valueBits':32,'genericOffsetsUsed':False,'sourceResultStoresProved':True}

def validate_integer_header(image,record,offsets):
    p,r,a,c=[f'{offsets[n]:02X}' for n in ('currentPtr','bufferLength','advancedCount','consumed')]
    prefix=record['entryProgram']
    _patterns(image,record['window'],prefix,['48895C2408','48896C2410','4889742418','57','4883EC20',prefix[5][1],'488BF2','488BD9','je32'])
    if len(bytes.fromhex(prefix[5][1]))!=7 or not prefix[5][1].startswith('803D') or not prefix[5][1].endswith('00'):
        _fail('integer-init-guard','byte class-initialization comparison',prefix[5])
    _patterns(image,record['window'],record['headerProgram'],[f'837B{r}01','jl32',f'488B43{p}','0FB628',f'8B7B{r}','83EF01','js32',
        f'48FF43{p}',f'FF43{a}',f'FF43{c}',f'897B{r}','4080FDFF','je32','48833E00','je32','4080FD03','jne32'])
    _patterns(image,record['window'],record['returnProgram'],['488B5C2430','488B6C2438','488B742440','4883C420','5F','C3'])
    if (prefix[0][0]!=record['readerMethod'][3] or record['headerProgram'][-1][0]+len(bytes.fromhex(record['headerProgram'][-1][1]))!=record['members'][0]['sourceProgram'][0][0]
        or record['members'][-1]['sourceProgram'][-1][0]+len(bytes.fromhex(record['members'][-1]['sourceProgram'][-1][1]))!=record['returnProgram'][0][0]
        or record['returnProgram'][-1][0]+1!=record['window']['endRva']):
        _fail('integer-source-frame','owned entry, header, contiguous members and complete RET',record['readerMethod'])
    return {'headerBytes':1,'memberCount':3,'completeOrdinaryReturn':True}

def _wrapper(image,record,wrappers):
    actual=wrappers.get(record['wrapperTypeDefinition']);wanted=[(m['fieldName'],m['setterMethod'][0],m['declaredType']) for m in record['members']]
    if (actual is None or actual.name!=record['wrapperTypeName'] or actual.wrapped_type!=record['runtimeTypeName']
        or [(m.name,m.method_index,m.declared_type) for m in actual.members]!=wanted
        or len(actual.inherited_members)!=record['inheritedMemberCount']):
        _fail('generated-members',wanted,None if actual is None else actual.row())
    image.validate_method_row(record['readerMethod'],label=LABEL)
    structs.check_reader_ref_wrapper_abi(image,record,fail=_fail)
    inherited._ancestry_matches(inherited._ancestry(image,record['wrapperTypeDefinition']),record['wrapperAncestry'],_fail)
    inherited._ancestry_matches(inherited._ancestry(image,record['runtimeTypeDefinition']),record['runtimeAncestry'],_fail)

def _integer_layout(image,record):
    proof=record['layout'];runtime=inherited._ancestry(image,record['runtimeTypeDefinition']);wrapper=inherited._ancestry(image,record['wrapperTypeDefinition'])
    closed=[r['parent'] for r in runtime if r['parent'] and r['parent']['kind']==0x15]
    slots=[(r,f) for r in wrapper for f in r['fields'] if f['type']['kind']==0x15]
    if len(closed)!=1 or len(slots)!=1:_fail('integer-unique-closed-base',[1,1],[len(closed),len(slots)])
    closed=closed[0];owner,slot=slots[0];typ=slot['type']
    if (bytes.fromhex(closed['rawHex'])[:8]!=bytes.fromhex(typ['rawHex'])[:8]
        or any(closed[k]!=typ[k] for k in ('definition','instanceIndex','arguments'))
        or [a['name'] for a in closed['arguments']]!=['int','int']
        or owner['offsets'][slot['name']]!=proof['instanceOffset']):
        _fail('integer-closed-int-int-owner','same current closed carrier and two int arguments',proof)
    fields=[(r,f) for r in runtime for f in r['fields'] if f['name']=='value']
    if len(fields)!=1 or fields[0][0]['definition']!=closed['definition'] or fields[0][1]['type']['kind']!=0x13:_fail('integer-value-VAR','one owned value VAR',fields)
    parameter=int.from_bytes(bytes.fromhex(fields[0][1]['type']['rawHex'])[:8],'little')
    ownership=type_parameter_owner(image.metadata.buf,parameter,[t.generic_container_index for t in image.metadata.types],source=LABEL)
    if ownership!=proof['valueParameterOwner'] or ownership['typeIndex']!=closed['definition'] or not 0<=ownership['ordinal']<len(closed['arguments']):
        _fail('integer-value-parameter-owner',proof['valueParameterOwner'],ownership)
    for i,m in enumerate(record['members']):
        image.validate_method_row(m['setterMethod'],label=LABEL);method=image.metadata.methods[m['setterMethod'][0]]
        if method.flags&0x10 or method.parameter_count!=1 or image.type_name(method.declaring_type)!=owner['name']:
            _fail('integer-setter-ABI','one owned closed-base instance setter',m['setterMethod'])
        actual=inherited._type_row(image,image.metadata.parameters[method.parameter_start].type_index)
        owned_fields=[(r,f) for r in runtime for f in r['fields'] if f['name']==m['fieldName']]
        if (len(owned_fields)!=1 or owned_fields[0][0]['definition']!=closed['definition']
            or i!=2 and owned_fields[0][1]['type']['name']!=actual['name']):
            _fail('integer-owned-field-type',m['fieldName'],owned_fields)
        if actual['name']!=m['declaredType'] or i==2 and actual['pointerRva']!=closed['arguments'][ownership['ordinal']]['pointerRva']:
            _fail('integer-concrete-setter-parameter',m['declaredType'],actual)
    return proof

def _pick_setter(image,record,member,selected):
    proof=member['setterTransfer'];rows=proof['setterProgram'];method=member['setterMethod'];image.validate_method_row(method,label=LABEL)
    md=image.metadata.methods[method[0]];params=image.metadata.parameters_for(md)
    if md.flags&0x10 or len(params)!=1 or selected.type_name(params[0].type_index)!=member['declaredType']:
        _fail('pick-setter-ABI','instance setter with exact field type',method)
    field=selected.field(member['fieldOwner']+'::'+member['fieldName']);offset=field[2]
    if field[1]!=member['declaredType']:_fail('pick-field-type',member['declaredType'],field)
    if member['kind'] in ('byte','scalar32'):
        slot=selected.field(record['wrapperAncestry'][-1]['name']+'::___instance')[2]
        op='88' if member['kind']=='byte' else '89'
        _patterns(image,proof['setterWindow'],rows,['4883EC28',f'488B41{slot:02X}','4885C0','je8',f'{op}50{offset:02X}','4883C428','C3'])
    else:
        _patterns(image,proof['setterWindow'],rows,['4053','4883EC20','488BDA','33D2','call','4885C0','je8',f'488D48{offset:02X}',f'488958{offset:02X}','4883C420','5B',rows[-1][1]])
        inherited._call(rows[4],record['getter']['method'][3],fail=_fail)
        if bytes.fromhex(rows[-1][1])[0]!=0xE9 or inherited._target(rows[-1])!=record['barrierTarget']:
            _fail('pick-reference-tail','selected actual barrier',rows[-1])
    if rows[0][0]!=method[3]:_fail('pick-setter-entry',method,rows[0])

def _validate_image(image,c,string_helpers):
    source,_=read_reviewed_contract(CONTRACTS_DIR/c['sourceDependency'],schema='endfield.skill-timeline-pick-target-native-contract.v1',status='exact-current-build',label=LABEL)
    if source['nativeInputs']!=c['nativeInputs'] or source['dispatcher']['unionTag']!=c['unionTag']:_fail('source-build-or-route',c['nativeInputs'],source['nativeInputs'])
    image.validate_dispatcher(source['dispatcher'],label=LABEL);image.check_windows(c['codeWindows'],label=LABEL)
    integer_source=json.loads((CONTRACTS_DIR/c['integerSourceDependency']).read_bytes())
    if (integer_source.get('schemaVersion')!=1 or c['records']['integer']['readerMethod'] not in integer_source['methods']
        or c['records']['pickTarget']['readerMethod']!=source['methods'][0]):
        _fail('owned-source-reader','exact current reader methods in their reviewed source families',c['records'])
    shared=read_value._contract()
    if shared['nativeInputs']!=c['nativeInputs']:_fail('read-value-build',c['nativeInputs'],shared['nativeInputs'])
    read_value._validate_image(image,shared)
    offsets=c['readerFieldsUnboxedOffsets'];selected=NativeReferenceContext(image)
    if offsets!={k:selected.field('MemoryPack.MemoryPackReader::'+k)[2]-16 for k in offsets} or set(offsets)!={'currentPtr','bufferLength','advancedCount','consumed'}:
        _fail('reader-layout','four current unboxed cursor fields',offsets)
    header=buffered.validate_object_header_source(image,c['objectHeader'],offsets,fail=_fail)
    buffered.validate_int32_source(image,c['int32Source'],offsets,fail=_fail)
    setters.validate_primitive_source(image,{'codeWindows':[c['byteSource']['window']]},c['byteSource']['member'],fail=_fail)
    wrappers=derive_from_image(image)
    for record in c['records'].values():_wrapper(image,record,wrappers)
    integer=c['records']['integer'];layout=_integer_layout(image,integer)
    ints={**validate_integer_stores(image,integer,layout,string_helpers),**validate_integer_header(image,integer,offsets)}
    record=c['records']['pickTarget'];normal=record['window'];proof=record['setterOutputSource']
    setters._parent(image,normal,record,proof,_fail)
    entry=record['entryProgram']
    _patterns(image,normal,entry,['48895C2418','57','4883EC20',entry[3][1],'488BDA','488BF9','je32'])
    if len(bytes.fromhex(entry[3][1]))!=7 or not entry[3][1].startswith('803D') or not entry[3][1].endswith('00'):
        _fail('pick-init-guard','byte class-initialization comparison',entry[3])
    _patterns(image,normal,record['headerCallProgram'],['488D542438','488BCF','call','84C0','je32'])
    inherited._call(record['headerCallProgram'][2],c['objectHeader']['window']['startRva'],fail=_fail)
    _patterns(image,normal,record['headerComparisonProgram'],['0FB6742438','4080FE07','jne32'])
    _patterns(image,normal,record['returnProgram'],['488B742430','488B5C2440','4883C420','5F','C3'])
    if (record['members'][-1]['assignment']['rva']+5!=record['returnProgram'][0][0] or record['returnProgram'][-1][0]+1!=normal['endRva']):
        _fail('pick-complete-return','final setter immediately through owned normal RET',record['returnProgram'])
    getter=record['getter'];g= getter['program'];instance=selected.field(record['wrapperAncestry'][-1]['name']+'::___instance')[2]
    cache=selected.field(record['wrapperTypeName']+'::__realInstance')[2]
    _patterns(image,getter['window'],g,['4053','4883EC20',g[2][1],'488BD9','je8',f'48837B{cache:02X}00','je32',f'488B43{instance:02X}',f'483943{cache:02X}','jne32',f'488B43{cache:02X}','4883C420','5B','C3'])
    image.validate_method_row(getter['method'],label=LABEL);gm=image.metadata.methods[getter['method'][0]]
    if gm.flags&0x10 or gm.parameter_count or selected.type_name(gm.return_type)!=record['runtimeTypeName'] or g[0][0]!=getter['method'][3]:
        _fail('pick-getter-ABI','owned concrete instance getter',getter['method'])
    for i,m in enumerate(record['members']):
        expected_source=source['orderedSourceReads'][i]
        if m['sourceCall']!={'rva':expected_source['sourceCallsiteRva'],'targetRva':expected_source['sourceTargetRva']}:
            _fail('pick-source-call-join',expected_source,m['sourceCall'])
        if m['kind'] in ('byte','scalar32'):
            expected_target=c['byteSource']['window']['startRva'] if m['kind']=='byte' else c['int32Source']['window']['startRva']
            if m['sourceCall']['targetRva']!=expected_target:_fail('pick-primitive-source',expected_target,m['sourceCall'])
        elif i in (5,6) and m['sourceCall']['targetRva']!=shared['calledEntryRva']:
            _fail('pick-read-value-physical-entry',shared['calledEntryRva'],m['sourceCall'])
        context=next((v for v in source['genericContexts'] if v['memberIndex']==i),None)
        if context is not None:
            named.check_typed_context(image,context,m['declaredType'],label=LABEL,fail=_fail)
            if i in (5,6):references._return_type(image,context,_fail)
        elif m['kind']=='byte-payload' and m['sourceCall']['targetRva'] not in string_helpers:
            _fail('pick-string-physical-helper',string_helpers,m['sourceCall'])
        setters._bridge(image,normal,m,final=i==6,context=context,fail=_fail)
        _pick_setter(image,record,m,selected)
    target=next(v for v in source['genericContexts'] if v['memberIndex']==6)
    child=next(v for v in source['genericContexts'] if v['memberIndex']==5)
    if child['typeDefinition']!=integer['runtimeTypeDefinition'] or child['typeName']!=integer['runtimeTypeName'] or target['typeName']!=record['members'][6]['declaredType']:
        _fail('pick-child-identity','separately owned integer and target types',[child,target])
    return {'objectHeader':header,'integer':ints,'pickFieldsForwarded':7,'condition':'selected ordinary branches, coherent non-null wrapper cache and normally returning native calls','runtimeExecutionObserved':False}

def validate_current_native_contract(*,children,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return {'status':'mismatched' if unity.is_file() else 'missing','detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins}
    child=children.get('target',{})
    if child.get('status')!='validated' or child.get('nativeInputs')!=pins:_fail('target-child-native',pins,child)
    string=strings.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if string.get('status')!='validated' or string.get('nativeInputs')!=pins:_fail('string-child-native',pins,string)
    summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c,string['sourceHelpers'])
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not match():return {'status':after.status if after.status!='validated' else 'mismatched','detail':'native inputs changed during PickTarget validation','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,'unionTag':c['unionTag'],'memberNames':list(FIELD_NAMES),'integerMemberNames':list(INTEGER_NAMES),'summary':summary,'runtimeMeaningExact':False,'evidenceBoundary':c['evidenceBoundary']}

def decode_action(data:bytes,*,source:str,digest:str,start:int,end:int,tag:int,native_validation:dict,target_decoder:Callable,depth:int=0):
    c=_contract();audit=native_validation.get('children',{}).get('pickTarget',{})
    target_native=native_validation.get('children',{}).get('target',{})
    if (native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=c['nativeInputs']
        or target_native.get('status')!='validated' or target_native.get('nativeInputs')!=c['nativeInputs']
        or audit.get('status')!='validated' or audit.get('nativeInputs')!=c['nativeInputs']
        or audit.get('unionTag')!=tag or tag!=c['unionTag'] or audit.get('memberNames')!=list(FIELD_NAMES) or audit.get('integerMemberNames')!=list(INTEGER_NAMES)):
        raise ValueError(f'{LABEL}:native-not-validated')
    if type(depth)is not int or not 0<=depth<=SEQUENCE_RECURSION_LIMIT:raise ValueError(f'{LABEL}:depth-limit')
    if (not source or not isinstance(data,bytes) or not isinstance(digest,str) or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)
        or hashlib.sha256(data).hexdigest().upper()!=digest.upper()):raise ValueError(f'{LABEL}:source-range-or-hash')
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((tag,),'pick-target-action')!=tag:raise ValueError(f'{LABEL}:physical-tag')
    fields=[]
    if reader.peek()==255:reader.take(1,'null-pick-target-wrapper')
    else:
        reader.header(7)
        for i,m in enumerate(c['records']['pickTarget']['members']):
            at=reader.pos;value={};kind=m['kind']
            if kind in ('byte','scalar32'):
                raw=reader.take(1 if kind=='byte' else 4,'pick-target.'+m['fieldName']);value={'rawHex':raw.hex().upper()}
            elif kind=='byte-payload':reader.byte_payload();value={'rawHex':data[at:reader.pos].hex().upper()}
            elif kind=='integer':
                rows=[]
                if reader.peek()==255:reader.take(1,'null-blackboard-int')
                else:
                    reader.header(3)
                    for name,k in zip(INTEGER_NAMES,('byte-payload','byte','scalar32'),strict=True):
                        begin=reader.pos
                        if k=='byte-payload':reader.byte_payload()
                        else:reader.take(1 if k=='byte' else 4,'blackboard-int.'+name)
                        rows.append({'fieldName':name,'kind':k,'start':begin,'end':reader.pos,'rawHex':data[begin:reader.pos].hex().upper()})
                value={'child':{'typeName':c['records']['integer']['runtimeTypeName'],'start':at,'end':reader.pos,'isNull':not rows,'namedFields':rows,'recursiveStoredSchemaExact':True,'valueEvaluated':False}}
            elif kind=='target':
                reader.target_profile();extent={'start':at,'end':reader.pos}
                if data[at]==255:
                    from scripts.game_data.memorypack import buff_target_settings_child_receipt as target
                    child=target.decode_target_settings_value(data,source=source,logical_sha256=digest,**extent,native_validation=native_validation['children']['target'])
                    if child['status']!='exact-null':raise ValueError(f'{LABEL}:target-null-proof')
                    child={**child,'isNull':True,'recursiveStoredSchemaExact':True}
                else:child=target_decoder(data,source,digest,extent,native_validation['children'],depth=depth)
                if child.get('recursiveStoredSchemaExact')is not True or [child.get('start'),child.get('end')]!=[at,reader.pos]:raise ValueError(f'{LABEL}:target-recursive-span')
                value={'child':child}
            else:raise ValueError(f'{LABEL}:unsupported-kind')
            fields.append({'fieldName':m['fieldName'],'declaredType':m['declaredType'],'kind':kind,'start':at,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(f'{LABEL}:action-end={reader.pos}; expected={end}')
    return {'schema':'endfield.buff-pick-target-action-receipt.v1','source':source,'logicalSha256':digest.upper(),'tag':tag,'start':start,'end':end,
        'typeName':c['records']['pickTarget']['runtimeTypeName'],'namedFields':fields,'isNull':not fields,'recursiveStoredSchemaExact':True,
        'wholeActionByteSpanExact':True,'wholeBuffDataExact':False,'runtimeMeaningExact':False,'targetSelectionObserved':False}
