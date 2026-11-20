"""Bounded CharacterAIBrain initialization source and mode-entry bridges.

Typed generic MethodInfo arguments do not authenticate closed compiled loader
entries. Resource selection and live graph scheduling remain explicit gaps.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
from scripts.common import check_installed_native_inputs
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.context import literal_record,unresolved_usage_index
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
from scripts.game_data.skill_combo_acceptance_native import _written_register

SCHEMA='endfield.skill-ai-mode-sources-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_ai_mode_sources_native.json'
LABEL='skillAIModeSourcesNative'


def need(check,value):
    if not value:raise ValueError(LABEL+'.'+check)


def _scope(fact):
    need('schema-status',fact.get('schema')==SCHEMA and fact.get('status')=='reviewed')
    expected=dict(originalPathOnly=True,activeEntityConfigSelected=False,configuredBlackboardAssetPathProved=False,
        compiledGenericLoadEntryProved=False,runtimeSelectionProved=False,modeEntryInitializationAndAddBridge=True)
    need('rules',type(fact['rules'])is dict and fact['rules'].keys()==expected.keys()
        and all(type(fact['rules'][key])is bool and fact['rules'][key]is value for key,value in expected.items()))
    need('evidence-boundary',all(fact['evidenceBoundary'].get(key)for key in ('exact','conditional','unresolved')))


def _literal(image,row):
    pe=image.pe;md=image.metadata;base=pe.image_base;at=base+row['instructionRva'];raw=pe.bytes_at_va(at,7)
    need('literal-load',raw==bytes.fromhex(row['instructionHex'])and raw[:2]in(b'\x48\x8b',b'\x4c\x8b')and raw[2]&0xc7==5)
    cell=at+7+struct.unpack_from('<i',raw,3)[0];need('literal-cell',cell-base==row['cellRva'])
    table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData']
    index=unresolved_usage_index(pe.bytes_at_va(cell,8),table.size//8,tag=5,source=LABEL,offset=cell)
    need('literal-index',index==row['literalIndex']);offset=table.offset+index*8
    start,size=literal_record(md.buf[offset:offset+8],pool.size,source=LABEL,offset=offset)
    need('literal-value',md.buf[pool.offset+start:pool.offset+start+size].decode()==row['value'])


def _semantics(fact):
    need('caller-role',fact['caller']['identity'][1:3]==['Beyond.Gameplay.AI.CharacterAIBrain','InitData']
        and fact['caller']['returnType']=='void'and fact['caller']['parameters']==[dict(name='aiComp',type='Beyond.Gameplay.AI.CharacterAIComponent')])
    need('block-coverage',set(fact['blocks'])=={'capture','configAndProviders','configModeEnumeration','cacheSelection','modeInitAndAdd','poolProvider'})
    blocks={key:[bytes.fromhex(row['hex'])for row in block['instructions']]for key,block in fact['blocks'].items()}
    def contains(key,*values):
        sequence=[bytes.fromhex(value)for value in values]
        need('opcode-'+key,sum(blocks[key][at:at+len(sequence)]==sequence for at in range(len(blocks[key])-len(sequence)+1))==1)
    fields={(row['owner'],row['name']):row for row in fact['fields']}
    def field_hex(owner,name,prefix,width=1):
        return prefix+int(fields[owner,name]['offset']).to_bytes(width,'little',signed=True).hex()
    brain='Beyond.Gameplay.AI.CharacterAIBrain';cfg='Beyond.Gameplay.AI.Config.CharacterAIConfigData'
    contains('capture','498bd8','4c8bea','488bf1')
    contains('configAndProviders',field_hex(cfg,'aiBBPath','488b53'))
    for name in ['m_modeDataCache','m_graphDataCache','m_behaviorDataCache']:
        contains('configAndProviders',field_hex(brain,name,'488d56'),'4533c0','488bcb')
    contains('configModeEnumeration',field_hex('Beyond.Gameplay.AI.Config.CharacterAIBrainConfigData','mode','4c8b4b'),'4d85c9')
    contains('configModeEnumeration',field_hex(brain,'m_modeDataCache','4c8b76'))
    contains('configModeEnumeration','4c8be3','49c1ec20')
    contains('cacheSelection','418bd4','498bce')
    contains('modeInitAndAdd',field_hex(brain,'m_graphDataCache','488b46'),field_hex(brain,'m_behaviorDataCache','488b4e'),'4d85f6')
    slot=fact['stackSlots']['selectedModeData'];source=fact['sourceOperands']['initEntityArgument']
    need('stack-slot-shape',type(slot)is int and 0<=slot<=4096)
    contains('cacheSelection','48898c24'+struct.pack('<i',slot).hex())
    need('physical-source-operand',source['prefix']=='498b55'and source['width']==1 and type(source['displacement'])is int)
    contains('modeInitAndAdd','4c8b8c24'+struct.pack('<i',slot).hex(),'448bc3',source['prefix']+int(source['displacement']).to_bytes(source['width'],'little',signed=True).hex(),'498bce')
    contains('modeInitAndAdd','4d8bc6','8bd3')
    need('named-entries',[tuple(row['target'][1:3])for row in fact['calls']]==[
        ('Beyond.Gameplay.AI.Config.CharacterAIBlackboard','GetMode'),('Beyond.Gameplay.AI.Config.CharacterAIBlackboard','GetGraph'),
        ('Beyond.Gameplay.AI.Config.CharacterAIBlackboard','GetBehavior'),('Beyond.Gameplay.AI.CharacterAIMode','InitData')])
    requests=[row['result']for row in fact['typedRequests']]
    need('typed-request-roles',[(row['typeName'],row['methodName'])for row in requests]==[
        ('Beyond.StringUtils','ZConcat'),('Beyond.Resource.ResourceManager','TryLoad'),('Beyond.Resource.FAssetProxyHandle','Get'),
        ('System.Collections.Generic.Dictionary`2+Enumerator','MoveNext'),('Beyond.Gameplay.AIManager','GetClassFromPool'),
        ('System.Collections.Generic.Dictionary`2','Add')])
    need('selected-request-types',requests[1]['methodArguments']==['Beyond.Gameplay.AI.Config.CharacterAIBlackboard']
        and requests[2]['methodArguments']==requests[1]['methodArguments']
        and requests[-1]['classArguments']==['Beyond.Gameplay.AI.CharacterAIModeType','Beyond.Gameplay.AI.CharacterAIMode'])
    bindings=[('Beyond.Gameplay.AI.CharacterAIComponent','<data>k__BackingField','configAndProviders','498b9d',4),
        ('Beyond.Gameplay.AI.CharacterAIComponentData','aiCfg','configAndProviders','488b5b',1),
        ('Beyond.Gameplay.AI.Config.CharacterAIConfigData','aiBBPath','configAndProviders','488b53',1),
        ('Beyond.Gameplay.AI.Config.CharacterAIConfigData','brainConfig','configModeEnumeration','488b5b',1),
        ('Beyond.Gameplay.AI.Config.CharacterAIBrainConfigData','mode','configModeEnumeration','4c8b4b',1),
        ('Beyond.Gameplay.AI.CharacterAIBrain','m_modeData','modeInitAndAdd','488b4e',1),
        ('Beyond.Gameplay.AI.CharacterAIBrain','m_modeDataCache','configModeEnumeration','4c8b76',1),
        ('Beyond.Gameplay.AI.CharacterAIBrain','m_graphDataCache','modeInitAndAdd','488b46',1),
        ('Beyond.Gameplay.AI.CharacterAIBrain','m_behaviorDataCache','modeInitAndAdd','488b4e',1)]
    for owner,name,block,prefix,width in bindings:
        need('field-role-present',(owner,name)in fields);prefix=bytes.fromhex(prefix);offset=fields[owner,name]['offset']
        uses=sum(raw.startswith(prefix)and len(raw)>=len(prefix)+width
            and int.from_bytes(raw[len(prefix):len(prefix)+width],'little',signed=True)==offset for raw in blocks[block])
        need('typed-field-operand',uses>=1)
    need('literal-argument-count',len(fact['literalLoads'])==2)


def _setup_destination(raw):
    # MOV r32/64,imm is the only extra form beyond the shared finite
    # MOV/LEA/XOR setup grammar. Branches/calls/unknown instructions refuse.
    at=1 if raw and 0x40<=raw[0]<=0x4f else 0
    if at<len(raw)and 0xb8<=raw[at]<=0xbf:
        rex=raw[0]if at else 0
        need('setup-immediate-size',len(raw)==at+1+(8 if rex&8 else 4))
        return ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15')[raw[at]-0xb8+(8 if rex&1 else 0)]
    return _written_register(raw)


def _transfers(fact,instructions):
    sources=[row['instructionRva']for row in fact['typedRequests']]+[row['instructionRva']for row in fact['literalLoads']]
    need('transfer-source-coverage',[row['loadRva']for row in fact['transfers']]==sources)
    need('transfer-argument-roles',[row['argument']for row in fact['transfers']]==['r9','loadMethodInfoArgument','rdx','rdx','rdx','r9','r8','rcx'])
    for row in fact['transfers']:
        start,end=row['loadRva'],row['callRva'];raw=instructions.get(start,b'')
        need('owned-rip-source',len(raw)==7 and raw[:2]in(b'\x48\x8b',b'\x4c\x8b')and raw[2]&0xc7==5)
        register=_setup_destination(raw);stack=row['argument']=='loadMethodInfoArgument'
        need('source-argument-register',register==('rax'if stack else row['argument']))
        need('bounded-transfer',start+7<=end<=start+96);at=start+7;stored=False
        while at<end:
            setup=instructions.get(at,b'');need('contiguous-transfer',bool(setup)and at+len(setup)<=end)
            if stack and setup[:4]==b'\x48\x89\x44\x24'and len(setup)==5:
                need('methodinfo-stack-argument',not stored and setup[4]==fact['stackSlots']['loadMethodInfoArgument']);stored=True
            else:
                destination=_setup_destination(setup)
                need('preserved-argument-transfer',destination is not None and destination!=register)
            at+=len(setup)
        need('stack-argument-supplied',not stack or stored)
        call=instructions.get(end,b'')
        need('physical-consumer-target',len(call)==5 and call[0]==0xe8
            and end+5+struct.unpack_from('<i',call,1)[0]==row['physicalTargetRva'])


def _validate(image,fact):
    _scope(fact);_semantics(fact);context=NativeReferenceContext(image);base=image.pe.image_base
    image.validate_method_row(fact['caller']['identity'],label=LABEL)
    method=image.metadata.methods[fact['caller']['identity'][0]]
    need('caller-signature',context.type_name(method.return_type)==fact['caller']['returnType']
        and [dict(name=image.metadata.string(row.name_index),type=context.type_name(row.type_index))for row in image.metadata.parameters_for(method)]==fact['caller']['parameters'])
    ranges=sorted(tuple(row['runtimeTriple'][:2])for row in image.unwind_index.family(fact['caller']['identity'][3])['ranges'])
    need('complete-caller-family',ranges==sorted((row['startRva'],row['endRva'])for row in fact['codeWindows']))
    image.check_windows(fact['codeWindows'],label=LABEL);instructions={}
    for block in fact['blocks'].values():
        start,end=block['startRva'],block['endRva'];need('owned-block',any(a<=start<end<=b for a,b in ranges));at=start
        for row in block['instructions']:
            raw=bytes.fromhex(row['hex']);need('contiguous-block',row['rva']==at and 0<len(raw)<=15)
            need('native-instruction',image.pe.bytes_at_va(base+at,len(raw))==raw);instructions[at]=raw;at+=len(raw)
        need('complete-block',at==end)
    for row in fact['calls']:
        raw=instructions.get(row['siteRva'],b'');need('actual-named-entry',len(raw)==5 and raw[0]==0xe8
            and row['siteRva']+5+struct.unpack_from('<i',raw,1)[0]==row['target'][3]);image.validate_method_row(row['target'],label=LABEL+'.callee')
    for row in fact['fields']:
        need('typed-field',tuple(context.field(row['owner']+'::'+row['name']))==(row['owner'],row['typeName'],row['offset']))
        td=image.named_types[row['owner']]
        declarations=[field for field in image.metadata.fields_for(td)if image.metadata.string(field.name_index)==row['name']]
        need('ordinary-field-declaration',len(declarations)==1 and type(row['ordinaryKind'])is int)
        context.require_ordinary_kind(declarations[0].type_index,row['ordinaryKind'])
    _transfers(fact,instructions)
    for row in fact['typedRequests']:need('typed-request',derive_typed_usage_context(image,row['instructionRva'],label=LABEL)==row['result'])
    for row in fact['literalLoads']:_literal(image,row)
    return dict(schema='endfield.skill-ai-mode-sources-native-audit.v1',status='validated',nativeInputs=fact['nativeInputs'],rules=fact['rules'],
        evidenceBoundary=fact['evidenceBoundary'],literalArguments=[row['value']for row in fact['literalLoads']],
        initializedModeBridge='aiComp.data.aiCfg.brainConfig.mode physical pair -> modeDataCache query -> Mode.InitData -> m_modeData Add request',
        configuredBlackboardAssetPathProved=False,runtimeSelectionProved=False)


def validate_current_native_contract(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path)
    try:
        raw=path.read_bytes();fact=json.loads(raw);_scope(fact);pins=fact['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(gameassembly),metadata=Path(metadata))
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
        if failure:=check_unity_input(gate.gameassembly,pins):return failure
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),fact)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,detail=after.detail)
        if failure:=check_unity_input(gate.gameassembly,pins):return failure
        need('contract-bookend',raw==path.read_bytes());return result
    except(ValueError,KeyError,TypeError,IndexError,OSError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=path)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_ai_mode_sources_native.json')
    args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('--output must be below reports/')
    result=validate_current_native_contract(gameassembly=args.gameassembly,metadata=args.metadata,contract_path=args.contract)
    if result.get('status')=='validated':args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));return 0 if result.get('status')=='validated'else 2


if __name__=='__main__':raise SystemExit(main())
