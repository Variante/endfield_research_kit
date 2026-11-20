"""Check bounded writer/checkpoint fragments against selected COFF and DLL bytes.

This proves a conditional local instruction model. It never authenticates a
whole producer, recorder epoch, CRT implementation, or runtime delivery.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.coff_pe_match import CoffObject, PeImage, bookended_inputs, match_function, cohort_bindings

SCHEMA = 'endfield.capture-checkpoint-writer-native-contract.v2'
CONTRACT_PATH = CONTRACTS_DIR / 'capture_checkpoint_writer_native.json'


def require(condition, check):
    if not condition:
        raise ValueError('checkpoint-writer: ' + check)


def validate_fragments(contract, sections):
    """Check the reviewed local control/data relations, not just window hashes."""
    operands = contract['operands']
    anchors = contract['anchors']
    def raw(key):
        row = anchors[key]
        value = sections[row['owner']][row['offset']:row['offset'] + len(bytes.fromhex(row['hex']))]
        require(value == bytes.fromhex(row['hex']), 'anchor bytes ' + key)
        return value
    def disp(key):
        value = operands[key]
        require(type(value) is int and 0 <= value < 2**31, 'displacement ' + key)
        return struct.pack('<I', value)
    require(raw('pollRecorder') == b'\x48\x8b\x8b' + disp('recorder'), 'poll recorder receiver')
    require(raw('pollWriteReceiver') == bytes.fromhex('488d542430488bcb'), 'same stack record and writer receiver')
    require(raw('pollWriteResult') == b'\x88\x83' + disp('writeOk') + bytes.fromhex('41b601'), 'write result and wrote flag')
    require(raw('pollUnrecorded') == b'\x48\xff\x83' + disp('unrecorded'), 'failed writer increments unrecorded')
    require(raw('pollFlushReceiver') == b'\x48\x8d\x8b' + disp('output'), 'same output flush receiver')
    require(raw('pollStatusReceiver') == bytes.fromhex('4533c033d2488bcb'), 'nonfinal status on same writer')
    require(raw('writeOutputReceiver') == b'\x49\x8d\x8f' + disp('output'), 'write output field')
    require(raw('writeSuccess') == bytes.fromhex('488b4560490187') + disp('bytes') + b'\x49\xff\x87' + disp('rows') + bytes.fromhex('b301'), 'write success increments bytes and rows')
    require(raw('writeFailure') == b'\x49\xff\x87' + disp('unrecorded') + bytes.fromhex('32db'), 'write failure excludes success counters')
    for key, prefix, operand in [('statusRows', '488b96', 'rows'), ('statusBytes', '488b96', 'bytes'), ('statusUnrecorded', '488b96', 'unrecorded')]:
        require(raw(key) == bytes.fromhex(prefix) + disp(operand), 'status writer field ' + key)
    for key, prefix, operand in [('statusDropped', '4c8b70', 'dropped'), ('statusUnreadable', '4c8b60', 'unreadable'), ('statusTruncated', '4c8b78', 'truncated')]:
        value = operands[operand]
        require(type(value) is int and 0 < value < 128 and raw(key) == bytes.fromhex(prefix) + bytes([value]), 'status recorder counter ' + key)
    require(raw('statusAttempted') == bytes.fromhex('488b0848894c2478'), 'attempted snapshot')
    require(raw('statusAdmitted') == bytes.fromhex('488b40084889442470'), 'admitted snapshot')
    for key in ('statusRecorderDropped', 'statusRecorderUnreadable', 'statusRecorderTruncated', 'statusRecorderAttempted', 'statusRecorderAdmitted'):
        require(raw(key) == b'\x48\x8b\x86' + disp('recorder'), 'same recorder pointer load ' + key)
    expected_moves = {'outputDropped':'498bd6', 'outputUnreadable':'498bd4', 'outputTruncated':'498bd7', 'outputAttempted':'488b542478', 'outputAdmitted':'488b542470'}
    for key, expected in expected_moves.items():
        require(raw(key) == bytes.fromhex(expected), 'output counter carrier ' + key)
    branch_specs={'drain-limit':('poll','73'), 'empty-queue':('poll','74'), 'failed-output':('poll','74'),
                  'written-loop':('poll','eb'), 'unrecorded-loop':('poll','eb'), 'no-new-write-skip-flush':('poll','74'),
                  'status-not-due':('poll','72'), 'within-byte-budget':('write','76'),
                  'over-budget-skips-increment':('write','eb'), 'output-good':('write','74'),
                  'failed-write-skips-increment':('write','eb')}
    branches={row['role']:row for row in contract['branches']}
    require(len(branches)==len(contract['branches']) and set(branches)==set(branch_specs), 'complete branch role coverage')
    for role,row in branches.items():
        require((row['owner'],row['opcode'])==branch_specs[role] and type(row['displacementBytes'])is int, 'branch semantic role '+role)
        at = row['offset']; code = sections[row['owner']]
        opcode = bytes.fromhex(row['opcode'])
        width = row['displacementBytes']
        require(width in (1, 4) and code[at:at+len(opcode)] == opcode, 'branch opcode ' + row['role'])
        target = at + len(opcode) + width + int.from_bytes(code[at+len(opcode):at+len(opcode)+width], 'little', signed=True)
        require(target == row['targetOffset'], 'branch target ' + row['role'])
    predicates={'empty-queue':bytes.fromhex('84c0'), 'failed-output':b'\x80\xbb'+disp('writeOk')+b'\0',
                'no-new-write-skip-flush':bytes.fromhex('4584f6'), 'within-byte-budget':bytes.fromhex('483bc8'),
                'output-good':bytes.fromhex('42f68439')+struct.pack('<I',operands['output']+16)+b'\x06'}
    for role,predicate in predicates.items():
        row=branches[role];at=row['offset']
        require(sections[row['owner']][at-len(predicate):at]==predicate, 'branch predicate '+role)
    require(branches['failed-output']['targetOffset']==anchors['pollUnrecorded']['offset'], 'failed output target anchor')
    require(branches['output-good']['targetOffset']==anchors['writeSuccess']['offset'], 'successful output target anchor')
    end_success=anchors['writeSuccess']['offset']+len(raw('writeSuccess'))
    require(branches['over-budget-skips-increment']['targetOffset']==end_success
            and branches['failed-write-skips-increment']['targetOffset']==end_success, 'failure skips counter anchors')
    require(branches['empty-queue']['targetOffset']==branches['drain-limit']['targetOffset']
            and branches['written-loop']['targetOffset']==branches['unrecorded-loop']['targetOffset'], 'shared drain and loop targets')
    return {'writerCounterFieldJoinsValidated': True, 'boundedWriterInstructionRelationsValidated': True,
            'statusCounterCarrierJoinsValidated': True, 'compiledCheckpointSemanticsProved': False,
            'crtHelperIdentityAndSemanticsProved': False,
            'localDeliveryProved': False, 'numericAdmission': False, 'transportAdmitted': False}


def evaluate(contract, objects, pe):
    require(contract['schema'] == SCHEMA and contract['status'] == 'reviewed', 'contract schema/status')
    require(contract['evidenceBoundary'] == 'conditional' and contract['conditions'] and contract['unresolved'], 'explicit conditional boundary')
    functions = contract['functions']; results = {}; sections = {}
    for role, spec in functions.items():
        obj = objects[spec['object']]
        result = match_function(obj, pe, spec['symbol'])
        require(result['unique'], 'unique complete function candidate ' + role)
        candidate = result['candidates'][0]
        require(candidate['rva'] == spec['rva'] and candidate['bytes'] == spec['bytes'], 'selected function interval ' + role)
        results[role] = result
        sections[role] = obj.sections[result['coffSection']].raw
        require(hashlib.sha256(sections[role]).hexdigest() == spec['objectSectionSha256'], 'reviewed object program ' + role)
    bindings = cohort_bindings(list(results.values()))
    for role, spec in functions.items():
        results[role] = match_function(objects[spec['object']], pe, spec['symbol'], symbol_bindings=bindings)
    calls = {row['role']:row for row in contract['calls']}
    labels = {'attempted':'outputAttempted', 'admitted':'outputAdmitted', 'written':'statusRows',
              'dropped':'outputDropped', 'unrecorded':'statusUnrecorded', 'unreadableFields':'outputUnreadable',
              'truncatedFields':'outputTruncated', 'bytesWritten':'statusBytes'}
    require(len(calls) == len(contract['calls']) and set(calls) == {'poll-pop','poll-write','poll-flush','poll-periodic-status','write-output'} | {'label-'+n for n in labels} | {'value-'+n for n in labels}, 'complete selected call coverage')
    for role,owner,target in [('poll-pop','poll','pop'),('poll-write','poll','write'),('poll-flush','poll','flush'),('poll-periodic-status','poll','status'),('write-output','write','outputWrite')]:
        require(calls[role]['owner']==owner and calls[role].get('target')==target, 'core call role '+role)
    for role,key in [('poll-pop','pollRecorder'),('poll-write','pollWriteReceiver'),('poll-flush','pollFlushReceiver'),('poll-periodic-status','pollStatusReceiver'),('write-output','writeOutputReceiver')]:
        anchor=contract['anchors'][key]
        require(calls[role]['relocationOffset']==anchor['offset']+len(bytes.fromhex(anchor['hex']))+1, 'call receiver adjacency '+role)
    for call in calls.values():
        result = results[call['owner']]['candidates'][0]
        reloc = [r for r in result['relocations'] if r['offset'] == call['relocationOffset']]
        expected_symbol=functions[call['target']]['symbol'];expected_target=results[call['target']]['candidates'][0]['rva']
        require(len(reloc) == 1 and reloc[0]['symbol'] == expected_symbol and reloc[0]['targetRva'] == expected_target, 'selected call binding ' + call['role'])
        offset=call['relocationOffset']
        require(reloc[0]['kind']==4 and sections[call['owner']][offset:offset+4]==bytes(4), 'direct REL32 zero addend '+call['role'])
        instruction=pe.read(result['rva']+offset-1,5)
        require(instruction[0]==0xe8 and result['rva']+offset+4+int.from_bytes(instruction[1:],'little',signed=True)==expected_target, 'actual CPU call target '+call['role'])
    literal_rows = []
    require(len(contract['statusLabels']) == len(labels) and {r['name'] for r in contract['statusLabels']} == set(labels), 'complete status label coverage')
    for row in contract['statusLabels']:
        require(row['carrierAnchor'] == labels[row['name']], 'status label carrier identity')
        at=row['relocationOffset']-3
        require(sections['status'][at:at+3] == bytes.fromhex('488d15'), 'label address in RDX')
        anchor=contract['anchors'][row['carrierAnchor']]
        require(anchor['owner']=='status' and anchor['offset']==at+12, 'label to carrier adjacency')
        end=anchor['offset']+len(bytes.fromhex(anchor['hex']))
        require(sections['status'][end:end+3] == bytes.fromhex('488bc8'), 'same returned ostream receiver')
        require(calls['label-'+row['name']]['owner']=='status' and calls['label-'+row['name']]['relocationOffset']==at+8
                and calls['label-'+row['name']]['target']=='stringInsert'
                and calls['value-'+row['name']]['owner']=='status' and calls['value-'+row['name']]['relocationOffset']==end+4
                and calls['value-'+row['name']]['target']=='unsignedInsert', 'label/value receiving calls')
        rels = results['status']['candidates'][0]['relocations']
        selected = [r for r in rels if r['offset'] == row['relocationOffset']]
        require(len(selected) == 1 and selected[0]['kind'] == 4, 'status label relocation')
        target = selected[0]['targetRva']
        require(pe.cstring(target) == ',"' + row['name'] + '":', 'linked status label ' + row['name'])
        literal_rows.append({'name':row['name'], 'targetRva':target})
    rules = validate_fragments(contract, sections)
    return {'rules': rules, 'matches': results, 'statusLabels': literal_rows,
            'conditions': contract['conditions'], 'unresolved': contract['unresolved']}


def validate_writer(*, dll, session_object, provider_object, runtime_object, contract_path=CONTRACT_PATH):
    paths = {key:Path(value).resolve() for key,value in {'dll':dll, 'sessionObject':session_object, 'providerObject':provider_object, 'runtimeObject':runtime_object}.items()}
    report = {'schema':'endfield.capture-checkpoint-writer-native-audit.v2', 'status':'blocked', 'rules':{}, 'failures':[]}
    try:
        contract_path = Path(contract_path).resolve()
        with bookended_inputs([contract_path, *paths.values()]) as (data, identities):
            report['sourceInputs']=identities
            contract = json.loads(data[contract_path])
            for key,path in paths.items():
                actual=hashlib.sha256(data[path]).hexdigest();expected=contract['nativeInputs'][key]
                require(actual == expected, 'selected input hash '+key+'; source='+str(path)+'; expected='+str(expected)+'; actual='+actual)
            result = evaluate(contract, {key:CoffObject(data[paths[key]]) for key in ('sessionObject','providerObject','runtimeObject')}, PeImage(data[paths['dll']]))
        report.update(result, status='validated-conditional-fragments', inputs=identities)
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error) as error:
        report.update(status='blocked', rules={}, failures=[{'validator':'capture_checkpoint_writer_native', 'check':str(error)[:1200]}])
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('dll','session-object','provider-object','runtime-object','output'):
        parser.add_argument('--'+flag, type=Path, required=True)
    args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    require(args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()), 'output under reports/')
    result=validate_writer(dll=args.dll,session_object=args.session_object,provider_object=args.provider_object,runtime_object=args.runtime_object)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k]for k in ('status','rules','failures')}))
    return 0 if result['status']=='validated-conditional-fragments' else 1


if __name__=='__main__':
    raise SystemExit(main())
