"""Name the observed flag bit through the original compiled isKinematic setter.

The managed bool setter requests a named internal call. Its compiled native
registration loop pairs that name with a bool-forwarding wrapper. The wrapper
calls a setter that reads the same typed dynamic flags getter, compares the
declared bit to the incoming bool, passes that bit to the native flag setter,
and copies the resulting bit into the cached isKinematic property.

This proves original compiled flag semantics on selected binaries. It neither
executes the setter nor proves live registration, IFix selection, awake-body
participation or contact solving. Live body snapshots are a separate input.

Evidence and admission boundary
-------------------------------
The selected registration loop uses its authenticated compiled count; the adjacent
word is separate data, not a sentinel. This exact original compiled association
does not establish a live cached registration, setter invocation or IFix choice.
Typed dynamic flag buffering is independent of static pose getter buffering.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import load_layout
from scripts.game_data.il2cpp.native_image import open_native_image, NATIVE_MAPPER_PATH
from scripts.game_data.il2cpp.protocol import load_native_mapper

CONTRACT=CONTRACTS_DIR/'collision_body_mode_native.json'
SCHEMA='endfield.collision-body-mode-native.v2'


def validate_route(image,player,contract):
    method=contract['managedSetter']
    image.validate_method_row(method['method'],label='collision-body-mode')
    image.validate_method_row([*method['method'][:3],method['parameterType']],label='collision-body-mode-bool')
    raw=image.pe.bytes_at_va(image.pe.image_base+method['method'][3],method['bodyBytes'])
    if hashlib.sha256(raw).hexdigest()!=method['bodySha256']:
        raise ValueError('managed isKinematic setter body hash differs')
    lookup=image.pe.bytes_at_va(image.pe.image_base+method['lookupRva'],12)
    if (lookup[:3]!=bytes.fromhex('488d0d') or lookup[7]!=0xe8
            or method['lookupRva']+7+struct.unpack_from('<i',lookup,3)[0]!=method['literalRva']
            or method['lookupRva']+12+struct.unpack_from('<i',lookup,8)[0]!=method['resolverRva']):
        raise ValueError('managed isKinematic literal/resolver route differs')
    literal=image.pe.c_string_at_va(image.pe.image_base+method['literalRva'])
    name=f"{method['method'][1]}::{method['method'][2]}"
    if literal!=name+'('+method['parameterType']+')':
        raise ValueError('managed isKinematic requested name differs')
    for key,prefix in (('cacheLoadRva','488b05'),('cacheStoreRva','488905')):
        at=method[key];cell=image.pe.bytes_at_va(image.pe.image_base+at,7)
        if cell[:3]!=bytes.fromhex(prefix) or at+7+struct.unpack_from('<i',cell,3)[0]!=method['cacheCellRva']:
            raise ValueError('managed isKinematic cache route differs:'+key)
    if image.pe.bytes_at_va(image.pe.image_base+method['tailJumpRva'],3)!=bytes.fromhex('48ffe0'):
        raise ValueError('managed isKinematic tail forwarding differs')
    registration=contract['layout']['registration'];row=contract['registration']
    count=registration['count'];slot=row['slot']
    if not 0<=slot<count<=65536 or row['name']!=name:
        raise ValueError('isKinematic registration identity/count differs')
    if row.get('termination')!='compiled-count':
        raise ValueError('isKinematic registration compiled-count boundary differs')
    # The reviewed loop authenticates the count. The next word belongs to
    # adjacent data in this build and is not an array sentinel.
    names=player.bytes_at_va(player.image_base+registration['nameTableRva'],count*8)
    functions=player.bytes_at_va(player.image_base+registration['functionTableRva'],count*8)
    resolved=[]
    for index in range(count):
        current=player.c_string_at_va(struct.unpack_from('<Q',names,index*8)[0])
        target=struct.unpack_from('<Q',functions,index*8)[0]
        _,section,_=player.file_offset_for_va(target)
        if not current.startswith('UnityEngine.') or section!='.text':
            raise ValueError('isKinematic registration entry invalid:'+str(index))
        resolved.append(current)
    wrapper=next(w for w in contract['codeWindows'] if w['role']=='setter_wrapper')
    if (resolved.count(name)!=1 or resolved[slot]!=name or row['functionRva']!=wrapper['rva']
            or struct.unpack_from('<Q',functions,slot*8)[0]!=player.image_base+wrapper['rva']):
        raise ValueError('isKinematic registration name/function pair differs')
    getter=next(slot for slot in contract['vtableSlots'] if slot['role']=='typed_dynamic_flags')
    if contract['layout']['mode']['getFlagsSlot']!=getter['slot']*8:
        raise ValueError('isKinematic does not consume the typed flags getter')
    if method['method'][2]!='set_isKinematic' or contract['representation']['bodyModeName']!='kinematic':
        raise ValueError('isKinematic semantic name differs')


def load(*,gameassembly,metadata,unityplayer):
    contract,gate=load_layout(gameassembly=Path(gameassembly),metadata=Path(metadata),unityplayer=Path(unityplayer),
                             contract_path=CONTRACT,schema=SCHEMA,validator='collision_body_mode_native')
    if contract is None:
        return None,gate
    try:
        image=open_native_image(Path(gameassembly),Path(metadata))
        player=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(Path(unityplayer))
        pins=contract['nativeInputs']
        # The shared opened image is cached by path. Bind its actual bytes,
        # including metadata, to this selected build before reading identities.
        for key,data in (('gameAssemblySha256',image.pe.buf),('metadataSha256',image.metadata.buf),
                         ('unityPlayerSha256',player.buf)):
            if hashlib.sha256(data).hexdigest()!=pins[key]:
                raise ValueError('opened body-mode image differs from selected native inputs:'+key)
        validate_route(image,player,contract)
        after=check_installed_native_inputs(pins['gameAssemblySha256'],pins['metadataSha256'],
                                           gameassembly=Path(gameassembly),metadata=Path(metadata))
        if after.status!='validated' or sha256_file(Path(unityplayer)).lower()!=pins['unityPlayerSha256']:
            raise ValueError('body-mode selected native inputs changed')
        return contract,{**gate,'status':'validated','namedSetter':contract['managedSetter']['method'][1:3]}
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,struct.error) as error:
        return None,{**gate,'status':'failed','diagnostics':[{'check':'named_body_mode','detail':str(error)[:1800]}]}
