"""Exact guarded registration for an independently closed reference carrier.

This replays the existing nonnull constructor/key/static-check program. Its distinct
nominal gate proves the actual constructed reference Type record and reciprocal
generic definition/arguments, then binds that exact key to the adapter's first
class argument. Ordinary CLASS registration keeps its separate strict guard.
No constructed heap layout, formatter invocation or live selection follows.
"""
from scripts.game_data.il2cpp.formatter_checked_value_registration import program as _program

PROFILE='direct-constructed-reference-adapter-nonnull-skip-static-checks.v1'
LABEL='constructedGuardedReferenceRegistration'


def need(check,expected,actual):
 if type(expected)is not type(actual)or expected!=actual:
  raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:260]+' actual='+str(actual)[:260])


def require_carrier(original,raw,carrier):
 need('literal-complete-key-record',True,isinstance(raw,bytes)and len(raw)==16)
 need('actual-constructed-reference-key',bytes((21,0)),raw[10:12])
 need('own-current-closed-reference-name',original,carrier.get('type'))
 need('reference-representation-only',8,carrier.get('bytes'))
 need('same-complete-selected-key-record',raw.hex().upper(),carrier.get('declaredTypeRecordHex'))
 definition=bytes.fromhex(carrier.get('definitionTypeRecordHex',''))
 need('own-reference-definition-record',True,len(definition)==16 and definition[10:12]==bytes((18,0))
  and type(carrier.get('definitionTypeIndex'))is int
  and int.from_bytes(definition[:8],'little')==carrier['definitionTypeIndex'])
 need('fresh-closed-arguments',True,isinstance(carrier.get('argumentTypes'),list)
  and bool(carrier['argumentTypes'])and all(type(name)is str and name for name in carrier['argumentTypes']))


def _derive(image,original,wrapper,start,helpers):
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.formatter_direct_registration import _derive_program
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
 base=image.pe.image_base;context=NativeReferenceContext(image)
 source=_program([(base+start,image.pe.bytes_at_va(base+start,256))],base+start)
 usage=derive_typed_usage_context(image,source['key']['instruction']-base,label=LABEL)
 need('own-actual-Type-key',(2,original),(usage['tag'],usage['typeName']))
 pointer=context.type_pointer(usage['typeIndex']);raw=image.pe.bytes_at_va(pointer,16)
 carrier=closed_generic_reference_pointer_extent(context,pointer);require_carrier(original,raw,carrier)
 result=_derive_program(image,original,wrapper,start,helpers,source,profile=PROFILE,condition=__doc__)
 need('same-actual-key-type-pointer',pointer,context.type_pointer(result['key']['typeIndex']))
 result['constructedReferenceKey']=carrier
 result['constructedHeapLayoutAdmitted']=False
 return result


def derive(image,original,wrapper,candidates,helpers):
 found={};diagnostics=[]
 for candidate in candidates:
  if not candidate['rawHex'].lower().startswith('488b1d'):continue
  start=candidate['siteRva']-48
  if start<0:continue
  try:
   row=_derive(image,original,wrapper,start,helpers)
   need('exact-selected-key-site',candidate['siteRva'],row['key']['instructionRva']);found[start]=row
  except(ValueError,KeyError,IndexError,TypeError)as error:diagnostics.append(str(error)[:1100])
 if len(found)!=1:raise ValueError(LABEL+'.unique-source:matches='+str(len(found))+' diagnostics='+str(diagnostics[:4]))
 return next(iter(found.values()))


def validate(image,flow,*,label):
 need('explicit-constructed-key-reference-profile',PROFILE,flow.get('profile'))
 actual=_derive(image,flow['originalType'],flow['wrapperType'],flow['window']['startRva'],flow['helperMethods'])
 need('exact-current-constructed-key-declaration',actual,flow)
