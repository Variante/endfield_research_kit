"""Patrol's reference normalization and Object-class publication source.

The selected reference-kind path replaces one argument with the initialized
Object-class cell plus its by-value-type offset.  The actual startup slice
passes two literal name strings and an incoming image to the class lookup,
then publishes its unchanged result to that same cell.  The cell can be BSS;
file bytes are not a live class value.  Lookup/cache results, coherent class
and interning state, method-table population and actual interface dispatch
remain independent conditions.  An object registration is never a Point
registration or an observed inflated List callback.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-count-selection-source.v1'
LABEL='storyPatrolCountSelection'


def need(check,condition):
 if not condition:raise ValueError(LABEL+'.'+check)


def reference_program(regions,entry,*,image_base):
 """Complete count-one, nonbyref CLASS18 selected normal return."""
 g=BytesPath(regions,entry)
 g.take('4055','4156','4157','4883ec20','488d6c2420','48895d20','48897528','488bf1',
  '48897d30','4885c9');g.branch('75',True,1)
 g.take('8b01','48c1e003','488d480f','483bc8');g.branch('77',True,1)
 g.take('4883e1f0','488bc1');probe=g.relative('e8')
 g.take('482be1','33ff','4c8d742420','393e');g.branch('0f86',False)
 need('same-image-origin',g.relative('4c8d3d')==image_base)
 g.take('0f1f840000000000');iteration=g.at
 g.take('488b4608','488d0cfd00000000','488b0c01','4885c9');g.branch('74',False,1)
 for kind in (14,29):
  g.take('80790a'+bytes((kind,)).hex());g.branch('0f84',False)
 g.take('80790a12');g.branch('0f84',True)
 cell=g.relative('488b1d');g.take('4883c320','488d04fd00000000','ffc7','4a891c30','3b3e')
 need('same-owned-counted-backedge',g.relative('0f82')==iteration)
 g.take('8b16','498bce');interner=g.relative('e8')
 g.take('488b5d20','488b7528','488b7d30','488be5','415f','415e','5d','c3')
 return dict(selectedBytes=g.seen,inputCount=1,inputKind=18,inputNonnullRequired=True,
  inputByrefBitClearRequired=True,objectClassCell=cell,objectClassNonnullAndInitializedRequired=True,
  objectClassByvalTypeOffset=32,outputBufferElement='actual Object-class cell value +32',
  bufferAlignment=16,bufferBytesForCount1=16,probeTarget=probe,internerTarget=interner,
  internerArguments=dict(rcx='owned buffer',edx='unchanged incoming count1'),
  returnedInternerResultUnchanged=True,entryRspRestored=True,normalReturn=True,
  nonvolatilesRestored=['rbx','rbp','rsi','rdi','r14','r15'],
  objectClassIdentityProved=False,canonicalInternerIdentityProved=False,nominalPointCallbackSelected=False)


def publication_program(regions,entry,*,object_cell):
 """An owned startup slice, without claiming entry reachability or execution."""
 g=BytesPath(regions,entry);g.take('488b0b');image_cell=g.relative('48890d')
 g.take('488b00');other_image_cell=g.relative('488905')
 name=g.relative('4c8d05');namespace=g.relative('488d15');lookup=g.relative('e8')
 need('same-selected-Object-cell-writer',g.relative('488905')==object_cell)
 need('distinct-image-and-class-storage',len({image_cell,other_image_cell,object_cell})==3)
 return dict(selectedBytes=g.seen,start=entry,end=g.at,imageCell=image_cell,
  otherImageCell=other_image_cell,classCell=object_cell,nameAddress=name,namespaceAddress=namespace,
  classLookupTarget=lookup,lookupArguments=dict(rcx='unchanged first QWORD of incoming RBX',
   rdx='actual namespace string',r8='actual name string'),
  incomingRbxMustBeValidSelectedImageHolder=True,lookupNormalAbiRequired=True,
  returnedRaxPublishedUnchanged=True,completeStartupControlProved=False,publicationExecutionObserved=False)


def count_program(regions,entry,*,size_offset):
 need('bounded-operational-size-displacement',type(size_offset)is int and 16<=size_offset<128)
 g=BytesPath(regions,entry);g.take('8b41'+bytes((size_offset,)).hex(),'c3')
 return dict(selectedBytes=g.seen,receiver='incoming RCX',loadBytes=4,receiverOffset=size_offset,
  returnedEax='unchanged actual receiver DWORD',normalReturn=True,opaqueCalls=0,
  entryRspRestored=True,namedFieldLayoutClaimed=False,actualNominalCallbackSelected=False)


def derive(image,pins):
 from bisect import bisect_right
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp import enum_nominal_callback_sources as profile_owner
 from scripts.game_data.il2cpp.enum_primitive_normalizer_paths import null_program
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.native_cell_references import selected_qword_reference_candidates
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 profile=json.loads(profile_owner.CONTRACT_PATH.read_bytes());profile_owner.validate_profile(profile,pins)
 source=pointer.owned(image,base+profile['sourceEntries']['primitiveEntryRva'])
 normal=reference_program(source['regions'],source['pointer'],image_base=base)
 null=null_program(source['regions'],source['pointer']);cell=normal['objectClassCell']
 candidates=selected_qword_reference_candidates(image.pe,[cell-base])
 stores=[r for r in candidates if r['kind']in ('store','immediateStore')]
 need('one-actual-candidate-writer',len(stores)==1 and stores[0]['kind']=='store')
 candidate=stores[0];site=candidate['siteRva'];starts=sorted(image.unwind_index.entries)
 i=bisect_right(starts,site)-1
 need('owned-writer-instruction',i>=0 and starts[i]<=site<image.unwind_index.entries[starts[i]][1])
 writer=pointer.owned(image,base+image.unwind_index.resolve(starts[i]))
 need('bounded-owned-writer',sum(len(raw)for _,raw in writer['regions'])<=65536)
 publication=publication_program(writer['regions'],base+site-39,object_cell=cell)
 need('literal-System-Object-name-request',image.pe.bytes_at_va(publication['namespaceAddress'],7)==b'System\0'
  and image.pe.bytes_at_va(publication['nameAddress'],7)==b'Object\0')
 object_type=ctx.index.types['System.Object']
 need('own-ordinary-root-System-Object',object_type.generic_container_index<0 and object_type.parent_index<0
  and not list(md.fields_for(object_type)))
 owner=ctx.index.types['System.Collections.Generic.List`1']
 getter,=[m for m in md.methods_for(owner)if md.string(m.name_index)=='get_Count'and not m.parameter_count]
 scalar.owned_method_abi(image,ctx,getter.index,owner.index,('int',8,False),[],LABEL+'.Count')
 need('own-instance-Count-definition',not getter.flags&16)
 observed=GenericEntries(image).observe(getter.index,['object'],[])
 need('one-exact-object-registration',len(observed)==1 and observed[0]['pointer'])
 registered=observed[0];target=registered['pointer'];raw=image.pe.bytes_at_va(target,4)
 need('actual-Count-operational-leaf',raw[:2]==bytes.fromhex('8b41')and raw[3:]==b'\xc3')
 leaf=pointer.leaf(image,target,['8B41'+raw[2:3].hex().upper(),'C3'])
 count=count_program([(target,raw)],target,size_offset=raw[2])
 try:raw_cell=image.pe.bytes_at_va(cell,8)
 except ValueError as error:
  need('explicit-unbacked-cell-condition','raw-backed bytes actual=unbacked'in str(error))
  initial=dict(rawBacked=False,liveValueObserved=False)
 else:initial=dict(rawBacked=True,rawHex=raw_cell.hex().upper(),liveValueObserved=False)
 def captured(body):return dict(sourceWindows=body['windows'],sourceRegions=[[at,h.hex().upper()]for at,h in body['regions']])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-reference-normalization-source',nativeInputs=pins,
  proof=dict(normalizer=captured(source),selectedReferencePath=normal,nullInstantiationPath=null,
   actualCellInitialObservation=initial,actualWriterCandidate=candidate,publicationOwner=captured(writer),publicationSlice=publication,
   literalNames=dict(namespace='System',name='Object'),ownRootObjectTypeDefinition=object_type.index,
   countMethodDefinition=getter.index,independentObjectRegistration=registered,countLeaf=leaf,countProgram=count),
  selectedReferenceNormalizerSourceProved=True,unchangedLookupResultPublicationProved=True,
  actualObjectClassIdentityProved=False,actualNominalPointCountCallbackProved=False,actualListCountMeaningProved=False,
  wholeConversionProved=False,runtimeSelectionObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Complete selected CLASS18/count1 normalization, exact Object-cell writer and literal System/Object request, independent List<object>.Count registration and its exact DWORD load leaf.',
   conditional=__doc__,unresolved=['selected image and name lookup/cache class identity','initialized interner and method-key table pointer identity',
    'actual List<Point>/ICollection receiver MethodInfo and Count callback','fresh-empty-list growth and complete Convert/Init','runtime checkpoint and playback']))))
