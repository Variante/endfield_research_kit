"""Selected native player-command entry and cached-skill dispatch joins.

This records bounded original control paths, not live input acceptance or a
guarantee that a downstream cast succeeds. Native replacements remain excluded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp import protocol
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input

SCHEMA = 'endfield.skill-player-command-native-contract.v1'
LABEL = 'skillPlayerCommand'
CONTRACT_PATH = CONTRACTS_DIR/'skill_player_command_native.json'


def need(check, condition):
    if not condition:
        raise ValueError(LABEL+'.'+check)


def _same_json(actual, expected):
    """JSON value equality without Python's bool/int equivalence."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_same_json(actual[key], value) for key,value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_same_json(left,right) for left,right in zip(actual,expected))
    return actual == expected


def _scope(fact):
    need('schema-status', fact.get('schema') == SCHEMA and fact.get('status') == 'reviewed')
    need('original-boundary', _same_json(fact['rules'], dict(originalPathOnly=True,runtimeExecutionProved=False,
        executeReturnsCastAcceptance=False,requestRefreshReturn='controlsSelectedCommandFallbackOnly',
        requestRefreshCommandForwarded=True,centerToSkillReturnsCanCastPredicate=True,
        comboDispatchQueuesPendingSkill=True,castComboReturnsVoid=True,cachedRequestReadByTickToCast=True,
        pendingToActualTryCastJoinProved=False)))
    need('boundaries', all(fact['evidenceBoundary'].get(key) for key in ('exact','conditional','unresolved')))


def _validate(image, fact):
    _scope(fact)
    context = NativeReferenceContext(image); base = image.pe.image_base
    owned = {}
    for role,row in fact['methods'].items():
        image.validate_method_row(row['identity'], label=LABEL)
        method = image.metadata.methods[row['identity'][0]]
        need('method-signature', context.type_name(method.return_type) == row['returnType']
            and [dict(name=image.metadata.string(item.name_index),type=context.type_name(item.type_index))
                for item in image.metadata.parameters_for(method)] == row['parameters'])
        ranges = sorted(tuple(value['runtimeTriple'][:2]) for value in image.unwind_index.family(row['identity'][3])['ranges'])
        need('complete-method-family', ranges == sorted((value['startRva'],value['endRva'])
            for value in fact['codeWindows'] if value['owner'] == role) and bool(ranges))
        owned[role] = ranges
    need('window-owners', all(row['owner'] in owned for row in fact['codeWindows']))
    image.check_windows(fact['codeWindows'], label=LABEL)
    instructions = {}
    for block in fact['blocks'].values():
        start,end = block['startRva'],block['endRva']; at = start
        covered = start
        for left,right in owned[block['owner']]:
            if left <= covered < right:
                covered = right
            if covered >= end:
                break
        need('block-ownership',start < end <= covered)
        for row in block['instructions']:
            raw = bytes.fromhex(row['hex'])
            need('contiguous-block', row['rva'] == at and 0 < len(raw) <= 15)
            need('native-instruction', image.pe.bytes_at_va(base+at,len(raw)) == raw)
            need('consistent-overlap', at not in instructions or instructions[at] == raw)
            instructions[at] = raw; at += len(raw)
        need('complete-block', at == end)
    for row in fact['fields']:
        if row.get('static'):
            td = image.named_types[row['owner']]
            matches = [value for value in image.metadata.fields_for(td) if image.metadata.string(value.name_index) == row['name']]
            need('static-field-identity',len(matches)==1 and context.field_attributes(matches[0].type_index)&16)
            need('static-field-type',context.type_name(matches[0].type_index)==row['typeName'])
            offsets=protocol.runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index)
            need('static-field-offset',offsets[row['name']]==row['offset'])
        else:
            need('typed-field', tuple(context.field(row['owner']+'::'+row['name'])) == (row['owner'],row['typeName'],row['offset']))
    for row in fact['typedRequests']:
        need('typed-request', derive_typed_usage_context(image,row['instructionRva'],label=LABEL) == row['expected'])
    for row in fact['calls']:
        raw = instructions.get(row['siteRva'],b'')
        need('direct-call', len(raw) == 5 and raw[0] == 0xe8
            and row['siteRva']+5+struct.unpack_from('<i',raw,1)[0] == row['target'][3])
        image.validate_method_row(row['target'],label=LABEL+'.callee')
    _semantics(fact)
    return dict(schema='endfield.skill-player-command-native-audit.v1',status='validated',
        nativeInputs=fact['nativeInputs'],rules=fact['rules'],facts=fact['facts'],
        evidenceBoundary=fact['evidenceBoundary'],runtimeExecutionProved=False,
        methodCount=len(fact['methods']),codeWindowCount=len(fact['codeWindows']))


def _semantics(fact):
    expected_methods={'execute':('Beyond.Gameplay.Core.PlayerController+PlayerCommandController','Execute'),
        'onExecute':('Beyond.Gameplay.AI.CharacterMainCtrlSystem','OnExecutePlayerCommand'),
        'toSkill':('Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine','_ToSkill'),
        'tickToCast':('Beyond.Gameplay.AI.CharacterSkillSystem','_TickToCastSkill'),
        'castCombo':('Beyond.Gameplay.AI.CharacterSkillSystem','CastComboSkill')}
    need('method-role-coverage',set(fact['methods'])==set(expected_methods))
    for key,value in expected_methods.items():
        need('method-role',tuple(fact['methods'][key]['identity'][1:3])==value)
    need('void-command-entries',all(fact['methods'][key]['returnType']=='void'for key in ['execute','onExecute','tickToCast','castCombo']))
    expected_blocks={'executeCapture','executeAdmission','executeAfter','onExecuteCapture','refreshRequest','commandOneFallback',
        'toSkillSelection','toSkillStoredAllow','toSkillAdmission','toSkillInputStore','tickRequest','tickSelection',
        'tickAdmissionDispatch','castGate','castFindPending','castPendingWrite','castStateRequest'}
    need('block-role-coverage',set(fact['blocks'])==expected_blocks)
    blocks={key:[bytes.fromhex(row['hex'])for row in value['instructions']]for key,value in fact['blocks'].items()}
    def contains(key,*values):
        expected=[bytes.fromhex(value)for value in values]
        need('opcode-'+key,sum(blocks[key][index:index+len(expected)]==expected
            for index in range(len(blocks[key])-len(expected)+1))==1)
    contains('executeCapture','488bd9','8bf2')
    contains('executeAdmission','83792001')
    contains('executeAdmission','4533c0','8bd6')
    contains('onExecuteCapture','488bf9','8bda')
    contains('refreshRequest','488b4060','4885c0')
    contains('refreshRequest','488b9028010000','4885d2')
    contains('refreshRequest','488b8a60040000','4885c9')
    contains('refreshRequest','4533c0','8bd3')
    contains('refreshRequest','8d4bff','0fb6d0','85c9')
    contains('commandOneFallback','84d2')
    contains('toSkillSelection','488b9928010000','4885db')
    contains('toSkillSelection','40387938')
    contains('toSkillStoredAllow','488b4148')
    contains('toSkillStoredAllow','48c1e820')
    contains('toSkillStoredAllow','39b8d8000000')
    contains('toSkillAdmission','4c8b442448','41b101','48897c2430','488bd3','44887c2428','498bce','c644242000')
    contains('toSkillInputStore','0f114310','488d4b10','0f114b20','0f115330','0f115b40','0f116350','f20f116b60')
    contains('tickRequest','807a3800')
    contains('tickSelection','488b4248')
    contains('tickSelection','48c1e820')
    contains('tickSelection','83b8d800000000')
    contains('tickAdmissionDispatch','4c8be8','4885c0')
    contains('tickAdmissionDispatch','488b8dc0000000','4c8d442440','4533c9','488bd3')
    contains('castGate','4533c9','48c744242000000000','4533c0','488bd5')
    contains('castGate','84c0')
    contains('castPendingWrite','488bd7','c7431800000000','488d8c2490000000','c6838800000000')
    contains('castPendingWrite','0f114b30','0f115340','0f115b50','0f116360','0f116b70','f20f118380000000')
    contains('castStateRequest','4533c0','418d5005')
    expected_calls={
        'executeAdmission':['OnExecutePlayerCommand'],'refreshRequest':['RefreshNextSkillRequest'],
        'commandOneFallback':['get_owner'],'toSkillStoredAllow':['get_nextSkillId','_TryGetSkill'],
        'toSkillAdmission':['GetNextSkillId','GetNextSkillCastInputView','CheckCanInterruptCurSkill','CanCastSkill'],
        'toSkillInputStore':['CopyFrom'],'tickSelection':['get_nextSkillId','_TryGetSkill'],
        'tickAdmissionDispatch':['GetNextSkillId','CheckCanInterruptCurSkill','GetNextSkillCastInputView','CanCastSkill','CastComboSkill'],
        'castGate':['CanCastSkill'],'castPendingWrite':['Dispose','CopyFrom']}
    actual={}
    for row in fact['calls']:actual.setdefault(row['block'],[]).append(row['target'][2])
    need('ordered-call-roles',actual==expected_calls)
    need('fact-coverage',[row['id']for row in fact['facts']]==['playerCommandRefreshEntry','refreshReturnUse','centerRequestAdmission','cachedComboQueue'])
    need('typed-world-root',fact['typedRequests'][0]['expected']['typeName']=='Beyond.Gameplay.Core.GameWorld')
    requests=[row['expected']for row in fact['typedRequests']]
    need('typed-request-coverage',len(requests)==5
        and [(row['typeName'],row['methodName'])for row in requests[1:]]==[
            ('System.Collections.Generic.Dictionary`2','get_Item'),('System.Collections.Generic.Dictionary`2','get_Item'),
            ('System.Collections.Generic.List`1','get_Item'),('System.Collections.Generic.List`1','Add')]
        and all(row['classArguments']==['string','Beyond.Gameplay.Core.Skill']for row in requests[1:3])
        and all(row['classArguments']==['Beyond.Gameplay.AI.CharacterSkillSystem+SkillData']for row in requests[3:]))
    fields={(row['owner'],row['name']):row for row in fact['fields']}
    required_fields=[('Beyond.Gameplay.Core.GameWorld','aiManager','executeAdmission','488b81',4),
        ('Beyond.Gameplay.AIManager','<characterMainCtrlSystem>k__BackingField','executeAdmission','488b88',4),
        ('Beyond.Gameplay.AI.CharacterMainCtrlSystem','m_centerFsm','refreshRequest','488b47',1),
        ('Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine','m_entity','toSkillSelection','488b4e',1),
        ('Beyond.Gameplay.Core.Entity','<abilityCom>k__BackingField','toSkillSelection','488b99',4),
        ('Beyond.Gameplay.Core.AbilitySystem','m_comboController','refreshRequest','488b8a',4),
        ('Beyond.Gameplay.Core.AbilitySystem','m_activeSkillMap','toSkillAdmission','498b8e',4),
        ('Beyond.Gameplay.AI.CharacterSkillSystem','m_pendingComboSkills','castFindPending','488b46',1),
        ('Beyond.Gameplay.AI.CharacterSkillSystem+SkillData','castType','castPendingWrite','c743',1),
        ('Beyond.Gameplay.AI.CharacterSkillSystem+SkillData','inputData','castPendingWrite','488d4b',1),
        ('Beyond.Gameplay.AI.CharacterSkillSystem+SkillData','casting','castPendingWrite','c683',4)]
    for owner,name,block,prefix_hex,width in required_fields:
        need('receiver-field-bindings',(owner,name)in fields)
        offset=fields[owner,name]['offset'];prefix=bytes.fromhex(prefix_hex)
        expected_uses=2 if owner=='Beyond.Gameplay.AI.CharacterSkillSystem+SkillData'and name=='inputData'else 1
        need('receiver-field-bindings',sum(raw.startswith(prefix)and len(raw)>=len(prefix)+width
            and int.from_bytes(raw[len(prefix):len(prefix)+width],'little',signed=True)==offset
            for raw in blocks[block])==expected_uses)
    need('gate-rejection-branch',blocks['castGate'][-1][0]==0x74)
    contains('toSkillAdmission','0fb6f8','84c0')
    contains('toSkillInputStore','400fb6c7')


def validate_current_native_contract(*, gameassembly, metadata, contract_path=CONTRACT_PATH):
    path = Path(contract_path)
    try:
        raw = path.read_bytes(); fact = json.loads(raw); _scope(fact); pins = fact['nativeInputs']
        gate = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
            gameassembly=Path(gameassembly),metadata=Path(metadata))
        if gate.status != 'validated':
            return dict(status=gate.status,detail=gate.detail)
        if failure := check_unity_input(gate.gameassembly,pins):
            return failure
        result = _validate(open_native_image(gate.gameassembly,gate.metadata),fact)
        after = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
            gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status != 'validated':
            return dict(status=after.status,detail=after.detail)
        if failure := check_unity_input(gate.gameassembly,pins):
            return failure
        need('contract-bookend',raw == path.read_bytes())
        return result
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:
        return native_validation_failure(error,label=LABEL,source_path=path)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_player_command_native.json')
    args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):
        parser.error('--output must be below reports/')
    result=validate_current_native_contract(gameassembly=args.gameassembly,metadata=args.metadata,contract_path=args.contract)
    if result.get('status') == 'validated':
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result.get('status') == 'validated' else 2


if __name__ == '__main__':
    raise SystemExit(main())
