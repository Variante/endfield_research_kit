"""Compile reviewed playback reads into the existing capture manifest surface."""
from __future__ import annotations

import copy
import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract

SCHEMA = 'endfield.wwise-playback-observer.v4'
CONTRACT_PATH = CONTRACTS_DIR / 'wwise_playback_capture_native.json'
KINDS = {'pointer':1, 'u64':1, 'u32':2, 'utf16Direct':3, 'u8':4,
         'u16':5, 'bytes':6, 'argument':7, 'argumentU32':8, 'pointerFromField':9,
         'indexedU32':10, 'ringU32':11, 'ringPairU32':12, 'tapHistoryBytes':13, 'lastPointer':14}


def load_contract():
    value, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
                                     status='reviewedCurrentBuild', label='wwise-playback-observer')
    return value


def compile_reads(fields):
    if not 1 <= len(fields) <= 64:
        raise ValueError('playback read count must be 1..64')
    names, rows, spans = {}, [], 0
    for i, field in enumerate(fields):
        name, arg, offset = field['name'], field['argIndex'], field['offset']
        kind = KINDS[field['kind']]
        chain = field.get('projectionOffsets', []) if kind==13 else field.get('pointerOffsets', [])
        limit = 0x10000000 if kind!=9 and arg == 5 else 4096
        if name in names or type(arg) is not int or not 0 <= arg <= 11 or type(offset) is not int or not 0 <= offset <= limit or len(chain)>2:
            raise ValueError('unbounded or duplicate playback field')
        for j, value in enumerate(chain):
            maximum = 0x10000000 if kind!=9 and arg == 5 and j == 0 else 4096
            if type(value) is not int or not 0 <= value <= maximum or value==4097:
                raise ValueError('unbounded playback pointer step')
        if kind in (7,8) and (offset or chain):
            raise ValueError('argument reads cannot dereference storage')
        mode, reference, value = 0, 0, 0
        if 'requireArgument' in field:
            mode, reference = 3, field['requireArgument']
            if type(reference) is not int or not 0 <= reference <= 11:
                raise ValueError('unbounded playback argument guard')
        if kind == 9:
            base=field.get('baseField')
            if arg!=0 or base not in names or fields[names[base]]['kind'] not in ('pointer','pointerFromField') or any(k in field for k in ('requireMemory','requireArgument')):
                raise ValueError('field-based pointer requires an earlier pointer and its nonzero guard')
            arg=reference=names[base];mode=1;value=0
        elif kind == 14:
            count = field['countField']; maximum = field['maxCount']
            stride = field.get('stride',8)
            if count not in names or fields[names[count]]['kind'] not in ('u32','argumentU32') or type(maximum) is not int or not 1 <= maximum <= 65535 or type(stride) is not int or not 8 <= stride <= 64 or any(k in field for k in ('requireMemory','requireArgument')):
                raise ValueError('last pointer requires an earlier U32 count and bounded array')
            mode, reference, value = 1, names[count], stride << 16 | maximum
        elif kind in (6,13):
            spans += 1
            if spans > 1 or field['countField'] not in names:
                raise ValueError('span requires an earlier count and one span per phase')
            mode, reference = 1, names[field['countField']]
            if kind==13:
                maximum,prefix=field['maxTaps'],field['prefixWords']
                if arg>3 or len(chain)!=2 or type(maximum) is not int or not 1<=maximum<=64 or prefix!=4:raise ValueError('unbounded tap projection')
                value=maximum<<16|prefix
            else:
                stride, maximum = field['stride'], field['maxBytes']
                if type(stride) is not int or not 1 <= stride <= 65535 or type(maximum) is not int or not 1 <= maximum <= 512:
                    raise ValueError('unbounded playback span')
                value = stride << 16 | maximum
        elif 'requireMemory' in field:
            guard = field['requireMemory']; reference=names[guard['name']]
            mode, value = (1,0) if guard.get('nonzero') else (2,guard['equals'])
        if kind in (10,11,12):
            index=field.get('indexField');length=field.get('lengthField')
            if mode!=1 or value or index not in names or fields[names[index]]['kind'] not in ('u32','argumentU32'):
                raise ValueError('indexed read requires an earlier U32 index and nonzero field guard')
            value=names[index]
            if kind in (11,12):
                if offset%4 or length not in names or fields[names[length]]['kind']!='u32':raise ValueError('ring read requires an earlier U32 length and word offset')
                value|=names[length]<<16
        words = [arg, kind, offset, *(chain+[4097]*(2-len(chain))), mode, reference, value]
        rows.append(','.join(map(str,words))+';'); names[name]=i
    result = ''.join(rows)
    if len(result) >= 2048:
        raise ValueError('playback program exceeds bounded manifest string')
    return result


def project(base, contract, owners):
    if contract.get('schema') != SCHEMA or len(base.get('nativeHooks',[])) != 8:
        raise ValueError('playback recipe requires its reviewed contract and eight source/owner entries')
    output = copy.deepcopy(base)
    output['schema']='endfieldCapture.audioPlaybackBuild.v1'
    output['observerProfile']='audioPlaybackPhasesV1'
    external=next(h for h in output['hooks'] if h['name']=='AudioAdapter._PostEventWithExternalSource')
    external['abiId']='win64.il2cpp_post_event_external_source.v3'
    for i,row in enumerate(contract['hooks'],8):
        owner=owners[row['ownerContract']]
        if owner['nativeInputs'] != contract['nativeInputs'] or row['index'] != i:
            raise ValueError('playback owner inputs or hook order differ')
        group=next(g for g in owner['nativeGroups'] if g['key']==row['ownerGroup'])
        hook=dict(name=row['name'],sourceKind=row['ownerGroup'],module='AkSoundEngine.dll',rva=group['entryRva'],required=True,
                  abiId=row['abiId'],readProgram=compile_reads(row['memory']),memory=row['memory'],resultMemory=row['resultMemory'])
        hook['resultProgram']=compile_reads(row['resultMemory']) if row['resultMemory'] else ''
        if (hook['abiId']=='win64.transparent_entry_snapshot.v1') != (not row['resultMemory']):
            raise ValueError('paired ABI requires result reads; transparent entries cannot have results')
        output['nativeHooks'].append(hook)
    if len(output['nativeHooks'])!=32:
        raise ValueError('playback native hook count differs')
    for binding in contract['lineageArguments']:
        hook=next(h for h in output['nativeHooks'] if h['sourceKind']==binding['hookKind'])
        hook.setdefault('args',{})[binding['argumentName']]=dict(index=binding['argumentIndex'],kind='pointer')
    source=owners['wwise_source_native']
    transport=copy.deepcopy(next(t for t in source['ownerTransports'] if t['key']==contract['lineageTransportKey']))
    constructor=next(h for h in output['nativeHooks'] if h['sourceKind']==transport['constructor']['key'])
    transport['constructor']['parameterArgumentIndex']=constructor['args']['playbackBlobPointer']['index']
    output['playbackOwnerTransport']=transport
    output['playbackEvidenceBoundary']=contract['evidenceBoundary']
    output['playbackArgumentScope']=contract.get('argumentScope','')
    output['playbackSamplingBoundary']=contract.get('samplingBoundary','')
    output['captureBoundary']='Paired integer/pointer calls preserve same-invocation enter/normal-return/unwind and native output fields. Other hooks preserve transparent entry snapshots, including raw volatile vector arguments. Reads are bounded and non-atomic; each span preserves requested and copied lengths. No arguments, results or buffers are modified. Cross-thread lifetime, complete topology, individual COM HRESULTs and audibility require separate admission.'
    output['phaseNames']={'1':'enter','2':'return','3':'unwind','4':'entryOnly'}
    output['automaticWindow']=True
    return output


def validate_lineage_arguments(contract, owners, image):
    """Bind added raw-register roles within already gated complete owner bodies."""
    abi_registers=(1,2,8,9)
    for binding in contract['lineageArguments']:
        owner=owners[binding['ownerContract']]
        if owner['nativeInputs']!=contract['nativeInputs']: raise ValueError('lineage owner inputs differ')
        transport=next(t for t in owner['ownerTransports'] if t['key']==contract['lineageTransportKey'])
        endpoint=transport[binding['endpoint']]
        if endpoint['key']!=binding['hookKind']: raise ValueError('lineage endpoint differs')
        window=endpoint['windows'][binding['windowIndex']]
        encoded=bytes.fromhex(binding['instructionHex']);offset=binding['bodyOffset'];arg=binding['argumentIndex']
        if type(offset) is not int or not 0<=offset<=window['bodyLength']-len(encoded) or type(arg) is not int or not 0<=arg<4:
            raise ValueError('lineage instruction exceeds borrowed body')
        if len(encoded)!=3 or not 0x48<=encoded[0]<=0x4f or encoded[1]!=0x8b or encoded[2]>>6!=3 or ((encoded[2]&7)+(8 if encoded[0]&1 else 0))!=abi_registers[arg]:
            raise ValueError('lineage instruction does not retain its declared register argument')
        rva=int(window['rva'],16)+offset
        if image.bytes_at_va(image.image_base+rva,len(encoded))!=encoded:
            raise ValueError('lineage argument instruction differs from selected bytes')
        if 'forwardInstructionHex' in binding:
            forward=bytes.fromhex(binding['forwardInstructionHex']);at=binding['forwardBodyOffset']
            if type(at) is not int or not offset<at<=window['bodyLength']-len(forward) or len(forward)!=3 or not 0x48<=forward[0]<=0x4f or forward[1]!=0x8b or forward[2]>>6!=3:
                raise ValueError('lineage forwarding instruction is not a bounded register move')
            retained=((encoded[2]>>3)&7)+(8 if encoded[0]&4 else 0)
            origin=(forward[2]&7)+(8 if forward[0]&1 else 0)
            target=((forward[2]>>3)&7)+(8 if forward[0]&4 else 0)
            if retained!=origin or target!=abi_registers[binding['targetArgumentIndex']] or image.bytes_at_va(image.image_base+int(window['rva'],16)+at,len(forward))!=forward:
                raise ValueError('lineage forwarding does not preserve retained argument')


def validate_field_arguments(contract, owners, image):
    """Authenticate corrected raw argument roles inside borrowed complete bodies."""
    for binding in contract['fieldArguments']:
        owner=owners[binding['ownerContract']]
        if owner['nativeInputs']!=contract['nativeInputs']:raise ValueError('field argument owner inputs differ')
        hook=next(h for h in contract['hooks'] if h['ownerGroup']==binding['ownerGroup'])
        field=next(f for f in hook['memory'] if f['name']==binding['fieldName'])
        if field['argIndex']!=binding['argumentIndex']:raise ValueError('field argument role differs')
        group=next(g for g in owner['nativeGroups'] if g['key']==binding['ownerGroup'])
        window=group['windows'][binding['windowIndex']]
        for offset_key,hex_key in (('bodyOffset','instructionHex'),('useBodyOffset','useInstructionHex')):
            offset=binding[offset_key];raw=bytes.fromhex(binding[hex_key])
            if type(offset) is not int or not 0<=offset<=window['bodyLength']-len(raw):raise ValueError('field argument witness exceeds borrowed body')
            if image.bytes_at_va(image.image_base+int(window['rva'],16)+offset,len(raw))!=raw:raise ValueError('field argument selected bytes differ')


def validate_global_arguments(contract, owners, image):
    """Tie each module-relative read to a current dependency-owned RIP load."""
    bindings = contract['globalArguments']
    expected = {(h['ownerGroup'], f['name']) for h in contract['hooks']
                for f in h['memory'] if f['argIndex'] == 5}
    seen = set()
    for row in bindings:
        identity = row['hookKind'], row['fieldName']
        if identity not in expected or identity in seen:
            raise ValueError('global argument coverage differs')
        seen.add(identity)
        owner = owners[row['ownerContract']]
        if owner['nativeInputs'] != contract['nativeInputs']:
            raise ValueError('global argument owner inputs differ')
        group = next(g for g in owner['nativeGroups'] if g['key'] == row['ownerGroup'])
        hook = next(h for h in contract['hooks'] if h['ownerGroup'] == row['hookKind'])
        field = next(f for f in hook['memory'] if f['name'] == row['fieldName'])
        raw, at = bytes.fromhex(row['instructionHex']), int(row['rva'], 16)
        prefix = raw[:-4]
        valid = (len(prefix) == 3 and prefix[0] in (0x48, 0x4c) and prefix[1] == 0x8b
                 and field['kind'] == 'pointer') or (len(prefix) == 2 and prefix[0] == 0x8b
                 and field['kind'] == 'u32')
        if not valid or prefix[-1] & 0xc7 != 5 or field.get('pointerOffsets'):
            raise ValueError('global argument is not a direct typed RIP load')
        if not any(int(w['rva'], 16) <= at and at + len(raw) <= int(w['rva'], 16) + w['bodyLength']
                   for w in group['windows']):
            raise ValueError('global argument witness exceeds borrowed body')
        target = at + len(raw) + struct.unpack_from('<i', raw, len(prefix))[0]
        if target != field['offset'] or image.bytes_at_va(image.image_base + at, len(raw)) != raw:
            raise ValueError('global argument selected target or bytes differ')
    if seen != expected:
        raise ValueError('global argument coverage differs')
