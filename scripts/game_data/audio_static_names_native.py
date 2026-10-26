"""Fresh selected Audio expression enums and literal RTPC metadata identities.

The old Audio callsite catalog remains independently gated. These declarations
name static values only, never setter execution, live values or DSP behavior.
"""
import json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp import protocol,metadata_default_sources as programs

SCHEMA='endfield.audio-static-names-native.v1'
CONTRACT_PATH=CONTRACTS_DIR/'audio_static_names_native.json'
LABEL='audioStaticNames'

def declarations(path=CONTRACT_PATH):
 fact=json.loads(Path(path).read_bytes())
 if(fact['schema'],fact['status'],fact['evidenceBoundary'])!=(SCHEMA,'exact-current-build','exact')or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat'}:raise ValueError(LABEL+'.contract:schema')
 return fact


def export_record(image,name):
 pe=image.pe;base=pe.image_base;opt=struct.unpack_from('<I',pe.buf,60)[0]+24;rva,size=struct.unpack_from('<II',pe.buf,opt+112);directory=pe.bytes_at_va(base+rva,40);count,functions,names,ordinals=struct.unpack_from('<IIII',directory,24);rows=[]
 for i in range(count):
  nr=struct.unpack('<I',pe.bytes_at_va(base+names+i*4,4))[0]
  if pe.bytes_at_va(base+nr,len(name)+1)!=name.encode()+b'\0':continue
  ordinal=struct.unpack('<H',pe.bytes_at_va(base+ordinals+i*2,2))[0];entry=struct.unpack('<I',pe.bytes_at_va(base+functions+ordinal*4,4))[0];raw=pe.bytes_at_va(base+entry,5)
  if rva<=entry<rva+size or raw[0]!=233:raise ValueError(LABEL+'.native:original-export-tail')
  rows.append(dict(name=name,entryRva=entry,raw=raw.hex(),targetRva=entry+5+int.from_bytes(raw[1:],'little',signed=True)))
 if len(rows)!=1:raise ValueError(LABEL+'.native:unique-selected-export')
 return rows[0]


def derive_names(image,fact):
 ctx=NativeReferenceContext(image);md=image.metadata;defaults=protocol.field_defaults(md);section=md.sections['fieldAndParameterDefaultValueData']
 def owner(name):
  rows=image.named_type_definitions.get(name,[])
  if len(rows)!=1:raise ValueError(LABEL+'.native:unique-owner:'+name)
  return rows[0]
 def field(f,kind):
  default_type,index=defaults[f.index];ctx.require_ordinary_kind(default_type,kind);at=section.offset+index
  if not 0<=index<section.size:raise ValueError(LABEL+'.native:default-range')
  if kind==9:
   if at+5>section.offset+section.size or md.buf[at]!=240:raise ValueError(LABEL+'.native:reviewed-F0-UInt32-required')
   value=struct.unpack_from('<I',md.buf,at+1)[0];size=5
  else:
   if md.buf[at]>=192:raise ValueError(LABEL+'.native:reviewed-small-Int32-required')
   value,size=protocol.read_compressed_int32(md.buf,at)
   if at+size>section.offset+section.size:raise ValueError(LABEL+'.native:default-range')
  attributes=ctx.field_attributes(f.type_index)
  if attributes&32848!=32848:raise ValueError(LABEL+'.native:literal-static-default-attributes')
  return dict(name=md.string(f.name_index),fieldIndex=f.index,token=f.token,typeIndex=f.type_index,typeName=ctx.type_name(f.type_index),attributes=attributes,defaultTypeIndex=default_type,defaultType=ctx.type_name(default_type),dataIndex=index,raw=md.buf[at:at+size].hex(),value=value)
 enums=[]
 for row in fact['enums']:
  name=row['typeName'];td=owner(name);fields=list(md.fields_for(td));backing=[f for f in fields if md.string(f.name_index)=='value__']
  if ctx.parent(name)!='System.Enum'or len(backing)!=1:raise ValueError(LABEL+'.native:enum-backing')
  ctx.require_ordinary_kind(backing[0].type_index,8)
  for f in fields:
   if f!=backing[0]:ctx.require_ordinary_kind(f.type_index,17)
  members=[field(f,8)for f in fields if f!=backing[0]]
  if any(ctx.type_name(f.type_index)!=name for f in fields if f!=backing[0]):raise ValueError(LABEL+'.native:enum-owned-member-type')
  enums.append(dict(role=row['role'],typeName=name,typeIndex=td.index,token=td.token,backingType='int',members=members))
 rtpc=fact['rtpc'];td=owner(rtpc['typeName']);wanted={r['name']for r in rtpc['fields']};fields=[f for f in md.fields_for(td)if md.string(f.name_index)in wanted]
 if len(fields)!=len(wanted)or len(wanted)!=6:raise ValueError(LABEL+'.native:six-selected-RTPC-fields')
 for f in fields:ctx.require_ordinary_kind(f.type_index,9)
 return enums,dict(typeName=rtpc['typeName'],typeIndex=td.index,token=td.token,fields=[field(f,9)for f in fields])


def prove_sources(image,fact):
 base=image.pe.image_base;groups={}
 if set(fact['sources'])!={'export','literal','data','conversion','compressed'}:raise ValueError(LABEL+'.contract:source-set')
 for role,g in fact['sources'].items():
  if g.get('owned'):
   actual=[p['runtimeTriple'][:2]for p in image.unwind_index.family(g['entryRva'])['ranges']]
   if actual!=[[w['startRva'],w['endRva']]for w in g['windows']]:raise ValueError(LABEL+'.native:complete-owned-window-set:'+role)
  elif g['entryRva']in image.unwind_index.entries:raise ValueError(LABEL+'.native:selected-leaf-gained-pdata:'+role)
  image.check_windows(g['windows'],label=LABEL);groups[role]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in g['windows']]
 export=export_record(image,fact['export']['name'])
 if export!=fact['export']or export['targetRva']!=fact['sources']['export']['entryRva']:raise ValueError(LABEL+'.native:export-source-join')
 proof={role:getattr(programs,{'export':'literal_export','literal':'literal_forward','data':'default_data_pointer','conversion':'unsigned_conversion','compressed':'compressed_uint_f0'}[role])(groups[role],base+g['entryRva'],**(dict(image_base=base)if role=='conversion'else{}))for role,g in fact['sources'].items()}
 entries={k:base+g['entryRva']for k,g in fact['sources'].items()}
 if(proof['export']['literal'],proof['literal']['data'],proof['literal']['convert'],proof['conversion']['reader'])!=(entries['literal'],entries['data'],entries['conversion'],entries['compressed']):raise ValueError(LABEL+'.native:current-default-source-composition')
 offset=proof['data']['sectionOffsetField']
 if struct.unpack_from('<I',image.metadata.buf,offset)[0]!=image.metadata.sections['fieldAndParameterDefaultValueData'].offset:raise ValueError(LABEL+'.native:default-data-section-header-join')
 return proof


def validate(*,gameassembly=None,metadata=None,contract_path=CONTRACT_PATH):
 try:
  raw=Path(contract_path).read_bytes();fact=declarations(contract_path)
  if gameassembly is None or metadata is None:return dict(status='missing',gateVerified=False,detail='Audio static names require the explicit selected native pair')
  pins=fact['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
  if gate.status!='validated':return dict(status=gate.status,gateVerified=True,detail=gate.detail,metadataSha256=gate.metadata_sha256,gameAssemblySha256=gate.gameassembly_sha256)
  if {r['role']for r in fact['enums']}!={'expressionTypes','operatorTypes'}or len(fact['enums'])!=2:raise ValueError(LABEL+'.contract:enum-role-set')
  image=open_native_image(gate.gameassembly,gate.metadata);proof=prove_sources(image,fact);enums,rtpc=derive_names(image,fact)
  if enums!=fact['enums']or rtpc!=fact['rtpc']:raise ValueError(LABEL+'.native:current-declaration-value-join')
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,gateVerified=True,detail=after.detail,metadataSha256=after.metadata_sha256,gameAssemblySha256=after.gameassembly_sha256)
  if raw!=Path(contract_path).read_bytes():raise ValueError(LABEL+'.contract:changed-during-validation')
  return dict(status='validated',gateVerified=True,nativeInputs=pins,metadataSha256=pins['global-metadata.dat'].lower(),gameAssemblySha256=pins['GameAssembly.dll'].lower(),enums={r['role']:{f['value']:f['name']for f in r['members']}for r in enums},rtpcFields=rtpc['fields'],evidenceBoundary='exact',sourceConditions=[p['condition']for p in proof.values()])
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)
