"""Original Room parameter lifecycle on bounded owned storage, without engine Init."""
from __future__ import annotations

import ctypes
import hashlib
import struct
from pathlib import Path

from scripts.game_data.wwise_room_configuration_host import OwnedAllocator, RoomHostError
from scripts.game_data.wwise_room_parameters_native import load_validated


class OriginalRoomParameters:
    def __init__(self, *, gameassembly, metadata, ak_sound_engine, original_ak):
        contract, audit = load_validated(gameassembly=gameassembly, metadata=metadata,
                                         ak_sound_engine=ak_sound_engine)
        if contract is None:
            raise RoomHostError('parameter native gate ' + audit['status'] + ': ' + audit['detail'])
        if original_ak is None or not Path(original_ak).is_file():
            raise RoomHostError('explicit private original DLL copy required')
        if hashlib.sha256(Path(original_ak).read_bytes()).hexdigest() != contract['nativeInputs']['akSoundEngineSha256'].casefold():
            raise RoomHostError('private original DLL differs from selected parameter input')
        if not hasattr(ctypes, 'WinDLL'):
            raise RoomHostError('original parameter lifecycle requires Windows x64')
        self.contract, self.audit = contract, audit
        self.dll = ctypes.WinDLL(str(Path(original_ak).resolve()))
        self.base = self.dll._handle
        pointer, uint = ctypes.c_void_p, ctypes.c_uint32
        sites = audit['nativeEntryRvas']
        self.factory = ctypes.CFUNCTYPE(pointer, pointer)(self.base + int(audit['parameterFactoryRva'], 16))
        self.initialize = ctypes.CFUNCTYPE(uint, pointer, pointer, pointer, uint)(self.base + int(audit['initializeRva'], 16))
        self.clone = ctypes.CFUNCTYPE(pointer, pointer, pointer)(self.base + int(sites['roomParameterClone'], 16))
        self.update = ctypes.CFUNCTYPE(uint, pointer, ctypes.c_int16, pointer, uint)(self.base + int(sites['roomParameterUpdate'], 16))
        self.terminate = ctypes.CFUNCTYPE(uint, pointer, pointer)(self.base + int(sites['roomParameterTerminate'], 16))

    def run(self, *, stored_parameter_hex=None, serialized_parameter_hex=None, updates=()):
        """Return native writes and a distinct original clone, then release both."""
        if stored_parameter_hex is not None and serialized_parameter_hex is not None:
            raise RoomHostError('choose stored or serialized parameter input')
        updates = list(updates)
        if len(updates) > 256:
            raise RoomHostError('owned parameter update bound exceeded')
        normalized = []
        for identifier, payload in updates:
            if type(identifier) is not int or not -32768 <= identifier <= 32767:
                raise RoomHostError('parameter ID outside original signed-short ABI')
            if payload is not None and (not isinstance(payload, bytes) or len(payload) not in (1, 4)):
                raise RoomHostError('bounded parameter input must be one or four bytes, or null')
            normalized.append((identifier, payload))
        size = self.contract['clone']['byteExtent']
        stored = None if stored_parameter_hex is None else bytes.fromhex(stored_parameter_hex)
        serialized = None if serialized_parameter_hex is None else bytes.fromhex(serialized_parameter_hex)
        if stored is not None and len(stored) != size:
            raise RoomHostError('stored parameter extent differs')
        if serialized is not None and len(serialized) not in self.audit['serializedByteLengths']:
            raise RoomHostError('serialized parameter extent differs')
        allocator = OwnedAllocator()
        objects = []
        try:
            instance = self.factory(allocator.object)
            if not instance:
                raise RoomHostError('original parameter factory allocation failed')
            allocator.read(instance, size)
            objects.append(instance)
            if stored is not None:
                ctypes.memmove(instance + 8, stored[8:], size - 8)
            else:
                source = None if serialized is None else ctypes.create_string_buffer(serialized)
                if self.initialize(instance, allocator.object, source, 0 if serialized is None else len(serialized)) != 1:
                    raise RoomHostError('original parameter initialization failed')
            before = allocator.read(instance, size)
            rows = []
            for identifier, payload in normalized:
                source = None if payload is None else ctypes.create_string_buffer(payload, 4)
                initial = allocator.read(instance, size)
                result = self.update(instance, identifier, source, 0 if payload is None else len(payload))
                final = allocator.read(instance, size)
                rows.append(dict(parameterId=identifier, inputHex=None if payload is None else payload.hex(),
                                 result=result, initialParameterHex=initial.hex(), returnedParameterHex=final.hex(),
                                 changedByteOffsets=[index for index, pair in enumerate(zip(initial, final)) if pair[0] != pair[1]]))
            source_before_clone = allocator.read(instance, size)
            clone = self.clone(instance, allocator.object)
            if not clone:
                raise RoomHostError('original parameter clone allocation failed')
            if clone == instance:
                raise RoomHostError('original parameter clone reused source storage')
            clone_bytes = allocator.read(clone, size)
            objects.append(clone)
            if allocator.read(instance, size) != source_before_clone:
                raise RoomHostError('original clone changed source parameter bytes')
            expected = bytearray(source_before_clone)
            for store in self.contract['clone']['dirtyStores']:
                expected[store['offset']] = store['value']
            vtable = self.base + int(self.audit['parameterVtableRva'], 16)
            if struct.unpack_from('<Q', before)[0] != vtable or clone_bytes != bytes(expected):
                raise RoomHostError('original clone stored values/dirty/class differ')
            if allocator.errors:
                raise RoomHostError('original parameter allocator errors: ' + ','.join(allocator.errors))
            return dict(schema='endfield.room-original-parameter-lifecycle.v1',
                        initialParameterHex=before.hex(), updatedParameterHex=source_before_clone.hex(),
                        clonedParameterHex=clone_bytes.hex(), updates=rows,
                        cloneStorageDistinct=True, cloneSourceUnchanged=True, cloneCopyAndDirtyExact=True,
                        engineInitialized=False, liveAllocationGenerationClaim=False)
        finally:
            failures = []
            for instance in reversed(objects):
                try:
                    if self.terminate(instance, allocator.object) != 1:
                        failures.append('parameter termination result differs')
                except (OSError, ValueError) as error:
                    failures.append('parameter termination failed: ' + str(error)[:160])
            if allocator.live or allocator.errors:
                failures.append('parameter allocator cleanup incomplete')
            allocator.close()
            if failures:
                raise RoomHostError('; '.join(failures))
