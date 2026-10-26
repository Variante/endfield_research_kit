"""Conditional System.Object lookup, record cache and byval-key source.

Actual name comparisons, record-index geometry and constructor copies are
proved separately from live table/cache identity.  The selected warm name-table
slot must contain the independently selected root Object record, and any hit
must contain a class built from it.  Cold allocation and other child effects
must preserve the owned class and record.  These conditions do not observe
startup execution, interned pointer identity or List<Point> interface dispatch.
"""
import json

from scripts.game_data.memorypack.leveldata_patrol_count_selection_sources import need

SCHEMA='endfield.story-patrol-object-lookup-source.v1'


def object_record_join(*,definition,byval_index,record,registered_pointer,raw_type,argument):
 """Join actual metadata/byval data with the selected object registration."""
 need('bounded-root-object-definition',type(definition)is int and definition>=0
  and type(byval_index)is int and byval_index>=0 and len(record)>=88)
 need('same-root-Object-record-byval-index',int.from_bytes(record[8:12],'little',signed=True)==byval_index)
 need('actual-ordinary-Object-byval-key',len(raw_type)==16 and raw_type[10:12]==bytes((28,0))
  and int.from_bytes(raw_type[:8],'little')==definition)
 need('same-actual-registered-Object-key',type(registered_pointer)is int and registered_pointer>0
  and argument.get('type_pointer_va')==registered_pointer
  and bytes.fromhex(argument.get('raw_type_record_hex',''))==raw_type)
 return dict(typeName='System.Object',typeDefinition=definition,byvalTypeIndex=byval_index,
  registeredTypePointerVa=registered_pointer,registeredRawTypeHex=raw_type.hex().upper(),
  classByvalOffset=32,classByvalBytes=16,staticByvalContentsEqualSelectedKey=True,
  runtimeClassOrInternedPointerIdentityObserved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.enum_name_lookup_paths import (_owned_graph,lookup_program,find_program,
  record_class_program,insert_key_program)
 from scripts.game_data.il2cpp.enum_class_field_paths import constructor_fields,unique
 from scripts.game_data.il2cpp.enum_placeholder_type_copy import program as byval_program,_control
 from scripts.game_data.il2cpp.class_enum_fields_control import _no_register_write
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
 from scripts.game_data.il2cpp.owned_partition import checked_rows
 from scripts.game_data.memorypack import leveldata_patrol_count_selection_sources as selection,scalar_param_native as scalar
 _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
 selected=selection.derive(image,pins);publication=selected['proof']['publicationSlice']
 lookup,lookup_cfg=_owned_graph(image,publication['classLookupTarget'])
 request=lookup_program(lookup['regions'],lookup['pointer'],record_bytes=md.type_record_size,records=len(md.types))
 find,find_cfg=_owned_graph(image,request['findTarget'])
 matched=find_program(find['regions'],find['pointer'],namespace=b'System',name=b'Object')
 resolver,resolver_cfg=_owned_graph(image,request['recordClassTarget'])
 paths=[record_class_program(resolver['regions'],resolver['pointer'],mode=mode)for mode in ('minus-one','hit','cold')]
 constructor,constructor_cfg=_owned_graph(image,paths[2]['constructorTarget'])
 rows=[]
 for at,raw in constructor['regions']:rows+=checked_rows(decode_enum_underlying_instructions(image.mapper,raw,at),raw,SCHEMA)
 rows.sort(key=lambda row:int(row['va'],16))
 fields=constructor_fields(rows,constructor['regions'],constructor['pointer'])
 copy=byval_program(constructor['regions'],unique(constructor['regions'],bytes.fromhex('4863470883f8ff')))
 stores=_control(fields['completeCfg'],fields['prefix'],copy,constructor['pointer'])
 by={int(r['va'],16):i for i,r in enumerate(rows)}
 for register,key in (('rdi','recordOrigin'),('rbx','classOrigin')):
  _no_register_write(rows,by[fields['prefix'][key]]+1,by[copy['end']],register,calls_allowed=True)
 need('same-name-lookup-constructor-record-geometry',all(request[k]==fields['prefix'][k]
  for k in ('metadataHeaderCell','metadataBaseCell','headerOffsetField','recordBytes')))
 td=ctx.index.types['System.Object'];pointer=ctx.type_pointer(td.byval_type_index)
 scalar.ordinary(image,pointer,28,'storyPatrolObjectLookup.Object',reference=True)
 section=md.sections['typeDefinitions'];record=md.buf[section.offset+td.index*md.type_record_size:section.offset+(td.index+1)*md.type_record_size]
 argument,=selected['proof']['independentObjectRegistration']['classInstantiation']['arguments']
 nominal=object_record_join(definition=td.index,byval_index=td.byval_type_index,record=record,
  registered_pointer=pointer,raw_type=image.pe.bytes_at_va(pointer,16),argument=argument)
 need('root-Object-metadata-name-and-namespace',md.string(td.name_index)=='Object'and md.string(td.namespace_index)=='System'
  and int.from_bytes(record[:4],'little',signed=True)==td.name_index
  and int.from_bytes(record[4:8],'little',signed=True)==td.namespace_index and td.declaring_type_index<0)
 calls=[]
 for at,raw in lookup['regions']:
  offset=raw.find(bytes.fromhex('488bcbe8'))
  while offset>=0:
   site=at+offset+3;calls.append(dict(siteVa=site,targetVa=site+5+int.from_bytes(raw[offset+4:offset+8],'little',signed=True)))
   offset=raw.find(bytes.fromhex('488bcbe8'),offset+1)
 need('same-owned-two-name-key-insertions',len(calls)==2 and len({r['targetVa']for r in calls})==1)
 insertion,insertion_cfg=_owned_graph(image,calls[0]['targetVa']);key=insert_key_program(insertion['regions'],insertion['pointer'])
 need('same-actual-metadata-cells-in-key-insertion',all(key[k]==request[k]for k in ('metadataHeaderCell','metadataBaseCell')))
 def capture(body,graph):return dict(sourceWindows=body['windows'],sourceRegions=[[at,h.hex().upper()]for at,h in body['regions']],completeCfg=graph)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-Object-lookup-and-key-copy-source',nativeInputs=pins,
  proof=dict(selectionSource=selected,lookup=capture(lookup,lookup_cfg),selectedWarmLookup=request,
   find=capture(find,find_cfg),selectedMatchingSystemObjectSlot=matched,
   recordClass=capture(resolver,resolver_cfg),recordClassPaths=paths,
   classConstructor=capture(constructor,constructor_cfg),constructorFields=fields,
   byvalCopy=copy,allDirectByvalStores=stores,ownRootObject=nominal,ownRootObjectRecordHex=record.hex().upper(),
   actualInsertionCalls=calls,insertion=capture(insertion,insertion_cfg),nameKeyInsertion=key),
  matchingNameRecordIndexAndClassResultTransfersProved=True,classByvalMatchesRegisteredObjectKeyConditional=True,
  initializedNameTablePopulationProved=False,actualLookupResultIdentityObserved=False,
  initializedInternerIdentityProved=False,actualNominalPointCountCallbackProved=False,
  wholeConversionProved=False,runtimeSelectionObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Complete current name lookup/find/cache/constructor/insertion CFGs and frames, literal System/Object comparisons, selected metadata record index geometry, dominating unchanged registered byval16 copy and exact Object registration key.',
   conditional=__doc__,unresolved=['selected image/name-table population and coherent class cache','opaque allocation/helper aliases and actual startup execution',
    'initialized interner/method-key table pointer identity','actual List<Point>/ICollection Count receiver and callback','fresh list growth and full conversion/initializer','runtime checkpoints and playback']))))
