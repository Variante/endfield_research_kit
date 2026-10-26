"""Fresh current CallServer stored-list copy; callback continuation is unproved."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs,repo_path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.owned_reference_field_copy import derive_reference_field_copy
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs

SCHEMA='callServerCallbackNativeContract.v2'
AUDIT_SCHEMA='callServerCallbackNativeContractAudit.v2'
DEFAULT_CONTRACT=CONTRACTS_DIR/'callserver_callback.json'
CONTINUATION_GATE='current_wait_list_to_on_custom_event_header_consumer'


def load_callserver_callback_contract(contract_path:Path=DEFAULT_CONTRACT,*,gameassembly:Path|None=None,metadata:Path|None=None)->dict:
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='mismatched',sourceFile=repo_path(path),sourceSha256='',nativeContract={},directCopyFacts={},callbackContinuationProved=False,validationFailures=[],usesOcrOrManualOrder=False)
    def reject(gate,expected,actual,status='mismatched'):
        audit['status']=status;audit['validationFailures'].append(dict(validator='callServerCallbackNativeContract',gate=gate,sourceFile=audit['sourceFile'],expected=expected,actual=str(actual)[:800]));return audit
    try:raw=path.read_bytes();contract=json.loads(raw)
    except (OSError,ValueError)as error:return reject('read_valid_json','readable v2 claims contract',error,'missing'if isinstance(error,OSError)else'mismatched')
    audit['sourceSha256']=hashlib.sha256(raw).hexdigest().upper()
    if not isinstance(contract,dict)or set(contract)!={'schema','status','copyClaim','callbackContinuation','evidenceBoundary'}or(contract['schema'],contract['status'])!=(SCHEMA,'reviewed'):return reject('current_claim_shape',SCHEMA,contract.get('schema')if isinstance(contract,dict)else type(contract).__name__)
    continuation=contract['callbackContinuation']
    if not isinstance(continuation,dict)or continuation!={'status':'pendingReview','gate':CONTINUATION_GATE}:return reject('continuation_boundary','pendingReview current compiled consumer',continuation)
    native=check_installed_native_inputs(gameassembly=gameassembly,metadata=metadata)
    if native.status!='validated':return reject('installed_native_inputs','validated explicit selected native pair',native.detail,native.status)
    before=snapshot_complete_reader_inputs()
    try:facts=derive_reference_field_copy(open_native_image(native.gameassembly,native.metadata),contract['copyClaim'])
    except (ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return reject('current_owned_reference_copy','typed owned original-this source to wait-field store',error,'validation_failed')
    final=check_installed_native_inputs(native.gameassembly_sha256,native.metadata_sha256,gameassembly=native.gameassembly,metadata=native.metadata)
    if final.status!='validated':return reject('selected_native_exit','unchanged selected pair',final.detail,final.status)
    try:unchanged=path.read_bytes()==raw and snapshot_complete_reader_inputs()==before
    except OSError:unchanged=False
    if not unchanged:return reject('current_source_exit','unchanged contract and complete reader/dependency bytes','changed or missing during native proof')
    audit.update(nativeContract=contract,directCopyFacts=facts,directCopyStatus='validated',selectedNativeInputs={'GameAssembly.dll':native.gameassembly_sha256,'global-metadata.dat':native.metadata_sha256})
    return reject(CONTINUATION_GATE,'fresh compiled wait-list consumption, UID/header lookup and successor dispatch proof','current direct copy is proved; callback continuation remains unproved','pendingReview')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=DEFAULT_CONTRACT);parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args(argv)
    audit=load_callserver_callback_contract(args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_bytes((json.dumps(audit,indent=2)+'\n').encode())
    print(json.dumps({k:audit.get(k)for k in('status','directCopyStatus','callbackContinuationProved','validationFailures')},indent=2));return 0 if audit['status']=='validated'else 1


if __name__=='__main__':raise SystemExit(main())
