"""Exact nonfloating inline setter refresh before the selected field store."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def need(key,condition,detail=None):
 if not condition:raise ValueError('generatedInlineRefresh.'+key+':'+str(detail)[:700])

def program(regions,entry,*,field,mode,base_slot,cache_slot,barrier,cast,refresh):
 from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle,generated_member_sources as members
 need('finite-nonfloating-source',mode in('normalized-byte-return','int32-return','qword-return','reference-return'))
 need('exact-cache-domain',base_slot==16 and 16<cache_slot<128 and refresh in('empty','different'))
 g=BytesPath(regions,entry);g.take('4056','4883ec20');flag=g.relative('803d')+1;g.take('00')
 g.take({'normalized-byte-return':'0fb6f2','int32-return':'8bf2','qword-return':'488bf2','reference-return':'488bf2'}[mode],'48895c2430','488bd9');lifecycle._initialized(g)
 c=bytes((cache_slot,)).hex();g.take('48837b'+c+'00')
 def eq(equal):
  first=lifecycle._peek(g);long=first==b'\x0f';opcode=lifecycle._peek(g,2)[1]if long else first[0]
  need('owned-equality-branch',opcode&15 in(4,5)and(long and opcode>>4==8 or not long and opcode>>4==7))
  g.branch(('0f'if long else'')+format(opcode,'02x'),equal if opcode&15==4 else not equal,4 if long else 1)
 eq(refresh=='empty')
 if refresh=='different':g.take('488b4310','483943'+c);eq(False)
 first=g.relative('488b15');g.take('48897c2438','488b7b10','488bcf');g.call(cast)
 g.take('488943'+c,'488bcf');second=g.relative('488b15');g.call(cast);g.take('488d4b'+c);g.call(barrier)
 need('same-exact-refresh-class-cell',first==second)
 g.take('488b7c2438');g.jump('eb',1)if lifecycle._peek(g)==b'\xeb'else g.jump('e9')
 reference=mode=='reference-return';g.take('488b4b'+c if reference else'488b43'+c,'488b5c2430','4885c9'if reference else'4885c0');lifecycle._nonnull(g)
 prefix={'normalized-byte-return':'408870','int32-return':'8970','qword-return':'488970','reference-return':'488971'}[mode]
 g.take(members._displacement(prefix,field))
 if reference:
  g.take('4883c1'+bytes((field,)).hex()if field<128 else'4881c1'+field.to_bytes(4,'little').hex())
 g.take('4883c420','5e')
 if reference:need('same-field-barrier',g.relative('e9')==barrier)
 else:g.take('c3')
 return dict(selectedBytes=g.seen,initializedFlag=flag,refresh=refresh,baseSlot=base_slot,cacheSlot=cache_slot,fieldOffset=field,castClassCell=first,
  sameBaseReferenceCachedBeforeField=True,completeIncomingValueStoredUnchanged=True,fullFrameAndNonvolatilesRestored=True,
  normalReturnViaBarrier=reference,condition='Initialized metadata and compatible nonnull actual base; both actual exact compatible casts return that same base reference; disabled cache/field barriers and ordinary helper ABI. No runtime invocation or failed cast path is observed.')

def derive(image,body,*,original,field,mode,base_slot,cache_slot,barrier):
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.memorypack import generated_member_sources as members,pooled_string_list_sources as lists
 base=image.pe.image_base;calls={control_transfer(r)['target']for r in body['rows']if members.ec.raw(r)[:1]==b'\xe8'};candidates=[]
 for target in calls-{barrier}:
  try:
   programs=[]
   for refresh in('empty','different'):
    proof=program(body['regions'],body['pointer'],field=field,mode=mode,base_slot=base_slot,cache_slot=cache_slot,barrier=barrier,cast=target,refresh=refresh)
    sites={at for at,h in proof['selectedBytes']};usages=[]
    for row in body['rows']:
     if members.ec.va(row)in sites and members.ec.raw(row)[:3]==bytes.fromhex('488b15'):
      usage=derive_typed_usage_context(image,members.ec.va(row)-base,label='generatedInlineRefresh.class')
      need('actual-current-owned-class',(usage['tag'],usage['typeName'])==(1,original));usages.append(usage)
    need('both-actual-refresh-class-loads',len(usages)==2);programs.append(dict(path=refresh,program=proof,classUsages=usages))
   cast_body=members._body(image,target);predicates={control_transfer(r)['target']for r in cast_body['rows']if members.ec.raw(r)[:1]==b'\xe8'}
   need('one-actual-compatible-cast-predicate',len(predicates)==1)
   cast_program=lists.compatible_list_cast(cast_body['regions'],target,predicates.pop(),null=False)
   candidates.append(dict(programs=programs,baseSlot=base_slot,cacheSlot=cache_slot,typeName=original,sameBaseReferenceCachedBeforeField=True,
    cast=dict(targetRva=target-base,family=cast_body['family'],codeWindows=cast_body['windows'],program=cast_program),
    initializedCompatibleNonNullBaseRequired=True,emptyOrDifferentCacheAdmitted=True,predicateOutcomeObserved=False,barrierTargetRva=barrier-base))
  except(ValueError,KeyError,IndexError):pass
 need('one-complete-inline-setter-refresh',len(candidates)==1,len(candidates));return candidates[0]
