"""Selected camera-state reference Param, with only a null nested constant."""
import json
from scripts.game_data.memorypack.reference_param import derive_reference_parameter
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
LABEL='cameraStateParam'
VALUE='Beyond.Gameplay.View.CameraControlState'


def null_state_program(rows,entry,header,barrier):
 g=_Path(rows);g.at=entry
 g.take('mov [rsp+0x10], rbx','mov [rsp+0x18], rsi','push rdi','sub rsp, 0x20');raw=bytes.fromhex(g.row()['bytes']);scalar.need(LABEL,'initializationGuard',(7,b'\x80\x3d',0),(len(raw),raw[:2],raw[-1]))
 g.take('mov rbx, rdx','mov rdi, rcx');g.branch(5,True)
 g.take('lea rdx, [rsp+0x30]');r=g.row();scalar.need(LABEL,'headerDefault',bytes.fromhex('c644243000'),bytes.fromhex(r['bytes']));g.take('mov rcx, rdi');g.call(header);g.take('test al, al');g.branch(4,True)
 g.take('mov rcx, rbx');r=g.row();scalar.need(LABEL,'clearOutput',bytes.fromhex('48c70300000000'),bytes.fromhex(r['bytes']));g.call(barrier);g.take('mov rbx, [rsp+0x38]','mov rsi, [rsp+0x40]','add rsp, 0x20','pop rdi','ret')
 return dict(selectedInstructions=g.seen,wireBytes=1,returnedReference=0)


def derive(image,pins,profile):
 parent,ctx,owned,calls=derive_reference_parameter(image,pins,profile,VALUE,reader_method='ReadValue');base=image.pe.image_base;md=image.metadata
 w,=[w for w in derive_from_image(image).values() if w.wrapped_type==VALUE];scalar.need(LABEL,'referenceState',False,ctx.is_value_type(VALUE));scalar.need(LABEL,'stateHolder',(w.name,VALUE,16),ctx.field(w.name+'::__instance'))
 methods={md.string(m.name_index):m for m in md.methods_for(md.types[w.type_definition])};m=methods['Deserialize'];primitive.reader_abi(image,ctx,m,w);source=owned(image.method_pointer_va(m))
 # Initialization calls precede the normal header call; bind the unique already-proved helper.
 header=base+parent['parentHeader']['pointerRva'];at,encoded=parent['ownedMethods']['set___path__']['instructions'][7];barrier=base+at+5+int.from_bytes(bytes.fromhex(encoded)[1:],'little',signed=True)
 path=null_state_program(source['rows'],source['pointer'],header,barrier)
 getter=methods['GetValue'];scalar.owned_method_abi(image,ctx,getter.index,w.type_definition,(VALUE,18,True),[],LABEL+'.getter');at=image.method_pointer_va(getter);raw=image.pe.bytes_at_va(at,5);scalar.need(LABEL,'referenceGetter',bytes.fromhex('488b4110c3'),raw)
 registration=profile['childRegistration'];composition=profile['childComposition'];validate_eager_wrap_registration(image,registration,label=LABEL+'.childRegistration');validate_registered_formatter_composition(image,composition,label=LABEL+'.childComposition')
 scalar.need(LABEL,'childOriginal',VALUE,registration['originalType']);scalar.need(LABEL,'childWrapper',w.name,registration['wrapperType']);scalar.need(LABEL,'childComposition',[VALUE],[r['originalType'] for r in composition['registrations']])
 forward=owned(base+composition['methods'][1][3]);fcalls=calls(forward);forwarding=prove_zero_wrapper_forwarder(forward['rows'],dict(metadataInit=fcalls[0],classInit=fcalls[1]),source['pointer'],label=LABEL+'.childForward')
 return json.loads(json.dumps(dict(parent=parent,childForwarding=forwarding,childWrapper=w.name,childMethod=[m.index,w.name,'Deserialize',source['pointer']-base],childWindows=source['windows'],nullState=path,getter=[getter.index,w.name,'GetValue',at-base],getterBytes=raw.hex().upper(),evidenceBoundary=dict(direct='Typed four-member reference Param, selected complete reader and owned stores/factory/null output, two Int32 bindings and pooled path; generated CameraControlState FF branch consumes one byte and clears the original reference.',conditional='Initialized coherent compatible generated Param and camera-state wrapper/formatter routes, matching initialized StringPool, sufficient contiguous input, disjoint valid storage and ordinary helper/allocation/barrier ABI.',unresolved=['all positive camera-state constants','live provider default/cache/override selection','cold refill or malformed paths','runtime camera execution']))))
