"""Actual SendGlobal callers with ready contexts and an empty Lua-key set."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_radio_dispatch_programs as dispatch


def need(check,condition):
 if not condition:raise ValueError('patrolRadioSend.'+check)


def play(regions,entry):
 g=BytesPath(regions,entry);calls=[];uses=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use(role,prefix):
  at=g.at;cell=g.relative(prefix);uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
 g.take('48895c2410','894c2408','56','57','4156','4881ecb0000000','498bf8','488bf2','8bd9','4983783800');g.branch('75',True,1)
 g.take('48c78424e000000000000000','0f57c0','33c0','0f11442428','0f11442438','0f11442448','4889442458')
 singleton=use('singleton','488b0d');target=call('singleton')
 g.take('4885c0');g.branch('0f84',False)
 g.take('4c8b7018','0f1006','0f11442428','0f104e10','0f114c2438','0f104620','0f11442448','f20f104e30','f20f114c2458','488d4c2428');call('barrier')
 g.take('4d85f6');g.branch('0f84',False)
 macro=dispatch.play_dispatch_call(regions,g.at);g.seen.extend(macro['selectedBytes']);g.at=macro['nextInstructionVa']
 need('same-singleton-site',use('singleton','488b0d')==singleton);need('same-singleton-target',call('singleton')==target)
 g.take('4885c0');g.branch('0f84',False)
 g.take('488b4820','4885c9');g.branch('0f84',False)
 use('containsLuaKey','4c8b05');g.take('8bd3');call('containsLuaKey')
 g.take('84c0');g.branch('0f84',True)
 g.take('488b9c24d8000000','4881c4b0000000','415e','5f','5e','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=uses,dispatchMacro=macro,keyBytes=4,payloadBytes=56,
  payloadInput='same incoming RDX address',payloadLocalRsp=[40,96],copiedSlices=[[0,16],[16,16],[32,16],[48,8]],
  sameWholePayloadIncludingPaddingTransferred=True,globalDispatcherFieldOffset=24,luaKeySetFieldOffset=32,
  selectedMethodContextAlreadyReadyRequired=True,selectedLuaContainsResult=False,
  luaDispatchRequested=False,entryRspRestored=True,allNonvolatilesRestored=True,callbackEffectsOrPlaybackProved=False)


def stop(regions,entry,*,found):
 need('literal-dispatch-result',type(found)is bool)
 g=BytesPath(regions,entry);calls=[];uses=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use(role,prefix):
  at=g.at;cell=g.relative(prefix);uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
 g.take('4053','56','57','4154','4155','4156','4157','4883ec50','4d8bf0','4c8bea','8bd9','4983783800');g.branch('75',True,1)
 g.take('33ff','4889bc24a8000000','4889bc2498000000');singleton=use('singleton','488b0d');target=call('singleton')
 g.take('4885c0');g.branch('0f84',False)
 g.take('4c8b7818','4c89ac2498000000');image_base=g.relative('4c8d25');collector=g.relative('393d');g.branch('74',True,1)
 g.take('4d85ff');g.branch('0f84',False)
 g.take('498b4638','488b08','48397920');g.branch('75',True,1)
 macro=dispatch.stop_inline_dispatch(regions,g.at,found=found);g.seen.extend(macro['selectedBytes']);g.at=macro['nextInstructionVa']
 need('same-singleton-site',use('singleton','488b0d')==singleton);need('same-singleton-target',call('singleton')==target)
 g.take('4885c0');g.branch('0f84',False)
 g.take('488b4820','4885c9');g.branch('0f84',False)
 use('containsLuaKey','4c8b05');g.take('8bd3');call('containsLuaKey')
 g.take('84c0');g.branch('0f84',True)
 g.take('4883c450','415f','415e','415d','415c','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,calls=calls,usageSites=uses,dispatchMacro=macro,collectorDisabledFlagVa=collector,imageBaseVa=image_base,
  keyBytes=4,payloadBytes=8,payloadInput='same incoming RDX string reference',payloadLocalRsp=[152,160],
  sameStringReferenceTransferred=True,globalDispatcherFieldOffset=24,luaKeySetFieldOffset=32,
  selectedMethodContextAlreadyReadyRequired=True,selectedLuaContainsResult=False,luaDispatchRequested=False,
  entryRspRestored=True,allNonvolatilesRestored=True,callbackEffectsOrPlaybackProved=False)


def empty_lua_keys(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2410','48896c2418','4889742420','57','4154','4155','4156','4157','4883ec30','4883791000','4d8be8','8bda','488bf1')
 g.branch('0f84',True)
 g.take('32c0','488b5c2468','488b6c2470','488b742478','4883c430','415f','415e','415d','415c','5f','c3')
 return dict(selectedBytes=g.seen,bucketArrayFieldOffset=16,selectedBucketArrayRequiredNull=True,returnsFalse=True,
  noCallsOrNonframeWrites=True,entryRspRestored=True,allNonvolatilesRestored=True,
  nonemptyKeyTableSearchProved=False,actualSetContentsOrIdentityObserved=False)
