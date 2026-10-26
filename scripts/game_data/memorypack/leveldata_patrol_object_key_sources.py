"""Actual Object-kind argument hash/comparison and complete interner hit.

The raw kind28 and byref bit determine the hash and selected equality path;
type record addresses and their first QWORD are not compared.  A coherent
initialized interner candidate must still be the actual registered object
instantiation.  Equal contents do not identify that pointer, populate the
method-key table or select an inflated List<Point> Count callback.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_patrol_count_selection_sources import need

SCHEMA='endfield.story-patrol-object-key-source.v1'


def hash_program(regions,entry):
 g=BytesPath(regions,entry)
 g.take('4053','4883ec20','480fbe410a','8b5908','4869d0');prime=int.from_bytes(g.read(4),'little',signed=True)
 need('positive-Object-key-hash-prime',0<prime<1<<31)
 g.take('0fb6410a','48c1eb1d','83e301','4803da')
 for value,opcode in ((18,'75'),(17,'74'),(21,'74'),(29,'74'),(15,'74')):
  g.take('3c'+bytes((value,)).hex());g.branch(opcode,value==18,1)
 g.take('488bc3','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,inputKind=28,byrefMaskDwordBit=29,prime=prime,
  hash='28 * actual positive prime + raw byref bit modulo 2^64',
  dataQwordRead=False,typeRecordAddressHashed=False,opaqueCalls=0,
  nonvolatileRbxRestored=True,entryRspRestored=True,normalReturn=True)


def compare_program(regions,entry,*,image_base):
 g=BytesPath(regions,entry)
 g.take('4883ec28','4c8bda','48895c2430');need('Object-comparator-image-origin',g.relative('488d15')==image_base)
 g.take('4c8bd1','66660f1f840000000000','410fb6430a','4138420a');g.branch('0f85',False)
 g.take('418b4308','418b4a08','c1e81d','c1e91d','83e001','83e101','3bc8');g.branch('0f85',False)
 g.take('410fbe420a','83c0f1','83f80f');g.branch('0f87',False)
 g.take('4898','8b8c82');table=image_base+int.from_bytes(g.read(4),'little',signed=True)
 g.take('4803ca','ffe1');slot=table+(28-15)*4
 need('owned-Object-kind28-compare-switch-word',all(slot+i in g.bytes for i in range(4)))
 raw=bytes(g.bytes[slot+i]for i in range(4));target=image_base+int.from_bytes(raw,'little',signed=True)
 need('owned-Object-kind28-compare-target',target in g.bytes);g.at=target
 g.take('33c0','488b5c2430','4883c428','c3')
 return dict(selectedBytes=g.seen,inputKinds=[28,28],sameRawByrefBitRequired=True,
  byrefMaskDwordBit=29,returnedEax=0,dataQwordReadOrCompared=False,
  typeRecordAddressCompared=False,ownedSwitchSlot=slot,ownedSwitchWordHex=raw.hex().upper(),
  ownedSwitchTarget=target,opaqueCalls=0,nonvolatileRbxRestored=True,entryRspRestored=True,normalReturn=True)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.enum_argument_interner_paths import hit_program
 from scripts.game_data.memorypack import pointer_param as pointer,leveldata_patrol_object_lookup_sources as lookup_owner
 _publication_gate(image,pins);base=image.pe.image_base;lookup=lookup_owner.derive(image,pins)
 selected=lookup['proof']['selectionSource']['proof']['selectedReferencePath']
 body=pointer.owned(image,selected['internerTarget']);hit=hit_program(body['regions'],body['pointer'])
 hashing=pointer.owned(image,hit['hashTarget']);comparison=pointer.owned(image,hit['compareTarget'])
 hashed=hash_program(hashing['regions'],hashing['pointer'])
 compared=compare_program(comparison['regions'],comparison['pointer'],image_base=base)
 need('independent-root-Object-kind28-key',bytes.fromhex(lookup['proof']['ownRootObject']['registeredRawTypeHex'])[10:12]==bytes((28,0))
  and lookup['classByvalMatchesRegisteredObjectKeyConditional']is True)
 need('actual-interner-comparison-with-unchanged-arguments',hit['inputCount']==1
  and hit['compareArguments']==dict(rcx='unchanged input buffer[0]',rdx='candidate instantiation arguments[0]')
  and hit['returnedCandidateInstantiationUnchanged']is True)
 def capture(b):return dict(sourceWindows=b['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in b['regions']])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-Object-argument-key-and-interner-source',nativeInputs=pins,
  proof=dict(ObjectLookupSource=lookup,interner=capture(body),selectedCountOneHit=hit,
   argumentHash=capture(hashing),selectedObjectHash=hashed,argumentCompare=capture(comparison),selectedObjectEquality=compared),
  ObjectKindAndByrefDetermineHashAndEquality=True,recordPointerOrDataEqualityRequired=False,
  countOneHitReturnsSameCandidateConditional=True,registeredCanonicalInstantiationIdentityProved=False,
  actualNominalPointCountCallbackProved=False,wholeConversionProved=False,runtimeSelectionObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Complete selected raw kind28 hash/equality/full frames and actual count-one interner caller/hash/compare/candidate-return source joined to independent Object lookup and byval copy.',
   conditional=__doc__,unresolved=['initialized interner population/canonical registered instantiation pointer',
    'method-key table and actual incoming List<Point> MethodInfo/receiver','actual Count callback and full conversion','runtime checkpoints and playback']))))
