"""Exact ordinary slot-five value invocation; callback identity stays conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions,entry,*,prepare):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bd9','498bf8','488bf2');g.call(prepare)
 g.take('4c8b0e','4c8bc3','488bd7','488bce','498b8190010000','4d8b8998010000',
  '488b5c2430','488b742438','4883c420','5f','48ffe0')
 return dict(selectedBytes=g.seen,slot=5,callbackOffset=400,methodInfoOffset=408,
  callbackArguments=dict(rcx='incoming RDX receiver',rdx='incoming R8 Reader',r8='incoming R9 output',r9='selected slot MethodInfo'),
  sameIncomingReaderAndOutput=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
  normalReturnViaSelectedCallback=True,actualCallbackIdentityProved=False,wireGrammarAdmitted=False,
  selectedCanonicalCallbackAndCoherentReceiverRequired=True)
