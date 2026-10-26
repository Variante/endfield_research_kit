"""Exact InheritBuff pooled-string list parent and bounded owned loop.

The existing nominal STRING list and BeyondStringFormatter owners are rederived
on the supplied image. The finite parent join authenticates its actual RDX
MethodSpec/E8 and named member; the uniform source owner still proves enclosing
arguments, setter/frame and return. No reference stride supplies a wire width,
no closed List<string> registration is invented, and runtime provider/callback
choice remains conditional. Growth/refill and whole Skill authority stay closed.
"""
import copy
import json

from scripts.game_data.memorypack import skill_pooled_string_list_sources as strings
from scripts.game_data.memorypack import reference_list_induction_sources as induction

SCHEMA='endfield.skill-inherit-buff-string-list-sources.v1'
CAPABILITY='inherit-buff-string-list'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_InheritBuffAction_DataForMemoryPack'
TYPE='Beyond.Gameplay.Core.InheritBuffAction+Data'
FIELD='inheritSkillIdList'
MEMBER=7
LIMIT=10000


def need(check,condition):
 if not condition:raise ValueError('skillInheritBuffStringList.'+check)


def same(left,right):
 encode=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
 return encode(left)==encode(right)


def parent_request(parent):
 """Only select the declared current member; fresh native checks are separate."""
 need('finite-parent-owner',parent.get('schema')=='endfield.skill-timeline-inherit-buff-native-contract.v1'
  and parent.get('status')=='exact-current-build'and parent.get('dispatcher',{}).get('wrapperName')==WRAPPER)
 reads=[r for r in parent.get('orderedSourceReads',[])if r.get('memberIndex')==MEMBER]
 contexts=[r for r in parent.get('nestedContexts',[])if r.get('memberIndex')==MEMBER]
 need('one-exact-member-and-context',len(reads)==len(contexts)==1)
 read=reads[0];context=contexts[0]
 need('named-string-list-source',read.get('fieldName')==FIELD and read.get('readKind',read.get('kind'))=='string-list'
  and type(read.get('memberIndex'))is int and type(context.get('memberIndex'))is int
  and context.get('typeName')=='System.Collections.Generic.List`1'and type(context.get('typeKind'))is int and context['typeKind']==21)
 at=read.get('sourceCallsiteRva');target=read.get('sourceTargetRva');raw=bytes.fromhex(read.get('sourceCallHex',''))
 load=bytes.fromhex(context.get('instructionHex',''));usage_at=context.get('instructionRva')
 need('actual-RDX-before-exact-E8',type(at)is int and at>=0 and type(target)is int and target>0
  and len(raw)==5 and raw[0]==232 and at+5+int.from_bytes(raw[1:],'little',signed=True)==target
  and type(usage_at)is int and 0<=usage_at<at and len(load)==7 and load[:3]==bytes.fromhex('488b15'))
 return dict(memberIndex=MEMBER,fieldName=FIELD,context=copy.deepcopy(context),
  sourceInstruction=[at,read['sourceCallHex']],sourceTargetRva=target)


def compose(component,parent,pins):
 """Pure exact projection; only derive performs selected-image admission."""
 need('same-owned-string-component',component.get('schema')=='endfield.skill-pooled-string-list-sources.v1'
  and component.get('status')=='validated-conditional-components'and component.get('nativeInputs')==pins
  and set(component.get('capabilities',{}))=={strings.CAPABILITY}
  and component.get('requiredExternalCapabilities')==['byte-payload'])
 proof=component.get('proof',{});listing=proof.get('listComponent',{});callback=proof.get('stringCallback',{})
 expected=strings.capability(listing,callback);cap=component['capabilities'][strings.CAPABILITY]
 need('complete-string-shape-and-bounded-domain',same(cap,expected)and cap.get('countLimit')==LIMIT
  and type(cap.get('countLimit'))is int and cap.get('positiveCountsAdmitted')is True)
 witness=listing['witnessComponent'];fresh=induction._certificate(witness,count_limit=LIMIT)
 need('same-complete-loop-induction',same(fresh['induction'],listing.get('induction'))
  and{p['newList']for p in fresh['induction']['pathProofs']}=={False,True})
 need('actual-parent-closed-list-reader-join',same(parent.get('typedRequest'),witness.get('typedRequest'))
  and parent.get('closedListType')==strings.LIST and parent.get('elementType')=='string'
  and parent.get('elementTypeKind')==14 and type(parent.get('elementTypeKind'))is int
  and parent.get('sourceTargetRva')==witness.get('callTargetRva')==cap['packableReaderTargetRva']
  and witness.get('referenceSource',{}).get('packableContext',{}).get('packableDefinition')==cap['packableReaderMethodDefinition']
  and parent.get('wrapperName')==WRAPPER and parent.get('wrappedType')==TYPE and parent.get('fieldName')==FIELD
  and type(parent.get('memberIndex'))is int and parent['memberIndex']==MEMBER
  and parent.get('parentFieldAdmitted')is False)
 return dict(cap,sourceParentScope=dict(wrapperName=WRAPPER,wrappedType=TYPE,memberIndex=MEMBER,fieldName=FIELD),
  parentRequestBound=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,*,parent):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 _publication_gate(image,pins);selected=parent_request(parent);base=image.pe.image_base
 need('same-parent-selected-inputs',parent.get('nativeInputs')==pins)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
 need('fresh-parent-nominal-member',wrapper.wrapped_type==TYPE and len(wrapper.members)>MEMBER
  and(wrapper.members[MEMBER].name,wrapper.members[MEMBER].declared_type)==(FIELD,strings.LIST))
 for row in parent['methods']:image.validate_method_row(row,label='skillInheritBuffStringList.parent')
 image.check_windows(parent['codeWindows'],label='skillInheritBuffStringList.parent')
 image.check_instruction_windows([selected['sourceInstruction']],label='skillInheritBuffStringList.actualE8')
 context=selected['context'];usage=derive_typed_usage_context(image,context['instructionRva'],label='skillInheritBuffStringList.actualUsage')
 need('fresh-exact-parent-MethodSpec',usage['instructionHex']==context['instructionHex']
  and same(usage['methodSpec'],context['methodSpec'])and usage['methodArguments']==[strings.LIST])
 owner=NativeReferenceContext(image);field=owner.field(TYPE+'::'+FIELD)
 need('fresh-owned-parent-field',field[:2]==(TYPE,strings.LIST))
 component=strings.derive(image,pins,typed_request=usage,call_target=base+selected['sourceTargetRva'],count_limit=LIMIT)
 listing=component['proof']['listComponent'];carrier=listing['witnessComponent']['closedCarrier'];element,=carrier['classArguments']
 join=dict(wrapperName=WRAPPER,wrappedType=TYPE,memberIndex=MEMBER,fieldName=FIELD,originalField=field,
  typedRequest=usage,sourceInstruction=selected['sourceInstruction'],sourceTargetRva=selected['sourceTargetRva'],
  closedListType=carrier['name'],elementType=element['name'],elementTypeKind=bytes.fromhex(element['rawHex'])[10],parentFieldAdmitted=False)
 cap=compose(component,join,pins);_publication_gate(image,pins)
 return dict(schema=SCHEMA,status='validated-conditional-inherit-buff-string-list',nativeInputs=dict(pins),
  capabilities={CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],
  proof=dict(parent=join,stringList=component),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Actual current InheritBuff member7 nominal field and RDX MethodSpec/E8, own STRING reference-list zero/one/two/three programs with bounded10000 induction and exact pooled callback/registration/backend source.',
   conditional=__doc__,structuralOnly='Stored pooled Skill identifiers; no lookup/runtime inheritance meaning inferred.',
   unresolved=['enclosing argument/setter/frame/return owned by uniform source','runtime provider/callback selection','growth/refill/errors','whole Skill/physical EOF']))
