"""Reviewed primary-provider retained descriptor and device I/O entry reads."""
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_queue_native import validate_native_group_windows
from scripts.game_data import wwise_owner_carrier_native as carrier
from scripts.game_data import wwise_decoder_provider_native as preparation

CONTRACT_PATH=CONTRACTS_DIR/'wwise_provider_retention_native.json'
SCHEMA='endfield.wwise-provider-retention-native.v1'


def load_retention_contract(path: Path=CONTRACT_PATH) -> dict:
    value,_=read_reviewed_contract(path,schema=SCHEMA,status='reviewedCurrentBuild',label='wwise-provider-retention')
    return value


def validate_retention_bytes(contract, image, bodies, records, parent, storage):
    fail=preparation._fail
    if contract.get('schema')!=SCHEMA or contract.get('status')!='reviewedCurrentBuild':
        fail('providerRetentionSchema','contract',SCHEMA,contract.get('schema'))
    if contract['nativeInputs'] != parent['nativeInputs'] or storage['nativeInputs'] != parent['nativeInputs']:
        fail('providerRetentionInputs','selected inputs',parent['nativeInputs'],contract['nativeInputs'])
    groups=contract['nativeGroups']
    if len(groups)!=3 or {g['key'] for g in groups}!={'providerRetainedPreparation','providerStartPrimary','deviceIoStorage'}:
        fail('providerRetentionGroups','groups','three distinct groups',[g['key'] for g in groups])
    validate_native_group_windows(groups,image,bodies,records)
    witnesses={g['key']:carrier._witnesses(g) for g in groups}
    layout=contract['layouts']
    if set(layout)!= {'provider','device'} or set(layout['provider'])!={'addressPoint','descriptor','device'} or set(layout['device'])!={'ioContext'}:
        fail('providerRetentionLayoutCoverage','layouts','reviewed fields',layout)
    if any(type(v) is not int or not 0<=v<=127 for v in layout['provider'].values()) or type(layout['device']['ioContext']) is not int or not 0<=layout['device']['ioContext']<=4096:
        fail('providerRetentionFieldBounds','layouts','bounded positive displacements',layout)
    if layout['provider']['descriptor']!=storage['layouts']['provider']['descriptorAllocation'] or layout['provider']['addressPoint']!=storage['layouts']['provider']['primaryTable']:
        fail('providerRetentionStorageLayout','provider',storage['layouts']['provider'],layout['provider'])
    expected={
      'providerRetainedPreparation':{'retainProvider':'488bf9','requireDescriptor':'488379'+layout['provider']['descriptor'].to_bytes(1,'little').hex()+'00',
         'loadDevice':'488b4f'+layout['provider']['device'].to_bytes(1,'little').hex(),
         'loadDescriptor':'488b57'+layout['provider']['descriptor'].to_bytes(1,'little').hex(),'callResolverSlot':'ff5008',
         'storeSelectedDevice':'488947'+layout['provider']['device'].to_bytes(1,'little').hex()},
      'providerStartPrimary':{'retainProvider':'488bf1','loadTable':'488b01','loadDevice':'488b4e'+layout['provider']['device'].to_bytes(1,'little').hex()},
      'deviceIoStorage':{'retainIoArgument':'488bda','retainDevice':'488bf9','storeIoContext':'48899f'+layout['device']['ioContext'].to_bytes(4,'little').hex()}}
    for group,rows in expected.items():
        for role,code in rows.items():
            actual=witnesses[group][role]['instructionHex']
            if code!=actual: fail('providerRetentionInstruction',group+'.'+role,code,actual)
