"""Finite actual closed Lock camera property, without open generic offsets."""
import json
from scripts.game_data.memorypack import generated_initial24_capture_sources as capture


def need(key,condition):
 if not condition:raise ValueError('generatedClosedCameraProperty.'+key)


def norm(value):return json.loads(json.dumps(value))


def verify(owner,setter,read,layout,base):
 from scripts.game_data.memorypack.lock_camera_base_sources import DEFINITION,DERIVED_TYPES
 from scripts.game_data.memorypack.lock_camera_member_sources import BASE_WRAPPERS
 closed=setter.get('closedReferenceCarrier',{});decl=setter.get('closedFieldDeclaration',{});getter=setter.get('getter',{})
 need('finite-owned-closed-property-declaration',owner.get('wrappedType')in DERIVED_TYPES
  and setter['method'][1]==BASE_WRAPPERS[DERIVED_TYPES.index(owner['wrappedType'])]
  and closed.get('type')==DEFINITION+'<'+owner['wrappedType']+'>'and closed.get('argumentTypes')==[owner['wrappedType']]
  and closed.get('bytes')==8 and bytes.fromhex(closed.get('declaredTypeRecordHex',''))[10:12]==bytes((21,0))
  and bytes.fromhex(closed.get('definitionTypeRecordHex',''))[10:12]==bytes((18,0))
  and int.from_bytes(bytes.fromhex(closed['definitionTypeRecordHex'])[:8],'little')==closed.get('definitionTypeIndex')
  and setter.get('targetField')==closed['type']+'::'+read['fieldName']
  and(decl.get('ownerDefinition'),decl.get('name'),decl.get('typeName'))==(DEFINITION,read['fieldName'],capture.TYPE)
  and bytes.fromhex(decl.get('typeRecordHex',''))[10:12]==bytes((17,128))
  and int.from_bytes(bytes.fromhex(decl['typeRecordHex'])[:8],'little')==layout['typeDefinition']
  and setter.get('fieldOffsetSource')=='complete actual named compiled property effect'
  and setter.get('nativeClosedMetadataFieldOffsetsAdmitted')is False and setter.get('openGenericFieldOffsetUsed')is False)
 joined=owner.get('constructedGetterJoin',{});matches=[x for x in joined.get('setters',[])if x.get('method')==setter['method']]
 need('independently-constructed-compatible-base-getter',getter.get('closedParent')==closed and getter.get('coherentNonNullSamePointerReturn')is True
  and getter.get('nativeClosedMetadataFieldOffsetsAdmitted')is False and getter.get('refreshAdmitted')is True
  and getter.get('baseHolder')==owner['lifecycle'].get('baseHolder')and getter.get('typedCache',[])[:2]==[setter['method'][1],closed['type']]
  and joined.get('inheritedCacheCoherenceAssumed')is False and len(matches)==1
  and matches[0].get('mode')=='exact-compatible-refresh-from-constructed-base'and matches[0].get('cacheOffset')==getter['typedCache'][2])
 program=setter.get('program',{});null=program.get('ownedNullExit',{});body=program.get('selectedBytes',[])
 need('whole-owned-named-Initial24-setter',setter.get('profile')=='cached-getter-setter'and setter.get('incomingValueStoredUnchanged')is True
  and program.get('getterTarget')==base+getter['method'][3]and program.get('paddingBitsPreserved')is True
  and program.get('boolBytesNormalized')is False and program.get('metadataFieldOwnershipProved')is False
  and bool(body)and body[0][0]==base+setter['method'][3])
 from scripts.game_data.memorypack.generated_cached_initial24_sources import program as setter_program
 bytes_=[(a,bytes.fromhex(h))for a,h in body]+[(null['nullTargetVa'],bytes.fromhex(null['bytes']))]
 need('exact-whole-property-setter-byte-replay',norm(setter_program(bytes_,base+setter['method'][3],getter=base+getter['method'][3],field=setter['fieldOffset']))==program)
 return getter
