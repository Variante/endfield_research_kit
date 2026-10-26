"""Compose actual Handle retention with its finite nested boxed hash source.

The selected HashSet bucket is empty and has a spare slot. Allocation capacity,
classes, comparer and boxed callback identities are explicit conditions; this
does not observe a live retained handle or infer a hash from value width.
"""
from scripts.game_data.memorypack import leveldata_patrol_retain_sources as outer
from scripts.game_data.memorypack import leveldata_patrol_value_hash_sources as hashing
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-retention-sources.v1'


def need(check,condition):
 if not condition:raise ValueError('patrolRetention.'+check)


def _check(retain,hash_source,pins):
 outer.validate_outer(retain,pins);hashing.validate(hash_source,pins)
 a=retain['proof'];b=hash_source['proof']
 need('same-actual-complete-hash-wrapper',a['imageBase']==b['imageBase']and a['helpers']['valueHash']==b['helpers']['wrapper'])
 for name in(outer.HANDLE,'Beyond.Resource.FAssetProxyUntrackedHandle'):
  x=a['valueLayouts'][name];y=b['fields'][name]
  need('same-actual-nominal-value:'+name,x['typeDefinition']==y['typeDefinition']and x['parent']==y['parent']and x['valueType']is y['valueType']is True
   and x['fields']==[[name,f['typeName'],f['offset']]for f in y['fields']])
 return dict(actualWholeHashWrapper=True,exactHandleAndNestedFieldLayouts=True,selectedNativeAndNestedChildEffects=True,
  nullableObjectArrayShortcutSelected=False,liveComparerAndCallbackSelectionObserved=False)


def compose(retain,hash_source,pins):
 joins=_check(retain,hash_source,pins)
 return packets.norm(dict(schema=SCHEMA,status='validated-conditional-composed-handle-retention-source',nativeInputs=pins,
  proof=dict(retainSource=retain,valueHashSource=hash_source,sourceJoins=joins),
  selectedWholeHandleHashAndSpareSetInsertionProved=True,fullHandlePaddingAndFramesProved=True,
  nullArrayShortcutAssumed=False,liveRetentionOrHashValueObserved=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=retain['conditions']+hash_source['conditions']+[
   'The actual Handle value takes its own one-element boxed field array, then its Untracked value takes its own four-element array. The two boxed ID adjustors and two Byte-backed Enum callbacks must select the recorded actual slot2 target/MethodInfo pairs. A null Object[] path is not selected for this nominal.',
   'The same HashSet comparer, stable positive bucket table, empty selected bucket and spare next slot are required. Native hash/class seeds, allocation/import/TLS/cache identities and payload capacity remain incoming conditions; no successful asset load, live retention or hash value is observed.']))


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 _publication_gate(image,pins);value=compose(outer.derive_outer(image,pins),hashing.derive(image,pins),pins)
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-composed-handle-retention-source'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedWholeHandleHashAndSpareSetInsertionProved','fullHandlePaddingAndFramesProved'))
  and all(value.get(k)is False for k in('nullArrayShortcutAssumed','liveRetentionOrHashValueObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];need('exact-source-joins',p['sourceJoins']==_check(p['retainSource'],p['valueHashSource'],pins))
 return value
