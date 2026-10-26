"""Literal selected context-flag identity leaf from an actual caller target.

This profile declares an exact20-byte reachable source span, not a physical
function extent. The selected byte predicate returns incoming RCX unchanged,
with no calls or writes. No meaning, initialization or live value is assigned
to that flag; its cold tail is retained but never admitted.
"""
import hashlib
import json
from .formatter_value_paths import BytesPath

SCHEMA='endfield.selected-context-identity-source.v1'


def need(check,condition):
 if not condition:raise ValueError('readyContextSource.'+check)


def program(regions,entry):
 g=BytesPath(regions,entry);g.take('f6813801000001');cold=g.relative('74',1)
 need('literal-adjacent-cold-tail',cold==entry+14)
 g.take('488bc1');ret=g.relative('eb',1);need('literal-source-span-return',ret==entry+19)
 cold_path=BytesPath(regions,cold);cold_target=cold_path.relative('e9')
 need('cold-tail-does-not-enter-selected-return',cold_target!=ret)
 g.at=ret;g.take('c3')
 return dict(selectedBytes=g.seen,entry=entry,flagByteOffset=312,flagMask=1,selectedFlagBitSetRequired=True,
  coldInstructionVa=cold,coldTargetVa=cold_target,normalReturnVa=ret,returnsIncomingRcxUnchanged=True,
  nonframeMemoryWrites=0,frameWrites=0,opaqueCalls=0,entryRspAndNonvolatilesUnchanged=True,
  normalReturn=True,coldTailEffectsProved=False,flagMeaningOrLiveValueProved=False)


def derive(image,pins,*,entry):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 _publication_gate(image,pins);base=image.pe.image_base
 need('actual-positive-entry',type(entry)is int and entry>base)
 raw=image.pe.bytes_at_va(entry,20);p=program([(entry,raw)],entry)
 result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-selected-context-identity-source',nativeInputs=pins,
  actualEntryRva=entry-base,proof=dict(imageBase=base,sourceWindows=[dict(startRva=entry-base,endRva=entry-base+20,
   sha256=hashlib.sha256(raw).hexdigest().upper())],sourceRegions=[[entry,raw.hex()]],program=p),
  selectedIdentityAndNoNonframeEffectsProved=True,physicalFunctionExtentProved=False,
  coldEffectsProved=False,runtimeSelectionObserved=False,runtimeInvocationObserved=False)))
 validate(result,pins);_publication_gate(image,pins);return result


def validate(source,pins):
 need('same-source-envelope',source.get('schema')==SCHEMA and source.get('nativeInputs')==pins and
  source.get('status')=='validated-conditional-selected-context-identity-source'and
  source.get('selectedIdentityAndNoNonframeEffectsProved')is True and all(source.get(k)is False for k in
   ('physicalFunctionExtentProved','coldEffectsProved','runtimeSelectionObserved','runtimeInvocationObserved')))
 p=source['proof'];base=p['imageBase'];a=base+source['actualEntryRva'];regions=p['sourceRegions'];windows=p['sourceWindows']
 need('actual-exact-declared-span',len(regions)==len(windows)==1 and regions[0][0]==a)
 raw=bytes.fromhex(regions[0][1]);need('same-source-span-window',len(raw)==20 and windows==[dict(startRva=a-base,endRva=a-base+20,
  sha256=hashlib.sha256(raw).hexdigest().upper())])
 need('complete-selected-identity-replay',json.loads(json.dumps(program([(a,raw)],a)))==p['program'])
 return dict(actualEntryRva=source['actualEntryRva'],selectedIdentityAndNoNonframeEffectsProved=True,
  physicalFunctionExtentProved=False,runtimeSelectionObserved=False)
