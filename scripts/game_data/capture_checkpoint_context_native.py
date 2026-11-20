"""Bounded staged context-producer/epoch candidates from COFF and linked bytes.

TLS offsets are consistency witnesses, never independent named TLS ownership.
This validator does not admit a capture, saved-register ABI, hook epoch or local
delivery; it authenticates only the explicitly enumerated compiled fragments.
"""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.coff_pe_match import (CoffObject,PeImage,match_function,cohort_bindings,
    cohort_relocation_consistency,bookended_inputs)

SCHEMA='endfield.capture-checkpoint-context-native-contract.v2'
AUDIT_SCHEMA='endfield.capture-checkpoint-context-native-audit.v2'
CONTRACT_PATH=CONTRACTS_DIR/'capture_checkpoint_context_native.json'
RULES=dict(completeComdatCandidateJoinsProved=True,sharedTlsRelativeOffsetConsistent=True,
    independentTlsNamedIdentityProved=False,conditionalEarlyCounterIncrementProved=True,
    everyContextEarlyExitCounted=False,recorderCodeReferencesEnumerated=True,
    sequenceCodeReferencesAreIncrementOnly=True,allModuleWritesEnumerated=False,
    ordinaryStartAttemptGuardProved=True,wholeRecorderEpochProved=False,
    allScopedHooksEnabledForPrefixProved=False,backendImplementationProved=False,localDeliveryProved=False,
    transportAdmitted=False)


def _need(ok,check,expected=None,actual=None):
    if not ok:raise ValueError(check+': expected='+str(expected)[:350]+'; actual='+str(actual)[:700])


def _relative(raw,rva):
    if len(raw)==5 and raw[0]in(0xe8,0xe9):return rva+5+struct.unpack_from('<i',raw,1)[0]
    if len(raw)==2 and raw[0]in(0x74,0x75):return rva+2+int.from_bytes(raw[1:],'little',signed=True)
    if len(raw)==6 and raw[:2]in(b'\x0f\x84',b'\x0f\x85'):return rva+6+struct.unpack_from('<i',raw,2)[0]
    raise ValueError('checkpoint-context-relative-opcode')


def _join_bodies(obj,pe,contract):
    rows=contract['functions'];required={'context','pairedBegin','pairedRecord','entry','start','stop','pairCaller'}
    _need(set(rows)==required,'checkpoint-function-coverage',sorted(required),sorted(rows))
    candidates=[match_function(obj,pe,row['symbol'])for row in rows.values()]
    bindings=cohort_bindings(candidates)
    matched={role:match_function(obj,pe,row['symbol'],symbol_bindings=bindings)for role,row in rows.items()}
    for role,result in matched.items():
        row=rows[role];_need(result['unique']and len(result['candidates'])==1,'checkpoint-unique-body',role,result)
        actual=result['candidates'][0]
        _need(actual['rva']==row['rva']and actual['bytes']==row['bytes']and
            hashlib.sha256(pe.read(row['rva'],row['bytes'])).hexdigest()==row['sha256'],
            'checkpoint-selected-body',row,actual)
    return matched


def _validate(obj,pe,contract):
    _need(json.dumps(contract['rules'],sort_keys=True)==json.dumps(RULES,sort_keys=True),'checkpoint-rule-boundary',RULES,contract['rules'])
    _need({r['id']for r in contract['facts']}=={'compiledContextEarlyCounter','relativeTlsConsistency','boundedEpochCandidates'}
        and len(contract['facts'])==3 and all(r['evidence']=='conditional'and r['boundary']
        and json.dumps(r['rules'],sort_keys=True)==json.dumps(RULES,sort_keys=True)for r in contract['facts']),
        'checkpoint-facts','three conditional rule-bound facts',contract['facts'])
    matches=_join_bodies(obj,pe,contract);functions=contract['functions']
    consistency=cohort_relocation_consistency(list(matches.values()))
    expected_tls=contract['tlsSymbol']
    selected=[r for r in consistency if r['symbol']==expected_tls]
    _need(len(selected)==1 and selected[0]['consistent']is True and selected[0]['independentTlsLayoutProved']is False,
        'checkpoint-shared-relative-TLS','same symbol offset, independent named TLS unproved',selected)
    tls=selected[0]
    _need(len(tls['references'])>=4 and len({r['function']for r in tls['references']})>=2,
        'checkpoint-TLS-reference-coverage','multiple context and paired references',tls)
    def checked(row):
        function=functions[row['owner']];raw=bytes.fromhex(row['hex']);rva=row['rva']
        _need(raw and function['rva']<=rva<rva+len(raw)<=function['rva']+function['bytes']and pe.read(rva,len(raw))==raw,
            'checkpoint-span-body',row,'native bytes/ownership differ');return raw
    spans=contract['spans'];_need(set(spans)=={'earlyCounter','startAttempt'},'checkpoint-span-coverage','earlyCounter/startAttempt',spans)
    row=spans['earlyCounter'];raw=checked(row);operands=contract['earlyCounterOperands']
    slot=operands['savedRecorderStackSlot'];offset=operands['counterSlotOffset']
    _need(type(slot)is int and type(offset)is int and slot>=0 and offset>=0,'checkpoint-counter-operands','nonnegative reviewed offsets',operands)
    expected=bytes.fromhex('4d85ff')+raw[3:5]+bytes.fromhex('4084f6')+raw[8:10]+bytes.fromhex('488b4424')+slot.to_bytes(1,'little')+bytes.fromhex('f048ff40')+offset.to_bytes(1,'little')
    _need(len(raw)==len(expected)and raw==expected and raw[3]==0x74 and raw[8]==0x75
        and _relative(raw[3:5],row['rva']+3)==row['rva']+len(raw)
        and _relative(raw[8:10],row['rva']+8)==row['rva']+len(raw),
        'checkpoint-counter-machine-predicate','R15 nonzero and SIL zero: reload saved pointer and LOCK INC counter; otherwise join after increment',raw.hex())
    row=spans['startAttempt'];raw=checked(row)
    _need(len(raw)==42 and raw[:2]==bytes.fromhex('84c0')and raw[2]==0x75
        and raw[4:11]==bytes.fromhex('b8010000008605')and raw[15:19]==bytes.fromhex('84c00f84')and raw[23:29]==bytes.fromhex('44882e488d05')
        and raw[33:36]==bytes.fromhex('488946')and raw[36]==struct.calcsize('<Q')and raw[37]==0xe9,
        'checkpoint-start-attempt-machine-guard','if non-adopt: exchange byte1; previous0 takes ordinary first-start; previous1 returns rejection',raw.hex())
    _need(_relative(raw[2:4],row['rva']+2)==contract['startGuardTargets']['adopt']
        and _relative(raw[17:23],row['rva']+17)==contract['startGuardTargets']['firstOrdinary']
        and _relative(raw[37:42],row['rva']+37)==contract['startGuardTargets']['rejectedReturn'],
        'checkpoint-start-attempt-edges',contract['startGuardTargets'],raw.hex())
    # Enumerate all executable-object references, rather than merely selected uses.
    by_section={}
    for role,function in functions.items():by_section[obj.symbol(function['symbol']).section]=role
    inventories={}
    for role,symbol in contract['storageSymbols'].items():
        target=obj.symbol(symbol);refs=[]
        for section in obj.sections.values():
            if not section.characteristics&0x20000000:continue
            for offset,index,kind in section.relocations:
                if index!=target.index:continue
                _need(section.index in by_section,'checkpoint-reference-body-coverage',symbol,section.index)
                owner=by_section[section.index];candidate=matches[owner]['candidates'][0]
                links=[r for r in candidate['relocations']if r['offset']==offset and r['symbol']==symbol]
                _need(len(links)==1,'checkpoint-storage-relocation-site','one matching linked relocation',(owner,offset,symbol))
                linked=links[0]
                _need(kind in(4,5),'checkpoint-storage-relocation','RIP relative data reference',linked)
                refs.append(dict(owner=owner,offset=offset,kind=kind,targetRva=linked['targetRva'],prefix=section.raw[max(0,offset-5):offset].hex()))
        _need(refs and len({r['targetRva']for r in refs})==1,'checkpoint-shared-storage-symbol',symbol,refs)
        inventories[role]=refs
    _need(set(inventories)=={'recorder','sequence','attempted','retained'},'checkpoint-storage-coverage','four selected storage roles',inventories)
    sequence=inventories['sequence']
    _need({r['owner']for r in sequence}=={'entry','context','pairedRecord'}and len(sequence)==3
        and all(r['prefix']==bytes.fromhex('f0480fc105').hex()for r in sequence),
        'checkpoint-sequence-reference-operations','every executable COFF reference is LOCK XADD qword',sequence)
    increments=contract['sequenceIncrements']
    _need(set(increments)=={'entry','context','pairedRecord'},'checkpoint-sequence-increment-coverage','three complete increment transfers',increments)
    for ref in sequence:
        role=ref['owner'];row=increments[role];raw=checked(row)
        if role=='entry':prefix=bytes.fromhex('b801000000f0480fc105')
        elif role=='pairedRecord':prefix=bytes.fromhex('bb010000008bc3f0480fc105')
        else:
            parameters=contract['sequenceLocalOperands']
            _need(set(parameters)=={'indexSlot','phaseSlot','phaseValue'}and all(type(value)is int for value in parameters.values()),'checkpoint-sequence-local-operands','integer reviewed stack/value operands',parameters)
            prefix=(bytes.fromhex('b801000000448965')+parameters['indexSlot'].to_bytes(1,'little',signed=True)
                +bytes.fromhex('c745')+parameters['phaseSlot'].to_bytes(1,'little',signed=True)
                +parameters['phaseValue'].to_bytes(4,'little')+bytes.fromhex('f0480fc105'))
        _need(row['owner']==role and raw[:len(prefix)]==prefix and len(raw)==len(prefix)+7
            and raw[-3:]==bytes.fromhex('48ffc0')and row['rva']+len(prefix)==functions[role]['rva']+ref['offset'],
            'checkpoint-sequence-plus-one-'+role,'RAX=1; no RAX clobber; LOCK XADD then returned-sequence INC',raw.hex())
    recorder=inventories['recorder']
    opcodes={}
    for ref in recorder:
        raw=obj.sections[obj.symbol(functions[ref['owner']]['symbol']).section].raw
        opcodes.setdefault(ref['owner'],[]).append(raw[ref['offset']-3:ref['offset']].hex())
    _need(opcodes=={'pairedBegin':['4c8b3d'],'start':['488905','48890d'],'stop':['488705'],'context':['488b05'],'entry':['4c8b35']},
        'checkpoint-recorder-reference-operations','three loads, two start stores, one stop exchange',opcodes)
    _need(len(inventories['attempted'])==1 and inventories['attempted'][0]['owner']=='start',
        'checkpoint-attempted-reference-coverage','one ordinary-start exchange',inventories['attempted'])
    attempted=inventories['attempted'][0]
    _need(spans['startAttempt']['rva']+11==functions['start']['rva']+attempted['offset'],
        'checkpoint-attempted-guard-site','the guard XCHG displacement is the unique attempted-symbol reference',attempted)
    for call in contract['directCalls']:
        if call['owner']=='pairCaller':
            function=functions['pairCaller'];raw=pe.read(call['rva'],5)
            _need(function['rva']<=call['rva']<call['rva']+5<=function['rva']+function['bytes'],'checkpoint-pair-caller-owner',function,call)
        else:
            caller=contract['contextCallers'][call['owner']];raw=pe.read(call['rva'],5)
            _need(hashlib.sha256(pe.read(caller['rva'],caller['bytes'])).hexdigest()==caller['sha256']
                and caller['rva']<=call['rva']<call['rva']+5<=caller['rva']+caller['bytes'],
                'checkpoint-context-caller-body',caller,call)
            prelude=pe.read(call['rva']-13,13);index=caller['hookIndex']
            _need(type(index)is int and 0<=index<1<<32 and prelude[:5]==b'\xb9'+index.to_bytes(4,'little')
                and prelude[5:9]==bytes.fromhex('488d9424'),'checkpoint-context-caller-index','MOV ECX selected index; LEA RDX reviewed frame slot',prelude.hex())
        _need(raw[0]==0xe8 and _relative(raw,call['rva'])==functions[call['target']]['rva'],
            'checkpoint-actual-caller-target',call,raw.hex())
    _need(len(contract['directCalls'])==len(contract['contextCallers'])+1
        and{r['owner']for r in contract['directCalls']}==set(contract['contextCallers'])|{'pairCaller'},
        'checkpoint-caller-coverage','context callers and one pair caller',contract['directCalls'])
    return dict(matches=matches,tlsConsistency=selected,storageReferenceInventory=inventories,
        rules=dict(RULES),facts=contract['facts'])


def load_capture_checkpoint_context(contract_path=CONTRACT_PATH,*,staged_dll,session_object):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',inputIdentities=[],rules={},facts=[],matches={},failures=[])
    try:
        with bookended_inputs([path,staged_dll,session_object])as(data,identities):
            contract=json.loads(data[path.resolve()]);_need(contract['schema']==SCHEMA and contract['status']=='reviewed','checkpoint-reviewed-contract',SCHEMA,contract.get('schema'))
            for role,source in(('stagedDll',staged_dll),('sessionObject',session_object)):
                raw=data[Path(source).resolve()];pin=contract['inputs'][role]
                _need(len(raw)==pin['bytes']and hashlib.sha256(raw).hexdigest()==pin['sha256'],'checkpoint-input-pin',pin,dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            result=_validate(CoffObject(data[Path(session_object).resolve()]),PeImage(data[Path(staged_dll).resolve()]),contract)
        audit.update(result,status='validated',inputIdentities=identities)
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',rules={},facts=[],matches={},inputIdentities=[])
        audit['failures'].append(dict(validator='capture_checkpoint_context_native',check=str(error).split(':',1)[0],detail=str(error)[:2000],source=str(path)))
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--staged-dll',type=Path,required=True);parser.add_argument('--session-object',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in('reports','scratch','tmp')):parser.error('output must be reports/scratch/tmp')
    audit=load_capture_checkpoint_context(staged_dll=args.staged_dll,session_object=args.session_object)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(dict(status=audit['status'],failures=audit['failures']),indent=2));return int(audit['status']!='validated')
if __name__=='__main__':raise SystemExit(main())
